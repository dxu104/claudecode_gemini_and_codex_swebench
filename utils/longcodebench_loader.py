"""
LongCodeBench dataset loader and detector.

This module provides utilities to detect and load LongCodeBench tunable SWE-bench datasets,
which include context files for different context lengths (k values).
"""

from typing import Dict, Optional, List, Any, Union
from datasets import load_dataset, Dataset
import re
import tempfile
import shutil
import zipfile
from pathlib import Path


def is_longcodebench_dataset(dataset_name: str) -> bool:
    """
    Detect if a dataset name indicates a LongCodeBench dataset.
    
    Args:
        dataset_name: HuggingFace dataset identifier or path
        
    Returns:
        True if the dataset appears to be a LongCodeBench dataset
    """
    # Check for common LongCodeBench naming patterns
    patterns = [
        r'longcodebench',
        r'long-code-bench',
        r'\blcb\b',  # Match "LCB" as a word (e.g., "Steefano/LCB")
        r'swebench.*tuned',
        r'swebench.*k\d+',
    ]
    
    dataset_lower = dataset_name.lower()
    return any(re.search(pattern, dataset_lower) for pattern in patterns)


def extract_context_length(dataset_name: str) -> Optional[int]:
    """
    Extract context length (k value) from dataset name if present.
    
    Args:
        dataset_name: HuggingFace dataset identifier
        
    Returns:
        Context length (k) if found, None otherwise
    """
    # Look for patterns like "k20", "k-20", "context-20", etc.
    patterns = [
        r'k-?(\d+)',
        r'context-?(\d+)',
        r'(\d+)k',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, dataset_name.lower())
        if match:
            return int(match.group(1))
    
    return None


def has_context_files(instance: Dict) -> bool:
    """
    Check if an instance contains context files information.
    
    Args:
        instance: A dataset instance
        
    Returns:
        True if the instance has context files information
    """
    # Check for various possible field names
    context_fields = [
        'context_files',
        'context_file_paths',
        'retrieved_files',
        'relevant_files',
        'k_files',
    ]
    
    return any(field in instance and instance[field] for field in context_fields)


def get_context_files(instance: Dict) -> List[str]:
    """
    Extract context files from an instance.
    
    Args:
        instance: A dataset instance
        
    Returns:
        List of file paths (relative to repo root)
    """
    # Try different possible field names
    context_fields = [
        'context_files',
        'context_file_paths',
        'retrieved_files',
        'relevant_files',
        'k_files',
    ]
    
    for field in context_fields:
        if field in instance:
            files = instance[field]
            if isinstance(files, list):
                return files
            elif isinstance(files, str):
                # If it's a string, try to parse it (could be JSON or newline-separated)
                try:
                    import json
                    return json.loads(files)
                except (json.JSONDecodeError, ValueError):
                    # Try newline-separated
                    return [f.strip() for f in files.split('\n') if f.strip()]
    
    return []


def load_longcodebench_from_zip(
    dataset_name: str,
    split: str = "test",
    context_length: Optional[Union[int, str]] = None
) -> Dataset:
    """
    从 zip 文件中加载 LongCodeBench 数据集（Steefano/LCB 格式）。
    
    Args:
        dataset_name: HuggingFace dataset identifier (如 'Steefano/LCB')
        split: Dataset split to load (default: "test")
        context_length: Context length (如 '32K', '128K', '1M' 或整数)
        
    Returns:
        Loaded dataset
    """
    # 找到缓存的 zip 文件
    cache_base = Path.home() / '.cache/huggingface/hub'
    dataset_dir_name = dataset_name.replace("/", "--")
    lcb_dir = cache_base / f'datasets--{dataset_dir_name}'
    
    zip_files = list(lcb_dir.rglob('LongSWE_Bench.zip'))
    if not zip_files:
        raise ValueError(
            f"LongSWE_Bench.zip not found for {dataset_name}. "
            f"Make sure the dataset has been downloaded from HuggingFace."
        )
    
    zip_file = zip_files[0]
    
    # 确定 context length 字符串格式
    if context_length is None:
        # 默认使用 32K
        context_length_str = '32K'
    elif isinstance(context_length, str):
        context_length_str = context_length
    elif isinstance(context_length, int):
        # 将数字转换为字符串格式
        if context_length >= 1000000:
            context_length_str = '1M'
        elif context_length >= 512000:
            context_length_str = '512K'
        elif context_length >= 256000:
            context_length_str = '256K'
        elif context_length >= 128000:
            context_length_str = '128K'
        elif context_length >= 64000:
            context_length_str = '64K'
        else:
            context_length_str = '32K'
    else:
        context_length_str = '32K'
    
    # 创建临时目录
    temp_dir = Path(tempfile.mkdtemp(prefix='longcodebench_'))
    
    try:
        # 解压特定 context length 的数据到临时目录
        with zipfile.ZipFile(zip_file, 'r') as z:
            # 首先检查可用的 splits
            available_splits = set()
            for f in z.namelist():
                if f'LongSWE_Bench/{context_length_str}/' in f:
                    parts = f.split('/')
                    if len(parts) >= 3:
                        split_name = parts[2]  # 例如 'test' 或 'train'
                        if split_name and split_name not in ['dataset_dict.json', 'dataset_info.json', 'state.json']:
                            available_splits.add(split_name)
            
            # 确定实际要使用的 split
            actual_split = split
            if split not in available_splits:
                if 'train' in available_splits:
                    actual_split = 'train'
                    print(f"Note: Split '{split}' not found. Using 'train' instead.")
                elif available_splits:
                    actual_split = list(available_splits)[0]
                    print(f"Note: Split '{split}' not found. Using '{actual_split}' instead.")
                else:
                    # 查找可用的 context lengths
                    available = set()
                    for f in z.namelist():
                        if 'LongSWE_Bench/' in f and f.count('/') >= 2:
                            parts = f.split('/')
                            if len(parts) > 1 and parts[1]:
                                available.add(parts[1])
                    available = sorted(available)
                    raise ValueError(
                        f"No data found for {context_length_str}/{split}. "
                        f"Available context lengths: {available}"
                    )
            
            # 查找需要解压的文件（使用实际可用的 split）
            prefix = f'LongSWE_Bench/{context_length_str}/{actual_split}/'
            files_to_extract = [f for f in z.namelist() if f.startswith(prefix)]
            
            if not files_to_extract:
                raise ValueError(f"No files found for {context_length_str}/{actual_split}")
            
            # 解压文件
            for file_path in files_to_extract:
                z.extract(file_path, temp_dir)
        
        # 构建数据集路径（使用实际可用的 split）
        dataset_path = temp_dir / f'LongSWE_Bench/{context_length_str}/{actual_split}'
        
        # 查找 Arrow 文件
        arrow_files = list(dataset_path.glob('*.arrow'))
        if not arrow_files:
            raise ValueError(f"No Arrow files found in {dataset_path}")
        
        # 使用 load_dataset 加载 Arrow 文件（不指定 split，让库自动检测）
        arrow_file_pattern = str(dataset_path / '*.arrow')
        dataset_dict = load_dataset('arrow', data_files=arrow_file_pattern)
        
        # 从 dataset_dict 中获取实际的 split（使用 actual_split，因为我们已经确定了）
        # 注意：load_dataset 可能返回的 split 名称与文件路径中的不同
        if actual_split in dataset_dict:
            dataset = dataset_dict[actual_split]
        elif 'train' in dataset_dict:
            # 如果请求的 split 不存在，但 train 存在，使用 train
            if actual_split != 'train':
                print(f"Note: Split '{actual_split}' not found. Using 'train' instead.")
            dataset = dataset_dict['train']
        elif len(dataset_dict) == 1:
            # 如果只有一个 split，直接使用它
            loaded_split = list(dataset_dict.keys())[0]
            if loaded_split != actual_split:
                print(f"Note: Split '{actual_split}' not found. Using '{loaded_split}' instead.")
            dataset = list(dataset_dict.values())[0]
        else:
            available = list(dataset_dict.keys())
            raise ValueError(
                f"Could not load split '{actual_split}'. Available splits: {available}"
            )
        
        return dataset
        
    finally:
        # 清理临时目录
        if temp_dir.exists():
            shutil.rmtree(temp_dir)


def load_longcodebench_dataset(
    dataset_name: str,
    split: str = "test",
    context_length: Optional[Union[int, str]] = None
) -> Dataset:
    """
    Load a LongCodeBench dataset, optionally filtering by context length.
    
    Args:
        dataset_name: HuggingFace dataset identifier
        split: Dataset split to load (default: "test", will fallback to "train" if needed)
        context_length: Optional context length to filter by (if dataset has multiple k values)
        
    Returns:
        Loaded dataset
    """
    # 检查是否是 Steefano/LCB 格式（需要特殊处理）
    if 'Steefano/LCB' in dataset_name or 'Steefano--LCB' in dataset_name.replace('/', '--'):
        # 使用 zip 文件加载方法（会自动处理 split 回退）
        return load_longcodebench_from_zip(dataset_name, split, context_length)
    
    # 否则使用标准方法
    try:
        dataset = load_dataset(dataset_name, split=split)
    except Exception as e:
        # 如果标准方法失败，尝试 zip 方法作为后备
        try:
            return load_longcodebench_from_zip(dataset_name, split, context_length)
        except:
            raise ValueError(
                f"Failed to load dataset {dataset_name}: {e}\n"
                "Make sure the dataset exists on HuggingFace and you have access to it."
            )
    
    # If context_length is specified and dataset has a 'k' or 'context_length' field,
    # filter to that specific k value
    if context_length is not None:
        if 'k' in dataset.features:
            dataset = dataset.filter(lambda x: x['k'] == context_length)
        elif 'context_length' in dataset.features:
            dataset = dataset.filter(lambda x: x['context_length'] == context_length)
        else:
            # If no k field, check if dataset name contains k value
            dataset_k = extract_context_length(dataset_name)
            if dataset_k is not None and dataset_k != context_length:
                raise ValueError(
                    f"Dataset {dataset_name} has context length {dataset_k}, "
                    f"but requested {context_length}"
                )
    
    return dataset


def enrich_instance_with_context(instance: Dict, repo_path: str) -> Dict:
    """
    Enrich an instance with context file information if available.
    
    This function can be used to prepare context files for inclusion in prompts.
    
    Args:
        instance: A dataset instance
        repo_path: Path to the repository root
        
    Returns:
        Enriched instance with additional context information
    """
    enriched = instance.copy()
    
    if has_context_files(instance):
        context_files = get_context_files(instance)
        enriched['context_files'] = context_files
        enriched['has_context'] = True
    else:
        enriched['context_files'] = []
        enriched['has_context'] = False
    
    return enriched


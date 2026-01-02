"""
LongCodeBench dataset loader and detector.

This module provides utilities to detect and load LongCodeBench tunable SWE-bench datasets,
which include context files for different context lengths (k values).
"""

from typing import Dict, Optional, List, Any
from datasets import load_dataset, Dataset
import re


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


def load_longcodebench_dataset(
    dataset_name: str,
    split: str = "test",
    context_length: Optional[int] = None
) -> Dataset:
    """
    Load a LongCodeBench dataset, optionally filtering by context length.
    
    Args:
        dataset_name: HuggingFace dataset identifier
        split: Dataset split to load (default: "test")
        context_length: Optional context length to filter by (if dataset has multiple k values)
        
    Returns:
        Loaded dataset
    """
    try:
        dataset = load_dataset(dataset_name, split=split)
    except Exception as e:
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


#!/usr/bin/env python3
"""
Create tunable SWE-bench dataset from original dataset.
Adapted from long-code-bench/src/long_code_bench/data/tune_swebench.py

This module creates a tunable version of SWE-bench where each problem
has multiple variants with different numbers of context files (k values).
"""

import itertools
import os
import pathlib
import random
from copy import deepcopy
from typing import List, Literal, Optional

import datasets as dts
from tqdm.auto import tqdm

# Try to import from swebench (may need to install from source)
try:
    from swebench.swebench.inference.make_datasets.bm25_retrieval import main as bm25_main
    from swebench.swebench.inference.make_datasets.create_instance import (
        PROMPT_FUNCTIONS,
        add_text_inputs,
    )
    from swebench.swebench.inference.make_datasets.create_text_dataset import (
        extract_fields,
    )
    SWEBENCH_AVAILABLE = True
except ImportError:
    SWEBENCH_AVAILABLE = False
    print("⚠️  Warning: swebench.inference.make_datasets modules not available.")
    print("   You may need to install SWE-bench from source:")
    print("   git clone https://github.com/princeton-nlp/SWE-bench.git")
    print("   cd SWE-bench && pip install -e .")

# Try to import count_tokens from long-code-bench or implement a simple version
COUNT_TOKENS_AVAILABLE = False
try:
    # Try to import from long-code-bench if available (check common locations)
    import sys
    possible_paths = [
        "/Users/xudecheng/Memverge/long-code-bench/src",
        os.path.expanduser("~/long-code-bench/src"),
        os.path.join(os.path.dirname(__file__), "../../long-code-bench/src"),
    ]
    for long_code_bench_path in possible_paths:
        if os.path.exists(long_code_bench_path):
            sys.path.insert(0, long_code_bench_path)
            try:
                from long_code_bench.data.count_tokens import count_tokens
                COUNT_TOKENS_AVAILABLE = True
                break
            except ImportError:
                continue
except ImportError:
    pass

if not COUNT_TOKENS_AVAILABLE:
    print("⚠️  Warning: count_tokens not available. Token counting will be skipped.")
    print("   To enable token counting, ensure long-code-bench is available.")


def _process_retrieval_file(dataset: str, splits: List[str], tmp_dir: Optional[str] = None) -> str:
    """Generate BM25 retrieval file for the dataset."""
    if not SWEBENCH_AVAILABLE:
        raise ImportError(
            "swebench.inference.make_datasets modules are required for retrieval. "
            "Please install SWE-bench from source."
        )
    
    if tmp_dir is None:
        tmp_dir = os.getenv("TMPDIR", "/tmp")
    
    print(f"Running BM25 retrieval (this may take a while)...")
    bm25_main(
        dataset,
        document_encoding_style="file_name_and_contents",
        output_dir=tmp_dir,
        splits=splits,
        shard_id=None,
        num_shards=20,
        leave_indexes=False,
    )
    
    if pathlib.Path(dataset).exists():
        data_name = os.path.basename(dataset)
    else:
        data_name = dataset.replace("/", "__")
    
    retrieval_file = f"{tmp_dir}/{data_name}/file_name_and_contents.retrieval.jsonl"
    print(f"✓ Retrieval file generated: {retrieval_file}")
    return retrieval_file


def _save_dataset(
    data: dts.DatasetDict,
    output_dir: Optional[str] = None,
    hfhub_dataset: Optional[str] = None,
) -> None:
    """Save dataset to disk or HuggingFace Hub."""
    if output_dir:
        print(f"\nSaving dataset to {output_dir}...")
        pathlib.Path(output_dir).mkdir(parents=True, exist_ok=True)
        data.save_to_disk(output_dir)
        print(f"✓ Dataset saved to {output_dir}")
    
    if hfhub_dataset:
        token = os.getenv("HF_TOKEN_WRITE")
        if not token:
            raise ValueError(
                "The Hugging Face token is required to push to the hub. "
                "Set HF_TOKEN_WRITE environment variable."
            )
        print(f"\nPushing dataset to HuggingFace Hub: {hfhub_dataset}...")
        data.push_to_hub(hfhub_dataset, token=token)
        print(f"✓ Dataset pushed to {hfhub_dataset}")


def make_tunable_swebench(
    dataset: str,
    splits: List[str],
    prompt_style: Literal["style-2", "style-3", "full_file_gen"],
    retrieval_type: Literal["bm25", "random"],
    max_k: int,
    max_tokens: Optional[int] = None,
    retrieval_file: Optional[str] = None,
    output_dir: Optional[str] = None,
    hfhub_dataset: Optional[str] = None,
    num_workers: int = 1,
) -> None:
    """Create a tunable version of the SWE-Bench dataset.
    
    This function creates a dataset where each problem statement has multiple
    variants with different numbers of context files (k=0 to k=max_k-1).
    
    The generated dataset can be used with any backend (claude, codex, gemini, cline)
    via the swe_bench.py run command.
    
    Args:
        dataset: HuggingFace dataset name or path to dataset on disk
        splits: List of splits to process (e.g., ["test"])
        prompt_style: Prompt style ("style-2", "style-3", or "full_file_gen")
        retrieval_type: Retrieval strategy ("bm25" or "random")
        max_k: Maximum number of files to retrieve (creates k=0 to k=max_k-1 variants)
        max_tokens: Optional max tokens limit
        retrieval_file: Optional path to existing retrieval file
        output_dir: Directory to save the dataset
        hfhub_dataset: Optional HuggingFace dataset name to push to
        num_workers: Number of workers for token counting
    """
    if not SWEBENCH_AVAILABLE:
        raise ImportError(
            "swebench.inference.make_datasets modules are required. "
            "Please install SWE-bench from source:\n"
            "  git clone https://github.com/princeton-nlp/SWE-bench.git\n"
            "  cd SWE-bench && pip install -e ."
        )
    
    # Load dataset
    print(f"\n{'='*60}")
    print(f"Loading dataset: {dataset}")
    print(f"{'='*60}")
    if pathlib.Path(dataset).exists():
        data = dts.load_from_disk(dataset)
    else:
        data = dts.load_dataset(dataset)
    
    if not isinstance(data, dts.DatasetDict):
        raise ValueError("The dataset must be a DatasetDict.")
    
    print(f"✓ Loaded dataset with splits: {list(data.keys())}")
    for split in splits:
        if split in data:
            print(f"  {split}: {len(data[split])} instances")
    
    # Process retrieval file
    if retrieval_file is None and retrieval_type == "bm25":
        retrieval_file = _process_retrieval_file(dataset, splits)
    elif retrieval_file is None:
        raise ValueError("retrieval_file must be provided when retrieval_type != 'bm25'")
    
    # Add text inputs for each split
    print(f"\n{'='*60}")
    print(f"Adding text inputs (retrieval_type: {retrieval_type})")
    print(f"{'='*60}")
    global_instances = {}
    for split in tqdm(splits, desc="Retrieving files"):
        if split not in data:
            print(f"⚠️  Warning: Split '{split}' not found in dataset, skipping")
            continue
        print(f"Processing split: {split}")
        global_instances[split] = {
            x["instance_id"]: deepcopy(x) for x in data[split]
        }
        add_text_inputs(
            global_instances[split],
            retrieval_file,
            max_k,
            prompt_style,
            max_tokens=max_tokens,
            file_source=f"oracle+{retrieval_type}",
            keep_contents=True,
        )
    
    # Build prompts for each k value
    print(f"\n{'='*60}")
    print(f"Building prompts for k=0 to k={max_k-1}")
    print(f"{'='*60}")
    split_instances = {}
    for split, k in tqdm(
        itertools.product(splits, range(max_k)),
        total=len(splits) * max_k,
        desc="Building prompts",
    ):
        if split not in global_instances:
            continue
        split_instances[f"{split}-{k}"] = {
            x["instance_id"]: deepcopy(x)
            for x in global_instances[split].values()
        }
        for instance in split_instances[f"{split}-{k}"].values():
            retrieved_files = len(instance["file_contents"])
            num_files = int(retrieved_files / max_k * k)
            if num_files == 0:
                instance["file_contents"] = instance["oracle_file_contents"]
            else:
                instance["file_contents"] = (
                    dict(list(instance["file_contents"].items())[:num_files])
                    | instance["oracle_file_contents"]
                )
            instance["text_inputs"] = PROMPT_FUNCTIONS[prompt_style](instance)
    
    # Extract fields and create final dataset
    columns = [
        "instance_id",
        "num_files",
        "retrieval_strategy",
        "text",
        "repo",
        "base_commit",
        "problem_statement",
        "hints_text",
        "created_at",
        "patch",
        "test_patch",
        "version",
        "FAIL_TO_PASS",
        "PASS_TO_PASS",
        "environment_setup_commit",
    ]
    
    print(f"\n{'='*60}")
    print(f"Extracting fields and creating final dataset")
    print(f"{'='*60}")
    split_data = {}
    for split in splits:
        if split not in data:
            continue
        print(f"Processing {split} split...")
        split_data[split] = {key: [] for key in columns}
        for instance, k in tqdm(
            itertools.product(data[split], range(max_k)),
            total=len(data[split]) * max_k,
            desc=f"Processing {split} split",
        ):
            datum = extract_fields(
                split_instances[f"{split}-{k}"][instance["instance_id"]]
            )
            if datum is None:
                print("Skipping instance due to missing fields.")
                continue
            datum["num_files"] = k
            datum["retrieval_strategy"] = retrieval_type
            for key in columns:
                split_data[split][key].append(datum[key])
        
        print(f"✓ Finished processing split {split}")
        split_data[split] = dts.Dataset.from_dict(split_data[split])
    
    data_final = dts.DatasetDict(split_data)
    
    # Count tokens if available
    if COUNT_TOKENS_AVAILABLE:
        print(f"\n{'='*60}")
        print(f"Counting tokens")
        print(f"{'='*60}")
        data_final = count_tokens(data_final, num_workers=num_workers)
    else:
        print("\n⚠️  Skipping token counting (count_tokens not available)")
    
    # Save dataset
    _save_dataset(data_final, output_dir, hfhub_dataset)
    
    # Summary
    print(f"\n{'='*60}")
    print(f"✅ Successfully created tunable dataset!")
    print(f"{'='*60}")
    total_instances = sum(len(split_data[s]) for s in splits if s in split_data)
    original_instances = sum(len(data[s]) for s in splits if s in data)
    print(f"Original instances: {original_instances}")
    print(f"Total instances (with variants): {total_instances}")
    print(f"Variants per instance: {max_k} (k=0 to k={max_k-1})")
    print(f"\nYou can now use this dataset with:")
    print(f"  python swe_bench.py run --dataset {output_dir} --longcodebench --backend cline")
    print(f"  python swe_bench.py run --dataset {output_dir} --longcodebench --max-k 10 --backend cline")


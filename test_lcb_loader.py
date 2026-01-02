#!/usr/bin/env python3
"""测试 LongCodeBench 数据集加载器"""

from utils.longcodebench_loader import (
    load_longcodebench_dataset,
    load_longcodebench_from_zip,
    is_longcodebench_dataset
)

def test_loader():
    dataset_name = "Steefano/LCB"
    
    print(f"Testing dataset: {dataset_name}")
    print(f"Is LongCodeBench: {is_longcodebench_dataset(dataset_name)}")
    
    try:
        # 测试加载 32K 的数据（使用 train split，因为数据集只有 train）
        print("\n=== Testing 32K context length ===")
        dataset = load_longcodebench_dataset(dataset_name, split="train", context_length="32K")
        print(f"✓ Successfully loaded dataset")
        print(f"  Dataset size: {len(dataset)}")
        print(f"  Features: {list(dataset.features.keys())[:10]}")
        
        if len(dataset) > 0:
            first = dataset[0]
            print(f"\n  First instance keys: {list(first.keys())[:10]}")
            
            # 检查关键字段
            swe_fields = ['instance_id', 'repo', 'problem_statement', 'base_commit']
            print("\n  SWE-bench fields:")
            for field in swe_fields:
                if field in first:
                    value = first[field]
                    if isinstance(value, str):
                        display = value[:50] + "..." if len(value) > 50 else value
                        print(f"    {field}: {display}")
            
            # 检查 context files
            context_fields = ['context_files', 'retrieved_files', 'relevant_files', 'k_files', 'splits']
            print("\n  Context-related fields:")
            for field in context_fields:
                if field in first:
                    value = first[field]
                    if isinstance(value, list):
                        print(f"    {field}: list with {len(value)} items")
                        if len(value) > 0:
                            print(f"      First item: {value[0]}")
                    else:
                        print(f"    {field}: {type(value).__name__}")
        
        print("\n✓ Test passed! Dataset loading works.")
        return True
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_loader()
    exit(0 if success else 1)


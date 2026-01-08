"""
Context window size analyzer for LongCodeBench datasets.

This module provides utilities to analyze and report context window sizes
for different k-values (num_files) in tunable SWE-bench datasets.
"""

from typing import Dict, List, Optional
from collections import defaultdict
from datasets import Dataset

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False


def count_tokens(text: str, model: str = "gpt-4") -> int:
    """
    Count tokens in text using tiktoken (GPT-4 encoding).
    
    Falls back to word-based estimation if tiktoken is not available.
    
    Args:
        text: Input text string
        model: Model name for encoding (default: "gpt-4")
        
    Returns:
        Token count (or -1 if tiktoken is not available and estimation fails)
    """
    if not text:
        return 0
    
    # Try to use tiktoken for accurate token counting
    if TIKTOKEN_AVAILABLE:
        try:
            encoding = tiktoken.encoding_for_model(model)
            return len(encoding.encode(text))
        except Exception:
            # If specified model doesn't exist, try cl100k_base (GPT-4 and GPT-3.5 use this)
            try:
                encoding = tiktoken.get_encoding("cl100k_base")
                return len(encoding.encode(text))
            except Exception:
                pass
    
    # Fallback to word-based estimation if tiktoken is not available
    # Uses the approximation: 1 token ≈ 0.75 words
    words = text.split()
    num_words = len(words)
    tokens = int(num_words / 0.75)
    
    return tokens


def analyze_context_by_k(dataset: Dataset, instance_id: Optional[str] = None) -> Dict:
    """
    Analyze context window sizes grouped by k-value (num_files).
    
    Args:
        dataset: LongCodeBench dataset
        instance_id: Optional instance ID to filter by
        
    Returns:
        Dictionary with analysis results:
        {
            k_value: {
                'count': number of instances,
                'avg_tokens': average token count,
                'min_tokens': minimum token count,
                'max_tokens': maximum token count,
                'avg_chars': average character count,
                'min_chars': minimum character count,
                'max_chars': maximum character count,
            }
        }
    """
    # Group instances by k-value (num_files)
    k_groups = defaultdict(list)
    
    for instance in dataset:
        # Filter by instance_id if specified
        if instance_id and instance.get('instance_id') != instance_id:
            continue
            
        k_value = instance.get('num_files', 0)
        text = instance.get('text', '')
        
        if text:
            tokens = count_tokens(text)
            chars = len(text)
            k_groups[k_value].append({
                'tokens': tokens,
                'chars': chars,
                'instance_id': instance.get('instance_id', 'unknown')
            })
    
    # Calculate statistics for each k-value
    results = {}
    for k_value in sorted(k_groups.keys()):
        instances = k_groups[k_value]
        if not instances:
            continue
            
        tokens_list = [inst['tokens'] for inst in instances]
        chars_list = [inst['chars'] for inst in instances]
        
        results[k_value] = {
            'count': len(instances),
            'avg_tokens': int(sum(tokens_list) / len(tokens_list)),
            'min_tokens': min(tokens_list),
            'max_tokens': max(tokens_list),
            'avg_chars': int(sum(chars_list) / len(chars_list)),
            'min_chars': min(chars_list),
            'max_chars': max(chars_list),
        }
    
    return results


def print_context_analysis(analysis: Dict, instance_id: Optional[str] = None):
    """
    Print a formatted analysis of context window sizes by k-value.
    
    Args:
        analysis: Results from analyze_context_by_k()
        instance_id: Optional instance ID for display
    """
    if not analysis:
        print("No context analysis data available.")
        return
    
    print("\n" + "=" * 80)
    print("📊 CONTEXT WINDOW SIZE ANALYSIS BY K-VALUE (num_files)")
    print("=" * 80)
    if instance_id:
        print(f"Instance ID: {instance_id}")
    print(f"\n{'K-Value':<10} {'Count':<8} {'Avg Tokens':<15} {'Min Tokens':<15} {'Max Tokens':<15} {'Avg Chars':<15}")
    print("-" * 80)
    
    for k_value in sorted(analysis.keys()):
        stats = analysis[k_value]
        print(f"{k_value:<10} {stats['count']:<8} {stats['avg_tokens']:<15,} {stats['min_tokens']:<15,} {stats['max_tokens']:<15,} {stats['avg_chars']:<15,}")
    
    print("=" * 80)
    if TIKTOKEN_AVAILABLE:
        print(f"Note: Token count uses tiktoken (GPT-4 encoding: cl100k_base)")
    else:
        print(f"Note: Token count estimation uses 1 token ≈ 0.75 words (tiktoken not available)")
    print("=" * 80 + "\n")


def analyze_dataset_context(dataset: Dataset, instance_id: Optional[str] = None, 
                            print_results: bool = True) -> Dict:
    """
    Analyze and optionally print context window statistics for a dataset.
    
    Args:
        dataset: LongCodeBench dataset
        instance_id: Optional instance ID to filter by
        print_results: Whether to print formatted results
        
    Returns:
        Analysis results dictionary
    """
    analysis = analyze_context_by_k(dataset, instance_id)
    
    if print_results:
        print_context_analysis(analysis, instance_id)
    
    return analysis


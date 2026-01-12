#!/usr/bin/env python3
"""
Enhanced SWE-bench benchmark runner with real evaluation support
"""

import argparse
import json
import os
import sys
import subprocess
import time
from datetime import datetime
from pathlib import Path
import logging
import jsonlines
from collections import defaultdict
from datasets import load_dataset
from utils.longcodebench_loader import is_longcodebench_dataset

class EnhancedBenchmarkRunner:
    def __init__(self, model=None, backend="claude", longcodebench=False, context_length=None, max_k=None, instance_id=None, timeout=None):
        self.base_dir = Path.cwd()
        self.log_file = self.base_dir / "benchmark_scores.log"
        self.summary_file = self.base_dir / "benchmark_scores_summary.txt"
        self.predictions_dir = self.base_dir / "predictions"
        self.results_dir = self.base_dir / "results"
        self.eval_results_dir = self.base_dir / "evaluation_results"
        self.model = model
        self.backend = backend
        self.longcodebench = longcodebench
        self.context_length = context_length
        self.max_k = max_k
        self.instance_id = instance_id
        # Default timeout: 8 hours (28800 seconds), or None for unlimited
        self.timeout = timeout if timeout is not None else 28800
        
        # Create directories
        self.predictions_dir.mkdir(exist_ok=True)
        self.results_dir.mkdir(exist_ok=True)
        self.eval_results_dir.mkdir(exist_ok=True)
        
    def log_result(self, dataset_name, num_instances, generation_score, 
                   evaluation_score, generation_time, evaluation_time, 
                   prediction_file, notes="", evaluation_status="pending"):
        """Log comprehensive benchmark results"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        log_entry = {
            "timestamp": timestamp,
            "prediction_file": str(prediction_file),
            "dataset": dataset_name,
            "num_instances": num_instances,
            "generation_score": generation_score,
            "evaluation_score": evaluation_score,
            "evaluation_status": evaluation_status,
            "generation_time": generation_time,
            "evaluation_time": evaluation_time,
            "model": self.model,
            "backend": self.backend,
            "notes": notes
        }
        
        # Append to log file (JSON format)
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
        
        # Append formatted summary to summary file
        self._write_formatted_summary(log_entry, generation_score, evaluation_score, 
                                     evaluation_status, generation_time, evaluation_time)
        
        print(f"\n✅ Results logged to {self.log_file}")
        print(f"✅ Formatted summary saved to {self.summary_file}")
        if evaluation_status == "completed":
            print(f"   Generation Score: {generation_score:.2f}% (patches created)")
            print(f"   Evaluation Score: {evaluation_score:.2f}% (issues fixed) ← REAL SCORE")
        else:
            print(f"   Generation Score: {generation_score:.2f}% (patches created)")
            print(f"   Evaluation: {evaluation_status}")
    
    def _write_formatted_summary(self, log_entry, generation_score, evaluation_score,
                                evaluation_status, generation_time, evaluation_time):
        """Write formatted summary to summary file"""
        timestamp = log_entry.get("timestamp", "")
        dataset = log_entry.get("dataset", "")
        num_instances = log_entry.get("num_instances", 0)
        model = log_entry.get("model") or "default"
        backend = log_entry.get("backend", "unknown")
        notes = log_entry.get("notes", "")
        
        with open(self.summary_file, 'a', encoding='utf-8') as f:
            f.write("\n" + "="*80 + "\n")
            f.write(f"BENCHMARK RUN SUMMARY - {timestamp}\n")
            f.write("="*80 + "\n")
            f.write(f"Dataset: {dataset}\n")
            f.write(f"Backend: {backend}\n")
            if model and model != "default":
                f.write(f"Model: {model}\n")
            f.write(f"Instances tested: {num_instances}\n")
            f.write(f"\nGeneration Score: {generation_score:.2f}% (patches created)\n")
            f.write(f"  Generation time: {generation_time:.1f}s\n")
            
            if evaluation_status == "completed":
                f.write(f"\nEvaluation Score: {evaluation_score:.2f}% (issues fixed) ← REAL SCORE\n")
                f.write(f"  Evaluation time: {evaluation_time:.1f}s\n")
                f.write(f"\n🎯 Real Success Rate: {evaluation_score:.2f}%\n")
            elif evaluation_status == "skipped":
                f.write(f"\nEvaluation: SKIPPED (use without --skip-eval for real scores)\n")
            else:
                f.write(f"\nEvaluation: {evaluation_status.upper()}\n")
            
            total_time = generation_time + evaluation_time
            f.write(f"\nTotal time: {total_time:.1f} seconds\n")
            f.write(f"  Generation: {generation_time:.1f}s\n")
            if evaluation_time > 0:
                f.write(f"  Evaluation: {evaluation_time:.1f}s\n")
            
            if notes:
                f.write(f"\nNotes: {notes}\n")
            
            f.write("="*80 + "\n")
            
    def run_inference(self, dataset_name, limit):
        """Run code model on the dataset"""
        model_info = f" with model {self.model}" if self.model else ""
        print(f"\n🚀 Running {self.backend.title()} Code{model_info} on {dataset_name} (limit: {limit})...")

        cmd = [
            sys.executable,
            "code_swe_agent.py",
            "--dataset_name", dataset_name,
            "--backend", self.backend,
        ]
        
        # Only add --limit if it's not None
        if limit is not None:
            cmd.extend(["--limit", str(limit)])

        if self.model:
            cmd.extend(["--model", self.model])
        
        if self.longcodebench:
            cmd.append("--longcodebench")
        
        if self.context_length is not None:
            cmd.extend(["--context-length", str(self.context_length)])
        
        if self.max_k is not None:
            cmd.extend(["--max-k", str(self.max_k)])
        
        if self.instance_id is not None:
            cmd.extend(["--instance-id", self.instance_id])
        
        try:
            start_time = time.time()
            timeout_seconds = self.timeout  # Use configured timeout (default: 8 hours)
            # Use Popen to stream output in real-time
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Print output in real-time with timeout handling
            output_lines = []
            timeout_reached = False
            end_time = start_time + timeout_seconds if timeout_seconds is not None else float('inf')
            
            for line in iter(process.stdout.readline, ''):
                current_time = time.time()
                if timeout_seconds is not None and current_time > end_time:
                    timeout_reached = True
                    process.kill()
                    print(f"\n❌ Inference timed out after {timeout_seconds} seconds ({timeout_seconds/3600:.1f} hours)")
                    break
                print(line, end='', flush=True)
                output_lines.append(line)
            
            if not timeout_reached:
                process.wait()
            
            execution_time = time.time() - start_time
            
            if timeout_reached:
                return None, execution_time
            
            if process.returncode != 0:
                print(f"⚠️ Warning: Inference had issues but continuing...")
                if output_lines:
                    # Show last 20 lines of output for debugging
                    print(f"Last 20 lines of output:")
                    for line in output_lines[-20:]:
                        print(f"  {line.rstrip()}")
            
            # Find the latest prediction file (exclude _eval.jsonl files)
            pred_files = [
                f for f in sorted(self.predictions_dir.glob("predictions_*.jsonl"), reverse=True)
                if "_eval.jsonl" not in str(f)
            ]
            
            if not pred_files:
                print("❌ No prediction files generated")
                return None, execution_time
                
            latest_pred = pred_files[0]
            print(f"✅ Predictions saved to: {latest_pred}")
            return str(latest_pred), execution_time
            
        except Exception as e:
            if 'process' in locals() and process.poll() is None:
                process.kill()
            print(f"❌ Error during inference: {e}")
            import traceback
            traceback.print_exc()
            return None, 0
            
    def calculate_generation_score(self, prediction_file):
        """Calculate score based on patch generation (not real score)"""
        if not prediction_file or not Path(prediction_file).exists():
            return 0.0, 0
        
        total = 0
        generated = 0
        
        with jsonlines.open(prediction_file) as reader:
            for obj in reader:
                total += 1
                # Check if a non-empty patch was generated
                if obj.get("prediction", "").strip():
                    generated += 1
        
        if total == 0:
            return 0.0, 0
            
        score = (generated / total) * 100
        return score, total
        
    def run_evaluation(self, prediction_file, dataset_name, max_workers=2):
        """Run real SWE-bench evaluation using Docker"""
        print(f"\n🔬 Running real evaluation on {prediction_file}...")
        print("This will test if patches actually fix the issues (takes time)...")
        
        # Load predictions
        predictions = []
        with jsonlines.open(prediction_file) as reader:
            for obj in reader:
                predictions.append(obj)
        
        # Check if this is a tunable dataset (has num_files field)
        has_num_files = any("num_files" in pred for pred in predictions)
        is_tunable = (is_longcodebench_dataset(dataset_name) or self.longcodebench) and has_num_files
        
        # For LongCodeBench datasets, use the original SWE-bench dataset for evaluation
        evaluation_dataset = dataset_name
        if is_longcodebench_dataset(dataset_name) or self.longcodebench:
            if "Verified" in dataset_name or "verified" in dataset_name.lower():
                evaluation_dataset = "princeton-nlp/SWE-bench_Verified"
            else:
                evaluation_dataset = "princeton-nlp/SWE-bench"
                print(f"[LongCodeBench] Using original SWE-bench dataset for evaluation: {evaluation_dataset}")
        
        model_name = f"{self.backend}-code"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_run_id = f"{self.backend}_code_{timestamp}"
        
        # If tunable dataset, evaluate each k-value group separately
        if is_tunable:
            print(f"[Tunable] Detected tunable dataset with k-value variants. Evaluating each k-value group separately...")
            
            # Group predictions by num_files (k value)
            predictions_by_k = defaultdict(list)
            for pred in predictions:
                k_value = pred.get("num_files", 0)
                predictions_by_k[k_value].append(pred)
            
            print(f"[Tunable] Found {len(predictions_by_k)} k-value groups: {sorted(predictions_by_k.keys())}")
            
            results_by_k = {}
            total_eval_time = 0
            total_resolved = 0
            total_instances = 0
            
            # Evaluate each k-value group
            for k_value in sorted(predictions_by_k.keys()):
                k_predictions = predictions_by_k[k_value]
                print(f"\n{'='*60}")
                print(f"Evaluating k={k_value} ({len(k_predictions)} instances)")
                print(f"{'='*60}")
                
                # Create temporary eval file for this k-value group
                tmp_dir = Path(os.getenv("TMPDIR", "/tmp"))
                tmp_eval_file = tmp_dir / f"pred_{base_run_id}_k{k_value}_eval.jsonl"
                
                with jsonlines.open(tmp_eval_file, mode='w') as writer:
                    for pred in k_predictions:
                        eval_pred = {
                            "instance_id": pred.get("instance_id", ""),
                            "model_name_or_path": model_name,
                            "model_patch": pred.get("prediction", "")
                        }
                        writer.write(eval_pred)
                
                # Run evaluation for this k-value group
                k_run_id = f"{base_run_id}_k{k_value}"
                cmd = [
                    sys.executable, "-m", "swebench.harness.run_evaluation",
                    "--predictions_path", str(tmp_eval_file),
                    "--dataset_name", evaluation_dataset,
                    "--split", "test",
                    "--run_id", k_run_id,
                    "--max_workers", str(max_workers),
                    "--timeout", "600",
                    "--cache_level", "env",
                    "--out_dir", str(self.eval_results_dir),
                ]
                
                print(f"Running: {' '.join(cmd)}")
                
                try:
                    start_time = time.time()
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        bufsize=1,
                        cwd=str(self.eval_results_dir),
                    )
                    
                    output_lines = []
                    for line in iter(process.stdout.readline, ''):
                        print(line, end='')
                        output_lines.append(line)
                    
                    process.wait()
                    k_eval_time = time.time() - start_time
                    total_eval_time += k_eval_time
                    
                    # Check if there were network errors but evaluation might have completed
                    output_text = ''.join(output_lines)
                    has_network_error = 'ReadTimeout' in output_text or 'Connection timed out' in output_text
                    if has_network_error and process.returncode != 0:
                        print(f"\n⚠️  Network timeout error detected for k={k_value}, but checking if evaluation completed...")
                    
                    # Parse results for this k-value
                    # Note: k_total should always be len(k_predictions), not the total_instances from evaluation
                    # because evaluation reports total_instances for the entire dataset, not just this k-value group
                    k_total = len(k_predictions)
                    json_path = self.eval_results_dir / f"{model_name}.{k_run_id}.json"
                    k_resolved = None
                    if json_path.exists():
                        try:
                            with open(json_path) as f:
                                data = json.load(f)
                            k_resolved = data.get("resolved_instances", 0)
                            results_by_k[k_value] = data
                        except (OSError, json.JSONDecodeError) as exc:
                            logging.warning(f"Failed to parse evaluation JSON for k={k_value}: {exc}")
                    
                    if k_resolved is None:
                        # Fallback to regex parsing
                        import re
                        match = re.search(r'Instances resolved: (\d+)', output_text)
                        if match:
                            k_resolved = int(match.group(1))
                        else:
                            # If we can't find resolved count, assume 0 (evaluation failed)
                            k_resolved = 0
                            if has_network_error:
                                print(f"⚠️  Could not parse results for k={k_value} due to network error")
                    
                    k_score = (k_resolved / k_total * 100) if k_total else 0
                    total_resolved += k_resolved
                    total_instances += k_total  # This is now correct: len(k_predictions) for each group
                    
                    if has_network_error and k_resolved > 0:
                        print(f"\n📊 k={k_value} Evaluation Score: {k_score:.2f}% ({k_resolved}/{k_total} issues fixed) [Note: Network timeout occurred but evaluation completed]")
                    else:
                        print(f"\n📊 k={k_value} Evaluation Score: {k_score:.2f}% ({k_resolved}/{k_total} issues fixed)")
                    
                    # Clean up temporary file
                    if tmp_eval_file.exists():
                        tmp_eval_file.unlink()
                        
                except Exception as e:
                    print(f"\n⚠️ Evaluation error for k={k_value}: {e}")
                    import traceback
                    traceback.print_exc()
                    results_by_k[k_value] = {"error": str(e)}
            
            # Summary across all k-values
            print(f"\n{'='*60}")
            print(f"📊 TUNABLE DATASET EVALUATION SUMMARY")
            print(f"{'='*60}")
            for k_value in sorted(results_by_k.keys()):
                if "error" not in results_by_k[k_value]:
                    k_data = results_by_k[k_value]
                    k_resolved = k_data.get("resolved_instances", 0)
                    # Use the actual number of predictions for this k-value, not total_instances from evaluation
                    k_total = len(predictions_by_k[k_value])
                    k_score = (k_resolved / k_total * 100) if k_total else 0
                    print(f"  k={k_value}: {k_score:.2f}% ({k_resolved}/{k_total} issues fixed)")
                else:
                    print(f"  k={k_value}: ERROR - {results_by_k[k_value]['error']}")
            
            overall_score = (total_resolved / total_instances * 100) if total_instances else 0
            print(f"\n📊 Overall Score: {overall_score:.2f}% ({total_resolved}/{total_instances} issues fixed)")
            print(f"⏱️  Total Evaluation Time: {total_eval_time:.1f}s")
            
            # Save combined results
            combined_results_file = self.eval_results_dir / f"{model_name}.{base_run_id}_combined.json"
            with open(combined_results_file, 'w') as f:
                json.dump({
                    "overall": {
                        "resolved_instances": total_resolved,
                        "total_instances": total_instances,
                        "score": overall_score
                    },
                    "by_k": results_by_k
                }, f, indent=2)
            
            return overall_score, total_eval_time
        
        else:
            # Standard evaluation (non-tunable or no num_files field)
            eval_file = prediction_file.replace('.jsonl', '_eval.jsonl')
            
            with jsonlines.open(eval_file, mode='w') as writer:
                for pred in predictions:
                    eval_pred = {
                        "instance_id": pred.get("instance_id", ""),
                        "model_name_or_path": model_name,
                        "model_patch": pred.get("prediction", "")
                    }
                    writer.write(eval_pred)
            
            # Run evaluation
            run_id = base_run_id
            
            cmd = [
                sys.executable, "-m", "swebench.harness.run_evaluation",
                "--predictions_path", eval_file,
                "--dataset_name", evaluation_dataset,
                "--split", "test",
                "--run_id", run_id,
                "--max_workers", str(max_workers),
                "--timeout", "600",
                "--cache_level", "env",
                "--out_dir", str(self.eval_results_dir),
            ]
            
            print(f"Running: {' '.join(cmd)}")
            
            try:
                start_time = time.time()
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    cwd=str(self.eval_results_dir),
                )
                
                output_lines = []
                for line in iter(process.stdout.readline, ''):
                    print(line, end='')
                    output_lines.append(line)
                
                process.wait()
                eval_time = time.time() - start_time

                json_path = self.eval_results_dir / f"{model_name}.{run_id}.json"
                resolved = total = None
                if json_path.exists():
                    try:
                        with open(json_path) as f:
                            data = json.load(f)
                        resolved = data.get("resolved_instances")
                        total = data.get("total_instances") or len(predictions)
                    except (OSError, json.JSONDecodeError) as exc:
                        logging.warning(f"Failed to parse evaluation JSON: {exc}")

                if resolved is None or total is None:
                    logging.warning("Structured evaluation results missing; falling back to regex parsing.")
                    output_text = ''.join(output_lines)
                    import re
                    patterns = [
                        r'Instances resolved: (\d+)',
                        r'(\d+) of (\d+) instances',
                        r'(\d+)/(\d+) resolved',
                        r'resolved (\d+) of (\d+)',
                        r'Success Rate: (\d+\.?\d*)\%'
                    ]
                    resolved = None
                    total = None
                    for pattern in patterns:
                        match = re.search(pattern, output_text)
                        if match:
                            if '%' in pattern:
                                return float(match.group(1)), eval_time
                            elif 'Instances resolved' in pattern:
                                resolved = int(match.group(1))
                                total = len(predictions)
                                break
                            else:
                                resolved = int(match.group(1))
                                total = int(match.group(2)) if len(match.groups()) > 1 else len(predictions)
                                break
                    if resolved is None or total is None:
                        print("\n⚠️ Could not parse evaluation results")
                        return None, eval_time

                score = (resolved / total) * 100 if total else 0
                print(f"\n📊 Real Evaluation Score: {score:.2f}% ({resolved}/{total} issues fixed)")
                return score, eval_time
                    
            except subprocess.TimeoutExpired:
                print("\n⚠️ Evaluation timed out")
                return None, 1800
            except Exception as e:
                print(f"\n⚠️ Evaluation error: {e}")
                return None, 0

def main():
    parser = argparse.ArgumentParser(
        description="Run SWE-bench benchmark with real evaluation scores"
    )
    parser.add_argument("--dataset", default="princeton-nlp/SWE-bench_Lite", 
                       help="Dataset to use")
    parser.add_argument("--limit", type=int, default=5,
                       help="Number of instances to test (default: 5)")
    parser.add_argument("--skip-eval", action="store_true",
                       help="Skip Docker evaluation (faster but no real scores)")
    parser.add_argument("--max-workers", type=int, default=2,
                       help="Max parallel Docker containers for evaluation (default: 2)")
    parser.add_argument("--notes", default="",
                       help="Optional notes about this run")
    parser.add_argument("--longcodebench", action="store_true",
                       help="Explicitly indicate this is a LongCodeBench dataset")
    parser.add_argument("--context-length", type=str, metavar="K",
                       help="Context length for LongCodeBench datasets (e.g., '32K', '128K', '1M' or integer)")
    parser.add_argument("--max-k", type=int, metavar="K",
                       help="Maximum number of context files (k value) to include. Only instances with num_files <= max_k will be used.")
    parser.add_argument("--instance-id", type=str, metavar="ID",
                       help="Specific instance ID to process. For tunable datasets, this will process all k-value variants of this instance.")
    parser.add_argument("--timeout", type=int, metavar="SECONDS",
                       help="Timeout for inference in seconds (default: 28800 = 8 hours). Use 0 for unlimited timeout.")
    
    args = parser.parse_args()
    
    # Handle timeout: 0 means unlimited (None), otherwise use provided value
    timeout_value = None if (hasattr(args, 'timeout') and args.timeout == 0) else (args.timeout if hasattr(args, 'timeout') and args.timeout else None)
    
    runner = EnhancedBenchmarkRunner(
        longcodebench=args.longcodebench,
        context_length=args.context_length,
        max_k=args.max_k if hasattr(args, 'max_k') else None,
        instance_id=args.instance_id if hasattr(args, 'instance_id') else None,
        timeout=timeout_value
    )
    
    print("="*60)
    print("Enhanced SWE-bench Benchmark Runner")
    print("="*60)
    print(f"Dataset: {args.dataset}")
    print(f"Instances: {args.limit}")
    print(f"Evaluation: {'SKIPPED (fast mode)' if args.skip_eval else 'ENABLED (real scores)'}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run inference
    print("\nPhase 1: Generating patches with Claude Code...")
    start_time = time.time()
    prediction_file, generation_time = runner.run_inference(args.dataset, args.limit)
    
    if not prediction_file:
        print("❌ Failed to generate predictions")
        runner.log_result(
            args.dataset, args.limit, 0.0, None, generation_time, 0,
            None, f"Failed to generate predictions. {args.notes}", "failed"
        )
        return
    
    # Calculate generation score
    generation_score, total_instances = runner.calculate_generation_score(prediction_file)
    print(f"\n📈 Generation Score: {generation_score:.2f}% ({int(generation_score * total_instances / 100)}/{total_instances} patches generated)")
    
    # Run evaluation if not skipped
    evaluation_score = None
    evaluation_time = 0
    evaluation_status = "skipped" if args.skip_eval else "pending"
    
    if not args.skip_eval:
        print("\nPhase 2: Evaluating patches with Docker (testing if they work)...")
        evaluation_score, evaluation_time = runner.run_evaluation(
            prediction_file, args.dataset, args.max_workers
        )
        
        if evaluation_score is not None:
            evaluation_status = "completed"
        else:
            evaluation_status = "failed"
            evaluation_score = 0.0
    
    total_time = time.time() - start_time
    
    # Log results
    runner.log_result(
        args.dataset, total_instances, generation_score,
        evaluation_score, generation_time, evaluation_time,
        prediction_file, args.notes, evaluation_status
    )
    
    # Display summary
    print("\n" + "="*60)
    print("BENCHMARK SUMMARY")
    print("="*60)
    print(f"Dataset: {args.dataset}")
    print(f"Instances tested: {total_instances}")
    print(f"Generation Score: {generation_score:.2f}% (patches created)")
    
    if evaluation_status == "completed":
        print(f"Evaluation Score: {evaluation_score:.2f}% (issues actually fixed) ← REAL SCORE")
        print(f"\n🎯 Real Success Rate: {evaluation_score:.2f}%")
    elif evaluation_status == "skipped":
        print("Evaluation: SKIPPED (use without --skip-eval for real scores)")
    else:
        print("Evaluation: FAILED")
    
    print(f"\nTotal time: {total_time:.1f} seconds")
    print(f"  Generation: {generation_time:.1f}s")
    if evaluation_time > 0:
        print(f"  Evaluation: {evaluation_time:.1f}s")
    
    print(f"\nResults logged to: {runner.log_file}")
    print(f"Formatted summary saved to: {runner.summary_file}")
    
    # Show recent scores
    print("\n📊 Recent runs:")
    if runner.log_file.exists():
        with open(runner.log_file, 'r') as f:
            lines = f.readlines()
            recent = lines[-5:] if len(lines) >= 5 else lines
            for line in recent:
                entry = json.loads(line)
                gen_score = entry.get('generation_score', 0)
                eval_score = entry.get('evaluation_score')
                status = entry.get('evaluation_status', 'unknown')
                
                if status == "completed" and eval_score is not None:
                    print(f"  {entry['timestamp']}: Gen={gen_score:.1f}% → Eval={eval_score:.1f}% (real)")
                else:
                    print(f"  {entry['timestamp']}: Gen={gen_score:.1f}% ({status})")

if __name__ == "__main__":
    main()
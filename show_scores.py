#!/usr/bin/env python3
"""
Score summary viewer for SWE-bench benchmark results
Shows all tests with real vs placeholder scores, trends, and statistics
"""

import json
import argparse
from datetime import datetime
from pathlib import Path
import csv
from typing import List, Dict

class ScoreViewer:
    def __init__(self):
        self.base_dir = Path.cwd()
        self.log_file = self.base_dir / "benchmark_scores.log"
        self.predictions_dir = self.base_dir / "predictions"
        self.eval_results_dir = self.base_dir / "evaluation_results"
        
    def load_scores(self) -> List[Dict]:
        """Load all scores from log file"""
        if not self.log_file.exists():
            print(f"No log file found at {self.log_file.absolute()}")
            return []
        
        scores = []
        with open(self.log_file, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    scores.append(entry)
                except json.JSONDecodeError:
                    print(f"Warning: Skipping invalid JSON line: {line.strip()}")
                except Exception as exc:
                    print(f"Warning: Failed to parse line due to {exc}: {line.strip()}")

        return scores
    
    def display_scores(self, scores: List[Dict], filter_type="all"):
        """Display scores in a formatted table"""
        if not scores:
            print("No scores to display.")
            return
        
        # Filter scores
        if filter_type == "evaluated":
            scores = [s for s in scores if s.get("evaluation_status") == "completed"]
        elif filter_type == "pending":
            scores = [s for s in scores if s.get("evaluation_status") != "completed"]
        
        print("\n" + "="*100)
        print(f"{'Timestamp':<20} {'Instances':>10} {'Gen Score':>10} {'Eval Score':>10} {'Status':<12} {'Notes'}")
        print("="*100)
        
        for entry in scores:
            # Safely extract values with proper defaults
            timestamp = str(entry.get("timestamp") or "Unknown")[:19]
            instances = entry.get("num_instances")
            gen_score = entry.get("generation_score")
            eval_score = entry.get("evaluation_score")
            status = entry.get("evaluation_status") or "unknown"
            notes = str(entry.get("notes") or "")[:30]
            
            # Convert to safe numeric types
            try:
                instances = int(instances) if instances is not None else 0
            except (ValueError, TypeError):
                instances = 0
            
            try:
                gen_score = float(gen_score) if gen_score is not None else 0.0
            except (ValueError, TypeError):
                gen_score = 0.0
            
            # Format eval score
            if eval_score is not None:
                try:
                    eval_str = f"{float(eval_score):>9.1f}%"
                except (ValueError, TypeError):
                    eval_str = "      -   "
            else:
                eval_str = "      -   "
            
            # Status indicator
            if status == "completed":
                status_str = "✓ Evaluated"
            elif status == "pending":
                status_str = "○ Pending"
            elif status == "skipped":
                status_str = "- Skipped"
            else:
                status_str = "? " + str(status)[:10]
            
            # Print with safe formatting
            try:
                print(f"{timestamp:<20} {instances:>10} {gen_score:>9.1f}% {eval_str} {status_str:<12} {notes}")
            except Exception as e:
                # Fallback for any unexpected errors
                print(f"{timestamp:<20} {'ERROR':>10} {'ERROR':>10} {'ERROR':>10} {'ERROR':<12} {str(e)[:30]}")
        
        print("="*100)
    
    def show_statistics(self, scores: List[Dict]):
        """Show statistics and trends"""
        if not scores:
            return
        
        evaluated = [s for s in scores if s.get("evaluation_status") == "completed"]
        pending = [s for s in scores if s.get("evaluation_status") != "completed"]
        
        print("\n" + "="*60)
        print("STATISTICS")
        print("="*60)
        
        print(f"Total runs: {len(scores)}")
        print(f"  - Evaluated: {len(evaluated)}")
        print(f"  - Pending evaluation: {len(pending)}")
        
        if evaluated:
            gen_scores = [s.get("generation_score", 0) or 0 for s in evaluated]
            eval_scores = [s.get("evaluation_score", 0) for s in evaluated 
                          if s.get("evaluation_score") is not None]
            
            # Convert to float safely
            gen_scores = [float(g) if g is not None else 0.0 for g in gen_scores]
            eval_scores = [float(e) if e is not None else 0.0 for e in eval_scores]
            
            if gen_scores:
                print(f"\nGeneration Scores (patches created):")
                print(f"  Average: {sum(gen_scores)/len(gen_scores):.1f}%")
                print(f"  Min: {min(gen_scores):.1f}%")
                print(f"  Max: {max(gen_scores):.1f}%")
            
            if eval_scores:
                print(f"\nEvaluation Scores (issues fixed - REAL):")
                print(f"  Average: {sum(eval_scores)/len(eval_scores):.1f}%")
                print(f"  Min: {min(eval_scores):.1f}%")
                print(f"  Max: {max(eval_scores):.1f}%")
                
                # Show average drop from generation to evaluation
                if gen_scores:
                    avg_gen = sum(gen_scores)/len(gen_scores)
                    avg_eval = sum(eval_scores)/len(eval_scores)
                    drop = avg_gen - avg_eval
                    print(f"\nAverage drop from generation to evaluation: {drop:.1f}%")
                    if avg_gen == 0:
                        print("No patches generated; success rate unavailable.")
                    else:
                        print(f"Success rate: {avg_eval/avg_gen*100:.1f}% of generated patches actually work")
        
        # Time statistics
        all_gen_times = [s.get("generation_time", 0) or 0 for s in scores 
                        if s.get("generation_time") is not None]
        all_eval_times = [s.get("evaluation_time", 0) or 0 for s in evaluated 
                         if s.get("evaluation_time") is not None]
        
        if all_gen_times:
            all_gen_times = [float(t) for t in all_gen_times]
            print(f"\nGeneration times:")
            print(f"  Average: {sum(all_gen_times)/len(all_gen_times):.1f}s")
            print(f"  Total: {sum(all_gen_times):.1f}s")
        
        if all_eval_times:
            all_eval_times = [float(t) for t in all_eval_times]
            print(f"\nEvaluation times:")
            print(f"  Average: {sum(all_eval_times)/len(all_eval_times):.1f}s")
            print(f"  Total: {sum(all_eval_times):.1f}s")
    
    def show_trends(self, scores: List[Dict]):
        """Show score trends over time"""
        evaluated = [s for s in scores if s.get("evaluation_status") == "completed"]
        
        if len(evaluated) < 2:
            return
        
        print("\n" + "="*60)
        print("TRENDS (Evaluated Runs Only)")
        print("="*60)
        
        # Sort by timestamp
        evaluated.sort(key=lambda x: x.get("timestamp", ""))
        
        # Show last 10 runs
        recent = evaluated[-10:] if len(evaluated) >= 10 else evaluated
        
        print("\nRecent evaluation scores:")
        for entry in recent:
            timestamp = str(entry.get("timestamp", "Unknown"))[:10]
            eval_score = entry.get("evaluation_score") or 0.0
            instances = entry.get("num_instances") or 0
            try:
                eval_score = float(eval_score)
                instances = int(instances)
                print(f"  {timestamp}: {eval_score:5.1f}% on {instances} instances")
            except (ValueError, TypeError):
                print(f"  {timestamp}: N/A on {instances} instances")
        
        # Calculate trend
        if len(evaluated) >= 3:
            first_half = evaluated[:len(evaluated)//2]
            second_half = evaluated[len(evaluated)//2:]
            
            first_scores = [float(e.get("evaluation_score", 0) or 0) for e in first_half]
            second_scores = [float(e.get("evaluation_score", 0) or 0) for e in second_half]
            
            if first_scores and second_scores:
                first_avg = sum(first_scores) / len(first_scores)
                second_avg = sum(second_scores) / len(second_scores)
                
                trend = second_avg - first_avg
                if trend > 0:
                    print(f"\n📈 Improving trend: +{trend:.1f}% from first to second half")
                elif trend < 0:
                    print(f"\n📉 Declining trend: {trend:.1f}% from first to second half")
                else:
                    print(f"\n➡️  Stable performance")
    
    def export_to_csv(self, scores: List[Dict], filename: str):
        """Export scores to CSV file"""
        if not scores:
            print("No scores to export.")
            return
        
        with open(filename, 'w', newline='') as csvfile:
            fieldnames = [
                'timestamp', 'dataset', 'num_instances', 
                'generation_score', 'evaluation_score', 
                'evaluation_status', 'generation_time', 
                'evaluation_time', 'notes'
            ]
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for entry in scores:
                row = {k: entry.get(k, '') for k in fieldnames}
                writer.writerow(row)
        
        print(f"\n✅ Exported {len(scores)} entries to {filename}")
    
    def show_pending_evaluations(self, scores: List[Dict]):
        """Show which predictions still need evaluation"""
        pending = []
        
        for entry in scores:
            if entry.get("evaluation_status") != "completed":
                pred_file = entry.get("prediction_file", "Unknown")
                timestamp = entry.get("timestamp", "Unknown")
                instances = entry.get("num_instances", 0)
                pending.append((timestamp, pred_file, instances))
        
        if not pending:
            print("\n✅ All runs have been evaluated!")
            return
        
        print("\n" + "="*60)
        print(f"PENDING EVALUATIONS ({len(pending)} runs)")
        print("="*60)
        
        for timestamp, pred_file, instances in pending:
            filename = Path(pred_file).name if pred_file != "Unknown" else "Unknown"
            print(f"  {str(timestamp)[:19]}: {filename} ({instances} instances)")
        
        print(f"\nTo evaluate these, run:")
        print(f"  python swe_bench.py eval --interactive")
        print(f"  (then select 'pending')")
    
    def analyze_k_value_breakdown(self, scores: List[Dict], timestamp: str = None, pred_file: str = None):
        """Analyze success rate by k-value (num_files) for a specific benchmark run"""
        from collections import defaultdict
        import glob
        
        # Find the target run
        target_entry = None
        if timestamp:
            for entry in scores:
                if str(entry.get("timestamp", ""))[:19] == timestamp[:19]:
                    target_entry = entry
                    break
        elif pred_file:
            for entry in scores:
                if entry.get("prediction_file") == pred_file or Path(entry.get("prediction_file", "")).name == Path(pred_file).name:
                    target_entry = entry
                    break
        else:
            # Use the most recent evaluated run
            evaluated = [s for s in scores if s.get("evaluation_status") == "completed"]
            if evaluated:
                evaluated.sort(key=lambda x: x.get("timestamp", ""))
                target_entry = evaluated[-1]
        
        if not target_entry:
            print("\n❌ No matching benchmark run found.")
            if timestamp:
                print(f"   Searched for timestamp: {timestamp}")
            elif pred_file:
                print(f"   Searched for prediction file: {pred_file}")
            else:
                print("   No evaluated runs found.")
            return
        
        pred_file_path = target_entry.get("prediction_file")
        if not pred_file_path or pred_file_path == "None":
            print(f"\n❌ No prediction file found for this run.")
            print(f"   Timestamp: {target_entry.get('timestamp')}")
            return
        
        # Resolve prediction file path
        if not Path(pred_file_path).is_absolute():
            pred_file_path = self.predictions_dir / Path(pred_file_path).name
        else:
            pred_file_path = Path(pred_file_path)
        
        if not pred_file_path.exists():
            print(f"\n❌ Prediction file not found: {pred_file_path}")
            return
        
        # Load predictions
        predictions = []
        try:
            with open(pred_file_path, 'r') as f:
                for line in f:
                    try:
                        pred = json.loads(line.strip())
                        predictions.append(pred)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"\n❌ Error loading predictions: {e}")
            return
        
        if not predictions:
            print(f"\n❌ No predictions found in file: {pred_file_path}")
            return
        
        # Group by k-value (num_files)
        k_value_stats = defaultdict(lambda: {"total": 0, "generated": 0, "evaluated": 0, "passed": 0})
        
        for pred in predictions:
            k_value = pred.get("num_files", 0)
            k_value_stats[k_value]["total"] += 1
            if pred.get("patch"):
                k_value_stats[k_value]["generated"] += 1
        
        # Try to load evaluation results
        model_name = target_entry.get("model") or "unknown"
        backend = target_entry.get("backend") or "unknown"
        
        # Look for evaluation result files
        eval_files = list(self.eval_results_dir.glob(f"*{model_name}*.json")) if self.eval_results_dir.exists() else []
        if not eval_files:
            eval_files = list(self.eval_results_dir.glob(f"*.json")) if self.eval_results_dir.exists() else []
        
        eval_data_by_k = {}
        for eval_file in eval_files:
            try:
                with open(eval_file, 'r') as f:
                    eval_data = json.load(f)
                    # Try to extract k-value from filename or data
                    filename = eval_file.name
                    # Look for pattern like _k19.json or k=19
                    import re
                    k_match = re.search(r'[kK][_=]?(\d+)', filename)
                    if k_match:
                        k_val = int(k_match.group(1))
                        eval_data_by_k[k_val] = eval_data
            except Exception:
                continue
        
        # Update evaluation stats
        for k_value, eval_data in eval_data_by_k.items():
            if k_value in k_value_stats:
                results = eval_data.get("results", {})
                k_value_stats[k_value]["evaluated"] = len(results)
                k_value_stats[k_value]["passed"] = sum(1 for r in results.values() if r.get("status") == "RESOLVED")
        
        # Display results
        print("\n" + "="*80)
        print("K-VALUE (num_files) BREAKDOWN ANALYSIS")
        print("="*80)
        print(f"Run timestamp: {target_entry.get('timestamp')}")
        print(f"Prediction file: {Path(pred_file_path).name}")
        print(f"Total predictions: {len(predictions)}")
        print()
        print(f"{'K-Value':<10} {'Total':>8} {'Generated':>10} {'Gen Rate':>10} {'Evaluated':>10} {'Passed':>8} {'Eval Rate':>10}")
        print("-"*80)
        
        sorted_k_values = sorted(k_value_stats.keys())
        for k_value in sorted_k_values:
            stats = k_value_stats[k_value]
            total = stats["total"]
            generated = stats["generated"]
            evaluated = stats["evaluated"]
            passed = stats["passed"]
            
            gen_rate = (generated / total * 100) if total > 0 else 0.0
            eval_rate = (passed / evaluated * 100) if evaluated > 0 else 0.0
            
            eval_str = f"{evaluated:>10}" if evaluated > 0 else "      N/A"
            passed_str = f"{passed:>8}" if evaluated > 0 else "     N/A"
            eval_rate_str = f"{eval_rate:>9.1f}%" if evaluated > 0 else "      N/A"
            
            print(f"{k_value:<10} {total:>8} {generated:>10} {gen_rate:>9.1f}% {eval_str} {passed_str} {eval_rate_str}")
        
        print("-"*80)
        
        # Summary
        total_all = sum(s["total"] for s in k_value_stats.values())
        generated_all = sum(s["generated"] for s in k_value_stats.values())
        evaluated_all = sum(s["evaluated"] for s in k_value_stats.values())
        passed_all = sum(s["passed"] for s in k_value_stats.values())
        
        if total_all > 0:
            overall_gen_rate = generated_all / total_all * 100
            print(f"{'Overall':<10} {total_all:>8} {generated_all:>10} {overall_gen_rate:>9.1f}%", end="")
            if evaluated_all > 0:
                overall_eval_rate = passed_all / evaluated_all * 100
                print(f" {evaluated_all:>10} {passed_all:>8} {overall_eval_rate:>9.1f}%")
            else:
                print(f" {'N/A':>10} {'N/A':>8} {'N/A':>10}")
        
        if not eval_data_by_k:
            print(f"\n⚠️  Note: No evaluation results found in {self.eval_results_dir}")
            print("   Evaluation rates are not available.")

def main():
    parser = argparse.ArgumentParser(
        description="View and analyze SWE-bench benchmark scores"
    )
    
    parser.add_argument("--filter", choices=["all", "evaluated", "pending"],
                       default="all", help="Filter scores to display")
    parser.add_argument("--export", type=str, metavar="FILE.csv",
                       help="Export scores to CSV file")
    parser.add_argument("--stats", action="store_true",
                       help="Show detailed statistics")
    parser.add_argument("--trends", action="store_true",
                       help="Show score trends over time")
    parser.add_argument("--pending", action="store_true",
                       help="Show pending evaluations")
    parser.add_argument("--last", type=int, metavar="N",
                       help="Show only last N entries")
    parser.add_argument("--k-breakdown", action="store_true",
                       help="Analyze success rate by k-value (num_files)")
    parser.add_argument("--timestamp", type=str, metavar="TIMESTAMP",
                       help="Timestamp for k-value breakdown (format: YYYY-MM-DD HH:MM:SS)")
    parser.add_argument("--pred-file", type=str, metavar="FILE",
                       help="Prediction file for k-value breakdown")
    
    args = parser.parse_args()
    
    viewer = ScoreViewer()
    scores = viewer.load_scores()
    
    if not scores:
        print("No benchmark scores found.")
        print("Run benchmarks first with:")
        print("  python run_benchmark_with_eval.py --limit 5")
        return
    
    # Apply last N filter if specified
    if args.last:
        scores = scores[-args.last:]
    
    # Main display
    print("\n" + "="*60)
    print("SWE-BENCH BENCHMARK SCORES")
    print("="*60)
    
    viewer.display_scores(scores, args.filter)
    
    # Additional displays based on flags
    if args.stats:
        viewer.show_statistics(scores)
    
    if args.trends:
        viewer.show_trends(scores)
    
    if args.pending:
        viewer.show_pending_evaluations(scores)
    
    # Export if requested
    if args.export:
        viewer.export_to_csv(scores, args.export)
    
    # K-value breakdown if requested
    if args.k_breakdown:
        viewer.analyze_k_value_breakdown(scores, timestamp=args.timestamp, pred_file=args.pred_file)
        return
    
    # Quick summary
    evaluated = len([s for s in scores if s.get("evaluation_status") == "completed"])
    pending = len([s for s in scores if s.get("evaluation_status") != "completed"])
    
    print(f"\nSummary: {len(scores)} total runs, {evaluated} evaluated, {pending} pending")
    
    if pending > 0:
        print(f"\n💡 Tip: You have {pending} runs pending evaluation.")
        print(f"   Run: python swe_bench.py eval --interactive")

if __name__ == "__main__":
    main()

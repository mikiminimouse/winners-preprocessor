import json
import os
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime

def analyze_advanced(base_dir: str):
    base_path = Path(base_dir)
    input_dir = base_path / "Input"
    ready_dir = base_path / "Ready2Docling"
    exceptions_dir = base_path / "Exceptions"
    processing_dir = base_path / "Processing"
    merge_dir = base_path / "Merge"
    
    stats = {
        "total_input": 0,
        "ready_total": 0,
        "exceptions_total": 0,
        "routes": Counter(),
        "formats": Counter(),
        "exception_categories": Counter(),
        "ops_by_cycle": defaultdict(lambda: defaultdict(Counter)), # cycle -> op_type -> status -> count
        "units_by_cycle": Counter(),   # cycle_num -> count of units finished in this cycle
        "routes_by_cycle": defaultdict(Counter), # cycle -> route -> count
        "exception_by_cycle": defaultdict(Counter), # cycle -> category -> count
        "leftovers": {
            "processing": 0,
            "merge": 0
        }
    }
    
    # 1. Input Analysis
    if input_dir.exists():
        stats["total_input"] = len(list(input_dir.glob("UNIT_*")))
    
    # 2. Ready2Docling Analysis
    if ready_dir.exists():
        for unit_dir in ready_dir.rglob("UNIT_*"):
            if unit_dir.is_dir():
                stats["ready_total"] += 1
                manifest_path = unit_dir / "manifest.json"
                if manifest_path.exists():
                    try:
                        with open(manifest_path) as f:
                            m = json.load(f)
                            proc = m.get("processing", {})
                            route = proc.get("route", "unknown")
                            cycle = proc.get("current_cycle", 1)
                            
                            stats["routes"][route] += 1
                            stats["routes_by_cycle"][cycle][route] += 1
                            stats["units_by_cycle"][cycle] += 1
                            
                            # Operations
                            ops = proc.get("operations", [])
                            # Also check applied_operations at root level
                            root_ops = m.get("applied_operations", [])
                            all_ops = ops + root_ops
                            
                            seen_ops = set() # Avoid double counting if identical
                            for op in all_ops:
                                op_type = op.get("type", "unknown")
                                status = op.get("status", "success")
                                op_cycle = op.get("cycle", cycle)
                                timestamp = op.get("timestamp", "")
                                
                                op_key = (op_type, status, op_cycle, timestamp)
                                if op_key not in seen_ops:
                                    stats["ops_by_cycle"][op_cycle][op_type][status] += 1
                                    seen_ops.add(op_key)
                            
                            # Formats
                            files = m.get("files", [])
                            if files:
                                main_file = files[0]
                                ext = Path(main_file.get("current_name", "")).suffix.lower().lstrip(".")
                                if not ext: ext = "no_ext"
                                stats["formats"][ext] += 1
                    except:
                        pass

    # 3. Exceptions Analysis
    if exceptions_dir.exists():
        for unit_dir in exceptions_dir.rglob("UNIT_*"):
            if unit_dir.is_dir():
                stats["exceptions_total"] += 1
                rel_path = unit_dir.relative_to(exceptions_dir)
                parts = rel_path.parts
                
                # Category logic: Exceptions/Exceptions_N/Category/UNIT or MixedTypes/Cycle_N/UNIT
                category = "Unknown"
                cycle = 1
                
                if len(parts) >= 2:
                    if parts[0].startswith("Exceptions_"):
                        cycle = int(parts[0].split("_")[1])
                        category = parts[1]
                    elif parts[0] == "MixedTypes" and len(parts) >= 3:
                        cycle = int(parts[1].split("_")[1]) if "Cycle_" in parts[1] else 1
                        category = "MixedTypes"
                    else:
                        category = parts[0]
                
                stats["exception_categories"][category] += 1
                stats["exception_by_cycle"][cycle][category] += 1
                
                # Check manifest
                manifest_path = unit_dir / "manifest.json"
                if manifest_path.exists():
                    try:
                        with open(manifest_path) as f:
                            m = json.load(f)
                            proc = m.get("processing", {})
                            ops = proc.get("operations", [])
                            root_ops = m.get("applied_operations", [])
                            all_ops = ops + root_ops
                            
                            seen_ops = set()
                            for op in all_ops:
                                op_type = op.get("type", "unknown")
                                status = op.get("status", "error" if op_type != "classify" else "success")
                                op_cycle = op.get("cycle", cycle)
                                timestamp = op.get("timestamp", "")
                                
                                op_key = (op_type, status, op_cycle, timestamp)
                                if op_key not in seen_ops:
                                    stats["ops_by_cycle"][op_cycle][op_type][status] += 1
                                    seen_ops.add(op_key)
                    except:
                        pass

    # 4. Leftovers
    if processing_dir.exists():
        stats["leftovers"]["processing"] = len(list(processing_dir.rglob("UNIT_*")))
    if merge_dir.exists():
        stats["leftovers"]["merge"] = len(list(merge_dir.rglob("UNIT_*")))

    # Output Generation
    report = []
    report.append(f"# 📊 Deep Lifecycle Analytics: {base_dir}")
    report.append(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    report.append("## 1. Overall Volume")
    total_out = stats["ready_total"] + stats["exceptions_total"]
    efficiency = (stats["ready_total"] / stats["total_input"] * 100) if stats["total_input"] > 0 else 0
    report.append(f"- **Total Input**: {stats['total_input']}")
    report.append(f"- **Total Output**: {total_out} ({(total_out/stats['total_input']*100):.1f}% accountability)")
    report.append(f"- **Success Rate**: {stats['ready_total']} ({efficiency:.1f}%)")
    report.append(f"- **Quarantine Rate**: {stats['exceptions_total']} ({(stats['exceptions_total'] / stats['total_input'] * 100):.1f}%)\n")

    report.append("## 2. Lifecycle by Cycle")
    for cycle in sorted(set(list(stats["units_by_cycle"].keys()) + list(stats["exception_by_cycle"].keys()))):
        report.append(f"### Cycle {cycle}")
        
        # Success in this cycle
        ready_in_cycle = stats["units_by_cycle"][cycle]
        report.append(f"**Successfully finished**: {ready_in_cycle}")
        if ready_in_cycle > 0:
            report.append("| Route | Count | Share |")
            report.append("| :--- | :--- | :--- |")
            for r, c in stats["routes_by_cycle"][cycle].items():
                report.append(f"| {r} | {c} | {(c/ready_in_cycle*100):.1f}% |")
            report.append("")

        # Exceptions in this cycle
        exc_in_cycle = sum(stats["exception_by_cycle"][cycle].values())
        report.append(f"**Failed/Quarantined in this cycle**: {exc_in_cycle}")
        if exc_in_cycle > 0:
            report.append("| Category | Count | Share |")
            report.append("| :--- | :--- | :--- |")
            for cat, c in stats["exception_by_cycle"][cycle].items():
                report.append(f"| {cat} | {c} | {(c/exc_in_cycle*100):.1f}% |")
            report.append("")

        # Operations in this cycle
        ops_in_cycle = stats["ops_by_cycle"][cycle]
        if ops_in_cycle:
            report.append("**Operations in this cycle**:")
            report.append("| Operation | Total | Success | Failed | Skipped | Success % |")
            report.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
            for op, sc in ops_in_cycle.items():
                s = sc.get("success", 0) + sc.get("completed", 0)
                f = sc.get("failed", 0) + sc.get("error", 0)
                sk = sc.get("skipped", 0)
                tot = s + f + sk
                rate = (s / (s + f) * 100) if (s + f) > 0 else 0
                report.append(f"| {op} | {tot} | {s} | {f} | {sk} | {rate:.1f}% |")
            report.append("\n")

    report.append("## 3. Format Distribution (Final Ready)")
    report.append("| Format | Count | Share |")
    report.append("| :--- | :--- | :--- |")
    for f, c in sorted(stats["formats"].items(), key=lambda x: x[1], reverse=True):
        report.append(f"| {f} | {c} | {(c/stats['ready_total']*100):.1f}% |")
    report.append("\n")

    report.append("## 4. Health Check")
    is_cln = stats["leftovers"]["processing"] == 0 and stats["leftovers"]["merge"] == 0
    report.append(f"- **Intermediate Cleanliness**: {'✅ PASS' if is_cln else '❌ FAIL'}")
    report.append(f"  - Processing Leftovers: {stats['leftovers']['processing']}")
    report.append(f"  - Merge Leftovers: {stats['leftovers']['merge']}")
    report.append(f"- **Data Integrity**: {'✅ PASS' if stats['total_input'] == total_out else '❌ FAIL'}")
    
    print("\n".join(report))

if __name__ == "__main__":
    import sys
    base = sys.argv[1] if len(sys.argv) > 1 else "Data/2025-11-29"
    analyze_advanced(base)

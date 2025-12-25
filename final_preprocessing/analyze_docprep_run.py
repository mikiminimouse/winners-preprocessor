import json
import os
from pathlib import Path
from collections import defaultdict, Counter

def analyze_run(base_dir: str):
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
        "processed_formats": Counter(),
        "exception_categories": Counter(),
        "routes": Counter(),
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
                # Format is usually parent dir name (e.g. pdf, docx)
                # Structure: Ready2Docling/format/type/UNIT_ID or Ready2Docling/format/UNIT_ID
                # Let's verify manifest
                manifest_path = unit_dir / "manifest.json"
                if manifest_path.exists():
                    try:
                        with open(manifest_path) as f:
                            m = json.load(f)
                            route = m.get("processing", {}).get("route", "unknown")
                            stats["routes"][route] += 1
                            
                            # Check files
                            files = m.get("files", [])
                            exts = [Path(f["current_name"]).suffix for f in files]
                            # Use route as format proxy
                            stats["processed_formats"][route] += 1
                    except:
                        pass
                else:
                    # Fallback to dir name
                    stats["processed_formats"][unit_dir.parent.name] += 1

    # 3. Exceptions Analysis
    if exceptions_dir.exists():
        for unit_dir in exceptions_dir.rglob("UNIT_*"):
            if unit_dir.is_dir():
                stats["exceptions_total"] += 1
                # Category is parent dir (Mixed, Special, etc)
                # Категория - это папка внутри Exceptions (или подпапка, если есть Cycle_N)
                rel_path = unit_dir.relative_to(exceptions_dir)
                parts = rel_path.parts
                if len(parts) >= 2:
                    # Если папка - Cycle_N, берем родительскую как категорию
                    if parts[-2].startswith("Cycle_") or parts[-2].startswith("Exceptions_"):
                        category = parts[0]
                    else:
                        category = parts[-2]
                else:
                    category = "Unknown"
                
                stats["exception_categories"][category] += 1

    # 4. Leftovers
    if processing_dir.exists():
        stats["leftovers"]["processing"] = len(list(processing_dir.rglob("UNIT_*")))
    
    if merge_dir.exists():
        stats["leftovers"]["merge"] = len(list(merge_dir.rglob("UNIT_*")))

    print("="*40)
    print(f"ANALYSIS REPORT: {base_dir}")
    print("="*40)
    print(f"Total Input Units: {stats['total_input']}")
    print(f"Total Successfully Processed: {stats['ready_total']}")
    print(f"Total Exceptions: {stats['exceptions_total']}")
    print("-" * 20)
    print("Processed by Route/Format:")
    for k, v in stats["processed_formats"].items():
        print(f"  {k}: {v}")
    print("-" * 20)
    print("Exceptions by Category:")
    for k, v in stats["exception_categories"].items():
        print(f"  {k}: {v}")
    print("-" * 20)
    print("Leftovers (Should be 0):")
    print(f"  Processing: {stats['leftovers']['processing']}")
    print(f"  Merge: {stats['leftovers']['merge']}")
    print("="*40)
    
    total_out = stats["ready_total"] + stats["exceptions_total"]
    diff = stats["total_input"] - total_out
    print(f"Input vs Output Delta: {diff} (Positive means lost units, Negative means duplicates/extras)")
    
    if stats["leftovers"]["processing"] > 0 or stats["leftovers"]["merge"] > 0:
        print("\n❌ FAIL: Leftovers found in intermediate directories!")
    else:
        print("\n✅ PASS: No leftovers.")

if __name__ == "__main__":
    import sys
    base = sys.argv[1] if len(sys.argv) > 1 else "Data/2025-03-18"
    analyze_run(base)

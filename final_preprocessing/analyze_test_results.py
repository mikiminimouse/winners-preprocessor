#!/usr/bin/env python3
"""
Анализ результатов тестирования и сбор статистики.
"""
import sys
from pathlib import Path
from collections import defaultdict, Counter

sys.path.insert(0, str(Path(__file__).parent))

from docprep.utils.paths import get_unit_files
from docprep.core.manifest import load_manifest

def analyze_complete_results(date: str):
    """Анализирует полные результаты обработки."""
    base_dir = Path("Data") / date
    
    print("=" * 80)
    print("ПОЛНЫЙ АНАЛИЗ РЕЗУЛЬТАТОВ")
    print("=" * 80)
    print(f"Дата: {date}")
    print()
    
    stats = {
        "input": 0,
        "iterations": defaultdict(lambda: {
            "processing": defaultdict(int),
            "merge": defaultdict(lambda: defaultdict(int)),
            "exceptions": defaultdict(int),
        }),
        "ready2docling": defaultdict(int),
        "by_extension": Counter(),
        "by_category": Counter(),
    }
    
    # Input
    input_dir = base_dir / "Input"
    if input_dir.exists():
        stats["input"] = len([d for d in input_dir.iterdir() if d.is_dir() and d.name.startswith("UNIT_")])
    
    # Итерации
    for iteration in range(1, 4):
        # Processing
        processing_dir = base_dir / "Processing" / f"Processing_{iteration}"
        if processing_dir.exists():
            for category in ["Convert", "Extract", "Normalize"]:
                category_dir = processing_dir / category
                if category_dir.exists():
                    count = len(list(category_dir.rglob("UNIT_*")))
                    if count > 0:
                        stats["iterations"][iteration]["processing"][category] = count
        
        # Merge
        for merge_num in range(4):
            merge_dir = base_dir / "Merge" / f"Merge_{merge_num}"
            if merge_dir.exists():
                for subdir in ["Direct", "Converted", "Extracted", "Normalized"]:
                    subdir_path = merge_dir / subdir
                    if subdir_path.exists():
                        count = len(list(subdir_path.rglob("UNIT_*")))
                        if count > 0:
                            stats["iterations"][iteration]["merge"][merge_num][subdir] = count
        
        # Exceptions
        exceptions_dir = base_dir / "Exceptions" / f"Exceptions_{iteration}"
        if exceptions_dir.exists():
            count = len(list(exceptions_dir.rglob("UNIT_*")))
            if count > 0:
                stats["iterations"][iteration]["exceptions"][iteration] = count
    
    # Ready2Docling
    ready_dir = base_dir / "Ready2Docling"
    if ready_dir.exists():
        for ext_dir in ready_dir.iterdir():
            if ext_dir.is_dir():
                count = len(list(ext_dir.rglob("UNIT_*")))
                if count > 0:
                    stats["ready2docling"][ext_dir.name] = count
                    
                    # Собираем расширения
                    for unit_dir in ext_dir.rglob("UNIT_*"):
                        if unit_dir.is_dir():
                            files = get_unit_files(unit_dir)
                            for file_path in files:
                                ext = file_path.suffix.lower().lstrip(".")
                                if ext:
                                    stats["by_extension"][ext] += 1
                            
                            # Категория из manifest
                            manifest_path = unit_dir / "manifest.json"
                            if manifest_path.exists():
                                try:
                                    manifest = load_manifest(unit_dir)
                                    operations = manifest.get("applied_operations", [])
                                    if operations:
                                        category = operations[-1].get("category", "unknown")
                                        stats["by_category"][category] += 1
                                except:
                                    pass
    
    # Выводим статистику
    print("СТАТИСТИКА:")
    print("-" * 80)
    print(f"Input: {stats['input']} UNIT")
    print()
    
    for iteration in sorted(stats["iterations"].keys()):
        print(f"Итерация {iteration}:")
        iter_stats = stats["iterations"][iteration]
        
        if iter_stats["processing"]:
            print(f"  Processing_{iteration}:")
            for category, count in iter_stats["processing"].items():
                print(f"    {category}: {count} UNIT")
        
        if iter_stats["merge"]:
            print(f"  Merge:")
            for merge_num, subdirs in iter_stats["merge"].items():
                for subdir, count in subdirs.items():
                    print(f"    Merge_{merge_num}/{subdir}: {count} UNIT")
        
        if iter_stats["exceptions"]:
            print(f"  Exceptions_{iteration}: {sum(iter_stats['exceptions'].values())} UNIT")
        print()
    
    print("Ready2Docling:")
    for ext, count in sorted(stats["ready2docling"].items(), key=lambda x: x[1], reverse=True):
        print(f"  {ext}: {count} UNIT")
    print()
    
    print("Расширения файлов в Ready2Docling:")
    for ext, count in stats["by_extension"].most_common(20):
        print(f"  .{ext}: {count} файлов")
    print()
    
    print("Категории в Ready2Docling:")
    for category, count in stats["by_category"].most_common():
        print(f"  {category}: {count} UNIT")
    
    return stats

if __name__ == "__main__":
    date = "2025-03-19"
    stats = analyze_complete_results(date)


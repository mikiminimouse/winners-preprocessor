#!/usr/bin/env python3
"""
Анализ и исправление структуры UNIT.
Проверяет правильность распределения и готовность к финальной сборке.
"""
import sys
from pathlib import Path
from collections import defaultdict

def analyze_structure(date: str):
    """Анализирует структуру и выявляет проблемы."""
    base_dir = Path("Data") / date
    
    print("=" * 80)
    print("АНАЛИЗ СТРУКТУРЫ UNIT")
    print("=" * 80)
    print(f"Дата: {date}")
    print()
    
    # Собираем статистику
    stats = {
        "input": 0,
        "processing": defaultdict(int),
        "merge": defaultdict(lambda: defaultdict(int)),
        "exceptions": defaultdict(int),
        "ready2docling": 0,
    }
    
    # Input
    input_dir = base_dir / "Input"
    if input_dir.exists():
        stats["input"] = len([d for d in input_dir.iterdir() if d.is_dir() and d.name.startswith("UNIT_")])
    
    # Processing
    processing_dir = base_dir / "Processing"
    if processing_dir.exists():
        for proc_dir in processing_dir.iterdir():
            if proc_dir.is_dir() and proc_dir.name.startswith("Processing_"):
                proc_num = proc_dir.name.split("_")[1]
                count = len(list(proc_dir.rglob("UNIT_*")))
                if count > 0:
                    stats["processing"][proc_num] = count
    
    # Merge
    merge_dir = base_dir / "Merge"
    if merge_dir.exists():
        for merge_cycle_dir in merge_dir.iterdir():
            if merge_cycle_dir.is_dir() and merge_cycle_dir.name.startswith("Merge_"):
                merge_num = merge_cycle_dir.name.split("_")[1]
                for subdir in ["Direct", "Converted", "Extracted", "Normalized"]:
                    subdir_path = merge_cycle_dir / subdir
                    if subdir_path.exists():
                        count = len(list(subdir_path.rglob("UNIT_*")))
                        if count > 0:
                            stats["merge"][merge_num][subdir] = count
    
    # Exceptions
    exceptions_dir = base_dir / "Exceptions"
    if exceptions_dir.exists():
        for exc_dir in exceptions_dir.iterdir():
            if exc_dir.is_dir() and exc_dir.name.startswith("Exceptions_"):
                exc_num = exc_dir.name.split("_")[1]
                count = len(list(exc_dir.rglob("UNIT_*")))
                if count > 0:
                    stats["exceptions"][exc_num] = count
    
    # Ready2Docling
    ready_dir = base_dir / "Ready2Docling"
    if ready_dir.exists():
        stats["ready2docling"] = len(list(ready_dir.rglob("UNIT_*")))
    
    # Выводим статистику
    print("СТАТИСТИКА:")
    print("-" * 80)
    print(f"Input: {stats['input']} UNIT")
    print()
    
    print("Processing:")
    for proc_num, count in sorted(stats["processing"].items()):
        print(f"  Processing_{proc_num}: {count} UNIT")
    print()
    
    print("Merge:")
    for merge_num in sorted(stats["merge"].keys()):
        print(f"  Merge_{merge_num}:")
        for subdir in ["Direct", "Converted", "Extracted", "Normalized"]:
            count = stats["merge"][merge_num].get(subdir, 0)
            if count > 0:
                print(f"    {subdir}: {count} UNIT")
    print()
    
    print("Exceptions:")
    for exc_num, count in sorted(stats["exceptions"].items()):
        print(f"  Exceptions_{exc_num}: {count} UNIT")
    print()
    
    print(f"Ready2Docling: {stats['ready2docling']} UNIT")
    print()
    
    # Проверяем проблемы
    print("ПРОВЕРКА ПРОБЛЕМ:")
    print("-" * 80)
    problems = []
    
    # 1. Проверяем Merge_1, Merge_2, Merge_3 - не должно быть Direct
    for merge_num in ["1", "2", "3"]:
        if stats["merge"][merge_num].get("Direct", 0) > 0:
            problems.append(f"Merge_{merge_num} содержит Direct UNIT (должно быть только в Merge_0)")
    
    # 2. Проверяем, что Merge_1 содержит обработанные UNIT
    if stats["merge"]["1"].get("Converted", 0) == 0 and stats["merge"]["1"].get("Extracted", 0) == 0 and stats["merge"]["1"].get("Normalized", 0) == 0:
        if stats["processing"]["1"] == 0:
            problems.append("Merge_1 пуст, но Processing_1 тоже пуст - UNIT могли быть перемещены")
    
    # 3. Проверяем Processing_2 - должны быть обработаны
    if stats["processing"]["2"] > 0:
        problems.append(f"Processing_2 содержит {stats['processing']['2']} UNIT - требуют обработки")
    
    if problems:
        for problem in problems:
            print(f"  ⚠️ {problem}")
    else:
        print("  ✅ Проблем не обнаружено")
    
    print()
    print("=" * 80)
    
    return stats, problems

if __name__ == "__main__":
    date = "2025-12-20"
    stats, problems = analyze_structure(date)
    
    if problems:
        print(f"\nНайдено проблем: {len(problems)}")
    else:
        print("\n✅ Структура корректна")


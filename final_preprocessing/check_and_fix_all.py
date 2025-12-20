#!/usr/bin/env python3
"""
Проверка и исправление всей структуры.
Проверяет правильность распределения UNIT и готовность к финальной сборке.
"""
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

def check_complete_structure(date: str):
    """Проверяет полную структуру и выявляет проблемы."""
    base_dir = Path("Data") / date
    
    print("=" * 80)
    print("ПОЛНАЯ ПРОВЕРКА СТРУКТУРЫ")
    print("=" * 80)
    print(f"Дата: {date}")
    print()
    
    issues = []
    
    # 1. Проверяем Merge_0 - должна быть только Direct
    print("1. ПРОВЕРКА MERGE_0:")
    print("-" * 80)
    merge_0 = base_dir / "Merge" / "Merge_0"
    if merge_0.exists():
        direct_count = len(list((merge_0 / "Direct").rglob("UNIT_*"))) if (merge_0 / "Direct").exists() else 0
        print(f"  Direct: {direct_count} UNIT")
        
        # Проверяем, нет ли других поддиректорий
        for subdir in merge_0.iterdir():
            if subdir.is_dir() and subdir.name != "Direct":
                issues.append(f"Merge_0 содержит {subdir.name} (должна быть только Direct)")
    print()
    
    # 2. Проверяем Merge_1, Merge_2, Merge_3 - не должно быть Direct
    print("2. ПРОВЕРКА MERGE_1, MERGE_2, MERGE_3:")
    print("-" * 80)
    for merge_num in [1, 2, 3]:
        merge_dir = base_dir / "Merge" / f"Merge_{merge_num}"
        if merge_dir.exists():
            print(f"  Merge_{merge_num}:")
            for subdir in ["Direct", "Converted", "Extracted", "Normalized"]:
                subdir_path = merge_dir / subdir
                if subdir_path.exists():
                    count = len(list(subdir_path.rglob("UNIT_*")))
                    if count > 0:
                        print(f"    {subdir}: {count} UNIT")
                    if subdir == "Direct" and count > 0:
                        issues.append(f"Merge_{merge_num} содержит Direct UNIT (не должно быть)")
    print()
    
    # 3. Проверяем Processing - должны быть только в Processing_N
    print("3. ПРОВЕРКА PROCESSING:")
    print("-" * 80)
    processing_dir = base_dir / "Processing"
    if processing_dir.exists():
        for proc_dir in processing_dir.iterdir():
            if proc_dir.is_dir() and proc_dir.name.startswith("Processing_"):
                proc_num = proc_dir.name.split("_")[1]
                count = len(list(proc_dir.rglob("UNIT_*")))
                if count > 0:
                    print(f"  {proc_dir.name}: {count} UNIT")
                    if proc_num == "1" and count > 0:
                        issues.append(f"Processing_1 содержит {count} UNIT (должны быть обработаны)")
    print()
    
    # 4. Проверяем Ready2Docling
    print("4. ПРОВЕРКА READY2DOCLING:")
    print("-" * 80)
    ready_dir = base_dir / "Ready2Docling"
    if ready_dir.exists():
        total = len(list(ready_dir.rglob("UNIT_*")))
        print(f"  Всего UNIT: {total}")
        
        # По типам
        type_counts = {}
        for ext_dir in ready_dir.iterdir():
            if ext_dir.is_dir():
                count = len(list(ext_dir.rglob("UNIT_*")))
                if count > 0:
                    type_counts[ext_dir.name] = count
        
        for file_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"    {file_type}: {count} UNIT")
    print()
    
    # 5. Выводим проблемы
    print("5. ВЫЯВЛЕННЫЕ ПРОБЛЕМЫ:")
    print("-" * 80)
    if issues:
        for issue in issues:
            print(f"  ⚠️ {issue}")
    else:
        print("  ✅ Проблем не обнаружено")
    print()
    
    print("=" * 80)
    
    return issues

if __name__ == "__main__":
    date = "2025-12-20"
    issues = check_complete_structure(date)
    
    if issues:
        print(f"\nНайдено проблем: {len(issues)}")
    else:
        print("\n✅ Структура корректна, готова к финальной сборке")


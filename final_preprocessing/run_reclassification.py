#!/usr/bin/env python3
"""
Скрипт для повторной классификации UNIT из Merge_1.
"""
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from docprep.engine.classifier import Classifier

def reclassify_merge_1(date: str):
    """Классифицирует UNIT из Merge_1 (Цикл 2)."""
    print("=" * 80)
    print("ПОВТОРНАЯ КЛАССИФИКАЦИЯ UNIT ИЗ MERGE_1 (ЦИКЛ 2)")
    print("=" * 80)
    print(f"Дата: {date}")
    print()
    
    base_dir = Path(f"Data/{date}")
    merge_1_dir = base_dir / "Merge" / "Merge_1"
    
    if not merge_1_dir.exists():
        print(f"❌ Merge_1 не существует: {merge_1_dir}")
        return
    
    classifier = Classifier()
    classify_processed = 0
    classify_errors = []
    
    # Собираем все UNIT из Merge_1
    merge_dirs = []
    for subdir in ["Converted", "Extracted", "Normalized"]:
        subdir_path = merge_1_dir / subdir
        if subdir_path.exists():
            merge_dirs.append(subdir_path)
    
    all_merge_units = []
    for merge_subdir in merge_dirs:
        for ext_dir in merge_subdir.iterdir():
            if not ext_dir.is_dir():
                continue
            for unit_dir in ext_dir.iterdir():
                if unit_dir.is_dir() and unit_dir.name.startswith("UNIT_"):
                    all_merge_units.append(unit_dir)
    
    print(f"Найдено UNIT для классификации: {len(all_merge_units)}")
    print()
    
    if not all_merge_units:
        print("⚠️ UNIT не найдены в Merge_1")
        return
    
    # Классифицируем каждый UNIT
    for i, unit_dir in enumerate(all_merge_units, 1):
        try:
            result = classifier.classify_unit(
                unit_path=unit_dir,
                cycle=2,
                protocol_date=date,
                dry_run=False,
                copy_mode=False,  # Перемещаем, так как это финальная обработка
            )
            classify_processed += 1
            if i % 50 == 0:
                print(f"  Классифицировано: {i}/{len(all_merge_units)}")
        except Exception as e:
            classify_errors.append({"unit": unit_dir.name, "error": str(e)})
            if len(classify_errors) <= 10:
                print(f"  ❌ {unit_dir.name}: {e}")
    
    print()
    print(f"✅ Классифицировано: {classify_processed}/{len(all_merge_units)}")
    if classify_errors:
        print(f"❌ Ошибок: {len(classify_errors)}")
    
    # Статистика после классификации
    print()
    print("РАСПРЕДЕЛЕНИЕ ПОСЛЕ КЛАССИФИКАЦИИ:")
    print("-" * 80)
    
    processing_2 = base_dir / "Processing" / "Processing_2"
    merge_2 = base_dir / "Merge" / "Merge_2"
    exceptions_2 = base_dir / "Exceptions" / "Exceptions_2"
    
    stats = {
        "processing_2": len(list(processing_2.rglob("UNIT_*"))) if processing_2.exists() else 0,
        "merge_2": len(list(merge_2.rglob("UNIT_*"))) if merge_2.exists() else 0,
        "exceptions_2": len(list(exceptions_2.rglob("UNIT_*"))) if exceptions_2.exists() else 0,
    }
    
    print(f"  Processing_2: {stats['processing_2']} UNIT")
    print(f"  Merge_2: {stats['merge_2']} UNIT")
    print(f"  Exceptions_2: {stats['exceptions_2']} UNIT")
    
    print()
    print("=" * 80)
    print("✅ КЛАССИФИКАЦИЯ ЗАВЕРШЕНА")
    print("=" * 80)
    
    return {
        "processed": classify_processed,
        "errors": classify_errors,
        "stats": stats,
    }

if __name__ == "__main__":
    date = "2025-12-20"
    results = reclassify_merge_1(date)
    if results:
        print(f"\nИтого: {results['processed']} UNIT классифицировано")


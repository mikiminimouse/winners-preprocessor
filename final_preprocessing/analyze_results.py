#!/usr/bin/env python3
"""
Детальный анализ результатов классификации.
"""
import sys
from pathlib import Path
from collections import Counter

# Добавляем путь к модулю
sys.path.insert(0, str(Path(__file__).parent))

def analyze_results():
    """Детальный анализ результатов классификации."""
    date = "2025-03-18"
    base_dir = Path(f"Data/{date}")
    
    print("=" * 60)
    print("ДЕТАЛЬНЫЙ АНАЛИЗ РЕЗУЛЬТАТОВ КЛАССИФИКАЦИИ")
    print("=" * 60)
    
    # Проверяем Input
    input_dir = base_dir / "Input"
    input_units = [d for d in input_dir.iterdir() if d.is_dir() and d.name.startswith("UNIT_")]
    print(f"\n📁 Input: {len(input_units)} UNIT")
    
    # Проверяем пустые UNIT
    empty_units = []
    for unit in input_units:
        files = [f for f in unit.iterdir() if f.is_file() and f.name not in ["manifest.json", "audit.log.jsonl"]]
        if not files:
            empty_units.append(unit.name)
    
    if empty_units:
        print(f"  ⚠️  Пустые UNIT (без файлов): {len(empty_units)}")
        print(f"     Примеры: {', '.join(empty_units[:5])}")
    
    # Проверяем Merge
    merge_dir = base_dir / "Merge"
    merge_units = []
    for merge_subdir in merge_dir.rglob("UNIT_*"):
        if merge_subdir.is_dir():
            merge_units.append(merge_subdir)
    
    print(f"\n📁 Merge: {len(merge_units)} UNIT")
    
    # Разбивка по поддиректориям
    merge_by_type = Counter()
    for unit in merge_units:
        # Получаем путь относительно Merge
        rel_path = unit.relative_to(merge_dir)
        path_parts = rel_path.parts
        if len(path_parts) >= 2:
            merge_by_type[f"{path_parts[0]}/{path_parts[1]}"] += 1
    
    for merge_type, count in merge_by_type.most_common():
        print(f"  {merge_type}: {count} UNIT")
    
    # Проверяем Processing
    processing_dir = base_dir / "Processing"
    processing_units = []
    for proc_subdir in processing_dir.rglob("UNIT_*"):
        if proc_subdir.is_dir():
            processing_units.append(proc_subdir)
    
    print(f"\n📁 Processing: {len(processing_units)} UNIT")
    
    # Разбивка по поддиректориям
    proc_by_type = Counter()
    for unit in processing_units:
        rel_path = unit.relative_to(processing_dir)
        path_parts = rel_path.parts
        if len(path_parts) >= 2:
            proc_by_type[f"{path_parts[0]}/{path_parts[1]}"] += 1
    
    for proc_type, count in proc_by_type.most_common():
        print(f"  {proc_type}: {count} UNIT")
    
    # Проверяем Exceptions
    exceptions_dir = base_dir / "Exceptions"
    exceptions_units = []
    for exc_subdir in exceptions_dir.rglob("UNIT_*"):
        if exc_subdir.is_dir():
            exceptions_units.append(exc_subdir)
    
    print(f"\n📁 Exceptions: {len(exceptions_units)} UNIT")
    
    # Разбивка по поддиректориям
    exc_by_type = Counter()
    for unit in exceptions_units:
        rel_path = unit.relative_to(exceptions_dir)
        path_parts = rel_path.parts
        if len(path_parts) >= 2:
            exc_by_type[f"{path_parts[0]}/{path_parts[1]}"] += 1
    
    for exc_type, count in exc_by_type.most_common():
        print(f"  {exc_type}: {count} UNIT")
    
    # Проверяем неправильные директории
    print(f"\n🔍 Проверка неправильных директорий:")
    wrong_dirs = []
    for category in ["Exceptions", "Merge", "Processing"]:
        category_dir = Path(f"Data/{category}/{date}")
        if category_dir.exists():
            wrong_units = len([d for d in category_dir.rglob("UNIT_*") if d.is_dir()])
            wrong_dirs.append((str(category_dir), wrong_units))
    
    if wrong_dirs:
        print(f"  ❌ Найдены неправильные директории:")
        for dir_path, unit_count in wrong_dirs:
            print(f"    {dir_path}: {unit_count} UNIT")
    else:
        print(f"  ✅ Неправильных директорий не найдено")
    
    # Итоговая статистика
    total_processed = len(merge_units) + len(processing_units) + len(exceptions_units)
    total_input = len(input_units)
    
    print(f"\n📊 ИТОГОВАЯ СТАТИСТИКА:")
    print(f"  Input: {total_input} UNIT")
    print(f"  Обработано: {total_processed} UNIT")
    print(f"  Пустые (unknown): {len(empty_units)} UNIT")
    print(f"  Разница: {total_input - total_processed - len(empty_units)} UNIT")
    
    # Проверяем, что все UNIT с файлами обработаны
    units_with_files = total_input - len(empty_units)
    if total_processed == units_with_files:
        print(f"\n✅ Все UNIT с файлами успешно обработаны!")
    else:
        print(f"\n⚠️  Не все UNIT обработаны: {units_with_files} с файлами, {total_processed} обработано")

if __name__ == "__main__":
    analyze_results()

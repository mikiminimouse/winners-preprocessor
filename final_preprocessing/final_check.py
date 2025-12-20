#!/usr/bin/env python3
"""
Финальная проверка структуры и результатов классификации.
"""
import sys
from pathlib import Path
from collections import Counter

# Добавляем путь к модулю
sys.path.insert(0, str(Path(__file__).parent))

def final_check():
    """Финальная проверка структуры."""
    date = "2025-03-18"
    base_dir = Path(f"Data/{date}")
    
    print("=" * 60)
    print("ФИНАЛЬНАЯ ПРОВЕРКА СТРУКТУРЫ")
    print("=" * 60)
    
    # 1. Проверка неправильных директорий
    print("\n1. Проверка неправильных директорий:")
    wrong_dirs = []
    for category in ["Exceptions", "Merge", "Processing"]:
        category_dir = Path(f"Data/{category}/{date}")
        if category_dir.exists():
            units = len([d for d in category_dir.rglob("UNIT_*") if d.is_dir()])
            if units > 0:
                wrong_dirs.append((str(category_dir), units))
    
    if wrong_dirs:
        print(f"  ❌ Найдены неправильные директории с UNIT:")
        for dir_path, unit_count in wrong_dirs:
            print(f"    {dir_path}: {unit_count} UNIT")
    else:
        print(f"  ✅ Неправильных директорий не найдено")
    
    # 2. Проверка правильной структуры
    print("\n2. Проверка правильной структуры:")
    categories = {
        "Input": base_dir / "Input",
        "Processing": base_dir / "Processing",
        "Merge": base_dir / "Merge",
        "Exceptions": base_dir / "Exceptions",
        "Ready2Docling": base_dir / "Ready2Docling",
    }
    
    for name, path in categories.items():
        if path.exists():
            units = len([d for d in path.rglob("UNIT_*") if d.is_dir()])
            print(f"  ✅ {name}: {units} UNIT")
        else:
            print(f"  ⚠️  {name}: не найдена")
    
    # 3. Проверка путей UNIT
    print("\n3. Проверка путей UNIT:")
    all_units = []
    for category_path in categories.values():
        if category_path.exists():
            units = [d for d in category_path.rglob("UNIT_*") if d.is_dir()]
            all_units.extend(units)
    
    wrong_paths = []
    for unit in all_units:
        unit_str = str(unit)
        if not unit_str.startswith(f"Data/{date}/"):
            wrong_paths.append(unit_str)
    
    if wrong_paths:
        print(f"  ❌ Найдено UNIT с неправильными путями: {len(wrong_paths)}")
        for path in wrong_paths[:5]:
            print(f"    {path}")
    else:
        print(f"  ✅ Все UNIT в правильных директориях")
    
    # 4. Статистика по категориям
    print("\n4. Статистика по категориям:")
    
    # Merge
    merge_units = [d for d in (base_dir / "Merge").rglob("UNIT_*") if d.is_dir()]
    merge_by_type = Counter()
    for unit in merge_units:
        rel_path = unit.relative_to(base_dir / "Merge")
        if len(rel_path.parts) >= 2:
            merge_by_type[rel_path.parts[0]] += 1
    print(f"  Merge: {len(merge_units)} UNIT")
    for merge_type, count in merge_by_type.most_common():
        print(f"    {merge_type}: {count} UNIT")
    
    # Processing
    proc_units = [d for d in (base_dir / "Processing").rglob("UNIT_*") if d.is_dir()]
    proc_by_type = Counter()
    for unit in proc_units:
        rel_path = unit.relative_to(base_dir / "Processing")
        if len(rel_path.parts) >= 2:
            proc_by_type[rel_path.parts[0]] += 1
    print(f"  Processing: {len(proc_units)} UNIT")
    for proc_type, count in proc_by_type.most_common():
        print(f"    {proc_type}: {count} UNIT")
    
    # Exceptions
    exc_units = [d for d in (base_dir / "Exceptions").rglob("UNIT_*") if d.is_dir()]
    exc_by_type = Counter()
    for unit in exc_units:
        rel_path = unit.relative_to(base_dir / "Exceptions")
        if len(rel_path.parts) >= 2:
            exc_by_type[rel_path.parts[0]] += 1
    print(f"  Exceptions: {len(exc_units)} UNIT")
    for exc_type, count in exc_by_type.most_common():
        print(f"    {exc_type}: {count} UNIT")
    
    # 5. Проверка Input
    input_units = [d for d in (base_dir / "Input").iterdir() if d.is_dir() and d.name.startswith("UNIT_")]
    empty_units = []
    for unit in input_units:
        files = [f for f in unit.iterdir() if f.is_file() and f.name not in ["manifest.json", "audit.log.jsonl"]]
        if not files:
            empty_units.append(unit.name)
    
    print(f"\n5. Input директория:")
    print(f"  Всего UNIT: {len(input_units)}")
    print(f"  Пустые UNIT: {len(empty_units)}")
    print(f"  UNIT с файлами: {len(input_units) - len(empty_units)}")
    
    # 6. Итоговая проверка
    print("\n6. Итоговая проверка:")
    total_processed = len(merge_units) + len(proc_units) + len(exc_units)
    units_with_files = len(input_units) - len(empty_units)
    
    if total_processed == units_with_files:
        print(f"  ✅ Все UNIT с файлами обработаны: {total_processed}")
    else:
        print(f"  ⚠️  Несоответствие: {units_with_files} с файлами, {total_processed} обработано")
    
    if not wrong_dirs and not wrong_paths:
        print(f"\n✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ УСПЕШНО!")
    else:
        print(f"\n⚠️  Найдены проблемы, требующие исправления")

if __name__ == "__main__":
    final_check()

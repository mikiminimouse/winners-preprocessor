#!/usr/bin/env python3
"""
Проверка дубликатов UNIT.
"""
import sys
from pathlib import Path
from collections import Counter

# Добавляем путь к модулю
sys.path.insert(0, str(Path(__file__).parent))

def check_duplicates():
    """Проверка дубликатов UNIT."""
    date = "2025-03-18"
    base_dir = Path(f"Data/{date}")
    
    print("=" * 60)
    print("ПРОВЕРКА ДУБЛИКАТОВ UNIT")
    print("=" * 60)
    
    # Находим все UNIT
    all_units = []
    for category in ["Input", "Processing", "Merge", "Exceptions"]:
        category_path = base_dir / category
        if category_path.exists():
            units = [d for d in category_path.rglob("UNIT_*") if d.is_dir()]
            for unit in units:
                all_units.append((unit.name, str(unit)))
    
    # Проверяем дубликаты
    unit_names = Counter([name for name, _ in all_units])
    duplicates = {name: count for name, count in unit_names.items() if count > 1}
    
    if duplicates:
        print(f"\n❌ Найдено дубликатов: {len(duplicates)}")
        for unit_name, count in duplicates.items():
            print(f"\n  {unit_name}: {count} копий")
            for name, path in all_units:
                if name == unit_name:
                    print(f"    - {path}")
    else:
        print(f"\n✅ Дубликатов не найдено")
    
    print(f"\nВсего UNIT: {len(all_units)}")
    print(f"Уникальных UNIT: {len(unit_names)}")

if __name__ == "__main__":
    check_duplicates()

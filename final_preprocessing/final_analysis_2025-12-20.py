#!/usr/bin/env python3
"""
Финальный анализ результатов классификации на дате 2025-12-20.
"""
import sys
from pathlib import Path
from collections import Counter

# Добавляем путь к модулю
sys.path.insert(0, str(Path(__file__).parent))

def final_analysis():
    """Финальный анализ результатов."""
    date = "2025-12-20"
    base_dir = Path(f"Data/{date}")
    
    print("=" * 60)
    print("ФИНАЛЬНЫЙ АНАЛИЗ РЕЗУЛЬТАТОВ КЛАССИФИКАЦИИ")
    print(f"Дата: {date}")
    print("=" * 60)
    
    # Проверяем структуру
    categories = {
        "Input": base_dir / "Input",
        "Processing": base_dir / "Processing",
        "Merge": base_dir / "Merge",
        "Exceptions": base_dir / "Exceptions",
    }
    
    print("\n📁 Распределение UNIT по директориям:")
    total_units = 0
    for name, path in categories.items():
        if path.exists():
            units = [d for d in path.rglob("UNIT_*") if d.is_dir()]
            unit_count = len(units)
            total_units += unit_count
            print(f"  {name}: {unit_count} UNIT")
        else:
            print(f"  {name}: не найдена")
    
    print(f"\n  Всего обработано: {total_units} UNIT")
    
    # Детальная статистика по Merge
    print("\n📊 Детальная статистика по Merge:")
    merge_dir = base_dir / "Merge"
    if merge_dir.exists():
        merge_by_type = Counter()
        for unit in merge_dir.rglob("UNIT_*"):
            if unit.is_dir():
                rel_path = unit.relative_to(merge_dir)
                if len(rel_path.parts) >= 3:
                    merge_type = f"{rel_path.parts[0]}/{rel_path.parts[1]}/{rel_path.parts[2]}"
                    merge_by_type[merge_type] += 1
        
        for merge_type, count in sorted(merge_by_type.items()):
            print(f"  {merge_type}: {count} UNIT")
    
    # Детальная статистика по Processing
    print("\n📊 Детальная статистика по Processing:")
    proc_dir = base_dir / "Processing"
    if proc_dir.exists():
        proc_by_type = Counter()
        for unit in proc_dir.rglob("UNIT_*"):
            if unit.is_dir():
                rel_path = unit.relative_to(proc_dir)
                if len(rel_path.parts) >= 3:
                    proc_type = f"{rel_path.parts[0]}/{rel_path.parts[1]}/{rel_path.parts[2]}"
                    proc_by_type[proc_type] += 1
        
        for proc_type, count in sorted(proc_by_type.items()):
            print(f"  {proc_type}: {count} UNIT")
    
    # Детальная статистика по Exceptions
    print("\n📊 Детальная статистика по Exceptions:")
    exc_dir = base_dir / "Exceptions"
    if exc_dir.exists():
        exc_by_type = Counter()
        for unit in exc_dir.rglob("UNIT_*"):
            if unit.is_dir():
                rel_path = unit.relative_to(exc_dir)
                if len(rel_path.parts) >= 2:
                    exc_type = f"{rel_path.parts[0]}/{rel_path.parts[1]}"
                    exc_by_type[exc_type] += 1
        
        for exc_type, count in sorted(exc_by_type.items()):
            print(f"  {exc_type}: {count} UNIT")
    
    # Проверка неправильных директорий
    print("\n🔍 Проверка неправильных директорий:")
    wrong_dirs = []
    for category in ["Exceptions", "Merge", "Processing"]:
        category_dir = Path(f"Data/{category}/{date}")
        if category_dir.exists():
            units = len([d for d in category_dir.rglob("UNIT_*") if d.is_dir()])
            if units > 0:
                wrong_dirs.append((str(category_dir), units))
    
    if wrong_dirs:
        print(f"  ❌ Найдены неправильные директории:")
        for dir_path, unit_count in wrong_dirs:
            print(f"    {dir_path}: {unit_count} UNIT")
    else:
        print(f"  ✅ Неправильных директорий не найдено")
    
    # Проверка Input
    print("\n📁 Input директория:")
    input_dir = base_dir / "Input"
    if input_dir.exists():
        input_units = [d for d in input_dir.iterdir() if d.is_dir() and d.name.startswith("UNIT_")]
        empty_units = []
        for unit in input_units:
            files = [f for f in unit.iterdir() if f.is_file() and f.name not in ["manifest.json", "audit.log.jsonl"]]
            if not files:
                empty_units.append(unit.name)
        
        print(f"  Всего UNIT: {len(input_units)}")
        print(f"  Пустые UNIT: {len(empty_units)}")
        print(f"  UNIT с файлами: {len(input_units) - len(empty_units)}")
    
    print("\n✅ Анализ завершен")

if __name__ == "__main__":
    final_analysis()

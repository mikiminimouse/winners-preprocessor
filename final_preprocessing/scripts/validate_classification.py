#!/usr/bin/env python3
"""
Скрипт для валидации корректной классификации UNIT в пайплайне docprep.

Этот скрипт проверяет:
1. Все UNIT из Input корректно классифицированы
2. Ни один UNIT не потерян
3. Ни один UNIT не классифицирован дважды
4. Все manifest.json корректно созданы
"""

import sys
from pathlib import Path
from collections import Counter, defaultdict
import json

# Добавляем путь к модулю docprep
sys.path.insert(0, str(Path(__file__).parent))

from docprep.utils.paths import find_all_units, get_unit_files
from docprep.core.manifest import load_manifest


def collect_input_units_stats(input_dir: Path) -> dict:
    """Собирает статистику по входным UNIT."""
    stats = {
        "total_units": 0,
        "empty_units": 0,
        "units_with_files": 0,
        "file_extensions": Counter(),
        "units_by_extension": defaultdict(set),
        "unit_list": set(),
    }
    
    print(f"Анализ входных UNIT в {input_dir}...")
    
    for unit_dir in input_dir.iterdir():
        if not unit_dir.is_dir() or not unit_dir.name.startswith("UNIT_"):
            continue
            
        stats["total_units"] += 1
        stats["unit_list"].add(unit_dir.name)
        files = get_unit_files(unit_dir)
        
        if not files:
            stats["empty_units"] += 1
            continue
        
        stats["units_with_files"] += 1
        
        for file_path in files:
            ext = file_path.suffix.lower().lstrip(".")
            if not ext:
                ext = "no_extension"
            stats["file_extensions"][ext] += 1
            stats["units_by_extension"][ext].add(unit_dir.name)
    
    print(f"Найдено {stats['total_units']} UNIT")
    print(f"Пустых UNIT: {stats['empty_units']}")
    print(f"UNIT с файлами: {stats['units_with_files']}")
    
    return stats


def collect_processed_units_stats(base_dir: Path) -> dict:
    """Собирает статистику по обработанным UNIT."""
    stats = {
        "classified_units": 0,
        "unit_locations": defaultdict(list),
        "unit_routes": Counter(),
        "categories": Counter(),
        "errors": [],
        "unit_set": set(),
    }
    
    print(f"Анализ обработанных UNIT в {base_dir}...")
    
    # Директории для поиска
    search_dirs = [
        base_dir / "Processing" / "Processing_1",
        base_dir / "Processing" / "Processing_2",
        base_dir / "Processing" / "Processing_3",
        base_dir / "Merge" / "Merge_0",
        base_dir / "Merge" / "Merge_1",
        base_dir / "Merge" / "Merge_2",
        base_dir / "Merge" / "Merge_3",
        base_dir / "Exceptions" / "Exceptions_1",
        base_dir / "Exceptions" / "Exceptions_2",
        base_dir / "Exceptions" / "Exceptions_3",
    ]
    
    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
            
        print(f"Поиск в {search_dir}...")
        for unit_dir in search_dir.rglob("UNIT_*"):
            if not unit_dir.is_dir():
                continue
                
            unit_id = unit_dir.name
            stats["unit_set"].add(unit_id)
            stats["classified_units"] += 1
            stats["unit_locations"][unit_id].append(str(unit_dir.relative_to(base_dir)))
            
            # Проверяем manifest
            manifest_path = unit_dir / "manifest.json"
            if not manifest_path.exists():
                stats["errors"].append(f"Отсутствует manifest.json в {unit_dir}")
                continue
            
            try:
                manifest = load_manifest(unit_dir)
                
                # Получаем категорию
                operations = manifest.get("applied_operations", [])
                if operations:
                    last_op = operations[-1]
                    category = last_op.get("category", "unknown")
                    stats["categories"][category] += 1
                
                # Получаем route
                route = manifest.get("processing", {}).get("route")
                if route:
                    stats["unit_routes"][route] += 1
                    
            except Exception as e:
                stats["errors"].append(f"Ошибка чтения manifest.json в {unit_dir}: {e}")
    
    print(f"Найдено {stats['classified_units']} обработанных UNIT")
    print(f"Уникальных UNIT: {len(stats['unit_set'])}")
    
    return stats


def validate_classification(input_stats: dict, processed_stats: dict) -> dict:
    """Проверяет корректность классификации."""
    results = {
        "valid": True,
        "issues": [],
        "summary": {},
    }
    
    input_units = input_stats["unit_list"]
    processed_units = processed_stats["unit_set"]
    
    # Проверка на потерянные UNIT
    lost_units = input_units - processed_units
    if lost_units:
        results["valid"] = False
        results["issues"].append(f"Потеряно {len(lost_units)} UNIT: {sorted(lost_units)[:10]}...")
    
    # Проверка на дубликаты
    duplicate_units = [unit for unit, locations in processed_stats["unit_locations"].items() if len(locations) > 1]
    if duplicate_units:
        results["valid"] = False
        results["issues"].append(f"Найдены дубликаты для {len(duplicate_units)} UNIT")
        for unit in duplicate_units[:5]:
            results["issues"].append(f"  {unit} находится в: {processed_stats['unit_locations'][unit]}")
    
    # Проверка баланса
    results["summary"] = {
        "input_units": len(input_units),
        "processed_units": len(processed_units),
        "lost_units": len(lost_units),
        "duplicate_units": len(duplicate_units),
    }
    
    return results


def main():
    """Основная функция."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Валидация классификации UNIT")
    parser.add_argument("--date", required=True, help="Дата в формате YYYY-MM-DD")
    parser.add_argument("--base-dir", default="Data", help="Базовая директория с данными")
    
    args = parser.parse_args()
    
    base_dir = Path(args.base_dir) / args.date
    input_dir = base_dir / "Input"
    
    if not input_dir.exists():
        print(f"Ошибка: Директория {input_dir} не существует")
        return 1
    
    print("=" * 80)
    print("ВАЛИДАЦИЯ КЛАССИФИКАЦИИ UNIT")
    print("=" * 80)
    print(f"Дата: {args.date}")
    print(f"Базовая директория: {base_dir}")
    print()
    
    # Сбор статистики
    input_stats = collect_input_units_stats(input_dir)
    print()
    
    processed_stats = collect_processed_units_stats(base_dir)
    print()
    
    # Валидация
    validation_results = validate_classification(input_stats, processed_stats)
    
    # Вывод результатов
    print("=" * 80)
    print("РЕЗУЛЬТАТЫ ВАЛИДАЦИИ")
    print("=" * 80)
    
    print(f"Всего входных UNIT: {validation_results['summary']['input_units']}")
    print(f"Обработано UNIT: {validation_results['summary']['processed_units']}")
    print(f"Потеряно UNIT: {validation_results['summary']['lost_units']}")
    print(f"Дубликаты UNIT: {validation_results['summary']['duplicate_units']}")
    print()
    
    if validation_results["valid"]:
        print("✅ КЛАССИФИКАЦИЯ КОРРЕКТНА")
    else:
        print("❌ НАЙДЕНЫ ОШИБКИ КЛАССИФИКАЦИИ")
        for issue in validation_results["issues"]:
            print(f"  - {issue}")
    
    # Статистика по категориям
    if processed_stats["categories"]:
        print("\nРАСПРЕДЕЛЕНИЕ ПО КАТЕГОРИЯМ:")
        for category, count in processed_stats["categories"].most_common():
            print(f"  {category}: {count}")
    
    # Статистика по route
    if processed_stats["unit_routes"]:
        print("\nРАСПРЕДЕЛЕНИЕ ПО ROUTE:")
        for route, count in processed_stats["unit_routes"].most_common():
            print(f"  {route}: {count}")
    
    # Ошибки
    if processed_stats["errors"]:
        print(f"\nОШИБКИ ({len(processed_stats['errors'])}):")
        for error in processed_stats["errors"][:10]:
            print(f"  - {error}")
        if len(processed_stats["errors"]) > 10:
            print(f"  ... и еще {len(processed_stats['errors']) - 10} ошибок")
    
    return 0 if validation_results["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
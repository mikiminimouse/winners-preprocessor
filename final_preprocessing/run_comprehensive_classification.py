#!/usr/bin/env python3
"""
Полное тестирование классификации с детальной статистикой и аналитикой.
"""
import sys
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime
import json

# Добавляем путь к модулю
sys.path.insert(0, str(Path(__file__).parent))

from docprep.engine.classifier import Classifier
from docprep.utils.paths import get_unit_files
from docprep.core.manifest import load_manifest

def collect_input_statistics(input_dir: Path):
    """Собирает детальную статистику по входным UNIT."""
    stats = {
        "total_units": 0,
        "empty_units": 0,
        "units_with_files": 0,
        "file_extensions": Counter(),
        "file_types": Counter(),
        "units_by_extension": defaultdict(set),
        "files_by_extension": Counter(),
    }
    
    for unit_dir in input_dir.iterdir():
        if not unit_dir.is_dir() or not unit_dir.name.startswith("UNIT_"):
            continue
        
        stats["total_units"] += 1
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
            stats["files_by_extension"][ext] += 1
            stats["units_by_extension"][ext].add(unit_dir.name)
    
    return stats

def analyze_output_statistics(date: str):
    """Анализирует результаты классификации из manifest."""
    base_dir = Path(f"Data/{date}")
    results = {
        "total_classified": 0,
        "by_category": Counter(),
        "by_location": defaultdict(int),
        "empty_units": 0,
        "units_with_files": 0,
        "empty_by_category": Counter(),
        "with_files_by_category": Counter(),
        "file_extensions_input": Counter(),
        "file_extensions_output": Counter(),
        "category_by_extension_input": defaultdict(lambda: Counter()),
        "category_by_extension_output": defaultdict(lambda: Counter()),
        "category_by_location": defaultdict(lambda: Counter()),
        "route_distribution": Counter(),
        "errors": [],
    }
    
    # Собираем информацию из всех директорий
    search_dirs = [
        base_dir / "Processing" / "Processing_1",
        base_dir / "Merge" / "Merge_0",
        base_dir / "Exceptions" / "Exceptions_1",
    ]
    
    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        
        for unit_dir in search_dir.rglob("UNIT_*"):
            if not unit_dir.is_dir():
                continue
            
            manifest_path = unit_dir / "manifest.json"
            if not manifest_path.exists():
                continue
            
            try:
                manifest = load_manifest(unit_dir)
                results["total_classified"] += 1
                
                files = manifest.get("files", [])
                is_empty = len(files) == 0
                
                if is_empty:
                    results["empty_units"] += 1
                else:
                    results["units_with_files"] += 1
                
                # Категория из applied_operations
                operations = manifest.get("applied_operations", [])
                category = "unknown"
                if operations:
                    last_op = operations[-1]
                    category = last_op.get("category", "unknown")
                    results["by_category"][category] += 1
                    
                    if is_empty:
                        results["empty_by_category"][category] += 1
                    else:
                        results["with_files_by_category"][category] += 1
                
                # Определяем локацию
                location_parts = list(unit_dir.parts)
                location = "/".join(location_parts[location_parts.index(date)+1:]) if date in location_parts else "unknown"
                results["by_location"][location] += 1
                results["category_by_location"][category][location] += 1
                
                # Route
                route = manifest.get("processing", {}).get("route")
                if route:
                    results["route_distribution"][route] += 1
                
                # Расширения файлов
                for file_info in files:
                    original_name = file_info.get("original_name", "")
                    if original_name:
                        ext = Path(original_name).suffix.lower().lstrip(".")
                        if not ext:
                            ext = "no_extension"
                        if ext:
                            results["file_extensions_input"][ext] += 1
                            results["category_by_extension_input"][category][ext] += 1
                    
                    current_name = file_info.get("current_name", "")
                    if current_name:
                        ext = Path(current_name).suffix.lower().lstrip(".")
                        if not ext:
                            ext = "no_extension"
                        if ext:
                            results["file_extensions_output"][ext] += 1
                            results["category_by_extension_output"][category][ext] += 1
                
            except Exception as e:
                results["errors"].append({
                    "unit": unit_dir.name,
                    "error": str(e),
                })
    
    return results

def run_classification(date: str):
    """Запускает классификацию всех UNIT из Input."""
    print("=" * 80)
    print("ЗАПУСК КЛАССИФИКАЦИИ")
    print("=" * 80)
    
    # Проверяем оба варианта (Input и input)
    input_dir = Path(f"Data/{date}/Input")
    if not input_dir.exists():
        input_dir = Path(f"Data/{date}/input")
    
    if not input_dir.exists():
        print(f"❌ Директория не найдена: {input_dir}")
        return None, []
    
    units = [d for d in input_dir.iterdir() if d.is_dir() and d.name.startswith("UNIT_")]
    print(f"\nНайдено UNIT в Input: {len(units)}")
    
    # Проверяем, какие уже обработаны
    base_dir = Path(f"Data/{date}")
    processed_units = set()
    for search_dir in [
        base_dir / "Processing" / "Processing_1",
        base_dir / "Merge" / "Merge_0",
        base_dir / "Exceptions" / "Exceptions_1",
    ]:
        if search_dir.exists():
            for unit_dir in search_dir.rglob("UNIT_*"):
                if unit_dir.is_dir():
                    processed_units.add(unit_dir.name)
    
    units_to_process = [d for d in units if d.name not in processed_units]
    print(f"Уже обработано: {len(processed_units)}")
    print(f"Требуется обработка: {len(units_to_process)}")
    
    if not units_to_process:
        print("\n✅ Все UNIT уже обработаны")
        return len(units), []
    
    classifier = Classifier()
    processed = 0
    errors = []
    total = len(units_to_process)
    
    print(f"\nНачинаем обработку {total} UNIT...")
    for i, unit_path in enumerate(units_to_process, 1):
        try:
            result = classifier.classify_unit(
                unit_path,
                cycle=1,
                protocol_date=date,
                dry_run=False,
                copy_mode=True,  # Копируем для тестирования
            )
            processed += 1
            if i % 100 == 0:
                print(f"  Обработано: {i}/{total} ({i*100//total}%)")
        except Exception as e:
            errors.append({"unit": unit_path.name, "error": str(e)})
            if len(errors) <= 10:
                print(f"  ❌ {unit_path.name}: {e}")
    
    print(f"\n✅ Обработано: {processed}/{total}")
    if errors:
        print(f"❌ Ошибок: {len(errors)}")
    
    return processed, errors

def generate_comprehensive_report(date: str, input_stats: dict, output_stats: dict, processed: int, errors: list):
    """Генерирует подробный отчет."""
    report = []
    report.append("# ПОЛНЫЙ ОТЧЕТ О КЛАССИФИКАЦИИ UNIT")
    report.append(f"\n**Дата**: {date}")
    report.append(f"**Время генерации**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. Входные данные
    report.append("\n## 1. СТАТИСТИКА ВХОДНЫХ ДАННЫХ (INPUT)")
    report.append(f"\n### Общая статистика")
    report.append(f"- **Всего UNIT**: {input_stats['total_units']}")
    report.append(f"- **Пустых UNIT**: {input_stats['empty_units']} ({input_stats['empty_units']*100//input_stats['total_units'] if input_stats['total_units'] > 0 else 0}%)")
    report.append(f"- **UNIT с файлами**: {input_stats['units_with_files']} ({input_stats['units_with_files']*100//input_stats['total_units'] if input_stats['total_units'] > 0 else 0}%)")
    
    report.append(f"\n### Расширения файлов на входе (топ-30)")
    report.append("| Расширение | Файлов | UNIT |")
    report.append("|------------|--------|------|")
    for ext, file_count in input_stats['file_extensions'].most_common(30):
        unit_count = len(input_stats['units_by_extension'][ext])
        report.append(f"| .{ext} | {file_count} | {unit_count} |")
    
    # 2. Выходные данные
    report.append("\n## 2. СТАТИСТИКА ВЫХОДНЫХ ДАННЫХ (OUTPUT)")
    report.append(f"\n### Общая статистика")
    report.append(f"- **Всего классифицировано**: {output_stats['total_classified']}")
    report.append(f"- **Пустых UNIT**: {output_stats['empty_units']} ({output_stats['empty_units']*100//output_stats['total_classified'] if output_stats['total_classified'] > 0 else 0}%)")
    report.append(f"- **UNIT с файлами**: {output_stats['units_with_files']} ({output_stats['units_with_files']*100//output_stats['total_classified'] if output_stats['total_classified'] > 0 else 0}%)")
    
    report.append(f"\n### Распределение по категориям (ВСЕ UNIT)")
    report.append("| Категория | Всего UNIT | Пустых | С файлами | % от общего |")
    report.append("|-----------|------------|--------|-----------|-------------|")
    total_categorized = sum(output_stats['by_category'].values())
    for category, count in output_stats['by_category'].most_common():
        empty = output_stats['empty_by_category'].get(category, 0)
        with_files = output_stats['with_files_by_category'].get(category, 0)
        percentage = count * 100 // total_categorized if total_categorized > 0 else 0
        report.append(f"| {category} | {count} | {empty} | {with_files} | {percentage}% |")
    
    report.append(f"\n### Распределение по категориям (БЕЗ ПУСТЫХ UNIT)")
    report.append("| Категория | UNIT с файлами | % от UNIT с файлами |")
    report.append("|-----------|----------------|---------------------|")
    total_with_files = output_stats['units_with_files']
    for category, count in output_stats['by_category'].most_common():
        with_files = output_stats['with_files_by_category'].get(category, 0)
        percentage = with_files * 100 // total_with_files if total_with_files > 0 else 0
        report.append(f"| {category} | {with_files} | {percentage}% |")
    
    # 3. Анализ Unknown UNIT
    report.append("\n## 3. ДЕТАЛЬНЫЙ АНАЛИЗ UNKNOWN UNIT")
    unknown_count = output_stats['by_category'].get('unknown', 0)
    unknown_empty = output_stats['empty_by_category'].get('unknown', 0)
    unknown_with_files = output_stats['with_files_by_category'].get('unknown', 0)
    
    report.append(f"\n### Статистика")
    report.append(f"- **Всего unknown UNIT**: {unknown_count}")
    report.append(f"  - Пустых: {unknown_empty} ({unknown_empty*100//unknown_count if unknown_count > 0 else 0}%)")
    report.append(f"  - С файлами: {unknown_with_files} ({unknown_with_files*100//unknown_count if unknown_count > 0 else 0}%)")
    report.append(f"- **Процент от общего числа UNIT**: {unknown_count*100//output_stats['total_classified'] if output_stats['total_classified'] > 0 else 0}%")
    report.append(f"- **Процент от UNIT с файлами**: {unknown_with_files*100//output_stats['units_with_files'] if output_stats['units_with_files'] > 0 else 0}%")
    
    report.append(f"\n### Вывод")
    if unknown_empty > 0:
        report.append(f"**Основная причина большого количества unknown UNIT**: {unknown_empty} из {unknown_count} ({unknown_empty*100//unknown_count if unknown_count > 0 else 0}%) - это **пустые UNIT**, которые не могут быть классифицированы, так как не содержат файлов.")
        report.append(f"\nЕсли исключить пустые UNIT, то unknown UNIT с файлами составляют только {unknown_with_files} из {output_stats['units_with_files']} ({unknown_with_files*100//output_stats['units_with_files'] if output_stats['units_with_files'] > 0 else 0}%) от всех UNIT с файлами.")
    
    # 4. Расширения файлов по категориям (вход)
    report.append("\n## 4. РАСШИРЕНИЯ ФАЙЛОВ ПО КАТЕГОРИЯМ (ВХОД)")
    for category in sorted(output_stats['category_by_extension_input'].keys()):
        if output_stats['category_by_extension_input'][category]:
            report.append(f"\n### {category.upper()}")
            report.append("| Расширение | Количество файлов |")
            report.append("|------------|-------------------|")
            for ext, count in output_stats['category_by_extension_input'][category].most_common(20):
                report.append(f"| .{ext} | {count} |")
    
    # 5. Расширения файлов по категориям (выход)
    report.append("\n## 5. РАСШИРЕНИЯ ФАЙЛОВ ПО КАТЕГОРИЯМ (ВЫХОД)")
    for category in sorted(output_stats['category_by_extension_output'].keys()):
        if output_stats['category_by_extension_output'][category]:
            report.append(f"\n### {category.upper()}")
            report.append("| Расширение | Количество файлов |")
            report.append("|------------|-------------------|")
            for ext, count in output_stats['category_by_extension_output'][category].most_common(20):
                report.append(f"| .{ext} | {count} |")
    
    # 6. Распределение по локациям
    report.append("\n## 6. РАСПРЕДЕЛЕНИЕ ПО ЛОКАЦИЯМ")
    report.append("| Категория | Локация | Количество UNIT |")
    report.append("|-----------|---------|------------------|")
    for category in sorted(output_stats['category_by_location'].keys()):
        for location, count in sorted(output_stats['category_by_location'][category].items()):
            report.append(f"| {category} | {location} | {count} |")
    
    # 7. Сравнение входных и выходных расширений
    report.append("\n## 7. СРАВНЕНИЕ ВХОДНЫХ И ВЫХОДНЫХ РАСШИРЕНИЙ")
    report.append("\n### Топ-30 расширений на входе")
    report.append("| Расширение | Количество файлов |")
    report.append("|------------|-------------------|")
    for ext, count in output_stats['file_extensions_input'].most_common(30):
        report.append(f"| .{ext} | {count} |")
    
    report.append("\n### Топ-30 расширений на выходе")
    report.append("| Расширение | Количество файлов |")
    report.append("|------------|-------------------|")
    for ext, count in output_stats['file_extensions_output'].most_common(30):
        report.append(f"| .{ext} | {count} |")
    
    # 8. Route distribution
    if output_stats['route_distribution']:
        report.append("\n## 8. РАСПРЕДЕЛЕНИЕ ПО ROUTE")
        report.append("| Route | Количество UNIT |")
        report.append("|-------|-----------------|")
        for route, count in output_stats['route_distribution'].most_common():
            report.append(f"| {route} | {count} |")
    
    # 9. Ошибки
    if errors:
        report.append("\n## 9. ОШИБКИ КЛАССИФИКАЦИИ")
        report.append(f"\nВсего ошибок: {len(errors)}")
        report.append("\n| UNIT | Ошибка |")
        report.append("|------|--------|")
        for error in errors[:50]:
            error_msg = error['error'].replace('\n', ' ').replace('|', '\\|')[:200]
            report.append(f"| {error['unit']} | {error_msg} |")
        if len(errors) > 50:
            report.append(f"\n... и еще {len(errors) - 50} ошибок")
    
    # 10. Итоговая сводка
    report.append("\n## 10. ИТОГОВАЯ СВОДКА")
    report.append(f"\n### Обработка")
    report.append(f"- Обработано UNIT: {processed}")
    report.append(f"- Всего UNIT в Input: {input_stats['total_units']}")
    report.append(f"- Всего классифицировано: {output_stats['total_classified']}")
    
    report.append(f"\n### Пустые UNIT")
    report.append(f"- Пустых UNIT в Input: {input_stats['empty_units']}")
    report.append(f"- Пустых UNIT в Output: {output_stats['empty_units']}")
    report.append(f"- Процент пустых: {output_stats['empty_units']*100//output_stats['total_classified'] if output_stats['total_classified'] > 0 else 0}%")
    
    report.append(f"\n### UNIT с файлами")
    report.append(f"- UNIT с файлами в Input: {input_stats['units_with_files']}")
    report.append(f"- UNIT с файлами в Output: {output_stats['units_with_files']}")
    
    report.append(f"\n### Unknown UNIT")
    report.append(f"- Всего unknown: {unknown_count}")
    report.append(f"- Пустых unknown: {unknown_empty} ({unknown_empty*100//unknown_count if unknown_count > 0 else 0}%)")
    report.append(f"- Unknown с файлами: {unknown_with_files} ({unknown_with_files*100//output_stats['units_with_files'] if output_stats['units_with_files'] > 0 else 0}% от UNIT с файлами)")
    
    return "\n".join(report)

def main():
    """Главная функция."""
    date = "2025-12-20"
    
    print("=" * 80)
    print("ПОЛНОЕ ТЕСТИРОВАНИЕ КЛАССИФИКАЦИИ С ДЕТАЛЬНОЙ СТАТИСТИКОЙ")
    print("=" * 80)
    
    # 1. Собираем статистику входных данных
    print("\n1. Сбор статистики входных данных...")
    input_dir = Path(f"Data/{date}/Input")
    if not input_dir.exists():
        input_dir = Path(f"Data/{date}/input")
    
    if not input_dir.exists():
        print(f"❌ Директория Input не найдена")
        return
    
    input_stats = collect_input_statistics(input_dir)
    print(f"   Всего UNIT: {input_stats['total_units']}")
    print(f"   Пустых UNIT: {input_stats['empty_units']}")
    print(f"   UNIT с файлами: {input_stats['units_with_files']}")
    print(f"   Уникальных расширений: {len(input_stats['file_extensions'])}")
    
    # 2. Запускаем классификацию
    print("\n2. Запуск классификации...")
    processed, errors = run_classification(date)
    
    # 3. Анализируем результаты
    print("\n3. Анализ результатов...")
    output_stats = analyze_output_statistics(date)
    print(f"   Всего классифицировано: {output_stats['total_classified']}")
    print(f"   Пустых UNIT: {output_stats['empty_units']}")
    print(f"   UNIT с файлами: {output_stats['units_with_files']}")
    
    # 4. Генерируем отчет
    print("\n4. Генерация отчета...")
    report = generate_comprehensive_report(date, input_stats, output_stats, processed or 0, errors)
    
    # 5. Сохраняем отчет
    report_path = Path(f"COMPREHENSIVE_CLASSIFICATION_REPORT_{date}.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    
    print(f"\n✅ Отчет сохранен: {report_path}")
    
    # 6. Краткая сводка
    print("\n" + "=" * 80)
    print("КРАТКАЯ СВОДКА")
    print("=" * 80)
    print(f"Обработано UNIT: {processed or 0}")
    print(f"Всего UNIT в Input: {input_stats['total_units']}")
    print(f"Пустых UNIT: {input_stats['empty_units']} ({input_stats['empty_units']*100//input_stats['total_units'] if input_stats['total_units'] > 0 else 0}%)")
    print(f"UNIT с файлами: {input_stats['units_with_files']} ({input_stats['units_with_files']*100//input_stats['total_units'] if input_stats['total_units'] > 0 else 0}%)")
    
    unknown_count = output_stats['by_category'].get('unknown', 0)
    unknown_empty = output_stats['empty_by_category'].get('unknown', 0)
    unknown_with_files = output_stats['with_files_by_category'].get('unknown', 0)
    
    print(f"\nUnknown UNIT: {unknown_count}")
    print(f"  - Пустых: {unknown_empty} ({unknown_empty*100//unknown_count if unknown_count > 0 else 0}%)")
    print(f"  - С файлами: {unknown_with_files} ({unknown_with_files*100//output_stats['units_with_files'] if output_stats['units_with_files'] > 0 else 0}% от UNIT с файлами)")
    
    print("\n" + "=" * 80)
    print("✅ ВСЕ ЗАВЕРШЕНО")
    print("=" * 80)

if __name__ == "__main__":
    main()


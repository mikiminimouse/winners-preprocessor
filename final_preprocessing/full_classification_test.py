#!/usr/bin/env python3
"""
Полное тестирование классификации и сбор статистики.
"""
import sys
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime
import json

# Добавляем путь к модулю
sys.path.insert(0, str(Path(__file__).parent))

from docprep.engine.classifier import Classifier
from docprep.core.unit_processor import process_directory_units
from docprep.utils.paths import get_unit_files
from docprep.core.manifest import load_manifest

def collect_input_statistics(input_dir: Path):
    """Собирает статистику по входным UNIT."""
    stats = {
        "total_units": 0,
        "empty_units": 0,
        "units_with_files": 0,
        "file_extensions": Counter(),
        "file_types": Counter(),
        "units_by_extension": defaultdict(list),
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
            stats["file_extensions"][ext] += 1
            stats["units_by_extension"][ext].append(unit_dir.name)
    
    return stats

def collect_output_statistics(date: str):
    """Собирает статистику по обработанным UNIT."""
    base_dir = Path(f"Data/{date}")
    stats = {
        "by_category": defaultdict(lambda: {"total": 0, "by_extension": Counter(), "by_type": Counter()}),
        "by_location": defaultdict(int),
        "empty_units": 0,
        "units_with_files": 0,
    }
    
    # Processing
    processing_dir = base_dir / "Processing" / "Processing_1"
    if processing_dir.exists():
        for category in ["Convert", "Extract", "Normalize"]:
            category_dir = processing_dir / category
            if not category_dir.exists():
                continue
            
            for ext_dir in category_dir.iterdir():
                if not ext_dir.is_dir():
                    continue
                
                units = [d for d in ext_dir.iterdir() if d.is_dir() and d.name.startswith("UNIT_")]
                for unit_dir in units:
                    files = get_unit_files(unit_dir)
                    location = f"Processing/Processing_1/{category}/{ext_dir.name}"
                    stats["by_location"][location] += 1
                    stats["by_category"][category]["total"] += 1
                    stats["by_category"][category]["by_extension"][ext_dir.name] += 1
                    
                    if not files:
                        stats["empty_units"] += 1
                    else:
                        stats["units_with_files"] += 1
                        for file_path in files:
                            ext = file_path.suffix.lower().lstrip(".")
                            stats["by_category"][category]["by_type"][ext] += 1
    
    # Merge
    merge_dir = base_dir / "Merge" / "Merge_0"
    if merge_dir.exists():
        direct_dir = merge_dir / "Direct"
        if direct_dir.exists():
            for ext_dir in direct_dir.iterdir():
                if not ext_dir.is_dir():
                    continue
                
                units = [d for d in ext_dir.iterdir() if d.is_dir() and d.name.startswith("UNIT_")]
                for unit_dir in units:
                    files = get_unit_files(unit_dir)
                    location = f"Merge/Merge_0/Direct/{ext_dir.name}"
                    stats["by_location"][location] += 1
                    stats["by_category"]["direct"]["total"] += 1
                    stats["by_category"]["direct"]["by_extension"][ext_dir.name] += 1
                    
                    if not files:
                        stats["empty_units"] += 1
                    else:
                        stats["units_with_files"] += 1
                        for file_path in files:
                            ext = file_path.suffix.lower().lstrip(".")
                            stats["by_category"]["direct"]["by_type"][ext] += 1
    
    # Exceptions
    exceptions_dir = base_dir / "Exceptions" / "Exceptions_1"
    if exceptions_dir.exists():
        for subcategory in ["Ambiguous", "Mixed", "Special"]:
            subcategory_dir = exceptions_dir / subcategory
            if not subcategory_dir.exists():
                continue
            
            units = [d for d in subcategory_dir.iterdir() if d.is_dir() and d.name.startswith("UNIT_")]
            for unit_dir in units:
                files = get_unit_files(unit_dir)
                location = f"Exceptions/Exceptions_1/{subcategory}"
                stats["by_location"][location] += 1
                stats["by_category"][subcategory.lower()]["total"] += 1
                
                if not files:
                    stats["empty_units"] += 1
                else:
                    stats["units_with_files"] += 1
                    for file_path in files:
                        ext = file_path.suffix.lower().lstrip(".")
                        stats["by_category"][subcategory.lower()]["by_type"][ext] += 1
    
    return stats

def analyze_classification_results(date: str):
    """Анализирует результаты классификации."""
    base_dir = Path(f"Data/{date}")
    results = {
        "total_classified": 0,
        "by_category": Counter(),
        "by_route": Counter(),
        "empty_units": 0,
        "units_with_files": 0,
        "file_extensions_input": Counter(),
        "file_extensions_output": Counter(),
        "category_by_extension": defaultdict(lambda: Counter()),
        "category_by_location": defaultdict(lambda: Counter()),
        "empty_units_by_category": Counter(),
        "units_with_files_by_category": Counter(),
        "classification_errors": [],
    }
    
    # Собираем информацию из manifest
    for category_dir in [
        base_dir / "Processing" / "Processing_1",
        base_dir / "Merge" / "Merge_0",
        base_dir / "Exceptions" / "Exceptions_1",
    ]:
        if not category_dir.exists():
            continue
        
        for unit_dir in category_dir.rglob("UNIT_*"):
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
                        results["empty_units_by_category"][category] += 1
                    else:
                        results["units_with_files_by_category"][category] += 1
                
                # Определяем локацию
                location_parts = unit_dir.parts
                if "Processing" in location_parts:
                    location = f"Processing/{location_parts[location_parts.index('Processing')+1]}/{location_parts[location_parts.index('Processing')+2]}"
                    if len(location_parts) > location_parts.index('Processing')+3:
                        location += f"/{location_parts[location_parts.index('Processing')+3]}"
                elif "Merge" in location_parts:
                    location = f"Merge/{location_parts[location_parts.index('Merge')+1]}/{location_parts[location_parts.index('Merge')+2]}"
                    if len(location_parts) > location_parts.index('Merge')+3:
                        location += f"/{location_parts[location_parts.index('Merge')+3]}"
                elif "Exceptions" in location_parts:
                    location = f"Exceptions/{location_parts[location_parts.index('Exceptions')+1]}/{location_parts[location_parts.index('Exceptions')+2]}"
                else:
                    location = "unknown"
                
                results["category_by_location"][category][location] += 1
                
                # Route
                route = manifest.get("processing", {}).get("route")
                if route:
                    results["by_route"][route] += 1
                
                # Расширения файлов
                for file_info in files:
                    original_name = file_info.get("original_name", "")
                    if original_name:
                        ext = Path(original_name).suffix.lower().lstrip(".")
                        if ext:
                            results["file_extensions_input"][ext] += 1
                            results["category_by_extension"][category][ext] += 1
                    
                    current_name = file_info.get("current_name", "")
                    if current_name:
                        ext = Path(current_name).suffix.lower().lstrip(".")
                        if ext:
                            results["file_extensions_output"][ext] += 1
                
            except Exception as e:
                results["classification_errors"].append({
                    "unit": unit_dir.name,
                    "error": str(e),
                })
    
    return results

def run_full_classification(date: str):
    """Запускает полную классификацию."""
    print("=" * 80)
    print("ПОЛНОЕ ТЕСТИРОВАНИЕ КЛАССИФИКАЦИИ")
    print("=" * 80)
    
    # Проверяем разные варианты названия директории
    input_dir = None
    for dir_name in ["Input", "input"]:
        test_dir = Path(f"Data/{date}/{dir_name}")
        if test_dir.exists():
            input_dir = test_dir
            break
    
    # 1. Собираем статистику входных данных
    print("\n1. Сбор статистики входных данных...")
    if input_dir and input_dir.exists():
        input_stats = collect_input_statistics(input_dir)
    else:
        print(f"   ⚠️  Директория Input не найдена, собираем статистику только по обработанным UNIT")
        input_stats = {
            "total_units": 0,
            "empty_units": 0,
            "units_with_files": 0,
            "file_extensions": Counter(),
            "file_types": Counter(),
            "units_by_extension": defaultdict(list),
        }
    print(f"   Всего UNIT: {input_stats['total_units']}")
    print(f"   Пустых UNIT: {input_stats['empty_units']}")
    print(f"   UNIT с файлами: {input_stats['units_with_files']}")
    print(f"   Уникальных расширений: {len(input_stats['file_extensions'])}")
    
    # 2. Проверяем, нужно ли запускать классификацию
    print("\n2. Проверка необходимости классификации...")
    if input_dir and input_dir.exists():
        units_in_input = [d for d in input_dir.iterdir() if d.is_dir() and d.name.startswith("UNIT_")]
        print(f"   UNIT в Input: {len(units_in_input)}")
    else:
        units_in_input = []
        print(f"   UNIT в Input: 0 (директория не найдена)")
    
    # Проверяем, есть ли уже обработанные UNIT
    base_dir = Path(f"Data/{date}")
    processed_units = set()
    for category_dir in [
        base_dir / "Processing" / "Processing_1",
        base_dir / "Merge" / "Merge_0",
        base_dir / "Exceptions" / "Exceptions_1",
    ]:
        if category_dir.exists():
            for unit_dir in category_dir.rglob("UNIT_*"):
                if unit_dir.is_dir():
                    processed_units.add(unit_dir.name)
    
    print(f"   Уже обработано UNIT: {len(processed_units)}")
    
    # Запускаем классификацию только для UNIT в Input
    units_to_process = [d for d in units_in_input if d.name not in processed_units]
    print(f"   UNIT для обработки: {len(units_to_process)}")
    
    if units_to_process:
        print("\n3. Запуск классификации...")
        classifier = Classifier()
        processed = 0
        errors = []
        total = len(units_to_process)
        
        for i, unit_dir in enumerate(units_to_process, 1):
            try:
                result = classifier.classify_unit(
                    unit_dir,
                    cycle=1,
                    protocol_date=date,
                    dry_run=False,
                    copy_mode=True,  # Копируем для тестирования
                )
                processed += 1
                if i % 100 == 0:
                    print(f"   Обработано: {i}/{total} ({i*100//total}%)")
            except Exception as e:
                errors.append({"unit": unit_dir.name, "error": str(e)})
                print(f"   ❌ {unit_dir.name}: {e}")
        
        print(f"\n   ✅ Обработано: {processed}/{total}")
        if errors:
            print(f"   ❌ Ошибок: {len(errors)}")
    else:
        print("\n3. Все UNIT уже обработаны, пропускаем классификацию")
        errors = []
    
    # 4. Собираем статистику выходных данных
    print("\n4. Сбор статистики выходных данных...")
    output_stats = collect_output_statistics(date)
    
    # 5. Анализируем результаты
    print("\n5. Анализ результатов...")
    analysis = analyze_classification_results(date)
    
    # 6. Формируем отчет
    print("\n6. Формирование отчета...")
    report = generate_report(date, input_stats, output_stats, analysis, errors)
    
    # Сохраняем отчет
    report_path = Path(f"CLASSIFICATION_REPORT_{date}.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    
    print(f"\n✅ Отчет сохранен: {report_path}")
    print("=" * 80)

def generate_report(date: str, input_stats: dict, output_stats: dict, analysis: dict, errors: list) -> str:
    """Генерирует подробный отчет."""
    report = []
    report.append("# Отчет о классификации UNIT")
    report.append(f"\n**Дата**: {date}")
    report.append(f"**Время генерации**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. Входные данные
    report.append("\n## 1. Входные данные")
    report.append(f"\n### Общая статистика")
    report.append(f"- **Всего UNIT**: {input_stats['total_units']}")
    report.append(f"- **Пустых UNIT**: {input_stats['empty_units']} ({input_stats['empty_units']*100//input_stats['total_units'] if input_stats['total_units'] > 0 else 0}%)")
    report.append(f"- **UNIT с файлами**: {input_stats['units_with_files']} ({input_stats['units_with_files']*100//input_stats['total_units'] if input_stats['total_units'] > 0 else 0}%)")
    
    report.append(f"\n### Расширения файлов на входе (топ-20)")
    report.append("| Расширение | Количество файлов | Количество UNIT |")
    report.append("|------------|-------------------|----------------|")
    for ext, count in input_stats['file_extensions'].most_common(20):
        units_count = len(set(input_stats['units_by_extension'][ext]))
        report.append(f"| .{ext} | {count} | {units_count} |")
    
    # 2. Выходные данные
    report.append("\n## 2. Выходные данные")
    report.append(f"\n### Общая статистика")
    report.append(f"- **Всего классифицировано**: {analysis['total_classified']}")
    report.append(f"- **Пустых UNIT**: {analysis['empty_units']} ({analysis['empty_units']*100//analysis['total_classified'] if analysis['total_classified'] > 0 else 0}%)")
    report.append(f"- **UNIT с файлами**: {analysis['units_with_files']} ({analysis['units_with_files']*100//analysis['total_classified'] if analysis['total_classified'] > 0 else 0}%)")
    
    report.append(f"\n### Распределение по категориям")
    report.append("| Категория | Количество UNIT | Процент |")
    report.append("|-----------|-----------------|---------|")
    total_categorized = sum(analysis['by_category'].values())
    for category, count in analysis['by_category'].most_common():
        percentage = count * 100 // total_categorized if total_categorized > 0 else 0
        report.append(f"| {category} | {count} | {percentage}% |")
    
    report.append(f"\n### Распределение по категориям (без учета пустых UNIT)")
    report.append("| Категория | Количество UNIT | Процент |")
    report.append("|-----------|-----------------|---------|")
    total_with_files = analysis['units_with_files']
    for category, count in analysis['by_category'].most_common():
        # Приблизительная оценка (без учета пустых)
        percentage = count * 100 // total_with_files if total_with_files > 0 else 0
        report.append(f"| {category} | {count} | {percentage}% |")
    
    report.append(f"\n### Распределение по локациям")
    report.append("| Локация | Количество UNIT |")
    report.append("|---------|------------------|")
    for location, count in sorted(output_stats['by_location'].items()):
        report.append(f"| {location} | {count} |")
    
    # 3. Анализ по форматам
    report.append("\n## 3. Анализ по форматам")
    
    report.append(f"\n### Расширения файлов на выходе (топ-20)")
    report.append("| Расширение | Количество файлов |")
    report.append("|------------|-------------------|")
    for ext, count in analysis['file_extensions_output'].most_common(20):
        report.append(f"| .{ext} | {count} |")
    
    # 4. Ошибки
    if errors:
        report.append("\n## 4. Ошибки классификации")
        report.append(f"\nВсего ошибок: {len(errors)}")
        report.append("\n| UNIT | Ошибка |")
        report.append("|------|--------|")
        for error in errors[:20]:
            report.append(f"| {error['unit']} | {error['error'][:100]} |")
    
    # 5. Анализ unknown UNIT
    report.append("\n## 5. Анализ unknown UNIT")
    unknown_count = analysis['by_category'].get('unknown', 0)
    unknown_empty = analysis['empty_units_by_category'].get('unknown', 0)
    unknown_with_files = analysis['units_with_files_by_category'].get('unknown', 0)
    
    report.append(f"\n- **Всего unknown UNIT**: {unknown_count}")
    report.append(f"  - Пустых: {unknown_empty}")
    report.append(f"  - С файлами: {unknown_with_files}")
    report.append(f"- **Процент от общего**: {unknown_count*100//analysis['total_classified'] if analysis['total_classified'] > 0 else 0}%")
    report.append(f"- **Процент от UNIT с файлами**: {unknown_with_files*100//analysis['units_with_files'] if analysis['units_with_files'] > 0 else 0}%")
    report.append(f"\n**Вывод**: Из {unknown_count} unknown UNIT, {unknown_empty} - это пустые UNIT ({unknown_empty*100//unknown_count if unknown_count > 0 else 0}%), которые не могут быть классифицированы.")
    
    # 6. Детальная статистика по категориям и расширениям
    report.append("\n## 6. Детальная статистика по категориям и расширениям")
    
    for category in sorted(analysis['category_by_extension'].keys()):
        report.append(f"\n### {category.upper()}")
        report.append("| Расширение | Количество UNIT |")
        report.append("|-----------|-----------------|")
        for ext, count in analysis['category_by_extension'][category].most_common(20):
            report.append(f"| .{ext} | {count} |")
    
    # 7. Статистика по локациям
    report.append("\n## 7. Распределение по локациям")
    report.append("| Категория | Локация | Количество UNIT |")
    report.append("|-----------|---------|------------------|")
    for category in sorted(analysis['category_by_location'].keys()):
        for location, count in sorted(analysis['category_by_location'][category].items()):
            report.append(f"| {category} | {location} | {count} |")
    
    # 8. Сравнение входных и выходных расширений
    report.append("\n## 8. Сравнение входных и выходных расширений")
    report.append("\n### Топ-20 расширений на входе")
    report.append("| Расширение | Количество файлов |")
    report.append("|------------|-------------------|")
    for ext, count in input_stats['file_extensions'].most_common(20):
        report.append(f"| .{ext} | {count} |")
    
    report.append("\n### Топ-20 расширений на выходе")
    report.append("| Расширение | Количество файлов |")
    report.append("|------------|-------------------|")
    for ext, count in analysis['file_extensions_output'].most_common(20):
        report.append(f"| .{ext} | {count} |")
    
    return "\n".join(report)

def main():
    """Главная функция."""
    date = "2025-12-20"
    run_full_classification(date)

if __name__ == "__main__":
    main()


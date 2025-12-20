#!/usr/bin/env python3
"""
Полная классификация UNIT с детальной статистикой.
"""
import sys
from pathlib import Path
from collections import defaultdict, Counter
import json
from datetime import datetime

# Добавляем путь к модулю
sys.path.insert(0, str(Path(__file__).parent))

from docprep.engine.classifier import Classifier
from docprep.core.unit_processor import process_directory_units
from docprep.utils.paths import get_unit_files
from docprep.core.manifest import load_manifest

def collect_statistics(date: str):
    """Собирает статистику по всем UNIT."""
    print("=" * 80)
    print("СБОР СТАТИСТИКИ ПО UNIT")
    print("=" * 80)
    
    base_dir = Path(f"Data/{date}")
    stats = {
        "input": {
            "total_units": 0,
            "empty_units": 0,
            "units_with_files": 0,
            "file_extensions": Counter(),
            "file_types": Counter(),
        },
        "output": {
            "by_category": defaultdict(int),
            "by_subcategory": defaultdict(int),
            "by_extension": defaultdict(int),
            "by_route": defaultdict(int),
        },
        "processing": {
            "direct": defaultdict(int),
            "convert": defaultdict(int),
            "extract": defaultdict(int),
            "normalize": defaultdict(int),
            "special": defaultdict(int),
            "mixed": defaultdict(int),
            "unknown": defaultdict(int),
        },
        "errors": [],
    }
    
    # 1. Анализ Input
    print("\n1. Анализ Input...")
    # Проверяем оба варианта (Input и input)
    input_dir = base_dir / "Input"
    if not input_dir.exists():
        input_dir = base_dir / "input"
    if input_dir.exists():
        units = [d for d in input_dir.iterdir() if d.is_dir() and d.name.startswith("UNIT_")]
        stats["input"]["total_units"] = len(units)
        
        for unit_dir in units:
            files = get_unit_files(unit_dir)
            if not files:
                stats["input"]["empty_units"] += 1
            else:
                stats["input"]["units_with_files"] += 1
                for file_path in files:
                    ext = file_path.suffix.lower().lstrip(".")
                    stats["input"]["file_extensions"][ext] += 1
    
    # 2. Анализ Output
    print("\n2. Анализ Output...")
    
    # Processing
    processing_dir = base_dir / "Processing" / "Processing_1"
    if processing_dir.exists():
        for category in ["Convert", "Extract", "Normalize"]:
            cat_dir = processing_dir / category
            if cat_dir.exists():
                for ext_dir in cat_dir.iterdir():
                    if ext_dir.is_dir():
                        units = [d for d in ext_dir.iterdir() if d.is_dir() and d.name.startswith("UNIT_")]
                        count = len(units)
                        stats["output"]["by_category"][category.lower()] += count
                        stats["output"]["by_extension"][f"{category.lower()}/{ext_dir.name}"] += count
                        stats["processing"][category.lower()][ext_dir.name] += count
    
    # Merge
    merge_dir = base_dir / "Merge" / "Merge_0"
    if merge_dir.exists():
        direct_dir = merge_dir / "Direct"
        if direct_dir.exists():
            for ext_dir in direct_dir.iterdir():
                if ext_dir.is_dir():
                    units = [d for d in ext_dir.iterdir() if d.is_dir() and d.name.startswith("UNIT_")]
                    count = len(units)
                    stats["output"]["by_category"]["direct"] += count
                    stats["output"]["by_extension"][f"direct/{ext_dir.name}"] += count
                    stats["processing"]["direct"][ext_dir.name] += count
    
    # Exceptions
    exceptions_dir = base_dir / "Exceptions" / "Exceptions_1"
    if exceptions_dir.exists():
        for subcat_dir in exceptions_dir.iterdir():
            if subcat_dir.is_dir():
                units = [d for d in subcat_dir.iterdir() if d.is_dir() and d.name.startswith("UNIT_")]
                count = len(units)
                subcat = subcat_dir.name
                stats["output"]["by_category"]["exceptions"] += count
                stats["output"]["by_subcategory"][subcat] += count
                
                # Определяем категорию по subcategory
                if subcat == "Ambiguous":
                    stats["processing"]["unknown"][subcat] += count
                elif subcat == "Mixed":
                    stats["processing"]["mixed"][subcat] += count
                elif subcat == "Special":
                    stats["processing"]["special"][subcat] += count
    
    # 3. Детальный анализ manifest
    print("\n3. Детальный анализ manifest...")
    
    all_units = []
    
    # Собираем все UNIT из всех директорий
    for root_dir in [processing_dir, merge_dir, exceptions_dir]:
        if not root_dir.exists():
            continue
        for unit_dir in root_dir.rglob("UNIT_*"):
            if unit_dir.is_dir():
                all_units.append(unit_dir)
    
    # Анализируем manifest
    for unit_dir in all_units:
        manifest_path = unit_dir / "manifest.json"
        if not manifest_path.exists():
            continue
        
        try:
            manifest = load_manifest(unit_dir)
            route = manifest.get("processing", {}).get("route")
            if route:
                stats["output"]["by_route"][route] += 1
            
            # Анализируем файлы
            files = manifest.get("files", [])
            for file_info in files:
                original_name = file_info.get("original_name", "")
                if original_name:
                    ext = Path(original_name).suffix.lower().lstrip(".")
                    if ext:
                        stats["output"]["by_extension"][f"manifest/{ext}"] += 1
        except Exception as e:
            stats["errors"].append({"unit": unit_dir.name, "error": str(e)})
    
    return stats

def analyze_unknown_units(date: str):
    """Анализирует unknown UNIT."""
    print("\n" + "=" * 80)
    print("АНАЛИЗ UNKNOWN UNIT")
    print("=" * 80)
    
    base_dir = Path(f"Data/{date}")
    ambiguous_dir = base_dir / "Exceptions" / "Exceptions_1" / "Ambiguous"
    
    if not ambiguous_dir.exists():
        print("Директория Ambiguous не найдена")
        return {}
    
    units = [d for d in ambiguous_dir.iterdir() if d.is_dir() and d.name.startswith("UNIT_")]
    
    analysis = {
        "total": len(units),
        "empty": 0,
        "with_files": 0,
        "file_extensions": Counter(),
        "file_types": Counter(),
        "reasons": Counter(),
    }
    
    for unit_dir in units:
        files = get_unit_files(unit_dir)
        if not files:
            analysis["empty"] += 1
            analysis["reasons"]["empty_unit"] += 1
        else:
            analysis["with_files"] += 1
            for file_path in files:
                ext = file_path.suffix.lower().lstrip(".")
                analysis["file_extensions"][ext] += 1
        
        # Проверяем manifest
        manifest_path = unit_dir / "manifest.json"
        if manifest_path.exists():
            try:
                manifest = load_manifest(unit_dir)
                error = manifest.get("files", [{}])[0].get("error") if manifest.get("files") else None
                if error:
                    analysis["reasons"][error] += 1
            except:
                pass
    
    return analysis

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
        return
    
    units = [d for d in input_dir.iterdir() if d.is_dir() and d.name.startswith("UNIT_")]
    print(f"\nНайдено UNIT в Input: {len(units)}")
    
    classifier = Classifier()
    processed = 0
    errors = []
    
    for i, unit_path in enumerate(units, 1):
        try:
            result = classifier.classify_unit(
                unit_path,
                cycle=1,
                protocol_date=date,
                dry_run=False,
                copy_mode=False,  # Перемещаем, так как это финальная обработка
            )
            processed += 1
            if i % 50 == 0:
                print(f"  Обработано: {i}/{len(units)}")
        except Exception as e:
            errors.append({"unit": unit_path.name, "error": str(e)})
            print(f"  ❌ {unit_path.name}: {e}")
    
    print(f"\n✅ Обработано: {processed}")
    if errors:
        print(f"❌ Ошибок: {len(errors)}")
    
    return processed, errors

def generate_report(stats: dict, unknown_analysis: dict, date: str):
    """Генерирует подробный отчет."""
    report = []
    report.append("=" * 80)
    report.append("ПОЛНЫЙ ОТЧЕТ ПО КЛАССИФИКАЦИИ UNIT")
    report.append("=" * 80)
    report.append(f"Дата: {date}")
    report.append(f"Время генерации: {datetime.now().isoformat()}")
    report.append("")
    
    # 1. Статистика Input
    report.append("=" * 80)
    report.append("1. СТАТИСТИКА INPUT")
    report.append("=" * 80)
    report.append(f"Всего UNIT: {stats['input']['total_units']}")
    report.append(f"Пустых UNIT: {stats['input']['empty_units']}")
    report.append(f"UNIT с файлами: {stats['input']['units_with_files']}")
    report.append("")
    
    report.append("Расширения файлов (Input):")
    for ext, count in stats['input']['file_extensions'].most_common():
        report.append(f"  .{ext}: {count}")
    report.append("")
    
    # 2. Статистика Output
    report.append("=" * 80)
    report.append("2. СТАТИСТИКА OUTPUT")
    report.append("=" * 80)
    
    report.append("\nПо категориям:")
    for cat, count in sorted(stats['output']['by_category'].items()):
        report.append(f"  {cat}: {count}")
    report.append("")
    
    report.append("По подкатегориям (Exceptions):")
    for subcat, count in sorted(stats['output']['by_subcategory'].items()):
        report.append(f"  {subcat}: {count}")
    report.append("")
    
    # 3. Детальная статистика по обработке
    report.append("=" * 80)
    report.append("3. ДЕТАЛЬНАЯ СТАТИСТИКА ПО ОБРАБОТКЕ")
    report.append("=" * 80)
    
    for category in ["direct", "convert", "extract", "normalize", "special", "mixed", "unknown"]:
        if stats['processing'][category]:
            report.append(f"\n{category.upper()}:")
            total = sum(stats['processing'][category].values())
            report.append(f"  Всего: {total}")
            for ext, count in sorted(stats['processing'][category].items()):
                report.append(f"    {ext}: {count}")
    
    # 4. Статистика по расширениям
    report.append("\n" + "=" * 80)
    report.append("4. СТАТИСТИКА ПО РАСШИРЕНИЯМ (OUTPUT)")
    report.append("=" * 80)
    for ext_path, count in sorted(stats['output']['by_extension'].items()):
        report.append(f"  {ext_path}: {count}")
    
    # 5. Анализ Unknown
    report.append("\n" + "=" * 80)
    report.append("5. АНАЛИЗ UNKNOWN UNIT")
    report.append("=" * 80)
    report.append(f"Всего Unknown: {unknown_analysis.get('total', 0)}")
    report.append(f"Пустых: {unknown_analysis.get('empty', 0)}")
    report.append(f"С файлами: {unknown_analysis.get('with_files', 0)}")
    report.append("")
    
    if unknown_analysis.get('file_extensions'):
        report.append("Расширения файлов в Unknown:")
        for ext, count in unknown_analysis['file_extensions'].most_common():
            report.append(f"  .{ext}: {count}")
        report.append("")
    
    if unknown_analysis.get('reasons'):
        report.append("Причины попадания в Unknown:")
        for reason, count in unknown_analysis['reasons'].most_common():
            report.append(f"  {reason}: {count}")
        report.append("")
    
    # 6. Статистика без пустых UNIT
    report.append("=" * 80)
    report.append("6. СТАТИСТИКА БЕЗ УЧЕТА ПУСТЫХ UNIT")
    report.append("=" * 80)
    
    empty_count = stats['input']['empty_units']
    total_with_files = stats['input']['units_with_files']
    
    report.append(f"Всего UNIT с файлами: {total_with_files}")
    report.append(f"Пустых UNIT (исключено): {empty_count}")
    report.append("")
    
    # Пересчитываем статистику без пустых
    for category in ["direct", "convert", "extract", "normalize", "special", "mixed"]:
        if stats['processing'][category]:
            total = sum(stats['processing'][category].values())
            report.append(f"{category.upper()}: {total}")
    
    # 7. Ошибки
    if stats['errors']:
        report.append("\n" + "=" * 80)
        report.append("7. ОШИБКИ")
        report.append("=" * 80)
        for error in stats['errors'][:10]:
            report.append(f"  {error['unit']}: {error['error']}")
        if len(stats['errors']) > 10:
            report.append(f"  ... и еще {len(stats['errors']) - 10}")
    
    report.append("\n" + "=" * 80)
    report.append("КОНЕЦ ОТЧЕТА")
    report.append("=" * 80)
    
    return "\n".join(report)

def main():
    """Главная функция."""
    date = "2025-12-20"
    
    # 1. Запускаем классификацию
    print("\n" + "=" * 80)
    print("ШАГ 1: КЛАССИФИКАЦИЯ")
    print("=" * 80)
    processed, errors = run_classification(date)
    
    # 2. Собираем статистику
    print("\n" + "=" * 80)
    print("ШАГ 2: СБОР СТАТИСТИКИ")
    print("=" * 80)
    stats = collect_statistics(date)
    
    # 3. Анализируем Unknown
    print("\n" + "=" * 80)
    print("ШАГ 3: АНАЛИЗ UNKNOWN")
    print("=" * 80)
    unknown_analysis = analyze_unknown_units(date)
    
    # 4. Генерируем отчет
    print("\n" + "=" * 80)
    print("ШАГ 4: ГЕНЕРАЦИЯ ОТЧЕТА")
    print("=" * 80)
    report = generate_report(stats, unknown_analysis, date)
    
    # 5. Сохраняем отчет
    report_path = Path(f"CLASSIFICATION_REPORT_{date}.md")
    report_path.write_text(report, encoding="utf-8")
    print(f"\n✅ Отчет сохранен: {report_path}")
    
    # 6. Выводим краткую сводку
    print("\n" + "=" * 80)
    print("КРАТКАЯ СВОДКА")
    print("=" * 80)
    print(f"Обработано UNIT: {processed}")
    print(f"Всего UNIT в Input: {stats['input']['total_units']}")
    print(f"Пустых UNIT: {stats['input']['empty_units']}")
    print(f"UNIT с файлами: {stats['input']['units_with_files']}")
    print(f"Unknown UNIT: {unknown_analysis.get('total', 0)}")
    print(f"  - Пустых: {unknown_analysis.get('empty', 0)}")
    print(f"  - С файлами: {unknown_analysis.get('with_files', 0)}")
    
    print("\n" + "=" * 80)
    print("✅ ВСЕ ЗАВЕРШЕНО")
    print("=" * 80)

if __name__ == "__main__":
    main()


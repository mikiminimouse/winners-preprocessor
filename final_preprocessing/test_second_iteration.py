#!/usr/bin/env python3
"""
Тестирование второй итерации обработки.
"""
import sys
from pathlib import Path
from collections import Counter
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from docprep.engine.converter import Converter
from docprep.engine.extractor import Extractor
from docprep.engine.normalizers.name import NameNormalizer
from docprep.engine.normalizers.extension import ExtensionNormalizer
from docprep.engine.classifier import Classifier
from docprep.utils.statistics import (
    analyze_output_statistics,
    calculate_percentage_statistics,
    generate_statistics_report,
    collect_input_statistics,
)

def process_second_iteration(date: str):
    """Обрабатывает UNIT из Processing_1 и запускает повторную классификацию."""
    print("=" * 80)
    print("ТЕСТИРОВАНИЕ ВТОРОЙ ИТЕРАЦИИ ОБРАБОТКИ")
    print("=" * 80)
    print(f"Дата: {date}")
    print()
    
    base_dir = Path(f"Data/{date}")
    processing_1_dir = base_dir / "Processing" / "Processing_1"
    
    # Статистика до обработки
    print("1. СТАТИСТИКА ДО ОБРАБОТКИ")
    print("-" * 80)
    before_stats = {
        "convert": len(list((processing_1_dir / "Convert").rglob("UNIT_*"))) if (processing_1_dir / "Convert").exists() else 0,
        "extract": len(list((processing_1_dir / "Extract").rglob("UNIT_*"))) if (processing_1_dir / "Extract").exists() else 0,
        "normalize": len(list((processing_1_dir / "Normalize").rglob("UNIT_*"))) if (processing_1_dir / "Normalize").exists() else 0,
    }
    print(f"  Convert UNIT: {before_stats['convert']}")
    print(f"  Extract UNIT: {before_stats['extract']}")
    print(f"  Normalize UNIT: {before_stats['normalize']}")
    print()
    
    # 2. Обработка через Converter
    print("2. ОБРАБОТКА ЧЕРЕЗ CONVERTER")
    print("-" * 80)
    converter = Converter()
    convert_dir = processing_1_dir / "Convert"
    convert_processed = 0
    convert_errors = []
    
    if convert_dir.exists():
        for category_dir in convert_dir.iterdir():
            if not category_dir.is_dir():
                continue
            for unit_dir in category_dir.iterdir():
                if not unit_dir.is_dir() or not unit_dir.name.startswith("UNIT_"):
                    continue
                try:
                    result = converter.convert_unit(
                        unit_path=unit_dir,
                        cycle=1,
                        protocol_date=date,
                        dry_run=False,
                    )
                    convert_processed += 1
                    if convert_processed % 20 == 0:
                        print(f"  Обработано: {convert_processed}")
                except Exception as e:
                    convert_errors.append({"unit": unit_dir.name, "error": str(e)})
                    print(f"  ❌ {unit_dir.name}: {e}")
    
    print(f"  ✅ Обработано: {convert_processed}/{before_stats['convert']}")
    if convert_errors:
        print(f"  ❌ Ошибок: {len(convert_errors)}")
    print()
    
    # 3. Обработка через Extractor
    print("3. ОБРАБОТКА ЧЕРЕЗ EXTRACTOR")
    print("-" * 80)
    extractor = Extractor()
    extract_dir = processing_1_dir / "Extract"
    extract_processed = 0
    extract_errors = []
    
    if extract_dir.exists():
        for category_dir in extract_dir.iterdir():
            if not category_dir.is_dir():
                continue
            for unit_dir in category_dir.iterdir():
                if not unit_dir.is_dir() or not unit_dir.name.startswith("UNIT_"):
                    continue
                try:
                    result = extractor.extract_unit(
                        unit_path=unit_dir,
                        cycle=1,
                        protocol_date=date,
                        dry_run=False,
                    )
                    extract_processed += 1
                    if extract_processed % 20 == 0:
                        print(f"  Обработано: {extract_processed}")
                except Exception as e:
                    extract_errors.append({"unit": unit_dir.name, "error": str(e)})
                    print(f"  ❌ {unit_dir.name}: {e}")
    
    print(f"  ✅ Обработано: {extract_processed}/{before_stats['extract']}")
    if extract_errors:
        print(f"  ❌ Ошибок: {len(extract_errors)}")
    print()
    
    # 4. Обработка через Normalizers
    print("4. ОБРАБОТКА ЧЕРЕЗ NORMALIZERS")
    print("-" * 80)
    name_normalizer = NameNormalizer()
    extension_normalizer = ExtensionNormalizer()
    normalize_dir = processing_1_dir / "Normalize"
    normalize_processed = 0
    normalize_errors = []
    
    if normalize_dir.exists():
        for category_dir in normalize_dir.iterdir():
            if not category_dir.is_dir():
                continue
            for unit_dir in category_dir.iterdir():
                if not unit_dir.is_dir() or not unit_dir.name.startswith("UNIT_"):
                    continue
                try:
                    # Нормализация имен
                    name_normalizer.normalize_names(
                        unit_path=unit_dir,
                        cycle=1,
                        protocol_date=date,
                        dry_run=False,
                    )
                    # Нормализация расширений
                    extension_normalizer.normalize_extensions(
                        unit_path=unit_dir,
                        cycle=1,
                        protocol_date=date,
                        dry_run=False,
                    )
                    normalize_processed += 1
                    if normalize_processed % 10 == 0:
                        print(f"  Обработано: {normalize_processed}")
                except Exception as e:
                    normalize_errors.append({"unit": unit_dir.name, "error": str(e)})
                    print(f"  ❌ {unit_dir.name}: {e}")
    
    print(f"  ✅ Обработано: {normalize_processed}/{before_stats['normalize']}")
    if normalize_errors:
        print(f"  ❌ Ошибок: {len(normalize_errors)}")
    print()
    
    # 5. Повторная классификация
    print("5. ПОВТОРНАЯ КЛАССИФИКАЦИЯ (ЦИКЛ 2)")
    print("-" * 80)
    classifier = Classifier()
    
    # Классифицируем UNIT из Merge_1
    merge_1_dir = base_dir / "Merge" / "Merge_1"
    classify_processed = 0
    classify_errors = []
    
    merge_dirs = []
    if merge_1_dir.exists():
        for subdir in ["Converted", "Extracted", "Normalized"]:
            subdir_path = merge_1_dir / subdir
            if subdir_path.exists():
                merge_dirs.append(subdir_path)
    
    for merge_subdir in merge_dirs:
        for ext_dir in merge_subdir.iterdir():
            if not ext_dir.is_dir():
                continue
            for unit_dir in ext_dir.iterdir():
                if not unit_dir.is_dir() or not unit_dir.name.startswith("UNIT_"):
                    continue
                try:
                    result = classifier.classify_unit(
                        unit_path=unit_dir,
                        cycle=2,
                        protocol_date=date,
                        dry_run=False,
                        copy_mode=False,  # Перемещаем, так как это финальная обработка
                    )
                    classify_processed += 1
                    if classify_processed % 50 == 0:
                        print(f"  Обработано: {classify_processed}")
                except Exception as e:
                    classify_errors.append({"unit": unit_dir.name, "error": str(e)})
                    print(f"  ❌ {unit_dir.name}: {e}")
    
    print(f"  ✅ Классифицировано: {classify_processed}")
    if classify_errors:
        print(f"  ❌ Ошибок: {len(classify_errors)}")
    print()
    
    # 6. Сбор статистики
    print("6. СБОР СТАТИСТИКИ")
    print("-" * 80)
    output_stats = analyze_output_statistics(date)
    
    # Статистика после обработки
    after_stats = {
        "processing_2": len(list((base_dir / "Processing" / "Processing_2").rglob("UNIT_*"))) if (base_dir / "Processing" / "Processing_2").exists() else 0,
        "merge_1": len(list((base_dir / "Merge" / "Merge_1").rglob("UNIT_*"))) if (base_dir / "Merge" / "Merge_1").exists() else 0,
        "exceptions_2": len(list((base_dir / "Exceptions" / "Exceptions_2").rglob("UNIT_*"))) if (base_dir / "Exceptions" / "Exceptions_2").exists() else 0,
    }
    
    print(f"  Processing_2 UNIT: {after_stats['processing_2']}")
    print(f"  Merge_1 UNIT: {after_stats['merge_1']}")
    print(f"  Exceptions_2 UNIT: {after_stats['exceptions_2']}")
    print()
    
    # 7. Генерация отчета
    print("7. ГЕНЕРАЦИЯ ОТЧЕТА")
    print("-" * 80)
    
    # Собираем входную статистику (если нужно)
    input_dir = base_dir / "Input"
    if not input_dir.exists():
        input_dir = base_dir / "input"
    if input_dir.exists():
        input_stats = collect_input_statistics(input_dir)
    else:
        input_stats = {
            "total_units": 0,
            "empty_units": 0,
            "units_with_files": 0,
            "file_extensions": Counter(),
        }
    
    percentages = calculate_percentage_statistics(input_stats, output_stats)
    report = generate_statistics_report(date, input_stats, output_stats, percentages)
    
    # Сохраняем отчет
    report_path = Path(f"SECOND_ITERATION_REPORT_{date}.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    
    # Дополнительный отчет по второй итерации
    detailed_report = []
    detailed_report.append("# ОТЧЕТ О ВТОРОЙ ИТЕРАЦИИ ОБРАБОТКИ")
    detailed_report.append(f"\n**Дата**: {date}")
    detailed_report.append(f"**Время генерации**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    detailed_report.append("")
    
    detailed_report.append("## 1. ОБРАБОТКА UNIT")
    detailed_report.append("")
    detailed_report.append("### Converter")
    detailed_report.append(f"- Обработано: {convert_processed}/{before_stats['convert']}")
    if convert_errors:
        detailed_report.append(f"- Ошибок: {len(convert_errors)}")
        for error in convert_errors[:10]:
            detailed_report.append(f"  - {error['unit']}: {error['error'][:100]}")
    
    detailed_report.append("")
    detailed_report.append("### Extractor")
    detailed_report.append(f"- Обработано: {extract_processed}/{before_stats['extract']}")
    if extract_errors:
        detailed_report.append(f"- Ошибок: {len(extract_errors)}")
        for error in extract_errors[:10]:
            detailed_report.append(f"  - {error['unit']}: {error['error'][:100]}")
    
    detailed_report.append("")
    detailed_report.append("### Normalizers")
    detailed_report.append(f"- Обработано: {normalize_processed}/{before_stats['normalize']}")
    if normalize_errors:
        detailed_report.append(f"- Ошибок: {len(normalize_errors)}")
        for error in normalize_errors[:10]:
            detailed_report.append(f"  - {error['unit']}: {error['error'][:100]}")
    
    detailed_report.append("")
    detailed_report.append("## 2. ПОВТОРНАЯ КЛАССИФИКАЦИЯ")
    detailed_report.append(f"- Классифицировано UNIT: {classify_processed}")
    if classify_errors:
        detailed_report.append(f"- Ошибок: {len(classify_errors)}")
    
    detailed_report.append("")
    detailed_report.append("## 3. РАСПРЕДЕЛЕНИЕ ПОСЛЕ ВТОРОЙ ИТЕРАЦИИ")
    detailed_report.append(f"- Processing_2: {after_stats['processing_2']} UNIT")
    detailed_report.append(f"- Merge_1: {after_stats['merge_1']} UNIT")
    detailed_report.append(f"- Exceptions_2: {after_stats['exceptions_2']} UNIT")
    
    detailed_report.append("")
    detailed_report.append("## 4. СТАТИСТИКА")
    detailed_report.append("")
    detailed_report.append("```")
    detailed_report.append(report)
    detailed_report.append("```")
    
    detailed_report_path = Path(f"SECOND_ITERATION_DETAILED_REPORT_{date}.md")
    with open(detailed_report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(detailed_report))
    
    print(f"  ✅ Отчет сохранен: {report_path}")
    print(f"  ✅ Детальный отчет сохранен: {detailed_report_path}")
    print()
    
    print("=" * 80)
    print("✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("=" * 80)
    
    return {
        "convert": {"processed": convert_processed, "errors": convert_errors},
        "extract": {"processed": extract_processed, "errors": extract_errors},
        "normalize": {"processed": normalize_processed, "errors": normalize_errors},
        "classify": {"processed": classify_processed, "errors": classify_errors},
        "after_stats": after_stats,
    }

if __name__ == "__main__":
    date = "2025-12-20"
    results = process_second_iteration(date)
    print("\nРезультаты:")
    print(f"  Converter: {results['convert']['processed']} обработано")
    print(f"  Extractor: {results['extract']['processed']} обработано")
    print(f"  Normalizers: {results['normalize']['processed']} обработано")
    print(f"  Classifier: {results['classify']['processed']} классифицировано")


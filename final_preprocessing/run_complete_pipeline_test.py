#!/usr/bin/env python3
"""
Полный цикл тестирования всех итераций от Input до Ready2Docling.
Включает все итерации с классификацией, обработкой и финальным merge.
"""
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter

sys.path.insert(0, str(Path(__file__).parent))

from docprep.engine.classifier import Classifier
from docprep.engine.converter import Converter
from docprep.engine.extractor import Extractor
from docprep.engine.normalizers.extension import ExtensionNormalizer
from docprep.engine.merger import Merger
from docprep.core.config import init_directory_structure, get_data_paths
from docprep.utils.paths import get_unit_files
from docprep.core.manifest import load_manifest

def collect_metrics(date: str, iteration: int):
    """Собирает метрики для итерации."""
    base_dir = Path("Data") / date
    metrics = {
        "iteration": iteration,
        "processing": defaultdict(int),
        "merge": defaultdict(lambda: defaultdict(int)),
        "exceptions": defaultdict(int),
        "ready2docling": 0,
    }
    
    # Processing
    processing_dir = base_dir / "Processing" / f"Processing_{iteration}"
    if processing_dir.exists():
        for category in ["Convert", "Extract", "Normalize"]:
            category_dir = processing_dir / category
            if category_dir.exists():
                count = len(list(category_dir.rglob("UNIT_*")))
                if count > 0:
                    metrics["processing"][category] = count
    
    # Merge
    merge_dir = base_dir / "Merge"
    if merge_dir.exists():
        for merge_num in range(4):
            merge_cycle_dir = merge_dir / f"Merge_{merge_num}"
            if merge_cycle_dir.exists():
                for subdir in ["Direct", "Converted", "Extracted", "Normalized"]:
                    subdir_path = merge_cycle_dir / subdir
                    if subdir_path.exists():
                        count = len(list(subdir_path.rglob("UNIT_*")))
                        if count > 0:
                            metrics["merge"][merge_num][subdir] = count
    
    # Exceptions
    exceptions_dir = base_dir / "Exceptions"
    if exceptions_dir.exists():
        for exc_num in range(1, 4):
            exc_cycle_dir = exceptions_dir / f"Exceptions_{exc_num}"
            if exc_cycle_dir.exists():
                count = len(list(exc_cycle_dir.rglob("UNIT_*")))
                if count > 0:
                    metrics["exceptions"][exc_num] = count
    
    # Ready2Docling
    ready_dir = base_dir / "Ready2Docling"
    if ready_dir.exists():
        metrics["ready2docling"] = len(list(ready_dir.rglob("UNIT_*")))
    
    return metrics

def process_iteration(date: str, iteration: int):
    """Обрабатывает одну итерацию."""
    print(f"\n{'=' * 80}")
    print(f"ИТЕРАЦИЯ {iteration}")
    print("=" * 80)
    
    base_dir = Path("Data") / date
    
    # 1. Классификация
    print(f"\n{iteration}.1. КЛАССИФИКАЦИЯ (ЦИКЛ {iteration})")
    print("-" * 80)
    
    classifier = Classifier()
    classified = 0
    errors = []
    
    # Определяем источник UNIT для классификации
    if iteration == 1:
        # Первая итерация - из Input
        source_dir = base_dir / "Input"
        units = [d for d in source_dir.iterdir() if d.is_dir() and d.name.startswith("UNIT_")]
        copy_mode = True
    else:
        # Последующие итерации - из Merge_{iteration-1}
        source_dir = base_dir / "Merge" / f"Merge_{iteration-1}"
        units = []
        for subdir in ["Converted", "Extracted", "Normalized"]:
            subdir_path = source_dir / subdir
            if subdir_path.exists():
                units.extend(list(subdir_path.rglob("UNIT_*")))
        copy_mode = False
    
    units = [u for u in units if u.is_dir()]
    print(f"Найдено UNIT для классификации: {len(units)}")
    
    for i, unit_dir in enumerate(units, 1):
        try:
            result = classifier.classify_unit(
                unit_path=unit_dir,
                cycle=iteration,
                protocol_date=date,
                dry_run=False,
                copy_mode=copy_mode,
            )
            classified += 1
            if i % 100 == 0:
                print(f"  Классифицировано: {i}/{len(units)}")
        except Exception as e:
            errors.append({"unit": unit_dir.name, "error": str(e)})
            if len(errors) <= 10:
                print(f"  ❌ {unit_dir.name}: {e}")
    
    print(f"✅ Классифицировано: {classified}/{len(units)}")
    if errors:
        print(f"❌ Ошибок: {len(errors)}")
    
    # 2. Обработка
    print(f"\n{iteration}.2. ОБРАБОТКА")
    print("-" * 80)
    
    processing_dir = base_dir / "Processing" / f"Processing_{iteration}"
    converter = Converter()
    extractor = Extractor()
    normalizer = ExtensionNormalizer()
    
    # Convert
    convert_dir = processing_dir / "Convert"
    if convert_dir.exists():
        convert_units = list(convert_dir.rglob("UNIT_*"))
        convert_count = len([u for u in convert_units if u.is_dir()])
        print(f"Convert: {convert_count} UNIT")
        
        processed = 0
        for unit_dir in convert_units:
            if not unit_dir.is_dir():
                continue
            try:
                converter.convert_unit(
                    unit_path=unit_dir,
                    cycle=iteration,
                    protocol_date=date,
                    dry_run=False,
                )
                processed += 1
            except Exception as e:
                if processed < 5:
                    print(f"  ❌ {unit_dir.name}: {e}")
        print(f"  ✅ Обработано: {processed}/{convert_count}")
    
    # Extract
    extract_dir = processing_dir / "Extract"
    if extract_dir.exists():
        extract_units = list(extract_dir.rglob("UNIT_*"))
        extract_count = len([u for u in extract_units if u.is_dir()])
        print(f"Extract: {extract_count} UNIT")
        
        processed = 0
        for unit_dir in extract_units:
            if not unit_dir.is_dir():
                continue
            try:
                extractor.extract_unit(
                    unit_path=unit_dir,
                    cycle=iteration,
                    protocol_date=date,
                    dry_run=False,
                )
                processed += 1
            except Exception as e:
                if processed < 5:
                    print(f"  ❌ {unit_dir.name}: {e}")
        print(f"  ✅ Обработано: {processed}/{extract_count}")
    
    # Normalize
    normalize_dir = processing_dir / "Normalize"
    if normalize_dir.exists():
        normalize_units = list(normalize_dir.rglob("UNIT_*"))
        normalize_count = len([u for u in normalize_units if u.is_dir()])
        print(f"Normalize: {normalize_count} UNIT")
        
        processed = 0
        for unit_dir in normalize_units:
            if not unit_dir.is_dir():
                continue
            try:
                normalizer.normalize_unit(
                    unit_path=unit_dir,
                    cycle=iteration,
                    protocol_date=date,
                    dry_run=False,
                )
                processed += 1
            except Exception as e:
                if processed < 5:
                    print(f"  ❌ {unit_dir.name}: {e}")
        print(f"  ✅ Обработано: {processed}/{normalize_count}")
    
    # Собираем метрики
    metrics = collect_metrics(date, iteration)
    return metrics, errors

def final_merge(date: str):
    """Финальный merge всех UNIT из Merge_N в Ready2Docling."""
    print(f"\n{'=' * 80}")
    print("ФИНАЛЬНЫЙ MERGE В READY2DOCLING")
    print("=" * 80)
    
    base_dir = Path("Data") / date
    data_paths = get_data_paths(date)
    target_dir = data_paths.get("ready2docling", base_dir / "Ready2Docling")
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # Собираем все Merge_N директории
    source_dirs = []
    
    # Merge_0/Direct
    merge_0_direct = base_dir / "Merge" / "Merge_0" / "Direct"
    if merge_0_direct.exists():
        source_dirs.append(merge_0_direct)
        print(f"  Добавлен источник: Merge_0/Direct")
    
    # Merge_1, Merge_2, Merge_3
    for merge_num in range(1, 4):
        merge_dir = base_dir / "Merge" / f"Merge_{merge_num}"
        if merge_dir.exists():
            for subdir in ["Converted", "Extracted", "Normalized"]:
                subdir_path = merge_dir / subdir
                if subdir_path.exists():
                    source_dirs.append(subdir_path)
                    print(f"  Добавлен источник: Merge_{merge_num}/{subdir}")
    
    print(f"\nВсего источников: {len(source_dirs)}")
    
    if source_dirs:
        merger = Merger()
        result = merger.collect_units(
            source_dirs=source_dirs,
            target_dir=target_dir,
            cycle=None,
        )
        
        print(f"✅ Обработано UNIT: {result['units_processed']}")
        if result['errors']:
            print(f"❌ Ошибок: {len(result['errors'])}")
            for error in result['errors'][:10]:
                print(f"  {error['unit_id']}: {error['error']}")
        
        return result
    return None

def generate_final_report(date: str, all_metrics: list, merge_result: dict):
    """Генерирует финальный отчет."""
    report = []
    report.append("# ПОЛНЫЙ ОТЧЕТ О ТЕСТИРОВАНИИ ПАЙПЛАЙНА")
    report.append(f"\n**Дата**: {date}")
    report.append(f"**Время генерации**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    report.append("\n## ИТЕРАЦИИ")
    for metrics in all_metrics:
        iteration = metrics["iteration"]
        report.append(f"\n### Итерация {iteration}")
        report.append(f"- Processing_{iteration}:")
        for category, count in metrics["processing"].items():
            report.append(f"  - {category}: {count} UNIT")
        report.append(f"- Merge_{iteration}:")
        for merge_num, subdirs in metrics["merge"].items():
            for subdir, count in subdirs.items():
                report.append(f"  - Merge_{merge_num}/{subdir}: {count} UNIT")
        report.append(f"- Exceptions_{iteration}: {sum(metrics['exceptions'].values())} UNIT")
    
    if merge_result:
        report.append("\n## ФИНАЛЬНЫЙ MERGE")
        report.append(f"- Обработано UNIT: {merge_result['units_processed']}")
        if merge_result['errors']:
            report.append(f"- Ошибок: {len(merge_result['errors'])}")
    
    # Статистика Ready2Docling
    base_dir = Path("Data") / date
    ready_dir = base_dir / "Ready2Docling"
    if ready_dir.exists():
        report.append("\n## READY2DOCLING")
        type_counts = Counter()
        for ext_dir in ready_dir.iterdir():
            if ext_dir.is_dir():
                count = len(list(ext_dir.rglob("UNIT_*")))
                if count > 0:
                    type_counts[ext_dir.name] = count
        
        for file_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
            report.append(f"- {file_type}: {count} UNIT")
    
    return "\n".join(report)

def run_complete_pipeline(date: str):
    """Запускает полный цикл обработки."""
    print("=" * 80)
    print("ПОЛНЫЙ ЦИКЛ ТЕСТИРОВАНИЯ ПАЙПЛАЙНА")
    print("=" * 80)
    print(f"Дата: {date}")
    print()
    
    # Инициализация
    print("ИНИЦИАЛИЗАЦИЯ СТРУКТУРЫ")
    print("-" * 80)
    init_directory_structure(date=date)
    print("✅ Структура создана")
    
    all_metrics = []
    all_errors = []
    
    # Итерация 1
    metrics1, errors1 = process_iteration(date, 1)
    all_metrics.append(metrics1)
    all_errors.extend(errors1)
    
    # Итерация 2
    metrics2, errors2 = process_iteration(date, 2)
    all_metrics.append(metrics2)
    all_errors.extend(errors2)
    
    # Итерация 3
    metrics3, errors3 = process_iteration(date, 3)
    all_metrics.append(metrics3)
    all_errors.extend(errors3)
    
    # Финальный merge
    merge_result = final_merge(date)
    
    # Генерация отчета
    print(f"\n{'=' * 80}")
    print("ГЕНЕРАЦИЯ ОТЧЕТА")
    print("=" * 80)
    
    report = generate_final_report(date, all_metrics, merge_result)
    report_path = Path(f"COMPLETE_PIPELINE_REPORT_{date}.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    
    print(f"✅ Отчет сохранен: {report_path}")
    
    # Финальная статистика
    print(f"\n{'=' * 80}")
    print("ФИНАЛЬНАЯ СТАТИСТИКА")
    print("=" * 80)
    
    base_dir = Path("Data") / date
    stats = {
        "input": len(list((base_dir / "Input").iterdir())) if (base_dir / "Input").exists() else 0,
        "ready2docling": len(list((base_dir / "Ready2Docling").rglob("UNIT_*"))) if (base_dir / "Ready2Docling").exists() else 0,
    }
    
    print(f"Input: {stats['input']} UNIT")
    print(f"Ready2Docling: {stats['ready2docling']} UNIT")
    
    print(f"\n{'=' * 80}")
    print("✅ ПОЛНЫЙ ЦИКЛ ЗАВЕРШЕН")
    print("=" * 80)

if __name__ == "__main__":
    date = "2025-03-19"
    run_complete_pipeline(date)


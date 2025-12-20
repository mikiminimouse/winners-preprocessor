#!/usr/bin/env python3
"""
Полный цикл обработки UNIT от Input до Ready2Docling.
"""
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from docprep.engine.classifier import Classifier
from docprep.engine.converter import Converter
from docprep.engine.extractor import Extractor
from docprep.engine.normalizers.extension import ExtensionNormalizer
from docprep.engine.merger import Merger
from docprep.core.config import init_directory_structure, get_data_paths, READY2DOCLING_DIR

def run_full_pipeline(date: str):
    """Запускает полный цикл обработки для указанной даты."""
    print("=" * 80)
    print("ПОЛНЫЙ ЦИКЛ ОБРАБОТКИ")
    print("=" * 80)
    print(f"Дата: {date}")
    print()
    
    # Инициализируем структуру
    print("1. ИНИЦИАЛИЗАЦИЯ СТРУКТУРЫ")
    print("-" * 80)
    init_directory_structure(date=date)
    print("✅ Структура создана")
    print()
    
    base_dir = Path("Data") / date
    input_dir = base_dir / "Input"
    
    if not input_dir.exists():
        print(f"❌ Input директория не существует: {input_dir}")
        return
    
    # Подсчитываем UNIT
    units = [d for d in input_dir.iterdir() if d.is_dir() and d.name.startswith("UNIT_")]
    print(f"Найдено UNIT в Input: {len(units)}")
    print()
    
    # ЦИКЛ 1: Классификация
    print("2. ЦИКЛ 1: КЛАССИФИКАЦИЯ")
    print("-" * 80)
    classifier = Classifier()
    classified = 0
    errors = []
    
    for unit_dir in units:
        try:
            result = classifier.classify_unit(
                unit_path=unit_dir,
                cycle=1,
                protocol_date=date,
                dry_run=False,
                copy_mode=True,  # Копируем из Input
            )
            classified += 1
            if classified % 100 == 0:
                print(f"  Классифицировано: {classified}/{len(units)}")
        except Exception as e:
            errors.append({"unit": unit_dir.name, "error": str(e)})
            if len(errors) <= 10:
                print(f"  ❌ {unit_dir.name}: {e}")
    
    print(f"✅ Классифицировано: {classified}/{len(units)}")
    if errors:
        print(f"❌ Ошибок: {len(errors)}")
    print()
    
    # ЦИКЛ 1: Обработка
    print("3. ЦИКЛ 1: ОБРАБОТКА")
    print("-" * 80)
    
    processing_1_dir = base_dir / "Processing" / "Processing_1"
    converter = Converter()
    extractor = Extractor()
    normalizer = ExtensionNormalizer()
    
    # Convert
    convert_dir = processing_1_dir / "Convert"
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
                    cycle=1,
                    protocol_date=date,
                    dry_run=False,
                )
                processed += 1
            except Exception as e:
                if processed < 5:
                    print(f"  ❌ {unit_dir.name}: {e}")
        print(f"  ✅ Обработано: {processed}/{convert_count}")
    
    # Extract
    extract_dir = processing_1_dir / "Extract"
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
                    cycle=1,
                    protocol_date=date,
                    dry_run=False,
                )
                processed += 1
            except Exception as e:
                if processed < 5:
                    print(f"  ❌ {unit_dir.name}: {e}")
        print(f"  ✅ Обработано: {processed}/{extract_count}")
    
    # Normalize
    normalize_dir = processing_1_dir / "Normalize"
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
                    cycle=1,
                    protocol_date=date,
                    dry_run=False,
                )
                processed += 1
            except Exception as e:
                if processed < 5:
                    print(f"  ❌ {unit_dir.name}: {e}")
        print(f"  ✅ Обработано: {processed}/{normalize_count}")
    
    print()
    
    # ЦИКЛ 2: Повторная классификация
    print("4. ЦИКЛ 2: ПОВТОРНАЯ КЛАССИФИКАЦИЯ")
    print("-" * 80)
    
    merge_1_dir = base_dir / "Merge" / "Merge_1"
    if merge_1_dir.exists():
        merge_1_units = []
        for subdir in ["Converted", "Extracted", "Normalized"]:
            subdir_path = merge_1_dir / subdir
            if subdir_path.exists():
                merge_1_units.extend(list(subdir_path.rglob("UNIT_*")))
        
        merge_1_count = len([u for u in merge_1_units if u.is_dir()])
        print(f"Найдено UNIT в Merge_1: {merge_1_count}")
        
        if merge_1_count > 0:
            reclassified = 0
            for unit_dir in merge_1_units:
                if not unit_dir.is_dir():
                    continue
                try:
                    classifier.classify_unit(
                        unit_path=unit_dir,
                        cycle=2,
                        protocol_date=date,
                        dry_run=False,
                        copy_mode=False,
                    )
                    reclassified += 1
                except Exception as e:
                    if reclassified < 5:
                        print(f"  ❌ {unit_dir.name}: {e}")
            
            print(f"✅ Классифицировано: {reclassified}/{merge_1_count}")
    
    print()
    
    # ФИНАЛЬНЫЙ MERGE
    print("5. ФИНАЛЬНЫЙ MERGE В READY2DOCLING")
    print("-" * 80)
    
    data_paths = get_data_paths(date)
    target_dir = data_paths.get("ready2docling", base_dir / "Ready2Docling")
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # Собираем все Merge_N директории
    source_dirs = []
    
    # Merge_0/Direct
    merge_0_direct = base_dir / "Merge" / "Merge_0" / "Direct"
    if merge_0_direct.exists():
        source_dirs.append(merge_0_direct)
    
    # Merge_1, Merge_2, Merge_3
    for merge_num in range(1, 4):
        merge_dir = base_dir / "Merge" / f"Merge_{merge_num}"
        if merge_dir.exists():
            for subdir in ["Converted", "Extracted", "Normalized"]:
                subdir_path = merge_dir / subdir
                if subdir_path.exists():
                    source_dirs.append(subdir_path)
    
    print(f"Источников для merge: {len(source_dirs)}")
    
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
    
    print()
    print("=" * 80)
    print("✅ ПОЛНЫЙ ЦИКЛ ЗАВЕРШЕН")
    print("=" * 80)
    
    # Статистика
    print("\nСТАТИСТИКА:")
    print("-" * 80)
    
    stats = {
        "input": len(units),
        "merge_0": len(list((base_dir / "Merge" / "Merge_0" / "Direct").rglob("UNIT_*"))) if (base_dir / "Merge" / "Merge_0" / "Direct").exists() else 0,
        "merge_1": len(list((base_dir / "Merge" / "Merge_1").rglob("UNIT_*"))) if (base_dir / "Merge" / "Merge_1").exists() else 0,
        "processing_2": len(list((base_dir / "Processing" / "Processing_2").rglob("UNIT_*"))) if (base_dir / "Processing" / "Processing_2").exists() else 0,
        "ready2docling": len(list(target_dir.rglob("UNIT_*"))) if target_dir.exists() else 0,
    }
    
    print(f"Input: {stats['input']} UNIT")
    print(f"Merge_0/Direct: {stats['merge_0']} UNIT")
    print(f"Merge_1: {stats['merge_1']} UNIT")
    print(f"Processing_2: {stats['processing_2']} UNIT")
    print(f"Ready2Docling: {stats['ready2docling']} UNIT")

if __name__ == "__main__":
    date = "2025-03-19"
    run_full_pipeline(date)


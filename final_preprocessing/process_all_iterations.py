#!/usr/bin/env python3
"""
Обработка всех итераций для Processing_2, Processing_3 и т.д.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from docprep.engine.classifier import Classifier
from docprep.engine.converter import Converter
from docprep.engine.extractor import Extractor
from docprep.engine.normalizers.extension import ExtensionNormalizer
from docprep.core.config import get_data_paths

def process_all_iterations(date: str, max_iterations: int = 3):
    """Обрабатывает все итерации до тех пор, пока есть UNIT для обработки."""
    print("=" * 80)
    print("ОБРАБОТКА ВСЕХ ИТЕРАЦИЙ")
    print("=" * 80)
    print(f"Дата: {date}")
    print()
    
    base_dir = Path("Data") / date
    
    for iteration in range(2, max_iterations + 1):
        print(f"\n{'=' * 80}")
        print(f"ИТЕРАЦИЯ {iteration}")
        print("=" * 80)
        
        processing_dir = base_dir / "Processing" / f"Processing_{iteration}"
        if not processing_dir.exists():
            print(f"Processing_{iteration} не существует, пропускаем")
            continue
        
        # Проверяем есть ли UNIT для обработки
        units_to_process = list(processing_dir.rglob("UNIT_*"))
        units_count = len([u for u in units_to_process if u.is_dir()])
        
        if units_count == 0:
            print(f"UNIT в Processing_{iteration} не найдены, пропускаем")
            continue
        
        print(f"Найдено UNIT в Processing_{iteration}: {units_count}")
        
        # Обработка
        converter = Converter()
        extractor = Extractor()
        normalizer = ExtensionNormalizer()
        
        # Convert
        convert_dir = processing_dir / "Convert"
        if convert_dir.exists():
            convert_units = list(convert_dir.rglob("UNIT_*"))
            convert_count = len([u for u in convert_units if u.is_dir()])
            if convert_count > 0:
                print(f"\nConvert: {convert_count} UNIT")
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
            if extract_count > 0:
                print(f"\nExtract: {extract_count} UNIT")
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
            if normalize_count > 0:
                print(f"\nNormalize: {normalize_count} UNIT")
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
        
        # Повторная классификация
        print(f"\nПовторная классификация (Цикл {iteration + 1})...")
        merge_dir = base_dir / "Merge" / f"Merge_{iteration}"
        if merge_dir.exists():
            merge_units = []
            for subdir in ["Converted", "Extracted", "Normalized"]:
                subdir_path = merge_dir / subdir
                if subdir_path.exists():
                    merge_units.extend(list(subdir_path.rglob("UNIT_*")))
            
            merge_count = len([u for u in merge_units if u.is_dir()])
            print(f"Найдено UNIT в Merge_{iteration}: {merge_count}")
            
            if merge_count > 0:
                classifier = Classifier()
                reclassified = 0
                for unit_dir in merge_units:
                    if not unit_dir.is_dir():
                        continue
                    try:
                        classifier.classify_unit(
                            unit_path=unit_dir,
                            cycle=iteration + 1,
                            protocol_date=date,
                            dry_run=False,
                            copy_mode=False,
                        )
                        reclassified += 1
                    except Exception as e:
                        if reclassified < 5:
                            print(f"  ❌ {unit_dir.name}: {e}")
                
                print(f"✅ Классифицировано: {reclassified}/{merge_count}")
    
    print(f"\n{'=' * 80}")
    print("✅ ОБРАБОТКА ВСЕХ ИТЕРАЦИЙ ЗАВЕРШЕНА")
    print("=" * 80)

if __name__ == "__main__":
    date = "2025-12-20"
    process_all_iterations(date, max_iterations=3)


#!/usr/bin/env python3
"""
Обработка UNIT из Processing_2 через Converter, Extractor, Normalizers.
"""
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from docprep.engine.converter import Converter
from docprep.engine.extractor import Extractor
from docprep.engine.normalizers.extension import ExtensionNormalizer
from docprep.core.config import get_data_paths

def process_processing_2(date: str):
    """Обрабатывает UNIT из Processing_2."""
    print("=" * 80)
    print("ОБРАБОТКА PROCESSING_2")
    print("=" * 80)
    print(f"Дата: {date}")
    print()
    
    base_dir = Path("Data") / date
    processing_2_dir = base_dir / "Processing" / "Processing_2"
    
    if not processing_2_dir.exists():
        print(f"❌ Processing_2 не существует: {processing_2_dir}")
        return
    
    data_paths = get_data_paths(date)
    
    # Инициализируем обработчики
    converter = Converter()
    extractor = Extractor()
    normalizer = ExtensionNormalizer()
    
    # Обрабатываем Convert
    convert_dir = processing_2_dir / "Convert"
    if convert_dir.exists():
        print("Обработка Convert...")
        convert_units = list(convert_dir.rglob("UNIT_*"))
        convert_count = len([u for u in convert_units if u.is_dir()])
        print(f"  Найдено UNIT: {convert_count}")
        
        processed = 0
        errors = []
        for unit_dir in convert_units:
            if not unit_dir.is_dir():
                continue
            
            try:
                # Определяем расширение из пути
                ext_dir = unit_dir.parent
                ext_name = ext_dir.name
                
                result = converter.convert_unit(
                    unit_path=unit_dir,
                    cycle=2,
                    protocol_date=date,
                    dry_run=False,
                )
                processed += 1
                if processed % 10 == 0:
                    print(f"  Обработано: {processed}/{convert_count}")
            except Exception as e:
                errors.append({"unit": unit_dir.name, "error": str(e)})
                if len(errors) <= 5:
                    print(f"  ❌ {unit_dir.name}: {e}")
        
        print(f"  ✅ Обработано: {processed}/{convert_count}")
        if errors:
            print(f"  ❌ Ошибок: {len(errors)}")
    
    # Обрабатываем Extract
    extract_dir = processing_2_dir / "Extract"
    if extract_dir.exists():
        print("\nОбработка Extract...")
        extract_units = list(extract_dir.rglob("UNIT_*"))
        extract_count = len([u for u in extract_units if u.is_dir()])
        print(f"  Найдено UNIT: {extract_count}")
        
        processed = 0
        errors = []
        for unit_dir in extract_units:
            if not unit_dir.is_dir():
                continue
            
            try:
                result = extractor.extract_unit(
                    unit_path=unit_dir,
                    cycle=2,
                    protocol_date=date,
                    dry_run=False,
                )
                processed += 1
                if processed % 10 == 0:
                    print(f"  Обработано: {processed}/{extract_count}")
            except Exception as e:
                errors.append({"unit": unit_dir.name, "error": str(e)})
                if len(errors) <= 5:
                    print(f"  ❌ {unit_dir.name}: {e}")
        
        print(f"  ✅ Обработано: {processed}/{extract_count}")
        if errors:
            print(f"  ❌ Ошибок: {len(errors)}")
    
    # Обрабатываем Normalize
    normalize_dir = processing_2_dir / "Normalize"
    if normalize_dir.exists():
        print("\nОбработка Normalize...")
        normalize_units = list(normalize_dir.rglob("UNIT_*"))
        normalize_count = len([u for u in normalize_units if u.is_dir()])
        print(f"  Найдено UNIT: {normalize_count}")
        
        processed = 0
        errors = []
        for unit_dir in normalize_units:
            if not unit_dir.is_dir():
                continue
            
            try:
                result = normalizer.normalize_unit(
                    unit_path=unit_dir,
                    cycle=2,
                    protocol_date=date,
                    dry_run=False,
                )
                processed += 1
                if processed % 10 == 0:
                    print(f"  Обработано: {processed}/{normalize_count}")
            except Exception as e:
                errors.append({"unit": unit_dir.name, "error": str(e)})
                if len(errors) <= 5:
                    print(f"  ❌ {unit_dir.name}: {e}")
        
        print(f"  ✅ Обработано: {processed}/{normalize_count}")
        if errors:
            print(f"  ❌ Ошибок: {len(errors)}")
    
    print()
    print("=" * 80)
    print("✅ ОБРАБОТКА ЗАВЕРШЕНА")
    print("=" * 80)

if __name__ == "__main__":
    date = "2025-12-20"
    process_processing_2(date)


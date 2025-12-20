#!/usr/bin/env python3
"""
Финальная сборка всех UNIT из Merge_N в Ready2Docling.
"""
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from docprep.engine.merger import Merger
from docprep.core.config import get_data_paths, READY2DOCLING_DIR

def collect_all_to_ready2docling(date: str):
    """Собирает все UNIT из всех Merge_N в Ready2Docling."""
    print("=" * 80)
    print("ФИНАЛЬНАЯ СБОРКА UNIT В READY2DOCLING")
    print("=" * 80)
    print(f"Дата: {date}")
    print()
    
    base_dir = Path("Data") / date
    data_paths = get_data_paths(date)
    
    # Целевая директория
    target_dir = data_paths.get("ready2docling", base_dir / "Ready2Docling")
    target_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Целевая директория: {target_dir}")
    print()
    
    # Собираем все Merge_N директории (кроме Merge_0, так как Direct уже должны быть обработаны)
    source_dirs = []
    
    # Merge_0/Direct - тоже собираем
    merge_0_direct = base_dir / "Merge" / "Merge_0" / "Direct"
    if merge_0_direct.exists():
        source_dirs.append(merge_0_direct)
        print(f"  Добавлен источник: {merge_0_direct}")
    
    # Merge_1, Merge_2, Merge_3 - все поддиректории
    for merge_num in range(1, 4):
        merge_dir = base_dir / "Merge" / f"Merge_{merge_num}"
        if merge_dir.exists():
            for subdir in ["Converted", "Extracted", "Normalized"]:
                subdir_path = merge_dir / subdir
                if subdir_path.exists():
                    source_dirs.append(subdir_path)
                    print(f"  Добавлен источник: {subdir_path}")
    
    if not source_dirs:
        print("⚠️ Источники не найдены")
        return
    
    print()
    print(f"Всего источников: {len(source_dirs)}")
    print()
    
    # Запускаем сборку
    merger = Merger()
    result = merger.collect_units(
        source_dirs=source_dirs,
        target_dir=target_dir,
        cycle=None,
    )
    
    print("РЕЗУЛЬТАТЫ СБОРКИ:")
    print("-" * 80)
    print(f"Обработано UNIT: {result['units_processed']}")
    if result['errors']:
        print(f"Ошибок: {len(result['errors'])}")
        for error in result['errors'][:10]:
            print(f"  ❌ {error['unit_id']}: {error['error']}")
    
    # Статистика по типам файлов
    print()
    print("СТАТИСТИКА ПО ТИПАМ:")
    print("-" * 80)
    type_counts = {}
    for unit_info in result['processed_units']:
        file_type = unit_info.get('file_type', 'unknown')
        type_counts[file_type] = type_counts.get(file_type, 0) + 1
    
    for file_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {file_type}: {count} UNIT")
    
    print()
    print("=" * 80)
    print("✅ СБОРКА ЗАВЕРШЕНА")
    print("=" * 80)
    
    return result

if __name__ == "__main__":
    date = "2025-12-20"
    result = collect_all_to_ready2docling(date)


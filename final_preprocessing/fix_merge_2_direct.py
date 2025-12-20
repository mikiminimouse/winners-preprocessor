#!/usr/bin/env python3
"""
Скрипт для перемещения UNIT из Merge_2/Direct в Ready2Docling.
"""
import sys
from pathlib import Path
import shutil

def fix_merge_2_direct(date: str):
    """Перемещает UNIT из Merge_2/Direct в Ready2Docling."""
    base_dir = Path("Data") / date
    
    # Старое место
    merge_2_direct = base_dir / "Merge" / "Merge_2" / "Direct"
    
    # Новое место
    ready2docling = base_dir / "Ready2Docling"
    
    if not merge_2_direct.exists():
        print(f"Merge_2/Direct не существует: {merge_2_direct}")
        return
    
    print(f"Перемещение UNIT из {merge_2_direct} в {ready2docling}")
    
    units_moved = 0
    for ext_dir in merge_2_direct.iterdir():
        if not ext_dir.is_dir():
            continue
        
        ext_name = ext_dir.name
        new_ext_dir = ready2docling / ext_name
        
        if not new_ext_dir.exists():
            new_ext_dir.mkdir(parents=True, exist_ok=True)
        
        for unit_dir in ext_dir.iterdir():
            if not unit_dir.is_dir() or not unit_dir.name.startswith("UNIT_"):
                continue
            
            new_unit_dir = new_ext_dir / unit_dir.name
            
            if new_unit_dir.exists():
                print(f"  ⚠️ {unit_dir.name} уже существует в Ready2Docling, пропускаем")
                continue
            
            shutil.move(str(unit_dir), str(new_unit_dir))
            units_moved += 1
            if units_moved % 10 == 0:
                print(f"  Перемещено: {units_moved}")
    
    print(f"\n✅ Всего перемещено UNIT: {units_moved}")
    
    # Удаляем пустые директории
    print("\nОчистка пустых директорий...")
    try:
        if merge_2_direct.exists():
            # Проверяем, пуста ли директория
            if not any(merge_2_direct.rglob("*")):
                merge_2_direct.rmdir()
                print(f"  Удалена пустая директория: {merge_2_direct}")
    except Exception as e:
        print(f"  ⚠️ Не удалось удалить {merge_2_direct}: {e}")

if __name__ == "__main__":
    date = "2025-12-20"
    fix_merge_2_direct(date)


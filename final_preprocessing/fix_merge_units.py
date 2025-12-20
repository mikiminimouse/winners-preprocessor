#!/usr/bin/env python3
"""
Скрипт для перемещения UNIT из неправильного места в правильное.
"""
import sys
from pathlib import Path
import shutil

def fix_merge_units(date: str):
    """Перемещает UNIT из Data/Merge/date в Data/date/Merge."""
    base_dir = Path("Data")
    
    # Старое место
    old_merge = base_dir / "Merge" / date
    
    # Новое место
    new_merge = base_dir / date / "Merge"
    
    if not old_merge.exists():
        print(f"Старое место не существует: {old_merge}")
        return
    
    print(f"Перемещение UNIT из {old_merge} в {new_merge}")
    
    # Находим все UNIT
    units_moved = 0
    for merge_cycle_dir in old_merge.iterdir():
        if not merge_cycle_dir.is_dir() or not merge_cycle_dir.name.startswith("Merge_"):
            continue
        
        cycle_name = merge_cycle_dir.name
        new_cycle_dir = new_merge / cycle_name
        
        print(f"  Обработка {cycle_name}...")
        
        for category_dir in merge_cycle_dir.iterdir():
            if not category_dir.is_dir():
                continue
            
            category_name = category_dir.name
            new_category_dir = new_cycle_dir / category_name
            
            for ext_dir in category_dir.iterdir():
                if not ext_dir.is_dir():
                    continue
                
                ext_name = ext_dir.name
                new_ext_dir = new_category_dir / ext_name
                
                for unit_dir in ext_dir.iterdir():
                    if not unit_dir.is_dir() or not unit_dir.name.startswith("UNIT_"):
                        continue
                    
                    new_unit_dir = new_ext_dir / unit_dir.name
                    
                    # Перемещаем UNIT
                    if not new_ext_dir.exists():
                        new_ext_dir.mkdir(parents=True, exist_ok=True)
                    
                    if new_unit_dir.exists():
                        print(f"    ⚠️ {unit_dir.name} уже существует в новом месте, пропускаем")
                        continue
                    
                    shutil.move(str(unit_dir), str(new_unit_dir))
                    units_moved += 1
                    if units_moved % 10 == 0:
                        print(f"    Перемещено: {units_moved}")
    
    print(f"\n✅ Всего перемещено UNIT: {units_moved}")
    
    # Удаляем пустые директории
    print("\nОчистка пустых директорий...")
    for merge_cycle_dir in old_merge.iterdir():
        if merge_cycle_dir.is_dir():
            try:
                # Проверяем, пуста ли директория
                if not any(merge_cycle_dir.rglob("*")):
                    merge_cycle_dir.rmdir()
                    print(f"  Удалена пустая директория: {merge_cycle_dir}")
            except Exception as e:
                print(f"  ⚠️ Не удалось удалить {merge_cycle_dir}: {e}")

if __name__ == "__main__":
    date = "2025-12-20"
    fix_merge_units(date)


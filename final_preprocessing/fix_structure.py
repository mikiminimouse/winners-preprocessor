#!/usr/bin/env python3
"""
Исправление структуры директорий - перемещение UNIT из неправильных мест.
"""
import sys
from pathlib import Path
import shutil

# Добавляем путь к модулю
sys.path.insert(0, str(Path(__file__).parent))

def fix_structure():
    """Исправление структуры директорий."""
    date = "2025-03-18"
    
    print("=" * 60)
    print("ИСПРАВЛЕНИЕ СТРУКТУРЫ ДИРЕКТОРИЙ")
    print("=" * 60)
    
    # Ищем неправильные директории
    wrong_dirs = []
    for category in ["Exceptions", "Merge", "Processing"]:
        category_dir = Path(f"Data/{category}/{date}")
        if category_dir.exists():
            wrong_dirs.append(category_dir)
    
    if not wrong_dirs:
        print("✅ Неправильных директорий не найдено")
        return
    
    print(f"\nНайдено неправильных директорий: {len(wrong_dirs)}")
    
    # Правильная базовая директория
    correct_base = Path(f"Data/{date}")
    
    moved_count = 0
    
    for wrong_dir in wrong_dirs:
        print(f"\nОбработка: {wrong_dir}")
        
        # Определяем категорию
        category = wrong_dir.parent.name  # Exceptions, Merge, или Processing
        
        # Находим все UNIT в неправильной директории
        units = list(wrong_dir.rglob("UNIT_*"))
        units = [u for u in units if u.is_dir()]
        
        print(f"  Найдено UNIT: {len(units)}")
        
        for unit in units:
            # Получаем относительный путь от неправильной директории
            rel_path = unit.relative_to(wrong_dir)
            
            # Строим правильный путь
            correct_path = correct_base / category / rel_path
            
            print(f"  Перемещение: {unit.name}")
            print(f"    Из: {unit}")
            print(f"    В: {correct_path}")
            
            # Создаем родительскую директорию
            correct_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Перемещаем, если целевая директория не существует
            if not correct_path.exists():
                try:
                    shutil.move(str(unit), str(correct_path))
                    moved_count += 1
                    print(f"    ✅ Перемещен")
                except Exception as e:
                    print(f"    ❌ Ошибка: {e}")
            else:
                print(f"    ⚠️  Целевая директория уже существует, пропускаем")
                # Можно удалить старую, если нужно
                # shutil.rmtree(unit)
    
    print(f"\n✅ Перемещено UNIT: {moved_count}")
    
    # Удаляем пустые неправильные директории
    print(f"\nОчистка пустых директорий...")
    for wrong_dir in wrong_dirs:
        try:
            # Проверяем, что директория пустая
            if not any(wrong_dir.rglob("*")):
                wrong_dir.rmdir()
                print(f"  ✅ Удалена: {wrong_dir}")
        except Exception as e:
            print(f"  ⚠️  Не удалось удалить {wrong_dir}: {e}")

if __name__ == "__main__":
    fix_structure()

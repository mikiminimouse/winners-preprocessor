#!/usr/bin/env python3
"""
Тестовый скрипт для проверки исправления путей в docprep.
"""
import sys
from pathlib import Path

# Добавляем пути
sys.path.insert(0, str(Path(__file__).parent / "final_preprocessing"))

from docprep.core.config import DATA_BASE_DIR, get_data_paths, init_directory_structure

def test_paths():
    """Тестирует правильность формирования путей."""
    print("=" * 80)
    print("ТЕСТИРОВАНИЕ ПУТЕЙ")
    print("=" * 80)
    
    # Проверяем DATA_BASE_DIR
    print(f"\n1. DATA_BASE_DIR: {DATA_BASE_DIR}")
    print(f"   Абсолютный путь: {DATA_BASE_DIR.resolve()}")
    print(f"   Существует: {DATA_BASE_DIR.exists()}")
    
    # Проверяем пути для даты
    test_date = "2025-03-20"
    print(f"\n2. Пути для даты {test_date}:")
    paths = get_data_paths(test_date)
    for key, path in paths.items():
        print(f"   {key}: {path}")
        print(f"      Абсолютный: {path.resolve()}")
        print(f"      Внутри Data/{test_date}/: {'Data/' + test_date in str(path)}")
    
    # Проверяем, что все пути внутри правильной директории
    print(f"\n3. Проверка структуры:")
    all_correct = True
    for key, path in paths.items():
        expected_base = DATA_BASE_DIR / test_date
        if not str(path).startswith(str(expected_base)):
            print(f"   ❌ {key}: путь вне директории {test_date}")
            print(f"      Ожидалось: {expected_base}")
            print(f"      Получено: {path}")
            all_correct = False
        else:
            print(f"   ✅ {key}: путь корректный")
    
    if all_correct:
        print("\n✅ Все пути формируются правильно!")
        return 0
    else:
        print("\n❌ Обнаружены проблемы с путями!")
        return 1

if __name__ == "__main__":
    sys.exit(test_paths())


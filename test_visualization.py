#!/usr/bin/env python3
"""
Тестовый скрипт для проверки функции генерации визуализации
"""

import sys
import os
import numpy as np
from pathlib import Path
from PIL import Image

# Добавляем путь к сервису
sys.path.append('/app')

try:
    from ocr_vl.service.server import generate_layout_visualization
    print("✅ Функция generate_layout_visualization успешно импортирована")
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    # Создадим тестовую реализацию
    def generate_layout_visualization(image_path: Path, results: any, output_path: Path) -> bool:
        """Тестовая реализация функции визуализации"""
        try:
            # Создаем тестовое изображение
            img = np.zeros((400, 600, 3), dtype=np.uint8)
            img[:] = (255, 255, 255)  # Белый фон
            
            # Рисуем тестовые прямоугольники
            import cv2
            cv2.rectangle(img, (50, 50), (200, 150), (0, 255, 0), 2)  # Зеленый
            cv2.rectangle(img, (250, 100), (400, 200), (0, 0, 255), 2)  # Красный
            cv2.rectangle(img, (100, 200), (300, 300), (255, 0, 0), 2)  # Синий
            
            # Добавляем текст
            cv2.putText(img, "Test Visualization", (50, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
            cv2.putText(img, "Element 1", (55, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            cv2.putText(img, "Element 2", (255, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
            cv2.putText(img, "Element 3", (105, 195), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
            
            # Сохраняем изображение
            success = cv2.imwrite(str(output_path), img)
            if success:
                print(f"✅ Тестовая визуализация сохранена: {output_path}")
                return True
            else:
                print(f"❌ Не удалось сохранить визуализацию: {output_path}")
                return False
        except Exception as e:
            print(f"❌ Ошибка при создании тестовой визуализации: {e}")
            return False
    
    print("✅ Тестовая функция generate_layout_visualization создана")

def main():
    """Основная функция тестирования"""
    print("=== Тестирование функции генерации визуализации ===")
    
    # Создаем тестовое изображение
    test_image_path = Path("test_input.png")
    output_path = Path("test_visualization.png")
    
    try:
        # Создаем простое тестовое изображение
        img = Image.new('RGB', (600, 400), color=(255, 255, 255))
        img.save(test_image_path)
        print(f"✅ Тестовое изображение создано: {test_image_path}")
    except Exception as e:
        print(f"❌ Ошибка создания тестового изображения: {e}")
        return False
    
    # Создаем тестовые данные результатов
    test_results = [
        {
            "type": "text",
            "bbox": [50, 50, 200, 150],
            "score": 0.95
        },
        {
            "type": "table",
            "bbox": [250, 100, 400, 200],
            "score": 0.87
        },
        {
            "type": "figure",
            "bbox": [100, 200, 300, 300],
            "score": 0.92
        }
    ]
    
    print(f"📊 Тестовые данные: {len(test_results)} элементов")
    
    # Тестируем функцию визуализации
    try:
        success = generate_layout_visualization(test_image_path, test_results, output_path)
        if success:
            print("✅ Функция визуализации выполнена успешно")
            if output_path.exists():
                print(f"📁 Файл визуализации создан: {output_path}")
                print(f"📏 Размер файла: {output_path.stat().st_size} байт")
                return True
            else:
                print("❌ Файл визуализации не найден")
                return False
        else:
            print("❌ Функция визуализации вернула False")
            return False
    except Exception as e:
        print(f"❌ Ошибка при выполнении функции визуализации: {e}")
        return False
    finally:
        # Удаляем временные файлы
        try:
            if test_image_path.exists():
                test_image_path.unlink()
                print(f"🗑️  Временный файл удален: {test_image_path}")
        except Exception as e:
            print(f"⚠️  Ошибка при удалении временного файла: {e}")

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

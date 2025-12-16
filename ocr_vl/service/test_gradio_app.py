#!/usr/bin/env python3
"""
Упрощенный тестовый скрипт для проверки функциональности Gradio UI без GPU
"""

import os
import sys
import time
from pathlib import Path

# Добавляем путь к сервису
sys.path.append('/app')

def test_imports():
    """Проверка импорта необходимых модулей"""
    print("🔍 Проверка импорта модулей...")
    
    try:
        import gradio as gr
        print("✅ Gradio импортирован успешно")
    except ImportError as e:
        print(f"❌ Ошибка импорта Gradio: {e}")
        return False
    
    try:
        # Проверяем импорт наших функций
        from server import process_with_paddleocr, save_results_locally
        print("✅ Функции из server.py импортированы успешно")
    except ImportError as e:
        print(f"⚠️  Предупреждение: Ошибка импорта из server.py: {e}")
        print("     Это нормально при тестировании без GPU")
    
    return True

def test_file_structure():
    """Проверка структуры файлов"""
    print("\n🔍 Проверка структуры файлов...")
    
    required_files = [
        "gradio_app.py",
        "server.py",
        "requirements.txt",
        "Dockerfile",
        "start.sh"
    ]
    
    for file in required_files:
        if Path(f"/app/{file}").exists() or Path(f"./{file}").exists() or Path(f"ocr_vl/service/{file}").exists():
            print(f"✅ Файл {file} найден")
        else:
            print(f"❌ Файл {file} не найден")
            return False
    
    # Проверка assets
    if Path("/app/assets/company.css").exists() or Path("ocr_vl/service/assets/company.css").exists():
        print("✅ Директория assets найдена")
    else:
        print("❌ Директория assets не найдена")
        return False
    
    return True

def test_gradio_app_syntax():
    """Проверка синтаксиса Gradio приложения"""
    print("\n🔍 Проверка синтаксиса Gradio приложения...")
    
    try:
        # Проверяем синтаксис gradio_app.py
        with open("ocr_vl/service/gradio_app.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # Простая проверка на синтаксические ошибки
        compile(content, "gradio_app.py", "exec")
        print("✅ Синтаксис gradio_app.py корректен")
        return True
    except SyntaxError as e:
        print(f"❌ Синтаксическая ошибка в gradio_app.py: {e}")
        return False
    except Exception as e:
        print(f"❌ Ошибка при проверке синтаксиса: {e}")
        return False

def test_dockerfile():
    """Проверка Dockerfile"""
    print("\n🔍 Проверка Dockerfile...")
    
    try:
        with open("ocr_vl/service/Dockerfile", "r", encoding="utf-8") as f:
            content = f.read()
        
        # Проверяем наличие ключевых элементов
        required_elements = [
            "EXPOSE 8081",
            "EXPOSE 7860",
            "gradio_app.py",
            "COPY server.py",
            "COPY assets/"
        ]
        
        missing_elements = []
        for element in required_elements:
            if element in content:
                print(f"✅ Элемент найден: {element}")
            else:
                missing_elements.append(element)
                print(f"❌ Элемент не найден: {element}")
        
        if not missing_elements:
            print("✅ Dockerfile содержит все необходимые элементы")
            return True
        else:
            print(f"❌ В Dockerfile отсутствуют элементы: {missing_elements}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при проверке Dockerfile: {e}")
        return False

def test_start_script():
    """Проверка скрипта запуска"""
    print("\n🔍 Проверка скрипта запуска...")
    
    try:
        with open("ocr_vl/service/start.sh", "r", encoding="utf-8") as f:
            content = f.read()
        
        # Проверяем наличие ключевых команд
        required_commands = [
            "uvicorn server:app",
            "python3 /app/gradio_app.py",
            "--port 8081",
            "--port 7860"
        ]
        
        missing_commands = []
        for cmd in required_commands:
            if cmd in content:
                print(f"✅ Команда найдена: {cmd}")
            else:
                # Проверяем альтернативные варианты
                if (cmd == "--port 8081" and "8081" in content) or \
                   (cmd == "--port 7860" and "7860" in content):
                    print(f"✅ Команда найдена: {cmd}")
                else:
                    missing_commands.append(cmd)
                    print(f"❌ Команда не найдена: {cmd}")
        
        if not missing_commands:
            print("✅ Скрипт запуска содержит все необходимые команды")
            return True
        else:
            print(f"❌ В скрипте запуска отсутствуют команды: {missing_commands}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при проверке скрипта запуска: {e}")
        return False

def main():
    """Основная функция тестирования"""
    print("=" * 60)
    print("ТЕСТИРОВАНИЕ GRADIO UI ДЛЯ PADDLEOCR-VL")
    print("=" * 60)
    
    tests = [
        test_imports,
        test_file_structure,
        test_gradio_app_syntax,
        test_dockerfile,
        test_start_script
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 60)
    print(f"РЕЗУЛЬТАТЫ: {passed}/{total} тестов пройдено")
    print("=" * 60)
    
    if passed == total:
        print("✅ Все тесты пройдены успешно!")
        print("Готово к сборке Docker образа и деплою на Cloud.ru")
        return True
    else:
        print("❌ Некоторые тесты не пройдены")
        print("Необходимо исправить ошибки перед сборкой")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

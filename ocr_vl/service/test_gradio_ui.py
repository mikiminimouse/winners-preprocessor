#!/usr/bin/env python3
"""
Тестовый скрипт для проверки функциональности Gradio UI
"""

import requests
import time
import os
from pathlib import Path

def test_gradio_ui():
    """
    Тестирование Gradio UI
    """
    print("🔍 Тестирование Gradio UI...")
    
    # Проверяем доступность Gradio UI
    try:
        response = requests.get("http://localhost:7860", timeout=10)
        if response.status_code == 200:
            print("✅ Gradio UI доступен на порту 7860")
        else:
            print(f"❌ Gradio UI вернул статус {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Gradio UI недоступен на порту 7860")
        return False
    except Exception as e:
        print(f"❌ Ошибка при проверке Gradio UI: {e}")
        return False
    
    # Проверяем доступность FastAPI
    try:
        response = requests.get("http://localhost:8081/health", timeout=10)
        if response.status_code == 200:
            print("✅ FastAPI доступен на порту 8081")
        else:
            print(f"❌ FastAPI вернул статус {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ FastAPI недоступен на порту 8081")
        return False
    except Exception as e:
        print(f"❌ Ошибка при проверке FastAPI: {e}")
        return False
    
    print("✅ Все сервисы работают корректно")
    return True

if __name__ == "__main__":
    test_gradio_ui()

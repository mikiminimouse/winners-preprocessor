#!/usr/bin/env python3
"""
Простой тест подключения к SmolDocling через evolution-openai
"""
import json
import time
import requests
from evolution_openai import EvolutionOpenAI

# Конфигурация из примера пользователя
API_KEY_ID = "ZDRhOWQ3OTAtZjU4MC00MzA2LThhNTgtMDU1NGFlMjE4OWRl"
API_SECRET = "85a830f9340966e0ad1fd1642884c7c8"
BASE_URL = "https://d63e30af-085a-49f0-9724-8162da967af2.modelrun.inference.cloud.ru/v1"
MODEL_NAME = "model-run-4qigw-disease"

def wait_for_server_ready(max_wait_time: int = 300):
    """Wait for the inference server to be ready"""
    print(f"⏳ Ожидание готовности сервера SmolDocling (максимум {max_wait_time} секунд)...")
    
    # Try direct health check first
    health_url = "https://d63e30af-085a-49f0-9724-8162da967af2.modelrun.inference.cloud.ru/health"
    
            start_time = time.time()
    while time.time() - start_time < max_wait_time:
        try:
            response = requests.get(health_url, timeout=10)
            if response.status_code == 200:
                print("✅ Сервер готов к работе (health check)")
                return True
        except requests.exceptions.RequestException as e:
            print(f"    Health check не доступен: {e}")
        
        time.sleep(10)
    
    print("❌ Сервер не стал доступен в течение отведенного времени")
    return False

def test_connection():
    try:
        print("🔍 Тестирование подключения к SmolDocling...")
            client = EvolutionOpenAI(
            key_id=API_KEY_ID, 
            secret=API_SECRET, 
            base_url=BASE_URL
            )
            
        # Send a wake-up request
        print("    Отправка запроса для пробуждения сервера...")
                    response = client.chat.completions.create(
            model=MODEL_NAME,
                        messages=[
                            {"role": "system", "content": "Вы очень полезный ассистент."},
                {"role": "user", "content": "Что такое искусственный интеллект?"},
                        ],
            max_tokens=100,
            temperature=0.5,
            presence_penalty=0,
            top_p=0.95,
        )

        print(f"✅ Подключение успешно!")
        print(f"Ответ: {response.choices[0].message.content}")
                        return True
                except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return False

if __name__ == "__main__":
    # First wait for server to be ready
    if wait_for_server_ready():
        test_connection()
    else:
        print("❌ Сервер не готов к работе")



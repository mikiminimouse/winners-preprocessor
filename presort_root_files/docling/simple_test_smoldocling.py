#!/usr/bin/env python3
"""
Простой тест подключения к SmolDocling через evolution-openai
"""
from evolution_openai import EvolutionOpenAI

# Конфигурация из примера пользователя
API_KEY_ID = "ZDRhOWQ3OTAtZjU4MC00MzA2LThhNTgtMDU1NGFlMjE4OWRl"
API_SECRET = "85a830f9340966e0ad1fd1642884c7c8"
BASE_URL = "https://d63e30af-085a-49f0-9724-8162da967af2.modelrun.inference.cloud.ru/v1"
MODEL_NAME = "model-run-4qigw-disease"

def test_connection():
    try:
        print("🔍 Тестирование подключения к SmolDocling...")
        client = EvolutionOpenAI(
            key_id=API_KEY_ID, 
            secret=API_SECRET, 
            base_url=BASE_URL
        )
        
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
    test_connection()

#!/usr/bin/env python3
"""
Простой тест подключения к Qwen3-VL-8B через Cloud.ru ML Inference.
Использует стандартный OpenAI клиент с API key.
"""
import os
import sys
from openai import OpenAI

# Конфигурация
API_KEY = "ZDRhOWQ3OTAtZjU4MC00MzA2LThhNTgtMDU1NGFlMjE4OWRl.85a830f9340966e0ad1fd1642884c7c8"
BASE_URL = "https://92ad3238-81c6-4396-a02a-fb9cef99bce3.modelrun.inference.cloud.ru/v1"
MODEL_NAME = "qwen3-vl-8b-instruct"

print("=" * 70)
print("ТЕСТ ПОДКЛЮЧЕНИЯ К QWEN3-VL-8B (Cloud.ru ML Inference)")
print("=" * 70)
print()
print(f"🔑 API Key: {API_KEY[:30]}...")
print(f"🌐 Base URL: {BASE_URL}")
print(f"🤖 Модель: {MODEL_NAME}")
print()

# Инициализация клиента
print("🔌 Инициализация клиента OpenAI...")
try:
    client = OpenAI(
        api_key=API_KEY,
        base_url=BASE_URL
    )
    print("✅ Клиент инициализирован")
except Exception as e:
    print(f"❌ Ошибка инициализации: {e}")
    sys.exit(1)

# Тест 1: Простой текстовый запрос
print("\n" + "=" * 70)
print("ТЕСТ 1: Простой текстовый запрос")
print("=" * 70)

try:
    import time
    print("   Отправка запроса...")
    start_time = time.time()
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": "Вы очень полезный ассистент."},
            {"role": "user", "content": "Скажи 'Привет' одним словом"}
        ],
        max_tokens=10,
        temperature=0.5,
        timeout=30.0  # Таймаут 30 секунд
    )
    elapsed = time.time() - start_time
    print(f"   ⏱️  Время ответа: {elapsed:.2f} сек")
    
    if response.choices and response.choices[0].message.content:
        print(f"✅ Запрос выполнен успешно!")
        print(f"📝 Ответ модели: {response.choices[0].message.content}")
    else:
        print("❌ Пустой ответ от модели")
        
except Exception as e:
    print(f"❌ Ошибка запроса: {e}")
    sys.exit(1)

# Тест 2: Запрос с вопросом
print("\n" + "=" * 70)
print("ТЕСТ 2: Запрос с вопросом")
print("=" * 70)

try:
    print("   Отправка запроса...")
    start_time = time.time()
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "user", "content": "Что такое искусственный интеллект? Ответь кратко."}
        ],
        max_tokens=100,
        temperature=0.5,
        presence_penalty=0,
        top_p=0.95,
        timeout=30.0  # Таймаут 30 секунд
    )
    elapsed = time.time() - start_time
    print(f"   ⏱️  Время ответа: {elapsed:.2f} сек")
    
    if response.choices and response.choices[0].message.content:
        print(f"✅ Запрос выполнен успешно!")
        print(f"📝 Ответ модели:")
        print(f"   {response.choices[0].message.content}")
    else:
        print("❌ Пустой ответ от модели")
        
except Exception as e:
    print(f"❌ Ошибка запроса: {e}")
    sys.exit(1)

print("\n" + "=" * 70)
print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
print("=" * 70)
print("\n🎉 API работает корректно!")
print("   Теперь можно использовать для обработки изображений.")


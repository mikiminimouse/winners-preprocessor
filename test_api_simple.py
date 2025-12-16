#!/usr/bin/env python3
"""Простой тест API с разными вариантами авторизации."""
from evolution_openai import EvolutionOpenAI
import sys

API_KEY_FULL = "ZDRhOWQ3OTAtZjU4MC00MzA2LThhNTgtMDU1NGFlMjE4OWRl.85a830f9340966e0ad1fd1642884c7c8"
BASE_URL = "https://92ad3238-81c6-4396-a02a-fb9cef99bce3.modelrun.inference.cloud.ru/v1"

# Разделяем ключ
API_KEY_ID, API_KEY_SECRET = API_KEY_FULL.split(".", 1)

print("="*70)
print("ТЕСТ ПОДКЛЮЧЕНИЯ К QWEN3-VL-8B API")
print("="*70)
print(f"\nKey ID: {API_KEY_ID[:30]}...")
print(f"Secret: {API_KEY_SECRET[:20]}...")
print(f"Base URL: {BASE_URL}\n")

# Вариант с key_id и secret
print("Пробуем подключение с key_id и secret...")
try:
    client = EvolutionOpenAI(
        key_id=API_KEY_ID,
        secret=API_KEY_SECRET,
        base_url=BASE_URL
    )
    print("✅ Клиент создан успешно!")
    
    # Пробуем простой запрос
    print("\nОтправляем тестовый запрос...")
    response = client.chat.completions.create(
        model="qwen3-vl-8b-instruct",
        messages=[{"role": "user", "content": "Скажи 'Привет' одним словом"}],
        max_tokens=10
    )
    
    print(f"✅ Запрос выполнен успешно!")
    print(f"Ответ модели: {response.choices[0].message.content}")
    print("\n🎉 API работает корректно!")
    sys.exit(0)
    
except Exception as e:
    error_str = str(e)
    print(f"❌ Ошибка: {error_str}")
    
    if "401" in error_str or "Unauthorized" in error_str:
        print("\n⚠️  Проблема с авторизацией (401)")
        print("Возможные причины:")
        print("1. API key неправильный или истек")
        print("2. API key не имеет доступа к этому endpoint")
        print("3. Неправильный формат разделения ключа")
        print("\nПроверьте:")
        print(f"- Key ID начинается с: {API_KEY_ID[:10]}")
        print(f"- Secret начинается с: {API_KEY_SECRET[:10]}")
        print(f"- Endpoint доступен: {BASE_URL}")
    else:
        print(f"\nДетали ошибки: {e}")
    
    sys.exit(1)


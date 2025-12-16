#!/usr/bin/env python3
"""Простой тест подключения к Qwen3-VL-8B."""
from evolution_openai import EvolutionOpenAI

API_KEY_FULL = "ZDRhOWQ3OTAtZjU4MC00MzA2LThhNTgtMDU1NGFlMjE4OWRl.85a830f9340966e0ad1fd1642884c7c8"
BASE_URL = "https://92ad3238-81c6-4396-a02a-fb9cef99bce3.modelrun.inference.cloud.ru/v1"

# Разделяем ключ
if "." in API_KEY_FULL:
    API_KEY_ID, API_KEY_SECRET = API_KEY_FULL.split(".", 1)
    print(f"Key ID: {API_KEY_ID[:20]}...")
    print(f"Secret: {API_KEY_SECRET[:20]}...")
else:
    API_KEY_ID = API_KEY_FULL
    API_KEY_SECRET = ""

print(f"\nПробуем варианты подключения...\n")

# Вариант 1: api_key и api_secret
print("1. api_key + api_secret:")
try:
    client = EvolutionOpenAI(
        api_key=API_KEY_ID,
        api_secret=API_KEY_SECRET,
        base_url=BASE_URL
    )
    print("   ✅ Успешно!")
    # Пробуем простой запрос
    response = client.chat.completions.create(
        model="qwen3-vl-8b-instruct",
        messages=[{"role": "user", "content": "Привет"}],
        max_tokens=10
    )
    print(f"   ✅ Запрос выполнен: {response.choices[0].message.content}")
except Exception as e:
    print(f"   ❌ Ошибка: {e}")

# Вариант 2: key_id и secret
print("\n2. key_id + secret:")
try:
    client = EvolutionOpenAI(
        key_id=API_KEY_ID,
        secret=API_KEY_SECRET,
        base_url=BASE_URL
    )
    print("   ✅ Успешно!")
    response = client.chat.completions.create(
        model="qwen3-vl-8b-instruct",
        messages=[{"role": "user", "content": "Привет"}],
        max_tokens=10
    )
    print(f"   ✅ Запрос выполнен: {response.choices[0].message.content}")
except Exception as e:
    print(f"   ❌ Ошибка: {e}")

# Вариант 3: полный ключ как api_key
print("\n3. Полный ключ как api_key:")
try:
    client = EvolutionOpenAI(
        api_key=API_KEY_FULL,
        base_url=BASE_URL
    )
    print("   ✅ Успешно!")
    response = client.chat.completions.create(
        model="qwen3-vl-8b-instruct",
        messages=[{"role": "user", "content": "Привет"}],
        max_tokens=10
    )
    print(f"   ✅ Запрос выполнен: {response.choices[0].message.content}")
except Exception as e:
    print(f"   ❌ Ошибка: {e}")


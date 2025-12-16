#!/usr/bin/env python3
"""Прямой тест API через HTTP."""
import requests
import base64
import json

API_KEY_FULL = "ZDRhOWQ3OTAtZjU4MC00MzA2LThhNTgtMDU1NGFlMjE4OWRl.85a830f9340966e0ad1fd1642884c7c8"
BASE_URL = "https://92ad3238-81c6-4396-a02a-fb9cef99bce3.modelrun.inference.cloud.ru/v1"

# Пробуем разные варианты авторизации
headers_variants = [
    {"Authorization": f"Bearer {API_KEY_FULL}"},
    {"Authorization": f"ApiKey {API_KEY_FULL}"},
    {"X-API-Key": API_KEY_FULL},
    {"api-key": API_KEY_FULL},
]

print("Тестируем прямые HTTP запросы...\n")

for i, headers in enumerate(headers_variants, 1):
    print(f"{i}. Headers: {list(headers.keys())[0]}")
    try:
        # Простой запрос к /models
        response = requests.get(
            f"{BASE_URL}/models",
            headers={**headers, "Content-Type": "application/json"},
            timeout=10
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   ✅ Успешно! Ответ: {response.text[:200]}")
            break
        else:
            print(f"   Ответ: {response.text[:200]}")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")

print("\n" + "="*50)
print("Пробуем chat completion с API key в заголовке:")
print("="*50)

# Пробуем chat completion
payload = {
    "model": "qwen3-vl-8b-instruct",
    "messages": [{"role": "user", "content": "Привет"}],
    "max_tokens": 10
}

for i, headers in enumerate(headers_variants, 1):
    print(f"\n{i}. Headers: {list(headers.keys())[0]}")
    try:
        response = requests.post(
            f"{BASE_URL}/chat/completions",
            headers={**headers, "Content-Type": "application/json"},
            json=payload,
            timeout=30
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Успешно! Ответ: {result}")
            break
        else:
            print(f"   Ответ: {response.text[:300]}")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")


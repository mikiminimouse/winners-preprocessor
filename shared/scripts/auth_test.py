#!/usr/bin/env python3
"""
Тестирование различных вариантов аутентификации для SmolDocling
"""
import requests
import json

# Конфигурация из примера пользователя
API_KEY_ID = "ZDRhOWQ3OTAtZjU4MC00MzA2LThhNTgtMDU1NGFlMjE4OWRl"
API_SECRET = "85a830f9340966e0ad1fd1642884c7c8"
BASE_URL = "https://d63e30af-085a-49f0-9724-8162da967af2.modelrun.inference.cloud.ru"
MODEL_NAME = "model-run-4qigw-disease"

def test_auth_options():
    """Test different authentication options"""
    print("🔍 Тестирование различных вариантов аутентификации...")
    
    # Option 1: Basic Auth with key_id and secret
    print("\n1. Попытка Basic Auth...")
    try:
        response = requests.get(
            f"{BASE_URL}/health",
            auth=(API_KEY_ID, API_SECRET)
        )
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.text[:100]}...")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
    
    # Option 2: Bearer token (trying to use key_id as token)
    print("\n2. Попытка Bearer token (key_id)...")
    try:
        headers = {
            "Authorization": f"Bearer {API_KEY_ID}"
        }
        response = requests.get(
            f"{BASE_URL}/health",
            headers=headers
        )
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.text[:100]}...")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
    
    # Option 3: Custom header (as seen in some cloud services)
    print("\n3. Попытка пользовательского заголовка...")
    try:
        headers = {
            "X-API-Key": API_KEY_ID
        }
        response = requests.get(
            f"{BASE_URL}/health",
            headers=headers
        )
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.text[:100]}...")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
    
    # Option 4: API Key in query parameter
    print("\n4. Попытка API ключа в параметрах запроса...")
    try:
        params = {
            "api_key": API_KEY_ID
        }
        response = requests.get(
            f"{BASE_URL}/health",
            params=params
        )
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.text[:100]}...")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")

if __name__ == "__main__":
    print("=== Тестирование аутентификации для SmolDocling ===")
    test_auth_options()

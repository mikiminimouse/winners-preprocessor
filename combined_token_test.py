#!/usr/bin/env python3
"""
Тестирование аутентификации с комбинированным токеном
"""
import requests
import json

# Комбинированный токен из работающего скрипта
COMBINED_TOKEN = "ZDRhOWQ3OTAtZjU4MC00MzA2LThhNTgtMDU1NGFlMjE4OWRl.85a830f9340966e0ad1fd1642884c7c8"
BASE_URL = "https://d63e30af-085a-49f0-9724-8162da967af2.modelrun.inference.cloud.ru"

def test_combined_token():
    """Test authentication with combined token"""
    print("🔍 Тестирование аутентификации с комбинированным токеном...")
    
    # Option 1: Bearer token with combined token
    print("\n1. Попытка Bearer token (комбинированный токен)...")
    try:
        headers = {
            "Authorization": f"Bearer {COMBINED_TOKEN}"
        }
        response = requests.get(
            f"{BASE_URL}/health",
            headers=headers
        )
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        return False

def test_chat_completion():
    """Test chat completion endpoint"""
    print("\n🔍 Тестирование chat completion endpoint...")
    try:
        headers = {
            "Authorization": f"Bearer {COMBINED_TOKEN}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "model-run-4qigw-disease",
            "messages": [
                {"role": "system", "content": "Вы очень полезный ассистент."},
                {"role": "user", "content": "Что такое искусственный интеллект?"}
            ],
            "max_tokens": 100,
            "temperature": 0.5
        }
        
        response = requests.post(
            f"{BASE_URL}/v1/chat/completions",
            headers=headers,
            json=data
        )
        print(f"   Status Code: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {response.text}")
            return True
        else:
            print(f"   Error Response: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        return False

if __name__ == "__main__":
    print("=== Тестирование аутентификации с комбинированным токеном ===")
    
    # Test health endpoint
    if test_combined_token():
        print("\n✅ Health endpoint работает!")
        # Test chat completion
        if test_chat_completion():
            print("\n✅ Chat completion работает!")
        else:
            print("\n❌ Chat completion не работает")
    else:
        print("\n❌ Health endpoint не работает")

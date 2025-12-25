#!/usr/bin/env python3
"""
Тестирование аутентификации только с API ключом
"""
import requests
import json

# Конфигурация из примера пользователя
API_KEY_ID = "ZDRhOWQ3OTAtZjU4MC00MzA2LThhNTgtMDU1NGFlMjE4OWRl"
BASE_URL = "https://d63e30af-085a-49f0-9724-8162da967af2.modelrun.inference.cloud.ru"

def test_token_only():
    """Test authentication with token only"""
    print("🔍 Тестирование аутентификации только с API ключом...")
    
    # Option 1: Bearer token with API_KEY_ID only
    print("\n1. Попытка Bearer token (только API_KEY_ID)...")
    try:
        headers = {
            "Authorization": f"Bearer {API_KEY_ID}"
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
            "Authorization": f"Bearer {API_KEY_ID}",
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
    print("=== Тестирование аутентификации только с API ключом ===")
    
    # Test health endpoint
    if test_token_only():
        print("\n✅ Health endpoint работает!")
        # Test chat completion
        test_chat_completion()
    else:
        print("\n❌ Health endpoint не работает")

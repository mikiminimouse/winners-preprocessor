#!/usr/bin/env python3
"""
Тестирование прямого API вызова к SmolDocling
"""
import requests
import json

# Конфигурация
BASE_URL = "https://d63e30af-085a-49f0-9724-8162da967af2.modelrun.inference.cloud.ru"
MODEL_NAME = "model-run-4qigw-disease"

def test_health_endpoint():
    """Test the health endpoint"""
    try:
        print("🔍 Тестирование health endpoint...")
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Ошибка при тестировании health endpoint: {e}")
        return False

def test_models_endpoint():
    """Test the models endpoint"""
    try:
        print("\n🔍 Тестирование models endpoint...")
        response = requests.get(f"{BASE_URL}/v1/models")
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print(f"Response: {response.text}")
        else:
            print(f"Error Response: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Ошибка при тестировании models endpoint: {e}")
        return False

if __name__ == "__main__":
    print("=== Тестирование прямого API вызова к SmolDocling ===")
    
    # Test health endpoint
    test_health_endpoint()
    
    # Test models endpoint
    test_models_endpoint()

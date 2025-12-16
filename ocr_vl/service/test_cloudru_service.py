#!/usr/bin/env python3
"""
Тест работы PaddleOCR-VL Service на Cloud.ru ML Inference
Версия 1.0.8
"""
import os
import requests
import base64
import json
from PIL import Image
import io
from datetime import datetime

BASE_URL = os.getenv("ML_INFERENCE_URL", "https://9525a16c-09c1-4489-87d3-bf1946792a53.modelrun.inference.cloud.ru")
API_KEY = os.getenv("ML_INFERENCE_API_KEY", "ZDRhOWQ3OTAtZjU4MC00MzA2LThhNTgtMDU1NGFlMjE4OWRl.85a830f9340966e0ad1fd1642884c7c8")

def create_test_image():
    """Создает простое тестовое изображение с текстом"""
    img = Image.new('RGB', (600, 200), color='white')
    from PIL import ImageDraw
    
    draw = ImageDraw.Draw(img)
    
    # Рисуем текст
    text = "Test OCR Text\nHello World\n12345"
    draw.multiline_text((50, 50), text, fill='black')
    
    # Конвертируем в base64
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode()
    
    return img_base64

def test_health():
    """Тест health check"""
    print("=" * 60)
    print("1. Тест Health Check")
    print("=" * 60)
    
    try:
        headers = {"Authorization": f"Bearer {API_KEY}"} if API_KEY else {}
        response = requests.get(f"{BASE_URL}/health", headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print("✅ Health Check: OK")
            print(f"  - Status: {data.get('status')}")
            print(f"  - PaddleOCR: {data.get('paddleocr')}")
            print(f"  - S3 Storage: {data.get('s3_storage')}")
            return True, data
        else:
            print(f"❌ Health Check: Failed ({response.status_code})")
            print(f"Response: {response.text[:200]}")
            return False, None
    except Exception as e:
        print(f"❌ Health Check: Error - {e}")
        return False, None

def test_root():
    """Тест корневого endpoint"""
    print("\n" + "=" * 60)
    print("2. Тест Root Endpoint")
    print("=" * 60)
    
    try:
        headers = {"Authorization": f"Bearer {API_KEY}"} if API_KEY else {}
        response = requests.get(f"{BASE_URL}/", headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print("✅ Root Endpoint: OK")
            print(f"  - Service: {data.get('service')}")
            print(f"  - Version: {data.get('version')}")
            return True
        else:
            print(f"❌ Root Endpoint: Failed ({response.status_code})")
            return False
    except Exception as e:
        print(f"❌ Root Endpoint: Error - {e}")
        return False

def test_ocr_simple():
    """Простой тест OCR обработки"""
    print("\n" + "=" * 60)
    print("3. Тест OCR обработки (простой)")
    print("=" * 60)
    
    try:
        # Создаем тестовое изображение
        print("Создание тестового изображения...")
        img_base64 = create_test_image()
        
        # Отправляем запрос
        print("Отправка OCR запроса...")
        print("⚠️  Это может занять 1-3 минуты (инициализация модели при первом запросе)...")
        
        headers = {"Authorization": f"Bearer {API_KEY}"} if API_KEY else {}
        response = requests.post(
            f"{BASE_URL}/ocr",
            data={"image_base64": img_base64},
            headers=headers,
            timeout=300  # 5 минут для инициализации модели
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ OCR обработка: УСПЕХ!")
            print(f"  - Status: {result.get('status')}")
            print(f"  - Input type: {result.get('input_type')}")
            
            local_files = result.get('local_files', {})
            if local_files:
                print(f"  - Markdown файл: {local_files.get('markdown', 'N/A')}")
                print(f"  - JSON файл: {local_files.get('json', 'N/A')}")
            
            return True, result
        else:
            print(f"❌ OCR обработка: Failed ({response.status_code})")
            print(f"Response: {response.text[:500]}")
            return False, None
            
    except requests.Timeout:
        print("❌ OCR обработка: Timeout (инициализация модели заняла слишком много времени)")
        print("   Это может быть нормально при первом запуске на GPU")
        return False, None
    except Exception as e:
        print(f"❌ OCR обработка: Error - {e}")
        import traceback
        traceback.print_exc()
        return False, None

def main():
    """Основная функция тестирования"""
    print("\n" + "=" * 60)
    print("ТЕСТИРОВАНИЕ PaddleOCR-VL Service v1.0.8")
    print("Cloud.ru ML Inference")
    print("=" * 60)
    print(f"Base URL: {BASE_URL}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    results = {}
    
    # Тест 1: Health Check
    health_ok, health_data = test_health()
    results['health'] = health_ok
    
    # Тест 2: Root Endpoint
    root_ok = test_root()
    results['root'] = root_ok
    
    # Тест 3: OCR обработка (только если health check OK)
    if health_ok:
        ocr_ok, ocr_result = test_ocr_simple()
        results['ocr'] = ocr_ok
    else:
        print("\n⚠️  Пропуск OCR теста - health check не прошел")
        results['ocr'] = False
    
    # Итоговый отчет
    print("\n" + "=" * 60)
    print("ИТОГОВЫЙ ОТЧЕТ")
    print("=" * 60)
    print(f"Health Check: {'✅ OK' if results['health'] else '❌ FAILED'}")
    print(f"Root Endpoint: {'✅ OK' if results['root'] else '❌ FAILED'}")
    print(f"OCR Processing: {'✅ OK' if results['ocr'] else '❌ FAILED'}")
    
    if results['health'] and results['root']:
        print("\n✅ Сервис работает и готов к использованию!")
        if not results['ocr']:
            print("⚠️  OCR обработка не протестирована (возможно, требуется инициализация модели)")
    else:
        print("\n❌ Сервис не работает полностью - проверьте логи")
    
    return results

if __name__ == "__main__":
    results = main()
    exit(0 if all(results.values()) else 1)


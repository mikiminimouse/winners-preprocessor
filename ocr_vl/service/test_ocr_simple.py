#!/usr/bin/env python3
"""
Простой тест OCR запроса для диагностики
"""
import os
import requests
import base64
from PIL import Image
import io
import time

BASE_URL = os.getenv("ML_INFERENCE_URL", "https://9525a16c-09c1-4489-87d3-bf1946792a53.modelrun.inference.cloud.ru")
API_KEY = "ZDRhOWQ3OTAtZjU4MC00MzA2LThhNTgtMDU1NGFlMjE4OWRl.85a830f9340966e0ad1fd1642884c7c8"

def create_test_image():
    """Создает простое тестовое изображение"""
    img = Image.new('RGB', (200, 100), color='white')
    from PIL import ImageDraw, ImageFont
    draw = ImageDraw.Draw(img)
    draw.text((10, 40), "Test OCR", fill='black')
    
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

def test_ocr():
    """Тест OCR запроса"""
    print("=" * 60)
    print("ТЕСТ OCR ЗАПРОСА")
    print("=" * 60)
    print()
    
    # Health check
    print("1. Health Check...")
    try:
        response = requests.get(
            f"{BASE_URL}/health",
            headers={"Authorization": f"Bearer {API_KEY}"},
            timeout=10
        )
        print(f"   ✅ Status: {response.status_code}")
        data = response.json()
        print(f"   ✅ PaddleOCR: {data.get('paddleocr')}")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        return
    
    print()
    print("2. Создание тестового изображения...")
    img_base64 = create_test_image()
    print(f"   ✅ Изображение создано (Base64 длина: {len(img_base64)})")
    
    print()
    print("3. Отправка OCR запроса...")
    print("   ⚠️  Это может занять 1-2 минуты (инициализация модели)...")
    print()
    
    start_time = time.time()
    
    try:
        response = requests.post(
            f"{BASE_URL}/ocr",
            data={"image_base64": img_base64},
            headers={"Authorization": f"Bearer {API_KEY}"},
            timeout=300  # 5 минут
        )
        
        elapsed = time.time() - start_time
        print(f"   Время выполнения: {elapsed:.2f} секунд")
        print(f"   Статус: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Успешно!")
            print(f"   Результат: {result.get('status', 'N/A')}")
        else:
            print(f"   ❌ Ошибка: {response.status_code}")
            print(f"   Ответ: {response.text[:500]}")
            
    except requests.Timeout:
        print(f"   ❌ Timeout после {time.time() - start_time:.2f} секунд")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_ocr()


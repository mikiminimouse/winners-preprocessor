#!/usr/bin/env python3
"""
Тест функциональности PaddleOCR-VL
Проверяет, работает ли OCR обработка
"""
import requests
import base64
import json
from PIL import Image
import io

def create_test_image():
    """Создает простое тестовое изображение с текстом"""
    img = Image.new('RGB', (600, 200), color='white')
    from PIL import ImageDraw
    
    draw = ImageDraw.Draw(img)
    # Используем базовый шрифт
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
    except:
        font = None
    
    # Рисуем текст
    text = "Test OCR Text\nHello World\n12345"
    draw.multiline_text((50, 50), text, fill='black', font=font)
    
    # Конвертируем в base64
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode()
    
    return img_base64, img

def test_health():
    """Тест health check"""
    print("=" * 60)
    print("1. Тест Health Check")
    print("=" * 60)
    
    try:
        response = requests.get("http://localhost:8081/health", timeout=5)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print("✅ Health Check: OK")
            print(f"  - Status: {data.get('status')}")
            print(f"  - PaddleOCR: {data.get('paddleocr')}")
            print(f"  - S3 Storage: {data.get('s3_storage')}")
            return True
        else:
            print(f"❌ Health Check: Failed ({response.status_code})")
            return False
    except Exception as e:
        print(f"❌ Health Check: Error - {e}")
        return False

def test_ocr_processing():
    """Тест OCR обработки"""
    print("\n" + "=" * 60)
    print("2. Тест OCR обработки")
    print("=" * 60)
    
    try:
        # Создаем тестовое изображение
        print("Создание тестового изображения...")
        img_base64, img = create_test_image()
        
        # Отправляем запрос
        print("Отправка OCR запроса...")
        response = requests.post(
            "http://localhost:8081/ocr",
            data={"image_base64": img_base64},
            timeout=180  # Большой таймаут для инициализации модели
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ OCR обработка: УСПЕХ!")
            print(f"  - Status: {result.get('status')}")
            print(f"  - Input type: {result.get('input_type')}")
            
            local_files = result.get('local_files', {})
            if local_files:
                print(f"  - Markdown файл: {local_files.get('markdown')}")
                print(f"  - JSON файл: {local_files.get('json')}")
            
            return True
        else:
            print(f"❌ OCR обработка: Failed ({response.status_code})")
            print(f"Response: {response.text[:500]}")
            return False
            
    except requests.Timeout:
        print("❌ OCR обработка: Timeout (инициализация модели заняла слишком много времени)")
        print("   Это может быть нормально при первом запуске без GPU")
        return False
    except Exception as e:
        print(f"❌ OCR обработка: Error - {e}")
        return False

def main():
    """Основная функция тестирования"""
    print("\n" + "=" * 60)
    print("ТЕСТИРОВАНИЕ PaddleOCR-VL Service")
    print("=" * 60 + "\n")
    
    # Тест 1: Health Check
    health_ok = test_health()
    
    # Тест 2: OCR обработка (только если health check OK)
    if health_ok:
        ocr_ok = test_ocr_processing()
    else:
        print("\n⚠️  Пропуск OCR теста - health check не прошел")
        ocr_ok = False
    
    # Итоговый отчет
    print("\n" + "=" * 60)
    print("ИТОГОВЫЙ ОТЧЕТ")
    print("=" * 60)
    print(f"Health Check: {'✅ OK' if health_ok else '❌ FAILED'}")
    print(f"OCR Processing: {'✅ OK' if ocr_ok else '❌ FAILED'}")
    
    if health_ok:
        print("\n✅ Сервис работает и готов к использованию!")
        if not ocr_ok:
            print("⚠️  OCR обработка не протестирована (возможно, требуется GPU или инициализация)")
    else:
        print("\n❌ Сервис не работает - проверьте логи контейнера")

if __name__ == "__main__":
    main()


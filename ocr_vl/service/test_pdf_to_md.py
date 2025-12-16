#!/usr/bin/env python3
"""
Тест конвертации PDF в MD формат
Версия 1.0.9
"""
import os
import requests
import base64
import json
from pathlib import Path
from datetime import datetime

BASE_URL = os.getenv("ML_INFERENCE_URL", "https://9525a16c-09c1-4489-87d3-bf1946792a53.modelrun.inference.cloud.ru")
API_KEY = os.getenv("ML_INFERENCE_API_KEY", "ZDRhOWQ3OTAtZjU4MC00MzA2LThhNTgtMDU1NGFlMjE4OWRl.85a830f9340966e0ad1fd1642884c7c8")

def get_headers():
    """Получить заголовки с авторизацией"""
    return {"Authorization": f"Bearer {API_KEY}"}

def test_health():
    """Проверка здоровья сервиса"""
    print("=" * 60)
    print("1. Проверка Health Check")
    print("=" * 60)
    
    try:
        response = requests.get(
            f"{BASE_URL}/health",
            headers=get_headers(),
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Status: {data.get('status')}")
            print(f"✅ PaddleOCR: {data.get('paddleocr')}")
            print(f"✅ S3 Storage: {data.get('s3_storage')}")
            return True
        else:
            print(f"❌ Health Check failed: {response.status_code}")
            print(response.text[:200])
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def convert_pdf_to_images(pdf_path):
    """Конвертирует PDF в изображения"""
    try:
        from pdf2image import convert_from_path
        print(f"Конвертация PDF в изображения: {pdf_path}")
        images = convert_from_path(pdf_path, dpi=300)
        print(f"✅ Получено {len(images)} страниц")
        return images
    except ImportError:
        print("❌ pdf2image не установлен")
        return None
    except Exception as e:
        print(f"❌ Ошибка конвертации PDF: {e}")
        return None

def image_to_base64(image):
    """Конвертирует PIL Image в base64"""
    import io
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

def process_pdf_to_md(pdf_path):
    """Обрабатывает PDF файл и конвертирует в MD"""
    print("\n" + "=" * 60)
    print("2. Конвертация PDF в MD")
    print("=" * 60)
    
    if not Path(pdf_path).exists():
        print(f"❌ Файл не найден: {pdf_path}")
        return False
    
    # Конвертируем PDF в изображения
    images = convert_pdf_to_images(pdf_path)
    if not images:
        return False
    
    print(f"\nОбработка {len(images)} страниц...")
    
    all_results = []
    
    for i, image in enumerate(images, 1):
        print(f"\nОбработка страницы {i}/{len(images)}...")
        
        try:
            # Конвертируем изображение в base64
            img_base64 = image_to_base64(image)
            
            # Отправляем запрос на OCR
            print("Отправка OCR запроса...")
            print("⚠️  Это может занять время (особенно первая страница - инициализация модели)...")
            
            response = requests.post(
                f"{BASE_URL}/ocr",
                data={"image_base64": img_base64},
                headers=get_headers(),
                timeout=600  # 10 минут для обработки
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Страница {i} обработана успешно")
                all_results.append(result)
                
                # Выводим информацию о результатах
                local_files = result.get('local_files', {})
                if local_files:
                    print(f"  - Markdown: {local_files.get('markdown', 'N/A')}")
            else:
                print(f"❌ Ошибка обработки страницы {i}: {response.status_code}")
                print(response.text[:500])
                return False
                
        except requests.Timeout:
            print(f"❌ Timeout при обработке страницы {i}")
            return False
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    print(f"\n✅ Все {len(images)} страниц обработаны успешно!")
    return True

def main():
    """Основная функция"""
    print("\n" + "=" * 60)
    print("ТЕСТИРОВАНИЕ КОНВЕРТАЦИИ PDF В MD")
    print("Версия: 1.0.9")
    print("=" * 60)
    print(f"Base URL: {BASE_URL}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Тест 1: Health Check
    if not test_health():
        print("\n❌ Health Check не прошел, прекращаем тестирование")
        return
    
    # Тест 2: Конвертация PDF
    # Ищем PDF файлы в проекте
    pdf_files = [
        "/root/winners_preprocessor/pilot_winers223/data/pending/_legacy_ready/Протокол_подведения_итогов № 2323-2503691630.pdf",
        "/root/winners_preprocessor/pilot_winers223/data/pending/_legacy_ready/протокол.pdf"
    ]
    
    pdf_found = None
    for pdf_path in pdf_files:
        if Path(pdf_path).exists():
            pdf_found = pdf_path
            break
    
    if not pdf_found:
        print("\n⚠️  PDF файлы не найдены по указанным путям")
        print("Укажите путь к PDF файлу для тестирования")
        return
    
    print(f"\nНайден PDF файл: {pdf_found}")
    
    # Обрабатываем PDF
    success = process_pdf_to_md(pdf_found)
    
    if success:
        print("\n" + "=" * 60)
        print("✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО УСПЕШНО")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО С ОШИБКАМИ")
        print("=" * 60)

if __name__ == "__main__":
    main()


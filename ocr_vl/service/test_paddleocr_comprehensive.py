#!/usr/bin/env python3
"""
Комплексное тестирование PaddleOCR-VL-0.9B
Тестирует: Health Check, OCR обработку, конвертацию PDF в MD
Версия: 1.3.6
Дата: 06.12.2025
"""
import os
import sys
import requests
import base64
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

# Настройки ML Inference
BASE_URL = os.getenv(
    "ML_INFERENCE_URL",
    "https://9525a16c-09c1-4489-87d3-bf1946792a53.modelrun.inference.cloud.ru"
).rstrip("/")

API_KEY = os.getenv(
    "ML_INFERENCE_API_KEY",
    "ZDRhOWQ3OTAtZjU4MC00MzA2LThhNTgtMDU1NGFlMjE4OWRl.85a830f9340966e0ad1fd1642884c7c8"
)

REQUEST_TIMEOUT = 600  # 10 минут для OCR обработки
HEALTH_TIMEOUT = 10

def get_headers():
    """Получить заголовки с авторизацией"""
    return {"Authorization": f"Bearer {API_KEY}"}

class TestResults:
    """Класс для хранения результатов тестирования"""
    def __init__(self):
        self.results = []
        self.errors = []
        self.start_time = time.time()
    
    def add_result(self, test_name: str, success: bool, message: str = "", details: Dict = None):
        """Добавить результат теста"""
        self.results.append({
            "test": test_name,
            "success": success,
            "message": message,
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        })
        if not success:
            self.errors.append(f"{test_name}: {message}")
    
    def print_summary(self):
        """Вывести итоговый отчет"""
        elapsed = time.time() - self.start_time
        passed = sum(1 for r in self.results if r["success"])
        total = len(self.results)
        
        print("\n" + "=" * 70)
        print("ИТОГОВЫЙ ОТЧЕТ ТЕСТИРОВАНИЯ PADDLEOCR-VL-0.9B")
        print("=" * 70)
        print(f"Всего тестов: {total}")
        print(f"Успешных: {passed} ✅")
        print(f"Неудачных: {total - passed} ❌")
        print(f"Время выполнения: {elapsed:.2f} секунд")
        print(f"Base URL: {BASE_URL}")
        
        if self.errors:
            print("\n" + "=" * 70)
            print("ОШИБКИ:")
            print("=" * 70)
            for error in self.errors:
                print(f"  ❌ {error}")
        
        print("\n" + "=" * 70)
        print("ДЕТАЛЬНЫЕ РЕЗУЛЬТАТЫ:")
        print("=" * 70)
        for result in self.results:
            status = "✅" if result["success"] else "❌"
            print(f"{status} {result['test']}: {result['message']}")
            if result["details"]:
                for key, value in result["details"].items():
                    print(f"     {key}: {value}")

def test_health(results: TestResults):
    """Тест 1: Health Check"""
    print("\n" + "=" * 70)
    print("ТЕСТ 1: Health Check")
    print("=" * 70)
    
    try:
        response = requests.get(
            f"{BASE_URL}/health",
            headers=get_headers(),
            timeout=HEALTH_TIMEOUT
        )
        
        if response.status_code == 200:
            data = response.json()
            status = data.get('status')
            paddleocr_status = data.get('paddleocr')
            
            print(f"✅ Status: {status}")
            print(f"✅ PaddleOCR: {paddleocr_status}")
            print(f"✅ S3 Storage: {data.get('s3_storage', 'N/A')}")
            
            results.add_result(
                "Health Check",
                True,
                f"Status: {status}, PaddleOCR: {paddleocr_status}",
                data
            )
            return True
        else:
            error_msg = response.text[:200]
            results.add_result(
                "Health Check",
                False,
                f"HTTP {response.status_code}: {error_msg}"
            )
            return False
    except Exception as e:
        results.add_result("Health Check", False, f"Exception: {str(e)}")
        return False

def test_ocr_multipart(results: TestResults):
    """Тест 2: OCR обработка через Multipart (рекомендуемый способ)"""
    print("\n" + "=" * 70)
    print("ТЕСТ 2: OCR обработка (Multipart Upload)")
    print("=" * 70)
    
    try:
        from PIL import Image, ImageDraw
        import io
        
        # Создаем тестовое изображение с текстом
        print("Создание тестового изображения...")
        img = Image.new('RGB', (800, 300), color='white')
        draw = ImageDraw.Draw(img)
        
        # Рисуем текст для тестирования OCR
        text_lines = [
            "Тест OCR PaddleOCR-VL-0.9B",
            "Распознавание текста",
            "12345 67890",
            "Test Document",
            "Пример текста на русском языке"
        ]
        y_offset = 50
        for line in text_lines:
            draw.text((50, y_offset), line, fill='black')
            y_offset += 40
        
        # Сохраняем в BytesIO
        temp_file = io.BytesIO()
        img.save(temp_file, format='PNG')
        temp_file.seek(0)
        
        print("Отправка файла через multipart...")
        start_time = time.time()
        
        files = {'file': ('test_ocr_image.png', temp_file, 'image/png')}
        response = requests.post(
            f"{BASE_URL}/ocr",
            files=files,
            headers=get_headers(),
            timeout=REQUEST_TIMEOUT
        )
        
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ OCR обработка завершена за {elapsed:.2f} сек")
            
            # Проверяем наличие результатов
            local_files = result.get('local_files', {})
            if local_files:
                print(f"✅ Markdown файл: {local_files.get('markdown', 'N/A')}")
                print(f"✅ JSON файл: {local_files.get('json', 'N/A')}")
            
            results.add_result(
                "OCR Multipart",
                True,
                f"Успешно обработано за {elapsed:.2f} сек",
                {
                    "status": result.get("status"),
                    "input_type": result.get("input_type"),
                    "time_seconds": f"{elapsed:.2f}",
                    "has_results": bool(local_files)
                }
            )
            return True
        else:
            error_msg = response.text[:500]
            print(f"❌ Ошибка: HTTP {response.status_code}")
            print(f"   {error_msg}")
            results.add_result(
                "OCR Multipart",
                False,
                f"HTTP {response.status_code}: {error_msg[:200]}"
            )
            return False
            
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Exception: {error_msg}")
        import traceback
        traceback.print_exc()
        results.add_result("OCR Multipart", False, f"Exception: {error_msg}")
        return False

def test_pdf_to_md_multipart(results: TestResults, pdf_path: Optional[str] = None):
    """Тест 3: Конвертация PDF в MD через Multipart (рекомендуемый способ)"""
    print("\n" + "=" * 70)
    print("ТЕСТ 3: Конвертация PDF в MD (Multipart)")
    print("=" * 70)
    
    # Ищем PDF файлы
    if not pdf_path:
        pdf_candidates = [
            "/root/winners_preprocessor/input/test_document.pdf",
            "/root/winners_preprocessor/pilot_winers223/data/pending/_legacy_ready/протокол.pdf",
            "/root/winners_preprocessor/pilot_winers223/data/pending/_legacy_ready/Протокол_подведения_итогов № 2323-2503691630.pdf",
            "/root/winners_preprocessor/final_pilot_Winers223/data/input/UNIT_f037caebc68b4368/протокол.pdf",
        ]
        
        for candidate in pdf_candidates:
            if Path(candidate).exists():
                pdf_path = candidate
                break
    
    if not pdf_path or not Path(pdf_path).exists():
        results.add_result(
            "PDF to MD (Multipart)",
            False,
            "PDF файл не найден для тестирования"
        )
        print("⚠️  PDF файлы не найдены. Укажите путь к PDF файлу:")
        print("   python3 test_paddleocr_comprehensive.py /path/to/file.pdf")
        return False
    
    try:
        from pdf2image import convert_from_path
        from PIL import Image
        import io
        
        print(f"📄 Обработка PDF: {Path(pdf_path).name}")
        print(f"   Полный путь: {pdf_path}")
        
        # Конвертируем PDF в изображения
        print("Конвертация PDF в изображения...")
        images = convert_from_path(pdf_path, dpi=200)  # DPI 200 для скорости
        print(f"✅ Получено {len(images)} страниц")
        
        # Обрабатываем первые 2 страницы для теста
        max_pages = min(2, len(images))
        print(f"Обрабатываем первые {max_pages} страниц(ы) для теста...")
        
        all_results = []
        total_time = 0
        
        for i, image in enumerate(images[:max_pages], 1):
            print(f"\n📄 Обработка страницы {i}/{max_pages}...")
            
            try:
                # Сохраняем изображение в BytesIO для multipart
                temp_file = io.BytesIO()
                image.save(temp_file, format='PNG')
                temp_file.seek(0)
                
                print("Отправка OCR запроса через multipart...")
                page_start = time.time()
                
                files = {'file': (f'page_{i}.png', temp_file, 'image/png')}
                response = requests.post(
                    f"{BASE_URL}/ocr",
                    files=files,
                    headers=get_headers(),
                    timeout=REQUEST_TIMEOUT
                )
                
                page_time = time.time() - page_start
                total_time += page_time
                
                if response.status_code == 200:
                    result = response.json()
                    all_results.append(result)
                    print(f"✅ Страница {i} обработана за {page_time:.2f} сек")
                    
                    local_files = result.get('local_files', {})
                    if local_files:
                        md_file = local_files.get('markdown', 'N/A')
                        print(f"   📄 Markdown: {Path(md_file).name if md_file != 'N/A' else 'N/A'}")
                else:
                    error_msg = response.text[:500]
                    print(f"❌ Ошибка обработки страницы {i}: HTTP {response.status_code}")
                    print(f"   {error_msg}")
                    results.add_result(
                        "PDF to MD (Multipart)",
                        False,
                        f"Ошибка обработки страницы {i}: HTTP {response.status_code}",
                        {"error": error_msg, "page": i}
                    )
                    return False
                    
            except requests.Timeout:
                print(f"❌ Timeout при обработке страницы {i}")
                results.add_result(
                    "PDF to MD (Multipart)",
                    False,
                    f"Timeout при обработке страницы {i}"
                )
                return False
            except Exception as e:
                print(f"❌ Ошибка: {e}")
                import traceback
                traceback.print_exc()
                results.add_result(
                    "PDF to MD (Multipart)",
                    False,
                    f"Exception на странице {i}: {str(e)}"
                )
                return False
        
        print(f"\n✅ Все {max_pages} страниц обработаны успешно!")
        print(f"⏱️  Общее время: {total_time:.2f} сек")
        print(f"⏱️  Среднее время на страницу: {total_time/max_pages:.2f} сек")
        
        results.add_result(
            "PDF to MD (Multipart)",
            True,
            f"Успешно обработано {max_pages} страниц за {total_time:.2f} сек",
            {
                "pdf_file": Path(pdf_path).name,
                "pages_processed": max_pages,
                "total_pages": len(images),
                "total_time_seconds": f"{total_time:.2f}",
                "avg_time_per_page": f"{total_time/max_pages:.2f}"
            }
        )
        return True
        
    except ImportError as e:
        results.add_result(
            "PDF to MD (Multipart)",
            False,
            f"Не установлена библиотека: {str(e)}"
        )
        print(f"❌ Не установлена библиотека: {e}")
        print("   Установите: pip install pdf2image")
        return False
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Exception: {error_msg}")
        import traceback
        traceback.print_exc()
        results.add_result(
            "PDF to MD (Multipart)",
            False,
            f"Exception: {error_msg}"
        )
        return False

def test_service_info(results: TestResults):
    """Тест 4: Информация о сервисе"""
    print("\n" + "=" * 70)
    print("ТЕСТ 4: Информация о сервисе")
    print("=" * 70)
    
    try:
        response = requests.get(
            f"{BASE_URL}/",
            headers=get_headers(),
            timeout=HEALTH_TIMEOUT
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Service: {data.get('service', 'N/A')}")
            print(f"✅ Version: {data.get('version', 'N/A')}")
            
            results.add_result(
                "Service Info",
                True,
                f"Service: {data.get('service')}, Version: {data.get('version')}",
                data
            )
            return True
        else:
            results.add_result(
                "Service Info",
                False,
                f"HTTP {response.status_code}"
            )
            return False
    except Exception as e:
        results.add_result("Service Info", False, f"Exception: {str(e)}")
        return False

def main():
    """Основная функция тестирования"""
    print("=" * 70)
    print("КОМПЛЕКСНОЕ ТЕСТИРОВАНИЕ PADDLEOCR-VL-0.9B")
    print("=" * 70)
    print(f"Версия сервиса: 1.3.6")
    print(f"Base URL: {BASE_URL}")
    print(f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Тестирование модели: PaddleOCR-VL-0.9B")
    print(f"Компоненты: PP-DocLayoutV2 + PaddleOCR-VL-0.9B")
    
    results = TestResults()
    
    # Тест 1: Health Check
    print("\n" + "🔍 Начинаем тестирование...")
    if not test_health(results):
        print("\n⚠️  Health Check не прошел, но продолжаем тестирование...")
    
    # Тест 2: OCR Multipart
    test_ocr_multipart(results)
    
    # Тест 3: PDF to MD через Multipart
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else None
    test_pdf_to_md_multipart(results, pdf_path)
    
    # Тест 4: Service Info
    test_service_info(results)
    
    # Выводим итоговый отчет
    results.print_summary()
    
    # Сохраняем результаты в файл
    report_dir = Path(__file__).parent / "test_results"
    report_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = report_dir / f"test_report_paddleocr_{timestamp}.json"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump({
            "test_run": {
                "timestamp": datetime.now().isoformat(),
                "base_url": BASE_URL,
                "service_version": "1.3.6",
                "model": "PaddleOCR-VL-0.9B"
            },
            "summary": {
                "total": len(results.results),
                "passed": sum(1 for r in results.results if r["success"]),
                "failed": sum(1 for r in results.results if not r["success"]),
                "duration_seconds": time.time() - results.start_time
            },
            "results": results.results,
            "errors": results.errors
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 Детальный отчет сохранен: {report_file}")
    
    # Возвращаем код выхода
    if results.errors:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()


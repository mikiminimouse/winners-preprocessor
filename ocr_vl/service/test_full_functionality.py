#!/usr/bin/env python3
"""
Комплексный тест функциональности PaddleOCR-VL сервиса
Тестирует: Health Check, Base64, URL, Multipart, PDF to MD
"""
import os
import sys
import requests
import base64
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

BASE_URL = os.getenv("ML_INFERENCE_URL", "https://9525a16c-09c1-4489-87d3-bf1946792a53.modelrun.inference.cloud.ru")
API_KEY = os.getenv("ML_INFERENCE_API_KEY", "ZDRhOWQ3OTAtZjU4MC00MzA2LThhNTgtMDU1NGFlMjE4OWRl.85a830f9340966e0ad1fd1642884c7c8")

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
        print("ИТОГОВЫЙ ОТЧЕТ ТЕСТИРОВАНИЯ")
        print("=" * 70)
        print(f"Всего тестов: {total}")
        print(f"Успешных: {passed} ✅")
        print(f"Неудачных: {total - passed} ❌")
        print(f"Время выполнения: {elapsed:.2f} секунд")
        
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
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            results.add_result(
                "Health Check",
                True,
                f"Status: {data.get('status')}, PaddleOCR: {data.get('paddleocr')}",
                data
            )
            return True
        else:
            results.add_result(
                "Health Check",
                False,
                f"HTTP {response.status_code}: {response.text[:200]}"
            )
            return False
    except Exception as e:
        results.add_result("Health Check", False, f"Exception: {str(e)}")
        return False

def create_test_image_base64():
    """Создать тестовое изображение в Base64"""
    try:
        from PIL import Image, ImageDraw
        img = Image.new('RGB', (400, 150), color='white')
        draw = ImageDraw.Draw(img)
        draw.text((20, 50), "Test OCR Document\nSample Text 123", fill='black')
        
        import io
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()
    except Exception as e:
        print(f"Ошибка создания тестового изображения: {e}")
        return None

def test_ocr_base64(results: TestResults):
    """Тест 2: OCR с Base64"""
    print("\n" + "=" * 70)
    print("ТЕСТ 2: OCR обработка (Base64)")
    print("=" * 70)
    
    try:
        img_base64 = create_test_image_base64()
        if not img_base64:
            results.add_result("OCR Base64", False, "Не удалось создать тестовое изображение")
            return False
        
        print("Отправка запроса...")
        start_time = time.time()
        
        response = requests.post(
            f"{BASE_URL}/ocr",
            data={"image_base64": img_base64},
            headers=get_headers(),
            timeout=300
        )
        
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            results.add_result(
                "OCR Base64",
                True,
                f"Успешно обработано за {elapsed:.2f} сек",
                {
                    "status": result.get("status"),
                    "input_type": result.get("input_type"),
                    "time_seconds": f"{elapsed:.2f}"
                }
            )
            return True
        else:
            error_msg = response.text[:500]
            results.add_result(
                "OCR Base64",
                False,
                f"HTTP {response.status_code}: {error_msg}",
                {"response": error_msg}
            )
            return False
            
    except requests.Timeout:
        results.add_result("OCR Base64", False, "Timeout (превышено время ожидания)")
        return False
    except Exception as e:
        results.add_result("OCR Base64", False, f"Exception: {str(e)}")
        return False

def test_ocr_multipart(results: TestResults):
    """Тест 3: OCR с Multipart upload"""
    print("\n" + "=" * 70)
    print("ТЕСТ 3: OCR обработка (Multipart)")
    print("=" * 70)
    
    try:
        from PIL import Image
        import io
        
        # Создаем тестовое изображение
        img = Image.new('RGB', (400, 150), color='white')
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        draw.text((20, 50), "Test Multipart Upload", fill='black')
        
        # Сохраняем во временный файл
        temp_file = io.BytesIO()
        img.save(temp_file, format='PNG')
        temp_file.seek(0)
        
        print("Отправка файла через multipart...")
        start_time = time.time()
        
        files = {'file': ('test_image.png', temp_file, 'image/png')}
        response = requests.post(
            f"{BASE_URL}/ocr",
            files=files,
            headers=get_headers(),
            timeout=300
        )
        
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            results.add_result(
                "OCR Multipart",
                True,
                f"Успешно обработано за {elapsed:.2f} сек",
                {
                    "status": result.get("status"),
                    "input_type": result.get("input_type"),
                    "time_seconds": f"{elapsed:.2f}"
                }
            )
            return True
        else:
            error_msg = response.text[:500]
            results.add_result(
                "OCR Multipart",
                False,
                f"HTTP {response.status_code}: {error_msg}"
            )
            return False
            
    except Exception as e:
        results.add_result("OCR Multipart", False, f"Exception: {str(e)}")
        return False

def test_pdf_to_md(results: TestResults, pdf_path: Optional[str] = None):
    """Тест 4: Конвертация PDF в MD"""
    print("\n" + "=" * 70)
    print("ТЕСТ 4: Конвертация PDF в MD")
    print("=" * 70)
    
    # Ищем PDF файлы
    if not pdf_path:
        pdf_candidates = [
            "/root/winners_preprocessor/pilot_winers223/data/pending/_legacy_ready/Протокол_подведения_итогов № 2323-2503691630.pdf",
            "/root/winners_preprocessor/pilot_winers223/data/pending/_legacy_ready/протокол.pdf",
            "/root/winners_preprocessor/input/test_document.pdf",
        ]
        
        for candidate in pdf_candidates:
            if Path(candidate).exists():
                pdf_path = candidate
                break
    
    if not pdf_path or not Path(pdf_path).exists():
        results.add_result(
            "PDF to MD",
            False,
            "PDF файл не найден для тестирования"
        )
        return False
    
    try:
        from pdf2image import convert_from_path
        from PIL import Image
        import io
        
        print(f"Обработка PDF: {Path(pdf_path).name}")
        print("Конвертация PDF в изображения...")
        
        # Конвертируем PDF в изображения
        images = convert_from_path(pdf_path, dpi=200)  # Уменьшаем DPI для скорости
        print(f"✅ Получено {len(images)} страниц")
        
        # Обрабатываем только первые 2 страницы для теста (чтобы не тратить много времени)
        max_pages = min(2, len(images))
        print(f"Обрабатываем первые {max_pages} страниц(ы) для теста...")
        
        all_results = []
        total_time = 0
        
        for i, image in enumerate(images[:max_pages], 1):
            print(f"\nОбработка страницы {i}/{max_pages}...")
            
            # Конвертируем в base64
            buffered = io.BytesIO()
            image.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode()
            
            print("Отправка OCR запроса...")
            page_start = time.time()
            
            response = requests.post(
                f"{BASE_URL}/ocr",
                data={"image_base64": img_base64},
                headers=get_headers(),
                timeout=600
            )
            
            page_time = time.time() - page_start
            total_time += page_time
            
            if response.status_code == 200:
                result = response.json()
                all_results.append(result)
                print(f"✅ Страница {i} обработана за {page_time:.2f} сек")
            else:
                error_msg = response.text[:500]
                results.add_result(
                    "PDF to MD",
                    False,
                    f"Ошибка обработки страницы {i}: HTTP {response.status_code}",
                    {"error": error_msg, "page": i}
                )
                return False
        
        results.add_result(
            "PDF to MD",
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
        
    except ImportError:
        results.add_result("PDF to MD", False, "pdf2image не установлен")
        return False
    except Exception as e:
        results.add_result("PDF to MD", False, f"Exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_docs_endpoint(results: TestResults):
    """Тест 5: Проверка endpoints документации"""
    print("\n" + "=" * 70)
    print("ТЕСТ 5: Endpoints документации")
    print("=" * 70)
    
    endpoints = [
        ("/", "Root endpoint"),
        ("/docs", "Swagger UI"),
        ("/redoc", "ReDoc"),
        ("/openapi.json", "OpenAPI schema"),
    ]
    
    success_count = 0
    for path, name in endpoints:
        try:
            response = requests.get(
                f"{BASE_URL}{path}",
                headers=get_headers(),
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"✅ {name}: доступен")
                success_count += 1
            else:
                print(f"⚠️  {name}: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"❌ {name}: {str(e)}")
    
    results.add_result(
        "Documentation Endpoints",
        success_count == len(endpoints),
        f"Доступно {success_count}/{len(endpoints)} endpoints",
        {"available": success_count, "total": len(endpoints)}
    )
    
    return success_count == len(endpoints)

def main():
    """Основная функция тестирования"""
    print("=" * 70)
    print("КОМПЛЕКСНОЕ ТЕСТИРОВАНИЕ PADDLEOCR-VL СЕРВИСА")
    print("=" * 70)
    print(f"Base URL: {BASE_URL}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = TestResults()
    
    # Тест 1: Health Check
    if not test_health(results):
        print("\n⚠️  Health Check не прошел, но продолжаем тестирование...")
    
    # Тест 2: OCR Base64
    test_ocr_base64(results)
    
    # Тест 3: OCR Multipart
    test_ocr_multipart(results)
    
    # Тест 4: PDF to MD
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else None
    test_pdf_to_md(results, pdf_path)
    
    # Тест 5: Documentation endpoints
    test_docs_endpoint(results)
    
    # Выводим итоговый отчет
    results.print_summary()
    
    # Сохраняем результаты в файл
    report_file = Path(__file__).parent / "test_results" / f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_file.parent.mkdir(exist_ok=True)
    
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump({
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



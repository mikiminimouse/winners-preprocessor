#!/usr/bin/env python3
"""
Тестирование конвертации PDF через PaddleOCR-VL ML Inference
Обрабатывает PDF файлы, конвертируя их в изображения и отправляя на OCR
"""
import os
import sys
import json
import time
import base64
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

import requests
from pdf2image import convert_from_path
from PIL import Image
import io

# Настройки ML Inference
ML_INFERENCE_URL = os.getenv(
    "ML_INFERENCE_URL",
    "https://c5b0e67c-1426-48e5-b2cd-c86c0acdb5c3.modelrun.inference.cloud.ru"
).rstrip("/")

# API Key для авторизации
ML_INFERENCE_API_KEY = os.getenv(
    "ML_INFERENCE_API_KEY",
    "ZDRhOWQ3OTAtZjU4MC00MzA2LThhNTgtMDU1NGFlMjE4OWRl.85a830f9340966e0ad1fd1642884c7c8"
)

# Таймауты
REQUEST_TIMEOUT = 300  # 5 минут для обработки
HEALTH_CHECK_TIMEOUT = 10


def get_headers() -> dict:
    """Возвращает заголовки с авторизацией"""
    return {
        "Authorization": f"Bearer {ML_INFERENCE_API_KEY}",
        "Accept": "application/json"
    }


def check_health() -> bool:
    """Проверка доступности ML Inference сервиса"""
    try:
        response = requests.get(
            f"{ML_INFERENCE_URL}/health",
            headers=get_headers(),
            timeout=HEALTH_CHECK_TIMEOUT
        )
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ Health check: {health_data}")
            return health_data.get("status") == "healthy"
        else:
            print(f"❌ Health check failed: {response.status_code}")
            print(f"   Ответ: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False


def pdf_to_images(pdf_path: Path, dpi: int = 200) -> list[Image.Image]:
    """Конвертирует PDF в список изображений (по страницам)"""
    try:
        print(f"📄 Конвертация PDF в изображения: {pdf_path.name}")
        images = convert_from_path(str(pdf_path), dpi=dpi)
        print(f"   Извлечено страниц: {len(images)}")
        return images
    except Exception as e:
        print(f"❌ Ошибка конвертации PDF: {e}")
        raise


def image_to_base64(image: Image.Image) -> str:
    """Конвертирует PIL Image в Base64 строку"""
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    img_bytes = buffer.getvalue()
    return base64.b64encode(img_bytes).decode('utf-8')


def process_image_via_ocr(image: Image.Image, page_num: int, total_pages: int) -> Optional[Dict[str, Any]]:
    """Отправляет изображение на OCR обработку"""
    try:
        print(f"   📤 Отправка страницы {page_num}/{total_pages} на OCR...")
        
        # Конвертируем в Base64
        image_base64 = image_to_base64(image)
        
        # Отправляем запрос
        start_time = time.time()
        response = requests.post(
            f"{ML_INFERENCE_URL}/ocr",
            headers=get_headers(),
            data={"image_base64": f"data:image/png;base64,{image_base64}"},
            timeout=REQUEST_TIMEOUT
        )
        elapsed_time = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            print(f"      ✅ Страница {page_num} обработана за {elapsed_time:.2f}s")
            return {
                "page": page_num,
                "status": "success",
                "processing_time": elapsed_time,
                "result": result
            }
        else:
            print(f"      ❌ Ошибка обработки страницы {page_num}: {response.status_code}")
            print(f"         Ответ: {response.text[:200]}")
            return {
                "page": page_num,
                "status": "error",
                "error": f"HTTP {response.status_code}: {response.text[:200]}",
                "processing_time": elapsed_time
            }
            
    except Exception as e:
        print(f"      ❌ Исключение при обработке страницы {page_num}: {e}")
        return {
            "page": page_num,
            "status": "error",
            "error": str(e)
        }


def process_pdf_file(pdf_path: Path, max_pages: Optional[int] = None) -> Dict[str, Any]:
    """Обрабатывает PDF файл через OCR"""
    print(f"\n{'='*60}")
    print(f"📄 ОБРАБОТКА PDF: {pdf_path.name}")
    print(f"{'='*60}")
    
    start_time = time.time()
    results = {
        "file": str(pdf_path),
        "file_size": pdf_path.stat().st_size,
        "timestamp": datetime.now().isoformat(),
        "pages": [],
        "summary": {}
    }
    
    try:
        # Конвертируем PDF в изображения
        images = pdf_to_images(pdf_path)
        
        if max_pages:
            images = images[:max_pages]
            print(f"   Ограничение: обрабатываем первые {len(images)} страниц")
        
        total_pages = len(images)
        results["summary"]["total_pages"] = total_pages
        
        # Обрабатываем каждую страницу
        successful = 0
        failed = 0
        total_processing_time = 0
        
        for idx, image in enumerate(images, 1):
            page_result = process_image_via_ocr(image, idx, total_pages)
            if page_result:
                results["pages"].append(page_result)
                if page_result.get("status") == "success":
                    successful += 1
                    total_processing_time += page_result.get("processing_time", 0)
                else:
                    failed += 1
        
        elapsed_time = time.time() - start_time
        
        # Собираем статистику
        results["summary"].update({
            "successful_pages": successful,
            "failed_pages": failed,
            "total_processing_time": total_processing_time,
            "average_page_time": total_processing_time / successful if successful > 0 else 0,
            "total_elapsed_time": elapsed_time
        })
        
        print(f"\n✅ Обработка завершена:")
        print(f"   Успешно: {successful}/{total_pages} страниц")
        print(f"   Ошибок: {failed}/{total_pages} страниц")
        print(f"   Общее время: {elapsed_time:.2f}s")
        print(f"   Среднее время на страницу: {total_processing_time/successful:.2f}s" if successful > 0 else "")
        
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        results["error"] = str(e)
        results["summary"]["status"] = "failed"
    
    return results


def save_results(results: Dict[str, Any], output_dir: Path):
    """Сохраняет результаты в JSON и Markdown"""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = Path(results["file"]).stem
    
    # Сохраняем JSON
    json_path = output_dir / f"{timestamp}_{base_name}_results.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n💾 Результаты сохранены: {json_path}")
    
    # Сохраняем Markdown отчет
    md_path = output_dir / f"{timestamp}_{base_name}_report.md"
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(f"# Отчет обработки PDF: {base_name}\n\n")
        f.write(f"**Дата:** {results['timestamp']}\n\n")
        f.write(f"**Файл:** {results['file']}\n")
        f.write(f"**Размер:** {results['file_size'] / 1024:.1f} KB\n\n")
        
        summary = results.get("summary", {})
        f.write("## Статистика\n\n")
        f.write(f"- Всего страниц: {summary.get('total_pages', 0)}\n")
        f.write(f"- Успешно обработано: {summary.get('successful_pages', 0)}\n")
        f.write(f"- Ошибок: {summary.get('failed_pages', 0)}\n")
        f.write(f"- Общее время: {summary.get('total_elapsed_time', 0):.2f}s\n")
        f.write(f"- Среднее время на страницу: {summary.get('average_page_time', 0):.2f}s\n\n")
        
        f.write("## Детали по страницам\n\n")
        for page_result in results.get("pages", []):
            f.write(f"### Страница {page_result.get('page')}\n\n")
            f.write(f"- Статус: {page_result.get('status')}\n")
            if page_result.get("status") == "success":
                result_data = page_result.get("result", {})
                f.write(f"- Время обработки: {page_result.get('processing_time', 0):.2f}s\n")
                if "local_files" in result_data:
                    f.write(f"- Локальные файлы: {result_data['local_files']}\n")
                if "s3_files" in result_data:
                    f.write(f"- S3 файлы: {result_data['s3_files']}\n")
            else:
                f.write(f"- Ошибка: {page_result.get('error', 'Unknown')}\n")
            f.write("\n")
    
    print(f"💾 Отчет сохранен: {md_path}")


def main():
    """Основная функция"""
    print("="*60)
    print("🧪 ТЕСТИРОВАНИЕ PADDLEOCR-VL ML INFERENCE")
    print("="*60)
    
    # Проверка health
    print("\n1. Проверка доступности сервиса...")
    if not check_health():
        print("❌ Сервис недоступен. Проверьте ML_INFERENCE_URL")
        sys.exit(1)
    
    # Пути к тестовым файлам
    test_files = [
        Path("/root/winners_preprocessor/pilot_winers223/data/pending/_legacy_ready/Протокол_подведения_итогов № 2323-2503691630.pdf"),
        Path("/root/winners_preprocessor/pilot_winers223/data/pending/_legacy_ready/протокол.pdf")
    ]
    
    # Проверка существования файлов
    existing_files = [f for f in test_files if f.exists()]
    if not existing_files:
        print("❌ Тестовые файлы не найдены")
        sys.exit(1)
    
    print(f"\n2. Найдено файлов для обработки: {len(existing_files)}")
    
    # Директория для результатов
    output_dir = Path("/root/winners_preprocessor/paddle_docker_servise/test_results")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Обработка каждого файла
    all_results = []
    for pdf_file in existing_files:
        try:
            # Ограничиваем до 3 страниц для теста
            result = process_pdf_file(pdf_file, max_pages=3)
            all_results.append(result)
            save_results(result, output_dir)
        except Exception as e:
            print(f"❌ Ошибка при обработке {pdf_file.name}: {e}")
    
    # Итоговый отчет
    print(f"\n{'='*60}")
    print("📊 ИТОГОВЫЙ ОТЧЕТ")
    print(f"{'='*60}")
    
    total_files = len(all_results)
    total_pages = sum(r.get("summary", {}).get("total_pages", 0) for r in all_results)
    total_successful = sum(r.get("summary", {}).get("successful_pages", 0) for r in all_results)
    total_failed = sum(r.get("summary", {}).get("failed_pages", 0) for r in all_results)
    
    print(f"Обработано файлов: {total_files}")
    print(f"Всего страниц: {total_pages}")
    print(f"Успешно: {total_successful}")
    print(f"Ошибок: {total_failed}")
    
    # Сохраняем итоговый отчет
    summary_path = output_dir / f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "ml_inference_url": ML_INFERENCE_URL,
            "total_files": total_files,
            "total_pages": total_pages,
            "successful_pages": total_successful,
            "failed_pages": total_failed,
            "results": all_results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Итоговый отчет: {summary_path}")


if __name__ == "__main__":
    main()


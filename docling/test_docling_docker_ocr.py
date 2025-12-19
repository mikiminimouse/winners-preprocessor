#!/usr/bin/env python3
"""
Тестирование Docling в Docker контейнере:
- OCR для PDF файлов
- Извлечение текста, разметки, таблиц
- Проверка всех компонентов pipeline
"""
import os
import sys
import json
import time
import requests
from pathlib import Path
from typing import Dict, List, Any

# Конфигурация
ROUTER_API = "http://localhost:8080"
DOCLING_API = "http://localhost:8000/process"

def check_services():
    """Проверяет доступность сервисов."""
    print("Проверка доступности сервисов...")
    
    try:
        router_health = requests.get(f"{ROUTER_API}/health", timeout=5)
        if router_health.status_code == 200:
            print("  ✓ Router API доступен")
        else:
            print(f"  ✗ Router API недоступен (status: {router_health.status_code})")
            return False
    except Exception as e:
        print(f"  ✗ Router API недоступен: {e}")
        return False
    
    try:
        docling_health = requests.get(f"{DOCLING_API.replace('/process', '/health')}", timeout=5)
        print("  ✓ Docling API доступен")
    except:
        print("  ⚠ Docling API health endpoint не отвечает (продолжаем)")
    
    return True

def process_file(file_path: Path) -> Dict[str, Any]:
    """Обрабатывает файл через Router -> Docling pipeline."""
    print(f"\nОбработка: {file_path.name}")
    
    # Шаг 1: Отправка в Router
    try:
        with open(file_path, 'rb') as f:
            files = {'file': (file_path.name, f, 'application/pdf')}
            response = requests.post(
                f"{ROUTER_API}/upload",
                files=files,
                timeout=300
            )
        
        if response.status_code != 200:
            return {"error": f"Router HTTP {response.status_code}: {response.text}"}
        
        router_result = response.json()
    except Exception as e:
        return {"error": f"Router error: {e}"}
    
    unit_id = router_result.get("unit_id")
    route = router_result.get("route", "unknown")
    
    print(f"  Router: unit_id={unit_id}, route={route}")
    
    if not unit_id:
        return {"error": "Router не вернул unit_id", "router_result": router_result}
    
    # Шаг 2: Обработка через Docling
    try:
        manifest = router_result.get("manifest", {})
        response = requests.post(
            DOCLING_API,
            json={
                "unit_id": unit_id,
                "manifest": manifest
            },
            timeout=300
        )
        
        if response.status_code != 200:
            return {
                "error": f"Docling HTTP {response.status_code}: {response.text}",
                "unit_id": unit_id,
                "route": route
            }
        
        docling_result = response.json()
    except Exception as e:
        return {"error": f"Docling error: {e}", "unit_id": unit_id, "route": route}
    
    # Шаг 3: Анализ результатов из output
    output_dir = Path("output") / f"UNIT_{unit_id}"
    analysis = {
        "file": file_path.name,
        "unit_id": unit_id,
        "route": route,
        "success": False,
        "text_extracted": False,
        "text_length": 0,
        "tables_found": 0,
        "layout_detected": False,
        "ocr_used": False,
        "method": "unknown",
        "errors": []
    }
    
    if output_dir.exists():
        json_files = list(output_dir.glob("*.json"))
        if json_files:
            try:
                with open(json_files[0], 'r', encoding='utf-8') as f:
                    output_data = json.load(f)
                
                # Анализ данных
                text = output_data.get("text", "")
                if text and len(text.strip()) > 0:
                    analysis["text_extracted"] = True
                    analysis["text_length"] = len(text.strip())
                
                tables = output_data.get("tables", [])
                if isinstance(tables, list):
                    analysis["tables_found"] = len(tables)
                
                layout = output_data.get("layout", {})
                if layout and len(layout) > 0:
                    analysis["layout_detected"] = True
                
                method = output_data.get("processing_method", "unknown")
                analysis["method"] = method
                
                if "ocr" in method.lower() or "docling" in method.lower():
                    analysis["ocr_used"] = True
                
                analysis["success"] = True
            except Exception as e:
                analysis["errors"].append(f"Ошибка чтения output: {e}")
    
    return analysis

def main():
    print("=" * 70)
    print("ТЕСТИРОВАНИЕ DOCLING В DOCKER: OCR, ТЕКСТ, РАЗМЕТКА, ТАБЛИЦЫ")
    print("=" * 70)
    print()
    
    if not check_services():
        print("\n✗ Сервисы недоступны. Убедитесь, что контейнеры запущены:")
        print("  docker-compose up -d")
        return
    
    print()
    
    # Находим тестовые файлы
    print("Поиск тестовых файлов...")
    pdf_files = list(Path("input").glob("*.pdf"))[:10]
    jpeg_files = list(Path("input").glob("*.jpeg")) + list(Path("input").glob("*.jpg"))
    
    print(f"  Найдено PDF: {len(pdf_files)}")
    print(f"  Найдено JPEG: {len(jpeg_files)}")
    print()
    
    # Выбираем файлы для теста
    test_files = []
    
    # Берем несколько PDF (особенно те, что требуют OCR)
    for pdf_file in pdf_files[:5]:
        test_files.append(pdf_file)
    
    # Берем JPEG файлы
    for jpeg_file in jpeg_files[:3]:
        test_files.append(jpeg_file)
    
    print(f"Тестирование {len(test_files)} файлов...")
    print()
    
    results = []
    
    for i, file_path in enumerate(test_files, 1):
        print(f"[{i}/{len(test_files)}] {file_path.name}")
        result = process_file(file_path)
        results.append(result)
        
        # Выводим результаты
        if "error" in result:
            print(f"  ✗ Ошибка: {result['error']}")
        else:
            print(f"  Route: {result.get('route', 'unknown')}")
            print(f"  Method: {result.get('method', 'unknown')}")
            print(f"  Текст: {'✓' if result.get('text_extracted') else '✗'} ({result.get('text_length', 0)} символов)")
            print(f"  Таблицы: {result.get('tables_found', 0)}")
            print(f"  Разметка: {'✓' if result.get('layout_detected') else '✗'}")
            print(f"  OCR: {'✓' if result.get('ocr_used') else '✗'}")
        
        print()
        time.sleep(0.5)
    
    # Итоговая статистика
    print("=" * 70)
    print("ИТОГОВАЯ СТАТИСТИКА")
    print("=" * 70)
    
    successful = sum(1 for r in results if r.get("success", False))
    with_text = sum(1 for r in results if r.get("text_extracted", False))
    with_tables = sum(1 for r in results if r.get("tables_found", 0) > 0)
    with_layout = sum(1 for r in results if r.get("layout_detected", False))
    with_ocr = sum(1 for r in results if r.get("ocr_used", False))
    pdf_scan = sum(1 for r in results if r.get("route") == "pdf_scan")
    pdf_scan_with_text = sum(1 for r in results if r.get("route") == "pdf_scan" and r.get("text_extracted", False))
    
    print(f"Всего файлов: {len(results)}")
    print(f"Успешно обработано: {successful}/{len(results)}")
    print(f"С извлеченным текстом: {with_text}/{len(results)}")
    print(f"С таблицами: {with_tables}/{len(results)}")
    print(f"С разметкой: {with_layout}/{len(results)}")
    print(f"С OCR: {with_ocr}/{len(results)}")
    print()
    print(f"PDF_SCAN файлов: {pdf_scan}")
    print(f"PDF_SCAN с текстом: {pdf_scan_with_text}/{pdf_scan}")
    print()
    
    # Проблемы
    if pdf_scan > 0 and pdf_scan_with_text == 0:
        print("⚠️  ПРОБЛЕМА: PDF_SCAN файлы не извлекают текст!")
        print("   OCR не работает для сканированных PDF.")
    elif pdf_scan_with_text < pdf_scan:
        print(f"⚠️  Частичная проблема: {pdf_scan - pdf_scan_with_text}/{pdf_scan} PDF_SCAN файлов без текста")
    else:
        print("✓ OCR работает корректно для PDF_SCAN файлов")
    
    # Сохраняем отчет
    report_file = f"docling_docker_test_report_{int(time.time())}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": time.time(),
            "total_files": len(results),
            "results": results,
            "statistics": {
                "successful": successful,
                "with_text": with_text,
                "with_tables": with_tables,
                "with_layout": with_layout,
                "with_ocr": with_ocr,
                "pdf_scan": pdf_scan,
                "pdf_scan_with_text": pdf_scan_with_text
            }
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\nОтчет сохранен: {report_file}")
    print("=" * 70)

if __name__ == "__main__":
    main()


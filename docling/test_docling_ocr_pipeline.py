#!/usr/bin/env python3
"""
Тестирование Docling pipeline для обработки PDF и JPEG файлов:
- OCR для сканированных PDF
- Извлечение текста
- Разметка (Layout Analysis)
- Извлечение таблиц
"""
import os
import sys
import json
import time
import requests
from pathlib import Path
from typing import Dict, List, Any
from pypdf import PdfReader

# Конфигурация
DOCLING_API = "http://localhost:8000/process"
ROUTER_API = "http://localhost:8080"

def check_pdf_has_text(pdf_path: Path) -> tuple[bool, int]:
    """Проверяет, есть ли текстовый слой в PDF."""
    try:
        reader = PdfReader(str(pdf_path))
        total_text = 0
        for page in reader.pages[:5]:  # Проверяем первые 5 страниц
            text = page.extract_text()
            if text:
                total_text += len(text.strip())
        return total_text > 100, total_text
    except Exception as e:
        print(f"  Ошибка проверки PDF: {e}")
        return False, 0

def process_file_via_router(file_path: Path) -> Dict[str, Any]:
    """Обрабатывает файл через Router API."""
    print(f"  Отправка в Router API...")
    
    try:
        with open(file_path, 'rb') as f:
            files = {'file': (file_path.name, f, 'application/pdf')}
            response = requests.post(
                f"{ROUTER_API}/preprocess",
                files=files,
                timeout=300
            )
        
        if response.status_code == 200:
            result = response.json()
            return result
        else:
            return {"error": f"HTTP {response.status_code}: {response.text}"}
    except Exception as e:
        return {"error": str(e)}

def process_file_via_docling(unit_id: str, manifest: Dict[str, Any]) -> Dict[str, Any]:
    """Обрабатывает файл через Docling API."""
    print(f"  Отправка в Docling API...")
    
    try:
        response = requests.post(
            DOCLING_API,
            json={
                "unit_id": unit_id,
                "manifest": manifest
            },
            timeout=300
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"HTTP {response.status_code}: {response.text}"}
    except Exception as e:
        return {"error": str(e)}

def analyze_result(result: Dict[str, Any], file_path: Path) -> Dict[str, Any]:
    """Анализирует результат обработки."""
    analysis = {
        "file": file_path.name,
        "success": False,
        "text_extracted": False,
        "text_length": 0,
        "tables_found": 0,
        "layout_detected": False,
        "ocr_used": False,
        "errors": []
    }
    
    # Проверяем результат от Router
    if "unit_id" in result:
        analysis["unit_id"] = result["unit_id"]
        analysis["route"] = result.get("route", "unknown")
        analysis["success"] = True
    
    # Проверяем результат от Docling
    if "processing_result" in result:
        docling_result = result["processing_result"]
        
        # Текст
        if "text" in docling_result:
            text = docling_result["text"]
            if text and len(text.strip()) > 0:
                analysis["text_extracted"] = True
                analysis["text_length"] = len(text.strip())
        
        # Таблицы
        if "tables" in docling_result:
            tables = docling_result["tables"]
            if isinstance(tables, list):
                analysis["tables_found"] = len(tables)
        
        # Разметка
        if "layout" in docling_result:
            layout = docling_result["layout"]
            if layout and len(layout) > 0:
                analysis["layout_detected"] = True
        
        # OCR
        if "method" in docling_result:
            method = docling_result["method"]
            if "ocr" in method.lower():
                analysis["ocr_used"] = True
    
    # Проверяем output файлы
    if "unit_id" in result:
        unit_id = result["unit_id"]
        output_dir = Path("output") / f"UNIT_{unit_id}"
        
        if output_dir.exists():
            json_file = list(output_dir.glob("*.json"))
            md_file = list(output_dir.glob("*.md"))
            
            if json_file:
                try:
                    with open(json_file[0], 'r', encoding='utf-8') as f:
                        output_data = json.load(f)
                        
                        # Дополнительная проверка из output
                        if "text" in output_data:
                            text = output_data["text"]
                            if text and len(text.strip()) > 0:
                                analysis["text_extracted"] = True
                                analysis["text_length"] = len(text.strip())
                        
                        if "tables" in output_data:
                            tables = output_data["tables"]
                            if isinstance(tables, list) and len(tables) > 0:
                                analysis["tables_found"] = len(tables)
                except Exception as e:
                    analysis["errors"].append(f"Ошибка чтения output JSON: {e}")
    
    if "error" in result:
        analysis["errors"].append(result["error"])
        analysis["success"] = False
    
    return analysis

def main():
    print("=" * 70)
    print("ТЕСТИРОВАНИЕ DOCLING PIPELINE: OCR, ТЕКСТ, РАЗМЕТКА, ТАБЛИЦЫ")
    print("=" * 70)
    print()
    
    # Проверяем доступность сервисов
    print("1. Проверка доступности сервисов...")
    try:
        router_health = requests.get(f"{ROUTER_API}/health", timeout=5)
        if router_health.status_code == 200:
            print("   ✓ Router API доступен")
        else:
            print(f"   ✗ Router API недоступен (status: {router_health.status_code})")
            return
    except Exception as e:
        print(f"   ✗ Router API недоступен: {e}")
        return
    
    try:
        docling_health = requests.get(f"{DOCLING_API.replace('/process', '/health')}", timeout=5)
        print("   ✓ Docling API доступен")
    except:
        print("   ⚠ Docling API health endpoint не отвечает (продолжаем)")
    
    print()
    
    # Находим PDF и JPEG файлы
    print("2. Поиск файлов для тестирования...")
    pdf_files = list(Path("input").glob("*.pdf"))
    jpeg_files = list(Path("input").glob("*.jpeg")) + list(Path("input").glob("*.jpg"))
    
    print(f"   Найдено PDF: {len(pdf_files)}")
    print(f"   Найдено JPEG: {len(jpeg_files)}")
    print()
    
    # Выбираем файлы для теста
    test_files = []
    
    # Берем несколько PDF (с текстом и без)
    for pdf_file in pdf_files[:10]:
        has_text, text_len = check_pdf_has_text(pdf_file)
        test_files.append({
            "path": pdf_file,
            "type": "pdf",
            "needs_ocr": not has_text,
            "text_length": text_len
        })
    
    # Берем JPEG файлы
    for jpeg_file in jpeg_files[:5]:
        test_files.append({
            "path": jpeg_file,
            "type": "jpeg",
            "needs_ocr": True,
            "text_length": 0
        })
    
    print(f"3. Тестирование {len(test_files)} файлов...")
    print()
    
    results = []
    
    for i, file_info in enumerate(test_files, 1):
        file_path = file_info["path"]
        file_type = file_info["type"]
        needs_ocr = file_info["needs_ocr"]
        
        print(f"[{i}/{len(test_files)}] {file_path.name}")
        print(f"  Тип: {file_type.upper()}")
        print(f"  Требует OCR: {'Да' if needs_ocr else 'Нет'}")
        
        # Обработка через Router
        router_result = process_file_via_router(file_path)
        
        if "error" in router_result:
            print(f"  ✗ Ошибка Router: {router_result['error']}")
            results.append({
                "file": file_path.name,
                "error": router_result["error"]
            })
            continue
        
        unit_id = router_result.get("unit_id")
        route = router_result.get("route", "unknown")
        
        print(f"  ✓ Router: unit_id={unit_id}, route={route}")
        
        # Обработка через Docling
        if unit_id:
            manifest = router_result.get("manifest", {})
            docling_result = process_file_via_docling(unit_id, manifest)
            
            if "error" in docling_result:
                print(f"  ✗ Ошибка Docling: {docling_result['error']}")
            else:
                print(f"  ✓ Docling: обработано")
            
            # Анализ результата
            analysis = analyze_result({
                **router_result,
                "processing_result": docling_result.get("result", {})
            }, file_path)
            
            results.append(analysis)
            
            # Выводим краткую статистику
            print(f"  Результаты:")
            print(f"    - Текст извлечен: {'✓' if analysis['text_extracted'] else '✗'} ({analysis['text_length']} символов)")
            print(f"    - Таблицы найдены: {analysis['tables_found']}")
            print(f"    - Разметка обнаружена: {'✓' if analysis['layout_detected'] else '✗'}")
            print(f"    - OCR использован: {'✓' if analysis['ocr_used'] else '✗'}")
        
        print()
        time.sleep(0.5)  # Небольшая задержка между файлами
    
    # Итоговая статистика
    print("=" * 70)
    print("ИТОГОВАЯ СТАТИСТИКА")
    print("=" * 70)
    
    successful = sum(1 for r in results if r.get("success", False))
    with_text = sum(1 for r in results if r.get("text_extracted", False))
    with_tables = sum(1 for r in results if r.get("tables_found", 0) > 0)
    with_layout = sum(1 for r in results if r.get("layout_detected", False))
    with_ocr = sum(1 for r in results if r.get("ocr_used", False))
    
    print(f"Всего файлов обработано: {len(results)}")
    print(f"Успешно: {successful}/{len(results)}")
    print(f"С извлеченным текстом: {with_text}/{len(results)}")
    print(f"С таблицами: {with_tables}/{len(results)}")
    print(f"С разметкой: {with_layout}/{len(results)}")
    print(f"С OCR: {with_ocr}/{len(results)}")
    print()
    
    # Сохраняем результаты
    report_file = f"docling_ocr_test_report_{int(time.time())}.json"
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
                "with_ocr": with_ocr
            }
        }, f, ensure_ascii=False, indent=2)
    
    print(f"Отчет сохранен: {report_file}")
    print("=" * 70)

if __name__ == "__main__":
    main()



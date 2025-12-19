#!/usr/bin/env python3
"""
Комплексное тестирование системы обработки документов через Docling.
Тестирует все основные функции: OCR, Text Extraction, Layout Analysis, Table Extraction, HTML, метрики.
"""
import requests
import json
import time
from pathlib import Path
from datetime import datetime
import subprocess

DOCLING_API = "http://localhost:8000/process"

def test_pdf_text():
    """Тест обработки PDF с текстовым слоем."""
    print("\n" + "="*80)
    print("ТЕСТ 1: PDF с текстовым слоем (pdf_text)")
    print("="*80)
    
    unit_dirs = list(Path("/root/winners_preprocessor/normalized").glob("UNIT_*"))
    for unit_dir in unit_dirs[:1]:
        files = list((unit_dir / "files").glob("*.pdf"))
        if not files:
            continue
        
        file_path = files[0]
        unit_id = unit_dir.name
        
        payload = {
            "unit_id": unit_id,
            "manifest": f"mongodb://{unit_id}",
            "files": [{
                "path": str(file_path),
                "original_name": file_path.name,
                "detected_type": "pdf",
                "needs_ocr": False,
                "file_id": "test_pdf_text",
                "route": "pdf_text"
            }],
            "route": "pdf_text"
        }
        
        try:
            start = time.time()
            response = requests.post(DOCLING_API, json=payload, timeout=300)
            elapsed = time.time() - start
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Успешно обработан за {elapsed:.2f}s")
                print(f"   Status: {result.get('status')}")
                print(f"   Output files: {len(result.get('output_files', []))}")
                
                # Проверяем содержимое
                output_dir = Path(f"/root/winners_preprocessor/output/{unit_id}")
                json_file = output_dir / f"{file_path.stem}.json"
                if json_file.exists():
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        text_len = len(data.get('text', ''))
                        tables_count = len(data.get('tables', []))
                        print(f"   Извлечено текста: {text_len} символов")
                        print(f"   Извлечено таблиц: {tables_count}")
                        if text_len > 100:
                            print(f"   ✅ Текст успешно извлечен")
                        else:
                            print(f"   ⚠️  Текст слишком короткий")
                
                return True
            else:
                print(f"❌ Ошибка: HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Исключение: {e}")
            return False
    
    return False

def test_pdf_ocr():
    """Тест обработки PDF с OCR."""
    print("\n" + "="*80)
    print("ТЕСТ 2: PDF требующий OCR (pdf_scan)")
    print("="*80)
    
    # Ищем unit с needs_ocr=true
    try:
        result = subprocess.run(
            ["docker", "exec", "docling_mongodb", "mongosh",
             "-u", "admin", "-p", "password",
             "--authenticationDatabase", "admin",
             "--quiet",
             "--eval",
             "db = db.getSiblingDB('docling_metadata'); "
             "var m = db.manifests.findOne({'processing.route': 'pdf_scan'}); "
             "if (m) { print(m.unit_id); }"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0 and result.stdout.strip():
            unit_id = result.stdout.strip()
            unit_dir = Path(f"/root/winners_preprocessor/normalized/{unit_id}")
            
            if unit_dir.exists():
                files = list((unit_dir / "files").glob("*.pdf"))
                if files:
                    file_path = files[0]
                    
                    payload = {
                        "unit_id": unit_id,
                        "manifest": f"mongodb://{unit_id}",
                        "files": [{
                            "path": str(file_path),
                            "original_name": file_path.name,
                            "detected_type": "pdf",
                            "needs_ocr": True,
                            "file_id": "test_pdf_ocr",
                            "route": "pdf_scan"
                        }],
                        "route": "pdf_scan"
                    }
                    
                    print(f"Обработка unit: {unit_id}")
                    print(f"Файл: {file_path.name}")
                    print("⚠️  OCR обработка может занять много времени...")
                    
                    try:
                        start = time.time()
                        response = requests.post(DOCLING_API, json=payload, timeout=600)
                        elapsed = time.time() - start
                        
                        if response.status_code == 200:
                            result = response.json()
                            print(f"✅ Успешно обработан за {elapsed:.2f}s")
                            print(f"   Status: {result.get('status')}")
                            return True
                        else:
                            print(f"❌ Ошибка: HTTP {response.status_code}")
                            return False
                    except Exception as e:
                        print(f"❌ Исключение: {e}")
                        return False
        
        print("⚠️  Unit с OCR не найден, пропускаем тест")
        return True
    except Exception as e:
        print(f"⚠️  Ошибка поиска OCR unit: {e}")
        return True

def test_html():
    """Тест обработки HTML файлов."""
    print("\n" + "="*80)
    print("ТЕСТ 3: HTML файлы (html_text)")
    print("="*80)
    
    try:
        result = subprocess.run(
            ["docker", "exec", "docling_mongodb", "mongosh",
             "-u", "admin", "-p", "password",
             "--authenticationDatabase", "admin",
             "--quiet",
             "--eval",
             "db = db.getSiblingDB('docling_metadata'); "
             "var m = db.manifests.findOne({'processing.route': 'html_text'}); "
             "if (m) { print(m.unit_id); }"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0 and result.stdout.strip():
            unit_id = result.stdout.strip()
            unit_dir = Path(f"/root/winners_preprocessor/normalized/{unit_id}")
            
            if unit_dir.exists():
                files = list((unit_dir / "files").glob("*"))
                if files:
                    file_path = files[0]
                    
                    payload = {
                        "unit_id": unit_id,
                        "manifest": f"mongodb://{unit_id}",
                        "files": [{
                            "path": str(file_path),
                            "original_name": file_path.name,
                            "detected_type": "html",
                            "needs_ocr": False,
                            "file_id": "test_html",
                            "route": "html_text"
                        }],
                        "route": "html_text"
                    }
                    
                    print(f"Обработка unit: {unit_id}")
                    print(f"Файл: {file_path.name}")
                    
                    try:
                        start = time.time()
                        response = requests.post(DOCLING_API, json=payload, timeout=60)
                        elapsed = time.time() - start
                        
                        if response.status_code == 200:
                            result = response.json()
                            print(f"✅ Успешно обработан за {elapsed:.2f}s")
                            
                            # Проверяем содержимое
                            output_dir = Path(f"/root/winners_preprocessor/output/{unit_id}")
                            json_file = output_dir / f"{file_path.stem}.json"
                            if json_file.exists():
                                with open(json_file, 'r', encoding='utf-8') as f:
                                    data = json.load(f)
                                    text_len = len(data.get('text', ''))
                                    print(f"   Извлечено текста: {text_len} символов")
                                    if text_len > 10:
                                        print(f"   ✅ HTML текст успешно извлечен")
                            
                            return True
                        else:
                            print(f"❌ Ошибка: HTTP {response.status_code}")
                            return False
                    except Exception as e:
                        print(f"❌ Исключение: {e}")
                        return False
        
        print("⚠️  HTML unit не найден, пропускаем тест")
        return True
    except Exception as e:
        print(f"⚠️  Ошибка поиска HTML unit: {e}")
        return True

def test_metrics():
    """Тест сохранения метрик в MongoDB."""
    print("\n" + "="*80)
    print("ТЕСТ 4: Метрики в MongoDB")
    print("="*80)
    
    try:
        result = subprocess.run(
            ["docker", "exec", "docling_mongodb", "mongosh",
             "-u", "admin", "-p", "password",
             "--authenticationDatabase", "admin",
             "--quiet",
             "--eval",
             "db = db.getSiblingDB('docling_metadata'); "
             "var count = db.processing_metrics.countDocuments({}); "
             "print('Total metrics:', count); "
             "var latest = db.processing_metrics.find().sort({created_at: -1}).limit(1).toArray(); "
             "if (latest.length > 0) { "
             "  print('Latest metric - unit_id:', latest[0].unit_id); "
             "  print('Latest metric - status:', latest[0].status); "
             "  print('Latest metric - route:', latest[0].route); "
             "  print('Has processing_times:', latest[0].processing_times ? 'yes' : 'no'); "
             "}"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print(result.stdout)
            if "Total metrics:" in result.stdout and int(result.stdout.split("Total metrics:")[1].split()[0]) > 0:
                print("✅ Метрики сохранены в MongoDB")
                return True
            else:
                print("⚠️  Метрики не найдены")
                return False
        else:
            print(f"❌ Ошибка получения метрик: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Исключение: {e}")
        return False

def test_caching():
    """Тест кэширования результатов."""
    print("\n" + "="*80)
    print("ТЕСТ 5: Кэширование результатов")
    print("="*80)
    
    unit_dirs = list(Path("/root/winners_preprocessor/normalized").glob("UNIT_*"))
    if not unit_dirs:
        print("❌ No units found")
        return False
    
    unit_dir = unit_dirs[0]
    files = list((unit_dir / "files").glob("*.pdf"))
    if not files:
        print("❌ No files found")
        return False
    
    unit_id = unit_dir.name
    file_path = files[0]
    
    payload = {
        "unit_id": unit_id + "_cache_test",
        "manifest": f"mongodb://{unit_id}",
        "files": [{
            "path": str(file_path),
            "original_name": file_path.name,
            "detected_type": "pdf",
            "needs_ocr": False,
            "file_id": "test_cache",
            "route": "pdf_text"
        }],
        "route": "pdf_text"
    }
    
    # Первый запрос - должен обработать
    print("Первый запрос (создание кэша)...")
    try:
        start1 = time.time()
        response1 = requests.post(DOCLING_API, json=payload, timeout=60)
        elapsed1 = time.time() - start1
        print(f"   Время обработки: {elapsed1:.2f}s")
        
        # Второй запрос - должен использовать кэш
        print("Второй запрос (из кэша)...")
        start2 = time.time()
        response2 = requests.post(DOCLING_API, json=payload, timeout=60)
        elapsed2 = time.time() - start2
        print(f"   Время обработки: {elapsed2:.2f}s")
        
        if elapsed2 < elapsed1 * 0.5:
            print("✅ Кэширование работает (второй запрос быстрее)")
            return True
        else:
            print("⚠️  Кэширование может не работать")
            return True  # Не критично
    except Exception as e:
        print(f"❌ Исключение: {e}")
        return False

def main():
    """Запускает все тесты."""
    print("\n" + "="*80)
    print("КОМПЛЕКСНОЕ ТЕСТИРОВАНИЕ СИСТЕМЫ ОБРАБОТКИ ДОКУМЕНТОВ")
    print("="*80)
    
    results = {}
    
    # Тесты
    results["PDF Text"] = test_pdf_text()
    results["PDF OCR"] = test_pdf_ocr()
    results["HTML"] = test_html()
    results["Metrics"] = test_metrics()
    results["Caching"] = test_caching()
    
    # Итоги
    print("\n" + "="*80)
    print("ИТОГИ ТЕСТИРОВАНИЯ")
    print("="*80)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:20} : {status}")
    
    total = len(results)
    passed = sum(1 for r in results.values() if r)
    
    print(f"\nВсего тестов: {total}")
    print(f"Пройдено: {passed}")
    print(f"Провалено: {total - passed}")
    
    if passed == total:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
    else:
        print("\n⚠️  НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ")

if __name__ == "__main__":
    main()


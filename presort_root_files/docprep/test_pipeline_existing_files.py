#!/usr/bin/env python3
"""
Тестирование пайплайна на существующих файлах из input/.
Не требует разархивирования - использует уже имеющиеся файлы.
"""
import os
import sys
import json
import time
import requests
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

# Конфигурация
ROUTER_API = "http://localhost:8080"
DOCLING_API = "http://localhost:8000/process"

# Директория с файлами для теста пайплайна.
# По умолчанию берём корень input/, но можно переопределить:
#   PIPELINE_INPUT_DIR=input/protocols python3 test_pipeline_existing_files.py
PIPELINE_INPUT_DIR = Path(os.environ.get("PIPELINE_INPUT_DIR", "input"))

def check_services():
    """Проверяет доступность сервисов."""
    print("Проверка доступности сервисов...")
    
    # Проверка Router
    try:
        response = requests.get(f"{ROUTER_API}/health", timeout=5)
        if response.status_code == 200:
            print("✓ Router API доступен")
            return True
        else:
            print(f"✗ Router API недоступен (status: {response.status_code})")
            return False
    except Exception as e:
        print(f"✗ Router API недоступен: {e}")
        print("  Запустите router: cd router && python main.py")
        return False

def get_files_from_input():
    """Получает список файлов из PIPELINE_INPUT_DIR (рекурсивно)."""
    if not PIPELINE_INPUT_DIR.exists():
        print(f"✗ Директория {PIPELINE_INPUT_DIR} не найдена")
        return []

    files = [
        f
        for f in PIPELINE_INPUT_DIR.rglob("*")
        if f.is_file() and not f.name.startswith(".")
    ]
    return sorted(files)

def process_file_via_api(file_path: Path):
    """Обрабатывает файл через Router API."""
    try:
        with open(file_path, 'rb') as f:
            files = {'file': (file_path.name, f, 'application/octet-stream')}
            response = requests.post(
                f"{ROUTER_API}/upload",
                files=files,
                timeout=300
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        print(f"  ✗ Ошибка обработки {file_path.name}: {e}")
        return None

def process_all_files(files: List[Path], limit: int = None):
    """Обрабатывает все файлы через пайплайн."""
    if limit:
        files = files[:limit]
    
    print(f"\nОбработка {len(files)} файлов...")
    print("=" * 60)
    
    results = {
        "total": len(files),
        "processed": 0,
        "failed": 0,
        "results": []
    }
    
    start_time = time.time()
    
    for i, file_path in enumerate(files, 1):
        print(f"\n[{i}/{len(files)}] {file_path.name} ({file_path.stat().st_size:,} bytes)")
        
        file_start = time.time()
        result = process_file_via_api(file_path)
        file_time = time.time() - file_start
        
        if result:
            results["processed"] += 1
            results["results"].append({
                "file": file_path.name,
                "status": "success",
                "time": file_time,
                "result": result
            })
            print(f"  ✓ Обработан за {file_time:.2f}с")
        else:
            results["failed"] += 1
            results["results"].append({
                "file": file_path.name,
                "status": "failed",
                "time": file_time
            })
            print(f"  ✗ Ошибка")
    
    total_time = time.time() - start_time
    
    results["total_time"] = total_time
    results["average_time"] = total_time / len(files) if files else 0
    
    return results

def main():
    """Главная функция."""
    print("=" * 60)
    print("ТЕСТИРОВАНИЕ ПАЙПЛАЙНА НА СУЩЕСТВУЮЩИХ ФАЙЛАХ")
    print("=" * 60)
    
    # Проверка сервисов
    if not check_services():
        print("\n⚠️  Сервисы недоступны. Запустите:")
        print("  1. Router: cd router && python main.py")
        print("  2. Docling: cd docling && python main.py")
        sys.exit(1)
    
    # Получаем файлы
    files = get_files_from_input()
    if not files:
        print("✗ Файлы не найдены в input/")
        sys.exit(1)
    
    print(f"\nНайдено файлов в input/: {len(files)}")
    
    # Обрабатываем файлы
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    if limit:
        print(f"Ограничение: {limit} файлов")
    
    results = process_all_files(files, limit)
    
    # Сохраняем результаты
    report_file = f"pipeline_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # Выводим статистику
    print("\n" + "=" * 60)
    print("РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
    print("=" * 60)
    print(f"Всего файлов: {results['total']}")
    print(f"✓ Обработано успешно: {results['processed']}")
    print(f"✗ Ошибок: {results['failed']}")
    print(f"⏱  Общее время: {results['total_time']:.2f}с")
    print(f"⏱  Среднее время на файл: {results['average_time']:.2f}с")
    print(f"\nОтчет сохранен: {report_file}")
    print("=" * 60)

if __name__ == "__main__":
    main()


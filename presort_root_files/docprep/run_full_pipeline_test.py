#!/usr/bin/env python3
"""
Скрипт для полного тестирования pipeline от разархивирования до обработки через Docling.
Собирает детальные метрики по времени обработки и используемым библиотекам.
"""
import os
import sys
import json
import time
import requests
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from pymongo import MongoClient
from collections import defaultdict

# Конфигурация
ROUTER_API = "http://localhost:8080"
DOCLING_API = "http://localhost:8000/process"
MONGO_SERVER = os.environ.get("MONGO_SERVER", "localhost:27017")
MONGO_USER = os.environ.get("MONGO_METADATA_USER", "docling_user")
MONGO_PASSWORD = os.environ.get("MONGO_METADATA_PASSWORD", "password")
MONGO_DB = os.environ.get("MONGO_METADATA_DB", "docling_metadata")

# Глобальные метрики
pipeline_metrics = {
    "started_at": datetime.utcnow().isoformat(),
    "extraction": {},
    "preprocessing": {},
    "docling_processing": {},
    "extensions_stats": {},
    "library_usage": {},
    "stages_timing": {}
}


def get_mongo_client():
    """Получает MongoDB клиент."""
    try:
        # Пробуем разные варианты подключения
        mongo_urls = [
            f'mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_SERVER}/?authSource=admin',
            f'mongodb://{MONGO_USER}:{MONGO_PASSWORD}@mongodb:27017/?authSource=admin',
            f'mongodb://{MONGO_USER}:{MONGO_PASSWORD}@localhost:27017/?authSource=admin'
        ]
        
        for url in mongo_urls:
            try:
                client = MongoClient(url, serverSelectionTimeoutMS=5000)
                # Проверяем подключение
                client.admin.command('ping')
                return client
            except:
                continue
        
        # Fallback через docker exec
        return None
    except Exception as e:
        print(f"⚠️  Ошибка подключения к MongoDB напрямую: {e}")
        return None

def get_mongo_via_docker():
    """Получает данные из MongoDB через docker exec."""
    try:
        result = subprocess.run(
            ["docker", "exec", "docling_mongodb", "mongosh",
             "-u", "admin", "-p", "password",
             "--authenticationDatabase", "admin",
             "--quiet",
             "--eval",
             f"db = db.getSiblingDB('{MONGO_DB}'); JSON.stringify({{metrics: db.processing_metrics.find({{}}).toArray(), manifests: db.manifests.find({{}}).toArray()}})"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            import json
            return json.loads(result.stdout.strip())
        return None
    except Exception as e:
        print(f"⚠️  Ошибка получения данных через docker: {e}")
        return None


def extract_vitaly_rar() -> Dict[str, Any]:
    """Разархивирует Vitaly.rar и собирает метрики."""
    print("\n" + "="*80)
    print("ЭТАП 1: РАЗАРХИВИРОВАНИЕ Vitaly.rar")
    print("="*80)
    
    start_time = time.time()
    input_dir = Path("input")
    input_dir.mkdir(exist_ok=True)
    
    # Проверяем, возможно архив уже распакован
    rar_file = Path("Vitaly.rar")
    if not rar_file.exists():
        # Проверяем, может файлы уже в input/
        extracted_files = [f for f in input_dir.iterdir() if f.is_file()]
        if extracted_files:
            print(f"⚠️  Vitaly.rar не найден, но в input/ уже есть {len(extracted_files)} файлов")
            # Подсчитываем файлы
            files_by_extension = defaultdict(int)
            for f in extracted_files:
                ext = f.suffix.lower() or "no_extension"
                files_by_extension[ext] += 1
            
            metrics = {
                "extraction_time": 0,
                "total_files": len(extracted_files),
                "files_by_extension": dict(files_by_extension),
                "already_extracted": True
            }
            print(f"✅ Используем существующие файлы из input/")
            print(f"Файлы по расширениям:")
            for ext, count in sorted(files_by_extension.items()):
                print(f"  {ext:15} : {count:3} файлов")
            pipeline_metrics["extraction"] = metrics
            return metrics
        print(f"❌ Vitaly.rar не найден и input/ пуст")
        return {}
    
    print(f"Архив: {rar_file} ({rar_file.stat().st_size / 1024 / 1024:.2f} MB)")
    
    # Разархивирование
    try:
        result = subprocess.run(
            ["unrar", "x", "-y", str(rar_file), str(input_dir)],
            capture_output=True, text=True, timeout=300
        )
        if result.returncode != 0:
            result = subprocess.run(
                ["7z", "x", str(rar_file), f"-o{input_dir}", "-y"],
                capture_output=True, text=True, timeout=300
            )
            if result.returncode != 0:
                print(f"❌ Ошибка разархивирования: {result.stderr[:200]}")
                return {}
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return {}
    
    extraction_time = time.time() - start_time
    
    # Подсчет файлов
    extracted_files = [f for f in input_dir.iterdir() if f.is_file()]
    files_by_extension = defaultdict(int)
    for f in extracted_files:
        ext = f.suffix.lower() or "no_extension"
        files_by_extension[ext] += 1
    
    metrics = {
        "extraction_time": extraction_time,
        "total_files": len(extracted_files),
        "files_by_extension": dict(files_by_extension),
        "archive_size_mb": rar_file.stat().st_size / 1024 / 1024
    }
    
    print(f"✅ Извлечено {len(extracted_files)} файлов за {extraction_time:.2f}s")
    print(f"Файлы по расширениям:")
    for ext, count in sorted(files_by_extension.items()):
        print(f"  {ext:15} : {count:3} файлов")
    
    pipeline_metrics["extraction"] = metrics
    return metrics


def run_preprocessing() -> Dict[str, Any]:
    """Запускает preprocessing через Router API."""
    print("\n" + "="*80)
    print("ЭТАП 2: PREPROCESSING (Router)")
    print("="*80)
    
    start_time = time.time()
    
    # Проверка доступности Router
    try:
        response = requests.get(f"{ROUTER_API}/health", timeout=5)
        if response.status_code != 200:
            print("❌ Router API недоступен")
            return {}
        print("✅ Router API доступен")
    except Exception as e:
        print(f"❌ Ошибка подключения к Router: {e}")
        return {}
    
    # Запуск обработки
    print("Запуск обработки всех файлов из input/...")
    try:
        response = requests.post(
            f"{ROUTER_API}/process_now",
            timeout=600  # 10 минут
        )
        if response.status_code != 200:
            print(f"❌ Ошибка обработки: HTTP {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return {}
        
        result = response.json()
        print(f"✅ Preprocessing завершен")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return {}
    
    preprocessing_time = time.time() - start_time
    
    # Получение метрик из MongoDB
    client = get_mongo_client()
    preprocessing_metrics = []
    
    if client:
        db = client[MONGO_DB]
        metrics_collection = db["processing_metrics"]
        # Ждем сохранения метрик (небольшая задержка)
        time.sleep(2)
        preprocessing_metrics = list(metrics_collection.find().sort("created_at", -1).limit(100))
    else:
        # Используем docker exec
        data = get_mongo_via_docker()
        if data:
            preprocessing_metrics = data.get("metrics", [])
    
    metrics = {
        "preprocessing_time": preprocessing_time,
        "units_created": len(preprocessing_metrics),
        "status": "completed"
    }
    
    print(f"✅ Создано unit'ов: {len(preprocessing_metrics)}")
    print(f"Время preprocessing: {preprocessing_time:.2f}s")
    
    pipeline_metrics["preprocessing"] = metrics
    return metrics


def run_docling_processing() -> Dict[str, Any]:
    """Запускает обработку через Docling API."""
    print("\n" + "="*80)
    print("ЭТАП 3: DOCLING PROCESSING")
    print("="*80)
    
    start_time = time.time()
    
    # Проверка доступности Docling - пробуем localhost и docling (для контейнера)
    docling_health_urls = [
        f"{DOCLING_API.replace('/process', '/health')}",
        "http://docling:8000/health",
        "http://localhost:8000/health"
    ]
    
    docling_api_urls = [
        DOCLING_API,
        "http://docling:8000/process",
        "http://localhost:8000/process"
    ]
    
    docling_available = False
    working_api = None
    
    for health_url in docling_health_urls:
        try:
            response = requests.get(health_url, timeout=5)
            if response.status_code == 200:
                print(f"✅ Docling API доступен: {health_url}")
                docling_available = True
                # Находим соответствующий API URL
                for api_url in docling_api_urls:
                    if health_url.replace('/health', '/process') == api_url or \
                       (health_url == "http://docling:8000/health" and api_url == "http://docling:8000/process") or \
                       (health_url == "http://localhost:8000/health" and api_url == "http://localhost:8000/process"):
                        working_api = api_url
                        break
                break
        except:
            continue
    
    if not docling_available:
        print("❌ Docling API недоступен")
        return {}
    
    # Получение манифестов из MongoDB
    client = get_mongo_client()
    manifests = []
    
    if client:
        db = client[MONGO_DB]
        manifests_collection = db["manifests"]
        manifests = list(manifests_collection.find())
    else:
        # Используем docker exec
        data = get_mongo_via_docker()
        if data:
            manifests = data.get("manifests", [])
    
    if not manifests:
        print("❌ Манифесты не найдены")
        return {}
    
    print(f"Найдено {len(manifests)} unit'ов для обработки")
    
    processing_results = []
    library_usage = defaultdict(lambda: {"count": 0, "total_time": 0.0, "stages": []})
    extensions_stats = defaultdict(lambda: {
        "count": 0,
        "total_time": 0.0,
        "routes": defaultdict(int),
        "stages": defaultdict(float)
    })
    
    for idx, manifest in enumerate(manifests, 1):
        unit_id = manifest.get("unit_id")
        route = manifest.get("processing", {}).get("route", "unknown")
        files = manifest.get("files", [])
        
        print(f"\n[{idx}/{len(manifests)}] Обработка {unit_id} (route: {route})")
        
        # Подготовка запроса
        payload = {
            "unit_id": unit_id,
            "manifest": f"mongodb://{unit_id}",
            "files": files,
            "route": route
        }
        
        try:
            unit_start = time.time()
            api_url = working_api or DOCLING_API
            response = requests.post(
                api_url,
                json=payload,
                timeout=600
            )
            unit_time = time.time() - unit_start
            
            if response.status_code == 200:
                result = response.json()
                processing_results.append({
                    "unit_id": unit_id,
                    "status": "success",
                    "time": unit_time,
                    "route": route,
                    "response": result
                })
                
                # Собираем статистику по расширениям
                for file_info in files:
                    ext = Path(file_info.get("path", "")).suffix.lower() or "no_extension"
                    extensions_stats[ext]["count"] += 1
                    extensions_stats[ext]["total_time"] += unit_time
                    extensions_stats[ext]["routes"][route] += 1
                
                print(f"  ✅ Успешно за {unit_time:.2f}s")
            else:
                processing_results.append({
                    "unit_id": unit_id,
                    "status": "failed",
                    "time": unit_time,
                    "route": route,
                    "error": response.text[:200]
                })
                print(f"  ❌ Ошибка: HTTP {response.status_code}")
        
        except Exception as e:
            print(f"  ❌ Исключение: {e}")
            processing_results.append({
                "unit_id": unit_id,
                "status": "error",
                "route": route,
                "error": str(e)
            })
        
        # Небольшая задержка между запросами
        time.sleep(0.1)
    
    # Получаем детальные метрики из MongoDB и output файлов
    detailed_metrics = []
    if client:
        db = client[MONGO_DB]
        metrics_collection = db["processing_metrics"]
        detailed_metrics = list(metrics_collection.find().sort("created_at", -1))
    else:
        data = get_mongo_via_docker()
        if data:
            detailed_metrics = data.get("metrics", [])
    
    # Дополняем метрики из output файлов
    output_dir = Path("/root/winners_preprocessor/output")
    if output_dir.exists():
        for unit_dir in output_dir.iterdir():
            if unit_dir.is_dir():
                for json_file in unit_dir.glob("*.json"):
                    try:
                        with open(json_file, 'r', encoding='utf-8') as f:
                            output_data = json.load(f)
                            # Ищем соответствующую метрику в MongoDB или создаем новую
                            unit_id = output_data.get("unit_id")
                            existing = next((m for m in detailed_metrics if m.get("unit_id") == unit_id), None)
                            if existing:
                                # Дополняем существующую метрику методом из output
                                existing["processing_method"] = output_data.get("processing_method", "unknown")
                                # Дополняем времена если их нет
                                if "processing_times" not in existing or not existing["processing_times"]:
                                    metrics = output_data.get("metrics", {})
                                    if metrics:
                                        existing["processing_times"] = metrics.get("processing_times", {})
                            else:
                                # Создаем новую метрику из output файла
                                metrics = output_data.get("metrics", {})
                                if metrics:
                                    new_metric = {
                                        "unit_id": unit_id,
                                        "file_name": output_data.get("file", ""),
                                        "route": output_data.get("route", "unknown"),
                                        "processing_method": output_data.get("processing_method", "unknown"),
                                        "processing_times": metrics.get("processing_times", {}),
                                        "file_stats": metrics.get("file_stats", {})
                                    }
                                    detailed_metrics.append(new_metric)
                    except Exception as e:
                        pass  # Пропускаем файлы с ошибками
    
    # Анализ использования библиотек из метрик
    for metric in detailed_metrics:
        method = metric.get("processing_method") or metric.get("method") or "unknown"
        route = metric.get("route", "unknown")
        processing_times = metric.get("processing_times", {})
        
        # Определяем библиотеку по методу и route
        library = None
        method_lower = str(method).lower()
        route_lower = str(route).lower()
        
        if "pdfplumber" in method_lower or "plumber" in method_lower:
            library = "pdfplumber"
        elif "python-docx" in method_lower or "docx" in method_lower or (route_lower == "docx" and "fallback" in method_lower):
            library = "python-docx"
        elif "beautifulsoup" in method_lower or "soup" in method_lower or route_lower == "html_text":
            library = "beautifulsoup"
        elif "pytesseract" in method_lower or "tesseract" in method_lower:
            library = "pytesseract"
        elif "pdf2image" in method_lower:
            library = "pdf2image"
        elif "docling" in method_lower:
            library = "docling-core"
        else:
            # Определяем по route если метод неизвестен
            if route_lower == "pdf_text" or route_lower == "pdf_scan":
                library = "pdfplumber_fallback"
            elif route_lower == "docx":
                library = "python-docx_fallback"
            elif route_lower == "html_text":
                library = "beautifulsoup_fallback"
            else:
                library = "fallback/unknown"
        
        if library:
            library_usage[library]["count"] += 1
            total_time = processing_times.get("total", 0)
            library_usage[library]["total_time"] += total_time
            library_usage[library]["stages"].append({
                "route": route,
                "method": method,
                "times": processing_times
            })
    
    processing_time = time.time() - start_time
    
    successful = sum(1 for r in processing_results if r.get("status") == "success")
    failed = len(processing_results) - successful
    
    metrics = {
        "processing_time": processing_time,
        "total_units": len(manifests),
        "successful": successful,
        "failed": failed,
        "success_rate": (successful / len(manifests) * 100) if manifests else 0,
        "results": processing_results,
        "library_usage": dict(library_usage),
        "extensions_stats": dict(extensions_stats)
    }
    
    print(f"\n✅ Обработка завершена")
    print(f"   Успешно: {successful}/{len(manifests)}")
    print(f"   Ошибок: {failed}")
    print(f"   Время: {processing_time:.2f}s")
    
    pipeline_metrics["docling_processing"] = metrics
    return metrics


def collect_detailed_stats() -> Dict[str, Any]:
    """Собирает детальную статистику из MongoDB."""
    print("\n" + "="*80)
    print("ЭТАП 4: СБОР ДЕТАЛЬНОЙ СТАТИСТИКИ")
    print("="*80)
    
    client = get_mongo_client()
    all_metrics = []
    
    if client:
        db = client[MONGO_DB]
        metrics_collection = db["processing_metrics"]
        all_metrics = list(metrics_collection.find())
    else:
        data = get_mongo_via_docker()
        if data:
            all_metrics = data.get("metrics", [])
    
    # Статистика по этапам обработки
    stages_timing = defaultdict(lambda: {
        "count": 0,
        "total_time": 0.0,
        "min": float("inf"),
        "max": 0.0,
        "avg": 0.0
    })
    
    # Статистика по расширениям и routes
    extensions_detailed = defaultdict(lambda: {
        "count": 0,
        "routes": defaultdict(int),
        "times": {
            "total": [],
            "text_extraction": [],
            "ocr": [],
            "layout_analysis": [],
            "table_extraction": []
        },
        "library_methods": defaultdict(int)
    })
    
    for metric in all_metrics:
        route = metric.get("route", "unknown")
        processing_times = metric.get("processing_times", {})
        method = metric.get("processing_method", "unknown")
        
        # Собираем времена по этапам
        for stage, stage_time in processing_times.items():
            if stage_time:
                stages_timing[stage]["count"] += 1
                stages_timing[stage]["total_time"] += stage_time
                stages_timing[stage]["min"] = min(stages_timing[stage]["min"], stage_time)
                stages_timing[stage]["max"] = max(stages_timing[stage]["max"], stage_time)
        
        # Определяем расширение из file_name
        file_name = metric.get("file_name", "")
        ext = Path(file_name).suffix.lower() if file_name else "unknown"
        
        extensions_detailed[ext]["count"] += 1
        extensions_detailed[ext]["routes"][route] += 1
        extensions_detailed[ext]["library_methods"][method] += 1
        
        if "total" in processing_times:
            extensions_detailed[ext]["times"]["total"].append(processing_times["total"])
        if "text_extraction" in processing_times:
            extensions_detailed[ext]["times"]["text_extraction"].append(processing_times["text_extraction"])
        if "ocr" in processing_times:
            extensions_detailed[ext]["times"]["ocr"].append(processing_times["ocr"])
        if "layout_analysis" in processing_times:
            extensions_detailed[ext]["times"]["layout_analysis"].append(processing_times["layout_analysis"])
        if "table_extraction" in processing_times:
            extensions_detailed[ext]["times"]["table_extraction"].append(processing_times["table_extraction"])
    
    # Вычисляем средние значения
    for stage, stats in stages_timing.items():
        if stats["count"] > 0:
            stats["avg"] = stats["total_time"] / stats["count"]
        if stats["min"] == float("inf"):
            stats["min"] = 0.0
    
    # Вычисляем средние по расширениям
    for ext, stats in extensions_detailed.items():
        for time_type, times in stats["times"].items():
            if times:
                stats["times"][time_type] = {
                    "min": min(times),
                    "max": max(times),
                    "avg": sum(times) / len(times),
                    "total": sum(times)
                }
            else:
                stats["times"][time_type] = {"min": 0, "max": 0, "avg": 0, "total": 0}
    
    stats = {
        "stages_timing": dict(stages_timing),
        "extensions_detailed": dict(extensions_detailed)
    }
    
    pipeline_metrics["stages_timing"] = stats["stages_timing"]
    pipeline_metrics["extensions_stats"] = stats["extensions_detailed"]
    
    print(f"✅ Собрано метрик: {len(all_metrics)}")
    print(f"Этапов обработки: {len(stages_timing)}")
    print(f"Типов файлов: {len(extensions_detailed)}")
    
    return stats


def generate_report() -> str:
    """Генерирует полный отчет."""
    print("\n" + "="*80)
    print("ГЕНЕРАЦИЯ ОТЧЕТА")
    print("="*80)
    
    lines = []
    lines.append("# ПОЛНЫЙ ОТЧЕТ ОБ ОБРАБОТКЕ PIPELINE")
    lines.append("")
    lines.append(f"**Время начала:** {pipeline_metrics['started_at']}")
    lines.append(f"**Время завершения:** {datetime.utcnow().isoformat()}")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # 1. Общая статистика
    lines.append("## ОБЩАЯ СТАТИСТИКА")
    lines.append("")
    
    extraction = pipeline_metrics.get("extraction", {})
    preprocessing = pipeline_metrics.get("preprocessing", {})
    docling = pipeline_metrics.get("docling_processing", {})
    
    lines.append("| Этап | Время | Детали |")
    lines.append("|------|-------|--------|")
    
    if extraction:
        lines.append(f"| **Разархивирование** | {extraction.get('extraction_time', 0):.2f}s | {extraction.get('total_files', 0)} файлов |")
    
    if preprocessing:
        lines.append(f"| **Preprocessing** | {preprocessing.get('preprocessing_time', 0):.2f}s | {preprocessing.get('units_created', 0)} unit'ов |")
    
    if docling:
        lines.append(f"| **Docling Processing** | {docling.get('processing_time', 0):.2f}s | {docling.get('successful', 0)}/{docling.get('total_units', 0)} успешно |")
    
    total_time = (
        extraction.get('extraction_time', 0) +
        preprocessing.get('preprocessing_time', 0) +
        docling.get('processing_time', 0)
    )
    lines.append(f"| **ИТОГО** | **{total_time:.2f}s** | Полный pipeline |")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # 2. Статистика по расширениям файлов
    lines.append("## СТАТИСТИКА ПО РАСШИРЕНИЯМ ФАЙЛОВ")
    lines.append("")
    
    extensions = pipeline_metrics.get("extensions_stats", {})
    if extensions:
        lines.append("| Расширение | Количество | Routes | Среднее время |")
        lines.append("|------------|------------|--------|---------------|")
        
        for ext, stats in sorted(extensions.items()):
            count = stats.get("count", 0)
            routes = ", ".join([f"{r}({c})" for r, c in list(stats.get("routes", {}).items())[:3]])
            avg_time = stats.get("times", {}).get("total", {}).get("avg", 0)
            lines.append(f"| `{ext}` | {count} | {routes[:50]} | {avg_time:.3f}s |")
        
        lines.append("")
        lines.append("### Детальная статистика по расширениям:")
        lines.append("")
        
        for ext, stats in sorted(extensions.items())[:10]:  # Первые 10
            lines.append(f"#### {ext}")
            lines.append(f"- Количество файлов: {stats.get('count', 0)}")
            lines.append(f"- Routes: {dict(stats.get('routes', {}))}")
            lines.append("")
            times = stats.get("times", {})
            if times:
                lines.append("Времена обработки:")
                for time_type, time_stats in times.items():
                    if time_stats and isinstance(time_stats, dict):
                        avg = time_stats.get("avg", 0)
                        if avg > 0:
                            lines.append(f"  - {time_type}: avg={avg:.3f}s, min={time_stats.get('min', 0):.3f}s, max={time_stats.get('max', 0):.3f}s")
                lines.append("")
    else:
        lines.append("Статистика по расширениям недоступна")
        lines.append("")
    
    lines.append("---")
    lines.append("")
    
    # 3. Статистика по этапам обработки
    lines.append("## СТАТИСТИКА ПО ЭТАПАМ ОБРАБОТКИ")
    lines.append("")
    
    stages = pipeline_metrics.get("stages_timing", {})
    if stages:
        lines.append("| Этап | Количество | Общее время | Среднее | Мин | Макс |")
        lines.append("|------|------------|-------------|---------|-----|------|")
        
        for stage, stats in sorted(stages.items()):
            count = stats.get("count", 0)
            total = stats.get("total_time", 0)
            avg = stats.get("avg", 0)
            min_time = stats.get("min", 0)
            max_time = stats.get("max", 0)
            lines.append(f"| `{stage}` | {count} | {total:.2f}s | {avg:.3f}s | {min_time:.3f}s | {max_time:.3f}s |")
    else:
        lines.append("Статистика по этапам недоступна")
    
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # 4. Статистика по используемым библиотекам/LLM
    lines.append("## СТАТИСТИКА ПО ИСПОЛЬЗУЕМЫМ БИБЛИОТЕКАМ/LLM")
    lines.append("")
    
    library_usage = docling.get("library_usage", {})
    if library_usage:
        lines.append("| Библиотека | Использований | Общее время | Среднее время | Этапы |")
        lines.append("|------------|---------------|-------------|---------------|-------|")
        
        for lib, stats in sorted(library_usage.items()):
            count = stats.get("count", 0)
            total_time = stats.get("total_time", 0)
            avg_time = total_time / count if count > 0 else 0
            
            # Собираем этапы использования
            routes = set()
            for stage_info in stats.get("stages", []):
                route = stage_info.get("route", "unknown")
                if route:
                    routes.add(str(route))
                else:
                    routes.add("unknown")
            routes_str = ", ".join(sorted([r for r in routes if r])[:3])
            
            lines.append(f"| **{lib}** | {count} | {total_time:.2f}s | {avg_time:.3f}s | {routes_str} |")
        
        lines.append("")
        lines.append("### Детальная информация по библиотекам:")
        lines.append("")
        
        for lib, stats in sorted(library_usage.items()):
            lines.append(f"#### {lib}")
            lines.append(f"- Количество использований: {stats.get('count', 0)}")
            lines.append(f"- Общее время: {stats.get('total_time', 0):.2f}s")
            lines.append(f"- Среднее время: {stats.get('total_time', 0) / max(stats.get('count', 1), 1):.3f}s")
            lines.append("")
            lines.append("Использование по этапам:")
            for stage_info in stats.get("stages", [])[:5]:
                route = stage_info.get("route", "unknown")
                method = stage_info.get("method", "unknown")
                times = stage_info.get("times", {})
                lines.append(f"  - Route: {route}, Method: {method}")
                if times:
                    for time_stage, time_val in times.items():
                        if time_val and time_val > 0:
                            lines.append(f"    - {time_stage}: {time_val:.3f}s")
            lines.append("")
    else:
        lines.append("Статистика по библиотекам недоступна")
        lines.append("")
    
    lines.append("---")
    lines.append("")
    
    # 5. Выводы
    lines.append("## ВЫВОДЫ")
    lines.append("")
    
    if docling:
        success_rate = docling.get("success_rate", 0)
        lines.append(f"- **Успешность обработки:** {success_rate:.1f}%")
        lines.append(f"- **Всего обработано:** {docling.get('total_units', 0)} unit'ов")
        lines.append(f"- **Успешно:** {docling.get('successful', 0)}")
        lines.append(f"- **Ошибок:** {docling.get('failed', 0)}")
        lines.append("")
    
    if library_usage:
        most_used = max(library_usage.items(), key=lambda x: x[1].get("count", 0))
        lines.append(f"- **Наиболее используемая библиотека:** {most_used[0]} ({most_used[1].get('count', 0)} использований)")
        lines.append("")
    
    lines.append("---")
    lines.append("")
    lines.append(f"**Отчет сгенерирован:** {datetime.utcnow().isoformat()}")
    
    return "\n".join(lines)


def main():
    """Главная функция."""
    print("="*80)
    print("ПОЛНОЕ ТЕСТИРОВАНИЕ PIPELINE")
    print("="*80)
    
    # 1. Разархивирование
    extract_vitaly_rar()
    
    # 2. Preprocessing
    run_preprocessing()
    
    # 3. Docling Processing
    run_docling_processing()
    
    # 4. Сбор детальной статистики
    collect_detailed_stats()
    
    # 5. Генерация отчета
    report = generate_report()
    
    # Сохранение отчета
    report_file = "FULL_PIPELINE_REPORT.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)
    
    print(f"\n✅ Отчет сохранен в {report_file}")
    
    # Сохранение метрик в JSON
    metrics_file = "pipeline_metrics.json"
    with open(metrics_file, "w", encoding="utf-8") as f:
        json.dump(pipeline_metrics, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"✅ Метрики сохранены в {metrics_file}")
    
    print("\n" + "="*80)
    print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("="*80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())


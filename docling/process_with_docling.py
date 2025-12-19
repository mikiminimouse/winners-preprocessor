#!/usr/bin/env python3
"""
Скрипт для обработки всех unit'ов через Docling API.
"""
import requests
import json
import time
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import os
import subprocess

# Конфигурация
DOCLING_API = "http://localhost:8000/process"
ROUTER_API = "http://localhost:8080"
MONGO_SERVER = os.environ.get("MONGO_SERVER", "localhost:27017")
MONGO_METADATA_USER = os.environ.get("MONGO_METADATA_USER", "docling_user")
MONGO_METADATA_PASSWORD = os.environ.get("MONGO_METADATA_PASSWORD", "password")
MONGO_METADATA_DB = os.environ.get("MONGO_METADATA_DB", "docling_metadata")

# Статистика обработки
processing_stats = {
    "started_at": datetime.utcnow().isoformat(),
    "total_units": 0,
    "processed": 0,
    "successful": 0,
    "failed": 0,
    "errors": [],
    "results": []
}


def get_all_manifests() -> List[Dict[str, Any]]:
    """Получает все манифесты через MongoDB shell."""
    try:
        # Используем mongosh для получения манифестов
        cmd = [
            "docker", "exec", "docling_mongodb", "mongosh",
            "-u", "admin", "-p", "password",
            "--authenticationDatabase", "admin",
            "--quiet",
            "--eval",
            f"db = db.getSiblingDB('{MONGO_METADATA_DB}'); "
            f"JSON.stringify(db.manifests.find({{}}).toArray())"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            print(f"Ошибка получения манифестов: {result.stderr}")
            return []
        
        # Парсим JSON
        manifests_json = result.stdout.strip()
        if not manifests_json:
            return []
        
        manifests = json.loads(manifests_json)
        
        # Удаляем _id из результатов
        for manifest in manifests:
            if '_id' in manifest:
                manifest['_id'] = str(manifest['_id'])
        
        return manifests
    
    except json.JSONDecodeError as e:
        print(f"Ошибка парсинга JSON: {e}")
        return []
    except Exception as e:
        print(f"Ошибка получения манифестов: {e}")
        return []


def process_unit_with_docling(manifest: Dict[str, Any]) -> Dict[str, Any]:
    """Обрабатывает unit через Docling API."""
    unit_id = manifest.get("unit_id")
    route = manifest.get("processing", {}).get("route", "unknown")
    files = manifest.get("files", [])
    
    print(f"\n{'='*80}")
    print(f"Обработка unit: {unit_id}")
    print(f"Route: {route}")
    print(f"Файлов: {len(files)}")
    
    # Формируем запрос к Docling
    # Docling ожидает manifest как путь, но у нас он в MongoDB
    # Используем специальный формат для MongoDB
    manifest_path = f"mongodb://{unit_id}"
    
    payload = {
        "unit_id": unit_id,
        "manifest": manifest_path,
        "files": files,
        "route": route
    }
    
    try:
        print(f"Отправка запроса в Docling: {DOCLING_API}")
        start_time = time.time()
        
        response = requests.post(
            DOCLING_API,
            json=payload,
            timeout=300  # 5 минут на обработку
        )
        
        processing_time = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Успешно обработан за {processing_time:.2f} секунд")
            print(f"   Статус: {result.get('status')}")
            print(f"   Output файлов: {len(result.get('output_files', []))}")
            
            return {
                "unit_id": unit_id,
                "status": "success",
                "response": result,
                "processing_time": processing_time,
                "route": route,
                "files_count": len(files)
            }
        else:
            error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
            print(f"❌ Ошибка: {error_msg}")
            
            return {
                "unit_id": unit_id,
                "status": "failed",
                "error": error_msg,
                "processing_time": processing_time,
                "route": route,
                "files_count": len(files),
                "http_status": response.status_code
            }
    
    except requests.exceptions.Timeout:
        error_msg = "Timeout при обработке (превышено 5 минут)"
        print(f"❌ {error_msg}")
        return {
            "unit_id": unit_id,
            "status": "failed",
            "error": error_msg,
            "route": route,
            "files_count": len(files)
        }
    
    except Exception as e:
        error_msg = f"Ошибка при обработке: {str(e)}"
        print(f"❌ {error_msg}")
        return {
            "unit_id": unit_id,
            "status": "failed",
            "error": error_msg,
            "route": route,
            "files_count": len(files)
        }


def generate_report() -> str:
    """Генерирует отчет об обработке."""
    lines = []
    
    lines.append("# ОТЧЕТ ОБ ОБРАБОТКЕ ДОКУМЕНТОВ ЧЕРЕЗ DOCLING")
    lines.append("")
    lines.append(f"**Время начала:** {processing_stats['started_at']}")
    lines.append(f"**Время завершения:** {datetime.utcnow().isoformat()}")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Общая статистика
    lines.append("## ОБЩАЯ СТАТИСТИКА")
    lines.append("")
    lines.append("| Показатель | Значение |")
    lines.append("|------------|----------|")
    lines.append(f"| **Всего unit'ов** | {processing_stats['total_units']} |")
    lines.append(f"| **Обработано** | {processing_stats['processed']} |")
    lines.append(f"| **Успешно** | {processing_stats['successful']} |")
    lines.append(f"| **Ошибок** | {processing_stats['failed']} |")
    
    if processing_stats['total_units'] > 0:
        success_rate = (processing_stats['successful'] / processing_stats['total_units']) * 100
        lines.append(f"| **Успешность** | {success_rate:.1f}% |")
    
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Статистика по routes
    routes_stats = {}
    for result in processing_stats['results']:
        route = result.get('route') or 'unknown'
        if route not in routes_stats:
            routes_stats[route] = {'total': 0, 'success': 0, 'failed': 0}
        routes_stats[route]['total'] += 1
        if result.get('status') == 'success':
            routes_stats[route]['success'] += 1
        else:
            routes_stats[route]['failed'] += 1
    
    if routes_stats:
        lines.append("## СТАТИСТИКА ПО ROUTES")
        lines.append("")
        lines.append("| Route | Всего | Успешно | Ошибок | Успешность |")
        lines.append("|-------|-------|---------|--------|------------|")
        for route in sorted(routes_stats.keys(), key=lambda x: str(x)):
            stats = routes_stats[route]
            success_rate = (stats['success'] / stats['total'] * 100) if stats['total'] > 0 else 0
            lines.append(f"| `{route}` | {stats['total']} | {stats['success']} | {stats['failed']} | {success_rate:.1f}% |")
        lines.append("")
        lines.append("---")
        lines.append("")
    
    # Ошибки
    if processing_stats['errors']:
        lines.append("## АНАЛИЗ ОШИБОК")
        lines.append("")
        lines.append(f"**Всего ошибок:** {len(processing_stats['errors'])}")
        lines.append("")
        
        # Группируем по типу ошибки
        error_types = {}
        for error in processing_stats['errors']:
            error_msg = error.get('error', 'Unknown error')
            error_type = error_msg.split(':')[0] if ':' in error_msg else error_msg[:50]
            if error_type not in error_types:
                error_types[error_type] = []
            error_types[error_type].append(error)
        
        for error_type, errors in error_types.items():
            lines.append(f"### {error_type} ({len(errors)} ошибок)")
            lines.append("")
            for error in errors[:5]:  # Первые 5
                lines.append(f"- **{error.get('unit_id', 'unknown')}** ({error.get('route', 'unknown')}): {error.get('error', '')[:200]}")
            if len(errors) > 5:
                lines.append(f"- ... и еще {len(errors) - 5} ошибок")
            lines.append("")
        
        lines.append("---")
        lines.append("")
    
    # Детали успешных обработок
    successful = [r for r in processing_stats['results'] if r.get('status') == 'success']
    if successful:
        lines.append("## УСПЕШНЫЕ ОБРАБОТКИ")
        lines.append("")
        lines.append(f"**Всего успешно обработано:** {len(successful)}")
        lines.append("")
        
        # Показываем первые 10
        for result in successful[:10]:
            unit_id = result.get('unit_id', 'unknown')
            route = result.get('route', 'unknown')
            files_count = result.get('files_count', 0)
            processing_time = result.get('processing_time', 0)
            output_files = result.get('response', {}).get('output_files', [])
            
            lines.append(f"### {unit_id}")
            lines.append(f"- Route: `{route}`")
            lines.append(f"- Файлов: {files_count}")
            lines.append(f"- Время обработки: {processing_time:.2f} сек")
            lines.append(f"- Output файлов: {len(output_files)}")
            lines.append("")
        
        if len(successful) > 10:
            lines.append(f"... и еще {len(successful) - 10} успешных обработок")
            lines.append("")
        
        lines.append("---")
        lines.append("")
    
    # Выводы
    lines.append("## ВЫВОДЫ")
    lines.append("")
    lines.append(f"### ✅ Успешно обработано: {processing_stats['successful']} unit'ов")
    if processing_stats['failed'] > 0:
        lines.append(f"### ⚠️ Ошибок: {processing_stats['failed']} unit'ов")
    lines.append("")
    
    return "\n".join(lines)


def main():
    """Главная функция."""
    print("=" * 80)
    print("ОБРАБОТКА UNIT'ОВ ЧЕРЕЗ DOCLING")
    print("=" * 80)
    print()
    
    # Проверяем доступность Docling
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code != 200:
            print("❌ Docling API недоступен")
            return 1
        print("✅ Docling API доступен")
    except Exception as e:
        print(f"❌ Ошибка подключения к Docling: {e}")
        return 1
    
    # Получаем все манифесты
    print("\nПолучение манифестов из MongoDB...")
    manifests = get_all_manifests()
    
    if not manifests:
        print("❌ Манифесты не найдены")
        return 1
    
    processing_stats['total_units'] = len(manifests)
    print(f"✅ Найдено {len(manifests)} unit'ов для обработки")
    
    # Обрабатываем каждый unit
    print(f"\nНачинаем обработку {len(manifests)} unit'ов...")
    
    for idx, manifest in enumerate(manifests, 1):
        print(f"\n[{idx}/{len(manifests)}] ", end="")
        result = process_unit_with_docling(manifest)
        
        processing_stats['results'].append(result)
        processing_stats['processed'] += 1
        
        if result.get('status') == 'success':
            processing_stats['successful'] += 1
        else:
            processing_stats['failed'] += 1
            processing_stats['errors'].append(result)
        
        # Небольшая задержка между запросами
        time.sleep(0.5)
    
    # Генерируем отчет
    print("\n" + "=" * 80)
    print("ГЕНЕРАЦИЯ ОТЧЕТА")
    print("=" * 80)
    
    report = generate_report()
    
    # Сохраняем отчет
    report_file = "DOCLING_PROCESSING_REPORT.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)
    
    print(f"✅ Отчет сохранен в {report_file}")
    
    # Выводим краткую сводку
    print("\n" + "=" * 80)
    print("ИТОГИ ОБРАБОТКИ")
    print("=" * 80)
    print(f"Всего unit'ов: {processing_stats['total_units']}")
    print(f"Успешно: {processing_stats['successful']}")
    print(f"Ошибок: {processing_stats['failed']}")
    if processing_stats['total_units'] > 0:
        success_rate = (processing_stats['successful'] / processing_stats['total_units']) * 100
        print(f"Успешность: {success_rate:.1f}%")
    
    return 0


if __name__ == "__main__":
    exit(main())


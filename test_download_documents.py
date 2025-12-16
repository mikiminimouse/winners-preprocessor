#!/usr/bin/env python3
"""
Скрипт для скачивания документов по Uя ускорения процесса.RLs из JSON файла, полученного через test_mongo_direct.py или test_mcp_server.py.
Использует параллельное скачивание дл
"""
import os
import sys
import json
import requests
from pathlib import Path
from typing import Dict, Any, List, Tuple
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def sanitize_filename(filename: str) -> str:
    """Санитизирует имя файла, удаляя опасные символы."""
    # Удаляем path traversal и опасные символы
    filename = filename.replace('..', '').replace('/', '_').replace('\\', '_')
    # Удаляем другие опасные символы
    dangerous_chars = ['<', '>', ':', '"', '|', '?', '*']
    for char in dangerous_chars:
        filename = filename.replace(char, '_')
    return filename


# Глобальный счетчик для потокобезопасного вывода
_download_lock = threading.Lock()
_downloaded_count = 0
_failed_count = 0

# Браузерные заголовки, которые позволяют корректно скачивать файлы с zakupki.gov.ru
_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}


# Создаем сессию с retry механизмом и браузерными заголовками
def create_session_with_retry() -> requests.Session:
    """Создает requests-сессию с retry механизмом и заголовками, имитирующими браузер."""
    session = requests.Session()

    # Настройка retry стратегии
    retry_strategy = Retry(
        total=3,  # Всего 3 попытки
        backoff_factor=1,  # Экспоненциальная задержка: 1, 2, 4 секунды
        status_forcelist=[429, 500, 502, 503, 504],  # Коды для retry
        allowed_methods=["GET", "HEAD"],
    )

    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=50, pool_maxsize=50)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # Добавляем заголовки браузера
    session.headers.update(_BROWSER_HEADERS)

    return session

# Глобальная сессия для всех запросов
_session = None
_session_lock = threading.Lock()


def get_session():
    """Получает или создает глобальную сессию с браузерными заголовками и retry."""
    global _session
    with _session_lock:
        if _session is None:
            _session = create_session_with_retry()
        return _session


def check_zakupki_health(timeout: int = 5) -> bool:
    """
    Быстрый health-check доступности zakupki.gov.ru через текущий сетевой стек (включая VPN).
    Возвращает True, если HTTPS отвечает кодом < 500, иначе False.
    """
    try:
        session = get_session()
        resp = session.get("https://zakupki.gov.ru", timeout=timeout, allow_redirects=True, stream=False)
        return resp.status_code < 500
    except Exception as e:
        print(f"[HEALTHCHECK] zakupki.gov.ru недоступен: {type(e).__name__}: {e}")
        return False


def download_document(url: str, dest_path: Path, timeout: int = 300, show_progress: bool = False, delay: float = 0.1) -> Tuple[bool, str]:
    """
    Скачивает документ по URL в указанный путь с retry механизмом.
    
    Args:
        url: URL для скачивания
        dest_path: Путь для сохранения файла
        timeout: Таймаут запроса в секундах
        show_progress: Показывать ли прогресс
        delay: Задержка перед запросом (для rate limiting)
    
    Returns:
        Tuple[bool, str]: (успех, сообщение об ошибке или имя файла)
    """
    global _downloaded_count, _failed_count
    
    # Небольшая задержка для rate limiting
    if delay > 0:
        time.sleep(delay)
    
    try:
        if show_progress:
            with _download_lock:
                current = _downloaded_count + _failed_count + 1
                print(f"  [{current}] Скачивание: {url[:60]}...", end='\r', flush=True)
        
        session = get_session()
        response = session.get(url, timeout=timeout, stream=True)
        response.raise_for_status()
        
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(dest_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        file_size = dest_path.stat().st_size
        
        with _download_lock:
            _downloaded_count += 1
            if show_progress:
                print(f"  [{_downloaded_count}] ✓ {dest_path.name} ({file_size:,} bytes)")
        
        return True, dest_path.name
    except requests.exceptions.RequestException as e:
        with _download_lock:
            _failed_count += 1
            error_msg = f"{type(e).__name__}: {str(e)}"
            if show_progress:
                print(f"  [{_failed_count}] ✗ Ошибка: {error_msg[:60]}")
        return False, error_msg
    except Exception as e:
        with _download_lock:
            _failed_count += 1
            error_msg = f"{type(e).__name__}: {str(e)}"
            if show_progress:
                print(f"  [{_failed_count}] ✗ Ошибка: {error_msg[:60]}")
        return False, error_msg


def download_protocols_from_json(json_file: str, output_dir: str = "input/test_downloads", limit: int = None, max_workers: int = 10) -> Dict[str, Any]:
    """
    Скачивает документы из JSON файла с протоколами.
    
    Args:
        json_file: Путь к JSON файлу с протоколами
        output_dir: Директория для сохранения документов
        limit: Лимит количества документов для скачивания (None = все)
    
    Returns:
        Словарь с результатами скачивания
    """
    # Читаем JSON файл
    print(f"Чтение файла: {json_file}")
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    date = data.get('date', 'unknown')
    protocols = data.get('protocols', {})
    
    print(f"Дата: {date}")
    print(f"Количество протоколов: {len(protocols)}")
    
    # Создаем директорию для скачивания
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    print(f"Директория для скачивания: {output_path.absolute()}")
    
    downloaded = []
    failed = []
    skipped = []
    total_urls = 0
    
    # Подготавливаем список задач для скачивания
    download_tasks = []
    
    for purchase_number, doc_info in protocols.items():
        # Обрабатываем как один документ, так и список
        docs = [doc_info] if isinstance(doc_info, dict) else doc_info
        
        for doc in docs:
            url = doc.get("url")
            filename = doc.get("fileName", f"{purchase_number}.pdf")
            
            if not url:
                skipped.append({
                    "purchase_number": purchase_number,
                    "filename": filename,
                    "reason": "URL отсутствует"
                })
                continue
            
            # Санитизируем имя файла
            safe_filename = sanitize_filename(filename)
            if not safe_filename:
                safe_filename = f"{purchase_number}.pdf"
            
            # Создаем уникальное имя файла, если файл уже существует
            dest_path = output_path / safe_filename
            counter = 1
            while dest_path.exists():
                name_parts = safe_filename.rsplit('.', 1)
                if len(name_parts) == 2:
                    new_name = f"{name_parts[0]}_{counter}.{name_parts[1]}"
                else:
                    new_name = f"{safe_filename}_{counter}"
                dest_path = output_path / new_name
                counter += 1
            
            download_tasks.append({
                "purchase_number": purchase_number,
                "url": url,
                "filename": filename,
                "dest_path": dest_path
            })
            total_urls += 1
    
    # Применяем лимит
    if limit and limit < len(download_tasks):
        download_tasks = download_tasks[:limit]
        total_urls = limit
    
    print(f"Всего URLs для скачивания: {total_urls}")
    print(f"Параллельных потоков: {max_workers}")
    if limit:
        print(f"Лимит скачивания: {limit}")
    
    print(f"\nНачало параллельного скачивания...")
    start_time = time.time()
    
    # Сбрасываем счетчики
    global _downloaded_count, _failed_count
    _downloaded_count = 0
    _failed_count = 0
    
    # Поток для вывода метрик в реальном времени
    def print_metrics():
        while _downloaded_count + _failed_count < total_urls:
            time.sleep(2)  # Обновление каждые 2 секунды
            elapsed = time.time() - start_time
            completed = _downloaded_count + _failed_count
            if completed > 0:
                speed = completed / elapsed if elapsed > 0 else 0
                remaining = (total_urls - completed) / speed if speed > 0 else 0
                with _download_lock:
                    print(f"\n[METRICS] Завершено: {completed}/{total_urls} | "
                          f"Успешно: {_downloaded_count} | Ошибок: {_failed_count} | "
                          f"Скорость: {speed:.1f} файл/сек | "
                          f"Осталось: {remaining:.0f} сек", flush=True)
    
    metrics_thread = threading.Thread(target=print_metrics, daemon=True)
    metrics_thread.start()
    
    # Вычисляем задержку для rate limiting (чтобы не перегружать сервер)
    # Для 32 потоков: ~0.03 сек между запросами = ~33 запроса/сек
    # Для 10 потоков: ~0.1 сек между запросами = ~10 запросов/сек
    rate_limit_delay = max(0.05, 1.0 / max_workers) if max_workers > 10 else 0.1
    
    print(f"Rate limiting: {rate_limit_delay:.2f} сек между запросами")
    
    # Параллельное скачивание
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Запускаем все задачи с небольшой задержкой для rate limiting
        future_to_task = {
            executor.submit(download_document, task["url"], task["dest_path"], 300, True, rate_limit_delay): task
            for task in download_tasks
        }
        
        # Обрабатываем результаты по мере завершения
        for future in as_completed(future_to_task):
            task = future_to_task[future]
            try:
                success, result = future.result()
                if success:
                    downloaded.append({
                        "purchase_number": task["purchase_number"],
                        "url": task["url"],
                        "filename": task["filename"],
                        "saved_as": result,
                        "path": str(task["dest_path"].absolute())
                    })
                else:
                    failed.append({
                        "purchase_number": task["purchase_number"],
                        "url": task["url"],
                        "filename": task["filename"],
                        "error": result
                    })
            except Exception as e:
                failed.append({
                    "purchase_number": task["purchase_number"],
                    "url": task["url"],
                    "filename": task["filename"],
                    "error": str(e)
                })
    
    print()  # Новая строка после прогресса
    
    # Создаем отчет
    report = {
        "date": date,
        "timestamp": datetime.now().isoformat(),
        "total_protocols": len(protocols),
        "total_urls": total_urls,
        "downloaded_count": len(downloaded),
        "failed_count": len(failed),
        "skipped_count": len(skipped),
        "downloaded": downloaded,
        "failed": failed,
        "skipped": skipped
    }
    
    return report


def main():
    """Основная функция для скачивания документов."""
    print("=" * 60)
    print("Скачивание документов по URLs из JSON файла")
    print("=" * 60)
    
    if len(sys.argv) < 2:
        print("\nИспользование: python3 test_download_documents.py <json_file> [output_dir] [limit] [max_workers]")
        print("\nПараметры:")
        print("  json_file    - JSON файл с протоколами (обязательно)")
        print("  output_dir   - Директория для сохранения (по умолчанию: input/test_downloads)")
        print("  limit        - Лимит количества документов (по умолчанию: все)")
        print("  max_workers  - Количество параллельных потоков (по умолчанию: 10)")
        print("\nПримеры:")
        print("  python3 test_download_documents.py test_protocols_2025-01-17.json")
        print("  python3 test_download_documents.py test_protocols_2025-01-17.json input/test_downloads")
        print("  python3 test_download_documents.py test_protocols_2025-01-17.json input/test_downloads 500")
        print("  python3 test_download_documents.py test_protocols_2025-01-17.json input/test_downloads 500 20")
        print("\nРекомендации по max_workers:")
        print("  - Для быстрого интернета: 20-30 потоков")
        print("  - Для медленного интернета: 5-10 потоков")
        print("  - Для локальной сети: 30-50 потоков")
        sys.exit(1)
    
    json_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "input/test_downloads"
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else None
    max_workers = int(sys.argv[4]) if len(sys.argv) > 4 else 10
    
    if not os.path.exists(json_file):
        print(f"\nОШИБКА: Файл не найден: {json_file}")
        sys.exit(1)
    
    print(f"\nJSON файл: {json_file}")
    print(f"Директория вывода: {output_dir}")
    if limit:
        print(f"Лимит: {limit} документов")
    print(f"Параллельных потоков: {max_workers}")

    # Быстрый health-check zakupki.gov.ru, чтобы не долбить сервер без VPN
    print("\nПроверка доступности zakupki.gov.ru через текущую сеть (VPN)...")
    if not check_zakupki_health():
        print("✗ zakupki.gov.ru недоступен (нет VPN / блокировка). Скачивание прервано.")
        sys.exit(1)
    else:
        print("✓ zakupki.gov.ru доступен, начинаем скачивание.")

    # Скачиваем документы
    try:
        report = download_protocols_from_json(json_file, output_dir, limit, max_workers)
        
        # Сохраняем отчет
        report_file = f"download_report_{report['date']}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print("\n" + "=" * 60)
        print("Результаты скачивания:")
        print("=" * 60)
        print(f"Всего протоколов: {report['total_protocols']}")
        print(f"Всего URLs: {report['total_urls']}")
        print(f"✓ Скачано успешно: {report['downloaded_count']}")
        print(f"✗ Ошибок скачивания: {report['failed_count']}")
        print(f"⊘ Пропущено: {report['skipped_count']}")
        print(f"\nОтчет сохранен в: {report_file}")
        
        if report['failed_count'] > 0:
            print(f"\nПервые 5 ошибок:")
            for i, failed_item in enumerate(report['failed'][:5], 1):
                print(f"  {i}. {failed_item.get('purchase_number', 'unknown')}: {failed_item.get('url', '')[:60]}...")
        
    except Exception as e:
        print(f"\n✗ Ошибка при скачивании документов: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("Скачивание завершено")
    print("=" * 60)


if __name__ == "__main__":
    main()


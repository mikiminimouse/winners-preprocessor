#!/usr/bin/env python3
"""
Воркер для обработки протоколов из локальной Mongo `docling_metadata.protocols`.

Шаги:
1. Берёт документы со статусом "pending" (ограничение по количеству за запуск).
2. Скачивает файлы по `urls` (zakupki.gov.ru, через VPN/сетевой стек хоста).
3. Для каждого успешно скачанного файла вызывает Router `/upload`,
   который создаёт unit + manifest и триггерит Docling.
4. Обновляет документ протокола в Mongo:
   - статус → "processing" (если хотя бы один файл отдан в Router)
   - или статус → "error" + `last_error`, если ничего не удалось обработать.

Этот скрипт НЕ дожидается завершения Docling/LLM — только ставит их в работу.
"""

from __future__ import annotations

import os
import sys
import json
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from pymongo import MongoClient, ReturnDocument
from pymongo.errors import PyMongoError

from test_download_documents import (
    sanitize_filename,
    download_document,
    check_zakupki_health,
)


# --- Конфигурация из окружения ---

# Mongo с метаданными (локальная, где лежит `docling_metadata.protocols`)
MONGO_METADATA_SERVER = os.environ.get("MONGO_METADATA_SERVER", "localhost:27017")
MONGO_METADATA_USER = os.environ.get("MONGO_METADATA_USER", "docling_user")
MONGO_METADATA_PASSWORD = os.environ.get("MONGO_METADATA_PASSWORD", "password")
MONGO_METADATA_DB = os.environ.get("MONGO_METADATA_DB", "docling_metadata")
MONGO_METADATA_PROTOCOLS_COLLECTION = os.environ.get(
    "MONGO_METADATA_PROTOCOLS_COLLECTION", "protocols"
)

# Ограничения воркера
PROTOCOLS_PROCESS_LIMIT = int(os.environ.get("PROTOCOLS_PROCESS_LIMIT", "200"))
MAX_URLS_PER_PROTOCOL = int(os.environ.get("MAX_URLS_PER_PROTOCOL", "3"))

# Таймаут HTTP-скачиваний (секунды) для download_document.
# Продакшн-значение можно держать повыше, но для диагностики и чтобы не "зависать"
# на одном протоколе слишком долго — используем более агрессивное значение по умолчанию.
DOWNLOAD_HTTP_TIMEOUT = int(os.environ.get("DOWNLOAD_HTTP_TIMEOUT", "90"))

# Параллелизм скачивания файлов внутри одного протокола
DOWNLOAD_CONCURRENCY = int(os.environ.get("DOWNLOAD_CONCURRENCY", "5"))

# Таймаут HTTP-запроса к Router /upload (секунды)
ROUTER_HTTP_TIMEOUT = int(os.environ.get("ROUTER_HTTP_TIMEOUT", "180"))

# Режим сухого запуска для Router: если =1, то файлы скачиваются,
# но не отправляются в Router /upload (чистый бенчмарк скачивания).
DRY_RUN_ROUTER = os.environ.get("DRY_RUN_ROUTER", "0") == "1"

# Параллелизм скачивания файлов внутри одного протокола
DOWNLOAD_CONCURRENCY = int(os.environ.get("DOWNLOAD_CONCURRENCY", "5"))

# Router API (из docker-compose router→порт 8080 на хосте)
ROUTER_UPLOAD_URL = os.environ.get(
    "ROUTER_UPLOAD_URL", "http://localhost:8080/upload"
)

# Локальная директория, куда временно скачиваем файлы протоколов
PROTOCOLS_DOWNLOAD_DIR = Path(
    os.environ.get("PROTOCOLS_DOWNLOAD_DIR", "input/protocols")
)

# Разрешить принудительный запуск воркера даже при недоступных zakupki.gov.ru
# По умолчанию = "0" → старое поведение, воркер останавливается при healthcheck fail.
SKIP_ZAKUPKI_HEALTHCHECK = os.environ.get("SKIP_ZAKUPKI_HEALTHCHECK", "0") == "1"


@dataclass
class ProcessedFile:
    """Информация о локально скачанном файле."""

    url: str
    path: str
    original_name: str
    saved_as: str


def _now_utc() -> datetime:
    return datetime.utcnow()


def get_metadata_client() -> MongoClient:
    """
    Создаёт клиент для локальной Mongo с метаданными.
    Предполагается, что `mongo-init/init.js` уже создал пользователя `docling_user`.
    """
    url = (
        f"mongodb://{MONGO_METADATA_USER}:{MONGO_METADATA_PASSWORD}"
        f"@{MONGO_METADATA_SERVER}/?authSource=admin"
    )

    print("Подключение к ЛОКАЛЬНОЙ Mongo (docling_metadata) из воркера:")
    print(f"  URL: mongodb://{MONGO_METADATA_USER}:***@{MONGO_METADATA_SERVER}/?authSource=admin")
    print(f"  DB:  {MONGO_METADATA_DB}")

    client = MongoClient(
        url,
        serverSelectionTimeoutMS=10_000,
        connectTimeoutMS=10_000,
        socketTimeoutMS=10_000,
    )
    # Быстрая проверка подключения
    client.admin.command("ping")
    return client


def _reserve_pending_protocols(
    coll, limit: int
) -> List[Dict[str, Any]]:
    """
    Выбирает до `limit` документов со статусом "pending" и
    атомарно переводит их в статус "downloading", чтобы
    несколько воркеров не забирали один и тот же протокол.
    """
    reserved: List[Dict[str, Any]] = []

    for _ in range(limit):
        try:
            doc = coll.find_one_and_update(
                {"status": "pending"},
                {
                    "$set": {
                        "status": "downloading",
                        "updated_at": _now_utc(),
                    }
                },
                return_document=ReturnDocument.AFTER,
            )
        except PyMongoError as e:
            print(f"✗ Mongo error during find_one_and_update: {e}")
            break

        if not doc:
            break

        reserved.append(doc)

    return reserved


def _load_benchmark_protocols_from_json(
    json_path: str, limit: int
) -> List[Dict[str, Any]]:
    """
    Загружает протоколы из JSON-файла формата test_protocols_*.json
    (см. TEST_MONGODB_INSTRUCTIONS.md) для оффлайн-бенчмарка скачивания.

    Возвращает список документов в "почти Mongo" формате:
      { "_id": ..., "unit_id": ..., "purchaseNoticeNumber": ..., "urls": [...] }
    """
    print(f"Загрузка протоколов для бенчмарка из JSON: {json_path}")
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"✗ Не удалось прочитать JSON {json_path}: {e}")
        return []

    protocols = data.get("protocols") or {}
    reserved: List[Dict[str, Any]] = []

    for idx, (pn, entry) in enumerate(protocols.items(), start=1):
        if idx > limit:
            break

        urls: List[Dict[str, Any]] = []
        if isinstance(entry, dict):
            url = entry.get("url")
            if url:
                urls.append(
                    {
                        "url": url,
                        "fileName": entry.get("fileName"),
                    }
                )
        elif isinstance(entry, list):
            for u in entry:
                if not isinstance(u, dict):
                    continue
                url = u.get("url")
                if not url:
                    continue
                urls.append(
                    {
                        "url": url,
                        "fileName": u.get("fileName"),
                    }
                )

        reserved.append(
            {
                "_id": f"bench_{pn}",
                "unit_id": pn,
                "purchaseNoticeNumber": pn,
                "urls": urls,
            }
        )

    print(f"Загружено протоколов из JSON: {len(reserved)} (лимит {limit})")
    return reserved


def _download_files_for_protocol(
    unit_id: str, urls: List[Dict[str, Any]]
) -> Tuple[List[ProcessedFile], List[str]]:
    """
    Скачивает файлы по списку urls для одного протокола.

    Возвращает:
        (список успешно скачанных файлов, список ошибок)
    """
    success_files: List[ProcessedFile] = []
    errors: List[str] = []

    # Ограничиваем количество URL на протокол
    limited_urls = urls[:MAX_URLS_PER_PROTOCOL]

    unit_dir = PROTOCOLS_DOWNLOAD_DIR / unit_id
    unit_dir.mkdir(parents=True, exist_ok=True)

    if not limited_urls:
        return success_files, errors

    print(
        f"  [DOWNLOAD] unit_id={unit_id}: старт скачивания {len(limited_urls)} файлов "
        f"(потоков до {DOWNLOAD_CONCURRENCY})"
    )

    # Предварительно готовим задания с уже рассчитанными путями
    tasks: List[Tuple[int, str, str, Path]] = []
    for idx, url_info in enumerate(limited_urls, start=1):
        url = url_info.get("url")
        if not url:
            errors.append(f"[{unit_id}] URL отсутствует в urls[{idx - 1}]")
            continue

        original_name = url_info.get("fileName") or f"{unit_id}_{idx}.pdf"
        safe_name = sanitize_filename(original_name) or f"{unit_id}_{idx}.pdf"

        dest_path = unit_dir / safe_name
        counter = 1
        while dest_path.exists():
            stem, dot, ext = safe_name.rpartition(".")
            if dot:
                new_name = f"{stem}_{counter}.{ext}"
            else:
                new_name = f"{safe_name}_{counter}"
            dest_path = unit_dir / new_name
            counter += 1

        tasks.append((idx, url, original_name, dest_path))

    def _download_one(idx: int, url: str, original_name: str, dest_path: Path):
        start_ts = time.time()
        print(f"    [DL-{idx}] ➜ {url} → {dest_path.name}")
        ok, result = download_document(
            url=url,
            dest_path=dest_path,
            timeout=DOWNLOAD_HTTP_TIMEOUT,
            show_progress=False,
            delay=0.1,
        )
        elapsed = time.time() - start_ts
        return idx, url, original_name, dest_path, ok, result, elapsed

    # Параллельное скачивание в нескольких потоках
    max_workers = max(1, min(DOWNLOAD_CONCURRENCY, len(tasks)))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {
            executor.submit(_download_one, idx, url, original_name, dest_path): (
                idx,
                url,
            )
            for idx, url, original_name, dest_path in tasks
        }

        for future in as_completed(future_map):
            idx, url = future_map[future]
            try:
                (
                    _i,
                    _url,
                    original_name,
                    dest_path,
                    ok,
                    result,
                    elapsed,
                ) = future.result()
            except Exception as e:
                msg = f"[{unit_id}] Исключение при скачивании (idx={idx}, url={url}): {e}"
                print(f"    [DL-{idx}] ✗ {msg}")
                errors.append(msg)
                continue

            if ok:
                print(
                    f"    [DL-{idx}] ✓ скачано за {elapsed:.2f} сек → {dest_path.name}"
                )
                success_files.append(
                    ProcessedFile(
                        url=url,
                        path=str(dest_path.absolute()),
                        original_name=original_name,
                        saved_as=dest_path.name,
                    )
                )
            else:
                msg = f"[{unit_id}] Ошибка скачивания {url}: {result} (за {elapsed:.2f} сек)"
                print(f"    [DL-{idx}] ✗ {msg}")
                errors.append(msg)

    print(
        f"  [DOWNLOAD] unit_id={unit_id}: успешно={len(success_files)}, "
        f"ошибок={len(errors)}"
    )

    return success_files, errors


def _send_files_to_router(
    files: List[ProcessedFile],
) -> Tuple[List[str], List[str]]:
    """
    Отправляет каждый файл в Router `/upload`.

    Возвращает:
        (список unit_id от Router, список ошибок)
    """
    unit_ids: List[str] = []
    errors: List[str] = []

    for f in files:
        print(f"    [ROUTER] ➜ отправка файла в Router: {f.path}")
        try:
            with open(f.path, "rb") as fp:
                files_payload = {"file": (f.saved_as, fp, "application/octet-stream")}
                resp = requests.post(
                    ROUTER_UPLOAD_URL,
                    files=files_payload,
                    timeout=ROUTER_HTTP_TIMEOUT,
                )
        except Exception as e:
            msg = f"[router] Ошибка при отправке {f.path}: {e}"
            print(f"    [ROUTER] ✗ {msg}")
            errors.append(msg)
            continue

        if resp.status_code != 200:
            msg = f"[router] HTTP {resp.status_code} для {f.path}: {resp.text[:200]}"
            print(f"    [ROUTER] ✗ {msg}")
            errors.append(msg)
            continue

        try:
            payload = resp.json()
        except Exception as e:
            msg = f"[router] Некорректный JSON ответ для {f.path}: {e}"
            print(f"    [ROUTER] ✗ {msg}")
            errors.append(msg)
            continue

        status = payload.get("status")
        unit_id = payload.get("unit_id")

        if status != "processed" or not unit_id:
            msg = (
                f"[router] Ответ без unit_id/processed для {f.path}: "
                f"{json.dumps(payload, ensure_ascii=False)[:200]}"
            )
            print(f"    [ROUTER] ✗ {msg}")
            errors.append(msg)
            continue

        print(f"    [ROUTER] ✓ OK для {f.path}, unit_id={unit_id}")
        unit_ids.append(unit_id)

    return unit_ids, errors


def process_pending_protocols() -> Dict[str, Any]:
    """
    Основная функция воркера:
    - health-check zakupki.gov.ru
    - резервирование pending-протоколов
    - скачивание файлов
    - отправка в Router
    - обновление статуса в Mongo
    """
    print("=" * 80)
    print("PROCESS PROTOCOL UNITS WORKER")
    print(f"Лимит протоколов за запуск: {PROTOCOLS_PROCESS_LIMIT}")
    print(f"Максимум URL на протокол: {MAX_URLS_PER_PROTOCOL}")
    print(f"Router /upload: {ROUTER_UPLOAD_URL}")
    print("=" * 80)

    # Health-check zakupki.gov.ru через текущий сетевой стек (VPN)
    print("Проверка доступности zakupki.gov.ru через текущую сеть (VPN)...")
    health_ok = check_zakupki_health()
    if not health_ok:
        if not SKIP_ZAKUPKI_HEALTHCHECK:
            print("✗ zakupki.gov.ru недоступен (нет VPN / блокировка). Воркер завершён.")
            return {
                "started_at": _now_utc().isoformat(),
                "finished_at": _now_utc().isoformat(),
                "duration_sec": 0.0,
                "processed_ok": 0,
                "processed_error": 0,
                "reserved": 0,
                "health_ok": False,
            }

        print(
            "⚠ zakupki.gov.ru недоступен, но SKIP_ZAKUPKI_HEALTHCHECK=1 — "
            "продолжаем работу на свой страх и риск."
        )
    else:
        print("✓ zakupki.gov.ru доступен, продолжаем.")

    # Режим оффлайн-бенчмарка: берём протоколы из JSON вместо Mongo.
    benchmark_json_path = os.environ.get("BENCHMARK_PROTOCOLS_JSON")
    use_benchmark_json = bool(benchmark_json_path)

    client: Optional[MongoClient] = None
    coll = None

    try:
        if use_benchmark_json:
            print(
                f"Режим БЕНЧМАРКА: читаем протоколы из JSON {benchmark_json_path}, "
                f"лимит={PROTOCOLS_PROCESS_LIMIT}"
            )
            reserved = _load_benchmark_protocols_from_json(
                benchmark_json_path, PROTOCOLS_PROCESS_LIMIT
            )
            if not reserved:
                print("Нет протоколов для бенчмарка (JSON пустой или не прочитан).")
                return {
                    "started_at": _now_utc().isoformat(),
                    "finished_at": _now_utc().isoformat(),
                    "duration_sec": 0.0,
                    "processed_ok": 0,
                    "processed_error": 0,
                    "reserved": 0,
                    "health_ok": health_ok,
                }
        else:
            print("Режим MONGO: резервируем протоколы из локальной docling_metadata...")
            client = get_metadata_client()
            try:
                db = client[MONGO_METADATA_DB]
                coll = db[MONGO_METADATA_PROTOCOLS_COLLECTION]

                # Резервируем pending-документы
                reserved = _reserve_pending_protocols(coll, PROTOCOLS_PROCESS_LIMIT)
                if not reserved:
                    print("Нет протоколов со статусом 'pending' для обработки.")
                    return {
                        "started_at": _now_utc().isoformat(),
                        "finished_at": _now_utc().isoformat(),
                        "duration_sec": 0.0,
                        "processed_ok": 0,
                        "processed_error": 0,
                        "reserved": 0,
                        "health_ok": True,
                    }
            except Exception:
                # Если что-то пошло не так при подключении к Mongo,
                # пробрасываем исключение выше — это "боевой" режим.
                if client is not None:
                    client.close()
                raise

        total = len(reserved)
        print(f"Зарезервировано протоколов для обработки: {total}")

        processed_ok = 0
        processed_error = 0
        total_download_time = 0.0
        total_router_time = 0.0

        for idx, doc in enumerate(reserved, start=1):
            proto_id = doc.get("_id")
            unit_id = doc.get("unit_id")
            pn = doc.get("purchaseNoticeNumber")
            urls = doc.get("urls") or []

            print("-" * 80)
            print(
                f"[{idx}/{total}] Протокол: _id={proto_id}, unit_id={unit_id}, "
                f"purchaseNoticeNumber={pn}, urls={len(urls)}"
            )

            if not urls:
                msg = "В документе отсутствует поле urls, нечего скачивать."
                print(f"✗ {msg}")
                if coll is not None:
                    try:
                        coll.update_one(
                            {"_id": proto_id},
                            {
                                "$set": {
                                    "status": "error",
                                    "last_error": msg,
                                    "updated_at": _now_utc(),
                                }
                            },
                        )
                    except PyMongoError as e:
                        print(f"✗ Mongo error при обновлении статуса: {e}")
                processed_error += 1
                continue

            # 1. Скачиваем файлы (замеряем время именно скачивания)
            dl_start = time.time()
            files, dl_errors = _download_files_for_protocol(unit_id, urls)
            dl_elapsed = time.time() - dl_start
            total_download_time += dl_elapsed
            print(f"  [TIMING] DOWNLOAD unit_id={unit_id} занял {dl_elapsed:.2f} сек")
            for e in dl_errors:
                print(f"  [DOWNLOAD] {e}")

            if not files:
                msg = "Не удалось скачать ни одного файла для протокола."
                print(f"✗ {msg}")
                if coll is not None:
                    try:
                        coll.update_one(
                            {"_id": proto_id},
                            {
                                "$set": {
                                    "status": "error",
                                    "last_error": msg + " " + "; ".join(dl_errors),
                                    "updated_at": _now_utc(),
                                }
                            },
                        )
                    except PyMongoError as e:
                        print(f"✗ Mongo error при обновлении статуса: {e}")
                processed_error += 1
                continue

            # 2. Отправляем в Router (замеряем время Router-запросов),
            #    либо пропускаем, если DRY_RUN_ROUTER=1 (чистый бенчмарк скачивания).
            router_units: List[str] = []
            router_errors: List[str] = []

            if DRY_RUN_ROUTER:
                print(
                    f"  [DRY-RUN] Router отключён (DRY_RUN_ROUTER=1), "
                    f"файлы скачаны локально, но не отправляются на {ROUTER_UPLOAD_URL}"
                )
                rt_elapsed = 0.0
            else:
                rt_start = time.time()
                router_units, router_errors = _send_files_to_router(files)
                rt_elapsed = time.time() - rt_start
                total_router_time += rt_elapsed
                print(
                    f"  [TIMING] ROUTER unit_id={unit_id} занял {rt_elapsed:.2f} сек"
                )
            for e in router_errors:
                print(f"  [ROUTER] {e}")

            if not router_units and not DRY_RUN_ROUTER:
                msg = "Router не вернул ни одного unit_id."
                print(f"✗ {msg}")
                if coll is not None:
                    try:
                        coll.update_one(
                            {"_id": proto_id},
                            {
                                "$set": {
                                    "status": "error",
                                    "last_error": msg + " " + "; ".join(router_errors),
                                    "updated_at": _now_utc(),
                                }
                            },
                        )
                    except PyMongoError as e:
                        print(f"✗ Mongo error при обновлении статуса: {e}")
                processed_error += 1
                continue

            # 3. Успешно поставили протокол в работу
            if DRY_RUN_ROUTER:
                print(
                    f"✓ Протокол {pn} (unit_id={unit_id}) успешно скачан (DRY-RUN Router)."
                )
            else:
                print(
                    f"✓ Протокол {pn} (unit_id={unit_id}) отправлен в Router."
                    f" Router unit_ids: {router_units}"
                )
                if coll is not None:
                    try:
                        coll.update_one(
                            {"_id": proto_id},
                            {
                                "$set": {
                                    "status": "processing",
                                    "router_unit_ids": router_units,
                                    "last_error": None,
                                    "updated_at": _now_utc(),
                                }
                            },
                        )
                    except PyMongoError as e:
                        print(f"✗ Mongo error при обновлении статуса: {e}")

            processed_ok += 1

        print("=" * 80)
        print("ИТОГ ВОРКЕРА:")
        print(f"  Успешно поставлено в обработку протоколов: {processed_ok}")
        print(f"  Завершено с ошибкой: {processed_error}")
        print(f"  Суммарное время скачивания (DOWNLOAD): {total_download_time:.2f} сек")
        print(f"  Суммарное время Router (UPLOAD): {total_router_time:.2f} сек")

        return {
            "started_at": _now_utc().isoformat(),
            "finished_at": _now_utc().isoformat(),
            "duration_sec": 0.0,  # перезапишем в main, где замеряем точно
            "processed_ok": processed_ok,
            "processed_error": processed_error,
            "reserved": len(reserved),
            "health_ok": True,
            "download_time_total": total_download_time,
            "router_time_total": total_router_time,
        }
    finally:
        if client is not None:
            client.close()


def main() -> None:
    started_at = _now_utc()
    start_ts = time.time()
    try:
        worker_metrics = process_pending_protocols()
        finished_at = _now_utc()
        duration_sec = time.time() - start_ts

        # Если process_pending_protocols вернул dict, дополняем его
        if isinstance(worker_metrics, dict):
            worker_metrics.setdefault("started_at", started_at.isoformat())
            worker_metrics["finished_at"] = finished_at.isoformat()
            worker_metrics["duration_sec"] = duration_sec
        else:
            # fallback, если по какой-то причине вернулось не dict
            worker_metrics = {
                "started_at": started_at.isoformat(),
                "finished_at": finished_at.isoformat(),
                "duration_sec": duration_sec,
                "processed_ok": None,
                "processed_error": None,
                "reserved": None,
                "health_ok": None,
            }

        # Пишем метрики в JSON-отчёт
        ts_str = started_at.strftime("%Y%m%d_%H%M%S")
        report_path = Path(f"download_metrics_{ts_str}.json")
        try:
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(worker_metrics, f, ensure_ascii=False, indent=2)
            print(f"\nMETRICS: отчёт сохранён в {report_path}")
            if worker_metrics.get("processed_ok"):
                avg = worker_metrics["duration_sec"] / max(
                    1, worker_metrics["processed_ok"]
                )
                print(
                    f"METRICS: всего протоколов OK={worker_metrics['processed_ok']}, "
                    f"время={worker_metrics['duration_sec']:.1f} сек, "
                    f"среднее на протокол ≈ {avg:.3f} сек"
                )
        except Exception as e:
            print(f"✗ Не удалось сохранить metrics JSON: {e}")

    except KeyboardInterrupt:
        print("\nОстановка по Ctrl+C")
    except Exception as e:
        print(f"\n✗ Ошибка в воркере: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()



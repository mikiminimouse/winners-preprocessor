#!/usr/bin/env python3
"""
Синхронизация протоколов из удалённой MongoDB в локальную Mongo (docling_metadata.protocols).

Цели:
- Вытащить ограниченное количество протоколов (юнитов) из удалённой БД `protocols223.purchaseProtocol`.
- Для каждого протокола собрать структуру, аналогичную MCP:
  purchaseNoticeNumber → один или несколько {url, fileName, ...}.
- Сгенерировать unit_id в формате, совместимом с existing pipeline: "UNIT_<16hex>".
- Сохранить метаданные в локальную БД `docling_metadata.protocols`, чтобы дальше:
  - скачивать документы по urls,
  - создавать манифесты/units,
  - запускать preprocessor + docling,
  - и передавать результат в LLM.

Важно:
- Удалённая Mongo:
  - читаем параметры из `.env`:
    mongoServer, readAllUser, readAllPassword, sslCertPath.
- Локальная Mongo (docling_metadata):
  - читаем MONGO_SERVER, MONGO_METADATA_USER, MONGO_METADATA_PASSWORD, MONGO_METADATA_DB.
- РФ VPN для этого скрипта НЕ нужен (VPN нужен только для скачивания файлов с zakupki.gov.ru).
"""

from __future__ import annotations

import sys
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from pymongo import MongoClient, ASCENDING
from pymongo.errors import PyMongoError


@dataclass
class UrlInfo:
    url: str
    fileName: str
    guid: Optional[str] = None
    contentUid: Optional[str] = None
    description: Optional[str] = None


@dataclass
class ProtocolMeta:
    unit_id: str
    purchaseNoticeNumber: str
    loadDate: datetime
    urls: List[UrlInfo]
    multi_url: bool
    url_kinds: List[str]
    source: str
    status: str
    created_at: datetime
    updated_at: datetime


def _load_env() -> Dict[str, str]:
    """
    Простейший парсер .env, чтобы не зависеть от python-dotenv.
    Поддерживает строки вида KEY=VALUE, игнорирует комментарии и пустые строки.
    """
    cfg: Dict[str, str] = {}
    try:
        with open(".env", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                cfg[key.strip()] = value.strip()
    except FileNotFoundError:
        # если .env нет — оставляем cfg пустым, дальше вывалимся по проверкам
        pass
    # Перекрываем значениями из реальных env-переменных (имеют приоритет)
    import os as _os

    for k, v in _os.environ.items():
        cfg.setdefault(k, v)
    return cfg


def _get_remote_mongo_client(cfg: Dict[str, str]) -> MongoClient:
    """Клиент для удалённой Mongo с протоколами (protocols223)."""
    mongo_hosts = cfg.get("mongoServer")
    username = cfg.get("readAllUser")
    password = cfg.get("readAllPassword")
    ssl_cert = cfg.get("sslCertPath")

    if not all([mongo_hosts, username, password, ssl_cert]):
        print("✗ Не все параметры удалённой Mongo заданы в .env:", file=sys.stderr)
        print(f"  mongoServer:    {'OK' if mongo_hosts else 'MISSING'}", file=sys.stderr)
        print(f"  readAllUser:    {'OK' if username else 'MISSING'}", file=sys.stderr)
        print(f"  readAllPassword:{'OK' if password else 'MISSING'}", file=sys.stderr)
        print(f"  sslCertPath:    {'OK' if ssl_cert else 'MISSING'}", file=sys.stderr)
        sys.exit(1)

    url_mongo = f"mongodb://{username}:{password}@{mongo_hosts}/?authSource=protocols223"

    print("Подключение к УДАЛЁННОЙ Mongo (protocols223):")
    print(f"  URL: mongodb://{username}:***@{mongo_hosts}/?authSource=protocols223")
    print(f"  CA:  {ssl_cert}")

    client = MongoClient(
        url_mongo,
        tls=True,
        authMechanism="SCRAM-SHA-1",
        tlsAllowInvalidHostnames=True,
        tlsCAFile=ssl_cert,
        serverSelectionTimeoutMS=20_000,
        connectTimeoutMS=20_000,
        socketTimeoutMS=20_000,
    )
    client.admin.command("ping")
    return client


def _get_local_mongo_client(cfg: Dict[str, str]) -> MongoClient:
    """
    Клиент для локальной Mongo с метаданными (docling_metadata).

    По умолчанию использует docling-параметры:
    - MONGO_SERVER (обычно mongodb:27017 в docker-compose)
    - MONGO_METADATA_USER / MONGO_METADATA_PASSWORD
    - MONGO_METADATA_DB (docling_metadata)
    """
    # ВАЖНО: для локальной БД метаданных НЕ используем удалённый mongoServer.
    # Здесь нас интересует локальный Mongo из docker-compose (docling_mongodb),
    # доступный с хоста по localhost:27017, если не переопределено отдельно.
    mongo_server = cfg.get("LOCAL_MONGO_SERVER") or "localhost:27017"
    user = cfg.get("MONGO_METADATA_USER", "docling_user")
    password = cfg.get("MONGO_METADATA_PASSWORD", "password")
    db_name = cfg.get("MONGO_METADATA_DB", "docling_metadata")

    url = f"mongodb://{user}:{password}@{mongo_server}/?authSource=admin"
    print()
    print("Подключение к ЛОКАЛЬНОЙ Mongo (docling_metadata):")
    print(f"  URL: mongodb://{user}:***@{mongo_server}/?authSource=admin")
    print(f"  DB:  {db_name}")

    client = MongoClient(
        url,
        serverSelectionTimeoutMS=10_000,
        connectTimeoutMS=10_000,
        socketTimeoutMS=10_000,
    )
    client.admin.command("ping")
    return client


def _generate_unit_id() -> str:
    """Генерирует unit_id в формате UNIT_<16hex>, совместимый с существующими манифестами."""
    # Берём первые 16 hex символов из uuid4
    return f"UNIT_{uuid.uuid4().hex[:16]}"


def _classify_multi_url(urls: List[UrlInfo]) -> List[str]:
    """Очень простая классификация случаев с несколькими URL на один протокол."""
    kinds: List[str] = []
    if len(urls) <= 1:
        return kinds

    names = [u.fileName.lower() for u in urls]

    def has_ext(ext: str) -> bool:
        return any(name.endswith(ext) for name in names)

    if has_ext(".pdf") and (has_ext(".doc") or has_ext(".docx")):
        kinds.append("pdf+doc/docx")
    if has_ext(".html") or has_ext(".htm"):
        if has_ext(".pdf"):
            kinds.append("html+pdf")
        else:
            kinds.append("html-only")
    if any("эп" in name or "podpis" in name or "ep " in name for name in names):
        kinds.append("signature/ep")
    if has_ext(".zip") or has_ext(".7z") or has_ext(".rar"):
        kinds.append("archive+files")

    if not kinds:
        kinds.append("multi-uncategorized")

    return kinds


def _extract_urls_from_attachments(raw_doc: Dict[str, Any]) -> Tuple[List[UrlInfo], Optional[datetime]]:
    """Извлекает список UrlInfo и дату loadDate из Mongo-документа purchaseProtocol."""
    load_date = raw_doc.get("loadDate")
    if isinstance(load_date, str):
        try:
            load_date = datetime.fromisoformat(load_date)
        except Exception:
            load_date = None

    urls: List[UrlInfo] = []
    attachments = raw_doc.get("attachments")

    def add_from_doc(doc: Dict[str, Any]) -> None:
        url = doc.get("url") or doc.get("downloadUrl") or doc.get("fileUrl")
        if not url:
            return
        urls.append(
            UrlInfo(
                url=url,
                fileName=doc.get("fileName") or doc.get("name") or "",
                guid=doc.get("guid"),
                contentUid=doc.get("contentUid"),
                description=doc.get("description"),
            )
        )

    if isinstance(attachments, dict):
        # Ожидаемый формат: attachments.document
        docs_field = attachments.get("document", [])
        if isinstance(docs_field, dict):
            docs_field = [docs_field]
        if isinstance(docs_field, list):
            for item in docs_field:
                if isinstance(item, dict):
                    add_from_doc(item)
    elif isinstance(attachments, list):
        # На всякий случай — если attachments уже список документов
        for item in attachments:
            if isinstance(item, dict):
                add_from_doc(item)

    return urls, load_date if isinstance(load_date, datetime) else None


def sync_remote_protocols() -> None:
    """
    Основная функция:
    - читает ограниченное количество новых протоколов из удалённой Mongo;
    - создаёт/обновляет документы в docling_metadata.protocols.
    """
    cfg = _load_env()

    # лимиты и окно
    limit = int(cfg.get("REMOTE_PROTOCOLS_SYNC_LIMIT", "200"))
    days_back = int(cfg.get("REMOTE_PROTOCOLS_SYNC_DAYS_BACK", "7"))

    print("=" * 80)
    print("SYNC REMOTE PROTOCOLS → LOCAL docling_metadata.protocols")
    print(f"Лимит протоколов за запуск: {limit}")
    print(f"Окно по loadDate (дней назад): {days_back}")

    remote_client = _get_remote_mongo_client(cfg)
    local_client = _get_local_mongo_client(cfg)

    try:
        remote_db = remote_client["protocols223"]
        remote_coll = remote_db["purchaseProtocol"]

        local_db_name = cfg.get("MONGO_METADATA_DB", "docling_metadata")
        local_db = local_client[local_db_name]
        local_coll = local_db["protocols"]

        # Инициализируем индексы для локальной коллекции (без падения, если уже есть)
        try:
            local_coll.create_index([("purchaseNoticeNumber", ASCENDING)], name="pn_idx")
            local_coll.create_index([("unit_id", ASCENDING)], unique=False, name="unit_idx")
            local_coll.create_index([("status", ASCENDING)], name="status_idx")
            local_coll.create_index([("loadDate", ASCENDING)], name="loadDate_idx")
        except PyMongoError as e_idx:
            print(f"⚠ Ошибка при создании индексов (можно игнорировать, если уже существуют): {e_idx}")

        # Берём окно по дате, начинаем с более новых
        now = datetime.utcnow()
        start_dt = now - timedelta(days=days_back)

        query = {
            "loadDate": {
                "$gte": datetime(start_dt.year, start_dt.month, start_dt.day, 0, 0, 0),
                "$lte": datetime(now.year, now.month, now.day, 23, 59, 59),
            }
        }

        projection = {
            "purchaseInfo.purchaseNoticeNumber": 1,
            "attachments": 1,
            "loadDate": 1,
        }

        print()
        print(f"Запрос к удалённой Mongo по окну loadDate: {start_dt.date()} .. {now.date()}")

        cursor = remote_coll.find(
            query,
            projection,
            no_cursor_timeout=True,
            batch_size=1000,
        ).sort("loadDate", -1)  # от новых к старым

        inserted = 0
        skipped_existing = 0
        scanned = 0

        try:
            for raw_doc in cursor:
                if inserted >= limit:
                    break

                scanned += 1
                purchase_info = raw_doc.get("purchaseInfo") or {}
                pn = purchase_info.get("purchaseNoticeNumber")
                if not pn:
                    continue

                # Идемпотентность: проверяем, есть ли уже запись по PN
                existing = local_coll.find_one(
                    {
                        "purchaseNoticeNumber": pn,
                        "source": "remote_mongo",
                    },
                    {"_id": 1},
                )
                if existing:
                    skipped_existing += 1
                    continue

                urls, load_date = _extract_urls_from_attachments(raw_doc)
                if not urls:
                    # нам нечего скачивать для этого протокола
                    continue

                unit_id = _generate_unit_id()
                multi = len(urls) > 1
                url_kinds = _classify_multi_url(urls) if multi else []
                now_ts = datetime.utcnow()

                meta = ProtocolMeta(
                    unit_id=unit_id,
                    purchaseNoticeNumber=str(pn),
                    loadDate=load_date or raw_doc.get("loadDate", now_ts),
                    urls=urls,
                    multi_url=multi,
                    url_kinds=url_kinds,
                    source="remote_mongo",
                    status="pending",
                    created_at=now_ts,
                    updated_at=now_ts,
                )

                doc_to_insert: Dict[str, Any] = asdict(meta)
                # asdict сериализует UrlInfo в словари автоматически

                local_coll.insert_one(doc_to_insert)
                inserted += 1

                if inserted % 50 == 0:
                    print(
                        f"  Вставлено {inserted} протоколов, "
                        f"пропущено (уже были) {skipped_existing}, просмотрено {scanned}",
                        flush=True,
                    )

        finally:
            cursor.close()

        print()
        print("РЕЗУЛЬТАТ СИНХРОНИЗАЦИИ:")
        print(f"  просмотрено документов в удалённой Mongo: {scanned}")
        print(f"  вставлено новых протоколов в docling_metadata.protocols: {inserted}")
        print(f"  пропущено, т.к. уже были в локальной коллекции: {skipped_existing}")

    finally:
        remote_client.close()
        local_client.close()


def main() -> None:
    try:
        sync_remote_protocols()
    except KeyboardInterrupt:
        print("\nОстановка по Ctrl+C")
    except Exception as e:
        print(f"\n✗ Ошибка при синхронизации: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()



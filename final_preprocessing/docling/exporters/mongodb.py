"""
MongoDB экспорт DoclingDocument в local MongoDB.
"""
import os
import logging
from pathlib import Path
from typing import Any, Optional, Dict
from datetime import datetime

try:
    from pymongo import MongoClient
    from pymongo.errors import PyMongoError
    PYMONGO_AVAILABLE = True
except ImportError:
    PYMONGO_AVAILABLE = False
    MongoClient = None

logger = logging.getLogger(__name__)


def get_mongodb_client() -> Optional[Any]:
    """
    Создает подключение к local MongoDB.

    Использует переменные окружения:
    - LOCAL_MONGO_SERVER или MONGO_METADATA_SERVER (default: localhost:27018)
    - MONGO_METADATA_USER (default: admin)
    - MONGO_METADATA_PASSWORD (default: password)
    - MONGO_METADATA_DB (default: docling_metadata)

    Returns:
        MongoClient или None при ошибке
    """
    if not PYMONGO_AVAILABLE:
        logger.error("pymongo not available. Install with: pip install pymongo>=4.0.0")
        return None

    # Получаем конфигурацию из env
    server = os.environ.get(
        "LOCAL_MONGO_SERVER",
        os.environ.get("MONGO_METADATA_SERVER", "localhost:27018")
    )
    user = os.environ.get("MONGO_METADATA_USER", "admin")
    password = os.environ.get("MONGO_METADATA_PASSWORD", "password")
    db_name = os.environ.get("MONGO_METADATA_DB", "docling_metadata")

    try:
        # Формируем connection string
        if ":" in server:
            host, port = server.split(":")
        else:
            host = server
            port = "27018"

        # Подключение с аутентификацией
        if user and password:
            mongo_url = f"mongodb://{user}:{password}@{host}:{port}/?authSource=admin"
        else:
            mongo_url = f"mongodb://{host}:{port}/"

        client = MongoClient(mongo_url, serverSelectionTimeoutMS=5000)

        # Проверяем подключение
        client.admin.command("ping")
        logger.info(f"Connected to MongoDB: {host}:{port}")

        return client

    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        return None


def export_to_mongodb(
    document: Any,
    manifest: Dict,
    unit_id: str,
    collection_name: str = "docling_results",
) -> Optional[str]:
    """
    Экспортирует DoclingDocument в MongoDB.

    Args:
        document: Document объект от Docling
        manifest: Полный manifest из docprep
        unit_id: Идентификатор UNIT
        collection_name: Имя коллекции (default: docling_results)

    Returns:
        ID документа в MongoDB или None при ошибке
    """
    if not PYMONGO_AVAILABLE:
        raise ImportError("pymongo not available")

    client = get_mongodb_client()
    if not client:
        raise ConnectionError("Failed to connect to MongoDB")

    try:
        db_name = os.environ.get("MONGO_METADATA_DB", "docling_metadata")
        db = client[db_name]
        collection = db[collection_name]

        # Сериализуем документ
        if hasattr(document, "model_dump"):
            doc_dict = document.model_dump()
        elif hasattr(document, "dict"):
            doc_dict = document.dict()
        elif hasattr(document, "__dict__"):
            doc_dict = document.__dict__
        else:
            doc_dict = {"document": str(document)}

        # Формируем документ для MongoDB
        mongo_doc = {
            "unit_id": unit_id,
            "protocol_id": manifest.get("protocol_id", ""),
            "protocol_date": manifest.get("protocol_date", ""),
            "route": manifest.get("processing", {}).get("route", "unknown"),
            "docling_document": doc_dict,
            "export_formats": ["mongodb"],
            "created_at": datetime.utcnow(),
            "manifest": manifest,  # Полный manifest для контекста
        }

        # Добавляем processing_time если есть в manifest
        if "processing_time" in manifest.get("processing", {}):
            mongo_doc["processing_time"] = manifest["processing"]["processing_time"]

        # Вставляем или обновляем документ
        result = collection.update_one(
            {"unit_id": unit_id},
            {"$set": mongo_doc},
            upsert=True,
        )

        # Создаем индексы если их еще нет
        _ensure_indexes(collection)

        doc_id = result.upserted_id if result.upserted_id else collection.find_one(
            {"unit_id": unit_id}
        )["_id"]

        logger.info(f"Exported document to MongoDB: unit_id={unit_id}, _id={doc_id}")
        return str(doc_id)

    except PyMongoError as e:
        logger.error(f"MongoDB error: {e}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Failed to export to MongoDB: {e}", exc_info=True)
        raise
    finally:
        client.close()


def _ensure_indexes(collection):
    """Создает индексы для коллекции если их еще нет."""
    try:
        # Индекс по unit_id (уникальный)
        collection.create_index("unit_id", unique=True, background=True)

        # Индекс по protocol_date для фильтрации
        collection.create_index("protocol_date", background=True)

        # Индекс по route для фильтрации
        collection.create_index("route", background=True)

        # Составной индекс для поиска
        collection.create_index([("protocol_date", 1), ("route", 1)], background=True)

        logger.debug("MongoDB indexes ensured")
    except Exception as e:
        logger.warning(f"Failed to create indexes: {e}")


"""
MongoDB операции для router микросервиса.
Подключение к удаленной БД протоколов и локальной БД метаданных.
"""
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from pymongo import MongoClient
from pymongo.errors import PyMongoError
from fastapi import HTTPException

from .config import (
    MONGO_SERVER, MONGO_USER, MONGO_PASSWORD, MONGO_SSL_CERT,
    MONGO_PROTOCOLS_DB, MONGO_PROTOCOLS_COLLECTION,
    MONGO_METADATA_USER, MONGO_METADATA_PASSWORD, MONGO_METADATA_DB,
    MONGO_METADATA_COLLECTION, MONGO_METRICS_COLLECTION, PROTOCOLS_COUNT_LIMIT
)

# Глобальные клиенты (инициализируются при первом использовании)
_mongo_client: Optional[MongoClient] = None
_mongo_metadata_client: Optional[MongoClient] = None

# Флаги для подавления повторяющихся ошибок
_mongo_error_shown = False
_mongo_metadata_error_shown = False


def get_mongo_client() -> Optional[MongoClient]:
    """Получает или создает MongoDB клиент для чтения протоколов."""
    global _mongo_client
    
    if _mongo_client is not None:
        try:
            _mongo_client.admin.command('ping')
            return _mongo_client
        except Exception:
            _mongo_client = None
    
    if not all([MONGO_SERVER, MONGO_USER, MONGO_PASSWORD]):
        return None
    
    try:
        url_mongo = f'mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_SERVER}/?authSource=protocols223'
        
        if MONGO_SSL_CERT:
            _mongo_client = MongoClient(
                url_mongo,
                tls=True,
                authMechanism="SCRAM-SHA-1",
                tlsAllowInvalidHostnames=True,
                tlsCAFile=MONGO_SSL_CERT
            )
        else:
            _mongo_client = MongoClient(url_mongo)
        
        _mongo_client.admin.command('ping')
        return _mongo_client
    except Exception as e:
        print(f"❌ MongoDB connection error: {e}")
        return None


def get_mongo_metadata_client() -> Optional[MongoClient]:
    """Получает или создает MongoDB клиент для записи метаданных."""
    global _mongo_metadata_client, _mongo_metadata_error_shown
    
    if _mongo_metadata_client is not None:
        try:
            _mongo_metadata_client.admin.command('ping')
            return _mongo_metadata_client
        except Exception:
            _mongo_metadata_client = None
    
    if not all([MONGO_SERVER, MONGO_METADATA_USER, MONGO_METADATA_PASSWORD]):
        return None
    
    try:
        url_mongo = f'mongodb://{MONGO_METADATA_USER}:{MONGO_METADATA_PASSWORD}@{MONGO_SERVER}/?authSource=admin'
        
        if MONGO_SSL_CERT:
            _mongo_metadata_client = MongoClient(
                url_mongo,
                tls=True,
                authMechanism="SCRAM-SHA-1",
                tlsAllowInvalidHostnames=True,
                tlsCAFile=MONGO_SSL_CERT
            )
        else:
            _mongo_metadata_client = MongoClient(url_mongo)
        
        _mongo_metadata_client.admin.command('ping')
        # Сбрасываем флаг ошибки при успешном подключении
        _mongo_metadata_error_shown = False
        return _mongo_metadata_client
    except Exception as e:
        # Показываем ошибку только один раз
        if not _mongo_metadata_error_shown:
            error_msg = str(e)
            # Сокращаем длинные сообщения об ошибках
            if len(error_msg) > 200:
                error_msg = error_msg[:200] + "..."
            print(f"⚠️  MongoDB metadata недоступна: {error_msg}")
            print("💡 Метрики будут сохраняться локально")
            _mongo_metadata_error_shown = True
        return None


def get_protocols_by_date(date_str: str) -> Dict[str, Any]:
    """Получает протоколы по дате из удаленной MongoDB."""
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"Неверный формат даты '{date_str}'. Используйте формат YYYY-MM-DD")
    
    client = get_mongo_client()
    if not client:
        raise HTTPException(status_code=500, detail="MongoDB не настроен или недоступен")
    
    try:
        db = client[MONGO_PROTOCOLS_DB]
        collection = db[MONGO_PROTOCOLS_COLLECTION]
        
        start_of_day = datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0)
        end_of_day = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59)
        
        query = {
            "loadDate": {
                "$gte": start_of_day,
                "$lte": end_of_day
            }
        }
        
        result_dict = {}
        protocols = collection.find(query).limit(PROTOCOLS_COUNT_LIMIT)
        
        for protocol in protocols:
            purchase_info = protocol.get('purchaseInfo', {})
            purchase_notice_number = purchase_info.get('purchaseNoticeNumber')
            attachments = protocol.get('attachments', {})
            documents = attachments.get('document', [])
            
            if isinstance(documents, dict):
                documents = [documents]
            
            urls = []
            for doc in documents:
                if isinstance(doc, dict) and 'url' in doc:
                    urls.append({
                        "url": doc.get('url'),
                        "fileName": doc.get('fileName', '')
                    })
            
            if purchase_notice_number and urls:
                if len(urls) == 1:
                    result_dict[purchase_notice_number] = urls[0]
                else:
                    result_dict[purchase_notice_number] = urls
        
        return result_dict
    
    except PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"MongoDB error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


def save_manifest_to_mongo(unit_id: str, manifest: Dict) -> bool:
    """Сохраняет manifest в локальную MongoDB."""
    client = get_mongo_metadata_client()
    if not client:
        return False
    
    try:
        db = client[MONGO_METADATA_DB]
        collection = db[MONGO_METADATA_COLLECTION]
        
        manifest["updated_at"] = datetime.utcnow().isoformat()
        
        collection.update_one(
            {"unit_id": unit_id},
            {"$set": manifest},
            upsert=True
        )
        return True
    except Exception as e:
        print(f"❌ Error saving manifest to MongoDB: {e}")
        return False


def get_manifest_from_mongo(unit_id: str) -> Optional[Dict]:
    """Получает manifest из локальной MongoDB."""
    client = get_mongo_metadata_client()
    if not client:
        return None
    
    try:
        db = client[MONGO_METADATA_DB]
        collection = db[MONGO_METADATA_COLLECTION]
        
        manifest = collection.find_one({"unit_id": unit_id})
        if manifest:
            manifest.pop("_id", None)
        return manifest
    except Exception as e:
        print(f"❌ Error getting manifest from MongoDB: {e}")
        return None


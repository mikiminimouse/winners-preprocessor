"""
Router/Preprocessor для классификации и предобработки документов перед Docling.
Обрабатывает: PDF (text/scan), DOC, DOCX, архивы (RAR/ZIP), фейковые DOC (HTML/архивы), JPEG.
"""
import os
import json
import hashlib
import hmac
import time
import shutil
import subprocess
import zipfile
import tarfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import uuid

from fastapi import FastAPI, File, UploadFile, Header, HTTPException, BackgroundTasks, Query
from fastapi import Path as PathParam
from fastapi.responses import JSONResponse
import requests
import magic
from pypdf import PdfReader
from pymongo import MongoClient
from pymongo.errors import PyMongoError, ConnectionFailure

app = FastAPI(title="Docling Router/Preprocessor")

# Конфигурация из переменных окружения
INPUT_DIR = Path(os.environ.get("INPUT_DIR", "/app/input"))
TEMP_DIR = Path(os.environ.get("TEMP_DIR", "/app/temp"))
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/app/output"))
EXTRACTED_DIR = Path(os.environ.get("EXTRACTED_DIR", "/app/extracted"))
NORMALIZED_DIR = Path(os.environ.get("NORMALIZED_DIR", "/app/normalized"))
ARCHIVE_DIR = Path(os.environ.get("ARCHIVE_DIR", "/app/archive"))
DOCLING_API = os.environ.get("DOCLING_API", "http://docling:8000/process")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "secret")
MAX_UNPACK_SIZE_MB = int(os.environ.get("MAX_UNPACK_SIZE_MB", "500"))
MAX_FILES_IN_ARCHIVE = int(os.environ.get("MAX_FILES_IN_ARCHIVE", "1000"))

# MongoDB конфигурация
MONGO_SERVER = os.environ.get("MONGO_SERVER")
MONGO_USER = os.environ.get("MONGO_USER")
MONGO_PASSWORD = os.environ.get("MONGO_PASSWORD")
MONGO_SSL_CERT = os.environ.get("MONGO_SSL_CERT")
MONGO_PROTOCOLS_DB = os.environ.get("MONGO_PROTOCOLS_DB", "protocols223")
MONGO_PROTOCOLS_COLLECTION = os.environ.get("MONGO_PROTOCOLS_COLLECTION", "purchaseProtocol")

# MongoDB конфигурация для метаданных
MONGO_METADATA_USER = os.environ.get("MONGO_METADATA_USER", "docling_user")
MONGO_METADATA_PASSWORD = os.environ.get("MONGO_METADATA_PASSWORD", "password")
MONGO_METADATA_DB = os.environ.get("MONGO_METADATA_DB", "docling_metadata")
MONGO_METADATA_COLLECTION = os.environ.get("MONGO_METADATA_COLLECTION", "manifests")
MONGO_METRICS_COLLECTION = os.environ.get("MONGO_METRICS_COLLECTION", "processing_metrics")

PROTOCOLS_COUNT_LIMIT = int(os.environ.get("PROTOCOLS_COUNT_LIMIT", "100"))

# Браузерные заголовки для скачивания документов с zakupki.gov.ru
BROWSER_HEADERS = {
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

# MongoDB клиенты (инициализируются при первом использовании)
_mongo_client: Optional[MongoClient] = None
_mongo_metadata_client: Optional[MongoClient] = None

# Глобальная переменная для метрик текущей сессии обработки
_current_processing_metrics: Optional[Dict[str, Any]] = None

# Создаем необходимые директории
for d in [INPUT_DIR, TEMP_DIR, OUTPUT_DIR, EXTRACTED_DIR, NORMALIZED_DIR, ARCHIVE_DIR]:
    d.mkdir(parents=True, exist_ok=True)


def calculate_sha256(file_path: Path) -> str:
    """Вычисляет SHA256 хеш файла."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def get_mongo_client() -> Optional[MongoClient]:
    """Получает или создает MongoDB клиент для чтения протоколов."""
    global _mongo_client
    
    if _mongo_client is not None:
        try:
            # Проверяем, что клиент еще жив
            _mongo_client.admin.command('ping')
            return _mongo_client
        except Exception:
            # Если клиент мертв, создаем новый
            _mongo_client = None
    
    if not all([MONGO_SERVER, MONGO_USER, MONGO_PASSWORD]):
        return None
    
    try:
        url_mongo = f'mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_SERVER}/?authSource=protocols223'
        
        # Если указан SSL сертификат, используем SSL подключение
        if MONGO_SSL_CERT:
            _mongo_client = MongoClient(
                url_mongo,
                tls=True,
                authMechanism="SCRAM-SHA-1",
                tlsAllowInvalidHostnames=True,
                tlsCAFile=MONGO_SSL_CERT
            )
        else:
            # Локальное подключение без SSL
            _mongo_client = MongoClient(url_mongo)
        
        # Проверяем подключение
        _mongo_client.admin.command('ping')
        return _mongo_client
    except Exception as e:
        print(f"MongoDB connection error: {e}")
        return None


def get_mongo_metadata_client() -> Optional[MongoClient]:
    """Получает или создает MongoDB клиент для записи метаданных."""
    global _mongo_metadata_client
    
    if _mongo_metadata_client is not None:
        try:
            # Проверяем, что клиент еще жив
            _mongo_metadata_client.admin.command('ping')
            return _mongo_metadata_client
        except Exception:
            # Если клиент мертв, создаем новый
            _mongo_metadata_client = None
    
    if not all([MONGO_SERVER, MONGO_METADATA_USER, MONGO_METADATA_PASSWORD]):
        return None
    
    try:
        url_mongo = f'mongodb://{MONGO_METADATA_USER}:{MONGO_METADATA_PASSWORD}@{MONGO_SERVER}/?authSource=admin'
        
        # Если указан SSL сертификат, используем SSL подключение
        if MONGO_SSL_CERT:
            _mongo_metadata_client = MongoClient(
                url_mongo,
                tls=True,
                authMechanism="SCRAM-SHA-1",
                tlsAllowInvalidHostnames=True,
                tlsCAFile=MONGO_SSL_CERT
            )
        else:
            # Локальное подключение без SSL
            _mongo_metadata_client = MongoClient(url_mongo)
        
        # Проверяем подключение
        _mongo_metadata_client.admin.command('ping')
        return _mongo_metadata_client
    except Exception as e:
        print(f"MongoDB metadata connection error: {e}")
        return None


def get_protocols_by_date(date_str: str) -> Dict[str, Any]:
    """
    Получает протоколы по дате из MongoDB и извлекает purchaseNoticeNumber и URL вложений.
    Возвращает словарь: {purchaseNoticeNumber: {url, fileName} или [{url, fileName}, ...]}
    """
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
        
        # Создаем запрос для поиска по дате
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
            
            # Если documents - это один документ (словарь), превращаем в список
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
                # Если только один URL, сохраняем как объект, иначе как список
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
    """Сохраняет manifest в MongoDB вместо JSON файла."""
    client = get_mongo_metadata_client()
    if not client:
        return False
    
    try:
        db = client[MONGO_METADATA_DB]
        collection = db[MONGO_METADATA_COLLECTION]
        
        # Добавляем timestamp для обновления
        manifest["updated_at"] = datetime.utcnow().isoformat()
        
        # Используем upsert для обновления существующего или создания нового
        collection.update_one(
            {"unit_id": unit_id},
            {"$set": manifest},
            upsert=True
        )
        return True
    except Exception as e:
        print(f"Error saving manifest to MongoDB: {e}")
        return False


def get_manifest_from_mongo(unit_id: str) -> Optional[Dict]:
    """Получает manifest из MongoDB."""
    client = get_mongo_metadata_client()
    if not client:
        return None
    
    try:
        db = client[MONGO_METADATA_DB]
        collection = db[MONGO_METADATA_COLLECTION]
        
        manifest = collection.find_one({"unit_id": unit_id})
        if manifest:
            # Удаляем _id из результата
            manifest.pop("_id", None)
        return manifest
    except Exception as e:
        print(f"Error getting manifest from MongoDB: {e}")
        return None


def init_processing_metrics() -> Dict[str, Any]:
    """Инициализирует структуру метрик для новой сессии обработки."""
    global _current_processing_metrics
    session_id = str(uuid.uuid4())
    _current_processing_metrics = {
        "session_id": session_id,
        "started_at": datetime.utcnow().isoformat(),
        "completed_at": None,
        "input_files": [],
        "archives_extracted": [],
        "conversions": [],
        "units_created": [],
        "errors": [],
        "summary": {
            "total_input_files": 0,
            "total_archives": 0,
            "total_extracted": 0,
            "total_units": 0,
            "total_errors": 0,
            "by_extension": {},
            "by_detected_type": {},
            "pdf_statistics": {
                "total_pdf": 0,
                "pdf_with_text_layer": 0,
                "pdf_requires_ocr": 0
            }
        }
    }
    return _current_processing_metrics


def get_current_metrics() -> Optional[Dict[str, Any]]:
    """Получает текущие метрики обработки."""
    global _current_processing_metrics
    return _current_processing_metrics


def save_processing_metrics(metrics: Optional[Dict[str, Any]] = None) -> bool:
    """Сохраняет метрики обработки в MongoDB."""
    global _current_processing_metrics
    
    if metrics is None:
        metrics = _current_processing_metrics
    
    if not metrics:
        return False
    
    client = get_mongo_metadata_client()
    if not client:
        return False
    
    try:
        # Обновляем summary перед сохранением
        _update_metrics_summary(metrics)
        
        # Устанавливаем время завершения
        if not metrics.get("completed_at"):
            metrics["completed_at"] = datetime.utcnow().isoformat()
        
        db = client[MONGO_METADATA_DB]
        collection = db[MONGO_METRICS_COLLECTION]
        
        # Сохраняем метрики с session_id как ключ
        collection.update_one(
            {"session_id": metrics["session_id"]},
            {"$set": metrics},
            upsert=True
        )
        return True
    except Exception as e:
        print(f"Error saving processing metrics to MongoDB: {e}")
        return False


def _update_metrics_summary(metrics: Dict[str, Any]) -> None:
    """Обновляет summary в метриках на основе собранных данных."""
    summary = metrics.get("summary", {})
    
    # Подсчитываем статистику
    summary["total_input_files"] = len(metrics.get("input_files", []))
    summary["total_archives"] = len(metrics.get("archives_extracted", []))
    summary["total_units"] = len(metrics.get("units_created", []))
    summary["total_errors"] = len(metrics.get("errors", []))
    
    # Подсчитываем извлеченные файлы
    total_extracted = 0
    for archive in metrics.get("archives_extracted", []):
        total_extracted += archive.get("extracted_count", 0)
    summary["total_extracted"] = total_extracted
    
    # Статистика по расширениям
    by_extension = {}
    for file_info in metrics.get("input_files", []):
        ext = file_info.get("extension", "unknown")
        by_extension[ext] = by_extension.get(ext, 0) + 1
    summary["by_extension"] = by_extension
    
    # Статистика по типам
    by_type = {}
    for file_info in metrics.get("input_files", []):
        detected_type = file_info.get("detected_type", "unknown")
        by_type[detected_type] = by_type.get(detected_type, 0) + 1
    summary["by_detected_type"] = by_type
    
    # Статистика по PDF (OCR vs text layer)
    pdf_stats = {
        "total_pdf": 0,
        "pdf_with_text_layer": 0,
        "pdf_requires_ocr": 0
    }
    for file_info in metrics.get("input_files", []):
        if file_info.get("detected_type") == "pdf":
            pdf_stats["total_pdf"] += 1
            if file_info.get("needs_ocr", False):
                pdf_stats["pdf_requires_ocr"] += 1
            else:
                pdf_stats["pdf_with_text_layer"] += 1
    
    # Также учитываем PDF из извлеченных архивов
    for archive in metrics.get("archives_extracted", []):
        if archive.get("success", False):
            for file_detail in archive.get("extracted_files_details", []):
                if file_detail.get("detected_type") == "pdf":
                    pdf_stats["total_pdf"] += 1
                    if file_detail.get("needs_ocr", False):
                        pdf_stats["pdf_requires_ocr"] += 1
                    else:
                        pdf_stats["pdf_with_text_layer"] += 1
    
    summary["pdf_statistics"] = pdf_stats


def add_input_file_metric(file_path: Path, file_info: Dict[str, Any]) -> None:
    """Добавляет информацию о входном файле в метрики."""
    global _current_processing_metrics
    if not _current_processing_metrics:
        init_processing_metrics()
    
    metric_entry = {
        "filename": file_path.name,
        "extension": file_path.suffix.lower(),
        "size": file_path.stat().st_size,
        "detected_type": file_info.get("detected_type", "unknown"),
        "mime_type": file_info.get("mime_type", ""),
        "is_archive": file_info.get("is_archive", False),
        "is_fake_doc": file_info.get("is_fake_doc", False),
        "needs_ocr": file_info.get("needs_ocr", False),
        "requires_conversion": file_info.get("requires_conversion", False)
    }
    _current_processing_metrics["input_files"].append(metric_entry)


def add_archive_extraction_metric(archive_id: str, original_file: str, extracted_files: List[Dict], success: bool) -> None:
    """Добавляет информацию об извлечении архива в метрики."""
    global _current_processing_metrics
    if not _current_processing_metrics:
        init_processing_metrics()
    
    # Собираем детальную информацию о файлах в архиве
    extracted_files_details = []
    files_by_extension = {}
    files_by_type = {}
    pipeline_info = {}
    
    if success and extracted_files:
        for ext_file in extracted_files:
            ext_path = Path(ext_file.get("path", ""))
            if ext_path.exists():
                # Определяем тип каждого файла
                file_info = detect_file_type(ext_path)
                file_info["original_name"] = ext_file.get("original_name", "")
                file_info["size"] = ext_file.get("size", 0)
                extracted_files_details.append(file_info)
                
                # Статистика по расширениям
                ext = ext_path.suffix.lower() or "no_extension"
                files_by_extension[ext] = files_by_extension.get(ext, 0) + 1
                
                # Статистика по типам
                detected_type = file_info.get("detected_type", "unknown")
                files_by_type[detected_type] = files_by_type.get(detected_type, 0) + 1
                
                # Информация о pipeline обработки
                if detected_type not in pipeline_info:
                    pipeline_info[detected_type] = {
                        "count": 0,
                        "needs_ocr": 0,
                        "requires_conversion": 0,
                        "route": None
                    }
                pipeline_info[detected_type]["count"] += 1
                if file_info.get("needs_ocr", False):
                    pipeline_info[detected_type]["needs_ocr"] += 1
                if file_info.get("requires_conversion", False):
                    pipeline_info[detected_type]["requires_conversion"] += 1
                
                # Определяем route для каждого типа
                if detected_type == "pdf":
                    pipeline_info[detected_type]["route"] = "pdf_scan" if file_info.get("needs_ocr") else "pdf_text"
                elif detected_type == "docx":
                    pipeline_info[detected_type]["route"] = "docx"
                elif detected_type == "doc":
                    pipeline_info[detected_type]["route"] = "docx"  # После конвертации
                elif detected_type == "image":
                    pipeline_info[detected_type]["route"] = "image_ocr"
                elif detected_type == "html":
                    pipeline_info[detected_type]["route"] = "html_text"
    
    metric_entry = {
        "archive_id": archive_id,
        "original_file": original_file,
        "extracted_count": len(extracted_files) if success else 0,
        "extracted_files": [f.get("original_name", "") for f in extracted_files] if success else [],
        "extracted_files_details": extracted_files_details,
        "files_by_extension": files_by_extension,
        "files_by_type": files_by_type,
        "pipeline_info": pipeline_info,
        "success": success
    }
    _current_processing_metrics["archives_extracted"].append(metric_entry)


def add_conversion_metric(original: str, converted_to: str, success: bool) -> None:
    """Добавляет информацию о конвертации файла в метрики."""
    global _current_processing_metrics
    if not _current_processing_metrics:
        init_processing_metrics()
    
    metric_entry = {
        "original": original,
        "converted_to": converted_to,
        "success": success
    }
    _current_processing_metrics["conversions"].append(metric_entry)


def add_unit_created_metric(unit_id: str, files_count: int, file_types: List[str]) -> None:
    """Добавляет информацию о созданном unit'е в метрики."""
    global _current_processing_metrics
    if not _current_processing_metrics:
        init_processing_metrics()
    
    metric_entry = {
        "unit_id": unit_id,
        "files_count": files_count,
        "file_types": file_types
    }
    _current_processing_metrics["units_created"].append(metric_entry)


def add_error_metric(file: str, stage: str, error: str, details: str = "") -> None:
    """Добавляет информацию об ошибке в метрики."""
    global _current_processing_metrics
    if not _current_processing_metrics:
        init_processing_metrics()
    
    metric_entry = {
        "file": file,
        "stage": stage,
        "error": error,
        "details": details,
        "timestamp": datetime.utcnow().isoformat()
    }
    _current_processing_metrics["errors"].append(metric_entry)


def download_document(url: str, dest_path: Path, timeout: int = 300) -> bool:
    """
    Скачивает документ по URL в указанный путь, используя браузерные заголовки.
    """
    try:
        response = requests.get(
            url,
            timeout=timeout,
            stream=True,
            headers=BROWSER_HEADERS,
            allow_redirects=True,
        )
        response.raise_for_status()

        dest_path.parent.mkdir(parents=True, exist_ok=True)

        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        return True
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return False


def detect_file_type(file_path: Path) -> Dict[str, Any]:
    """
    Определяет тип файла используя magic bytes и mimetype.
    Возвращает: detected_type, mime_type, needs_ocr, requires_conversion, is_archive
    """
    result = {
        "detected_type": "unknown",
        "mime_type": "application/octet-stream",
        "needs_ocr": False,
        "requires_conversion": False,
        "is_archive": False,
        "is_fake_doc": False,
        "extension": file_path.suffix.lower(),
        "magic_bytes": None,
        "detection_details": {}
    }
    
    try:
        # Используем python-magic для определения MIME типа
        mime = magic.from_file(str(file_path), mime=True)
        result["mime_type"] = mime
        result["detection_details"]["mime_detected"] = mime
        
        # Читаем первые байты для дополнительной проверки
        with open(file_path, "rb") as f:
            header = f.read(16)
        
        # Сохраняем magic bytes для логирования
        result["magic_bytes"] = header.hex()[:32]  # Первые 16 байт в hex
        result["detection_details"]["header_hex"] = header.hex()[:32]
        
        # Проверка на архивы (даже если расширение .doc)
        if header.startswith(b"Rar!\x1a\x07") or header.startswith(b"Rar!\x1a\x07\x00"):
            result["is_archive"] = True
            result["detected_type"] = "rar_archive"
            result["detection_details"]["archive_type"] = "RAR"
            if result["extension"] == ".doc":
                result["is_fake_doc"] = True
                result["detection_details"]["fake_doc_reason"] = "RAR archive with .doc extension"
        elif header.startswith(b"PK\x03\x04") or header.startswith(b"PK\x05\x06"):
            # ZIP или DOCX (DOCX это ZIP)
            result["detection_details"]["zip_signature"] = True
            if mime == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                result["detected_type"] = "docx"
                result["needs_ocr"] = False
                result["detection_details"]["docx_detected"] = True
            elif mime == "application/zip":
                result["is_archive"] = True
                result["detected_type"] = "zip_archive"
                result["detection_details"]["archive_type"] = "ZIP"
                if result["extension"] == ".doc":
                    result["is_fake_doc"] = True
                    result["detection_details"]["fake_doc_reason"] = "ZIP archive with .doc extension"
        elif header.startswith(b"%PDF"):
            result["detected_type"] = "pdf"
            result["detection_details"]["pdf_signature"] = True
            # Проверяем наличие текстового слоя
            try:
                reader = PdfReader(str(file_path))
                has_text = False
                text_length = 0
                for page in reader.pages[:3]:  # Проверяем первые 3 страницы
                    text = page.extract_text()
                    if text:
                        text_length += len(text.strip())
                        if len(text.strip()) > 10:
                            has_text = True
                            break
                result["needs_ocr"] = not has_text
                result["detection_details"]["pdf_text_check"] = {
                    "has_text": has_text,
                    "text_length": text_length
                }
            except Exception as e:
                result["needs_ocr"] = True  # Если ошибка чтения - считаем сканом
                result["detection_details"]["pdf_text_check"] = {
                    "error": str(e),
                    "assumed_scan": True
                }
        elif header.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
            # OLE2 формат - реальный DOC
            result["detected_type"] = "doc"
            result["requires_conversion"] = True
            result["needs_ocr"] = False
            result["detection_details"]["ole2_signature"] = True
            result["detection_details"]["real_doc"] = True
        elif mime.startswith("image/"):
            result["detected_type"] = "image"
            result["needs_ocr"] = True
            result["detection_details"]["image_type"] = mime
        elif mime == "text/html" or header.startswith(b"<!DOCTYPE") or header.startswith(b"<html"):
            result["detected_type"] = "html"
            if result["extension"] == ".doc":
                result["is_fake_doc"] = True
                result["detection_details"]["fake_doc_reason"] = "HTML file with .doc extension"
            result["needs_ocr"] = False
            result["detection_details"]["html_detected"] = True
        elif mime == "application/msword":
            result["detected_type"] = "doc"
            result["requires_conversion"] = True
            result["needs_ocr"] = False
            result["detection_details"]["msword_mime"] = True
            # Проверяем, не является ли это архивом с неправильным MIME
            if not header.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
                result["detection_details"]["suspicious"] = "MIME says msword but no OLE2 signature"
        
        # Логируем результат определения типа
        print(f"[DETECT_TYPE] {file_path.name}: extension={result['extension']}, "
              f"mime={result['mime_type']}, detected={result['detected_type']}, "
              f"is_archive={result['is_archive']}, is_fake_doc={result['is_fake_doc']}, "
              f"magic_bytes={result.get('magic_bytes', 'N/A')[:16]}...")
        
    except Exception as e:
        print(f"Error detecting file type for {file_path}: {e}")
        import traceback
        error_details = traceback.format_exc()
        result["detected_type"] = "unknown"
        result["detection_details"]["error"] = str(e)
        result["detection_details"]["error_traceback"] = error_details
        add_error_metric(str(file_path), "detect_type", str(e), error_details)
    
    return result


def sanitize_filename(filename: str) -> str:
    """Очищает имя файла от опасных символов."""
    # Удаляем ../ и абсолютные пути
    filename = filename.replace("../", "").replace("..\\", "")
    filename = os.path.basename(filename)
    # Удаляем опасные символы
    dangerous = ['<', '>', ':', '"', '|', '?', '*', '\x00']
    for char in dangerous:
        filename = filename.replace(char, '_')
    return filename


def safe_extract_archive(archive_path: Path, extract_to: Path, archive_id: str) -> Tuple[List[Dict], bool]:
    """
    Безопасно распаковывает архив с проверками на zip bomb и ограничениями.
    Возвращает список файлов и успешность операции.
    """
    extracted_files = []
    max_size = MAX_UNPACK_SIZE_MB * 1024 * 1024
    total_size = 0
    file_count = 0
    archive_size = archive_path.stat().st_size
    extraction_details = {
        "archive_path": str(archive_path),
        "archive_size": archive_size,
        "archive_type": None,
        "extraction_started": datetime.utcnow().isoformat(),
        "extraction_errors": []
    }
    
    try:
        # Определяем тип архива
        file_type = detect_file_type(archive_path)
        extraction_details["archive_type"] = file_type.get("detected_type", "unknown")
        extraction_details["detected_mime"] = file_type.get("mime_type", "")
        extraction_details["is_fake_doc"] = file_type.get("is_fake_doc", False)
        
        print(f"[EXTRACT_ARCHIVE] Starting extraction: {archive_path.name}, "
              f"type={extraction_details['archive_type']}, size={archive_size}, "
              f"is_fake_doc={extraction_details['is_fake_doc']}")
        
        # Проверка на HTML файлы - не должны распаковываться как архивы
        if file_type.get("detected_type") == "html":
            error_msg = f"File {archive_path.name} is an HTML file, not an archive. Cannot extract."
            extraction_details["extraction_errors"].append({
                "error": error_msg,
                "reason": "html_not_archive",
                "detected_type": file_type.get("detected_type"),
                "mime_type": file_type.get("mime_type")
            })
            print(f"[EXTRACT_ARCHIVE] ERROR: {error_msg}")
            add_error_metric(str(archive_path), "extraction", error_msg, json.dumps(extraction_details))
            return extracted_files, False
        
        # Проверка на реальный DOC файл (OLE2), который не является архивом
        if archive_path.suffix.lower() == ".doc" and not file_type.get("is_archive") and not file_type.get("is_fake_doc"):
            # Это реальный DOC файл, не архив
            error_msg = f"File {archive_path.name} is a real DOC file (OLE2 format), not an archive. Cannot extract."
            extraction_details["extraction_errors"].append({
                "error": error_msg,
                "reason": "real_doc_not_archive",
                "detected_type": file_type.get("detected_type"),
                "has_ole2_signature": file_type.get("detection_details", {}).get("ole2_signature", False)
            })
            print(f"[EXTRACT_ARCHIVE] ERROR: {error_msg}")
            add_error_metric(str(archive_path), "extraction", error_msg, json.dumps(extraction_details))
            return extracted_files, False
        
        if file_type["detected_type"] == "zip_archive" or archive_path.suffix.lower() == ".zip":
            extraction_details["extraction_method"] = "zipfile"
            try:
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    total_members = len(zip_ref.namelist())
                    extraction_details["total_members"] = total_members
                    print(f"[EXTRACT_ARCHIVE] ZIP archive contains {total_members} members")
                    
                    for member in zip_ref.namelist():
                        if file_count >= MAX_FILES_IN_ARCHIVE:
                            error_msg = f"Too many files in archive (>{MAX_FILES_IN_ARCHIVE})"
                            extraction_details["extraction_errors"].append({
                                "error": error_msg,
                                "file_count": file_count,
                                "limit": MAX_FILES_IN_ARCHIVE
                            })
                            raise ValueError(error_msg)
                        
                        # Безопасное имя файла
                        safe_name = sanitize_filename(member)
                        if not safe_name or safe_name.endswith('/'):
                            continue
                        
                        # Проверка размера
                        info = zip_ref.getinfo(member)
                        if info.file_size > max_size:
                            extraction_details["extraction_errors"].append({
                                "warning": f"File {member} skipped: too large ({info.file_size} > {max_size})"
                            })
                            continue
                        
                        total_size += info.file_size
                        if total_size > max_size:
                            error_msg = f"Archive too large (>{MAX_UNPACK_SIZE_MB}MB)"
                            extraction_details["extraction_errors"].append({
                                "error": error_msg,
                                "total_size": total_size,
                                "limit": max_size
                            })
                            raise ValueError(error_msg)
                        
                        # Извлекаем файл
                        dest_path = extract_to / safe_name
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        with zip_ref.open(member) as source, open(dest_path, 'wb') as target:
                            shutil.copyfileobj(source, target)
                        
                        file_count += 1
                        extracted_files.append({
                            "original_name": member,
                            "safe_name": safe_name,
                            "path": str(dest_path),
                            "size": info.file_size
                        })
                    
                    extraction_details["extracted_count"] = file_count
                    extraction_details["total_extracted_size"] = total_size
                    print(f"[EXTRACT_ARCHIVE] Successfully extracted {file_count} files from ZIP archive")
            except zipfile.BadZipFile as e:
                error_msg = f"Invalid ZIP file: {str(e)}"
                extraction_details["extraction_errors"].append({
                    "error": error_msg,
                    "error_type": "BadZipFile"
                })
                print(f"[EXTRACT_ARCHIVE] ERROR: {error_msg}")
                add_error_metric(str(archive_path), "extraction", error_msg, json.dumps(extraction_details))
                return extracted_files, False
        
        elif file_type["detected_type"] == "rar_archive" or archive_path.suffix.lower() == ".rar":
            # Для RAR архивов сначала пробуем unrar, затем 7z как fallback
            extraction_details["extraction_method"] = "unrar"
            try:
                # Пробуем unrar сначала
                cmd = ["unrar", "x", "-y", str(archive_path), str(extract_to)]
                print(f"[EXTRACT_ARCHIVE] Running unrar command: {' '.join(cmd)}")
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                
                extraction_details["unrar_returncode"] = result.returncode
                extraction_details["unrar_stdout"] = result.stdout[:1000]
                extraction_details["unrar_stderr"] = result.stderr[:1000]
                
                if result.returncode != 0:
                    # Если unrar не сработал, пробуем 7z как fallback
                    print(f"[EXTRACT_ARCHIVE] unrar failed (code {result.returncode}), trying 7z as fallback...")
                    extraction_details["extraction_method"] = "7z_fallback"
                    cmd = ["7z", "x", str(archive_path), f"-o{extract_to}", "-y"]
                    print(f"[EXTRACT_ARCHIVE] Running 7z command: {' '.join(cmd)}")
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                    
                    extraction_details["7z_returncode"] = result.returncode
                    extraction_details["7z_stdout"] = result.stdout[:1000]
                    extraction_details["7z_stderr"] = result.stderr[:1000]
                    
                    if result.returncode != 0:
                        error_msg = f"Both unrar and 7z failed. unrar: {extraction_details.get('unrar_stderr', '')[:200]}, 7z: {result.stderr[:200]}"
                        extraction_details["extraction_errors"].append({
                            "error": error_msg,
                            "unrar_returncode": extraction_details.get("unrar_returncode"),
                            "7z_returncode": result.returncode,
                            "stderr": result.stderr[:500]
                        })
                        print(f"[EXTRACT_ARCHIVE] ERROR: {error_msg}")
                        add_error_metric(str(archive_path), "extraction", error_msg, json.dumps(extraction_details))
                        raise subprocess.CalledProcessError(result.returncode, cmd, result.stderr)
                
                # Собираем список извлеченных файлов (для unrar и 7z fallback)
                for file_path in extract_to.rglob("*"):
                    if file_path.is_file():
                        file_count += 1
                        if file_count > MAX_FILES_IN_ARCHIVE:
                            error_msg = f"Too many files in archive (>{MAX_FILES_IN_ARCHIVE})"
                            extraction_details["extraction_errors"].append({
                                "error": error_msg,
                                "file_count": file_count
                            })
                            raise ValueError(error_msg)
                        
                        stat = file_path.stat()
                        total_size += stat.st_size
                        if total_size > max_size:
                            error_msg = f"Archive too large (>{MAX_UNPACK_SIZE_MB}MB)"
                            extraction_details["extraction_errors"].append({
                                "error": error_msg,
                                "total_size": total_size
                            })
                            raise ValueError(error_msg)
                        
                        extracted_files.append({
                            "original_name": file_path.name,
                            "safe_name": file_path.name,
                            "path": str(file_path),
                            "size": stat.st_size
                        })
                
                extraction_details["extracted_count"] = file_count
                extraction_details["total_extracted_size"] = total_size
                print(f"[EXTRACT_ARCHIVE] Successfully extracted {file_count} files from RAR archive")
            except FileNotFoundError as e:
                error_msg = f"Archive extraction utility not found: {str(e)}. Install unrar and/or p7zip-full."
                extraction_details["extraction_errors"].append({
                    "error": error_msg,
                    "error_type": "FileNotFoundError",
                    "exception": str(e)
                })
                print(f"[EXTRACT_ARCHIVE] ERROR: {error_msg}")
                add_error_metric(str(archive_path), "extraction", error_msg, json.dumps(extraction_details))
                raise ValueError(error_msg)
        elif archive_path.suffix.lower() == ".7z":
            # Для 7z архивов используем 7z
            extraction_details["extraction_method"] = "7z"
            try:
                cmd = ["7z", "x", str(archive_path), f"-o{extract_to}", "-y"]
                print(f"[EXTRACT_ARCHIVE] Running 7z command: {' '.join(cmd)}")
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                
                extraction_details["7z_returncode"] = result.returncode
                extraction_details["7z_stdout"] = result.stdout[:1000]
                extraction_details["7z_stderr"] = result.stderr[:1000]
                
                if result.returncode != 0:
                    error_msg = f"7z extraction failed with return code {result.returncode}: {result.stderr[:200]}"
                    extraction_details["extraction_errors"].append({
                        "error": error_msg,
                        "returncode": result.returncode,
                        "stderr": result.stderr[:500]
                    })
                    print(f"[EXTRACT_ARCHIVE] ERROR: {error_msg}")
                    add_error_metric(str(archive_path), "extraction", error_msg, json.dumps(extraction_details))
                    raise subprocess.CalledProcessError(result.returncode, cmd, result.stderr)
                
                # Собираем список извлеченных файлов
                for file_path in extract_to.rglob("*"):
                    if file_path.is_file():
                        file_count += 1
                        if file_count > MAX_FILES_IN_ARCHIVE:
                            error_msg = f"Too many files in archive (>{MAX_FILES_IN_ARCHIVE})"
                            extraction_details["extraction_errors"].append({
                                "error": error_msg,
                                "file_count": file_count
                            })
                            raise ValueError(error_msg)
                        
                        stat = file_path.stat()
                        total_size += stat.st_size
                        if total_size > max_size:
                            error_msg = f"Archive too large (>{MAX_UNPACK_SIZE_MB}MB)"
                            extraction_details["extraction_errors"].append({
                                "error": error_msg,
                                "total_size": total_size
                            })
                            raise ValueError(error_msg)
                        
                        extracted_files.append({
                            "original_name": file_path.name,
                            "safe_name": file_path.name,
                            "path": str(file_path),
                            "size": stat.st_size
                        })
                
                extraction_details["extracted_count"] = file_count
                extraction_details["total_extracted_size"] = total_size
                archive_type_name = "RAR" if file_type["detected_type"] == "rar_archive" else "7z"
                print(f"[EXTRACT_ARCHIVE] Successfully extracted {file_count} files from {archive_type_name} archive")
            except FileNotFoundError as e:
                error_msg = f"Archive extraction utility not found: {str(e)}. Install unrar and/or p7zip-full."
                extraction_details["extraction_errors"].append({
                    "error": error_msg,
                    "error_type": "FileNotFoundError",
                    "exception": str(e)
                })
                print(f"[EXTRACT_ARCHIVE] ERROR: {error_msg}")
                add_error_metric(str(archive_path), "extraction", error_msg, json.dumps(extraction_details))
                raise ValueError(error_msg)
        else:
            # Неизвестный тип архива или файл не является архивом
            error_msg = f"Unknown archive type or file is not an archive. Detected type: {file_type.get('detected_type')}"
            extraction_details["extraction_errors"].append({
                "error": error_msg,
                "detected_type": file_type.get("detected_type"),
                "is_archive": file_type.get("is_archive", False)
            })
            print(f"[EXTRACT_ARCHIVE] ERROR: {error_msg}")
            add_error_metric(str(archive_path), "extraction", error_msg, json.dumps(extraction_details))
            return extracted_files, False
        
        extraction_details["extraction_completed"] = datetime.utcnow().isoformat()
        extraction_details["success"] = True
        return extracted_files, True
    
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        error_msg = f"Error extracting archive {archive_path.name}: {str(e)}"
        extraction_details["extraction_errors"].append({
            "error": error_msg,
            "exception_type": type(e).__name__,
            "traceback": error_details
        })
        extraction_details["extraction_completed"] = datetime.utcnow().isoformat()
        extraction_details["success"] = False
        print(f"[EXTRACT_ARCHIVE] ERROR: {error_msg}")
        print(f"[EXTRACT_ARCHIVE] Traceback: {error_details}")
        add_error_metric(str(archive_path), "extraction", error_msg, json.dumps(extraction_details))
        return extracted_files, False


def create_manifest(unit_id: str, files: List[Dict], archive_info: Optional[Dict] = None) -> Dict:
    """Создает manifest.json для unit'а документов."""
    manifest = {
        "unit_id": unit_id,
        "created_at": datetime.utcnow().isoformat(),
        "processing": {
            "status": "ready",
            "route": None
        },
        "files": [],
        "archive": archive_info
    }
    
    # Определяем общий route для unit'а
    file_types = [f.get("detected_type") for f in files]
    needs_ocr_any = any(f.get("needs_ocr", False) for f in files)
    
    if len(files) == 1:
        f = files[0]
        if f["detected_type"] == "pdf":
            manifest["processing"]["route"] = "pdf_scan" if f.get("needs_ocr") else "pdf_text"
        elif f["detected_type"] == "docx":
            manifest["processing"]["route"] = "docx"
        elif f["detected_type"] == "image":
            manifest["processing"]["route"] = "image_ocr"
        elif f["detected_type"] == "html":
            manifest["processing"]["route"] = "html_text"
    else:
        # Множественные файлы - mixed route
        manifest["processing"]["route"] = "mixed"
    
    # Добавляем информацию о файлах
    for file_info in files:
        manifest["files"].append({
            "file_id": file_info.get("file_id", str(uuid.uuid4())),
            "original_name": file_info.get("original_name", ""),
            "path": file_info.get("path", ""),
            "detected_type": file_info.get("detected_type", "unknown"),
            "mime_type": file_info.get("mime_type", ""),
            "needs_ocr": file_info.get("needs_ocr", False),
            "requires_conversion": file_info.get("requires_conversion", False),
            "sha256": file_info.get("sha256", ""),
            "size": file_info.get("size", 0)
        })
    
    return manifest


def process_file(file_path: Path, background_tasks: BackgroundTasks) -> Dict:
    """Основная функция обработки файла: классификация, распаковка, создание unit'а."""
    print(f"[PROCESS_FILE] Starting processing: {file_path.name}, size={file_path.stat().st_size}")
    
    try:
        # Шаг 1: Определение типа файла
        print(f"[PROCESS_FILE] Step 1: Detecting file type for {file_path.name}")
        file_info = detect_file_type(file_path)
        file_sha256 = calculate_sha256(file_path)
        file_info["sha256"] = file_sha256
        file_info["original_name"] = file_path.name
        file_info["size"] = file_path.stat().st_size
        
        # Добавляем метрику входного файла
        add_input_file_metric(file_path, file_info)
        
        print(f"[PROCESS_FILE] Step 1 completed: detected_type={file_info['detected_type']}, "
              f"is_archive={file_info.get('is_archive')}, is_fake_doc={file_info.get('is_fake_doc')}")
        
        # Проверка: HTML файлы не должны обрабатываться как архивы
        if file_info.get("detected_type") == "html":
            # HTML файлы обрабатываются как обычные файлы, не архивы
            print(f"[PROCESS_FILE] HTML file detected, processing as regular file (not archive)")
            file_info["is_archive"] = False
            file_info["is_fake_doc"] = False
        
        # Шаг 2: Обработка архивов
        if file_info["is_archive"] or file_info["is_fake_doc"]:
            print(f"[PROCESS_FILE] Step 2: Processing archive/fake_doc: {file_path.name}")
            archive_id = f"ARCHIVE_{file_sha256[:16]}"
            extract_dir = EXTRACTED_DIR / archive_id
            extract_dir.mkdir(parents=True, exist_ok=True)
            
            # Сохраняем оригинальный архив
            archive_storage = ARCHIVE_DIR / archive_id
            archive_storage.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, archive_storage / file_path.name)
            print(f"[PROCESS_FILE] Archive saved to: {archive_storage / file_path.name}")
            
            # Распаковываем
            print(f"[PROCESS_FILE] Extracting archive {archive_id}...")
            extracted_files, success = safe_extract_archive(file_path, extract_dir, archive_id)
            
            # Добавляем метрику извлечения архива
            add_archive_extraction_metric(archive_id, file_path.name, extracted_files, success)
            
            if not success:
                error_msg = "Failed to extract archive"
                print(f"[PROCESS_FILE] ERROR: {error_msg} for {file_path.name}")
                add_error_metric(str(file_path), "extraction", error_msg, 
                               f"Archive extraction failed. Archive ID: {archive_id}")
                return {"status": "error", "message": error_msg, "file": str(file_path)}
            
            print(f"[PROCESS_FILE] Archive extracted successfully: {len(extracted_files)} files extracted")
            
            # Обрабатываем каждый извлеченный файл
            print(f"[PROCESS_FILE] Step 3: Processing {len(extracted_files)} extracted files...")
            unit_files = []
            for idx, ext_file in enumerate(extracted_files, 1):
                ext_path = Path(ext_file["path"])
                if not ext_path.exists():
                    print(f"[PROCESS_FILE] WARNING: Extracted file not found: {ext_path}")
                    continue
                
                print(f"[PROCESS_FILE] Processing extracted file {idx}/{len(extracted_files)}: {ext_file['original_name']}")
                ext_info = detect_file_type(ext_path)
                ext_info["sha256"] = calculate_sha256(ext_path)
                ext_info["original_name"] = ext_file["original_name"]
                ext_info["size"] = ext_path.stat().st_size
                ext_info["file_id"] = str(uuid.uuid4())
                ext_info["path"] = str(ext_path)
                unit_files.append(ext_info)
            
            print(f"[PROCESS_FILE] Step 3 completed: {len(unit_files)} files ready for unit creation")
            
            # Создаем unit для архива
            print(f"[PROCESS_FILE] Step 4: Creating unit for archive...")
            unit_id = f"UNIT_{archive_id}"
            normalized_unit_dir = NORMALIZED_DIR / unit_id
            normalized_unit_dir.mkdir(parents=True, exist_ok=True)
            
            # Копируем файлы в normalized
            files_dir = normalized_unit_dir / "files"
            files_dir.mkdir(exist_ok=True)
            
            for unit_file in unit_files:
                src = Path(unit_file["path"])
                dst = files_dir / sanitize_filename(src.name)
                shutil.copy2(src, dst)
                unit_file["path"] = str(dst)
            
            print(f"[PROCESS_FILE] Files copied to normalized directory: {normalized_unit_dir}")
            
            # Создаем manifest
            archive_info = {
                "is_archive": True,
                "archive_id": archive_id,
                "original_path": str(file_path),
                "extracted_count": len(unit_files)
            }
            manifest = create_manifest(unit_id, unit_files, archive_info)
            
            # Сохраняем в MongoDB (fallback на JSON если MongoDB недоступен)
            saved_to_mongo = save_manifest_to_mongo(unit_id, manifest)
            if not saved_to_mongo:
                # Fallback: сохраняем в JSON файл
                manifest_path = normalized_unit_dir / "manifest.json"
                with open(manifest_path, "w", encoding="utf-8") as f:
                    json.dump(manifest, f, indent=2, ensure_ascii=False)
                print(f"[PROCESS_FILE] Manifest saved to JSON: {manifest_path}")
            else:
                print(f"[PROCESS_FILE] Manifest saved to MongoDB")
            
            # Добавляем метрику созданного unit'а
            file_types = [f.get("detected_type", "unknown") for f in unit_files]
            add_unit_created_metric(unit_id, len(unit_files), file_types)
            
            # Триггерим обработку в Docling
            background_tasks.add_task(trigger_docling, unit_id, None)
            
            print(f"[PROCESS_FILE] Unit created successfully: {unit_id}, files={len(unit_files)}")
            
            return {
                "status": "processed",
                "unit_id": unit_id,
                "archive_id": archive_id,
                "files_count": len(unit_files),
                "manifest_storage": "mongodb" if saved_to_mongo else "json"
            }
        
        # Шаг 3: Обработка одиночных файлов
        else:
            print(f"[PROCESS_FILE] Step 2: Processing single file (not archive)...")
            unit_id = f"UNIT_{file_sha256[:16]}"
            normalized_unit_dir = NORMALIZED_DIR / unit_id
            normalized_unit_dir.mkdir(parents=True, exist_ok=True)
            
            files_dir = normalized_unit_dir / "files"
            files_dir.mkdir(exist_ok=True)
            
            # Копируем файл
            dest_file = files_dir / sanitize_filename(file_path.name)
            shutil.copy2(file_path, dest_file)
            file_info["path"] = str(dest_file)
            file_info["file_id"] = str(uuid.uuid4())
            print(f"[PROCESS_FILE] File copied to normalized: {dest_file}")
            
            # Создаем manifest
            manifest = create_manifest(unit_id, [file_info])
            
            # Сохраняем в MongoDB (fallback на JSON если MongoDB недоступен)
            saved_to_mongo = save_manifest_to_mongo(unit_id, manifest)
            if not saved_to_mongo:
                # Fallback: сохраняем в JSON файл
                manifest_path = normalized_unit_dir / "manifest.json"
                with open(manifest_path, "w", encoding="utf-8") as f:
                    json.dump(manifest, f, indent=2, ensure_ascii=False)
                print(f"[PROCESS_FILE] Manifest saved to JSON: {manifest_path}")
            else:
                print(f"[PROCESS_FILE] Manifest saved to MongoDB")
            
            # Если нужна конвертация DOC -> DOCX, ждем её (LibreOffice делает это автоматически)
            if file_info.get("requires_conversion"):
                print(f"[PROCESS_FILE] Step 3: Waiting for DOC->DOCX conversion...")
                docx_path = dest_file.with_suffix(".docx")
                max_wait = 60  # секунд
                waited = 0
                while not docx_path.exists() and waited < max_wait:
                    time.sleep(2)
                    waited += 2
                
                if docx_path.exists():
                    print(f"[PROCESS_FILE] DOCX file found: {docx_path}")
                    # Обновляем manifest с DOCX файлом
                    docx_info = detect_file_type(docx_path)
                    docx_info["sha256"] = calculate_sha256(docx_path)
                    docx_info["original_name"] = docx_path.name
                    docx_info["size"] = docx_path.stat().st_size
                    docx_info["file_id"] = str(uuid.uuid4())
                    docx_info["path"] = str(docx_path)
                    docx_info["converted_from"] = str(dest_file)
                    
                    # Добавляем метрику конвертации
                    add_conversion_metric(file_path.name, docx_path.name, True)
                    
                    manifest = create_manifest(unit_id, [docx_info])
                    save_manifest_to_mongo(unit_id, manifest)
                    print(f"[PROCESS_FILE] Manifest updated with DOCX file")
                else:
                    print(f"[PROCESS_FILE] WARNING: DOCX conversion timeout, using original DOC")
                    add_conversion_metric(file_path.name, "", False)
            
            # Добавляем метрику созданного unit'а
            add_unit_created_metric(unit_id, 1, [file_info.get("detected_type", "unknown")])
            
            # Триггерим обработку в Docling
            background_tasks.add_task(trigger_docling, unit_id, None)
            
            print(f"[PROCESS_FILE] Unit created successfully: {unit_id}")
            
            return {
                "status": "processed",
                "unit_id": unit_id,
                "file_type": file_info["detected_type"],
                "needs_ocr": file_info.get("needs_ocr", False),
                "manifest_storage": "mongodb" if saved_to_mongo else "json"
            }
    
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        error_msg = f"Error processing file {file_path.name}: {str(e)}"
        print(f"[PROCESS_FILE] ERROR: {error_msg}")
        print(f"[PROCESS_FILE] Traceback: {error_details}")
        add_error_metric(str(file_path), "process_file", error_msg, error_details)
        return {"status": "error", "message": str(e), "file": str(file_path)}


def trigger_docling(unit_id: str, manifest_path: Optional[Path] = None):
    """Отправляет unit в Docling для обработки."""
    try:
        time.sleep(2)  # Небольшая задержка для завершения записи manifest
        
        # Пытаемся получить manifest из MongoDB, fallback на JSON файл
        manifest = get_manifest_from_mongo(unit_id)
        
        if not manifest and manifest_path and manifest_path.exists():
            # Fallback: читаем из JSON файла
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
        elif not manifest:
            # Пытаемся найти JSON файл
            manifest_path = NORMALIZED_DIR / unit_id / "manifest.json"
            if manifest_path.exists():
                with open(manifest_path, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
        
        if not manifest:
            print(f"Manifest not found for unit {unit_id}")
            return
        
        payload = {
            "unit_id": unit_id,
            "manifest": f"mongodb://{unit_id}" if manifest_path is None else str(manifest_path),
            "files": manifest.get("files", []),
            "route": manifest.get("processing", {}).get("route")
        }
        
        response = requests.post(
            DOCLING_API,
            json=payload,
            timeout=300
        )
        
        if response.status_code == 200:
            print(f"Successfully triggered Docling for unit {unit_id}")
        else:
            print(f"Error triggering Docling: {response.status_code} - {response.text}")
    
    except Exception as e:
        print(f"Error triggering Docling for unit {unit_id}: {e}")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "router"}


@app.post("/upload")
async def upload(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    """Загрузка файла через API."""
    try:
        # Сохраняем файл во временную директорию
        temp_file = TEMP_DIR / sanitize_filename(file.filename)
        with open(temp_file, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        # Перемещаем в input для обработки
        input_file = INPUT_DIR / temp_file.name
        shutil.move(temp_file, input_file)
        
        # Обрабатываем файл
        result = process_file(input_file, background_tasks)
        return JSONResponse(content=result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/webhook")
async def webhook(
    payload: dict,
    x_signature: str = Header(None),
    background_tasks: BackgroundTasks = None
):
    """Webhook endpoint для внешних триггеров."""
    # Проверка подписи (если настроено)
    if WEBHOOK_SECRET and WEBHOOK_SECRET != "secret":
        if not x_signature:
            raise HTTPException(status_code=403, detail="Missing signature")
        
        expected = hmac.new(
            WEBHOOK_SECRET.encode(),
            json.dumps(payload, sort_keys=True).encode(),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(x_signature, expected):
            raise HTTPException(status_code=403, detail="Invalid signature")
    
    # Обработка payload
    file_path = payload.get("file_path")
    if file_path:
        path = Path(file_path)
        if path.exists():
            result = process_file(path, background_tasks)
            return JSONResponse(content=result)
        else:
            raise HTTPException(status_code=400, detail=f"File not found: {file_path}")
    
    raise HTTPException(status_code=400, detail="file_path missing in payload")


@app.post("/process_now")
async def process_now(background_tasks: BackgroundTasks = None):
    """Обрабатывает все файлы из INPUT_DIR."""
    # Инициализируем метрики для новой сессии
    metrics = init_processing_metrics()
    print(f"[PROCESS_NOW] Starting processing session: {metrics['session_id']}")
    
    processed = []
    input_files = [f for f in INPUT_DIR.iterdir() if f.is_file() and not f.name.startswith('.')]
    
    print(f"[PROCESS_NOW] Found {len(input_files)} files to process")
    
    for file_path in input_files:
        if file_path.is_file() and not file_path.name.startswith('.'):
            result = process_file(file_path, background_tasks)
            processed.append({
                "file": file_path.name,
                "result": result
            })
    
    # Сохраняем метрики в MongoDB
    save_processing_metrics()
    print(f"[PROCESS_NOW] Processing completed. Session ID: {metrics['session_id']}")
    print(f"[PROCESS_NOW] Summary: {len(processed)} files processed, "
          f"{metrics['summary']['total_units']} units created, "
          f"{metrics['summary']['total_errors']} errors")
    
    return JSONResponse(content={
        "status": "processing",
        "processed_count": len(processed),
        "session_id": metrics["session_id"],
        "summary": metrics["summary"],
        "files": processed
    })


@app.get("/status/{unit_id}")
async def get_status(unit_id: str):
    """Получить статус обработки unit'а."""
    # Пытаемся получить из MongoDB
    manifest = get_manifest_from_mongo(unit_id)
    
    # Fallback на JSON файл
    if not manifest:
        manifest_path = NORMALIZED_DIR / unit_id / "manifest.json"
        if manifest_path.exists():
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
    
    if not manifest:
        raise HTTPException(status_code=404, detail=f"Unit {unit_id} not found")
    
    return JSONResponse(content=manifest)


def get_processing_summary(session_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Получает агрегированную статистику обработки из MongoDB."""
    client = get_mongo_metadata_client()
    if not client:
        return None
    
    try:
        db = client[MONGO_METADATA_DB]
        collection = db[MONGO_METRICS_COLLECTION]
        
        # Если указан session_id, получаем конкретную сессию
        if session_id:
            metrics = collection.find_one({"session_id": session_id})
            if metrics:
                metrics.pop("_id", None)
            return metrics
        
        # Иначе получаем последнюю сессию
        metrics = collection.find_one(sort=[("started_at", -1)])
        if metrics:
            metrics.pop("_id", None)
        return metrics
    except Exception as e:
        print(f"Error getting processing summary: {e}")
        return None


@app.get("/metrics/processing")
async def get_processing_metrics(session_id: Optional[str] = None):
    """Получить метрики обработки. Если session_id не указан, возвращает последнюю сессию."""
    metrics = get_processing_summary(session_id)
    
    if not metrics:
        raise HTTPException(status_code=404, detail="Processing metrics not found")
    
    return JSONResponse(content=metrics)


@app.get("/metrics/summary")
async def get_metrics_summary(session_id: Optional[str] = None):
    """Получить агрегированную сводку метрик обработки."""
    metrics = get_processing_summary(session_id)
    
    if not metrics:
        raise HTTPException(status_code=404, detail="Processing metrics not found")
    
    # Возвращаем только summary и основные статистики
    summary_data = {
        "session_id": metrics.get("session_id"),
        "started_at": metrics.get("started_at"),
        "completed_at": metrics.get("completed_at"),
        "summary": metrics.get("summary", {}),
        "total_archives": len(metrics.get("archives_extracted", [])),
        "total_conversions": len(metrics.get("conversions", [])),
        "total_errors": len(metrics.get("errors", []))
    }
    
    return JSONResponse(content=summary_data)


@app.get("/protocols/{date}")
async def get_protocols(date: str = PathParam(..., pattern=r"^\d{4}-\d{2}-\d{2}$")):
    """
    Получает протоколы по дате из MongoDB и возвращает URLs документов.
    Формат даты: YYYY-MM-DD
    """
    try:
        protocols = get_protocols_by_date(date)
        return JSONResponse(content={
            "date": date,
            "protocols_count": len(protocols),
            "protocols": protocols
        })
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/download_protocols/{date}")
async def download_protocols(date: str, background_tasks: BackgroundTasks = None):
    """
    Получает протоколы по дате, скачивает документы и обрабатывает их.
    Формат даты: YYYY-MM-DD
    """
    try:
        # Получаем протоколы
        protocols = get_protocols_by_date(date)
        
        if not protocols:
            return JSONResponse(content={
                "status": "no_protocols",
                "date": date,
                "message": "Протоколы не найдены для указанной даты"
            })
        
        downloaded = []
        failed = []
        
        # Скачиваем документы
        for purchase_number, doc_info in protocols.items():
            # Обрабатываем как один документ, так и список
            docs = [doc_info] if isinstance(doc_info, dict) else doc_info
            
            for doc in docs:
                url = doc.get("url")
                filename = doc.get("fileName", f"{purchase_number}.pdf")
                
                if not url:
                    continue
                
                # Скачиваем файл
                dest_path = INPUT_DIR / sanitize_filename(filename)
                if download_document(url, dest_path):
                    downloaded.append({
                        "purchase_number": purchase_number,
                        "url": url,
                        "filename": filename,
                        "path": str(dest_path)
                    })
                    
                    # Обрабатываем файл (синхронно, так как уже в background task)
                    process_file(dest_path, background_tasks)
                else:
                    failed.append({
                        "purchase_number": purchase_number,
                        "url": url,
                        "filename": filename
                    })
        
        return JSONResponse(content={
            "status": "processing",
            "date": date,
            "downloaded_count": len(downloaded),
            "failed_count": len(failed),
            "downloaded": downloaded,
            "failed": failed
        })
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)




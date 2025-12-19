"""
Router/Preprocessor API для классификации и предобработки документов.
FastAPI endpoints для загрузки, обработки и мониторинга файлов.
"""
import json
import hashlib
import hmac
from pathlib import Path
from typing import Dict, Optional, Any

from fastapi import FastAPI, File, UploadFile, Header, HTTPException, BackgroundTasks, Query
from fastapi import Path as PathParam
from fastapi.responses import JSONResponse
import shutil

# Импортируем из модулей
from .config import (
    INPUT_DIR, TEMP_DIR, OUTPUT_DIR, EXTRACTED_DIR, NORMALIZED_DIR, ARCHIVE_DIR,
    DOCLING_API, WEBHOOK_SECRET, MONGO_METADATA_DB, MONGO_METRICS_COLLECTION, NORMALIZED_DIR
)
from .mongo import (
    get_mongo_metadata_client, get_manifest_from_mongo, get_protocols_by_date
)
from .utils import sanitize_filename, calculate_sha256
from .core.processor import FileProcessor, process_file as core_process_file
from .metrics import init_processing_metrics, save_processing_metrics, get_current_metrics

# ============================================================================
# FastAPI приложение
# ============================================================================

app = FastAPI(
    title="Docling Router/Preprocessor",
    description="API для предобработки документов перед Docling",
    version="2.0"
)


# ============================================================================
# ФУНКЦИИ-ПОМОЩНИКИ
# ============================================================================

def process_file(file_path: Path, background_tasks: Optional[BackgroundTasks] = None) -> Dict[str, Any]:
    """
    Обрабатывает загруженный файл с полным pipeline.
    
    Использует FileProcessor из core для обработки файла.
    Возвращает результат в формате словаря для обратной совместимости с API.
    
    Args:
        file_path: Путь к файлу для обработки
        background_tasks: BackgroundTasks (не используется, для совместимости)
    
    Returns:
        Словарь с результатами обработки
    """
    # Используем функцию из core/processor.py для обратной совместимости
    # Она уже обрабатывает исключения и возвращает словарь
    return core_process_file(file_path, background_tasks)


def download_document(url: str, dest_path: Path) -> bool:
    """
    Скачивает документ с URL.
    Используется для загрузки протоколов с zakupki.gov.ru
    """
    try:
        import requests
        
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(dest_path, 'wb') as f:
            f.write(response.content)
        
        print(f"✅ Downloaded: {url} → {dest_path.name}")
        return True
    
    except Exception as e:
        print(f"❌ Error downloading {url}: {e}")
        return False
    

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
        print(f"❌ Error getting processing summary: {e}")
        return None


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "router",
        "version": "2.0"
    }


@app.post("/upload")
async def upload(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    """
    Загрузка файла через API.
    
    Параметры:
    - file: UploadFile - загружаемый файл
    
    Возвращает:
    - status: статус обработки
    - file: имя файла
    - size: размер файла
    - detected_type: определенный тип файла
    """
    try:
        # Сохраняем файл во временную директорию
        temp_file = TEMP_DIR / sanitize_filename(file.filename)
        with open(temp_file, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        # Перемещаем в input для обработки
        input_file = INPUT_DIR / temp_file.name
        shutil.move(str(temp_file), str(input_file))
        
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
    """
    Webhook endpoint для внешних триггеров.
    
    Параметры:
    - file_path: путь до файла
    - x_signature: HMAC подпись (если настроено)
    
    Возвращает:
    - статус обработки файла
    """
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
    """
    Обрабатывает все файлы из INPUT_DIR.
    
    Возвращает:
    - status: статус обработки
    - processed_count: количество обработанных файлов
    - session_id: ID сессии обработки
    - summary: сводка по обработанным файлам
    """
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
    print(f"[PROCESS_NOW] Summary: {len(processed)} files processed")
    
    return JSONResponse(content={
        "status": "processing",
        "processed_count": len(processed),
        "session_id": metrics["session_id"],
        "summary": metrics["summary"],
        "files": processed
    })


@app.get("/status/{unit_id}")
async def get_status(unit_id: str):
    """
    Получить статус обработки unit'а.
    
    Параметры:
    - unit_id: идентификатор unit'а
    
    Возвращает:
    - manifest: информация о unit'е и обработанных файлах
    """
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


@app.get("/metrics/processing")
async def get_processing_metrics(session_id: Optional[str] = Query(None)):
    """
    Получить метрики обработки.
    
    Параметры (опциональные):
    - session_id: ID сессии (если не указан, вернет последнюю)
    
    Возвращает:
    - Полные метрики обработки: файлы, ошибки, размеры и т.д.
    """
    metrics = get_processing_summary(session_id)
    
    if not metrics:
        raise HTTPException(status_code=404, detail="Processing metrics not found")
    
    return JSONResponse(content=metrics)


@app.get("/metrics/summary")
async def get_metrics_summary(session_id: Optional[str] = Query(None)):
    """
    Получить агрегированную сводку метрик обработки.
    
    Параметры (опциональные):
    - session_id: ID сессии (если не указан, вернет последнюю)
    
    Возвращает:
    - Сводка: количество архивов, конверсий, ошибок и т.д.
    """
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
    
    Параметры:
    - date: дата в формате YYYY-MM-DD
    
    Возвращает:
    - Словарь протоколов с URLs документов
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
    
    Параметры:
    - date: дата в формате YYYY-MM-DD
    
    Возвращает:
    - Список скачанных и обработанных документов
    - Список файлов, которые не удалось скачать
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
                    
                    # Обрабатываем файл
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


# ============================================================================
# ЗАПУСК
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)

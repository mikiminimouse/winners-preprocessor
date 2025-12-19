"""
API для Docling сервиса обработки документов.
Обрабатывает документы через Docling и fallback библиотеки.
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from pathlib import Path
import json
import logging
import os
import time
import signal
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor
import functools

from processor import DocumentProcessor, save_processing_error

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Docling Processing API")

# Конфигурация timeout
DEFAULT_TIMEOUT = int(os.environ.get("DEFAULT_TIMEOUT", "300"))  # 5 минут по умолчанию

# Конфигурация параллельной обработки
MAX_PARALLEL_WORKERS = int(os.environ.get("MAX_PARALLEL_WORKERS", "2"))  # Количество параллельных worker'ов
PARALLEL_ENABLED = os.environ.get("PARALLEL_ENABLED", "true").lower() == "true"

# ThreadPoolExecutor для параллельной обработки
executor = ThreadPoolExecutor(max_workers=MAX_PARALLEL_WORKERS) if PARALLEL_ENABLED else None


class ProcessRequest(BaseModel):
    """Запрос на обработку unit'а документов."""
    unit_id: str
    manifest: str  # Путь к manifest.json
    files: List[dict]
    route: Optional[str] = None


class ProcessResponse(BaseModel):
    """Ответ после обработки."""
    unit_id: str
    status: str
    output_files: List[str]
    processing_time: float


@app.post("/process")
async def process_documents(request: ProcessRequest):
    """
    Обрабатывает unit документов согласно manifest.
    
    В реальной реализации здесь должна быть логика:
    1. Чтение manifest.json (из файла или MongoDB)
    2. Определение route (pdf_scan, pdf_text, docx, mixed, etc.)
    3. Запуск соответствующего пайплайна Docling:
       - Text Extraction (для pdf_text, docx)
       - OCR (для pdf_scan, image)
       - Layout Analysis
       - Table Extraction
       - Export (JSON, Markdown, HTML)
    4. Сохранение результатов в output/
    """
    try:
        import time
        start_time = time.time()
        
        # Пытаемся получить manifest
        manifest = None
        
        # Если manifest начинается с mongodb://, получаем из MongoDB
        if request.manifest.startswith("mongodb://"):
            unit_id = request.manifest.replace("mongodb://", "")
            try:
                from pymongo import MongoClient
                import os
                
                mongo_server = os.environ.get("MONGO_SERVER", "mongodb:27017")
                mongo_user = os.environ.get("MONGO_METADATA_USER", "docling_user")
                mongo_password = os.environ.get("MONGO_METADATA_PASSWORD", "password")
                mongo_db = os.environ.get("MONGO_METADATA_DB", "docling_metadata")
                
                url_mongo = f'mongodb://{mongo_user}:{mongo_password}@{mongo_server}/?authSource=admin'
                client = MongoClient(url_mongo)
                db = client[mongo_db]
                manifest_doc = db.manifests.find_one({"unit_id": unit_id})
                
                if manifest_doc:
                    manifest_doc.pop("_id", None)
                    manifest = manifest_doc
                    logger.info(f"Manifest loaded from MongoDB for unit {unit_id}")
                else:
                    logger.warning(f"Manifest not found in MongoDB for unit {unit_id}")
            except Exception as e:
                logger.warning(f"Could not load manifest from MongoDB: {e}")
        
        # Если не получили из MongoDB, пробуем как файл
        if not manifest:
            manifest_path = Path(request.manifest)
            if manifest_path.exists():
                with open(manifest_path, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
                logger.info(f"Manifest loaded from file: {request.manifest}")
            else:
                # Если manifest не найден, используем данные из запроса
                logger.info(f"Manifest not found at {request.manifest}, using request data")
                manifest = {
                    "unit_id": request.unit_id,
                    "processing": {"route": request.route},
                    "files": request.files
                }
        
        route = request.route or manifest.get("processing", {}).get("route", "unknown")
        files = request.files or manifest.get("files", [])
        
        logger.info(f"Processing unit {request.unit_id} with route {route}, {len(files)} files")
        
        # Проверяем существование файлов
        existing_files = []
        missing_files = []
        
        for file_info in files:
            file_path_str = file_info.get("path", "")
            file_name = Path(file_path_str).name
            
            # Всегда используем путь относительно /data/normalized
            # Файлы находятся в /data/normalized/UNIT_*/files/
            unit_dir = Path("/data/normalized") / request.unit_id / "files"
            file_path = unit_dir / file_name
            
            logger.info(f"Looking for file: {file_name} in {unit_dir}")
            
            if file_path.exists():
                existing_files.append({**file_info, "path": str(file_path)})
                logger.info(f"File found: {file_path}")
            else:
                # Проверяем, существует ли директория unit'а
                if not unit_dir.exists():
                    logger.warning(f"Unit directory does not exist: {unit_dir}")
                else:
                    # Показываем, что есть в директории
                    existing_files_list = list(unit_dir.glob("*"))
                    logger.warning(f"Unit directory exists but file not found. Files in dir: {[f.name for f in existing_files_list[:5]]}")
                
                missing_files.append(str(file_path))
                logger.warning(f"File not found: {file_path}")
        
        if not existing_files:
            raise HTTPException(
                status_code=404,
                detail=f"No files found for unit {request.unit_id}. Missing: {missing_files[:3]}"
            )
        
        # Обработка документов с использованием DocumentProcessor
        output_files = []
        output_dir = Path("/data/output") / request.unit_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Проверка timeout - увеличиваем для больших файлов
        timeout = DEFAULT_TIMEOUT
        
        # Определяем размер файлов и увеличиваем timeout для больших
        total_size = sum(
            Path(file_info["path"]).stat().st_size 
            for file_info in existing_files 
            if Path(file_info["path"]).exists()
        )
        is_large = total_size > 50 * 1024 * 1024  # 50 MB
        if is_large:
            timeout = int(timeout * 2)  # Удваиваем timeout для больших файлов
            logger.info(f"Large files detected ({total_size / 1024 / 1024:.1f} MB), timeout increased to {timeout}s")
        
        processing_results = []
        
        # Функция для обработки одного файла
        def process_single_file(file_info: Dict[str, Any]) -> Dict[str, Any]:
            """Обрабатывает один файл."""
            try:
                processor = DocumentProcessor(request.unit_id, file_info, output_dir)
                result = processor.process()
                return result
            except Exception as e:
                logger.error(f"Error processing file {file_info.get('original_name')}: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e),
                    "output_files": []
                }
        
        # Подготовка файлов для обработки
        files_to_process = []
        for file_info in existing_files:
            # Определяем route для каждого файла
            file_route = file_info.get("route")
            if not file_route:
                if route == "mixed":
                    # Для mixed route определяем route для каждого файла
                    detected_type = file_info.get("detected_type", "unknown")
                    needs_ocr = file_info.get("needs_ocr", False)
                    if detected_type == "pdf":
                        file_route = "pdf_scan" if needs_ocr else "pdf_text"
                    elif detected_type == "docx":
                        file_route = "docx"
                    elif detected_type == "html":
                        file_route = "html_text"
                    else:
                        file_route = "unknown"
                else:
                    file_route = route
            file_info["route"] = file_route
            files_to_process.append(file_info)
        
        # Параллельная или последовательная обработка
        if PARALLEL_ENABLED and executor and len(files_to_process) > 1:
            # Параллельная обработка нескольких файлов
            logger.info(f"Processing {len(files_to_process)} files in parallel (max {MAX_PARALLEL_WORKERS} workers)")
            
            # Создаем задачи для параллельной обработки
            futures = []
            
            for file_info in files_to_process:
                # Проверка времени перед запуском новой задачи
                elapsed = time.time() - start_time
                if elapsed > timeout * 0.8:
                    logger.warning(
                        f"Unit {request.unit_id} processing time approaching timeout "
                        f"({elapsed:.2f}s / {timeout}s)"
                    )
                
                if elapsed > timeout:
                    error_msg = f"Timeout exceeded ({elapsed:.2f}s > {timeout}s)"
                    logger.error(f"Unit {request.unit_id}: {error_msg}")
                    save_processing_error({
                        "unit_id": request.unit_id,
                        "file_name": "multiple_files",
                        "route": route,
                        "error_type": "timeout",
                        "error_message": error_msg,
                        "processing_time_before_error": elapsed,
                        "created_at": datetime.utcnow().isoformat()
                    })
                    raise HTTPException(status_code=504, detail=error_msg)
                
                # Добавляем задачу в executor
                future = executor.submit(process_single_file, file_info)
                futures.append(future)
            
            # Ждем завершения всех задач
            for future in futures:
                try:
                    remaining_time = timeout - (time.time() - start_time)
                    if remaining_time <= 0:
                        raise TimeoutError("Timeout exceeded")
                    result = future.result(timeout=max(remaining_time, 1))
                    processing_results.append(result)
                    if result.get("success"):
                        output_files.extend(result.get("output_files", []))
                    else:
                        logger.error(f"Error processing file: {result.get('error')}")
                except Exception as e:
                    logger.error(f"Error in parallel processing: {e}", exc_info=True)
                    processing_results.append({
                        "success": False,
                        "error": str(e),
                        "output_files": []
                    })
        else:
            # Последовательная обработка
            logger.info(f"Processing {len(files_to_process)} files sequentially")
            
            for file_info in files_to_process:
                # Проверка времени обработки
                elapsed = time.time() - start_time
                if elapsed > timeout * 0.8:
                    logger.warning(
                        f"Unit {request.unit_id} processing time approaching timeout "
                        f"({elapsed:.2f}s / {timeout}s)"
                    )
                
                if elapsed > timeout:
                    error_msg = f"Timeout exceeded ({elapsed:.2f}s > {timeout}s)"
                    logger.error(f"Unit {request.unit_id}: {error_msg}")
                    save_processing_error({
                        "unit_id": request.unit_id,
                        "file_id": file_info.get("file_id", ""),
                        "file_name": file_info.get("original_name", ""),
                        "route": file_info.get("route", route),
                        "error_type": "timeout",
                        "error_message": error_msg,
                        "processing_time_before_error": elapsed,
                        "created_at": datetime.utcnow().isoformat()
                    })
                    raise HTTPException(status_code=504, detail=error_msg)
                
                # Обработка файла
                result = process_single_file(file_info)
                processing_results.append(result)
                
                if result.get("success"):
                    output_files.extend(result.get("output_files", []))
                else:
                    logger.error(f"Error processing file {file_info.get('original_name')}: {result.get('error')}")
                    # Продолжаем обработку остальных файлов
        
        processing_time = time.time() - start_time
        
        # Проверка успешности обработки
        all_successful = all(r.get("success", False) for r in processing_results)
        status = "completed" if all_successful else "partial"
        
        if not all_successful:
            logger.warning(f"Unit {request.unit_id} processed with errors")
        
        logger.info(f"Unit {request.unit_id} processed in {processing_time:.2f}s, status: {status}")
        
        return ProcessResponse(
            unit_id=request.unit_id,
            status=status,
            output_files=output_files,
            processing_time=processing_time
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing unit {request.unit_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "docling"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)




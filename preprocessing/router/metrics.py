"""
Метрики обработки документов.
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import uuid

from .mongo import get_mongo_metadata_client, MONGO_METADATA_DB, MONGO_METRICS_COLLECTION
# Импорт detect_file_type будет сделан внутри функции для избежания циклических импортов


# Глобальная переменная для метрик текущей сессии обработки
_current_processing_metrics: Optional[Dict[str, Any]] = None


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
        "fake_doc_files": [],
        "doc_conversions_detailed": [],
        "pdf_sorts": [],
        "pending_processing": {
            "normalize": [],
            "convert": [],
            "extract": []
        },
        "duplicates": [],
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
            },
            "fake_doc_statistics": {
                "total_fake_doc": 0,
                "by_type": {},
                "by_reason": {}
            },
            "doc_conversion_statistics": {
                "total_attempted": 0,
                "successful": 0,
                "failed": 0,
                "avg_conversion_time": 0.0,
                "errors_by_reason": {}
            },
            "pending_statistics": {
                "files_in_pending_normalize": 0,
                "files_in_pending_convert": 0,
                "files_in_pending_extract": 0,
                "files_processed_from_pending": 0
            },
            "duplicate_statistics": {
                "total_duplicate_files": 0,
                "duplicate_groups_count": 0
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
    
    # Статистика по фейковым .doc файлам
    fake_doc_stats = {
        "total_fake_doc": 0,
        "by_type": {},
        "by_reason": {}
    }
    for fake_doc in metrics.get("fake_doc_files", []):
        fake_doc_stats["total_fake_doc"] += 1
        detected_type = fake_doc.get("detected_type", "unknown")
        fake_doc_stats["by_type"][detected_type] = fake_doc_stats["by_type"].get(detected_type, 0) + 1
        reason = fake_doc.get("fake_doc_reason", "unknown")
        fake_doc_stats["by_reason"][reason] = fake_doc_stats["by_reason"].get(reason, 0) + 1
    summary["fake_doc_statistics"] = fake_doc_stats
    
    # Статистика по конвертации DOC
    doc_conv_stats = {
        "total_attempted": 0,
        "successful": 0,
        "failed": 0,
        "avg_conversion_time": 0.0,
        "errors_by_reason": {}
    }
    conversion_times = []
    for conv in metrics.get("doc_conversions_detailed", []):
        doc_conv_stats["total_attempted"] += 1
        if conv.get("success", False):
            doc_conv_stats["successful"] += 1
            if conv.get("conversion_time"):
                conversion_times.append(conv["conversion_time"])
        else:
            doc_conv_stats["failed"] += 1
            error = conv.get("error", "unknown")
            doc_conv_stats["errors_by_reason"][error] = doc_conv_stats["errors_by_reason"].get(error, 0) + 1
    
    if conversion_times:
        doc_conv_stats["avg_conversion_time"] = sum(conversion_times) / len(conversion_times)
    
    summary["doc_conversion_statistics"] = doc_conv_stats


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
    
    # Обновляем summary в реальном времени
    summary = _current_processing_metrics.get("summary", {})
    summary["total_input_files"] = len(_current_processing_metrics.get("input_files", []))
    
    # Обновляем статистику по типам
    detected_type = file_info.get("detected_type", "unknown")
    summary["by_detected_type"][detected_type] = summary["by_detected_type"].get(detected_type, 0) + 1
    
    # Обновляем статистику по расширениям
    extension = file_path.suffix.lower() or "no_extension"
    summary["by_extension"][extension] = summary["by_extension"].get(extension, 0) + 1


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
                # Определяем тип каждого файла (импорт внутри функции)
                from .file_detection import detect_file_type
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


def add_conversion_metric(original: str, converted_to: str, success: bool, details: Optional[Dict[str, Any]] = None) -> None:
    """Добавляет информацию о конвертации файла в метрики."""
    global _current_processing_metrics
    if not _current_processing_metrics:
        init_processing_metrics()
    
    metric_entry = {
        "original": original,
        "converted_to": converted_to,
        "success": success,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if details:
        metric_entry["details"] = details
    
    _current_processing_metrics["conversions"].append(metric_entry)


def add_fake_doc_metric(file_path: str, detected_type: str, fake_doc_reason: str, file_info: Optional[Dict[str, Any]] = None) -> None:
    """Добавляет информацию о фейковом .doc файле в метрики."""
    global _current_processing_metrics
    if not _current_processing_metrics:
        init_processing_metrics()
    
    # Инициализируем структуру для фейковых .doc если её нет
    if "fake_doc_files" not in _current_processing_metrics:
        _current_processing_metrics["fake_doc_files"] = []
    
    metric_entry = {
        "file_path": file_path,
        "detected_type": detected_type,
        "fake_doc_reason": fake_doc_reason,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if file_info:
        metric_entry["file_info"] = {
            "mime_type": file_info.get("mime_type"),
            "is_archive": file_info.get("is_archive", False),
            "extension": file_info.get("extension"),
            "magic_bytes": file_info.get("magic_bytes")
        }
    
    _current_processing_metrics["fake_doc_files"].append(metric_entry)


def add_doc_conversion_detailed_metric(
    original_file: str,
    success: bool,
    conversion_time: Optional[float] = None,
    error: Optional[str] = None,
    error_details: Optional[Dict[str, Any]] = None
) -> None:
    """Добавляет детальную информацию о конвертации DOC в метрики."""
    global _current_processing_metrics
    if not _current_processing_metrics:
        init_processing_metrics()
    
    # Инициализируем структуру для детальных метрик конвертации если её нет
    if "doc_conversions_detailed" not in _current_processing_metrics:
        _current_processing_metrics["doc_conversions_detailed"] = []
    
    metric_entry = {
        "original_file": original_file,
        "success": success,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if conversion_time is not None:
        metric_entry["conversion_time"] = conversion_time
    
    if error:
        metric_entry["error"] = error
    
    if error_details:
        metric_entry["error_details"] = error_details
    
    _current_processing_metrics["doc_conversions_detailed"].append(metric_entry)


def add_unit_created_metric(unit_id: str, files_count: int, file_types: List[str]) -> None:
    """Добавляет информацию о созданном unit в метрики и обновляет summary."""
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
    
    # Обновляем summary в реальном времени
    summary = _current_processing_metrics.get("summary", {})
    summary["total_units"] = len(_current_processing_metrics.get("units_created", []))


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
    
    # Обновляем summary в реальном времени
    summary = _current_processing_metrics.get("summary", {})
    summary["total_errors"] = len(_current_processing_metrics.get("errors", []))


def add_pdf_sort_metric(unit_id: str, unit_type: str, files_count: int, files_info: List[Dict[str, Any]]) -> None:
    """Добавляет метрику сортировки PDF unit'а."""
    global _current_processing_metrics
    if not _current_processing_metrics:
        init_processing_metrics()
    
    # Инициализируем структуру для метрик сортировки PDF если её нет
    if "pdf_sorts" not in _current_processing_metrics:
        _current_processing_metrics["pdf_sorts"] = []
    
    metric_entry = {
        "unit_id": unit_id,
        "unit_type": unit_type,  # "text_pdf" или "scan_pdf"
        "files_count": files_count,
        "files_info": files_info,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    _current_processing_metrics["pdf_sorts"].append(metric_entry)


def add_pending_file_metric(stage: str, file_path: str, unit_id: str, detected_type: str) -> None:
    """Добавляет метрику о файле, перемещенном в промежуточную директорию."""
    global _current_processing_metrics
    if not _current_processing_metrics:
        init_processing_metrics()
    
    if "pending_processing" not in _current_processing_metrics:
        _current_processing_metrics["pending_processing"] = {"normalize": [], "convert": [], "extract": []}
    
    metric_entry = {
        "file_path": file_path,
        "unit_id": unit_id,
        "detected_type": detected_type,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if stage in _current_processing_metrics["pending_processing"]:
        _current_processing_metrics["pending_processing"][stage].append(metric_entry)
        
        # Обновляем summary
        summary = _current_processing_metrics.get("summary", {})
        pending_stats = summary.get("pending_statistics", {})
        if stage == "normalize":
            pending_stats["files_in_pending_normalize"] = pending_stats.get("files_in_pending_normalize", 0) + 1
        elif stage == "convert":
            pending_stats["files_in_pending_convert"] = pending_stats.get("files_in_pending_convert", 0) + 1
        elif stage == "extract":
            pending_stats["files_in_pending_extract"] = pending_stats.get("files_in_pending_extract", 0) + 1


def add_duplicate_metric(unit_id: str, file_paths: List[str], hash_value: str) -> None:
    """Добавляет информацию о дубликатах файлов в unit."""
    global _current_processing_metrics
    if not _current_processing_metrics:
        init_processing_metrics()
    
    if "duplicates" not in _current_processing_metrics:
        _current_processing_metrics["duplicates"] = []
    
    metric_entry = {
        "unit_id": unit_id,
        "file_paths": file_paths,
        "hash_value": hash_value,
        "duplicate_count": len(file_paths) - 1,  # Все кроме первого
        "timestamp": datetime.utcnow().isoformat()
    }
    
    _current_processing_metrics["duplicates"].append(metric_entry)
    
    # Обновляем summary
    summary = _current_processing_metrics.get("summary", {})
    dup_stats = summary.get("duplicate_statistics", {})
    dup_stats["total_duplicate_files"] = dup_stats.get("total_duplicate_files", 0) + (len(file_paths) - 1)
    dup_stats["duplicate_groups_count"] = dup_stats.get("duplicate_groups_count", 0) + 1


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


"""
Работа с манифестами для router микросервиса.

Реализует manifest v2 согласно PRD раздел 14.
"""
from typing import List, Dict, Optional
import uuid
from datetime import datetime
from pathlib import Path

from .config import MONGO_METADATA_DB
from .state_machine import UnitStateMachine


def create_manifest(unit_id: str, files: List[Dict], archive_info: Optional[Dict] = None) -> Dict:
    """Создает manifest для unit'а документов."""
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


def create_manifest_v2(
    unit_id: str,
    protocol_id: Optional[str] = None,
    protocol_date: Optional[str] = None,
    files: List[Dict] = None,
    current_cycle: int = 1,
    state_trace: Optional[List[str]] = None,
    final_cluster: Optional[str] = None,
    final_reason: Optional[str] = None,
    unit_semantics: Optional[Dict] = None,
    source_urls: Optional[List[Dict]] = None,
    manifest_path: Optional[Path] = None
) -> Dict:
    """
    Создает manifest v2 для unit'а согласно PRD раздел 14.2.
    
    Manifest v2 содержит:
    - schema_version: "2.0"
    - unit_id: идентификатор UNIT
    - protocol_id: ID протокола из БД
    - protocol_date: Дата протокола из БД (YYYY-MM-DD) - используется для структуры директорий
    - source: информация об источниках (URLs)
    - unit_semantics: семантика UNIT (домен, сущность, ожидаемое содержимое)
    - files: список файлов с трансформациями
    - processing: информация о циклах обработки
    - state_machine: состояние и история переходов
    - integrity: проверка целостности
    
    Args:
        unit_id: Идентификатор UNIT
        protocol_id: ID протокола в БД (опционально)
        protocol_date: Дата протокола из БД в формате YYYY-MM-DD (опционально)
        files: Список файлов с информацией о трансформациях (опционально)
        current_cycle: Текущий цикл обработки (1-3)
        state_trace: История переходов состояний (опционально)
        final_cluster: Финальный кластер (Merge_1, Merge_2, Merge_3) (опционально)
        final_reason: Причина попадания в финальный кластер (опционально)
        unit_semantics: Семантика UNIT (опционально)
        source_urls: Список URL источников (опционально)
        manifest_path: Путь к существующему manifest для загрузки state_trace (опционально)
    
    Returns:
        Словарь с manifest v2
    """
    if files is None:
        files = []
    
    # Загружаем state_trace из существующего manifest или используем переданный
    if state_trace is None and manifest_path and manifest_path.exists():
        try:
            import json
            with open(manifest_path, 'r', encoding='utf-8') as f:
                existing_manifest = json.load(f)
                if "state_machine" in existing_manifest:
                    state_trace = existing_manifest["state_machine"].get("state_trace", [])
        except Exception:
            pass
    
    # Если state_trace все еще None, создаем начальный
    if state_trace is None:
        state_trace = ["RAW_INPUT"]
    
    # Определяем route для обработки
    route = None
    if len(files) == 1:
        f = files[0]
        detected_type = f.get("detected_type", "unknown")
        needs_ocr = f.get("needs_ocr", False)
        
        if detected_type == "pdf":
            route = "pdf_scan" if needs_ocr else "pdf_text"
        elif detected_type == "docx":
            route = "docx"
        elif detected_type == "image":
            route = "image_ocr"
        elif detected_type == "html":
            route = "html_text"
    else:
        route = "mixed"
    
    # Формируем список файлов с трансформациями
    files_list = []
    for file_info in files:
        file_entry = {
            "original_name": file_info.get("original_name", ""),
            "current_name": file_info.get("current_name", file_info.get("original_name", "")),
            "mime_detected": file_info.get("mime_type", ""),
            "pages_or_parts": file_info.get("pages_or_parts", 1),
            "transformations": file_info.get("transformations", [])
        }
        files_list.append(file_entry)
    
    # Определяем финальное состояние из state_trace
    final_state = state_trace[-1] if state_trace else "RAW_INPUT"
    initial_state = state_trace[0] if state_trace else "RAW_INPUT"
    
    manifest = {
        "schema_version": "2.0",
        "unit_id": unit_id,
        "protocol_id": protocol_id or "",
        "protocol_date": protocol_date or "",  # Дата протокола из БД (YYYY-MM-DD)
        "source": {
            "urls": source_urls or []
        },
        "unit_semantics": unit_semantics or {
            "domain": "public_procurement",
            "entity": "tender_protocol",
            "expected_content": ["protocol", "attachments"]
        },
        "files": files_list,
        "processing": {
            "current_cycle": current_cycle,
            "max_cycles": 3,
            "final_cluster": final_cluster or "",
            "final_reason": final_reason or "",
            "classifier_confidence": 1.0,  # Можно добавить реальную оценку
            "route": route
        },
        "state_machine": {
            "initial_state": initial_state,
            "final_state": final_state,
            "current_state": final_state,
            "state_trace": state_trace
        },
        "integrity": {
            "checksum": "",  # Можно вычислить SHA256 для всего UNIT
            "file_count": len(files)
        },
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }
    
    return manifest


def update_manifest_v2(
    manifest: Dict,
    state_trace: Optional[List[str]] = None,
    current_cycle: Optional[int] = None,
    final_cluster: Optional[str] = None,
    final_reason: Optional[str] = None,
    transformations: Optional[List[Dict]] = None,
    protocol_date: Optional[str] = None
) -> Dict:
    """
    Обновляет существующий manifest v2.
    
    Args:
        manifest: Существующий manifest
        state_trace: Новый state_trace (опционально)
        current_cycle: Новый текущий цикл (опционально)
        final_cluster: Финальный кластер (опционально)
        final_reason: Причина попадания в финальный кластер (опционально)
        transformations: Новые трансформации для добавления в files (опционально)
        protocol_date: Дата протокола из БД (опционально, для обновления)
    
    Returns:
        Обновленный manifest
    """
    if state_trace is not None:
        manifest["state_machine"]["state_trace"] = state_trace
        manifest["state_machine"]["final_state"] = state_trace[-1] if state_trace else manifest["state_machine"]["final_state"]
        manifest["state_machine"]["current_state"] = state_trace[-1] if state_trace else manifest["state_machine"]["current_state"]
    
    if current_cycle is not None:
        manifest["processing"]["current_cycle"] = current_cycle
    
    if final_cluster is not None:
        manifest["processing"]["final_cluster"] = final_cluster
    
    if final_reason is not None:
        manifest["processing"]["final_reason"] = final_reason
    
    if transformations is not None and manifest.get("files"):
        # Добавляем трансформации к первому файлу (можно улучшить логику)
        for i, trans in enumerate(transformations):
            if i < len(manifest["files"]):
                if "transformations" not in manifest["files"][i]:
                    manifest["files"][i]["transformations"] = []
                manifest["files"][i]["transformations"].append(trans)
    
    if protocol_date is not None:
        manifest["protocol_date"] = protocol_date
    
    manifest["updated_at"] = datetime.utcnow().isoformat()
    
    return manifest

"""
Manifest v2 - управление метаданными UNIT.

Manifest = состояние UNIT, хранит текущее состояние и историю трансформаций.
Согласно PRD раздел 14: Manifest = состояние, Audit = история.
"""
import json
import os  # ДОБАВЛЕНО: для fsync()
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from .state_machine import UnitState
from .config import MAX_CYCLES


def load_manifest(unit_path: Path) -> Dict[str, Any]:
    """
    Загружает manifest.json из директории UNIT.

    Args:
        unit_path: Путь к директории UNIT

    Returns:
        Словарь с manifest данными

    Raises:
        FileNotFoundError: Если manifest.json не найден
        json.JSONDecodeError: Если manifest.json некорректен
    """
    manifest_path = unit_path / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_manifest(unit_path: Path, manifest: Dict[str, Any]) -> None:
    """
    Сохраняет manifest.json в директорию UNIT.

    Args:
        unit_path: Путь к директории UNIT
        manifest: Словарь с manifest данными
    """
    unit_path.mkdir(parents=True, exist_ok=True)
    manifest_path = unit_path / "manifest.json"

    # Обновляем updated_at
    manifest["updated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # ИСПРАВЛЕНИЕ БАГ #5: Добавление fsync() для гарантии записи на диск
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        f.flush()  # Flush Python buffers
        os.fsync(f.fileno())  # Force write to disk


def _determine_route_from_files(files: List[Dict[str, Any]]) -> str:
    """
    Определяет route для обработки на основе файлов.
    
    Делегирует в unified routing registry для консистентности.
    
    Args:
        files: Список файлов с информацией о типах
        
    Returns:
        Route строка: pdf_text, pdf_scan, docx, xlsx, pptx, html, xml, image_ocr, rtf, mixed
    """
    from .routing import determine_route_from_files as _routing_determine
    return _routing_determine(files)


def create_manifest_v2(
    unit_id: str,
    protocol_id: Optional[str] = None,
    protocol_date: Optional[str] = None,
    files: Optional[List[Dict[str, Any]]] = None,
    current_cycle: int = 1,
    state_trace: Optional[List[str]] = None,
    final_cluster: Optional[str] = None,
    final_reason: Optional[str] = None,
    unit_semantics: Optional[Dict[str, Any]] = None,
    source_urls: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Создает manifest v2 для unit'а согласно PRD раздел 14.2.

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

    Returns:
        Словарь с manifest v2
    """
    if files is None:
        files = []

    if state_trace is None:
        state_trace = ["RAW"]

    # Определяем route для обработки
    route = _determine_route_from_files(files)

    # Формируем список файлов с трансформациями
    files_list = []
    for file_info in files:
        file_entry = {
            "original_name": file_info.get("original_name", ""),
            "current_name": file_info.get("current_name", file_info.get("original_name", "")),
            "mime_detected": file_info.get("mime_type", file_info.get("mime_detected", "")),
            "detected_type": file_info.get("detected_type", "unknown"),
            "needs_ocr": file_info.get("needs_ocr", False),
            "pages_or_parts": file_info.get("pages_or_parts", 1),
            "transformations": file_info.get("transformations", []),
        }
        files_list.append(file_entry)

    # Определяем финальное состояние из state_trace
    final_state = state_trace[-1] if state_trace else "RAW"
    initial_state = state_trace[0] if state_trace else "RAW"

    manifest = {
        "schema_version": "2.0",
        "unit_id": unit_id,
        "protocol_id": protocol_id or "",
        "protocol_date": protocol_date or "",
        "source": {"urls": source_urls or []},
        "unit_semantics": unit_semantics
        or {
            "domain": "public_procurement",
            "entity": "tender_protocol",
            "expected_content": ["protocol", "attachments"],
        },
        "files": files_list,
        "files_metadata": {
            f.get("original_name", ""): {
                "detected_type": f.get("detected_type", "unknown"),
                "needs_ocr": f.get("needs_ocr", False),
                "mime_type": f.get("mime_detected", "unknown"),
                "pages_or_parts": f.get("pages_or_parts", 1),
            }
            for f in files_list
        },
        "processing": {
            "current_cycle": current_cycle,
            "max_cycles": MAX_CYCLES,
            "final_cluster": final_cluster or "",
            "final_reason": final_reason or "",
            "classifier_confidence": 1.0,
            "route": route,
        },
        "state_machine": {
            "initial_state": initial_state,
            "final_state": final_state,
            "current_state": final_state,
            "state_trace": state_trace,
        },
        "integrity": {
            "checksum": "",  # Можно вычислить SHA256 для всего UNIT
            "file_count": len(files),
        },
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }

    return manifest


def update_manifest_operation(
    manifest: Dict[str, Any], operation: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Обновляет manifest, добавляя информацию об операции.

    Args:
        manifest: Существующий manifest
        operation: Информация об операции:
            - type: тип операции (convert, extract, normalize, rename)
            - file_index: индекс файла (опционально)
            - from: исходный формат/путь (опционально)
            - to: целевой формат/путь (опционально)
            - cycle: номер цикла
            - tool: инструмент (libreoffice, python-magic и т.д.)
            - timestamp: время операции (опционально)

    Returns:
        Обновленный manifest
    """
    operation_type = operation.get("type")
    file_index = operation.get("file_index", 0)
    cycle = operation.get("cycle", manifest.get("processing", {}).get("current_cycle", 1))

    # Добавляем timestamp если не указан
    if "timestamp" not in operation:
        operation["timestamp"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # Добавляем операцию к файлу
    if "files" in manifest and len(manifest["files"]) > file_index:
        file_entry = manifest["files"][file_index]
        if "transformations" not in file_entry:
            file_entry["transformations"] = []
        file_entry["transformations"].append(operation)

    # Обновляем applied_operations на уровне unit
    if "applied_operations" not in manifest:
        manifest["applied_operations"] = []
    manifest["applied_operations"].append(operation)

    manifest["updated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    return manifest


def update_manifest_state(
    manifest: Dict[str, Any], state: UnitState, cycle: int
) -> Dict[str, Any]:
    """
    Обновляет manifest, добавляя новое состояние в state_trace.

    Args:
        manifest: Существующий manifest
        state: Новое состояние
        cycle: Номер цикла

    Returns:
        Обновленный manifest
    """
    # Обновляем state_machine
    if "state_machine" not in manifest:
        manifest["state_machine"] = {
            "initial_state": state.value,
            "final_state": state.value,
            "current_state": state.value,
            "state_trace": [state.value],
        }
    else:
        state_trace = manifest["state_machine"].get("state_trace", [])
        state_trace.append(state.value)
        manifest["state_machine"]["state_trace"] = state_trace
        manifest["state_machine"]["current_state"] = state.value
        manifest["state_machine"]["final_state"] = state.value

    # Обновляем processing
    if "processing" not in manifest:
        manifest["processing"] = {}
    manifest["processing"]["current_cycle"] = cycle
    manifest["processing"]["current_state"] = state.value

    manifest["updated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    return manifest



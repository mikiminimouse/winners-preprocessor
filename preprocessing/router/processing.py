"""
Основная логика обработки файлов для router.
Классификация, распаковка, создание unit'а.
"""
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

from .config import INPUT_DIR, ARCHIVE_DIR, EXTRACTED_DIR
from .mongo import save_manifest_to_mongo
from .archive import safe_extract_archive
from .manifest import create_manifest
from .utils import calculate_sha256
from .file_detection import detect_file_type
from .metrics import add_input_file_metric, add_archive_extraction_metric, add_unit_created_metric
import uuid


def process_file_minimal(file_path: Path) -> Dict[str, Any]:
    """Минимальная функция обработки файла."""
    return {
        "status": "pending",
        "unit_id": str(uuid.uuid4()),
        "file": str(file_path)
    }

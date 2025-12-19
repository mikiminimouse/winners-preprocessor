"""
Обработка mixed units - юнитов с файлами разных типов.
"""
from pathlib import Path
from typing import Dict, List, Any
import shutil
import json
from datetime import datetime

from .file_classifier import classify_unit_files
from .config import PENDING_MIXED_DIR, EXTRACT_SORTED_MIXED_DIR


def process_mixed_unit(unit_id: str, file_paths: List[Path], source_stage: str = "detection") -> Dict[str, Any]:
    """
    Обрабатывает mixed unit - перемещает все файлы в pending/mixed/.
    
    Args:
        unit_id: ID юнита
        file_paths: Список путей к файлам
        source_stage: "detection" или "extraction"
    
    Returns:
        Результат обработки с метриками
    """
    result = {
        "unit_id": unit_id,
        "is_mixed": True,
        "source_stage": source_stage,
        "files_moved": 0,
        "target_directory": None,
        "errors": []
    }
    
    # Определяем целевую директорию
    if source_stage == "extraction":
        base_dir = EXTRACT_SORTED_MIXED_DIR
    else:
        base_dir = PENDING_MIXED_DIR
    
    unit_target_dir = base_dir / unit_id / "files"
    unit_target_dir.mkdir(parents=True, exist_ok=True)
    result["target_directory"] = str(base_dir / unit_id)
    
    # Перемещаем все файлы
    for file_path in file_paths:
        try:
            if file_path.exists():
                dest_file = unit_target_dir / file_path.name
                
                # Избегаем перезаписи
                counter = 1
                while dest_file.exists():
                    stem, suffix = file_path.stem, file_path.suffix
                    dest_file = unit_target_dir / f"{stem}_{counter}{suffix}"
                    counter += 1
                
                shutil.move(str(file_path), str(dest_file))
                result["files_moved"] += 1
        except Exception as e:
            result["errors"].append({
                "file": str(file_path),
                "error": str(e)
            })
    
    # Сохраняем метаданные о mixed unit
    save_mixed_unit_metadata(unit_id, result, file_paths, base_dir)
    
    return result


def save_mixed_unit_metadata(unit_id: str, process_result: Dict, file_paths: List[Path], base_dir: Path):
    """Сохраняет метаданные mixed unit."""
    metadata = {
        "unit_id": unit_id,
        "is_mixed": True,
        "processed_at": datetime.utcnow().isoformat(),
        "source_stage": process_result["source_stage"],
        "files_count": len(file_paths),
        "files": [str(f) for f in file_paths],
        "target_directory": process_result["target_directory"]
    }
    
    metadata_file = base_dir / unit_id / "mixed_metadata.json"
    metadata_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)


def get_mixed_units_statistics(include_extraction: bool = True) -> Dict[str, Any]:
    """
    Получает статистику по mixed units.
    
    Args:
        include_extraction: Включать ли статистику из extraction
    
    Returns:
        {
            "detection_mixed": {"units": int, "files": int},
            "extraction_mixed": {"units": int, "files": int},
            "total_mixed": {"units": int, "files": int}
        }
    """
    stats = {
        "detection_mixed": {"units": 0, "files": 0},
        "extraction_mixed": {"units": 0, "files": 0},
        "total_mixed": {"units": 0, "files": 0}
    }
    
    # Считаем mixed units из detection
    if PENDING_MIXED_DIR.exists():
        units = [d for d in PENDING_MIXED_DIR.iterdir() if d.is_dir() and d.name.startswith("UNIT_")]
        stats["detection_mixed"]["units"] = len(units)
        for unit_dir in units:
            files_dir = unit_dir / "files"
            if files_dir.exists():
                files = [f for f in files_dir.iterdir() if f.is_file()]
                stats["detection_mixed"]["files"] += len(files)
    
    # Считаем mixed units из extraction
    if include_extraction and EXTRACT_SORTED_MIXED_DIR.exists():
        units = [d for d in EXTRACT_SORTED_MIXED_DIR.iterdir() if d.is_dir() and d.name.startswith("UNIT_")]
        stats["extraction_mixed"]["units"] = len(units)
        for unit_dir in units:
            files_dir = unit_dir / "files"
            if files_dir.exists():
                files = [f for f in files_dir.iterdir() if f.is_file()]
                stats["extraction_mixed"]["files"] += len(files)
    
    # Итого
    stats["total_mixed"]["units"] = stats["detection_mixed"]["units"] + stats["extraction_mixed"]["units"]
    stats["total_mixed"]["files"] = stats["detection_mixed"]["files"] + stats["extraction_mixed"]["files"]
    
    return stats


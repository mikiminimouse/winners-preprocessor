"""
Управление промежуточными состояниями файлов на разных этапах обработки.
Сохранение метаданных в JSON файлах по этапам.
"""
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from .config import (
    DETECTED_DIR, EXTRACTED_DIR, CONVERTED_DIR, NORMALIZED_DIR, READY_DIR
)
from .utils import sanitize_filename


class StateManager:
    """Управление состояниями файлов на этапах обработки."""
    
    def __init__(self):
        self.metadata_file = DETECTED_DIR / "metadata.json"
        self.ready_file = READY_DIR / "units.json"
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Создает необходимые директории."""
        for d in [DETECTED_DIR, EXTRACTED_DIR, CONVERTED_DIR, NORMALIZED_DIR, READY_DIR]:
            d.mkdir(parents=True, exist_ok=True)
        
        # Создаем поддиректории для detected
        for subdir in ["pdf", "doc", "docx", "html", "image", "rtf", "excel", "unknown"]:
            (DETECTED_DIR / subdir).mkdir(parents=True, exist_ok=True)
        
        # Создаем поддиректории для архивов (zip, rar, 7z, archDOC)
        archive_base = DETECTED_DIR / "archive"
        for archive_subdir in ["zip", "rar", "7z", "archDOC"]:
            (archive_base / archive_subdir).mkdir(parents=True, exist_ok=True)
    
    def save_detected_metadata(self, file_path: Path, file_info: Dict[str, Any]) -> bool:
        """Сохраняет метаданные о файле после определения типа."""
        try:
            # Загружаем существующие метаданные
            metadata = self._load_metadata()
            
            # Добавляем информацию о файле
            file_key = str(file_path)
            metadata["files"][file_key] = {
                "file_path": str(file_path),
                "detected_type": file_info.get("detected_type", "unknown"),
                "needs_ocr": file_info.get("needs_ocr", False),
                "is_archive": file_info.get("is_archive", False),
                "mime_type": file_info.get("mime_type", ""),
                "size": file_info.get("size", file_path.stat().st_size if file_path.exists() else 0),
                "sha256": file_info.get("sha256", ""),
                "detected_at": datetime.utcnow().isoformat(),
                "state": "detected",
                "next_step": self._get_next_step(file_info)
            }
            
            # Обновляем статистику
            self._update_statistics(metadata, file_info)
            
            # Сохраняем
            return self._save_metadata(metadata)
        except Exception as e:
            print(f"Error saving detected metadata: {e}")
            return False
    
    def save_extracted_metadata(self, archive_id: str, archive_path: Path, extracted_files: List[Dict]) -> bool:
        """Сохраняет метаданные об извлеченном архиве."""
        try:
            metadata_file = EXTRACTED_DIR / archive_id / "metadata.json"
            metadata_file.parent.mkdir(parents=True, exist_ok=True)
            
            metadata = {
                "archive_id": archive_id,
                "original_file": str(archive_path),
                "extracted_at": datetime.utcnow().isoformat(),
                "extracted_files": [
                    {
                        "original_name": f.get("original_name", ""),
                        "path": f.get("path", ""),
                        "size": f.get("size", 0)
                    }
                    for f in extracted_files
                ],
                "extraction_success": True
            }
            
            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"Error saving extracted metadata: {e}")
            return False
    
    def save_converted_metadata(self, unit_id: str, original_file: Path, converted_file: Path) -> bool:
        """Сохраняет метаданные о конвертированном файле."""
        try:
            metadata_file = CONVERTED_DIR / unit_id / "metadata.json"
            metadata_file.parent.mkdir(parents=True, exist_ok=True)
            
            metadata = {
                "unit_id": unit_id,
                "original_file": str(original_file),
                "converted_file": str(converted_file),
                "converted_at": datetime.utcnow().isoformat(),
                "conversion_success": True
            }
            
            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"Error saving converted metadata: {e}")
            return False
    
    def add_ready_unit(self, unit_id: str, manifest_path: Path, route: str, files_count: int) -> bool:
        """Добавляет unit в список готовых для Docling."""
        try:
            # Загружаем существующий список
            ready_units = self._load_ready_units()
            
            # Добавляем новый unit
            ready_units["ready_units"].append({
                "unit_id": unit_id,
                "route": route,
                "files_count": files_count,
                "manifest_path": str(manifest_path),
                "ready_at": datetime.utcnow().isoformat()
            })
            
            # Обновляем статистику
            ready_units["total_ready"] = len(ready_units["ready_units"])
            ready_units["last_updated"] = datetime.utcnow().isoformat()
            
            # Сохраняем
            return self._save_ready_units(ready_units)
        except Exception as e:
            print(f"Error adding ready unit: {e}")
            return False
    
    def _load_metadata(self) -> Dict[str, Any]:
        """Загружает метаданные из файла."""
        if self.metadata_file.exists():
            with open(self.metadata_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "files": {},
            "statistics": {
                "total": 0,
                "by_type": {}
            }
        }
    
    def _save_metadata(self, metadata: Dict[str, Any]) -> bool:
        """Сохраняет метаданные в файл."""
        try:
            with open(self.metadata_file, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving metadata: {e}")
            return False
    
    def _load_ready_units(self) -> Dict[str, Any]:
        """Загружает список готовых unit'ов."""
        if self.ready_file.exists():
            with open(self.ready_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "ready_units": [],
            "total_ready": 0,
            "last_updated": datetime.utcnow().isoformat()
        }
    
    def _save_ready_units(self, ready_units: Dict[str, Any]) -> bool:
        """Сохраняет список готовых unit'ов."""
        try:
            with open(self.ready_file, "w", encoding="utf-8") as f:
                json.dump(ready_units, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving ready units: {e}")
            return False
    
    def _update_statistics(self, metadata: Dict[str, Any], file_info: Dict[str, Any]) -> None:
        """Обновляет статистику в метаданных."""
        stats = metadata.get("statistics", {"total": 0, "by_type": {}})
        stats["total"] = len(metadata.get("files", {}))
        
        by_type = stats.get("by_type", {})
        detected_type = file_info.get("detected_type", "unknown")
        by_type[detected_type] = by_type.get(detected_type, 0) + 1
        stats["by_type"] = by_type
    
    def _get_next_step(self, file_info: Dict[str, Any]) -> str:
        """Определяет следующий шаг обработки на основе информации о файле."""
        if file_info.get("is_archive") or file_info.get("is_fake_doc"):
            return "extract_archive"
        elif file_info.get("requires_conversion"):
            return "convert_doc"
        else:
            return "normalize"
    
    def get_statistics(self) -> Dict[str, Any]:
        """Возвращает статистику по всем этапам."""
        metadata = self._load_metadata()
        ready_units = self._load_ready_units()
        
        # Подсчитываем файлы на каждом этапе
        detected_count = len(metadata.get("files", {}))
        
        # Подсчитываем архивы
        extracted_dirs = [d for d in EXTRACTED_DIR.iterdir() if d.is_dir()]
        extracted_count = sum(
            len(list((d / "metadata.json").parent.rglob("*"))) - 1  # -1 для metadata.json
            for d in extracted_dirs
            if (d / "metadata.json").exists()
        )
        
        # Подсчитываем конвертированные
        converted_dirs = [d for d in CONVERTED_DIR.iterdir() if d.is_dir()]
        converted_count = len(converted_dirs)
        
        # Подсчитываем нормализованные
        normalized_dirs = [d for d in NORMALIZED_DIR.iterdir() if d.is_dir()]
        normalized_count = len(normalized_dirs)
        
        # Подсчитываем готовые
        ready_count = ready_units.get("total_ready", 0)
        
        return {
            "detected": {
                "count": detected_count,
                "by_type": metadata.get("statistics", {}).get("by_type", {})
            },
            "extracted": {
                "count": extracted_count,
                "archives_processed": len(extracted_dirs)
            },
            "converted": {
                "count": converted_count
            },
            "normalized": {
                "count": normalized_count
            },
            "ready": {
                "count": ready_count
            }
        }


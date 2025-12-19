"""
Merger - объединение UNIT из Merge_1, Merge_2, Merge_3 в Ready2Docling.

Сборка финальных UNIT с дедупликацией и сортировкой по расширениям.
"""
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional

from ..core.manifest import load_manifest, save_manifest
from ..core.audit import get_audit_logger
from ..utils.file_ops import detect_file_type


class Merger:
    """Объединитель UNIT для финальной сборки."""

    def __init__(self):
        """Инициализирует Merger."""
        self.audit_logger = get_audit_logger()

    def collect_units(
        self,
        source_dirs: List[Path],
        target_dir: Path,
        cycle: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Собирает UNIT из нескольких источников в целевую директорию.

        Args:
            source_dirs: Список директорий источников (Merge_1, Merge_2, Merge_3)
            target_dir: Целевая директория (Ready2Docling)
            cycle: Номер цикла (опционально, для фильтрации)

        Returns:
            Словарь с результатами объединения
        """
        correlation_id = self.audit_logger.get_correlation_id()

        # Собираем все UNIT из источников
        all_units = {}  # unit_id -> {source, files, cycle}

        for source_dir in source_dirs:
            if not source_dir.exists():
                continue

            # Ищем UNIT во всех поддиректориях
            for unit_dir in source_dir.rglob("UNIT_*"):
                if unit_dir.is_dir():
                    unit_id = unit_dir.name
                    # Приоритет более поздним циклам
                    if unit_id not in all_units:
                        all_units[unit_id] = {
                            "source": source_dir.name,
                            "files": [],
                            "manifest": None,
                        }

                    # Находим файлы
                    files_dir = unit_dir / "files"
                    if files_dir.exists():
                        files = [f for f in files_dir.iterdir() if f.is_file()]
                        all_units[unit_id]["files"].extend(files)
                    else:
                        # Ищем файлы напрямую в unit_dir
                        files = [
                            f
                            for f in unit_dir.iterdir()
                            if f.is_file()
                            and f.name not in ["manifest.json", "audit.log.jsonl", "metadata.json"]
                        ]
                        all_units[unit_id]["files"].extend(files)

                    # Загружаем manifest
                    manifest_path = unit_dir / "manifest.json"
                    if manifest_path.exists() and all_units[unit_id]["manifest"] is None:
                        try:
                            all_units[unit_id]["manifest"] = load_manifest(unit_dir)
                        except Exception:
                            pass

        # Обрабатываем каждый UNIT
        processed_units = []
        errors = []

        for unit_id, unit_info in all_units.items():
            try:
                # Определяем категорию для сортировки
                files = unit_info["files"]
                if not files:
                    continue

                # Определяем тип файла (берем первый или доминирующий)
                file_types = {}
                for file_path in files:
                    detection = detect_file_type(file_path)
                    file_type = detection.get("detected_type", "unknown")
                    file_types[file_type] = file_types.get(file_type, 0) + 1

                # Определяем доминирующий тип
                if file_types:
                    dominant_type = max(file_types.items(), key=lambda x: x[1])[0]
                else:
                    dominant_type = "unknown"

                # Определяем целевую директорию с сортировкой по расширению
                target_subdir = self._get_target_subdir(dominant_type, files, target_dir)

                # Создаем директорию UNIT
                target_unit_dir = target_subdir / unit_id
                target_unit_dir.mkdir(parents=True, exist_ok=True)

                # Копируем файлы
                target_files_dir = target_unit_dir / "files"
                target_files_dir.mkdir(parents=True, exist_ok=True)

                copied_files = []
                for file_path in files:
                    target_file = target_files_dir / file_path.name
                    shutil.copy2(file_path, target_file)
                    copied_files.append(str(target_file))

                # Копируем manifest если есть
                if unit_info["manifest"]:
                    manifest = unit_info["manifest"]
                    # Обновляем состояние на READY_FOR_DOCLING
                    manifest["processing"]["final_cluster"] = unit_info["source"]
                    manifest["state_machine"]["current_state"] = "READY_FOR_DOCLING"
                    manifest["state_machine"]["final_state"] = "READY_FOR_DOCLING"
                    if "READY_FOR_DOCLING" not in manifest["state_machine"]["state_trace"]:
                        manifest["state_machine"]["state_trace"].append("READY_FOR_DOCLING")

                    save_manifest(target_unit_dir, manifest)

                processed_units.append(
                    {
                        "unit_id": unit_id,
                        "source": unit_info["source"],
                        "files_count": len(copied_files),
                        "target_dir": str(target_unit_dir),
                        "file_type": dominant_type,
                    }
                )

                # Логируем операцию
                self.audit_logger.log_event(
                    unit_id=unit_id,
                    event_type="operation",
                    operation="merge",
                    details={
                        "source": unit_info["source"],
                        "files_count": len(copied_files),
                        "target_dir": str(target_unit_dir),
                    },
                    state_before="MERGED",
                    state_after="READY_FOR_DOCLING",
                    unit_path=target_unit_dir,
                )

            except Exception as e:
                errors.append({"unit_id": unit_id, "error": str(e)})

        return {
            "units_processed": len(processed_units),
            "processed_units": processed_units,
            "errors": errors,
        }

    def _get_target_subdir(self, file_type: str, files: List[Path], base_dir: Path) -> Path:
        """
        Определяет целевую поддиректорию для UNIT на основе типа файлов.

        Args:
            file_type: Тип файла
            files: Список файлов
            base_dir: Базовая директория Ready2Docling

        Returns:
            Путь к целевой поддиректории
        """
        # Маппинг типов на директории
        type_to_dir = {
            "docx": "docx",
            "pdf": "pdf",
            "jpg": "jpg",
            "jpeg": "jpeg",
            "png": "png",
            "tiff": "tiff",
            "pptx": "pptx",
            "xlsx": "xlsx",
            "xml": "xml",
            "rtf": "rtf",
        }

        subdir_name = type_to_dir.get(file_type, "other")

        # Для PDF дополнительная сортировка на scan/text
        if file_type == "pdf":
            # Проверяем первый файл на наличие текстового слоя
            if files:
                detection = detect_file_type(files[0])
                if detection.get("needs_ocr", True):
                    subdir_name = "pdf/scan"
                else:
                    subdir_name = "pdf/text"

        return base_dir / subdir_name


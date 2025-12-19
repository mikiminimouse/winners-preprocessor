"""
ExtensionNormalizer - нормализация расширений файлов по сигнатурам.

Проверяет magic bytes и MIME, переименовывает без конвертации.
"""
from pathlib import Path
from typing import Dict, Any

from ...core.manifest import load_manifest, save_manifest, update_manifest_operation
from ...core.audit import get_audit_logger
from ...utils.file_ops import detect_file_type


class ExtensionNormalizer:
    """Нормализатор расширений файлов."""

    # Маппинг типов на расширения
    TYPE_TO_EXTENSION = {
        "pdf": ".pdf",
        "docx": ".docx",
        "doc": ".doc",
        "xlsx": ".xlsx",
        "xls": ".xls",
        "pptx": ".pptx",
        "ppt": ".ppt",
        "zip_archive": ".zip",
        "rar_archive": ".rar",
        "7z_archive": ".7z",
        "jpg": ".jpg",
        "jpeg": ".jpeg",
        "png": ".png",
        "gif": ".gif",
        "tiff": ".tiff",
        "html": ".html",
        "xml": ".xml",
        "txt": ".txt",
    }

    def __init__(self):
        """Инициализирует ExtensionNormalizer."""
        self.audit_logger = get_audit_logger()

    def normalize_extensions(self, unit_path: Path) -> Dict[str, Any]:
        """
        Нормализует расширения всех файлов в UNIT.

        Args:
            unit_path: Путь к директории UNIT

        Returns:
            Словарь с результатами нормализации
        """
        unit_id = unit_path.name
        correlation_id = self.audit_logger.get_correlation_id()

        # Загружаем manifest
        manifest_path = unit_path / "manifest.json"
        try:
            manifest = load_manifest(unit_path)
        except FileNotFoundError:
            manifest = None

        # Находим все файлы
        files = [
            f
            for f in unit_path.rglob("*")
            if f.is_file() and f.name not in ["manifest.json", "audit.log.jsonl"]
        ]

        normalized_files = []
        errors = []

        for file_path in files:
            try:
                detection = detect_file_type(file_path)
                detected_type = detection.get("detected_type")
                extension_matches = detection.get("extension_matches_content", True)

                # Если расширение не соответствует содержимому, исправляем
                if not extension_matches and detected_type in self.TYPE_TO_EXTENSION:
                    current_ext = file_path.suffix.lower()
                    correct_ext = self.TYPE_TO_EXTENSION[detected_type]

                    if current_ext != correct_ext:
                        # Переименовываем файл
                        new_name = file_path.stem + correct_ext
                        new_path = file_path.parent / new_name
                        file_path.rename(new_path)

                        normalized_files.append(
                            {
                                "original_name": file_path.name,
                                "normalized_name": new_name,
                                "original_extension": current_ext,
                                "correct_extension": correct_ext,
                                "detected_type": detected_type,
                                "original_path": str(file_path),
                                "new_path": str(new_path),
                            }
                        )

                        # Обновляем manifest
                        if manifest:
                            operation = {
                                "type": "normalize",
                                "subtype": "extension",
                                "original_extension": current_ext,
                                "correct_extension": correct_ext,
                                "detected_type": detected_type,
                                "cycle": manifest.get("processing", {}).get("current_cycle", 1),
                            }
                            manifest = update_manifest_operation(manifest, operation)
            except Exception as e:
                errors.append({"file": str(file_path), "error": str(e)})

        # Сохраняем обновленный manifest
        if manifest:
            save_manifest(unit_path, manifest)

        # Логируем операцию
        self.audit_logger.log_event(
            unit_id=unit_id,
            event_type="operation",
            operation="normalize",
            details={
                "subtype": "extension",
                "files_normalized": len(normalized_files),
                "errors": errors,
            },
            state_before=manifest.get("state_machine", {}).get("current_state") if manifest else None,
            state_after=None,
            unit_path=unit_path,
        )

        return {
            "unit_id": unit_id,
            "files_normalized": len(normalized_files),
            "normalized_files": normalized_files,
            "errors": errors,
        }


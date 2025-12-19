"""
NameNormalizer - нормализация имен файлов.

Исправляет смещённые точки, убирает двойные расширения.
НЕ меняет тип файла, только имя.
"""
import re
from pathlib import Path
from typing import Dict, Any, List

from ...core.manifest import load_manifest, save_manifest, update_manifest_operation
from ...core.audit import get_audit_logger


class NameNormalizer:
    """Нормализатор имен файлов."""

    def __init__(self):
        """Инициализирует NameNormalizer."""
        self.audit_logger = get_audit_logger()

    def normalize_names(self, unit_path: Path) -> Dict[str, Any]:
        """
        Нормализует имена всех файлов в UNIT.

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
                original_name = file_path.name
                normalized_name = self._normalize_filename(original_name)

                if normalized_name != original_name:
                    # Переименовываем файл
                    new_path = file_path.parent / normalized_name
                    file_path.rename(new_path)

                    normalized_files.append(
                        {
                            "original_name": original_name,
                            "normalized_name": normalized_name,
                            "original_path": str(file_path),
                            "new_path": str(new_path),
                        }
                    )

                    # Обновляем manifest
                    if manifest:
                        operation = {
                            "type": "normalize",
                            "subtype": "name",
                            "original_name": original_name,
                            "normalized_name": normalized_name,
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
                "subtype": "name",
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

    def _normalize_filename(self, filename: str) -> str:
        """
        Нормализует имя файла.

        Исправления:
        - Удаление двойных расширений (file.doc.docx → file.docx)
        - Исправление смещённых точек (file.doc.txt → file.doc.txt нормализация)

        Args:
            filename: Исходное имя файла

        Returns:
            Нормализованное имя файла
        """
        # Убираем двойные расширения
        # Например: file.doc.docx → file.docx
        parts = filename.rsplit(".", 2)
        if len(parts) == 3:
            name, ext1, ext2 = parts
            # Проверяем, является ли ext1 валидным расширением
            # Если да, то вероятно это двойное расширение
            common_extensions = [
                "doc",
                "docx",
                "xls",
                "xlsx",
                "ppt",
                "pptx",
                "pdf",
                "txt",
                "zip",
                "rar",
            ]
            if ext1.lower() in common_extensions:
                # Убираем первое расширение
                filename = f"{name}.{ext2}"

        return filename


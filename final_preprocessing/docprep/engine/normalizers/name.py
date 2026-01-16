"""
NameNormalizer - нормализация имен файлов.

Исправляет смещённые точки, убирает двойные расширения.
НЕ меняет тип файла, только имя.
"""
import re
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from ...core.manifest import load_manifest, save_manifest, update_manifest_operation
from ...core.audit import get_audit_logger
from ...core.state_machine import UnitState
from ...core.unit_processor import (
    move_unit_to_target,
    update_unit_state,
    determine_unit_extension,
)
from ...core.config import PROCESSING_DIR

logger = logging.getLogger(__name__)


class NameNormalizer:
    """Нормализатор имен файлов."""

    def __init__(self):
        """Инициализирует NameNormalizer."""
        self.audit_logger = get_audit_logger()

    def normalize_names(
        self,
        unit_path: Path,
        cycle: int,
        protocol_date: Optional[str] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Нормализует имена всех файлов в UNIT, перемещает UNIT и обновляет state.

        Args:
            unit_path: Путь к директории UNIT
            cycle: Номер цикла (1, 2, 3)
            protocol_date: Дата протокола для организации по датам (опционально)
            dry_run: Если True, только показывает что будет сделано

        Returns:
            Словарь с результатами нормализации:
            - unit_id: идентификатор UNIT
            - files_normalized: количество нормализованных файлов
            - normalized_files: список нормализованных файлов
            - errors: список ошибок
            - moved_to: путь к новой директории UNIT (после перемещения)
        """
        unit_id = unit_path.name
        correlation_id = self.audit_logger.get_correlation_id()

        # Загружаем manifest
        manifest_path = unit_path / "manifest.json"
        try:
            manifest = load_manifest(unit_path)
            current_cycle = manifest.get("processing", {}).get("current_cycle", cycle)
            if not protocol_date:
                protocol_date = manifest.get("protocol_date")
        except FileNotFoundError:
            manifest = None
            current_cycle = cycle
            logger.warning(f"Manifest not found for unit {unit_id}, using cycle {cycle}")

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
                    if not dry_run:
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
                            "cycle": current_cycle,
                        }
                        manifest = update_manifest_operation(manifest, operation)
            except Exception as e:
                errors.append({"file": str(file_path), "error": str(e)})
                logger.error(f"Failed to normalize name for {file_path}: {e}")

        # Сохраняем обновленный manifest
        if manifest:
            save_manifest(unit_path, manifest)

        # После нормализации имени файлы остаются в той же директории Normalize
        # (требуется также нормализация расширения через ExtensionNormalizer)
        # Определяем расширение для сортировки
        extension = determine_unit_extension(unit_path)

        # Файлы остаются в той же директории (не перемещаем)
        # ExtensionNormalizer обработает их после этого
        target_dir = unit_path

        # Логируем операцию
        self.audit_logger.log_event(
            unit_id=unit_id,
            event_type="operation",
            operation="normalize",
            details={
                "subtype": "name",
                "cycle": current_cycle,
                "files_normalized": len(normalized_files),
                "extension": extension,
                "target_directory": str(target_dir),
                "errors": errors,
            },
            state_before=manifest.get("state_machine", {}).get("current_state") if manifest else None,
            state_after=manifest.get("state_machine", {}).get("current_state") if manifest else None,  # State не меняется
            unit_path=target_dir,
        )

        return {
            "unit_id": unit_id,
            "files_normalized": len(normalized_files),
            "normalized_files": normalized_files,
            "errors": errors,
            "moved_to": str(target_dir),
            "extension": extension,
        }

    def _normalize_filename(self, filename: str) -> str:
        """
        Нормализует имя файла.

        Исправления:
        - Удаление пробелов перед точкой расширения (file. doc → file.doc)
        - Удаление множественных пробелов (file  name → file name)
        - Удаление двойных расширений (file.doc.docx → file.docx)
        - Удаление точек в начале/конце имени

        Args:
            filename: Исходное имя файла

        Returns:
            Нормализованное имя файла
        """
        import re

        # 1. Убираем пробелы перед точкой расширения
        # Паттерн: один или более пробелов перед точкой
        # Примеры: "file. doc" → "file.doc", "file  .doc" → "file.doc", "file.  doc" → "file.doc"
        filename = re.sub(r'\s+\.', '.', filename)

        # 2. Убираем множественные пробелы (заменяем на один пробел)
        filename = re.sub(r'\s+', ' ', filename)

        # 3. Убираем двойные расширения
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
                "7z",
            ]
            if ext1.lower() in common_extensions:
                # Убираем первое расширение
                filename = f"{name}.{ext2}"

        # 4. Убираем точки в начале/конце имени
        filename = filename.strip('.')

        return filename

    def normalize_unit(
        self,
        unit_path: Path,
        cycle: int,
        protocol_date: Optional[str] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Alias для normalize_names для совместимости с другими engine-компонентами.
        """
        return self.normalize_names(unit_path, cycle, protocol_date, dry_run)


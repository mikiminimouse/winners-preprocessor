"""
Converter - конвертация файлов между форматами (doc→docx, xls→xlsx и т.д.).
"""
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

from ..core.manifest import load_manifest, save_manifest, update_manifest_operation
from ..core.audit import get_audit_logger
from ..core.exceptions import OperationError, QuarantineError
from ..core.state_machine import UnitState
from ..core.unit_processor import (
    move_unit_to_target,
    update_unit_state,
    determine_unit_extension,
    get_extension_subdirectory,
)
from ..core.config import get_cycle_paths, MERGE_DIR
from ..utils.file_ops import detect_file_type

logger = logging.getLogger(__name__)


class Converter:
    """Конвертер файлов через LibreOffice."""

    # Поддерживаемые конвертации
    CONVERSION_MAP = {
        "doc": "docx",
        "xls": "xlsx",
        "ppt": "pptx",
        "rtf": "docx",
    }

    def __init__(self, libreoffice_path: str = "libreoffice"):
        """
        Инициализирует Converter.

        Args:
            libreoffice_path: Путь к LibreOffice (по умолчанию "libreoffice")
        """
        self.libreoffice_path = libreoffice_path
        self.audit_logger = get_audit_logger()

    def convert_unit(
        self,
        unit_path: Path,
        cycle: int,
        from_format: Optional[str] = None,
        to_format: Optional[str] = None,
        engine: str = "libreoffice",
        protocol_date: Optional[str] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Конвертирует все файлы в UNIT, перемещает UNIT в целевую директорию и обновляет state.

        Args:
            unit_path: Путь к директории UNIT
            cycle: Номер цикла (1, 2, 3)
            from_format: Исходный формат (опционально, определяется автоматически)
            to_format: Целевой формат (опционально, определяется автоматически)
            engine: Движок конвертации (по умолчанию "libreoffice")
            protocol_date: Дата протокола для организации по датам (опционально)
            dry_run: Если True, только показывает что будет сделано

        Returns:
            Словарь с результатами конвертации:
            - unit_id: идентификатор UNIT
            - files_converted: количество конвертированных файлов
            - files_failed: количество ошибок
            - converted_files: список конвертированных файлов
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

        # Находим файлы для конвертации
        files_to_convert = []
        all_files = [
            f for f in unit_path.rglob("*") if f.is_file() and f.name not in ["manifest.json", "audit.log.jsonl"]
        ]

        for file_path in all_files:
            detection = detect_file_type(file_path)
            detected_type = detection.get("detected_type")

            # Определяем формат конвертации
            if from_format is None:
                source_format = detected_type
            else:
                source_format = from_format

            if source_format in self.CONVERSION_MAP:
                target_format = to_format or self.CONVERSION_MAP[source_format]
                files_to_convert.append((file_path, source_format, target_format))

        if not files_to_convert:
            logger.info(f"No files to convert in unit {unit_id}")
            return {
                "unit_id": unit_id,
                "files_converted": 0,
                "files_failed": 0,
                "converted_files": [],
                "errors": [],
                "moved_to": str(unit_path),
            }

        converted_files = []
        errors = []
        target_format_used = None

        for file_path, source_format, target_format in files_to_convert:
            try:
                result = self._convert_file(file_path, source_format, target_format, engine)
                converted_files.append(result)
                target_format_used = target_format  # Используем последний целевой формат

                # Обновляем manifest
                if manifest:
                    operation = {
                        "type": "convert",
                        "from": source_format,
                        "to": target_format,
                        "cycle": current_cycle,
                        "tool": engine,
                        "original_file": str(file_path),
                        "converted_file": result.get("output_path"),
                    }
                    manifest = update_manifest_operation(manifest, operation)
            except Exception as e:
                errors.append({"file": str(file_path), "error": str(e)})
                logger.error(f"Failed to convert {file_path}: {e}")

        # Сохраняем обновленный manifest
        if manifest:
            save_manifest(unit_path, manifest)

        # Определяем следующий цикл (после конвертации переходим к следующему циклу)
        next_cycle = min(current_cycle + 1, 3)

        # Определяем расширение для сортировки (используем целевой формат после конвертации)
        extension = target_format_used if target_format_used else determine_unit_extension(unit_path)

        # Перемещаем НАПРЯМУЮ в Merge_N/Converted/ (без Processing_N+1/Direct/)
        # Правильный путь: Data/YYYY-MM-DD/Merge, а не Data/Merge/YYYY-MM-DD
        if protocol_date:
            # Если указана дата, используем структуру Data/date/Merge
            from ..core.config import DATA_BASE_DIR
            merge_base = DATA_BASE_DIR / protocol_date / "Merge"
        else:
            merge_base = MERGE_DIR
        
        cycle_paths = get_cycle_paths(current_cycle, None, merge_base, None)
        target_base_dir = cycle_paths["merge"] / "Converted"

        # Определяем новое состояние ПЕРЕД перемещением
        # Проверяем текущее состояние из manifest
        from ..core.state_machine import UnitStateMachine
        state_machine = UnitStateMachine(unit_id, manifest_path)
        current_state = state_machine.get_current_state()
        
        # Определяем целевое состояние
        if current_state == UnitState.CLASSIFIED_1:
            # Из CLASSIFIED_1 переходим в PENDING_CONVERT, затем в CLASSIFIED_2
            # Сначала переводим в PENDING_CONVERT (если не dry_run)
            if not dry_run:
                update_unit_state(
                    unit_path=unit_path,
                    new_state=UnitState.PENDING_CONVERT,
                    cycle=current_cycle,
                    operation={
                        "type": "convert",
                        "status": "pending",
                    },
                )
            # Целевое состояние после конвертации
            new_state = UnitState.CLASSIFIED_2
        elif current_state == UnitState.PENDING_CONVERT:
            # Уже в PENDING_CONVERT, переводим в CLASSIFIED_2
            new_state = UnitState.CLASSIFIED_2
        elif current_cycle == 2:
            # Для цикла 2 переходим в CLASSIFIED_3
            new_state = UnitState.CLASSIFIED_3
        else:
            # Для цикла 3 или выше - финальное состояние
            new_state = UnitState.MERGED_PROCESSED

        # Перемещаем UNIT в целевую директорию с учетом расширения
        target_dir = move_unit_to_target(
            unit_dir=unit_path,
            target_base_dir=target_base_dir,
            extension=extension,
            dry_run=dry_run,
        )

        # Обновляем state machine после перемещения (если не dry_run)
        if not dry_run:
            # Перезагружаем state machine из нового местоположения
            new_manifest_path = target_dir / "manifest.json"
            state_machine = UnitStateMachine(unit_id, new_manifest_path)
            current_state_after_move = state_machine.get_current_state()
            
            # Переходим в целевое состояние
            update_unit_state(
                unit_path=target_dir,
                new_state=new_state,
                cycle=next_cycle,
                operation={
                    "type": "convert",
                    "files_converted": len(converted_files),
                    "target_format": target_format_used,
                },
            )

        # Логируем операцию
        self.audit_logger.log_event(
            unit_id=unit_id,
            event_type="operation",
            operation="convert",
            details={
                "cycle": current_cycle,
                "files_converted": len(converted_files),
                "files_failed": len(errors),
                "target_format": target_format_used,
                "extension": extension,
                "target_directory": str(target_dir),
                "errors": errors,
            },
            state_before=manifest.get("state_machine", {}).get("current_state") if manifest else None,
            state_after=new_state.value,
            unit_path=target_dir,
        )

        return {
            "unit_id": unit_id,
            "files_converted": len(converted_files),
            "files_failed": len(errors),
            "converted_files": converted_files,
            "errors": errors,
            "moved_to": str(target_dir),
            "next_cycle": next_cycle,
            "extension": extension,
        }

    def _convert_file(
        self, file_path: Path, source_format: str, target_format: str, engine: str
    ) -> Dict[str, Any]:
        """
        Конвертирует один файл.

        Args:
            file_path: Путь к исходному файлу
            source_format: Исходный формат
            target_format: Целевой формат
            engine: Движок конвертации

        Returns:
            Словарь с результатами конвертации

        Raises:
            OperationError: Если конвертация не удалась
        """
        if engine != "libreoffice":
            raise OperationError(f"Unsupported conversion engine: {engine}", operation="convert")

        # Определяем выходной путь
        output_dir = file_path.parent
        output_name = file_path.stem + "." + target_format
        output_path = output_dir / output_name

        # Конвертация через LibreOffice в headless режиме
        try:
            cmd = [
                self.libreoffice_path,
                "--headless",
                "--convert-to",
                target_format,
                "--outdir",
                str(output_dir),
                str(file_path),
            ]

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=300  # 5 минут таймаут
            )

            if result.returncode != 0:
                raise OperationError(
                    f"LibreOffice conversion failed: {result.stderr}",
                    operation="convert",
                    operation_details={"returncode": result.returncode, "stderr": result.stderr},
                )

            # Проверяем, что выходной файл создан
            if not output_path.exists():
                raise OperationError(
                    f"Converted file not found: {output_path}",
                    operation="convert",
                )

            # Удаляем исходный файл (опционально, можно оставить)
            # file_path.unlink()

            return {
                "original_file": str(file_path),
                "output_path": str(output_path),
                "source_format": source_format,
                "target_format": target_format,
                "success": True,
            }

        except subprocess.TimeoutExpired:
            raise OperationError(
                f"Conversion timeout for {file_path}",
                operation="convert",
            )
        except Exception as e:
            raise OperationError(
                f"Conversion error: {str(e)}",
                operation="convert",
                operation_details={"exception": type(e).__name__},
            )


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

    # Поддерживаемые конвертации (source_format -> target_format)
    CONVERSION_MAP = {
        "doc": "docx",
        "xls": "xlsx",
        "ppt": "pptx",
        "rtf": "docx",
    }
    
    # Маппинг форматов для LibreOffice (target_format -> LibreOffice format string)
    # LibreOffice использует формат в виде расширения для --convert-to
    LIBREOFFICE_FORMAT_MAP = {
        "docx": "docx",
        "xlsx": "xlsx",
        "pptx": "pptx",
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
            logger.warning(f"No files to convert in unit {unit_id} - unit will not be moved to Converted")
            # Если нет файлов для конвертации, UNIT не должен перемещаться в Converted
            # Возвращаем результат без перемещения
            return {
                "unit_id": unit_id,
                "files_converted": 0,
                "files_failed": 0,
                "converted_files": [],
                "errors": [{"error": "No files found that require conversion"}],
                "moved_to": str(unit_path),  # Остается на месте
            }

        converted_files = []
        errors = []
        target_format_used = None

        for file_path, source_format, target_format in files_to_convert:
            try:
                if dry_run:
                    # В dry_run режиме только логируем
                    logger.info(f"[DRY RUN] Would convert {file_path.name} from {source_format} to {target_format}")
                    converted_files.append({
                        "original_file": str(file_path),
                        "output_path": str(file_path.parent / (file_path.stem + "." + target_format)),
                        "source_format": source_format,
                        "target_format": target_format,
                        "success": True,
                    })
                    target_format_used = target_format
                else:
                result = self._convert_file(file_path, source_format, target_format, engine)
                    if result.get("success"):
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
                        "original_file": str(file_path.name),
                        "converted_file": str(Path(result.get("output_path")).name),
                    }
                    manifest = update_manifest_operation(manifest, operation)
                    
                    # Обновляем информацию о файле в manifest
                    files = manifest.get("files", [])
                    for file_info in files:
                        if file_info.get("original_name") == file_path.name or file_info.get("current_name") == file_path.name:
                            # Обновляем current_name на конвертированный файл
                            file_info["current_name"] = Path(result.get("output_path")).name
                            file_info["detected_type"] = target_format
                            # Добавляем информацию о трансформации
                            if "transformations" not in file_info:
                                file_info["transformations"] = []
                            file_info["transformations"].append({
                                "type": "convert",
                                "from": source_format,
                                "to": target_format,
                                "cycle": current_cycle,
                            })
                            break
                    else:
                        errors.append({"file": str(file_path), "error": "Conversion failed"})
            except Exception as e:
                errors.append({"file": str(file_path), "error": str(e)})
                logger.error(f"Failed to convert {file_path}: {e}")

        # Если не было успешных конвертаций, не перемещаем UNIT
        if not converted_files and not dry_run:
            logger.warning(f"No files were successfully converted in unit {unit_id} - unit will not be moved")
            if manifest:
                save_manifest(unit_path, manifest)
            return {
                "unit_id": unit_id,
                "files_converted": 0,
                "files_failed": len(errors),
                "converted_files": [],
                "errors": errors,
                "moved_to": str(unit_path),  # Остается на месте
            }

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

        # Определяем формат для LibreOffice
        # LibreOffice использует формат в виде расширения (без точки)
        libreoffice_format = self.LIBREOFFICE_FORMAT_MAP.get(target_format, target_format)
        
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
                libreoffice_format,  # Используем правильный формат для LibreOffice
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
            # LibreOffice может создавать файл с другим именем (например, с пробелами)
            if not output_path.exists():
                # Пробуем найти файл с другим именем в той же директории
                output_dir_files = list(output_dir.glob(f"{file_path.stem}.*"))
                # Исключаем исходный файл
                output_dir_files = [f for f in output_dir_files if f.suffix.lower() != file_path.suffix.lower()]
                if output_dir_files:
                    # Берем первый найденный файл с правильным расширением
                    for found_file in output_dir_files:
                        if found_file.suffix.lower() == f".{target_format}":
                            output_path = found_file
                            break
                    else:
                        # Если не нашли с правильным расширением, берем первый
                        output_path = output_dir_files[0]
                else:
                    raise OperationError(
                        f"Converted file not found: {output_path}. LibreOffice stdout: {result.stdout[:200] if result.stdout else 'empty'}",
                        operation="convert",
                    )

            # Удаляем исходный файл после успешной конвертации
            if file_path.exists() and output_path.exists():
                try:
                    file_path.unlink()
                except Exception as e:
                    logger.warning(f"Failed to remove original file {file_path}: {e}")

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


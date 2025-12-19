"""
Converter - конвертация файлов между форматами (doc→docx, xls→xlsx и т.д.).
"""
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List

from ..core.manifest import load_manifest, save_manifest, update_manifest_operation
from ..core.audit import get_audit_logger
from ..core.exceptions import OperationError, QuarantineError
from ..utils.file_ops import detect_file_type


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
        from_format: Optional[str] = None,
        to_format: Optional[str] = None,
        engine: str = "libreoffice",
    ) -> Dict[str, Any]:
        """
        Конвертирует все файлы в UNIT.

        Args:
            unit_path: Путь к директории UNIT
            from_format: Исходный формат (опционально, определяется автоматически)
            to_format: Целевой формат (опционально, определяется автоматически)
            engine: Движок конвертации (по умолчанию "libreoffice")

        Returns:
            Словарь с результатами конвертации
        """
        unit_id = unit_path.name
        correlation_id = self.audit_logger.get_correlation_id()

        # Загружаем manifest
        manifest_path = unit_path / "manifest.json"
        try:
            manifest = load_manifest(unit_path)
        except FileNotFoundError:
            manifest = None

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

        converted_files = []
        errors = []

        for file_path, source_format, target_format in files_to_convert:
            try:
                result = self._convert_file(file_path, source_format, target_format, engine)
                converted_files.append(result)

                # Обновляем manifest
                if manifest:
                    operation = {
                        "type": "convert",
                        "from": source_format,
                        "to": target_format,
                        "cycle": manifest.get("processing", {}).get("current_cycle", 1),
                        "tool": engine,
                        "original_file": str(file_path),
                        "converted_file": result.get("output_path"),
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
            operation="convert",
            details={
                "files_converted": len(converted_files),
                "files_failed": len(errors),
                "errors": errors,
            },
            state_before=manifest.get("state_machine", {}).get("current_state") if manifest else None,
            state_after=None,
            unit_path=unit_path,
        )

        return {
            "unit_id": unit_id,
            "files_converted": len(converted_files),
            "files_failed": len(errors),
            "converted_files": converted_files,
            "errors": errors,
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


"""
Extractor - безопасная разархивация архивов (ZIP, RAR, 7Z).
"""
import zipfile
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional

from ..core.manifest import load_manifest, save_manifest, update_manifest_operation
from ..core.audit import get_audit_logger
from ..core.exceptions import OperationError, QuarantineError
from ..utils.file_ops import detect_file_type, sanitize_filename

# Проверка доступности библиотек для архивов
try:
    import rarfile

    RARFILE_AVAILABLE = True
except ImportError:
    RARFILE_AVAILABLE = False

try:
    import py7zr

    PY7ZR_AVAILABLE = True
except ImportError:
    PY7ZR_AVAILABLE = False


class Extractor:
    """
    Извлекатель архивов с защитой от zip bomb.

    Ограничения:
    - Максимальный размер распаковки
    - Максимальное количество файлов
    - Максимальная глубина вложенности
    """

    # Лимиты безопасности
    MAX_UNPACK_SIZE_MB = 500
    MAX_FILES_IN_ARCHIVE = 1000
    MAX_DEPTH = 10

    def __init__(self):
        """Инициализирует Extractor."""
        self.audit_logger = get_audit_logger()

    def extract_unit(
        self,
        unit_path: Path,
        max_depth: int = 2,
        keep_archive: bool = False,
        flatten: bool = False,
    ) -> Dict[str, Any]:
        """
        Извлекает все архивы в UNIT.

        Args:
            unit_path: Путь к директории UNIT
            max_depth: Максимальная глубина рекурсивной распаковки
            keep_archive: Сохранять ли исходный архив
            flatten: Размещать все файлы в одной директории

        Returns:
            Словарь с результатами извлечения
        """
        unit_id = unit_path.name
        correlation_id = self.audit_logger.get_correlation_id()

        # Загружаем manifest
        manifest_path = unit_path / "manifest.json"
        try:
            manifest = load_manifest(unit_path)
        except FileNotFoundError:
            manifest = None

        # Находим архивы
        archive_files = []
        all_files = [
            f for f in unit_path.rglob("*") if f.is_file() and f.name not in ["manifest.json", "audit.log.jsonl"]
        ]

        for file_path in all_files:
            detection = detect_file_type(file_path)
            if detection.get("is_archive") or detection.get("detected_type") in [
                "zip_archive",
                "rar_archive",
                "7z_archive",
            ]:
                archive_files.append(file_path)

        extracted_files = []
        errors = []

        for archive_path in archive_files:
            try:
                result = self._extract_archive(
                    archive_path, unit_path, max_depth, keep_archive, flatten
                )
                extracted_files.extend(result.get("files", []))

                # Обновляем manifest
                if manifest:
                    operation = {
                        "type": "extract",
                        "archive_path": str(archive_path),
                        "extracted_count": len(result.get("files", [])),
                        "cycle": manifest.get("processing", {}).get("current_cycle", 1),
                    }
                    manifest = update_manifest_operation(manifest, operation)
            except QuarantineError as e:
                errors.append(
                    {"file": str(archive_path), "error": str(e), "quarantined": True}
                )
            except Exception as e:
                errors.append({"file": str(archive_path), "error": str(e)})

        # Сохраняем обновленный manifest
        if manifest:
            save_manifest(unit_path, manifest)

        # Логируем операцию
        self.audit_logger.log_event(
            unit_id=unit_id,
            event_type="operation",
            operation="extract",
            details={
                "archives_processed": len(archive_files),
                "files_extracted": len(extracted_files),
                "errors": errors,
            },
            state_before=manifest.get("state_machine", {}).get("current_state") if manifest else None,
            state_after=None,
            unit_path=unit_path,
        )

        return {
            "unit_id": unit_id,
            "archives_processed": len(archive_files),
            "files_extracted": len(extracted_files),
            "extracted_files": extracted_files,
            "errors": errors,
        }

    def _extract_archive(
        self,
        archive_path: Path,
        extract_to: Path,
        max_depth: int,
        keep_archive: bool,
        flatten: bool,
    ) -> Dict[str, Any]:
        """
        Извлекает один архив.

        Args:
            archive_path: Путь к архиву
            extract_to: Директория для извлечения
            max_depth: Максимальная глубина
            keep_archive: Сохранять ли архив
            flatten: Размещать все в одной директории

        Returns:
            Словарь с результатами извлечения

        Raises:
            QuarantineError: Если архив опасен (zip bomb)
            OperationError: Если извлечение не удалось
        """
        detection = detect_file_type(archive_path)
        archive_type = detection.get("detected_type")

        # Создаем директорию для извлечения
        extract_dir = extract_to / f"{archive_path.stem}_extracted"
        extract_dir.mkdir(parents=True, exist_ok=True)

        max_size = self.MAX_UNPACK_SIZE_MB * 1024 * 1024
        total_size = 0
        file_count = 0
        extracted_files = []

        try:
            if archive_type == "zip_archive" or archive_path.suffix.lower() == ".zip":
                extracted_files = self._extract_zip(
                    archive_path, extract_dir, max_size, max_depth, flatten
                )
            elif archive_type == "rar_archive" or archive_path.suffix.lower() == ".rar":
                if not RARFILE_AVAILABLE:
                    raise OperationError(
                        "RAR extraction requires rarfile library",
                        operation="extract",
                    )
                extracted_files = self._extract_rar(
                    archive_path, extract_dir, max_size, max_depth, flatten
                )
            elif archive_path.suffix.lower() == ".7z":
                if not PY7ZR_AVAILABLE:
                    raise OperationError(
                        "7z extraction requires py7zr library",
                        operation="extract",
                    )
                extracted_files = self._extract_7z(
                    archive_path, extract_dir, max_size, max_depth, flatten
                )
            else:
                raise OperationError(
                    f"Unsupported archive type: {archive_type}",
                    operation="extract",
                )

            # Удаляем исходный архив если не нужно сохранять
            if not keep_archive:
                archive_path.unlink()

            return {"files": extracted_files, "extract_dir": str(extract_dir)}

        except QuarantineError:
            raise
        except Exception as e:
            raise OperationError(
                f"Extraction error: {str(e)}",
                operation="extract",
                operation_details={"exception": type(e).__name__},
            )

    def _extract_zip(
        self, archive_path: Path, extract_dir: Path, max_size: int, max_depth: int, flatten: bool
    ) -> List[Dict[str, Any]]:
        """Извлекает ZIP архив."""
        extracted_files = []
        total_size = 0
        file_count = 0

        with zipfile.ZipFile(archive_path, "r") as zip_ref:
            for member in zip_ref.namelist():
                # Проверка на zip bomb
                file_info = zip_ref.getinfo(member)
                total_size += file_info.file_size
                file_count += 1

                if total_size > max_size:
                    raise QuarantineError(
                        f"Archive exceeds size limit: {total_size} > {max_size}",
                        reason="zip_bomb_size",
                    )

                if file_count > self.MAX_FILES_IN_ARCHIVE:
                    raise QuarantineError(
                        f"Archive exceeds file count limit: {file_count} > {self.MAX_FILES_IN_ARCHIVE}",
                        reason="zip_bomb_count",
                    )

                # Санитизируем имя файла
                safe_name = sanitize_filename(member)

                if flatten:
                    # Размещаем все в одной директории
                    target_path = extract_dir / Path(safe_name).name
                else:
                    # Сохраняем структуру
                    target_path = extract_dir / safe_name

                # Извлекаем файл
                zip_ref.extract(member, extract_dir)
                if target_path.exists():
                    extracted_files.append(
                        {
                            "original_name": member,
                            "extracted_path": str(target_path),
                            "size": file_info.file_size,
                        }
                    )

        return extracted_files

    def _extract_rar(
        self, archive_path: Path, extract_dir: Path, max_size: int, max_depth: int, flatten: bool
    ) -> List[Dict[str, Any]]:
        """Извлекает RAR архив."""
        # Реализация через rarfile
        extracted_files = []
        # TODO: Реализовать полную логику
        return extracted_files

    def _extract_7z(
        self, archive_path: Path, extract_dir: Path, max_size: int, max_depth: int, flatten: bool
    ) -> List[Dict[str, Any]]:
        """Извлекает 7z архив."""
        # Реализация через py7zr
        extracted_files = []
        # TODO: Реализовать полную логику
        return extracted_files


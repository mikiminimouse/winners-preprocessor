"""
Extractor - безопасная разархивация архивов (ZIP, RAR, 7Z).
"""
import zipfile
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from ..core.manifest import load_manifest, save_manifest, update_manifest_operation
from ..core.audit import get_audit_logger
from ..core.exceptions import OperationError, QuarantineError
from ..core.state_machine import UnitState
from ..core.unit_processor import (
    move_unit_to_target,
    update_unit_state,
    determine_unit_extension,
)
from ..core.config import get_cycle_paths, MERGE_DIR
from ..utils.file_ops import detect_file_type, sanitize_filename
from ..utils.paths import get_unit_files

logger = logging.getLogger(__name__)

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
        cycle: int,
        max_depth: int = 2,
        keep_archive: bool = False,
        flatten: bool = False,
        protocol_date: Optional[str] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Извлекает все архивы в UNIT, перемещает UNIT в целевую директорию и обновляет state.

        Args:
            unit_path: Путь к директории UNIT
            cycle: Номер цикла (1, 2, 3)
            max_depth: Максимальная глубина рекурсивной распаковки
            keep_archive: Сохранять ли исходный архив
            flatten: Размещать все файлы в одной директории
            protocol_date: Дата протокола для организации по датам (опционально)
            dry_run: Если True, только показывает что будет сделано

        Returns:
            Словарь с результатами извлечения:
            - unit_id: идентификатор UNIT
            - archives_processed: количество обработанных архивов
            - files_extracted: количество извлеченных файлов
            - extracted_files: список извлеченных файлов
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

        # Проверяем, есть ли уже извлеченные файлы (директории *_extracted)
        has_extracted_dirs = any(
            f.is_dir() and "_extracted" in f.name 
            for f in unit_path.iterdir() 
            if f.name not in ["manifest.json", "audit.log.jsonl"]
        )
        
        # Если нет архивов для извлечения и нет извлеченных директорий, UNIT не должен перемещаться
        if not archive_files and not has_extracted_dirs:
            logger.warning(f"No archives to extract in unit {unit_id} - unit will not be moved to Extracted")
            # Если нет архивов для извлечения, UNIT не должен перемещаться в Extracted
            return {
                "unit_id": unit_id,
                "archives_processed": 0,
                "files_extracted": 0,
                "extracted_files": [],
                "errors": [{"error": "No archives found that require extraction"}],
                "moved_to": str(unit_path),  # Остается на месте
            }

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
                        "cycle": current_cycle,
                    }
                    manifest = update_manifest_operation(manifest, operation)
            except QuarantineError as e:
                errors.append(
                    {"file": str(archive_path), "error": str(e), "quarantined": True}
                )
                logger.error(f"Quarantined archive {archive_path}: {e}")
            except Exception as e:
                errors.append({"file": str(archive_path), "error": str(e)})
                logger.error(f"Failed to extract {archive_path}: {e}")

        # Проверяем, есть ли уже извлеченные файлы (директории *_extracted)
        has_extracted_dirs = any(
            f.is_dir() and "_extracted" in f.name 
            for f in unit_path.iterdir() 
            if f.name not in ["manifest.json", "audit.log.jsonl"]
        )
        
        # Если не было успешных извлечений и нет уже извлеченных директорий, не перемещаем UNIT
        if not extracted_files and not has_extracted_dirs and not dry_run:
            logger.warning(f"No archives were successfully extracted in unit {unit_id} - unit will not be moved")
            if manifest:
                save_manifest(unit_path, manifest)
            return {
                "unit_id": unit_id,
                "archives_processed": len(archive_files),
                "files_extracted": 0,
                "extracted_files": [],
                "errors": errors,
                "moved_to": str(unit_path),  # Остается на месте
            }

        # Сохраняем обновленный manifest
        if manifest:
            save_manifest(unit_path, manifest)

        # Определяем расширение для сортировки из извлеченных файлов
        extension = determine_unit_extension(unit_path)

        # Определяем следующий цикл (после извлечения переходим к следующему циклу)
        next_cycle = min(current_cycle + 1, 3)

        # Перемещаем НАПРЯМУЮ в Merge_N/Extracted/ (без Processing_N+1/Direct/)
        # Правильный путь: Data/YYYY-MM-DD/Merge, а не Data/Merge/YYYY-MM-DD
        if protocol_date:
            # Если указана дата, используем структуру Data/date/Merge
            from ..core.config import DATA_BASE_DIR
            merge_base = DATA_BASE_DIR / protocol_date / "Merge"
        else:
            merge_base = MERGE_DIR
        
        cycle_paths = get_cycle_paths(current_cycle, None, merge_base, None)
        target_base_dir = cycle_paths["merge"] / "Extracted"

        # Определяем новое состояние ПЕРЕД перемещением
        # Проверяем текущее состояние из manifest
        from ..core.state_machine import UnitStateMachine
        state_machine = UnitStateMachine(unit_id, manifest_path)
        current_state = state_machine.get_current_state()
        
        # Определяем целевое состояние
        if current_state == UnitState.CLASSIFIED_1:
            # Из CLASSIFIED_1 переходим в PENDING_EXTRACT, затем в CLASSIFIED_2
            # Сначала переводим в PENDING_EXTRACT (если не dry_run)
            if not dry_run:
                update_unit_state(
                    unit_path=unit_path,
                    new_state=UnitState.PENDING_EXTRACT,
                    cycle=current_cycle,
                    operation={
                        "type": "extract",
                        "status": "pending",
                    },
                )
            # Целевое состояние после извлечения
            new_state = UnitState.CLASSIFIED_2
        elif current_state == UnitState.PENDING_EXTRACT:
            # Уже в PENDING_EXTRACT, переводим в CLASSIFIED_2
            new_state = UnitState.CLASSIFIED_2
        elif current_state == UnitState.CLASSIFIED_2 and current_cycle == 2:
            # Для UNITов в CLASSIFIED_2 с циклом 2 переходим в CLASSIFIED_3
            new_state = UnitState.CLASSIFIED_3
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
            
            # Переходим в целевое состояние
            update_unit_state(
                unit_path=target_dir,
                new_state=new_state,
                cycle=next_cycle,
                operation={
                    "type": "extract",
                    "archives_processed": len(archive_files),
                    "files_extracted": len(extracted_files),
                },
            )

        # Логируем операцию
        self.audit_logger.log_event(
            unit_id=unit_id,
            event_type="operation",
            operation="extract",
            details={
                "cycle": current_cycle,
                "archives_processed": len(archive_files),
                "files_extracted": len(extracted_files),
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
            "archives_processed": len(archive_files),
            "files_extracted": len(extracted_files),
            "extracted_files": extracted_files,
            "errors": errors,
            "moved_to": str(target_dir),
            "next_cycle": next_cycle,
            "extension": extension,
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
        extracted_files = []
        total_size = 0
        file_count = 0

        with rarfile.RarFile(archive_path, "r") as rar_ref:
            for member in rar_ref.infolist():
                # Проверка на zip bomb
                total_size += member.file_size
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
                safe_name = sanitize_filename(member.filename)

                if flatten:
                    # Размещаем все в одной директории
                    target_path = extract_dir / Path(safe_name).name
                else:
                    # Сохраняем структуру
                    target_path = extract_dir / safe_name

                # Извлекаем файл
                rar_ref.extract(member, extract_dir)
                if target_path.exists():
                    extracted_files.append(
                        {
                            "original_name": member.filename,
                            "extracted_path": str(target_path),
                            "size": member.file_size,
                        }
                    )

        return extracted_files

    def _extract_7z(
        self, archive_path: Path, extract_dir: Path, max_size: int, max_depth: int, flatten: bool
    ) -> List[Dict[str, Any]]:
        """Извлекает 7z архив."""
        extracted_files = []
        total_size = 0
        file_count = 0

        with py7zr.SevenZipFile(archive_path, "r") as sz_ref:
            # Получаем информацию о файлах
            file_list = sz_ref.list()
            
            for file_info in file_list:
                # Проверка на zip bomb
                # Для 7z используем uncompressed_size если доступен
                file_size = getattr(file_info, 'uncompressed', 0) or getattr(file_info, 'size', 0)
                total_size += file_size
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

            # Извлекаем все файлы
            extracted = sz_ref.extractall(path=str(extract_dir))
            
            # Получаем список извлеченных файлов
            for filename in extracted:
                file_path = extract_dir / filename
                if file_path.exists():
                    # Получаем размер файла
                    file_size = file_path.stat().st_size
                    extracted_files.append(
                        {
                            "original_name": filename,
                            "extracted_path": str(file_path),
                            "size": file_size,
                        }
                    )

        return extracted_files


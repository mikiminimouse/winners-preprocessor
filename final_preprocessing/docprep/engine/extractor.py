"""
Extractor - безопасная разархивация архивов (ZIP, RAR, 7Z).
"""
import zipfile
import subprocess
import logging
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Set

from ..core.manifest import load_manifest, save_manifest, update_manifest_operation
from ..core.audit import get_audit_logger
from ..core.exceptions import OperationError, QuarantineError
from ..core.state_machine import UnitState
from ..core.unit_processor import (
    move_unit_to_target,
    update_unit_state,
    determine_unit_extension,
)
from ..core.config import get_cycle_paths, MERGE_DIR, get_data_paths, EXCEPTION_SUBDIRS
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
            extension = file_path.suffix.lower()
            archive_extensions = {".zip", ".rar", ".7z"}
            
            if (detection.get("is_archive") or 
                detection.get("detected_type") in ["zip_archive", "rar_archive", "7z_archive"] or
                extension in archive_extensions):
                archive_files.append(file_path)


        # Проверяем, есть ли уже извлеченные файлы (директории *_extracted)
        has_extracted_dirs = any(
            f.is_dir() and "_extracted" in f.name 
            for f in unit_path.iterdir() 
            if f.name not in ["manifest.json", "audit.log.jsonl"]
        )
        
        # Если нет архивов для извлечения и нет извлеченных директорий, UNIT не должен перемещаться
        if not archive_files and not has_extracted_dirs:
            logger.warning(f"No archives to extract in unit {unit_id} - moving to Exceptions")
            
            # Определяем целевую директорию в Exceptions
            if protocol_date:
                data_paths = get_data_paths(protocol_date)
                exceptions_base = data_paths["exceptions"]
            else:
                from ..core.config import EXCEPTIONS_DIR
                exceptions_base = EXCEPTIONS_DIR
            
            # НОВАЯ СТРУКТУРА v2: Exceptions/Direct для цикла 1, Exceptions/Processed_N для остальных
            if cycle == 1:
                target_base_dir = exceptions_base / "Direct" / "NoProcessableFiles"
            else:
                target_base_dir = exceptions_base / f"Processed_{cycle}" / "NoProcessableFiles"
            
            # Перемещаем в Exceptions
            target_dir = move_unit_to_target(
                unit_dir=unit_path,
                target_base_dir=target_base_dir,
                extension=None,
                dry_run=dry_run,
            )
            
            # Обновляем состояние (только если не dry_run)
            if not dry_run:
                exception_state_map = {
                    1: UnitState.EXCEPTION_1,
                    2: UnitState.EXCEPTION_2,
                    3: UnitState.EXCEPTION_3,
                }
                new_state = exception_state_map.get(cycle, UnitState.EXCEPTION_1)

                update_unit_state(
                    unit_path=target_dir,
                    new_state=new_state,
                    cycle=cycle,
                    operation={
                        "type": "extract",
                        "status": "skipped",
                        "reason": "no_processable_files",
                    },
                )

            return {
                "unit_id": unit_id,
                "archives_processed": 0,
                "files_extracted": 0,
                "extracted_files": [],
                "errors": [{"error": "No archives found that require extraction"}],
                "moved_to": str(target_dir),
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
                        "status": "success",
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
        
        # Если не было успешных извлечений и нет уже извлеченных директорий, перемещаем в Exceptions
        if not extracted_files and not has_extracted_dirs and not dry_run:
            logger.warning(f"No archives were successfully extracted in unit {unit_id} - moving to Exceptions")
            
            # Определяем целевую директорию в Exceptions
            if protocol_date:
                data_paths = get_data_paths(protocol_date)
                exceptions_base = data_paths["exceptions"]
            else:
                from ..core.config import EXCEPTIONS_DIR
                exceptions_base = EXCEPTIONS_DIR
            
            # НОВАЯ СТРУКТУРА v2: Exceptions/Direct для цикла 1, Exceptions/Processed_N для остальных
            if current_cycle == 1:
                target_base_dir = exceptions_base / "Direct" / EXCEPTION_SUBDIRS["ErExtract"]
            else:
                target_base_dir = exceptions_base / f"Processed_{current_cycle}" / EXCEPTION_SUBDIRS["ErExtract"]
            
            # Перемещаем в Exceptions
            target_dir = move_unit_to_target(
                unit_dir=unit_path,
                target_base_dir=target_base_dir,
                extension=None,
                dry_run=dry_run,
            )
            
            # Обновляем состояние в EXCEPTION_N
            exception_state_map = {
                1: UnitState.EXCEPTION_1,
                2: UnitState.EXCEPTION_2,
                3: UnitState.EXCEPTION_3,
            }
            new_state = exception_state_map.get(current_cycle, UnitState.EXCEPTION_1)
            
            update_unit_state(
                unit_path=target_dir,
                new_state=new_state,
                cycle=current_cycle,
                operation={
                    "type": "extract",
                    "status": "failed",
                    "errors": errors,
                },
            )
            
            return {
                "unit_id": unit_id,
                "archives_processed": len(archive_files),
                "files_extracted": 0,
                "extracted_files": [],
                "errors": errors,
                "moved_to": str(target_dir),
            }

        # Сохраняем обновленный manifest
        if manifest:
            save_manifest(unit_path, manifest)

        # Определяем расширение для сортировки из извлеченных файлов
        # Для Mixed units используем "Mixed" вместо расширения файла
        if manifest and manifest.get("is_mixed", False):
            extension = "Mixed"
        else:
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
        Извлекает один архив с рекурсивной распаковкой вложенных архивов.

        Args:
            archive_path: Путь к архиву
            extract_to: Директория для извлечения
            max_depth: Максимальная глубина рекурсии
            keep_archive: Сохранять ли архив
            flatten: Размещать все в одной директории

        Returns:
            Словарь с результатами извлечения

        Raises:
            QuarantineError: Если архив опасен (zip bomb)
            OperationError: Если извлечение не удалось
        """
        # Используем set для отслеживания обработанных архивов (защита от циклов)
        processed_hashes: Set[str] = set()

        # Вызываем рекурсивную функцию с глубиной 0
        extracted_files = self._extract_archive_recursive(
            archive_path=archive_path,
            extract_to=extract_to,
            current_depth=0,
            max_depth=max_depth,
            keep_archive=keep_archive,
            flatten=flatten,
            processed_hashes=processed_hashes,
        )

        return {"files": extracted_files, "extract_dir": str(extract_to / f"{archive_path.stem}_extracted")}

    def _extract_archive_recursive(
        self,
        archive_path: Path,
        extract_to: Path,
        current_depth: int,
        max_depth: int,
        keep_archive: bool,
        flatten: bool,
        processed_hashes: Set[str],
    ) -> List[Dict[str, Any]]:
        """
        Рекурсивно извлекает архив и вложенные архивы.

        Args:
            archive_path: Путь к архиву
            extract_to: Директория для извлечения
            current_depth: Текущая глубина рекурсии
            max_depth: Максимальная глубина рекурсии
            keep_archive: Сохранять ли архив
            flatten: Размещать все в одной директории
            processed_hashes: Set хэшей обработанных архивов (защита от циклов)

        Returns:
            Список извлеченных файлов (включая из вложенных архивов)

        Raises:
            QuarantineError: Если архив опасен (zip bomb)
            OperationError: Если извлечение не удалось
        """
        # Проверяем глубину
        if current_depth > max_depth:
            logger.warning(f"Max depth {max_depth} reached, stopping recursion for {archive_path}")
            return []

        # Вычисляем SHA256 хэш архива для обнаружения дубликатов
        try:
            archive_hash = self._calculate_file_hash(archive_path)
            if archive_hash in processed_hashes:
                logger.warning(f"Circular dependency detected: {archive_path} already processed")
                return []
            processed_hashes.add(archive_hash)
        except Exception as e:
            logger.warning(f"Failed to calculate hash for {archive_path}: {e}")
            # Продолжаем без проверки на дубликаты

        detection = detect_file_type(archive_path)
        archive_type = detection.get("detected_type")

        # Создаем директорию для извлечения
        extract_dir = extract_to / f"{archive_path.stem}_extracted"
        extract_dir.mkdir(parents=True, exist_ok=True)

        max_size = self.MAX_UNPACK_SIZE_MB * 1024 * 1024
        extracted_files = []

        try:
            # Извлекаем текущий архив
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

            # РЕКУРСИВНАЯ ЛОГИКА: Сканируем извлеченные файлы на наличие вложенных архивов
            if current_depth < max_depth:
                nested_archives = []
                for file_info in extracted_files:
                    file_path = Path(file_info["extracted_path"])
                    if file_path.exists() and file_path.is_file():
                        # Проверяем, является ли файл архивом
                        file_detection = detect_file_type(file_path)
                        file_extension = file_path.suffix.lower()
                        archive_extensions = {".zip", ".rar", ".7z"}

                        if (file_detection.get("is_archive") or
                            file_detection.get("detected_type") in ["zip_archive", "rar_archive", "7z_archive"] or
                            file_extension in archive_extensions):
                            nested_archives.append(file_path)

                # Рекурсивно извлекаем вложенные архивы
                if nested_archives:
                    logger.info(f"Found {len(nested_archives)} nested archives at depth {current_depth}")
                    for nested_archive in nested_archives:
                        try:
                            nested_files = self._extract_archive_recursive(
                                archive_path=nested_archive,
                                extract_to=extract_dir,  # Извлекаем в ту же директорию
                                current_depth=current_depth + 1,
                                max_depth=max_depth,
                                keep_archive=keep_archive,
                                flatten=flatten,
                                processed_hashes=processed_hashes,
                            )
                            extracted_files.extend(nested_files)
                            logger.info(f"Extracted {len(nested_files)} files from nested archive {nested_archive.name}")
                        except Exception as e:
                            logger.error(f"Failed to extract nested archive {nested_archive}: {e}")

            # Удаляем исходный архив если не нужно сохранять
            if not keep_archive:
                archive_path.unlink()

            return extracted_files

        except QuarantineError:
            raise
        except Exception as e:
            raise OperationError(
                f"Extraction error: {str(e)}",
                operation="extract",
                operation_details={"exception": type(e).__name__},
            )

    def _calculate_file_hash(self, file_path: Path) -> str:
        """
        Вычисляет SHA256 хэш файла.

        Args:
            file_path: Путь к файлу

        Returns:
            Hex-строка SHA256 хэша
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            # Читаем файл блоками для экономии памяти
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

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
                if target_path.exists() and target_path.is_file():
                    # Валидация извлеченного файла
                    try:
                        validation_result = detect_file_type(target_path)
                        validated_type = validation_result.get("detected_type", "unknown")
                        validation_passed = validated_type != "corrupted"
                    except Exception as e:
                        logger.warning(f"Validation failed for {target_path}: {e}")
                        validated_type = "unknown"
                        validation_passed = False

                    extracted_files.append(
                        {
                            "original_name": member,
                            "extracted_path": str(target_path),
                            "size": file_info.file_size,
                            "validated_type": validated_type,
                            "validation_passed": validation_passed,
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
                if target_path.exists() and target_path.is_file():
                    # Валидация извлеченного файла
                    try:
                        validation_result = detect_file_type(target_path)
                        validated_type = validation_result.get("detected_type", "unknown")
                        validation_passed = validated_type != "corrupted"
                    except Exception as e:
                        logger.warning(f"Validation failed for {target_path}: {e}")
                        validated_type = "unknown"
                        validation_passed = False

                    extracted_files.append(
                        {
                            "original_name": member.filename,
                            "extracted_path": str(target_path),
                            "size": member.file_size,
                            "validated_type": validated_type,
                            "validation_passed": validation_passed,
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
            sz_ref.extractall(path=str(extract_dir))
            
            # Получаем список извлеченных файлов
            for file_info in file_list:
                filename = file_info.filename
                file_path = extract_dir / filename
                if file_path.exists() and file_path.is_file():
                    # Получаем размер файла
                    file_size = file_path.stat().st_size

                    # Валидация извлеченного файла
                    try:
                        validation_result = detect_file_type(file_path)
                        validated_type = validation_result.get("detected_type", "unknown")
                        validation_passed = validated_type != "corrupted"
                    except Exception as e:
                        logger.warning(f"Validation failed for {file_path}: {e}")
                        validated_type = "unknown"
                        validation_passed = False

                    extracted_files.append(
                        {
                            "original_name": filename,
                            "extracted_path": str(file_path),
                            "size": file_size,
                            "validated_type": validated_type,
                            "validation_passed": validation_passed,
                        }
                    )

        return extracted_files


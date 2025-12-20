"""
Модуль для обработки UNIT: перемещение, создание manifest, обновление state.

Содержит функции для работы с UNIT как с атомарными единицами обработки:
- Поиск UNIT в директориях
- Перемещение UNIT между директориями с учетом сортировки по расширениям
- Создание manifest при первой классификации
- Обновление state machine при переходах
"""
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
import logging

from .config import (
    get_cycle_paths,
    get_processing_paths,
    EXCEPTIONS_DIR,
    EXTENSIONS_DIRECT,
)
from .manifest import (
    load_manifest,
    save_manifest,
    create_manifest_v2,
    update_manifest_state,
    update_manifest_operation,
)
from .state_machine import UnitStateMachine, UnitState
from .exceptions import StateTransitionError
from .audit import get_audit_logger
from ..utils.paths import find_all_units, get_unit_files, ensure_unit_structure
from ..utils.file_ops import detect_file_type, sanitize_filename

logger = logging.getLogger(__name__)


def find_unit_directory(
    unit_id: str, search_dirs: List[Path], cycle: Optional[int] = None
) -> Optional[Path]:
    """
    Находит директорию UNIT в указанных директориях.

    Args:
        unit_id: Идентификатор UNIT
        search_dirs: Список директорий для поиска
        cycle: Номер цикла (опционально, для логирования)

    Returns:
        Путь к директории UNIT или None
    """
    for search_dir in search_dirs:
        if not search_dir.exists():
            continue

        # Рекурсивный поиск UNIT
        unit_dirs = list(search_dir.rglob(unit_id))
        for unit_dir in unit_dirs:
            if unit_dir.is_dir() and unit_dir.name == unit_id:
                return unit_dir

    logger.warning(f"Unit {unit_id} not found in search directories")
    return None


def determine_unit_extension(unit_dir: Path) -> Optional[str]:
    """
    Определяет расширение файлов UNIT для сортировки.

    Использует первый файл UNIT для определения расширения на основе
    detected_type из detect_file_type().

    Args:
        unit_dir: Директория UNIT

    Returns:
        Расширение файла (без точки) или None
    """
    files = get_unit_files(unit_dir)
    if not files:
        return None

    # Берем первый файл и определяем его тип
    first_file = files[0]
    try:
        detection = detect_file_type(first_file)
        detected_type = detection.get("detected_type", "")

        # Нормализуем расширение
        if detected_type:
            # Убираем суффиксы типа "_archive"
            ext = detected_type.replace("_archive", "")
            return ext

        # Fallback: используем расширение файла
        ext = first_file.suffix.lower().lstrip(".")
        return ext if ext else None
    except Exception as e:
        logger.warning(f"Failed to detect file type for {first_file}: {e}")
        # Fallback: используем расширение файла
        ext = first_file.suffix.lower().lstrip(".")
        return ext if ext else None


def get_extension_subdirectory(
    category: str,
    classification: Optional[Dict[str, Any]] = None,
    detected_type: Optional[str] = None,
    original_extension: Optional[str] = None,
) -> Optional[str]:
    """
    Определяет поддиректорию по расширению для категории.

    Args:
        category: Категория (direct, convert, extract, normalize)
        classification: Результат классификации файла (опционально)
        detected_type: Определенный тип файла (опционально)
        original_extension: Исходное расширение (опционально)

    Returns:
        Имя поддиректории (без точки) или None
    """
    # Используем classification если доступен
    if classification:
        detected_type = classification.get("detected_type", detected_type)
        original_extension = classification.get("original_extension", original_extension)
        has_false_extension = classification.get("has_false_extension", False)

    # Определяем расширение для сортировки
    def get_extension_for_sorting():
        if not detected_type:
            return None

        # Для fake_doc используем detected_type
        if classification and classification.get("is_fake_doc"):
            return detected_type.replace("_archive", "")

        # Если есть ложное расширение, используем detected_type
        if classification and has_false_extension:
            return detected_type.replace("_archive", "")

        # Для архивов убираем суффикс "_archive"
        if detected_type.endswith("_archive"):
            return detected_type.replace("_archive", "")

        # Используем detected_type
        return detected_type

    if category == "direct":
        return get_extension_for_sorting()

    elif category == "normalize":
        # Для normalize используем исходное расширение, если оно есть и корректное
        # Это важно, так как detected_type может быть неправильным
        if original_extension:
            ext = original_extension.lstrip(".").lower()
            # Нормализуем jpeg -> jpg
            if ext == "jpeg":
                ext = "jpg"
            # Проверяем, что это поддерживаемое расширение для normalize
            normalize_extensions = {"docx", "pdf", "xlsx", "pptx", "rtf", "jpg", "jpeg", "png", "tiff", "xml", "txt", "doc"}
            if ext in normalize_extensions:
                return ext
        # Если original_extension не передан или не поддерживается, используем detected_type
        if detected_type:
            # Нормализуем jpeg -> jpg
            normalized = detected_type.replace("_archive", "")
            if normalized == "jpeg":
                normalized = "jpg"
            return normalized
        return None

    elif category == "convert":
        # Для convert ВСЕГДА используем исходное расширение файла, а не detected_type
        # Это важно, так как detected_type может быть неправильным (например, doc определяется как xls)
        if original_extension:
            ext = original_extension.lstrip(".")
            return ext if ext else None
        # Если original_extension не передан, пытаемся получить из classification
        if classification:
            file_path = classification.get("file_path")
            if file_path:
                from pathlib import Path
                ext = Path(file_path).suffix.lower().lstrip(".")
                return ext if ext else None
        # Fallback: используем detected_type только если нет другого выбора
        return detected_type.replace("_archive", "") if detected_type else None

    elif category == "extract":
        # Для архивов ВСЕГДА используем исходное расширение файла
        # Это важно, так как detected_type может быть неправильным
        if original_extension:
            ext = original_extension.lstrip(".").lower()
            # Проверяем, что это действительно архив
            archive_extensions = {"zip", "rar", "7z"}
            if ext in archive_extensions:
                return ext
        # Если original_extension не передан или не архив, используем detected_type
        if detected_type:
            archive_type_map = {
                "zip_archive": "zip",
                "rar_archive": "rar",
                "7z_archive": "7z",
            }
            return archive_type_map.get(detected_type, detected_type.replace("_archive", ""))
        return None

    return None


def move_unit_to_target(
    unit_dir: Path,
    target_base_dir: Path,
    extension: Optional[str] = None,
    dry_run: bool = False,
    copy_mode: bool = False,
) -> Path:
    """
    Перемещает или копирует UNIT в целевую директорию с учетом сортировки по расширениям.

    Args:
        unit_dir: Текущая директория UNIT
        target_base_dir: Базовая целевая директория
        extension: Расширение для создания поддиректории (опционально)
        dry_run: Если True, только создает директорию, но не перемещает/копирует
        copy_mode: Если True, копирует вместо перемещения (сохраняет исходные файлы)

    Returns:
        Путь к новой директории UNIT
    """
    unit_id = unit_dir.name

    # Определяем целевую директорию с учетом расширения
    if extension:
        target_dir = target_base_dir / extension / unit_id
    else:
        target_dir = target_base_dir / unit_id

    # Создаем целевую директорию
    target_dir.parent.mkdir(parents=True, exist_ok=True)

    if dry_run:
        action = "copy" if copy_mode else "move"
        logger.info(f"[DRY RUN] Would {action} {unit_dir} -> {target_dir}")
        return target_dir

    # Перемещаем или копируем UNIT
    if target_dir.exists() and target_dir != unit_dir:
        logger.warning(f"Target directory exists, removing: {target_dir}")
        shutil.rmtree(target_dir)

    if unit_dir != target_dir:
        if copy_mode:
            logger.info(f"Copying unit {unit_id}: {unit_dir} -> {target_dir}")
            shutil.copytree(str(unit_dir), str(target_dir), dirs_exist_ok=True)
            # При копировании не очищаем исходную директорию
        else:
            logger.info(f"Moving unit {unit_id}: {unit_dir} -> {target_dir}")
            shutil.move(str(unit_dir), str(target_dir))
            # Очищаем пустые директории после перемещения
            _cleanup_empty_directories(unit_dir)
    else:
        logger.debug(f"Unit {unit_id} already at target location: {target_dir}")

    return target_dir


def _cleanup_empty_directories(path: Path) -> None:
    """
    Рекурсивно удаляет пустые директории начиная с указанного пути.
    
    Args:
        path: Путь к директории для очистки
    """
    try:
        # Проверяем родительские директории
        current = path
        while current and current.exists():
            parent = current.parent
            # Не удаляем базовые директории (Input, Processing, Merge и т.д.)
            if parent.name in ["Input", "Processing", "Merge", "Exceptions", "Ready2Docling"]:
                break
            # Не удаляем директории с датами (YYYY-MM-DD)
            if len(current.name) == 10 and current.name.count("-") == 2:
                break
            # Проверяем, пуста ли директория
            try:
                if current.exists() and current.is_dir():
                    # Проверяем, есть ли файлы или поддиректории
                    items = list(current.iterdir())
                    if not items:
                        logger.debug(f"Removing empty directory: {current}")
                        current.rmdir()
                        current = parent
                    else:
                        break
                else:
                    break
            except OSError:
                # Директория не пуста или есть проблемы с доступом
                break
    except Exception as e:
        logger.warning(f"Failed to cleanup empty directories for {path}: {e}")


def create_unit_manifest_if_needed(
    unit_path: Path,
    unit_id: str,
    protocol_id: Optional[str] = None,
    protocol_date: Optional[str] = None,
    files: Optional[List[Dict[str, Any]]] = None,
    cycle: int = 1,
    source_urls: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Создает manifest для UNIT, если он еще не существует.

    Args:
        unit_path: Путь к директории UNIT
        unit_id: Идентификатор UNIT
        protocol_id: ID протокола (опционально)
        protocol_date: Дата протокола (опционально)
        files: Список файлов UNIT (опционально)
        cycle: Номер цикла (по умолчанию 1)
        source_urls: Список URL источников (опционально)

    Returns:
        Словарь с manifest данными
    """
    manifest_path = unit_path / "manifest.json"

    # Если manifest уже существует, загружаем его
    if manifest_path.exists():
        try:
            return load_manifest(unit_path)
        except Exception as e:
            logger.warning(f"Failed to load existing manifest: {e}, creating new one")

    # Создаем новый manifest
    # Если files не предоставлены, собираем информацию из файлов в UNIT
    if files is None:
        unit_files = get_unit_files(unit_path)
        files = []
        for file_path in unit_files:
            try:
                detection = detect_file_type(file_path)
                files.append({
                    "original_name": file_path.name,
                    "current_name": file_path.name,
                    "mime_type": detection.get("mime_type", ""),
                    "detected_type": detection.get("detected_type", "unknown"),
                    "needs_ocr": detection.get("needs_ocr", False),
                    "transformations": [],
                })
            except Exception as e:
                logger.warning(f"Failed to detect file type for {file_path}: {e}")

    # Создаем manifest v2
    manifest = create_manifest_v2(
        unit_id=unit_id,
        protocol_id=protocol_id,
        protocol_date=protocol_date,
        files=files,
        current_cycle=cycle,
        state_trace=["RAW"],
        source_urls=source_urls or [],
    )

    # Сохраняем manifest
    save_manifest(unit_path, manifest)

    logger.info(f"Created manifest for unit {unit_id} at {manifest_path}")
    return manifest


def update_unit_state(
    unit_path: Path,
    new_state: UnitState,
    cycle: int,
    operation: Optional[Dict[str, Any]] = None,
    final_cluster: Optional[str] = None,
    final_reason: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Обновляет state machine UNIT и сохраняет изменения в manifest.

    Args:
        unit_path: Путь к директории UNIT
        new_state: Новое состояние UNIT
        cycle: Номер цикла
        operation: Информация об операции (опционально)
        final_cluster: Финальный кластер (опционально)
        final_reason: Причина попадания в финальный кластер (опционально)

    Returns:
        Обновленный manifest

    Raises:
        StateTransitionError: Если переход не разрешен
    """
    manifest_path = unit_path / "manifest.json"

    # Загружаем manifest
    try:
        manifest = load_manifest(unit_path)
    except FileNotFoundError:
        logger.error(f"Manifest not found for unit {unit_path.name}")
        raise

    # Создаем state machine и проверяем переход
    state_machine = UnitStateMachine(unit_path.name, manifest_path)

    if not state_machine.can_transition_to(new_state):
        current_state = state_machine.get_current_state()
        raise StateTransitionError(
            f"Invalid transition from {current_state} to {new_state} for unit {unit_path.name}"
        )

    # Выполняем переход
    state_machine.transition(new_state)

    # Обновляем manifest с новым состоянием
    manifest = update_manifest_state(
        manifest,
        new_state,
        cycle,
    )
    
    # Обновляем state_trace вручную
    manifest["state_machine"]["state_trace"] = state_machine.get_state_trace()

    # Добавляем информацию об операции, если предоставлена
    if operation:
        manifest = update_manifest_operation(manifest, operation)

    # Обновляем финальный кластер и причину, если предоставлены
    if final_cluster:
        manifest["processing"]["final_cluster"] = final_cluster
    if final_reason:
        manifest["processing"]["final_reason"] = final_reason

    # Сохраняем manifest
    save_manifest(unit_path, manifest)

    # Логируем в audit log
    audit_logger = get_audit_logger()
    audit_logger.log_event(
        unit_id=unit_path.name,
        event_type="state_transition",
        operation="update_state",
        details={
            "new_state": new_state.value,
            "cycle": cycle,
            "final_cluster": final_cluster,
            "final_reason": final_reason,
        },
        state_before=state_machine.get_state_trace()[-2] if len(state_machine.get_state_trace()) > 1 else None,
        state_after=new_state.value,
        unit_path=unit_path,  # Исправлено: передаем unit_path для сохранения лога в правильной директории
    )

    logger.info(f"Updated state for unit {unit_path.name}: {new_state.value}")
    return manifest


def process_directory_units(
    source_dir: Path,
    processor_func: Callable[[Path], Dict[str, Any]],
    recursive: bool = True,
    limit: Optional[int] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Обрабатывает все UNIT в директории, применяя функцию обработки к каждому.

    Args:
        source_dir: Директория для поиска UNIT
        processor_func: Функция для обработки одного UNIT (принимает Path к UNIT, возвращает Dict)
        recursive: Если True, выполняет рекурсивный поиск
        limit: Ограничение на количество UNIT для обработки (опционально)
        dry_run: Если True, только показывает что будет сделано

    Returns:
        Словарь с результатами обработки:
        {
            "units_processed": int,
            "units_succeeded": int,
            "units_failed": int,
            "errors": List[Dict],
            "results": List[Dict]
        }
    """
    result = {
        "units_processed": 0,
        "units_succeeded": 0,
        "units_failed": 0,
        "errors": [],
        "results": [],
    }

    # Находим все UNIT в директории
    units = find_all_units(source_dir, recursive=recursive)
    if limit:
        units = units[:limit]

    logger.info(f"Found {len(units)} units in {source_dir}")

    # Обрабатываем каждый UNIT
    for unit_dir in units:
        unit_id = unit_dir.name
        result["units_processed"] += 1

        try:
            logger.info(f"Processing unit {unit_id} ({result['units_processed']}/{len(units)})")
            unit_result = processor_func(unit_dir)
            result["units_succeeded"] += 1
            result["results"].append({
                "unit_id": unit_id,
                "status": "success",
                "result": unit_result,
            })
        except Exception as e:
            result["units_failed"] += 1
            error_info = {
                "unit_id": unit_id,
                "error": str(e),
                "unit_path": str(unit_dir),
            }
            result["errors"].append(error_info)
            logger.error(f"Failed to process unit {unit_id}: {e}", exc_info=True)

    logger.info(
        f"Processing completed: {result['units_succeeded']} succeeded, "
        f"{result['units_failed']} failed out of {result['units_processed']} total"
    )

    return result


"""
Конфигурация путей и директорий для preprocessing системы.

Все пути настраиваются через переменные окружения.
Поддерживает структуру с датами согласно PRD.
"""
import os
from pathlib import Path
from typing import Dict, Optional, List


# ============================================================================
# БАЗОВЫЕ ДИРЕКТОРИИ (настраиваются через env)
# ============================================================================

# Базовая директория Data (может быть переопределена через env)
DATA_BASE_DIR = Path(os.environ.get("DATA_BASE_DIR", "./Data"))

# Базовые директории относительно DATA_BASE_DIR
INPUT_DIR = DATA_BASE_DIR / "Input"
PROCESSING_DIR = DATA_BASE_DIR / "Processing"
MERGE_DIR = DATA_BASE_DIR / "Merge"
READY2DOCLING_DIR = DATA_BASE_DIR / "Ready2Docling"
EXCEPTIONS_DIR = DATA_BASE_DIR / "Exceptions"  # Отдельная директория, аналогично Merge

# Максимальное количество циклов обработки
MAX_CYCLES = 3

# Поддерживаемые расширения для сортировки
EXTENSIONS_CONVERT = ["doc", "xls", "ppt", "rtf"]
EXTENSIONS_ARCHIVES = ["zip", "rar", "7z"]
EXTENSIONS_DIRECT = ["docx", "jpeg", "jpg", "pdf", "png", "pptx", "rtf", "tiff", "xlsx", "xml"]
EXTENSIONS_NORMALIZE = EXTENSIONS_DIRECT  # Те же расширения для нормализации


def get_cycle_paths(cycle: int, processing_base: Optional[Path] = None, merge_base: Optional[Path] = None, exceptions_base: Optional[Path] = None) -> Dict[str, Path]:
    """
    Получает пути для указанного цикла обработки.

    Args:
        cycle: Номер цикла (1, 2, 3)
        processing_base: Базовая директория для Processing (по умолчанию PROCESSING_DIR)
        merge_base: Базовая директория для Merge (по умолчанию MERGE_DIR)
        exceptions_base: Базовая директория для Exceptions (по умолчанию EXCEPTIONS_DIR)

    Returns:
        Словарь с путями:
        - pending: Pending_N директория
        - merge: Merge_N директория
        - exceptions: Exceptions_N директория
    """
    if cycle < 1 or cycle > MAX_CYCLES:
        raise ValueError(f"Cycle must be between 1 and {MAX_CYCLES}, got {cycle}")

    if processing_base is None:
        processing_base = PROCESSING_DIR
    if merge_base is None:
        merge_base = MERGE_DIR
    if exceptions_base is None:
        exceptions_base = EXCEPTIONS_DIR

    return {
        "pending": processing_base / f"Pending_{cycle}",
        "merge": merge_base / f"Merge_{cycle}",
        "exceptions": exceptions_base / f"Exceptions_{cycle}",
    }


def get_pending_paths(cycle: int, processing_base: Optional[Path] = None) -> Dict[str, Path]:
    """
    Получает пути поддиректорий для Pending_N цикла.

    Args:
        cycle: Номер цикла (1, 2, 3)
        processing_base: Базовая директория для Processing (по умолчанию PROCESSING_DIR)

    Returns:
        Словарь с путями:
        - convert: директория для конвертации
        - extract: директория для разархивации (archives)
        - normalize: директория для нормализации
        - direct: директория для прямых файлов
    """
    if processing_base is None:
        processing_base = PROCESSING_DIR
    
    pending_dir = processing_base / f"Pending_{cycle}"

    return {
        "convert": pending_dir / "convert",
        "extract": pending_dir / "archives",
        "normalize": pending_dir / "normalize",
        "direct": pending_dir / "direct",
    }


def init_directory_structure(base_dir: Optional[Path] = None, date: Optional[str] = None) -> None:
    """
    Инициализирует полную структуру директорий для обработки согласно PRD.

    Создает все необходимые директории для циклов обработки с поддиректориями по расширениям.
    Если указана дата, создает структуру для конкретной даты.

    Args:
        base_dir: Базовая директория (по умолчанию DATA_BASE_DIR)
        date: Дата в формате YYYY-MM-DD (опционально)
    """
    if base_dir is None:
        base_dir = DATA_BASE_DIR

    # Создаем базовые директории
    input_base = INPUT_DIR
    processing_base = PROCESSING_DIR
    merge_base = MERGE_DIR
    exceptions_base = EXCEPTIONS_DIR
    ready_base = READY2DOCLING_DIR

    # Если указана дата, добавляем её в путь
    if date:
        processing_base = processing_base / date
        merge_base = merge_base / date
        exceptions_base = exceptions_base / date
        ready_base = ready_base / date
        input_base = input_base / date

    # Создаем базовые директории
    input_base.mkdir(parents=True, exist_ok=True)
    ready_base.mkdir(parents=True, exist_ok=True)

    # Создаем директории для каждого цикла
    for cycle in range(1, MAX_CYCLES + 1):
        # Processing/Pending_N структура
        pending_dir = processing_base / f"Pending_{cycle}"
        pending_paths = get_pending_paths(cycle, processing_base)

        # Создаем поддиректории Pending с сортировкой по расширениям
        # convert/ - по исходным расширениям
        for ext in EXTENSIONS_CONVERT:
            (pending_paths["convert"] / ext).mkdir(parents=True, exist_ok=True)

        # archives/ - по типам архивов
        for ext in EXTENSIONS_ARCHIVES:
            (pending_paths["extract"] / ext).mkdir(parents=True, exist_ok=True)

        # direct/ - по расширениям готовых файлов
        for ext in EXTENSIONS_DIRECT:
            (pending_paths["direct"] / ext).mkdir(parents=True, exist_ok=True)

        # normalize/ - по целевым расширениям
        for ext in EXTENSIONS_NORMALIZE:
            (pending_paths["normalize"] / ext).mkdir(parents=True, exist_ok=True)

        # Exceptions/Exceptions_N структура (отдельная директория, аналогично Merge)
        exceptions_dir = exceptions_base / f"Exceptions_{cycle}"
        for subdir in ["special", "mixed", "unknown"]:
            (exceptions_dir / subdir).mkdir(parents=True, exist_ok=True)

        # Merge_N структура
        merge_cycle_dir = merge_base / f"Merge_{cycle}"

        if cycle == 1:
            # Merge_1 содержит только direct/
            direct_dir = merge_cycle_dir / "direct"
            for ext in EXTENSIONS_DIRECT:
                (direct_dir / ext).mkdir(parents=True, exist_ok=True)
        else:
            # Merge_2 и Merge_3 содержат extracted/, converted/, normalized/
            for category in ["extracted", "converted", "normalized"]:
                category_dir = merge_cycle_dir / category
                for ext in EXTENSIONS_DIRECT:
                    (category_dir / ext).mkdir(parents=True, exist_ok=True)

    # Ready2Docling структура с поддиректориями по расширениям
    for ext in EXTENSIONS_DIRECT:
        ext_dir = ready_base / ext
        ext_dir.mkdir(parents=True, exist_ok=True)

        # Для PDF дополнительно создаем scan/ и text/
        if ext == "pdf":
            (ext_dir / "scan").mkdir(parents=True, exist_ok=True)
            (ext_dir / "text").mkdir(parents=True, exist_ok=True)


def get_data_paths(date: Optional[str] = None) -> Dict[str, Path]:
    """
    Получает все базовые пути для работы с данными.

    Args:
        date: Дата в формате YYYY-MM-DD (опционально)

    Returns:
        Словарь с путями:
        - input: Input директория
        - processing: Processing директория
        - merge: Merge директория
        - exceptions: Exceptions директория
        - ready2docling: Ready2Docling директория
    """
    paths = {
        "input": INPUT_DIR,
        "processing": PROCESSING_DIR,
        "merge": MERGE_DIR,
        "exceptions": EXCEPTIONS_DIR,
        "ready2docling": READY2DOCLING_DIR,
    }

    if date:
        for key in paths:
            paths[key] = paths[key] / date

    return paths


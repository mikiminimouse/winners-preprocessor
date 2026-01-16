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
# Используем абсолютный путь относительно проекта для избежания проблем с относительными путями
_default_data_dir = Path(__file__).parent.parent.parent / "Data"
DATA_BASE_DIR = Path(os.environ.get("DATA_BASE_DIR", str(_default_data_dir.resolve())))

# Базовые директории относительно DATA_BASE_DIR
INPUT_DIR = DATA_BASE_DIR / "Input"
PROCESSING_DIR = DATA_BASE_DIR / "Processing"
MERGE_DIR = DATA_BASE_DIR / "Merge"
READY2DOCLING_DIR = DATA_BASE_DIR / "Ready2Docling"
EXCEPTIONS_DIR = DATA_BASE_DIR / "Exceptions"  # Отдельная директория, аналогично Merge
ER_MERGE_DIR = DATA_BASE_DIR / "ErMerge"  # Директория для ошибок при финальном merge

# Максимальное количество циклов обработки
MAX_CYCLES = 3

# Поддерживаемые расширения для сортировки
EXTENSIONS_CONVERT = ["doc", "xls", "ppt", "rtf"]
EXTENSIONS_ARCHIVES = ["zip", "rar", "7z"]
EXTENSIONS_DIRECT = ["docx", "jpeg", "jpg", "pdf", "png", "pptx", "rtf", "tiff", "xlsx", "xml"]
EXTENSIONS_NORMALIZE = EXTENSIONS_DIRECT  # Те же расширения для нормализации

# Поддиректории для Exceptions
EXCEPTION_SUBDIRS = {
    "Empty": "Empty",
    "Special": "Special",
    "Ambiguous": "Ambiguous",
    "Mixed": "Mixed",
    "ErConvert": "ErConvert",
    "ErExtract": "ErExtract",  # ИСПРАВЛЕНО: было ErExtact
    "ErNormalize": "ErNormalize",  # ИСПРАВЛЕНО: было ErNormalaze
    "NoProcessableFiles": "NoProcessableFiles",
}


def get_cycle_paths(cycle: int, processing_base: Optional[Path] = None, merge_base: Optional[Path] = None, exceptions_base: Optional[Path] = None) -> Dict[str, Path]:
    """
    Получает пути для указанного цикла обработки.

    НОВАЯ СТРУКТУРА (v2):
    - Merge/Direct/ - для файлов готовых к Docling сразу (без обработки)
    - Merge/Processed_N/ - для файлов обработанных в цикле N
    - Exceptions/Direct/ - для исключений до обработки через Processing
    - Exceptions/Processed_N/ - для исключений после обработки в цикле N

    Args:
        cycle: Номер цикла (1, 2, 3)
        processing_base: Базовая директория для Processing (по умолчанию PROCESSING_DIR)
        merge_base: Базовая директория для Merge (по умолчанию MERGE_DIR)
        exceptions_base: Базовая директория для Exceptions (по умолчанию EXCEPTIONS_DIR)

    Returns:
        Словарь с путями:
        - processing: Processing_N директория
        - merge: Processed_N директория (для обработанных units)
        - exceptions: Processed_N директория (для исключений после обработки)
        - merge_direct: Direct директория (только для цикла 1, для прямых файлов)
        - exceptions_direct: Direct директория (только для цикла 1, для исключений до обработки)
    """
    if cycle < 1 or cycle > MAX_CYCLES:
        raise ValueError(f"Cycle must be between 1 and {MAX_CYCLES}, got {cycle}")

    if processing_base is None:
        processing_base = PROCESSING_DIR
    if merge_base is None:
        merge_base = MERGE_DIR
    if exceptions_base is None:
        exceptions_base = EXCEPTIONS_DIR

    result = {
        "processing": processing_base / f"Processing_{cycle}",
        "merge": merge_base / f"Processed_{cycle}",
        "exceptions": exceptions_base / f"Processed_{cycle}",
    }

    # Добавляем Direct директории (только для цикла 1)
    if cycle == 1:
        result["merge_direct"] = merge_base / "Direct"
        result["exceptions_direct"] = exceptions_base / "Direct"

    return result


def get_processing_paths(cycle: int, processing_base: Optional[Path] = None) -> Dict[str, Path]:
    """
    Получает пути поддиректорий для Processing_N цикла.

    Args:
        cycle: Номер цикла (1, 2, 3)
        processing_base: Базовая директория для Processing (по умолчанию PROCESSING_DIR)

    Returns:
        Словарь с путями:
        - Convert: директория для конвертации
        - Extract: директория для разархивации
        - Normalize: директория для нормализации
        Примечание: Direct НЕ возвращается, так как Direct файлы идут напрямую в Merge/Direct/
    """
    if processing_base is None:
        processing_base = PROCESSING_DIR
    
    processing_dir = processing_base / f"Processing_{cycle}"

    return {
        "Convert": processing_dir / "Convert",
        "Extract": processing_dir / "Extract",
        "Normalize": processing_dir / "Normalize",
    }


def init_directory_structure(base_dir: Optional[Path] = None, date: Optional[str] = None) -> None:
    """
    Инициализирует базовую структуру директорий для обработки.

    ВАЖНО: Создаёт только базовые директории категорий.
    Поддиректории с расширениями (doc, docx, pdf и т.д.) создаются ON-DEMAND
    при перемещении первого unit в move_unit_to_target().

    Args:
        base_dir: Базовая директория (по умолчанию DATA_BASE_DIR)
        date: Дата в формате YYYY-MM-DD (опционально)
    """
    if base_dir is None:
        base_dir = DATA_BASE_DIR

    # Если указана дата, создаем структуру внутри Data/date/
    if date:
        date_dir = base_dir / date
        date_dir.mkdir(parents=True, exist_ok=True)

        input_base = date_dir / "Input"
        processing_base = date_dir / "Processing"
        merge_base = date_dir / "Merge"
        exceptions_base = date_dir / "Exceptions"
        ready_base = date_dir / "Ready2Docling"
    else:
        input_base = INPUT_DIR
        processing_base = PROCESSING_DIR
        merge_base = MERGE_DIR
        exceptions_base = EXCEPTIONS_DIR
        ready_base = READY2DOCLING_DIR

    # Создаем только базовые директории (без поддиректорий расширений)
    input_base.mkdir(parents=True, exist_ok=True)

    # Ready2Docling создается только базовая директория
    # Поддиректории расширений создаются on-demand при перемещении units
    ready_base.mkdir(parents=True, exist_ok=True)

    # =========================================================================
    # СТРУКТУРА v3 (on-demand для расширений):
    # - Базовые директории создаются здесь
    # - Поддиректории расширений создаются автоматически при перемещении units
    # =========================================================================

    # Merge/Direct/ - базовая директория (без поддиректорий расширений)
    (merge_base / "Direct").mkdir(parents=True, exist_ok=True)

    # Exceptions/Direct/ с категориями исключений
    exceptions_direct_dir = exceptions_base / "Direct"
    for subdir in ["Empty", "Special", "Ambiguous", "Mixed", "NoProcessableFiles"]:
        (exceptions_direct_dir / subdir).mkdir(parents=True, exist_ok=True)

    # Создаем директории для каждого цикла (только базовые, без расширений)
    for cycle in range(1, MAX_CYCLES + 1):
        # Processing/Processing_N - базовые категории
        processing_paths = get_processing_paths(cycle, processing_base)
        processing_paths["Convert"].mkdir(parents=True, exist_ok=True)
        processing_paths["Extract"].mkdir(parents=True, exist_ok=True)
        processing_paths["Normalize"].mkdir(parents=True, exist_ok=True)

        # Exceptions/Processed_N с категориями исключений
        exceptions_processed_dir = exceptions_base / f"Processed_{cycle}"
        for subdir in ["Empty", "Special", "Ambiguous", "Mixed", "ErConvert", "ErNormalize", "ErExtract", "NoProcessableFiles"]:
            (exceptions_processed_dir / subdir).mkdir(parents=True, exist_ok=True)

        # Merge/Processed_N - базовые категории (без расширений)
        # ПРИМЕЧАНИЕ: Direct НЕ создаётся в Processed_N, т.к. все Direct units идут в Merge/Direct/
        merge_processed_dir = merge_base / f"Processed_{cycle}"
        for category in ["Converted", "Extracted", "Normalized", "Mixed"]:
            (merge_processed_dir / category).mkdir(parents=True, exist_ok=True)


def get_data_paths(date: Optional[str] = None) -> Dict[str, Path]:
    """
    Получает все базовые пути для работы с данными.

    Если указана дата, возвращает пути внутри Data/date/, иначе стандартные пути.

    Args:
        date: Дата в формате YYYY-MM-DD (опционально)

    Returns:
        Словарь с путями:
        - input: Input директория
        - processing: Processing директория
        - merge: Merge директория
        - exceptions: Exceptions директория
        - er_merge: ErMerge директория
        - ready2docling: Ready2Docling директория
    """
    if date:
        # Если указана дата, все категории внутри Data/date/
        date_dir = DATA_BASE_DIR / date
        return {
            "input": date_dir / "Input",
            "processing": date_dir / "Processing",
            "merge": date_dir / "Merge",
            "exceptions": date_dir / "Exceptions",
            "er_merge": date_dir / "ErMerge",
            "ready2docling": date_dir / "Ready2Docling",
        }
    else:
        # Без даты используем стандартные пути
        return {
            "input": INPUT_DIR,
            "processing": PROCESSING_DIR,
            "merge": MERGE_DIR,
            "exceptions": EXCEPTIONS_DIR,
            "er_merge": ER_MERGE_DIR,
            "ready2docling": READY2DOCLING_DIR,
        }


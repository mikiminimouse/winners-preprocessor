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
        - processing: Processing_N директория
        - merge: Merge_N директория
        - exceptions: Exceptions_N директория
        - merge_0: Merge_0 директория (только для цикла 1, для Direct файлов)
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
        "merge": merge_base / f"Merge_{cycle}",
        "exceptions": exceptions_base / f"Exceptions_{cycle}",
    }
    
    # Добавляем Merge_0 для прямых файлов (только для цикла 1)
    if cycle == 1:
        result["merge_0"] = merge_base / "Merge_0"
    
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
        Примечание: Direct НЕ возвращается, так как Direct файлы идут напрямую в Merge_0/Direct/
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
    Инициализирует полную структуру директорий для обработки согласно PRD.

    Создает все необходимые директории для циклов обработки с поддиректориями по расширениям.
    Если указана дата, создает структуру для конкретной даты внутри Data/date/.

    Args:
        base_dir: Базовая директория (по умолчанию DATA_BASE_DIR)
        date: Дата в формате YYYY-MM-DD (опционально)
    """
    if base_dir is None:
        base_dir = DATA_BASE_DIR

    # Если указана дата, создаем структуру внутри Data/date/
    if date:
        # Создаем директорию с датой
        date_dir = base_dir / date
        date_dir.mkdir(parents=True, exist_ok=True)
        
        # Все категории внутри директории с датой
        input_base = date_dir / "Input"
        processing_base = date_dir / "Processing"
        merge_base = date_dir / "Merge"
        exceptions_base = date_dir / "Exceptions"
        ready_base = date_dir / "Ready2Docling"
    else:
        # Без даты используем стандартные пути
        input_base = INPUT_DIR
        processing_base = PROCESSING_DIR
        merge_base = MERGE_DIR
        exceptions_base = EXCEPTIONS_DIR
        ready_base = READY2DOCLING_DIR

    # Создаем базовые директории
    input_base.mkdir(parents=True, exist_ok=True)
    ready_base.mkdir(parents=True, exist_ok=True)

    # Создаем Merge_0/Direct/ (единственная Direct директория)
    merge_0_dir = merge_base / "Merge_0"
    direct_dir = merge_0_dir / "Direct"
    for ext in EXTENSIONS_DIRECT:
        (direct_dir / ext).mkdir(parents=True, exist_ok=True)

    # Создаем директории для каждого цикла
    for cycle in range(1, MAX_CYCLES + 1):
        # Processing/Processing_N структура
        processing_dir = processing_base / f"Processing_{cycle}"
        processing_paths = get_processing_paths(cycle, processing_base)

        # Создаем поддиректории Processing с сортировкой по расширениям
        # Direct/ НЕ создается - Direct файлы идут напрямую в Merge_0/Direct/
        
        # Convert/ - по исходным расширениям
        for ext in EXTENSIONS_CONVERT:
            (processing_paths["Convert"] / ext).mkdir(parents=True, exist_ok=True)

        # Extract/ - по типам архивов
        for ext in EXTENSIONS_ARCHIVES:
            (processing_paths["Extract"] / ext).mkdir(parents=True, exist_ok=True)

        # Normalize/ - по целевым расширениям
        for ext in EXTENSIONS_NORMALIZE:
            (processing_paths["Normalize"] / ext).mkdir(parents=True, exist_ok=True)

        # Exceptions/Exceptions_N структура (отдельная директория, аналогично Merge)
        exceptions_dir = exceptions_base / f"Exceptions_{cycle}"
        for subdir in ["Special", "Mixed", "Ambiguous", "Empty"]:
            (exceptions_dir / subdir).mkdir(parents=True, exist_ok=True)

        # Merge_N структура (Merge_1, Merge_2, Merge_3 содержат Converted, Extracted, Normalized)
        merge_cycle_dir = merge_base / f"Merge_{cycle}"
        for category in ["Converted", "Extracted", "Normalized"]:
            category_dir = merge_cycle_dir / category
            for ext in EXTENSIONS_DIRECT:
                (category_dir / ext).mkdir(parents=True, exist_ok=True)

    # Ready2Docling структура с поддиректориями по расширениям
    for ext in EXTENSIONS_DIRECT:
        ext_dir = ready_base / ext
        ext_dir.mkdir(parents=True, exist_ok=True)

        # Для PDF дополнительно создаем scan/, text/ и mixed/
        if ext == "pdf":
            (ext_dir / "scan").mkdir(parents=True, exist_ok=True)
            (ext_dir / "text").mkdir(parents=True, exist_ok=True)
            (ext_dir / "mixed").mkdir(parents=True, exist_ok=True)


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
            "ready2docling": date_dir / "Ready2Docling",
        }
    else:
        # Без даты используем стандартные пути
        return {
            "input": INPUT_DIR,
            "processing": PROCESSING_DIR,
            "merge": MERGE_DIR,
            "exceptions": EXCEPTIONS_DIR,
            "ready2docling": READY2DOCLING_DIR,
        }


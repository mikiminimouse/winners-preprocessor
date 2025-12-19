"""
Конфигурация для router микросервиса.
Загружает параметры из переменных окружения.
"""
import os
from pathlib import Path

# ============================================================================
# ДИРЕКТОРИИ
# ============================================================================

INPUT_DIR = Path(os.environ.get("INPUT_DIR", "/app/input"))
TEMP_DIR = Path(os.environ.get("TEMP_DIR", "/app/temp"))
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/app/output"))
EXTRACTED_DIR = Path(os.environ.get("EXTRACTED_DIR", "/app/extracted"))
NORMALIZED_DIR = Path(os.environ.get("NORMALIZED_DIR", "/app/normalized"))
ARCHIVE_DIR = Path(os.environ.get("ARCHIVE_DIR", "/app/archive"))

# Pending директории для промежуточной обработки
PENDING_DIR = Path(os.environ.get("PENDING_DIR", "/app/pending"))
PENDING_DIRECT_DIR = PENDING_DIR / "direct"
PENDING_NORMALIZE_DIR = PENDING_DIR / "normalize"
PENDING_CONVERT_DIR = PENDING_DIR / "convert"
PENDING_EXTRACT_DIR = PENDING_DIR / "extract"
PENDING_SPECIAL_DIR = PENDING_DIR / "special"
PENDING_MIXED_DIR = PENDING_DIR / "mixed"

# Extract sorted директории (после распаковки архивов)
EXTRACT_SORTED_DIR = Path(os.environ.get("EXTRACT_SORTED_DIR", "/app/extract_sorted"))
EXTRACT_NORMALIZE_DIR = EXTRACT_SORTED_DIR / "normalize"
EXTRACT_CONVERT_DIR = EXTRACT_SORTED_DIR / "convert"
EXTRACT_SORTED_MIXED_DIR = EXTRACT_SORTED_DIR / "mixed"

# Ready директории
READY_DOCLING_DIR = Path(os.environ.get("READY_DOCLING_DIR", "/app/ready_docling"))
READY_DIR = Path(os.environ.get("READY_DIR", "/app/ready"))

# Дополнительные директории для state_manager
DETECTED_DIR = Path(os.environ.get("DETECTED_DIR", "/app/detected"))
CONVERTED_DIR = Path(os.environ.get("CONVERTED_DIR", "/app/converted"))

# ============================================================================
# ИТЕРАТИВНЫЕ ЦИКЛЫ ОБРАБОТКИ (PRD раздел 8, 13)
# ============================================================================

# Базовая директория для обработки (Processing/)
PROCESSING_BASE_DIR = Path(os.environ.get("PROCESSING_BASE_DIR", "/app/Processing"))

# Pending директории для циклов
PENDING_1_DIR = PROCESSING_BASE_DIR / "Pending_1"
PENDING_2_DIR = PROCESSING_BASE_DIR / "Pending_2"
PENDING_3_DIR = PROCESSING_BASE_DIR / "Pending_3"

# Merge директории для циклов
MERGE_1_DIR = PROCESSING_BASE_DIR / "Merge_1"
MERGE_2_DIR = PROCESSING_BASE_DIR / "Merge_2"
MERGE_3_DIR = PROCESSING_BASE_DIR / "Merge_3"

# Exceptions директории для циклов
EXCEPTIONS_1_DIR = PROCESSING_BASE_DIR / "Exceptions_1"
EXCEPTIONS_2_DIR = PROCESSING_BASE_DIR / "Exceptions_2"
EXCEPTIONS_3_DIR = PROCESSING_BASE_DIR / "Exceptions_3"

# Максимальное количество циклов обработки
MAX_CYCLES = 3

# ============================================================================
# API КОНФИГУРАЦИЯ
# ============================================================================

DOCLING_API = os.environ.get("DOCLING_API", "http://docling:8000/process")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "secret")

# ============================================================================
# ЛИМИТЫ И ПАРАМЕТРЫ
# ============================================================================

MAX_UNPACK_SIZE_MB = int(os.environ.get("MAX_UNPACK_SIZE_MB", "500"))
MAX_FILES_IN_ARCHIVE = int(os.environ.get("MAX_FILES_IN_ARCHIVE", "1000"))
PROTOCOLS_COUNT_LIMIT = int(os.environ.get("PROTOCOLS_COUNT_LIMIT", "100"))

# ============================================================================
# MONGODB - УДАЛЕННАЯ БД (протоколы)
# ============================================================================

MONGO_SERVER = os.environ.get("MONGO_SERVER")
MONGO_USER = os.environ.get("MONGO_USER")
MONGO_PASSWORD = os.environ.get("MONGO_PASSWORD")
MONGO_SSL_CERT = os.environ.get("MONGO_SSL_CERT")
MONGO_PROTOCOLS_DB = os.environ.get("MONGO_PROTOCOLS_DB", "protocols223")
MONGO_PROTOCOLS_COLLECTION = os.environ.get("MONGO_PROTOCOLS_COLLECTION", "purchaseProtocol")

# ============================================================================
# MONGODB - ЛОКАЛЬНАЯ БД (метаданные)
# ============================================================================

MONGO_METADATA_USER = os.environ.get("MONGO_METADATA_USER", "docling_user")
MONGO_METADATA_PASSWORD = os.environ.get("MONGO_METADATA_PASSWORD", "password")
MONGO_METADATA_DB = os.environ.get("MONGO_METADATA_DB", "docling_metadata")
MONGO_METADATA_COLLECTION = os.environ.get("MONGO_METADATA_COLLECTION", "manifests")
MONGO_PROTOCOLS_COLLECTION_LOCAL = os.environ.get("MONGO_PROTOCOLS_COLLECTION_LOCAL", "protocols")
MONGO_METRICS_COLLECTION = os.environ.get("MONGO_METRICS_COLLECTION", "processing_metrics")

# ============================================================================
# HTTP ЗАГОЛОВКИ
# ============================================================================

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

# ============================================================================
# ТИПЫ ФАЙЛОВ И РАСШИРЕНИЯ
# ============================================================================

# Расширения файлов подписей
SIGNATURE_EXTENSIONS = [".sig", ".p7s", ".pem", ".cer", ".crt"]

# Неподдерживаемые расширения
UNSUPPORTED_EXTENSIONS = [".exe", ".dll", ".db", ".tmp", ".log", ".ini", ".sys", ".bat", ".sh"]

# Сложные расширения (требуют специальной обработки)
COMPLEX_EXTENSIONS = [".tar.gz", ".tar.bz2", ".tar.xz", ".docm", ".xlsm", ".pptm", ".dotx", ".xltx", ".potx"]

# Типы файлов, требующие конвертации
CONVERTIBLE_TYPES = {
    "doc": "docx",
    "xls": "xlsx",
    "ppt": "pptx"
}

# Поддерживаемые типы файлов
SUPPORTED_FILE_TYPES = [
    "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
    "rtf", "html", "xml", "jpg", "jpeg", "png", "gif", "bmp", "tiff"
]

# Типы архивов
ARCHIVE_TYPES = ["zip_archive", "rar_archive", "7z_archive"]

# ============================================================================
# ИНИЦИАЛИЗАЦИЯ ДИРЕКТОРИЙ
# ============================================================================

def init_directories():
    """Создает необходимые директории."""
    base_dirs = [
        INPUT_DIR, TEMP_DIR, OUTPUT_DIR, EXTRACTED_DIR, NORMALIZED_DIR, ARCHIVE_DIR,
        PENDING_DIR, PENDING_DIRECT_DIR, PENDING_NORMALIZE_DIR, PENDING_CONVERT_DIR,
        PENDING_EXTRACT_DIR, PENDING_SPECIAL_DIR, PENDING_MIXED_DIR,
        EXTRACT_SORTED_DIR, EXTRACT_NORMALIZE_DIR, EXTRACT_CONVERT_DIR, EXTRACT_SORTED_MIXED_DIR,
        READY_DOCLING_DIR, READY_DIR, DETECTED_DIR, CONVERTED_DIR,
        # Итеративные циклы
        PROCESSING_BASE_DIR,
        PENDING_1_DIR, PENDING_2_DIR, PENDING_3_DIR,
        MERGE_1_DIR, MERGE_2_DIR, MERGE_3_DIR,
        EXCEPTIONS_1_DIR, EXCEPTIONS_2_DIR, EXCEPTIONS_3_DIR
    ]
    for d in base_dirs:
        d.mkdir(parents=True, exist_ok=True)
    
    # Создаем поддиректории для Pending циклов
    for cycle in [1, 2, 3]:
        cycle_dirs = get_cycle_directories(cycle)
        pending_dir = cycle_dirs["pending_dir"]
        # Создаем поддиректории для категорий
        for category in ["convert", "direct", "normalize", "archives", "special", "mixed"]:
            (pending_dir / category).mkdir(parents=True, exist_ok=True)
        
        # Создаем поддиректории для Merge
        merge_dir = cycle_dirs["merge_dir"]
        if cycle == 1:
            # Merge_1 содержит только direct
            (merge_dir / "direct").mkdir(parents=True, exist_ok=True)
        else:
            # Merge_2 и Merge_3 содержат extracted, converted, normalized
            for subdir in ["extracted", "converted", "normalized"]:
                (merge_dir / subdir).mkdir(parents=True, exist_ok=True)
        
        # Создаем поддиректории для Exceptions
        exceptions_dir = cycle_dirs["exceptions_dir"]
        for subdir in ["special", "mixed", "unknown"]:
            (exceptions_dir / subdir).mkdir(parents=True, exist_ok=True)


def ensure_directories():
    """Создает все необходимые директории (алиас для совместимости)."""
    init_directories()


def get_cycle_directories(cycle: int) -> dict:
    """
    Возвращает словарь с директориями для указанного цикла обработки.
    
    Args:
        cycle: Номер цикла (1, 2, или 3)
    
    Returns:
        Словарь с ключами:
        - pending_dir: Path к Pending_N директории
        - merge_dir: Path к Merge_N директории
        - exceptions_dir: Path к Exceptions_N директории
    
    Raises:
        ValueError: Если cycle не в диапазоне 1-3
    """
    if cycle < 1 or cycle > MAX_CYCLES:
        raise ValueError(f"Cycle must be between 1 and {MAX_CYCLES}, got {cycle}")
    
    cycle_dirs = {
        1: {
            "pending_dir": PENDING_1_DIR,
            "merge_dir": MERGE_1_DIR,
            "exceptions_dir": EXCEPTIONS_1_DIR
        },
        2: {
            "pending_dir": PENDING_2_DIR,
            "merge_dir": MERGE_2_DIR,
            "exceptions_dir": EXCEPTIONS_2_DIR
        },
        3: {
            "pending_dir": PENDING_3_DIR,
            "merge_dir": MERGE_3_DIR,
            "exceptions_dir": EXCEPTIONS_3_DIR
        }
    }
    
    return cycle_dirs[cycle]


def create_false_ext_directory(base_dir: Path, detected_type: str) -> Path:
    """
    Создает директорию для файлов с ложными расширениями.
    
    Args:
        base_dir: Базовая директория (например, PENDING_DIRECT_DIR)
        detected_type: Определенный тип файла
    
    Returns:
        Path к созданной директории
    """
    false_ext_dir = base_dir / f"false_ext_{detected_type}"
    false_ext_dir.mkdir(parents=True, exist_ok=True)
    return false_ext_dir


# Инициализируем директории при импорте модуля
init_directories()


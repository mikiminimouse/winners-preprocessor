"""
Runner - тонкая обертка над DocumentConverter из Docling.

Минимум кода, максимум делегирования Docling.
"""
import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any

try:
    # Импортируем установленный пакет docling напрямую
    # ВАЖНО: Убеждаемся, что site-packages находится в начале sys.path
    import sys
    import importlib
    import site
    from pathlib import Path
    
    # Перемещаем site-packages в начало sys.path
    site_dirs = []
    for site_dir in site.getsitepackages():
        if (Path(site_dir) / 'docling' / '__init__.py').exists():
            if site_dir in sys.path:
                sys.path.remove(site_dir)
            sys.path.insert(0, site_dir)
            site_dirs.append(site_dir)
    
    # Удаляем локальный модуль docling из sys.modules, если он там есть
    _local_docling_backup = {}
    if 'docling' in sys.modules:
        mod = sys.modules['docling']
        if hasattr(mod, '__file__') and mod.__file__:
            mod_file = str(mod.__file__)
            if 'final_preprocessing' in mod_file:
                # Сохраняем локальные модули
                _local_docling_backup = {
                    k: v for k, v in sys.modules.items() 
                    if k.startswith('docling')
                }
                # Удаляем их
                for k in list(_local_docling_backup.keys()):
                    sys.modules.pop(k, None)
    
    # Импортируем установленный пакет
    document_converter_mod = importlib.import_module('docling.document_converter')
    DocumentConverter = document_converter_mod.DocumentConverter
    
    pipeline_options_mod = importlib.import_module('docling.datamodel.pipeline_options')
    PipelineOptions = pipeline_options_mod.PipelineOptions
    
    base_models_mod = importlib.import_module('docling.datamodel.base_models')
    InputFormat = base_models_mod.InputFormat
    
    DOCLING_AVAILABLE = True
except (ImportError, Exception):
    DOCLING_AVAILABLE = False
    DocumentConverter = None
    PipelineOptions = None
    InputFormat = None


# Global counter for processed units per format
PROCESSED_COUNTS = {}

def get_processed_count(format_name: str) -> int:
    """Returns the number of processed files for a given format."""
    return PROCESSED_COUNTS.get(format_name, 0)

def reset_processed_counts():
    """Resets all processed counts."""
    global PROCESSED_COUNTS
    PROCESSED_COUNTS = {}

logger = logging.getLogger(__name__)


def run_docling_conversion(
    file_path: Path,
    options: Optional[PipelineOptions] = None,
    input_format: Optional[InputFormat] = None,  # Не используется, оставлен для обратной совместимости
    max_retries: int = 1,
    retry_delay: float = 1.0,
    check_limit: bool = False,
    limit_per_format: int = 50,
) -> Optional[Any]:
    """
    Запускает конвертацию файла через DocumentConverter с поддержкой retry и лимитов.

    Args:
        file_path: Путь к файлу для обработки
        options: PipelineOptions для настройки Docling
        input_format: InputFormat (опционально, определяется автоматически)
        max_retries: Максимальное количество попыток (по умолчанию 1, без retry)
        retry_delay: Задержка между попытками в секундах
        check_limit: Проверять ли лимит обработанных файлов
        limit_per_format: Лимит файлов на один формат (по расширению)

    Returns:
        Document объект от Docling или None при ошибке или превышении лимита

    Raises:
        ImportError: Если Docling не установлен
        FileNotFoundError: Если файл не найден
        Exception: При ошибках конвертации после всех попыток
    """
    if not DOCLING_AVAILABLE:
        raise ImportError(
            "Docling not available. Install with: pip install docling>=1.0.0"
        )

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Проверка лимита (по расширению файла как прокси для формата)
    if check_limit:
        ext = file_path.suffix.lower().lstrip('.')
        current_count = PROCESSED_COUNTS.get(ext, 0)
        if current_count >= limit_per_format:
            logger.info(f"Skipping {file_path}: limit of {limit_per_format} reached for format {ext}")
            return None

    last_exception = None
    for attempt in range(max_retries + 1):
        try:
            # Создаем DocumentConverter с опциями
            # Если options=None, используем опции по умолчанию (без параметров)
            if options is not None:
                converter = DocumentConverter(options)
            else:
                # Используем опции по умолчанию
                converter = DocumentConverter()

            # Запускаем конвертацию
            if attempt > 0:
                logger.info(f"Retrying conversion (attempt {attempt + 1}/{max_retries + 1}) for {file_path}")
            else:
                logger.info(f"Converting {file_path} with Docling...")
            
            # convert() не принимает input_format как параметр, формат определяется автоматически
            document = converter.convert(str(file_path))

            # Увеличиваем счетчик обработанных файлов, если успешно
            if check_limit:
                ext = file_path.suffix.lower().lstrip('.')
                PROCESSED_COUNTS[ext] = PROCESSED_COUNTS.get(ext, 0) + 1

            logger.info(f"Successfully converted {file_path}")
            return document

        except Exception as e:
            last_exception = e
            logger.warning(f"Docling conversion failed for {file_path} (attempt {attempt + 1}/{max_retries + 1}): {e}")
            
            # Если это последняя попытка, логируем ошибку полностью
            if attempt == max_retries:
                logger.error(f"Docling conversion failed after {max_retries + 1} attempts for {file_path}: {e}", exc_info=True)
            else:
                # Ждем перед следующей попыткой
                time.sleep(retry_delay)
    
    # Если все попытки не удались, пробрасываем последнее исключение
    raise last_exception


def run_batch_conversion(
    file_paths: list[Path],
    options: Optional[PipelineOptions] = None,
    limit_per_format: int = 50,
) -> Dict[Path, Any]:
    """
    Запускает конвертацию нескольких файлов.

    Args:
        file_paths: Список путей к файлам
        options: PipelineOptions (общие для всех файлов)
        limit_per_format: Лимит файлов на один формат

    Returns:
        Словарь {file_path: document} с результатами
    """
    results = {}

    # Сбрасываем счетчики перед батчем (опционально, зависит от логики вызова)
    # Но для безопасности лучше не сбрасывать здесь, чтобы лимит работал глобально
    # reset_processed_counts() 

    for file_path in file_paths:
        try:
            document = run_docling_conversion(
                file_path, 
                options, 
                check_limit=True,
                limit_per_format=limit_per_format
            )
            if document:
                results[file_path] = document
        except Exception as e:
            logger.error(f"Failed to convert {file_path}: {e}")
            results[file_path] = None

    return results


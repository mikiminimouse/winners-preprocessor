"""
Runner - тонкая обертка над DocumentConverter из Docling.

Минимум кода, максимум делегирования Docling.
"""
import logging
import time
import threading
from pathlib import Path
from typing import Optional, Dict, Any

# Используем централизованный импорт Docling из _docling_import.py
from ._docling_import import (
    get_document_converter,
    get_pipeline_options,
    get_input_format,
    is_docling_available,
)

# Получаем классы через shared модуль
DocumentConverter = get_document_converter()
PipelineOptions = get_pipeline_options()
InputFormat = get_input_format()
DOCLING_AVAILABLE = is_docling_available()


class ProcessedCountsManager:
    """
    Потокобезопасный менеджер счетчиков обработанных файлов.

    Использует threading.Lock для защиты от race conditions
    при параллельной обработке.
    """

    def __init__(self):
        self._counts: Dict[str, int] = {}
        self._lock = threading.Lock()

    def get(self, format_name: str) -> int:
        """Возвращает количество обработанных файлов для формата."""
        with self._lock:
            return self._counts.get(format_name, 0)

    def increment(self, format_name: str) -> int:
        """Атомарно увеличивает счетчик и возвращает новое значение."""
        with self._lock:
            self._counts[format_name] = self._counts.get(format_name, 0) + 1
            return self._counts[format_name]

    def reset(self):
        """Сбрасывает все счетчики."""
        with self._lock:
            self._counts.clear()

    def get_all(self) -> Dict[str, int]:
        """Возвращает копию всех счетчиков."""
        with self._lock:
            return self._counts.copy()


# Глобальный экземпляр менеджера счетчиков
_processed_counts_manager = ProcessedCountsManager()


def get_processed_count(format_name: str) -> int:
    """Returns the number of processed files for a given format."""
    return _processed_counts_manager.get(format_name)


def reset_processed_counts():
    """Resets all processed counts."""
    _processed_counts_manager.reset()

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
        current_count = _processed_counts_manager.get(ext)
        if current_count >= limit_per_format:
            logger.info(f"Skipping {file_path}: limit of {limit_per_format} reached for format {ext}")
            return None

    last_exception = None
    for attempt in range(max_retries + 1):
        try:
            # Создаем DocumentConverter с опциями
            # Если options=None, используем опции по умолчанию (без параметров)
            if options is not None:
                # Extract format_options from PipelineOptions
                from docling.document_converter import FormatOption
                from docling.datamodel.base_models import InputFormat
                format_options = {}
                
                # Handle PDF options
                if hasattr(options, 'pdf') and options.pdf is not None:
                    format_options[InputFormat.PDF] = FormatOption(
                        pipeline_options=options.pdf,
                        pipeline_cls=None,  # Use default pipeline class
                        backend=None  # Use default backend
                    )
                
                converter = DocumentConverter(format_options=format_options)
            else:
                # Используем опции по умолчанию
                converter = DocumentConverter()

            # Логируем применяемые опции для диагностики
            if options is not None and hasattr(options, 'pdf') and options.pdf is not None:
                pdf_opts = options.pdf
                logger.info(f"PDF options applied: do_ocr={pdf_opts.do_ocr}, "
                           f"do_table_structure={pdf_opts.do_table_structure}, "
                           f"images_scale={getattr(pdf_opts, 'images_scale', 'default')}, "
                           f"generate_page_images={getattr(pdf_opts, 'generate_page_images', 'default')}")

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
                _processed_counts_manager.increment(ext)

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


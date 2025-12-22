"""
Runner - тонкая обертка над DocumentConverter из Docling.

Минимум кода, максимум делегирования Docling.
"""
import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any

try:
    from docling.document_converter import DocumentConverter
    from docling.datamodel.pipeline_options import PipelineOptions
    from docling.datamodel.base_models import InputFormat
    DOCLING_AVAILABLE = True
except ImportError:
    DOCLING_AVAILABLE = False
    DocumentConverter = None
    PipelineOptions = None
    InputFormat = None

logger = logging.getLogger(__name__)


def run_docling_conversion(
    file_path: Path,
    options: Optional[PipelineOptions] = None,
    input_format: Optional[InputFormat] = None,
    max_retries: int = 1,
    retry_delay: float = 1.0,
) -> Optional[Any]:
    """
    Запускает конвертацию файла через DocumentConverter с поддержкой retry.

    Args:
        file_path: Путь к файлу для обработки
        options: PipelineOptions для настройки Docling
        input_format: InputFormat (опционально, определяется автоматически)
        max_retries: Максимальное количество попыток (по умолчанию 1, без retry)
        retry_delay: Задержка между попытками в секундах

    Returns:
        Document объект от Docling или None при ошибке

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

    last_exception = None
    for attempt in range(max_retries + 1):
    try:
        # Создаем DocumentConverter с опциями
        if options:
            converter = DocumentConverter(options)
        else:
            # Используем опции по умолчанию
            converter = DocumentConverter()

        # Запускаем конвертацию
            if attempt > 0:
                logger.info(f"Retrying conversion (attempt {attempt + 1}/{max_retries + 1}) for {file_path}")
            else:
        logger.info(f"Converting {file_path} with Docling...")
            
        document = converter.convert(str(file_path), input_format=input_format)

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
) -> Dict[Path, Any]:
    """
    Запускает конвертацию нескольких файлов.

    Args:
        file_paths: Список путей к файлам
        options: PipelineOptions (общие для всех файлов)

    Returns:
        Словарь {file_path: document} с результатами
    """
    results = {}

    for file_path in file_paths:
        try:
            document = run_docling_conversion(file_path, options)
            if document:
                results[file_path] = document
        except Exception as e:
            logger.error(f"Failed to convert {file_path}: {e}")
            results[file_path] = None

    return results


"""
Конфигурация Docling - маппинг route → Docling PipelineOptions через YAML templates.

Использует pipeline templates из YAML файлов для конфигурации Docling,
обеспечивая воспроизводимость и версионирование конфигураций.
"""
import os
import logging
import yaml
from functools import lru_cache
from typing import Dict, Any, Optional, Tuple
from pathlib import Path

# Используем централизованный импорт Docling из _docling_import.py
from ._docling_import import (
    get_pipeline_options,
    get_pdf_pipeline_options,
    get_vlm_pipeline_options,
    get_input_format,
    is_docling_available,
)

# Получаем классы через shared модуль
PipelineOptions = get_pipeline_options()
PdfPipelineOptions = get_pdf_pipeline_options()
VlmPipelineOptions = get_vlm_pipeline_options()
InputFormat = get_input_format()
DOCLING_AVAILABLE = is_docling_available()

# Путь к директории с pipeline templates
TEMPLATES_DIR = Path(__file__).parent / "pipeline_templates"

logger = logging.getLogger(__name__)


@lru_cache(maxsize=32)
def _load_yaml_file(file_path: str) -> Optional[Tuple]:
    """
    Загружает YAML файл с кэшированием.

    Возвращает tuple для совместимости с lru_cache.
    Кэш сбрасывается только при перезапуске процесса.

    Args:
        file_path: Путь к YAML файлу

    Returns:
        Кортеж (yaml_content, mtime) или None если файл не найден
    """
    path = Path(file_path)
    if not path.exists():
        return None

    try:
        mtime = path.stat().st_mtime
        with open(path, "r", encoding="utf-8") as f:
            content = yaml.safe_load(f)
        return (content, mtime)
    except Exception as e:
        logger.error(f"Failed to load YAML file {file_path}: {e}")
        return None


def load_pipeline_template(route: str) -> Optional[Dict[str, Any]]:
    """
    Загружает pipeline template из YAML файла для указанного route.

    Использует кэширование для избежания повторного чтения с диска.

    Args:
        route: Route для загрузки шаблона

    Returns:
        Словарь с конфигурацией pipeline или None если шаблон не найден
    """
    template_path = TEMPLATES_DIR / f"{route}.yaml"

    if not template_path.exists():
        logger.warning(f"Pipeline template not found for route {route}: {template_path}")
        return None

    result = _load_yaml_file(str(template_path))
    if result is None:
        return None

    # result[0] содержит контент YAML
    return result[0]


def clear_template_cache():
    """Очищает кэш загруженных templates."""
    _load_yaml_file.cache_clear()


def build_docling_options(route: str, manifest: Optional[Dict[str, Any]] = None) -> Optional[PipelineOptions]:
    """
    Строит Docling PipelineOptions на основе route через YAML templates (приоритетно)
    или hardcoded конфигурацию (fallback).

    Args:
        route: Route из contract/manifest (pdf_text, pdf_scan, docx, xlsx, html, xml)
        manifest: Полный manifest из docprep (опционально, для обратной совместимости)

    Returns:
        PipelineOptions для DocumentConverter или None если Docling недоступен
    """
    if not DOCLING_AVAILABLE:
        return None
    
    # Пытаемся загрузить template из YAML
    template = load_pipeline_template(route)
    if template:
        return _build_options_from_template(template)
    
    # Fallback на hardcoded конфигурацию для обратной совместимости
    return _build_options_legacy(route, manifest)


def _build_options_from_template(template: Dict[str, Any]) -> PipelineOptions:
    """
    Строит PipelineOptions из YAML template.

    ВАЖНО: Применяет ВСЕ настройки из YAML, включая:
    - models.layout - модель для layout detection
    - models.tables - модель для извлечения таблиц
    - models.ocr - настройки OCR
    - docling.* - настройки извлечения (images_scale, generate_page_images и т.д.)

    Args:
        template: Словарь с конфигурацией из YAML

    Returns:
        PipelineOptions для DocumentConverter
    """
    docling_config = template.get("docling", {})
    models_config = template.get("models", {})
    route = template.get("route", "")

    # Настройки для PDF
    pdf_opts = None
    if route.startswith("pdf") or route == "image_ocr":
        pdf_opts = PdfPipelineOptions()

        # === OCR настройки ===
        ocr_setting = models_config.get("ocr")
        if ocr_setting == "tesseract" or docling_config.get("force_ocr"):
            pdf_opts.do_ocr = True
        elif ocr_setting in (None, "off", False):
            pdf_opts.do_ocr = False
        else:
            pdf_opts.do_ocr = False

        # === Table extraction настройки (КРИТИЧНО для производительности) ===
        tables_setting = models_config.get("tables")
        extract_tables_setting = docling_config.get("extract_tables")

        # Отключаем таблицы если явно указано off или extract_tables=false
        if tables_setting == "off" or extract_tables_setting is False:
            pdf_opts.do_table_structure = False
            logger.info(f"[{route}] Table extraction DISABLED (tables={tables_setting}, extract_tables={extract_tables_setting})")
        elif tables_setting is not None and tables_setting != "off":
            pdf_opts.do_table_structure = True
            logger.info(f"[{route}] Table extraction ENABLED with model: {tables_setting}")
        else:
            pdf_opts.do_table_structure = False
            logger.info(f"[{route}] Table extraction DISABLED (default)")

        # === Images scale (оптимизация памяти и скорости) ===
        if "images_scale" in docling_config:
            pdf_opts.images_scale = float(docling_config["images_scale"])
            logger.debug(f"[{route}] images_scale set to {pdf_opts.images_scale}")

        # === Generate page images ===
        if "generate_page_images" in docling_config:
            pdf_opts.generate_page_images = bool(docling_config["generate_page_images"])
            logger.debug(f"[{route}] generate_page_images set to {pdf_opts.generate_page_images}")

        # === Generate picture images ===
        if "generate_picture_images" in docling_config:
            pdf_opts.generate_picture_images = bool(docling_config["generate_picture_images"])
            logger.debug(f"[{route}] generate_picture_images set to {pdf_opts.generate_picture_images}")

        # === Layout model настройки (КРИТИЧНО для производительности) ===
        layout_setting = models_config.get("layout")
        if layout_setting == "off" or layout_setting is False:
            # Отключаем layout detection для ускорения
            # В Docling это делается через do_layout=False если такой параметр есть
            if hasattr(pdf_opts, 'do_layout'):
                pdf_opts.do_layout = False
            logger.info(f"[{route}] Layout detection DISABLED")
        elif layout_setting:
            logger.info(f"[{route}] Layout detection ENABLED with model: {layout_setting}")

        # Логируем итоговую конфигурацию
        logger.info(f"[{route}] PDF options: do_ocr={pdf_opts.do_ocr}, do_table_structure={pdf_opts.do_table_structure}")

    # Создаем PipelineOptions с pdf опциями
    if pdf_opts:
        options = PipelineOptions(pdf=pdf_opts)
    else:
        options = PipelineOptions()

    # VLM pipeline не используется для digital форматов.
    # Для OCR (pdf_scan, image_ocr) VLM будет добавлен в отдельной задаче.

    return options


def _build_options_legacy(route: str, manifest: Optional[Dict[str, Any]]) -> PipelineOptions:
    """
    Строит PipelineOptions используя legacy hardcoded логику (fallback).
    
    Args:
        route: Route для обработки
        manifest: Manifest данные (опционально)
        
    Returns:
        PipelineOptions для DocumentConverter
    """
    # Базовые опции для всех форматов
    options = PipelineOptions()

    # Маппинг route → настройки Docling
    if route == "pdf_scan":
        # PDF со сканированным содержимым - нужен OCR/VLM
        options.pdf = PdfPipelineOptions()
        options.pdf.do_ocr = True
        options.pdf.do_table_structure = True  # Извлекаем таблицы даже из сканов
        # VLM pipeline для лучшего качества OCR
        try:
            options.vlm = VlmPipelineOptions()
            # Настройка VLM endpoint если доступен
            vlm_endpoint = os.environ.get("VLM_ENDPOINT")
            if vlm_endpoint:
                options.vlm.endpoint = vlm_endpoint
            # Настройка модели VLM
            vlm_model = os.environ.get("VLM_MODEL", "default")
            if hasattr(options.vlm, "model"):
                options.vlm.model = vlm_model
        except Exception:
            # Если VLM недоступен, используем стандартный OCR
            pass

    elif route == "pdf_text":
        # PDF с текстовым слоем - только text extraction
        options.pdf = PdfPipelineOptions()
        options.pdf.do_ocr = False
        options.pdf.do_table_structure = True  # Извлекаем таблицы

    elif route == "pdf_mixed":
        # Смешанный PDF - используем OCR для страниц без текста
        options.pdf = PdfPipelineOptions()
        options.pdf.do_ocr = True
        options.pdf.do_table_structure = True

    elif route == "docx":
        # Word документы - нативная обработка
        pass  # Docling использует нативную обработку для DOCX

    elif route == "xlsx":
        # Excel таблицы - нативная обработка
        pass  # Docling использует нативную обработку для XLSX

    elif route == "pptx":
        # PowerPoint презентации - нативная обработка
        pass  # Docling использует нативную обработку для PPTX

    elif route in ["html", "html_text"]:
        # HTML документы - парсинг структуры
        pass  # Docling парсит HTML структуру автоматически

    elif route == "xml":
        # XML документы - парсинг структуры
        pass  # Docling парсит XML структуру автоматически

    elif route == "image_ocr":
        # Изображения - только OCR через PDF pipeline
        options.pdf = PdfPipelineOptions()
        options.pdf.do_ocr = True
        options.pdf.do_table_structure = True  # Пытаемся извлечь таблицы из изображений

    elif route == "rtf":
        # RTF документы - обрабатываем как текст
        pass  # Docling обрабатывает RTF

    else:
        # Fallback для неизвестных routes
        # Используем базовые настройки с OCR по умолчанию
        options.pdf = PdfPipelineOptions()
        options.pdf.do_ocr = False
        options.pdf.do_table_structure = True

    return options


def get_input_format_from_route(route: str) -> Optional[InputFormat]:
    """
    Определяет InputFormat на основе route.

    Args:
        route: Route из manifest

    Returns:
        InputFormat или None
    """
    if not DOCLING_AVAILABLE:
        return None

    route_to_format = {
        "pdf_text": InputFormat.PDF,
        "pdf_scan": InputFormat.PDF,
        "pdf_mixed": InputFormat.PDF,
        "docx": InputFormat.DOCX,
        "xlsx": InputFormat.XLSX,
        "pptx": InputFormat.PPTX,
        "html": InputFormat.HTML,
        "html_text": InputFormat.HTML,
        "xml": None,  # XML определяется автоматически Docling (может быть XML_JATS или XML_USPTO)
        "image_ocr": InputFormat.PDF,  # Изображения обрабатываются как PDF
        "rtf": InputFormat.DOCX,  # RTF обрабатывается как DOCX
    }

    return route_to_format.get(route)


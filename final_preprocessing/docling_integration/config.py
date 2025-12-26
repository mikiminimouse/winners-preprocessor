"""
Конфигурация Docling - маппинг route → Docling PipelineOptions через YAML templates.

Использует pipeline templates из YAML файлов для конфигурации Docling,
обеспечивая воспроизводимость и версионирование конфигураций.
"""
import os
import logging
import yaml
from typing import Dict, Any, Optional
from pathlib import Path

try:
    # Импортируем установленный пакет docling напрямую
    # ВАЖНО: Убеждаемся, что site-packages находится в начале sys.path
    import sys
    import importlib
    import site
    
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
    
    base_models_mod = importlib.import_module('docling.datamodel.base_models')
    InputFormat = base_models_mod.InputFormat
    
    pipeline_options_mod = importlib.import_module('docling.datamodel.pipeline_options')
    PipelineOptions = pipeline_options_mod.PipelineOptions
    PdfPipelineOptions = pipeline_options_mod.PdfPipelineOptions
    VlmPipelineOptions = pipeline_options_mod.VlmPipelineOptions
    
    DOCLING_AVAILABLE = True
except (ImportError, Exception):
    DOCLING_AVAILABLE = False
    PipelineOptions = None
    InputFormat = None
    DocumentConverter = None
    PdfPipelineOptions = None
    VlmPipelineOptions = None

# Путь к директории с pipeline templates
TEMPLATES_DIR = Path(__file__).parent / "pipeline_templates"

logger = logging.getLogger(__name__)


def load_pipeline_template(route: str) -> Optional[Dict[str, Any]]:
    """
    Загружает pipeline template из YAML файла для указанного route.
    
    Args:
        route: Route для загрузки шаблона
        
    Returns:
        Словарь с конфигурацией pipeline или None если шаблон не найден
    """
    template_path = TEMPLATES_DIR / f"{route}.yaml"
    
    if not template_path.exists():
        logger.warning(f"Pipeline template not found for route {route}: {template_path}")
        return None
    
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            template = yaml.safe_load(f)
        return template
    except Exception as e:
        logger.error(f"Failed to load pipeline template for route {route}: {e}")
        return None


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
    
    Args:
        template: Словарь с конфигурацией из YAML
        
    Returns:
        PipelineOptions для DocumentConverter
    """
    docling_config = template.get("docling", {})
    
    # Настройки для PDF
    pdf_opts = None
    if template.get("route", "").startswith("pdf") or template.get("route") == "image_ocr":
        pdf_opts = PdfPipelineOptions()
        pdf_config = template.get("models", {})
        
        if pdf_config.get("ocr") == "tesseract" or docling_config.get("force_ocr"):
            pdf_opts.do_ocr = True
        else:
            pdf_opts.do_ocr = False
        
        if pdf_config.get("tables") != "off":
            pdf_opts.do_table_structure = True
    
    # Создаем PipelineOptions с pdf опциями
    # Общие настройки Docling применяются через pdf опции, если они есть
    if pdf_opts:
        options = PipelineOptions(pdf=pdf_opts)
    else:
        options = PipelineOptions()
    
    # VLM pipeline (если указан в template)
    # Temporarily disabled due to configuration issues
    # vlm_config = template.get("models", {}).get("vlm")
    # if vlm_config:
    #     try:
    #         options.vlm = VlmPipelineOptions()
    #         vlm_endpoint = os.environ.get("VLM_ENDPOINT")
    #         if vlm_endpoint:
    #             options.vlm.endpoint = vlm_endpoint
    #         vlm_model = os.environ.get("VLM_MODEL", vlm_config.get("model", "default"))
    #         if hasattr(options.vlm, "model"):
    #             options.vlm.model = vlm_model
    #         
    #         # TODO: Cloud.ru integration placeholder
    #         # Future integration for Granite model:
    #         # if vlm_model == "granite_docling":
    #         #     options.vlm.provider = "cloud_ru"
    #         #     options.vlm.model_path = "run granite_docling"
    #     except Exception:
    #         pass
    
    # OCR options
    # TODO: Cloud.ru integration placeholder for PaddleOCR
    # if template.get("models", {}).get("ocr") == "paddle_ocr_vlm":
    #     if hasattr(options, 'ocr_options'):
    #         options.ocr_options.provider = "cloud_ru"
    #         options.ocr_options.docker_image = "PaddleOCR_VLM:@ocr_vl"
    
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


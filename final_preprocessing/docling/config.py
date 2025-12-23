"""
Конфигурация Docling - маппинг manifest.processing.route → Docling PipelineOptions.

Не дублирует parsing логику, только настраивает Docling для разных routes.
"""
import os
from typing import Dict, Any, Optional
from pathlib import Path

try:
    from docling.document_converter import DocumentConverter
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import (
        PdfPipelineOptions,
        VlmPipelineOptions,
        PipelineOptions,
    )
    DOCLING_AVAILABLE = True
except ImportError:
    DOCLING_AVAILABLE = False
    PipelineOptions = None
    InputFormat = None


def build_docling_options(route: str, manifest: Dict[str, Any]) -> Optional[PipelineOptions]:
    """
    Строит Docling PipelineOptions на основе route из manifest.

    Args:
        route: Route из manifest.processing.route (pdf_text, pdf_scan, docx, xlsx, html, xml)
        manifest: Полный manifest из docprep

    Returns:
        PipelineOptions для DocumentConverter или None если Docling недоступен
    """
    if not DOCLING_AVAILABLE:
        return None

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
        options.do_caption_mentions = True
        options.do_table_of_contents = True

    elif route == "pdf_mixed":
        # Смешанный PDF - используем OCR для страниц без текста
        options.pdf = PdfPipelineOptions()
        options.pdf.do_ocr = True
        options.pdf.do_table_structure = True
        options.do_caption_mentions = True

    elif route == "docx":
        # Word документы - нативная обработка
        options.do_caption_mentions = True
        options.do_table_of_contents = True
        options.do_table_structure = True

    elif route == "xlsx":
        # Excel таблицы - нативная обработка
        options.do_table_structure = True
        options.do_caption_mentions = True

    elif route == "pptx":
        # PowerPoint презентации - нативная обработка
        options.do_caption_mentions = True
        options.do_table_of_contents = True

    elif route in ["html", "html_text"]:
        # HTML документы - парсинг структуры
        options.do_caption_mentions = True
        options.do_table_of_contents = True
        options.do_table_structure = True

    elif route == "xml":
        # XML документы - парсинг структуры
        options.do_caption_mentions = True
        options.do_table_structure = True

    elif route == "image_ocr":
        # Изображения - только OCR через PDF pipeline
        options.pdf = PdfPipelineOptions()
        options.pdf.do_ocr = True
        options.pdf.do_table_structure = True  # Пытаемся извлечь таблицы из изображений

    elif route == "rtf":
        # RTF документы - обрабатываем как текст
        options.do_caption_mentions = True

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
        "xml": InputFormat.XML,
        "image_ocr": InputFormat.PDF,  # Изображения обрабатываются как PDF
        "rtf": InputFormat.DOCX,  # RTF обрабатывается как DOCX
    }

    return route_to_format.get(route)


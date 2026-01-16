"""
Константы и маппинги для Docling Pipeline.

Централизованное место для всех констант, которые используются
в разных модулях: pipeline.py, runner.py, config.py.
"""
from typing import FrozenSet, Dict

# Docling routes - группировка по типу обработки
DIGITAL_ROUTES: FrozenSet[str] = frozenset([
    "docx", "pdf_text", "xlsx", "xml", "html", "pptx", "rtf"
])

OCR_ROUTES: FrozenSet[str] = frozenset([
    "pdf_scan", "pdf_scan_table", "image_ocr"
])

ALL_ROUTES: FrozenSet[str] = DIGITAL_ROUTES | OCR_ROUTES

# Маппинг route → extension для определения поддиректории выхода
ROUTE_TO_EXTENSION: Dict[str, str] = {
    "pdf_text": "pdf",
    "pdf_scan": "pdf",
    "pdf_mixed": "pdf",
    "docx": "docx",
    "xlsx": "xlsx",
    "html": "html",
    "html_text": "html",
    "xml": "xml",
    "pptx": "pptx",
    "rtf": "rtf",
    "image_ocr": "image",
}

# Маппинг image extensions → "image" для группировки
IMAGE_EXTENSIONS: FrozenSet[str] = frozenset([
    "jpg", "jpeg", "png", "tiff", "tif", "bmp", "gif"
])

# Расширения файлов, поддерживаемые Docling
DOCLING_SUPPORTED_EXTENSIONS: FrozenSet[str] = frozenset([
    ".pdf", ".docx", ".xlsx", ".pptx", ".html", ".htm",
    ".xml", ".rtf", ".jpg", ".jpeg", ".png", ".tiff",
    ".tif", ".gif", ".bmp"
])

# Расширения файлов, которые НЕ поддерживаются Docling
UNSUPPORTED_EXTENSIONS: FrozenSet[str] = frozenset([
    ".zip", ".rar", ".7z", ".exe", ".dll", ".bin"
])

# Служебные файлы, которые не должны обрабатываться
EXCLUDED_FILENAMES: FrozenSet[str] = frozenset([
    "manifest.json", "docprep.contract.json", "audit.log.jsonl",
    "raw_url_map.json", "unit.meta.json"
])


def get_extension_for_route(route: str) -> str:
    """
    Возвращает расширение для указанного route.

    Args:
        route: Route из contract

    Returns:
        Расширение файла или "other" если route неизвестен
    """
    return ROUTE_TO_EXTENSION.get(route, "other")


def normalize_extension(extension: str) -> str:
    """
    Нормализует расширение файла (lowercase, без точки).
    Группирует image форматы.

    Args:
        extension: Расширение файла

    Returns:
        Нормализованное расширение
    """
    ext = extension.lower().lstrip(".")
    if ext in IMAGE_EXTENSIONS:
        return "image"
    return ext or "other"


def is_digital_route(route: str) -> bool:
    """Проверяет, является ли route digital (без OCR)."""
    return route in DIGITAL_ROUTES


def is_ocr_route(route: str) -> bool:
    """Проверяет, требует ли route OCR обработку."""
    return route in OCR_ROUTES

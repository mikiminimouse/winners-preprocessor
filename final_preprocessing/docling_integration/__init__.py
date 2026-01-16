"""
Docling Library - упрощенный orchestration слой для IBM Docling.

Использует реальный Docling как dependency, интегрируется с docprep через адаптер.
"""
__version__ = "1.1.0"

from .constants import (
    DIGITAL_ROUTES,
    OCR_ROUTES,
    ALL_ROUTES,
    ROUTE_TO_EXTENSION,
    DOCLING_SUPPORTED_EXTENSIONS,
    get_extension_for_route,
    normalize_extension,
    is_digital_route,
    is_ocr_route,
)
from .pipeline import DoclingPipeline
from .runner import run_docling_conversion, get_processed_count, reset_processed_counts
from .config import build_docling_options, get_input_format_from_route, clear_template_cache
from .bridge_docprep import load_unit_from_ready2docling, get_main_file

__all__ = [
    # Pipeline
    "DoclingPipeline",
    # Runner
    "run_docling_conversion",
    "get_processed_count",
    "reset_processed_counts",
    # Config
    "build_docling_options",
    "get_input_format_from_route",
    "clear_template_cache",
    # Bridge
    "load_unit_from_ready2docling",
    "get_main_file",
    # Constants
    "DIGITAL_ROUTES",
    "OCR_ROUTES",
    "ALL_ROUTES",
    "ROUTE_TO_EXTENSION",
    "DOCLING_SUPPORTED_EXTENSIONS",
    "get_extension_for_route",
    "normalize_extension",
    "is_digital_route",
    "is_ocr_route",
]


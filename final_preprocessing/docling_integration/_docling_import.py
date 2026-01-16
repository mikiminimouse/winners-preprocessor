"""
Централизованный импорт Docling из site-packages.
Используется всеми модулями для избежания дублирования логики импорта.
"""
import sys
import importlib
import site
from pathlib import Path
from typing import Optional

# Флаг инициализации
_INITIALIZED = False

# Кэш для импортированных модулей
_DOCLING_MODULES = {}

def ensure_docling_import():
    """
    Обеспечивает корректный импорт Docling из site-packages.
    Вызывается один раз при первом использовании.

    Returns:
        True если успешно, False если Docling недоступен
    """
    global _INITIALIZED, _DOCLING_MODULES

    if _INITIALIZED:
        return True

    try:
        # Перемещаем site-packages в начало sys.path
        for site_dir in site.getsitepackages():
            if (Path(site_dir) / 'docling' / '__init__.py').exists():
                if site_dir in sys.path:
                    sys.path.remove(site_dir)
                sys.path.insert(0, site_dir)

        # Очищаем локальные модули docling если они есть
        _cleanup_local_docling()

        # Импортируем необходимые модули
        _DOCLING_MODULES['document_converter'] = importlib.import_module('docling.document_converter')
        _DOCLING_MODULES['pipeline_options'] = importlib.import_module('docling.datamodel.pipeline_options')
        _DOCLING_MODULES['base_models'] = importlib.import_module('docling.datamodel.base_models')

        _INITIALIZED = True
        return True

    except ImportError:
        return False


def _cleanup_local_docling():
    """Удаляет локальные модули docling из sys.modules."""
    if 'docling' in sys.modules:
        mod = sys.modules['docling']
        if hasattr(mod, '__file__') and mod.__file__:
            if 'final_preprocessing' in str(mod.__file__):
                to_remove = [k for k in sys.modules.keys() if k.startswith('docling')]
                for k in to_remove:
                    sys.modules.pop(k, None)


def import_installed_docling_module(module_name: str):
    """
    Импортирует модуль из установленного пакета docling.

    Args:
        module_name: Имя модуля (например, 'document_converter' или 'datamodel.pipeline_options')

    Returns:
        Импортированный модуль

    Raises:
        ImportError: Если модуль не найден
    """
    # Обеспечиваем инициализацию
    if not ensure_docling_import():
        raise ImportError("Docling not available")

    # Маппинг коротких имен на ключи в кэше
    module_map = {
        'document_converter': 'document_converter',
        'datamodel.pipeline_options': 'pipeline_options',
        'datamodel.base_models': 'base_models',
    }

    cache_key = module_map.get(module_name)
    if cache_key and cache_key in _DOCLING_MODULES:
        return _DOCLING_MODULES[cache_key]

    # Fallback для других модулей
    full_name = f'docling.{module_name}'
    try:
        module = importlib.import_module(full_name)
        return module
    except ImportError as e:
        raise ImportError(f"Failed to import {full_name}: {e}")


def is_docling_available() -> bool:
    """Проверяет доступность Docling."""
    return ensure_docling_import()


def get_document_converter() -> Optional:
    """Возвращает класс DocumentConverter."""
    if not ensure_docling_import():
        return None
    return _DOCLING_MODULES['document_converter'].DocumentConverter


def get_pipeline_options() -> Optional:
    """Возвращает класс PipelineOptions."""
    if not ensure_docling_import():
        return None
    return _DOCLING_MODULES['pipeline_options'].PipelineOptions


def get_pdf_pipeline_options() -> Optional:
    """Возвращает класс PdfPipelineOptions."""
    if not ensure_docling_import():
        return None
    return _DOCLING_MODULES['pipeline_options'].PdfPipelineOptions


def get_vlm_pipeline_options() -> Optional:
    """Возвращает класс VlmPipelineOptions."""
    if not ensure_docling_import():
        return None
    return _DOCLING_MODULES['pipeline_options'].VlmPipelineOptions


def get_input_format() -> Optional:
    """Возвращает класс InputFormat."""
    if not ensure_docling_import():
        return None
    return _DOCLING_MODULES['base_models'].InputFormat


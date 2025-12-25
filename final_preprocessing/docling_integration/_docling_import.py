"""
Вспомогательный модуль для импорта установленного пакета docling.
Используется для импорта установленного пакета docling из site-packages.
Локальный модуль переименован в docling_integration, поэтому конфликта имен больше нет.
"""
import sys
import importlib
from pathlib import Path
from typing import Optional

# Кэш для импортированных модулей
_imported_modules = {}

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
    full_name = f'docling.{module_name}'
    
    # Проверяем кэш
    if full_name in _imported_modules:
        return _imported_modules[full_name]
    
    # Сохраняем локальные модули docling для возможного восстановления
    _local_docling_modules = {}
    if 'docling' in sys.modules:
        mod = sys.modules['docling']
        if hasattr(mod, '__file__') and mod.__file__:
            mod_file = str(mod.__file__)
            if 'final_preprocessing' in mod_file:
                # Сохраняем все локальные модули docling.*
                _local_docling_modules = {
                    k: v for k, v in sys.modules.items() 
                    if k.startswith('docling')
                }
                # Удаляем их из sys.modules
                for k in list(_local_docling_modules.keys()):
                    sys.modules.pop(k, None)
    
    try:
        # Убеждаемся, что site-packages в sys.path
        import site
        for site_dir in site.getsitepackages():
            if site_dir not in sys.path:
                sys.path.insert(0, site_dir)
        
        # Импортируем установленный пакет
        module = importlib.import_module(full_name)
        _imported_modules[full_name] = module
        return module
    except ImportError as e:
        # Восстанавливаем локальные модули при ошибке
        if _local_docling_modules:
            sys.modules.update(_local_docling_modules)
        raise


def get_document_converter():
    """Получает класс DocumentConverter из установленного пакета."""
    mod = import_installed_docling_module('document_converter')
    return mod.DocumentConverter


def get_pipeline_options():
    """Получает класс PipelineOptions из установленного пакета."""
    mod = import_installed_docling_module('datamodel.pipeline_options')
    return mod.PipelineOptions


def get_input_format():
    """Получает класс InputFormat из установленного пакета."""
    mod = import_installed_docling_module('datamodel.base_models')
    return mod.InputFormat


def get_pdf_pipeline_options():
    """Получает класс PdfPipelineOptions из установленного пакета."""
    mod = import_installed_docling_module('datamodel.pipeline_options')
    return mod.PdfPipelineOptions


def get_vlm_pipeline_options():
    """Получает класс VlmPipelineOptions из установленного пакета."""
    mod = import_installed_docling_module('datamodel.pipeline_options')
    return mod.VlmPipelineOptions


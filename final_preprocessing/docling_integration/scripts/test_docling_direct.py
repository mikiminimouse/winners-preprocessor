#!/usr/bin/env python3
"""
Прямой тест Docling без использования локальных модулей.

Этот скрипт тестирует установленный пакет docling напрямую.
Локальный модуль переименован в docling_integration, поэтому конфликта имен больше нет.
"""
import sys
import site
from pathlib import Path

# Добавляем site-packages в начало sys.path
for site_dir in site.getsitepackages():
    if (Path(site_dir) / 'docling' / '__init__.py').exists():
        if site_dir not in sys.path:
            sys.path.insert(0, site_dir)
        break

# Теперь импортируем установленный пакет docling
from docling.document_converter import DocumentConverter
from docling.datamodel.pipeline_options import PipelineOptions

print("✅ Docling успешно импортирован!")
print(f"DocumentConverter: {DocumentConverter}")
print(f"PipelineOptions: {PipelineOptions}")

# Создаем конвертер
converter = DocumentConverter()
print(f"✅ DocumentConverter создан: {converter}")

print("\n✅ Установленный пакет Docling работает корректно!")


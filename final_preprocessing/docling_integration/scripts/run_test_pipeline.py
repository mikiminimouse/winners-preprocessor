#!/usr/bin/env python3
"""
Wrapper скрипт для запуска test_docling_pipeline.py с правильной настройкой sys.path.

Этот скрипт правильно настраивает sys.path для работы с docling_integration модулем
и установленным пакетом docling.
"""
import sys
import site
from pathlib import Path

# 1. Добавляем site-packages в начало sys.path ПЕРЕД final_preprocessing
for site_dir in site.getsitepackages():
    if (Path(site_dir) / 'docling' / '__init__.py').exists():
        if site_dir not in sys.path:
            sys.path.insert(0, site_dir)
        break

# 2. Добавляем путь к проекту
_project_root = Path(__file__).parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# 3. Теперь можно импортировать модули
from final_preprocessing.docling_integration.scripts.test_docling_pipeline import main

if __name__ == '__main__':
    main()


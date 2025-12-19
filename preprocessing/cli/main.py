#!/usr/bin/env python3
"""
Основной модуль CLI для препроцессинга документов.

Содержит класс PreprocessingTestCLI с меню и роутингом команд.
Импортирует все handlers из соответствующих модулей.
"""

import sys
import json
import time
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

# Настройка PYTHONPATH для доступа к sync_db
project_root = Path(__file__).parent.parent.parent  # /root/winners_preprocessor
sys.path.insert(0, str(project_root))

# Загрузка переменных окружения из .env файла
def load_env_file():
    """Загружает переменные окружения из .env файла если он существует."""
    env_file = Path(__file__).parent.parent.parent / ".env"
    if env_file.exists():
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        # Удаляем кавычки если они есть
                        value = value.strip('"').strip("'")
                        os.environ[key] = value
        except Exception as e:
            print(f"⚠️  Не удалось загрузить .env файл: {e}")

# Загружаем переменные окружения
load_env_file()

# Импортируем функции из router (новые модули)
sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    from router.config import (
        INPUT_DIR, TEMP_DIR, OUTPUT_DIR, EXTRACTED_DIR, NORMALIZED_DIR, ARCHIVE_DIR,
        DOCLING_API
    )
    from router.mongo import get_mongo_client, get_mongo_metadata_client, get_manifest_from_mongo, get_protocols_by_date
    from router.file_detection import detect_file_type
    from router.metrics import init_processing_metrics, save_processing_metrics
    from router.api import process_file, download_document
except ImportError:
    # Fallback для случаев когда router не доступен
    INPUT_DIR = Path("/root/winners_preprocessor/data/input")
    TEMP_DIR = Path("/root/winners_preprocessor/data/temp")
    OUTPUT_DIR = Path("/root/winners_preprocessor/data/output")
    EXTRACTED_DIR = Path("/root/winners_preprocessor/data/extracted")
    NORMALIZED_DIR = Path("/root/winners_preprocessor/data/normalized")
    ARCHIVE_DIR = Path("/root/winners_preprocessor/data/archive")
    DOCLING_API = "http://localhost:8001/process"

    def get_protocols_by_date(*args, **kwargs):
        return []

    def download_document(*args, **kwargs):
        return False

    def process_file(*args, **kwargs):
        return None

    def init_processing_metrics(*args, **kwargs):
        pass

    def save_processing_metrics(*args, **kwargs):
        pass

    def get_manifest_from_mongo(*args, **kwargs):
        return None

    def get_mongo_metadata_client(*args, **kwargs):
        return None

    def get_mongo_client(*args, **kwargs):
        return None

    def detect_file_type(*args, **kwargs):
        return {"type": "unknown", "mime": "unknown"}

# Импорт модуля синхронизации протоколов (новый микросервис sync_db)
try:
    from sync_db import SyncService as SyncDBService
except ImportError:
    SyncDBService = None

# Импорт модуля скачивания протоколов
try:
    from router.downloader.manager import ProtocolDownloader
    from router.downloader.core import check_zakupki_health
except ImportError:
    ProtocolDownloader = None
    check_zakupki_health = None

# Импорт всех handlers
try:
    # Попытка относительного импорта
    from .handlers.load_handlers import (
        handle_sync_protocols,
        handle_download_protocols,
        handle_check_input_files
    )
    from .handlers.test_handlers import (
        handle_test_file_type_detection,
        handle_test_archive_extraction,
        handle_test_normalization,
        handle_test_manifest_creation,
        handle_test_docling_processing
    )
    from .handlers.step_handlers import (
        handle_step1_scan_and_detect,
        handle_step2_classify,
        handle_step3_check_duplicates,
        handle_step4_check_mixed,
        handle_step5_distribute,
        handle_full_processing
    )
    from .handlers.stats_handlers import (
        handle_view_pending_structure,
        handle_category_statistics,
        handle_units_report
    )
    from .handlers.merge_handlers import (
        handle_merge_dry_run,
        handle_merge_real
    )
    from .handlers.pipeline_handlers import (
        handle_full_pipeline_test,
        handle_integration_test
    )
    from .handlers.monitor_handlers import (
        handle_view_metrics,
        handle_view_logs,
        handle_check_mongodb
    )
    from .handlers.utils_handlers import (
        handle_cleanup_test_data,
        handle_create_test_files,
        handle_check_infrastructure
    )
except ImportError:
    # Fallback для абсолютного импорта
    from handlers.load_handlers import (
        handle_sync_protocols,
        handle_download_protocols,
        handle_check_input_files
    )
    from handlers.test_handlers import (
        handle_test_file_type_detection,
        handle_test_archive_extraction,
        handle_test_normalization,
        handle_test_manifest_creation,
        handle_test_docling_processing
    )
    from handlers.step_handlers import (
        handle_step1_scan_and_detect,
        handle_step2_classify,
        handle_step3_check_duplicates,
        handle_step4_check_mixed,
        handle_step5_distribute,
        handle_full_processing
    )
    from handlers.stats_handlers import (
        handle_view_pending_structure,
        handle_category_statistics,
        handle_units_report
    )
    from handlers.merge_handlers import (
        handle_merge_dry_run,
        handle_merge_real
    )
    from handlers.pipeline_handlers import (
        handle_full_pipeline_test,
        handle_integration_test
    )
    from handlers.monitor_handlers import (
        handle_view_metrics,
        handle_view_logs,
        handle_check_mongodb
    )
    from handlers.utils_handlers import (
        handle_cleanup_test_data,
        handle_create_test_files,
        handle_check_infrastructure
    )

# Импорт конфигурации
try:
    from .config import MENU_CATEGORIES, MENU_MAPPING, MENU_TITLE, MENU_SEPARATOR, CLI_SETTINGS
except ImportError:
    from config import MENU_CATEGORIES, MENU_MAPPING, MENU_TITLE, MENU_SEPARATOR, CLI_SETTINGS


class PreprocessingTestCLI:
    """CLI для тестирования препроцессинга."""

    def __init__(self):
        self.metrics = None
        self.session_id = None

        # Импортируем time и json для использования в handlers
        self.time = time
        self.json = json

        # Импортируем основные функции для использования в handlers
        self.INPUT_DIR = INPUT_DIR
        self.TEMP_DIR = TEMP_DIR
        self.OUTPUT_DIR = OUTPUT_DIR
        self.EXTRACTED_DIR = EXTRACTED_DIR
        self.NORMALIZED_DIR = NORMALIZED_DIR
        self.ARCHIVE_DIR = ARCHIVE_DIR
        self.DOCLING_API = DOCLING_API

        # Импортируем функции
        self.get_protocols_by_date = get_protocols_by_date
        self.download_document = download_document
        self.process_file = process_file
        self.init_processing_metrics = init_processing_metrics
        self.save_processing_metrics = save_processing_metrics
        self.get_manifest_from_mongo = get_manifest_from_mongo
        self.get_mongo_metadata_client = get_mongo_metadata_client
        self.get_mongo_client = get_mongo_client
        self.detect_file_type = detect_file_type

    def show_menu(self):
        """Показывает главное меню."""
        print(f"\n{MENU_SEPARATOR}")
        print(MENU_TITLE)
        print(MENU_SEPARATOR)

        for category_key, category_info in MENU_CATEGORIES.items():
            print(f"\n=== {category_info['title']} ===")
            for item in category_info['items']:
                print(item)

        print("\n0. Выход")
        print(f"\n{MENU_SEPARATOR}")

    def run(self):
        """Главный цикл CLI."""
        print("\n🚀 ЗАПУСК CLI ТЕСТИРОВАНИЯ ПРЕПРОЦЕССИНГА")
        print(MENU_SEPARATOR)

        while True:
            try:
                self.show_menu()
                choice = input(CLI_SETTINGS["prompt_template"]).strip()

                if choice == "0":
                    print("👋 Выход...")
                    break

                # Получаем информацию о выбранном пункте меню
                choice_num = int(choice) if choice.isdigit() else None
                if choice_num and choice_num in MENU_MAPPING:
                    category, function_name = MENU_MAPPING[choice_num]

                    # Получаем функцию из соответствующего модуля
                    handler_function = self._get_handler_function(category, function_name)

                    if handler_function:
                        # Вызываем функцию с экземпляром CLI
                        handler_function(self)
                    else:
                        print(f"❌ Функция {function_name} не найдена в категории {category}")
                else:
                    print("❌ Неверный выбор. Попробуйте снова.")

                input("\n⏎ Нажмите Enter для продолжения...")

            except KeyboardInterrupt:
                print("\n\n👋 Выход...")
                break
            except Exception as e:
                print(f"\n❌ Ошибка: {e}")
                import traceback
                traceback.print_exc()
                input("\n⏎ Нажмите Enter для продолжения...")

    def _get_handler_function(self, category: str, function_name: str):
        """Получает функцию handler по категории и имени."""
        # Маппинг категорий к модулям
        category_mapping = {
            "load": {
                "sync_protocols": handle_sync_protocols,
                "download_protocols": handle_download_protocols,
                "check_input_files": handle_check_input_files
            },
            "test": {
                "test_file_type_detection": handle_test_file_type_detection,
                "test_archive_extraction": handle_test_archive_extraction,
                "test_normalization": handle_test_normalization,
                "test_manifest_creation": handle_test_manifest_creation,
                "test_docling_processing": handle_test_docling_processing
            },
            "step": {
                "step1_scan_and_detect": handle_step1_scan_and_detect,
                "step2_classify": handle_step2_classify,
                "step3_check_duplicates": handle_step3_check_duplicates,
                "step4_check_mixed": handle_step4_check_mixed,
                "step5_distribute": handle_step5_distribute,
                "full_processing": handle_full_processing
            },
            "stats": {
                "view_pending_structure": handle_view_pending_structure,
                "category_statistics": handle_category_statistics,
                "units_report": handle_units_report
            },
            "merge": {
                "merge_dry_run": handle_merge_dry_run,
                "merge_real": handle_merge_real
            },
            "pipeline": {
                "full_pipeline_test": handle_full_pipeline_test,
                "integration_test": handle_integration_test
            },
            "monitor": {
                "view_metrics": handle_view_metrics,
                "view_logs": handle_view_logs,
                "check_mongodb": handle_check_mongodb
            },
            "utils": {
                "cleanup_test_data": handle_cleanup_test_data,
                "create_test_files": handle_create_test_files,
                "check_infrastructure": handle_check_infrastructure
            }
        }

        if category in category_mapping and function_name in category_mapping[category]:
            return category_mapping[category][function_name]

        return None


def main():
    """Точка входа для CLI."""
    cli = PreprocessingTestCLI()
    cli.run()


if __name__ == "__main__":
    main()

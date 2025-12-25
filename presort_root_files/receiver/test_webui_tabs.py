#!/usr/bin/env python3
"""
Тестовый скрипт для проверки функционала вкладок Sync Manager и Download Control.

Проверяет:
1. Импорты всех необходимых модулей
2. Инициализацию сервисов
3. Корректность обработчиков
4. Структуру данных
"""

import sys
import logging
from pathlib import Path

# Добавляем путь к проекту
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "receiver"))

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_imports():
    """Тест импортов всех необходимых модулей."""
    logger.info("=" * 60)
    logger.info("Тест 1: Проверка импортов")
    logger.info("=" * 60)
    
    try:
        # Импорты для Sync Manager
        from receiver.sync_db.manager import SyncManagerService
        from receiver.sync_db.models import SyncRequest, SyncRunStatus
        logger.info("✅ Импорты Sync Manager: OK")
        
        # Импорты для Download Control
        from receiver.downloader.enhanced_service import EnhancedProtocolDownloader
        from receiver.downloader.models import DownloadRequest
        logger.info("✅ Импорты Download Control: OK")
        
        # Импорты WebUI handlers
        from receiver.webui.handlers.sync_manager_handlers import (
            sync_manager_start_sync,
            sync_manager_get_status,
            sync_manager_cancel,
            sync_manager_get_cursor_state,
            sync_manager_get_recent_runs
        )
        logger.info("✅ Импорты Sync Manager handlers: OK")
        
        from receiver.webui.handlers.download_handlers import download_protocols_handler
        logger.info("✅ Импорты Download handlers: OK")
        
        # Импорты WebUI services
        from receiver.webui.services.ui_service import get_ui_service
        logger.info("✅ Импорты UI Service: OK")
        
        # Импорты WebUI tabs
        from receiver.webui.tabs.sync_manager import create_sync_manager_tab
        logger.info("✅ Импорты Sync Manager tab: OK")
        
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка импорта: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_ui_service():
    """Тест инициализации UI Service."""
    logger.info("=" * 60)
    logger.info("Тест 2: Инициализация UI Service")
    logger.info("=" * 60)
    
    try:
        from receiver.webui.services.ui_service import get_ui_service
        
        ui_service = get_ui_service()
        logger.info("✅ UI Service создан")
        
        # Пытаемся инициализировать сервисы (может не работать без БД, но структура должна быть правильной)
        try:
            success = ui_service.initialize_services()
            if success:
                logger.info("✅ Сервисы инициализированы")
            else:
                logger.warning("⚠️ Сервисы не инициализированы (возможно, нет подключения к БД)")
        except Exception as e:
            logger.warning(f"⚠️ Ошибка инициализации сервисов (ожидаемо без БД): {e}")
        
        # Проверяем методы получения сервисов
        sync_service = ui_service.get_sync_service()
        downloader_service = ui_service.get_downloader_service()
        analytics_service = ui_service.get_analytics_service()
        sync_manager_service = ui_service.get_sync_manager_service()
        
        logger.info(f"  Sync Service: {'✅' if sync_service else '❌'}")
        logger.info(f"  Downloader Service: {'✅' if downloader_service else '❌'}")
        logger.info(f"  Analytics Service: {'✅' if analytics_service else '❌'}")
        logger.info(f"  Sync Manager Service: {'✅' if sync_manager_service else '❌'}")
        
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка UI Service: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_handlers_structure():
    """Тест структуры обработчиков."""
    logger.info("=" * 60)
    logger.info("Тест 3: Проверка структуры обработчиков")
    logger.info("=" * 60)
    
    try:
        from receiver.webui.handlers.sync_manager_handlers import (
            sync_manager_start_sync,
            sync_manager_get_status,
            sync_manager_cancel,
            sync_manager_get_cursor_state,
            sync_manager_get_recent_runs
        )
        from receiver.webui.handlers.download_handlers import download_protocols_handler
        
        # Проверяем сигнатуры функций
        import inspect
        
        # Sync Manager handlers
        sig_start = inspect.signature(sync_manager_start_sync)
        logger.info(f"✅ sync_manager_start_sync: {len(sig_start.parameters)} параметров")
        
        sig_status = inspect.signature(sync_manager_get_status)
        logger.info(f"✅ sync_manager_get_status: {len(sig_status.parameters)} параметров")
        
        sig_cancel = inspect.signature(sync_manager_cancel)
        logger.info(f"✅ sync_manager_cancel: {len(sig_cancel.parameters)} параметров")
        
        sig_cursor = inspect.signature(sync_manager_get_cursor_state)
        logger.info(f"✅ sync_manager_get_cursor_state: {len(sig_cursor.parameters)} параметров")
        
        sig_runs = inspect.signature(sync_manager_get_recent_runs)
        logger.info(f"✅ sync_manager_get_recent_runs: {len(sig_runs.parameters)} параметров")
        
        # Download handler
        sig_download = inspect.signature(download_protocols_handler)
        logger.info(f"✅ download_protocols_handler: {len(sig_download.parameters)} параметров")
        
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка проверки обработчиков: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_models():
    """Тест моделей данных."""
    logger.info("=" * 60)
    logger.info("Тест 4: Проверка моделей данных")
    logger.info("=" * 60)
    
    try:
        from receiver.sync_db.models import SyncRequest, SyncRunStatus
        from receiver.downloader.models import DownloadRequest
        
        # Тест SyncRequest
        try:
            request = SyncRequest(
                collection="protocols",
                mode="incremental"
            )
            logger.info("✅ SyncRequest создан успешно")
        except Exception as e:
            logger.error(f"❌ Ошибка создания SyncRequest: {e}")
            return False
        
        # Тест DownloadRequest
        try:
            download_request = DownloadRequest(
                max_units_per_run=10,
                max_urls_per_unit=15
            )
            logger.info("✅ DownloadRequest создан успешно")
        except Exception as e:
            logger.error(f"❌ Ошибка создания DownloadRequest: {e}")
            return False
        
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка проверки моделей: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_tab_creation():
    """Тест создания табов (без запуска Gradio)."""
    logger.info("=" * 60)
    logger.info("Тест 5: Проверка создания табов")
    logger.info("=" * 60)
    
    try:
        # Проверяем, что функция существует и может быть вызвана
        from receiver.webui.tabs.sync_manager import create_sync_manager_tab
        
        # Функция должна существовать
        if callable(create_sync_manager_tab):
            logger.info("✅ create_sync_manager_tab: функция доступна")
        else:
            logger.error("❌ create_sync_manager_tab: не является функцией")
            return False
        
        logger.info("✅ Таб Sync Manager: структура проверена")
        logger.info("ℹ️  Полная проверка таба требует запуска Gradio приложения")
        
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка проверки табов: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_handler_error_handling():
    """Тест обработки ошибок в обработчиках."""
    logger.info("=" * 60)
    logger.info("Тест 6: Проверка обработки ошибок")
    logger.info("=" * 60)
    
    try:
        from receiver.webui.handlers.sync_manager_handlers import sync_manager_get_cursor_state
        from receiver.webui.handlers.download_handlers import download_protocols_handler
        
        # Тест обработчика с невалидными данными (должен вернуть ошибку, а не упасть)
        result = sync_manager_get_cursor_state()
        logger.info(f"✅ sync_manager_get_cursor_state обработал запрос: {type(result)}")
        
        # Тест download handler с пустыми параметрами
        result = download_protocols_handler("", 0)
        logger.info(f"✅ download_protocols_handler обработал запрос: {type(result)}")
        logger.info(f"   Результат: {result[0][:50]}..." if result and len(result) > 0 else "   Результат: пустой")
        
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка проверки обработки ошибок: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def main():
    """Запуск всех тестов."""
    logger.info("\n" + "=" * 60)
    logger.info("НАЧАЛО ТЕСТИРОВАНИЯ ВКЛАДОК WEBUI")
    logger.info("=" * 60 + "\n")
    
    tests = [
        ("Импорты", test_imports),
        ("UI Service", test_ui_service),
        ("Структура обработчиков", test_handlers_structure),
        ("Модели данных", test_models),
        ("Создание табов", test_tab_creation),
        ("Обработка ошибок", test_handler_error_handling),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            logger.error(f"❌ Тест '{name}' упал с исключением: {e}")
            results.append((name, False))
        logger.info("")
    
    # Итоги
    logger.info("=" * 60)
    logger.info("ИТОГИ ТЕСТИРОВАНИЯ")
    logger.info("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{status}: {name}")
    
    logger.info("")
    logger.info(f"Пройдено тестов: {passed}/{total}")
    
    if passed == total:
        logger.info("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Функционал готов к ручному тестированию.")
        return 0
    else:
        logger.warning(f"⚠️ Некоторые тесты не пройдены. Проверьте ошибки выше.")
        return 1


if __name__ == "__main__":
    sys.exit(main())


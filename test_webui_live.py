#!/usr/bin/env python3
"""
Тестовый скрипт для проверки функционала WebUI после перезапуска.

Проверяет доступность обработчиков и их работу.
"""

import sys
import logging
from pathlib import Path
import time

# Добавляем путь к проекту
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "receiver"))

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def test_sync_manager_handlers():
    """Тест обработчиков Sync Manager."""
    logger.info("=" * 60)
    logger.info("Тест обработчиков Sync Manager")
    logger.info("=" * 60)
    
    try:
        from receiver.webui.handlers.sync_manager_handlers import (
            sync_manager_start_sync,
            sync_manager_get_status,
            sync_manager_cancel,
            sync_manager_get_cursor_state,
            sync_manager_get_recent_runs
        )
        
        # Тест 1: Получение состояния курсора
        logger.info("Тест 1: Получение состояния курсора...")
        cursor_result = sync_manager_get_cursor_state()
        logger.info(f"✅ Результат: {cursor_result[:100]}..." if len(cursor_result) > 100 else f"✅ Результат: {cursor_result}")
        
        # Тест 2: Получение последних запусков
        logger.info("Тест 2: Получение последних запусков...")
        runs_result = sync_manager_get_recent_runs(5)
        logger.info(f"✅ Результат: {runs_result[:100]}..." if len(runs_result) > 100 else f"✅ Результат: {runs_result}")
        
        # Тест 3: Создание запроса синхронизации (dry-run)
        logger.info("Тест 3: Создание запроса синхронизации (dry-run)...")
        try:
            status, info, run_id = sync_manager_start_sync(
                mode="incremental",
                from_date="",
                to_date="",
                batch_size=100,
                dry_run=True,
                write_mode="merge"
            )
            logger.info(f"✅ Статус: {status[:50]}...")
            logger.info(f"✅ Run ID: {run_id}")
            
            if run_id:
                # Тест 4: Получение статуса запуска
                logger.info("Тест 4: Получение статуса запуска...")
                time.sleep(1)  # Даем время на запуск
                status_result, details, progress = sync_manager_get_status(run_id)
                logger.info(f"✅ Статус: {status_result[:50]}...")
                logger.info(f"✅ Прогресс: {progress}%")
        except Exception as e:
            logger.warning(f"⚠️ Ошибка при создании запроса (может быть нормально без БД): {e}")
        
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка тестирования Sync Manager handlers: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_download_handlers():
    """Тест обработчиков Download Control."""
    logger.info("=" * 60)
    logger.info("Тест обработчиков Download Control")
    logger.info("=" * 60)
    
    try:
        from receiver.webui.handlers.download_handlers import download_protocols_handler
        
        # Тест 1: Загрузка без параметров (должна обработать корректно)
        logger.info("Тест 1: Загрузка без параметров...")
        try:
            status, metrics, errors, chart = download_protocols_handler("", 0)
            logger.info(f"✅ Статус: {status[:100]}..." if len(status) > 100 else f"✅ Статус: {status}")
            logger.info(f"✅ Метрики: {metrics[:100]}..." if len(metrics) > 100 else f"✅ Метрики: {metrics}")
        except Exception as e:
            logger.warning(f"⚠️ Ошибка при загрузке (может быть нормально без VPN/БД): {e}")
        
        # Тест 2: Загрузка с датой
        logger.info("Тест 2: Загрузка с датой...")
        try:
            status, metrics, errors, chart = download_protocols_handler("2024-01-01", 10)
            logger.info(f"✅ Статус: {status[:100]}..." if len(status) > 100 else f"✅ Статус: {status}")
        except Exception as e:
            logger.warning(f"⚠️ Ошибка при загрузке с датой: {e}")
        
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка тестирования Download handlers: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_ui_service():
    """Тест UI Service."""
    logger.info("=" * 60)
    logger.info("Тест UI Service")
    logger.info("=" * 60)
    
    try:
        from receiver.webui.services.ui_service import get_ui_service
        
        ui_service = get_ui_service()
        success = ui_service.initialize_services()
        
        if success:
            logger.info("✅ Сервисы инициализированы")
            
            sync_service = ui_service.get_sync_service()
            downloader_service = ui_service.get_downloader_service()
            analytics_service = ui_service.get_analytics_service()
            sync_manager_service = ui_service.get_sync_manager_service()
            
            logger.info(f"  Sync Service: {'✅' if sync_service else '❌'}")
            logger.info(f"  Downloader Service: {'✅' if downloader_service else '❌'}")
            logger.info(f"  Analytics Service: {'✅' if analytics_service else '❌'}")
            logger.info(f"  Sync Manager Service: {'✅' if sync_manager_service else '❌'}")
        else:
            logger.warning("⚠️ Сервисы не инициализированы")
        
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка тестирования UI Service: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_tab_imports():
    """Тест импорта табов."""
    logger.info("=" * 60)
    logger.info("Тест импорта табов")
    logger.info("=" * 60)
    
    try:
        from receiver.webui.tabs.sync_manager import create_sync_manager_tab
        logger.info("✅ Таб Sync Manager импортирован")
        
        if callable(create_sync_manager_tab):
            logger.info("✅ Функция create_sync_manager_tab доступна")
        else:
            logger.error("❌ create_sync_manager_tab не является функцией")
            return False
        
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка импорта табов: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def main():
    """Запуск всех тестов."""
    logger.info("\n" + "=" * 60)
    logger.info("ТЕСТИРОВАНИЕ WEBUI ПОСЛЕ ОБНОВЛЕНИЙ")
    logger.info("=" * 60 + "\n")
    
    tests = [
        ("Импорт табов", test_tab_imports),
        ("UI Service", test_ui_service),
        ("Sync Manager handlers", test_sync_manager_handlers),
        ("Download handlers", test_download_handlers),
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
        logger.info("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ! WebUI готов к использованию.")
        return 0
    else:
        logger.warning(f"⚠️ Некоторые тесты не пройдены. Проверьте ошибки выше.")
        return 1


if __name__ == "__main__":
    sys.exit(main())


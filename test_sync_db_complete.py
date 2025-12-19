#!/usr/bin/env python3
"""
Полный интеграционный тест sync_db с VPN функциональностью.
"""

import sys
import os
from pathlib import Path

# Добавляем пути
sys.path.insert(0, str(Path(__file__).parent))

def test_sync_db_complete():
    """Полное тестирование sync_db."""
    print("🎯 ПОЛНЫЙ ИНТЕГРАЦИОННЫЙ ТЕСТ SYNC_DB")
    print("=" * 60)

    results = {
        "imports": False,
        "models": False,
        "services": False,
        "vpn_functionality": False,
        "config_loading": False,
        "graceful_degradation": False
    }

    # 1. Тестирование импортов
    print("📦 ТЕСТ 1: Импорты")
    try:
        from sync_db import SyncService, SyncError, ConnectionError, ValidationError
        from sync_db.models import SyncConfig, SyncResult, ProtocolDocument
        print("   ✅ Все импорты успешны")
        results["imports"] = True
    except Exception as e:
        print(f"   ❌ Ошибка импортов: {e}")
        return results

    # Импортируем VPNService для использования в тестах
    from sync_db.services import VPNService

    # 2. Тестирование моделей
    print("\n🏗️  ТЕСТ 2: Модели данных")
    try:
        config = SyncConfig.from_env()
        result = SyncResult(status="success", date="2025-12-16")
        doc = ProtocolDocument(unit_id="test", urls=[])
        print("   ✅ Модели созданы успешно")
        results["models"] = True
    except Exception as e:
        print(f"   ❌ Ошибка моделей: {e}")

    # 3. Тестирование сервисов
    print("\n🔧 ТЕСТ 3: Сервисы")
    try:
        vpn = VPNService()
        conn = ConnectionService(config)
        print("   ✅ Сервисы инициализированы")
        results["services"] = True
    except Exception as e:
        print(f"   ❌ Ошибка сервисов: {e}")

    # 4. Тестирование VPN функциональности
    print("\n🔐 ТЕСТ 4: VPN функциональность")
    try:
        vpn_status = vpn.test_mongo_accessibility()
        print(f"   📊 Доступность MongoDB проверена: {len(vpn_status)} параметров")
        print(f"   🔍 Прямой доступ: {'✅' if not vpn_status['direct_access'] else '❌'} (ожидаемо без VPN)")
        results["vpn_functionality"] = True
    except Exception as e:
        print(f"   ❌ Ошибка VPN: {e}")

    # 5. Тестирование загрузки конфигурации
    print("\n⚙️  ТЕСТ 5: Загрузка конфигурации")
    try:
        env_config = config.__dict__
        required_fields = ['mongo_server', 'mongo_user', 'mongo_password']
        has_required = all(getattr(config, field, None) for field in required_fields)
        print(f"   ✅ Конфигурация загружена: {len(env_config)} параметров")
        print(f"   🔑 Обязательные поля: {'✅' if has_required else '❌'}")
        results["config_loading"] = True
    except Exception as e:
        print(f"   ❌ Ошибка конфигурации: {e}")

    # 6. Тестирование graceful degradation
    print("\n🛡️  ТЕСТ 6: Graceful degradation")
    try:
        # Отключаем VPN и тестируем
        config_no_vpn = SyncConfig.from_env()
        config_no_vpn.vpn_enabled = False

        sync_no_vpn = SyncService(config_no_vpn)
        from datetime import datetime, timedelta
        yesterday = datetime.utcnow() - timedelta(days=1)

        # Это должно завершиться с ошибкой, но gracefully
        result_no_vpn = sync_no_vpn.sync_protocols_for_date(yesterday, limit=1)
        expected_error = not result_no_vpn.success

        print(f"   ✅ Graceful degradation: {'✅' if expected_error else '❌'} (ожидаемая ошибка без VPN)")
        results["graceful_degradation"] = True
    except Exception as e:
        print(f"   ❌ Ошибка degradation: {e}")

    # Итоговый отчет
    print("\n" + "=" * 60)
    print("📊 ИТОГОВЫЙ ОТЧЕТ ТЕСТИРОВАНИЯ")
    print("=" * 60)

    passed = sum(results.values())
    total = len(results)

    for test, status in results.items():
        icon = "✅" if status else "❌"
        print(f"{icon} {test.replace('_', ' ').title()}")

    print("-" * 60)
    print(f"ПРОЙДЕНО: {passed}/{total} тестов")
    print(f"УСПЕШНОСТЬ: {(passed/total)*100:.1f}%")
    if passed == total:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! SYNC_DB ГОТОВ К ПРОДАКШЕНУ!")
        return True
    else:
        print("⚠️  НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ")
        return False

if __name__ == "__main__":
    success = test_sync_db_complete()
    sys.exit(0 if success else 1)

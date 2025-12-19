#!/usr/bin/env python3
"""
Тест VPN функциональности в sync_db.
"""

import sys
import os
from pathlib import Path

# Добавляем пути
sys.path.insert(0, str(Path(__file__).parent))

def test_vpn_functionality():
    """Тестирование VPN функциональности."""
    print("🧪 ТЕСТИРОВАНИЕ VPN ФУНКЦИОНАЛЬНОСТИ SYNC_DB")
    print("=" * 50)

    try:
        from sync_db.services import VPNService

        print("✅ VPNService импортирован")

        # Создаем VPN сервис
        vpn = VPNService()
        print("✅ VPNService создан")

        # Проверяем наличие конфигурационных файлов
        config_exists = vpn.vpn_config_path and os.path.exists(vpn.vpn_config_path)
        route_exists = vpn.route_script_path and os.path.exists(vpn.route_script_path)

        print(f"📁 VPN конфиг найден: {'✅' if config_exists else '❌'}")
        print(f"📁 Route скрипт найден: {'✅' if route_exists else '❌'}")

        # Тестируем проверку доступности MongoDB
        print("\n🔍 Тестирование проверки доступности MongoDB...")
        accessibility = vpn.test_mongo_accessibility()

        print("📊 Результаты проверки:")
        for key, value in accessibility.items():
            status = "✅" if value else "❌"
            print(f"   {key}: {status}")

        # Тестируем определение необходимости VPN
        needs_vpn = vpn.is_vpn_required()
        print(f"\n🔐 Требуется VPN: {'✅ Да' if needs_vpn else '❌ Нет'}")

        print("\n✅ VPN функциональность протестирована!")
        print("ℹ️  Для полного тестирования нужен реальный VPN")

        return True

    except Exception as e:
        print(f"❌ Ошибка тестирования VPN: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_vpn_functionality()
    sys.exit(0 if success else 1)

#!/usr/bin/env python3
"""
Ручное тестирование синхронизации с VPN.

Используется когда VPN нужно подключить вручную.
"""

import sys
import time
from pathlib import Path

# Добавляем пути
sys.path.insert(0, str(Path(__file__).parent))

def test_manual_vpn_sync():
    """Тестирование синхронизации с ручным VPN."""
    print("🔐 РУЧНОЕ ТЕСТИРОВАНИЕ СИНХРОНИЗАЦИИ С VPN")
    print("=" * 50)

    print("📋 ИНСТРУКЦИИ:")
    print("1. Откройте новый терминал")
    print("2. Выполните команду:")
    print("   sudo openvpn --config /root/winners_preprocessor/vitaly_bychkov.ovpn \\")
    print("                 --up /root/winners_preprocessor/route-up-zakupki.sh")
    print("3. Дождитесь сообщения 'Initialization Sequence Completed'")
    print("4. Вернитесь сюда и нажмите Enter")
    print()

    input("🔄 Нажмите Enter после подключения VPN...")

    print("\n🔍 Проверка VPN подключения...")
    try:
        from sync_db.services import VPNService

        vpn = VPNService()
        status = vpn.test_mongo_accessibility()

        print("📊 Статус VPN:")
        for key, value in status.items():
            icon = "✅" if value else "❌"
            print(f"   {key}: {icon}")

        if status["direct_access"]:
            print("\n✅ MongoDB доступна через VPN!")
            print("🚀 Запуск синхронизации...")

            from sync_db import SyncService
            from datetime import datetime, timedelta

            sync = SyncService()
            yesterday = datetime.utcnow() - timedelta(days=1)

            result = sync.sync_protocols_for_date(yesterday, limit=5)

            print("
📊 РЕЗУЛЬТАТ СИНХРОНИЗАЦИИ:"            print(f"   Статус: {'✅' if result.success else '❌'} {result.status}")
            if hasattr(result, 'inserted'):
                print(f"   Синхронизировано: {result.inserted} протоколов")

        else:
            print("\n❌ MongoDB все еще недоступна")
            print("Проверьте:")
            print("  - VPN подключен: ip link show | grep tun")
            print("  - Маршруты: ip route get 192.168.0.46")
            print("  - Логи VPN в соседнем терминале")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_manual_vpn_sync()

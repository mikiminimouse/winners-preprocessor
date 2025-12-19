#!/usr/bin/env python3
"""
Тест производительности sync_db с оптимизированными таймаутами.
"""

import time
import sys
from pathlib import Path

# Добавляем пути
sys.path.insert(0, str(Path(__file__).parent))

def test_connection_performance():
    """Тестирование скорости подключений."""
    print("⚡ ТЕСТ ПРОИЗВОДИТЕЛЬНОСТИ ПОДКЛЮЧЕНИЙ")
    print("=" * 50)

    from sync_db.services import VPNService
    from sync_db.utils.connection_utils import get_local_mongo_client

    # Тест 1: Локальная MongoDB
    print("1️⃣ Тест локального подключения к MongoDB:")
    start_time = time.time()

    client = get_local_mongo_client()
    if client:
        connection_time = time.time() - start_time
        print(".2f")
        client.close()
    else:
        print("❌ Ошибка подключения к локальной MongoDB")

    # Тест 2: VPN сервис
    print("\n2️⃣ Тест VPN сервиса:")
    start_time = time.time()

    vpn = VPNService()
    init_time = time.time() - start_time
    print(".2f"
    # Тест 3: Проверка доступности MongoDB
    print("\n3️⃣ Тест проверки доступности MongoDB:")
    start_time = time.time()

    accessibility = vpn.test_mongo_accessibility()
    check_time = time.time() - start_time
    print(".2f"    print(f"   Прямой доступ: {'✅' if accessibility['direct_access'] else '❌'}")
    print(f"   Ping успешен: {'✅' if accessibility['ping_success'] else '❌'}")

    print("\n📊 РЕЗУЛЬТАТЫ:")
    print(f"   Локальное подключение: {'быстрое' if connection_time < 2 else 'медленное'} ({connection_time:.2f}с)")
    print(f"   Инициализация VPN: {'быстрая' if init_time < 1 else 'медленная'} ({init_time:.2f}с)")
    print(f"   Проверка доступности: {'быстрая' if check_time < 2 else 'медленная'} ({check_time:.2f}с)")

    total_time = connection_time + init_time + check_time
    print(".2f"
    if total_time < 5:
        print("✅ ПРОИЗВОДИТЕЛЬНОСТЬ: ОТЛИЧНАЯ")
    elif total_time < 10:
        print("⚠️ ПРОИЗВОДИТЕЛЬНОСТЬ: ХОРОШАЯ")
    else:
        print("❌ ПРОИЗВОДИТЕЛЬНОСТЬ: ТРЕБУЕТ ОПТИМИЗАЦИИ")

if __name__ == "__main__":
    test_connection_performance()

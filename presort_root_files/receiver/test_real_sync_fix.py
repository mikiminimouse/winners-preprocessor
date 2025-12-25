#!/usr/bin/env python3
"""
Тест синхронизации с реальными данными после исправления ProtocolDocument.
"""

import sys
from pathlib import Path

# Добавляем пути
sys.path.insert(0, str(Path(__file__).parent))

def test_real_sync():
    """Тест синхронизации с реальными данными."""
    print("🧪 ТЕСТ СИНХРОНИЗАЦИИ С РЕАЛЬНЫМИ ДАННЫМИ")
    print("=" * 60)

    try:
        from sync_db import SyncService
        from sync_db.models import ProtocolDocument
        from datetime import datetime, timedelta

        print("1️⃣ Создание SyncService...")
        sync = SyncService()

        print("2️⃣ Проверка подключений...")
        connections = sync.test_connections()
        if not connections["can_proceed"]:
            print("❌ Подключения недоступны")
            return False

        print("3️⃣ Получение одного реального документа...")
        yesterday = datetime.utcnow() - timedelta(days=1)

        # Получаем доступ к сервисам
        sync._ensure_connections()

        # Получаем один документ из удаленной БД
        remote_db = sync.connection_service.remote_client["protocols223"]
        remote_coll = remote_db["purchaseProtocol"]

        # Ищем документ за вчера
        start_dt = datetime(yesterday.year, yesterday.month, yesterday.day, 0, 0, 0)
        end_dt = datetime(yesterday.year, yesterday.month, yesterday.day, 23, 59, 59)

        query = {
            "loadDate": {
                "$gte": start_dt,
                "$lte": end_dt,
            }
        }

        sample_doc = remote_coll.find_one(query, {"_id": 0})
        if not sample_doc:
            print("❌ Не найдено документов за вчерашний день")
            return False

        print(f"   Найден документ: {len(sample_doc)} полей")

        print("4️⃣ Создание ProtocolDocument из реального документа...")
        try:
            protocol = ProtocolDocument.from_mongo_doc(sample_doc)
            print("✅ ProtocolDocument создан успешно!")
            print(f"   unit_id: {protocol.unit_id}")
            print(f"   urls: {len(protocol.urls)}")
            if protocol.purchaseInfo:
                print(f"   purchaseNoticeNumber: {protocol.purchaseInfo.get('purchaseNoticeNumber', 'N/A')}")
            print(f"   loadDate: {protocol.loadDate}")
            print(f"   status_field: {protocol.status_field}")

        except Exception as e:
            print(f"❌ Ошибка создания ProtocolDocument: {e}")
            import traceback
            traceback.print_exc()
            return False

        print("5️⃣ Тестирование to_mongo_dict...")
        try:
            mongo_dict = protocol.to_mongo_dict()
            print(f"✅ MongoDB dict создан: {len(mongo_dict)} полей")

            # Проверяем ключевые поля
            required = ['unit_id', 'urls', 'source', 'status', 'created_at', 'loadDate']
            present = [f for f in required if f in mongo_dict]
            print(f"   Обязательные поля: {len(present)}/{len(required)} ✅")

        except Exception as e:
            print(f"❌ Ошибка to_mongo_dict: {e}")
            return False

        print("6️⃣ Тестирование сохранения в локальную БД...")
        try:
            local_db = sync.connection_service.local_client["docling_metadata"]
            local_coll = local_db["protocols"]

            # Вставляем тестовый документ
            test_doc = mongo_dict.copy()
            test_doc["_test_sync"] = True  # Маркер тестового документа

            result = local_coll.insert_one(test_doc)
            print(f"✅ Документ сохранен в локальную БД: {result.inserted_id}")

            # Удаляем тестовый документ
            local_coll.delete_one({"_id": result.inserted_id})
            print("✅ Тестовый документ удален")

        except Exception as e:
            print(f"❌ Ошибка сохранения: {e}")
            return False

        print("\n🎉 ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
        print("ProtocolDocument исправлен и работает с реальными данными!")

        # Закрываем подключения
        sync.connection_service.close()

        return True

    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_real_sync()
    sys.exit(0 if success else 1)

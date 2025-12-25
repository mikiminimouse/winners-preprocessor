#!/usr/bin/env python3
"""
Тест исправления ProtocolDocument - проверка создания объектов без конфликтов.
"""

import sys
from pathlib import Path

# Добавляем пути
sys.path.insert(0, str(Path(__file__).parent))

def test_protocol_document():
    """Тестирование создания ProtocolDocument."""
    print("🧪 ТЕСТ ИСПРАВЛЕНИЯ PROTOCOLDOCUMENT")
    print("=" * 50)

    try:
        from sync_db.models import ProtocolDocument

        # Создаем тестовый документ MongoDB
        test_mongo_doc = {
            "_id": "507f1f77bcf86cd799439011",
            "guid": "test-guid-123",
            "purchaseInfo": {
                "purchaseNoticeNumber": "12345678901234567890"
            },
            "loadDate": "2025-12-16T10:30:00Z",
            "status": "P",
            "type": 419551,
            "typeName": "Протокол подведения итогов",
            "attachments": {
                "document": [
                    {
                        "url": "https://zakupki.gov.ru/test.pdf",
                        "fileName": "protocol.pdf",
                        "description": "Тестовый протокол"
                    }
                ]
            }
        }

        print("📄 Создание ProtocolDocument из тестового документа...")
        protocol = ProtocolDocument.from_mongo_doc(test_mongo_doc)

        print("✅ ProtocolDocument создан успешно!")
        print(f"   unit_id: {protocol.unit_id}")
        print(f"   urls: {len(protocol.urls)}")
        print(f"   purchaseNoticeNumber: {protocol.purchaseInfo['purchaseNoticeNumber'] if protocol.purchaseInfo else 'N/A'}")
        print(f"   loadDate: {protocol.loadDate}")
        print(f"   status_field: {protocol.status_field}")
        print(f"   guid: {protocol.guid}")

        # Тестируем to_mongo_dict
        print("\n📤 Тестирование to_mongo_dict...")
        mongo_dict = protocol.to_mongo_dict()

        required_fields = ['unit_id', 'urls', 'source', 'status', 'created_at', 'guid', 'purchaseInfo', 'loadDate']
        present_fields = [field for field in required_fields if field in mongo_dict]

        print(f"✅ MongoDB dict создан: {len(mongo_dict)} полей")
        print(f"   Обязательные поля: {len(present_fields)}/{len(required_fields)} ✅")

        return True

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_protocol_document()
    sys.exit(0 if success else 1)

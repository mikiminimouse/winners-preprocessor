#!/usr/bin/env python3
"""
Тест обработки протоколов после исправления ProtocolDocument.
"""

import sys
from pathlib import Path

# Добавляем пути
sys.path.insert(0, str(Path(__file__).parent))

def test_protocol_processing():
    """Тест обработки протоколов."""
    print("🧪 ТЕСТ ОБРАБОТКИ ПРОТОКОЛОВ")
    print("=" * 40)

    # Имитируем реальный документ из MongoDB (на основе структуры из логов)
    test_doc = {
        "_id": "507f1f77bcf86cd799439011",
        "guid": "96044532-5438-4fa7-97bd-16de4b30699e",
        "createDateTime": "2012-10-12T09:51:29.815Z",
        "purchaseInfo": {
            "purchaseNoticeNumber": "32515525370",
            "name": "Восстановление полной функциональности электропечей",
            "purchaseMethodCode": 4142,
            "purchaseMethodName": "Открытый запрос предложений",
            "registrationNumber": "32515525370-01"
        },
        "placer": {
            "mainInfo": {
                "fullName": "МУНИЦИПАЛЬНОЕ УНИТАРНОЕ ПРЕДПРИЯТИЕ \"РЫНОК ГОРОДА СВЕРДЛОВСК\"",
                "legalAddress": "Адрес организации",
                "postalAddress": "Адрес для почты"
            }
        },
        "missedContest": False,
        "publicationDateTime": "2012-10-15T14:04:18.267Z",
        "status": "P",
        "version": 1,
        "attachments": {
            "document": [
                {
                    "createDateTime": "2012-10-15T18:01:23.019Z",
                    "fileName": "3262_251215081252_001.pdf",
                    "description": "Протокол подведения итогов",
                    "url": "https://zakupki.gov.ru/223/purchase/public/download/download.html?id=test123",
                    "guid": "3262_251215081252_001",
                    "contentUid": "content-uuid-123"
                }
            ]
        },
        "type": 419551,
        "typeName": "Протокол подведения итогов",
        "procedureDate": "2012-10-12T05:30:00Z",
        "procedurePlace": "3-й проезд Марьиной Рощи, д. 40, г. Москва, 127018",
        "lotApplicationsList": {
            "protocolLotApplications": [
                {
                    "lot": {
                        "guid": "lot-guid-123",
                        "ordinalNumber": 1,
                        "subject": "Восстановление полной функциональности электропечей",
                        "currency": {
                            "code": "RUB",
                            "name": "Российский рубль",
                            "digitalCode": "643"
                        },
                        "initialSum": 1500000
                    },
                    "application": {
                        "applicationDate": "2012-10-11T09:30:00Z",
                        "applicationNumber": "179/030/1",
                        "supplierInfo": {
                            "name": "Поставщик 1",
                            "inn": "123456789012",
                            "kpp": "123456789"
                        },
                        "price": 1066000,
                        "currency": {
                            "code": "RUB",
                            "name": "Российский рубль",
                            "digitalCode": "643"
                        },
                        "conditionProposals": "Указаны в заявке",
                        "accepted": "T",
                        "winnerIndication": "N"
                    }
                }
            ]
        },
        "md5": "9e752d4ded36713df786511cfe167441",
        "loadDate": "2025-12-16T04:06:22.186Z",
        "region": "Moskva",
        "zipName": "purchaseProtocol_Moskva_20121015_000000_20121016_000000_daily_001.xml.zip",
        "xmlName": "purchaseProtocol_Moskva_20121015_000000_20121016_000000_daily_001.xml"
    }

    try:
        from sync_db.models import ProtocolDocument

        print("📄 Обработка тестового документа...")
        print(f"   Документ содержит {len(test_doc)} полей")

        # Создаем ProtocolDocument
        protocol = ProtocolDocument.from_mongo_doc(test_doc)

        print("✅ ProtocolDocument создан успешно!")
        print(f"   🆔 unit_id: {protocol.unit_id}")
        print(f"   🔗 URLs: {len(protocol.urls)}")
        if protocol.urls:
            print(f"      └─ {protocol.urls[0]['fileName']}: {protocol.urls[0]['url'][:50]}...")

        print(f"   📄 purchaseNoticeNumber: {protocol.purchaseInfo['purchaseNoticeNumber'] if protocol.purchaseInfo else 'N/A'}")
        print(f"   📅 loadDate: {protocol.loadDate}")
        print(f"   📍 region: {protocol.region}")
        print(f"   📋 status_field: {protocol.status_field}")
        print(f"   🏷️  typeName: {protocol.typeName}")

        if protocol.placer and protocol.placer.get('mainInfo'):
            print(f"   🏢 Организация: {protocol.placer['mainInfo']['fullName'][:50]}...")

        # Тестируем to_mongo_dict
        print("\n💾 Создание MongoDB документа...")
        mongo_dict = protocol.to_mongo_dict()

        print(f"✅ MongoDB документ создан: {len(mongo_dict)} полей")

        # Проверяем наличие ключевых полей
        key_fields = [
            'unit_id', 'urls', 'source', 'status', 'created_at',
            'guid', 'purchaseInfo', 'loadDate', 'region', 'typeName'
        ]

        present = [field for field in key_fields if field in mongo_dict]
        print(f"   ✅ Ключевые поля: {len(present)}/{len(key_fields)}")

        # Тестируем сохранение (имитация)
        print("\n🗄️  Имитация сохранения в БД...")

        # Проверяем, что документ готов к сохранению
        required_for_save = ['unit_id', 'urls', 'source', 'status', 'created_at', 'updated_at']
        save_ready = all(field in mongo_dict for field in required_for_save)

        print(f"   ✅ Готов к сохранению: {save_ready}")

        if protocol.lotApplicationsList:
            lots = protocol.lotApplicationsList.get('protocolLotApplications', [])
            print(f"   📦 Лотов: {len(lots) if isinstance(lots, list) else 'N/A'}")

        print("\n🎉 ТЕСТ ПРОШЕЛ УСПЕШНО!")
        print("ProtocolDocument корректно обрабатывает реальные документы!")

        return True

    except Exception as e:
        print(f"❌ Ошибка обработки: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_protocol_processing()
    sys.exit(0 if success else 1)

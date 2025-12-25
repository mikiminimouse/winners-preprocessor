#!/usr/bin/env python3
"""
Тестовый скрипт для прямого подключения к MongoDB и получения URLs документов по дате.
Использует те же методы, что и router/main.py, но работает напрямую без запуска сервера.
"""
import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import PyMongoError

# Загружаем переменные из .env
load_dotenv()

# Конфигурация из переменных окружения
# Используем mongoServer (для MCP) или MONGO_SERVER (для router)
MONGO_SERVER = os.environ.get("MONGO_SERVER") or os.environ.get("mongoServer")
MONGO_USER = os.environ.get("MONGO_USER") or os.environ.get("readAllUser")
MONGO_PASSWORD = os.environ.get("MONGO_PASSWORD") or os.environ.get("readAllPassword")
MONGO_SSL_CERT = os.environ.get("MONGO_SSL_CERT") or os.environ.get("sslCertPath")
MONGO_PROTOCOLS_DB = os.environ.get("MONGO_PROTOCOLS_DB", "protocols223")
MONGO_PROTOCOLS_COLLECTION = os.environ.get("MONGO_PROTOCOLS_COLLECTION", "purchaseProtocol")
PROTOCOLS_COUNT_LIMIT = int(os.environ.get("PROTOCOLS_COUNT_LIMIT") or os.environ.get("protocolsCountLimit", "500"))

# Глобальный клиент MongoDB
_mongo_client: Optional[MongoClient] = None


def get_mongo_client() -> Optional[MongoClient]:
    """Получает или создает MongoDB клиент для чтения протоколов."""
    global _mongo_client
    
    if _mongo_client is not None:
        try:
            # Проверяем, что клиент еще жив
            _mongo_client.admin.command('ping')
            return _mongo_client
        except Exception:
            # Если клиент мертв, создаем новый
            _mongo_client = None
    
    if not all([MONGO_SERVER, MONGO_USER, MONGO_PASSWORD]):
        print("ОШИБКА: Не все необходимые переменные MongoDB найдены в .env файле")
        print(f"  MONGO_SERVER: {'✓' if MONGO_SERVER else '✗'}")
        print(f"  MONGO_USER: {'✓' if MONGO_USER else '✗'}")
        print(f"  MONGO_PASSWORD: {'✓' if MONGO_PASSWORD else '✗'}")
        return None
    
    try:
        url_mongo = f'mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_SERVER}/?authSource=protocols223'
        
        print(f"Подключение к MongoDB: {MONGO_SERVER}")
        print(f"Пользователь: {MONGO_USER}")
        print(f"SSL сертификат: {MONGO_SSL_CERT if MONGO_SSL_CERT else 'не используется'}")
        
        # Если указан SSL сертификат, используем SSL подключение
        if MONGO_SSL_CERT:
            if not os.path.exists(MONGO_SSL_CERT):
                print(f"ОШИБКА: SSL сертификат не найден: {MONGO_SSL_CERT}")
                return None
            
            _mongo_client = MongoClient(
                url_mongo,
                tls=True,
                authMechanism="SCRAM-SHA-1",
                tlsAllowInvalidHostnames=True,
                tlsCAFile=MONGO_SSL_CERT
            )
        else:
            # Локальное подключение без SSL
            _mongo_client = MongoClient(url_mongo)
        
        # Проверяем подключение
        _mongo_client.admin.command('ping')
        print("✓ Подключение к MongoDB успешно!")
        return _mongo_client
    except Exception as e:
        print(f"ОШИБКА подключения к MongoDB: {e}")
        return None


def get_protocols_by_date(date_str: str) -> Dict[str, Any]:
    """
    Получает протоколы по дате из MongoDB и извлекает purchaseNoticeNumber и URL вложений.
    Возвращает словарь: {purchaseNoticeNumber: {url, fileName} или [{url, fileName}, ...]}
    """
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"Неверный формат даты '{date_str}'. Используйте формат YYYY-MM-DD")
    
    client = get_mongo_client()
    if not client:
        raise Exception("MongoDB не настроен или недоступен")
    
    try:
        db = client[MONGO_PROTOCOLS_DB]
        collection = db[MONGO_PROTOCOLS_COLLECTION]
        
        print(f"\nЗапрос протоколов из базы: {MONGO_PROTOCOLS_DB}")
        print(f"Коллекция: {MONGO_PROTOCOLS_COLLECTION}")
        print(f"Дата: {date_str}")
        print(f"Лимит: {PROTOCOLS_COUNT_LIMIT}")
        
        # Создаем запрос для поиска по дате
        start_of_day = datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0)
        end_of_day = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59)
        
        query = {
            "loadDate": {
                "$gte": start_of_day,
                "$lte": end_of_day
            }
        }
        
        result_dict = {}
        protocols = collection.find(query).limit(PROTOCOLS_COUNT_LIMIT)
        
        protocol_count = 0
        for protocol in protocols:
            protocol_count += 1
            purchase_info = protocol.get('purchaseInfo', {})
            purchase_notice_number = purchase_info.get('purchaseNoticeNumber')
            attachments = protocol.get('attachments', {})
            documents = attachments.get('document', [])
            
            # Если documents - это один документ (словарь), превращаем в список
            if isinstance(documents, dict):
                documents = [documents]
            
            urls = []
            for doc in documents:
                if isinstance(doc, dict) and 'url' in doc:
                    urls.append({
                        "url": doc.get('url'),
                        "fileName": doc.get('fileName', '')
                    })
            
            if purchase_notice_number and urls:
                # Если только один URL, сохраняем как объект, иначе как список
                if len(urls) == 1:
                    result_dict[purchase_notice_number] = urls[0]
                else:
                    result_dict[purchase_notice_number] = urls
        
        print(f"\n✓ Найдено протоколов: {protocol_count}")
        print(f"✓ Протоколов с документами: {len(result_dict)}")
        
        return result_dict
    
    except PyMongoError as e:
        raise Exception(f"MongoDB error: {str(e)}")
    except Exception as e:
        raise Exception(f"Error: {str(e)}")


def main():
    """Основная функция для тестирования."""
    print("=" * 60)
    print("Тестирование подключения к MongoDB и получения протоколов")
    print("=" * 60)
    
    # Проверяем конфигурацию
    if not MONGO_SERVER:
        print("\nОШИБКА: Адрес MongoDB сервера не указан в .env файле!")
        print("Пожалуйста, укажите адрес MongoDB сервера в одном из форматов:")
        print("  Для MCP сервера: mongoServer=host:port")
        print("  Для router: MONGO_SERVER=host:port")
        print("\nПримеры:")
        print("  mongoServer=mongo.example.com:27017")
        print("  MONGO_SERVER=mongo.example.com:27017")
        print("  Или для кластера: mongoServer=host1:port1,host2:port2,host3:port3")
        sys.exit(1)
    
    # Тестируем подключение
    print("\n1. Тестирование подключения к MongoDB...")
    client = get_mongo_client()
    if not client:
        print("\n✗ Не удалось подключиться к MongoDB")
        sys.exit(1)
    
    # Проверяем доступность базы и коллекции
    print("\n2. Проверка доступности базы данных...")
    try:
        db = client[MONGO_PROTOCOLS_DB]
        collection = db[MONGO_PROTOCOLS_COLLECTION]
        
        # Проверяем количество документов в коллекции.
        # ВАЖНО: для удалённого прод-кластера используем быструю оценку
        # по метаданным, а не полный count_documents({}), чтобы не ловить таймауты.
        try:
            total_count = collection.estimated_document_count()
        except Exception as e_count:
            print(f"⚠ Не удалось получить оценочное количество документов: {e_count}")
            total_count = None
        
        print(f"✓ База данных '{MONGO_PROTOCOLS_DB}' доступна")
        print(f"✓ Коллекция '{MONGO_PROTOCOLS_COLLECTION}' доступна")
        if total_count is not None:
            print(f"✓ Оценочное количество документов в коллекции: {total_count}")
        
        # Проверяем структуру одного документа
        sample = collection.find_one({})
        if sample:
            print(f"\nПример структуры документа:")
            print(f"  - purchaseInfo: {'✓' if 'purchaseInfo' in sample else '✗'}")
            print(f"  - attachments: {'✓' if 'attachments' in sample else '✗'}")
            print(f"  - loadDate: {'✓' if 'loadDate' in sample else '✗'}")
    except Exception as e:
        print(f"✗ Ошибка при проверке базы данных: {e}")
        sys.exit(1)
    
    # Получаем протоколы по дате (если дата указана)
    if len(sys.argv) > 1:
        date_str = sys.argv[1]
        print(f"\n3. Получение протоколов за дату: {date_str}...")
        try:
            protocols = get_protocols_by_date(date_str)
            
            # Сохраняем результаты в JSON
            output_file = f"test_protocols_{date_str}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "date": date_str,
                    "protocols_count": len(protocols),
                    "protocols": protocols
                }, f, ensure_ascii=False, indent=2)
            
            print(f"\n✓ Результаты сохранены в: {output_file}")
            
            # Подсчитываем общее количество URLs
            total_urls = 0
            for purchase_number, doc_info in protocols.items():
                if isinstance(doc_info, dict):
                    total_urls += 1
                elif isinstance(doc_info, list):
                    total_urls += len(doc_info)
            
            print(f"✓ Всего URLs документов: {total_urls}")
            
        except Exception as e:
            print(f"\n✗ Ошибка при получении протоколов: {e}")
            sys.exit(1)
    else:
        print("\n3. Для получения протоколов укажите дату в формате YYYY-MM-DD")
        print("   Пример: python test_mongo_direct.py 2025-01-17")
    
    # Закрываем подключение
    if _mongo_client:
        _mongo_client.close()
        print("\n✓ Подключение закрыто")
    
    print("\n" + "=" * 60)
    print("Тестирование завершено")
    print("=" * 60)


if __name__ == "__main__":
    main()


#!/usr/bin/env python3
"""Простая проверка доступности чтения из MongoDB."""
import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

mongo_hosts = os.getenv('mongoServer')
username = os.getenv('readAllUser')
password = os.getenv('readAllPassword')
ssl_cert = os.getenv('sslCertPath')

print('=' * 60)
print('ПРОВЕРКА ДОСТУПНОСТИ ЧТЕНИЯ ИЗ MONGODB')
print('=' * 60)
print(f'Хосты: {mongo_hosts}')
print(f'Пользователь: {username}')
print(f'SSL сертификат: {ssl_cert}')
print()

try:
    url_mongo = f'mongodb://{username}:{password}@{mongo_hosts}/?authSource=protocols223'
    print('Подключение к MongoDB...')
    
    print(f'URL подключения: mongodb://{username}:***@{mongo_hosts}/?authSource=protocols223')
    
    client = MongoClient(
        url_mongo,
        tls=True,
        authMechanism='SCRAM-SHA-1',
        tlsAllowInvalidHostnames=True,
        tlsCAFile=ssl_cert,
        serverSelectionTimeoutMS=10000,
        connectTimeoutMS=10000,
        socketTimeoutMS=10000
    )
    
    print('Ожидание ответа от сервера...')
    
    # Проверка подключения
    client.admin.command('ping')
    print('✓ Подключение успешно!')
    print()
    
    # Проверка базы данных
    db = client['protocols223']
    collection = db['purchaseProtocol']
    
    # ВАЖНО: не делаем полный count_documents({}) по удалённой прод-коллекции —
    # это может быть очень дорого и приводить к таймаутам.
    # Для быстрой проверки используем estimated_document_count(),
    # который опирается на метаданные и значительно легче для кластера.
    try:
        total_estimated = collection.estimated_document_count()
        print(f'✓ Оценочное количество документов в коллекции: {total_estimated:,}')
    except Exception as e_count:
        print(f'⚠ Не удалось получить оценочное количество документов: {e_count}')
    
    # Проверка структуры документа
    sample = collection.find_one({})
    if sample:
        print()
        print('Структура документа:')
        keys = ['purchaseInfo', 'attachments', 'loadDate', 'purchaseNoticeNumber']
        for key in keys:
            status = '✓' if key in sample else '✗'
            print(f'  - {key}: {status}')
        
        if 'purchaseNoticeNumber' in sample:
            pn = sample.get('purchaseNoticeNumber', 'N/A')
            print(f'  Пример purchaseNoticeNumber: {str(pn)[:50]}')
        
        if 'attachments' in sample and isinstance(sample['attachments'], list):
            print(f'  Вложений в примере: {len(sample["attachments"])}')
    
    # Проверка по дате (реальный рабочий сценарий)
    from datetime import datetime
    test_date = datetime(2025, 1, 17)
    count_by_date = collection.count_documents({
        'loadDate': {
            '$gte': datetime(test_date.year, test_date.month, test_date.day),
            '$lt': datetime(test_date.year, test_date.month, test_date.day + 1)
        }
    })
    print()
    print(f'✓ Документов за {test_date.strftime("%Y-%m-%d")}: {count_by_date:,}')
    
    client.close()
    print()
    print('=' * 60)
    print('✓ ПРОВЕРКА ЗАВЕРШЕНА УСПЕШНО')
    print('=' * 60)
    
except Exception as e:
    print(f'✗ ОШИБКА: {e}')
    import traceback
    traceback.print_exc()


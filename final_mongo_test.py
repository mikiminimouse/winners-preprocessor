#!/usr/bin/env python3
"""
Финальный тест: прямое подключение к MongoDB с максимальными таймаутами
"""
import os
import sys
import signal
from pathlib import Path
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

mongo_hosts = os.getenv('mongoServer')
username = os.getenv('readAllUser')
password = os.getenv('readAllPassword')
ssl_cert = os.getenv('sslCertPath')

print('=' * 70)
print('ФИНАЛЬНЫЙ ТЕСТ: ПРЯМОЕ ПОДКЛЮЧЕНИЕ К MONGODB')
print('=' * 70)
print(f'Хосты: {mongo_hosts}')
print(f'Пользователь: {username}')
print(f'SSL сертификат: {ssl_cert}')
print()

def timeout_handler(signum, frame):
    print("\n✗ ТАЙМАУТ: Подключение не установлено за 90 секунд")
    print("   Это может означать:")
    print("   - Сервер не отвечает")
    print("   - Проблемы с сетью")
    print("   - Требуется дополнительная настройка")
    sys.exit(1)

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(90)  # 90 секунд максимум

try:
    url_mongo = f'mongodb://{username}:{password}@{mongo_hosts}/?authSource=protocols223'
    
    print('Подключение с таймаутами:')
    print('  - serverSelectionTimeoutMS: 60000 (60 сек)')
    print('  - connectTimeoutMS: 60000 (60 сек)')
    print('  - socketTimeoutMS: 60000 (60 сек)')
    print()
    print('Ожидание ответа...')
    
    client = MongoClient(
        url_mongo,
        tls=True,
        authMechanism='SCRAM-SHA-1',
        tlsAllowInvalidHostnames=True,
        tlsCAFile=ssl_cert,
        serverSelectionTimeoutMS=60000,
        connectTimeoutMS=60000,
        socketTimeoutMS=60000
    )
    
    print('Выполнение ping...')
    result = client.admin.command('ping')
    signal.alarm(0)  # Отключаем таймер
    
    print(f'✓ Ping успешен: {result}')
    print()
    
    # Получение данных
    db = client['protocols223']
    collection = db['purchaseProtocol']
    
    # Не штурмуем прод-коллекцию полным count_documents({}) — это может
    # быть очень тяжёлым запросом из удалённого окружения и приводить к таймаутам.
    # Здесь достаточно быстрой оценки по метаданным.
    try:
        total = collection.estimated_document_count()
        print(f'✓ Оценочное количество документов: {total:,}')
    except Exception as e_count:
        print(f'⚠ Не удалось получить оценочное количество документов: {e_count}')
    
    # Тест получения URLs
    sample = collection.find_one({})
    if sample:
        atts = sample.get('attachments', [])
        if isinstance(atts, list) and len(atts) > 0:
            urls_count = sum(1 for att in atts if isinstance(att, dict) and att.get('url'))
            print(f'✓ В примере документа найдено URLs: {urls_count}')
    
    client.close()
    
    print()
    print('=' * 70)
    print('✅ УСПЕХ! ПРЯМОЕ ПОДКЛЮЧЕНИЕ РАБОТАЕТ!')
    print('=' * 70)
    print()
    print('ВЫВОД: Можно получать URLs протоколов напрямую БЕЗ MCP!')
    
except Exception as e:
    signal.alarm(0)
    print()
    print('=' * 70)
    print('✗ ОШИБКА ПОДКЛЮЧЕНИЯ')
    print('=' * 70)
    print(f'Ошибка: {e}')
    print()
    print('ВЫВОД: Прямое подключение не работает в текущем окружении.')
    print('       Используйте MCP сервер для получения данных.')
    sys.exit(1)


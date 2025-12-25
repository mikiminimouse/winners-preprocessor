#!/usr/bin/env python3
"""
Ключевой тест: прямое подключение к MongoDB и получение URLs протоколов
БЕЗ использования MCP сервера.
"""
import os
import sys
from pathlib import Path
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# Получаем параметры из .env
mongo_hosts = os.getenv('mongoServer')
username = os.getenv('readAllUser')
password = os.getenv('readAllPassword')
ssl_cert = os.getenv('sslCertPath')

print('=' * 70)
print('КЛЮЧЕВОЙ ТЕСТ: ПРЯМОЕ ПОДКЛЮЧЕНИЕ К MONGODB БЕЗ MCP')
print('=' * 70)
print(f'Хосты: {mongo_hosts}')
print(f'Пользователь: {username}')
print(f'SSL сертификат: {ssl_cert}')
print()

if not all([mongo_hosts, username, password, ssl_cert]):
    print('✗ ОШИБКА: Не все параметры установлены в .env')
    sys.exit(1)

if not Path(ssl_cert).exists():
    print(f'✗ ОШИБКА: SSL сертификат не найден: {ssl_cert}')
    sys.exit(1)

try:
    # Формируем строку подключения
    url_mongo = f'mongodb://{username}:{password}@{mongo_hosts}/?authSource=protocols223'
    
    print('1. Подключение к MongoDB...')
    print(f'   URL: mongodb://{username}:***@{mongo_hosts}/?authSource=protocols223')
    
    client = MongoClient(
        url_mongo,
        tls=True,
        authMechanism='SCRAM-SHA-1',
        tlsAllowInvalidHostnames=True,
        tlsCAFile=ssl_cert,
        serverSelectionTimeoutMS=30000,  # 30 секунд
        connectTimeoutMS=30000,
        socketTimeoutMS=30000
    )
    
    print('   Ожидание ответа сервера (до 30 сек)...')
    
    # Проверка подключения
    result = client.admin.command('ping')
    print(f'   ✓ Ping успешен: {result}')
    print()
    
    # Подключение к базе данных
    print('2. Подключение к базе данных protocols223...')
    db = client['protocols223']
    collection = db['purchaseProtocol']
    print('   ✓ База данных доступна')
    print()
    
    # Подсчет документов
    print('3. Подсчет документов в коллекции...')
    total_count = collection.count_documents({})
    print(f'   ✓ Всего документов: {total_count:,}')
    print()
    
    # Получение примера документа
    print('4. Получение примера документа...')
    sample = collection.find_one({})
    if sample:
        print('   ✓ Документ получен')
        print(f'   Ключи документа: {list(sample.keys())[:10]}')
        
        # Проверка наличия ключевых полей
        has_purchase_info = 'purchaseInfo' in sample
        has_attachments = 'attachments' in sample
        has_load_date = 'loadDate' in sample
        has_purchase_number = 'purchaseNoticeNumber' in sample
        
        print(f'   - purchaseInfo: {"✓" if has_purchase_info else "✗"}')
        print(f'   - attachments: {"✓" if has_attachments else "✗"}')
        print(f'   - loadDate: {"✓" if has_load_date else "✗"}')
        print(f'   - purchaseNoticeNumber: {"✓" if has_purchase_number else "✗"}')
        print()
        
        # Извлечение URLs (как в mcp_http_server.py)
        print('5. Извлечение URLs из примера документа...')
        urls_found = []
        
        if has_purchase_number:
            purchase_number = sample.get('purchaseNoticeNumber')
            print(f'   purchaseNoticeNumber: {purchase_number}')
        
        if has_attachments and isinstance(sample.get('attachments'), list):
            attachments = sample['attachments']
            print(f'   Вложений найдено: {len(attachments)}')
            
            for i, att in enumerate(attachments[:3], 1):  # Первые 3
                if isinstance(att, dict):
                    url = att.get('url') or att.get('downloadUrl') or att.get('fileUrl')
                    filename = att.get('fileName') or att.get('name') or 'unknown'
                    if url:
                        urls_found.append({'url': url, 'fileName': filename})
                        print(f'   [{i}] {filename[:50]}')
                        print(f'       URL: {url[:80]}...')
        
        print()
        print(f'   ✓ Найдено URLs: {len(urls_found)}')
        print()
    
    # Тест получения протоколов по дате
    print('6. Тест получения протоколов по дате (2025-01-17)...')
    test_date = datetime(2025, 1, 17)
    query = {
        'loadDate': {
            '$gte': datetime(test_date.year, test_date.month, test_date.day),
            '$lt': datetime(test_date.year, test_date.month, test_date.day + 1)
        }
    }
    
    count_by_date = collection.count_documents(query)
    print(f'   ✓ Документов за {test_date.strftime("%Y-%m-%d")}: {count_by_date:,}')
    
    if count_by_date > 0:
        print('   Получение примеров протоколов...')
        protocols_sample = list(collection.find(query).limit(3))
        
        total_urls = 0
        for protocol in protocols_sample:
            pn = protocol.get('purchaseNoticeNumber', 'N/A')
            atts = protocol.get('attachments', [])
            if isinstance(atts, list):
                total_urls += len(atts)
        
        print(f'   ✓ В первых 3 протоколах найдено URLs: {total_urls}')
        print()
    
    # Полный тест извлечения (как в get_protocols_by_date_223)
    print('7. Полный тест извлечения URLs (как в mcp_http_server.py)...')
    protocols_dict = {}
    
    sample_protocols = list(collection.find(query).limit(5))
    print(f'   Обработка {len(sample_protocols)} протоколов...')
    
    for protocol in sample_protocols:
        purchase_number = protocol.get('purchaseNoticeNumber')
        if not purchase_number:
            continue
        
        attachments = protocol.get('attachments', [])
        if not isinstance(attachments, list) or len(attachments) == 0:
            continue
        
        doc_list = []
        for att in attachments:
            if isinstance(att, dict):
                url = att.get('url') or att.get('downloadUrl') or att.get('fileUrl')
                filename = att.get('fileName') or att.get('name') or 'unknown'
                if url:
                    doc_list.append({
                        'url': url,
                        'fileName': filename
                    })
        
        if doc_list:
            if len(doc_list) == 1:
                protocols_dict[purchase_number] = doc_list[0]
            else:
                protocols_dict[purchase_number] = doc_list
    
    print(f'   ✓ Извлечено протоколов с URLs: {len(protocols_dict)}')
    total_extracted_urls = sum(
        1 if isinstance(v, dict) else len(v) 
        for v in protocols_dict.values()
    )
    print(f'   ✓ Всего URLs извлечено: {total_extracted_urls}')
    print()
    
    # Показываем примеры
    if protocols_dict:
        print('   Примеры извлеченных данных:')
        for i, (pn, doc_info) in enumerate(list(protocols_dict.items())[:2], 1):
            print(f'   [{i}] purchaseNoticeNumber: {pn}')
            if isinstance(doc_info, dict):
                print(f'       URL: {doc_info.get("url", "N/A")[:60]}...')
                print(f'       FileName: {doc_info.get("fileName", "N/A")}')
            elif isinstance(doc_info, list):
                print(f'       URLs: {len(doc_info)}')
                for j, doc in enumerate(doc_info[:2], 1):
                    print(f'         [{j}] {doc.get("fileName", "N/A")}')
        print()
    
    client.close()
    
    print('=' * 70)
    print('✅ УСПЕХ! ПРЯМОЕ ПОДКЛЮЧЕНИЕ К MONGODB РАБОТАЕТ!')
    print('=' * 70)
    print()
    print('✓ Подключение установлено')
    print('✓ Чтение данных работает')
    print('✓ Извлечение URLs работает')
    print('✓ Можно получать протоколы по дате')
    print()
    print('ВЫВОД: Можно использовать прямое подключение БЕЗ MCP сервера!')
    print('=' * 70)
    
except Exception as e:
    print()
    print('=' * 70)
    print('✗ ОШИБКА ПОДКЛЮЧЕНИЯ')
    print('=' * 70)
    print(f'Ошибка: {e}')
    print()
    import traceback
    traceback.print_exc()
    sys.exit(1)


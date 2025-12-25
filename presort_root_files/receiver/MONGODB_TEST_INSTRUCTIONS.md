# ИНСТРУКЦИИ ПО ТЕСТИРОВАНИЮ ПОДКЛЮЧЕНИЯ К MONGODB

## Найденные секреты подключения

### Удаленная MongoDB (protocols223.purchaseProtocol)
```
Сервер: 87.242.92.79:8635,178.170.193.76:8635
Пользователь: readProtocols223
Пароль: cei8saht8UCh3oka4geegheuwahzoph2
SSL сертификат: /root/winners_preprocessor/certs/sber2.crt
База данных: protocols223
Коллекция: purchaseProtocol
```

### Локальная MongoDB (docling_metadata.protocols)
```
Сервер: localhost:27017
Пользователь: admin
Пароль: password
База данных: docling_metadata
Коллекция: protocols
```

## Важно: VPN обязателен

Для доступа к удаленной MongoDB **необходимо VPN подключение**. Без VPN серверы недоступны.

### Проверка доступности серверов без VPN
```bash
# Проверяем доступность портов
timeout 5 bash -c "</dev/tcp/87.242.92.79/8635" && echo "OPEN" || echo "CLOSED"
timeout 5 bash -c "</dev/tcp/178.170.193.76/8635" && echo "OPEN" || echo "CLOSED"
# Результат: CLOSED (без VPN)
```

## Ручное тестирование подключения

### 1. Подключение к VPN
```bash
# Запустить OpenVPN
sudo openvpn --config /root/winners_preprocessor/vitaly_bychkov.ovpn

# В другом терминале проверить подключение
curl -s https://zakupki.gov.ru | head -1
# Должно показать HTML контент
```

### 2. Тестирование MongoDB подключения
```bash
# После подключения VPN запустить тест
cd /root/winners_preprocessor
python3 test_mcp_mongo_connection.py
```

### 3. Запуск синхронизации протоколов
```bash
# Синхронизация через CLI
cd /root/winners_preprocessor/preprocessing
source venv/bin/activate
python3 run_cli.py
# Выбрать пункт 1: "Синхронизация протоколов из MongoDB"
```

## Структура данных MongoDB

### Удаленная БД (protocols223.purchaseProtocol)
```javascript
{
  "_id": ObjectId("..."),
  "purchaseInfo": {
    "purchaseNoticeNumber": "01234567890123456789"
  },
  "attachments": {
    "document": [
      {
        "url": "https://zakupki.gov.ru/...",
        "fileName": "Протокол подведения итогов.pdf",
        "guid": "uuid-string",
        "contentUid": "content-uuid",
        "description": "Протокол подведения итогов"
      }
    ]
  },
  "loadDate": ISODate("2024-12-17T12:00:00.000Z")
}
```

### Локальная БД (docling_metadata.protocols)
```javascript
{
  "_id": ObjectId("..."),
  "unit_id": "UNIT_a1b2c3d4e5f6789a",
  "purchaseNoticeNumber": "01234567890123456789",
  "loadDate": ISODate("2024-12-17T12:00:00.000Z"),
  "urls": [...],  // Из attachments
  "multi_url": false,
  "url_count": 1,
  "source": "remote_mongo",
  "status": "pending",
  "created_at": ISODate("..."),
  "updated_at": ISODate("...")
}
```

## Процесс синхронизации

1. **Подключение к удаленной MongoDB** через VPN
2. **Запрос протоколов** за указанную дату (по умолчанию вчера)
3. **Извлечение URL** из поля `attachments`
4. **Генерация unit_id** в формате `UNIT_<16hex>`
5. **Проверка дубликатов** по `purchaseNoticeNumber + source`
6. **Сохранение** в локальную MongoDB с статусом `pending`

## Тестирование без VPN (локальная разработка)

Для тестирования без VPN можно использовать mock-данные:

```bash
cd /root/winners_preprocessor/preprocessing
source venv/bin/activate
python3 test_sync_local_only.py
```

Этот тест:
- Создает mock данные для удаленной MongoDB
- Синхронизирует их в локальную MongoDB
- Проверяет корректность структуры данных

## Диагностика проблем

### Проблема: "No servers found yet"
**Решение**: Проверить VPN подключение
```bash
curl -s https://zakupki.gov.ru | grep -o "<title>.*</title>"
# Должно показать: <title>Официальный сайт для размещения информации о размещении заказов</title>
```

### Проблема: "Authentication failed"
**Решение**: Проверить credentials в коде
```python
# Правильные параметры
mongo_hosts = "87.242.92.79:8635,178.170.193.76:8635"
username = "readProtocols223"
password = "cei8saht8UCh3oka4geegheuwahzoph2"
```

### Проблема: "SSL certificate verify failed"
**Решение**: Проверить путь к сертификату
```bash
ls -la /root/winners_preprocessor/certs/sber2.crt
# Файл должен существовать
```

## Рабочие файлы для тестирования

- `test_mcp_mongo_connection.py` - тест подключения к MongoDB
- `test_mongo_with_vpn.py` - автоматический тест VPN + MongoDB
- `preprocessing/tests/test_protocol_sync.py` - unit тесты
- `preprocessing/tests/test_sync_integration.py` - интеграционный тест
- `preprocessing/test_sync_local_only.py` - тест с mock данными

## Следующие шаги

1. **Подключить VPN** и протестировать реальное подключение к MongoDB
2. **Запустить синхронизацию** за 1 день
3. **Проверить структуру** синхронизированных данных
4. **Интегрировать** синхронизацию в основной pipeline

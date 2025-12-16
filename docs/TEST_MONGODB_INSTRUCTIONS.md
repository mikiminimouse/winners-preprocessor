# Инструкция по тестированию MongoDB подключения

## Текущий статус

✅ Скрипты созданы и готовы к использованию:
- `test_mongo_direct.py` - тестирование подключения и получения URLs
- `test_download_documents.py` - скачивание документов по URLs

✅ Подключение к удалённой MongoDB (`protocols223` → `purchaseProtocol`) протестировано:
- прямое TLS‑подключение по `mongoServer` из `.env` **работает без использования РФ VPN**
- РФ VPN нужен **только** для скачивания файлов с портала `zakupki.gov.ru`, а не для доступа к Mongo

✅ Конфигурация обновлена в `.env`:
- `MONGO_USER=readProtocols223`
- `MONGO_PASSWORD=cei8saht8UCh3oka4geegheuwahzoph2`
- `MONGO_SSL_CERT=/root/winners_preprocessor/certs/sber2.crt`
- `PROTOCOLS_COUNT_LIMIT=500`

## Что нужно сделать

### 1. Указать адрес MongoDB сервера

Отредактируйте файл `.env` и укажите адрес сервера:

```bash
MONGO_SERVER=host:port
```

Или для шардированного кластера:

```bash
MONGO_SERVER=host1:port1,host2:port2,host3:port3
```

### 2. Тестирование подключения

#### Шаг 1: Проверка подключения к MongoDB

```bash
python3 test_mongo_direct.py
```

Этот скрипт:
- Проверит подключение к MongoDB
- Проверит доступность базы `protocols223`
- Проверит коллекцию `purchaseProtocol`
- Покажет структуру документов

#### Шаг 2: Получение протоколов по дате

```bash
python3 test_mongo_direct.py 2025-01-17
```

Этот скрипт:
- Получит протоколы за указанную дату
- Извлечет URLs документов
- Сохранит результаты в `test_protocols_2025-01-17.json`

#### Шаг 3: Скачивание документов

```bash
python3 test_download_documents.py test_protocols_2025-01-17.json
```

Или с указанием директории и лимита:

```bash
python3 test_download_documents.py test_protocols_2025-01-17.json input/test_downloads 500
```

Этот скрипт:
- Скачает документы по URLs из JSON файла
- Сохранит их в указанную директорию (по умолчанию `input/test_downloads`)
- Создаст отчет `download_report_2025-01-17.json`

## Использование через router API (альтернативный способ)

Если router сервер запущен, можно использовать API эндпоинты:

### Получить протоколы по дате:

```bash
curl "http://localhost:8080/protocols/2025-01-17"
```

### Получить и скачать протоколы (полный пайплайн):

```bash
curl -X POST "http://localhost:8080/download_protocols/2025-01-17"
```

Это автоматически:
- Получит протоколы из MongoDB
- Скачает документы
- Обработает их через пайплайн (router → docling → output)

## Структура результатов

### JSON файл с протоколами (`test_protocols_YYYY-MM-DD.json`):

```json
{
  "date": "2025-01-17",
  "protocols_count": 150,
  "protocols": {
    "purchaseNoticeNumber1": {
      "url": "https://example.com/doc1.pdf",
      "fileName": "doc1.pdf"
    },
    "purchaseNoticeNumber2": [
      {
        "url": "https://example.com/doc2.pdf",
        "fileName": "doc2.pdf"
      },
      {
        "url": "https://example.com/doc3.pdf",
        "fileName": "doc3.pdf"
      }
    ]
  }
}
```

### JSON файл с отчетом о скачивании (`download_report_YYYY-MM-DD.json`):

```json
{
  "date": "2025-01-17",
  "timestamp": "2025-01-17T10:00:00",
  "total_protocols": 150,
  "total_urls": 200,
  "downloaded_count": 195,
  "failed_count": 5,
  "skipped_count": 0,
  "downloaded": [...],
  "failed": [...],
  "skipped": [...]
}
```

## Устранение неполадок

### Ошибка: "MONGO_SERVER не указан"

Укажите адрес сервера в `.env` файле:
```bash
MONGO_SERVER=your-mongo-host:27017
```

### Ошибка: "SSL сертификат не найден"

Проверьте путь к сертификату в `.env`:
```bash
MONGO_SSL_CERT=/root/winners_preprocessor/certs/sber2.crt
```

### Ошибка подключения к MongoDB

1. Проверьте доступность сервера:
   ```bash
   ping your-mongo-host
   ```

2. Проверьте учетные данные в `.env`

3. Проверьте, что сертификат доступен и корректен

### Ошибка: "ModuleNotFoundError"

Установите необходимые пакеты:
```bash
pip3 install --break-system-packages python-dotenv pymongo requests
```

## Следующие шаги

После успешного тестирования:
1. Интегрировать с пайплайном обработки документов
2. Настроить автоматическое получение протоколов по расписанию
3. Обработать скачанные документы через Docling


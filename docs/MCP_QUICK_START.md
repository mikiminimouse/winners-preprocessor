# Быстрый старт: Настройка MCP HTTP Server для получения протоколов

## Минимально необходимые переменные окружения

Для работы функции `get_protocols_by_date_223` (получение протоколов по дате) нужны следующие переменные в `.env`:

### Обязательные (4 переменные):

```bash
# 1. Адреса MongoDB хостов
mongoServer=mongo1.example.com:27017,mongo2.example.com:27017

# 2. Пользователь MongoDB
readAllUser=readonly_user

# 3. Пароль пользователя (СЕКРЕТ!)
readAllPassword=your-secure-password

# 4. Путь к SSL сертификату
sslCertPath=/path/to/mongodb-ca.pem
```

### Опциональные:

```bash
# Лимит протоколов (по умолчанию 100)
protocolsCountLimit=100
```

## Быстрая настройка

1. **Скопируйте шаблон:**
```bash
cp .env.example .env
```

2. **Заполните реальные значения:**
```bash
nano .env  # или используйте ваш редактор
```

3. **Проверьте права доступа:**
```bash
chmod 600 .env
```

4. **Запустите сервер:**
```bash
python mcp_http_server.py
```

## Тестовый запрос

```bash
curl -X POST "http://localhost:8000/tools/call" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "get_protocols_by_date_223",
    "arguments": {
      "date": "2025-01-17"
    }
  }'
```

## Формат ответа

```json
{
  "jsonrpc": "2.0",
  "result": {
    "content": [
      {
        "type": "json",
        "json": {
          "purchaseNoticeNumber1": {
            "url": "https://example.com/doc1.pdf",
            "fileName": "doc1.pdf"
          },
          "purchaseNoticeNumber2": [
            {
              "url": "https://example.com/doc2.pdf",
              "fileName": "doc2.pdf"
            }
          ]
        }
      }
    ]
  }
}
```

## Следующие шаги после получения протоколов

1. **Извлечь URL документов** из JSON ответа
2. **Скачать документы** по URL в директорию `input/`
3. **Обработать через Docling пайплайн** (router → docling → output)

Подробности см. в `MCP_ENV_CONFIG.md`



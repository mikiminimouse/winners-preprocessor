# Инструкция по развертыванию

## Предварительные требования

- Docker 20.10+
- Docker Compose 2.0+
- Минимум 2 vCPU, 8 GB RAM (для DigitalOcean Droplet)

## Шаги развертывания

### 1. Подготовка окружения

```bash
cd /root/winners_preprocessor

# Создайте .env файл (опционально)
cp .env.example .env
# Отредактируйте .env при необходимости
```

### 2. Настройка Docling образа

**Важно:** В `docker-compose.yml` используется образ `ibm/docling:latest`. 

Если у вас другой образ Docling или нужно собрать свой:

1. Замените `image: ibm/docling:latest` на ваш образ
2. Или создайте свой Dockerfile для Docling в `./docling/Dockerfile`

Пример кастомного Docling Dockerfile:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Установка Docling
RUN pip install docling

# Копирование API кода (если используете docling_api_example.py)
COPY docling_api_example.py .

CMD ["uvicorn", "docling_api_example:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 3. Запуск сервисов

```bash
# Сборка и запуск всех сервисов
docker-compose up -d --build

# Проверка статуса
docker-compose ps

# Просмотр логов
docker-compose logs -f
```

### 4. Проверка работоспособности

```bash
# Проверка router
curl http://localhost:8080/health

# Проверка docling (если доступен)
curl http://localhost:8000/health

# Загрузка тестового файла
curl -X POST "http://localhost:8080/upload" \
  -F "file=@test_document.pdf"
```

### 5. Мониторинг

```bash
# Логи всех сервисов
docker-compose logs -f

# Логи конкретного сервиса
docker-compose logs -f router
docker-compose logs -f docling
docker-compose logs -f scheduler

# Использование ресурсов
docker stats

# Проверка обработанных файлов
ls -la normalized/
ls -la output/
```

## Настройка расписания

Scheduler по умолчанию запускается каждые 15 минут. Чтобы изменить:

1. Отредактируйте `.env`:
```bash
SCHEDULE_CRON="0 */1 * * *"  # Каждый час
```

2. Перезапустите scheduler:
```bash
docker-compose restart scheduler
```

## Обработка файлов

### Способ 1: Загрузка через API

```bash
curl -X POST "http://localhost:8080/upload" \
  -F "file=@document.pdf"
```

### Способ 2: Копирование в input/

```bash
cp document.pdf input/
# Scheduler автоматически обработает файл при следующем запуске
```

### Способ 3: Webhook

```bash
curl -X POST "http://localhost:8080/webhook" \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "/app/input/document.pdf"
  }'
```

## Структура результатов

После обработки файлы будут в:

- `normalized/UNIT_*/` - нормализованные unit'ы с manifest.json
- `output/` - результаты обработки Docling (JSON, Markdown, HTML)
- `archive/ARCHIVE_*/` - оригинальные архивы

## Troubleshooting

### Проблема: LibreOffice не конвертирует DOC

**Решение:**
1. Проверьте логи: `docker-compose logs libreoffice`
2. Убедитесь, что файл действительно DOC (OLE2), а не архив
3. Проверьте права доступа к файлам

### Проблема: Архив не распаковывается

**Решение:**
1. Проверьте лимиты в `.env`:
   - `MAX_UNPACK_SIZE_MB=500`
   - `MAX_FILES_IN_ARCHIVE=1000`
2. Увеличьте лимиты при необходимости
3. Проверьте логи router: `docker-compose logs router`

### Проблема: Docling не обрабатывает файлы

**Решение:**
1. Проверьте, что manifest.json создан:
   ```bash
   cat normalized/UNIT_*/manifest.json
   ```
2. Проверьте логи Docling:
   ```bash
   docker-compose logs docling
   ```
3. Убедитесь, что Docling API доступен:
   ```bash
   curl http://docling:8000/health
   ```

### Проблема: Недостаточно памяти

**Решение:**
1. Уменьшите `OCR_THREADS` в docker-compose.yml
2. Обрабатывайте файлы пакетами меньшего размера
3. Увеличьте RAM на сервере

## Масштабирование

Для обработки больших объемов:

1. **Горизонтальное масштабирование:**
   ```bash
   docker-compose up -d --scale router=3 --scale docling=2
   ```

2. **Использование очереди (Redis):**
   - Добавьте Redis в docker-compose.yml
   - Используйте RQ или Celery для асинхронной обработки

3. **Внешний GPU сервер:**
   - Настройте отдельный сервер для LLM fallback
   - Обновите router для отправки запросов на GPU сервер

## Остановка и очистка

```bash
# Остановка сервисов
docker-compose down

# Остановка с удалением volumes (осторожно!)
docker-compose down -v

# Очистка всех данных (кроме кода)
rm -rf input/* output/* temp/* extracted/* normalized/* archive/*
```

## Обновление

```bash
# Остановка
docker-compose down

# Обновление кода
git pull  # или обновите файлы вручную

# Пересборка и запуск
docker-compose up -d --build
```




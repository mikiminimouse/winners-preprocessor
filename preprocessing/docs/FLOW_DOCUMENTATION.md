# ДОКУМЕНТАЦИЯ ПОЛНОГО FLOW ПРЕПРОЦЕССИНГА ДОКУМЕНТОВ

## Обзор архитектуры

Система препроцессинга документов Winners223 представляет собой многоэтапный pipeline для автоматической обработки закупочных протоколов с zakupki.gov.ru.

## Компоненты системы

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Scheduler     │    │     Router      │    │    Docling      │
│   (APScheduler) │───▶│ (FastAPI)       │───▶│   Pipeline      │
│                 │    │                 │    │                 │
│ • CRON задачи   │    │ • Детекция типов│    │ • OCR           │
│ • API триггеры  │    │ • Распаковка     │    │ • Layout        │
└─────────────────┘    │ • Нормализация   │    │ • Tables        │
                       │ • Manifest       │    └─────────────────┘
                       └─────────────────┘             │
┌─────────────────┐           │                        ▼
│   MongoDB       │◀──────────┼─────────────────▶ ┌─────────────┐
│                 │           │                   │   LLM        │
│ • protocols223  │           │                   │ Processing   │
│ • docling_meta  │           │                   └─────────────┘
│ • manifests     │           │
│ • metrics       │           │
└─────────────────┘           │
                              ▼
                       ┌─────────────────┐
                       │   Directories   │
                       │                 │
                       │ • input/        │
                       │ • normalized/   │
                       │ • pending/      │
                       │ • ready_docling/│
                       │ • output/       │
                       └─────────────────┘
```

## Полный Flow обработки

### Этап 1: Синхронизация протоколов (MongoDB Sync)

**Компонент:** `protocol_sync.py`
**Назначение:** Синхронизация закупочных протоколов из удаленной MongoDB

**Процесс:**
1. Подключение к удаленной MongoDB (`protocols223.purchaseProtocol`)
2. Запрос протоколов по дате (с фильтром по `loadDate`)
3. Генерация уникальных `unit_id` для каждой записи
4. Сохранение в локальную MongoDB (`docling_metadata.protocols`)

**Выход:** Записи протоколов в локальной MongoDB с полями:
- `purchaseNoticeNumber`
- `attachments` (массив ссылок на документы)
- `loadDate`
- `unit_id` (уникальный идентификатор)

### Этап 2: Скачивание документов (VPN Download)

**Компонент:** `downloader/manager.py`, `downloader/core.py`
**Назначение:** Скачивание документов с zakupki.gov.ru через VPN

**Процесс:**
1. **VPN настройка:** `route-up-zakupki.sh` настраивает split-tunnel routing
2. **Атомарное резервирование:** ProtocolDownloader резервирует протоколы в MongoDB
3. **Параллельное скачивание:** ThreadPoolExecutor скачивает документы
4. **Retry механизм:** Повторные попытки при ошибках сети/VPN
5. **Сохранение:** Файлы сохраняются в `input/` директорию

**Особенности:**
- **Split-tunnel VPN:** Только трафик на zakupki.gov.ru идет через VPN
- **Browser headers:** Имитация браузерных запросов
- **Rate limiting:** Задержки между запросами
- **Resume capability:** Возможность продолжения после прерываний

### Этап 3: Router/Preprocessor

**Компонент:** `router/main.py`
**Назначение:** Предварительная обработка и маршрутизация документов

#### Шаг 3.1: Детекция типов файлов (File Type Detection)

**Методы детекции:**
1. **MIME тип** (python-magic)
2. **Magic bytes** (сигнатуры файлов)
3. **Расширение файла**
4. **Содержимое** (для сложных случаев)

**Поддерживаемые типы:**
- **Документы:** PDF, DOC, DOCX, XLS, XLSX, PPT, PPTX
- **Изображения:** JPG, PNG, TIFF, BMP
- **Архивы:** ZIP, RAR, 7z
- **Текст:** TXT, RTF, CSV

#### Шаг 3.2: Распаковка архивов (Archive Extraction)

**Защита от угроз:**
- **Zip bomb detection:** Ограничение коэффициента декомпрессии
- **Path traversal:** Санитизация путей файлов
- **Размер файлов:** Ограничение размера распакованных файлов
- **Количество файлов:** Ограничение количества файлов в архиве

**Поддерживаемые форматы:** ZIP, RAR, 7z, TAR

#### Шаг 3.3: Нормализация (Unit Creation)

**Структура unit:**
```
UNIT_{unit_id}/
├── files/
│   ├── document1.pdf
│   ├── document2.docx
│   └── ...
├── manifest.json
└── metadata.json (опционально)
```

**Содержимое manifest.json:**
```json
{
  "unit_id": "uuid-string",
  "purchase_number": "01234567890123456789",
  "files": [
    {
      "filename": "protocol.pdf",
      "original_path": "https://...",
      "detected_type": "pdf",
      "size_bytes": 12345,
      "mime_type": "application/pdf"
    }
  ],
  "created_at": "2024-12-17T10:00:00Z",
  "stage": "normalized"
}
```

#### Шаг 3.4: Создание manifest'ов

**Сохранение в MongoDB:**
- База: `docling_metadata`
- Коллекция: `manifests`
- Индексы: по `unit_id`, `purchase_number`, `created_at`

### Этап 4: Docling Pipeline

**Компонент:** Docling API (отдельный сервис)
**Назначение:** Преобразование документов в структурированный текст и метаданные

**Процесс:**
1. **Маршрутизация по типам:**
   - `pdf_text`: Текстовые PDF
   - `pdf_scan`: Сканированные PDF (OCR)
   - `docx`: Word документы
   - `image_ocr`: Изображения
   - `mixed`: Смешанные документы

2. **Обработка:**
   - **OCR:** Распознавание текста из изображений
   - **Layout Analysis:** Определение структуры документа
   - **Table Extraction:** Извлечение таблиц
   - **Metadata Extraction:** Извлечение метаданных

3. **Выход:** Markdown с метаданными

**HTTP API:**
```bash
POST http://docling:8081/process
Content-Type: application/json

{
  "unit_id": "uuid",
  "files": ["path/to/file.pdf"],
  "routing_type": "pdf_text"
}
```

### Этап 5: LLM Processing

**Назначение:** Семантическая обработка и извлечение структурированных данных

**Процесс:**
1. **Чтение Markdown** из Docling
2. **Prompt Engineering** для извлечения данных
3. **JSON Structured Output** с информацией о закупке
4. **Валидация и постобработка**

## Директории и файлы

### Структура директорий
```
/app/data/
├── input/           # Входные файлы (из скачивания)
├── temp/            # Временные файлы
├── extracted/       # Распакованные архивы
├── normalized/      # Нормализованные units
│   └── UNIT_xxx/    # Структура unit'а
├── pending/         # Ожидающие обработки
│   ├── direct/      # Готовые к Docling
│   ├── convert/     # Требуют конвертации
│   ├── extract/     # Архивы
│   └── special/     # Специальные форматы
├── ready_docling/   # Готовые к Docling
└── output/          # Финальные результаты
```

### MongoDB структуры

#### protocols223.purchaseProtocol (remote)
```javascript
{
  _id: ObjectId,
  purchaseNoticeNumber: "01234567890123456789",
  attachments: [
    {
      url: "https://zakupki.gov.ru/...",
      fileName: "protocol.pdf",
      guid: "uuid"
    }
  ],
  loadDate: ISODate("2024-12-17T00:00:00Z")
}
```

#### docling_metadata.protocols (local)
```javascript
{
  _id: ObjectId,
  purchaseNoticeNumber: "01234567890123456789",
  attachments: [...],
  loadDate: ISODate,
  unit_id: "uuid-string",
  status: "pending|downloaded|processed"
}
```

#### docling_metadata.manifests
```javascript
{
  _id: ObjectId,
  unit_id: "uuid",
  purchase_number: "01234567890123456789",
  files: [...],
  created_at: ISODate,
  stage: "normalized",
  docling_status: "pending|processing|completed|error"
}
```

## Запуск системы

### По расписанию (Production)
```bash
# Через scheduler
docker-compose up scheduler

# Конфигурация CRON в scheduler/main.py
SCHEDULE_CRON = "*/15 * * * *"  # Каждые 15 минут
```

### По команде (Manual)
```bash
# Через CLI
docker-compose exec router python3 cli.py
# Выбрать пункт 14: "ПОЛНАЯ ОБРАБОТКА"

# Через API
curl -X POST http://localhost:8080/process_now
```

### Полностью вручную (Development)
```bash
# 1. Синхронизация
docker-compose exec cli python3 cli.py  # пункт 1

# 2. Скачивание
docker-compose exec cli python3 cli.py  # пункт 2

# 3. Обработка
docker-compose exec cli python3 cli.py  # пункт 14

# 4. Merge
docker-compose exec cli python3 cli.py  # пункт 21
```

## Мониторинг и метрики

### Метрики обработки
- **processed_units:** Количество обработанных units
- **downloaded_files:** Скачанные файлы
- **docling_requests:** Запросы к Docling
- **errors_total:** Общее количество ошибок
- **processing_time:** Время обработки

### Логи
- **Application logs:** router/main.py логирует все операции
- **MongoDB logs:** Операции с БД
- **VPN logs:** Подключения и ошибки
- **Docling logs:** Обработка документов

### Health checks
- **MongoDB connectivity:** Проверка подключений
- **VPN availability:** Доступность zakupki.gov.ru
- **Disk space:** Свободное место
- **Service health:** Статус всех компонентов

## Производительность

### Типичные показатели
- **Синхронизация:** 1000 протоколов/минуту
- **Скачивание:** 50-100 файлов/минуту
- **Обработка:** 100+ файлов/минуту
- **Docling:** 10-20 файлов/минуту
- **Полный цикл:** 1-2 часа на 1000 протоколов

### Ограничения
- **VPN bandwidth:** Ограничение скорости скачивания
- **MongoDB IOPS:** Операции ввода-вывода
- **CPU:** Обработка больших PDF с OCR
- **Memory:** Работа с большими архивами

## Обработка ошибок

### Типы ошибок
1. **Network errors:** Проблемы VPN, таймауты
2. **File corruption:** Поврежденные архивы/PDF
3. **MongoDB errors:** Дубликаты, отключения
4. **Docling errors:** Не поддерживаемые форматы
5. **Resource limits:** Недостаток памяти/CPU

### Стратегии восстановления
- **Retry mechanisms:** Повторные попытки операций
- **Circuit breakers:** Отключение при множественных ошибках
- **Dead letter queues:** Отложенная обработка проблемных файлов
- **Manual intervention:** CLI для ручной обработки

### Логика обработки ошибок
```python
try:
    # Основная операция
    process_file(file_path)
except NetworkError:
    # Retry с exponential backoff
    retry_with_backoff(process_file, file_path)
except FileCorruptionError:
    # Логирование и пропуск
    log_error(f"Corrupted file: {file_path}")
    skip_file(file_path)
except Exception as e:
    # Общая обработка
    log_critical_error(e)
    raise
```

## Безопасность

### Сетевые меры
- **VPN-only access:** Все внешние запросы через VPN
- **IP whitelisting:** Разрешенные IP адреса
- **Rate limiting:** Ограничение запросов

### Файловые меры
- **Path sanitization:** Защита от path traversal
- **Size limits:** Ограничение размера файлов
- **Type validation:** Проверка типов файлов
- **Archive scanning:** Проверка архивов на вредоносный код

### Данные меры
- **Encryption at rest:** Шифрование данных в MongoDB
- **Access control:** RBAC для MongoDB
- **Audit logging:** Логи всех операций
- **Data retention:** Автоматическая очистка старых данных

## Расширение системы

### Добавление новых типов файлов
1. Обновить `detect_file_type()` в `router/main.py`
2. Добавить обработку в `process_file()`
3. Обновить маршрутизацию Docling
4. Добавить тесты в CLI

### Добавление новых источников данных
1. Создать новый синхронизатор (аналог `protocol_sync.py`)
2. Добавить коллекцию в MongoDB
3. Интегрировать в CLI
4. Обновить flow документацию

### Оптимизация производительности
1. **Parallel processing:** Увеличить количество потоков
2. **Caching:** Кэширование результатов детекции
3. **Batch operations:** Групповая обработка в MongoDB
4. **Async I/O:** Асинхронные операции скачивания

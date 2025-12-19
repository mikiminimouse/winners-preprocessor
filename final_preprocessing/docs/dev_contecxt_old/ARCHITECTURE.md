# Архитектура пайплайна обработки документов

## Общая схема

```
┌─────────────┐
│   Input     │ → Файлы (PDF, DOC, DOCX, архивы, изображения)
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────────────┐
│         Router/Preprocessor                     │
│  ┌──────────────────────────────────────────┐   │
│  │ 1. Определение типа (magic/mimetype)     │   │
│  │ 2. Распаковка архивов (если нужно)       │   │
│  │ 3. Классификация PDF (text/scan)         │   │
│  │ 4. Конвертация DOC→DOCX (LibreOffice)   │   │
│  │ 5. Создание manifest.json                │   │
│  │ 6. Нормализация unit'ов                 │   │
│  └──────────────────────────────────────────┘   │
└──────┬──────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────┐
│              Docling Pipeline                    │
│  ┌──────────────────────────────────────────┐   │
│  │ Route: pdf_text → Text Extraction         │   │
│  │ Route: pdf_scan → OCR → Layout → Tables  │   │
│  │ Route: docx → Text Extraction → Layout   │   │
│  │ Route: image → OCR → Layout → Tables     │   │
│  │ Route: mixed → Объединение результатов    │   │
│  └──────────────────────────────────────────┘   │
└──────┬──────────────────────────────────────────┘
       │
       ▼
┌─────────────┐
│   Output    │ → JSON, Markdown, HTML
└─────────────┘
```

## Компоненты

### 1. Router/Preprocessor

**Задачи:**
- Классификация файлов по типу (magic bytes + mimetype)
- Распаковка архивов (ZIP, RAR) с защитой от zip bomb
- Определение PDF text vs scan
- Конвертация DOC → DOCX через LibreOffice
- Создание manifest.json для связывания файлов
- Нормализация unit'ов для Docling

**Технологии:**
- FastAPI для API
- python-magic для определения типов
- pypdf для проверки PDF text layer
- 7z/unzip для распаковки архивов

### 2. Docling

**Задачи:**
- Text Extraction (для PDF с текстом, DOCX)
- OCR (Docling OCR для сканов и изображений)
- Layout Analysis (блоки, заголовки, reading order)
- Table Extraction (извлечение таблиц)
- Export (JSON, Markdown, HTML)

**Особенности:**
- Использует Docling OCR вместо Tesseract
- CPU-оптимизированные модели
- Работает на DigitalOcean (2 vCPU, 8GB RAM)

### 3. LibreOffice

**Задачи:**
- Автоматическая конвертация DOC → DOCX
- Мониторинг директорий на наличие .doc файлов
- Headless режим (без GUI)

### 4. Scheduler

**Задачи:**
- Периодический запуск обработки (cron-like)
- Вызов router API для обработки файлов из input/
- Настраиваемое расписание через переменные окружения

**Технологии:**
- APScheduler для планирования задач

### 5. PostgreSQL (опционально)

**Задачи:**
- Хранение метаданных для больших объемов
- Аудит и трекинг обработки
- Запросы и отчеты

## Потоки данных

### Поток 1: PDF с текстовым слоем

```
PDF (text) → Router → detect_type → needs_ocr=false
  → Normalized Unit → Docling → Text Extraction
  → Layout Analysis → Table Extraction → Export
```

### Поток 2: PDF скан

```
PDF (scan) → Router → detect_type → needs_ocr=true
  → Normalized Unit → Docling → OCR (Docling OCR)
  → Layout Analysis → Table Extraction → Export
```

### Поток 3: DOC файл

```
DOC → Router → detect_type → requires_conversion=true
  → LibreOffice → DOCX → Normalized Unit
  → Docling → Text Extraction → Layout → Tables → Export
```

### Поток 4: Архив (ZIP/RAR)

```
Archive → Router → detect_type → is_archive=true
  → Extract → Process each file
  → Create Unit with multiple files
  → Docling → Process each file → Merge results
```

### Поток 5: Фейковый DOC (архив)

```
DOC (fake) → Router → magic bytes → is_archive=true
  → Extract → Process as archive
  → Same as Поток 4
```

### Поток 6: Смешанный документ (DOCX + изображение)

```
Archive → Extract → DOCX + JPEG
  → Create Unit with route=mixed
  → Docling → Process DOCX (text) + JPEG (OCR)
  → Merge results → Export
```

## Формат manifest.json

```json
{
  "unit_id": "UNIT_abc123",
  "created_at": "2025-01-17T10:00:00",
  "processing": {
    "status": "ready|processing|done|error",
    "route": "pdf_scan|pdf_text|docx|image_ocr|mixed"
  },
  "files": [
    {
      "file_id": "uuid",
      "original_name": "document.pdf",
      "path": "/app/normalized/UNIT_abc123/files/document.pdf",
      "detected_type": "pdf|docx|doc|image|html",
      "mime_type": "application/pdf",
      "needs_ocr": true|false,
      "requires_conversion": true|false,
      "sha256": "hash",
      "size": 12345
    }
  ],
  "archive": {
    "is_archive": true|false,
    "archive_id": "ARCHIVE_xyz",
    "original_path": "/app/input/archive.zip",
    "extracted_count": 2
  }
}
```

## Безопасность

1. **Защита от zip bomb:**
   - Лимит на размер распаковки (MAX_UNPACK_SIZE_MB)
   - Лимит на количество файлов (MAX_FILES_IN_ARCHIVE)

2. **Санитизация имен файлов:**
   - Удаление ../ и опасных символов
   - Проверка на path traversal

3. **Изоляция контейнеров:**
   - Docker network для изоляции
   - Read-only volumes где возможно

4. **Webhook подпись:**
   - HMAC SHA256 для проверки подлинности

## Масштабирование

### Горизонтальное масштабирование

```bash
docker-compose up -d --scale router=3 --scale docling=2
```

### Вертикальное масштабирование

- Увеличение CPU/RAM на сервере
- Оптимизация OCR_THREADS
- Использование GPU для LLM fallback

### Асинхронная обработка

- Добавление Redis для очереди задач
- Использование RQ или Celery
- Batch processing для больших объемов

## Мониторинг и логирование

- Логи всех сервисов через `docker-compose logs`
- Health checks для каждого сервиса
- Метрики обработки (можно добавить Prometheus)
- Статус unit'ов через API `/status/{unit_id}`




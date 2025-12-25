# Обзор YAML Templates для Docling Pipeline

## Введение

YAML templates используются для конфигурации Docling pipelines в зависимости от типа документа. Это позволяет гибко настраивать обработку различных форматов и маршрутов.

## Структура template

Каждый template содержит следующие секции:

```yaml
route: имя_маршрута
models:
  # Настройки моделей
performance:
  # Настройки производительности
docling:
  # Флаги Docling
language:
  # Настройки языка
processing_constraints:
  # Ограничения обработки
```

## Детальный обзор templates

### 1. pdf_text.yaml

**Назначение**: PDF документы с текстовым слоем (born-digital)

**Ключевые особенности**:
- Не требует OCR (текст уже в PDF)
- Использует `publaynet_detectron2` для layout detection
- Использует `table-transformer` для извлечения таблиц
- Оптимизирован для русского языка

**Настройки**:
```yaml
models:
  layout: publaynet_detectron2
  tables: table-transformer
  ocr: off

performance:
  threads: 4
  batch_pages: 8

docling:
  parse_text: true
  extract_tables: true
  extract_figures: true
  do_caption_mentions: true
  do_table_of_contents: true
  preserve_layout: true
  preserve_formatting: true

language:
  primary: ru
  fallback: en
  encoding: utf-8

processing_constraints:
  allow_gpu: false
  max_runtime_sec: 180
  max_memory_mb: 4096
```

### 2. pdf_scan.yaml

**Назначение**: Сканированные PDF документы (требуют OCR)

**Ключевые особенности**:
- Требует OCR для извлечения текста
- Использует `tesseract` как OCR engine
- Использует `docbank` для layout detection
- Может использовать VLM pipeline для улучшения качества OCR

**Настройки**:
```yaml
models:
  ocr: tesseract
  layout: docbank
  tables: off

performance:
  threads: 6
  dpi: 300

docling:
  force_ocr: true
  language: eng
  do_caption_mentions: true
  extract_figures: true

processing_constraints:
  allow_gpu: false
  max_runtime_sec: 300
  max_memory_mb: 4096
```

### 3. pdf_scan_table.yaml

**Назначение**: Сканированные PDF с акцентом на таблицы

**Ключевые особенности**:
- Требует OCR и специализированную обработку таблиц
- Использует `tesseract` для OCR
- Использует `docbank` для layout detection
- Включает извлечение таблиц

**Настройки**:
```yaml
models:
  ocr: tesseract
  layout: docbank
  tables: table-transformer

performance:
  threads: 4
  dpi: 300

docling:
  force_ocr: true
  do_table_structure: true
  extract_tables: true

processing_constraints:
  allow_gpu: false
  max_runtime_sec: 600
  max_memory_mb: 8192
```

### 4. docx.yaml

**Назначение**: Microsoft Word документы

**Ключевые особенности**:
- Нативная обработка через Docling
- Извлечение структуры документа
- Поддержка оглавлений и ссылок

**Настройки**:
```yaml
models:
  layout: native
  tables: native

docling:
  do_caption_mentions: true
  do_table_of_contents: true
  do_table_structure: true

processing_constraints:
  allow_gpu: false
  max_runtime_sec: 120
  max_memory_mb: 2048
```

### 5. xlsx.yaml

**Назначение**: Microsoft Excel таблицы

**Ключевые особенности**:
- Нативная обработка через Docling
- Извлечение структуры таблиц
- Поддержка формул и форматирования

**Настройки**:
```yaml
models:
  layout: native
  tables: native

docling:
  do_table_structure: true
  do_caption_mentions: true

processing_constraints:
  allow_gpu: false
  max_runtime_sec: 120
  max_memory_mb: 2048
```

### 6. pptx.yaml

**Назначение**: Microsoft PowerPoint презентации

**Ключевые особенности**:
- Нативная обработка через Docling
- Извлечение слайдов и структуры
- Поддержка оглавлений

**Настройки**:
```yaml
models:
  layout: native

docling:
  do_caption_mentions: true
  do_table_of_contents: true

processing_constraints:
  allow_gpu: false
  max_runtime_sec: 120
  max_memory_mb: 2048
```

### 7. html.yaml

**Назначение**: HTML документы

**Ключевые особенности**:
- Парсинг HTML структуры
- Извлечение текста и таблиц
- Поддержка оглавлений

**Настройки**:
```yaml
models:
  layout: native
  tables: native

docling:
  do_caption_mentions: true
  do_table_of_contents: true
  do_table_structure: true

processing_constraints:
  allow_gpu: false
  max_runtime_sec: 60
  max_memory_mb: 1024
```

### 8. xml.yaml

**Назначение**: XML документы

**Ключевые особенности**:
- Парсинг XML структуры
- Автоматическое определение типа XML (JATS, USPTO и др.)
- Извлечение структурированных данных

**Настройки**:
```yaml
models:
  layout: native
  tables: native

docling:
  do_caption_mentions: true
  do_table_structure: true

processing_constraints:
  allow_gpu: false
  max_runtime_sec: 60
  max_memory_mb: 1024
```

### 9. image_ocr.yaml

**Назначение**: Изображения (JPG, PNG, TIFF и др.)

**Ключевые особенности**:
- Обработка через OCR
- Использует `tesseract` для извлечения текста
- Может извлекать таблицы из изображений

**Настройки**:
```yaml
models:
  ocr: tesseract
  layout: docbank

performance:
  dpi: 300

docling:
  force_ocr: true
  do_table_structure: true
  extract_figures: true

processing_constraints:
  allow_gpu: false
  max_runtime_sec: 120
  max_memory_mb: 2048
```

## Параметры конфигурации

### models.*
- `layout` - модель для layout detection (publaynet_detectron2, docbank, native)
- `tables` - модель для table structure recognition (table-transformer, native, off)
- `ocr` - OCR engine (tesseract, off)

### performance.*
- `threads` - количество потоков обработки
- `batch_pages` - количество страниц в batch
- `dpi` - разрешение для OCR (только для сканированных документов)

### docling.*
- `parse_text` - извлекать текст
- `extract_tables` - извлекать таблицы
- `extract_figures` - извлекать изображения
- `do_caption_mentions` - обрабатывать ссылки на изображения/таблицы
- `do_table_of_contents` - извлекать оглавление
- `force_ocr` - принудительно использовать OCR
- `preserve_layout` - сохранять layout документа
- `preserve_formatting` - сохранять форматирование

### language.*
- `primary` - основной язык документа
- `fallback` - резервный язык
- `encoding` - кодировка текста

### processing_constraints.*
- `allow_gpu` - разрешить использование GPU
- `max_runtime_sec` - максимальное время обработки
- `max_memory_mb` - максимальное использование памяти
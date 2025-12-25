# Конфигурация и настройки Docling Integration

**Дата создания:** 2025-12-24  
**Версия:** 1.0

## Обзор

Конфигурация Docling Integration осуществляется через:

1. **YAML Templates** - приоритетный способ (файлы в `pipeline_templates/`)
2. **Legacy hardcoded конфигурация** - fallback для обратной совместимости
3. **Environment Variables** - для внешних сервисов (VLM, MongoDB)

---

## 1. YAML Templates

**Расположение:** `final_preprocessing/docling_integration/pipeline_templates/`

Каждый template соответствует определенному route и описывает настройки обработки для этого типа документов.

### 1.1. Структура YAML template

```yaml
route: pdf_text              # Route из contract

models:                      # Модели для обработки
  layout: publaynet_detectron2
  tables: table-transformer
  ocr: off

performance:                 # Настройки производительности
  threads: 4
  batch_pages: 8

docling:                     # Флаги Docling
  parse_text: true
  extract_tables: true
  extract_figures: true

language:                    # Настройки языка
  primary: ru
  fallback: en
  encoding: utf-8

processing_constraints:      # Ограничения обработки
  allow_gpu: false
  max_runtime_sec: 180
  max_memory_mb: 4096
```

### 1.2. Доступные Templates

#### pdf_text.yaml

**Назначение:** PDF документы с текстовым слоем (born-digital).

**Модели:**
- `layout`: `publaynet_detectron2` - модель для анализа layout документа
- `tables`: `table-transformer` - модель для извлечения таблиц
- `ocr`: `off` - OCR не требуется, текст уже в PDF

**Performance:**
- `threads`: 4
- `batch_pages`: 8

**Docling флаги:**
- `parse_text`: true
- `extract_tables`: true
- `extract_figures`: true
- `do_caption_mentions`: true
- `do_table_of_contents`: true

**Язык:**
- `primary`: ru - оптимизация для русского языка
- `fallback`: en
- `encoding`: utf-8

**Производительность:** ~40-70 PDF/hour/CPU

#### pdf_scan.yaml

**Назначение:** PDF документы со сканированным содержимым (требуется OCR).

**Модели:**
- `ocr`: `tesseract` - OCR движок
- `layout`: `docbank` - модель для анализа layout сканированных документов
- `tables`: `off` - таблицы не извлекаются (для ускорения)

**Performance:**
- `threads`: 6
- `dpi`: 300

**Docling флаги:**
- `force_ocr`: true
- `language`: eng (можно настроить на rus)
- `do_caption_mentions`: true
- `extract_figures`: true

**Производительность:** ~10-20 PDF/hour/CPU

#### pdf_scan_table.yaml

**Назначение:** PDF документы со сканированным содержимым и таблицами (самый тяжелый workload).

**Модели:**
- `ocr`: `tesseract`
- `layout`: `publaynet_detectron2`
- `tables`: `cascadetabnet` - специализированная модель для извлечения таблиц из сканов

**Performance:**
- `threads`: 8
- `dpi`: 300

**Docling флаги:**
- `force_ocr`: true
- `extract_tables`: true
- `normalize_cells`: true - нормализация ячеек таблиц
- `do_caption_mentions`: true
- `extract_figures`: true

**Ограничения:**
- `max_runtime_sec`: 600 (10 минут)
- `max_memory_mb`: 8192 (8 GB)

**Производительность:** ~4-8 PDF/hour/CPU

#### docx.yaml

**Назначение:** Microsoft Word документы (нативный формат).

**Модели:**
- `layout`: `native` - нативная обработка без моделей
- `tables`: `native` - нативное извлечение таблиц
- `ocr`: `off`

**Performance:**
- `threads`: 4

**Docling флаги:**
- `parse_text`: true
- `extract_tables`: true
- `do_caption_mentions`: true
- `do_table_of_contents`: true
- `extract_figures`: true

**Производительность:** ~100-200 docs/hour/CPU

#### xlsx.yaml

**Назначение:** Microsoft Excel таблицы (нативный формат).

**Модели:**
- `layout`: `native`
- `tables`: `native`
- `ocr`: `off`

**Performance:**
- `threads`: 4

**Docling флаги:**
- `extract_tables`: true
- `normalize_cells`: true - нормализация ячеек
- `do_caption_mentions`: true

**Производительность:** ~80-150 docs/hour/CPU

#### pptx.yaml

**Назначение:** Microsoft PowerPoint презентации (нативный формат).

**Модели:**
- `layout`: `native`
- `tables`: `native`
- `ocr`: `off`

**Performance:**
- `threads`: 4

**Docling флаги:**
- `parse_text`: true
- `extract_tables`: true
- `do_caption_mentions`: true
- `do_table_of_contents`: true
- `extract_figures`: true

**Производительность:** ~80-150 docs/hour/CPU

#### html.yaml

**Назначение:** HTML документы (структурированный формат).

**Модели:**
- `layout`: `native` - парсинг HTML структуры
- `tables`: `native` - извлечение HTML таблиц
- `ocr`: `off`

**Performance:**
- `threads`: 4

**Docling флаги:**
- `parse_text`: true
- `extract_tables`: true
- `do_caption_mentions`: true
- `do_table_of_contents`: true

**Ограничения:**
- `max_runtime_sec`: 30
- `max_memory_mb`: 1024

**Производительность:** ~150-300 docs/hour/CPU

#### xml.yaml

**Назначение:** XML документы (структурированный формат).

**Модели:**
- `layout`: `native`
- `tables`: `native`
- `ocr`: `off`

**Performance:**
- `threads`: 4

**Docling флаги:**
- `parse_text`: true
- `extract_tables`: true
- `do_caption_mentions`: true

**Примечание:** Docling автоматически определяет тип XML (XML_JATS, XML_USPTO, и т.д.)

**Производительность:** ~150-300 docs/hour/CPU

#### image_ocr.yaml

**Назначение:** Изображения (требуется OCR).

**Модели:**
- `ocr`: `tesseract`
- `layout`: не используется (изображения обрабатываются через PDF pipeline)

**Performance:**
- `threads`: 4
- `dpi`: 300 (для конвертации изображений в PDF)

**Docling флаги:**
- `force_ocr`: true
- `extract_tables`: true - попытка извлечения таблиц из изображений
- `extract_figures`: true

**Производительность:** ~60-100 images/hour/CPU

### 1.3. Параметры конфигурации

#### models.*

Определяет модели для различных задач обработки.

**Возможные значения:**

- **layout:**
  - `publaynet_detectron2` - для PDF с текстовым слоем
  - `docbank` - для сканированных документов
  - `native` - для нативных форматов (DOCX, XLSX, и т.д.)

- **tables:**
  - `table-transformer` - для PDF с текстовым слоем
  - `cascadetabnet` - для сканированных документов с таблицами
  - `native` - для нативных форматов
  - `off` - таблицы не извлекаются

- **ocr:**
  - `tesseract` - использование Tesseract OCR
  - `off` - OCR не требуется

- **vlm:**
  - Опционально: конфигурация VLM pipeline через environment variables

#### performance.*

Настройки производительности обработки.

**Параметры:**

- `threads` (int): Количество потоков для обработки (обычно 4-8)
- `batch_pages` (int): Размер батча страниц для обработки (для PDF)
- `dpi` (int): Разрешение для OCR (обычно 300)

#### docling.*

Флаги для настройки поведения Docling.

**Основные флаги:**

- `parse_text` (bool): Извлекать текст
- `extract_tables` (bool): Извлекать таблицы
- `extract_figures` (bool): Извлекать изображения/фигуры
- `do_caption_mentions` (bool): Обрабатывать подписи к изображениям
- `do_table_of_contents` (bool): Извлекать оглавление
- `normalize_cells` (bool): Нормализовать ячейки таблиц
- `force_ocr` (bool): Принудительно использовать OCR
- `preserve_layout` (bool): Сохранять layout документа (экспериментально)
- `preserve_formatting` (bool): Сохранять форматирование (экспериментально)

**Примечание:** Некоторые флаги (например, `preserve_layout`, `preserve_formatting`) могут не поддерживаться в текущей версии Docling и являются комментариями в YAML.

#### language.*

Настройки языка для обработки.

**Параметры:**

- `primary` (str): Основной язык (например, `ru`, `en`)
- `fallback` (str): Резервный язык
- `encoding` (str): Кодировка текста (обычно `utf-8`)

**Примечание:** Настройки языка в YAML templates используются как документация. Реальная поддержка русского языка зависит от настроек Docling и моделей OCR.

#### processing_constraints.*

Ограничения на обработку документов.

**Параметры:**

- `allow_gpu` (bool): Разрешить использование GPU (обычно `false` для CPU-only)
- `max_runtime_sec` (int): Максимальное время обработки в секундах
- `max_memory_mb` (int): Максимальное использование памяти в MB

### 1.4. Маппинг Template → PipelineOptions

Процесс построения `PipelineOptions` из YAML template:

```python
# 1. Загрузка template
template = load_pipeline_template(route)

# 2. Построение PdfPipelineOptions (если нужно)
if template.get("route", "").startswith("pdf") or template.get("route") == "image_ocr":
    pdf_opts = PdfPipelineOptions()
    pdf_config = template.get("models", {})
    
    if pdf_config.get("ocr") == "tesseract":
        pdf_opts.do_ocr = True
    
    if pdf_config.get("tables") != "off":
        pdf_opts.do_table_structure = True
    
    options = PipelineOptions(pdf=pdf_opts)

# 3. Настройка VLM (если указан)
vlm_config = template.get("models", {}).get("vlm")
if vlm_config:
    options.vlm = VlmPipelineOptions()
    options.vlm.endpoint = os.environ.get("VLM_ENDPOINT")
```

**Важно:** Не все параметры из YAML напрямую маппятся в `PipelineOptions`. Некоторые параметры (например, `performance.*`, `language.*`) используются только как документация или для будущих улучшений.

---

## 2. Legacy Hardcoded Конфигурация

**Расположение:** `final_preprocessing/docling_integration/config.py` (функция `_build_options_legacy`)

Используется как fallback, если YAML template не найден.

### 2.1. Логика для различных routes

#### pdf_scan

```python
options.pdf = PdfPipelineOptions()
options.pdf.do_ocr = True
options.pdf.do_table_structure = True

# VLM pipeline (если доступен)
options.vlm = VlmPipelineOptions()
options.vlm.endpoint = os.environ.get("VLM_ENDPOINT")
```

#### pdf_text

```python
options.pdf = PdfPipelineOptions()
options.pdf.do_ocr = False
options.pdf.do_table_structure = True
```

#### docx, xlsx, pptx

```python
# Базовые опции без PDF-specific настроек
options = PipelineOptions()
# Docling использует нативную обработку для этих форматов
```

#### html, xml

```python
options = PipelineOptions()
# Docling парсит структуру автоматически
```

#### image_ocr

```python
options.pdf = PdfPipelineOptions()
options.pdf.do_ocr = True
options.pdf.do_table_structure = True
```

### 2.2. Неподдерживаемые параметры

В legacy конфигурации есть попытки установить параметры, которые не существуют в `PipelineOptions`:

```python
# ЭТО НЕ РАБОТАЕТ - такие поля не существуют
options.do_caption_mentions = True  # ❌
options.do_table_of_contents = True  # ❌
```

Эти параметры должны быть удалены или перенесены в правильные места (например, в `PdfPipelineOptions`, если они там поддерживаются).

---

## 3. Environment Variables

### 3.1. VLM Pipeline (Cloud.ru Granite Docling)

**VLM_ENDPOINT** (str): URL endpoint для VLM сервиса (Cloud.ru Granite Docling)

**Пример:**
```bash
export VLM_ENDPOINT="https://ml-foundation.cloud.ru/model-run/granite_docling"
```

**VLM_MODEL** (str): Название модели VLM

**Пример:**
```bash
export VLM_MODEL="granite-docling"
```

**VLM_API_KEY** (str): API ключ для доступа к Cloud.ru ML Foundation (опционально)

**Пример:**
```bash
export VLM_API_KEY="your-api-key"
```

**Использование:**
```python
vlm_config = template.get("models", {}).get("vlm")
if vlm_config:
    options.vlm = VlmPipelineOptions()
    vlm_endpoint = os.environ.get("VLM_ENDPOINT")
    if vlm_endpoint:
        options.vlm.endpoint = vlm_endpoint
    vlm_model = os.environ.get("VLM_MODEL", "granite-docling")
    if hasattr(options.vlm, "model"):
        options.vlm.model = vlm_model
```

**Статус:** Планируется к интеграции на следующем этапе рефакторинга

### 3.1.1. PaddleOCR_VLM Service

**PADDLEOCR_VLM_ENDPOINT** (str): URL endpoint для PaddleOCR_VLM сервиса (Cloud.ru)

**Пример:**
```bash
export PADDLEOCR_VLM_ENDPOINT="https://ml-foundation.cloud.ru/docker-run/paddleocr_vlm"
```

**PADDLEOCR_VLM_API_KEY** (str): API ключ для доступа к PaddleOCR_VLM (опционально)

**Пример:**
```bash
export PADDLEOCR_VLM_API_KEY="your-api-key"
```

**PADDLEOCR_VLM_ENABLED** (bool): Включить использование PaddleOCR_VLM для OCR (по умолчанию: false)

**Пример:**
```bash
export PADDLEOCR_VLM_ENABLED="true"
```

**Использование:**
- Для PDF файлов, требующих OCR обработки (pdf_scan, pdf_scan_table)
- Альтернатива локальному Tesseract для ресурсоемких задач
- Используется через внешний API вызов к сервису

**Статус:** Планируется к интеграции на следующем этапе рефакторинга

### 3.2. MongoDB

**LOCAL_MONGO_SERVER** или **MONGO_METADATA_SERVER** (str): Адрес MongoDB сервера

**Пример:**
```bash
export LOCAL_MONGO_SERVER="localhost:27018"
# или
export MONGO_METADATA_SERVER="mongodb:27017"
```

**MONGO_METADATA_USER** (str): Имя пользователя MongoDB

**Пример:**
```bash
export MONGO_METADATA_USER="admin"
```

**MONGO_METADATA_PASSWORD** (str): Пароль MongoDB

**Пример:**
```bash
export MONGO_METADATA_PASSWORD="password"
```

**MONGO_METADATA_DB** (str): Имя базы данных MongoDB

**Пример:**
```bash
export MONGO_METADATA_DB="docling_metadata"
```

**Использование:**
```python
server = os.environ.get("LOCAL_MONGO_SERVER", os.environ.get("MONGO_METADATA_SERVER", "localhost:27018"))
user = os.environ.get("MONGO_METADATA_USER", "admin")
password = os.environ.get("MONGO_METADATA_PASSWORD", "password")
db_name = os.environ.get("MONGO_METADATA_DB", "docling_metadata")

mongo_url = f"mongodb://{user}:{password}@{server}/?authSource=admin"
```

---

## 4. Внешние библиотеки и модели

### 4.1. Модели Layout Analysis

#### publaynet_detectron2

- **Тип:** CNN модель для анализа layout документов
- **Использование:** PDF с текстовым слоем
- **Источник:** Pre-trained модель из Docling
- **Требования:** PyTorch, detectron2

#### docbank

- **Тип:** Модель для анализа layout сканированных документов
- **Использование:** PDF со сканированным содержимым
- **Источник:** Pre-trained модель из Docling

### 4.2. Модели Table Extraction

#### table-transformer

- **Тип:** Transformer модель для извлечения таблиц
- **Использование:** PDF с текстовым слоем
- **Источник:** Pre-trained модель из Docling
- **Требования:** PyTorch

#### cascadetabnet

- **Тип:** CNN модель для извлечения таблиц из сканов
- **Использование:** PDF со сканированным содержимым и таблицами
- **Источник:** Pre-trained модель из Docling
- **Требования:** PyTorch, больше памяти чем table-transformer

### 4.3. OCR Engines

#### Tesseract

- **Тип:** OCR движок
- **Использование:** PDF со сканированным содержимым, изображения
- **Поддержка языков:** Множество языков, включая русский (rus)
- **Требования:** Установленный Tesseract OCR

**Настройка для русского языка:**
- Требуется установка языковых пакетов Tesseract для русского
- В Docling настройка языка через `PdfPipelineOptions` (если поддерживается)

### 4.4. VLM (Vision Language Model)

- **Тип:** Удаленный VLM сервис
- **Использование:** Опционально для улучшения OCR качества
- **Настройка:** Через environment variables (VLM_ENDPOINT, VLM_MODEL)
- **Источник:** Внешний API (например, IBM Granite, Cloud.ru)

---

## 5. Зависимости

### 5.1. Python пакеты

**Основные:**

- `docling>=2.60.0` - основная библиотека Docling
- `docling-core>=2.50.0` - ядро Docling
- `pyyaml>=6.0` - для загрузки YAML templates
- `pymongo>=4.0.0` - для экспорта в MongoDB (опционально)

**Требования Docling:**

- `torch` (PyTorch) - для моделей
- `detectron2` - для некоторых моделей layout analysis
- `tesseract` - для OCR (через системные зависимости)

### 5.2. Системные зависимости

- **Tesseract OCR:** Требуется для OCR обработки
- **CUDA/GPU:** Опционально для ускорения обработки (если `allow_gpu=true`)

---

## 6. Приоритет конфигурации

1. **YAML template** (приоритет 1) - если существует для route
2. **Legacy hardcoded** (fallback) - если template не найден
3. **Environment variables** - для внешних сервисов (VLM, MongoDB)

---

**Следующий документ:** [CONTRACTS_AND_DATA.md](CONTRACTS_AND_DATA.md) - контракты и потоки данных

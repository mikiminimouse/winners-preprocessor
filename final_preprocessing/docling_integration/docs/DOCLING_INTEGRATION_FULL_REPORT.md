# Docling Integration: Полный технический отчёт

**Дата:** 2026-01-16
**Версия:** 1.1.0
**Автор:** Автоматически сгенерирован на основе анализа кодовой базы

---

## Оглавление

1. [Обзор архитектуры](#1-обзор-архитектуры)
2. [Схема потока данных](#2-схема-потока-данных)
3. [Компоненты системы](#3-компоненты-системы)
4. [Pipeline Templates (YAML)](#4-pipeline-templates-yaml)
5. [Экспортёры результатов](#5-экспортёры-результатов)
6. [Проблемы и области улучшения](#6-проблемы-и-области-улучшения)
7. [Рекомендации по Best Practices](#7-рекомендации-по-best-practices)
8. [Внешние зависимости Docling](#8-внешние-зависимости-docling)

---

## 1. Обзор архитектуры

### 1.1 Структура проекта

```
docling_integration/
├── __init__.py                    # Public API
├── _docling_import.py            # Централизованный импорт Docling
├── config.py                     # YAML → PipelineOptions (236 строк)
├── constants.py                  # Маппинги и константы (97 строк)
├── pipeline.py                   # DoclingPipeline orchestration (422 строки)
├── runner.py                     # DocumentConverter wrapper (223 строки)
├── bridge_docprep.py             # Интеграция с DocPrep (236 строк)
├── system_check.py               # Валидация системы
│
├── exporters/                    # Экспортёры результатов
│   ├── json.py                   # → JSON (model_dump)
│   ├── markdown.py               # → Markdown (export_to_markdown)
│   └── mongodb.py                # → Local MongoDB
│
├── pipeline_templates/           # YAML конфигурации (11 файлов)
│   ├── pdf_text.yaml            # Digital PDF (оптимизирован)
│   ├── pdf_text_tables.yaml     # PDF с таблицами
│   ├── pdf_scan.yaml            # Scanned PDF (OCR)
│   ├── pdf_scan_table.yaml      # Scanned PDF + Tables
│   ├── docx.yaml                # MS Word
│   ├── xlsx.yaml                # MS Excel
│   ├── pptx.yaml                # MS PowerPoint
│   ├── html.yaml                # HTML
│   ├── xml.yaml                 # XML
│   ├── rtf.yaml                 # RTF
│   └── image_ocr.yaml           # Images (JPG, PNG, TIFF)
│
├── scripts/                      # Тестовые скрипты
└── tests/                        # Pytest тесты (8 passed)
```

### 1.2 Принципы архитектуры

| Принцип | Реализация |
|---------|------------|
| **YAML-Driven Config** | Конфигурация через `pipeline_templates/*.yaml` |
| **Contract as Source of Truth** | `docprep.contract.json` — единственный вход |
| **Thin Wrapper** | Минимальная обёртка над `DocumentConverter` |
| **Graceful Degradation** | `skip_failed=True`, quarantine директория |
| **Thread-Safe Counters** | `ProcessedCountsManager` с Lock |

---

## 2. Схема потока данных

### 2.1 Полный pipeline от входа до результата

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         ВХОДНЫЕ ДАННЫЕ                                   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Ready2Docling/                                                          │
│  └── UNIT_005f915e838b47ac/                                             │
│      ├── docprep.contract.json  ← ИСТОЧНИК ИСТИНЫ                        │
│      │   {                                                               │
│      │     "routing": {"docling_route": "pdf_text"},                    │
│      │     "source": {"original_filename": "Protocol.pdf"},             │
│      │     "unit": {"batch_date": "2025-03-04", "unit_id": "UNIT_..."}  │
│      │   }                                                               │
│      ├── manifest.json          ← НЕ используется Docling                │
│      └── files/                                                          │
│          └── Protocol.pdf       ← Файл для обработки                     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               │
┌──────────────────────────────────┐               │
│   1. bridge_docprep.py           │               │
│   load_unit_from_ready2docling() │               │
│   ─────────────────────────────  │               │
│   • Загрузка contract.json       │               │
│   • Валидация готовности         │               │
│   • Поиск главного файла         │               │
│   • Извлечение route             │               │
└──────────────────────────────────┘               │
                    │                               │
                    ▼                               │
┌──────────────────────────────────┐               │
│   unit_data = {                  │               │
│     "contract": {...},           │               │
│     "route": "pdf_text",         │               │
│     "unit_id": "UNIT_...",       │               │
│     "files": [Path(...)],        │               │
│     "unit_path": Path(...)       │               │
│   }                              │               │
└──────────────────────────────────┘               │
                    │                               │
                    ▼                               │
┌──────────────────────────────────┐               │
│   2. config.py                   │               │
│   build_docling_options(route)   │               │
│   ─────────────────────────────  │               │
│   • load_pipeline_template()     │◄──────────────┤
│   • LRU cache (32 slots)         │               │
│   • _build_options_from_template │               │
└──────────────────────────────────┘               │
                    │                               │
                    ▼                               │
┌──────────────────────────────────┐    ┌─────────┴─────────┐
│   pipeline_templates/pdf_text.yaml    │  YAML Template    │
│   ─────────────────────────────────   └───────────────────┘
│   route: pdf_text                │
│   models:                        │
│     layout: off       ← Ускорение│
│     tables: off       ← Ускорение│
│     ocr: off                     │
│   docling:                       │
│     extract_tables: false        │
│     images_scale: 0.5            │
│     generate_page_images: false  │
└──────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────┐
│   PdfPipelineOptions(            │
│     do_ocr=False,                │
│     do_table_structure=False,    │
│     images_scale=0.5,            │
│     generate_page_images=False   │
│   )                              │
└──────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│   3. runner.py                                                            │
│   run_docling_conversion(file_path, options, input_format)               │
│   ───────────────────────────────────────────────────────                │
│                                                                           │
│   from docling.document_converter import DocumentConverter, FormatOption  │
│   from docling.datamodel.base_models import InputFormat                   │
│                                                                           │
│   format_options = {                                                      │
│       InputFormat.PDF: FormatOption(                                     │
│           pipeline_options=pdf_options,                                   │
│           pipeline_cls=None,  # StandardPdfPipeline (default)            │
│           backend=None        # PyPdfiumDocumentBackend (default)        │
│       )                                                                   │
│   }                                                                       │
│                                                                           │
│   converter = DocumentConverter(format_options=format_options)            │
│   result = converter.convert(str(file_path))                             │
│                                                                           │
│   return result  # ConversionResult с .document (DoclingDocument)        │
└──────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│   ConversionResult                                                        │
│   ────────────────                                                        │
│   .document: DoclingDocument     ← Главный результат                      │
│   .status: ConversionStatus                                               │
│   .errors: List[str]                                                      │
│   .timings: Dict                                                          │
└──────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│   4. ЭКСПОРТЁРЫ (параллельно)                                            │
└──────────────────────────────────────────────────────────────────────────┘
          │                    │                    │
          ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐
│ exporters/      │  │ exporters/      │  │ exporters/mongodb.py        │
│ json.py         │  │ markdown.py     │  │                             │
│ ───────────────│  │ ───────────────│  │ export_to_mongodb(          │
│                 │  │                 │  │   document,                  │
│ document.       │  │ document.       │  │   contract,                  │
│   model_dump()  │  │   document.     │  │   unit_id                    │
│                 │  │ export_to_      │  │ )                            │
│ + metadata      │  │   markdown()    │  │                             │
└─────────────────┘  │                 │  │ mongo_doc = {               │
          │          │ + YAML          │  │   "unit_id": unit_id,       │
          ▼          │   frontmatter   │  │   "docling_document":       │
┌─────────────────┐  └─────────────────┘  │     document.model_dump(),  │
│ OutputDocling/  │           │          │   "contract": contract,      │
│ pdf/            │           ▼          │   "route": route,            │
│ UNIT_.../       │  ┌─────────────────┐  │   "protocol_date": date,    │
│ UNIT_....json   │  │ OutputDocling/  │  │   "created_at": datetime    │
└─────────────────┘  │ pdf/            │  │ }                           │
                     │ UNIT_.../       │  │                             │
                     │ UNIT_....md     │  │ collection.update_one(      │
                     └─────────────────┘  │   {"unit_id": unit_id},     │
                                          │   {"$set": mongo_doc},      │
                                          │   upsert=True               │
                                          │ )                           │
                                          └─────────────────────────────┘
                                                       │
                                                       ▼
                                          ┌─────────────────────────────┐
                                          │ MongoDB: docling_metadata   │
                                          │ Collection: docling_results │
                                          │ ─────────────────────────── │
                                          │ Indexes:                    │
                                          │ • unit_id (unique)          │
                                          │ • protocol_date             │
                                          │ • route                     │
                                          │ • (protocol_date, route)    │
                                          └─────────────────────────────┘
```

### 2.2 Результат обработки

```python
result = {
    "success": True,
    "unit_id": "UNIT_005f915e838b47ac",
    "route": "pdf_text",
    "document": <ConversionResult>,  # .document содержит DoclingDocument
    "exports": {
        "json": "/path/OutputDocling/pdf/UNIT_.../UNIT_....json",
        "markdown": "/path/OutputDocling/pdf/UNIT_.../UNIT_....md",
        "mongodb": "ObjectId(...)"
    },
    "processing_time": 8.34,  # секунды
    "errors": []
}
```

---

## 3. Компоненты системы

### 3.1 `_docling_import.py` — Централизованный импорт

**Назначение:** Избежать конфликтов между локальными модулями и site-packages Docling.

```python
# Ключевые функции:
ensure_docling_import()              # Инициализация при первом использовании
import_installed_docling_module()    # Импорт из site-packages
is_docling_available() -> bool       # Проверка доступности
get_document_converter()             # → DocumentConverter class
get_pipeline_options()               # → PipelineOptions class
get_pdf_pipeline_options()           # → PdfPipelineOptions class
get_input_format()                   # → InputFormat enum
```

### 3.2 `config.py` — Конфигурация из YAML (236 строк)

**Назначение:** Маппинг `route → PipelineOptions` через YAML templates.

```python
# Основные функции:
load_pipeline_template(route: str) -> Optional[Dict]
    # Загружает YAML, кэширует через @lru_cache(maxsize=32)

build_docling_options(route: str) -> Optional[PipelineOptions]
    # Строит PipelineOptions из template
    # Raises ValueError если template не найден

# Применяемые настройки из YAML:
# - models.layout: "off" | "publaynet_detectron2" | "docbank"
# - models.tables: "off" | "table-transformer" | "cascadetabnet"
# - models.ocr: "off" | "tesseract"
# - docling.extract_tables: bool
# - docling.images_scale: float
# - docling.generate_page_images: bool
# - docling.generate_picture_images: bool
```

### 3.3 `bridge_docprep.py` — Интеграция с DocPrep (236 строк)

**Назначение:** Загрузка UNIT из Ready2Docling, используя ТОЛЬКО contract.

```python
# Главные функции:
load_unit_from_ready2docling(unit_path: Path) -> Dict
    # Возвращает:
    # - contract: docprep.contract.json (ОБЯЗАТЕЛЕН)
    # - files: список файлов
    # - unit_id, route, unit_path
    # - ast_nodes (опционально)
    # - validation

get_main_file(unit_data: Dict) -> Optional[Path]
    # Приоритет:
    # 1. contract.source.original_filename
    # 2. AST nodes с role="document"
    # 3. Первый файл с поддерживаемым расширением
```

**Критическая валидация:**
- `route == "mixed"` → ValueError (должно фильтроваться в merger)
- `route == "unknown"` → ValueError
- Файлы `.zip`, `.rar`, `.7z` → ValueError

### 3.4 `runner.py` — Обёртка DocumentConverter (223 строки)

**Назначение:** Тонкая обёртка с retry и счётчиками.

```python
run_docling_conversion(
    file_path: Path,
    options: Optional[PipelineOptions] = None,
    input_format: Optional[InputFormat] = None,  # Не используется
    max_retries: int = 1,
    retry_delay: float = 1.0,
    check_limit: bool = False,
    limit_per_format: int = 50
) -> Optional[ConversionResult]

# Внутренняя логика:
# 1. Валидация файла
# 2. Построение format_options из PipelineOptions
# 3. DocumentConverter(format_options=...).convert(str(file_path))
# 4. Retry при ошибках
# 5. Thread-safe счётчики через ProcessedCountsManager
```

### 3.5 `pipeline.py` — DoclingPipeline (422 строки)

**Назначение:** Главный orchestration класс.

```python
class DoclingPipeline:
    def __init__(
        self,
        export_json: bool = True,
        export_markdown: bool = False,  # По умолчанию ВЫКЛЮЧЕН
        export_mongodb: bool = True,
        base_output_dir: Optional[Path] = None,
        ready2docling_dir: Optional[Path] = None,
        quarantine_dir: Optional[Path] = None,
        skip_failed: bool = True
    )

    def process_unit(self, unit_path: Path) -> Dict[str, Any]
        # Полный цикл обработки одного UNIT

    def process_directory(
        self,
        ready2docling_dir: Path,
        limit: Optional[int] = None,
        recursive: bool = True
    ) -> Dict[str, Any]
        # Массовая обработка всех UNIT_* директорий
```

**Структура выхода:**
```
OutputDocling/
├── pdf/
│   └── UNIT_005f915e838b47ac/
│       ├── UNIT_005f915e838b47ac.json
│       └── UNIT_005f915e838b47ac.md
├── docx/
│   └── UNIT_.../
├── xlsx/
│   └── UNIT_.../
└── image/
    └── UNIT_.../
```

---

## 4. Pipeline Templates (YAML)

### 4.1 Обзор маршрутов

| Route | Тип | OCR | Layout | Tables | Performance | Когда использовать |
|-------|-----|-----|--------|--------|-------------|-------------------|
| `pdf_text` | Digital | ❌ | ❌ | ❌ | 200-400/hr | **По умолчанию** для PDF |
| `pdf_text_tables` | Digital | ❌ | ✅ | ✅ | 40-70/hr | PDF с важными таблицами |
| `pdf_scan` | Scanned | ✅ | ✅ | ❌ | 10-20/hr | Сканированные PDF |
| `pdf_scan_table` | Scanned | ✅ | ✅ | ✅ | 4-8/hr | **Самый медленный** |
| `docx` | Native | ❌ | native | native | 100-200/hr | MS Word |
| `xlsx` | Native | ❌ | native | native | 80-150/hr | MS Excel |
| `pptx` | Native | ❌ | native | native | ~100/hr | MS PowerPoint |
| `html` | Web | ❌ | native | native | 150-300/hr | HTML страницы |
| `xml` | Structured | ❌ | native | native | 150-300/hr | XML документы |
| `rtf` | Text | ❌ | native | ❌ | ~100/hr | RTF документы |
| `image_ocr` | Images | ✅ | ❌ | ✅ | 60-100/hr | JPG, PNG, TIFF |

### 4.2 Оптимизированный `pdf_text.yaml`

```yaml
route: pdf_text

models:
  layout: off           # ← КРИТИЧНО: отключает publaynet_detectron2 (~30-40 сек)
  tables: off           # ← КРИТИЧНО: отключает table-transformer (~20-30 сек)
  ocr: off

docling:
  parse_text: true
  extract_tables: false  # ← Согласовано с models.tables
  extract_figures: false
  images_scale: 0.5     # ← Оптимизация памяти (2x меньше)
  generate_page_images: false
  generate_picture_images: false

processing_constraints:
  max_runtime_sec: 60   # ← Уменьшен с 180
  max_memory_mb: 2048   # ← Уменьшен с 4096
```

### 4.3 `pdf_text_tables.yaml` — когда таблицы важны

```yaml
route: pdf_text_tables

models:
  layout: publaynet_detectron2  # ← Включен для детекции таблиц
  tables: table-transformer     # ← Включен для извлечения

docling:
  extract_tables: true
  extract_figures: true
  preserve_layout: true
  images_scale: 1.0     # ← Полное качество

processing_constraints:
  max_runtime_sec: 180
  max_memory_mb: 4096
```

---

## 5. Экспортёры результатов

### 5.1 JSON Export (`exporters/json.py`)

```python
def export_to_json(document, output_path, metadata=None) -> Path:
    # Использует document.model_dump() для сериализации
    # Добавляет _export_metadata с timestamp
```

**Формат выхода:**
```json
{
  "document": { /* DoclingDocument structure */ },
  "_export_metadata": {
    "exported_at": "2025-03-04T12:00:00Z",
    "export_format": "json",
    "unit_id": "UNIT_...",
    "route": "pdf_text"
  }
}
```

### 5.2 Markdown Export (`exporters/markdown.py`)

```python
def export_to_markdown(document, output_path, metadata=None) -> Path:
    # 1. Извлекает DoclingDocument из ConversionResult
    # 2. Вызывает doc.export_to_markdown()
    # 3. Добавляет YAML frontmatter с метаданными
```

**Формат выхода:**
```markdown
---
exported_at: 2025-03-04T12:00:00Z
export_format: markdown
unit_id: UNIT_005f915e838b47ac
route: pdf_text
---

# Заголовок документа

Содержимое...
```

### 5.3 MongoDB Export (`exporters/mongodb.py`)

```python
def export_to_mongodb(document, contract, unit_id) -> str:
    # Формирует mongo_doc:
    mongo_doc = {
        "unit_id": unit_id,
        "protocol_id": "",
        "protocol_date": contract.unit.batch_date,
        "route": contract.routing.docling_route,
        "docling_document": document.model_dump(),
        "contract": contract,
        "cost_estimation": contract.cost_estimation,
        "created_at": datetime.utcnow()
    }
    # Upsert по unit_id (идемпотентно)
```

**Индексы MongoDB:**
- `unit_id` (unique) — для идемпотентности
- `protocol_date` — для фильтрации по дате
- `route` — для фильтрации по типу
- `(protocol_date, route)` — составной индекс

**Переменные окружения:**
```bash
LOCAL_MONGO_SERVER=localhost:27018
MONGO_METADATA_USER=admin
MONGO_METADATA_PASSWORD=password
MONGO_METADATA_DB=docling_metadata
```

---

## 6. Проблемы и области улучшения

### 6.1 КРИТИЧЕСКИЕ ПРОБЛЕМЫ

#### P1: `runner.py` — Неоптимальное создание FormatOption

**Текущий код (runner.py:128-141):**
```python
if options is not None:
    from docling.document_converter import FormatOption
    from docling.datamodel.base_models import InputFormat
    format_options = {}

    if hasattr(options, 'pdf') and options.pdf is not None:
        format_options[InputFormat.PDF] = FormatOption(
            pipeline_options=options.pdf,
            pipeline_cls=None,  # ← ПРОБЛЕМА: должен быть StandardPdfPipeline
            backend=None        # ← ПРОБЛЕМА: должен быть PyPdfiumDocumentBackend
        )
```

**Проблема:** Передача `None` для `pipeline_cls` и `backend` может привести к неожиданному поведению в некоторых версиях Docling.

**Рекомендация по Best Practice Docling:**
```python
from docling.pipeline.standard_pdf_pipeline import StandardPdfPipeline
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend

format_options[InputFormat.PDF] = PdfFormatOption(
    pipeline_options=pipeline_options,
    pipeline_cls=StandardPdfPipeline,  # ← Явно указать
    backend=PyPdfiumDocumentBackend    # ← Явно указать
)
```

---

#### P2: YAML настройки не полностью применяются

**Текущий код (config.py):**
```python
# Эти настройки из YAML НЕ применяются к PdfPipelineOptions:
# - performance.threads → НЕТ в PdfPipelineOptions
# - performance.batch_pages → НЕТ в PdfPipelineOptions
# - processing_constraints.max_runtime_sec → НЕТ в PdfPipelineOptions
# - language.primary → НЕТ в PdfPipelineOptions
```

**Проблема:** YAML содержит настройки, которые не применяются через API Docling.

**Рекомендация:** Удалить неиспользуемые настройки из YAML или использовать `AcceleratorOptions`:
```python
from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions

pipeline_options.accelerator_options = AcceleratorOptions(
    num_threads=4,  # ← Это работает
    device=AcceleratorDevice.AUTO
)
```

---

#### P3: OCR для русского языка не настроен

**Текущий код (pdf_scan.yaml):**
```yaml
docling:
  force_ocr: true
  language: eng  # ← ПРОБЛЕМА: только английский
```

**Проблема:** Tesseract настроен только на английский, русский текст будет плохо распознаваться.

**Рекомендация:**
```python
from docling.datamodel.pipeline_options import TesseractOcrOptions

pipeline_options.ocr_options = TesseractOcrOptions(
    lang=["rus", "eng"],  # ← Добавить русский
    tesseract_cmd="/usr/bin/tesseract"  # ← Явный путь
)
```

Или использовать EasyOCR (лучше для русского):
```python
from docling.datamodel.pipeline_options import EasyOcrOptions

pipeline_options.ocr_options = EasyOcrOptions(
    lang=["ru", "en"],
    confidence_threshold=0.5
)
```

---

### 6.2 СРЕДНИЕ ПРОБЛЕМЫ

#### P4: Markdown экспорт теряет структуру

**Проблема:** `export_to_markdown()` возвращает плоский текст без учёта иерархии заголовков.

**Симптом:** Заголовки документа не форматируются как `#`, `##`, `###`.

**Причина:** Docling `export_to_markdown()` — это базовый метод, не учитывающий семантику.

**Рекомендация:** Использовать `HierarchicalChunker` для сохранения структуры:
```python
from docling_core.transforms.chunker import HierarchicalChunker

chunker = HierarchicalChunker()
chunks = list(chunker.chunk(doc))

# Каждый chunk имеет:
# - chunk.text
# - chunk.meta.headings (список заголовков)
# - chunk.meta.doc_items (ссылки на элементы)
```

---

#### P5: Отсутствует параллелизация обработки

**Текущий код (pipeline.py:370-414):**
```python
for unit_dir in unit_dirs:
    result = self.process_unit(unit_dir)  # ← Последовательно
```

**Проблема:** Обработка выполняется последовательно, не используя многоядерность CPU.

**Рекомендация:**
```python
from concurrent.futures import ThreadPoolExecutor, as_completed

with ThreadPoolExecutor(max_workers=4) as executor:
    futures = {
        executor.submit(self.process_unit, unit_dir): unit_dir
        for unit_dir in unit_dirs
    }
    for future in as_completed(futures):
        result = future.result()
```

---

#### P6: Нет кэширования результатов по hash файла

**Проблема:** Повторная обработка того же файла выполняется заново.

**Рекомендация:** Кэширование через file hash:
```python
import hashlib

def get_file_hash(file_path: Path) -> str:
    with open(file_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

# Проверка кэша перед обработкой
cache_key = f"{unit_id}:{get_file_hash(main_file)}"
if cache_key in results_cache:
    return results_cache[cache_key]
```

---

### 6.3 НИЗКИЕ ПРОБЛЕМЫ

#### P7: Общие Exception вместо специфичных

**Текущий код:**
```python
except Exception as e:
    logger.error(f"Pipeline failed: {e}")
```

**Рекомендация:** Использовать специфичные исключения:
```python
from docling.exceptions import ConversionError, UnsupportedFormatError

try:
    document = converter.convert(file_path)
except UnsupportedFormatError:
    # Файл не поддерживается
except ConversionError:
    # Ошибка конвертации
except TimeoutError:
    # Превышен timeout
```

---

#### P8: `input_format` в runner.py не используется

**Код:**
```python
def run_docling_conversion(
    file_path: Path,
    options: Optional[PipelineOptions] = None,
    input_format: Optional[InputFormat] = None,  # ← Не используется
```

**Факт:** Docling автоматически определяет формат по расширению файла.

**Рекомендация:** Удалить параметр или использовать для `allowed_formats`:
```python
converter = DocumentConverter(
    allowed_formats=[input_format] if input_format else None
)
```

---

## 7. Рекомендации по Best Practices

### 7.1 Рекомендуемая конфигурация DocumentConverter

```python
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    EasyOcrOptions,  # или TesseractOcrOptions
    TableFormerMode,
)
from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
from docling.pipeline.standard_pdf_pipeline import StandardPdfPipeline
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend

# === Для pdf_text (быстрый, без таблиц) ===
pdf_options_fast = PdfPipelineOptions()
pdf_options_fast.do_ocr = False
pdf_options_fast.do_table_structure = False
pdf_options_fast.images_scale = 0.5
pdf_options_fast.generate_page_images = False
pdf_options_fast.generate_picture_images = False
pdf_options_fast.accelerator_options = AcceleratorOptions(
    num_threads=4,
    device=AcceleratorDevice.CPU
)

# === Для pdf_text_tables (с таблицами) ===
pdf_options_tables = PdfPipelineOptions()
pdf_options_tables.do_ocr = False
pdf_options_tables.do_table_structure = True
pdf_options_tables.table_structure_options.mode = TableFormerMode.ACCURATE
pdf_options_tables.table_structure_options.do_cell_matching = True

# === Для pdf_scan (OCR) ===
pdf_options_ocr = PdfPipelineOptions()
pdf_options_ocr.do_ocr = True
pdf_options_ocr.ocr_options = EasyOcrOptions(
    lang=["ru", "en"],
    confidence_threshold=0.5
)

# === Создание конвертера ===
converter = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(
            pipeline_options=pdf_options_fast,
            pipeline_cls=StandardPdfPipeline,
            backend=PyPdfiumDocumentBackend
        )
    }
)
```

### 7.2 Chunking для RAG

```python
from docling_core.transforms.chunker import HierarchicalChunker

doc = converter.convert(file_path).document
chunker = HierarchicalChunker()

chunks = list(chunker.chunk(doc))
for chunk in chunks:
    print(f"Text: {chunk.text[:100]}...")
    print(f"Headings: {chunk.meta.headings}")
    print(f"Page: {chunk.meta.doc_items[0].prov[0].page_no if chunk.meta.doc_items else 'N/A'}")
```

### 7.3 Интеграция с LlamaIndex

```python
from llama_index.readers.docling import DoclingReader
from llama_index.node_parser.docling import DoclingNodeParser

# Для сохранения grounding (page numbers, bounding boxes)
reader = DoclingReader(export_type=DoclingReader.ExportType.JSON)
node_parser = DoclingNodeParser()

documents = reader.load_data(source_path)
nodes = node_parser.get_nodes_from_documents(documents)
```

---

## 8. Внешние зависимости Docling

### 8.1 Основные зависимости

| Пакет | Версия | Назначение |
|-------|--------|------------|
| `docling` | >=2.60.0 | Основная библиотека |
| `docling-core` | >=2.50.0 | Core модели и chunking |
| `pymongo` | >=4.0.0 | MongoDB экспорт |
| `pyyaml` | >=6.0 | YAML parsing |

### 8.2 Опциональные зависимости (для OCR/Layout)

| Пакет | Когда нужен |
|-------|-------------|
| `tesseract-ocr` | route: pdf_scan, image_ocr |
| `easyocr` | Альтернатива Tesseract (лучше для русского) |
| `torch` | Для GPU-ускорения моделей |
| `detectron2` | Layout detection (publaynet) |
| `transformers` | Table extraction (table-transformer) |

### 8.3 Cloud.ru интеграции (будущее)

| Сервис | Назначение |
|--------|------------|
| Cloud.ru Granite Docling VLM | Улучшенное понимание документов |
| Cloud.ru PaddleOCR VLM | GPU-ускоренная OCR |

---

## Заключение

Docling Integration представляет собой хорошо структурированный компонент с YAML-driven конфигурацией. Основные области для улучшения:

1. **Критические:** Исправить создание FormatOption в runner.py, добавить русский язык в OCR
2. **Средние:** Добавить параллелизацию, улучшить Markdown экспорт через Chunker
3. **Низкие:** Специфичные исключения, кэширование результатов

**Текущий статус тестов:** 8 passed, 3 skipped (smoke tests OK)

**Производительность:**
- pdf_text: ~200-400 PDF/час (оптимизирован)
- DOCX: ~100-200/час
- XLSX: ~80-150/час

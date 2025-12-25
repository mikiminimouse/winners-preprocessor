# Контракты и потоки данных

**Дата создания:** 2025-12-24  
**Версия:** 1.0

## Обзор

Система использует формализованный контракт (`docprep.contract.json`) как границу между DocPrep и Docling Integration, обеспечивая контрактную строгость и однозначность обработки.

---

## 1. docprep.contract.json

### 1.1. Структура контракта

**Расположение:** `Ready2Docling/{extension}/{unit_id}/docprep.contract.json`

**Версия:** 1.0

```json
{
  "contract_version": "1.0",
  "unit": {
    "unit_id": "UNIT_xxx",
    "batch_date": "2025-03-04",
    "state": "READY_FOR_DOCLING",
    "correlation_id": "uuid-xxxx-xxxx-xxxx"
  },
  "source": {
    "original_filename": "document.pdf",
    "detected_mime": "application/pdf",
    "true_extension": "pdf",
    "size_bytes": 12345,
    "checksum_sha256": "abc123..."
  },
  "document_profile": {
    "document_type": "pdf",
    "content_type": "text",
    "language_hint": ["ru"],
    "page_count": 10,
    "needs_ocr": false,
    "has_tables": true,
    "has_forms": false,
    "quality_score": 0.8
  },
  "routing": {
    "docling_route": "pdf_text",
    "priority": "normal",
    "pipeline_version": "2025-01"
  },
  "processing_constraints": {
    "allow_gpu": false,
    "max_runtime_sec": 180,
    "max_memory_mb": 4096
  },
  "history": {
    "docprep_cycles": 1,
    "transformations": [
      {
        "type": "convert",
        "timestamp": "2025-03-04T12:00:00Z"
      }
    ]
  },
  "cost_estimation": {
    "cpu_seconds_estimate": 10,
    "cost_usd_estimate": 0.000139
  }
}
```

### 1.2. Поля контракта

#### unit

Метаданные UNIT.

- `unit_id` (str, обязательное): Идентификатор UNIT
- `batch_date` (str, обязательное): Дата батча (формат: YYYY-MM-DD)
- `state` (str): Состояние UNIT (обычно "READY_FOR_DOCLING")
- `correlation_id` (str): UUID для трейсинга

#### source

Информация об исходном файле.

- `original_filename` (str, обязательное): Оригинальное имя файла
- `detected_mime` (str): Определенный MIME тип
- `true_extension` (str, обязательное): Реальное расширение файла
- `size_bytes` (int): Размер файла в байтах
- `checksum_sha256` (str): SHA256 хеш файла

#### document_profile

Профиль документа для обработки.

- `document_type` (str): Тип документа (pdf, docx, и т.д.)
- `content_type` (str): Тип содержимого (text, scan, scan_table, image)
- `language_hint` (list[str]): Подсказки по языку
- `page_count` (int): Количество страниц
- `needs_ocr` (bool): Требуется ли OCR
- `has_tables` (bool): Есть ли таблицы
- `has_forms` (bool): Есть ли формы
- `quality_score` (float): Оценка качества (0.0-1.0)

#### routing

Маршрутизация для Docling.

- `docling_route` (str, обязательное): Route для Docling (pdf_text, pdf_scan, docx, и т.д.)
- `priority` (str): Приоритет обработки (normal, high, low)
- `pipeline_version` (str): Версия pipeline

**КРИТИЧЕСКИ ВАЖНО:** `docling_route` не должен быть "mixed" или "unknown". Такие UNIT должны быть отфильтрованы в merger.

#### processing_constraints

Ограничения на обработку.

- `allow_gpu` (bool): Разрешить использование GPU
- `max_runtime_sec` (int): Максимальное время обработки
- `max_memory_mb` (int): Максимальное использование памяти

#### history

История обработки в DocPrep.

- `docprep_cycles` (int): Количество циклов обработки в DocPrep
- `transformations` (list): Список трансформаций

#### cost_estimation

Оценка стоимости обработки.

- `cpu_seconds_estimate` (int): Оценка времени обработки в секундах
- `cost_usd_estimate` (float): Оценка стоимости в USD

### 1.3. Генерация контракта

**Файл:** `final_preprocessing/docprep/core/contract.py`

**Функция:** `generate_contract_from_manifest(unit_path: Path, manifest: Optional[Dict] = None, main_file_path: Optional[Path] = None) -> Dict[str, Any]`

**Процесс:**

1. Загрузка manifest (если не передан)
2. Определение route из manifest или из файлов/путей
3. Определение главного файла (если не передан)
4. Извлечение метаданных из manifest
5. Вычисление checksum файла
6. Оценка стоимости обработки
7. Формирование контракта

**Валидация:**

- Route не должен быть "mixed" или "unknown"
- Должен быть определен главный файл
- `docling_route` должен быть валидным

**Сохранение:**

```python
contract_path = unit_path / "docprep.contract.json"
with open(contract_path, "w", encoding="utf-8") as f:
    json.dump(contract, f, indent=2, ensure_ascii=False)
```

### 1.4. Загрузка контракта

**Файл:** `final_preprocessing/docprep/core/contract.py`

**Функция:** `load_contract(unit_path: Path) -> Dict[str, Any]`

**Использование:**

```python
contract = load_contract(unit_path)
route = contract["routing"]["docling_route"]
unit_id = contract["unit"]["unit_id"]
```

**Обработка ошибок:**

- `FileNotFoundError` - если contract не найден

### 1.5. Валидация контракта

Валидация выполняется в `bridge_docprep.py`:

```python
# КРИТИЧЕСКАЯ ВАЛИДАЦИЯ: route не должен быть "mixed"
if route == "mixed":
    raise ValueError(
        f"Contract contains route='mixed' for unit {unit_id}. "
        f"This violates contract boundary - mixed units must be filtered before Ready2Docling."
    )

if not route or route == "unknown":
    raise ValueError(
        f"Contract does not contain valid route for unit {unit_id}. "
        f"Route must be explicitly defined in contract.routing.docling_route."
    )
```

---

## 2. Потоки данных

### 2.1. Input (Входные данные)

#### Структура директорий

```
Ready2Docling/
├── docx/
│   └── UNIT_xxx/
│       ├── files/
│       │   └── document.docx
│       ├── docprep.contract.json
│       └── manifest.json (не используется Docling)
├── pdf/
│   └── UNIT_yyy/
│       └── ...
└── xlsx/
    └── UNIT_zzz/
        └── ...
```

#### Компоненты входа

1. **UNIT директория:** `Ready2Docling/{extension}/{unit_id}/`
2. **Файлы документов:** `files/` или напрямую в UNIT директории
3. **Контракт:** `docprep.contract.json` (обязателен)
4. **Manifest:** `manifest.json` (не используется Docling, только для DocPrep)

#### Главный файл

Главный файл определяется через:

1. **AST nodes:** Файл с ролью "document" в AST nodes
2. **Приоритет расширений:** По расширению файла
3. **Fallback:** Первый поддерживаемый файл

### 2.2. Processing (Обработка)

#### Этапы обработки Docling

1. **Format Detection (автоматически):**
   - Docling определяет формат по расширению файла и сигнатуре
   - Используется `InputFormat` enum

2. **Pipeline Initialization:**
   - Создание `DocumentConverter` с `PipelineOptions`
   - Инициализация моделей (если требуется)

3. **Document Processing:**
   - Извлечение текста, таблиц, изображений
   - Анализ layout (если настроено)
   - OCR (если требуется)

4. **ConversionResult:**
   - Создание `ConversionResult` объекта
   - Содержит `DoclingDocument` с результатами обработки

#### Внутренняя структура DoclingDocument

```python
ConversionResult
├── document (DoclingDocument)
│   ├── schema_name
│   ├── version
│   ├── name
│   ├── origin
│   ├── body (BodyNode)
│   │   ├── self_ref
│   │   ├── parent
│   │   ├── children (list of CREF)
│   │   └── content_layer
│   ├── groups (list of GroupNode)
│   │   ├── self_ref
│   │   ├── parent (CREF)
│   │   ├── children (list of CREF)
│   │   ├── name
│   │   └── label
│   ├── texts (list of TextNode)
│   │   ├── self_ref
│   │   ├── parent (CREF)
│   │   ├── text
│   │   ├── label (section_header, text, list_item, и т.д.)
│   │   ├── level (для заголовков)
│   │   └── formatting (bold, italic, и т.д.)
│   ├── tables (list of TableNode)
│   │   ├── self_ref
│   │   └── data (TableData)
│   │       └── table_cells (list of TableCell)
│   ├── pictures (list of PictureNode)
│   ├── pages (list of PageNode)
│   └── ...
├── input
├── assembled
├── errors
└── ...
```

### 2.3. Output (Выходные данные)

#### Структура директорий

```
OutputDocling/
├── docx/
│   └── UNIT_xxx/
│       ├── UNIT_xxx.json
│       └── UNIT_xxx.md
├── pdf/
│   └── UNIT_yyy/
│       ├── UNIT_yyy.json
│       └── UNIT_yyy.md
└── xlsx/
    └── UNIT_zzz/
        └── ...
```

#### JSON экспорт

**Путь:** `OutputDocling/{extension}/{unit_id}/{unit_id}.json`

**Содержимое:**

- Полный `DoclingDocument` через `model_dump()`
- Метаданные экспорта: `_export_metadata`

**Формат:**

```json
{
  "schema_name": "docling-1.0",
  "version": "1.0",
  "document": {
    "body": {...},
    "groups": [...],
    "texts": [...],
    "tables": [...],
    "pictures": [...],
    ...
  },
  "_export_metadata": {
    "exported_at": "2025-03-04T12:00:00Z",
    "export_format": "json",
    "unit_id": "UNIT_xxx",
    "route": "pdf_text",
    "protocol_date": "2025-03-04"
  }
}
```

#### Markdown экспорт

**Путь:** `OutputDocling/{extension}/{unit_id}/{unit_id}.md`

**Содержимое:**

- Метаданные в YAML front matter
- Структурированный контент с сохранением layout:
  - Заголовки (`##`, `###`)
  - Абзацы
  - Списки (`- `)
  - Таблицы (Markdown таблицы)
  - Изображения (`![caption](path)`)

**Формат:**

```markdown
---
exported_at: 2025-03-04T12:00:00Z
export_format: markdown
unit_id: UNIT_xxx
route: pdf_text
protocol_date: 2025-03-04
---

## Заголовок

Текст абзаца.

- Элемент списка 1
- Элемент списка 2

| Колонка 1 | Колонка 2 |
| --- | --- |
| Ячейка 1 | Ячейка 2 |
```

#### MongoDB экспорт

**Коллекция:** `docling_results` (или указанная в параметрах)

**Структура документа:**

```json
{
  "unit_id": "UNIT_xxx",
  "protocol_date": "2025-03-04",
  "route": "pdf_text",
  "docling_document": {...},
  "contract": {...},
  "export_formats": ["mongodb"],
  "created_at": ISODate("2025-03-04T12:00:00Z"),
  "cost_estimation": {...}
}
```

**Индексы:**

- `unit_id` (unique)
- `protocol_date`
- `route`
- `(protocol_date, route)` (составной)

---

## 3. Маппинг contract → Docling route

### 3.1. Route из contract

```python
routing = contract.get("routing", {})
route = routing.get("docling_route")
```

### 3.2. Route → InputFormat

```python
route_to_format = {
    "pdf_text": InputFormat.PDF,
    "pdf_scan": InputFormat.PDF,
    "pdf_mixed": InputFormat.PDF,
    "docx": InputFormat.DOCX,
    "xlsx": InputFormat.XLSX,
    "pptx": InputFormat.PPTX,
    "html": InputFormat.HTML,
    "xml": None,  # Автоматическое определение
    "image_ocr": InputFormat.PDF,  # Изображения через PDF pipeline
    "rtf": InputFormat.DOCX,  # RTF как DOCX
}
```

### 3.3. Route → PipelineOptions

Route определяет какой YAML template загружается:

```python
template = load_pipeline_template(route)  # pipeline_templates/{route}.yaml
options = _build_options_from_template(template)
```

---

## 4. Обработка ошибок

### 4.1. Ошибки валидации контракта

- **Отсутствие contract:** `FileNotFoundError`
- **Некорректный route:** `ValueError` (route="mixed" или "unknown")
- **Отсутствие главного файла:** `ValueError`

### 4.2. Ошибки обработки

- **Неподдерживаемый формат:** `ConversionError` → Quarantine
- **Ошибки конвертации:** Логирование, retry механизм
- **Ошибки экспорта:** Логирование, продолжение обработки

### 4.3. Quarantine

Проблемные UNIT копируются в `Quarantine/{unit_id}/` с:

- Все файлы из UNIT
- `error_info.txt` с описанием ошибки

---

**Следующий документ:** [BEST_PRACTICES.md](BEST_PRACTICES.md) - лучшие практики использования Docling

# Детальное описание компонентов Docling Integration

**Дата создания:** 2025-12-24  
**Версия:** 1.0

## Обзор компонентов

Docling Integration состоит из следующих основных компонентов:

1. **Bridge** (`bridge_docprep.py`) - мост между DocPrep и Docling
2. **Config** (`config.py`) - конфигурация Docling через YAML templates
3. **Runner** (`runner.py`) - тонкая обертка над DocumentConverter
4. **Pipeline** (`pipeline.py`) - основной orchestration
5. **Exporters** (`exporters/`) - экспорт результатов

---

## 1. Bridge (bridge_docprep.py)

**Путь:** `final_preprocessing/docling_integration/bridge_docprep.py`

**Назначение:** Мост между DocPrep и Docling Integration, обеспечивающий загрузку и валидацию UNIT из Ready2Docling.

### 1.1. Основные функции

#### `load_unit_from_ready2docling(unit_path: Path) -> Dict[str, Any]`

Загружает UNIT из Ready2Docling с валидацией готовности.

**Процесс:**

1. **Валидация готовности через DoclingAdapter:**
   ```python
   adapter = DoclingAdapter()
   validation = adapter.validate_readiness(unit_path)
   if not validation["ready"]:
       raise ValueError(f"Unit not ready: {validation['errors']}")
   ```

2. **Загрузка контракта:**
   - ТОЛЬКО `docprep.contract.json` используется как вход
   - `manifest.json` НЕ используется Docling (только для DocPrep)
   - Контракт обязателен для обработки

3. **Валидация route:**
   - Route не должен быть "mixed" или "unknown"
   - Должен соответствовать поддерживаемым форматам

4. **Построение AST nodes:**
   - Использует `DoclingAdapter.build_ast_nodes()` для определения структуры UNIT
   - AST nodes используются для определения главного файла

5. **Нахождение файлов:**
   - Исключает служебные файлы (manifest.json, audit.log.jsonl, и т.д.)
   - Возвращает список файлов для обработки

**Возвращаемые данные:**

```python
{
    "contract": {...},           # docprep.contract.json
    "validation": {...},         # результаты валидации
    "ast_nodes": {...},          # AST узлы из адаптера
    "files": [Path, ...],        # список файлов
    "unit_id": "UNIT_xxx",       # идентификатор UNIT
    "route": "pdf_text",         # route из contract
    "unit_path": Path(...),      # путь к UNIT
}
```

**Обработка ошибок:**

- `FileNotFoundError` - если UNIT или contract не найден
- `ValueError` - если UNIT не готов или contract некорректен
- Логирование предупреждений при проблемах с AST nodes

#### `get_main_file(unit_data: Dict[str, Any]) -> Optional[Path]`

Определяет главный файл для обработки.

**Логика определения:**

1. **Приоритет 1:** AST nodes с ролью "document"
   ```python
   ast_nodes = unit_data.get("ast_nodes", {})
   file_nodes = ast_nodes.get("files", [])
   for file_node in file_nodes:
       if file_node.get("role") == "document":
           return Path(file_node["path"])
   ```

2. **Приоритет 2:** Приоритет по расширениям
   - Поддерживаемые расширения: `.pdf`, `.docx`, `.xlsx`, `.pptx`, `.html`, `.xml`, `.rtf`, изображения
   - Фильтрация неподдерживаемых форматов (`.zip`, `.rar`, `.7z`, `.exe`, `.dll`, `.bin`)

3. **Fallback:** Первый поддерживаемый файл

**Обработка ошибок:**

- `ValueError` - если нет поддерживаемых файлов

### 1.2. Зависимости

- `docprep.adapters.docling.DoclingAdapter` - адаптер для валидации
- `docprep.core.contract.load_contract` - загрузка контракта
- Стандартная библиотека Python: `pathlib`, `logging`

### 1.3. Ключевые особенности

- **Контрактная строгость:** Использует только contract.json, не manifest.json
- **Валидация:** Строгая валидация готовности UNIT перед обработкой
- **Гибкость:** Поддержка определения главного файла через AST или приоритет расширений

---

## 2. Config (config.py)

**Путь:** `final_preprocessing/docling_integration/config.py`

**Назначение:** Конфигурация Docling через YAML templates с fallback на legacy hardcoded конфигурацию.

### 2.1. Основные функции

#### `load_pipeline_template(route: str) -> Optional[Dict[str, Any]]`

Загружает YAML template для route из `pipeline_templates/{route}.yaml`.

**Процесс:**

1. Определение пути к template: `pipeline_templates/{route}.yaml`
2. Загрузка через `yaml.safe_load()`
3. Возврат словаря с конфигурацией или `None` если template не найден

**Обработка ошибок:**

- Логирование предупреждений при отсутствии template
- Логирование ошибок при проблемах загрузки

#### `build_docling_options(route: str, manifest: Optional[Dict] = None) -> Optional[PipelineOptions]`

Строит `PipelineOptions` для DocumentConverter.

**Логика:**

1. **Приоритет 1:** YAML template
   ```python
   template = load_pipeline_template(route)
   if template:
       return _build_options_from_template(template)
   ```

2. **Приоритет 2:** Legacy hardcoded конфигурация
   ```python
   return _build_options_legacy(route, manifest)
   ```

#### `_build_options_from_template(template: Dict[str, Any]) -> PipelineOptions`

Строит `PipelineOptions` из YAML template.

**Процесс:**

1. **PDF опции (если нужны):**
   ```python
   if template.get("route", "").startswith("pdf") or template.get("route") == "image_ocr":
       pdf_opts = PdfPipelineOptions()
       pdf_config = template.get("models", {})
       
       # OCR настройка
       if pdf_config.get("ocr") == "tesseract" or docling_config.get("force_ocr"):
           pdf_opts.do_ocr = True
       
       # Таблицы
       if pdf_config.get("tables") != "off":
           pdf_opts.do_table_structure = True
       
       options = PipelineOptions(pdf=pdf_opts)
   ```

2. **VLM pipeline (если указан):**
   ```python
   vlm_config = template.get("models", {}).get("vlm")
   if vlm_config:
       options.vlm = VlmPipelineOptions()
       vlm_endpoint = os.environ.get("VLM_ENDPOINT")
       if vlm_endpoint:
           options.vlm.endpoint = vlm_endpoint
   ```

3. **Возврат PipelineOptions**

#### `_build_options_legacy(route: str, manifest: Optional[Dict]) -> PipelineOptions`

Legacy hardcoded конфигурация для обратной совместимости.

**Поддерживаемые routes:**

- `pdf_scan` - OCR + VLM pipeline
- `pdf_text` - только text extraction, таблицы
- `pdf_mixed` - OCR для страниц без текста
- `docx`, `xlsx`, `pptx` - нативные форматы
- `html`, `xml` - веб-форматы
- `image_ocr` - изображения через OCR
- `rtf` - RTF документы

#### `get_input_format_from_route(route: str) -> Optional[InputFormat]`

Определяет `InputFormat` на основе route.

**Маппинг:**

```python
route_to_format = {
    "pdf_text": InputFormat.PDF,
    "pdf_scan": InputFormat.PDF,
    "pdf_mixed": InputFormat.PDF,
    "docx": InputFormat.DOCX,
    "xlsx": InputFormat.XLSX,
    "pptx": InputFormat.PPTX,
    "html": InputFormat.HTML,
    "xml": None,  # Автоматическое определение (XML_JATS или XML_USPTO)
    "image_ocr": InputFormat.PDF,  # Изображения обрабатываются как PDF
    "rtf": InputFormat.DOCX,  # RTF обрабатывается как DOCX
}
```

### 2.2. Особенности импорта Docling

**Проблема:** Конфликт имен между локальным модулем `docling_integration` и установленным пакетом `docling`.

**Решение:** Сложная логика импорта с манипуляцией `sys.path`:

```python
# Перемещаем site-packages в начало sys.path
site_dirs = []
for site_dir in site.getsitepackages():
    if (Path(site_dir) / 'docling' / '__init__.py').exists():
        if site_dir in sys.path:
            sys.path.remove(site_dir)
        sys.path.insert(0, site_dir)

# Удаляем локальный модуль из sys.modules
if 'docling' in sys.modules:
    mod = sys.modules['docling']
    if 'final_preprocessing' in str(mod.__file__):
        for k in list(sys.modules.keys()):
            if k.startswith('docling'):
                sys.modules.pop(k, None)

# Импортируем установленный пакет
document_converter_mod = importlib.import_module('docling.document_converter')
```

### 2.3. Зависимости

- `yaml` - для загрузки YAML templates
- `docling.document_converter.DocumentConverter`
- `docling.datamodel.pipeline_options.PipelineOptions`
- `docling.datamodel.pipeline_options.PdfPipelineOptions`
- `docling.datamodel.pipeline_options.VlmPipelineOptions`
- `docling.datamodel.base_models.InputFormat`

---

## 3. Runner (runner.py)

**Путь:** `final_preprocessing/docling_integration/runner.py`

**Назначение:** Тонкая обертка над `DocumentConverter` с поддержкой retry и batch обработки.

### 3.1. Основные функции

#### `run_docling_conversion(file_path: Path, options: Optional[PipelineOptions] = None, max_retries: int = 1, retry_delay: float = 1.0) -> Optional[Any]`

Запускает конвертацию файла через DocumentConverter.

**Процесс:**

1. **Валидация:**
   ```python
   if not DOCLING_AVAILABLE:
       raise ImportError("Docling not available")
   if not file_path.exists():
       raise FileNotFoundError(f"File not found: {file_path}")
   ```

2. **Инициализация DocumentConverter:**
   ```python
   if options is not None:
       converter = DocumentConverter(options)
   else:
       converter = DocumentConverter()  # Default options
   ```

3. **Конвертация:**
   ```python
   document = converter.convert(str(file_path))
   # Примечание: convert() не принимает input_format - определяется автоматически
   ```

4. **Retry механизм:**
   - По умолчанию 1 попытка (без retry)
   - Задержка между попытками: `retry_delay` секунд
   - Логирование всех попыток

**Обработка ошибок:**

- Логирование предупреждений при каждой попытке
- Полное логирование ошибки при последней попытке
- Проброс последнего исключения после всех попыток

#### `run_batch_conversion(file_paths: list[Path], options: Optional[PipelineOptions] = None) -> Dict[Path, Any]`

Запускает конвертацию нескольких файлов.

**Процесс:**

1. Последовательная обработка каждого файла
2. Сохранение результатов в словарь: `{file_path: document}`
3. Логирование ошибок для каждого файла
4. Продолжение обработки при ошибках (не прерывает batch)

### 3.2. Зависимости

- `docling.document_converter.DocumentConverter`
- `docling.datamodel.pipeline_options.PipelineOptions`
- Стандартная библиотека Python: `pathlib`, `logging`, `time`

### 3.3. Ключевые особенности

- **Минимальная обертка:** Максимум делегирования Docling
- **Retry механизм:** Настраиваемое количество попыток
- **Batch обработка:** Поддержка обработки нескольких файлов

---

## 4. Pipeline (pipeline.py)

**Путь:** `final_preprocessing/docling_integration/pipeline.py`

**Назначение:** Основной orchestration pipeline, координирующий все компоненты.

### 4.1. Класс DoclingPipeline

#### Инициализация

```python
pipeline = DoclingPipeline(
    export_json: bool = True,
    export_markdown: bool = False,
    export_mongodb: bool = True,
    base_output_dir: Optional[Path] = None,
    ready2docling_dir: Optional[Path] = None,
    quarantine_dir: Optional[Path] = None,
    skip_failed: bool = True,
)
```

**Параметры:**

- `export_json` - экспортировать в JSON
- `export_markdown` - экспортировать в Markdown
- `export_mongodb` - экспортировать в MongoDB
- `base_output_dir` - базовая директория для экспорта (OutputDocling)
- `ready2docling_dir` - базовая директория Ready2Docling
- `quarantine_dir` - директория для проблемных UNIT
- `skip_failed` - пропускать неудачные UNIT и продолжать обработку

#### `process_unit(unit_path: Path) -> Dict[str, Any]`

Обрабатывает один UNIT.

**Последовательность:**

1. **Загрузка UNIT:**
   ```python
   unit_data = load_unit_from_ready2docling(unit_path)
   contract = unit_data["contract"]
   unit_id = unit_data["unit_id"]
   route = unit_data["route"]
   ```

2. **Получение главного файла:**
   ```python
   main_file = get_main_file(unit_data)
   ```

3. **Построение опций:**
   ```python
   options = build_docling_options(route)
   # Для не-PDF файлов options может быть None (используются default)
   ```

4. **Конвертация:**
   ```python
   document = run_docling_conversion(main_file, options=options)
   ```

5. **Экспорт:**
   - JSON: `export_to_json(document, json_path, metadata)`
   - Markdown: `export_to_markdown(document, md_path, metadata)`
   - MongoDB: `export_to_mongodb(document, contract, unit_id)`

6. **Определение output subdirectory:**
   ```python
   output_subdir = self._get_output_subdirectory(contract)
   # Результат: docx/, pdf/, xlsx/, и т.д.
   ```

**Возвращаемые данные:**

```python
{
    "unit_id": "UNIT_xxx",
    "route": "pdf_text",
    "success": True,
    "exports": {
        "json": "/path/to/file.json",
        "markdown": "/path/to/file.md",
        "mongodb": "document_id"  # опционально
    },
    "processing_time": 0.15,
    "errors": []
}
```

#### `process_directory(ready2docling_dir: Path) -> Dict[str, Any]`

Обрабатывает все UNIT в директории.

**Процесс:**

1. Рекурсивный поиск UNIT: `ready2docling_dir.rglob("UNIT_*")`
2. Последовательная обработка каждого UNIT
3. Сбор результатов в список
4. Генерация отчета с метриками

**Обработка ошибок:**

- При `skip_failed=True` ошибки логируются, но не прерывают обработку
- Проблемные UNIT копируются в Quarantine

#### `_get_output_subdirectory(contract: Dict[str, Any]) -> Path`

Определяет поддиректорию для экспорта на основе расширения из contract.

**Логика:**

1. Извлечение `true_extension` из `contract.source`
2. Маппинг расширения → поддиректория:
   - `jpg`, `jpeg`, `png`, `tiff` → `image/`
   - `doc`, `docx` → `docx/`
   - `xls`, `xlsx` → `xlsx/`
   - `ppt`, `pptx` → `pptx/`
   - `pdf` → `pdf/`
   - `html`, `htm` → `html/`
   - `xml` → `xml/`
   - `rtf` → `rtf/`
   - Иначе → `other/`

3. Fallback на route если extension не определен

#### `_quarantine_unit(unit_path: Path, unit_id: str, error: str) -> Optional[Path]`

Копирует проблемный UNIT в quarantine.

**Процесс:**

1. Создание директории `quarantine_dir/{unit_id}/`
2. Копирование всех файлов из UNIT
3. Создание `error_info.txt` с описанием ошибки

### 4.2. Зависимости

- `bridge_docprep` - загрузка UNIT
- `config` - построение опций
- `runner` - конвертация
- `exporters.json`, `exporters.markdown`, `exporters.mongodb` - экспорт
- Стандартная библиотека Python: `pathlib`, `logging`, `time`, `shutil`

---

## 5. Exporters

### 5.1. JSON Exporter (exporters/json.py)

**Назначение:** Экспорт DoclingDocument в JSON формат.

#### `export_to_json(document: Any, output_path: Path, include_metadata: bool = True, metadata: Optional[dict] = None) -> Path`

**Процесс:**

1. **Сериализация документа:**
   ```python
   if hasattr(document, "model_dump"):
       doc_dict = document.model_dump()
   elif hasattr(document, "dict"):
       doc_dict = document.dict()
   ```

2. **Добавление метаданных:**
   ```python
   doc_dict["_export_metadata"] = {
       "exported_at": datetime.utcnow().isoformat() + "Z",
       "export_format": "json",
       **metadata
   }
   ```

3. **Сохранение:**
   ```python
   json.dump(doc_dict, f, indent=2, ensure_ascii=False, default=str)
   ```

**Особенности:**

- Использует `model_dump()` для Pydantic моделей
- Поддержка `default=str` для несериализуемых объектов
- UTF-8 encoding с `ensure_ascii=False` для поддержки кириллицы

### 5.2. Markdown Exporter (exporters/markdown.py)

**Назначение:** Экспорт DoclingDocument в Markdown с сохранением структуры.

#### `export_to_markdown(document: Any, output_path: Path, include_metadata: bool = True, metadata: Optional[dict] = None) -> Path`

**Процесс:**

1. **Извлечение DoclingDocument:**
   ```python
   if hasattr(document, "document"):
       docling_document = document.document
   ```

2. **Извлечение структурированного контента:**
   ```python
   structured_content = _extract_structured_content(docling_document)
   ```

3. **Рекурсивная обработка иерархии:**
   - Построение индекса элементов по `self_ref`
   - Обработка body → groups → texts
   - Форматирование с учетом `label` и `level`

4. **Форматирование элементов:**
   - Заголовки: `##`, `###` (на основе `level`)
   - Списки: `- ` с отступами
   - Таблицы: Markdown таблицы
   - Изображения: `![caption](path)`

**Вспомогательные функции:**

- `_extract_structured_content()` - извлечение структуры
- `_process_element_recursive()` - рекурсивная обработка иерархии
- `_format_text_element()` - форматирование текстовых элементов
- `_table_to_markdown()` - конвертация таблиц
- `_picture_to_markdown()` - конвертация изображений

**Особенности:**

- Сохранение layout структуры документа
- Поддержка заголовков, списков, таблиц, изображений
- Обработка CREF ссылок для навигации по структуре

### 5.3. MongoDB Exporter (exporters/mongodb.py)

**Назначение:** Экспорт DoclingDocument в MongoDB.

#### `export_to_mongodb(document: Any, contract: Dict, unit_id: str, collection_name: str = "docling_results") -> Optional[str]`

**Процесс:**

1. **Подключение к MongoDB:**
   ```python
   client = get_mongodb_client()
   db = client[db_name]
   collection = db[collection_name]
   ```

2. **Сериализация документа:**
   ```python
   doc_dict = document.model_dump()
   ```

3. **Формирование документа MongoDB:**
   ```python
   mongo_doc = {
       "unit_id": unit_id,
       "protocol_date": contract["unit"]["batch_date"],
       "route": contract["routing"]["docling_route"],
       "docling_document": doc_dict,
       "contract": contract,
       "created_at": datetime.utcnow(),
   }
   ```

4. **Upsert:**
   ```python
   collection.update_one(
       {"unit_id": unit_id},
       {"$set": mongo_doc},
       upsert=True
   )
   ```

5. **Создание индексов:**
   - `unit_id` (уникальный)
   - `protocol_date`
   - `route`
   - Составной индекс `(protocol_date, route)`

#### `get_mongodb_client() -> Optional[Any]`

Создает подключение к MongoDB.

**Переменные окружения:**

- `LOCAL_MONGO_SERVER` или `MONGO_METADATA_SERVER` (default: `localhost:27018`)
- `MONGO_METADATA_USER` (default: `admin`)
- `MONGO_METADATA_PASSWORD` (default: `password`)
- `MONGO_METADATA_DB` (default: `docling_metadata`)

**Особенности:**

- Поддержка аутентификации
- Проверка подключения через `ping`
- Обработка ошибок подключения

---

## Взаимодействие компонентов

### Последовательность вызовов

```python
# 1. Pipeline инициализация
pipeline = DoclingPipeline(...)

# 2. process_unit()
unit_data = bridge.load_unit_from_ready2docling(unit_path)
main_file = bridge.get_main_file(unit_data)
options = config.build_docling_options(route)
document = runner.run_docling_conversion(main_file, options)
exporters.json.export_to_json(document, json_path)
exporters.markdown.export_to_markdown(document, md_path)
exporters.mongodb.export_to_mongodb(document, contract, unit_id)
```

### Потоки данных

1. **Ready2Docling → Bridge:** UNIT директория + contract.json
2. **Bridge → Config:** route из contract
3. **Config → Runner:** PipelineOptions
4. **Runner → Docling:** file_path + PipelineOptions
5. **Docling → Runner:** ConversionResult
6. **Runner → Exporters:** ConversionResult / DoclingDocument
7. **Exporters → OutputDocling/MongoDB:** Экспортированные данные

---

**Следующий документ:** [CONFIGURATION.md](CONFIGURATION.md) - конфигурация и настройки

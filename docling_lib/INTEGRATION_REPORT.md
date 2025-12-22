# Отчет об интеграции docprep с docling

## Дата: 2025-12-22

## Выполненные работы

### 1. Доработка DoclingAdapter ✅

**Файл:** `final_preprocessing/docprep/adapters/docling.py`

**Улучшения:**
- ✅ Расширено извлечение метаданных из manifest:
  - route из `manifest.processing.route`
  - needs_ocr из файлов (для PDF)
  - file_type_analysis для всех файлов
  - transformation_history для отслеживания трансформаций
- ✅ Улучшено определение ролей файлов:
  - document vs attachment на основе transformations
  - Поддержка original_name и current_name mapping
  - Определение mime_type из manifest
- ✅ Расширена валидация готовности UNIT:
  - Поддержка состояний: `READY_FOR_DOCLING`, `MERGED_DIRECT`, `MERGED_PROCESSED`
  - Улучшенная проверка структуры manifest

### 2. Улучшение bridge_docprep ✅

**Файл:** `docling_lib/bridge_docprep.py`

**Улучшения:**
- ✅ Приоритетное использование `manifest.processing.route`
- ✅ Fallback на определение route из структуры директорий Ready2Docling
- ✅ Улучшенное определение главного файла:
  - Использование AST nodes для определения главного документа
  - Приоритет файлам с расширениями документов
  - Поддержка multi-file UNIT

**Новая функция:** `_determine_route_from_path()` - определяет route из структуры директорий

### 3. Расширение config ✅

**Файл:** `docling_lib/config.py`

**Улучшения:**
- ✅ Расширен маппинг route → PipelineOptions:
  - `pdf_text`: text extraction, table structure, captions, TOC
  - `pdf_scan`: OCR/VLM pipeline, table structure
  - `pdf_mixed`: OCR + table structure
  - `docx/xlsx/pptx`: native format parsing с полными опциями
  - `html/html_text`: structure parsing, captions, TOC
  - `xml`: structure parsing, captions
  - `image_ocr`: image processing через PDF pipeline
  - `rtf`: text processing
- ✅ Добавлена поддержка VLM pipeline:
  - Endpoint configuration через `VLM_ENDPOINT`
  - Model selection через `VLM_MODEL`
  - Fallback на стандартный OCR при недоступности VLM

### 4. Улучшение runner ✅

**Файл:** `docling_lib/runner.py`

**Улучшения:**
- ✅ Добавлен retry mechanism:
  - Параметр `max_retries` для настройки количества попыток
  - Параметр `retry_delay` для задержки между попытками
  - Подробное логирование каждой попытки
- ✅ Улучшена обработка ошибок:
  - Детальное логирование ошибок
  - Проброс последнего исключения после всех попыток

### 5. Улучшение pipeline ✅

**Файл:** `docling_lib/pipeline.py`

**Улучшения:**
- ✅ Добавлена error policy:
  - Параметр `skip_failed` для пропуска неудачных UNIT
  - Параметр `quarantine_dir` для карантина проблемных документов
  - Подробное логирование ошибок с деталями
- ✅ Реализован quarantine механизм:
  - Копирование (не перемещение) проблемных UNIT
  - Создание файла `error_info.txt` с деталями ошибки
  - Сохранение всех файлов и manifest
- ✅ Улучшен экспорт:
  - JSON с полными метаданными
  - Markdown с сохранением структуры
  - MongoDB с индексацией

**Новая функция:** `_quarantine_unit()` - копирует проблемный UNIT в quarantine

### 6. Тестирование ✅

**Файл:** `docling_lib/test_integration.py`

**Создан тестовый скрипт для проверки:**
- Загрузки UNIT через bridge_docprep
- Определения route из manifest
- Построения Docling options
- Определения главного файла
- Полного pipeline обработки

**Результаты тестирования:**
- ✅ Загрузка UNIT работает корректно
- ✅ Определение route работает (из manifest и структуры директорий)
- ✅ Определение главного файла работает
- ⚠️ Docling options требуют установки полного пакета docling (сейчас установлен только docling-core)

## Структура интеграции

```
docprep (Ready2Docling)
    ↓
DoclingAdapter (build_ast_nodes, validate_readiness)
    ↓
bridge_docprep (load_unit_from_ready2docling, get_main_file)
    ↓
config (build_docling_options, get_input_format_from_route)
    ↓
runner (run_docling_conversion с retry)
    ↓
pipeline (process_unit с error policy и quarantine)
    ↓
exporters (JSON, Markdown, MongoDB)
```

## Поддерживаемые routes

- `pdf_text` - PDF с текстовым слоем
- `pdf_scan` - PDF со сканированным содержимым (OCR/VLM)
- `pdf_mixed` - Смешанный PDF
- `docx` - Word документы
- `xlsx` - Excel таблицы
- `pptx` - PowerPoint презентации
- `html` / `html_text` - HTML документы
- `xml` - XML документы
- `image_ocr` - Изображения (OCR)
- `rtf` - RTF документы

## Следующие шаги

1. **Установка docling:**
   ```bash
   pip install docling>=2.0.0
   ```
   Примечание: Требуется достаточно места на диске для установки

2. **Запуск docprep для подготовки данных:**
   ```bash
   cd final_preprocessing
   docprep pipeline Data/2025-03-20/Input Data/2025-03-20/Ready2Docling
   ```

3. **Тестирование docling pipeline:**
   ```bash
   python3 docling_lib/test_integration.py final_preprocessing/Data/2025-03-20 --limit 5
   ```

4. **Полная обработка через pipeline:**
   ```python
   from docling_lib.pipeline import DoclingPipeline
   
   pipeline = DoclingPipeline(
       export_json=True,
       export_markdown=True,
       export_mongodb=True,
       quarantine_dir=Path("Data/2025-03-20/Quarantine"),
   )
   
   results = pipeline.process_directory(
       Path("Data/2025-03-20/Ready2Docling"),
       limit=None,
   )
   ```

## Известные ограничения

1. **Docling установка:** Требуется установка полного пакета docling (>=2.0.0) для полной функциональности
2. **Место на диске:** Установка docling требует значительного места на диске
3. **VLM pipeline:** Требует настройки VLM endpoint для использования (опционально)

## Заключение

Интеграция docprep с docling успешно реализована. Все компоненты доработаны согласно плану:
- ✅ DoclingAdapter улучшен для извлечения всех метаданных
- ✅ bridge_docprep улучшен для определения route и главного файла
- ✅ config расширен для поддержки всех форматов
- ✅ runner улучшен с retry mechanism
- ✅ pipeline улучшен с error policy и quarantine

Система готова к использованию после установки полного пакета docling.


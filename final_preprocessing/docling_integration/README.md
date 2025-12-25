# Docling Library - Упрощенный orchestration слой

Минималистичный слой для обработки документов через IBM Docling, интегрированный с docprep.

## Архитектурные принципы

1. **Docling - двигатель, наш код - водитель** - не дублируем parsing логику
2. **Используем manifest из docprep** - не определяем тип файла заново
3. **Минимальная структура** - только orchestration, конфигурация, экспорт
4. **Реальный IBM Docling** - обязательная dependency

## Установка

```bash
pip install -r docling/requirements.txt
```

## Использование

### Обработка одного UNIT

```python
from pathlib import Path
from docling_integration.pipeline import DoclingPipeline

pipeline = DoclingPipeline(
    export_json=True,
    export_mongodb=True,
)

unit_path = Path("final_preprocessing/Data/2025-12-20/Ready2Docling/pdf/text/UNIT_xxx")
result = pipeline.process_unit(unit_path)

if result["success"]:
    print(f"Processed: {result['unit_id']}")
    print(f"Exports: {result['exports']}")
```

### Обработка всех UNIT за дату

```python
from pathlib import Path
from docling_integration.pipeline import DoclingPipeline

pipeline = DoclingPipeline()

ready2docling_dir = Path("final_preprocessing/Data/2025-12-20/Ready2Docling")
results = pipeline.process_directory(ready2docling_dir, limit=10)

print(f"Processed: {results['succeeded']}/{results['total_units']}")
```

### Тестирование

```bash
# Тест одного UNIT
python -m docling.tests.test_pipeline --date 2025-12-20 --unit UNIT_xxx

# Тест всех UNIT за дату (с лимитом)
python -m docling.tests.test_pipeline --date 2025-12-20 --limit 5
```

## Конфигурация

### Переменные окружения для MongoDB

```bash
LOCAL_MONGO_SERVER=localhost:27018
MONGO_METADATA_USER=admin
MONGO_METADATA_PASSWORD=password
MONGO_METADATA_DB=docling_metadata
```

### Routes

Pipeline автоматически определяет настройки Docling на основе `manifest.processing.route`:

- `pdf_text` - PDF с текстовым слоем (text extraction)
- `pdf_scan` - PDF со сканированным содержимым (OCR/VLM)
- `pdf_mixed` - Смешанный PDF
- `docx`, `xlsx`, `pptx` - Office форматы
- `html`, `xml` - Структурированные форматы
- `image_ocr` - Изображения (OCR)

## Структура

```
docling/
├── pipeline.py          # Основной orchestration
├── bridge_docprep.py    # Интеграция с docprep
├── runner.py            # Запуск DocumentConverter
├── config.py            # Конфигурация Docling options
├── exporters/
│   ├── json.py          # JSON экспорт
│   ├── markdown.py      # Markdown экспорт
│   └── mongodb.py       # MongoDB экспорт
└── tests/
    ├── test_integration.py
    └── test_pipeline.py
```

## Что НЕ включает

- ❌ `processors/` - Docling сам обрабатывает форматы
- ❌ Кастомный document model
- ❌ Layout parsing (Docling делает это)
- ❌ Table extraction (Docling делает это)
- ❌ FastAPI на этом этапе

## Что включает

- ✅ Orchestration (pipeline.py)
- ✅ Конфигурация Docling (config.py)
- ✅ Маппинг manifest → Docling options
- ✅ Экспорт в JSON/Markdown/MongoDB
- ✅ Интеграция с docprep через адаптер

## Зависимости

- `docling>=1.0.0` - IBM Docling библиотека
- `pymongo>=4.0.0` - MongoDB клиент


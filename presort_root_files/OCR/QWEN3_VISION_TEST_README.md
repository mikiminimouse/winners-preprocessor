# Тестирование Qwen3-VL-8B для формирования AST JSON

## Описание

Скрипты для тестирования Qwen3-VL-8B как внешнего ML inference для обработки документов и формирования AST JSON в формате Docling.

## Установка зависимостей

```bash
pip install evolution-openai
pip install pdf2image  # для обработки PDF
# Также требуется poppler-utils для pdf2image:
sudo apt-get install poppler-utils
```

## Использование

### 1. Сбор UNIT'ов для тестирования

```bash
python3 collect_test_units.py
```

Скрипт:
- Сканирует все UNIT'ы в `normalized/`
- Фильтрует UNIT'ы с `needs_ocr: false`
- Выбирает 10 разнообразных UNIT'ов
- Сохраняет список в `test_units_list.json`

### 2. Запуск тестирования

```bash
python3 test_qwen3_vision_ast.py
```

Скрипт:
- Загружает список UNIT'ов из `test_units_list.json`
- Обрабатывает каждый UNIT через Qwen3-VL-8B
- Формирует AST JSON в формате Docling
- Сохраняет результаты в `output_qwen3/`

## Поддерживаемые форматы

- **Изображения** (JPEG, PNG): прямая обработка через Qwen3-VL-8B
- **PDF**: конвертация страниц в изображения через `pdf2image`, затем обработка
- **DOCX**: требует предварительной конвертации в PDF

## Формат результатов

Результаты сохраняются в формате, аналогичном Docling:

```json
{
  "unit_id": "UNIT_...",
  "file": "filename.jpg",
  "route": "image_ocr",
  "status": "processed",
  "processing_method": "qwen3-vl-8b",
  "text": "извлеченный текст",
  "tables": [...],
  "layout": {
    "pages": [...],
    "sections": [...],
    "blocks": [...]
  },
  "metadata": {...},
  "metrics": {...}
}
```

## Структура AST JSON

AST JSON содержит:

- **text**: полный извлеченный текст из документа
- **tables**: массив таблиц с координатами и данными
- **layout**: структура документа (страницы, блоки, секции)
- **metadata**: метаданные документа (заголовок, автор, дата, количество страниц)

## Конфигурация

Параметры подключения к Qwen3-VL-8B находятся в начале `test_qwen3_vision_ast.py`:

```python
API_KEY = "ZDRhOWQ3OTAtZjU4MC00MzA2LThhNTgtMDU1NGFlMjE4OWRl.85a830f9340966e0ad1fd1642884c7c8"
BASE_URL = "https://92ad3238-81c6-4396-a02a-fb9cef99bce3.modelrun.inference.cloud.ru/v1"
MODEL_NAME = "qwen3-vl-8b-instruct"
```

## Интеграция с Docling pipeline

AST JSON, сформированный Qwen3-VL-8B, может быть использован в Docling pipeline:

1. **Docling нормализация**: подготовка файлов, создание UNIT'ов
2. **Qwen3-VL-8B обработка**: OCR, layout detection, table extraction → AST JSON
3. **Docling Document Model**: заполнение структуры Docling из AST JSON
4. **Docling экспорт**: Markdown/JSON/HTML

## Примеры использования

### Обработка одного изображения

```python
from test_qwen3_vision_ast import Qwen3VisionProcessor
from pathlib import Path

processor = Qwen3VisionProcessor()
result = processor.process_image(Path("document.jpg"))

if result["success"]:
    ast = result["ast"]
    print(f"Текст: {len(ast['text'])} символов")
    print(f"Таблиц: {len(ast['tables'])}")
```

## Ограничения

- Для PDF требуется `pdf2image` и `poppler-utils`
- DOCX требует предварительной конвертации в PDF
- Большие PDF могут обрабатываться долго (каждая страница отдельно)

## Отчеты

После выполнения тестирования создается отчет в `output_qwen3/test_report_*.json` с метриками:
- Количество обработанных UNIT'ов
- Время обработки
- Статистика по тексту и таблицам
- Ошибки (если есть)


# План рефакторинга Docling Integration

**Дата:** 2026-01-16
**Цель:** Упрощение, устранение дублирования, улучшение OCR для русского языка

---

## Ответы на ключевые вопросы

### 1. Зачем две зависимости: `docling` и `docling-core`?

**Ответ: `docling-core` указывать НЕ НУЖНО!**

```bash
$ pip3 show docling | grep Requires
Requires: ... docling-core, ... # ← docling-core уже включён как зависимость
```

**Факт:** `docling>=2.60.0` автоматически устанавливает `docling-core>=2.50.0`.

**Действие:** Удалить `docling-core>=2.50.0` из `requirements.txt`.

---

### 2. Зачем нужен `runner.py` если конвертация в docprep?

**Ключевое различие:**

| Компонент | Что делает | Инструмент |
|-----------|------------|------------|
| **docprep** | Конвертация **ФОРМАТОВ** (doc→docx, xls→xlsx) | LibreOffice |
| **docling_integration** | Извлечение **КОНТЕНТА** (docx→text/JSON/MD) | Docling |

**docprep НЕ извлекает текст из документов!** Он только:
- Конвертирует legacy форматы в современные (doc→docx)
- Разархивирует архивы
- Нормализует файлы
- Генерирует `docprep.contract.json`

**runner.py НУЖЕН для:**
- Вызова `DocumentConverter.convert()` — извлечение текстового содержимого
- Применения `PipelineOptions` (OCR, tables, layout)
- Retry логики при ошибках
- Thread-safe счётчиков

**НО runner.py можно УПРОСТИТЬ:**
- Удалить неиспользуемый параметр `input_format`
- Удалить `run_batch_conversion()` (не используется)
- Убрать избыточное логирование

**Оценка:** ~223 строки → ~120 строк (-46%)

---

### 3. Тестирование OCR: Tesseract vs EasyOCR для русского

**Текущая проблема:**
```yaml
# pdf_scan.yaml
docling:
  language: eng  # ← Только английский!
```

**План тестирования:**

| Тест | Tesseract | EasyOCR | Метрика |
|------|-----------|---------|---------|
| Чистый русский текст | `lang=["rus"]` | `lang=["ru"]` | WER, CER |
| Русский + английский | `lang=["rus", "eng"]` | `lang=["ru", "en"]` | WER |
| Таблицы на русском | + table extraction | + table extraction | Точность ячеек |
| Сканы низкого качества | DPI=300 | Default | WER |

**Тестовые данные:** 10 PDF из `pdf_scan` route с русским текстом.

---

## Фазы рефакторинга

### Фаза 1: Очистка зависимостей (5 мин)

**Файл:** `requirements.txt`

```diff
 docling>=2.60.0
-docling-core>=2.50.0
 pymongo>=4.0.0
 pyyaml>=6.0
```

**Обоснование:** `docling-core` устанавливается автоматически как зависимость `docling`.

---

### Фаза 2: Упрощение runner.py (30 мин)

**Текущее:** 223 строки
**Целевое:** ~120 строк

**Изменения:**

1. **Удалить неиспользуемый параметр `input_format`:**
```python
# БЫЛО:
def run_docling_conversion(
    file_path: Path,
    options: Optional[PipelineOptions] = None,
    input_format: Optional[InputFormat] = None,  # ← НЕ ИСПОЛЬЗУЕТСЯ
    ...
)

# СТАНЕТ:
def run_docling_conversion(
    file_path: Path,
    options: Optional[PipelineOptions] = None,
    max_retries: int = 1,
    retry_delay: float = 1.0
) -> ConversionResult
```

2. **Удалить `run_batch_conversion()`:**
   - Не используется в pipeline.py
   - `process_directory()` обрабатывает batch последовательно

3. **Удалить `ProcessedCountsManager` и связанную логику:**
   - `check_limit`, `limit_per_format` не используются
   - Thread-safe счётчики избыточны для последовательной обработки

4. **Упростить создание FormatOption:**
```python
# БЫЛО (проблемный код):
format_options[InputFormat.PDF] = FormatOption(
    pipeline_options=options.pdf,
    pipeline_cls=None,   # ← Проблема
    backend=None         # ← Проблема
)

# СТАНЕТ:
from docling.document_converter import PdfFormatOption

converter = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(pipeline_options=options.pdf)
    } if options and options.pdf else {}
)
```

---

### Фаза 3: Исправление OCR для русского языка (1 час)

**Файл:** `config.py` - добавить поддержку OCR options

**Файлы:** `pipeline_templates/pdf_scan.yaml`, `image_ocr.yaml`

**Шаг 3.1: Обновить YAML templates**

```yaml
# pdf_scan.yaml - НОВАЯ ВЕРСИЯ
route: pdf_scan

models:
  ocr: easyocr        # ← Изменено с tesseract
  layout: docbank
  tables: off

ocr_options:
  lang: ["ru", "en"]  # ← ДОБАВЛЕНО
  confidence_threshold: 0.5

docling:
  force_ocr: true
```

**Шаг 3.2: Обновить config.py для применения ocr_options**

```python
def _build_options_from_template(template: Dict[str, Any]) -> PipelineOptions:
    # ... существующий код ...

    # === OCR Options (НОВОЕ) ===
    ocr_options_config = template.get("ocr_options", {})
    ocr_setting = models_config.get("ocr")

    if ocr_setting == "easyocr":
        from docling.datamodel.pipeline_options import EasyOcrOptions
        pdf_opts.ocr_options = EasyOcrOptions(
            lang=ocr_options_config.get("lang", ["en"]),
            confidence_threshold=ocr_options_config.get("confidence_threshold", 0.5)
        )
    elif ocr_setting == "tesseract":
        from docling.datamodel.pipeline_options import TesseractOcrOptions
        pdf_opts.ocr_options = TesseractOcrOptions(
            lang=ocr_options_config.get("lang", ["eng"])
        )
```

---

### Фаза 4: Тестирование OCR (2 часа)

**Скрипт:** `scripts/test_ocr_comparison.py`

```python
"""
Сравнение качества OCR: Tesseract vs EasyOCR для русского языка.
"""
import time
from pathlib import Path
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    EasyOcrOptions,
    TesseractOcrOptions,
)

# Тестовые PDF (русский текст)
TEST_FILES = [
    # Добавить пути к тестовым файлам
]

def test_easyocr(file_path: Path) -> tuple[str, float]:
    """Тест EasyOCR."""
    options = PdfPipelineOptions()
    options.do_ocr = True
    options.ocr_options = EasyOcrOptions(lang=["ru", "en"])

    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)}
    )

    start = time.time()
    result = converter.convert(str(file_path))
    elapsed = time.time() - start

    text = result.document.export_to_markdown()
    return text, elapsed

def test_tesseract(file_path: Path) -> tuple[str, float]:
    """Тест Tesseract."""
    options = PdfPipelineOptions()
    options.do_ocr = True
    options.ocr_options = TesseractOcrOptions(lang=["rus", "eng"])

    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)}
    )

    start = time.time()
    result = converter.convert(str(file_path))
    elapsed = time.time() - start

    text = result.document.export_to_markdown()
    return text, elapsed

def compare_results():
    """Сравнение результатов."""
    for file_path in TEST_FILES:
        print(f"\n=== {file_path.name} ===")

        easy_text, easy_time = test_easyocr(file_path)
        tess_text, tess_time = test_tesseract(file_path)

        print(f"EasyOCR:   {len(easy_text)} chars, {easy_time:.2f}s")
        print(f"Tesseract: {len(tess_text)} chars, {tess_time:.2f}s")

        # Сохранить для ручной проверки качества
        (file_path.parent / f"{file_path.stem}_easyocr.md").write_text(easy_text)
        (file_path.parent / f"{file_path.stem}_tesseract.md").write_text(tess_text)

if __name__ == "__main__":
    compare_results()
```

**Критерии оценки:**
1. **WER (Word Error Rate)** - ручная проверка 100 слов
2. **Время обработки** - секунды на страницу
3. **Распознавание таблиц** - количество корректно извлечённых ячеек

---

### Фаза 5: Улучшение обработки native форматов (1 час)

**Проблема:** Для DOCX, XLSX, PPTX не применяются никакие options.

**Текущий код (pipeline.py:158-165):**
```python
if file_ext == '.pdf':
    options = build_docling_options(route)
else:
    # Для не-PDF файлов используем опции по умолчанию
    input_format = get_input_format_from_route(route)
```

**Улучшение:** Docling поддерживает FormatOption для native форматов!

```python
from docling.document_converter import (
    WordFormatOption,
    ExcelFormatOption,
    PowerpointFormatOption,
    HTMLFormatOption,
)

# Создание конвертера с опциями для всех форматов
converter = DocumentConverter(
    format_options={
        InputFormat.DOCX: WordFormatOption(),
        InputFormat.XLSX: ExcelFormatOption(),
        InputFormat.PPTX: PowerpointFormatOption(),
        InputFormat.HTML: HTMLFormatOption(),
    }
)
```

**Обновить runner.py:**
```python
def run_docling_conversion(
    file_path: Path,
    pdf_options: Optional[PdfPipelineOptions] = None,
) -> ConversionResult:
    """
    Конвертирует файл через Docling.

    PDF файлы используют переданные options.
    Native форматы (DOCX, XLSX, PPTX) используют defaults.
    """
    format_options = {}

    # PDF с кастомными options
    if pdf_options:
        format_options[InputFormat.PDF] = PdfFormatOption(
            pipeline_options=pdf_options
        )

    # Native форматы с defaults (Docling обрабатывает автоматически)
    # НЕ нужно явно указывать - Docling сам определит формат

    converter = DocumentConverter(format_options=format_options)
    return converter.convert(str(file_path))
```

---

### Фаза 6: Очистка неиспользуемых YAML настроек (30 мин)

**Проблема:** Многие настройки в YAML не применяются через API Docling.

**Настройки которые НЕ РАБОТАЮТ:**
```yaml
performance:
  threads: 4        # ← НЕ применяется
  batch_pages: 8    # ← НЕ применяется

processing_constraints:
  max_runtime_sec: 60   # ← НЕ применяется
  max_memory_mb: 2048   # ← НЕ применяется

language:
  primary: ru       # ← НЕ применяется (нужно через ocr_options)
```

**Решение:** Либо удалить, либо реализовать через AcceleratorOptions:

```python
from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions

if "performance" in template:
    perf = template["performance"]
    pdf_opts.accelerator_options = AcceleratorOptions(
        num_threads=perf.get("threads", 4),
        device=AcceleratorDevice.CPU
    )
```

---

## Итоговый план

| Фаза | Задача | Время | Приоритет |
|------|--------|-------|-----------|
| 1 | Очистка requirements.txt | 5 мин | Высокий |
| 2 | Упрощение runner.py | 30 мин | Высокий |
| 3 | OCR для русского языка | 1 час | Высокий |
| 4 | Тестирование OCR | 2 часа | Высокий |
| 5 | Native форматы | 1 час | Средний |
| 6 | Очистка YAML | 30 мин | Низкий |

**Общее время:** ~5 часов

---

## Ожидаемые результаты

| Метрика | До | После |
|---------|-----|-------|
| Строк в runner.py | 223 | ~120 |
| Зависимости в requirements.txt | 4 | 3 |
| OCR для русского | ❌ Только eng | ✅ ru + en |
| Применение YAML настроек | ~60% | ~90% |
| Тесты OCR | ❌ Нет | ✅ Comparison report |

---

## Риски и митигация

| Риск | Вероятность | Митигация |
|------|-------------|-----------|
| EasyOCR медленнее Tesseract | Средняя | Benchmark в Фазе 4, выбор по результатам |
| Регрессия после упрощения runner.py | Низкая | Существующие тесты (8 passed) |
| Несовместимость версий Docling | Низкая | Pinned version docling>=2.60.0 |

---

## Команды для выполнения

```bash
# Фаза 1: Очистка зависимостей
cd /root/winners_preprocessor/final_preprocessing/docling_integration
# Редактировать requirements.txt

# Фаза 4: Запуск тестов OCR
python3 scripts/test_ocr_comparison.py

# Верификация после изменений
python3 -m pytest tests/ -v
```

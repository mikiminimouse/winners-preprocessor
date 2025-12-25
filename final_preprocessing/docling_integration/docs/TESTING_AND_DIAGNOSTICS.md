# Тестирование и диагностика Docling Integration

**Дата создания:** 2025-12-25  
**Версия:** 1.0

## Обзор

Данный документ описывает стратегию тестирования, диагностические инструменты и руководство по устранению неполадок для системы Docling Integration.

---

## 1. Стратегия тестирования

### 1.1. Unit тесты

#### Компоненты для тестирования

**Bridge (`bridge_docprep.py`):**
- Загрузка UNIT из Ready2Docling
- Загрузка и валидация `docprep.contract.json`
- Определение главного файла
- Обработка ошибок (отсутствие контракта, неправильный формат)

**Config (`config.py`):**
- Загрузка YAML templates
- Построение `PipelineOptions` из templates
- Маппинг route → `InputFormat`
- Fallback на legacy конфигурацию
- Обработка VLM pipeline options

**Runner (`runner.py`):**
- Инициализация `DocumentConverter` с `PipelineOptions`
- Retry механизм
- Обработка ошибок конвертации
- Batch обработка (если поддерживается)

**Pipeline (`pipeline.py`):**
- Обработка одного UNIT (`process_unit`)
- Массовая обработка (`process_directory`)
- Экспорт результатов (JSON, Markdown, MongoDB)
- Quarantine механизм

**Exporters:**
- JSON экспорт (`exporters/json.py`)
- Markdown экспорт (`exporters/markdown.py`)
- MongoDB экспорт (`exporters/mongodb.py`)

#### Примеры Unit тестов

```python
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from docling_integration.bridge_docprep import load_unit, get_main_file
from docling_integration.config import build_pipeline_options

def test_load_unit_with_valid_contract():
    """Тест загрузки UNIT с валидным контрактом"""
    unit_path = Path("test_data/UNIT_123")
    contract = load_unit(unit_path)
    assert contract is not None
    assert "routing" in contract
    assert "docling_route" in contract["routing"]

def test_load_unit_without_contract():
    """Тест обработки отсутствующего контракта"""
    unit_path = Path("test_data/UNIT_INVALID")
    with pytest.raises(FileNotFoundError):
        load_unit(unit_path)

def test_build_pipeline_options_from_yaml():
    """Тест построения PipelineOptions из YAML template"""
    route = "pdf_text"
    options = build_pipeline_options(route)
    assert options is not None
    assert options.pdf is not None
    assert options.pdf.do_table_structure == True

@patch('docling_integration.runner.DocumentConverter')
def test_runner_retry_mechanism(mock_converter):
    """Тест механизма retry при ошибках"""
    mock_converter.return_value.convert.side_effect = [
        Exception("First attempt failed"),
        "Success"
    ]
    # Тест retry логики
```

#### Моки для Docling

```python
from unittest.mock import Mock, MagicMock

# Мок для DocumentConverter
mock_converter = Mock()
mock_converter.convert.return_value = Mock(
    document=Mock(
        body=Mock(children=[]),
        texts=[],
        tables=[],
        pictures=[]
    )
)

# Мок для ConversionResult
mock_result = MagicMock()
mock_result.document = Mock()
```

#### Тесты валидации контрактов

```python
def test_contract_validation_valid():
    """Тест валидации валидного контракта"""
    contract = {
        "routing": {"docling_route": "pdf_text"},
        "source": {"true_extension": "pdf"}
    }
    assert validate_contract(contract) == True

def test_contract_validation_invalid_route():
    """Тест валидации контракта с неподдерживаемым route"""
    contract = {
        "routing": {"docling_route": "mixed"}  # Неподдерживаемый route
    }
    assert validate_contract(contract) == False
```

### 1.2. Интеграционные тесты

#### Тесты полного pipeline

**Цель:** Проверить работу всего pipeline от входных данных до экспорта результатов.

```python
def test_full_pipeline_pdf_text():
    """Тест полного pipeline для pdf_text"""
    pipeline = DoclingPipeline(
        export_json=True,
        export_markdown=True,
        export_mongodb=False
    )
    
    unit_path = Path("test_data/UNIT_PDF_TEXT")
    result = pipeline.process_unit(unit_path)
    
    assert result["success"] == True
    assert "exports" in result
    assert "json" in result["exports"]
    assert "markdown" in result["exports"]

def test_full_pipeline_with_error():
    """Тест обработки ошибок в pipeline"""
    pipeline = DoclingPipeline()
    unit_path = Path("test_data/UNIT_INVALID")
    result = pipeline.process_unit(unit_path)
    
    assert result["success"] == False
    assert len(result["errors"]) > 0
```

#### Тесты с реальными файлами

**Использование тестовых данных:**

```python
# Тестовые данные в test_data/
test_data/
  UNIT_PDF_TEXT/
    files/
      document.pdf
    docprep.contract.json
  UNIT_DOCX/
    files/
      document.docx
    docprep.contract.json
```

**Тесты:**
- Обработка различных форматов (PDF, DOCX, XLSX, PPTX, HTML, XML, изображения)
- Валидация структуры экспортированных документов
- Проверка сохранения layout в Markdown
- Проверка корректности JSON экспорта

#### Тесты экспорта в различные форматы

```python
def test_json_export():
    """Тест JSON экспорта"""
    document = create_test_document()
    output_path = Path("test_output/test.json")
    export_to_json(document, output_path)
    
    assert output_path.exists()
    with open(output_path) as f:
        data = json.load(f)
        assert "document" in data
        assert "body" in data["document"]

def test_markdown_export():
    """Тест Markdown экспорта с сохранением структуры"""
    document = create_test_document_with_structure()
    output_path = Path("test_output/test.md")
    export_to_markdown(document, output_path)
    
    assert output_path.exists()
    with open(output_path) as f:
        content = f.read()
        assert "## " in content  # Проверка заголовков
        assert "|" in content  # Проверка таблиц
```

### 1.3. Тесты с реальными данными

#### Тесты на выборке документов из Ready2Docling

**Цель:** Валидация работы системы на реальных данных.

```python
def test_processing_sample_from_ready2docling():
    """Тест обработки выборки документов из Ready2Docling"""
    ready2docling_path = Path("Data/2025-03-04/Ready2Docling")
    
    pipeline = DoclingPipeline()
    results = []
    
    # Обработка первых 10 UNIT
    for unit_path in list(ready2docling_path.iterdir())[:10]:
        result = pipeline.process_unit(unit_path)
        results.append(result)
    
    # Проверка успешности
    success_rate = sum(1 for r in results if r["success"]) / len(results)
    assert success_rate >= 0.9  # Минимум 90% успешных обработок
```

#### Валидация качества экспорта

**Проверка структуры:**
- Наличие всех секций документа
- Корректность заголовков
- Сохранение таблиц
- Наличие изображений

**Метрики качества:**
- Процент успешно обработанных документов
- Время обработки на документ
- Размер экспортированных файлов
- Количество ошибок

#### Производительность на больших объемах

```python
def test_performance_large_batch():
    """Тест производительности на большом батче"""
    import time
    
    pipeline = DoclingPipeline()
    units = list(Path("Data/2025-03-04/Ready2Docling").iterdir())
    
    start_time = time.time()
    for unit_path in units:
        pipeline.process_unit(unit_path)
    end_time = time.time()
    
    total_time = end_time - start_time
    avg_time_per_unit = total_time / len(units)
    
    print(f"Обработано {len(units)} UNIT за {total_time:.2f} секунд")
    print(f"Среднее время на UNIT: {avg_time_per_unit:.2f} секунд")
    
    # Проверка, что среднее время в разумных пределах
    assert avg_time_per_unit < 60  # Меньше 60 секунд на UNIT
```

---

## 2. Диагностические инструменты

### 2.1. Логирование

#### Настройка логирования

```python
import logging

# Настройка логирования для Docling Integration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('docling_integration.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('docling_integration')
```

#### Детальное логирование этапов обработки

**В pipeline.py:**

```python
logger.info(f"Начало обработки UNIT: {unit_id}")
logger.debug(f"Contract: {contract}")
logger.info(f"Route: {route}")
logger.info(f"PipelineOptions: {options}")
logger.info(f"Конвертация документа...")
logger.info(f"Успешная конвертация: {unit_id}")
logger.info(f"Экспорт JSON: {json_path}")
logger.info(f"Экспорт Markdown: {md_path}")
```

#### Логирование ошибок с контекстом

```python
try:
    document = run_docling_conversion(file_path, options)
except Exception as e:
    logger.error(
        f"Ошибка конвертации для {unit_id}: {e}",
        exc_info=True,
        extra={
            "unit_id": unit_id,
            "file_path": str(file_path),
            "route": route,
            "contract": contract
        }
    )
    raise
```

#### Метрики производительности

```python
import time

start_time = time.time()
document = run_docling_conversion(file_path, options)
conversion_time = time.time() - start_time

logger.info(
    f"Конвертация завершена за {conversion_time:.2f} секунд",
    extra={"unit_id": unit_id, "conversion_time": conversion_time}
)
```

### 2.2. Мониторинг

#### Время обработки на UNIT

**Метрики для сбора:**
- Общее время обработки UNIT
- Время конвертации Docling
- Время экспорта (JSON, Markdown, MongoDB)
- Время загрузки контракта и файлов

```python
def process_unit_with_metrics(self, unit_path: Path) -> Dict[str, Any]:
    """Обработка UNIT с метриками"""
    metrics = {}
    
    # Загрузка
    start = time.time()
    contract = load_contract(unit_path)
    metrics["load_time"] = time.time() - start
    
    # Конвертация
    start = time.time()
    document = run_docling_conversion(file_path, options)
    metrics["conversion_time"] = time.time() - start
    
    # Экспорт
    start = time.time()
    export_results(document, ...)
    metrics["export_time"] = time.time() - start
    
    metrics["total_time"] = sum(metrics.values())
    return {"result": result, "metrics": metrics}
```

#### Успешность обработки

**Статистика:**
- Общее количество UNIT
- Количество успешно обработанных
- Количество ошибок
- Процент успешности

```python
def collect_statistics(results: List[Dict]) -> Dict:
    """Сбор статистики обработки"""
    total = len(results)
    successful = sum(1 for r in results if r["success"])
    failed = total - successful
    success_rate = successful / total if total > 0 else 0
    
    return {
        "total": total,
        "successful": successful,
        "failed": failed,
        "success_rate": success_rate
    }
```

#### Использование ресурсов

**Мониторинг:**
- Использование памяти
- Использование CPU
- Использование диска

```python
import psutil
import os

def get_resource_usage() -> Dict:
    """Получение информации об использовании ресурсов"""
    process = psutil.Process(os.getpid())
    
    return {
        "memory_mb": process.memory_info().rss / 1024 / 1024,
        "cpu_percent": process.cpu_percent(interval=1),
        "disk_usage": psutil.disk_usage('/').percent
    }
```

### 2.3. Анализ качества

#### Валидация структуры экспортированных документов

**Проверки:**
- Наличие обязательных полей в JSON
- Корректность структуры DoclingDocument
- Наличие body, groups, texts, tables, pictures

```python
def validate_document_structure(document: Dict) -> List[str]:
    """Валидация структуры документа"""
    errors = []
    
    if "body" not in document:
        errors.append("Отсутствует поле 'body'")
    
    if "texts" not in document:
        errors.append("Отсутствует поле 'texts'")
    
    # Проверка структуры body
    if "body" in document:
        body = document["body"]
        if "children" not in body:
            errors.append("Body не содержит 'children'")
    
    return errors
```

#### Проверка сохранения layout

**Проверки для Markdown:**
- Наличие заголовков (##, ###)
- Сохранение списков
- Наличие таблиц
- Правильные отступы

```python
def validate_markdown_layout(md_path: Path) -> List[str]:
    """Валидация layout в Markdown"""
    errors = []
    
    with open(md_path) as f:
        content = f.read()
        
        # Проверка заголовков
        if not re.search(r'^#{1,6}\s', content, re.MULTILINE):
            errors.append("Отсутствуют заголовки")
        
        # Проверка таблиц
        if "|" not in content and "Table" in content:
            errors.append("Таблицы не экспортированы")
    
    return errors
```

#### Анализ ошибок в Quarantine

**Автоматический анализ:**
- Группировка ошибок по типу
- Определение частых проблем
- Рекомендации по исправлению

```python
def analyze_quarantine(quarantine_path: Path) -> Dict:
    """Анализ ошибок в Quarantine"""
    errors_by_type = {}
    
    for unit_path in quarantine_path.iterdir():
        error_file = unit_path / "error_info.txt"
        if error_file.exists():
            with open(error_file) as f:
                error_msg = f.read()
                error_type = classify_error(error_msg)
                errors_by_type[error_type] = errors_by_type.get(error_type, 0) + 1
    
    return errors_by_type
```

---

## 3. Troubleshooting guide

### 3.1. Частые ошибки

#### Contract not found

**Ошибка:** `FileNotFoundError: docprep.contract.json not found`

**Причина:** Контракт не был сгенерирован в merger

**Решение:**
1. Проверить, что merger был запущен для данного UNIT
2. Проверить наличие `docprep.contract.json` в директории UNIT
3. Запустить merger заново для генерации контракта

**Проверка:**
```bash
ls -la Data/2025-03-04/Ready2Docling/UNIT_*/docprep.contract.json
```

#### Route "mixed"

**Ошибка:** `ValueError: Route 'mixed' is not supported`

**Причина:** UNIT с route='mixed' попал в Ready2Docling (должен быть отфильтрован)

**Решение:**
1. Проверить фильтрацию в `docprep/engine/merger.py`
2. Убедиться, что route='mixed' исключается
3. Переместить проблемный UNIT обратно в merge директорию

**Проверка:**
```python
# В merger.py должно быть:
if dominant_type == 'mixed':
    logger.warning(f"Unit {unit_id} has route 'mixed'. Skipping.")
    continue
```

#### Unsupported format

**Ошибка:** `docling.exceptions.ConversionError: File format not allowed`

**Причина:** Неподдерживаемый формат файла (ZIP, RAR, и т.д.)

**Решение:**
1. Проверить фильтрацию неподдерживаемых форматов в merger
2. Убедиться, что такие UNIT не попадают в Ready2Docling
3. Если формат должен поддерживаться, добавить предобработку

**Неподдерживаемые форматы:**
- Архивы: ZIP, RAR, 7Z
- Исполняемые файлы: EXE, DLL, BIN

#### Conversion errors

**Ошибка:** Общие ошибки конвертации от Docling

**Диагностика:**
1. Проверить логи для детальной информации об ошибке
2. Проверить формат файла (может быть поврежден)
3. Проверить размер файла (может быть слишком большой)
4. Проверить доступность ресурсов (память, CPU)

**Типичные причины:**
- Поврежденный файл
- Недостаточно памяти
- Неправильные PipelineOptions
- Неподдерживаемый подтип формата

### 3.2. Диагностика проблем с моделями

#### Проверка установки моделей Docling

**Проблема:** Модели не загружаются

**Решение:**
```python
# Проверка доступности моделей
from docling.document_converter import DocumentConverter
from docling.datamodel.pipeline_options import PipelineOptions

try:
    converter = DocumentConverter()
    print("Docling инициализирован успешно")
except Exception as e:
    print(f"Ошибка инициализации: {e}")
```

**Проверка кэша моделей:**
```bash
ls -lah ~/.cache/docling/
```

#### Проверка доступности Tesseract (для OCR)

**Проблема:** OCR не работает

**Решение:**
```bash
# Проверка установки
tesseract --version

# Проверка языков
tesseract --list-langs

# Должен быть 'rus' для русского языка
```

**Установка русского языка:**
```bash
sudo apt-get install tesseract-ocr-rus
```

#### Проверка памяти для больших документов

**Проблема:** Out of Memory ошибки

**Решение:**
1. Увеличить `max_memory_mb` в processing_constraints
2. Использовать более легкие модели (например, docbank вместо publaynet_detectron2)
3. Обрабатывать документы последовательно вместо параллельно
4. Проверить использование памяти процессами

```python
# Проверка памяти
import psutil
import os

process = psutil.Process(os.getpid())
memory_mb = process.memory_info().rss / 1024 / 1024
print(f"Использование памяти: {memory_mb:.2f} MB")
```

### 3.3. Работа с quarantine

#### Анализ error_info.txt

**Формат error_info.txt:**
```
UNIT_ID: UNIT_12345
ERROR_TYPE: ConversionError
ERROR_MESSAGE: File format not allowed
TIMESTAMP: 2025-03-04T12:00:00Z
FILE_PATH: /path/to/file.pdf
ROUTE: pdf_text
```

**Анализ:**
```python
def analyze_quarantine_unit(unit_path: Path) -> Dict:
    """Анализ проблемного UNIT"""
    error_file = unit_path / "error_info.txt"
    
    with open(error_file) as f:
        error_info = {}
        for line in f:
            if ':' in line:
                key, value = line.split(':', 1)
                error_info[key.strip()] = value.strip()
    
    return error_info
```

#### Проверка исходных файлов

**Действия:**
1. Проверить наличие файлов в UNIT
2. Проверить формат файлов
3. Попробовать открыть файлы вручную
4. Проверить размер файлов

```bash
# Проверка файлов в quarantine UNIT
ls -lah Quarantine/UNIT_*/files/

# Проверка типа файла
file Quarantine/UNIT_*/files/*

# Проверка размера
du -h Quarantine/UNIT_*/
```

#### Определение причины ошибки

**Шаги:**
1. Прочитать error_info.txt
2. Проверить логи обработки
3. Попробовать обработать файл вручную через Docling
4. Определить, является ли проблема системной или специфичной для файла

**Ручная проверка:**
```python
from docling.document_converter import DocumentConverter

converter = DocumentConverter()
try:
    document = converter.convert("path/to/problematic/file.pdf")
    print("Файл обрабатывается успешно")
except Exception as e:
    print(f"Ошибка: {e}")
```

---

**Связанные документы:**
- [COMPONENTS.md](COMPONENTS.md) - Описание компонентов
- [CONFIGURATION.md](CONFIGURATION.md) - Конфигурация
- [REFACTORING_AND_IMPROVEMENTS.md](REFACTORING_AND_IMPROVEMENTS.md) - Известные проблемы

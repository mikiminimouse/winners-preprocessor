# Внешние библиотеки и модели Docling Integration

**Дата создания:** 2025-12-25  
**Версия:** 1.0

## Обзор

Docling Integration использует IBM Docling библиотеку и различные модели машинного обучения для обработки документов. Данный документ описывает все внешние зависимости, библиотеки и модели, используемые в системе.

---

## 1. Основные зависимости Python

### 1.1. Основные библиотеки

#### docling

- **Версия:** `>=2.60.0`
- **Описание:** Основная библиотека IBM Docling для обработки документов
- **Использование:** Ядро системы, основной DocumentConverter
- **Установка:** `pip install docling>=2.60.0`

#### docling-core

- **Версия:** `>=2.50.0`
- **Описание:** Ядро Docling, содержащее базовые классы и утилиты
- **Использование:** Внутренние зависимости Docling
- **Установка:** Устанавливается автоматически с `docling`

#### pyyaml

- **Версия:** `>=6.0`
- **Описание:** Библиотека для парсинга YAML файлов
- **Использование:** Загрузка конфигурационных templates из `pipeline_templates/`
- **Установка:** `pip install pyyaml>=6.0`

#### pymongo

- **Версия:** `>=4.0.0`
- **Описание:** MongoDB клиент для Python
- **Использование:** Экспорт результатов обработки в MongoDB (опционально)
- **Установка:** `pip install pymongo>=4.0.0`

### 1.2. Зависимости Docling

#### torch (PyTorch)

- **Описание:** Фреймворк машинного обучения для моделей
- **Использование:** Все CNN и Transformer модели требуют PyTorch
- **Установка:** 
  - CPU-only: `pip install torch==2.9.1+cpu torchvision==0.24.1+cpu`
  - GPU: `pip install torch torchvision` (требует CUDA)

#### detectron2

- **Описание:** Фреймворк для детекции объектов от Facebook AI Research
- **Использование:** Требуется для некоторых моделей layout detection (publaynet_detectron2)
- **Установка:** `pip install detectron2` или через предкомпилированные wheel

#### Pillow/PIL

- **Описание:** Библиотека для обработки изображений
- **Использование:** Конвертация PDF страниц в изображения, обработка изображений
- **Установка:** Обычно устанавливается автоматически с зависимостями

#### pypdf / pypdf2

- **Описание:** Библиотека для работы с PDF файлами
- **Использование:** Извлечение метаданных, работа с PDF структурой
- **Установка:** Устанавливается автоматически с Docling

---

## 2. CNN модели используемые в Docling

### 2.1. Layout Detection Models

#### publaynet_detectron2

- **Тип:** CNN модель на основе Detectron2
- **Назначение:** Анализ layout документов (определение регионов: текст, таблицы, изображения)
- **Использование:** PDF с текстовым слоем (`pdf_text` route)
- **Источник:** Pre-trained модель от IBM, поставляется с Docling
- **Требования:**
  - PyTorch
  - detectron2
  - Достаточно памяти (обычно 2-4 GB)

**Особенности:**
- Хорошо работает с born-digital PDF
- Определяет регионы документа: текст, заголовки, таблицы, изображения, списки
- Используется для восстановления структуры документа

#### docbank

- **Тип:** CNN модель для анализа layout сканированных документов
- **Назначение:** Layout detection для документов после OCR
- **Использование:** PDF со сканированным содержимым (`pdf_scan`, `pdf_scan_table` routes)
- **Источник:** Pre-trained модель от IBM, поставляется с Docling
- **Требования:**
  - PyTorch
  - Меньше требований к памяти чем publaynet_detectron2

**Особенности:**
- Оптимизирована для работы с результатами OCR
- Работает с изображениями страниц после распознавания текста
- Альтернатива publaynet_detectron2 для сканированных документов

### 2.2. Table Extraction Models

#### table-transformer

- **Тип:** Transformer модель для извлечения таблиц
- **Назначение:** Определение структуры таблиц (ячейки, строки, столбцы, объединенные ячейки)
- **Использование:** PDF с текстовым слоем (`pdf_text` route)
- **Источник:** Pre-trained модель от IBM, поставляется с Docling
- **Требования:**
  - PyTorch
  - Обычно меньше требований к памяти чем cascadetabnet

**Особенности:**
- Transformer архитектура для лучшего понимания контекста
- Определяет структуру таблиц с высокой точностью
- Извлекает данные из ячеек с сохранением структуры

#### cascadetabnet

- **Тип:** CNN модель для извлечения таблиц из сканов
- **Назначение:** Определение структуры таблиц в сканированных документах
- **Использование:** PDF со сканированным содержимым и таблицами (`pdf_scan_table` route)
- **Источник:** Pre-trained модель от IBM, поставляется с Docling
- **Требования:**
  - PyTorch
  - Больше памяти чем table-transformer (обычно 4-8 GB)

**Особенности:**
- Работает с изображениями (результаты OCR)
- Более требовательна к ресурсам
- Лучше справляется со сложными таблицами в сканах

---

## 3. OCR Engine

### Tesseract

- **Тип:** OCR движок (Optical Character Recognition)
- **Назначение:** Распознавание текста из изображений и сканированных документов
- **Использование:** 
  - PDF со сканированным содержимым (`pdf_scan`, `pdf_scan_table` routes)
  - Изображения (`image_ocr` route)
- **Поддержка языков:** Множество языков, включая русский (rus)

**Установка:**

```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr
sudo apt-get install tesseract-ocr-rus  # Для русского языка

# macOS
brew install tesseract
brew install tesseract-lang  # Включает русский

# Windows
# Скачать с https://github.com/UB-Mannheim/tesseract/wiki
```

**Настройка для русского языка:**

- Требуется установка языкового пакета Tesseract для русского (`rus`)
- В Docling настройка языка через `PdfPipelineOptions` (если поддерживается API)
- Для улучшения качества можно использовать VLM pipeline

**Особенности:**
- Открытый исходный код
- Поддерживает множество языков
- Можно настроить параметры для улучшения качества распознавания
- Требует системной установки (не Python пакет)

---

## 4. VLM (Vision Language Model) интеграция

### 4.1. Обзор

VLM (Vision Language Model) - это удаленный сервис, который может использоваться для улучшения качества OCR и понимания документов.

**Тип:** Удаленный VLM сервис (опционально)

**Использование:** Опционально для улучшения OCR качества

**Источники:**
- IBM Granite
- Cloud.ru VLM API
- Другие совместимые VLM endpoints

### 4.2. Настройка

Настройка через environment variables:

```bash
export VLM_ENDPOINT="https://api.example.com/vlm"
export VLM_MODEL="granite-vision-ocr"
```

**В YAML templates:**

```yaml
models:
  vlm:
    enabled: true
    model: granite-vision-ocr  # или значение из VLM_MODEL env var
```

### 4.3. Конфигурация в PipelineOptions

VLM pipeline options настраиваются через `VlmPipelineOptions`:

```python
from docling.datamodel.pipeline_options import VlmPipelineOptions, PipelineOptions

options = PipelineOptions()
options.vlm = VlmPipelineOptions()
options.vlm.endpoint = os.environ.get("VLM_ENDPOINT")
options.vlm.model = os.environ.get("VLM_MODEL", "default")
```

### 4.4. Fallback механизм

- Если VLM недоступен, система автоматически использует стандартный OCR (Tesseract)
- Graceful degradation обеспечивает непрерывность обработки
- Логирование предупреждений при недоступности VLM

---

## 4.5. Cloud.ru ML Foundation Services

### Granite Docling (VLM Service)

**Тип:** Cloud.ru ML Foundation Model Run

**Назначение:** Улучшение понимания документов через Vision Language Model inference

**Использование:**
- Опциональное улучшение качества обработки документов
- VLM inference для сложных документов
- Улучшение OCR качества через языковые модели

**Интеграция:**
- Через VLM pipeline options в Docling
- Endpoint настраивается через environment variables
- Используется как часть Docling VLM pipeline

**Настройка:**
```bash
export VLM_ENDPOINT="https://ml-foundation.cloud.ru/model-run/granite_docling"
export VLM_MODEL="granite-docling"
```

**Статус:** Планируется к интеграции на следующем этапе рефакторинга

### PaddleOCR_VLM (OCR Service)

**Тип:** Cloud.ru ML Foundation Docker Run

**Назначение:** OCR обработка PDF файлов через GPU-ускоренный сервис

**Использование:**
- OCR для PDF документов, требующих высококачественного распознавания
- Обработка сложных документов с таблицами и изображениями
- Альтернатива локальному Tesseract для ресурсоемких задач

**Интеграция:**
- Через внешний API сервиса
- Endpoint настраивается через environment variables
- Используется для PDF, где требуется OCR (pdf_scan, pdf_scan_table)

**Настройка:**
```bash
export PADDLEOCR_VLM_ENDPOINT="https://ml-foundation.cloud.ru/docker-run/paddleocr_vlm"
export PADDLEOCR_VLM_API_KEY="your-api-key"
```

**Компонент:** `ocr_vl/` - Docker сервис PaddleOCR-VL

**Статус:** Планируется к интеграции на следующем этапе рефакторинга

### Архитектура гибридной обработки

**Текущая архитектура (Этап 1):**
- Ядро: `docling-core` с CNN моделями на CPU
- OCR: Локальный Tesseract
- VLM: Не используется

**Планируемая архитектура (Этап 2):**
- Ядро: `docling-core` с CNN моделями на CPU (основная обработка)
- OCR: Cloud.ru PaddleOCR_VLM (GPU) для ресурсоемких задач
- VLM: Cloud.ru Granite Docling (GPU) для улучшения понимания
- Fallback: Локальный Tesseract если внешние сервисы недоступны

**Преимущества:**
- Эффективное использование ресурсов (CPU для основной обработки, GPU для тяжелых задач)
- Масштабируемость через внешние сервисы
- Оптимизация затрат (GPU только для ресурсоемких задач)
- Graceful degradation при недоступности внешних сервисов

---

## 5. Системные зависимости

### 5.1. Tesseract OCR

**Требование:** Обязательно для OCR обработки

**Установка:** См. раздел 3 (OCR Engine)

**Проверка установки:**

```bash
tesseract --version
tesseract --list-langs  # Проверить установленные языки
```

### 5.2. CUDA / GPU (опционально)

**Требование:** Опционально для ускорения обработки

**Использование:** Если `allow_gpu=true` в конфигурации

**Требования:**
- NVIDIA GPU с поддержкой CUDA
- CUDA toolkit
- cuDNN
- PyTorch с поддержкой CUDA

**Установка:**

```bash
# PyTorch с CUDA
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

---

## 6. Установка всех зависимостей

### 6.1. Минимальная установка (CPU only)

```bash
# Основные пакеты
pip install docling>=2.60.0
pip install pyyaml>=6.0
pip install pymongo>=4.0.0  # Опционально

# PyTorch CPU-only
pip install torch==2.9.1+cpu torchvision==0.24.1+cpu

# Tesseract (системная установка)
sudo apt-get install tesseract-ocr tesseract-ocr-rus
```

### 6.2. Полная установка (с GPU поддержкой)

```bash
# Основные пакеты
pip install docling>=2.60.0
pip install pyyaml>=6.0
pip install pymongo>=4.0.0

# PyTorch с CUDA
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# Detectron2 (если требуется)
pip install detectron2 -f https://dl.fbaipublicfiles.com/detectron2/wheels/cu118/torch2.0/index.html

# Tesseract
sudo apt-get install tesseract-ocr tesseract-ocr-rus
```

### 6.3. Проверка установки

```python
import docling
print(f"Docling version: {docling.__version__}")

import torch
print(f"PyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")

# Проверка Tesseract
import subprocess
result = subprocess.run(['tesseract', '--version'], capture_output=True, text=True)
print(f"Tesseract: {result.stdout}")
```

---

## 7. Загрузка моделей

### 7.1. Автоматическая загрузка

Docling автоматически загружает необходимые модели при первом использовании:

- Модели загружаются в кэш при первом вызове
- Размер моделей: от нескольких сотен MB до нескольких GB
- Хранятся в `~/.cache/docling/` или аналогичной директории

### 7.2. Предварительная загрузка

Если необходимо предварительно загрузить модели:

```python
from docling.document_converter import DocumentConverter
from docling.datamodel.pipeline_options import PdfPipelineOptions, PipelineOptions

# Создание конвертера загрузит необходимые модели
options = PipelineOptions(
    pdf=PdfPipelineOptions(
        do_ocr=True,
        do_table_structure=True
    )
)
converter = DocumentConverter(options)  # Модели загружаются здесь
```

---

## 8. Версионирование и совместимость

### 8.1. Версии Docling

- **Минимальная версия:** `docling>=2.60.0`
- **Рекомендуемая версия:** Последняя стабильная версия
- **Проверка совместимости:** Обновления могут изменять API, необходимо тестирование

### 8.2. Совместимость моделей

- Модели привязаны к версии Docling
- Обновление Docling может потребовать обновления моделей
- Модели автоматически обновляются при обновлении Docling

### 8.3. Breaking Changes

При обновлении Docling:
- Проверить изменения в `PipelineOptions` API
- Проверить изменения в структуре `ConversionResult`
- Обновить тесты при необходимости

---

## 9. Ресурсы и производительность

### 9.1. Требования к памяти

- **Минимальная:** 2 GB RAM (для простых документов)
- **Рекомендуемая:** 4-8 GB RAM (для сложных документов с таблицами)
- **Для cascadetabnet:** 8+ GB RAM

### 9.2. Требования к CPU

- Все модели работают на CPU
- Многоядерные процессоры обеспечивают параллельную обработку
- Рекомендуется: 4+ ядер

### 9.3. Требования к GPU (опционально)

- NVIDIA GPU с 4+ GB VRAM
- CUDA 11.8 или выше
- Ускоряет обработку в 2-5 раз (зависит от модели)

---

## 10. Лицензии и использование

### 10.1. Docling

- Лицензия: См. официальную документацию IBM Docling
- Коммерческое использование: Требуется лицензия от IBM

### 10.2. Модели

- Модели от IBM: Лицензия согласно Docling license
- Tesseract: Apache License 2.0
- PyTorch: BSD-style license

### 10.3. Зависимости

- Все зависимости имеют открытые лицензии
- Проверьте лицензии для коммерческого использования

---

**Связанные документы:**
- [CONFIGURATION.md](CONFIGURATION.md) - Конфигурация системы
- [BEST_PRACTICES.md](BEST_PRACTICES.md) - Рекомендации по использованию
- [PERFORMANCE_AND_SCALING.md](PERFORMANCE_AND_SCALING.md) - Производительность

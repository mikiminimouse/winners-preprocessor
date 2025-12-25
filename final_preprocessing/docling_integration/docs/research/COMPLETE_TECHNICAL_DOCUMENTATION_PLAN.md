# План создания технической документации Docling Integration

## Цель

Создать комплексную техническую документацию, описывающую все компоненты системы конвейера Docling, включая архитектуру, настройки, внешние зависимости, модели, контракты и best practices.

## Структура документации

### 1. Архитектурный обзор

**Файл**: `ARCHITECTURE.md`

**Содержание**:

- Общая схема системы (DocPrep → Ready2Docling → Docling Integration → OutputDocling)
- Диаграмма потоков данных
- Взаимодействие компонентов
- Контрактная модель (docprep.contract.json как граница между системами)

**Компоненты для описания**:

- `final_preprocessing/docling_integration/pipeline.py` - основной orchestration
- `final_preprocessing/docling_integration/bridge_docprep.py` - мост с DocPrep
- `final_preprocessing/docprep/engine/merger.py` - финальная сборка UNIT

### 2. Детальное описание компонентов

**Файл**: `COMPONENTS.md`

**Компоненты для детального анализа**:

#### 2.1. Bridge (`bridge_docprep.py`)

- Загрузка UNIT из Ready2Docling
- Валидация готовности через DoclingAdapter
- Загрузка `docprep.contract.json`
- Получение главного файла через AST nodes
- Обработка ошибок и валидация

#### 2.2. Config (`config.py`)

- Загрузка YAML templates из `pipeline_templates/`
- Построение `PipelineOptions` из templates
- Fallback на legacy hardcoded конфигурацию
- Маппинг route → `InputFormat`
- Обработка VLM pipeline options
- Сложная логика импорта для избежания конфликтов имен

#### 2.3. Runner (`runner.py`)

- Тонкая обертка над `DocumentConverter`
- Инициализация с `PipelineOptions`
- Retry механизм
- Batch обработка
- Обработка ошибок

#### 2.4. Pipeline (`pipeline.py`)

- Класс `DoclingPipeline` - основной orchestration
- Метод `process_unit()` - обработка одного UNIT
- Метод `process_directory()` - массовая обработка
- Экспорт результатов (JSON, Markdown, MongoDB)
- Quarantine механизм для проблемных UNIT
- Определение output subdirectory по расширению

#### 2.5. Exporters

- `exporters/json.py` - экспорт через `model_dump()`
- `exporters/markdown.py` - структурированный экспорт с сохранением layout
- `exporters/mongodb.py` - экспорт в MongoDB

### 3. Конфигурация и настройки

**Файл**: `CONFIGURATION.md`

**Содержание**:

#### 3.1. YAML Templates (`pipeline_templates/`)

Детальное описание каждого template:

- `pdf_text.yaml` - PDF с текстовым слоем
- Модели: `publaynet_detectron2` для layout, `table-transformer` для таблиц
- Настройки для русского языка
- Performance параметры
- `pdf_scan.yaml` - PDF со сканированным содержимым
- OCR: `tesseract`
- Layout: `docbank`
- `pdf_scan_table.yaml` - PDF с таблицами
- `docx.yaml`, `xlsx.yaml`, `pptx.yaml` - нативные форматы
- `html.yaml`, `xml.yaml` - веб-форматы
- `image_ocr.yaml` - изображения через OCR

#### 3.2. Параметры конфигурации

- `models.*` - выбор моделей (layout, tables, ocr, vlm)
- `performance.*` - настройки производительности (threads, batch_pages, dpi)
- `docling.*` - флаги Docling (parse_text, extract_tables, extract_figures)
- `language.*` - настройки языка (primary, fallback, encoding)
- `processing_constraints.*` - ограничения (allow_gpu, max_runtime_sec, max_memory_mb)

#### 3.3. Environment Variables

- `VLM_ENDPOINT` - endpoint для VLM pipeline
- `VLM_MODEL` - модель VLM
- MongoDB настройки (если используются)

### 4. Контракты и данные

**Файл**: `CONTRACTS_AND_DATA.md`

**Содержание**:

#### 4.1. docprep.contract.json

- Структура контракта
- Поля: `unit`, `source`, `routing`, `processing`
- Как contract генерируется в `docprep/core/contract.py`
- Валидация контракта
- Маппинг contract → Docling route

#### 4.2. Потоки данных

- Input: Ready2Docling/UNIT_*/files/
- Processing: DocumentConverter.convert()
- Output: ConversionResult → DoclingDocument
- Export:

### 5. Внешние библиотеки и модели

**Файл**: `EXTERNAL_LIBRARIES_AND_MODELS.md`

**Содержание**:

#### 5.1. Основные зависимости

- `docling>=1.0.0` - IBM Docling библиотека
- `pymongo>=4.0.0` - MongoDB клиент
- `PyYAML` - для работы с YAML templates
- `pdf2image` - для конвертации PDF в изображения (опционально)

#### 5.2. CNN модели используемые в Docling

- `publaynet_detectron2` - для layout detection
- `table-transformer` - для table structure recognition
- `tesseract` - OCR engine
- `docbank` - альтернативная модель для layout detection

#### 5.3. VLM интеграция

- Remote VLM endpoints
- Model selection via environment variables
- Fallback на стандартный OCR при недоступности VLM

### 6. Best Practices и Community Guidelines

**Файл**: `BEST_PRACTICES.md`

**Содержание**:

#### 6.1. Правильное использование Docling как конвейера

- Docling как двигатель, наш код как водитель (не дублируем parsing логику)
- Использование manifest из docprep (не определяем тип файла заново)
- Минимальная структура (только orchestration, конфигурация, экспорт)

#### 6.2. Преимущества и недостатки использования Docling

##### Преимущества:
- Единая точка обработки для множества форматов
- Высокое качество извлечения структуры документа
- Поддержка современных моделей (layout detection, table extraction)
- Активное сообщество и развитие

##### Недостатки:
- Зависимость от внешней библиотеки
- Ограниченная кастомизация внутренней логики
- Потребление ресурсов (память, CPU)

#### 6.3. Альтернативные подходы

- Использование оригинального Docling без модификаций
- Пересборка Docling с кастомными компонентами
- Гибридный подход (Docling + собственные обработчики)

### 7. Анализ текущей реализации и улучшения

**Файл**: `IMPROVEMENTS_AND_REFACTORING.md`

**Содержание**:

#### 7.1. Проблемы и ошибки текущей реализации

- Отсутствие четкого разделения ответственности между компонентами
- Сложная логика импорта в `config.py` для избежания конфликтов имен
- Недостаточная обработка ошибок в некоторых частях pipeline
- Неоптимальная работа с большими файлами (нет streaming)

#### 7.2. Возможности для улучшения

- Рефакторинг логики импорта в `config.py`
- Добавление более подробного логирования и мониторинга
- Оптимизация обработки больших файлов
- Улучшение механизма retry и обработки временных ошибок
- Расширение набора экспортёров

#### 7.3. Рекомендации по рефакторингу

- Разделение конфигурации на более мелкие модули
- Добавление unit-тестов для критических компонентов
- Улучшение документации кода
- Оптимизация производительности для batch обработки

### 8. Сравнение с ранними наработками

**Файл**: `EARLY_DEVELOPMENT_COMPARISON.md`

**Содержание**:

#### 8.1. Архитектурные изменения

- Переход от монолитного `processor.py` к модульному подходу
- Удаление fallback библиотек в пользу чистого Docling
- Введение контрактной модели через `docprep.contract.json`

#### 8.2. Улучшения в обработке

- Более точное определение route через контракт
- Улучшенная обработка ошибок и quarantine механизм
- Оптимизированная конфигурация через YAML templates

#### 8.3. Уроки из ранних реализаций

- Не стоит дублировать функциональность Docling
- Важность четкого контракта между системами
- Необходимость тестирования с реальными данными

### 9. Тестирование и диагностика

**Файл**: `TESTING_AND_DIAGNOSTICS.md`

**Содержание**:

#### 9.1. Стратегия тестирования

- Unit тесты для компонентов
- Интеграционные тесты pipeline
- Тесты с реальными данными

#### 9.2. Диагностические инструменты

- Логирование ошибок и предупреждений
- Мониторинг производительности
- Анализ качества извлечения данных

#### 9.3. Troubleshooting guide

- Частые ошибки и их решения
- Диагностика проблем с моделями
- Работа с quarantine директорией

### 10. Производительность и масштабирование

**Файл**: `PERFORMANCE_AND_SCALING.md`

**Содержание**:

#### 10.1. Оценка производительности

- Производительность по типам документов
- Влияние настроек на скорость обработки
- Оценка ресурсов (CPU, память, диск)

#### 10.2. Рекомендации по масштабированию

- Batch обработка
- Параллельная обработка
- Оптимизация конфигурации для production

#### 10.3. Мониторинг и метрики

- Сбор метрик обработки
- Alerting при проблемах
- Анализ трендов производительности
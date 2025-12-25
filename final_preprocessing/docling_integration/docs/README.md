# Техническая документация Docling Integration

**Дата создания:** 2025-12-24  
**Версия:** 1.0

## Обзор

Данная документация описывает систему Docling Integration - компонент для семантического понимания документов через IBM Docling библиотеку.

### Гибридная архитектура

Система использует гибридный подход к обработке документов:
- **Ядро (CPU):** `docling-core` с CNN моделями для основной обработки
- **Внешние сервисы (GPU):** Cloud.ru ML Foundation для улучшения качества:
  - **Granite Docling** - улучшение понимания документов через VLM
  - **PaddleOCR_VLM** - OCR обработка для PDF через GPU-ускоренный сервис

Интеграция внешних сервисов планируется на следующем этапе рефакторинга после отладки обработки digital документов.

## Структура документации

### Основные документы

1. **[ARCHITECTURE.md](ARCHITECTURE.md)** - Архитектурный обзор системы
   - Общая схема системы (DocPrep → Ready2Docling → Docling Integration → OutputDocling)
   - Диаграммы потоков данных
   - Взаимодействие компонентов
   - Контрактная модель

2. **[COMPONENTS.md](COMPONENTS.md)** - Детальное описание компонентов
   - Bridge (bridge_docprep.py)
   - Config (config.py)
   - Runner (runner.py)
   - Pipeline (pipeline.py)
   - Exporters (JSON, Markdown, MongoDB)

3. **[CONFIGURATION.md](CONFIGURATION.md)** - Конфигурация и настройки
   - YAML Templates (pipeline_templates/)
   - Параметры конфигурации
   - Environment Variables (включая настройки внешних сервисов Cloud.ru)
   - Внешние библиотеки и модели

4. **[CONTRACTS_AND_DATA.md](CONTRACTS_AND_DATA.md)** - Контракты и потоки данных
   - Структура docprep.contract.json
   - Генерация и валидация контрактов
   - Потоки данных (Input → Processing → Output)
   - Маппинг contract → Docling route

5. **[BEST_PRACTICES.md](BEST_PRACTICES.md)** - Лучшие практики использования Docling
   - Анализ текущей реализации
   - Best practices от сообщества Docling
   - Готовый vs пересобранный образ
   - Варианты использования

6. **[REFACTORING_AND_IMPROVEMENTS.md](REFACTORING_AND_IMPROVEMENTS.md)** - План рефакторинга и улучшений
   - Критические проблемы
   - Проблемы с обработкой структуры документа
   - Проблемы с поддержкой русского языка
   - План рефакторинга (включая интеграцию внешних сервисов)

7. **[EXTERNAL_LIBRARIES_AND_MODELS.md](EXTERNAL_LIBRARIES_AND_MODELS.md)** - Внешние библиотеки и модели
   - Основные зависимости Python
   - CNN модели (publaynet_detectron2, docbank, table-transformer, cascadetabnet)
   - OCR Engine (Tesseract)
   - Cloud.ru ML Foundation сервисы (Granite Docling, PaddleOCR_VLM)

8. **[PERFORMANCE_AND_SCALING.md](PERFORMANCE_AND_SCALING.md)** - Производительность и масштабирование

9. **[TESTING_AND_DIAGNOSTICS.md](TESTING_AND_DIAGNOSTICS.md)** - Тестирование и диагностика

10. **[EARLY_DEVELOPMENT_COMPARISON.md](EARLY_DEVELOPMENT_COMPARISON.md)** - Сравнение с ранними наработками

### Промежуточные документы

Промежуточные документы, планы и отчеты, созданные в процессе разработки, находятся в директории [`research/`](research/).

## Быстрый старт

### Для понимания архитектуры

1. Начните с [ARCHITECTURE.md](ARCHITECTURE.md) - общий обзор системы
2. Изучите [COMPONENTS.md](COMPONENTS.md) - детальное описание компонентов
3. Посмотрите [CONFIGURATION.md](CONFIGURATION.md) - как настроить систему

### Для использования системы

1. Изучите [CONFIGURATION.md](CONFIGURATION.md) - настройки и конфигурация
2. Посмотрите [CONTRACTS_AND_DATA.md](CONTRACTS_AND_DATA.md) - понимание контрактов
3. Изучите [BEST_PRACTICES.md](BEST_PRACTICES.md) - лучшие практики

### Для разработки и рефакторинга

1. Изучите [REFACTORING_AND_IMPROVEMENTS.md](REFACTORING_AND_IMPROVEMENTS.md) - проблемы и решения
2. Посмотрите [BEST_PRACTICES.md](BEST_PRACTICES.md) - как правильно использовать Docling
3. Изучите [COMPONENTS.md](COMPONENTS.md) - понимание внутренней структуры

## Ключевые концепции

### Контрактная модель

`docprep.contract.json` является формализованным контрактом между DocPrep и Docling Integration:

- Docling использует ТОЛЬКО contract.json
- manifest.json НЕ используется как вход для Docling
- Route не должен быть "mixed" или "unknown"

### Поток обработки

```
Ready2Docling → Bridge → Config → Runner → Exporters → OutputDocling
```

1. **Bridge:** Загрузка UNIT и контракта
2. **Config:** Построение PipelineOptions из YAML templates
3. **Runner:** Обработка через DocumentConverter
4. **Exporters:** Экспорт в JSON/Markdown/MongoDB

### Модели и библиотеки

- **Layout Analysis:** publaynet_detectron2, docbank
- **Table Extraction:** table-transformer, cascadetabnet
- **OCR:** Tesseract (локальный), PaddleOCR_VLM (Cloud.ru, планируется)
- **VLM:** Cloud.ru Granite Docling (планируется)

## Основные компоненты

### Bridge (bridge_docprep.py)

Мост между DocPrep и Docling Integration:
- Загрузка UNIT из Ready2Docling
- Валидация контракта
- Получение главного файла

### Config (config.py)

Конфигурация Docling:
- Загрузка YAML templates
- Построение PipelineOptions
- Маппинг route → InputFormat

### Runner (runner.py)

Тонкая обертка над DocumentConverter:
- Инициализация конвертера
- Retry механизм
- Batch обработка

### Pipeline (pipeline.py)

Основной orchestration:
- Координация всех компонентов
- Обработка UNIT
- Экспорт результатов
- Quarantine проблемных UNIT

### Exporters

- **JSON:** Сериализация через model_dump()
- **Markdown:** Структурированный экспорт с сохранением layout
- **MongoDB:** Сохранение в базу данных

## Важные замечания

### Гибридная архитектура

**Текущий этап (CPU-only):**
- Ядро: `docling-core` с CNN моделями на CPU
- Локальная обработка всех форматов

**Следующий этап (гибридная обработка):**
- Ядро: `docling-core` на CPU для основной обработки
- Внешние сервисы: Cloud.ru ML Foundation на GPU для ресурсоемких задач
  - Granite Docling - VLM для улучшения понимания
  - PaddleOCR_VLM - OCR для PDF через GPU

### Использование готового пакета

Мы используем готовый pip пакет `docling>=2.60.0`, а не пересобранный образ:

- ✅ Простота установки и обновлений
- ✅ Соответствие официальной документации
- ✅ Поддержка сообщества

### Поддержка русского языка

Требуется дополнительная настройка:

- Проверить параметры языка в PdfPipelineOptions
- Настроить Tesseract для русского языка (если используется OCR)
- Убедиться в правильной кодировке (UTF-8)

### План рефакторинга

См. [REFACTORING_AND_IMPROVEMENTS.md](REFACTORING_AND_IMPROVEMENTS.md) для детального плана:

**Текущие этапы:**
- Отладка обработки digital документов
- Критические исправления
- Улучшение экспорта

**Следующий этап:**
- Интеграция Cloud.ru Granite Docling (VLM)
- Интеграция Cloud.ru PaddleOCR_VLM (OCR)
- Оптимизация гибридной архитектуры

## Связанные компоненты

- **DocPrep:** `final_preprocessing/docprep/` - предобработка документов
- **Merger:** `final_preprocessing/docprep/engine/merger.py` - финальная сборка UNIT
- **Contract:** `final_preprocessing/docprep/core/contract.py` - генерация контрактов

## Версионирование

- **Docling:** >=2.60.0
- **Docling-core:** >=2.50.0
- **Contract version:** 1.0

## Контакты и поддержка

Для вопросов и предложений по улучшению документации, пожалуйста, создайте issue или обратитесь к команде разработки.

---

**Последнее обновление:** 2025-12-24

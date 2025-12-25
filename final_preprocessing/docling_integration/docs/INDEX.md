# Техническая документация Docling Integration

## Общие сведения

Docling Integration - это оркестрационный слой для обработки документов через IBM Docling, интегрированный с внутренней системой DocPrep.

### Архитектурные принципы
1. **Docling - двигатель, наш код - водитель** - не дублируем parsing логику
2. **Используем manifest из docprep** - не определяем тип файла заново
3. **Минимальная структура** - только orchestration, конфигурация, экспорт

## Структура документации

### 1. Основные документы
- [`README.md`](README.md) - Краткое описание и инструкции по использованию

### 2. Архитектурная документация
- [`ARCHITECTURE.md`](ARCHITECTURE.md) - Общая архитектура системы (включая гибридную архитектуру с внешними сервисами)
- [`COMPONENTS.md`](COMPONENTS.md) - Детальное описание компонентов
- [`CONTRACTS_AND_DATA.md`](CONTRACTS_AND_DATA.md) - Контрактная модель и потоки данных

### 3. Конфигурация и настройки
- [`CONFIGURATION.md`](CONFIGURATION.md) - Общая конфигурация системы (включая настройки внешних сервисов)
- [`BEST_PRACTICES.md`](BEST_PRACTICES.md) - Рекомендации по конфигурации

### 4. Внешние зависимости
- [`EXTERNAL_LIBRARIES_AND_MODELS.md`](EXTERNAL_LIBRARIES_AND_MODELS.md) - Внешние библиотеки и модели (включая Cloud.ru сервисы)
- [`requirements.txt`](../requirements.txt) - Зависимости системы

### 5. Анализ и улучшения
- [`REFACTORING_AND_IMPROVEMENTS.md`](REFACTORING_AND_IMPROVEMENTS.md) - План рефакторинга (включая интеграцию внешних сервисов)
- [`EARLY_DEVELOPMENT_COMPARISON.md`](EARLY_DEVELOPMENT_COMPARISON.md) - Сравнение с ранними наработками
- [`PERFORMANCE_AND_SCALING.md`](PERFORMANCE_AND_SCALING.md) - Производительность и масштабирование

### 6. Тестирование и диагностика
- [`TESTING_AND_DIAGNOSTICS.md`](TESTING_AND_DIAGNOSTICS.md) - Методики тестирования

### 7. Промежуточные документы и отчеты
- [`research/`](research/) - Промежуточные документы, планы и отчеты, созданные в процессе разработки

## Начало работы

Для начала работы с системой рекомендуется:
1. Ознакомиться с [`README.md`](README.md)
2. Просмотреть [`ARCHITECTURE.md`](ARCHITECTURE.md) - общая архитектура системы
3. Изучить [`COMPONENTS.md`](COMPONENTS.md) - детальное описание компонентов
4. Посмотреть [`CONFIGURATION.md`](CONFIGURATION.md) - настройка системы

## Поддержка и развитие

Система активно развивается и поддерживается. Для вопросов и предложений обращайтесь к ответственным за проект.
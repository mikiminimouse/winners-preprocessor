# Архивные компоненты Preprocessing

## Обзор
Этот документ описывает компоненты, которые были перемещены в архив в результате реорганизации проекта preprocessing 20 декабря 2025 года.

## Причины архивации
1. **Замена эталонным решением** - Компоненты заменены `final_preprocessing/docprep/`
2. **Упрощение архитектуры** - Устранение дублирующей функциональности
3. **Снижение поддержки** - Меньше кода для поддержки
4. **Четкое разделение ответственности** - preprocessing только для загрузки и синхронизации

## Архивные директории

### 1. preprocessing_router/
**Путь:** `/root/winners_preprocessor/archive/preprocessing_router/`

**Содержание:**
- Все файлы маршрутизации и обработки
- API endpoints
- Архивные механизмы
- Конфигурации
- Ядро системы обработки (core/)

**Причина архивации:**
Полностью заменен `final_preprocessing/docprep/`

### 2. preprocessing_llm/
**Путь:** `/root/winners_preprocessor/archive/preprocessing_llm/`

**Содержание:**
- Устаревшие компоненты LLM
- Модели и скрипты обработки естественного языка

**Причина архивации:**
Заменены современными решениями в docprep

### 3. preprocessing_cli/
**Путь:** `/root/winners_preprocessor/archive/preprocessing_cli/`

**Содержание:**
- Устаревшие CLI handlers:
  - test_handlers.py
  - step_handlers.py
  - stats_handlers.py
  - pipeline_handlers.py
  - merge_handlers.py
  - monitor_handlers.py

**Причина архивации:**
Функциональность перенесена в `final_preprocessing/docprep/cli/`

### 4. preprocessing_docs/
**Путь:** `/root/winners_preprocessor/archive/preprocessing_docs/`

**Содержание:**
Устаревшие документы:
- ARCHITECTURE_FLOW.md
- BUSINESS_STATUS_REPORT.md
- CLI_ANALYSIS_REPORT.md
- CLI_COMPLETE_GUIDE.md
- CLI_README.md
- COMPONENT_GUIDE.md
- FLOW_DOCUMENTATION.md
- FULL_PIPELINE_REPORT.md
- IMPLEMENTATION_STATUS.md
- PIPELINE_ANALYSIS.md
- PIPELINE_STATUS_REPORT.md
- PIPELINE_TEST_REPORT.md
- PIPELINE_TEST_SUMMARY.md
- PRD.md
- PROTOCOL_SYNC_COMPONENT.md
- REFACTORING_ANALYSIS.md
- SYNC_PROTOCOLS_ANALYSIS.md

**Причина архивации:**
Заменены новой документацией в `preprocessing/docs/`

### 5. preprocessing_test_reports/
**Путь:** `/root/winners_preprocessor/archive/preprocessing_test_reports/`

**Содержание:**
- BUGFIX_REPORT.md
- CLI_FIXES_REPORT.md
- CLI_FIXES_UPDATE.md
- MICROSERVICES_README.md
- TEST_20_UNITS_REPORT.md
- test_cli_automated.py
- test_output.log
- TEST_REPORT.md
- WORK_COMPLETION_REPORT.md

**Причина архивации:**
Временные отчеты и тесты, больше не актуальны

## Активные компоненты (остались в проекте)

### 1. preprocessing/sync_db/
**Назначение:** Синхронизация протоколов из удаленной MongoDB

**Функциональность:**
- Подключение к удаленной MongoDB через VPN
- Синхронизация коллекции protocols223.purchaseProtocol
- Создание уникальных unit_id для каждого протокола
- Предотвращение дубликатов
- Расширенная аналитика и метрики

### 2. preprocessing/downloader/
**Назначение:** Загрузка документов по URL

**Функциональность:**
- Проверка доступности zakupki.gov.ru через VPN
- Загрузка документов по URL из синхронизированных протоколов
- Параллельная загрузка файлов
- Обработка ошибок загрузки
- Детальная статистика

### 3. preprocessing/scheduler/
**Назначение:** Планирование задач

**Функциональность:**
- Запуск синхронизации по расписанию
- Запуск обработки документов по расписанию
- Интеграция с APScheduler

### 4. preprocessing/cli/
**Назначение:** Интерфейс командной строки

**Функциональность:**
- Упрощенное меню для синхронизации и загрузки
- Проверка инфраструктуры
- Служебные функции

## Восстановление архивных компонентов

### Процедура восстановления
```bash
# Восстановление router компонента
cp -r /root/winners_preprocessor/archive/preprocessing_router/* /root/winners_preprocessor/preprocessing/router/

# Восстановление CLI handlers
cp /root/winners_preprocessor/archive/preprocessing_cli/* /root/winners_preprocessor/preprocessing/cli/handlers/

# Восстановление документов
cp /root/winners_preprocessor/archive/preprocessing_docs/* /root/winners_preprocessor/preprocessing/docs/

# Восстановление тестов
cp /root/winners_preprocessor/archive/preprocessing_test_reports/* /root/winners_preprocessor/preprocessing/
```

### Предупреждения при восстановлении
1. **Конфликты зависимостей** - Архивные компоненты могут конфликтовать с новыми
2. **Устаревшие API** - Некоторые функции могут не работать с новыми версиями библиотек
3. **Проблемы совместимости** - Структура данных могла измениться

## Интеграция с final_preprocessing/docprep

### Текущий поток данных
1. **preprocessing/sync_db** → Синхронизирует протоколы в локальную MongoDB
2. **preprocessing/downloader** → Загружает файлы в `final_preprocessing/Data/YYYY-MM-DD/Input/`
3. **final_preprocessing/docprep** → Обрабатывает файлы из Input директории
4. **Результат** → Готовые документы в `final_preprocessing/Data/YYYY-MM-DD/Ready2Docling/`

### Преимущества нового подхода
1. **Единая точка обработки** - Все функции в одном месте
2. **Лучшая модульность** - Четкое разделение ответственности
3. **Расширенные возможности** - Улучшенная аналитика и мониторинг
4. **Проще поддерживать** - Меньше кода, меньше багов

## Заключение

Архивация устаревших компонентов позволила:
1. Упростить структуру проекта
2. Снизить нагрузку по поддержке
3. Повысить стабильность системы
4. Обеспечить четкое разделение ответственности

Все архивные компоненты сохранены для возможного восстановления, но их использование не рекомендуется.

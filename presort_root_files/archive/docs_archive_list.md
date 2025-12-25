# Список заархивированных документов

## Документы, перемещенные в архив 20 декабря 2025 года

### 1. Архив preprocessing_router
Полная копия устаревшего компонента preprocessing/router/, содержащего:
- Все файлы маршрутизации и обработки
- API endpoints
- Архивные механизмы
- Конфигурации
- Ядро системы обработки (core/)

### 2. Архив preprocessing_cli
Устаревшие CLI handlers:
- test_handlers.py
- step_handlers.py
- stats_handlers.py
- pipeline_handlers.py
- merge_handlers.py
- monitor_handlers.py

### 3. Архив preprocessing_llm
Компоненты LLM:
- Весь каталог preprocessing/llm/

### 4. Архив устаревших документов
Следующие документы из preprocessing/docs/ были заархивированы как устаревшие:

#### Документы по маршрутизации и обработке (router-related):
- ARCHITECTURE_FLOW.md
- COMPONENT_GUIDE.md
- FLOW_DOCUMENTATION.md
- PROTOCOL_SYNC_COMPONENT.md
- REFACTORING_ANALYSIS.md
- SYNC_PROTOCOLS_ANALYSIS.md

#### Документы по анализу и статусу:
- BUSINESS_STATUS_REPORT.md
- FULL_PIPELINE_REPORT.md
- IMPLEMENTATION_STATUS.md
- PIPELINE_ANALYSIS.md
- PIPELINE_STATUS_REPORT.md
- PIPELINE_TEST_REPORT.md
- PIPELINE_TEST_SUMMARY.md

#### Документы по CLI:
- CLI_ANALYSIS_REPORT.md
- CLI_COMPLETE_GUIDE.md
- CLI_README.md

#### Документы по требованиям:
- PRD.md

### 5. Причина архивации
Все эти компоненты и документы были заменены новым эталонным решением в final_preprocessing/docprep/, которое предоставляет:
- Улучшенную архитектуру
- Лучшую модульность
- Более четкое разделение ответственности
- Расширенные возможности мониторинга и аналитики

### 6. Активные компоненты (остаются в проекте)
Следующие компоненты остаются активными и необходимы для работы системы:
- preprocessing/sync_db/ - Синхронизация протоколов
- preprocessing/downloader/ - Загрузка документов
- preprocessing/scheduler/ - Планирование задач
- preprocessing/cli/ - Интерфейс командной строки
- preprocessing/core/ - Ядро системы

### 7. Восстановление
В случае необходимости все заархивированные компоненты могут быть восстановлены из директории archive/.

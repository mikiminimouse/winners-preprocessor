# Руководство по компонентам preprocessing

**Дата создания:** 2025-01-17  
**Версия:** 2.0 (после рефакторинга)

## Обзор

Модуль preprocessing состоит из следующих основных компонентов:

1. **Core** - общие компоненты (конфигурация, исключения, интерфейсы, события, состояния)
2. **Router** - обработка и классификация файлов
3. **Sync DB** - синхронизация протоколов из удаленной MongoDB
4. **Downloader** - загрузка документов с zakupki.gov.ru
5. **Scheduler** - планирование задач
6. **CLI** - интерактивный интерфейс командной строки

---

## Core компоненты

### Конфигурация (`core/config.py`)

Централизованная система конфигурации с типизированными настройками.

**Использование:**
```python
from preprocessing.core.config import get_config

config = get_config()

# Доступ к настройкам router
input_dir = config.router.input_dir
output_dir = config.router.output_dir

# Доступ к настройкам MongoDB
mongo_server = config.sync_db.remote_mongo.server
```

**Структура конфигурации:**
- `AppConfig` - главная конфигурация
  - `router: RouterConfig` - настройки router
  - `sync_db: SyncDBConfig` - настройки синхронизации
  - `downloader: DownloaderConfig` - настройки загрузки
  - `scheduler: SchedulerConfig` - настройки планировщика
  - `metrics: MetricsConfig` - настройки метрик

### Исключения (`core/exceptions.py`)

Иерархия кастомных исключений для лучшей обработки ошибок.

**Использование:**
```python
from preprocessing.core.exceptions import ProcessingError, SyncError

try:
    # обработка файла
    pass
except ProcessingError as e:
    print(f"Ошибка обработки: {e}")
    print(f"Контекст: {e.context}")
```

**Иерархия исключений:**
- `PreprocessingError` - базовое исключение
  - `ConfigurationError` - ошибка конфигурации
  - `SyncError` - ошибка синхронизации
  - `ConnectionError` - ошибка подключения
  - `DownloadError` - ошибка загрузки
  - `ProcessingError` - ошибка обработки
    - `FileDetectionError` - ошибка определения типа файла
    - `ArchiveExtractionError` - ошибка распаковки архива
    - `ConversionError` - ошибка конвертации
    - `ClassificationError` - ошибка классификации
    - `DistributionError` - ошибка распределения
  - `MetricsError` - ошибка метрик
  - `ManifestError` - ошибка manifest

### Интерфейсы (`core/interfaces.py`)

Протоколы для type checking и dependency injection.

**Использование:**
```python
from preprocessing.core.interfaces import ISyncService, SyncResult

def process_sync(sync_service: ISyncService) -> SyncResult:
    return sync_service.sync_daily_updates()
```

**Доступные интерфейсы:**
- `ISyncService` - интерфейс сервиса синхронизации
- `IDownloadService` - интерфейс сервиса загрузки
- `IProcessingService` - интерфейс сервиса обработки
- `IMongoConnector` - интерфейс подключения к MongoDB

### Состояния (`core/states.py`)

Единая модель состояний для протоколов, файлов и units.

**Использование:**
```python
from preprocessing.core.states import ProtocolState, validate_state_transition

current_state = ProtocolState.PENDING
new_state = ProtocolState.DOWNLOADED

if validate_state_transition(current_state, new_state, PROTOCOL_STATE_TRANSITIONS):
    # Переход разрешен
    pass
```

**Типы состояний:**
- `ProtocolState` - состояния протоколов (PENDING, DOWNLOADED, PROCESSING, PROCESSED, ERROR)
- `FileState` - состояния файлов (INPUT, PENDING, NORMALIZED, PROCESSED, ERROR)
- `UnitState` - состояния units (CREATED, DISTRIBUTED, NORMALIZED, PROCESSED, ERROR)

### События (`core/events.py`)

Event-driven система для связи компонентов.

**Использование:**
```python
from preprocessing.core.events import get_event_bus, ProtocolSyncedEvent, EventType

# Публикация события
event_bus = get_event_bus()
event = ProtocolSyncedEvent(protocol_id="123", unit_id="UNIT_ABC", date="2025-01-17")
event_bus.publish(event)

# Подписка на события
def handle_sync(event: ProtocolSyncedEvent):
    print(f"Protocol synced: {event.protocol_id}")

event_bus.subscribe(EventType.PROTOCOL_SYNCED, handle_sync)
```

---

## Router компонент

### Структура

```
router/
├── api.py              # FastAPI endpoints
├── core/
│   ├── processor.py    # FileProcessor - основная логика обработки
│   └── pipeline.py     # ProcessingPipeline - управление pipeline
├── file_detection.py   # Определение типа файла
├── file_classifier.py  # Классификация файлов
├── unit_distribution_new.py  # Распределение units
└── ...
```

### FileProcessor

Основной класс для обработки файлов.

**Использование:**
```python
from preprocessing.router.core.processor import FileProcessor
from pathlib import Path

processor = FileProcessor()
result = processor.process_file(Path("/path/to/file.pdf"))

print(result["status"])  # "processed" или "error"
print(result["unit_id"])  # "UNIT_..."
```

### ProcessingPipeline

Управление обработкой нескольких файлов.

**Использование:**
```python
from preprocessing.router.core.pipeline import ProcessingPipeline
from pathlib import Path

pipeline = ProcessingPipeline()

# Обработка всех файлов из директории
result = pipeline.process_directory(Path("/app/input"))

print(f"Обработано: {result['processed']}")
print(f"Ошибок: {result['failed']}")
```

---

## Sync DB компонент

### Структура

```
sync_db/
├── service.py      # SyncService - основной сервис синхронизации
├── connector.py    # MongoConnector - управление подключениями
└── ...
```

### MongoConnector

Управление подключениями к MongoDB с connection pooling.

**Использование:**
```python
from preprocessing.sync_db.connector import MongoConnector

connector = MongoConnector()

try:
    remote_client = connector.get_remote_client()
    local_client = connector.get_local_client()
    
    # Использование клиентов
    # ...
finally:
    connector.close()
```

### SyncService

Основной сервис синхронизации протоколов.

**Использование:**
```python
from preprocessing.sync_db.service import SyncService
from datetime import datetime

service = SyncService()

# Синхронизация за дату
result = service.sync_protocols_for_date(datetime(2025, 1, 17), limit=200)

print(f"Просмотрено: {result.scanned}")
print(f"Вставлено: {result.inserted}")
```

---

## Downloader компонент

### ProtocolDownloader

Сервис загрузки документов с zakupki.gov.ru.

**Использование:**
```python
from preprocessing.downloader.service import ProtocolDownloader

downloader = ProtocolDownloader()

# Обработка ожидающих протоколов
result = downloader.process_pending_protocols(limit=100)

print(f"Обработано: {result.processed}")
print(f"Скачано: {result.downloaded}")
```

---

## Scheduler компонент

### Структура

```
scheduler/
├── main.py       # Запуск планировщика
├── jobs.py       # Определение задач
└── config.py     # Конфигурация триггеров
```

### Jobs

Задачи, выполняемые по расписанию:
- `trigger_processing()` - запуск обработки документов
- `sync_protocols()` - синхронизация протоколов

**Настройка расписания:**
```env
SCHEDULE_CRON=*/15 * * * *        # Каждые 15 минут
SYNC_SCHEDULE_CRON=0 2 * * *      # Каждый день в 2:00
```

---

## Рекомендации по использованию

### 1. Использование конфигурации

Всегда используйте `get_config()` для доступа к настройкам:
```python
from preprocessing.core.config import get_config

config = get_config()
input_dir = config.router.input_dir
```

### 2. Обработка ошибок

Используйте кастомные исключения:
```python
from preprocessing.core.exceptions import ProcessingError

try:
    processor.process_file(file_path)
except ProcessingError as e:
    logger.error(f"Ошибка обработки: {e.message}", extra=e.context)
```

### 3. Использование интерфейсов

Используйте интерфейсы для dependency injection:
```python
from preprocessing.core.interfaces import ISyncService

def my_function(sync_service: ISyncService):
    result = sync_service.sync_daily_updates()
    return result
```

### 4. Публикация событий

Публикуйте события для слабой связанности:
```python
from preprocessing.core.events import get_event_bus, FileProcessedEvent

event_bus = get_event_bus()
event = FileProcessedEvent(unit_id="UNIT_ABC", file_path="/path/to/file", category="direct")
event_bus.publish(event)
```

---

**Документ подготовлен:** 2025-01-17  
**Версия:** 2.0


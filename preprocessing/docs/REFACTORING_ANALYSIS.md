# Анализ архитектуры и проблемы текущей реализации

**Дата создания:** 2025-01-17  
**Версия:** 1.0

## Обзор

Данный документ описывает выявленные проблемы в текущей архитектуре модуля preprocessing и предлагает направления для улучшения.

---

## 1. Проблемы разделения ответственности (Separation of Concerns)

### 1.1 Router компонент

**Проблема:** Router (`preprocessing/router/api.py`) смешивает несколько ответственностей:

1. **HTTP API endpoints** - обработка HTTP запросов
2. **Бизнес-логика обработки** - встроена в `process_file()` внутри api.py
3. **Работа с файловой системой** - прямое манипулирование файлами
4. **Работа с MongoDB** - прямые вызовы в коде обработки
5. **Сбор метрик** - встроен в процесс обработки

**Примеры проблемного кода:**
```python
# router/api.py - process_file() делает слишком много
def process_file(file_path: Path, ...) -> Dict[str, Any]:
    # Генерация unit_id
    unit_id = f"UNIT_{uuid.uuid4().hex[:16].upper()}"
    # Детекция типа файла
    file_type_result = detect_file_type(file_path)
    # Добавление метрик
    add_input_file_metric(file_path, file_type_result)
    # Классификация
    classification = classify_file(file_path, file_type_result)
    # Распределение
    distribution_result = distribute_unit_by_new_structure(...)
    # Сохранение метрик
    save_processing_metrics()
    return {...}
```

**Решение:** Выделить отдельные слои:
- `router/api.py` - только HTTP endpoints
- `router/core/processor.py` - основная логика обработки
- `router/core/pipeline.py` - управление pipeline обработки

### 1.2 Sync DB компонент

**Проблема:** SyncService смешивает:
1. Управление подключениями к MongoDB (remote и local)
2. Бизнес-логику синхронизации
3. Обработку данных (извлечение URLs, генерация unit_id)
4. Управление транзакциями

**Примеры проблемного кода:**
```python
# sync_db/service.py - все в одном классе
class SyncService:
    def _get_remote_mongo_client(self): ...  # Управление подключением
    def _get_local_mongo_client(self): ...   # Управление подключением
    def _extract_urls_from_attachments(self): ...  # Бизнес-логика
    def _create_protocol_document(self): ...  # Бизнес-логика
    def sync_protocols_for_date(self): ...    # Оркестрация всего процесса
```

**Решение:** Выделить:
- `sync_db/connector.py` - управление подключениями (connection pooling)
- `sync_db/transformer.py` - трансформация данных (extract URLs, create documents)
- `sync_db/service.py` - только оркестрация синхронизации

### 1.3 Downloader компонент

**Проблема:** ProtocolDownloader смешивает:
1. Управление HTTP сессиями
2. Логику скачивания файлов
3. Управление параллельностью
4. Обновление статусов в MongoDB

**Примеры проблемного кода:**
```python
# downloader/service.py
class ProtocolDownloader:
    def _download_file(self, url, output_path): ...  # Низкоуровневая загрузка
    def _process_single_protocol(self, protocol, collection): ...  # Бизнес-логика
    def process_pending_protocols(self): ...  # Оркестрация + параллельность
```

**Решение:** Выделить:
- `downloader/core/download_manager.py` - управление загрузками (retry, session management)
- `downloader/core/parallel_executor.py` - управление параллельностью
- `downloader/service.py` - только оркестрация процесса

### 1.4 Scheduler компонент

**Проблема:** main.py смешивает:
1. Конфигурацию планировщика
2. Определение задач
3. Запуск планировщика

**Примеры проблемного кода:**
```python
# scheduler/main.py - все в одном файле
scheduler = BlockingScheduler()

def trigger_processing(): ...  # Определение задачи
def sync_protocols(): ...       # Определение задачи

# Конфигурация задач встроена в main
scheduler.add_job(trigger_processing, ...)
scheduler.add_job(sync_protocols, ...)

if __name__ == "__main__":
    scheduler.start()  # Запуск
```

**Решение:** Выделить:
- `scheduler/jobs.py` - определение всех задач
- `scheduler/config.py` - конфигурация планировщика
- `scheduler/main.py` - только запуск планировщика

---

## 2. Сложности потока данных

### 2.1 Прямые зависимости между компонентами

**Проблема:** Компоненты напрямую зависят друг от друга, что усложняет тестирование и изменения.

**Примеры:**
```python
# scheduler/main.py - прямое импортирование и вызов
from sync_db.service import SyncService

def sync_protocols():
    sync_service = SyncService()
    result = sync_service.sync_daily_updates()
```

**Проблемы:**
- Невозможно легко заменить SyncService на mock для тестирования
- Сложно добавить промежуточную обработку (логирование, валидацию)
- Нарушение принципа инверсии зависимостей (Dependency Inversion Principle)

**Решение:** Использовать интерфейсы и dependency injection:
```python
# core/interfaces.py
class ISyncService(Protocol):
    def sync_daily_updates(self) -> SyncResult: ...

# scheduler/jobs.py
def sync_protocols(sync_service: ISyncService):
    result = sync_service.sync_daily_updates()
```

### 2.2 Отсутствие единой модели состояний

**Проблема:** Разные компоненты используют разные представления состояний:

1. **Sync DB:** протоколы имеют статус `pending` в MongoDB
2. **Downloader:** обновляет статус на `downloaded`
3. **Router:** не использует статусы протоколов напрямую
4. **Metrics:** хранит отдельную структуру метрик

**Примеры проблем:**
```python
# sync_db/service.py
doc_to_insert = {
    "status": "pending",  # Статус протокола
    ...
}

# downloader/service.py
collection.update_one(
    {"unit_id": unit_id},
    {"$set": {"status": "downloaded"}}  # Обновление статуса
)

# router/api.py - нет проверки статуса, работает с файлами напрямую
```

**Решение:** Создать единую модель состояний:
```python
# core/states.py
class ProtocolState(Enum):
    PENDING = "pending"
    DOWNLOADED = "downloaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    ERROR = "error"
```

### 2.3 Отсутствие событийной модели

**Проблема:** Компоненты не уведомляют друг друга о событиях явным образом.

**Текущая реализация:**
- Scheduler вызывает Router через HTTP
- Router вызывает Downloader напрямую
- Downloader обновляет MongoDB, но Router не знает об этом напрямую

**Проблемы:**
- Сложно добавить обработчики событий (логирование, мониторинг, алерты)
- Невозможно легко добавить промежуточную обработку
- Сложно отследить полный путь обработки документа

**Решение:** Использовать event-driven подход:
```python
# core/events.py
class ProtocolSyncedEvent:
    protocol_id: str
    unit_id: str
    date: datetime

class FileDownloadedEvent:
    unit_id: str
    file_count: int

# Компоненты публикуют события, другие компоненты подписываются
```

---

## 3. Проблемы обработки ошибок

### 3.1 Разрозненные исключения

**Проблема:** Используются стандартные исключения Python без контекста.

**Примеры:**
```python
# sync_db/service.py
except ConnectionFailure as e:
    print(f"❌ Ошибка подключения к удалённой MongoDB: {e}")
    return None

# downloader/service.py
except Exception as e:
    print(f"❌ Ошибка скачивания {url}: {e}")
    return False

# router/api.py
except Exception as e:
    import traceback
    error_traceback = traceback.format_exc()
    print(f"❌ Error processing file {file_path}: {e}")
```

**Проблемы:**
- Невозможно различить типы ошибок программно
- Отсутствует структурированная информация об ошибках
- Сложно реализовать retry механизм для конкретных типов ошибок
- Нет иерархии ошибок

**Решение:** Создать кастомные исключения:
```python
# core/exceptions.py
class PreprocessingError(Exception):
    """Базовая ошибка препроцессинга"""
    pass

class SyncError(PreprocessingError):
    """Ошибка синхронизации"""
    pass

class DownloadError(PreprocessingError):
    """Ошибка загрузки"""
    pass

class ProcessingError(PreprocessingError):
    """Ошибка обработки"""
    pass
```

### 3.2 Отсутствие retry механизма

**Проблема:** Нет автоматического повторного выполнения операций при временных ошибках.

**Примеры:**
- Сбой подключения к MongoDB - операция завершается с ошибкой
- Временная недоступность zakupki.gov.ru - загрузка файла завершается с ошибкой
- Сбой сети при HTTP запросе - операция завершается с ошибкой

**Решение:** Добавить retry механизм с exponential backoff:
```python
# core/retry.py
@retry(
    exceptions=(ConnectionError, TimeoutError),
    max_attempts=3,
    backoff_factor=2
)
def download_file(url: str) -> bytes:
    ...
```

### 3.3 Неструктурированное логирование

**Проблема:** Используется print() вместо структурированного логирования.

**Примеры:**
```python
# sync_db/service.py
print("✅ Подключение к локальной MongoDB успешно")
print(f"❌ Ошибка подключения к удалённой MongoDB: {e}")

# downloader/service.py
print(f"✅ Downloaded: {url} → {dest_path.name}")
print(f"❌ Error downloading {url}: {e}")
```

**Проблемы:**
- Невозможно фильтровать логи по уровню
- Сложно парсить логи для анализа
- Нет контекста выполнения (unit_id, session_id, etc.)

**Решение:** Использовать structured logging:
```python
import structlog

logger = structlog.get_logger()

logger.info("sync_completed",
    scanned=result.scanned,
    inserted=result.inserted,
    duration=result.duration
)
```

---

## 4. Дублирование кода

### 4.1 Дублирование конфигурации MongoDB

**Проблема:** Каждый компонент отдельно читает конфигурацию MongoDB.

**Примеры:**
```python
# sync_db/service.py
mongo_server = os.getenv("MONGO_SERVER", "192.168.0.46:8635")
mongo_user = os.getenv("MONGO_USER", "readProtocols223")

# router/mongo.py
MONGO_SERVER = os.environ.get("MONGO_SERVER")
MONGO_USER = os.environ.get("MONGO_USER")

# downloader/utils.py
MONGO_METADATA_DB = os.environ.get("MONGO_METADATA_DB", "docling_metadata")
```

**Решение:** Централизованная конфигурация:
```python
# core/config.py
@dataclass
class MongoConfig:
    server: str
    user: str
    password: str
    db: str
    # ...

class Config:
    remote_mongo: MongoConfig
    local_mongo: MongoConfig
```

### 4.2 Дублирование загрузки .env файла

**Проблема:** Каждый компонент отдельно загружает .env файл.

**Примеры:**
```python
# sync_db/service.py
def load_env_file():
    env_file = Path(__file__).parent.parent.parent / ".env"
    # ...

# cli/main.py
def load_env_file():
    env_file = Path(__file__).parent.parent.parent / ".env"
    # ...

# downloader/utils.py
def load_env_file():
    env_file = Path(__file__).parent.parent.parent / ".env"
    # ...
```

**Решение:** Единая функция загрузки в core/config.py

### 4.3 Дублирование работы с MongoDB клиентами

**Проблема:** Каждый компонент создает MongoDB клиентов по-своему.

**Примеры:**
```python
# sync_db/service.py
def _get_local_mongo_client(self):
    url = f"mongodb://{self.config.local_mongo_user}:..."
    client = MongoClient(url, ...)

# router/mongo.py
def get_mongo_metadata_client():
    url = f"mongodb://{MONGO_METADATA_USER}:..."
    client = MongoClient(url, ...)
```

**Решение:** Единый connection manager:
```python
# core/mongo_manager.py
class MongoConnectionManager:
    def get_client(self, config: MongoConfig) -> MongoClient:
        ...
```

---

## 5. Проблемы конфигурации

### 5.1 Разрозненная конфигурация

**Проблема:** Конфигурация разбросана по разным модулям.

**Файлы с конфигурацией:**
- `router/config.py` - конфигурация router
- `downloader/config.py` - конфигурация downloader
- `sync_db/service.py` - конфигурация sync_db (внутри класса)
- `scheduler/main.py` - конфигурация scheduler (в коде)

**Проблемы:**
- Невозможно легко увидеть все настройки системы
- Сложно валидировать конфигурацию
- Дублирование значений по умолчанию
- Нет типизации конфигурации

**Решение:** Единая точка конфигурации с валидацией:
```python
# core/config.py
@dataclass
class RouterConfig:
    input_dir: Path
    output_dir: Path
    # ...

@dataclass
class AppConfig:
    router: RouterConfig
    downloader: DownloaderConfig
    sync_db: SyncDBConfig
    scheduler: SchedulerConfig

def load_config() -> AppConfig:
    # Загрузка и валидация
    ...
```

### 5.2 Отсутствие валидации конфигурации

**Проблема:** Конфигурация не валидируется при старте приложения.

**Примеры проблем:**
- Невалидные пути директорий
- Отсутствующие обязательные переменные окружения
- Неправильные форматы данных (например, cron выражения)

**Решение:** Добавить валидацию через pydantic или dataclasses с валидаторами:
```python
# core/config.py
from pydantic import BaseSettings, validator

class SchedulerConfig(BaseSettings):
    schedule_cron: str
    
    @validator('schedule_cron')
    def validate_cron(cls, v):
        # Валидация cron выражения
        ...
```

---

## 6. Проблемы тестируемости

### 6.1 Сложность мокирования зависимостей

**Проблема:** Компоненты напрямую зависят от внешних систем (MongoDB, файловая система, HTTP).

**Примеры:**
```python
# sync_db/service.py
def _get_remote_mongo_client(self):
    client = MongoClient(url, ...)  # Прямая зависимость от MongoDB
    return client

# downloader/service.py
def _download_file(self, url, output_path):
    session = get_session()  # Прямая зависимость от HTTP
    response = session.get(url, ...)
```

**Проблемы:**
- Невозможно легко протестировать без реальных зависимостей
- Медленные тесты (требуют реальных подключений)
- Невозможно протестировать edge cases (например, сбой сети)

**Решение:** Использовать dependency injection и интерфейсы:
```python
# core/interfaces.py
class IMongoClient(Protocol):
    def find(self, query): ...

# sync_db/service.py
class SyncService:
    def __init__(self, mongo_client: IMongoClient):
        self.mongo_client = mongo_client
```

### 6.2 Отсутствие unit тестов

**Проблема:** Нет unit тестов для компонентов.

**Текущее состояние:**
- Есть только integration тесты в `tests/`
- Нет тестов для отдельных функций/классов
- Нет тестов для edge cases

**Решение:** Добавить unit тесты с использованием mocks:
```python
# tests/unit/test_sync_service.py
def test_sync_protocols_for_date(mock_mongo_client):
    service = SyncService(mock_mongo_client)
    result = service.sync_protocols_for_date(target_date)
    assert result.status == "success"
```

---

## 7. Проблемы производительности

### 7.1 Отсутствие connection pooling

**Проблема:** Каждый компонент создает новые подключения к MongoDB вместо переиспользования.

**Примеры:**
```python
# sync_db/service.py
def sync_protocols_for_date(self):
    self.local_client = self._get_local_mongo_client()  # Новое подключение
    # ...
    self.local_client.close()  # Закрытие после использования
```

**Проблемы:**
- Нагрузка на MongoDB (множество подключений)
- Задержки на установку подключений
- Нет переиспользования соединений

**Решение:** Использовать connection pooling:
```python
# core/mongo_manager.py
class MongoConnectionManager:
    _pool: Dict[str, MongoClient] = {}
    
    def get_client(self, config: MongoConfig) -> MongoClient:
        if config.server not in self._pool:
            self._pool[config.server] = MongoClient(config.url, maxPoolSize=10)
        return self._pool[config.server]
```

### 7.2 Последовательная обработка в Router

**Проблема:** Router обрабатывает файлы последовательно.

**Примеры:**
```python
# router/api.py
@app.post("/process_now")
async def process_now():
    for file_path in input_files:
        result = process_file(file_path)  # Последовательно
```

**Проблемы:**
- Медленная обработка большого количества файлов
- Не используется многопоточность/многопроцессность

**Решение:** Асинхронная/параллельная обработка:
```python
# router/api.py
@app.post("/process_now")
async def process_now():
    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(process_file_async(f)) for f in input_files]
    results = [t.result() for t in tasks]
```

---

## 8. Проблемы метрик и мониторинга

### 8.1 Разрозненные метрики

**Проблема:** Метрики хранятся в разных местах:
- `router/metrics.py` - метрики обработки
- `local_metrics/` - локальные метрики (JSON файлы)
- MongoDB - метрики в коллекции processing_metrics

**Проблемы:**
- Сложно получить общую картину
- Нет единого формата метрик
- Нет экспорта метрик для внешних систем

**Решение:** Единая система метрик:
```python
# core/metrics.py
class MetricsService:
    def record_event(self, event: Event):
        # Единая точка записи метрик
        ...
    
    def get_metrics(self, filters: Dict) -> Metrics:
        # Единая точка получения метрик
        ...
```

### 8.2 Отсутствие мониторинга в реальном времени

**Проблема:** Нет возможности отслеживать прогресс обработки в реальном времени.

**Текущее состояние:**
- Метрики сохраняются только после завершения обработки
- Нет уведомлений о событиях
- Нет дашборда для мониторинга

**Решение:** Добавить event streaming и мониторинг:
```python
# core/events.py
class EventStream:
    def publish(self, event: Event):
        # Публикация событий
        ...
    
    def subscribe(self, handler: Callable):
        # Подписка на события
        ...
```

---

## Приоритеты рефакторинга

### Высокий приоритет:
1. ✅ Централизованная конфигурация
2. ✅ Разделение ответственности компонентов
3. ✅ Улучшение обработки ошибок (кастомные исключения)
4. ✅ Устранение дублирования кода

### Средний приоритет:
5. ✅ Упрощение потока данных (интерфейсы, dependency injection)
6. ✅ Единая модель состояний
7. ✅ Retry механизм
8. ✅ Структурированное логирование

### Низкий приоритет:
9. ⚠️ Event-driven подход (можно отложить на потом)
10. ⚠️ Connection pooling (можно оптимизировать при необходимости)
11. ⚠️ Асинхронная обработка в Router (можно оптимизировать при необходимости)

---

## Резюме

Текущая архитектура имеет следующие основные проблемы:

1. **Смешение ответственностей** - компоненты делают слишком много разных вещей
2. **Прямые зависимости** - сложно тестировать и изменять
3. **Разрозненная конфигурация** - сложно управлять настройками
4. **Дублирование кода** - нарушение DRY принципа
5. **Слабая обработка ошибок** - нет структурированных исключений и retry механизма
6. **Отсутствие единых моделей** - разрозненные состояния и метрики

Предложенный план рефакторинга решает эти проблемы через:
- Выделение четких слоев ответственности
- Использование интерфейсов и dependency injection
- Централизованную конфигурацию и валидацию
- Единые модели состояний и событий
- Структурированную обработку ошибок
- Улучшенную тестируемость

---

**Документ подготовлен:** 2025-01-17  
**Версия:** 1.0


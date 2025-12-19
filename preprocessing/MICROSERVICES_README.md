# 🔧 Микросервисы препроцессинга

Быстрый гайд по использованию рефакторинных микросервисов.

## 📁 Структура

```
preprocessing/
├── downloader/          # Сервис скачивания документов
├── sync_db/             # Сервис синхронизации протоколов
├── router/              # Основной маршрутизатор
├── scheduler/           # Планировщик задач
└── cli.py               # Главный CLI интерфейс
```

## 🚀 Быстрый старт

### Синхронизация протоколов

```python
from sync_db.service import SyncService
from datetime import datetime, timedelta

# Создаём сервис
sync = SyncService()

# Синхронизация одной даты
result = sync.sync_protocols_for_date(datetime.now(), limit=200)

# Синхронизация за 2 недели (начальная загрузка)
start = datetime.now() - timedelta(days=14)
result = sync.sync_protocols_for_date_range(start, datetime.now(), limit=1000)

# Ежедневные обновления
result = sync.sync_daily_updates()

print(f"✅ Синхронизировано: {result.scanned} документов")
print(f"💾 Вставлено: {result.inserted}")
print(f"⏭️  Пропущено: {result.skipped_existing}")
```

### Скачивание документов

```python
from downloader.service import ProtocolDownloader
from downloader.utils import check_zakupki_health
from pathlib import Path

# Проверяем VPN
if not check_zakupki_health():
    print("❌ VPN не доступен!")
    exit(1)

# Создаём downloader
downloader = ProtocolDownloader(output_dir=Path('/app/input'))

# Запускаем загрузку
result = downloader.process_pending_protocols(limit=100)

print(f"✅ Обработано: {result.processed} протоколов")
print(f"💾 Скачано: {result.downloaded} документов")
print(f"❌ Ошибок: {result.failed}")
```

## 📦 Импорты

### SyncService

```python
from sync_db.service import SyncService, SyncResult, SyncConfig
```

**Методы:**
- `sync_protocols_for_date(date, limit)` - синхронизация одной даты
- `sync_protocols_for_date_range(start, end, limit)` - диапазон дат
- `sync_full_collection(limit)` - полная синхронизация
- `sync_daily_updates()` - ежедневные обновления

**Результат (SyncResult):**
- `status` - "success", "partial", or "error"
- `scanned` - просмотрено документов
- `inserted` - вставлено новых
- `skipped_existing` - пропущено дубликатов
- `errors_count` - количество ошибок
- `duration` - время выполнения (сек)

### ProtocolDownloader

```python
from downloader.service import ProtocolDownloader, DownloadResult
from downloader.utils import check_zakupki_health
```

**Методы:**
- `process_pending_protocols(limit)` - скачивание ожидающих протоколов

**Результат (DownloadResult):**
- `status` - "success", "partial", or "error"
- `processed` - обработано протоколов
- `downloaded` - скачано документов
- `failed` - количество ошибок
- `duration` - время выполнения (сек)

### Конфигурация

```python
# downloader конфиг
from downloader.config import (
    MAX_URLS_PER_PROTOCOL,      # 15 по умолчанию
    DOWNLOAD_HTTP_TIMEOUT,      # 120 сек
    DOWNLOAD_CONCURRENCY,       # 20 потоков
    PROTOCOLS_CONCURRENCY,      # 20 протоколов параллельно
    MONGO_METADATA_DB,
    MONGO_METADATA_PROTOCOLS_COLLECTION,
)

# sync_db конфиг
from sync_db.config import (
    BATCH_SIZE,                 # 1000 документов
    MAX_WORKERS,                # 4 потока
    REMOTE_COLLECTION,          # protocols223.purchaseProtocol
    LOCAL_COLLECTION,           # docling_metadata.protocols
)
```

## 🧪 Тестирование

### Проверка импортов

```bash
cd preprocessing
python -c "
from downloader.service import ProtocolDownloader
from sync_db.service import SyncService
from downloader.utils import check_zakupki_health
print('✅ Все импорты работают!')
"
```

### Запуск CLI

```bash
cd preprocessing
source activate_venv.sh
python run_cli.py

# Выберите опцию:
# 1 - Синхронизация протоколов
# 2 - Скачивание протоколов
# 27 - Проверка инфраструктуры
```

## ⚙️ Переменные окружения

Обязательные переменные в `.env`:

```env
# MongoDB локальная
MONGO_METADATA_SERVER=localhost:27017
MONGO_METADATA_USER=docling_user
MONGO_METADATA_PASSWORD=password
MONGO_METADATA_DB=docling_metadata

# MongoDB удалённая (синхронизация)
MONGO_SERVER=192.168.0.46:8635
MONGO_USER=readProtocols223
MONGO_PASSWORD=your_password

# Директории
INPUT_DIR=/app/input
OUTPUT_DIR=/app/output

# Параметры скачивания
MAX_URLS_PER_PROTOCOL=15
DOWNLOAD_HTTP_TIMEOUT=120
```

## 🐛 Отладка

### Проверка MongoDB подключений

```python
from sync_db.service import SyncService

sync = SyncService()
result = sync._get_remote_mongo_client()
if result:
    print("✅ Удалённая MongoDB доступна")
else:
    print("❌ Ошибка подключения к удалённой MongoDB")

result = sync._get_local_mongo_client()
if result:
    print("✅ Локальная MongoDB доступна")
else:
    print("❌ Ошибка подключения к локальной MongoDB")
```

### Проверка VPN

```python
from downloader.utils import check_zakupki_health

if check_zakupki_health():
    print("✅ zakupki.gov.ru доступен")
    print("✅ VPN работает")
else:
    print("❌ VPN не работает или сайт недоступен")
```

## 📚 Дополнительно

- Полное описание см. в [REFACTORING_COMPLETE.md](../REFACTORING_COMPLETE.md)
- Инструкция по тестированию: [TESTING_CLI.md](../TESTING_CLI.md)

---

**✅ Версия:** 1.0 (после рефакторинга)  
**📅 Дата:** 2025-12-17


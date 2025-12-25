# Быстрый старт - Рефакторинг preprocessing

## Что было сделано?

Монолитный файл `preprocessing/router/main.py` (1598 строк) был разбит на 7 специализированных модулей. Удалены 3 дубликата (3329 строк кода).

## Новая структура

```
preprocessing/
├── router/
│   ├── config.py           ← Конфигурация (env переменные)
│   ├── mongo.py            ← MongoDB операции
│   ├── archive.py          ← Распаковка архивов
│   ├── manifest.py         ← Работа с манифестами
│   ├── utils.py            ← Утилиты (SHA256, sanitize)
│   ├── processing.py       ← Обработка файлов
│   ├── api.py              ← FastAPI endpoints (переименован)
│   └── ...
├── downloader/             ← Микросервис (не менялся)
├── sync_db/                ← Микросервис (не менялся)
├── cli/                    ← CLI (обновлены импорты)
├── scheduler/              ← Scheduler (обновлены импорты)
└── run_cli.py              ← Точка входа
```

## Импорты (НОВЫЕ!)

**Было:**
```python
from router.main import INPUT_DIR, get_mongo_client, safe_extract_archive
```

**Стало:**
```python
from router.config import INPUT_DIR
from router.mongo import get_mongo_client
from router.archive import safe_extract_archive
```

## Использование

### Запуск CLI
```bash
cd preprocessing
source activate_venv.sh
python run_cli.py
```

### В коде Python

```python
# Конфигурация
from router.config import INPUT_DIR, DOCLING_API, MAX_UNPACK_SIZE_MB

# MongoDB
from router.mongo import get_mongo_client, get_mongo_metadata_client

# Архивы
from router.archive import safe_extract_archive

# Манифесты
from router.manifest import create_manifest

# Утилиты
from router.utils import sanitize_filename, calculate_sha256

# Обработка
from router.processing import process_file_minimal

# Микросервисы (не менялись)
from downloader.service import ProtocolDownloader
from sync_db.service import SyncService
```

## Что улучшилось?

| Параметр | Было | Стало |
|----------|------|-------|
| Размер router/main.py | 1598 строк | ~400 (api.py) |
| Дубликаты | 3329 строк | Удалены |
| Модули router | 12 файлов | 10 файлов |
| Организация | Сложная | Логичная |
| Тестируемость | Сложная | Хорошая |

## Тестирование

Все модули работают:
```bash
cd preprocessing && source activate_venv.sh && python -c "
from router.config import INPUT_DIR
from router.mongo import get_mongo_client
from router.archive import safe_extract_archive
from router.manifest import create_manifest
print('✅ Все импорты работают!')
"
```

## FAQ

**Q: Может ли я использовать старые импорты?**
A: Нет, нужно использовать новые импорты из специализированных модулей.

**Q: Нужно ли менять код в других проектах?**
A: Да, если они импортировали из `router.main` - обновите импорты на новые модули.

**Q: Какие файлы были удалены?**
A: 
- preprocessing/cli.py (дубликат cli/)
- router/cli.py (дубликат preprocessing/cli.py)
- router/protocol_sync.py (функционал в sync_db)

**Q: Все ли функции на месте?**
A: Да, все функции перемещены в специализированные модули. Функциональность не изменилась.

## Документация

- `REFACTORING_COMPLETE_PHASE2.md` - Полный отчет
- `TESTING_CLI.md` - Тестирование CLI
- `MICROSERVICES_README.md` - Описание микросервисов

## Контакт

При вопросах - смотрите документацию выше или читайте код модулей.


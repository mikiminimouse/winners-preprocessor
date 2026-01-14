# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Проект: Receiver - Система синхронизации и загрузки протоколов закупок

Система для автоматической синхронизации протоколов закупок из удаленной MongoDB и загрузки связанных документов с zakupki.gov.ru через VPN.

## Основные команды

### Разработка и тестирование

```bash
# Запуск интерактивного CLI
cd /root/winners_preprocessor/final_preprocessing/receiver
python run_cli.py

# Запуск всех тестов
python -m pytest tests/ -v

# Запуск unit тестов
python -m pytest tests/test_*.py -v

# Запуск интеграционных тестов
python -m pytest tests/integration/ -v

# Запуск конкретного теста
python -m pytest tests/test_enhanced_components.py::test_imports -v
```

### Синхронизация протоколов (sync_db)

```bash
# Синхронизация за одну дату
python -m receiver.sync_db.enhanced_service sync-date --date 2025-03-19

# Синхронизация за диапазон дат
python -m receiver.sync_db.enhanced_service sync-range \
  --start-date 2025-03-01 --end-date 2025-03-19

# Ежедневное обновление (вчерашний день)
python -m receiver.sync_db.enhanced_service sync-daily

# Полная синхронизация за последние N дней
python -m receiver.sync_db.enhanced_service sync-full --days 30

# С ограничением количества записей
python -m receiver.sync_db.enhanced_service sync-date --date 2025-03-19 --limit 100
```

### Загрузка документов (downloader)

```bash
# Загрузка всех ожидающих протоколов
python -m receiver.downloader.enhanced_service

# Загрузка с лимитом
python -m receiver.downloader.enhanced_service --limit 50

# Загрузка в пользовательскую директорию
python -m receiver.downloader.enhanced_service --output-dir /custom/path

# С подробным логированием
python -m receiver.downloader.enhanced_service --verbose
```

### Проверка инфраструктуры

```bash
# Комплексная проверка здоровья системы
python -m receiver.sync_db.health_checks --check all

# Проверка VPN подключения
python -m receiver.sync_db.health_checks --check vpn

# Проверка удаленной MongoDB
python -m receiver.sync_db.health_checks --check remote-mongo

# Проверка локальной MongoDB
python -m receiver.sync_db.health_checks --check local-mongo

# С подробным выводом
python -m receiver.sync_db.health_checks --check all --verbose
```

### WebUI

```bash
# Запуск веб-интерфейса для мониторинга
cd /root/winners_preprocessor
python3 -m receiver.webui.app

# Или в фоновом режиме
nohup python3 -m receiver.webui.app > /tmp/webui.log 2>&1 &

# WebUI доступен по адресу: http://localhost:7860
```

### Docker

```bash
# Запуск всех сервисов
docker-compose up -d

# Проверка статуса
docker-compose ps

# Просмотр логов
docker-compose logs -f

# Остановка сервисов
docker-compose down
```

## Архитектура системы

### Компоненты высокого уровня

Система состоит из 4 основных компонентов, образующих pipeline обработки:

1. **sync_db** - Синхронизация протоколов из удаленной MongoDB в локальную
2. **downloader** - Загрузка документов по URL из протоколов
3. **scheduler** - Планирование и автоматический запуск задач
4. **webui** - Веб-интерфейс для мониторинга и управления

### Поток данных

```
Удаленная MongoDB (VPN)
  ↓ [sync_db]
Локальная MongoDB (протоколы + метаданные)
  ↓ [downloader]
final_preprocessing/Data/YYYY-MM-DD/Input/
  ↓ [final_preprocessing/docprep]
final_preprocessing/Data/YYYY-MM-DD/Ready2Docling/
```

### Ключевые модули

**core/** - Ядро системы
- `config.py` - Централизованная конфигурация через dataclasses (MongoConfig, RouterConfig, SyncDBConfig, DownloaderConfig, etc.)
- `interfaces.py` - Базовые интерфейсы и абстрактные классы
- `exceptions.py` - Кастомные исключения (ConnectionError, SyncError, etc.)
- `events.py` - Система событий для координации компонентов
- `states.py` - Машина состояний обработки документов
- `metrics.py` - Сбор и хранение метрик

**sync_db/** - Компонент синхронизации
- `enhanced_service.py` - Основной сервис синхронизации с EnhancedSyncService и EnhancedSyncResult
- `health_checks.py` - Проверки здоровья VPN, MongoDB, инфраструктуры
- `analytics.py` - Аналитика и статистика синхронизации
- `connector.py` - Менеджеры подключений к MongoDB
- `manager.py` - Управление жизненным циклом синхронизации

**downloader/** - Компонент загрузки
- `enhanced_service.py` - Основной сервис загрузки с DownloadResult
- `file_manager.py` - Управление файлами и директориями
- `status_tracker.py` - Отслеживание статусов загрузки
- `meta_generator.py` - Генерация метаданных для протоколов
- `models.py` - Модели данных (DownloadRequest, etc.)
- `utils.py` - Вспомогательные функции (sanitize_filename, check_zakupki_health)

**cli/** - Командная строка
- `main.py` - Основной класс PreprocessingTestCLI с интерактивным меню
- `handlers/load_handlers.py` - Обработчики для синхронизации и загрузки
- `handlers/utils_handlers.py` - Служебные обработчики (cleanup, infrastructure check)
- `config.py` - Конфигурация меню и маршрутизация команд

**webui/** - Веб-интерфейс Gradio
- `app.py` - Основное приложение Gradio
- `health_panel.py` - Панель Health Check с детальной диагностикой
- `charts.py` - Визуализация метрик и статистики
- `controls.py` - Элементы управления синхронизацией и загрузкой
- `tabs/` - Вкладки интерфейса (Dashboard, Configuration, Sync, Download, Health)

### VPN и безопасность

- **vpn_utils.py** - Критический модуль для работы через VPN
  - `ensure_vpn_connected()` - Автоматическое подключение к VPN
  - `check_remote_mongo_vpn_access()` - Проверка доступа к удаленной MongoDB
  - `check_zakupki_access()` - Проверка доступа к zakupki.gov.ru
  - `is_openvpn_running()`, `is_vpn_interface_up()`, `check_vpn_routes()` - Диагностика VPN
- Все подключения к удаленной MongoDB требуют VPN (192.168.0.46:8635)
- SSL сертификат для MongoDB: `/root/winners_preprocessor/final_preprocessing/receiver/certs/sber2.crt`
- VPN конфигурация: `/root/winners_preprocessor/final_preprocessing/receiver/vitaly_bychkov.ovpn`

### Система конфигурации

Централизованная конфигурация в `core/config.py`:
- Все настройки загружаются из переменных окружения через `load_env_file()`
- Используются dataclasses для типизации: `MongoConfig`, `SyncDBConfig`, `DownloaderConfig`, `RouterConfig`, `MetricsConfig`
- Глобальный экземпляр доступен через `get_config()`
- Валидация конфигурации при инициализации через `AppConfig.validate()`

### MongoDB архитектура

**Удаленная MongoDB** (через VPN, read-only):
- Сервер: 192.168.0.46:8635
- База: protocols223
- Коллекция: purchaseProtocol
- Аутентификация: SSL + user/password
- Используется для: Чтения исходных протоколов закупок

**Локальная MongoDB** (localhost):
- Сервер: localhost:27018
- База: docling_metadata
- Коллекции:
  - `protocols` - Синхронизированные протоколы с unit_id
  - `manifests` - Манифесты обработанных документов
  - `processing_metrics` - Метрики обработки
- Используется для: Хранения метаданных, координации компонентов

### Обработка ошибок

- Все компоненты используют кастомные исключения из `core/exceptions.py`
- `EnhancedSyncService` и `EnhancedProtocolDownloader` возвращают детальные результаты с metrics
- Health checks в `sync_db/health_checks.py` проверяют VPN, MongoDB, диск, Docker
- Retry логика для временных сбоев подключения
- Подробное логирование всех операций с уровнями INFO/WARNING/ERROR/DEBUG

## Переменные окружения

Файл `.env` должен находиться в `/root/winners_preprocessor/final_preprocessing/receiver/.env`

### Критические переменные

```bash
# Удаленная MongoDB (через VPN)
MONGO_SERVER=192.168.0.46:8635
MONGO_USER=readProtocols223
MONGO_PASSWORD=<пароль>
MONGO_SSL_CERT=/root/winners_preprocessor/final_preprocessing/receiver/certs/sber2.crt
MONGO_PROTOCOLS_DB=protocols223
MONGO_PROTOCOLS_COLLECTION=purchaseProtocol

# Локальная MongoDB
MONGO_METADATA_SERVER=localhost:27018
LOCAL_MONGO_SERVER=localhost:27018
MONGO_METADATA_USER=admin
MONGO_METADATA_PASSWORD=<пароль>
MONGO_METADATA_DB=docling_metadata

# VPN конфигурация
VPN_ENABLED_REMOTE_MONGO=true
VPN_ENABLED_ZAKUPKI=true
VPN_REQUIRED=true
VPN_CONFIG_FILE=/root/winners_preprocessor/final_preprocessing/receiver/vitaly_bychkov.ovpn
ZAKUPKI_URL=https://zakupki.gov.ru

# Директории обработки
INPUT_DIR=/root/winners_preprocessor/final_preprocessing/Data
OUTPUT_DIR=/root/winners_preprocessor/final_preprocessing/Data
```

### Опциональные переменные

```bash
# Лимиты загрузки
MAX_URLS_PER_PROTOCOL=15
DOWNLOAD_HTTP_TIMEOUT=120
DOWNLOAD_CONCURRENCY=20
PROTOCOLS_CONCURRENCY=20

# Параметры синхронизации
SYNC_BATCH_SIZE=1000
SYNC_MAX_WORKERS=4

# Scheduler
SCHEDULE_CRON=*/15 * * * *
SYNC_SCHEDULE_CRON=0 2 * * *
LOG_LEVEL=INFO
```

## Типичные задачи разработки

### Добавление нового типа вложений в протоколе

1. Изучить структуру протокола в `sync_db/enhanced_service.py` метод `_create_unit()`
2. Добавить обработку нового поля в `_extract_attachment_urls()`
3. Обновить статистику в `statistics['attachment_types']`
4. Добавить тесты в `tests/test_sync_integration.py`

### Изменение логики загрузки файлов

1. Модифицировать `downloader/enhanced_service.py` класс `EnhancedProtocolDownloader`
2. Обновить `FileManager` в `downloader/file_manager.py` для управления файлами
3. Проверить интеграцию с `meta_generator.py` для генерации метаданных
4. Обновить тесты в `tests/test_complete_pipeline.py`

### Добавление новой проверки здоровья

1. Добавить функцию в `sync_db/health_checks.py`
2. Зарегистрировать в `AVAILABLE_CHECKS` словаре
3. Интегрировать в WebUI через `webui/health_panel.py`
4. Добавить в CLI через `cli/handlers/utils_handlers.py`

### Расширение WebUI

1. Создать новую вкладку в `webui/tabs/`
2. Добавить обработчики в `webui/handlers/`
3. Интегрировать в `webui/app.py` через `gr.TabbedInterface`
4. Использовать `webui/charts.py` для визуализации данных

## Интеграция с final_preprocessing/docprep

Система receiver подготавливает данные для следующего этапа обработки:

1. **sync_db** синхронизирует протоколы в локальную MongoDB
2. **downloader** сохраняет файлы в `final_preprocessing/Data/YYYY-MM-DD/Input/`
3. **docprep** (отдельный компонент) читает из Input/ и обрабатывает документы
4. Результат попадает в `final_preprocessing/Data/YYYY-MM-DD/Ready2Docling/`

Структура директорий должна строго соблюдаться для корректной работы pipeline.

## Важные замечания

### VPN критичен для работы
- Удаленная MongoDB доступна только через VPN
- zakupki.gov.ru также требует VPN для корректной работы
- Всегда проверяйте VPN перед операциями: `python -m receiver.sync_db.health_checks --check vpn`

### Уникальность протоколов
- Система использует `unit_id = f"{purchaseNoticeNumber}_{source}"` для уникальной идентификации
- Дубликаты по `purchaseNoticeNumber` + `source` пропускаются автоматически
- MongoDB индекс на `unit_id` обеспечивает быструю проверку

### Параллельная обработка
- `DOWNLOAD_CONCURRENCY=20` - параллельных загрузок файлов
- `PROTOCOLS_CONCURRENCY=20` - параллельных обработок протоколов
- Настройки в `.env` или через `DownloaderConfig`

### Форматы дат
- Все даты в формате ISO: `YYYY-MM-DD`
- Диапазоны дат включают обе границы
- "Вчерашний день" - основной режим ежедневной синхронизации

### Тестирование
- Unit тесты мокают MongoDB и VPN подключения
- Интеграционные тесты требуют реального VPN и MongoDB
- Тесты в `tests/integration/` могут быть долгими (реальная загрузка файлов)

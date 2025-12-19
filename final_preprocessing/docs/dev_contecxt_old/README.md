# Preprocessing стек

## Описание

Preprocessing стек - система предобработки документов перед OCR обработкой.

## Компоненты

- **router/** - FastAPI сервис для классификации и маршрутизации файлов
- **scheduler/** - APScheduler сервис для автоматического запуска обработки
- **tests/** - тесты
- **docs/** - документация

## Технологии

- FastAPI для Router API
- APScheduler для планирования задач
- LibreOffice для конвертации DOC→DOCX
- Docker Compose для оркестрации

## Функциональность Router

1. Определение типа файла (magic bytes + mimetype)
2. Распаковка архивов (ZIP, RAR)
3. Классификация PDF (текстовый слой vs скан)
4. Конвертация DOC→DOCX (через LibreOffice)
5. Создание manifest.json с метаданными
6. Нормализация unit'ов для OCR_VL

## Быстрый старт

### Запуск через Docker Compose

```bash
cd preprocessing
docker-compose up -d
```

### Проверка статуса

```bash
docker-compose ps
docker-compose logs -f router
docker-compose logs -f scheduler
```

### Тестирование с CLI

#### Локальный запуск
```bash
cd preprocessing
python3 run_cli.py
```

#### Docker запуск
```bash
cd preprocessing
docker-compose run --rm cli
```

#### Автоматическое тестирование
```bash
cd preprocessing
python3 test_cli_basic.py
```

## API Endpoints (Router)

- `GET /health` - проверка здоровья сервиса
- `POST /upload` - загрузка файла для обработки
- `POST /webhook` - webhook для внешних триггеров
- `POST /process_now` - немедленная обработка всех файлов
- `GET /status/{unit_id}` - статус обработки unit'а
- `GET /protocols/{date}` - получение протоколов за дату
- `POST /download_protocols/{date}` - скачивание протоколов

## CLI для тестирования и управления

Универсальный CLI с **27 пунктами меню** для полного управления препроцессингом:

### Категории функций CLI

#### 1. ЗАГРУЗКА И ПОДГОТОВКА ДАННЫХ
- Синхронизация протоколов из MongoDB
- Скачивание документов через VPN
- Проверка входных файлов

#### 2. ПОШАГОВАЯ ОБРАБОТКА
- **Шаг 1:** Сканирование и детекция типов файлов
- **Шаг 2:** Классификация по категориям (direct/convert/extract/special)
- **Шаг 3:** Проверка дубликатов (SHA256 хэши)
- **Шаг 4:** Определение mixed units
- **Шаг 5:** Распределение по pending директориям
- **Полная обработка:** Все шаги последовательно

#### 3. РАСШИРЕННАЯ СТАТИСТИКА
- Просмотр структуры pending директорий
- Детальная статистика по категориям и типам файлов
- Отчет по обработанным units

#### 4. MERGE И ФИНАЛИЗАЦИЯ
- Merge (DRY RUN) - планирование операций
- Merge (РЕАЛЬНЫЙ) - выполнение merge в ready_docling

#### 5. ТЕСТИРОВАНИЕ И МОНИТОРИНГ
- Тестирование отдельных этапов
- Полное тестирование pipeline
- Просмотр метрик и логов
- Проверка инфраструктуры

### Запуск CLI

#### Через Docker
```bash
cd preprocessing
docker-compose run --rm cli
```

#### Локально
```bash
cd preprocessing
python3 run_cli.py
```

### Документация CLI

- [Полное руководство CLI](CLI_COMPLETE_GUIDE.md) - детальное описание всех функций
- [Документация Flow](FLOW_DOCUMENTATION.md) - полный pipeline препроцессинга
- [Анализ CLI систем](CLI_ANALYSIS_REPORT.md) - технический анализ интеграции

## Документация

- [Architecture](ARCHITECTURE.md)
- [Pipeline Analysis](PIPELINE_ANALYSIS.md)
- [Full Pipeline Report](FULL_PIPELINE_REPORT.md)


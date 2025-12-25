# Обзор проекта Winners Preprocessor

## Описание проекта

Winners Preprocessor - система обработки документов для извлечения текста и структуры из различных форматов документов (PDF, DOC, DOCX, изображения) с использованием OCR и анализа макета.

## Архитектура системы

Проект состоит из двух основных стеков:

### 1. OCR_VL стек
**Назначение:** OCR обработка документов и генерация Markdown/JSON

**Технологии:**
- PaddleOCR-VL (офлайн-образ с предзагруженными моделями)
- FastAPI для REST API
- Docker для контейнеризации
- Cloud.ru Object Storage для хранения результатов

**Компоненты:**
- `ocr_vl/service/` - основной Docker сервис
- `ocr_vl/tests/` - тесты
- `ocr_vl/docs/` - документация

### 2. Preprocessing стек
**Назначение:** Предобработка документов перед OCR (классификация, распаковка, конвертация)

**Технологии:**
- FastAPI для Router API
- APScheduler для планирования задач
- LibreOffice для конвертации DOC→DOCX
- Docker Compose для оркестрации

**Компоненты:**
- `preprocessing/router/` - классификация и маршрутизация файлов
- `preprocessing/scheduler/` - автоматический запуск обработки
- `preprocessing/tests/` - тесты
- `preprocessing/docs/` - документация

## Поток обработки документов

```
Входной файл (PDF/DOC/DOCX/изображение)
    ↓
Preprocessing (Router)
    ├─ Определение типа файла
    ├─ Распаковка архивов (если нужно)
    ├─ Конвертация DOC→DOCX
    └─ Создание manifest.json
    ↓
OCR_VL Service
    ├─ OCR обработка (PaddleOCR-VL)
    ├─ Анализ макета (PP-DocLayoutV2)
    └─ Генерация Markdown/JSON
    ↓
Результаты
    ├─ Локальное сохранение
    └─ Загрузка в Cloud.ru S3 (опционально)
```

## История разработки

### Изначальная попытка: Docling
Первоначально использовалась библиотека Docling для обработки документов. Однако были выявлены ограничения в качестве OCR для русских документов.

### Альтернативная попытка: Granite
Пробовали использовать Granite VLM для извлечения метаданных и обработки документов. Решение не подошло для основной задачи.

### Текущее решение: PaddleOCR-VL
Перешли на PaddleOCR-VL - специализированное решение для OCR с поддержкой русского языка и анализа макета документов.

**Преимущества:**
- Высокое качество OCR для русских документов
- Встроенный анализ макета (PP-DocLayoutV2)
- Офлайн-образ с предзагруженными моделями
- Генерация структурированного Markdown

## Структура проекта

```
winners_preprocessor/
├── ocr_vl/              # OCR_VL стек
│   ├── service/         # Docker сервис
│   ├── tests/          # Тесты
│   ├── docs/           # Документация
│   └── scripts/        # Скрипты сборки/деплоя
│
├── preprocessing/       # Preprocessing стек
│   ├── router/         # Router сервис
│   ├── scheduler/      # Scheduler сервис
│   ├── tests/          # Тесты
│   ├── docs/           # Документация
│   └── docker-compose.yml
│
├── archive/            # Архив устаревших компонентов
│   ├── docling/        # Старая Docling попытка
│   ├── granite/        # Старая Granite попытка
│   ├── cloudru_old/    # Старые Cloud.ru интеграции
│   └── pilots/         # Пилотные версии
│
├── shared/             # Общие компоненты
│   ├── scripts/        # Общие скрипты
│   ├── configs/        # Общие конфиги
│   └── utils/          # Общие утилиты
│
├── data/               # Данные проекта
│   ├── input/          # Входные файлы
│   ├── output/         # Результаты обработки
│   ├── temp/           # Временные файлы
│   └── test_images/    # Тестовые изображения
│
└── docs/               # Общая документация
    └── cursor_docker_paddleocr_vl.md  # История разработки
```

## Быстрый старт

### OCR_VL сервис

```bash
cd ocr_vl/service
docker build -t paddleocr-vl-service:latest .
docker run -p 8081:8081 paddleocr-vl-service:latest
```

Подробнее: [ocr_vl/docs/README.md](ocr_vl/docs/README.md)

### Preprocessing стек

```bash
cd preprocessing
docker-compose up -d
```

Подробнее: [preprocessing/docs/README.md](preprocessing/docs/README.md)

## Документация

- [OCR_VL документация](ocr_vl/docs/)
- [Preprocessing документация](preprocessing/docs/)
- [История разработки](docs/cursor_docker_paddleocr_vl.md)
- [Архив устаревших компонентов](archive/)

## Лицензия

Проект для внутреннего использования.


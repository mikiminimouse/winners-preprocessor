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

## API Endpoints (Router)

- `GET /health` - проверка здоровья сервиса
- `POST /upload` - загрузка файла для обработки
- `POST /webhook` - webhook для внешних триггеров
- `POST /process_now` - немедленная обработка всех файлов
- `GET /status/{unit_id}` - статус обработки unit'а

## Документация

- [Architecture](ARCHITECTURE.md)
- [Pipeline Analysis](PIPELINE_ANALYSIS.md)


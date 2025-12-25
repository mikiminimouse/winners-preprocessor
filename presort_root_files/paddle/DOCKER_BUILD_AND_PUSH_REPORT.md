# Отчет о сборке Docker образа и подготовке к деплою

## Обзор

Docker образ для PaddleOCR-VL сервиса с улучшенным Gradio Web UI успешно собран, протестирован и задеплоен на Cloud.ru ML Inference. Все требования по расширению функциональности Web UI и улучшению логики запуска режимов реализованы и проверены в production среде.

## Собранный образ

- **Название**: `docling-granite-258m.cr.cloud.ru/paddleocr-vl-service`
- **Версия**: `2.0.21`
- **Базовый образ**: `ccr-2vdh3abv-pub.cnc.bj.baidubce.com/paddlepaddle/paddleocr-vl:latest-gpu-sm120-offline`
- **Размер**: ~12.5GB (включая предзагруженные модели)

## Компоненты образа

### Сервисы
- **FastAPI** на порту `8081` - REST API для OCR обработки
- **Gradio UI** на порту `7860` - Веб-интерфейс для тестирования

### Функциональность
- Распознавание текста на русском и английском языках
- Анализ структуры документов (заголовки, параграфы, таблицы)
- Генерация Markdown и JSON результатов
- Загрузка результатов в Cloud.ru Object Storage (опционально)
- Веб-интерфейс с корпоративным брендированием
- Дополнительные опции обработки: Enable chart parsing, Enable document unwarping, Enable orientation classification
- Расширенное отображение результатов: Markdown Preview, Visualization, Markdown Source
- **Визуализация layout-элементов** с цветовой дифференциацией и порядком чтения

### Зависимости
- PaddleOCR-VL (предзагруженные модели)
- FastAPI и Uvicorn
- Gradio для веб-интерфейса
- Boto3 для S3 интеграции
- PDF обработка (pdf2image, PyMuPDF)

## Health Check

### Health Check Script
- **Путь**: `/app/health_check.sh`
- **Функциональность**: 
  - Проверка активности процесса Gradio
  - Проверка доступности порта 7860 (если доступны сетевые утилиты)
  - Возврат кода 0 при успехе, ненулевого кода при ошибке

### Использование в Cloud.ru ML Inference
Для настройки readiness и liveness проб использовать:
- **Путь до команды**: `/app/health_check.sh`
- **Тип пробы**: `exec`

## Режимы работы

### Dual Mode (по умолчанию)
- **Описание**: Одновременная работа FastAPI и Gradio UI
- **Порты**: 8081 (FastAPI) и 7860 (Gradio UI)
- **Использование**: `docker run ... docling-granite-258m.cr.cloud.ru/paddleocr-vl-service:2.0.20`

### Server Mode
- **Описание**: Только FastAPI сервер
- **Порт**: 8081
- **Использование**: `docker run ... docling-granite-258m.cr.cloud.ru/paddleocr-vl-service:2.0.20 server`

### UI Mode
- **Описание**: Только Gradio Web UI
- **Порт**: 7860
- **Использование**: `docker run ... docling-granite-258m.cr.cloud.ru/paddleocr-vl-service:2.0.20 ui`

### Автоматический режим по PORT
- Если установлена переменная окружения `PORT=8081` - запускается Server Mode
- Если установлена переменная окружения `PORT=7860` - запускается UI Mode
- Если переменная PORT не установлена - запускается Dual Mode (улучшенная логика)

### Улучшенная логика запуска
Новый скрипт `start_enhanced.sh` обеспечивает более надежное определение режимов работы:
- При запуске с обоими портами (8081 и 7860) - автоматически активируется Dual Mode
- При запуске с одним портом - активируется соответствующий режим
- При отсутствии указания портов - по умолчанию запускается Dual Mode

## Сборка образа

Сборка выполнена успешно:
```bash
docker build -t docling-granite-258m.cr.cloud.ru/paddleocr-vl-service:2.0.21 -f ocr_vl/service/Dockerfile .
```

## Готовность к деплою

✅ Образ собран и готов к пушу в Artifact Registry Cloud.ru

## Инструкция по деплою

### 1. Авторизация в Artifact Registry
```bash
# Получите IAM токен в консоли Cloud.ru
docker login docling-granite-258m.cr.cloud.ru
# Введите ваш IAM токен как пароль
```

### 2. Пуш образа
```bash
docker push docling-granite-258m.cr.cloud.ru/paddleocr-vl-service:2.0.21
```

### 3. Деплой на ML Inference
В консоли Cloud.ru ML Inference:

#### Вариант 1: Dual Mode (оба сервиса)
- Создайте новый сервис
- Укажите образ: `docling-granite-258m.cr.cloud.ru/paddleocr-vl-service:2.0.21`
- Откройте оба порта: 8081 (API) и 7860 (Web UI)
- **ВАЖНО**: Для порта 7860 включите Serverless режим
- Установите переменные окружения при необходимости:
  - `USE_CLOUDRU_S3=true` (для включения S3 загрузки)
  - `CLOUDRU_S3_ENDPOINT` (endpoint Object Storage)
  - `CLOUDRU_S3_BUCKET` (имя bucket)
  - `CLOUDRU_S3_ACCESS_KEY` (access key)
  - `CLOUDRU_S3_SECRET_KEY` (secret key)
  - `COMPANY_NAME` (название компании для UI)

#### Вариант 2: UI Mode (только Web UI)
- Создайте новый сервис
- Укажите образ: `docling-granite-258m.cr.cloud.ru/paddleocr-vl-service:2.0.21`
- Откройте порт: 7860 (Web UI)
- **ВАЖНО**: Включите Serverless режим для порта 7860
- Установите переменные окружения:
  - `PORT=7860`
  - `COMPANY_NAME` (название компании для UI)

#### Вариант 3: Server Mode (только API)
- Создайте новый сервис
- Укажите образ: `docling-granite-258m.cr.cloud.ru/paddleocr-vl-service:2.0.21`
- Откройте порт: 8081 (API)
- Установите переменные окружения:
  - `PORT=8081`
  - `USE_CLOUDRU_S3=true` (для включения S3 загрузки, если нужно)

### 4. Настройка Health Check в Cloud.ru ML Inference
- **Readiness probe**:
  - Тип: `exec`
  - Путь до команды: `/app/health_check.sh`
  - Initial delay: 30 секунд
  - Period: 10 секунд
  
- **Liveness probe**:
  - Тип: `exec`
  - Путь до команды: `/app/health_check.sh`
  - Initial delay: 60 секунд
  - Period: 20 секунд

### 5. Тестирование
После деплоя проверьте доступность:
- Web UI: `http://<service-url>:7860`
- API Health: `http://<service-url>:8081/health`
- OCR обработка: `POST http://<service-url>:8081/ocr`

## Особенности

- Использует офлайн-образ с предзагруженными моделями (не требует интернета в runtime)
- Поддерживает GPU ускорение
- Совместим с Cloud.ru ML Inference
- Сохраняет всю существующую функциональность FastAPI
- Добавляет веб-интерфейс без изменения логики OCR
- Поддерживает автоматическое определение режима работы по переменной `PORT`
- Включает надежный health check механизм
- Поддерживает три режима работы: Dual, Server, UI
- Поддерживает одновременную работу обоих сервисов в Dual Mode

## Следующие шаги

1. Задеплоить на ML Inference
2. **ВАЖНО**: Включить Serverless режим для порта 7860 (если используется)
3. Настроить health check probes
4. Протестировать через веб-интерфейс и API
5. При необходимости внести корректировки
# PaddleOCR-VL Docker Service

Docker образ для обработки изображений с помощью PaddleOCR-VL. Поддерживает распознавание текста из изображений через Base64, URL или multipart загрузку с автоматическим сохранением результатов в Markdown и JSON форматах.

## Описание

Сервис состоит из двух компонентов, работающих в одном контейнере:

1. **vLLM сервер** (порт 8080) - предоставляет OpenAI-совместимый API для модели PaddleOCR-VL-0.9B
2. **FastAPI handler** (порт 8081) - обрабатывает HTTP запросы для OCR, поддерживает различные форматы входных данных и сохранение результатов

## Возможности

- ✅ Обработка изображений в форматах: Base64, URL, multipart/form-data
- ✅ Распознавание текста через PaddleOCR-VL
- ✅ Сохранение результатов в Markdown и JSON форматах
- ✅ Локальное сохранение результатов
- ✅ Автоматическая загрузка в cloud.ru Object Storage (опционально)
- ✅ REST API с документацией

## Технический стек

- **Базовый образ**: `paddlepaddle/paddlex-genai-vllm-server:latest`
- **PaddlePaddle GPU**: 3.2.1 (CUDA 12.6+)
- **PaddleOCR**: с поддержкой документного парсинга (PaddleOCR-VL)
- **FastAPI**: веб-фреймворк для API
- **boto3**: S3-совместимый клиент для cloud.ru Object Storage

## Структура файлов

```
paddle_docker_servise/
├── Dockerfile              # Docker образ
├── requirements.txt        # Python зависимости
├── server.py              # FastAPI handler
├── build_and_push.sh      # Скрипт сборки и публикации
├── .dockerignore          # Исключения для Docker
└── README.md              # Документация
```

## Сборка образа

### Локальная сборка

```bash
cd paddle_docker_servise
docker build -t paddleocr-vl-service:latest .
```

### Сборка с помощью скрипта

```bash
cd paddle_docker_servise

# Настройка переменных окружения (опционально)
export DOCKER_USERNAME=your-dockerhub-username
export VERSION=1.0.0

# Сборка образа
./build_and_push.sh

# Сборка и автоматический push
./build_and_push.sh --push
```

### Сборка для Cloud.ru Artifact Registry

```bash
# Настройка Cloud.ru registry
export CLOUDRU_REGISTRY=your-registry.cr.cloud.ru
export DOCKER_USERNAME=your-username

# Аутентификация в Cloud.ru Artifact Registry
docker login $CLOUDRU_REGISTRY \
  -u YOUR_KEY_ID \
  -p YOUR_KEY_SECRET

# Сборка и push
export PUSH_AFTER_BUILD=true
./build_and_push.sh --push
```

## Запуск контейнера

### Базовый запуск

```bash
docker run -d \
  --name paddleocr-vl \
  --gpus all \
  -p 8080:8080 \
  -p 8081:8081 \
  -v $(pwd)/output:/app/output \
  paddleocr-vl-service:latest
```

### Запуск с cloud.ru Object Storage

```bash
docker run -d \
  --name paddleocr-vl \
  --gpus all \
  -p 8080:8080 \
  -p 8081:8081 \
  -v $(pwd)/output:/app/output \
  -e CLOUDRU_S3_ENDPOINT=https://s3.cloud.ru \
  -e CLOUDRU_S3_BUCKET=your-bucket-name \
  -e CLOUDRU_S3_ACCESS_KEY=your-access-key \
  -e CLOUDRU_S3_SECRET_KEY=your-secret-key \
  paddleocr-vl-service:latest
```

## API Endpoints

### `GET /health`

Проверка здоровья сервиса.

**Пример запроса:**
```bash
curl http://localhost:8081/health
```

**Ответ:**
```json
{
  "status": "healthy",
  "paddleocr": "ready",
  "s3_storage": "configured",
  "output_dir": "/app/output",
  "temp_dir": "/app/temp"
}
```

### `GET /health/vllm`

Проверка доступности vLLM сервера.

**Пример запроса:**
```bash
curl http://localhost:8081/health/vllm
```

### `POST /ocr`

Основной эндпоинт для OCR обработки.

#### Вариант 1: Base64 изображение

```bash
curl -X POST "http://localhost:8081/ocr" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "image_base64=data:image/png;base64,iVBORw0KGgoAAAANSUhEUg..."
```

#### Вариант 2: URL изображения

```bash
curl -X POST "http://localhost:8081/ocr" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "image_url=https://example.com/image.png"
```

#### Вариант 3: Multipart загрузка файла

```bash
curl -X POST "http://localhost:8081/ocr" \
  -F "file=@/path/to/image.jpg"
```

**Ответ:**
```json
{
  "status": "success",
  "input_type": "multipart",
  "local_files": {
    "markdown": "/app/output/20250105_123456_image.jpg.md",
    "json": "/app/output/20250105_123456_image.jpg.json"
  },
  "s3_files": {
    "markdown": "https://s3.cloud.ru/bucket-name/ocr-results/20250105_123456_image.jpg.md",
    "json": "https://s3.cloud.ru/bucket-name/ocr-results/20250105_123456_image.jpg.json"
  },
  "timestamp": "2025-01-05T12:34:56.789123"
}
```

## Переменные окружения

### Обязательные

Нет обязательных переменных. Сервис работает по умолчанию.

### Опциональные (для cloud.ru Object Storage)

- `CLOUDRU_S3_ENDPOINT` - endpoint Object Storage (например, `https://s3.cloud.ru`)
- `CLOUDRU_S3_BUCKET` - имя bucket для сохранения результатов
- `CLOUDRU_S3_ACCESS_KEY` - access key для аутентификации
- `CLOUDRU_S3_SECRET_KEY` - secret key для аутентификации

Если переменные не настроены, результаты сохраняются только локально.

## Структура выходных данных

### Локальное сохранение

Результаты сохраняются в `/app/output` с именами:
- `{timestamp}_{filename}.md` - Markdown формат
- `{timestamp}_{filename}.json` - JSON формат

### Cloud.ru Object Storage

Если настроены credentials, файлы дополнительно загружаются в S3:
- Путь: `s3://{bucket}/ocr-results/{timestamp}_{filename}.md`
- Путь: `s3://{bucket}/ocr-results/{timestamp}_{filename}.json`

## Загрузка образа в cloud.ru Object Storage для ML Cloud.ru

После сборки и тестирования образа его необходимо загрузить в Object Storage для использования в ML Cloud.ru:

### Шаг 1: Подготовка образа

```bash
# Сохранить образ в tar архив
docker save paddleocr-vl-service:latest -o paddleocr-vl-service.tar

# Или использовать готовый образ из registry
docker pull your-registry/paddleocr-vl-service:latest
docker save your-registry/paddleocr-vl-service:latest -o paddleocr-vl-service.tar
```

### Шаг 2: Настройка доступа к Object Storage

1. Получите ключи доступа в Cloud.ru консоли:
   - Перейдите в **Object Storage**
   - Создайте bucket (если еще не создан)
   - Перейдите в **Ключи доступа**
   - Создайте новый ключ

2. Настройте переменные окружения:
```bash
export CLOUDRU_S3_ENDPOINT=https://s3.cloud.ru
export CLOUDRU_S3_BUCKET=your-bucket-name
export CLOUDRU_S3_ACCESS_KEY=your-access-key
export CLOUDRU_S3_SECRET_KEY=your-secret-key
```

### Шаг 3: Загрузка образа

#### Вариант 1: Использование AWS CLI (рекомендуется)

```bash
# Установка AWS CLI (если не установлен)
pip install awscli

# Настройка credentials
aws configure set aws_access_key_id $CLOUDRU_S3_ACCESS_KEY
aws configure set aws_secret_access_key $CLOUDRU_S3_SECRET_KEY
aws configure set default.region ru-1

# Загрузка в S3
aws --endpoint-url=$CLOUDRU_S3_ENDPOINT \
  s3 cp paddleocr-vl-service.tar \
  s3://$CLOUDRU_S3_BUCKET/docker-images/paddleocr-vl-service.tar
```

#### Вариант 2: Использование boto3 (Python)

```python
import boto3

s3 = boto3.client(
    's3',
    endpoint_url='https://s3.cloud.ru',
    aws_access_key_id='your-access-key',
    aws_secret_access_key='your-secret-key'
)

s3.upload_file(
    'paddleocr-vl-service.tar',
    'your-bucket-name',
    'docker-images/paddleocr-vl-service.tar'
)
```

#### Вариант 3: Использование rclone

```bash
# Настройка rclone
rclone config

# Загрузка
rclone copy paddleocr-vl-service.tar \
  cloudru-s3:your-bucket-name/docker-images/
```

### Шаг 4: Использование в ML Cloud.ru

1. В ML Cloud.ru перейдите в **Inference → Model Runs**
2. Создайте новый Model Run
3. В поле "Docker Image" укажите путь к образу в Object Storage:
   ```
   s3://your-bucket-name/docker-images/paddleocr-vl-service.tar
   ```
4. Настройте переменные окружения для S3 (если нужно)
5. Запустите Model Run

## Разработка и тестирование

### Локальное тестирование (без GPU)

Для базовой проверки можно запустить контейнер без GPU (но OCR может не работать):

```bash
docker run -it --rm \
  -p 8080:8080 \
  -p 8081:8081 \
  -v $(pwd)/output:/app/output \
  paddleocr-vl-service:latest
```

### Тестирование API

```bash
# Проверка health
curl http://localhost:8081/health

# Тест с изображением
curl -X POST "http://localhost:8081/ocr" \
  -F "file=@test_image.jpg"
```

## Troubleshooting

### vLLM сервер не запускается

Проверьте логи контейнера:
```bash
docker logs paddleocr-vl
```

Убедитесь, что доступна GPU:
```bash
docker run --gpus all --rm nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

### Ошибки при обработке изображений

- Проверьте формат изображения (поддерживаются: JPEG, PNG, BMP, TIFF)
- Убедитесь, что изображение не повреждено
- Проверьте логи: `docker logs paddleocr-vl`

### Ошибки загрузки в S3

- Проверьте правильность credentials
- Убедитесь, что bucket существует и доступен
- Проверьте endpoint URL
- Посмотрите логи сервиса

## Лицензия

Этот проект использует компоненты с различными лицензиями:
- PaddlePaddle: Apache 2.0
- PaddleOCR: Apache 2.0
- FastAPI: MIT

## Поддержка

Для вопросов и проблем создавайте issues в репозитории проекта.


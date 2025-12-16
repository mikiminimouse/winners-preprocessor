# Инструкция по сборке и запуску Docker образа (Variant B: vLLM)

**Дата:** 06.12.2025  
**Версия:** 2.0.0  
**Вариант:** B (paddlex-genai-vllm-server с internal vLLM)

## Обзор

Этот образ реализует Variant B архитектуры:
- **FastAPI на порту 8081** - внешний API (оркестратор)
- **vLLM на порту 8080** - внутренний inference сервис (не публикуется наружу)
- **Предзагруженные модели** - все модели загружаются при сборке образа

## Структура файлов

- `Dockerfile.vllm` - основной Dockerfile
- `server_vllm.py` - FastAPI сервер (копируется как `server.py`)
- `start_vllm.sh` - скрипт запуска (копируется как `start.sh`)
- `warmup_vllm.py` - скрипт прогрева (копируется как `warmup.py`)
- `preload_models.py` - скрипт предзагрузки моделей (build-time)
- `requirements_vllm.txt` - зависимости Python

## Сборка образа

### Локальная сборка

```bash
cd /root/winners_preprocessor/paddle_docker_servise

# Сборка образа
docker build -f Dockerfile.vllm -t paddleocr-vl-vllm:2.0.0 .

# Тегирование для registry
docker tag paddleocr-vl-vllm:2.0.0 your-registry/paddleocr-vl-vllm:2.0.0
docker tag paddleocr-vl-vllm:2.0.0 your-registry/paddleocr-vl-vllm:latest
```

### Загрузка в Cloud.ru Artifact Registry

```bash
# Авторизация в Cloud.ru registry
# (замените на ваши credentials)

# Push образа
docker push your-registry/paddleocr-vl-vllm:2.0.0
docker push your-registry/paddleocr-vl-vllm:latest
```

## Локальное тестирование

```bash
# Запуск контейнера
docker run --gpus all \
  -p 8081:8081 \
  -v $(pwd)/output:/workspace/output \
  -e PADDLEX_HOME=/home/paddleocr/.paddlex \
  -e OUTPUT_DIR=/workspace/output \
  -e VLLM_URL=http://127.0.0.1:8080/v1/markdown \
  -e USE_VLM_API=true \
  paddleocr-vl-vllm:2.0.0

# Проверка health
curl http://localhost:8081/health

# Тест OCR (замените test.pdf на ваш файл)
curl -X POST \
  -F "file=@test.pdf" \
  http://localhost:8081/ocr/pdf
```

## Переменные окружения

### Обязательные

- `PADDLEX_HOME` - путь к директории с моделями (по умолчанию: `/home/paddleocr/.paddlex`)
- `OUTPUT_DIR` - директория для выходных файлов (по умолчанию: `/workspace/output`)

### Опциональные

- `VLLM_URL` - URL vLLM endpoint (по умолчанию: `http://127.0.0.1:8080/v1/markdown`)
- `USE_VLM_API` - использовать ли vLLM API (по умолчанию: `true`)
- `HF_HOME` - путь к HuggingFace cache (по умолчанию: `/home/paddleocr/.cache/huggingface`)

### Cloud.ru S3 (опционально)

- `CLOUDRU_S3_ENDPOINT` - S3 endpoint
- `CLOUDRU_S3_BUCKET` - имя bucket
- `CLOUDRU_S3_ACCESS_KEY` - access key
- `CLOUDRU_S3_SECRET_KEY` - secret key

## Развертывание в Cloud.ru ML Inference

### Настройки контейнера

1. **Образ:** `your-registry/paddleocr-vl-vllm:2.0.0`

2. **Порты:**
   - `8081` - публичный (FastAPI)
   - `8080` - не публикуется (vLLM internal)

3. **Переменные окружения:**
   ```yaml
   PADDLEX_HOME: /home/paddleocr/.paddlex
   OUTPUT_DIR: /workspace/output
   VLLM_URL: http://127.0.0.1:8080/v1/markdown
   USE_VLM_API: "true"
   ```

4. **Ресурсы:**
   - GPU: A100 80GB (рекомендуется)
   - CPU: 16 cores
   - RAM: 256GB

5. **Health Checks:**

   **Startup Probe:**
   ```yaml
   httpGet:
     path: /health
     port: 8081
   initialDelaySeconds: 120
   periodSeconds: 10
   failureThreshold: 50
   timeoutSeconds: 5
   ```

   **Liveness Probe:**
   ```yaml
   httpGet:
     path: /health
     port: 8081
   initialDelaySeconds: 300
   periodSeconds: 30
   failureThreshold: 3
   timeoutSeconds: 10
   ```

   **Readiness Probe:**
   ```yaml
   httpGet:
     path: /health
     port: 8081
   initialDelaySeconds: 180
   periodSeconds: 10
   failureThreshold: 3
   timeoutSeconds: 5
   ```

### Проверка развертывания

1. Проверка health:
   ```bash
   curl https://your-service-url.cloud.ru/health
   ```
   
   Ожидаемый ответ:
   ```json
   {
     "status": "healthy",
     "models_present": true,
     "models_path": "/home/paddleocr/.paddlex/official_models",
     "vllm_status": "available",
     "vllm_url": "http://127.0.0.1:8080/v1/markdown",
     "use_vlm_api": true,
     "output_dir": "/workspace/output",
     "s3_storage": "not_configured"
   }
   ```

2. Тест OCR:
   ```bash
   curl -X POST \
     -F "file=@test.pdf" \
     https://your-service-url.cloud.ru/ocr/pdf
   ```

## Команды для проверки моделей в образе

### Проверка перед push в registry

```bash
# Запуск контейнера для проверки
docker run --rm --entrypoint /bin/bash \
  paddleocr-vl-vllm:2.0.0 \
  -c "ls -la /home/paddleocr/.paddlex/official_models/"

# Проверка размера моделей
docker run --rm --entrypoint /bin/bash \
  paddleocr-vl-vllm:2.0.0 \
  -c "du -sh /home/paddleocr/.paddlex/official_models/*"

# Проверка через health endpoint (если контейнер запущен)
curl http://localhost:8081/health | jq '.models_present'
```

### Проверка через exec в Cloud.ru (если доступен)

```bash
# Подключение к контейнеру (замените на ваш способ подключения)
kubectl exec -it <pod-name> -- /bin/bash

# Внутри контейнера:
ls -la /home/paddleocr/.paddlex/official_models/
python3 -c "
from pathlib import Path
models_dir = Path('/home/paddleocr/.paddlex/official_models')
if models_dir.exists():
    for model_dir in models_dir.iterdir():
        if model_dir.is_dir():
            size = sum(f.stat().st_size for f in model_dir.rglob('*') if f.is_file())
            print(f'{model_dir.name}: {size / (1024*1024*1024):.2f} GB')
"
```

## Предзагруженные модели

При сборке образа загружаются следующие модели:

1. **PP-StructureV3** - layout detection
2. **PP-OCRv5** - detection, recognition, classification
3. **TableDet/TableRec** - table detection and recognition (если доступно)
4. **PaddleOCR-VL-0.9B** - vision-language model для semantic refinement

Все модели сохраняются в `/home/paddleocr/.paddlex/official_models/` и доступны при старте контейнера без необходимости скачивания.

## Архитектура

```
┌─────────────────────────────────────────┐
│         Cloud.ru ML Inference           │
│                                         │
│  ┌───────────────────────────────────┐  │
│  │  FastAPI (8081) - External API    │  │
│  │  - /health                        │  │
│  │  - /ocr/pdf                       │  │
│  └───────────┬───────────────────────┘  │
│              │                           │
│  ┌───────────▼───────────────────────┐  │
│  │  vLLM Server (8080) - Internal    │  │
│  │  - /v1/markdown                   │  │
│  └───────────────────────────────────┘  │
│                                         │
│  Models: PP-StructureV3, PP-OCRv5,     │
│          PaddleOCR-VL-0.9B              │
└─────────────────────────────────────────┘
```

## Устранение неполадок

### Модели не найдены

Проверьте, что модели предзагружены:
```bash
docker run --rm --entrypoint /bin/bash \
  paddleocr-vl-vllm:2.0.0 \
  -c "ls -la /home/paddleocr/.paddlex/official_models/"
```

### vLLM недоступен

Проверьте логи контейнера:
```bash
docker logs <container_id>
```

Убедитесь, что базовый образ `paddlex-genai-vllm-server:latest` запускает vLLM автоматически или запустите его вручную.

### Таймауты при обработке

Увеличьте таймауты в клиенте и health checks Cloud.ru (см. настройки выше).

## Примечания

- Этот образ использует базовый `paddlex-genai-vllm-server:latest`, который должен автоматически запускать vLLM сервер
- Если vLLM не запускается автоматически, может потребоваться дополнительная настройка в `start_vllm.sh`
- Все модели предзагружаются при сборке, поэтому первый запуск быстрее
- Размер образа будет больше из-за предзагруженных моделей (~8-10GB)


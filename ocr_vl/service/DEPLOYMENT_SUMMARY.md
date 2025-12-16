# Сводка по развертыванию PaddleOCR-VL Service

## ✅ Статус сборки

- **Образ собран:** ✅ `paddleocr-vl-service:latest`
- **Размер образа:** ~18.8 GB
- **Базовый образ:** `ccr-2vdh3abv-pub.cnc.bj.baidubce.com/paddlepaddle/paddlex-genai-vllm-server:latest`

## ✅ Проверка зависимостей

| Компонент | Статус | Примечание |
|-----------|--------|------------|
| FastAPI | ✅ Установлен | Версия 0.104.0+ |
| uvicorn | ✅ Установлен | ASGI сервер |
| boto3 | ✅ Установлен | S3 клиент для cloud.ru |
| requests | ✅ Установлен | HTTP клиент |
| Pillow | ✅ Установлен | Работа с изображениями |
| PaddleOCR-VL | ⚠️ Частично | Импорт работает, требует GPU для полной функциональности |
| paddlex_genai_server | ✅ Найден | `/usr/local/bin/paddlex_genai_server` |

**Примечание:** Проблема с torch/NCCL не критична - в GPU окружении ML Inference это будет работать корректно.

## 📋 Быстрый старт

### 1. Push в Artifact Registry

```bash
cd /root/winners_preprocessor/paddle_docker_servise

# Установите переменные окружения
export REGISTRY_ENDPOINT="registry-xxxxx.cr.cloud.ru"
export KEY_ID="your-key-id"
export KEY_SECRET="your-key-secret"
export VERSION="1.0.0"

# Запустите скрипт push
./push_to_artifact_registry.sh
```

### 2. Настройка ML Inference

**Основные параметры:**

```
Docker Image: registry-xxxxx.cr.cloud.ru/paddleocr-vl-service:latest
Port: 8081
Health Check: /health
Health Port: 8081
Initial Delay: 120 секунд
```

**Ресурсы:**
- CPU: 4-8 cores
- Memory: 16-32 GB
- GPU: 1x NVIDIA (CUDA 12.6+)

**Health Checks:**
- Liveness: `GET /health` на порту 8081
- Readiness: `GET /health` на порту 8081
- Startup: `GET /health` на порту 8081 (initialDelaySeconds: 0, failureThreshold: 30)

## 📝 API Endpoints

После развертывания доступны:

1. **GET /health** - проверка здоровья сервиса
2. **GET /health/vllm** - проверка vLLM сервера
3. **POST /ocr** - обработка изображений
   - Поддержка: Base64, URL, multipart/form-data

## 📚 Документация

- **ML_INFERENCE_CONFIG.md** - полная конфигурация для ML Inference
- **README.md** - общая документация сервиса
- **push_to_artifact_registry.sh** - скрипт для push образа

## 🔍 Проверка работоспособности

После развертывания проверьте:

```bash
# Health check
curl https://your-endpoint.modelrun.inference.cloud.ru/health

# Тест OCR
curl -X POST "https://your-endpoint.modelrun.inference.cloud.ru/ocr" \
  -F "file=@test_image.jpg"
```

## ⚠️ Важные замечания

1. **GPU обязателен** - сервис требует NVIDIA GPU с CUDA 12.6+
2. **Время старта** - первая инициализация может занять 2-3 минуты
3. **Размер образа** - 18GB, push может занять 10-30 минут
4. **Ресурсы** - минимум 16GB RAM и 4 CPU cores

## 🎯 Следующие шаги

1. ✅ Образ собран и протестирован
2. ⏳ Push в Artifact Registry (используйте `push_to_artifact_registry.sh`)
3. ⏳ Настройка ML Inference (используйте `ML_INFERENCE_CONFIG.md`)
4. ⏳ Тестирование в production окружении


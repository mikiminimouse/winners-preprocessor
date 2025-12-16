# ✅ Образ успешно загружен в Cloud.ru Artifact Registry

**Дата:** $(date)
**Реестр:** docling-granite-258m.cr.cloud.ru (публичный)

## 📦 Информация об образе

**Полный URI образа:**
```
docling-granite-258m.cr.cloud.ru/paddleocr-vl-service:latest
docling-granite-258m.cr.cloud.ru/paddleocr-vl-service:1.0.0
```

**Digest:**
```
sha256:e7afa04004434b4f973441a3d7d609317ca31ed99a28f1c9230e9449cddb71ce
```

**Размер образа:** ~18.8 GB

## 🚀 Использование в ML Inference

### Основные параметры:

**Docker Image URI:**
```
docling-granite-258m.cr.cloud.ru/paddleocr-vl-service:latest
```

**Порты:**
- `8081` - FastAPI Handler (основной API)
- `8080` - vLLM Server (опционально)

### Health Checks:

**Liveness Probe:**
- Path: `/health`
- Port: `8081`
- Initial Delay: `60` секунд
- Period: `30` секунд
- Timeout: `10` секунд
- Failure Threshold: `3`

**Readiness Probe:**
- Path: `/health`
- Port: `8081`
- Initial Delay: `90` секунд
- Period: `15` секунд
- Timeout: `5` секунд
- Failure Threshold: `3`

**Startup Probe (рекомендуется):**
- Path: `/health`
- Port: `8081`
- Initial Delay: `0` секунд
- Period: `10` секунд
- Timeout: `5` секунд
- Failure Threshold: `30` (до 5 минут на старт)

### Ресурсы:

**Минимальные требования:**
- CPU: `4` cores
- Memory: `16` GB
- GPU: `1x NVIDIA` (CUDA 12.6+)

**Рекомендуемые:**
- CPU: `8` cores
- Memory: `32` GB
- GPU: `1x NVIDIA A100` или эквивалент

### Переменные окружения (опционально):

Для сохранения результатов в S3:

```bash
CLOUDRU_S3_ENDPOINT=https://s3.cloud.ru
CLOUDRU_S3_BUCKET=your-bucket-name
CLOUDRU_S3_ACCESS_KEY=your-access-key
CLOUDRU_S3_SECRET_KEY=your-secret-key
```

## 📋 API Endpoints

После развертывания доступны:

1. **GET /health** - проверка здоровья сервиса
2. **GET /health/vllm** - проверка vLLM сервера
3. **POST /ocr** - обработка изображений (Base64, URL, multipart)

## ✅ Статус

- ✅ Образ собран
- ✅ Образ загружен в Artifact Registry
- ✅ Образ доступен для использования в ML Inference

## 📝 Следующие шаги

1. Перейдите в Cloud.ru → AI Factory → ML Inference
2. Создайте новый ML Inference
3. Укажите Docker Image URI: `docling-granite-258m.cr.cloud.ru/paddleocr-vl-service:latest`
4. Настройте параметры согласно ML_INFERENCE_CONFIG.md
5. Запустите inference

## 📚 Документация

- `ML_INFERENCE_CONFIG.md` - полная конфигурация для ML Inference
- `README.md` - общая документация сервиса
- `DEPLOYMENT_SUMMARY.md` - сводка по развертыванию


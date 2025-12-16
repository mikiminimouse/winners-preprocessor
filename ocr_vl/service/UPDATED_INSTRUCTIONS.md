# Обновленные инструкции по запуску

**Версия:** 1.0.8  
**Дата:** 05.12.2025

## ✅ Что изменилось

### Версия 1.0.8:

1. **Убран vLLM сервер** - больше не запускается
   - Было: Два сервиса (vLLM на 8080 + FastAPI на 8081)
   - Стало: Один сервис (FastAPI на 8081)

2. **Упрощен запуск** - только FastAPI handler
   - Было: Попытка запустить vLLM, затем FastAPI
   - Стало: Только FastAPI

3. **Меньше ошибок** - нет попыток скачать модель для vLLM

## 📦 Образ Docker

**URI:**
```
docling-granite-258m.cr.cloud.ru/paddleocr-vl-service:latest
```

**Версия:**
```
docling-granite-258m.cr.cloud.ru/paddleocr-vl-service:1.0.8
```

**Digest:**
```
sha256:517c7cc435e81889905d7a3bfc03846ec4a2a5b308cb8bfb34d0c752ff918fb6
```

## 🚀 Инструкции по запуску на Cloud.ru

### 1. Базовая конфигурация

**Docker Image URI:**
```
docling-granite-258m.cr.cloud.ru/paddleocr-vl-service:latest
```

**Порты:**
- **8081** - FastAPI handler (основной сервис)

### 2. Health Check

**Endpoint:** `GET /health`  
**Port:** `8081`  
**Initial Delay:** `180` секунд (рекомендуется)

**Настройки:**
- Liveness Probe: initial delay 180s, period 30s
- Readiness Probe: initial delay 240s, period 15s
- Startup Probe: failure threshold 40 (до 10 минут)

### 3. Переменные окружения (опционально)

**Cloud.ru Object Storage:**
```bash
CLOUDRU_S3_ENDPOINT=https://s3.cloud.ru
CLOUDRU_S3_BUCKET=bucket-winners223
CLOUDRU_S3_ACCESS_KEY=your-access-key
CLOUDRU_S3_SECRET_KEY=your-secret-key
```

### 4. Ресурсы

**Рекомендуемые:**
- CPU: 4+ cores
- Memory: 16GB+ RAM
- GPU: 1x NVIDIA GPU (CUDA 12.6+)
- Storage: 10GB+

## 🔍 Проверка работоспособности

### 1. Health Check

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  https://your-endpoint.cloud.ru/health
```

**Ожидаемый ответ:**
```json
{
    "status": "healthy",
    "paddleocr": "not_initialized",
    "s3_storage": "configured",
    "output_dir": "/app/output",
    "temp_dir": "/app/temp",
    "docs": "/docs - Swagger UI для тестирования API"
}
```

### 2. Swagger UI

```
https://your-endpoint.cloud.ru/docs
```

## ✅ Что работает

- ✅ FastAPI handler запускается успешно
- ✅ Health check доступен
- ✅ PaddleOCR-VL импортирован
- ✅ OCR функционал доступен
- ✅ S3 интеграция работает (если настроена)

## ⚠️ Особенности

1. **Инициализация модели:** PaddleOCR-VL инициализируется при первом запросе (может занять время)
2. **Производительность:** Используется PaddlePaddle бэкенд (без vLLM ускорения)
3. **GPU:** Рекомендуется для оптимальной производительности

## 📄 Полная документация

- `CLOUDRU_DEPLOYMENT_GUIDE.md` - детальное руководство
- `DEPLOYMENT_INSTRUCTIONS.md` - инструкции по развертыванию
- `FINAL_STATUS_REPORT.md` - финальный статус

---

**Статус:** ✅ Готово к использованию


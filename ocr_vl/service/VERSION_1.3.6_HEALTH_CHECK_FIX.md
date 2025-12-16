# Версия 1.3.6 - Улучшенный Health Check для предотвращения SIGTERM

**Дата:** 05.12.2025  
**Версия:** 1.3.6

## 🔴 Проблема в версии 1.3.5

### SIGTERM при первом запуске:

```
FatalError: `Termination signal` is detected by the operating system.
SIGTERM received by PID 1
```

**Причина:**
- Инициализация PaddleOCR-VL занимает ~80-90 секунд
- Health check не получает ответ вовремя
- Контейнер убивается до завершения инициализации

**После перезапуска:**
- Все работает нормально
- Модели уже инициализированы

## ✅ Решение в версии 1.3.6

### 1. Улучшенный Health Check endpoint

**Было:**
```python
ocr_status = "ready" if paddle_ocr is not None else "not_initialized"
status = "healthy"
```

**Стало:**
```python
if paddle_ocr is not None:
    ocr_status = "ready"
    status = "healthy"
else:
    ocr_status = "initializing"
    status = "starting"  # Для startup probe
```

**Преимущества:**
- Startup probe может принимать статус "starting"
- Ясно показывает, что идет инициализация
- Liveness probe должен ждать завершения

### 2. Увеличена задержка перед инициализацией

**Было:**
```python
await asyncio.sleep(2)  # 2 секунды
```

**Стало:**
```python
await asyncio.sleep(10)  # 10 секунд
```

**Преимущества:**
- Сервер успевает полностью запуститься
- Health check начинает отвечать до начала инициализации
- Меньше конфликтов с health check

## 📋 Настройки Health Check для Cloud.ru

### Рекомендуемые настройки:

**Startup Probe:**
```yaml
startupProbe:
  httpGet:
    path: /health
    port: 8081
  initialDelaySeconds: 0
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 30  # До 5 минут
  successThreshold: 1
```

**Важно:** Startup probe должен принимать статус "starting" как валидный ответ (200 OK), но не считать это "ready".

**Liveness Probe:**
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8081
  initialDelaySeconds: 180  # 3 минуты на инициализацию
  periodSeconds: 30
  timeoutSeconds: 10
  failureThreshold: 3
```

**Readiness Probe:**
```yaml
readinessProbe:
  httpGet:
    path: /health
    port: 8081
  initialDelaySeconds: 120  # 2 минуты
  periodSeconds: 15
  timeoutSeconds: 5
  failureThreshold: 3
```

## 🎯 Ожидаемое поведение

### При первом запуске:

1. **0-10 секунд:**
   - Сервер запускается
   - Health check возвращает: `{"status": "starting", "paddleocr": "initializing"}`

2. **10-100 секунд:**
   - Идет фоновая инициализация
   - Health check продолжает возвращать "starting"
   - Startup probe не убивает контейнер

3. **После 100 секунд:**
   - Инициализация завершена
   - Health check возвращает: `{"status": "healthy", "paddleocr": "ready"}`
   - Готов к обработке запросов

## 📦 Образ

**URI:** `docling-granite-258m.cr.cloud.ru/paddleocr-vl-service:1.3.6`

**Изменения:**
- Улучшенный health check endpoint
- Увеличена задержка перед инициализацией (10 секунд)
- Статус "starting" для startup probe

---

**Статус:** ✅ Готово к тестированию



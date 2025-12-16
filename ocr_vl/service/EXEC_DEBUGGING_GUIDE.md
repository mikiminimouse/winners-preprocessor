# Руководство по отладке и подключению к контейнеру на Cloud.ru

**Дата:** 06.12.2025  
**Версия:** 1.3.6

## 🔧 Подключение к контейнеру через exec

### Вариант 1: Через Cloud.ru Console (рекомендуется)

**Шаги:**

1. Войдите в Cloud.ru Console
2. Перейдите в ML Inference → Container Apps
3. Найдите ваш сервис `paddleocr-vl-service`
4. Откройте раздел "Container Shell" или "Exec"
5. Выполняйте команды в открывшейся консоли

**Доступность:** ⚠️ Зависит от настроек Cloud.ru

---

### Вариант 2: Через kubectl (если есть доступ к кластеру)

```bash
# 1. Найти pod
kubectl get pods -n <namespace> | grep paddleocr

# 2. Подключиться к контейнеру
kubectl exec -it <pod-name> -n <namespace> -- /bin/bash

# 3. Если контейнер не называется по умолчанию
kubectl exec -it <pod-name> -n <namespace> -c <container-name> -- /bin/bash
```

**Пример:**
```bash
kubectl exec -it paddleocr-vl-service-12345-abcde -n ml-inference -- /bin/bash
```

---

### Вариант 3: Добавить debug endpoint в FastAPI

**Проблема:** Exec может быть недоступен

**Решение:** Создать HTTP endpoints для отладки

```python
# Добавить в server.py:

@app.get("/debug/info")
async def debug_info():
    """Информация о системе"""
    import sys
    import paddle
    
    info = {
        "python_version": sys.version,
        "paddle_version": paddle.__version__ if paddle else "N/A",
        "models_path": os.environ.get("PADDLEX_HOME"),
        "gpu_available": paddle.device.is_compiled_with_cuda() if paddle else False,
        "paddleocr_initialized": paddle_ocr is not None,
    }
    
    return info

@app.get("/debug/models")
async def debug_models():
    """Список доступных моделей"""
    from pathlib import Path
    
    models_path = Path("/home/paddleocr/.paddlex/official_models")
    models = {}
    
    if models_path.exists():
        for model_dir in models_path.iterdir():
            if model_dir.is_dir():
                size = sum(f.stat().st_size for f in model_dir.rglob('*') if f.is_file())
                models[model_dir.name] = {
                    "path": str(model_dir),
                    "size_gb": round(size / (1024**3), 2),
                    "files_count": len(list(model_dir.rglob('*')))
                }
    
    return {"models": models}

@app.get("/debug/env")
async def debug_env():
    """Переменные окружения"""
    relevant_vars = {
        k: v for k, v in os.environ.items()
        if 'PADDLE' in k or 'FLAGS' in k or 'HF' in k or 'S3' in k
    }
    return relevant_vars

@app.post("/debug/test-ocr")
async def debug_test_ocr(image_path: str = Form(...)):
    """Тестовый OCR для отладки"""
    if paddle_ocr is None:
        return {"error": "PaddleOCR not initialized"}
    
    try:
        result = paddle_ocr.predict(image_path)
        return {
            "status": "success",
            "result_type": type(result).__name__,
            "has_markdown": hasattr(result, 'save_to_markdown'),
        }
    except Exception as e:
        return {"error": str(e)}
```

**Использование:**
```bash
# Информация о системе
curl http://your-service/debug/info

# Список моделей
curl http://your-service/debug/models

# Переменные окружения
curl http://your-service/debug/env
```

---

## 📋 Полезные команды для отладки

### Проверка логов

```bash
# Внутри контейнера:
tail -f /proc/1/fd/1  # Логи процесса PID 1 (uvicorn)

# Или через Python:
python3 -c "
import logging
logging.basicConfig(level=logging.DEBUG)
# Ваш код здесь
"

# Проверка переменных окружения:
env | grep -E "PADDLE|FLAGS|HF|S3"
```

### Проверка моделей

```bash
# Проверить наличие моделей:
ls -lh /home/paddleocr/.paddlex/official_models/

# Размер моделей:
du -sh /home/paddleocr/.paddlex/official_models/*

# Список файлов модели:
find /home/paddleocr/.paddlex -name "*.safetensors"
find /home/paddleocr/.paddlex -name "config.json"
```

### Проверка GPU

```bash
# Проверить доступность GPU:
nvidia-smi

# Или через Python:
python3 << EOF
import paddle
print(f"GPU available: {paddle.device.is_compiled_with_cuda()}")
print(f"GPU count: {paddle.device.cuda.device_count()}")
EOF
```

### Проверка процессов

```bash
# Список процессов:
ps aux | grep python
ps aux | grep paddle

# Использование памяти:
free -h
top -p $(pgrep -f uvicorn)

# Использование диска:
df -h
du -sh /app/*
```

### Тестирование PaddleOCR-VL

```bash
# Интерактивный Python:
python3

>>> from paddleocr import PaddleOCRVL
>>> ocr = PaddleOCRVL()
>>> result = ocr.predict("/app/temp/test.jpg")
>>> print(result)
```

---

## 🔍 Проверка через HTTP API

### Health Check

```bash
curl http://your-service-url/health
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

### Информация о сервисе

```bash
curl http://your-service-url/
```

### Проверка логов (если доступно)

```bash
# Через Cloud.ru Console:
# 1. Откройте Container App
# 2. Перейдите в "Logs"
# 3. Просматривайте логи в реальном времени
```

---

## 🛠️ Управление компонентами Paddle

### Управление через Python API

```python
# Внутри контейнера через Python:

# 1. Проверить версию PaddlePaddle:
import paddle
print(paddle.__version__)

# 2. Проверить версию PaddleOCR:
import paddleocr
print(paddleocr.__version__)

# 3. Проверить доступные модели:
from pathlib import Path
models_path = Path("/home/paddleocr/.paddlex/official_models")
for model in models_path.iterdir():
    print(f"{model.name}: {model.exists()}")

# 4. Инициализировать PaddleOCR-VL:
from paddleocr import PaddleOCRVL
ocr = PaddleOCRVL()

# 5. Обработать изображение:
result = ocr.predict("/app/temp/test.jpg")
result.save_to_markdown("/app/output/test.md")
```

### Управление через HTTP (рекомендуется)

Используйте debug endpoints, описанные выше, для управления через HTTP API.

---

## 📊 Мониторинг

### Метрики производительности

```python
# Добавить в server.py:

import time

@app.get("/debug/metrics")
async def debug_metrics():
    """Метрики производительности"""
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    
    return {
        "cpu_percent": process.cpu_percent(interval=1),
        "memory_mb": process.memory_info().rss / 1024 / 1024,
        "open_files": len(process.open_files()),
        "threads": process.num_threads(),
    }
```

### Мониторинг через Cloud.ru

- Используйте встроенные метрики Cloud.ru
- Проверяйте использование CPU/GPU
- Следите за использованием памяти

---

## ⚠️ Ограничения Cloud.ru

### Что может быть недоступно:

1. ❌ Прямой SSH доступ к контейнеру
2. ❌ Прямой `docker exec` из вашей машины
3. ⚠️ Ограниченный доступ к файловой системе
4. ⚠️ Ограниченные права пользователя

### Что доступно:

1. ✅ Логи через Cloud.ru Console
2. ✅ HTTP endpoints (health, debug)
3. ✅ Метрики через Cloud.ru
4. ⚠️ Container Shell (если включено)

---

## 💡 Рекомендации

### Для отладки:

1. **Используйте логи Cloud.ru:**
   - Проще всего получить доступ
   - Реальное время
   - Полная история

2. **Добавьте debug endpoints:**
   - Независимость от exec
   - Работает через HTTP
   - Легко расширяемо

3. **Используйте Container Shell (если доступно):**
   - Прямой доступ к контейнеру
   - Выполнение команд
   - Интерактивная отладка

### Для production:

1. **Отключите debug endpoints** или ограничьте доступ
2. **Используйте логирование** вместо print
3. **Настройте мониторинг** через Cloud.ru

---

**Версия документа:** 1.0  
**Последнее обновление:** 06.12.2025


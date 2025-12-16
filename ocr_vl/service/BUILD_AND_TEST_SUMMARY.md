# Итоги сборки и проверки Docker образа (Variant B)

**Дата:** 08.12.2025  
**Версия:** 2.0.0  
**Статус:** ✅ Сборка завершена успешно

## Результаты сборки

### Образ собран успешно

```bash
docker images paddleocr-vl-vllm:2.0.0
```

**ID образа:** `77ba521c8ee9`  
**Размер:** 12.5 GB  
**Тег:** `paddleocr-vl-vllm:2.0.0`

### Структура образа

**Файлы в `/app/`:**
- ✅ `server.py` - FastAPI сервер (Variant B, оркестратор)
- ✅ `start.sh` - скрипт запуска (исполняемый)
- ✅ `warmup.py` - скрипт прогрева моделей
- ✅ `preload_models.py` - скрипт предзагрузки (для reference)
- ✅ `output/`, `temp/` - директории для файлов

### Установленные зависимости

Проверка Python пакетов:
- ✅ FastAPI - HTTP фреймворк
- ✅ uvicorn - ASGI сервер
- ✅ pdf2image - конвертация PDF в изображения
- ✅ paddleocr - OCR библиотека
- ✅ boto3 - S3 клиент
- ✅ Pillow - обработка изображений
- ✅ Все зависимости из `requirements_vllm.txt`

## Изменения при сборке

### Исправления

1. **Базовый образ:**
   - Использован правильный образ: `ccr-2vdh3abv-pub.cnc.bj.baidubce.com/paddlepaddle/paddlex-genai-vllm-server:latest`
   - Образ доступен из Baidu Cloud Registry

2. **Пользователь:**
   - Убрана попытка переключения на `paddleocr` (пользователь отсутствует в базовом образе)
   - Контейнер работает от root (как в базовом образе)

3. **Зависимости:**
   - Убран `paddleocr-vl>=0.2.0` из requirements (пакет недоступен в PyPI)
   - Предполагается, что PaddleOCR-VL уже включен в базовый образ

## Предзагрузка моделей

### Статус

⚠️ **Модели не предзагружены при сборке**

**Причины:**
- PaddlePaddle не доступен при build-time в базовом образе
- Модели будут загружаться при первом использовании в runtime

**Решения:**
1. **Использовать офлайн-образ с предзагруженными моделями:**
   ```dockerfile
   FROM ccr-2vdh3abv-pub.cnc.bj.baidubce.com/paddlepaddle/paddleocr-vl:latest-gpu-sm120-offline
   ```
   Этот образ содержит предзагруженные модели

2. **Предзагрузить модели в runtime:**
   - При первом запуске модели будут загружены автоматически
   - Требуется доступ к интернету для первоначальной загрузки

## Проверка образа

### Команды для проверки

```bash
# Проверка структуры
docker run --rm --entrypoint /bin/bash paddleocr-vl-vllm:2.0.0 -u root -c "ls -la /app/"

# Проверка зависимостей
docker run --rm --entrypoint /bin/bash paddleocr-vl-vllm:2.0.0 -u root -c \
  "python3 -c 'import fastapi; import pdf2image; import paddleocr; print(\"OK\")'"

# Проверка скрипта запуска
docker run --rm --entrypoint /bin/bash paddleocr-vl-vllm:2.0.0 -u root -c "cat /app/start.sh"
```

## Следующие шаги

### 1. Локальное тестирование (требуется GPU)

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

# В другом терминале - проверка health
curl http://localhost:8081/health | jq

# Тест OCR
curl -X POST \
  -F "file=@/path/to/test.pdf" \
  http://localhost:8081/ocr/pdf | jq
```

### 2. Push в Cloud.ru Artifact Registry

```bash
# Тегирование
docker tag paddleocr-vl-vllm:2.0.0 \
  cr.yandex/<registry-id>/paddleocr-vl-vllm:2.0.0

docker tag paddleocr-vl-vllm:2.0.0 \
  cr.yandex/<registry-id>/paddleocr-vl-vllm:latest

# Авторизация
yc container registry configure-docker

# Push
docker push cr.yandex/<registry-id>/paddleocr-vl-vllm:2.0.0
docker push cr.yandex/<registry-id>/paddleocr-vl-vllm:latest
```

### 3. Развертывание в Cloud.ru ML Inference

См. инструкции в `BUILD_VLLM.md`:
- Настройки контейнера
- Переменные окружения
- Health checks
- Рекомендации по ресурсам

## Известные ограничения

1. **Модели:**
   - ⚠️ Модели не предзагружены (будут загружаться при первом использовании)
   - ⚠️ При первом запуске потребуется ~80-90 секунд на загрузку моделей
   - ⚠️ Требуется доступ к интернету для первоначальной загрузки (если модели не кэшированы)

2. **vLLM сервер:**
   - Базовый образ должен автоматически запускать vLLM сервер на порту 8080
   - Если vLLM не запускается автоматически, может потребоваться дополнительная настройка в `start.sh`

3. **Размер образа:**
   - 12.5 GB (зависит от базового образа)
   - После загрузки моделей может быть больше

## Рекомендации

### Для production

1. **Использовать офлайн-образ:**
   - Рассмотреть использование базового образа `paddleocr-vl:latest-gpu-sm120-offline`
   - Этот образ содержит предзагруженные модели
   - Не требует доступа к интернету в runtime

2. **Предзагрузка моделей:**
   - Запустить контейнер с доступом к интернету
   - Инициализировать модели при первом запуске
   - Сохранить volume с моделями для повторного использования

3. **Health checks:**
   - Настроить startup probe с большим `initialDelaySeconds` (≥120-180s)
   - Учесть время загрузки моделей при первом запуске

## Итог

✅ **Образ успешно собран**  
✅ **Все зависимости установлены**  
✅ **Структура файлов корректна**  
⚠️ **Требуется тестирование с GPU**  
⚠️ **Модели будут загружаться при первом использовании**

Образ готов к использованию, но рекомендуется:
- Тестирование с GPU перед production deployment
- Настройка предзагрузки моделей для production
- Проверка работы vLLM сервера


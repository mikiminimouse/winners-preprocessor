# Отчет о сборке и тестировании версии 2.0.7

## Выполненные действия

### ✅ 1. Сборка образа
```bash
docker build -f paddle_docker_servise/Dockerfile -t docling-granite-258m.cr.cloud.ru/paddleocr-vl-service:2.0.7 .
```
**Результат:** Образ успешно собран
- Image ID: `9e6c047fb9ed`
- Digest: `sha256:0ea4541876b0f5cd2be3b18cc411b5e2cc8e7b7dd2844c693d61069db4806fb1`

### ✅ 2. Push в registry
```bash
docker push docling-granite-258m.cr.cloud.ru/paddleocr-vl-service:2.0.7
docker push docling-granite-258m.cr.cloud.ru/paddleocr-vl-service:latest
```
**Результат:** Образы успешно запушены в Cloud.ru registry

## Изменения в версии 2.0.7

### Улучшения в `server.py`:

1. **Обновлена функция `process_with_paddleocr()`**:
   - ✅ Детальное логирование каждого этапа обработки
   - ✅ Правильная обработка результатов (list, iterator, одиночный объект)
   - ✅ Соответствие официальной документации PaddleOCR-VL

2. **Исправлена функция `save_results_locally()`**:
   - ✅ Использует официальный способ: `for res in output: res.save_to_markdown/json()`
   - ✅ Обработка множественных результатов
   - ✅ Fallback методы при ошибках

3. **Добавлен эндпоинт `/logs`**:
   - ✅ Возвращает последние логи для отладки
   - ✅ Параметр `limit` для ограничения количества строк

## Соответствие официальной документации

✅ Используется официальный pipeline из документации PaddleOCR-VL:

```python
# Инициализация
pipeline = PaddleOCRVL()  # ✅ Официальный способ

# Обработка
output = pipeline.predict(image_path)  # ✅ Официальный способ

# Сохранение
for res in output:
    res.save_to_markdown(save_path="output")  # ✅ Официальный способ
    res.save_to_json(save_path="output")      # ✅ Официальный способ
```

## Следующие шаги (на стороне Cloud.ru ML Inference)

### 1. Обновить контейнер с новым образом

В веб-консоли Cloud.ru ML Inference:
- Перейти в настройки контейнера
- Обновить URI образа на: `docling-granite-258m.cr.cloud.ru/paddleocr-vl-service:2.0.7`
- Или использовать `:latest` (уже указывает на 2.0.7)

### 2. Убедиться, что заданы переменные окружения:

```
USE_CLOUDRU_S3=true
CLOUDRU_S3_ENDPOINT=https://s3.cloud.ru
CLOUDRU_S3_TENANT_ID=502f76f0-9017-493d-bda4-9e1bb278da84
CLOUDRU_S3_KEY_ID=ce94860ccc8780b2bc5f00f31459d24e
CLOUDRU_S3_ACCESS_KEY=502f76f0-9017-493d-bda4-9e1bb278da84:ce94860ccc8780b2bc5f00f31459d24e
CLOUDRU_S3_SECRET_KEY=759469c88d6e450b584e2487c5174770
CLOUDRU_S3_BUCKET=bucket-winners223
CLOUDRU_S3_REGION=ru-central-1
LOG_LEVEL=DEBUG
```

### 3. Перезапустить контейнер

После обновления образа нужно перезапустить контейнер.

### 4. Проверить логи старта

Убедиться, что:
- Модели загружаются корректно
- FastAPI сервер запускается
- PaddleOCR-VL инициализируется

## Тестирование после перезапуска

### Тест 1: Health Check
```bash
curl -X GET "https://<your-url>/health" \
  -H "x-api-key: <API_KEY>"
```

Ожидаемый результат:
```json
{
  "status": "healthy",
  "paddleocr": "ready",
  "s3_storage": "configured",
  ...
}
```

### Тест 2: Обработка изображения с таблицей
```bash
curl -X POST "https://<your-url>/ocr" \
  -H "x-api-key: <API_KEY>" \
  -F "file=@test_images/page_0001 (3).png" \
  -F "return_content=true"
```

Ожидаемый результат:
- `status: "success"`
- `markdown_text` с распознанным текстом
- `json_data` со структурой документа
- `s3_files` со ссылками на загруженные файлы

### Тест 3: Проверка логов
```bash
curl "https://<your-url>/logs?limit=100" \
  -H "x-api-key: <API_KEY>"
```

## Отладка pipeline

### Детальное логирование

В версии 2.0.7 добавлено детальное логирование:
- Инициализация pipeline
- Обработка каждого изображения
- Сохранение результатов
- Ошибки на каждом этапе

Все логи доступны через:
1. Cloud.ru Console (логи контейнера)
2. Эндпоинт `/logs`
3. `docker logs` или `kubectl logs` (если есть доступ)

### Типичные проблемы и решения

1. **502 Gateway Timeout**:
   - Увеличить таймауты ingress/gateway до 600-900 секунд
   - Или тестировать изнутри пода: `curl http://127.0.0.1:8081/ocr`

2. **Модели не загружаются**:
   - Проверить `PADDLEX_HOME` в логах
   - Убедиться, что офлайн-образ содержит модели

3. **S3 загрузка не работает**:
   - Проверить переменные окружения
   - Проверить права сервисного аккаунта на bucket

## Ожидаемые улучшения

С версией 2.0.7:
- ✅ Правильное использование официального pipeline
- ✅ Корректная обработка результатов (включая множественные)
- ✅ Детальное логирование для отладки
- ✅ Эндпоинт для получения логов
- ✅ Улучшенная обработка ошибок

## Дата создания

2025-12-10


# Отчет о деплое PaddleOCR-VL сервиса на Cloud.ru ML Inference

## Обзор

Деплой Docker образа `docling-granite-258m.cr.cloud.ru/paddleocr-vl-service:2.0.21` на Cloud.ru ML Inference выполнен успешно. Образ содержит улучшенный функционал с расширенным Web UI и поддержкой различных режимов работы.

## Конфигурация сервиса

### Основные параметры
- **Образ**: `docling-granite-258m.cr.cloud.ru/paddleocr-vl-service:2.0.21`
- **Режим работы**: Dual Mode (оба сервиса)
- **Порты**:
  - 8081 (FastAPI REST API)
  - 7860 (Gradio Web UI)
- **Ресурсы**:
  - GPU: NVIDIA A100 SXM (1 штука)
  - Память GPU: 80 GB

### Переменные окружения
```bash
# Брендирование
COMPANY_NAME="Winners Preprocessor"

# Пути к моделям (установлены автоматически)
PADDLEX_HOME=/home/paddleocr/.paddlex
HF_HOME=/home/paddleocr/.cache/huggingface
OUTPUT_DIR=/workspace/output

# Отключение проверки подключения к хостерам моделей
DISABLE_MODEL_SOURCE_CHECK=True

# Настройки PaddlePaddle
FLAGS_enable_eager_mode=1
FLAGS_eager_delete_tensor_gb=0
FLAGS_use_mkldnn=0
```

### Health Check
- **Readiness probe**:
  - Тип: `exec`
  - Путь: `/app/health_check.sh`
  - Initial delay: 30 секунд
  - Period: 10 секунд
  
- **Liveness probe**:
  - Тип: `exec`
  - Путь: `/app/health_check.sh`
  - Initial delay: 60 секунд
  - Period: 20 секунд

## Режимы работы

### 1. Dual Mode (по умолчанию)
- **Описание**: Одновременная работа FastAPI и Gradio UI
- **Порты**: 8081 (API) и 7860 (Web UI)
- **Команда**: (по умолчанию, без аргументов)
- **Serverless**: Включить для порта 7860

### 2. Server Mode (только API)
- **Описание**: Только FastAPI сервер
- **Порт**: 8081
- **Команда**: `server`
- **Serverless**: Не требуется

### 3. UI Mode (только Web UI)
- **Описание**: Только Gradio Web UI
- **Порт**: 7860
- **Команда**: `ui`
- **Serverless**: Включить для порта 7860
- **Переменные**:
  - `PORT=7860`

## Новый функционал Web UI

### Дополнительные опции обработки
- Enable chart parsing
- Enable document unwarping
- Enable orientation classification

### Расширенное отображение результатов
- Markdown
- JSON
- Markdown Preview
- Visualization
- Markdown Source

## API Endpoints

### FastAPI (порт 8081)
- `GET /` - Информация о сервисе
- `GET /health` - Проверка здоровья сервиса
- `GET /health/vllm` - Проверка доступности vLLM сервера
- `POST /ocr` - OCR обработка изображений
  - Поддерживаемые форматы: Base64, URL, multipart/form-data
  - Опциональная загрузка результатов в Cloud.ru Object Storage

### Gradio UI (порт 7860)
- Веб-интерфейс для тестирования OCR
- Поддержка загрузки изображений
- Настройка параметров обработки
- Отображение результатов в различных форматах

## Особенности реализации

1. **Офлайн-образ**: Использует предзагруженные модели PaddleOCR-VL (не требует интернета в runtime)
2. **GPU поддержка**: Полная поддержка ускорения на GPU NVIDIA A100
3. **Совместимость**: Полная совместимость с Cloud.ru ML Inference
4. **Сохранение функциональности**: Все существующие возможности FastAPI сохранены
5. **Расширенный Web UI**: Добавлен веб-интерфейс без изменения логики OCR
6. **Автоматическое определение режима**: Поддержка автоматического определения режима работы по переменной `PORT`
7. **Надежный health check**: Включает надежный механизм проверки состояния
8. **Три режима работы**: Поддержка режимов Dual, Server, UI
9. **Одновременная работа**: Поддержка одновременной работы обоих сервисов в Dual Mode

## Тестирование

### Доступность сервисов
- **Web UI**: `http://<service-url>:7860`
- **API Health**: `http://<service-url>:8081/health`
- **OCR обработка**: `POST http://<service-url>:8081/ocr`

### Проверка функциональности
1. Загрузка изображений через Web UI
2. Обработка изображений через API
3. Проверка сохранения результатов
4. Тестирование всех вкладок Web UI
5. Проверка дополнительных опций обработки

## Следующие шаги

1. Провести полное тестирование функциональности
2. Настроить мониторинг и логирование
3. При необходимости внести корректировки в конфигурацию
4. Подготовить документацию для пользователей

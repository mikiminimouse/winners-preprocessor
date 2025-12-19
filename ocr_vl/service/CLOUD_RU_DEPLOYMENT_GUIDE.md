# Руководство по развертыванию PaddleOCR-VL Service в Cloud.ru ML Inference

## Обзор

Этот документ содержит рекомендации по развертыванию и настройке PaddleOCR-VL Service в среде Cloud.ru ML Inference с использованием новой системы управления режимами работы через переменную окружения `MODE`.

## Режимы работы сервиса

Сервис поддерживает три режима работы, контролируемые через переменную окружения `MODE`:

1. **`MODE=ui`** - Запуск только Gradio Web UI на порту 7860 (serverless режим)
2. **`MODE=server`** - Запуск только FastAPI сервера на порту 8081
3. **`MODE=dual`** - Запуск обоих сервисов (порт 7860 для UI, порт 8081 для сервера)

## Настройка в Cloud.ru ML Inference

### Serverless режим (только Web UI)

Для использования в serverless режиме (только Web UI):

1. В настройках контейнера установите:
   - **Image**: `docling-granite-258m.cr.cloud.ru/paddleocr-vl-service:2.0.25`
   - **Environment Variables**:
     - `MODE=ui`
     - `DISABLE_MODEL_SOURCE_CHECK=True` (установлено по умолчанию)
   - **Port**: 7860

2. Этот режим идеально подходит для интерактивной работы с интерфейсом и требует минимальных ресурсов.

### Полный режим (оба сервиса)

Для использования полного функционала сервиса с обоими сервисами:

1. В настройках контейнера установите:
   - **Image**: `docling-granite-258m.cr.cloud.ru/paddleocr-vl-service:2.0.25`
   - **Environment Variables**:
     - `MODE=dual`
     - `DISABLE_MODEL_SOURCE_CHECK=True` (установлено по умолчанию)
   - **Primary Port**: 7860 (для Web UI)
   - **Additional Port**: 8081 (для FastAPI)

2. Добавьте дополнительный порт 8081:
   - Перейдите на вкладку "Дополнительные порты"
   - Нажмите "Добавить порт"
   - Укажите номер порта 8081

## Health Check настройки

Для корректной работы механизмов автоматического масштабирования и мониторинга, настройте health check следующим образом:

### Для режима UI (serverless)
- **Health Check Type**: Exec
- **Command**: `/app/health_check.sh`
- **Environment Variables**: `MODE=ui`

### Для режима Server
- **Health Check Type**: Exec
- **Command**: `/app/health_check.sh`
- **Environment Variables**: `MODE=server`

### Для режима Dual
- **Health Check Type**: Exec
- **Command**: `/app/health_check.sh`
- **Environment Variables**: `MODE=dual`

## Рекомендации по использованию

### Рекомендуемые режимы для различных сценариев

1. **Интерактивная работа с интерфейсом**:
   - Используйте `MODE=ui` с основным портом 7860
   - Подходит для демонстраций и тестирования

2. **API интеграция**:
   - Используйте `MODE=server` с портом 8081
   - Подходит для интеграции с другими системами

3. **Полнофункциональное развертывание**:
   - Используйте `MODE=dual` с основным портом 7860 и дополнительным портом 8081
   - Подходит для production среды

### Переменные окружения

Следующие переменные окружения доступны для настройки:

- `MODE` - Режим работы сервиса (ui, server, dual)
- `DISABLE_MODEL_SOURCE_CHECK` - Отключение проверки источников моделей (по умолчанию True)
- `OUTPUT_DIR` - Директория для сохранения результатов (по умолчанию /workspace/output)
- `LOG_LEVEL` - Уровень логирования (по умолчанию DEBUG)
- `COMPANY_NAME` - Название компании для отображения в интерфейсе

## Устранение неполадок

### Частые проблемы и их решения

1. **Сервис не запускается**:
   - Проверьте, что установлена правильная переменная `MODE`
   - Убедитесь, что указаны правильные порты

2. **Health check не проходит**:
   - Проверьте, что переменная `MODE` в health check совпадает с режимом запуска
   - Убедитесь, что порты доступны

3. **Проблемы с подключением к API**:
   - В режиме `MODE=ui` FastAPI недоступен
   - Используйте `MODE=dual` или `MODE=server` для доступа к API

## Примеры конфигураций

### Конфигурация для serverless режима

```yaml
image: docling-granite-258m.cr.cloud.ru/paddleocr-vl-service:2.0.25
environment:
  MODE: ui
  DISABLE_MODEL_SOURCE_CHECK: "True"
ports:
  - 7860
health_check:
  type: exec
  command: /app/health_check.sh
  environment:
    MODE: ui
```

### Конфигурация для полного режима

```yaml
image: docling-granite-258m.cr.cloud.ru/paddleocr-vl-service:2.0.25
environment:
  MODE: dual
  DISABLE_MODEL_SOURCE_CHECK: "True"
ports:
  - 7860
  - 8081
health_check:
  type: exec
  command: /app/health_check.sh
  environment:
    MODE: dual
```

## Версии образов

- **Текущая версия**: 2.0.25
- **Стабильная версия**: latest
- **Предыдущие версии**: 2.0.24, 2.0.23, 2.0.22

Рекомендуется использовать тег `latest` для получения последней стабильной версии или конкретный номер версии для воспроизводимости.

# Отчет о завершении push образа в Artifact Registry Cloud.ru

## Статус операции

✅ **PUSH ОБРАЗА ВЫПОЛНЕН УСПЕШНО**

## Выполненные действия

### 1. Push основного образа
- **Образ**: `docling-granite-258m.cr.cloud.ru/paddleocr-vl-service:2.0.21`
- **Статус**: ✅ Успешно загружен
- **Digest**: `sha256:8506f725d2aadf6560faeecc472d5df56fbae4053a86e00c3153baf290b1e785`

### 2. Обновление тега latest
- **Образ**: `docling-granite-258m.cr.cloud.ru/paddleocr-vl-service:latest`
- **Статус**: ✅ Успешно обновлен
- **Digest**: `sha256:8506f725d2aadf6560faeecc472d5df56fbae4053a86e00c3153baf290b1e785`

### 3. Проверка доступности образов
- **Тег 2.0.21**: ✅ Доступен для скачивания
- **Тег latest**: ✅ Доступен для скачивания

## Информация об образе

### Repository
`docling-granite-258m.cr.cloud.ru/paddleocr-vl-service`

### Теги
- `2.0.21` - основная версия с улучшениями
- `latest` - последняя стабильная версия

### Размер
~12.5GB (включая предзагруженные модели PaddleOCR-VL)

## Готовность к следующим шагам

✅ **Деплой** на ML Inference
✅ **Тестирование** через веб-интерфейс и API

## Инструкция по использованию

### Pull образа
```bash
# Pull конкретной версии
docker pull docling-granite-258m.cr.cloud.ru/paddleocr-vl-service:2.0.21

# Pull последней версии
docker pull docling-granite-258m.cr.cloud.ru/paddleocr-vl-service:latest
```

### Запуск контейнера
```bash
# Dual Mode (по умолчанию) - оба сервиса
docker run -d -p 8081:8081 -p 7860:7860 docling-granite-258m.cr.cloud.ru/paddleocr-vl-service:2.0.21

# Server Mode - только API
docker run -d -p 8081:8081 docling-granite-258m.cr.cloud.ru/paddleocr-vl-service:2.0.21 server

# UI Mode - только Web UI
docker run -d -p 7860:7860 docling-granite-258m.cr.cloud.ru/paddleocr-vl-service:2.0.21 ui
```

## Заключение

Образ успешно загружен в Artifact Registry Cloud.ru и готов к использованию в production среде. Все теги доступны и функционируют корректно.

# Инструкция по использованию PaddleOCR-VL сервиса

## Обзор

PaddleOCR-VL сервис предоставляет мощные возможности для OCR обработки документов с помощью искусственного интеллекта. Сервис включает как программный API, так и веб-интерфейс для удобного тестирования.

## Веб-интерфейс (порт 7860)

### Доступ к интерфейсу

Откройте в браузере адрес: `http://<service-url>:7860`

### Использование Web UI

1. **Загрузка документа**:
   - Нажмите на область загрузки изображения или перетащите файл
   - Поддерживаются форматы: PNG, JPG, JPEG

2. **Настройка параметров обработки**:
   - **Enable chart parsing**: Включение распознавания диаграмм
   - **Enable document unwarping**: Включение коррекции искажений документа
   - **Enable orientation classification**: Включение классификации ориентации

3. **Выбор формата вывода**:
   - **Markdown**: Только структурированный текст
   - **JSON**: Только данные в формате JSON
   - **Оба**: Markdown и JSON одновременно

4. **Обработка документа**:
   - Нажмите кнопку "Обработать документ"
   - Дождитесь завершения обработки

5. **Просмотр результатов**:
   - **Markdown**: Структурированный текст с сохранением форматирования
   - **JSON**: Данные в формате JSON для программной обработки
   - **Markdown Preview**: Предварительный просмотр с визуализацией
   - **Visualization**: Визуализация структуры документа
   - **Markdown Source**: Исходный код Markdown

## API (порт 8081)

### Базовая информация

- **Базовый URL**: `http://<service-url>:8081`
- **Swagger UI**: `http://<service-url>:8081/docs`
- **ReDoc**: `http://<service-url>:8081/redoc`

### Эндпоинты

#### Проверка здоровья сервиса
```
GET /health
```
Возвращает статус здоровья сервиса.

#### OCR обработка изображений
```
POST /ocr
Content-Type: application/json
```

##### Загрузка Base64 изображения:
```json
{
  "base64_image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
}
```

##### Загрузка изображения по URL:
```json
{
  "image_url": "https://example.com/document.png"
}
```

##### Загрузка файла через multipart/form-data:
```bash
curl -X POST "http://<service-url>:8081/ocr" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.png"
```

### Ответ API

Успешный ответ содержит:
- **markdown**: Структурированный текст документа
- **json**: Данные в формате JSON
- **s3_links** (опционально): Ссылки на файлы в Cloud.ru Object Storage

## Примеры использования

### Python (с использованием requests)

```python
import requests
import base64

# Загрузка изображения по URL
response = requests.post(
    "http://<service-url>:8081/ocr",
    json={"image_url": "https://example.com/document.png"}
)
result = response.json()
print(result["markdown"])

# Загрузка Base64 изображения
with open("document.png", "rb") as f:
    encoded = base64.b64encode(f.read()).decode('utf-8')
    
response = requests.post(
    "http://<service-url>:8081/ocr",
    json={"base64_image": f"data:image/png;base64,{encoded}"}
)
result = response.json()
print(result["json"])
```

### cURL

```bash
# Загрузка файла
curl -X POST "http://<service-url>:8081/ocr" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.png"

# Загрузка по URL
curl -X POST "http://<service-url>:8081/ocr" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{"image_url": "https://example.com/document.png"}'
```

## Поддерживаемые функции

### Распознавание текста
- Русский язык
- Английский язык
- Смешанные языки

### Анализ структуры документов
- Заголовки
- Параграфы
- Таблицы
- Списки
- Диаграммы (при включении опции)

### Форматы вывода
- **Markdown**: Структурированный текст с сохранением форматирования
- **JSON**: Машиночитаемый формат с детальной информацией

## Рекомендации по использованию

### Для лучшего качества распознавания:
1. Используйте изображения высокого качества
2. Обеспечьте хорошее освещение при сканировании
3. Избегайте сильных искажений перспективы
4. При необходимости включите опцию "Enable document unwarping"

### При работе с таблицами:
1. Включите опцию "Enable chart parsing"
2. Убедитесь, что таблицы четко видны на изображении

### При обработке повернутых документов:
1. Включите опцию "Enable orientation classification"
2. Сервис автоматически определит и скорректирует ориентацию

## Устранение неполадок

### Частые проблемы и решения:

1. **Сервис недоступен**:
   - Проверьте, запущен ли контейнер
   - Убедитесь, что порты открыты
   - Проверьте логи сервиса

2. **Низкое качество распознавания**:
   - Попробуйте включить дополнительные опции обработки
   - Убедитесь, что изображение хорошего качества
   - Проверьте, правильно ли ориентирован документ

3. **Ошибки при загрузке изображений**:
   - Проверьте формат изображения (PNG, JPG, JPEG)
   - Убедитесь, что размер файла не превышает допустимый лимит
   - Проверьте URL при загрузке по ссылке

### Логи и диагностика

Для диагностики проблем проверьте логи сервиса:
```bash
docker logs <container-name>
```

## Поддержка

При возникновении проблем обращайтесь в техническую поддержку:
- Email: tech-support@company.com
- Внутренний чат: #ocr-support

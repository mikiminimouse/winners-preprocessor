# OCR_VL стек

## Описание

OCR_VL стек - Docker сервис для OCR обработки документов с использованием PaddleOCR-VL.

## Компоненты

- **service/** - основной Docker сервис с FastAPI
- **tests/** - тесты сервиса
- **docs/** - документация
- **scripts/** - скрипты сборки и деплоя

## Технологии

- PaddleOCR-VL (офлайн-образ с предзагруженными моделями)
- FastAPI для REST API
- Cloud.ru Object Storage для хранения результатов

## Быстрый старт

### Сборка образа

```bash
cd ocr_vl/service
docker build -t paddleocr-vl-service:latest .
```

### Запуск контейнера

```bash
docker run -p 8081:8081 \
  -e CLOUDRU_S3_ENDPOINT=https://s3.cloud.ru \
  -e CLOUDRU_S3_BUCKET=bucket-winners223 \
  -e CLOUDRU_S3_ACCESS_KEY=your-key \
  -e CLOUDRU_S3_SECRET_KEY=your-secret \
  paddleocr-vl-service:latest
```

### Тестирование

```bash
cd ocr_vl/tests
python3 test_ocr_local.py
```

## API Endpoints

- `GET /health` - проверка здоровья сервиса
- `POST /ocr` - OCR обработка изображения
- `GET /files` - список сохраненных файлов
- `GET /files/{file_type}/{filename}` - получение файла
- `POST /test/s3-upload` - тестовая загрузка в S3

## Документация

- [API документация](API.md)
- [Deployment](DEPLOYMENT.md)
- [Version History](VERSION_HISTORY.md)


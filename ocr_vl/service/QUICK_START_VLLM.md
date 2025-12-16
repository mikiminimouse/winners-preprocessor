# Быстрый старт: Variant B (vLLM)

## Сборка образа

```bash
cd /root/winners_preprocessor/paddle_docker_servise

# Сборка
docker build -f Dockerfile.vllm -t paddleocr-vl-vllm:2.0.0 .

# Проверка размера образа
docker images | grep paddleocr-vl-vllm
```

## Локальный запуск для тестирования

```bash
# Запуск контейнера
docker run --gpus all \
  -p 8081:8081 \
  -v $(pwd)/output:/workspace/output \
  -e PADDLEX_HOME=/home/paddleocr/.paddlex \
  -e OUTPUT_DIR=/workspace/output \
  paddleocr-vl-vllm:2.0.0

# В другом терминале - проверка health
curl http://localhost:8081/health | jq

# Тест OCR
curl -X POST \
  -F "file=@/path/to/test.pdf" \
  http://localhost:8081/ocr/pdf | jq
```

## Push в Cloud.ru Artifact Registry

```bash
# Тегирование
docker tag paddleocr-vl-vllm:2.0.0 \
  cr.yandex/<registry-id>/paddleocr-vl-vllm:2.0.0

docker tag paddleocr-vl-vllm:2.0.0 \
  cr.yandex/<registry-id>/paddleocr-vl-vllm:latest

# Авторизация (если еще не авторизованы)
yc container registry configure-docker

# Push
docker push cr.yandex/<registry-id>/paddleocr-vl-vllm:2.0.0
docker push cr.yandex/<registry-id>/paddleocr-vl-vllm:latest
```

## Проверка предзагруженных моделей

```bash
# Проверка наличия моделей в образе
docker run --rm --entrypoint /bin/bash \
  paddleocr-vl-vllm:2.0.0 \
  -c "find /home/paddleocr/.paddlex/official_models -type d -maxdepth 1"

# Ожидаемый вывод (примерно):
# /home/paddleocr/.paddlex/official_models
# /home/paddleocr/.paddlex/official_models/PP-StructureV2
# /home/paddleocr/.paddlex/official_models/PaddleOCR-VL
# /home/paddleocr/.paddlex/official_models/PP-OCRv4
```

## Важные замечания

1. **Размер образа:** Будет ~8-10GB из-за предзагруженных моделей
2. **Время сборки:** 10-30 минут (зависит от скорости интернета для загрузки моделей)
3. **GPU требуется:** Да, для работы моделей (особенно при warmup)
4. **Первый запуск:** Может занять 1-2 минуты для инициализации моделей

## Структура файлов

```
paddle_docker_servise/
├── Dockerfile.vllm          # Основной Dockerfile
├── server_vllm.py           # FastAPI сервер (Variant B)
├── start_vllm.sh            # Скрипт запуска
├── warmup_vllm.py           # Скрипт прогрева
├── preload_models.py        # Предзагрузка моделей (build-time)
├── requirements_vllm.txt    # Зависимости
├── BUILD_VLLM.md           # Полная документация
└── QUICK_START_VLLM.md     # Этот файл
```


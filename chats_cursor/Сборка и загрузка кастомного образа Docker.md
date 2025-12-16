# Сборка и загрузка кастомного образа Docker
_Exported on 02/12/2025 at 21:56:41 GMT+7 from Cursor (2.1.46)_

---

**User**

выполни ! >>

Собрать кастомный образ:
docker build -f Dockerfile.custom -t docling-serve-cu128-custom:latest .
Загрузить в Cloud.ru:
docker tag docling-serve-cu128-custom:latest \  docling-granite-258m.cr.cloud.ru/docling-serve-cu128-custom:latestdocker push docling-granite-258m.cr.cloud.ru/docling-serve-cu128-custom:latest
Настройки ML Inference:
Образ: docling-granite-258m.cr.cloud.ru/docling-serve-cu128-custom:latestПорт: 5001GPU: A100 16GBRAM: 32GBПеременные окружения:HF_HOME=/opt/app-root/src/.cache/huggingfaceTRANSFORMERS_CACHE=/opt/app-root/src/.cache/docling/modelsDOCLING_VLM_MODEL=granite_docling



Проверяю наличие необходимых файлов и готовлю команды для выполнения:





[3 tools called]





Создаю скрипт для автоматизации. В ask mode команды не выполняются, поэтому подготовлю готовый скрипт для запуска:



```bash

#!/bin/bash

# Скрипт для сборки и загрузки кастомного образа docling-serve-cu128-custom



set -e



cd /root/winners_preprocessor/cloudru_service



echo "======================================"

echo "СБОРКА И ЗАГРУЗКА DOCLING-SERVE-CU128-CUSTOM"

echo "======================================"



# Credentials Cloud.ru

REGISTRY="docling-granite-258m.cr.cloud.ru"

KEY_ID="7d6d56e6ab8bd89a869fdaec8f5abf88"

KEY_SECRET="aba749b45613a762247ad0ebaaee9a2a"

IMAGE_NAME="docling-serve-cu128-custom"



echo ""

echo "Шаг 1: Аутентификация в Cloud.ru Artifact Registry..."

docker login $REGISTRY -u $KEY_ID -p $KEY_SECRET



echo ""

echo "Шаг 2: Сборка кастомного образа..."

echo "Это может занять 10-20 минут (загрузка модели ~1-2GB)..."

docker build -f Dockerfile.custom -t $IMAGE_NAME:latest .



echo ""

echo "Шаг 3: Перетегирование для Cloud.ru..."

docker tag $IMAGE_NAME:latest $REGISTRY/$IMAGE_NAME:latest



echo ""

echo "Шаг 4: Загрузка образа в Cloud.ru Artifact Registry..."

echo "Это может занять 5-15 минут в зависимости от скорости сети..."

docker push $REGISTRY/$IMAGE_NAME:latest



echo ""

echo "======================================"

echo "✅ ГОТОВО!"

echo "======================================"

echo ""

echo "Образ загружен: $REGISTRY/$IMAGE_NAME:latest"

echo ""

echo "Следующие шаги:"

echo "1. Перейти в Cloud.ru → AI Factory → ML Inference"

echo "2. Создать новый ML Inference с параметрами:"

echo "   - Docker образ URI: $REGISTRY/$IMAGE_NAME:latest"

echo "   - Порт: 5001"

echo "   - GPU: A100 16GB"

echo "   - RAM: 32GB"

echo "   - Переменные окружения:"

echo "     HF_HOME=/opt/app-root/src/.cache/huggingface"

echo "     TRANSFORMERS_CACHE=/opt/app-root/src/.cache/docling/models"

echo "     DOCLING_VLM_MODEL=granite_docling"

echo "   - Liveness: HTTP GET /health, начальная задержка 180s"

echo ""

```



Сохраните как `build_and_push_custom.sh` и выполните:



```bash

chmod +x build_and_push_custom.sh

./build_and_push_custom.sh

```



Или выполните команды по отдельности:



```bash

cd /root/winners_preprocessor/cloudru_service



# 1. Аутентификация

docker login docling-granite-258m.cr.cloud.ru \

  -u 7d6d56e6ab8bd89a869fdaec8f5abf88 \

  -p aba749b45613a762247ad0ebaaee9a2a



# 2. Сборка образа (10-20 минут)

docker build -f Dockerfile.custom -t docling-serve-cu128-custom:latest .



# 3. Перетегирование

docker tag docling-serve-cu128-custom:latest \

  docling-granite-258m.cr.cloud.ru/docling-serve-cu128-custom:latest



# 4. Загрузка (5-15 минут)

docker push docling-granite-258m.cr.cloud.ru/docling-serve-cu128-custom:latest

```



Важно:

- Сборка займет 10–20 минут (загрузка модели ~1–2GB)

- Загрузка в Cloud.ru — 5–15 минут

- Убедитесь, что есть доступ к интернету для загрузки модели из Hugging Face



После загрузки создайте ML Inference с указанными параметрами.



Переключитесь в agent mode, если нужно, чтобы я выполнил команды автоматически.

---

**Cursor**

Проверяю наличие необходимых файлов, затем выполню сборку и загрузку образа.


Выполняю команды по порядку: сначала аутентификация, затем сборка и загрузка образа.


Аутентификация успешна. Собираю кастомный образ (может занять 10–20 минут из‑за загрузки модели):


Образ собран. Перетегирую для Cloud.ru:


Загружаю образ в Cloud.ru Artifact Registry (может занять несколько минут):


**Все операции выполнены успешно.**

## Выполненные шаги:

1. Аутентификация в Cloud.ru Artifact Registry — успешно
2. Сборка кастомного образа `docling-serve-cu128-custom:latest` — успешно
3. Перетегирование образа для Cloud.ru — успешно
4. Загрузка образа в Cloud.ru — успешно

Образ доступен: `docling-granite-258m.cr.cloud.ru/docling-serve-cu128-custom:latest`

## Следующие шаги для настройки ML Inference:

Перейдите в Cloud.ru → AI Factory → ML Inference и создайте новый ML Inference со следующими параметрами:

- **Docker образ URI**: `docling-granite-258m.cr.cloud.ru/docling-serve-cu128-custom:latest`
- **Порт**: `5001`
- **GPU**: `A100 16GB`
- **RAM**: `32GB`
- **Переменные окружения**:
  - `HF_HOME=/opt/app-root/src/.cache/huggingface`
  - `TRANSFORMERS_CACHE=/opt/app-root/src/.cache/docling/models`
  - `DOCLING_VLM_MODEL=granite_docling`
- **Liveness**: HTTP GET `/health`, начальная задержка `180s`

Образ содержит предзагруженную модель Granite Docling 258M и готов к использованию.


# Руководство по настройке S3 для Cloud.ru ML Inference

## Правильные переменные окружения для Docker Run

### Обязательные переменные:

```bash
USE_CLOUDRU_S3=true
CLOUDRU_S3_ENDPOINT=https://s3.cloud.ru
CLOUDRU_S3_BUCKET=bucket-winners223
CLOUDRU_S3_REGION=ru-central-1
CLOUDRU_S3_ACCESS_KEY=502f76f0-9017-493d-bda4-9e1bb278da84:ce94860ccc8780b2bc5f00f31459d24e
CLOUDRU_S3_SECRET_KEY=759469c88d6e450b584e2487c5174770
```

### ⚠️ КРИТИЧНО: Формат `CLOUDRU_S3_ACCESS_KEY`

**Cloud.ru требует формат `tenant_id:key_id`** (НЕ просто `key_id`):

```
ПРАВИЛЬНО: CLOUDRU_S3_ACCESS_KEY=502f76f0-9017-493d-bda4-9e1bb278da84:ce94860ccc8780b2bc5f00f31459d24e
           └──────────────────────────────────────┘ └──────────────────────────────────────┘
                        tenant_id                                 key_id

НЕПРАВИЛЬНО: CLOUDRU_S3_ACCESS_KEY=ce94860ccc8780b2bc5f00f31459d24e  # только key_id
```

## Настройка в Cloud.ru ML Inference (веб-консоль)

В разделе **"Environment Variables"** контейнера добавьте:

| Переменная | Значение |
|------------|----------|
| `USE_CLOUDRU_S3` | `true` |
| `CLOUDRU_S3_ENDPOINT` | `https://s3.cloud.ru` |
| `CLOUDRU_S3_BUCKET` | `bucket-winners223` |
| `CLOUDRU_S3_REGION` | `ru-central-1` |
| `CLOUDRU_S3_ACCESS_KEY` | `502f76f0-9017-493d-bda4-9e1bb278da84:ce94860ccc8780b2bc5f00f31459d24e` |
| `CLOUDRU_S3_SECRET_KEY` | `759469c88d6e450b584e2487c5174770` |

## Пример Docker Run команды

```bash
docker run --gpus all -p 8081:8081 \
  -e USE_CLOUDRU_S3=true \
  -e CLOUDRU_S3_ENDPOINT=https://s3.cloud.ru \
  -e CLOUDRU_S3_BUCKET=bucket-winners223 \
  -e CLOUDRU_S3_REGION=ru-central-1 \
  -e CLOUDRU_S3_ACCESS_KEY=502f76f0-9017-493d-bda4-9e1bb278da84:ce94860ccc8780b2bc5f00f31459d24e \
  -e CLOUDRU_S3_SECRET_KEY=759469c88d6e450b584e2487c5174770 \
  -e LOG_LEVEL=DEBUG \
  docling-granite-258m.cr.cloud.ru/paddleocr-vl-service:2.0.8
```

## Проверка настройки

### 1. Проверка через Health Check

```bash
curl -X GET "https://<your-url>/health" \
  -H "x-api-key: <API_KEY>"
```

Ожидаемый результат:
```json
{
  "status": "healthy",
  "paddleocr": "ready",
  "s3_storage": "configured",  // ✅ должно быть "configured"
  ...
}
```

### 2. Проверка через тест обработки

После обработки изображения в ответе должно быть:

```json
{
  "status": "success",
  "s3_files": {
    "status": "uploaded",  // ✅ должно быть "uploaded"
    "markdown": "https://bucket-winners223.s3.cloud.ru/ocr-results/...",
    "json": "https://bucket-winners223.s3.cloud.ru/ocr-results/..."
  }
}
```

## Формат публичных URL

После успешной загрузки результаты доступны по URL:

```
https://bucket-winners223.s3.cloud.ru/ocr-results/<timestamp>_<filename>.md
https://bucket-winners223.s3.cloud.ru/ocr-results/<timestamp>_<filename>.json
```

## Типичные ошибки

### ❌ Ошибка: `InvalidAccessKeyId`

**Причина:** Неправильный формат `CLOUDRU_S3_ACCESS_KEY`

**Решение:** Использовать формат `tenant_id:key_id`:
```
CLOUDRU_S3_ACCESS_KEY=502f76f0-9017-493d-bda4-9e1bb278da84:ce94860ccc8780b2bc5f00f31459d24e
```

### ❌ Ошибка: `Access Denied`

**Причина:** Недостаточно прав у сервисного аккаунта

**Решение:** Проверить права на bucket `bucket-winners223`:
- `s3:PutObject` - для загрузки файлов
- `s3:GetObject` - для чтения файлов (опционально)

### ❌ Ошибка: `Bucket not found`

**Причина:** Неправильное имя bucket или bucket не существует

**Решение:** Проверить имя bucket в консоли Cloud.ru

## Проверка качества результатов в S3

### 1. Скачать файл из S3

```bash
# Через curl (если bucket публичный)
curl -O "https://bucket-winners223.s3.cloud.ru/ocr-results/<filename>.md"

# Или через boto3
python3 - <<'PY'
import boto3

s3 = boto3.client(
    's3',
    endpoint_url='https://s3.cloud.ru',
    aws_access_key_id='502f76f0-9017-493d-bda4-9e1bb278da84:ce94860ccc8780b2bc5f00f31459d24e',
    aws_secret_access_key='759469c88d6e450b584e2487c5174770',
    region_name='ru-central-1'
)

# Список файлов
objects = s3.list_objects_v2(Bucket='bucket-winners223', Prefix='ocr-results/')
for obj in objects.get('Contents', []):
    print(f"{obj['Key']} - {obj['Size']} bytes")

# Скачать файл
s3.download_file('bucket-winners223', 'ocr-results/<filename>.md', 'downloaded.md')
PY
```

### 2. Проверить содержимое

- **Markdown файл**: должен содержать структурированный текст с таблицами, заголовками
- **JSON файл**: должен содержать структурированные данные с координатами, текстом, типами блоков

## Логирование

Для отладки S3 включите детальное логирование:

```bash
LOG_LEVEL=DEBUG
```

В логах вы увидите:
- Инициализацию S3 клиента
- Формат ACCESS_KEY (tenant_id:key_id или key_id_only)
- Детали загрузки каждого файла
- Ошибки с полным описанием

## Резюме

✅ **Правильный формат переменных:**
- `USE_CLOUDRU_S3=true` - включить S3
- `CLOUDRU_S3_ACCESS_KEY=tenant_id:key_id` - формат критичен!
- Все остальные переменные как указано выше

✅ **Проверка:**
- Health check должен показывать `"s3_storage": "configured"`
- После обработки в ответе должно быть `"s3_files": {"status": "uploaded"}`

✅ **Результаты:**
- Доступны по URL: `https://bucket-winners223.s3.cloud.ru/ocr-results/...`
- Формат: Markdown и JSON


# Инструкция по проверке обработки и S3 загрузки

## 🔍 Что проверить в логах контейнера (Cloud.ru Console)

### 1. Логи инициализации S3 (при старте)

**Ищите после строки "Starting FastAPI handler...":**

```
✅ Хорошо, если видите:
- "S3 bucket verified: bucket-winners223 (correct)"
- "✅ S3 client initialized successfully for bucket: bucket-winners223"
- "✅ S3 bucket access verified: bucket-winners223"

⚠️ Если видите:
- "⚠️  S3 bucket access test failed" - не критично, клиент все равно работает
```

### 2. Логи обработки запроса

**После отправки запроса на `/ocr` ищите:**

#### Этап 1: Обработка изображения
```
✅ "Processing image with PaddleOCR-VL: /app/temp/..."
✅ "PaddleOCR-VL processing completed successfully; init=X.XXs run=Y.YYs total=Z.ZZs"
```

#### Этап 2: Сохранение локально
```
✅ "Results saved locally: /app/output/..., /app/output/..."
✅ "Markdown saved: /app/output/..."
✅ "JSON saved: /app/output/..."
```

#### Этап 3: Проверка файлов перед S3
```
✅ "Verifying local files before S3 upload:"
✅ "  MD: ... - exists: True, size: XXX bytes"
✅ "  JSON: ... - exists: True, size: XXX bytes"
✅ "✅ Markdown file created successfully: XXX bytes"
✅ "✅ JSON file created successfully: XXX bytes"
```

#### Этап 4: Загрузка в S3
```
✅ "S3 upload started: bucket=bucket-winners223 (verifying: bucket-winners223)"
✅ "  Markdown: ... -> s3://bucket-winners223/ocr-results/... (XXX bytes)"
✅ "  JSON: ... -> s3://bucket-winners223/ocr-results/... (XXX bytes)"
✅ "✅ Markdown uploaded: s3://bucket-winners223/ocr-results/..."
✅ "✅ JSON uploaded: s3://bucket-winners223/ocr-results/..."
✅ "✅ Verified: Markdown file exists in S3"
✅ "✅ Verified: JSON file exists in S3"
✅ "✅ S3 upload completed successfully"
```

### 3. Ошибки (если есть)

#### Ошибки S3:
```
❌ "S3 upload failed (ClientError): ..."
❌ "S3 upload failed (BotoCoreError): ..."
❌ "Cannot access bucket: ..."
❌ "Bucket mismatch: ..."
```

#### Ошибки обработки:
```
❌ "PaddleOCR processing failed: ..."
❌ "Failed to save results locally: ..."
❌ "Markdown file not found"
❌ "JSON file is empty"
```

---

## 📊 Интерпретация результатов

### Сценарий A: Обработка завершилась, S3 работает

**В логах видно:**
- ✅ Все этапы 1-4 завершились успешно
- ✅ "S3 upload completed successfully"

**Действие:**
- Файлы **должны быть в S3**, несмотря на 502
- Проверьте S3 через несколько минут
- **Gateway Timeout не прервал обработку** - она завершилась на сервере

### Сценарий B: Gateway прервал обработку

**В логах:**
- ✅ Видны этапы 1-2 (обработка и сохранение)
- ❌ Нет этапов 3-4 (S3 загрузка не началась)

**Действие:**
- **Gateway Timeout прервал обработку** до начала S3 загрузки
- Нужно **увеличить Gateway Timeout** до 300-600 секунд

### Сценарий C: Обработка завершилась, но S3 не работает

**В логах:**
- ✅ Видны этапы 1-3 (обработка, сохранение, проверка файлов)
- ❌ Ошибки на этапе 4 (S3 загрузка)

**Действие:**
- Исправить проблему S3 (credentials, права, bucket)
- Файлы сохранены локально, но не загружены в S3

---

## ✅ Проверка файлов в S3

### Через Cloud.ru Console:
1. Object Storage → bucket-winners223
2. Директория: `ocr-results/`
3. Проверить файлы с временем после запроса

### Через Python скрипт:
```python
import boto3
from datetime import datetime

s3 = boto3.client(
    's3',
    endpoint_url='https://s3.cloud.ru',
    aws_access_key_id='502f76f0-9017-493d-bda4-9e1bb278da84:ce94860ccc8780b2bc5f00f31459d24e',
    aws_secret_access_key='759469c88d6e450b584e2487c5174770',
    region_name='ru-central-1'
)

# Все файлы
objects = s3.list_objects_v2(Bucket='bucket-winners223', Prefix='ocr-results/')
for obj in sorted(objects.get('Contents', []), key=lambda x: x['LastModified'], reverse=True)[:10]:
    print(f"{obj['Key']} - {obj['Size']} bytes - {obj['LastModified']}")
```

---

## 🎯 Что делать дальше

1. **Сначала:** Проверьте логи контейнера в Cloud.ru Console
2. **Затем:** Определите, какой сценарий (A, B, или C)
3. **Действие:**
   - Сценарий A: Увеличить Gateway Timeout для возврата результата через API
   - Сценарий B: Увеличить Gateway Timeout (критично!)
   - Сценарий C: Исправить S3 (credentials, права, bucket)

---

**Важно:** Логи покажут реальную ситуацию - завершается ли обработка и работает ли S3 загрузка!


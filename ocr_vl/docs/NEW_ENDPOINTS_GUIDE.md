# Руководство по новым API endpoints

**Дата:** 2025-12-10  
**Версия:** 2.0.10

---

## 📋 Новые endpoints

### 1. GET `/files` - Список сохраненных файлов

**Описание:**  
Получить список всех сохраненных MD и JSON файлов с результатами OCR обработки.

**Параметры:**
- `file_type` (опционально): Фильтр по типу - `md` или `json`
- `limit` (опционально): Максимальное количество файлов (1-200, по умолчанию: 50)

**Примеры запросов:**

```bash
# Получить все файлы (до 50)
curl -X GET "https://<url>/files" \
  -H "x-api-key: <API_KEY>"

# Получить только MD файлы
curl -X GET "https://<url>/files?file_type=md" \
  -H "x-api-key: <API_KEY>"

# Получить только JSON файлы
curl -X GET "https://<url>/files?file_type=json&limit=100" \
  -H "x-api-key: <API_KEY>"
```

**Пример ответа:**

```json
{
  "status": "success",
  "count": 2,
  "files": [
    {
      "filename": "20251210_120530_page_0001.md",
      "type": "md",
      "size_bytes": 12345,
      "modified": "2025-12-10T12:05:30.123456"
    },
    {
      "filename": "20251210_120530_page_0001.json",
      "type": "json",
      "size_bytes": 23456,
      "modified": "2025-12-10T12:05:30.123456"
    }
  ]
}
```

---

### 2. GET `/files/{file_type}/{filename}` - Получить содержимое файла

**Описание:**  
Получить содержимое сохраненного MD или JSON файла. Можно получить как JSON с содержимым, так и скачать файл напрямую.

**Параметры:**
- `file_type`: Тип файла - `md` или `json`
- `filename`: Имя файла или его часть (будет найден первый совпадающий файл)
- `download` (опционально): Если `true`, возвращает файл для скачивания, иначе JSON с содержимым

**Примеры запросов:**

```bash
# Получить содержимое MD файла как JSON
curl -X GET "https://<url>/files/md/page_0001" \
  -H "x-api-key: <API_KEY>"

# Получить содержимое JSON файла
curl -X GET "https://<url>/files/json/page_0001" \
  -H "x-api-key: <API_KEY>"

# Скачать MD файл напрямую
curl -X GET "https://<url>/files/md/page_0001?download=true" \
  -H "x-api-key: <API_KEY>" \
  -o result.md

# Скачать JSON файл напрямую
curl -X GET "https://<url>/files/json/page_0001?download=true" \
  -H "x-api-key: <API_KEY>" \
  -o result.json
```

**Пример ответа (JSON):**

```json
{
  "status": "success",
  "filename": "20251210_120530_page_0001.md",
  "size_bytes": 12345,
  "content": "# Markdown content here\n\n..."
}
```

**Для JSON файлов:**

```json
{
  "status": "success",
  "filename": "20251210_120530_page_0001.json",
  "size_bytes": 23456,
  "content": {
    "text": "...",
    "blocks": [...],
    "metadata": {...}
  }
}
```

---

### 3. POST `/test/s3-upload` - Тестовая загрузка в S3

**Описание:**  
Тестовый endpoint для проверки работы S3 загрузки без OCR обработки. Позволяет загрузить любой файл с локального компьютера в S3 bucket.

**Параметры:**
- `file` (обязательно): Файл для загрузки (multipart/form-data)
- `s3_key` (опционально): Кастомный ключ S3 (по умолчанию: `test-uploads/{timestamp}_{filename}`)

**Примеры запросов:**

```bash
# Загрузить тестовый файл в S3
curl -X POST "https://<url>/test/s3-upload" \
  -H "x-api-key: <API_KEY>" \
  -F "file=@test.txt"

# Загрузить с кастомным S3 ключом
curl -X POST "https://<url>/test/s3-upload" \
  -H "x-api-key: <API_KEY>" \
  -F "file=@document.pdf" \
  -F "s3_key=my-custom-path/document.pdf"

# Загрузить MD файл (для тестирования сохранения результатов OCR)
curl -X POST "https://<url>/test/s3-upload" \
  -H "x-api-key: <API_KEY>" \
  -F "file=@result.md"

# Загрузить JSON файл
curl -X POST "https://<url>/test/s3-upload" \
  -H "x-api-key: <API_KEY>" \
  -F "file=@result.json"
```

**Пример ответа:**

```json
{
  "status": "success",
  "message": "File uploaded to S3 successfully",
  "filename": "test.txt",
  "local_size_bytes": 1024,
  "s3_path": "s3://bucket-winners223/test-uploads/20251210_120530_test.txt",
  "s3_key": "test-uploads/20251210_120530_test.txt",
  "public_url": "https://bucket-winners223.s3.cloud.ru/test-uploads/20251210_120530_test.txt",
  "is_public_accessible": true,
  "upload_time_sec": 0.85,
  "bucket": "bucket-winners223",
  "timestamp": "2025-12-10T12:05:30.123456"
}
```

---

## 🔍 Использование

### Сценарий 1: Получить результаты OCR обработки

Если обработка завершилась, но файлы не загрузились в S3 (или хотите получить их напрямую):

```bash
# 1. Получить список файлов
curl -X GET "https://<url>/files?limit=10" \
  -H "x-api-key: <API_KEY>"

# 2. Получить содержимое MD файла
curl -X GET "https://<url>/files/md/20251210_120530" \
  -H "x-api-key: <API_KEY>"

# 3. Или скачать файл напрямую
curl -X GET "https://<url>/files/md/20251210_120530?download=true" \
  -H "x-api-key: <API_KEY>" \
  -o result.md
```

### Сценарий 2: Проверка работы S3

Проверить, что S3 загрузка работает корректно:

```bash
# 1. Создать тестовый файл
echo "Test content" > test.txt

# 2. Загрузить в S3
curl -X POST "https://<url>/test/s3-upload" \
  -H "x-api-key: <API_KEY>" \
  -F "file=@test.txt"

# 3. Проверить ответ:
# - status: "success"
# - public_url: доступная ссылка
# - is_public_accessible: true/false
```

### Сценарий 3: Тестирование сохранения результатов OCR

Если результаты OCR сохранены локально, но не загрузились в S3:

```bash
# 1. Найти последние результаты
curl -X GET "https://<url>/files?limit=5" \
  -H "x-api-key: <API_KEY>"

# 2. Скачать MD файл
curl -X GET "https://<url>/files/md/20251210_120530?download=true" \
  -H "x-api-key: <API_KEY>" \
  -o result.md

# 3. Загрузить в S3 вручную для проверки
curl -X POST "https://<url>/test/s3-upload" \
  -H "x-api-key: <API_KEY>" \
  -F "file=@result.md" \
  -F "s3_key=ocr-results/20251210_120530_result.md"
```

---

## ⚠️ Важные замечания

1. **Аутентификация:** Все endpoints требуют заголовок `x-api-key` с API ключом
2. **Размер файлов:** Большие файлы (>10MB) могут вернуться как JSON с содержимым медленно
3. **S3 доступность:** Если `is_public_accessible` = `false`, проверьте bucket policy
4. **Имена файлов:** При поиске по части имени будет найден первый совпадающий файл (самый новый)

---

## 🐛 Отладка

### Проблема: Файлы не найдены

```bash
# Проверьте список файлов
curl -X GET "https://<url>/files" \
  -H "x-api-key: <API_KEY>"
```

### Проблема: S3 загрузка не работает

```bash
# Проверьте тестовую загрузку
curl -X POST "https://<url>/test/s3-upload" \
  -H "x-api-key: <API_KEY>" \
  -F "file=@test.txt"
```

В ответе будут детали ошибки:
- `Cannot access S3 bucket` - проверьте credentials
- `Bucket mismatch` - проверьте CLOUDRU_S3_BUCKET
- `is_public_accessible: false` - проверьте bucket policy

---

## 📝 Примеры Python

```python
import requests

API_URL = "https://<url>"
API_KEY = "<API_KEY>"
headers = {"x-api-key": API_KEY}

# 1. Получить список файлов
response = requests.get(f"{API_URL}/files?limit=10", headers=headers)
files = response.json()["files"]
print(f"Found {len(files)} files")

# 2. Получить содержимое MD файла
md_response = requests.get(
    f"{API_URL}/files/md/page_0001",
    headers=headers
)
md_content = md_response.json()["content"]
print(f"MD content: {md_content[:100]}...")

# 3. Скачать файл
with open("result.md", "wb") as f:
    download_response = requests.get(
        f"{API_URL}/files/md/page_0001?download=true",
        headers=headers
    )
    f.write(download_response.content)

# 4. Тестовая загрузка в S3
with open("test.txt", "rb") as f:
    s3_response = requests.post(
        f"{API_URL}/test/s3-upload",
        headers=headers,
        files={"file": f}
    )
    result = s3_response.json()
    print(f"S3 URL: {result['public_url']}")
```

---

**Все новые endpoints готовы к использованию!**


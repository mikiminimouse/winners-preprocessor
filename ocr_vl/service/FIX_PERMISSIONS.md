# Исправление проблемы с правами доступа

## Проблема

В логах Cloud.ru ML Inference наблюдалась ошибка:
```
PermissionError: [Errno 13] Permission denied: '/app/temp/tmp*.jpg'
```

## Причина

1. **Старый код использовал `tempfile.NamedTemporaryFile`** - который создавал файлы с правами 0o600, недоступными для других процессов
2. **Попытка изменить права через `os.chmod`** не работала - в контейнере запуск происходит не от root или директория смонтирована с ограничениями

## Решение

### Изменения в `server.py`:

1. **Убрано использование `tempfile.NamedTemporaryFile`**
   - Вместо этого создаются файлы напрямую через `Path` и `open()`

2. **Убраны вызовы `os.chmod()`**
   - Файлы создаются с правами по умолчанию (обычно достаточными)

3. **Использование `uuid` для уникальных имен файлов**
   - Вместо системных временных файлов: `tmp_{uuid.uuid4().hex[:8]}.jpg`

### Новый код:

**Для Base64:**
```python
temp_filename = f"tmp_{uuid.uuid4().hex[:8]}.jpg"
temp_image_path = TEMP_DIR / temp_filename
image.save(str(temp_image_path), format='JPEG')
```

**Для URL:**
```python
temp_filename = f"tmp_{uuid.uuid4().hex[:8]}.jpg"
temp_image_path = TEMP_DIR / temp_filename
image.save(str(temp_image_path), format='JPEG')
```

**Для multipart:**
```python
suffix = Path(file.filename).suffix if file.filename else '.jpg'
temp_filename = f"tmp_{uuid.uuid4().hex[:8]}{suffix}"
temp_image_path = TEMP_DIR / temp_filename
with open(temp_image_path, 'wb') as f:
    f.write(content)
```

## Образ

**Новый образ с исправлениями:**
```
docling-granite-258m.cr.cloud.ru/paddleocr-vl-service:latest
Digest: sha256:18d75162e5a2e5bee2f7d30518c2bccd0fc681007d9fc97e43a12dd73367a0b3
Версия: 1.0.3
```

## Дополнительные исправления

1. **Проверка доступности директорий при старте:**
   - Добавлена проверка записи в `/app/temp` и `/app/output`
   - Логирование предупреждений при проблемах

2. **Улучшенная обработка ошибок:**
   - Детальное логирование проблем с записью файлов
   - Понятные сообщения об ошибках

## Тестирование

После обновления образа на Cloud.ru:

1. Проверить логи при старте - должны появиться сообщения:
   ```
   TEMP_DIR is writable: /app/temp
   OUTPUT_DIR is writable: /app/output
   ```

2. Отправить тестовый запрос и проверить, что:
   - Файлы успешно создаются в `/app/temp`
   - Ошибок `Permission denied` нет
   - OCR обработка работает

## Важно

⚠️ **Обязательно обновите образ на Cloud.ru ML Inference!**

Текущий образ на Cloud.ru все еще использует старую версию кода (строка 366 в логах соответствует старому коду).

После обновления образа проблема с правами доступа должна быть решена.


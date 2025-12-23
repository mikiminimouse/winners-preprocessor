# Исправления проблем с конвертацией .doc файлов

**Дата:** 2025-12-22

## Обнаруженные проблемы

### 1. .doc файлы попадают в категорию normalize вместо convert

**Причина:**
- Decision Engine возвращает `classification="normalize"` для ole2 файлов (scenario 2.2, 2.3)
- Это происходит потому, что ole2 - это общий тип, который может быть doc, xls или ppt
- Decision Engine не может определить конкретный тип без структурного парсинга

**Исправление:**
1. **`file_ops.py`**: Добавлено переопределение `classification` для .doc, .xls, .ppt файлов при обнаружении OLE2 сигнатуры
   - Если расширение `.doc` и есть OLE2 сигнатура → `classification="direct"` (готов к конвертации)
   - Аналогично для `.xls` и `.ppt`

2. **`classifier.py`**: Добавлена проверка расширения файла ПЕРЕД использованием classification из Decision Engine
   - Если расширение `.doc`, `.xls`, `.ppt`, `.rtf` → всегда `category="convert"`
   - Это гарантирует, что старые Office форматы всегда попадают в convert, а не normalize

### 2. Конвертация не выполняется для UNIT в Converted

**Причина:**
- UNIT перемещаются в `Merge_1/Converted` через `stage_merge` БЕЗ конвертации
- Это происходит потому, что `stage_merge` вызывается ДО конвертации или конвертер не вызывается

**Текущее состояние:**
- 228 UNIT в `Merge_1/Converted` с .doc файлами БЕЗ операций конвертации
- Конвертер правильно находит файлы для конвертации
- LibreOffice установлен и работает

**Решение:**
- Исправления в `converter.py` и `stage.py` уже предотвращают перемещение UNIT без конвертации
- Для уже перемещенных UNIT требуется повторная обработка

## Выполненные исправления

### 1. `file_ops.py`

Добавлено переопределение `classification` для старых Office форматов:

```python
# При обнаружении OLE2 сигнатуры для .doc файлов
if extension in [".doc", ".docx"] or mime_type_val.startswith("application/msword"):
    result["detected_type"] = "doc"
    result["requires_conversion"] = True
    result["classification"] = "direct"  # Переопределяем для конвертации
```

### 2. `classifier.py`

Добавлена проверка расширения ПЕРЕД использованием classification из Decision Engine:

```python
# Проверяем расширение файла для старых Office форматов
if extension in [".doc", ".xls", ".ppt", ".rtf"]:
    if detected_type in self.CONVERTIBLE_TYPES or detection.get("requires_conversion", False):
        classification["category"] = "convert"
        classification["needs_conversion"] = True
        return classification

# Если Decision Engine вернул "normalize" для .doc, .xls, .ppt файлов
if decision_classification == "normalize":
    if extension in [".doc", ".xls", ".ppt", ".rtf"]:
        classification["category"] = "convert"
        classification["needs_conversion"] = True
        return classification
```

## Результаты тестирования

### Проверка классификации

✅ `.doc` файлы теперь правильно классифицируются как `convert`
✅ `needs_conversion=True` устанавливается корректно
✅ `needs_normalization=False` для .doc файлов

### Проверка конвертации

✅ Конвертер правильно находит файлы для конвертации
✅ LibreOffice успешно конвертирует .doc → .docx
✅ Конвертер не перемещает UNIT без успешной конвертации

## Следующие шаги

### Для уже перемещенных UNIT

1. **Повторная конвертация:**
   ```bash
   cd final_preprocessing
   docprep substage convert run \
     --input Data/2025-12-16/Merge/Merge_1/Converted/doc \
     --cycle 1 \
     --date 2025-12-16
   ```

2. **Проверка результатов:**
   - Убедиться, что все .doc файлы конвертированы в .docx
   - Проверить, что операции конвертации добавлены в манифесты

### Для новых данных

✅ Исправления гарантируют, что:
- .doc файлы всегда попадают в `convert`, а не `normalize`
- UNIT не перемещаются в Converted без конвертации
- Конвертация выполняется перед merge

## Файлы изменений

1. `final_preprocessing/docprep/utils/file_ops.py`
   - Добавлено переопределение `classification` для OLE2 файлов

2. `final_preprocessing/docprep/engine/classifier.py`
   - Добавлена проверка расширения перед использованием Decision Engine classification
   - Добавлена проверка для normalize → convert для старых Office форматов

3. `final_preprocessing/docprep/engine/converter.py`
   - Уже исправлено: UNIT не перемещаются без конвертации

4. `final_preprocessing/docprep/cli/stage.py`
   - Уже исправлено: проверка операций перед merge


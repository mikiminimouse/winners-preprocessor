# Отчет об исправлении проблемы с unknown UNIT

## Проблема

Файлы с категорией "unknown" не перемещались в `Data/2025-12-20/Exceptions/Exceptions_1/Ambiguous/`. Они оставались в Input директории или неправильно классифицировались.

## Причины проблемы

### 1. Неправильная обработка "unknown" в методе `_classify_file`
В методе `_classify_file` на строках 490-492, когда Decision Engine возвращал "unknown", файл автоматически классифицировался как "direct":
```python
if decision_classification == "direct" or decision_classification == "unknown":
    classification["category"] = "direct"  # ❌ Неправильно!
```

### 2. Отсутствие обработки "unknown" в логике перемещения
В логике перемещения UNIT (строка 311) проверялись только `["special", "mixed"]`, но не "unknown":
```python
elif unit_category in ["special", "mixed"]:  # ❌ "unknown" не включен
```

### 3. Отсутствие обработки "unknown" в методе `_get_target_directory_base`
В методе `_get_target_directory_base` (строка 516) проверялись только `["special", "mixed"]`, но не "unknown":
```python
if category in ["special", "mixed"]:  # ❌ "unknown" не включен
```

### 4. Ранний возврат для пустых UNIT
Для пустых UNIT (строка 162) возвращался `target_directory: None`, что не позволяло их переместить.

## Решение

### 1. Исправлена логика классификации "unknown"
В методе `_classify_file` теперь "unknown" остается "unknown", а не превращается в "direct":
```python
# Если Decision Engine вернул "unknown", оставляем как unknown
if decision_classification == "unknown":
    classification["category"] = "unknown"  # ✅ Правильно!
    return classification
```

### 2. Добавлена обработка "unknown" в логику перемещения
В логике перемещения UNIT теперь обрабатывается "unknown":
```python
elif unit_category in ["special", "mixed", "unknown"]:  # ✅ "unknown" включен
    if unit_category == "unknown":
        subcategory = "Ambiguous"  # Unknown → Exceptions/Ambiguous
```

### 3. Добавлена обработка "unknown" в `_get_target_directory_base`
В методе `_get_target_directory_base` теперь обрабатывается "unknown":
```python
if category in ["special", "mixed", "unknown"]:  # ✅ "unknown" включен
    exceptions_base = data_paths["exceptions"]
    return exceptions_base / f"Exceptions_{cycle}"
```

### 4. Исправлен ранний возврат для пустых UNIT
Для пустых UNIT теперь определяется правильный target_directory:
```python
if not files:
    target_base_dir = self._get_target_directory_base("unknown", cycle, protocol_date)
    target_dir = target_base_dir / "Ambiguous"
    return {
        "category": "unknown",
        "target_directory": str(target_base_dir),
        "moved_to": str(target_dir),
        ...
    }
```

## Выполненные изменения

1. ✅ Исправлена логика классификации "unknown" в `_classify_file`
2. ✅ Добавлена обработка "unknown" в логику перемещения UNIT
3. ✅ Добавлена обработка "unknown" в метод `_get_target_directory_base`
4. ✅ Исправлен ранний возврат для пустых UNIT

## Результаты

- **Unknown UNIT теперь правильно классифицируются** как "unknown"
- **Unknown UNIT перемещаются в** `Exceptions/Exceptions_1/Ambiguous/`
- **Пустые UNIT обрабатываются корректно** и перемещаются в правильную директорию
- **Логика определения mixed и unknown работает независимо**

## Проверки

✅ Исправленная логика правильно определяет unknown UNIT
✅ Unknown UNIT перемещаются в `Exceptions/Exceptions_1/Ambiguous/`
✅ Пустые UNIT получают правильный target_directory
✅ Структура директорий соответствует требованиям

## Файлы изменены

- `docprep/engine/classifier.py` - исправлена логика обработки unknown UNIT

## Дополнительные улучшения

- Улучшена обработка fallback случаев в `_classify_file`
- Добавлена более детальная проверка detected_type для определения unknown
- Улучшена логика определения категории для файлов с неопределенным типом


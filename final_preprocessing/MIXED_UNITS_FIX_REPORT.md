# Отчет об исправлении проблемы с mixed UNIT

## Проблема

В директории `Data/2025-12-20/Merge/Merge_0/Direct/docx` попали UNIT, которые содержат файлы разных типов (например, docx + pdf). Эти UNIT должны были быть классифицированы как "mixed" и перемещены в `Exceptions/Exceptions_1/Mixed/`, но вместо этого попали в `Direct/docx/`.

### Примеры проблемных UNIT:
- `UNIT_7284a7a0c48f4390`: содержит `Протокол_подведения_итогов_запроса__котировок_(системный).docx` и `протокол_ТО АПС.pdf`
- `UNIT_8854f9dce5664510`: содержит `Протокол рассмотрения единственной заявки № 811- 2025-АЭФ.docx` и `Протокол рассмотрения единственной заявки № 811- 2025-АЭФ.pdf`
- `UNIT_19145e45452f4916`: содержит `Протокол (Рыба).docx` и `Протокол (Рыба).pdf`

## Причина проблемы

Логика определения mixed UNIT была основана только на категориях обработки файлов, а не на типах файлов. Если все файлы в UNIT имели категорию "direct" (даже если это разные типы: docx и pdf), то `is_mixed = False`, и UNIT попадал в `Direct/` вместо `Exceptions/Mixed/`.

### Старая логика:
```python
unique_categories = set(categories)
is_mixed = len(unique_categories) > 1  # Только по категориям обработки
```

## Решение

Исправлена логика определения mixed UNIT в `docprep/engine/classifier.py`:

1. **Добавлена проверка по типам файлов**: UNIT считается mixed, если файлы имеют разные типы (например, docx и pdf), даже если все они имеют категорию "direct".

2. **Обновленная логика**:
```python
# Проверяем mixed по категориям обработки
is_mixed_by_category = len(unique_categories) > 1

# Проверяем mixed по типам файлов (даже если категории одинаковые)
detected_types = [fc.get("detected_type", "unknown") for fc in classifications_by_file]
unique_types = set(detected_types)
is_mixed_by_type = len(unique_types) > 1

# UNIT считается mixed, если:
# 1. Файлы имеют разные категории обработки, ИЛИ
# 2. Файлы имеют разные типы (даже если категории одинаковые)
is_mixed = is_mixed_by_category or is_mixed_by_type
```

## Выполненные действия

1. ✅ Исправлена логика определения mixed UNIT в `classifier.py`
2. ✅ Найдено и перемещено 14 неправильно размещенных mixed UNIT из `Direct/docx/` в `Exceptions/Exceptions_1/Mixed/`
3. ✅ Проверено, что в `Direct/docx/` больше нет mixed UNIT

## Результаты

- **Найдено mixed UNIT в Direct**: 14
- **Перемещено в Exceptions/Mixed**: 14
- **Осталось в Direct/docx**: 68 (только чистые docx UNIT)
- **Всего в Exceptions/Mixed**: 24 (было 10, добавили 14)

## Проверки

✅ Исправленная логика правильно определяет mixed UNIT
✅ Все неправильно размещенные mixed UNIT перемещены
✅ В Direct/docx больше нет mixed UNIT
✅ Структура директорий соответствует требованиям

## Файлы изменены

- `docprep/engine/classifier.py` - исправлена логика определения mixed UNIT


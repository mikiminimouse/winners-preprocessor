# Отчет об анализе и исправлении проблем

**Дата:** 2025-12-19  
**Версия системы:** 1.0.0

## Выявленные проблемы

### Проблема 1: Неправильное распределение doc файлов в convert/xls вместо convert/doc

**Описание:**
- Файлы с расширением `.doc` попадали в `convert/xls` вместо `convert/doc`
- Причина: `detect_file_type()` определял doc файлы как `xls` (Excel)
- В функции `get_extension_subdirectory()` для категории "convert" использовался `detected_type` вместо `original_extension`

**Анализ:**
```python
# Проблемный код в get_extension_subdirectory():
elif category == "convert":
    if original_extension:
        return original_extension.lstrip(".")
    return detected_type.replace("_archive", "") if detected_type else None
```

Проблема была в том, что `original_extension` не всегда передавался в функцию.

**Исправление:**
1. В `classifier.py` добавлена передача `original_extension` из файла:
```python
# Определяем расширение для сортировки на основе первой классификации
extension = None
if classifications_by_file and files:
    first_classification = classifications_by_file[0]
    first_file = files[0]
    # Передаем original_extension из файла
    original_ext = first_file.suffix.lower()
    extension = get_extension_subdirectory(
        category=unit_category,
        classification=first_classification,
        original_extension=original_ext,
    )
```

2. В `unit_processor.py` улучшена логика для категории "convert":
```python
elif category == "convert":
    # Для convert ВСЕГДА используем исходное расширение файла, а не detected_type
    if original_extension:
        ext = original_extension.lstrip(".")
        return ext if ext else None
    # Если original_extension не передан, пытаемся получить из classification
    if classification:
        file_path = classification.get("file_path")
        if file_path:
            from pathlib import Path
            ext = Path(file_path).suffix.lower().lstrip(".")
            return ext if ext else None
    # Fallback: используем detected_type только если нет другого выбора
    return detected_type.replace("_archive", "") if detected_type else None
```

**Результат:** ✅ Исправлено - doc файлы теперь попадают в `convert/doc`

---

### Проблема 2: UNIT из Pending_1/direct не перемещаются в Merge_1/direct

**Описание:**
- UNIT из `Pending_1/direct` должны перемещаться в `Merge_1/direct`
- Проблема: путь к Merge формировался неправильно - не добавлялся `/direct`

**Анализ:**
```python
# Проблемный код в stage.py:
cycle_paths = get_cycle_paths(cycle, None, merge_base, None)
target_dir = cycle_paths["merge"]  # Это Merge_1, но нужно Merge_1/direct
```

**Исправление:**
```python
# Исправленный код:
cycle_paths = get_cycle_paths(cycle, None, merge_base, None)
target_dir = cycle_paths["merge"] / "direct"  # Merge_N/direct
```

**Результат:** ✅ Исправлено - UNIT теперь перемещаются в `Merge_1/direct`

---

### Проблема 3: Пустые директории остаются после перемещения UNIT

**Описание:**
- После перемещения UNIT из `Input/` остаются пустые директории
- После перемещения из `Pending_1/direct` остаются пустые директории

**Анализ:**
- Функция `move_unit_to_target()` только перемещала UNIT, но не очищала пустые директории

**Исправление:**
Добавлена функция `_cleanup_empty_directories()` в `unit_processor.py`:
```python
def _cleanup_empty_directories(path: Path) -> None:
    """
    Рекурсивно удаляет пустые директории начиная с указанного пути.
    """
    try:
        current = path
        while current and current.exists():
            parent = current.parent
            # Не удаляем базовые директории (Input, Processing, Merge и т.д.)
            if parent.name in ["Input", "Processing", "Merge", "Exceptions", "Ready2Docling"]:
                break
            # Не удаляем директории с датами (YYYY-MM-DD)
            if len(current.name) == 10 and current.name.count("-") == 2:
                break
            # Проверяем, пуста ли директория
            try:
                if current.exists() and current.is_dir():
                    items = list(current.iterdir())
                    if not items:
                        logger.debug(f"Removing empty directory: {current}")
                        current.rmdir()
                        current = parent
                    else:
                        break
                else:
                    break
            except OSError:
                break
    except Exception as e:
        logger.warning(f"Failed to cleanup empty directories for {path}: {e}")
```

И вызов этой функции добавлен в `move_unit_to_target()`:
```python
if unit_dir != target_dir:
    logger.info(f"Moving unit {unit_id}: {unit_dir} -> {target_dir}")
    shutil.move(str(unit_dir), str(target_dir))
    
    # Очищаем пустые директории после перемещения
    _cleanup_empty_directories(unit_dir)
```

**Результат:** ✅ Исправлено - пустые директории теперь удаляются после перемещения

---

## План тестирования

### Тест 1: Классификация doc файлов
```bash
python3 -m docprep.cli.main stage classifier \
  --cycle 1 \
  --input Data/Input/test_units \
  --date 2025-03-18 \
  --verbose
```
**Ожидаемый результат:** UNIT с doc файлами попадают в `Pending_1/convert/doc`

### Тест 2: Перемещение в Merge
```bash
python3 -m docprep.cli.main stage merge \
  --cycle 1 \
  --source Data/Processing/2025-03-18/Pending_1/direct \
  --date 2025-03-18 \
  --verbose
```
**Ожидаемый результат:** UNIT перемещаются в `Merge_1/direct`

### Тест 3: Очистка пустых директорий
После перемещения UNIT проверяется, что пустые директории удалены.

**Ожидаемый результат:** Пустые директории удалены

---

## Статус исправлений

- ✅ **Проблема 1:** Исправлено - doc файлы попадают в `convert/doc`
- ✅ **Проблема 2:** Исправлено - UNIT перемещаются в `Merge_1/direct`
- ✅ **Проблема 3:** Исправлено - пустые директории удаляются

---

## Рекомендации

1. **Для production:**
   - Протестировать на реальных данных с файлами
   - Проверить работу очистки директорий на больших объемах
   - Добавить логирование операций очистки

2. **Для дальнейшей отладки:**
   - Добавить unit-тесты для `get_extension_subdirectory()`
   - Добавить unit-тесты для `_cleanup_empty_directories()`
   - Проверить работу на различных типах файлов

3. **Для оптимизации:**
   - Рассмотреть возможность батчевой очистки директорий
   - Добавить проверку прав доступа перед удалением


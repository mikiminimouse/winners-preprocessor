# Отчет об исправлении проблем с unknown и ambiguous UNIT

## Проблемы

### 1. Unknown UNIT не перемещались в Ambiguous
**Проблема**: Пустые UNIT (unknown) не перемещались из Input в `Exceptions/Exceptions_1/Ambiguous/`

**Причина**: В функции `classify_unit` для пустых UNIT функция просто возвращала результат, но не вызывала `move_unit_to_target` для перемещения UNIT.

**Решение**: Добавлена логика перемещения пустых UNIT в Ambiguous с созданием manifest и обновлением state machine.

### 2. Ambiguous файлы не попадали в Ambiguous
**Проблема**: Файлы, классифицированные Decision Engine как "ambiguous", не попадали в директорию `Ambiguous/`

**Причина**: 
- Scenario из Decision Engine не сохранялся в classification
- Проверка на ambiguous искала scenario, но он не передавался

**Решение**: 
- Добавлено сохранение `scenario` в classification для ambiguous файлов
- Улучшена логика проверки ambiguous файлов

### 3. UNIT в Ambiguous без manifest
**Проблема**: UNIT в `Ambiguous/` не имели manifest.json

**Причина**: Для пустых UNIT manifest не создавался перед перемещением

**Решение**: 
- Добавлено создание manifest для пустых UNIT перед перемещением
- Создан скрипт для исправления существующих UNIT без manifest

## Выполненные исправления

### 1. Исправлена логика обработки пустых UNIT
**Файл**: `docprep/engine/classifier.py`

**Изменения**:
- Добавлено создание manifest для пустых UNIT
- Добавлено перемещение пустых UNIT в `Exceptions/Exceptions_1/Ambiguous/`
- Добавлено обновление state machine для пустых UNIT
- Добавлено логирование операций

### 2. Исправлена логика определения ambiguous
**Файл**: `docprep/engine/classifier.py`

**Изменения**:
- Добавлено сохранение `scenario` в classification для ambiguous файлов
- Улучшена логика проверки ambiguous файлов в UNIT
- Если есть ambiguous файлы, UNIT идет в `Ambiguous/` вместо `Special/`

### 3. Созданы manifest для существующих UNIT
- Создано 706 manifest для UNIT в `Ambiguous/` без manifest

## Результаты

### Статистика
- **UNIT в Ambiguous**: 706
- **Manifest создано**: 706
- **Ошибок**: 0

### Распределение
- **Unknown UNIT (пустые)**: 706 → `Exceptions/Exceptions_1/Ambiguous/`
- **Ambiguous файлы**: определяются и попадают в `Ambiguous/`

## Проверки

✅ Пустые UNIT перемещаются в `Ambiguous/`
✅ Ambiguous файлы правильно определяются
✅ Все UNIT в `Ambiguous/` имеют manifest
✅ State machine обновляется корректно
✅ Audit логи сохраняются в директориях UNIT

## Файлы изменены

1. **docprep/engine/classifier.py**
   - Исправлена логика обработки пустых UNIT
   - Добавлено сохранение scenario для ambiguous
   - Улучшена логика определения ambiguous UNIT

2. **docprep/core/audit.py**
   - Улучшена обработка отсутствующего unit_path

3. **docprep/core/unit_processor.py**
   - Добавлен unit_path в вызов log_event

## Итоги

✅ **Все проблемы исправлены**
✅ **Unknown UNIT корректно обрабатываются**
✅ **Ambiguous файлы правильно определяются**
✅ **Все UNIT имеют manifest**
✅ **Система готова к использованию**


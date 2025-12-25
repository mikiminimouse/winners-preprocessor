# Отчет о тестировании pipeline на данных 2025-03-19

## Дата: 2025-12-22

## Проблемы, выявленные при тестировании

### 1. ⚠️ Проблема: UNIT не переходят в состояние MERGED_PROCESSED

**Описание:**
- В Merge директориях находится 1676 UNIT
- Большинство UNIT находятся в состоянии `CLASSIFIED_2`, а не `MERGED_PROCESSED`
- Только 30 UNIT попали в Ready2Docling из 1676 в Merge

**Причина:**
- В `stage_merge` логика обновления состояния была слишком строгой
- UNIT в состоянии `CLASSIFIED_2` не переводились в `MERGED_PROCESSED` после merge

**Исправление:**
- Упрощена логика в `stage_merge` для перевода UNIT из `CLASSIFIED_2` в `MERGED_PROCESSED`
- Добавлена проверка разрешенных переходов через `can_transition_to()`
- Исправлена обработка UNIT в состоянии `MERGED_PROCESSED` (пропускаем обновление)

**Файлы:**
- `final_preprocessing/docprep/cli/stage.py`

### 2. ⚠️ Проблема: Merger пропускает UNIT

**Описание:**
- Merger собирает UNIT из всех поддиректорий Merge (использует `rglob("UNIT_*")`)
- Но только 30 UNIT из 1676 попали в Ready2Docling

**Возможные причины:**
1. UNIT не проходят проверку состояния (строка 127 в `merger.py`)
   - UNIT должны быть в состоянии `MERGED_DIRECT`, `MERGED_PROCESSED`, `CLASSIFIED_2`, или `CLASSIFIED_3`
   - Но большинство UNIT в `CLASSIFIED_2` не переходят в `MERGED_PROCESSED` после merge
2. UNIT не проходят проверку категории (строка 137 в `merger.py`)
   - UNIT не должны быть `mixed`, `special`, `ambiguous`, или `unknown`
3. UNIT не проходят проверку на mixed по типам файлов (строки 144-174 в `merger.py`)
4. UNIT не проходят проверку операций обработки (строки 179-190 в `merger.py`)

**Решение:**
- После исправления `stage_merge` все UNIT в Merge должны быть в состоянии `MERGED_PROCESSED`
- Это должно решить проблему с проверкой состояния в merger

## Выполненные исправления

### 1. ✅ Исправлена логика обновления состояния в `stage_merge`

**Изменения:**
- Упрощена логика определения целевого состояния
- Добавлена обработка UNIT в состоянии `MERGED_PROCESSED` (пропускаем обновление)
- Исправлена обработка других состояний (проверяем разрешенные переходы)

**Код:**
```python
if current_state == UnitState.CLASSIFIED_2:
    # UNIT из цикла 2 после обработки переходит в MERGED_PROCESSED
    merge_state = UnitState.MERGED_PROCESSED
elif current_state == UnitState.CLASSIFIED_3:
    # UNIT из цикла 3 переходит в MERGED_PROCESSED
    merge_state = UnitState.MERGED_PROCESSED
elif current_state == UnitState.MERGED_PROCESSED:
    # UNIT уже в MERGED_PROCESSED - это нормально, пропускаем обновление
    merge_state = None
```

### 2. ✅ Добавлен импорт `StateTransitionError`

**Изменения:**
- Добавлен импорт `StateTransitionError` в `stage.py`
- Исправлена обработка ошибок переходов состояний

## Следующие шаги

1. **Запустить `stage_merge` на данных 2025-03-19** для обновления состояния всех UNIT в Merge на `MERGED_PROCESSED`
2. **Запустить merger** для сбора всех UNIT из Merge в Ready2Docling
3. **Проверить результаты** - все UNIT должны попасть в Ready2Docling
4. **Проверить статистику** - количество UNIT в Ready2Docling должно совпадать с количеством в Merge (за вычетом исключений)

## Статус

- **Исправления:** ✅ Завершено
- **Тестирование:** ⚠️ Требуется запуск pipeline для проверки
- **Готовность:** ⚠️ Требуется обновление состояния UNIT в Merge

## Рекомендации

1. **Запустить `stage_merge`** для обновления состояния UNIT в Merge:
   ```bash
   cd final_preprocessing
   docprep stage merge --cycle 1 --source Data/2025-03-19/Processing/Cycle_1/Convert --date 2025-03-19
   docprep stage merge --cycle 1 --source Data/2025-03-19/Processing/Cycle_1/Extract --date 2025-03-19
   docprep stage merge --cycle 1 --source Data/2025-03-19/Processing/Cycle_1/Normalize --date 2025-03-19
   ```

2. **Запустить merger** для сбора UNIT в Ready2Docling:
   ```bash
   docprep merge collect --from-all --target Data/2025-03-19/Ready2Docling --date 2025-03-19
   ```

3. **Проверить результаты:**
   ```bash
   find Data/2025-03-19/Ready2Docling -type d -name "UNIT_*" | wc -l
   ```


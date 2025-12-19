# DocPrep - CLI система для preprocessing документов

CLI система для preprocessing документов перед обработкой в Docling pipeline.

## Особенности

- **Обработка директорий целиком**: CLI работает с директориями UNIT, а не отдельными файлами
- **3 цикла обработки**: Итеративная обработка с максимум 3 циклами
- **State Machine**: Строгие переходы состояний с валидацией
- **Manifest v2**: Управление состоянием UNIT через manifest.json
- **Audit Log**: Полное логирование всех операций в JSONL формате
- **Docling-ready**: Результат готов к обработке Docling без дополнительных проверок

## Установка

```bash
pip install -e .
```

## Использование

### Полный pipeline

```bash
docprep pipeline run Input/2025-03-18 Ready2Docling/2025-03-18
```

### Отдельный цикл

```bash
docprep cycle run 1 --input Input/2025-03-18 --pending Processing/2025-03-18/Pending_1 --merge Merge/2025-03-18/Merge_1
```

### Атомарные операции

```bash
# Конвертация
docprep substage convert --input Processing/2025-03-18/Pending_1/Convert

# Разархивация
docprep substage extract --input Processing/2025-03-18/Pending_1/Archives

# Нормализация
docprep substage normalize --input Processing/2025-03-18/Pending_1/Normalize
```

### Merge

```bash
docprep merge collect --source Merge/2025-03-18 --target Ready2Docling/2025-03-18 --from-all
```

### Инспекция

```bash
# Список UNIT
docprep inspect units Processing/2025-03-18

# Manifest UNIT
docprep inspect manifest UNIT_000123 --directory Ready2Docling/2025-03-18
```

## Архитектура

### State Machine

Система использует детерминированную state machine для управления состояниями UNIT:

- `RAW` → `CLASSIFIED_1` → `PENDING_*` → `CLASSIFIED_2` → ... → `READY_FOR_DOCLING`

### Manifest v2

Manifest хранит состояние UNIT:
- `schema_version`: версия схемы
- `unit_id`, `protocol_id`: идентификаторы
- `files[]`: список файлов с трансформациями
- `state_machine`: история переходов состояний
- `processing`: информация о циклах обработки

### Audit Log

Все операции логируются в `audit.log.jsonl`:
- Тип события (transition, operation, error)
- Детали операции
- Состояние до и после
- Correlation ID для связи событий

## Структура проекта

```
docprep/
├── cli/              # CLI команды
├── engine/           # Execution engine
├── core/             # Ядро системы
├── adapters/         # Адаптеры (Docling)
├── utils/            # Утилиты
└── schemas/          # JSON схемы
```

## Лицензия

MIT


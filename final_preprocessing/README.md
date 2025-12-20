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

# Дерево структуры
docprep inspect tree Data/2025-12-20
```

### Статистика и метрики

```bash
# Показать статистику
docprep stats show 2025-12-20

# Детальная статистика
docprep stats show 2025-12-20 --detailed

# Сравнить циклы
docprep stats compare 2025-12-20 --cycle1 1 --cycle2 2

# Экспорт статистики
docprep stats export 2025-12-20 --format markdown --output report.md
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

## Тестирование

Подробное руководство по тестированию через CLI: см. `docs/TESTING_GUIDE_CLI.md`

### Быстрый старт тестирования

```bash
# 1. Инициализация структуры
docprep utils init-date 2025-12-20

# 2. Классификация (Цикл 1)
docprep classifier run --input Data/2025-12-20/Input --cycle 1 --date 2025-12-20

# 3. Обработка
docprep substage convert run --input Data/2025-12-20/Processing/Processing_1/Convert --cycle 1 --date 2025-12-20
docprep substage extract run --input Data/2025-12-20/Processing/Processing_1/Extract --cycle 1 --date 2025-12-20
docprep substage normalize name --input Data/2025-12-20/Processing/Processing_1/Normalize --cycle 1 --date 2025-12-20
docprep substage normalize extension --input Data/2025-12-20/Processing/Processing_1/Normalize --cycle 1 --date 2025-12-20

# 4. Повторная классификация (Цикл 2)
docprep classifier run --input Data/2025-12-20/Merge/Merge_1 --cycle 2 --date 2025-12-20

# 5. Статистика
docprep stats show 2025-12-20 --detailed
```

## Документация

- **Архитектура:** `docs/ARCHITECTURE.md`
- **Классификация и статистика:** `docs/CLASSIFICATION_AND_STATISTICS.md`
- **Руководство по статистике:** `docs/STATISTICS_GUIDE.md`
- **Руководство по тестированию CLI:** `docs/TESTING_GUIDE_CLI.md`
- **Лог разработки:** `docs/DEVELOPMENT_LOG.md`

## Требования

- Python 3.8+
- LibreOffice (для конвертации)
- python-magic (для детекции файлов)
- rarfile (для извлечения RAR)
- py7zr (для извлечения 7Z)

## Лицензия

MIT


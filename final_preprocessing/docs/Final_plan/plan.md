# Реализация CLI Preprocessing системы

## Обзор

Реализация полной CLI-системы `docprep` для preprocessing документов согласно [PlantoMake.md](final_preprocessing/docs/Final_plan/PlantoMake.md). Система построена на принципе обработки **директорий целиком**, а не отдельных файлов, с поддержкой 3 циклов итеративной обработки.

## Структура репозитория

Создаётся следующая структура:

```
final_preprocessing/
├── docprep/
│   ├── __init__.py
│   ├── cli/              # CLI команды на Typer
│   │   ├── __init__.py
│   │   ├── main.py       # Точка входа CLI
│   │   ├── pipeline.py   # pipeline run
│   │   ├── cycle.py      # cycle run/classify/process
│   │   ├── stage.py      # stage classifier/pending/merge
│   │   ├── substage.py   # substage convert/extract/normalize
│   │   ├── classifier.py # classifier run
│   │   ├── merge.py      # merge collect
│   │   ├── inspect.py    # inspect tree/units/manifest
│   │   └── utils.py      # utils init-date/clean/stats
│   ├── engine/           # Execution engine
│   │   ├── __init__.py
│   │   ├── classifier.py
│   │   ├── converter.py
│   │   ├── extractor.py
│   │   ├── normalizers/
│   │   │   ├── __init__.py
│   │   │   ├── name.py      # normalize name
│   │   │   └── extension.py # normalize extension
│   │   ├── merger.py
│   │   └── validator.py
│   ├── core/             # Ядро системы
│   │   ├── __init__.py
│   │   ├── state_machine.py  # UnitState enum + transitions
│   │   ├── manifest.py       # manifest v2
│   │   ├── audit.py          # audit log writer
│   │   ├── config.py         # Конфигурация путей
│   │   └── exceptions.py     # Кастомные исключения
│   ├── schemas/          # JSON схемы
│   │   ├── __init__.py
│   │   ├── manifest.json
│   │   └── docling.json
│   ├── adapters/         # Адаптеры
│   │   ├── __init__.py
│   │   └── docling.py    # Docling adapter
│   └── utils/            # Утилиты
│       ├── __init__.py
│       ├── file_ops.py   # Файловые операции
│       └── paths.py      # Работа с путями
├── tests/
│   ├── __init__.py
│   ├── fixtures/         # Test fixtures
│   │   ├── classifier/
│   │   ├── convert/
│   │   ├── extract/
│   │   ├── normalize_name/
│   │   ├── normalize_ext/
│   │   ├── merge/
│   │   └── exceptions/
│   └── test_cli.py
├── pyproject.toml
├── README.md
└── .cursorrules
```

## Этапы реализации

### Этап 1: Базовая инфраструктура (core)

**1.1 State Machine** ([docprep/core/state_machine.py](docprep/core/state_machine.py))

- Enum `UnitState` со всеми состояниями согласно плану:
  - `RAW`, `CLASSIFIED`, `PENDING_CONVERT`, `PENDING_EXTRACT`, `PENDING_NORMALIZE`
  - `MERGED_DIRECT`, `MERGED_PROCESSED`
  - `EXCEPTION_*`, `READY_FOR_DOCLING`
- Словарь `ALLOWED_TRANSITIONS` с разрешёнными переходами
- Класс `UnitStateMachine`:
  - `can_transition_to(state) -> bool`
  - `transition(state) -> None` (с валидацией)
  - `get_current_state() -> UnitState`
  - `get_state_trace() -> List[str]`
  - Загрузка/сохранение состояния из manifest

**1.2 Manifest v2** ([docprep/core/manifest.py](docprep/core/manifest.py))

- Структура manifest согласно плану:
  - `schema_version`, `unit_id`, `protocol_id`, `cycle`
  - `current_state`, `current_cluster`
  - `applied_operations[]` (convert/extract/normalize/rename)
  - `source_files[]` → `result_files[]`
  - `ready_for_docling: bool`
- Функции:
  - `load_manifest(unit_path: Path) -> Dict`
  - `save_manifest(unit_path: Path, manifest: Dict) -> None`
  - `update_manifest_operation(manifest: Dict, operation: Dict) -> Dict`
  - `update_manifest_state(manifest: Dict, state: UnitState) -> Dict`

**1.3 Audit Log** ([docprep/core/audit.py](docprep/core/audit.py))

- Append-only JSONL формат (`audit.log.jsonl`)
- Структура события:
  - `timestamp`, `unit_id`, `event_type`, `operation`, `correlation_id`
  - `details: Dict`, `state_before`, `state_after`
- Класс `AuditLogger`:
  - `log_event(unit_id, event_type, operation, details, state_before, state_after)`
  - `get_correlation_id() -> str`
  - Запись в файл в директории UNIT

**1.4 Config** ([docprep/core/config.py](docprep/core/config.py))

- Константы путей:
  - `INPUT_DIR`, `PROCESSING_DIR`, `MERGE_DIR`, `READY2DOCLING_DIR`
  - Шаблоны для циклов: `PENDING_N_DIR`, `MERGE_N_DIR`, `EXCEPTIONS_N_DIR`
- Функция `get_cycle_paths(cycle: int, base_dir: Path) -> Dict[str, Path]`
- Функция `init_directory_structure(base_dir: Path) -> None`

**1.5 Exceptions** ([docprep/core/exceptions.py](docprep/core/exceptions.py))

- Иерархия исключений:
  - `PreprocessingError` (базовое)
  - `StateTransitionError`, `ManifestError`, `OperationError`
  - `QuarantineError` (для опасных файлов)

### Этап 2: Execution Engine

**2.1 Classifier** ([docprep/engine/classifier.py](docprep/engine/classifier.py))

- Класс `Classifier`:
  - `classify_unit(unit_path: Path, cycle: int) -> Dict`
  - Определение типа файла (magic bytes + MIME)
  - Категоризация: direct/convert/extract/normalize/special
  - Возврат категории для маршрутизации UNIT

**2.2 Converter** ([docprep/engine/converter.py](docprep/engine/converter.py))

- Класс `Converter`:
  - `convert_unit(unit_path: Path, from_format: str, to_format: str, engine: str = "libreoffice") -> Dict`
  - Поддержка: doc→docx, xls→xlsx, ppt→pptx
  - Обновление manifest с операцией convert
  - Логирование в audit log

**2.3 Extractor** ([docprep/engine/extractor.py](docprep/engine/extractor.py))

- Класс `Extractor`:
  - `extract_unit(unit_path: Path, max_depth: int = 2, keep_archive: bool = False, flatten: bool = False) -> Dict`
  - Поддержка ZIP, RAR, 7Z
  - Защита от zip bomb
  - Обновление manifest с операцией extract

**2.4 Normalizers** ([docprep/engine/normalizers/](docprep/engine/normalizers/))

- **name.py** (`NameNormalizer`):
  - Исправление смещённых точек
  - Удаление двойных расширений
  - **Не меняет тип файла**

- **extension.py** (`ExtensionNormalizer`):
  - Проверка magic bytes
  - MIME check
  - Переименование без конвертации

**2.5 Merger** ([docprep/engine/merger.py](docprep/engin
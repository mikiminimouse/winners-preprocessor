# 🔧 План рефакторинга DocPrep Backend
## Версия: 1.0 FINAL - Детальное руководство для Claude Code

**Дата:** 2026-01-17
**Приоритет:** Финальная стадия перед сдачей проекта
**Область:** Backend only (Web UI - отдельная итерация)

---

## 📋 СОДЕРЖАНИЕ

1. [Общий контекст проекта](#1-общий-контекст-проекта)
2. [Приоритеты рефакторинга](#2-приоритеты-рефакторинга)
3. [ФАЗА 1: Критические исправления](#3-фаза-1-критические-исправления)
4. [ФАЗА 2: Улучшение архитектуры](#4-фаза-2-улучшение-архитектуры)
5. [ФАЗА 3: Очистка и оптимизация](#5-фаза-3-очистка-и-оптимизация)
6. [ФАЗА 4: Тестовое покрытие](#6-фаза-4-тестовое-покрытие)
7. [Файловая карта изменений](#7-файловая-карта-изменений)
8. [Чеклист валидации](#8-чеклист-валидации)

---

## 1. ОБЩИЙ КОНТЕКСТ ПРОЕКТА

### 1.1 Что такое DocPrep

DocPrep - это CLI система для preprocessing документов перед обработкой в Docling pipeline. Система работает с атомарными единицами обработки (UNIT), которые проходят через 3 цикла итеративной обработки.

### 1.2 Ключевые компоненты

```
docprep/
├── core/                    # Ядро системы
│   ├── config.py           # Конфигурация и пути ⚠️ ОПЕЧАТКИ
│   ├── state_machine.py    # State Machine для UNIT ⚠️ УЛУЧШИТЬ
│   ├── manifest.py         # Манифест v2
│   ├── audit.py            # Audit logging
│   ├── unit_processor.py   # Обработка UNIT
│   ├── exceptions.py       # Кастомные исключения
│   ├── error_policy.py     # Политики обработки ошибок ⚠️ РАСШИРИТЬ
│   ├── decision_engine.py  # Decision Engine
│   └── base_engine.py      # Базовый класс движков ⚠️ ОПЕЧАТКИ
│
├── engine/                  # Движки обработки
│   ├── classifier.py       # Классификатор
│   ├── converter.py        # Конвертер (LibreOffice) - OK, зависимость нормальная
│   ├── extractor.py        # Распаковка архивов ⚠️ ОПЕЧАТКИ
│   ├── merger.py           # Объединение UNIT
│   ├── validator.py        # Валидатор
│   └── normalizers/
│       ├── name.py
│       └── extension.py    # ⚠️ ОПЕЧАТКИ
│
├── cli/                     # CLI интерфейс ⚠️ УПРОСТИТЬ
│   ├── main.py
│   ├── pipeline.py
│   ├── cycle.py
│   ├── stage.py           # ⚠️ ДУБЛИРОВАНИЕ КОДА
│   ├── substage.py        # ⚠️ ДУБЛИРОВАНИЕ КОДА
│   ├── classifier.py
│   ├── merge.py
│   ├── inspect_cmd.py
│   ├── utils.py
│   ├── stats.py
│   └── chunked_classifier.py  # ❌ УДАЛИТЬ (дублирует)
│
├── utils/
│   ├── file_ops.py
│   ├── paths.py
│   └── statistics.py
│
└── tests/                   # ⚠️ ДОПОЛНИТЬ
    ├── test_cli.py         # ❌ УДАЛИТЬ или реализовать
    ├── test_error_handling.py  # ⚠️ ОПЕЧАТКИ В ТЕСТАХ
    └── conftest.py
```

### 1.3 Поток обработки данных

```
Input/ 
   ↓ [Classifier Cycle 1]
   ├── Direct → Merge_0/Direct/
   ├── Convert → Processing_1/Convert/ → [Converter] → Merge_1/Converted/
   ├── Extract → Processing_1/Extract/ → [Extractor] → Merge_1/Extracted/
   ├── Normalize → Processing_1/Normalize/ → [Normalizers] → Merge_1/Normalized/
   └── Exceptions → Exceptions_1/{Empty|Special|Ambiguous|ErConvert|ErExtract|ErNormalize}
                                                          ↑ ИСПРАВИТЬ ОПЕЧАТКИ ↑
   ↓ [Classifier Cycle 2]
   ... (аналогично для Processing_2, Merge_2, Exceptions_2)
   
   ↓ [Classifier Cycle 3]
   ... (аналогично для Processing_3, Merge_3, Exceptions_3)
   
   ↓ [Final Merger]
Ready2Docling/
```

### 1.4 Критические замечания заказчика

1. **LibreOffice** - это ОБЯЗАТЕЛЬНАЯ зависимость системы, НЕ нужно добавлять fallback
2. **Web UI** - НЕ ТРОГАЕМ в этой итерации, только backend
3. **CLI** - нужно упростить для будущего слоя controller (декораторы для фронтенда)

---

## 2. ПРИОРИТЕТЫ РЕФАКТОРИНГА

### Уровень приоритета

| Приоритет | Описание | Влияние |
|-----------|----------|---------|
| 🔴 P0 | Критические баги, опечатки | Влияет на работу системы |
| 🟠 P1 | Улучшение архитектуры | Улучшает поддержку кода |
| 🟡 P2 | Очистка кода | Уменьшает технический долг |
| 🟢 P3 | Тесты | Повышает надёжность |

### Порядок выполнения

```
ФАЗА 1 (P0): Опечатки → ФАЗА 2 (P1): Архитектура → ФАЗА 3 (P2): Очистка → ФАЗА 4 (P3): Тесты
```

---

## 3. ФАЗА 1: КРИТИЧЕСКИЕ ИСПРАВЛЕНИЯ

### 3.1 🔴 Исправление опечаток в названиях директорий

**Проблема:** В коде используются неправильные названия директорий исключений:
- `ErExtact` → должно быть `ErExtract`
- `ErNormalaze` → должно быть `ErNormalize`

**Файлы для исправления:**

#### 3.1.1 `docprep/core/config.py`

```python
# НАЙТИ (строка ~около 85-90):
for subdir in ["Empty", "Special", "Ambiguous", "ErConvert", "ErNormalaze", "ErExtact"]:

# ЗАМЕНИТЬ НА:
for subdir in ["Empty", "Special", "Ambiguous", "ErConvert", "ErNormalize", "ErExtract"]:
```

#### 3.1.2 `docprep/engine/base_engine.py`

```python
# НАЙТИ в docstring метода move_to_exceptions:
reason: Причина перемещения (Empty, Special, Ambiguous, ErConvert, ErNormalaze, ErExtact)

# ЗАМЕНИТЬ НА:
reason: Причина перемещения (Empty, Special, Ambiguous, ErConvert, ErNormalize, ErExtract)
```

#### 3.1.3 `docprep/engine/extractor.py`

```python
# НАЙТИ:
target_base_dir = exceptions_base / f"Exceptions_{current_cycle}" / "ErExtact"

# ЗАМЕНИТЬ НА:
target_base_dir = exceptions_base / f"Exceptions_{current_cycle}" / "ErExtract"
```

#### 3.1.4 `docprep/engine/normalizers/extension.py`

```python
# НАЙТИ:
target_base_dir = exceptions_base / f"Exceptions_{current_cycle}" / "ErNormalaze"

# ЗАМЕНИТЬ НА:
target_base_dir = exceptions_base / f"Exceptions_{current_cycle}" / "ErNormalize"
```

#### 3.1.5 `docprep/tests/test_error_handling.py`

```python
# НАЙТИ все вхождения:
assert "ErExtact" != "FailedExtraction"
assert "ErNormalaze" is not None
assert (exceptions_1 / "ErNormalaze").exists()
assert (exceptions_1 / "ErExtact").exists()
error_dirs = ["Empty", "Special", "Ambiguous", "ErConvert", "ErNormalaze", "ErExtact"]

# ЗАМЕНИТЬ ВСЕ на корректные:
assert "ErExtract" != "FailedExtraction"
assert "ErNormalize" is not None
assert (exceptions_1 / "ErNormalize").exists()
assert (exceptions_1 / "ErExtract").exists()
error_dirs = ["Empty", "Special", "Ambiguous", "ErConvert", "ErNormalize", "ErExtract"]
```

#### 3.1.6 `docprep/docs/ARCHITECTURE.md`

```markdown
# НАЙТИ в структуре директорий:
│   │   ├── ErNormalaze/ # UNIT с ошибками нормализации
│   │   └── ErExtact/    # UNIT с ошибками извлечения

# ЗАМЕНИТЬ НА:
│   │   ├── ErNormalize/ # UNIT с ошибками нормализации
│   │   └── ErExtract/   # UNIT с ошибками извлечения
```

**Команда для автоматической замены:**
```bash
# Выполнить из корня проекта docprep/
find . -name "*.py" -o -name "*.md" | xargs sed -i 's/ErExtact/ErExtract/g'
find . -name "*.py" -o -name "*.md" | xargs sed -i 's/ErNormalaze/ErNormalize/g'
```

---

## 4. ФАЗА 2: УЛУЧШЕНИЕ АРХИТЕКТУРЫ

### 4.1 🟠 Централизованное логирование

**Текущая проблема:** Каждый модуль настраивает логирование отдельно.

**Создать новый файл `docprep/core/logging_config.py`:**

```python
"""
Централизованная конфигурация логирования для DocPrep.

Используется для единообразного логирования во всех модулях системы.
"""
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

# Формат логов
DEFAULT_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DETAILED_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'

# Глобальный флаг инициализации
_logging_initialized = False


def setup_logging(
    verbose: bool = False,
    log_file: Optional[str] = None,
    log_dir: Optional[Path] = None,
    include_timestamp: bool = True
) -> logging.Logger:
    """
    Настраивает централизованное логирование для DocPrep.
    
    Args:
        verbose: Если True, уровень DEBUG, иначе INFO
        log_file: Имя файла лога (опционально)
        log_dir: Директория для логов (опционально)
        include_timestamp: Добавлять timestamp к имени файла
    
    Returns:
        Корневой logger для docprep
    
    Example:
        >>> from docprep.core.logging_config import setup_logging
        >>> logger = setup_logging(verbose=True)
        >>> logger.info("Starting processing...")
    """
    global _logging_initialized
    
    # Определяем уровень логирования
    level = logging.DEBUG if verbose else logging.INFO
    
    # Выбираем формат
    log_format = DETAILED_FORMAT if verbose else DEFAULT_FORMAT
    
    # Создаём handlers
    handlers = []
    
    # Console handler (всегда)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(logging.Formatter(log_format))
    handlers.append(console_handler)
    
    # File handler (опционально)
    if log_file or log_dir:
        if log_dir:
            log_dir = Path(log_dir)
            log_dir.mkdir(parents=True, exist_ok=True)
            
            if log_file:
                log_path = log_dir / log_file
            else:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S') if include_timestamp else ''
                log_path = log_dir / f"docprep_{timestamp}.log"
        else:
            log_path = Path(log_file)
        
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)  # Файл всегда пишем подробно
        file_handler.setFormatter(logging.Formatter(DETAILED_FORMAT))
        handlers.append(file_handler)
    
    # Настраиваем корневой logger для docprep
    docprep_logger = logging.getLogger('docprep')
    
    # Очищаем существующие handlers (избегаем дублирования)
    if _logging_initialized:
        docprep_logger.handlers.clear()
    
    docprep_logger.setLevel(level)
    for handler in handlers:
        docprep_logger.addHandler(handler)
    
    # Отключаем propagation чтобы избежать дублирования
    docprep_logger.propagate = False
    
    _logging_initialized = True
    
    return docprep_logger


def get_logger(name: str) -> logging.Logger:
    """
    Получает logger для модуля.
    
    Использует иерархию docprep.* для единообразия.
    
    Args:
        name: Имя модуля (обычно __name__)
    
    Returns:
        Logger для модуля
    
    Example:
        >>> from docprep.core.logging_config import get_logger
        >>> logger = get_logger(__name__)
        >>> logger.info("Processing unit...")
    """
    # Преобразуем имя в иерархию docprep
    if not name.startswith('docprep'):
        name = f'docprep.{name}'
    
    return logging.getLogger(name)


# Логгеры для основных компонентов (для удобства импорта)
core_logger = get_logger('core')
engine_logger = get_logger('engine')
cli_logger = get_logger('cli')
utils_logger = get_logger('utils')
```

**Обновить `docprep/core/__init__.py`:**

```python
# Добавить в начало файла:
from .logging_config import setup_logging, get_logger

# Добавить в __all__:
__all__ = [
    # ... существующие экспорты ...
    # Logging
    "setup_logging",
    "get_logger",
]
```

**Обновить `docprep/cli/main.py`:**

```python
# Добавить импорт:
from ..core.logging_config import setup_logging

# В callback функции main():
@app.callback()
def main(
    verbose: bool = verbose_option,
    dry_run: bool = dry_run_option,
):
    """DocPrep - CLI система для preprocessing документов."""
    # Инициализируем логирование
    setup_logging(verbose=verbose)
```

---

### 4.2 🟠 Улучшение State Machine с метаданными

**Текущая проблема:** State trace хранится как список строк без контекста.

**Обновить `docprep/core/state_machine.py`:**

```python
"""
State Machine для управления состояниями UNIT.

Обеспечивает детерминированные переходы между состояниями
с полным отслеживанием истории и метаданных.
"""
import json
import logging
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone

from .exceptions import StateTransitionError

logger = logging.getLogger(__name__)


class UnitState(Enum):
    """Возможные состояния UNIT."""
    RAW = "RAW"
    CLASSIFIED_1 = "CLASSIFIED_1"
    CLASSIFIED_2 = "CLASSIFIED_2"
    CLASSIFIED_3 = "CLASSIFIED_3"
    PENDING_CONVERT = "PENDING_CONVERT"
    PENDING_EXTRACT = "PENDING_EXTRACT"
    PENDING_NORMALIZE = "PENDING_NORMALIZE"
    MERGED_DIRECT = "MERGED_DIRECT"
    MERGED_PROCESSED = "MERGED_PROCESSED"
    EXCEPTION_1 = "EXCEPTION_1"
    EXCEPTION_2 = "EXCEPTION_2"
    EXCEPTION_3 = "EXCEPTION_3"
    READY_FOR_DOCLING = "READY_FOR_DOCLING"


# Разрешённые переходы состояний
ALLOWED_TRANSITIONS: Dict[UnitState, List[UnitState]] = {
    UnitState.RAW: [UnitState.CLASSIFIED_1, UnitState.EXCEPTION_1],
    UnitState.CLASSIFIED_1: [
        UnitState.MERGED_DIRECT,
        UnitState.PENDING_CONVERT,
        UnitState.PENDING_EXTRACT,
        UnitState.PENDING_NORMALIZE,
        UnitState.EXCEPTION_1,
    ],
    UnitState.PENDING_CONVERT: [UnitState.CLASSIFIED_2, UnitState.EXCEPTION_1],
    UnitState.PENDING_EXTRACT: [UnitState.CLASSIFIED_2, UnitState.EXCEPTION_1],
    UnitState.PENDING_NORMALIZE: [UnitState.CLASSIFIED_2, UnitState.EXCEPTION_1],
    UnitState.CLASSIFIED_2: [
        UnitState.MERGED_PROCESSED,
        UnitState.PENDING_CONVERT,
        UnitState.PENDING_EXTRACT,
        UnitState.PENDING_NORMALIZE,
        UnitState.EXCEPTION_2,
    ],
    UnitState.CLASSIFIED_3: [
        UnitState.MERGED_PROCESSED,
        UnitState.EXCEPTION_3,
    ],
    UnitState.MERGED_DIRECT: [UnitState.READY_FOR_DOCLING],
    UnitState.MERGED_PROCESSED: [UnitState.READY_FOR_DOCLING],
    UnitState.EXCEPTION_1: [],  # Терминальное состояние
    UnitState.EXCEPTION_2: [],  # Терминальное состояние
    UnitState.EXCEPTION_3: [],  # Терминальное состояние
    UnitState.READY_FOR_DOCLING: [],  # Терминальное состояние
}


@dataclass
class StateTransition:
    """
    Представляет переход между состояниями с полными метаданными.
    
    Attributes:
        from_state: Исходное состояние (None для первого перехода)
        to_state: Целевое состояние
        timestamp: Время перехода (UTC ISO format)
        operation: Тип операции (classify, convert, extract, normalize, merge)
        cycle: Номер цикла обработки (1, 2, 3)
        metadata: Дополнительные данные о переходе
    """
    from_state: Optional[str]
    to_state: str
    timestamp: str
    operation: str = ""
    cycle: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертирует в словарь для JSON."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StateTransition':
        """Создаёт из словаря."""
        return cls(**data)


class UnitStateMachine:
    """
    State Machine для управления состояниями UNIT.
    
    Обеспечивает:
    - Валидацию переходов согласно ALLOWED_TRANSITIONS
    - Полную историю переходов с метаданными
    - Персистентность через manifest.json
    
    Example:
        >>> sm = UnitStateMachine("UNIT_001", manifest_path)
        >>> sm.transition(UnitState.CLASSIFIED_1, operation="classify", cycle=1)
        >>> print(sm.get_current_state())
        UnitState.CLASSIFIED_1
    """
    
    def __init__(self, unit_id: str, manifest_path: Optional[Path] = None):
        """
        Инициализирует State Machine.
        
        Args:
            unit_id: Идентификатор UNIT
            manifest_path: Путь к manifest.json (опционально)
        """
        self.unit_id = unit_id
        self.manifest_path = manifest_path
        self._current_state: Optional[UnitState] = None
        self._transitions: List[StateTransition] = []
        self._state_trace: List[str] = []  # Для обратной совместимости
        
        # Загружаем состояние из manifest если есть
        if manifest_path and manifest_path.exists():
            self._load_from_manifest()
        else:
            # Начинаем с RAW
            self._current_state = UnitState.RAW
            self._state_trace = [UnitState.RAW.value]
            self._transitions = [StateTransition(
                from_state=None,
                to_state=UnitState.RAW.value,
                timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                operation="init",
                cycle=0
            )]
    
    def _load_from_manifest(self) -> None:
        """Загружает состояние из manifest.json."""
        try:
            with open(self.manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            
            if "state_machine" in manifest:
                sm_data = manifest["state_machine"]
                
                # Загружаем state_trace (обратная совместимость)
                self._state_trace = sm_data.get("state_trace", [])
                
                # Загружаем transitions (новый формат)
                if "transitions" in sm_data:
                    self._transitions = [
                        StateTransition.from_dict(t) for t in sm_data["transitions"]
                    ]
                else:
                    # Конвертируем из старого формата
                    self._transitions = self._convert_trace_to_transitions(self._state_trace)
                
                # Определяем текущее состояние
                if self._state_trace:
                    try:
                        self._current_state = UnitState(self._state_trace[-1])
                    except ValueError:
                        logger.warning(f"Unknown state in trace: {self._state_trace[-1]}")
                        self._current_state = UnitState.RAW
                else:
                    self._current_state = UnitState.RAW
            else:
                self._current_state = UnitState.RAW
                self._state_trace = [UnitState.RAW.value]
                
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.warning(f"Failed to load manifest for {self.unit_id}: {e}")
            self._current_state = UnitState.RAW
            self._state_trace = [UnitState.RAW.value]
    
    def _convert_trace_to_transitions(self, trace: List[str]) -> List[StateTransition]:
        """Конвертирует старый state_trace в новый формат transitions."""
        transitions = []
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        
        for i, state in enumerate(trace):
            from_state = trace[i - 1] if i > 0 else None
            transitions.append(StateTransition(
                from_state=from_state,
                to_state=state,
                timestamp=now,
                operation="migrated",
                cycle=1
            ))
        
        return transitions
    
    def get_current_state(self) -> UnitState:
        """Возвращает текущее состояние."""
        return self._current_state or UnitState.RAW
    
    def get_state_trace(self) -> List[str]:
        """Возвращает историю состояний (для обратной совместимости)."""
        return self._state_trace.copy()
    
    def get_transitions(self) -> List[StateTransition]:
        """Возвращает полную историю переходов с метаданными."""
        return self._transitions.copy()
    
    def can_transition_to(self, new_state: UnitState) -> bool:
        """Проверяет, возможен ли переход в указанное состояние."""
        if self._current_state is None:
            return new_state == UnitState.RAW
        
        allowed = ALLOWED_TRANSITIONS.get(self._current_state, [])
        return new_state in allowed
    
    def transition(
        self,
        new_state: UnitState,
        operation: str = "",
        cycle: int = 1,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Выполняет переход в новое состояние.
        
        Args:
            new_state: Целевое состояние
            operation: Тип операции (classify, convert, extract, normalize, merge)
            cycle: Номер цикла (1, 2, 3)
            metadata: Дополнительные данные
        
        Raises:
            StateTransitionError: Если переход не разрешён
        """
        if not self.can_transition_to(new_state):
            raise StateTransitionError(
                f"Transition from {self._current_state} to {new_state} not allowed",
                current_state=self._current_state.value if self._current_state else "None",
                target_state=new_state.value,
                unit_id=self.unit_id
            )
        
        # Создаём запись о переходе
        transition = StateTransition(
            from_state=self._current_state.value if self._current_state else None,
            to_state=new_state.value,
            timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            operation=operation,
            cycle=cycle,
            metadata=metadata or {}
        )
        
        # Обновляем состояние
        self._current_state = new_state
        self._state_trace.append(new_state.value)
        self._transitions.append(transition)
        
        logger.debug(f"Unit {self.unit_id}: {transition.from_state} -> {transition.to_state}")
    
    def is_terminal(self) -> bool:
        """Проверяет, находится ли UNIT в терминальном состоянии."""
        return self._current_state in [
            UnitState.READY_FOR_DOCLING,
            UnitState.EXCEPTION_1,
            UnitState.EXCEPTION_2,
            UnitState.EXCEPTION_3,
        ]
    
    def to_manifest_dict(self) -> Dict[str, Any]:
        """
        Возвращает данные для сохранения в manifest.
        
        Returns:
            Словарь для секции state_machine в manifest.json
        """
        return {
            "initial_state": self._state_trace[0] if self._state_trace else UnitState.RAW.value,
            "current_state": self._current_state.value if self._current_state else UnitState.RAW.value,
            "final_state": self._state_trace[-1] if self._state_trace else None,
            "state_trace": self._state_trace,  # Обратная совместимость
            "transitions": [t.to_dict() for t in self._transitions],  # Новый формат
        }
    
    def save_to_manifest(self, manifest_path: Optional[Path] = None) -> None:
        """
        Сохраняет состояние в manifest.json.
        
        Args:
            manifest_path: Путь к manifest (использует self.manifest_path если не указан)
        """
        path = manifest_path or self.manifest_path
        if not path:
            raise ValueError("No manifest path specified")
        
        try:
            # Загружаем существующий manifest или создаём новый
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
            else:
                manifest = {"schema_version": "2.0", "unit_id": self.unit_id}
            
            # Обновляем секцию state_machine
            manifest["state_machine"] = self.to_manifest_dict()
            
            # Сохраняем
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            raise RuntimeError(f"Failed to save state to manifest: {e}")


def validate_state_transition(current_state: UnitState, new_state: UnitState) -> bool:
    """
    Валидирует переход между состояниями.
    
    Args:
        current_state: Текущее состояние
        new_state: Целевое состояние
    
    Returns:
        True если переход разрешён
    """
    allowed = ALLOWED_TRANSITIONS.get(current_state, [])
    return new_state in allowed
```

---

### 4.3 🟠 Вынос Magic Numbers в константы

**Обновить `docprep/core/config.py`:**

```python
# Добавить после существующих констант:

# ============================================================================
# СИСТЕМНЫЕ КОНСТАНТЫ
# ============================================================================

# Обработка
MAX_CYCLES = 3  # Уже есть
MAX_FILES_PER_UNIT = 1000
MAX_ARCHIVE_DEPTH = 5
MAX_ARCHIVE_SIZE_MB = 100
MAX_ARCHIVE_TOTAL_SIZE_MB = 500

# Конвертация
CONVERSION_TIMEOUT_SECONDS = 300
LIBREOFFICE_RETRY_COUNT = 3

# Классификация
DEFAULT_CONFIDENCE_THRESHOLD = 0.85
MIN_CONFIDENCE_THRESHOLD = 0.5

# Retry политика
DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_RETRY_DELAY_SECONDS = 1.0
MAX_RETRY_DELAY_SECONDS = 60.0

# Файлы
MIN_FILE_SIZE_BYTES = 1
MAX_FILE_NAME_LENGTH = 255

# Директории исключений (единый источник правды)
EXCEPTION_SUBDIRS = [
    "Empty",
    "Special", 
    "Ambiguous",
    "ErConvert",
    "ErExtract",   # ИСПРАВЛЕНО: было ErExtact
    "ErNormalize"  # ИСПРАВЛЕНО: было ErNormalaze
]
```

**Обновить использование в коде:**

```python
# В config.py init_directory_structure:
# БЫЛО:
for subdir in ["Empty", "Special", "Ambiguous", "ErConvert", "ErNormalaze", "ErExtact"]:

# СТАЛО:
for subdir in EXCEPTION_SUBDIRS:
```

```python
# В merger.py (пример):
# БЫЛО:
if len(files) > 1000:

# СТАЛО:
from ..core.config import MAX_FILES_PER_UNIT
if len(files) > MAX_FILES_PER_UNIT:
```

---

### 4.4 🟠 Унификация обработки ошибок

**Обновить `docprep/core/error_policy.py`:**

```python
# Добавить в конец файла:

from typing import Callable, TypeVar, Generic
from functools import wraps

T = TypeVar('T')


class OperationResult(Generic[T]):
    """
    Результат операции с унифицированной обработкой успеха/ошибки.
    
    Паттерн Result для единообразной обработки во всех движках.
    """
    
    def __init__(
        self,
        success: bool,
        value: Optional[T] = None,
        error: Optional[str] = None,
        error_type: Optional[str] = None,
        should_retry: bool = False,
        should_quarantine: bool = False
    ):
        self.success = success
        self.value = value
        self.error = error
        self.error_type = error_type
        self.should_retry = should_retry
        self.should_quarantine = should_quarantine
    
    @classmethod
    def ok(cls, value: T) -> 'OperationResult[T]':
        """Создаёт успешный результат."""
        return cls(success=True, value=value)
    
    @classmethod
    def fail(
        cls,
        error: str,
        error_type: str = "unknown",
        should_retry: bool = False,
        should_quarantine: bool = False
    ) -> 'OperationResult[T]':
        """Создаёт результат с ошибкой."""
        return cls(
            success=False,
            error=error,
            error_type=error_type,
            should_retry=should_retry,
            should_quarantine=should_quarantine
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертирует в словарь для JSON/логирования."""
        return {
            "success": self.success,
            "value": self.value,
            "error": self.error,
            "error_type": self.error_type,
            "should_retry": self.should_retry,
            "should_quarantine": self.should_quarantine
        }


def with_error_handling(
    operation_name: str,
    policy: ErrorPolicy = ErrorPolicy.RETRY
) -> Callable:
    """
    Декоратор для унифицированной обработки ошибок.
    
    Args:
        operation_name: Имя операции для логирования
        policy: Политика обработки ошибок
    
    Example:
        @with_error_handling("conversion", ErrorPolicy.RETRY)
        def convert_file(self, file_path: Path) -> OperationResult:
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> OperationResult:
            try:
                result = func(*args, **kwargs)
                # Если функция уже возвращает OperationResult, передаём как есть
                if isinstance(result, OperationResult):
                    return result
                # Иначе оборачиваем в успешный результат
                return OperationResult.ok(result)
                
            except QuarantineError as e:
                logger.error(f"[{operation_name}] Quarantine error: {e}")
                return OperationResult.fail(
                    str(e),
                    error_type="quarantine",
                    should_quarantine=True
                )
            except OperationError as e:
                logger.warning(f"[{operation_name}] Operation error: {e}")
                should_retry = policy == ErrorPolicy.RETRY
                return OperationResult.fail(
                    str(e),
                    error_type="operation",
                    should_retry=should_retry
                )
            except Exception as e:
                logger.exception(f"[{operation_name}] Unexpected error: {e}")
                return OperationResult.fail(
                    str(e),
                    error_type="unexpected"
                )
        
        return wrapper
    return decorator
```

---

## 5. ФАЗА 3: ОЧИСТКА И ОПТИМИЗАЦИЯ

### 5.1 🟡 Упрощение CLI модулей

**Создать `docprep/cli/utils.py` (общие утилиты):**

```python
"""
Общие утилиты для CLI команд.

Содержит вспомогательные функции и декораторы для унификации CLI.
"""
import typer
from pathlib import Path
from datetime import datetime
from typing import Any, Callable, Optional
from functools import wraps

try:
    from typer.models import OptionInfo
except ImportError:
    OptionInfo = None


def unwrap_option(val: Any) -> Any:
    """
    Извлекает значение из OptionInfo если необходимо.
    
    Typer может передавать OptionInfo вместо значения при программном вызове.
    """
    if OptionInfo and isinstance(val, OptionInfo):
        return val.default
    return val


def unwrap_all_options(func: Callable) -> Callable:
    """
    Декоратор для автоматического unwrap всех OptionInfo параметров.
    
    Example:
        @app.command("convert")
        @unwrap_all_options
        def convert(input_dir: Path, cycle: int = 1):
            # input_dir и cycle уже unwrapped
            pass
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        unwrapped_kwargs = {k: unwrap_option(v) for k, v in kwargs.items()}
        return func(*args, **unwrapped_kwargs)
    return wrapper


def validate_input_dir(input_dir: Path) -> None:
    """
    Валидирует входную директорию.
    
    Raises:
        typer.Exit: Если директория не существует
    """
    if not input_dir.exists():
        typer.echo(f"❌ Директория не найдена: {input_dir}", err=True)
        raise typer.Exit(1)


def get_protocol_date(date_str: Optional[str] = None) -> str:
    """
    Возвращает дату протокола.
    
    Args:
        date_str: Дата в формате YYYY-MM-DD или None
    
    Returns:
        Дата в формате YYYY-MM-DD (текущая если не указана)
    """
    return date_str or datetime.now().strftime("%Y-%m-%d")


def print_results(results: dict, operation: str = "Обработка") -> None:
    """
    Выводит результаты операции.
    
    Args:
        results: Словарь с результатами
        operation: Название операции для вывода
    """
    processed = results.get('units_processed', 0)
    failed = results.get('units_failed', 0)
    
    typer.echo(f"\n✅ {operation} завершена: {processed} UNIT")
    
    if failed > 0:
        typer.echo(f"❌ Ошибок: {failed}", err=True)
        
        # Выводим детали ошибок если есть
        errors = results.get('errors', [])
        for error in errors[:5]:  # Первые 5
            unit_id = error.get('unit_id', 'unknown')
            error_msg = error.get('error', 'Unknown error')
            typer.echo(f"  - {unit_id}: {error_msg}", err=True)
        
        if len(errors) > 5:
            typer.echo(f"  ... и ещё {len(errors) - 5} ошибок", err=True)


def echo_verbose(message: str, verbose: bool) -> None:
    """Выводит сообщение только в verbose режиме."""
    if verbose:
        typer.echo(message)
```

**Обновить `docprep/cli/substage.py` (пример упрощения):**

```python
# Заменить повторяющийся код на использование utils:

from .utils import unwrap_all_options, validate_input_dir, get_protocol_date, print_results, echo_verbose

@app.command("convert")
@unwrap_all_options  # Автоматический unwrap
def substage_convert_run(
    input_dir: Path = typer.Option(..., "--input", help="Входная директория"),
    cycle: int = typer.Option(1, "--cycle", help="Номер цикла (1, 2, 3)"),
    protocol_date: Optional[str] = typer.Option(None, "--date", help="Дата протокола"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
    dry_run: bool = typer.Option(False, "--dry-run"),
):
    """Конвертация форматов (doc→docx и т.д.)."""
    validate_input_dir(input_dir)
    protocol_date = get_protocol_date(protocol_date)
    
    typer.echo(f"🔄 Конвертация: {input_dir} (цикл {cycle})")
    
    converter = Converter()
    
    def process_unit(unit_path: Path) -> dict:
        result = converter.convert_unit(
            unit_path=unit_path,
            cycle=cycle,
            protocol_date=protocol_date,
            dry_run=dry_run,
        )
        echo_verbose(f"  ✓ {unit_path.name}: {result.get('files_converted', 0)} файлов", verbose)
        return result
    
    results = process_directory_units(
        source_dir=input_dir,
        processor_func=process_unit,
        dry_run=dry_run,
    )
    
    print_results(results, "Конвертация")
```

---

### 5.2 🟡 Удаление мусорного кода

**Файлы для удаления:**

1. **`docprep/cli/chunked_classifier.py`** - дублирует функциональность classifier
   ```bash
   rm docprep/cli/chunked_classifier.py
   ```

2. **`docprep/tests/test_cli.py`** - содержит только TODO-заглушки
   ```bash
   rm docprep/tests/test_cli.py
   ```

**Обновить `docprep/cli/main.py`:**

```python
# УДАЛИТЬ строку:
from . import chunked_classifier

# УДАЛИТЬ строку:
app.add_typer(chunked_classifier.app, name="chunked-classifier")
```

**Создать `.gitignore` (если нет):**

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
venv/
ENV/
env/

# IDE
.idea/
.vscode/
*.swp
*.swo

# Testing
.pytest_cache/
.coverage
htmlcov/

# Logs
*.log
logs/

# Data (не коммитим реальные данные)
Data/
!Data/.gitkeep
```

---

## 6. ФАЗА 4: ТЕСТОВОЕ ПОКРЫТИЕ

### 6.1 🟢 Тесты для State Machine

**Создать `docprep/tests/test_state_machine.py`:**

```python
"""
Тесты для State Machine.
"""
import pytest
import tempfile
import json
from pathlib import Path
from datetime import datetime

from docprep.core.state_machine import (
    UnitState,
    UnitStateMachine,
    StateTransition,
    ALLOWED_TRANSITIONS,
    validate_state_transition,
)
from docprep.core.exceptions import StateTransitionError


@pytest.fixture
def temp_manifest(tmp_path):
    """Создаёт временный manifest файл."""
    manifest_path = tmp_path / "UNIT_001" / "manifest.json"
    manifest_path.parent.mkdir(parents=True)
    
    manifest = {
        "schema_version": "2.0",
        "unit_id": "UNIT_001",
        "state_machine": {
            "initial_state": "RAW",
            "current_state": "RAW",
            "state_trace": ["RAW"]
        }
    }
    
    with open(manifest_path, "w") as f:
        json.dump(manifest, f)
    
    return manifest_path


class TestStateTransition:
    """Тесты для dataclass StateTransition."""
    
    def test_create_transition(self):
        """Тест создания перехода."""
        transition = StateTransition(
            from_state="RAW",
            to_state="CLASSIFIED_1",
            timestamp="2025-01-01T00:00:00Z",
            operation="classify",
            cycle=1
        )
        
        assert transition.from_state == "RAW"
        assert transition.to_state == "CLASSIFIED_1"
        assert transition.operation == "classify"
        assert transition.cycle == 1
    
    def test_to_dict(self):
        """Тест конвертации в словарь."""
        transition = StateTransition(
            from_state="RAW",
            to_state="CLASSIFIED_1",
            timestamp="2025-01-01T00:00:00Z"
        )
        
        result = transition.to_dict()
        
        assert isinstance(result, dict)
        assert result["from_state"] == "RAW"
        assert result["to_state"] == "CLASSIFIED_1"
    
    def test_from_dict(self):
        """Тест создания из словаря."""
        data = {
            "from_state": "RAW",
            "to_state": "CLASSIFIED_1",
            "timestamp": "2025-01-01T00:00:00Z",
            "operation": "classify",
            "cycle": 1,
            "metadata": {"category": "direct"}
        }
        
        transition = StateTransition.from_dict(data)
        
        assert transition.from_state == "RAW"
        assert transition.metadata == {"category": "direct"}


class TestUnitStateMachine:
    """Тесты для UnitStateMachine."""
    
    def test_init_without_manifest(self):
        """Тест инициализации без manifest."""
        sm = UnitStateMachine("UNIT_001")
        
        assert sm.get_current_state() == UnitState.RAW
        assert sm.get_state_trace() == ["RAW"]
    
    def test_init_with_manifest(self, temp_manifest):
        """Тест инициализации с manifest."""
        sm = UnitStateMachine("UNIT_001", temp_manifest)
        
        assert sm.get_current_state() == UnitState.RAW
    
    def test_valid_transition(self):
        """Тест валидного перехода."""
        sm = UnitStateMachine("UNIT_001")
        
        sm.transition(UnitState.CLASSIFIED_1, operation="classify", cycle=1)
        
        assert sm.get_current_state() == UnitState.CLASSIFIED_1
        assert "CLASSIFIED_1" in sm.get_state_trace()
    
    def test_invalid_transition_raises(self):
        """Тест невалидного перехода."""
        sm = UnitStateMachine("UNIT_001")
        
        # RAW -> READY_FOR_DOCLING не разрешён
        with pytest.raises(StateTransitionError):
            sm.transition(UnitState.READY_FOR_DOCLING)
    
    def test_can_transition_to(self):
        """Тест проверки возможности перехода."""
        sm = UnitStateMachine("UNIT_001")
        
        assert sm.can_transition_to(UnitState.CLASSIFIED_1) is True
        assert sm.can_transition_to(UnitState.READY_FOR_DOCLING) is False
    
    def test_is_terminal(self):
        """Тест определения терминального состояния."""
        sm = UnitStateMachine("UNIT_001")
        
        assert sm.is_terminal() is False
        
        sm.transition(UnitState.EXCEPTION_1)
        
        assert sm.is_terminal() is True
    
    def test_transition_with_metadata(self):
        """Тест перехода с метаданными."""
        sm = UnitStateMachine("UNIT_001")
        
        sm.transition(
            UnitState.CLASSIFIED_1,
            operation="classify",
            cycle=1,
            metadata={"category": "direct", "confidence": 0.95}
        )
        
        transitions = sm.get_transitions()
        last_transition = transitions[-1]
        
        assert last_transition.metadata == {"category": "direct", "confidence": 0.95}
    
    def test_save_to_manifest(self, tmp_path):
        """Тест сохранения в manifest."""
        manifest_path = tmp_path / "UNIT_001" / "manifest.json"
        manifest_path.parent.mkdir(parents=True)
        
        sm = UnitStateMachine("UNIT_001", manifest_path)
        sm.transition(UnitState.CLASSIFIED_1, operation="classify", cycle=1)
        sm.save_to_manifest()
        
        # Проверяем сохранённые данные
        with open(manifest_path) as f:
            manifest = json.load(f)
        
        assert manifest["state_machine"]["current_state"] == "CLASSIFIED_1"
        assert "transitions" in manifest["state_machine"]
    
    def test_full_workflow(self):
        """Тест полного workflow от RAW до READY_FOR_DOCLING."""
        sm = UnitStateMachine("UNIT_001")
        
        # RAW -> CLASSIFIED_1 (direct)
        sm.transition(UnitState.CLASSIFIED_1, operation="classify", cycle=1)
        
        # CLASSIFIED_1 -> MERGED_DIRECT
        sm.transition(UnitState.MERGED_DIRECT, operation="merge", cycle=1)
        
        # MERGED_DIRECT -> READY_FOR_DOCLING
        sm.transition(UnitState.READY_FOR_DOCLING, operation="final_merge", cycle=1)
        
        assert sm.get_current_state() == UnitState.READY_FOR_DOCLING
        assert sm.is_terminal() is True
        assert len(sm.get_state_trace()) == 4


class TestAllowedTransitions:
    """Тесты для таблицы переходов."""
    
    def test_raw_allowed_transitions(self):
        """RAW может перейти только в CLASSIFIED_1 или EXCEPTION_1."""
        allowed = ALLOWED_TRANSITIONS[UnitState.RAW]
        
        assert UnitState.CLASSIFIED_1 in allowed
        assert UnitState.EXCEPTION_1 in allowed
        assert len(allowed) == 2
    
    def test_terminal_states_have_no_transitions(self):
        """Терминальные состояния не имеют переходов."""
        terminal_states = [
            UnitState.EXCEPTION_1,
            UnitState.EXCEPTION_2,
            UnitState.EXCEPTION_3,
            UnitState.READY_FOR_DOCLING,
        ]
        
        for state in terminal_states:
            assert ALLOWED_TRANSITIONS[state] == []


class TestValidateStateTransition:
    """Тесты для функции validate_state_transition."""
    
    def test_valid_transition(self):
        """Тест валидного перехода."""
        assert validate_state_transition(UnitState.RAW, UnitState.CLASSIFIED_1) is True
    
    def test_invalid_transition(self):
        """Тест невалидного перехода."""
        assert validate_state_transition(UnitState.RAW, UnitState.READY_FOR_DOCLING) is False
```

---

## 7. ФАЙЛОВАЯ КАРТА ИЗМЕНЕНИЙ

### Сводная таблица

| Фаза | Файл | Действие | Приоритет |
|------|------|----------|-----------|
| 1 | `core/config.py` | Исправить опечатки | 🔴 P0 |
| 1 | `engine/base_engine.py` | Исправить опечатки в docstring | 🔴 P0 |
| 1 | `engine/extractor.py` | ErExtact → ErExtract | 🔴 P0 |
| 1 | `engine/normalizers/extension.py` | ErNormalaze → ErNormalize | 🔴 P0 |
| 1 | `tests/test_error_handling.py` | Исправить все опечатки | 🔴 P0 |
| 1 | `docs/ARCHITECTURE.md` | Исправить в документации | 🔴 P0 |
| 2 | `core/logging_config.py` | **СОЗДАТЬ** | 🟠 P1 |
| 2 | `core/__init__.py` | Добавить экспорты | 🟠 P1 |
| 2 | `cli/main.py` | Интегрировать logging | 🟠 P1 |
| 2 | `core/state_machine.py` | Добавить StateTransition | 🟠 P1 |
| 2 | `core/config.py` | Добавить константы | 🟠 P1 |
| 2 | `core/error_policy.py` | Добавить OperationResult | 🟠 P1 |
| 3 | `cli/utils.py` | **СОЗДАТЬ** (если нет) или обновить | 🟡 P2 |
| 3 | `cli/substage.py` | Упростить через utils | 🟡 P2 |
| 3 | `cli/stage.py` | Упростить через utils | 🟡 P2 |
| 3 | `cli/chunked_classifier.py` | **УДАЛИТЬ** | 🟡 P2 |
| 3 | `cli/main.py` | Удалить импорт chunked_classifier | 🟡 P2 |
| 3 | `tests/test_cli.py` | **УДАЛИТЬ** | 🟡 P2 |
| 3 | `.gitignore` | **СОЗДАТЬ** | 🟡 P2 |
| 4 | `tests/test_state_machine.py` | **СОЗДАТЬ** | 🟢 P3 |

---

## 8. ЧЕКЛИСТ ВАЛИДАЦИИ

### После каждой фазы проверять:

```bash
# 1. Синтаксис Python
python -m py_compile docprep/**/*.py

# 2. Импорты работают
python -c "from docprep.core import *; from docprep.engine import *; from docprep.cli.main import app"

# 3. CLI работает
python -m docprep.cli.main --help

# 4. Тесты проходят
pytest docprep/tests/ -v

# 5. Нет опечаток (финальная проверка)
grep -rn "ErExtact\|ErNormalaze" docprep/
# Должно быть пусто!
```

### Финальный чеклист

- [ ] Все опечатки исправлены (grep не находит)
- [ ] CLI запускается без ошибок
- [ ] Все тесты проходят
- [ ] Новые тесты для State Machine работают
- [ ] Документация обновлена
- [ ] .gitignore создан
- [ ] Мусорные файлы удалены

---

## 📌 ВАЖНЫЕ ЗАМЕЧАНИЯ

1. **LibreOffice** - НЕ добавлять fallback, это обязательная зависимость
2. **Web UI** - НЕ трогаем в этой итерации
3. **Обратная совместимость** - State Machine должен работать со старыми manifest
4. **Тестирование** - после каждого изменения запускать тесты

---

**Документ подготовлен:** Senior Backend Developer  
**Дата:** 2026-01-17  
**Статус:** Готов к выполнению в Claude Code
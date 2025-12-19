"""
State Machine для управления переходами состояний UNIT согласно PRD раздел 13.

Реализует детерминированную state machine на уровне UNIT, где файловая система
является материализованным представлением состояний.
"""
from enum import Enum
from typing import List, Optional, Dict, Any
from pathlib import Path
import json
from datetime import datetime


class UnitState(Enum):
    """Состояния UNIT согласно PRD раздел 13.1."""
    RAW_INPUT = "RAW_INPUT"
    CLASSIFIED_1 = "CLASSIFIED_1"
    CLASSIFIED_2 = "CLASSIFIED_2"
    CLASSIFIED_3 = "CLASSIFIED_3"
    PENDING_1 = "PENDING_1"
    PENDING_2 = "PENDING_2"
    PENDING_3 = "PENDING_3"
    MERGED_1_DIRECT = "MERGED_1_DIRECT"
    MERGED_2 = "MERGED_2"
    MERGED_3 = "MERGED_3"
    EXCEPTIONS_1 = "EXCEPTIONS_1"
    EXCEPTIONS_2 = "EXCEPTIONS_2"
    EXCEPTIONS_3 = "EXCEPTIONS_3"
    READY2DOCLING = "READY2DOCLING"


# Разрешенные переходы согласно PRD раздел 13.1
ALLOWED_TRANSITIONS = {
    UnitState.RAW_INPUT: [
        UnitState.CLASSIFIED_1
    ],
    UnitState.CLASSIFIED_1: [
        UnitState.MERGED_1_DIRECT,
        UnitState.PENDING_1,
        UnitState.EXCEPTIONS_1
    ],
    UnitState.PENDING_1: [
        UnitState.CLASSIFIED_2
    ],
    UnitState.CLASSIFIED_2: [
        UnitState.MERGED_2,
        UnitState.PENDING_2,
        UnitState.EXCEPTIONS_2
    ],
    UnitState.PENDING_2: [
        UnitState.CLASSIFIED_3
    ],
    UnitState.CLASSIFIED_3: [
        UnitState.MERGED_3,
        UnitState.EXCEPTIONS_3
    ],
    UnitState.MERGED_1_DIRECT: [
        UnitState.READY2DOCLING
    ],
    UnitState.MERGED_2: [
        UnitState.READY2DOCLING
    ],
    UnitState.MERGED_3: [
        UnitState.READY2DOCLING
    ],
    # Финальные состояния
    UnitState.READY2DOCLING: [],
    UnitState.EXCEPTIONS_1: [],
    UnitState.EXCEPTIONS_2: [],
    UnitState.EXCEPTIONS_3: []
}


class UnitStateMachine:
    """
    State Machine для управления переходами состояний UNIT.
    
    Согласно PRD раздел 13:
    - UNIT никогда не дробится
    - UNIT может находиться только в одном состоянии
    - Переходы выполняются только через Classifier
    - Максимум 3 классификационных цикла
    """
    
    def __init__(self, unit_id: str, manifest_path: Optional[Path] = None):
        """
        Инициализирует state machine для UNIT.
        
        Args:
            unit_id: Идентификатор UNIT
            manifest_path: Путь к manifest.json (опционально)
        """
        self.unit_id = unit_id
        self.manifest_path = manifest_path
        self._state_trace: List[str] = []
        self._current_state: Optional[UnitState] = None
        
        # Загружаем состояние из manifest, если он существует
        if manifest_path and manifest_path.exists():
            self._load_from_manifest()
        else:
            # Начальное состояние
            self._current_state = UnitState.RAW_INPUT
            self._state_trace = [UnitState.RAW_INPUT.value]
    
    def _load_from_manifest(self) -> None:
        """Загружает состояние из manifest.json."""
        try:
            with open(self.manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
            
            # Загружаем state_trace из manifest v2
            if "state_machine" in manifest:
                state_machine = manifest["state_machine"]
                state_trace = state_machine.get("state_trace", [])
                
                if state_trace:
                    self._state_trace = state_trace
                    # Текущее состояние - последнее в trace
                    last_state_str = state_trace[-1]
                    try:
                        self._current_state = UnitState(last_state_str)
                    except ValueError:
                        # Если состояние неизвестно, начинаем с RAW_INPUT
                        self._current_state = UnitState.RAW_INPUT
                        self._state_trace = [UnitState.RAW_INPUT.value]
                else:
                    self._current_state = UnitState.RAW_INPUT
                    self._state_trace = [UnitState.RAW_INPUT.value]
            else:
                # Старый формат manifest - начинаем с RAW_INPUT
                self._current_state = UnitState.RAW_INPUT
                self._state_trace = [UnitState.RAW_INPUT.value]
        except Exception:
            # При ошибке загрузки начинаем с начального состояния
            self._current_state = UnitState.RAW_INPUT
            self._state_trace = [UnitState.RAW_INPUT.value]
    
    def get_current_state(self) -> UnitState:
        """Возвращает текущее состояние UNIT."""
        return self._current_state
    
    def get_state_trace(self) -> List[str]:
        """Возвращает историю переходов состояний."""
        return self._state_trace.copy()
    
    def can_transition_to(self, new_state: UnitState) -> bool:
        """
        Проверяет, возможен ли переход в новое состояние.
        
        Args:
            new_state: Целевое состояние
        
        Returns:
            True если переход разрешен, False иначе
        """
        if self._current_state is None:
            return False
        
        allowed = ALLOWED_TRANSITIONS.get(self._current_state, [])
        return new_state in allowed
    
    def transition(self, new_state: UnitState, reason: Optional[str] = None) -> bool:
        """
        Выполняет переход в новое состояние.
        
        Args:
            new_state: Целевое состояние
            reason: Причина перехода (опционально)
        
        Returns:
            True если переход выполнен, False если переход невозможен
        
        Raises:
            ValueError: Если переход не разрешен
        """
        if not self.can_transition_to(new_state):
            raise ValueError(
                f"Transition from {self._current_state.value} to {new_state.value} "
                f"is not allowed for unit {self.unit_id}"
            )
        
        # Выполняем переход
        self._current_state = new_state
        self._state_trace.append(new_state.value)
        
        return True
    
    def get_cycle_from_state(self) -> Optional[int]:
        """
        Определяет номер цикла на основе текущего состояния.
        
        Returns:
            Номер цикла (1, 2, 3) или None
        """
        if self._current_state in [UnitState.CLASSIFIED_1, UnitState.PENDING_1, 
                                    UnitState.MERGED_1_DIRECT, UnitState.EXCEPTIONS_1]:
            return 1
        elif self._current_state in [UnitState.CLASSIFIED_2, UnitState.PENDING_2,
                                      UnitState.MERGED_2, UnitState.EXCEPTIONS_2]:
            return 2
        elif self._current_state in [UnitState.CLASSIFIED_3, UnitState.PENDING_3,
                                      UnitState.MERGED_3, UnitState.EXCEPTIONS_3]:
            return 3
        return None
    
    def is_final_state(self) -> bool:
        """Проверяет, является ли текущее состояние финальным."""
        return self._current_state in [
            UnitState.READY2DOCLING,
            UnitState.EXCEPTIONS_1,
            UnitState.EXCEPTIONS_2,
            UnitState.EXCEPTIONS_3
        ]
    
    def is_max_cycle_reached(self) -> bool:
        """Проверяет, достигнут ли максимальный цикл (3)."""
        cycle = self.get_cycle_from_state()
        return cycle is not None and cycle >= 3
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Возвращает представление state machine в виде словаря для manifest.
        
        Returns:
            Словарь с информацией о state machine
        """
        return {
            "initial_state": self._state_trace[0] if self._state_trace else UnitState.RAW_INPUT.value,
            "current_state": self._current_state.value if self._current_state else UnitState.RAW_INPUT.value,
            "final_state": self._state_trace[-1] if self._state_trace else None,
            "state_trace": self._state_trace.copy()
        }
    
    def save_to_manifest(self, manifest_path: Path) -> None:
        """
        Сохраняет состояние в manifest.json.
        
        Args:
            manifest_path: Путь к manifest.json
        """
        try:
            # Загружаем существующий manifest или создаем новый
            if manifest_path.exists():
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    manifest = json.load(f)
            else:
                manifest = {
                    "schema_version": "2.0",
                    "unit_id": self.unit_id
                }
            
            # Обновляем state_machine секцию
            manifest["state_machine"] = self.to_dict()
            
            # Сохраняем
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            with open(manifest_path, 'w', encoding='utf-8') as f:
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
        True если переход разрешен
    """
    allowed = ALLOWED_TRANSITIONS.get(current_state, [])
    return new_state in allowed


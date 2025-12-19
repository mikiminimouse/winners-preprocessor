"""
Управление итеративными циклами обработки UNIT согласно PRD.

Каждый UNIT может проходить до 3 циклов обработки:
- Cycle 1: RAW_INPUT → CLASSIFIED_1 → PENDING_1/MERGED_1_DIRECT/EXCEPTIONS_1
- Cycle 2: PENDING_1 → CLASSIFIED_2 → MERGED_2/PENDING_2/EXCEPTIONS_2
- Cycle 3: PENDING_2 → CLASSIFIED_3 → MERGED_3/EXCEPTIONS_3
"""
from typing import Optional, Dict
from pathlib import Path
from .config import MAX_CYCLES, get_cycle_directories


class CycleManager:
    """
    Менеджер для управления итеративными циклами обработки UNIT.
    
    Согласно PRD раздел 8:
    - Максимум 3 итерации
    - Каждый цикл: Classifier → маршрутизация → обработка → повторный Classifier
    """
    
    def __init__(self, initial_cycle: int = 1):
        """
        Инициализирует CycleManager.
        
        Args:
            initial_cycle: Начальный цикл (по умолчанию 1)
        
        Raises:
            ValueError: Если initial_cycle не в диапазоне 1-3
        """
        if initial_cycle < 1 or initial_cycle > MAX_CYCLES:
            raise ValueError(f"Initial cycle must be between 1 and {MAX_CYCLES}, got {initial_cycle}")
        
        self._current_cycle = initial_cycle
    
    def get_current_cycle(self) -> int:
        """Возвращает текущий номер цикла."""
        return self._current_cycle
    
    def get_next_cycle(self) -> Optional[int]:
        """
        Возвращает следующий цикл, если он существует.
        
        Returns:
            Номер следующего цикла или None, если достигнут максимум
        """
        if self.is_max_cycle():
            return None
        return self._current_cycle + 1
    
    def is_max_cycle(self) -> bool:
        """
        Проверяет, достигнут ли максимальный цикл.
        
        Returns:
            True если текущий цикл равен MAX_CYCLES
        """
        return self._current_cycle >= MAX_CYCLES
    
    def advance_cycle(self) -> bool:
        """
        Переходит к следующему циклу.
        
        Returns:
            True если переход выполнен, False если достигнут максимум
        """
        if self.is_max_cycle():
            return False
        
        self._current_cycle += 1
        return True
    
    def set_cycle(self, cycle: int) -> None:
        """
        Устанавливает текущий цикл.
        
        Args:
            cycle: Номер цикла (1-3)
        
        Raises:
            ValueError: Если cycle не в диапазоне 1-3
        """
        if cycle < 1 or cycle > MAX_CYCLES:
            raise ValueError(f"Cycle must be between 1 and {MAX_CYCLES}, got {cycle}")
        self._current_cycle = cycle
    
    def get_pending_dir(self) -> Path:
        """
        Возвращает директорию Pending для текущего цикла.
        
        Returns:
            Path к Pending_N директории
        """
        cycle_dirs = get_cycle_directories(self._current_cycle)
        return cycle_dirs["pending_dir"]
    
    def get_merge_dir(self) -> Path:
        """
        Возвращает директорию Merge для текущего цикла.
        
        Returns:
            Path к Merge_N директории
        """
        cycle_dirs = get_cycle_directories(self._current_cycle)
        return cycle_dirs["merge_dir"]
    
    def get_exceptions_dir(self) -> Path:
        """
        Возвращает директорию Exceptions для текущего цикла.
        
        Returns:
            Path к Exceptions_N директории
        """
        cycle_dirs = get_cycle_directories(self._current_cycle)
        return cycle_dirs["exceptions_dir"]
    
    def get_cycle_directories(self) -> Dict[str, Path]:
        """
        Возвращает все директории для текущего цикла.
        
        Returns:
            Словарь с ключами: pending_dir, merge_dir, exceptions_dir
        """
        return get_cycle_directories(self._current_cycle)
    
    def get_target_pending_dir(self, category: str, extension: Optional[str] = None) -> Path:
        """
        Возвращает целевую директорию в Pending для категории и расширения.
        
        Args:
            category: Категория (convert, direct, normalize, archives, special, mixed)
            extension: Расширение файла (опционально, для сортировки по расширениям)
        
        Returns:
            Path к целевой директории
        """
        pending_dir = self.get_pending_dir()
        target_dir = pending_dir / category
        
        # Если указано расширение, добавляем поддиректорию по расширению
        if extension:
            # Убираем точку из расширения, если есть
            ext_clean = extension.lstrip(".")
            target_dir = target_dir / ext_clean
        
        return target_dir
    
    def get_target_merge_dir(self, subcategory: str, extension: Optional[str] = None) -> Path:
        """
        Возвращает целевую директорию в Merge для подкатегории и расширения.
        
        Args:
            subcategory: Подкатегория Merge (direct, extracted, converted, normalized)
            extension: Расширение файла (опционально, для сортировки по расширениям)
        
        Returns:
            Path к целевой директории
        
        Raises:
            ValueError: Если cycle=1 и subcategory != "direct"
        """
        if self._current_cycle == 1 and subcategory != "direct":
            raise ValueError(f"Merge_1 can only contain 'direct' subcategory, got {subcategory}")
        
        if self._current_cycle > 1 and subcategory == "direct":
            raise ValueError(f"Merge_{self._current_cycle} cannot contain 'direct' subcategory")
        
        merge_dir = self.get_merge_dir()
        target_dir = merge_dir / subcategory
        
        # Если указано расширение, добавляем поддиректорию по расширению
        if extension:
            ext_clean = extension.lstrip(".")
            target_dir = target_dir / ext_clean
        
        return target_dir
    
    def get_target_exceptions_dir(self, subcategory: str) -> Path:
        """
        Возвращает целевую директорию в Exceptions для подкатегории.
        
        Args:
            subcategory: Подкатегория Exceptions (special, mixed, unknown)
        
        Returns:
            Path к целевой директории
        """
        exceptions_dir = self.get_exceptions_dir()
        return exceptions_dir / subcategory
    
    def __repr__(self) -> str:
        """Строковое представление CycleManager."""
        return f"CycleManager(cycle={self._current_cycle}, max={MAX_CYCLES})"


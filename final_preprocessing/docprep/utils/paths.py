"""
Утилиты для работы с путями и директориями UNIT.
"""
from pathlib import Path
from typing import List, Optional


def find_units(directory: Path, pattern: str = "UNIT_*") -> List[Path]:
    """
    Находит все директории UNIT в указанной директории.

    Args:
        directory: Директория для поиска
        pattern: Шаблон поиска (по умолчанию "UNIT_*")

    Returns:
        Список путей к директориям UNIT
    """
    if not directory.exists():
        return []

    units = [d for d in directory.iterdir() if d.is_dir() and d.name.startswith("UNIT_")]
    return sorted(units)


def get_unit_path(base_dir: Path, unit_id: str) -> Path:
    """
    Получает путь к директории UNIT.

    Args:
        base_dir: Базовая директория
        unit_id: Идентификатор UNIT

    Returns:
        Путь к директории UNIT
    """
    return base_dir / unit_id


def ensure_directory(path: Path) -> Path:
    """
    Создает директорию если она не существует.

    Args:
        path: Путь к директории

    Returns:
        Путь к директории
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


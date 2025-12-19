"""
Classifier - классификация файлов и определение категорий обработки.
"""
from pathlib import Path
from typing import Dict, Any, List, Optional
from collections import Counter

from ..core.manifest import load_manifest, save_manifest, update_manifest_state
from ..core.state_machine import UnitState, UnitStateMachine
from ..core.audit import get_audit_logger
from ..utils.file_ops import detect_file_type
from ..core.config import get_pending_paths


class Classifier:
    """
    Классификатор для определения категории обработки UNIT.

    Классифицирует файлы и определяет, куда должен быть направлен UNIT
    для дальнейшей обработки.
    """

    # Расширения для подписей
    SIGNATURE_EXTENSIONS = {".sig", ".p7s", ".pem", ".cer", ".crt"}

    # Неподдерживаемые расширения
    UNSUPPORTED_EXTENSIONS = {".exe", ".dll", ".db", ".tmp", ".log", ".ini", ".sys", ".bat", ".sh"}

    # Типы, требующие конвертации
    CONVERTIBLE_TYPES = {
        "doc": "docx",
        "xls": "xlsx",
        "ppt": "pptx",
    }

    def __init__(self):
        """Инициализирует Classifier."""
        self.audit_logger = get_audit_logger()

    def classify_unit(self, unit_path: Path, cycle: int) -> Dict[str, Any]:
        """
        Классифицирует UNIT и определяет категорию обработки.

        Args:
            unit_path: Путь к директории UNIT
            cycle: Номер цикла (1, 2, 3)

        Returns:
            Словарь с результатами классификации:
            - category: категория (direct, convert, extract, normalize, special)
            - unit_category: категория UNIT (может быть mixed)
            - is_mixed: является ли UNIT mixed
            - file_classifications: классификация каждого файла
            - target_directory: целевая директория для UNIT
        """
        unit_id = unit_path.name
        correlation_id = self.audit_logger.get_correlation_id()

        # Загружаем manifest если существует
        manifest_path = unit_path / "manifest.json"
        manifest = None
        if manifest_path.exists():
            try:
                from ..core.manifest import load_manifest

                manifest = load_manifest(unit_path)
            except Exception:
                pass

        # Находим все файлы в UNIT (исключаем служебные)
        files = [
            f
            for f in unit_path.rglob("*")
            if f.is_file()
            and f.name not in ["manifest.json", "audit.log.jsonl"]
            and not f.name.startswith(".")
        ]

        if not files:
            return {
                "category": "unknown",
                "unit_category": "unknown",
                "is_mixed": False,
                "file_classifications": [],
                "target_directory": None,
                "error": "No files found in UNIT",
            }

        # Классифицируем каждый файл
        file_classifications = []
        categories = []

        for file_path in files:
            classification = self._classify_file(file_path)
            file_classifications.append(
                {
                    "file_path": str(file_path),
                    "classification": classification,
                }
            )
            categories.append(classification["category"])

        # Определяем категорию UNIT
        category_counts = Counter(categories)
        unique_categories = set(categories)
        is_mixed = len(unique_categories) > 1

        # Определяем доминирующую категорию
        if is_mixed:
            unit_category = "mixed"
        elif categories:
            unit_category = categories[0]
        else:
            unit_category = "unknown"

        # Определяем целевую директорию на основе категории
        target_directory = self._get_target_directory(unit_category, cycle, unit_path)

        # Логируем классификацию
        self.audit_logger.log_event(
            unit_id=unit_id,
            event_type="operation",
            operation="classify",
            details={
                "cycle": cycle,
                "category": unit_category,
                "is_mixed": is_mixed,
                "file_count": len(files),
                "category_distribution": dict(category_counts),
            },
            state_before=manifest.get("state_machine", {}).get("current_state") if manifest else None,
            state_after="CLASSIFIED",
            unit_path=unit_path,
        )

        return {
            "category": unit_category,
            "unit_category": unit_category,
            "is_mixed": is_mixed,
            "file_classifications": file_classifications,
            "target_directory": target_directory,
            "category_distribution": dict(category_counts),
        }

    def _classify_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Классифицирует отдельный файл.

        Args:
            file_path: Путь к файлу

        Returns:
            Словарь с классификацией:
            - category: категория (direct, convert, extract, normalize, special)
            - detected_type: определенный тип файла
            - needs_conversion: требуется ли конвертация
            - needs_extraction: требуется ли разархивация
            - needs_normalization: требуется ли нормализация
        """
        extension = file_path.suffix.lower()
        detection = detect_file_type(file_path)

        classification = {
            "category": "unknown",
            "detected_type": detection.get("detected_type", "unknown"),
            "needs_conversion": False,
            "needs_extraction": False,
            "needs_normalization": False,
            "extension_matches_content": detection.get("extension_matches_content", True),
        }

        # Проверка на подписи
        if extension in self.SIGNATURE_EXTENSIONS:
            classification["category"] = "special"
            return classification

        # Проверка на неподдерживаемые форматы
        if extension in self.UNSUPPORTED_EXTENSIONS:
            classification["category"] = "special"
            return classification

        # Проверка на архивы
        if detection.get("is_archive") or detection.get("detected_type") in [
            "zip_archive",
            "rar_archive",
            "7z_archive",
        ]:
            classification["category"] = "extract"
            classification["needs_extraction"] = True
            return classification

        # Проверка на необходимость конвертации
        detected_type = detection.get("detected_type")
        if detected_type in self.CONVERTIBLE_TYPES:
            classification["category"] = "convert"
            classification["needs_conversion"] = True
            return classification

        # Проверка на необходимость нормализации
        if not detection.get("extension_matches_content", True):
            classification["category"] = "normalize"
            classification["needs_normalization"] = True
            return classification

        # Прямая обработка (ready)
        classification["category"] = "direct"
        return classification

    def _get_target_directory(
        self, category: str, cycle: int, unit_path: Path
    ) -> Optional[Path]:
        """
        Определяет целевую директорию для UNIT на основе категории.

        Args:
            category: Категория UNIT
            cycle: Номер цикла
            unit_path: Путь к UNIT (для определения базовой директории)

        Returns:
            Путь к целевой директории или None
        """
        try:
            pending_paths = get_pending_paths(cycle, unit_path.parent.parent)
        except Exception:
            # Fallback на базовую структуру
            from ..core.config import PROCESSING_DIR, get_pending_paths

            pending_paths = get_pending_paths(cycle, PROCESSING_DIR)

        category_mapping = {
            "direct": pending_paths["direct"],
            "convert": pending_paths["convert"],
            "extract": pending_paths["extract"],
            "normalize": pending_paths["normalize"],
            "special": unit_path.parent.parent / "Exceptions" / f"Exceptions_{cycle}",
            "mixed": pending_paths["normalize"],  # Mixed идет в normalize для обработки
        }

        return category_mapping.get(category)


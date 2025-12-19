"""
Validator - проверка целостности UNIT.

Валидация manifest, state machine переходов, соответствия файлов.
"""
from pathlib import Path
from typing import Dict, Any

from ..core.manifest import load_manifest
from ..core.state_machine import UnitStateMachine, validate_state_transition
from ..core.exceptions import ManifestError


class Validator:
    """Валидатор целостности UNIT."""

    def validate_unit(self, unit_path: Path) -> Dict[str, Any]:
        """
        Валидирует целостность UNIT.

        Args:
            unit_path: Путь к директории UNIT

        Returns:
            Словарь с результатами валидации
        """
        unit_id = unit_path.name
        validation_results = {
            "unit_id": unit_id,
            "valid": True,
            "errors": [],
            "warnings": [],
        }

        # Проверка наличия manifest.json
        manifest_path = unit_path / "manifest.json"
        if not manifest_path.exists():
            validation_results["valid"] = False
            validation_results["errors"].append("manifest.json not found")
            return validation_results

        try:
            manifest = load_manifest(unit_path)
        except Exception as e:
            validation_results["valid"] = False
            validation_results["errors"].append(f"Failed to load manifest: {str(e)}")
            return validation_results

        # Валидация структуры manifest
        required_fields = ["schema_version", "unit_id", "state_machine", "processing"]
        for field in required_fields:
            if field not in manifest:
                validation_results["valid"] = False
                validation_results["errors"].append(f"Manifest missing required field: {field}")

        # Валидация state machine переходов
        if "state_machine" in manifest:
            state_trace = manifest["state_machine"].get("state_trace", [])
            if len(state_trace) > 1:
                for i in range(len(state_trace) - 1):
                    try:
                        current_state = _state_from_string(state_trace[i])
                        next_state = _state_from_string(state_trace[i + 1])
                        if current_state and next_state:
                            if not validate_state_transition(current_state, next_state):
                                validation_results["warnings"].append(
                                    f"Invalid transition: {state_trace[i]} -> {state_trace[i + 1]}"
                                )
                    except Exception:
                        pass

        # Проверка соответствия файлов manifest
        if "files" in manifest:
            manifest_files = {f.get("current_name") for f in manifest["files"]}
            actual_files = {
                f.name
                for f in unit_path.rglob("*")
                if f.is_file() and f.name not in ["manifest.json", "audit.log.jsonl"]
            }

            # Проверяем, что файлы из manifest существуют
            for file_info in manifest["files"]:
                file_name = file_info.get("current_name")
                if file_name and file_name not in actual_files:
                    validation_results["warnings"].append(
                        f"File from manifest not found: {file_name}"
                    )

        # Проверка checksums (если указаны)
        if "integrity" in manifest:
            checksum = manifest["integrity"].get("checksum")
            if checksum and checksum != "":
                # TODO: Реализовать проверку checksum
                pass

        return validation_results


# Вспомогательная функция для парсинга состояния из строки
def _state_from_string(state_str: str):
    """Вспомогательная функция для парсинга состояния из строки."""
    from ..core.state_machine import UnitState

    try:
        return UnitState(state_str)
    except ValueError:
        return None


"""
DoclingAdapter - адаптер для построения AST узлов для Docling.

Читает manifest.json и нормализованные файлы из Ready2Docling/UNIT_xxx,
строит структуру для передачи в Docling pipeline.
"""
from pathlib import Path
from typing import Dict, Any, List, Optional

from ..core.manifest import load_manifest
from ..core.exceptions import ManifestError


class DoclingAdapter:
    """
    Адаптер для преобразования UNIT в Docling-ready структуру.

    Preprocessing НЕ знает про Docling, Docling НЕ знает про Pending/Merge.
    Связь только через этот adapter.
    """

    def __init__(self):
        """Инициализирует DoclingAdapter."""
        pass

    def build_ast_nodes(self, unit_path: Path) -> Dict[str, Any]:
        """
        Строит AST узлы для Docling из UNIT в Ready2Docling.

        Args:
            unit_path: Путь к UNIT в Ready2Docling

        Returns:
            Словарь с AST структурой:
            - DocNode: корневой узел документа
            - PageNode: страницы (для PDF/image)
            - FileNode: файлы (document/attachment роли)
            - MetadataNode: метаданные из manifest
        """
        # Загружаем manifest
        try:
            manifest = load_manifest(unit_path)
        except FileNotFoundError:
            raise ManifestError(f"Manifest not found in {unit_path}")

        unit_id = manifest.get("unit_id", unit_path.name)
        protocol_id = manifest.get("protocol_id", "")

        # Находим файлы
        files_dir = unit_path / "files"
        if not files_dir.exists():
            files_dir = unit_path

        files = [
            f
            for f in files_dir.rglob("*")
            if f.is_file() and f.name not in ["manifest.json", "audit.log.jsonl"]
        ]

        # Строим структуру AST
        doc_node = {
            "type": "DocNode",
            "unit_id": unit_id,
            "protocol_id": protocol_id,
            "metadata": self._build_metadata_node(manifest),
            "files": self._build_file_nodes(files, manifest),
            "pages": self._build_page_nodes(files, manifest),
        }

        return doc_node

    def _build_metadata_node(self, manifest: Dict[str, Any]) -> Dict[str, Any]:
        """
        Строит узел метаданных из manifest.

        Args:
            manifest: Manifest данные

        Returns:
            MetadataNode словарь
        """
        return {
            "type": "MetadataNode",
            "unit_id": manifest.get("unit_id"),
            "protocol_id": manifest.get("protocol_id"),
            "protocol_date": manifest.get("protocol_date"),
            "unit_semantics": manifest.get("unit_semantics", {}),
            "processing": manifest.get("processing", {}),
            "state_machine": manifest.get("state_machine", {}),
            "created_at": manifest.get("created_at"),
            "updated_at": manifest.get("updated_at"),
        }

    def _build_file_nodes(
        self, files: List[Path], manifest: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Строит узлы файлов.

        Args:
            files: Список путей к файлам
            manifest: Manifest данные

        Returns:
            Список FileNode словарей
        """
        file_nodes = []
        manifest_files = manifest.get("files", [])

        for file_path in files:
            # Ищем информацию о файле в manifest
            file_info = None
            for mf in manifest_files:
                if mf.get("current_name") == file_path.name:
                    file_info = mf
                    break

            # Определяем роль файла
            role = "document"  # По умолчанию документ
            if file_info:
                # Можно определить роль на основе содержимого или метаданных
                transformations = file_info.get("transformations", [])
                if any(t.get("type") == "convert" for t in transformations):
                    role = "document"
                else:
                    role = "attachment"

            file_node = {
                "type": "FileNode",
                "path": str(file_path),
                "name": file_path.name,
                "role": role,
                "mime_type": file_info.get("mime_detected") if file_info else None,
                "transformations": file_info.get("transformations", []) if file_info else [],
            }
            file_nodes.append(file_node)

        return file_nodes

    def _build_page_nodes(
        self, files: List[Path], manifest: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Строит узлы страниц для PDF/image файлов.

        Args:
            files: Список путей к файлам
            manifest: Manifest данные

        Returns:
            Список PageNode словарей
        """
        page_nodes = []

        for file_path in files:
            # Только для PDF и изображений
            if file_path.suffix.lower() in [".pdf", ".jpg", ".jpeg", ".png", ".tiff"]:
                page_node = {
                    "type": "PageNode",
                    "file_path": str(file_path),
                    "page_number": 1,  # TODO: Определить номер страницы для PDF
                }
                page_nodes.append(page_node)

        return page_nodes

    def validate_readiness(self, unit_path: Path) -> Dict[str, Any]:
        """
        Валидирует готовность UNIT к обработке Docling.

        Args:
            unit_path: Путь к UNIT

        Returns:
            Словарь с результатами валидации
        """
        validation = {"ready": True, "errors": [], "warnings": []}

        # Проверка наличия manifest
        manifest_path = unit_path / "manifest.json"
        if not manifest_path.exists():
            validation["ready"] = False
            validation["errors"].append("manifest.json not found")
            return validation

        try:
            manifest = load_manifest(unit_path)
        except Exception as e:
            validation["ready"] = False
            validation["errors"].append(f"Failed to load manifest: {str(e)}")
            return validation

        # Проверка состояния
        state_machine = manifest.get("state_machine", {})
        current_state = state_machine.get("current_state")
        if current_state != "READY_FOR_DOCLING":
            validation["ready"] = False
            validation["errors"].append(f"Unit not ready: current state is {current_state}")

        # Проверка наличия файлов
        files_dir = unit_path / "files"
        if not files_dir.exists():
            files_dir = unit_path

        files = [
            f
            for f in files_dir.rglob("*")
            if f.is_file() and f.name not in ["manifest.json", "audit.log.jsonl"]
        ]

        if not files:
            validation["ready"] = False
            validation["errors"].append("No files found in UNIT")

        return validation


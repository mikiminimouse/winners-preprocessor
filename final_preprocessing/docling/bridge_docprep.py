"""
Интеграция с docprep через существующий DoclingAdapter.

Использует готовый адаптер из docprep, не дублирует логику.
"""
import sys
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

# Добавляем путь к docprep для импорта
# Теперь docling и docprep находятся в одной директории final_preprocessing
_project_root = Path(__file__).parent.parent  # final_preprocessing
if _project_root.exists():
    sys.path.insert(0, str(_project_root))

try:
    from docprep.adapters.docling import DoclingAdapter
    from docprep.core.manifest import load_manifest
    DOCPREP_AVAILABLE = True
except ImportError as e:
    DOCPREP_AVAILABLE = False
    logging.warning(f"docprep not available: {e}")

logger = logging.getLogger(__name__)


def load_unit_from_ready2docling(unit_path: Path) -> Dict[str, Any]:
    """
    Загружает UNIT из Ready2Docling используя DoclingAdapter из docprep.

    Args:
        unit_path: Путь к UNIT директории в Ready2Docling

    Returns:
        Словарь с данными UNIT:
        - manifest: полный manifest
        - validation: результаты валидации
        - ast_nodes: AST узлы из адаптера
        - files: список путей к файлам
        - unit_id: идентификатор UNIT
        - route: route из manifest

    Raises:
        FileNotFoundError: Если UNIT не найден
        ValueError: Если UNIT не готов к обработке
    """
    if not DOCPREP_AVAILABLE:
        raise ImportError("docprep not available - cannot load unit")

    if not unit_path.exists():
        raise FileNotFoundError(f"Unit path not found: {unit_path}")

    # Используем существующий адаптер
    adapter = DoclingAdapter()

    # Валидация готовности UNIT
    validation = adapter.validate_readiness(unit_path)
    if not validation["ready"]:
        errors = "; ".join(validation["errors"])
        raise ValueError(f"Unit not ready for Docling processing: {errors}")

    # Загружаем manifest
    try:
        manifest = load_manifest(unit_path)
    except Exception as e:
        raise ValueError(f"Failed to load manifest: {e}")

    # Строим AST узлы через адаптер
    try:
        ast_nodes = adapter.build_ast_nodes(unit_path)
    except Exception as e:
        logger.warning(f"Failed to build AST nodes: {e}")
        ast_nodes = {}

    # Находим файлы в UNIT
    files_dir = unit_path / "files"
    if not files_dir.exists():
        files_dir = unit_path

    files = [
        f
        for f in files_dir.rglob("*")
        if f.is_file() and f.name not in ["manifest.json", "audit.log.jsonl"]
    ]

    if not files:
        raise ValueError(f"No files found in unit: {unit_path}")

    # Извлекаем route из manifest с fallback на структуру директорий
    route = manifest.get("processing", {}).get("route")
    unit_id = manifest.get("unit_id", unit_path.name)
    
    # Если route не найден в manifest, определяем из структуры директорий
    if not route or route == "unknown":
        route = _determine_route_from_path(unit_path, files, manifest)
        logger.info(f"Route determined from path structure: {route} for {unit_id}")
    
    # Валидация route
    if not route or route == "unknown":
        logger.warning(f"Could not determine route for {unit_id}, using default")
        route = "pdf_text"  # Default fallback

    return {
        "manifest": manifest,
        "validation": validation,
        "ast_nodes": ast_nodes,
        "files": files,
        "unit_id": unit_id,
        "route": route,
        "unit_path": unit_path,
    }


def get_main_file(unit_data: Dict[str, Any]) -> Optional[Path]:
    """
    Получает главный файл из UNIT для обработки.

    Использует AST nodes для определения главного документа, если доступно.

    Args:
        unit_data: Данные UNIT из load_unit_from_ready2docling

    Returns:
        Путь к главному файлу или None
    """
    files = unit_data.get("files", [])
    if not files:
        return None

    # Пытаемся использовать AST nodes для определения главного файла
    ast_nodes = unit_data.get("ast_nodes", {})
    file_nodes = ast_nodes.get("files", [])
    
    # Ищем файл с ролью "document" в AST nodes
    for file_node in file_nodes:
        if file_node.get("role") == "document":
            file_path = Path(file_node.get("path", ""))
            if file_path.exists():
                return file_path
    
    # Если не нашли через AST, используем первый файл
    # Приоритет файлам с расширениями документов
    document_extensions = [".pdf", ".docx", ".xlsx", ".pptx", ".html", ".xml"]
    for ext in document_extensions:
        for file_path in files:
            if file_path.suffix.lower() == ext:
                return file_path
    
    # Fallback: первый файл
    return files[0]


def _determine_route_from_path(
    unit_path: Path, files: List[Path], manifest: Dict[str, Any]
) -> str:
    """
    Определяет route из структуры директорий Ready2Docling.

    Args:
        unit_path: Путь к UNIT
        files: Список файлов в UNIT
        manifest: Manifest данные

    Returns:
        Route строка (pdf_text, pdf_scan, docx, etc.)
    """
    # Проверяем путь к UNIT для определения route
    path_str = str(unit_path)
    
    # Проверяем структуру директорий Ready2Docling
    if "/pdf/text/" in path_str:
        return "pdf_text"
    elif "/pdf/scan/" in path_str:
        return "pdf_scan"
    elif "/pdf/mixed/" in path_str:
        return "pdf_mixed"
    elif "/docx/" in path_str:
        return "docx"
    elif "/xlsx/" in path_str:
        return "xlsx"
    elif "/pptx/" in path_str:
        return "pptx"
    elif "/html/" in path_str:
        return "html"
    elif "/xml/" in path_str:
        return "xml"
    elif any("/" + ext + "/" in path_str for ext in ["jpg", "jpeg", "png", "tiff"]):
        return "image_ocr"
    
    # Если не определили по пути, проверяем файлы
    if files:
        first_file = files[0]
        ext = first_file.suffix.lower()
        
        if ext == ".pdf":
            # Для PDF проверяем needs_ocr из manifest
            manifest_files = manifest.get("files", [])
            for file_info in manifest_files:
                if file_info.get("current_name") == first_file.name:
                    needs_ocr = file_info.get("needs_ocr", False)
                    return "pdf_scan" if needs_ocr else "pdf_text"
            # Fallback для PDF
            return "pdf_text"
        elif ext == ".docx":
            return "docx"
        elif ext == ".xlsx":
            return "xlsx"
        elif ext == ".pptx":
            return "pptx"
        elif ext in [".html", ".htm"]:
            return "html"
        elif ext == ".xml":
            return "xml"
        elif ext in [".jpg", ".jpeg", ".png", ".tiff"]:
            return "image_ocr"
    
    return "unknown"


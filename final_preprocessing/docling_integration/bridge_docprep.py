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
    from docprep.core.contract import load_contract
    DOCPREP_AVAILABLE = True
except ImportError as e:
    DOCPREP_AVAILABLE = False
    logging.warning(f"docprep not available: {e}")

logger = logging.getLogger(__name__)


def load_unit_from_ready2docling(unit_path: Path) -> Dict[str, Any]:
    """
    Загружает UNIT из Ready2Docling используя ТОЛЬКО docprep.contract.json.

    КРИТИЧЕСКИ ВАЖНО: Docling использует ТОЛЬКО contract.json как вход.
    manifest.json НЕ используется - он нужен только для внутренней логики DocPrep.

    Контракт является формализованным входом для Docling и обеспечивает
    контрактную строгость между DocPrep и Docling.

    Args:
        unit_path: Путь к UNIT директории в Ready2Docling

    Returns:
        Словарь с данными UNIT:
        - contract: docprep.contract.json (ОБЯЗАТЕЛЕН)
        - validation: результаты валидации
        - ast_nodes: AST узлы из адаптера
        - files: список путей к файлам
        - unit_id: идентификатор UNIT
        - route: route из contract

    Raises:
        FileNotFoundError: Если UNIT или contract не найден
        ValueError: Если UNIT не готов к обработке или contract некорректен
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

    # Загружаем ТОЛЬКО контракт - manifest.json НЕ используется как вход для Docling
    contract_path = unit_path / "docprep.contract.json"
    
    if not contract_path.exists():
        raise FileNotFoundError(
            f"Contract not found: {contract_path}. "
            f"Unit must have docprep.contract.json to be processed by Docling. "
            f"This indicates a bug in DocPrep merger - contract should be generated automatically."
        )
    
    try:
        contract = load_contract(unit_path)
        logger.debug(f"Loaded contract from {contract_path}")
    except Exception as e:
        raise ValueError(
            f"Failed to load contract for unit {unit_path}: {e}. "
            f"Contract is REQUIRED for Docling processing."
        )

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
        if f.is_file() and f.name not in [
            "manifest.json", "docprep.contract.json", "audit.log.jsonl",
            "raw_url_map.json", "unit.meta.json"
        ]
    ]

    if not files:
        raise ValueError(f"No files found in unit: {unit_path}")

    # Извлекаем route из contract (единственный источник истины)
    routing = contract.get("routing", {})
    route = routing.get("docling_route")
    unit_info = contract.get("unit", {})
    unit_id = unit_info.get("unit_id", unit_path.name)
    
    # КРИТИЧЕСКАЯ ВАЛИДАЦИЯ: route не должен быть "mixed"
    if route == "mixed":
        raise ValueError(
            f"Contract contains route='mixed' for unit {unit_id}. "
            f"This violates contract boundary - mixed units must be filtered before Ready2Docling."
        )
    
    if not route or route == "unknown":
        raise ValueError(
            f"Contract does not contain valid route for unit {unit_id}. "
            f"Route must be explicitly defined in contract.routing.docling_route."
        )

    return {
        "contract": contract,
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

    # Исключаем служебные файлы
    excluded_names = [
        "manifest.json", "docprep.contract.json", "audit.log.jsonl",
        "raw_url_map.json", "unit.meta.json"
    ]
    document_files = [
        f for f in files
        if f.name not in excluded_names
    ]
    
    if not document_files:
        return None

    # Пытаемся использовать AST nodes для определения главного файла
    ast_nodes = unit_data.get("ast_nodes", {})
    file_nodes = ast_nodes.get("files", [])
    
    # Ищем файл с ролью "document" в AST nodes
    for file_node in file_nodes:
        if file_node.get("role") == "document":
            file_path = Path(file_node.get("path", ""))
            if file_path.exists() and file_path.name not in excluded_names:
                return file_path
    
    # Если не нашли через AST, используем первый файл документа
    # Приоритет файлам с расширениями документов, поддерживаемыми Docling
    # Docling поддерживает: PDF, DOCX, XLSX, PPTX, HTML, XML, RTF, изображения (через OCR)
    # НЕ поддерживает: ZIP, RAR, 7Z, EXE и другие архивы/бинарники
    docling_supported_extensions = [
        ".pdf", ".docx", ".xlsx", ".pptx", ".html", ".htm", ".xml", 
        ".rtf", ".jpg", ".jpeg", ".png", ".tiff", ".tif", ".gif", ".bmp"
    ]
    unsupported_extensions = {".zip", ".rar", ".7z", ".exe", ".dll", ".bin"}
    
    # Фильтруем неподдерживаемые форматы
    supported_files = [
        f for f in document_files 
        if f.suffix.lower() not in unsupported_extensions
    ]
    
    if not supported_files:
        raise ValueError(
            f"No Docling-supported files found in unit. "
            f"Found files: {[f.name for f in document_files]}. "
            f"Unsupported formats detected - these should be filtered in merger."
        )
    
    # Приоритет файлам с поддерживаемыми расширениями
    for ext in docling_supported_extensions:
        for file_path in supported_files:
            if file_path.suffix.lower() == ext:
                return file_path
    
    # Fallback: первый поддерживаемый файл
    return supported_files[0]


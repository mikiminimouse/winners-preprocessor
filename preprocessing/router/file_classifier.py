"""
Классификация файлов по категориям обработки:
- direct: файлы с корректным именем и расширением
- normalize: файлы с неправильным расположением точки или ложными расширениями
- convert: файлы, требующие конвертации (doc->docx, xls->xlsx и т.д.)
- extract: архивы (zip, rar, 7z)
- special: подписи, неподдерживаемые форматы, сложные расширения
- mixed: юниты с файлами разных типов
"""
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from .config import (
    SIGNATURE_EXTENSIONS, UNSUPPORTED_EXTENSIONS, COMPLEX_EXTENSIONS,
    CONVERTIBLE_TYPES, SUPPORTED_FILE_TYPES, ARCHIVE_TYPES
)
from .file_detection import detect_file_type


def classify_file(file_path: Path, detection_result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Классифицирует файл по категориям обработки.
    
    Args:
        file_path: Путь к файлу
        detection_result: Результат detect_file_type (если уже выполнено)
    
    Returns:
        Dict с категорией и метаданными:
        {
            "category": "direct|normalize|convert|extract|special",
            "subcategory": str,  # signature, unsupported, complex_extensions
            "detected_type": str,
            "requires_action": str,  # describe what needs to be done
            "has_false_extension": bool,
            "original_extension": str,
            "target_directory": Path
        }
    """
    if not file_path.exists():
        return {
            "category": "error",
            "error": "File does not exist"
        }
    
    # Определяем тип файла, если не передан
    if detection_result is None:
        detection_result = detect_file_type(file_path)
    
    detected_type = detection_result.get("detected_type", "unknown")
    extension = file_path.suffix.lower()
    is_archive = detection_result.get("is_archive", False)
    is_fake_doc = detection_result.get("is_fake_doc", False)
    extension_matches = detection_result.get("extension_matches_content", True)
    
    classification = {
        "category": "unknown",
        "subcategory": None,
        "detected_type": detected_type,
        "requires_action": "unknown",
        "has_false_extension": not extension_matches,
        "original_extension": extension,
        "target_directory": None,
        "needs_normalization": False,
        "needs_conversion": False,
        "needs_extraction": False,
        "is_special": False
    }
    
    # 1. Проверяем SPECIAL категории
    
    # Подписи
    if extension in SIGNATURE_EXTENSIONS:
        classification["category"] = "special"
        classification["subcategory"] = "signature"
        classification["requires_action"] = "Move to special/signature/"
        classification["is_special"] = True
        return classification
    
    # Неподдерживаемые форматы
    if extension in UNSUPPORTED_EXTENSIONS:
        classification["category"] = "special"
        classification["subcategory"] = "unsupported"
        classification["requires_action"] = "Move to special/unsupported/"
        classification["is_special"] = True
        return classification
    
    # Сложные расширения
    full_name = file_path.name.lower()
    for complex_ext in COMPLEX_EXTENSIONS:
        if full_name.endswith(complex_ext):
            classification["category"] = "special"
            classification["subcategory"] = "complex_extensions"
            classification["requires_action"] = f"Move to special/complex_extensions/"
            classification["is_special"] = True
            return classification
    
    # 2. Проверяем АРХИВЫ
    if is_archive or detected_type in ["zip_archive", "rar_archive", "7z_archive"]:
        classification["category"] = "extract"
        classification["subcategory"] = detected_type
        classification["requires_action"] = "Extract archive and process contents"
        classification["needs_extraction"] = True
        
        # Проверяем ложное расширение архива
        if is_fake_doc or not extension_matches:
            classification["has_false_extension"] = True
            classification["requires_action"] += " (has false extension)"
        
        return classification
    
    # 3. Проверяем необходимость КОНВЕРТАЦИИ
    if detected_type in CONVERTIBLE_TYPES:
        classification["category"] = "convert"
        classification["subcategory"] = detected_type
        target_type = CONVERTIBLE_TYPES[detected_type]
        classification["requires_action"] = f"Convert {detected_type} to {target_type}"
        classification["needs_conversion"] = True
        classification["target_type"] = target_type
        return classification
    
    # 4. Проверяем необходимость НОРМАЛИЗАЦИИ
    # Файлы без расширения или с неправильной точкой
    if not extension or not extension_matches:
        classification["category"] = "normalize"
        classification["subcategory"] = detected_type
        classification["requires_action"] = "Normalize filename/extension"
        classification["needs_normalization"] = True
        
        # Проверяем ложное расширение
        if is_fake_doc or (extension and detected_type and extension.lstrip('.') != detected_type):
            classification["has_false_extension"] = True
        
        return classification
    
    # 5. DIRECT категория - файлы с корректным именем и расширением
    # RTF и другие сложные форматы не должны быть в direct
    direct_types = ["pdf", "docx", "xlsx", "pptx", "jpg", "jpeg", "png", "tiff", "xml", "txt", "csv"]
    
    if detected_type in direct_types:
        classification["category"] = "direct"
        classification["subcategory"] = detected_type
        classification["requires_action"] = "Ready for processing"
        
        # Даже если файл корректный, проверяем ложное расширение
        if is_fake_doc or not extension_matches:
            classification["has_false_extension"] = True
            classification["category"] = "normalize"
            classification["requires_action"] = "Normalize false extension"
            classification["needs_normalization"] = True
        
        return classification
    
    # RTF и другие сложные форматы идут в special
    if detected_type in ["rtf", "html", "htm", "eml", "msg"]:
        classification["category"] = "special"
        classification["subcategory"] = detected_type
        classification["requires_action"] = f"Process {detected_type} as special format"
        classification["is_special"] = True
        return classification
    
    # 6. Неизвестные типы
    classification["category"] = "special"
    classification["subcategory"] = "unknown"
    classification["requires_action"] = "Unknown file type"
    classification["is_special"] = True
    
    return classification


def classify_unit_files(file_paths: List[Path], unit_id: str) -> Dict[str, Any]:
    """
    Классифицирует все файлы unit'а и определяет, является ли он mixed.
    
    Args:
        file_paths: Список путей к файлам unit'а
        unit_id: ID unit'а
    
    Returns:
        {
            "is_mixed": bool,
            "file_classifications": List[Dict],
            "unit_category": str,  # "mixed" or dominant category
            "type_distribution": Dict[str, int]
        }
    """
    classifications = []
    categories = {}
    
    for file_path in file_paths:
        cls = classify_file(file_path)
        classifications.append({
            "file_path": file_path,
            "classification": cls
        })
        category = cls["category"]
        categories[category] = categories.get(category, 0) + 1
    
    # Определяем, является ли unit mixed
    unique_categories = set(categories.keys())
    is_mixed = len(unique_categories) > 1
    
    # Для mixed units категория - "mixed"
    if is_mixed:
        unit_category = "mixed"
    else:
        unit_category = list(unique_categories)[0] if unique_categories else "unknown"
    
    return {
        "is_mixed": is_mixed,
        "file_classifications": classifications,
        "unit_category": unit_category,
        "type_distribution": categories,
        "total_files": len(file_paths)
    }


def get_target_directory(
    classification: Dict[str, Any], 
    base_pending_dir: Path, 
    cycle: int = 1
) -> Path:
    """
    Определяет целевую директорию для файла на основе классификации.
    
    Согласно PRD раздел 2.1 и 17.2, все UNIT_XXX должны быть отсортированы
    по расширениям файлов в поддиректориях.
    
    Args:
        classification: Результат classify_file()
        base_pending_dir: Базовая pending директория (или Processing/Pending_N)
        cycle: Номер цикла обработки (1, 2, или 3)
    
    Returns:
        Path к целевой директории с поддиректорией по расширению
    """
    category = classification["category"]
    subcategory = classification["subcategory"]
    detected_type = classification["detected_type"]
    original_extension = classification.get("original_extension", "")
    has_false_extension = classification.get("has_false_extension", False)
    
    # Определяем расширение для сортировки
    def get_extension_for_sorting():
        """Определяет расширение для создания поддиректории."""
        if has_false_extension:
            # Для файлов с ложным расширением используем detected_type
            return detected_type
        elif original_extension:
            # Убираем точку из расширения
            return original_extension.lstrip(".")
        else:
            # Используем detected_type как fallback
            return detected_type
    
    if category == "direct":
        # PRD: pending/direct/docx/, pending/direct/pdf/ и т.д.
        base = base_pending_dir / "direct"
        extension = get_extension_for_sorting()
        return base / extension
    
    elif category == "normalize":
        # PRD: pending/normalize/docx/, pending/normalize/pdf/ и т.д.
        # Используем целевое расширение (detected_type после нормализации)
        base = base_pending_dir / "normalize"
        extension = detected_type  # Целевое расширение после нормализации
        return base / extension
    
    elif category == "convert":
        # PRD: pending/convert/doc/, pending/convert/xls/ и т.д.
        # Используем исходное расширение файла
        base = base_pending_dir / "convert"
        # Для convert используем исходный тип (doc, xls, ppt)
        source_type = subcategory if subcategory else detected_type
        # Если subcategory это полный тип (например "doc"), используем его
        # Иначе пытаемся извлечь из original_extension
        if original_extension:
            ext_clean = original_extension.lstrip(".")
            return base / ext_clean
        else:
            return base / source_type
    
    elif category == "extract":
        # PRD: pending/archives/zip/, pending/archives/rar/ и т.д.
        base = base_pending_dir / "archives"
        # Определяем тип архива из detected_type
        archive_type_map = {
            "zip_archive": "zip",
            "rar_archive": "rar",
            "7z_archive": "7z"
        }
        archive_type = archive_type_map.get(detected_type, "zip")
        return base / archive_type
    
    elif category == "special":
        # Special файлы идут в pending/special/ без поддиректорий по расширениям
        # но с поддиректориями по типу special
        base = base_pending_dir / "special"
        if subcategory == "signature":
            return base / "signature"
        elif subcategory == "unsupported":
            return base / "unsupported"
        elif subcategory == "complex_extensions":
            return base / "complex_extensions"
        else:
            return base / "unsupported"
    
    # По умолчанию
    return base_pending_dir / "direct" / "unknown"


def classify_batch(file_paths: list[Path]) -> Dict[str, list]:
    """
    Классифицирует пакет файлов.
    
    Args:
        file_paths: Список путей к файлам
    
    Returns:
        Dict с группировкой файлов по категориям
    """
    result = {
        "direct": [],
        "normalize": [],
        "convert": [],
        "extract": [],
        "special": [],
        "errors": []
    }
    
    for file_path in file_paths:
        try:
            classification = classify_file(file_path)
            category = classification["category"]
            
            if category in result:
                result[category].append({
                    "file_path": file_path,
                    "classification": classification
                })
            else:
                result["errors"].append({
                    "file_path": file_path,
                    "error": f"Unknown category: {category}"
                })
        except Exception as e:
            result["errors"].append({
                "file_path": file_path,
                "error": str(e)
            })
    
    return result


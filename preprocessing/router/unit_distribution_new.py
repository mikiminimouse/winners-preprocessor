"""
Распределение unit'ов по новой структуре директорий:
- pending/direct/ - файлы с корректным именем
- pending/normalize/ - файлы для нормализации
- pending/convert/ - файлы для конвертации
- pending/extract/ - архивы
- pending/special/ - подписи, неподдерживаемые, сложные расширения
"""
import shutil
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from .config import (
    PENDING_DIR, PENDING_DIRECT_DIR, PENDING_NORMALIZE_DIR, 
    PENDING_CONVERT_DIR, PENDING_EXTRACT_DIR, PENDING_SPECIAL_DIR,
    PENDING_MIXED_DIR,
    ensure_directories, create_false_ext_directory, get_cycle_directories
)
from .file_detection import detect_file_type
from .file_classifier import classify_file, get_target_directory
from .duplicate_detection import detect_duplicates_in_unit, mark_duplicates_in_metadata
from .utils import sanitize_filename
from .metrics import add_pending_file_metric, add_duplicate_metric
from .cycle_manager import CycleManager


def distribute_unit_by_new_structure(
    unit_id: str,
    files: List[Dict],
    unit_metadata: Optional[Dict] = None,
    cycle: int = 1
) -> Dict:
    """
    Распределяет unit по новой структуре директорий согласно PRD.
    
    Классификация файлов:
    1. direct - файлы с корректным именем и расширением
    2. normalize - файлы с неправильным расположением точки/ложными расширениями
    3. convert - файлы, требующие конвертации (doc->docx, xls->xlsx)
    4. extract - архивы (zip, rar, 7z)
    5. special - подписи, неподдерживаемые форматы, сложные расширения
    
    Согласно PRD раздел 2.1, все UNIT_XXX сортируются по расширениям файлов
    в поддиректориях (docx/, pdf/, jpeg/ и т.д.).
    
    Args:
        unit_id: Идентификатор unit'а
        files: Список файлов unit'а с путями
        unit_metadata: Опциональные метаданные
        cycle: Номер цикла обработки (1, 2, или 3)
    
    Returns:
        Словарь с результатами распределения
    """
    result = {
        "unit_id": unit_id,
        "files_processed": 0,
        "files_by_category": {
            "direct": 0,
            "normalize": 0,
            "convert": 0,
            "extract": 0,
            "special": 0,
            "mixed": 0
        },
        "duplicates_detected": False,
        "duplicate_count": 0,
        "errors": [],
        "distributed_files": []
    }
    
    # Создаем директории
    ensure_directories()
    
    # Инициализируем CycleManager для получения правильных директорий
    cycle_manager = CycleManager(initial_cycle=cycle)
    cycle_dirs = cycle_manager.get_cycle_directories()
    base_pending_dir = cycle_dirs["pending_dir"]
    
    # Обрабатываем каждый файл
    classified_files = []
    
    for file_info in files:
        file_path = Path(file_info.get("path", ""))
        
        if not file_path.exists():
            result["errors"].append({
                "file": str(file_path),
                "error": "File does not exist"
            })
            continue
        
        try:
            # Определяем тип файла (если еще не определен)
            if "detected_type" in file_info and "mime_type" in file_info:
                # Используем уже определенный тип из file_info
                detection_result = {
                    "detected_type": file_info.get("detected_type"),
                    "mime_type": file_info.get("mime_type"),
                    "needs_ocr": file_info.get("needs_ocr", False),
                    "requires_conversion": file_info.get("requires_conversion", False),
                    "is_archive": file_info.get("is_archive", False),
                    "extension_matches_content": file_info.get("extension_matches_content", True),
                    "sha256": file_info.get("sha256", ""),
                    **{k: v for k, v in file_info.items() if k.startswith("detection_") or k in ["is_fake_doc", "is_signature_file", "is_unsupported"]}
                }
            else:
                # Определяем тип файла заново
                detection_result = detect_file_type(file_path)
            
            # Классифицируем файл
            classification = classify_file(file_path, detection_result)
            
            # Объединяем информацию
            file_data = {
                **file_info,
                **detection_result,
                "classification": classification,
                "path": str(file_path),
                "original_name": file_path.name,
                "processed_at": datetime.utcnow().isoformat()
            }
            
            classified_files.append(file_data)
            
        except Exception as e:
            result["errors"].append({
                "file": str(file_path),
                "error": str(e)
            })
    
    # Определяем дубликаты
    duplicates_map = detect_duplicates_in_unit(classified_files)
    if duplicates_map:
        classified_files = mark_duplicates_in_metadata(classified_files, duplicates_map)
        result["duplicates_detected"] = True
        result["duplicate_count"] = len(duplicates_map)
        
        # Добавляем метрики по дубликатам
        for hash_value, file_list in duplicates_map.items():
            file_paths = [f.get("path") for f in file_list]
            add_duplicate_metric(unit_id, file_paths, hash_value)
    
    # Проверяем, является ли unit mixed (файлы разных категорий)
    from .file_classifier import classify_unit_files
    from .mixed_unit_handler import process_mixed_unit
    
    file_paths_for_classification = [Path(f["path"]) for f in classified_files if Path(f["path"]).exists()]
    
    if file_paths_for_classification:
        unit_classification = classify_unit_files(file_paths_for_classification, unit_id)
        
        # Если unit mixed - обрабатываем его отдельно
        if unit_classification["is_mixed"]:
            mixed_result = process_mixed_unit(
                unit_id,
                file_paths_for_classification,
                source_stage="detection"
            )
            
            result["is_mixed"] = True
            result["files_processed"] = mixed_result["files_moved"]
            result["files_by_category"]["mixed"] = mixed_result["files_moved"]
            result["mixed_details"] = {
                "type_distribution": unit_classification["type_distribution"],
                "target_directory": mixed_result["target_directory"]
            }
            
            # Сохраняем метаданные
            try:
                save_unit_metadata(unit_id, result, unit_metadata)
            except Exception as e:
                result["errors"].append({
                    "unit": unit_id,
                    "error": f"Failed to save metadata: {str(e)}"
                })
            
            return result
    
    # Распределяем файлы по категориям
    for file_data in classified_files:
        try:
            file_path = Path(file_data["path"])
            classification = file_data["classification"]
            category = classification["category"]
            
            # Определяем целевую директорию с учетом цикла и сортировки по расширениям
            target_base_dir = get_target_directory(classification, base_pending_dir, cycle=cycle)
            
            # Создаем поддиректорию для unit'а
            # Структура: Processing/Pending_N/category/extension/UNIT_XXX/files/
            unit_target_dir = target_base_dir / unit_id / "files"
            unit_target_dir.mkdir(parents=True, exist_ok=True)
            
            # Перемещаем файл
            dest_file = unit_target_dir / sanitize_filename(file_path.name)
            
            # Избегаем перезаписи при дубликатах
            if dest_file.exists():
                name_parts = dest_file.stem, dest_file.suffix
                counter = 1
                while dest_file.exists():
                    dest_file = unit_target_dir / f"{name_parts[0]}_{counter}{name_parts[1]}"
                    counter += 1
            
            shutil.move(str(file_path), str(dest_file))
            
            # Обновляем путь в метаданных
            file_data["path"] = str(dest_file)
            file_data["target_directory"] = str(target_base_dir)
            file_data["category"] = category
            
            # Учитываем в статистике
            result["files_by_category"][category] += 1
            result["files_processed"] += 1
            result["distributed_files"].append(file_data)
            
            # Добавляем метрики
            add_pending_file_metric(
                category,
                str(dest_file),
                unit_id,
                classification["detected_type"]
            )
            
        except Exception as e:
            result["errors"].append({
                "file": file_data.get("path"),
                "error": f"Failed to distribute: {str(e)}"
            })
    
    # Сохраняем метаданные unit'а
    try:
        save_unit_metadata(unit_id, result, unit_metadata)
    except Exception as e:
        result["errors"].append({
            "unit": unit_id,
            "error": f"Failed to save metadata: {str(e)}"
        })
    
    return result


def save_unit_metadata(unit_id: str, distribution_result: Dict, original_metadata: Optional[Dict] = None):
    """Сохраняет метаданные unit'а после распределения."""
    import json
    
    metadata = {
        "unit_id": unit_id,
        "distributed_at": datetime.utcnow().isoformat(),
        "distribution_result": distribution_result,
        "original_metadata": original_metadata or {}
    }
    
    # Определяем основную категорию для сохранения метаданных
    categories = distribution_result["files_by_category"]
    main_category = max(categories, key=categories.get) if categories else "special"
    
    # Сохраняем в соответствующей директории
    category_dirs = {
        "direct": PENDING_DIRECT_DIR,
        "normalize": PENDING_NORMALIZE_DIR,
        "convert": PENDING_CONVERT_DIR,
        "extract": PENDING_EXTRACT_DIR,
        "special": PENDING_SPECIAL_DIR
    }
    
    base_dir = category_dirs.get(main_category, PENDING_DIRECT_DIR)
    metadata_file = base_dir / unit_id / "metadata.json"
    metadata_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)


def get_unit_statistics(pending_dir: Path = PENDING_DIR) -> Dict:
    """
    Получает статистику по unit'ам в pending директориях.
    
    Returns:
        Словарь со статистикой по категориям
    """
    stats = {
        "direct": {"units": 0, "files": 0},
        "normalize": {"units": 0, "files": 0},
        "convert": {"units": 0, "files": 0},
        "extract": {"units": 0, "files": 0},
        "special": {"units": 0, "files": 0},
        "mixed": {"units": 0, "files": 0}
    }
    
    categories = {
        "direct": PENDING_DIRECT_DIR,
        "normalize": PENDING_NORMALIZE_DIR,
        "convert": PENDING_CONVERT_DIR,
        "extract": PENDING_EXTRACT_DIR,
        "special": PENDING_SPECIAL_DIR,
        "mixed": PENDING_MIXED_DIR
    }
    
    for category, category_dir in categories.items():
        if not category_dir.exists():
            continue
        
        # Подсчитываем unit'ы (директории, начинающиеся с UNIT_) - рекурсивно
        units = []
        for item in category_dir.rglob("UNIT_*"):
            if item.is_dir() and item.name.startswith("UNIT_"):
                # Проверяем, что это не вложенный unit (например, UNIT_xxx/files/UNIT_yyy)
                parent_has_unit = any(p.name.startswith("UNIT_") for p in item.parents if p != category_dir)
                if not parent_has_unit:
                    units.append(item)
        
        stats[category]["units"] = len(units)
        
        # Подсчитываем файлы в units (рекурсивно ищем директорию files)
        for unit_dir in units:
            # Ищем директорию files в unit'е или его поддиректориях
            files_dirs = list(unit_dir.rglob("files"))
            if files_dirs:
                # Используем первую найденную директорию files
                files_dir = files_dirs[0]
                files = [f for f in files_dir.iterdir() if f.is_file()]
                stats[category]["files"] += len(files)
            else:
                # Если нет директории files, ищем файлы напрямую в unit'е (кроме metadata.json)
                files = [f for f in unit_dir.iterdir() if f.is_file() and f.name != "metadata.json"]
                stats[category]["files"] += len(files)
    
    return stats


def print_distribution_summary(result: Dict):
    """Выводит краткую сводку по распределению unit'а."""
    print(f"\n=== Распределение unit'а {result['unit_id']} ===")
    print(f"Обработано файлов: {result['files_processed']}")
    print(f"\nПо категориям:")
    for category, count in result['files_by_category'].items():
        if count > 0:
            print(f"  {category}: {count} файл(ов)")
    
    if result['duplicates_detected']:
        print(f"\n⚠ Найдено дубликатов: {result['duplicate_count']} групп")
    
    if result['errors']:
        print(f"\n✗ Ошибок: {len(result['errors'])}")
        for error in result['errors'][:3]:
            print(f"  - {error['error']}")


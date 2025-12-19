"""
Модуль для объединения обработанных файлов в финальную директорию ready_docling.

Процесс:
1. Собирает все обработанные файлы из pending/direct, pending/normalize, pending/convert
2. Объединяет файлы из архивов (pending/extract/sorted)
3. Группирует по типам файлов
4. Перемещает в ready_docling/ с сохранением структуры по типам
5. НЕ создает директорию doc/ - все doc конвертированы в docx
"""
import shutil
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from .config import (
    PENDING_DIR, PENDING_DIRECT_DIR, PENDING_NORMALIZE_DIR,
    PENDING_CONVERT_DIR, PENDING_MIXED_DIR,
    EXTRACT_SORTED_DIR, EXTRACT_NORMALIZE_DIR, EXTRACT_CONVERT_DIR,
    EXTRACT_SORTED_MIXED_DIR,
    READY_DOCLING_DIR, SUPPORTED_FILE_TYPES,
    PROCESSING_BASE_DIR, MERGE_1_DIR, MERGE_2_DIR, MERGE_3_DIR
)
from .utils import sanitize_filename
from .file_detection import detect_file_type
from pypdf import PdfReader


def merge_to_ready_docling(
    dry_run: bool = False,
    limit: Optional[int] = None
) -> Dict:
    """
    Объединяет все обработанные файлы в ready_docling/.
    
    Args:
        dry_run: Если True, только показывает что будет сделано без реального перемещения
        limit: Ограничение на количество unit'ов для обработки
    
    Returns:
        Словарь со статистикой операции
    """
    result = {
        "started_at": datetime.utcnow().isoformat(),
        "dry_run": dry_run,
        "units_processed": 0,
        "files_moved": 0,
        "files_by_type": {},
        "errors": [],
        "skipped": []
    }
    
    # Источники файлов для объединения
    sources = {
        "direct": PENDING_DIRECT_DIR,
        "normalize": PENDING_NORMALIZE_DIR,
        "convert": PENDING_CONVERT_DIR,
        "extract_sorted": EXTRACT_SORTED_DIR / "direct",
        "extract_normalize": EXTRACT_NORMALIZE_DIR,
        "extract_convert": EXTRACT_CONVERT_DIR,
        "mixed": PENDING_MIXED_DIR,
        "extract_mixed": EXTRACT_SORTED_MIXED_DIR
    }
    
    # Собираем все unit'ы из источников
    all_units = {}
    
    for source_name, source_dir in sources.items():
        if not source_dir.exists():
            continue
        
        # Ищем unit'ы в этой директории и всех поддиректориях
        for unit_dir in source_dir.rglob("UNIT_*"):
            if unit_dir.is_dir():
                unit_id = unit_dir.name
                if unit_id not in all_units:
                    all_units[unit_id] = []
                
                # Ищем файлы в unit'е
                files_dir = unit_dir / "files"
                if files_dir.exists():
                    files = [f for f in files_dir.iterdir() if f.is_file()]
                    all_units[unit_id].extend(files)
    
    # Обрабатываем unit'ы
    units_to_process = list(all_units.items())
    if limit:
        units_to_process = units_to_process[:limit]
    
    for unit_id, files in units_to_process:
        try:
            unit_result = merge_unit_files(unit_id, files, dry_run)
            
            result["units_processed"] += 1
            result["files_moved"] += unit_result["files_moved"]
            
            # Обновляем статистику по типам
            for file_type, count in unit_result["files_by_type"].items():
                result["files_by_type"][file_type] = result["files_by_type"].get(file_type, 0) + count
            
            if unit_result["errors"]:
                result["errors"].extend(unit_result["errors"])
            
        except Exception as e:
            result["errors"].append({
                "unit_id": unit_id,
                "error": str(e)
            })
    
    result["completed_at"] = datetime.utcnow().isoformat()
    
    return result


def merge_unit_files(
    unit_id: str,
    files: List[Path],
    dry_run: bool = False
) -> Dict:
    """
    Объединяет файлы одного unit'а в ready_docling/.
    
    Args:
        unit_id: Идентификатор unit'а
        files: Список путей к файлам unit'а
        dry_run: Режим имитации
    
    Returns:
        Результат обработки unit'а
    """
    result = {
        "unit_id": unit_id,
        "files_moved": 0,
        "files_by_type": {},
        "errors": [],
        "target_paths": []
    }
    
    for file_path in files:
        try:
            # Определяем тип файла по расширению
            extension = file_path.suffix.lower()
            
            # Маппинг расширений на директории в ready_docling
            type_mapping = {
                ".pdf": "pdf",
                ".docx": "docx",
                ".doc": "docx",  # doc конвертируются в docx
                ".xlsx": "xlsx",
                ".xls": "xlsx",
                ".rtf": "rtf",
                ".pptx": "pptx",
                ".ppt": "pptx",
                ".jpg": "jpg",
                ".jpeg": "jpg",
                ".png": "png",
                ".tiff": "tiff",
                ".xml": "xml"
            }
            
            target_type = type_mapping.get(extension)
            
            if not target_type:
                result["errors"].append({
                    "file": str(file_path),
                    "error": f"Unknown file type: {extension}"
                })
                continue
            
            # Создаем целевую директорию
            target_base = READY_DOCLING_DIR / target_type / unit_id / "files"
            
            if not dry_run:
                target_base.mkdir(parents=True, exist_ok=True)
            
            # Определяем имя файла
            target_file = target_base / sanitize_filename(file_path.name)
            
            # Избегаем перезаписи
            if target_file.exists() and not dry_run:
                name_parts = target_file.stem, target_file.suffix
                counter = 1
                while target_file.exists():
                    target_file = target_base / f"{name_parts[0]}_{counter}{name_parts[1]}"
                    counter += 1
            
            # Перемещаем файл
            if not dry_run:
                shutil.move(str(file_path), str(target_file))
            
            result["files_moved"] += 1
            result["files_by_type"][target_type] = result["files_by_type"].get(target_type, 0) + 1
            result["target_paths"].append(str(target_file))
            
        except Exception as e:
            result["errors"].append({
                "file": str(file_path),
                "error": str(e)
            })
    
    return result


def get_ready_docling_statistics() -> Dict:
    """
    Получает статистику по файлам в ready_docling/.
    
    Returns:
        Словарь со статистикой
    """
    stats = {
        "total_units": 0,
        "total_files": 0,
        "by_type": {}
    }
    
    if not READY_DOCLING_DIR.exists():
        return stats
    
    # Проходим по всем типам файлов
    for type_dir in READY_DOCLING_DIR.iterdir():
        if not type_dir.is_dir():
            continue
        
        file_type = type_dir.name
        
        # Подсчитываем unit'ы
        units = [d for d in type_dir.iterdir() if d.is_dir() and d.name.startswith("UNIT_")]
        
        type_stats = {
            "units": len(units),
            "files": 0
        }
        
        # Подсчитываем файлы
        for unit_dir in units:
            files_dir = unit_dir / "files"
            if files_dir.exists():
                files = [f for f in files_dir.iterdir() if f.is_file()]
                type_stats["files"] += len(files)
        
        stats["by_type"][file_type] = type_stats
        stats["total_units"] += type_stats["units"]
        stats["total_files"] += type_stats["files"]
    
    return stats


def cleanup_pending_after_merge(
    unit_ids: List[str],
    dry_run: bool = False
) -> Dict:
    """
    Очищает pending директории после успешного объединения.
    
    Args:
        unit_ids: Список unit_id для очистки
        dry_run: Режим имитации
    
    Returns:
        Результат очистки
    """
    result = {
        "cleaned_units": 0,
        "cleaned_directories": 0,
        "errors": []
    }
    
    sources = [
        PENDING_DIRECT_DIR,
        PENDING_NORMALIZE_DIR,
        PENDING_CONVERT_DIR,
        EXTRACT_SORTED_DIR,
        EXTRACT_NORMALIZE_DIR,
        EXTRACT_CONVERT_DIR
    ]
    
    for unit_id in unit_ids:
        try:
            for source_dir in sources:
                # Ищем unit в этой директории и поддиректориях
                for unit_dir in source_dir.rglob(unit_id):
                    if unit_dir.is_dir():
                        if not dry_run:
                            shutil.rmtree(unit_dir)
                        result["cleaned_directories"] += 1
            
            result["cleaned_units"] += 1
            
        except Exception as e:
            result["errors"].append({
                "unit_id": unit_id,
                "error": str(e)
            })
    
    return result


def print_merge_summary(result: Dict):
    """Выводит сводку по объединению."""
    print("\n=== Объединение в ready_docling ===")
    print(f"Режим: {'DRY RUN' if result['dry_run'] else 'РЕАЛЬНЫЙ'}")
    print(f"Обработано unit'ов: {result['units_processed']}")
    print(f"Перемещено файлов: {result['files_moved']}")
    
    if result['files_by_type']:
        print("\nПо типам файлов:")
        for file_type, count in sorted(result['files_by_type'].items()):
            print(f"  {file_type}: {count} файлов")
    
    if result['errors']:
        print(f"\n✗ Ошибок: {len(result['errors'])}")
        for error in result['errors'][:5]:
            print(f"  - {error.get('error', 'Unknown error')}")
    
    print(f"\nНачало: {result['started_at']}")
    print(f"Завершение: {result.get('completed_at', 'В процессе...')}")


def final_merge_to_ready_docling(
    dry_run: bool = False,
    limit: Optional[int] = None
) -> Dict:
    """
    Объединяет все UNIT из Merge_1/2/3 в Ready2Docling согласно PRD раздел 9.
    
    Согласно PRD:
    - Все данные из Merge_1, Merge_2, Merge_3 объединяются в Ready2Docling
    - Все UNIT_XXX отсортированы по расширениям файлов
    - Для PDF дополнительная сортировка на pdf/scan/ и pdf/text/
    
    Args:
        dry_run: Если True, только показывает что будет сделано без реального перемещения
        limit: Ограничение на количество unit'ов для обработки
    
    Returns:
        Словарь со статистикой операции
    """
    result = {
        "started_at": datetime.utcnow().isoformat(),
        "dry_run": dry_run,
        "units_processed": 0,
        "files_moved": 0,
        "files_by_type": {},
        "pdf_by_category": {"scan": 0, "text": 0},
        "errors": [],
        "skipped": []
    }
    
    # Источники: Merge_1, Merge_2, Merge_3
    merge_sources = {
        "Merge_1": MERGE_1_DIR,
        "Merge_2": MERGE_2_DIR,
        "Merge_3": MERGE_3_DIR
    }
    
    # Собираем все UNIT из всех Merge
    all_units = {}
    
    for merge_name, merge_dir in merge_sources.items():
        if not merge_dir.exists():
            continue
        
        # Ищем UNIT во всех поддиректориях Merge
        for unit_dir in merge_dir.rglob("UNIT_*"):
            if unit_dir.is_dir():
                unit_id = unit_dir.name
                if unit_id not in all_units:
                    all_units[unit_id] = {
                        "source": merge_name,
                        "files": []
                    }
                
                # Ищем файлы в unit'е
                files_dir = unit_dir / "files"
                if files_dir.exists():
                    files = [f for f in files_dir.iterdir() if f.is_file()]
                    all_units[unit_id]["files"].extend(files)
                else:
                    # Ищем файлы напрямую в unit_dir
                    files = [f for f in unit_dir.iterdir() if f.is_file() and f.name not in ["metadata.json", "manifest.json"]]
                    all_units[unit_id]["files"].extend(files)
    
    # Обрабатываем UNIT
    units_to_process = list(all_units.items())
    if limit:
        units_to_process = units_to_process[:limit]
    
    for unit_id, unit_info in units_to_process:
        try:
            unit_result = merge_unit_to_ready_docling(unit_id, unit_info["files"], dry_run)
            
            result["units_processed"] += 1
            result["files_moved"] += unit_result["files_moved"]
            
            # Обновляем статистику по типам
            for file_type, count in unit_result["files_by_type"].items():
                result["files_by_type"][file_type] = result["files_by_type"].get(file_type, 0) + count
            
            # Обновляем статистику PDF
            if "pdf_scan" in unit_result.get("files_by_type", {}):
                result["pdf_by_category"]["scan"] += unit_result["files_by_type"]["pdf_scan"]
            if "pdf_text" in unit_result.get("files_by_type", {}):
                result["pdf_by_category"]["text"] += unit_result["files_by_type"]["pdf_text"]
            
            if unit_result["errors"]:
                result["errors"].extend(unit_result["errors"])
            
        except Exception as e:
            result["errors"].append({
                "unit_id": unit_id,
                "error": str(e)
            })
    
    result["completed_at"] = datetime.utcnow().isoformat()
    
    return result


def merge_unit_to_ready_docling(
    unit_id: str,
    files: List[Path],
    dry_run: bool = False
) -> Dict:
    """
    Объединяет файлы одного UNIT в Ready2Docling с сортировкой по расширениям.
    
    Согласно PRD раздел 9:
    - Все UNIT_XXX отсортированы по расширениям файлов
    - Для PDF дополнительная сортировка на scan/text
    
    Args:
        unit_id: Идентификатор UNIT
        files: Список путей к файлам UNIT
        dry_run: Режим имитации
    
    Returns:
        Результат обработки UNIT
    """
    result = {
        "unit_id": unit_id,
        "files_moved": 0,
        "files_by_type": {},
        "errors": [],
        "target_paths": []
    }
    
    for file_path in files:
        try:
            # Определяем тип файла
            detection = detect_file_type(file_path)
            detected_type = detection.get("detected_type", "unknown")
            extension = file_path.suffix.lower()
            
            # Маппинг расширений на директории в ready_docling
            type_mapping = {
                ".pdf": "pdf",
                ".docx": "docx",
                ".doc": "docx",  # doc конвертируются в docx
                ".xlsx": "xlsx",
                ".xls": "xlsx",
                ".rtf": "rtf",
                ".pptx": "pptx",
                ".ppt": "pptx",
                ".jpg": "jpg",
                ".jpeg": "jpeg",
                ".png": "png",
                ".tiff": "tiff",
                ".xml": "xml"
            }
            
            target_type = type_mapping.get(extension)
            
            if not target_type:
                result["errors"].append({
                    "file": str(file_path),
                    "error": f"Unknown file type: {extension}"
                })
                continue
            
            # Для PDF определяем scan или text
            pdf_subcategory = None
            if target_type == "pdf":
                needs_ocr = detection.get("needs_ocr", False)
                # Дополнительная проверка для PDF
                try:
                    reader = PdfReader(str(file_path))
                    has_text = False
                    for page in reader.pages[:3]:  # Проверяем первые 3 страницы
                        text = page.extract_text()
                        if text and len(text.strip()) > 10:
                            has_text = True
                            break
                    pdf_subcategory = "text" if has_text else "scan"
                except Exception:
                    pdf_subcategory = "scan" if needs_ocr else "text"
            
            # Создаем целевую директорию
            if pdf_subcategory:
                # PDF с подкатегорией scan/text
                target_base = READY_DOCLING_DIR / target_type / pdf_subcategory / unit_id / "files"
                result_key = f"pdf_{pdf_subcategory}"
            else:
                # Обычные файлы
                target_base = READY_DOCLING_DIR / target_type / unit_id / "files"
                result_key = target_type
            
            if not dry_run:
                target_base.mkdir(parents=True, exist_ok=True)
            
            # Определяем имя файла
            target_file = target_base / sanitize_filename(file_path.name)
            
            # Избегаем перезаписи
            if target_file.exists() and not dry_run:
                name_parts = target_file.stem, target_file.suffix
                counter = 1
                while target_file.exists():
                    target_file = target_base / f"{name_parts[0]}_{counter}{name_parts[1]}"
                    counter += 1
            
            # Перемещаем файл
            if not dry_run:
                shutil.move(str(file_path), str(target_file))
            
            result["files_moved"] += 1
            result["files_by_type"][result_key] = result["files_by_type"].get(result_key, 0) + 1
            result["target_paths"].append(str(target_file))
            
        except Exception as e:
            result["errors"].append({
                "file": str(file_path),
                "error": str(e)
            })
    
    return result


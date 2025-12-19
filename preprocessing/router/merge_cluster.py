"""
Управление Merge кластером для перемещения готовых UNIT в Merge_1/2/3.

Согласно PRD раздел 7:
- Merge_1 содержит только direct (UNIT изначально корректны)
- Merge_2 и Merge_3 содержат extracted, converted, normalized
- Все UNIT сортируются по расширениям файлов
"""
from pathlib import Path
from typing import Dict, Optional, List
import shutil
import json
from datetime import datetime

from .cycle_manager import CycleManager
from .file_classifier import classify_file
from .file_detection import detect_file_type
from .state_machine import UnitStateMachine, UnitState
from .manifest import update_manifest_v2
from .config import get_cycle_directories
from .utils import sanitize_filename


def move_to_merge(
    unit_id: str,
    cycle: int,
    subcategory: str,
    reason: str
) -> Dict[str, Any]:
    """
    Перемещает UNIT в Merge кластер для указанного цикла.
    
    Согласно PRD раздел 7.2:
    - Merge_1: только direct поддиректория
    - Merge_2/3: extracted, converted, normalized (НЕ direct)
    - Все UNIT сортируются по расширениям файлов
    
    Args:
        unit_id: Идентификатор UNIT
        cycle: Номер цикла (1, 2, или 3)
        subcategory: Подкатегория Merge (direct, extracted, converted, normalized)
        reason: Причина попадания в Merge (direct, extracted, converted, normalized)
    
    Returns:
        Результат перемещения
    """
    result = {
        "unit_id": unit_id,
        "cycle": cycle,
        "subcategory": subcategory,
        "status": "moved",
        "target_path": None,
        "errors": []
    }
    
    # Валидация
    if cycle == 1 and subcategory != "direct":
        result["status"] = "error"
        result["errors"].append(f"Merge_1 can only contain 'direct', got {subcategory}")
        return result
    
    if cycle > 1 and subcategory == "direct":
        result["status"] = "error"
        result["errors"].append(f"Merge_{cycle} cannot contain 'direct'")
        return result
    
    if subcategory not in ["direct", "extracted", "converted", "normalized"]:
        result["status"] = "error"
        result["errors"].append(f"Invalid subcategory: {subcategory}")
        return result
    
    try:
        # Получаем директории цикла
        cycle_dirs = get_cycle_directories(cycle)
        merge_dir = cycle_dirs["merge_dir"]
        
        # Находим UNIT в текущем расположении
        unit_dir = _find_unit_directory(unit_id, cycle)
        if not unit_dir:
            result["status"] = "error"
            result["errors"].append(f"Unit {unit_id} not found")
            return result
        
        # Определяем расширение файлов для сортировки
        extension = _determine_extension_for_sorting(unit_dir)
        
        # Создаем целевую директорию с учетом расширения
        target_base = merge_dir / subcategory
        if extension:
            target_base = target_base / extension
        
        target_dir = target_base / unit_id
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Перемещаем UNIT
        if target_dir.exists() and target_dir != unit_dir:
            shutil.rmtree(target_dir)
        
        if unit_dir != target_dir:
            shutil.move(str(unit_dir), str(target_dir))
        
        result["target_path"] = str(target_dir)
        
        # Обновляем state machine
        state_machine = UnitStateMachine(unit_id)
        if cycle == 1:
            state_machine.transition(UnitState.MERGED_1_DIRECT)
        elif cycle == 2:
            state_machine.transition(UnitState.MERGED_2)
        elif cycle == 3:
            state_machine.transition(UnitState.MERGED_3)
        
        # Обновляем manifest
        manifest_path = target_dir / "manifest.json"
        if manifest_path.exists():
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
            
            manifest = update_manifest_v2(
                manifest,
                state_trace=state_machine.get_state_trace(),
                current_cycle=cycle,
                final_cluster=f"Merge_{cycle}",
                final_reason=reason
            )
            
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2, ensure_ascii=False)
        
    except Exception as e:
        result["status"] = "error"
        result["errors"].append(str(e))
    
    return result


def _find_unit_directory(unit_id: str, cycle: int) -> Optional[Path]:
    """
    Находит директорию UNIT в текущем цикле.
    
    Args:
        unit_id: Идентификатор UNIT
        cycle: Номер цикла
    
    Returns:
        Path к директории UNIT или None
    """
    cycle_dirs = get_cycle_directories(cycle)
    pending_dir = cycle_dirs["pending_dir"]
    
    # Ищем UNIT в pending директории
    unit_dirs = list(pending_dir.rglob(f"{unit_id}"))
    if unit_dirs:
        return unit_dirs[0]
    
    # Если не найден, ищем в других местах
    from .config import INPUT_DIR, PROCESSING_BASE_DIR
    
    # Ищем в Input
    unit_dirs = list(INPUT_DIR.rglob(f"{unit_id}"))
    if unit_dirs:
        return unit_dirs[0]
    
    # Ищем во всех циклах Processing
    for c in [1, 2, 3]:
        if c == cycle:
            continue
        c_dirs = get_cycle_directories(c)
        unit_dirs = list(c_dirs["pending_dir"].rglob(f"{unit_id}"))
        if unit_dirs:
            return unit_dirs[0]
    
    return None


def _determine_extension_for_sorting(unit_dir: Path) -> Optional[str]:
    """
    Определяет расширение файлов UNIT для сортировки.
    
    Args:
        unit_dir: Директория UNIT
    
    Returns:
        Расширение файла (без точки) или None
    """
    # Ищем файлы в UNIT
    files_dir = unit_dir / "files"
    if files_dir.exists():
        files = [f for f in files_dir.iterdir() if f.is_file()]
    else:
        files = [f for f in unit_dir.iterdir() if f.is_file() and f.name != "metadata.json" and f.name != "manifest.json"]
    
    if not files:
        return None
    
    # Берем первый файл и определяем его тип
    first_file = files[0]
    try:
        detection = detect_file_type(first_file)
        detected_type = detection.get("detected_type", "")
        
        # Нормализуем расширение
        if detected_type:
            # Убираем суффиксы типа "_archive"
            ext = detected_type.replace("_archive", "")
            return ext
        
        # Fallback: используем расширение файла
        ext = first_file.suffix.lower().lstrip(".")
        return ext if ext else None
    except Exception:
        # Fallback: используем расширение файла
        ext = first_file.suffix.lower().lstrip(".")
        return ext if ext else None


def get_merge_statistics(cycle: Optional[int] = None) -> Dict[str, Any]:
    """
    Получает статистику по Merge кластерам.
    
    Args:
        cycle: Номер цикла (опционально, если None - для всех циклов)
    
    Returns:
        Статистика по Merge
    """
    stats = {}
    
    cycles_to_check = [cycle] if cycle else [1, 2, 3]
    
    for c in cycles_to_check:
        cycle_dirs = get_cycle_directories(c)
        merge_dir = cycle_dirs["merge_dir"]
        
        cycle_stats = {
            "total_units": 0,
            "by_subcategory": {},
            "by_extension": {}
        }
        
        if merge_dir.exists():
            # Подсчитываем UNIT по подкатегориям
            for subcategory_dir in merge_dir.iterdir():
                if not subcategory_dir.is_dir():
                    continue
                
                subcategory = subcategory_dir.name
                units_count = len([d for d in subcategory_dir.iterdir() if d.is_dir() and d.name.startswith("UNIT_")])
                cycle_stats["by_subcategory"][subcategory] = units_count
                cycle_stats["total_units"] += units_count
                
                # Подсчитываем по расширениям
                for ext_dir in subcategory_dir.iterdir():
                    if not ext_dir.is_dir():
                        continue
                    
                    ext = ext_dir.name
                    ext_units = len([d for d in ext_dir.iterdir() if d.is_dir() and d.name.startswith("UNIT_")])
                    cycle_stats["by_extension"][ext] = cycle_stats["by_extension"].get(ext, 0) + ext_units
        
        stats[f"Merge_{c}"] = cycle_stats
    
    return stats


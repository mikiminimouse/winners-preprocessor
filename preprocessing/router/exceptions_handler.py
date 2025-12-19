"""
Управление Exceptions кластером для перемещения проблемных UNIT в Exceptions_1/2/3.

Согласно PRD раздел 6:
- Exceptions хранит UNIT, которые не имеют бизнес-ценности или не могут быть обработаны
- Поддиректории: special, mixed, unknown
"""
from pathlib import Path
from typing import Dict, Optional
import shutil
import json

from .config import get_cycle_directories
from .state_machine import UnitStateMachine, UnitState
from .manifest import update_manifest_v2


def move_to_exceptions(
    unit_id: str,
    cycle: int,
    reason: str,
    subcategory: str
) -> Dict[str, Any]:
    """
    Перемещает UNIT в Exceptions кластер для указанного цикла.
    
    Согласно PRD раздел 6.2:
    - special: подписи, системный мусор, файлы без документарной ценности
    - mixed: смешанные типы файлов внутри одного юнита
    - unknown: тип файла не определён, pipeline не подобран
    
    Args:
        unit_id: Идентификатор UNIT
        cycle: Номер цикла (1, 2, или 3)
        reason: Причина попадания в Exceptions
        subcategory: Подкатегория Exceptions (special, mixed, unknown)
    
    Returns:
        Результат перемещения
    """
    result = {
        "unit_id": unit_id,
        "cycle": cycle,
        "subcategory": subcategory,
        "reason": reason,
        "status": "moved",
        "target_path": None,
        "errors": []
    }
    
    # Валидация subcategory
    if subcategory not in ["special", "mixed", "unknown"]:
        result["status"] = "error"
        result["errors"].append(f"Invalid subcategory: {subcategory}. Must be one of: special, mixed, unknown")
        return result
    
    try:
        # Получаем директории цикла
        cycle_dirs = get_cycle_directories(cycle)
        exceptions_dir = cycle_dirs["exceptions_dir"]
        
        # Находим UNIT в текущем расположении
        unit_dir = _find_unit_directory(unit_id, cycle)
        if not unit_dir:
            result["status"] = "error"
            result["errors"].append(f"Unit {unit_id} not found")
            return result
        
        # Создаем целевую директорию
        target_base = exceptions_dir / subcategory
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
            state_machine.transition(UnitState.EXCEPTIONS_1)
        elif cycle == 2:
            state_machine.transition(UnitState.EXCEPTIONS_2)
        elif cycle == 3:
            state_machine.transition(UnitState.EXCEPTIONS_3)
        
        # Обновляем manifest
        manifest_path = target_dir / "manifest.json"
        if manifest_path.exists():
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
            
            manifest = update_manifest_v2(
                manifest,
                state_trace=state_machine.get_state_trace(),
                current_cycle=cycle,
                final_cluster=f"Exceptions_{cycle}",
                final_reason=reason
            )
            
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2, ensure_ascii=False)
        else:
            # Создаем новый manifest если не существует
            # Пытаемся найти существующий manifest для сохранения protocol_date
            protocol_date = None
            protocol_id = None
            try:
                # Ищем manifest в других местах
                from .config import PROCESSING_BASE_DIR
                for search_dir in [PROCESSING_BASE_DIR / f"Pending_{cycle}", 
                                   PROCESSING_BASE_DIR / f"Merge_{cycle}"]:
                    if search_dir.exists():
                        manifest_candidates = list(search_dir.rglob(f"{unit_id}/manifest.json"))
                        if manifest_candidates:
                            with open(manifest_candidates[0], 'r', encoding='utf-8') as f:
                                existing_manifest = json.load(f)
                                protocol_date = existing_manifest.get("protocol_date")
                                protocol_id = existing_manifest.get("protocol_id")
                                break
            except Exception:
                pass
            
            from .manifest import create_manifest_v2
            manifest = create_manifest_v2(
                unit_id=unit_id,
                protocol_id=protocol_id,
                protocol_date=protocol_date,
                current_cycle=cycle,
                state_trace=state_machine.get_state_trace()
            )
            manifest["processing"]["final_cluster"] = f"Exceptions_{cycle}"
            manifest["processing"]["final_reason"] = reason
            
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
    from .config import INPUT_DIR
    
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


def get_exceptions_statistics(cycle: Optional[int] = None) -> Dict[str, Any]:
    """
    Получает статистику по Exceptions кластерам.
    
    Args:
        cycle: Номер цикла (опционально, если None - для всех циклов)
    
    Returns:
        Статистика по Exceptions
    """
    stats = {}
    
    cycles_to_check = [cycle] if cycle else [1, 2, 3]
    
    for c in cycles_to_check:
        cycle_dirs = get_cycle_directories(c)
        exceptions_dir = cycle_dirs["exceptions_dir"]
        
        cycle_stats = {
            "total_units": 0,
            "by_subcategory": {
                "special": 0,
                "mixed": 0,
                "unknown": 0
            }
        }
        
        if exceptions_dir.exists():
            # Подсчитываем UNIT по подкатегориям
            for subcategory_dir in exceptions_dir.iterdir():
                if not subcategory_dir.is_dir():
                    continue
                
                subcategory = subcategory_dir.name
                if subcategory in cycle_stats["by_subcategory"]:
                    units_count = len([d for d in subcategory_dir.iterdir() if d.is_dir() and d.name.startswith("UNIT_")])
                    cycle_stats["by_subcategory"][subcategory] = units_count
                    cycle_stats["total_units"] += units_count
        
        stats[f"Exceptions_{c}"] = cycle_stats
    
    return stats


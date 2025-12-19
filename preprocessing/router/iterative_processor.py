"""
Итеративный процессор для управления циклами обработки UNIT согласно PRD раздел 8.

Логика обработки:
1. Classifier → маршрутизация в Pending_N
2. Обработка (convert/extract/normalize)
3. Повторный Classifier
4. Перемещение в Merge_N или Pending_N+1 или Exceptions_N
"""
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import shutil
import json
import subprocess

from .state_machine import UnitStateMachine, UnitState
from .cycle_manager import CycleManager
from .file_classifier import classify_file, classify_unit_files
from .file_detection import detect_file_type
from .unit_distribution_new import distribute_unit_by_new_structure
from .archive import safe_extract_archive
from .manifest import create_manifest_v2, update_manifest_v2
from .config import MAX_CYCLES, TEMP_DIR
from .utils import sanitize_filename


class IterativeProcessor:
    """
    Процессор для итеративной обработки UNIT согласно PRD.
    
    Управляет циклами обработки:
    - Cycle 1: RAW_INPUT → CLASSIFIED_1 → PENDING_1/MERGED_1_DIRECT/EXCEPTIONS_1
    - Cycle 2: PENDING_1 → CLASSIFIED_2 → MERGED_2/PENDING_2/EXCEPTIONS_2
    - Cycle 3: PENDING_2 → CLASSIFIED_3 → MERGED_3/EXCEPTIONS_3
    """
    
    def __init__(self, unit_id: str, manifest_path: Optional[Path] = None):
        """
        Инициализирует IterativeProcessor.
        
        Args:
            unit_id: Идентификатор UNIT
            manifest_path: Путь к manifest.json (опционально)
        """
        self.unit_id = unit_id
        self.manifest_path = manifest_path
        self.state_machine = UnitStateMachine(unit_id, manifest_path)
        self.cycle_manager = CycleManager(initial_cycle=1)
        self.manifest: Optional[Dict] = None
        
        # Загружаем manifest если существует
        if manifest_path and manifest_path.exists():
            self._load_manifest()
        else:
            # Создаем начальный manifest
            self.manifest = create_manifest_v2(
                unit_id=unit_id,
                current_cycle=1,
                state_trace=["RAW_INPUT"]
            )
    
    def _load_manifest(self) -> None:
        """Загружает manifest из файла."""
        try:
            with open(self.manifest_path, 'r', encoding='utf-8') as f:
                self.manifest = json.load(f)
            
            # Обновляем cycle_manager на основе manifest
            current_cycle = self.manifest.get("processing", {}).get("current_cycle", 1)
            self.cycle_manager.set_cycle(current_cycle)
        except Exception:
            # При ошибке загрузки создаем новый manifest, сохраняя protocol_date если был
            protocol_date = None
            if self.manifest and "protocol_date" in self.manifest:
                protocol_date = self.manifest.get("protocol_date")
            
            self.manifest = create_manifest_v2(
                unit_id=self.unit_id,
                protocol_id=self.manifest.get("protocol_id") if self.manifest else None,
                protocol_date=protocol_date,
                current_cycle=1,
                state_trace=["RAW_INPUT"]
            )
    
    def _save_manifest(self) -> None:
        """Сохраняет manifest в файл."""
        if self.manifest_path:
            self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.manifest_path, 'w', encoding='utf-8') as f:
                json.dump(self.manifest, f, indent=2, ensure_ascii=False)
    
    def process_cycle(self, cycle: int) -> Dict[str, Any]:
        """
        Обрабатывает один цикл обработки.
        
        Args:
            cycle: Номер цикла (1, 2, или 3)
        
        Returns:
            Результат обработки цикла
        """
        if cycle < 1 or cycle > MAX_CYCLES:
            raise ValueError(f"Cycle must be between 1 and {MAX_CYCLES}, got {cycle}")
        
        self.cycle_manager.set_cycle(cycle)
        result = {
            "cycle": cycle,
            "unit_id": self.unit_id,
            "status": "processing",
            "actions_taken": [],
            "errors": [],
            "final_state": None
        }
        
        try:
            # Шаг 1: Classifier → маршрутизация
            classification_result = self._classify_and_route(cycle)
            result["actions_taken"].append("classified")
            result["classification"] = classification_result
            
            # Если UNIT уже готов (direct), перемещаем в Merge
            if classification_result.get("is_ready"):
                if cycle == 1:
                    # Merge_1/direct
                    move_result = self._move_to_merge(cycle, "direct", "direct")
                    result["actions_taken"].append("moved_to_merge_1_direct")
                    result["final_state"] = "MERGED_1_DIRECT"
                else:
                    # Определяем причину (extracted/converted/normalized)
                    reason = classification_result.get("reason", "direct")
                    move_result = self._move_to_merge(cycle, reason, reason)
                    result["actions_taken"].append(f"moved_to_merge_{cycle}_{reason}")
                    result["final_state"] = f"MERGED_{cycle}"
                return result
            
            # Если UNIT требует обработки, выполняем её
            if classification_result.get("needs_processing"):
                processing_result = self._process_unit(cycle, classification_result)
                result["actions_taken"].append("processed")
                result["processing"] = processing_result
                
                # После обработки повторная классификация
                reclassification_result = self._reclassify_after_processing(cycle)
                result["actions_taken"].append("reclassified")
                result["reclassification"] = reclassification_result
                
                # Определяем следующий шаг
                if reclassification_result.get("is_ready"):
                    # Перемещаем в Merge
                    reason = reclassification_result.get("reason", "processed")
                    move_result = self._move_to_merge(cycle, reason, reason)
                    result["actions_taken"].append(f"moved_to_merge_{cycle}_{reason}")
                    result["final_state"] = f"MERGED_{cycle}"
                elif cycle < MAX_CYCLES:
                    # Перемещаем в следующий цикл
                    next_cycle = cycle + 1
                    move_result = self._move_to_next_cycle(next_cycle, reclassification_result)
                    result["actions_taken"].append(f"moved_to_cycle_{next_cycle}")
                    result["final_state"] = f"PENDING_{next_cycle}"
                else:
                    # Максимум циклов достигнут - в Exceptions
                    move_result = self._move_to_exceptions(cycle, "max_cycles_reached", "unknown")
                    result["actions_taken"].append("moved_to_exceptions")
                    result["final_state"] = f"EXCEPTIONS_{cycle}"
            else:
                # UNIT не может быть обработан - в Exceptions
                move_result = self._move_to_exceptions(cycle, "cannot_process", classification_result.get("reason", "unknown"))
                result["actions_taken"].append("moved_to_exceptions")
                result["final_state"] = f"EXCEPTIONS_{cycle}"
            
            result["status"] = "completed"
            
        except Exception as e:
            result["status"] = "error"
            result["errors"].append(str(e))
            result["final_state"] = f"EXCEPTIONS_{cycle}"
        
        return result
    
    def _classify_and_route(self, cycle: int) -> Dict[str, Any]:
        """
        Классифицирует UNIT и определяет маршрутизацию.
        
        Args:
            cycle: Номер цикла
        
        Returns:
            Результат классификации
        """
        # Находим файлы UNIT
        cycle_dirs = self.cycle_manager.get_cycle_directories()
        pending_dir = cycle_dirs["pending_dir"]
        
        # Ищем UNIT в pending директориях
        unit_dirs = list(pending_dir.rglob(f"{self.unit_id}"))
        if not unit_dirs:
            # Если UNIT не найден в pending, ищем в других местах
            from .config import INPUT_DIR
            unit_dirs = list(INPUT_DIR.rglob(f"{self.unit_id}"))
        
        if not unit_dirs:
            return {
                "is_ready": False,
                "needs_processing": False,
                "reason": "unit_not_found"
            }
        
        unit_dir = unit_dirs[0]
        files_dir = unit_dir / "files"
        
        if not files_dir.exists():
            # Ищем файлы напрямую в unit_dir
            files = [f for f in unit_dir.iterdir() if f.is_file() and f.name != "metadata.json"]
        else:
            files = [f for f in files_dir.iterdir() if f.is_file()]
        
        if not files:
            return {
                "is_ready": False,
                "needs_processing": False,
                "reason": "no_files"
            }
        
        # Классифицируем все файлы
        unit_classification = classify_unit_files(files, self.unit_id)
        
        # Определяем категорию UNIT
        categories = unit_classification.get("type_distribution", {})
        dominant_category = max(categories, key=categories.get) if categories else "unknown"
        
        # Проверяем, является ли UNIT готовым (direct)
        if dominant_category == "direct" and not unit_classification.get("is_mixed"):
            return {
                "is_ready": True,
                "needs_processing": False,
                "reason": "direct",
                "category": "direct"
            }
        
        # Определяем, нужна ли обработка
        needs_processing = dominant_category in ["convert", "extract", "normalize"]
        
        return {
            "is_ready": False,
            "needs_processing": needs_processing,
            "category": dominant_category,
            "is_mixed": unit_classification.get("is_mixed", False),
            "type_distribution": categories,
            "files": [str(f) for f in files]
        }
    
    def _process_unit(self, cycle: int, classification_result: Dict) -> Dict[str, Any]:
        """
        Обрабатывает UNIT (convert/extract/normalize).
        
        Args:
            cycle: Номер цикла
            classification_result: Результат классификации
        
        Returns:
            Результат обработки
        """
        category = classification_result.get("category")
        files = classification_result.get("files", [])
        
        result = {
            "category": category,
            "processed_files": [],
            "errors": []
        }
        
        if category == "convert":
            result.update(self._convert_files(files, cycle))
        elif category == "extract":
            result.update(self._extract_archives(files, cycle))
        elif category == "normalize":
            result.update(self._normalize_files(files, cycle))
        
        return result
    
    def _convert_files(self, files: List[str], cycle: int) -> Dict[str, Any]:
        """Конвертирует файлы (doc→docx, xls→xlsx и т.д.)."""
        result = {
            "converted": [],
            "errors": []
        }
        
        for file_path_str in files:
            try:
                file_path = Path(file_path_str)
                if not file_path.exists():
                    continue
                
                # Определяем тип файла
                detection = detect_file_type(file_path)
                detected_type = detection.get("detected_type")
                
                # Маппинг типов для конвертации
                convert_map = {
                    "doc": "docx",
                    "xls": "xlsx",
                    "ppt": "pptx"
                }
                
                if detected_type not in convert_map:
                    continue
                
                target_type = convert_map[detected_type]
                target_path = file_path.parent / f"{file_path.stem}.{target_type}"
                
                # Конвертация через LibreOffice (если доступен)
                try:
                    subprocess.run(
                        ["libreoffice", "--headless", "--convert-to", target_type.split("x")[0],
                         "--outdir", str(file_path.parent), str(file_path)],
                        check=True,
                        timeout=60,
                        capture_output=True
                    )
                    
                    if target_path.exists():
                        # Удаляем исходный файл
                        file_path.unlink()
                        result["converted"].append({
                            "from": str(file_path),
                            "to": str(target_path),
                            "type": f"{detected_type}→{target_type}"
                        })
                except Exception as e:
                    result["errors"].append({
                        "file": str(file_path),
                        "error": str(e)
                    })
            except Exception as e:
                result["errors"].append({
                    "file": file_path_str,
                    "error": str(e)
                })
        
        return result
    
    def _extract_archives(self, files: List[str], cycle: int) -> Dict[str, Any]:
        """Извлекает архивы."""
        result = {
            "extracted": [],
            "errors": []
        }
        
        for file_path_str in files:
            try:
                file_path = Path(file_path_str)
                if not file_path.exists():
                    continue
                
                # Создаем директорию для извлечения
                extract_dir = file_path.parent / f"{file_path.stem}_extracted"
                extract_dir.mkdir(parents=True, exist_ok=True)
                
                # Извлекаем архив
                extracted_files, success = safe_extract_archive(
                    file_path,
                    extract_dir,
                    self.unit_id
                )
                
                if success:
                    # Удаляем исходный архив
                    file_path.unlink()
                    result["extracted"].append({
                        "archive": str(file_path),
                        "extracted_to": str(extract_dir),
                        "files_count": len(extracted_files)
                    })
            except Exception as e:
                result["errors"].append({
                    "file": file_path_str,
                    "error": str(e)
                })
        
        return result
    
    def _normalize_files(self, files: List[str], cycle: int) -> Dict[str, Any]:
        """Нормализует имена файлов и расширения."""
        result = {
            "normalized": [],
            "errors": []
        }
        
        for file_path_str in files:
            try:
                file_path = Path(file_path_str)
                if not file_path.exists():
                    continue
                
                # Определяем тип файла
                detection = detect_file_type(file_path)
                detected_type = detection.get("detected_type")
                
                # Нормализуем имя файла
                normalized_name = sanitize_filename(file_path.name)
                
                # Исправляем расширение если нужно
                if detected_type and not normalized_name.endswith(f".{detected_type}"):
                    # Убираем старое расширение и добавляем правильное
                    name_without_ext = Path(normalized_name).stem
                    normalized_name = f"{name_without_ext}.{detected_type}"
                
                target_path = file_path.parent / normalized_name
                
                if target_path != file_path:
                    file_path.rename(target_path)
                    result["normalized"].append({
                        "from": str(file_path),
                        "to": str(target_path),
                        "type": detected_type
                    })
            except Exception as e:
                result["errors"].append({
                    "file": file_path_str,
                    "error": str(e)
                })
        
        return result
    
    def _reclassify_after_processing(self, cycle: int) -> Dict[str, Any]:
        """Повторно классифицирует UNIT после обработки."""
        # Аналогично _classify_and_route, но после обработки
        return self._classify_and_route(cycle)
    
    def _move_to_merge(self, cycle: int, subcategory: str, reason: str) -> Dict[str, Any]:
        """Перемещает UNIT в Merge кластер."""
        # Импортируем здесь чтобы избежать циклических зависимостей
        from .merge_cluster import move_to_merge
        return move_to_merge(self.unit_id, cycle, subcategory, reason)
    
    def _move_to_next_cycle(self, next_cycle: int, classification_result: Dict) -> Dict[str, Any]:
        """Перемещает UNIT в следующий цикл."""
        # Находим текущее расположение UNIT
        cycle_dirs = self.cycle_manager.get_cycle_directories()
        pending_dir = cycle_dirs["pending_dir"]
        
        # Ищем UNIT
        unit_dirs = list(pending_dir.rglob(f"{self.unit_id}"))
        if not unit_dirs:
            return {"status": "error", "message": "Unit not found"}
        
        unit_dir = unit_dirs[0]
        
        # Определяем целевую директорию для следующего цикла
        next_cycle_manager = CycleManager(initial_cycle=next_cycle)
        category = classification_result.get("category", "direct")
        next_pending_dir = next_cycle_manager.get_target_pending_dir(category)
        
        # Перемещаем UNIT
        target_dir = next_pending_dir / self.unit_id
        if target_dir.exists():
            shutil.rmtree(target_dir)
        shutil.move(str(unit_dir), str(target_dir))
        
        # Обновляем state machine и manifest
        self.cycle_manager.set_cycle(next_cycle)
        self.state_machine.transition(UnitState(f"PENDING_{next_cycle}"))
        
        if self.manifest:
            self.manifest = update_manifest_v2(
                self.manifest,
                state_trace=self.state_machine.get_state_trace(),
                current_cycle=next_cycle
            )
            self._save_manifest()
        
        return {"status": "moved", "target": str(target_dir)}
    
    def _move_to_exceptions(self, cycle: int, reason: str, subcategory: str) -> Dict[str, Any]:
        """Перемещает UNIT в Exceptions кластер."""
        # Импортируем здесь чтобы избежать циклических зависимостей
        from .exceptions_handler import move_to_exceptions
        return move_to_exceptions(self.unit_id, cycle, reason, subcategory)
    
    def process_all_cycles(self) -> Dict[str, Any]:
        """
        Обрабатывает все циклы до завершения или достижения максимума.
        
        Returns:
            Результат обработки всех циклов
        """
        result = {
            "unit_id": self.unit_id,
            "cycles_processed": [],
            "final_state": None,
            "status": "completed"
        }
        
        cycle = 1
        while cycle <= MAX_CYCLES:
            cycle_result = self.process_cycle(cycle)
            result["cycles_processed"].append(cycle_result)
            
            final_state = cycle_result.get("final_state")
            if final_state and ("MERGED" in final_state or "EXCEPTIONS" in final_state):
                result["final_state"] = final_state
                break
            
            cycle += 1
        
        if not result["final_state"]:
            result["status"] = "max_cycles_reached"
            result["final_state"] = f"EXCEPTIONS_{MAX_CYCLES}"
        
        return result


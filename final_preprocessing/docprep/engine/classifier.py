"""
Classifier - классификация файлов и определение категорий обработки.
"""
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from collections import Counter
import logging

from ..core.manifest import load_manifest
from ..core.state_machine import UnitState, UnitStateMachine
from ..core.audit import get_audit_logger
from ..core.unit_processor import (
    create_unit_manifest_if_needed,
    move_unit_to_target,
    update_unit_state,
    get_extension_subdirectory,
    determine_unit_extension,
)
from ..core.config import (
    get_processing_paths,
    get_data_paths,
    INPUT_DIR,
)
from ..utils.file_ops import detect_file_type
from ..utils.paths import get_unit_files
from ..core.manifest import _determine_route_from_files, save_manifest, load_manifest

logger = logging.getLogger(__name__)


class Classifier:
    """
    Классификатор для определения категории обработки UNIT.

    Классифицирует файлы и определяет, куда должен быть направлен UNIT
    для дальнейшей обработки.
    """

    # Расширения для подписей
    SIGNATURE_EXTENSIONS = {".sig", ".p7s", ".pem", ".cer", ".crt"}

    # Неподдерживаемые расширения
    UNSUPPORTED_EXTENSIONS = {".exe", ".dll", ".db", ".tmp", ".log", ".ini", ".sys", ".bat", ".sh"}

    # Типы, требующие конвертации
    CONVERTIBLE_TYPES = {
        "doc": "docx",
        "xls": "xlsx",
        "ppt": "pptx",
    }

    def __init__(self):
        """Инициализирует Classifier."""
        self.audit_logger = get_audit_logger()

    def _update_manifest_route(self, target_dir: Path, route: str) -> None:
        """Обновляет route в manifest целевой директории."""
        try:
            manifest_path = target_dir / "manifest.json"
            if manifest_path.exists():
                manifest = load_manifest(target_dir)
                current_route = manifest.get("processing", {}).get("route")
                
                # Обновляем только если route изменился или отсутствует
                if current_route != route:
                    if "processing" not in manifest:
                        manifest["processing"] = {}
                    manifest["processing"]["route"] = route
                    save_manifest(target_dir, manifest)
                    logger.debug(f"Updated route to '{route}' for unit in {target_dir}")
        except Exception as e:
            logger.warning(f"Failed to update manifest route in {target_dir}: {e}")

    def classify_unit(
        self,
        unit_path: Path,
        cycle: int,
        protocol_date: Optional[str] = None,
        protocol_id: Optional[str] = None,
        dry_run: bool = False,
        copy_mode: bool = False,
    ) -> Dict[str, Any]:
        """
        Классифицирует UNIT, создает manifest, перемещает UNIT в целевую директорию и обновляет state.

        NOTE: Ready2Docling - это отдельный этап, запускаемый через merge2docling.
              Direct units из ВСЕХ циклов идут в единую директорию Merge/Direct/.

        Args:
            unit_path: Путь к директории UNIT
            cycle: Номер цикла (1, 2, 3)
            protocol_date: Дата протокола (опционально)
            protocol_id: ID протокола (опционально)
            dry_run: Если True, только показывает что будет сделано
            copy_mode: Если True, копирует вместо перемещения (сохраняет исходные файлы)

        Returns:
            Словарь с результатами классификации:
            - category: категория (direct, convert, extract, normalize, special, mixed)
            - unit_category: категория UNIT
            - is_mixed: является ли UNIT mixed
            - file_classifications: классификация каждого файла
            - target_directory: целевая директория для UNIT
            - moved_to: путь к новой директории UNIT (после перемещения)
        """
        unit_id = unit_path.name

        # Автоматически включаем copy_mode для units из Input директории
        # (для периода тестирования, чтобы не удалять исходные файлы)
        if not copy_mode:
            try:
                # Проверяем, находится ли unit_path в Input директории
                unit_path_real = unit_path.resolve()
                
                # Получаем все возможные пути к Input директории
                is_in_input = False
                
                # Проверяем различные варианты путей Input
                from datetime import datetime
                current_date = datetime.now().strftime("%Y-%m-%d")
                
                # Пытаемся извлечь дату из пути unit_path
                unit_parts = unit_path.parts
                date_part = None
                for part in unit_parts:
                    if len(part) == 10 and part[4] == '-' and part[7] == '-':
                        try:
                            datetime.strptime(part, "%Y-%m-%d")
                            date_part = part
                            break
                        except ValueError:
                            continue
                
                # Список путей для проверки (только относительные части)
                check_patterns = []
                
                # Стандартный путь Input (относительная часть)
                input_dir_path = Path(INPUT_DIR)
                check_patterns.append(str(input_dir_path))
                
                # Пути с датами (относительные части)
                check_dates = [current_date]
                if date_part:
                    check_dates.append(date_part)
                
                for check_date in check_dates:
                    try:
                        data_paths = get_data_paths(check_date)
                        dated_input_dir = data_paths["input"]
                        check_patterns.append(str(dated_input_dir))
                    except (KeyError, ValueError, TypeError):
                        pass  # Игнорируем ошибки при получении путей для невалидных дат
                
                # Проверяем каждый путь (проверяем наличие паттернов в пути unit)
                unit_path_str = str(unit_path_real)
                for pattern in check_patterns:
                    if pattern in unit_path_str:
                        is_in_input = True
                        break
                
                # Дополнительная проверка: ищем "Input" в пути с датой
                if not is_in_input:
                    # Ищем паттерн вида "/YYYY-MM-DD/Input/"
                    import re
                    date_input_pattern = r"/\d{4}-\d{2}-\d{2}/Input/"
                    if re.search(date_input_pattern, unit_path_str):
                        is_in_input = True
                
                if is_in_input:
                    copy_mode = True
                    logger.debug(f"Auto-enabling copy_mode for unit from Input: {unit_id}")
            except Exception as e:
                logger.warning(f"Failed to check if unit is in Input directory: {e}")
                # Игнорируем ошибки, оставляем copy_mode как есть

        # Получаем файлы UNIT
        files = get_unit_files(unit_path)
        if not files:
            # Пустые UNIT идут в Exceptions/Empty
            target_base_dir = self._get_target_directory_base("empty", cycle, protocol_date)
            target_dir_base = target_base_dir / "Empty"
            
            # Загружаем manifest если существует
            manifest = None
            manifest_path = unit_path / "manifest.json"
            if manifest_path.exists():
                try:
                    manifest = load_manifest(unit_path)
                    if not protocol_date:
                        protocol_date = manifest.get("protocol_date")
                    if not protocol_id:
                        protocol_id = manifest.get("protocol_id")
                except Exception as e:
                    logger.warning(f"Failed to load manifest for {unit_id}: {e}")
            
            # Создаем manifest если его нет
            if not manifest:
                manifest = create_unit_manifest_if_needed(
                    unit_path=unit_path,
                    unit_id=unit_id,
                    protocol_id=protocol_id,
                    protocol_date=protocol_date,
                    files=[],  # Пустой список файлов
                    cycle=cycle,
                )
            
            # Перемещаем пустой UNIT в Empty
            if not dry_run:
                target_dir = move_unit_to_target(
                    unit_dir=unit_path,
                    target_base_dir=target_dir_base,
                    extension=None,  # Exceptions не сортируются по расширениям
                    dry_run=dry_run,
                    copy_mode=copy_mode,
                )
                
                # Обновляем state machine - пустые UNIT сразу в EXCEPTION
                exception_state_map = {
                    1: UnitState.EXCEPTION_1,
                    2: UnitState.EXCEPTION_2,
                    3: UnitState.EXCEPTION_3,
                }
                new_state = exception_state_map.get(cycle, UnitState.EXCEPTION_1)
                update_unit_state(
                    unit_path=target_dir,
                    new_state=new_state,
                    cycle=cycle,
                    operation={
                        "type": "classify",
                        "category": "empty",
                        "is_mixed": False,
                        "file_count": 0,
                        "reason": "empty_unit",
                    },
                    final_cluster="Exceptions/Direct" if cycle == 1 else f"Exceptions/Processed_{cycle}",
                    final_reason="Empty unit with no files",
                )

                # Логируем классификацию
                self.audit_logger.log_event(
                    unit_id=unit_id,
                    event_type="operation",
                    operation="classify",
                    details={
                        "cycle": cycle,
                        "category": "empty",
                        "is_mixed": False,
                        "file_count": 0,
                        "reason": "empty_unit",
                        "target_directory": str(target_dir),
                        "final_cluster": "Exceptions/Direct" if cycle == 1 else f"Exceptions/Processed_{cycle}",
                        "final_reason": "Empty unit with no files",
                    },
                    state_before="RAW",
                    state_after=new_state.value,
                    unit_path=target_dir,
                )
            else:
                target_dir = target_dir_base / unit_path.name
            
            return {
                "category": "empty",
                "unit_category": "empty",
                "is_mixed": False,
                "file_classifications": [],
                "target_directory": str(target_dir_base),  # ИСПРАВЛЕНО: было target_base_dir
                "moved_to": str(target_dir),
                "error": "No files found in UNIT",
            }

        # Загружаем manifest если существует
        manifest = None
        manifest_path = unit_path / "manifest.json"
        if manifest_path.exists():
            try:
                manifest = load_manifest(unit_path)
                # Используем protocol_date и protocol_id из manifest если они не предоставлены
                if not protocol_date:
                    protocol_date = manifest.get("protocol_date")
                if not protocol_id:
                    protocol_id = manifest.get("protocol_id")
            except Exception as e:
                logger.warning(f"Failed to load manifest for {unit_id}: {e}")

        # Классифицируем каждый файл
        file_classifications = []
        categories = []
        classifications_by_file = []
        manifest_files = []

        for file_path in files:
            classification = self._classify_file(file_path)
            file_classifications.append(
                {
                    "file_path": str(file_path),
                    "classification": classification,
                }
            )
            classifications_by_file.append(classification)
            categories.append(classification["category"])
            
            # Подготавливаем информацию для manifest/route
            detection = detect_file_type(file_path)
            manifest_files.append({
                "original_name": file_path.name,
                "current_name": file_path.name,
                "mime_type": classification.get("mime_type", detection.get("mime_type", "")),
                "detected_type": classification.get("detected_type", "unknown"),
                "needs_ocr": detection.get("needs_ocr", False),
                "transformations": [],
            })

        # Определяем категорию UNIT
        category_counts = Counter(categories)
        unique_categories = set(categories)
        
        # Проверяем mixed по категориям обработки
        is_mixed_by_category = len(unique_categories) > 1
        
        # Проверяем mixed по типам файлов (даже если категории одинаковые)
        detected_types = [fc.get("detected_type", "unknown") for fc in classifications_by_file]
        unique_types = set(detected_types)
        is_mixed_by_type = len(unique_types) > 1
        
        # UNIT считается mixed, если файлы имеют разные категории или типы
        is_mixed = is_mixed_by_category or is_mixed_by_type

        # Определяем доминирующую категорию
        if is_mixed:
            unit_category = "mixed"
        elif categories:
            unit_category = categories[0]
        else:
            unit_category = "unknown"

        # Предварительно вычисляем route для обновления старых манифестов
        current_route = _determine_route_from_files(manifest_files)

        # Определяем расширение для сортировки на основе первой классификации
        extension = None
        if classifications_by_file and files:
            first_classification = classifications_by_file[0]
            first_file = files[0]
            original_ext = first_file.suffix.lower()
            extension = get_extension_subdirectory(
                category=unit_category,
                classification=first_classification,
                original_extension=original_ext,
            )
        # Fallback: определяем расширение из файлов
        if not extension and files:
            extension = files[0].suffix.lower().lstrip(".")
        if not extension:
            extension = determine_unit_extension(unit_path)

        # Определяем целевую директорию на основе категории
        target_base_dir = self._get_target_directory_base(unit_category, cycle, protocol_date)
        
        # Обрабатываем случай direct в циклах 2-3 (UNIT уже обработан, готов к merge)
        # NOTE: Ready2Docling - это отдельный этап (merge2docling), здесь units идут в Merge
        if unit_category == "direct" and cycle > 1:
            # UNIT уже обработан и готов к merge - переводим в MERGED_PROCESSED
            # Direct файлы ВСЕГДА идут в Merge/Direct/ (единственная директория Direct в Merge)
            from ..core.config import get_data_paths
            data_paths = get_data_paths(protocol_date)
            target_base_dir = data_paths["merge"] / "Direct"

            target_dir = move_unit_to_target(
                unit_dir=unit_path,
                target_base_dir=target_base_dir,
                extension=extension,
                dry_run=dry_run,
                copy_mode=copy_mode,
            )

            if not dry_run:
                self._update_manifest_route(target_dir, current_route)

                # Определяем состояние: Cycle 2+: MERGED_PROCESSED
                new_state = UnitState.MERGED_PROCESSED

                update_unit_state(
                    unit_path=target_dir,
                    new_state=new_state,
                    cycle=cycle,
                    operation={
                        "type": "classify",
                        "status": "success",
                        "category": unit_category,
                        "file_count": len(files),
                    },
                )
            else:
                new_state = UnitState.MERGED_PROCESSED

            self.audit_logger.log_event(
                unit_id=unit_id,
                event_type="operation",
                operation="classify",
                details={
                    "cycle": cycle,
                    "category": unit_category,
                    "is_mixed": False,
                    "file_count": len(files),
                    "target_directory": str(target_dir),
                },
                state_before=manifest.get("state_machine", {}).get("current_state") if manifest else "CLASSIFIED_2",
                state_after=new_state.value,
                unit_path=target_dir,
            )

            return {
                "category": unit_category,
                "unit_category": unit_category,
                "is_mixed": False,
                "file_classifications": classifications_by_file,
                "target_directory": str(target_dir),
                "moved_to": str(target_dir),
            }

        # Создаем manifest если его нет
        if not manifest:
            manifest = create_unit_manifest_if_needed(
                unit_path=unit_path,
                unit_id=unit_id,
                protocol_id=protocol_id,
                protocol_date=protocol_date,
                files=manifest_files,
                cycle=cycle,
            )
        else:
            # Обогащаем существующий манифест метаданными файлов (ВАЖНО для Mixed Units)
            manifest["files_metadata"] = {
                f.get("original_name", ""): {
                    "detected_type": f.get("detected_type", "unknown"),
                    "needs_ocr": f.get("needs_ocr", False),
                    "mime_type": f.get("mime_detected", f.get("mime_type", "unknown")),
                    "pages_or_parts": f.get("pages_or_parts", 1),
                }
                for f in manifest_files
            }
            
            # Обновляем route в существующем манифесте
            if "processing" not in manifest:
                manifest["processing"] = {}
            manifest["processing"]["route"] = current_route
            
            # Сохраняем обновленный манифест перед перемещением
            if not dry_run:
                save_manifest(unit_path, manifest)

        # Перемещаем UNIT в целевую директорию (с учетом расширения)
        if unit_category == "direct" and cycle == 1:
            # Direct файлы идут НАПРЯМУЮ в Merge/Direct/ (без Processing)
            target_dir = move_unit_to_target(
                unit_dir=unit_path,
                target_base_dir=target_base_dir,
                extension=extension,
                dry_run=dry_run,
                copy_mode=copy_mode,
            )
            # Обновляем state сразу на MERGED_DIRECT
            if not dry_run:
                self._update_manifest_route(target_dir, current_route)

                update_unit_state(
                    unit_path=target_dir,
                    new_state=UnitState.MERGED_DIRECT,
                    cycle=cycle,
                    operation={
                        "type": "classify",
                        "category": unit_category,
                        "direct_to_merge_0": True,
                        "file_count": len(files),
                    },
                )
                new_state = UnitState.MERGED_DIRECT
            else:
                new_state = UnitState.MERGED_DIRECT
        elif unit_category in ["special", "unknown"]:
            # Для special и unknown используем subcategory как поддиректорию
            if unit_category == "unknown":
                # Unknown файлы идут в Ambiguous
                subcategory = "Ambiguous"
            else:
                subcategory = "Special"
            
            # Проверяем, есть ли ambiguous файлы (для special)
            if unit_category != "unknown":
                # Проверяем, есть ли ambiguous файлы (по scenario или по classification из Decision Engine)
                has_ambiguous = any(
                    (fc.get("classification", {}).get("scenario") and 
                     "ambiguous" in str(fc.get("classification", {}).get("scenario", "")).lower()) or
                    (fc.get("classification", {}).get("category") == "special" and 
                     fc.get("classification", {}).get("scenario"))
                    for fc in file_classifications
                )
                
                # Если есть ambiguous файлы, идем в Ambiguous
                if has_ambiguous:
                    subcategory = "Ambiguous"
                elif unit_category == "special":
                    subcategory = "Special"  # Все special (не ambiguous) идут в Special
            target_dir = move_unit_to_target(
                unit_dir=unit_path,
                target_base_dir=target_base_dir / subcategory,
                extension=None,  # Exceptions не сортируются по расширениям
                dry_run=dry_run,
                copy_mode=copy_mode,
            )
            # Для exceptions (special, ambiguous, unknown, empty) используем EXCEPTION_N состояния
            exception_state_map = {
                1: UnitState.EXCEPTION_1,
                2: UnitState.EXCEPTION_2,
                3: UnitState.EXCEPTION_3,
            }
            new_state = exception_state_map.get(cycle, UnitState.EXCEPTION_1)
            
            # Проверяем текущее состояние перед обновлением
            manifest_path = target_dir / "manifest.json"
            if manifest_path.exists():
                try:
                    manifest = load_manifest(target_dir)
                    state_machine = UnitStateMachine(unit_id, manifest_path)
                    current_state = state_machine.get_current_state()
                    
                    # Если UNIT уже в нужном состоянии для exceptions, не обновляем
                    if current_state == new_state:
                        # UNIT уже в правильном состоянии для exceptions - не обновляем
                        should_update_state = False
                    else:
                        should_update_state = True
                except (json.JSONDecodeError, FileNotFoundError, KeyError, ValueError) as e:
                    # Если не удалось загрузить manifest или state machine, обновляем состояние
                    logger.debug(f"Could not load manifest for {unit_id}: {e}")
                    should_update_state = True
            else:
                # Нет manifest - обновляем состояние
                should_update_state = True
            
            # Обновляем state machine (если не dry_run и состояние изменилось)
            if not dry_run and should_update_state:
                self._update_manifest_route(target_dir, current_route)

                update_unit_state(
                    unit_path=target_dir,
                    new_state=new_state,
                    cycle=cycle,
                    operation={
                        "type": "classify",
                        "category": unit_category,
                        "is_mixed": is_mixed,
                        "file_count": len(files),
                    },
                )
        elif unit_category == "mixed":
            # Для mixed юнитов выбираем приоритетную категорию обработки
            # Приоритет: extract > convert > normalize > direct
            priority_order = ["extract", "convert", "normalize", "direct"]
            chosen_category = "direct"
            
            # Проверяем наличие категорий в файлах
            file_cats = {fc["category"] for fc in classifications_by_file}
            for cat in priority_order:
                if cat in file_cats:
                    chosen_category = cat
                    break
            
            # Определяем целевую базу для выбранной категории
            target_base_dir = self._get_target_directory_base(chosen_category, cycle, protocol_date)
            
            # Если это direct в циклах 2-3, обрабатываем отдельно (уже реализовано выше для unit_category == "direct")
            # Но для простоты в mixed мы просто направляем в соответствующую директорию

            target_dir = move_unit_to_target(
                unit_dir=unit_path,
                target_base_dir=target_base_dir,
                extension="Mixed",  # ИСПРАВЛЕНИЕ: Mixed units всегда идут в /Mixed/ поддиректорию
                dry_run=dry_run,
                copy_mode=copy_mode,
            )

            # Определяем новое состояние на основе выбранной категории
            if cycle == 1:
                if chosen_category == "direct":
                    new_state = UnitState.MERGED_DIRECT
                else:
                    new_state = UnitState.CLASSIFIED_1
            elif cycle == 2:
                # В цикле 2 mixed может идти либо в CLASSIFIED_2 (если требует еще обработки),
                # либо в MERGED_PROCESSED (если это финальная стадия)
                # По умолчанию - CLASSIFIED_2, если это convert/extract/normalize
                if chosen_category in ["convert", "extract", "normalize"]:
                    new_state = UnitState.CLASSIFIED_2
                else:
                    new_state = UnitState.MERGED_PROCESSED
            else:
                new_state = UnitState.MERGED_PROCESSED
                
            if not dry_run:
                self._update_manifest_route(target_dir, current_route)
                
                update_unit_state(
                    unit_path=target_dir,
                    new_state=new_state,
                    cycle=cycle,
                    operation={
                        "type": "classify",
                        "status": "success",
                        "category": "mixed",
                        "chosen_route_category": chosen_category,
                        "is_mixed": True,
                        "file_count": len(files),
                    },
                )
        else:
            # Для остальных категорий (convert, extract, normalize) сортируем по расширению
            target_dir = move_unit_to_target(
                unit_dir=unit_path,
                target_base_dir=target_base_dir,
                extension=extension,
                dry_run=dry_run,
                copy_mode=copy_mode,
            )
            # Определяем новое состояние на основе цикла и текущего состояния
            # Проверяем текущее состояние из manifest
            manifest_path = target_dir / "manifest.json"
            from ..core.state_machine import UnitStateMachine
            state_machine = UnitStateMachine(unit_id, manifest_path)
            current_state = state_machine.get_current_state()
            
            # Если UNIT уже в CLASSIFIED_2 и приходит из Merge (обработан), переводим в MERGED_PROCESSED
            # Если UNIT в CLASSIFIED_2 и требует дальнейшей обработки, переводим в PENDING_*
            if current_state == UnitState.CLASSIFIED_2:
                # UNIT уже обработан, проверяем категорию
                if unit_category == "direct":
                    # Готов к merge - переводим в MERGED_PROCESSED
                    new_state = UnitState.MERGED_PROCESSED
                elif unit_category in ["convert", "extract", "normalize"]:
                    # Требует дальнейшей обработки - переводим в PENDING_*
                    pending_map = {
                        "convert": UnitState.PENDING_CONVERT,
                        "extract": UnitState.PENDING_EXTRACT,
                        "normalize": UnitState.PENDING_NORMALIZE,
                    }
                    new_state = pending_map.get(unit_category, UnitState.MERGED_PROCESSED)
                else:
                    # Для mixed, unknown, special - переводим в MERGED_PROCESSED или EXCEPTION
                    new_state = UnitState.MERGED_PROCESSED
            elif current_state == UnitState.CLASSIFIED_3:
                # UNIT уже в CLASSIFIED_3 - переводим в MERGED_PROCESSED
                new_state = UnitState.MERGED_PROCESSED
            elif unit_category == "direct" and cycle > 1:
                # Direct категория в циклах 2-3 (из обработанных UNIT) - переводим в MERGED_PROCESSED
                new_state = UnitState.MERGED_PROCESSED
            elif cycle == 3 and current_state in [UnitState.CLASSIFIED_2, UnitState.MERGED_PROCESSED]:
                # Для цикла 3, если UNIT уже в CLASSIFIED_2 или MERGED_PROCESSED, переводим в MERGED_PROCESSED
                new_state = UnitState.MERGED_PROCESSED
            else:
                # Для других состояний используем стандартную логику
                new_state_map = {
                    1: UnitState.CLASSIFIED_1,
                    2: UnitState.CLASSIFIED_2,
                    3: UnitState.MERGED_PROCESSED,  # Для цикла 3 переходим сразу в MERGED_PROCESSED
                }
                new_state = new_state_map.get(cycle, UnitState.CLASSIFIED_1)
            
            # Обновляем state machine (если не dry_run)
            if not dry_run:
                self._update_manifest_route(target_dir, current_route)

                update_unit_state(
                    unit_path=target_dir,
                    new_state=new_state,
                    cycle=cycle,
                    operation={
                        "type": "classify",
                        "category": unit_category,
                        "is_mixed": is_mixed,
                        "file_count": len(files),
                    },
                )

        # Логируем классификацию
        self.audit_logger.log_event(
            unit_id=unit_id,
            event_type="operation",
            operation="classify",
            details={
                "cycle": cycle,
                "category": unit_category,
                "is_mixed": is_mixed,
                "file_count": len(files),
                "category_distribution": dict(category_counts),
                "extension": extension,
                "target_directory": str(target_dir),
            },
            state_before=manifest.get("state_machine", {}).get("current_state") if manifest else "RAW",
            state_after=new_state.value,
            unit_path=target_dir,
        )

        return {
            "category": unit_category,
            "unit_category": unit_category,
            "is_mixed": is_mixed,
            "file_classifications": file_classifications,
            "target_directory": str(target_base_dir),
            "moved_to": str(target_dir),
            "category_distribution": dict(category_counts),
            "extension": extension,
        }

    def _classify_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Классифицирует отдельный файл.

        Использует результат Decision Engine для определения категории.

        Args:
            file_path: Путь к файлу

        Returns:
            Словарь с классификацией:
            - category: категория (direct, convert, extract, normalize, special)
            - detected_type: определенный тип файла
            - needs_conversion: требуется ли конвертация
            - needs_extraction: требуется ли разархивация
            - needs_normalization: требуется ли нормализация
            - correct_extension: правильное расширение (если нужна нормализация)
        """
        extension = file_path.suffix.lower()
        detection = detect_file_type(file_path)

        classification = {
            "category": "unknown",
            "detected_type": detection.get("detected_type", "unknown"),
            "mime_type": detection.get("mime_type", ""),
            "original_extension": extension,  # Сохраняем исходное расширение для сортировки
            "needs_conversion": False,
            "needs_extraction": False,
            "needs_normalization": False,
            "extension_matches_content": detection.get("extension_matches_content", True),
            "correct_extension": detection.get("correct_extension"),
        }

        # Проверка на подписи
        if extension in self.SIGNATURE_EXTENSIONS:
            classification["category"] = "special"
            return classification

        # Проверка на неподдерживаемые форматы
        if extension in self.UNSUPPORTED_EXTENSIONS:
            classification["category"] = "special"
            return classification

        # Проверка на архивы (проверяем расширение и detected_type)
        archive_extensions = {".zip", ".rar", ".7z"}
        archive_types = ["zip_archive", "rar_archive", "7z_archive"]
        
        if (extension in archive_extensions or 
            detection.get("is_archive") or 
            detection.get("detected_type") in archive_types):
            classification["category"] = "extract"
            classification["needs_extraction"] = True
            return classification

        # ВАЖНО: Проверка на необходимость конвертации ДО использования classification из Decision Engine
        # Это нужно, чтобы .doc, .xls, .ppt файлы всегда попадали в convert, а не в normalize
        detected_type = detection.get("detected_type")
        
        # Проверяем расширение файла для старых Office форматов
        # Если расширение .doc, .xls, .ppt - это всегда convert, независимо от Decision Engine
        if extension in [".doc", ".xls", ".ppt", ".rtf"]:
            # Проверяем, что это действительно старый Office формат
            if detected_type in self.CONVERTIBLE_TYPES or detection.get("requires_conversion", False):
                classification["category"] = "convert"
                classification["needs_conversion"] = True
                return classification
        
        # Проверка на необходимость конвертации по detected_type
        if detected_type in self.CONVERTIBLE_TYPES:
            classification["category"] = "convert"
            classification["needs_conversion"] = True
            return classification

        # Используем classification из Decision Engine
        decision_classification = detection.get("classification")

        # ВАЖНО: Если Decision Engine вернул "normalize" для .doc, .xls, .ppt файлов,
        # это может быть ошибка - такие файлы должны идти в convert
        if decision_classification == "normalize":
            # Проверяем расширение - если это старый Office формат, это convert, а не normalize
            if extension in [".doc", ".xls", ".ppt", ".rtf"]:
                # Это старый Office формат - должен быть convert
                classification["category"] = "convert"
                classification["needs_conversion"] = True
                return classification
            
            # Для других файлов используем normalize
            classification["category"] = "normalize"
            classification["needs_normalization"] = True
            classification["correct_extension"] = detection.get("correct_extension")
            return classification

        if decision_classification == "ambiguous":
            classification["category"] = "special"  # Ambiguous → Exceptions
            # Сохраняем scenario для проверки ambiguous
            classification["scenario"] = detection.get("scenario", "ambiguous")
            return classification

        # Если Decision Engine вернул "unknown", оставляем как unknown
        if decision_classification == "unknown":
            classification["category"] = "unknown"  # Unknown → Exceptions/Ambiguous
            return classification

        # Если Decision Engine вернул "direct", обрабатываем как direct
        if decision_classification == "direct":
            classification["category"] = "direct"
            return classification

        # Fallback: если ничего не определено, проверяем detected_type
        if detected_type and detected_type != "unknown":
            # Если тип определен, но Decision Engine не дал классификацию, 
            # проверяем, является ли это поддерживаемым форматом
            if detected_type in ["pdf", "docx", "xlsx", "pptx"]:
                classification["category"] = "direct"
            else:
                classification["category"] = "unknown"
        else:
            # Если тип не определен, это unknown
            classification["category"] = "unknown"
        
        return classification

    def _get_target_directory_base(
        self, category: str, cycle: int, protocol_date: Optional[str] = None
    ) -> Path:
        """
        Определяет базовую целевую директорию для UNIT на основе категории.

        Расширение будет добавлено позже через move_unit_to_target.
        NOTE: Ready2Docling - это отдельный этап (merge2docling).

        Args:
            category: Категория UNIT
            cycle: Номер цикла
            protocol_date: Дата протокола для организации по датам (опционально)

        Returns:
            Базовая целевая директория (без учета расширения)
        """
        # Если указана дата, получаем пути внутри Data/date/
        if protocol_date:
            data_paths = get_data_paths(protocol_date)
        else:
            # Без даты используем стандартные пути
            data_paths = get_data_paths()

        # Определяем базовую директорию в зависимости от категории
        # СТРУКТУРА:
        # - Exceptions/Direct/ - для исключений до обработки (цикл 1)
        # - Exceptions/Processed_N/ - для исключений после обработки (цикл N)
        # - Merge/Direct/ - для ВСЕХ direct файлов готовых к Docling (все циклы)
        # - Merge/Processed_N/ - для обработанных units (Converted, Extracted, Normalized, Mixed)

        if category in ["special", "unknown", "empty"]:
            # Exceptions находится внутри директории с датой
            exceptions_base = data_paths["exceptions"]
            if cycle == 1:
                # Исключения до обработки идут в Exceptions/Direct/
                return exceptions_base / "Direct"
            else:
                # Исключения после обработки идут в Exceptions/Processed_N/
                return exceptions_base / f"Processed_{cycle}"
        elif category == "direct":
            merge_base = data_paths["merge"]
            # Direct файлы ВСЕГДА идут в Merge/Direct/ независимо от цикла
            # Это единственная директория Direct в ветке Merge (как в Exceptions)
            return merge_base / "Direct"
        else:
            # Processing категории (convert, extract, normalize)
            processing_base = data_paths["processing"]
            processing_paths = get_processing_paths(cycle, processing_base)

            category_mapping = {
                "convert": processing_paths["Convert"],
                "extract": processing_paths["Extract"],
                "normalize": processing_paths["Normalize"],
            }

            return category_mapping.get(category, processing_paths["Convert"])


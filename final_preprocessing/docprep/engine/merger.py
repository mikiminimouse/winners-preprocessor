"""
Merger - объединение UNIT из Merge_1, Merge_2, Merge_3 в Ready2Docling.

Сборка финальных UNIT с дедупликацией и сортировкой по расширениям.
"""
import shutil
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from ..core.manifest import load_manifest, save_manifest, update_manifest_operation
from ..core.audit import get_audit_logger
from ..core.unit_processor import move_unit_to_target, update_unit_state
from ..core.state_machine import UnitState
from ..core.contract import generate_contract_from_manifest, save_contract
from ..utils.file_ops import detect_file_type

logger = logging.getLogger(__name__)


class Merger:
    """Объединитель UNIT для финальной сборки."""

    def __init__(self):
        """Инициализирует Merger."""
        self.audit_logger = get_audit_logger()

    def _move_skipped_unit(self, unit_id: str, source_path: Path, exceptions_base: Path, reason: str, cycle: int):
        """
        Перемещает UNIT в директорию исключений с указанием причины.
        """
        target_base_dir = exceptions_base / reason / f"Cycle_{cycle}"
        try:
            target_path = move_unit_to_target(source_path, target_base_dir)
            logger.info(f"Unit {unit_id} moved to Exceptions/{reason} due to: {reason}")
            # Обновляем манифест, если он существует
            manifest_path = target_path / "manifest.json"
            if manifest_path.exists():
                update_unit_state(
                    unit_path=target_path,
                    new_state=UnitState.MERGER_SKIPPED,
                    cycle=cycle,
                    operation={
                        "type": "merger_skip",
                        "reason": reason,
                    },
                    final_cluster=f"Exceptions/{reason}",
                    final_reason=f"Skipped by Merger: {reason}",
                )
        except Exception as e:
            logger.error(f"Failed to move unit {unit_id} to Exceptions/{reason}: {e}")

    def collect_units(
        self,
        source_dirs: List[Path],
        target_dir: Path,
        cycle: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Собирает UNIT из нескольких источников в целевую директорию.

        Args:
            source_dirs: Список директорий источников (Merge_0/Direct, Merge_1, Merge_2, Merge_3)
            target_dir: Целевая директория (Ready2Docling)
            cycle: Номер цикла (опционально, для фильтрации)

        Returns:
            Словарь с результатами объединения
        """
        correlation_id = self.audit_logger.get_correlation_id()

        # Собираем все UNIT из источников
        all_units = {}  # unit_id -> {source, files, cycle, source_path}

        for source_dir in source_dirs:
            if not source_dir.exists():
                continue

            # Специальная обработка для Merge_0/Direct
            merge_0_direct = source_dir / "Direct"
            if "Merge_0" in str(source_dir) and merge_0_direct.exists():
                # Обрабатываем Direct файлы из Merge_0
                for unit_dir in merge_0_direct.rglob("UNIT_*"):
                    if unit_dir.is_dir():
                        self._process_unit_dir(unit_dir, source_dir.name, all_units)
            else:
                # Обычная обработка для других директорий
                for unit_dir in source_dir.rglob("UNIT_*"):
                    if unit_dir.is_dir():
                        self._process_unit_dir(unit_dir, source_dir.name, all_units)

        # Определяем Exceptions base
        exceptions_base = target_dir.parent / "Exceptions"
        current_cycle = cycle or 1

        # Обрабатываем каждый UNIT
        processed_units = []
        errors = []

        for unit_id, unit_info in all_units.items():
            try:
                # Определяем категорию для сортировки
                files = unit_info["files"]
                if not files:
                    # Пропускаем пустые UNIT - они должны быть в Exceptions/Empty (уже там или остаются в Processing)
                    self._move_skipped_unit(unit_id, unit_info["source_path"], exceptions_base, "Empty", current_cycle)
                    continue

                # Проверка: файлы не пустые и прошли соответствующие этапы обработки
                valid_files = []
                for file_path in files:
                    if file_path.exists() and file_path.stat().st_size > 0:
                        valid_files.append(file_path)
                
                if not valid_files:
                    # Все файлы пустые - перемещаем в Exceptions/Empty
                    self._move_skipped_unit(unit_id, unit_info["source_path"], exceptions_base, "Empty", current_cycle)
                    continue
                
                files = valid_files

                # Определяем тип файла (берем первый или доминирующий)
                file_types = {}
                for file_path in files:
                    detection = detect_file_type(file_path)
                    file_type = detection.get("detected_type", "unknown")
                    
                    # Если detected_type unknown, проверяем расширение файла
                    if file_type == "unknown":
                        file_ext = file_path.suffix.lower().lstrip(".")
                        file_name_lower = file_path.name.lower()
                        
                        # Проверяем PDF по расширению (включая неправильные расширения)
                        if file_ext == "pdf" or file_name_lower.endswith("pdf") or file_name_lower.endswith(".pdf"):
                            file_type = "pdf"
                        # Проверяем другие типы по расширению
                        elif file_ext in ["docx", "doc", "xlsx", "xls", "pptx", "ppt", "rtf", "xml", "jpg", "jpeg", "png"]:
                            file_type = file_ext
                    
                    file_types[file_type] = file_types.get(file_type, 0) + 1

                # Определяем доминирующий тип
                if file_types:
                    dominant_type = max(file_types.items(), key=lambda x: x[1])[0]
                else:
                    dominant_type = "unknown"
                
                # Дополнительная проверка: если dominant_type unknown, но есть PDF файлы по расширению
                if dominant_type == "unknown":
                    pdf_count = 0
                    for file_path in files:
                        file_ext = file_path.suffix.lower().lstrip(".")
                        file_name_lower = file_path.name.lower()
                        if file_ext == "pdf" or file_name_lower.endswith("pdf") or file_name_lower.endswith(".pdf"):
                            pdf_count += 1
                    if pdf_count > 0:
                        dominant_type = "pdf"
                
                # Проверка: UNIT должен быть корректно обработан
                manifest = unit_info.get("manifest")
                if manifest:
                    processing_info = manifest.get("processing", {})
                    # Проверяем, что UNIT прошел классификацию
                    state = manifest.get("state_machine", {}).get("current_state", "")
                    if state not in ["MERGED_DIRECT", "MERGED_PROCESSED", "CLASSIFIED_1", "CLASSIFIED_2", "CLASSIFIED_3"]:
                        # UNIT не прошел необходимые этапы обработки - пропускаем
                        continue
                    
                    # Дополнительная проверка по расширениям файлов
                    # ВАЖНО: Если архив был успешно извлечен, проверяем только извлеченный контент
                    archive_extensions = {".zip", ".rar", ".7z", ".tar", ".gz"}
                    unsupported_extensions = {".exe", ".dll", ".bin", ".msi", ".bat", ".cmd", ".sh"}
                    
                    # Проверяем, был ли архив успешно извлечен
                    extraction_successful = any(
                        op.get("type") == "extract" and op.get("status") == "success"
                        for op in processing_info.get("operations", [])
                    ) or any(
                        t.get("type") == "extract" and t.get("status") == "success"
                        for f in manifest.get("files", [])
                        for t in f.get("transformations", [])
                    )
                    
                    # Определяем какие файлы проверять
                    files_to_check = []
                    for f in files:
                        is_archive = f.suffix.lower() in archive_extensions
                        # Если архив был извлечен, пропускаем исходные архивы
                        if is_archive and extraction_successful:
                            continue
                        # Пропускаем извлеченные директории
                        if f.is_dir() and "_extracted" in f.name:
                            continue
                        files_to_check.append(f)
                    
                    # Если после извлечения есть только архивы — проверяем извлеченный контент
                    if not files_to_check and extraction_successful:
                        # Ищем извлеченные файлы в поддиректориях *_extracted
                        extracted_dirs = [f for f in files if f.is_dir() and "_extracted" in f.name]
                        for extracted_dir in extracted_dirs:
                            if extracted_dir.exists():
                                files_to_check.extend([f for f in extracted_dir.iterdir() if f.is_file()])
                    
                    # Теперь проверяем только реальный контент
                    if any(f.suffix.lower() in unsupported_extensions for f in files_to_check):
                        logger.warning(
                            f"Unit {unit_id} contains files with unsupported extensions for Docling. "
                            f"Moving to Exceptions/UnsupportedExtension."
                        )
                        self._move_skipped_unit(unit_id, unit_info["source_path"], exceptions_base, "UnsupportedExtension", current_cycle)
                        continue
                    
                    # Проверяем операции обработки

                    operations = processing_info.get("operations", [])
                    # Для файлов, требующих конвертации, проверяем наличие операции convert
                    if dominant_type in ["doc", "xls", "ppt", "rtf"]:
                        has_convert = any(op.get("type") == "convert" for op in operations)
                        if not has_convert:
                            # Файл требует конвертации, но операция не выполнена
                            self._move_skipped_unit(unit_id, unit_info["source_path"], exceptions_base, "FailedConversion", current_cycle)
                            continue
                    
                    # Для архивов проверяем наличие операции extract
                    if dominant_type in ["zip_archive", "rar_archive", "7z_archive"]:
                        has_extract = any(op.get("type") == "extract" for op in operations)
                        if not has_extract:
                            # Архив требует извлечения, но операция не выполнена - пропускаем
                            continue
                        # ВАЖНО: Даже если архив был извлечен, Docling не поддерживает архивы напрямую
                        # Архивы должны быть извлечены на этапе preprocessing
                        # Если в UNIT остался архивный файл - это ошибка preprocessing
                        logger.warning(
                            f"Unit {unit_id} contains archive file after extraction - "
                            f"moving to Exceptions/ArchiveIncluded."
                        )
                        self._move_skipped_unit(unit_id, unit_info["source_path"], exceptions_base, "ArchiveIncluded", current_cycle)
                        continue
                    
                    # Фильтрация форматов, неподдерживаемых Docling
                    # Docling поддерживает: PDF, DOCX, XLSX, PPTX, HTML, XML, изображения (через OCR)
                    # Не поддерживает: ZIP, RAR, 7Z, EXE, и другие бинарные форматы
                    docling_unsupported_types = [
                        "zip_archive", "rar_archive", "7z_archive",
                        "exe", "dll", "bin",
                    ]
                    # ВАЖНО: Проверка unsupported_extensions уже выполнена выше с учетом извлеченного контента
                    # Проверяем только dominant_type для архивов, которые НЕ были извлечены
                    if dominant_type in docling_unsupported_types and not extraction_successful:
                        logger.warning(
                            f"Unit {unit_id} has unsupported file type '{dominant_type}' for Docling. "
                            f"Moving to Exceptions/UnsupportedType."
                        )
                        self._move_skipped_unit(unit_id, unit_info["source_path"], exceptions_base, "UnsupportedType", current_cycle)
                        continue

                # Определяем целевую директорию с сортировкой по расширению
                target_subdir = self._get_target_subdir(
                    dominant_type, files, target_dir, unit_info.get("manifest")
                )

                # Создаем директорию UNIT
                target_unit_dir = target_subdir / unit_id
                target_unit_dir.mkdir(parents=True, exist_ok=True)

                # Копируем файлы напрямую в UNIT директорию (без поддиректории files)
                copied_files = []
                for file_path in files:
                    target_file = target_unit_dir / file_path.name
                    # Избегаем перезаписи существующих файлов
                    if not target_file.exists():
                        shutil.copy2(file_path, target_file)
                    copied_files.append(str(target_file))

                # Копируем manifest если есть
                if unit_info["manifest"]:
                    manifest = unit_info["manifest"]
                    # Обновляем состояние на READY_FOR_DOCLING
                    manifest["processing"]["final_cluster"] = unit_info["source"]
                    manifest["state_machine"]["current_state"] = "READY_FOR_DOCLING"
                    manifest["state_machine"]["final_state"] = "READY_FOR_DOCLING"
                    if "READY_FOR_DOCLING" not in manifest["state_machine"]["state_trace"]:
                        manifest["state_machine"]["state_trace"].append("READY_FOR_DOCLING")

                    save_manifest(target_unit_dir, manifest)
                    
                    # Генерируем docprep.contract.json для Docling
                    # ВАЖНО: Docling использует ТОЛЬКО contract, manifest.json не используется как вход
                    try:
                        # Определяем главный файл для контракта
                        main_file_for_contract = None
                        for file_path_str in copied_files:
                            file_path_obj = Path(file_path_str)
                            # Используем первый скопированный файл как главный
                            if file_path_obj.exists():
                                main_file_for_contract = file_path_obj
                                break
                        
                        if main_file_for_contract:
                            contract = generate_contract_from_manifest(
                                unit_path=target_unit_dir,
                                manifest=manifest,
                                main_file_path=main_file_for_contract,
                            )
                            save_contract(target_unit_dir, contract)
                            logger.info(f"Generated docprep.contract.json for unit {unit_id}")
                        else:
                            logger.warning(f"No main file found for contract generation in unit {unit_id}")
                    except Exception as e:
                        # Ошибка генерации контракта критична - без контракта Docling не сможет обработать UNIT
                        logger.error(f"CRITICAL: Failed to generate contract for unit {unit_id}: {e}")
                        # Продолжаем, но это должно быть исправлено

                processed_units.append(
                    {
                        "unit_id": unit_id,
                        "source": unit_info["source"],
                        "files_count": len(copied_files),
                        "target_dir": str(target_unit_dir),
                        "file_type": dominant_type,
                    }
                )

                # Логируем операцию
                self.audit_logger.log_event(
                    unit_id=unit_id,
                    event_type="operation",
                    operation="merge",
                    details={
                        "source": unit_info["source"],
                        "files_count": len(copied_files),
                        "target_dir": str(target_unit_dir),
                    },
                    state_before="MERGED",
                    state_after="READY_FOR_DOCLING",
                    unit_path=target_unit_dir,
                )

            except Exception as e:
                errors.append({"unit_id": unit_id, "error": str(e)})

        return {
            "units_processed": len(processed_units),
            "processed_units": processed_units,
            "errors": errors,
        }

    def _process_unit_dir(self, unit_dir: Path, source_name: str, all_units: dict):
        """Обрабатывает директорию UNIT и добавляет её в коллекцию."""
        unit_id = unit_dir.name
        # Приоритет более поздним циклам
        if unit_id in all_units:
            # Если UNIT уже есть, проверяем, не является ли новый источник более приоритетным
            # В списке source_dirs порядок: Merge_0, Merge_1, Merge_2, Merge_3
            # Поэтому каждый следующий источник более приоритетен
            all_units[unit_id]["files"] = []  # Очищаем старые файлы
            all_units[unit_id]["manifest"] = None # Сбросим манифест для загрузки нового
            all_units[unit_id]["source"] = source_name
            all_units[unit_id]["source_path"] = unit_dir
        else:
            all_units[unit_id] = {
                "source": source_name,
                "files": [],
                "manifest": None,
                "source_path": unit_dir,
            }

        # Рекурсивный поиск файлов
        files = [
            f
            for f in unit_dir.rglob("*")
            if f.is_file()
            and f.name not in ["manifest.json", "audit.log.jsonl", "metadata.json"]
        ]
        
        # Фильтрация файлов - исключаем служебные и временные файлы
        filtered_files = []
        for file_path in files:
            # Пропускаем файлы в скрытых директориях
            if any(part.startswith('.') for part in file_path.parts):
                continue
            # Пропускаем временные файлы
            if file_path.name.startswith('~') or file_path.name.startswith('.'):
                continue
            filtered_files.append(file_path)
        
        all_units[unit_id]["files"].extend(filtered_files)

        # Загружаем manifest
        manifest_path = unit_dir / "manifest.json"
        if manifest_path.exists() and all_units[unit_id]["manifest"] is None:
            try:
                all_units[unit_id]["manifest"] = load_manifest(unit_dir)
            except Exception:
                pass

    def _get_target_subdir(
        self, file_type: str, files: List[Path], base_dir: Path, manifest: Optional[Dict] = None
    ) -> Path:
        """
        Определяет целевую поддиректорию для UNIT на основе типа файлов.

        Для PDF дополнительно сортирует на scan/text на основе needs_ocr из manifest.

        Args:
            file_type: Тип файла
            files: Список файлов
            base_dir: Базовая директория Ready2Docling
            manifest: Manifest UNIT для получения needs_ocr и route

        Returns:
            Путь к целевой поддиректории
        """
        # 1. Пытаемся определить по route из manifest (самый надежный способ)
        if manifest:
            route = manifest.get("processing", {}).get("route")
            if route == "mixed":
                return base_dir / "mixed"
            if route:
                # Маппинг route на директории
                route_to_dir = {
                    "pdf_text": "pdf",
                    "pdf_scan": "pdf",
                    "pdf_scan_table": "pdf",
                    "docx": "docx",
                    "xlsx": "xlsx",
                    "pptx": "pptx",
                    "html": "html",
                    "xml": "xml",
                    "image_ocr": "image",
                    "rtf": "rtf",
                }
                
                # Специальная обработка для изображений (сортируем по расширению в подпапки image)
                if route == "image_ocr" and files:
                    ext = files[0].suffix.lower().lstrip(".")
                    if ext in ["jpg", "jpeg", "png", "tiff"]:
                        return base_dir / ext
                    return base_dir / "image"
                
                subdir_name = route_to_dir.get(route)
                if subdir_name:
                    # Для PDF добавляем проверку на scan/text если нужно (но route уже содержит это)
                    # Однако для обратной совместимости с существующей структурой папок:
                    if subdir_name == "pdf":
                        # Проверяем, есть ли scan в route
                        if "scan" in route:
                            return base_dir / "pdf" / "scan"
                        return base_dir / "pdf" / "text"
                    
                    return base_dir / subdir_name

        # 2. Fallback: Маппинг типов на директории
        # ВАЖНО: .doc файлы НИКОГДА не должны попадать в docx без предварительной конвертации
        type_to_dir = {
            "docx": "docx",
            # "doc": "docx",  # УДАЛЕНО: .doc файлы должны быть конвертированы, а не напрямую в docx
            "pdf": "pdf",
            "jpg": "jpg",
            "jpeg": "jpeg",
            "png": "png",
            "tiff": "tiff",
            "pptx": "pptx",
            "xlsx": "xlsx",
            "xml": "xml",
            "rtf": "rtf",
        }
        
        if file_type == "mixed":
            return base_dir / "mixed"

        subdir_name = type_to_dir.get(file_type, "other")
        
        # Если файл попал в "other", проверяем расширение напрямую
        if subdir_name == "other" and files:
            # Проверяем расширения файлов
            extensions = set()
            for file_path in files:
                ext = file_path.suffix.lower().lstrip(".")
                if ext:
                    extensions.add(ext)
            
            # Маппинг расширений на директории
            ext_to_dir = {
                "docx": "docx",
                "pdf": "pdf",
                "jpg": "jpg",
                "jpeg": "jpeg",
                "png": "png",
                "tiff": "tiff",
                "pptx": "pptx",
                "xlsx": "xlsx",
                "xml": "xml",
                "rtf": "rtf",
            }
            
            # Берем первое найденное расширение
            if extensions:
                first_ext = list(extensions)[0]
                # Проверяем, является ли это PDF
                is_pdf_by_ext = False
                for ext in extensions:
                    if ext == "pdf" or ext.endswith("pdf"):
                        is_pdf_by_ext = True
                        first_ext = "pdf"
                        break
                subdir_name = ext_to_dir.get(first_ext, "other")

        # 3. Для PDF (fallback логика)
        is_pdf_unit = False
        if file_type == "pdf":
            is_pdf_unit = True
        else:
            for file_path in files:
                file_ext = file_path.suffix.lower()
                if file_ext == ".pdf" or file_path.name.lower().endswith(".pdf"):
                    is_pdf_unit = True
                    break
        
        if is_pdf_unit:
            pdf_files_need_ocr = []
            pdf_files_has_text = []

            if manifest:
                file_infos = manifest.get("files", [])
                for file_info in file_infos:
                    # Проверяем как по detected_type, так и по расширению файла
                    detected_type = file_info.get("detected_type", "").lower()
                    original_name = file_info.get("original_name", "")
                    current_name = file_info.get("current_name", original_name)
                    
                    # Проверяем, является ли файл PDF (по типу или расширению)
                    is_pdf = (
                        detected_type == "pdf" or
                        original_name.lower().endswith(".pdf") or
                        current_name.lower().endswith(".pdf") or
                        original_name.lower().endswith("pdf") or  # Для случаев типа "гpdf"
                        current_name.lower().endswith("pdf")
                    )
                    
                    if is_pdf:
                        needs_ocr = file_info.get("needs_ocr")
                        if needs_ocr is not None:
                            pdf_files_need_ocr.append(needs_ocr)
                            pdf_files_has_text.append(not needs_ocr)
                        else:
                            # Fallback to detect_file_type if needs_ocr is not in manifest
                            # Ищем локальный файл для детекции
                            current_name = file_info.get("current_name", "")
                            file_path_in_unit = None
                            for f in files:
                                if f.name == current_name:
                                    file_path_in_unit = f
                                    break
                            
                            if file_path_in_unit and file_path_in_unit.exists():
                                try:
                                    detection = detect_file_type(file_path_in_unit)
                                    needs_ocr_detected = detection.get("needs_ocr", True)
                                    pdf_files_need_ocr.append(needs_ocr_detected)
                                    pdf_files_has_text.append(not needs_ocr_detected)
                                except Exception:
                                    pdf_files_need_ocr.append(True)
                                    pdf_files_has_text.append(False)
            
            # Если не нашли в manifest, проверяем файлы напрямую
            if not pdf_files_need_ocr:
                for file_path in files:
                    file_ext = file_path.suffix.lower()
                    file_name_lower = file_path.name.lower()
                    is_pdf_file = (
                        file_ext == ".pdf" or
                        file_name_lower.endswith(".pdf")
                    )
                    
                    if is_pdf_file:
                        try:
                            detection = detect_file_type(file_path)
                            needs_ocr_detected = detection.get("needs_ocr", True)
                            pdf_files_need_ocr.append(needs_ocr_detected)
                            pdf_files_has_text.append(not needs_ocr_detected)
                        except Exception:
                            pdf_files_need_ocr.append(True)
                            pdf_files_has_text.append(False)
            
            if pdf_files_need_ocr:
                all_need_ocr = all(pdf_files_need_ocr)
                all_has_text = all(pdf_files_has_text)

                if all_need_ocr:
                    subdir_name = "pdf/scan"
                elif all_has_text:
                    subdir_name = "pdf/text"
                else:
                    subdir_name = "pdf/mixed"
            else:
                subdir_name = "pdf/scan"
        
        return base_dir / subdir_name

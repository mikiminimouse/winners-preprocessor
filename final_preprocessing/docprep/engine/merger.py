"""
Merger - объединение UNIT из Merge_1, Merge_2, Merge_3 в Ready2Docling.

Сборка финальных UNIT с дедупликацией и сортировкой по расширениям.
"""
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional

from ..core.manifest import load_manifest, save_manifest
from ..core.audit import get_audit_logger
from ..utils.file_ops import detect_file_type


class Merger:
    """Объединитель UNIT для финальной сборки."""

    def __init__(self):
        """Инициализирует Merger."""
        self.audit_logger = get_audit_logger()

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
        all_units = {}  # unit_id -> {source, files, cycle}

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

        # Обрабатываем каждый UNIT
        processed_units = []
        errors = []

        for unit_id, unit_info in all_units.items():
            try:
                # Определяем категорию для сортировки
                files = unit_info["files"]
                if not files:
                    # Пропускаем пустые UNIT - они должны быть в Exceptions/Empty
                    continue

                # Проверка: файлы не пустые и прошли соответствующие этапы обработки
                valid_files = []
                for file_path in files:
                    if file_path.exists() and file_path.stat().st_size > 0:
                        valid_files.append(file_path)
                
                if not valid_files:
                    # Все файлы пустые - пропускаем
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
                    # Проверяем, что UNIT прошел классификацию
                    state = manifest.get("state_machine", {}).get("current_state", "")
                    if state not in ["MERGED_DIRECT", "MERGED_PROCESSED", "CLASSIFIED_2", "CLASSIFIED_3"]:
                        # UNIT не прошел необходимые этапы обработки - пропускаем
                        continue
                    
                    # ВАЖНО: Проверяем, не является ли UNIT mixed/special/ambiguous
                    # Такие UNIT должны оставаться в Exceptions, а не попадать в Ready2Docling
                    processing_info = manifest.get("processing", {})
                    classification = processing_info.get("classification", {})
                    unit_category = classification.get("category")
                    
                    if unit_category in ["mixed", "special", "ambiguous", "unknown"]:
                        # UNIT был классифицирован как mixed/special/ambiguous - пропускаем
                        # Он должен остаться в Exceptions, а не попадать в Ready2Docling
                        continue
                    
                    # Дополнительная проверка: если в UNIT файлы разных типов (не только разные расширения)
                    # это может указывать на mixed UNIT
                    unique_types = set(file_types.keys())
                    if len(unique_types) > 1:
                        # Проверяем, не являются ли это просто разные расширения одного типа
                        # (например, jpg и jpeg - это один тип)
                        normalized_types = set()
                        for ft in unique_types:
                            # Нормализуем типы (jpg/jpeg -> image, docx/doc -> document и т.д.)
                            if ft in ["jpg", "jpeg", "png", "tiff", "gif"]:
                                normalized_types.add("image")
                            elif ft in ["docx", "doc", "rtf"]:
                                normalized_types.add("document")
                            elif ft in ["xlsx", "xls"]:
                                normalized_types.add("spreadsheet")
                            elif ft in ["pptx", "ppt"]:
                                normalized_types.add("presentation")
                            elif ft in ["pdf"]:
                                normalized_types.add("pdf")
                            elif ft in ["zip_archive", "rar_archive", "7z_archive"]:
                                normalized_types.add("archive")
                            else:
                                normalized_types.add(ft)
                        
                        # Если после нормализации осталось больше одного типа - это mixed
                        if len(normalized_types) > 1:
                            # Проверяем, нет ли специальных файлов (подписи, сертификаты)
                            special_extensions = {".cer", ".p7s", ".sig", ".crt", ".key"}
                            has_special = any(f.suffix.lower() in special_extensions for f in files)
                            
                            if has_special or len(normalized_types) > 2:
                                # Это mixed UNIT - пропускаем
                                continue
                    
                    # Проверяем операции обработки
                    operations = processing_info.get("operations", [])
                    # Для файлов, требующих конвертации, проверяем наличие операции convert
                    if dominant_type in ["doc", "xls", "ppt", "rtf"]:
                        has_convert = any(op.get("type") == "convert" for op in operations)
                        if not has_convert:
                            # Файл требует конвертации, но операция не выполнена - пропускаем
                            continue
                    
                    # Для архивов проверяем наличие операции extract
                    if dominant_type in ["zip_archive", "rar_archive", "7z_archive"]:
                        has_extract = any(op.get("type") == "extract" for op in operations)
                        if not has_extract:
                            # Архив требует извлечения, но операция не выполнена - пропускаем
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
        if unit_id not in all_units:
            all_units[unit_id] = {
                "source": source_name,
                "files": [],
                "manifest": None,
            }

        # Рекурсивный поиск файлов во всех поддиректориях
        # После разархивирования директория может называться как угодно (по имени архива)
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
            manifest: Manifest UNIT для получения needs_ocr

        Returns:
            Путь к целевой поддиректории
        """
        # Маппинг типов на директории
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
            # ВАЖНО: .doc файлы НИКОГДА не должны попадать в docx без предварительной конвертации
            ext_to_dir = {
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
            
            # Берем первое найденное расширение
            if extensions:
                first_ext = list(extensions)[0]
                # Проверяем, является ли это PDF (даже с неправильным расширением)
                is_pdf_by_ext = False
                for ext in extensions:
                    if ext == "pdf" or ext.endswith("pdf"):
                        is_pdf_by_ext = True
                        first_ext = "pdf"
                        break
                subdir_name = ext_to_dir.get(first_ext, "other")

        # Для PDF дополнительная сортировка на scan/text/mixed
        # Проверяем, является ли это PDF (по file_type или по расширениям файлов)
        is_pdf_unit = False
        if file_type == "pdf":
            is_pdf_unit = True
        else:
            # Проверяем расширения файлов, даже если file_type != "pdf"
            for file_path in files:
                file_ext = file_path.suffix.lower()
                file_name_lower = file_path.name.lower()
                if (
                    file_ext == ".pdf" or
                    file_name_lower.endswith("pdf") or
                    file_name_lower.endswith(".pdf")
                ):
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
                            file_path_in_unit = next(
                                (f for f in files if f.name == current_name or f.name == original_name),
                                None
                            )
                            if file_path_in_unit and file_path_in_unit.exists():
                                try:
                                    detection = detect_file_type(file_path_in_unit)
                                    needs_ocr_detected = detection.get("needs_ocr", True)
                                    pdf_files_need_ocr.append(needs_ocr_detected)
                                    pdf_files_has_text.append(not needs_ocr_detected)
                                except Exception:
                                    # Если не удалось определить, считаем scan по умолчанию
                                    pdf_files_need_ocr.append(True)
                                    pdf_files_has_text.append(False)
            
            # Если не нашли в manifest, проверяем файлы напрямую
            if not pdf_files_need_ocr:
                for file_path in files:
                    # Проверяем по расширению (включая неправильные расширения)
                    file_ext = file_path.suffix.lower()
                    file_name_lower = file_path.name.lower()
                    is_pdf_file = (
                        file_ext == ".pdf" or
                        file_name_lower.endswith("pdf") or
                        file_name_lower.endswith(".pdf")
                    )
                    
                    if is_pdf_file:
                        try:
                            detection = detect_file_type(file_path)
                            needs_ocr_detected = detection.get("needs_ocr", True)
                            pdf_files_need_ocr.append(needs_ocr_detected)
                            pdf_files_has_text.append(not needs_ocr_detected)
                        except Exception:
                            # Если не удалось определить, считаем scan по умолчанию
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
                    # Смешанный случай: некоторые требуют OCR, некоторые имеют текст
                    subdir_name = "pdf/mixed"
            else:
                # Fallback: если не удалось определить, но file_type == "pdf", идем в scan
                subdir_name = "pdf/scan"
        
        return base_dir / subdir_name

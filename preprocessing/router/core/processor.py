"""
Основная логика обработки файлов для router.

Выделяет бизнес-логику из HTTP endpoints для лучшей тестируемости и переиспользования.
"""
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from ...core.config import get_config
from ...core.exceptions import ProcessingError, FileDetectionError, ClassificationError, DistributionError
from ..file_detection import detect_file_type
from ..file_classifier import classify_file
from ..unit_distribution_new import distribute_unit_by_new_structure
from ..iterative_processor import IterativeProcessor
from ..state_machine import UnitStateMachine, UnitState
from ..manifest import create_manifest_v2
from ..config import PROCESSING_BASE_DIR
from ..metrics import (
    init_processing_metrics, save_processing_metrics,
    add_input_file_metric, get_current_metrics, add_error_metric
)


class FileProcessor:
    """Класс для обработки файлов."""
    
    def __init__(self):
        self.config = get_config().router
    
    def process_file(
        self,
        file_path: Path,
        unit_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Обрабатывает загруженный файл с полным pipeline.
        
        Процесс:
        1. Создает unit_id
        2. Определяет тип файла
        3. Классифицирует файл
        4. Распределяет по категориям (direct/normalize/convert/extract/special)
        5. Собирает метрики
        6. Возвращает unit_id и статус "processed"
        
        Args:
            file_path: Путь к файлу для обработки
            unit_metadata: Дополнительные метаданные для unit (опционально)
        
        Returns:
            Словарь с результатами обработки:
            {
                "status": "processed" | "error",
                "unit_id": str | None,
                "file": str,
                "size": int,
                "detected_type": str,
                "category": str,
                "distribution": dict,
                "path": str,
                "message": str (при ошибке)
            }
        
        Raises:
            ProcessingError: При ошибке обработки
        """
        try:
            # Проверка существования файла
            if not file_path.exists():
                raise ProcessingError(
                    f"File not found: {file_path}",
                    context={"file_path": str(file_path)}
                )
            
            # Инициализация метрик, если еще не инициализированы
            current_metrics = get_current_metrics()
            if not current_metrics:
                init_processing_metrics()
            
            # Генерация unit_id
            unit_id = f"UNIT_{uuid.uuid4().hex[:16].upper()}"
            
            # Определение типа файла
            try:
                file_type_result = detect_file_type(file_path)
            except Exception as e:
                raise FileDetectionError(
                    f"Failed to detect file type: {e}",
                    context={"file_path": str(file_path), "unit_id": unit_id},
                    original_error=e
                )
            
            # Добавление метрики входного файла
            add_input_file_metric(file_path, file_type_result)
            
            # Классификация файла
            try:
                classification = classify_file(file_path, file_type_result)
            except Exception as e:
                raise ClassificationError(
                    f"Failed to classify file: {e}",
                    context={"file_path": str(file_path), "unit_id": unit_id, "detected_type": file_type_result.get("detected_type")},
                    original_error=e
                )
            
            # Подготовка данных для распределения
            file_info = {
                "path": str(file_path),
                "original_name": file_path.name,
                "size": file_path.stat().st_size,
                "sha256": file_type_result.get("sha256", ""),
                **file_type_result,
                "classification": classification
            }
            
            # Подготовка метаданных unit
            if unit_metadata is None:
                unit_metadata = {
                    "source": "api_upload",
                    "uploaded_at": file_path.stat().st_mtime,
                    "original_filename": file_path.name
                }
            
            # Распределение unit по структуре директорий (Cycle 1)
            try:
                distribution_result = distribute_unit_by_new_structure(
                    unit_id=unit_id,
                    files=[file_info],
                    unit_metadata=unit_metadata,
                    cycle=1  # Начинаем с первого цикла
                )
            except Exception as e:
                raise DistributionError(
                    f"Failed to distribute unit: {e}",
                    context={"unit_id": unit_id, "file_path": str(file_path)},
                    original_error=e
                )
            
            # Создаем manifest v2
            manifest_path = PROCESSING_BASE_DIR / "Pending_1" / classification.get("category", "direct") / unit_id / "manifest.json"
            manifest = create_manifest_v2(
                unit_id=unit_id,
                protocol_id=unit_metadata.get("protocol_id") if unit_metadata else None,
                protocol_date=unit_metadata.get("protocol_date") if unit_metadata else None,  # Дата протокола из БД
                files=[{
                    "original_name": file_path.name,
                    "current_name": file_path.name,
                    "mime_type": file_type_result.get("mime_type", ""),
                    "detected_type": file_type_result.get("detected_type", "unknown"),
                    "needs_ocr": file_type_result.get("needs_ocr", False),
                    "transformations": []
                }],
                current_cycle=1,
                state_trace=["RAW_INPUT", "CLASSIFIED_1"],
                source_urls=unit_metadata.get("urls", []) if unit_metadata else []
            )
            
            # Сохраняем manifest
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            import json
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2, ensure_ascii=False)
            
            # Инициализируем IterativeProcessor для дальнейшей обработки
            # (опционально, можно запустить сразу или позже)
            iterative_processor = IterativeProcessor(unit_id, manifest_path)
            
            # Сохранение метрик
            save_processing_metrics()
            
            return {
                "status": "processed",
                "unit_id": unit_id,
                "file": file_path.name,
                "size": file_info["size"],
                "detected_type": file_type_result.get("detected_type", "unknown"),
                "category": classification.get("category", "unknown"),
                "distribution": {
                    "files_processed": distribution_result.get("files_processed", 0),
                    "files_by_category": distribution_result.get("files_by_category", {}),
                    "duplicates_detected": distribution_result.get("duplicates_detected", False)
                },
                "manifest_path": str(manifest_path),
                "state_trace": ["RAW_INPUT", "CLASSIFIED_1"],
                "path": str(file_path)
            }
        
        except ProcessingError:
            # Пробрасываем ProcessingError дальше
            raise
        except Exception as e:
            # Обертываем неожиданные ошибки в ProcessingError
            error_traceback = None
            try:
                import traceback
                error_traceback = traceback.format_exc()
            except Exception:
                pass
            
            # Добавляем ошибку в метрики
            add_error_metric(str(file_path), "process_file", str(e), error_traceback)
            
            raise ProcessingError(
                f"Unexpected error processing file: {e}",
                context={"file_path": str(file_path)},
                original_error=e
            )
    
    def process_files(
        self,
        file_paths: List[Path],
        unit_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Обрабатывает несколько файлов.
        
        Args:
            file_paths: Список путей к файлам
            unit_metadata: Дополнительные метаданные (опционально)
        
        Returns:
            Список результатов обработки (может содержать ошибки)
        """
        results = []
        for file_path in file_paths:
            try:
                result = self.process_file(file_path, unit_metadata)
                results.append(result)
            except ProcessingError as e:
                # Добавляем ошибку в результаты
                results.append({
                    "status": "error",
                    "message": str(e),
                    "unit_id": None,
                    "file": str(file_path),
                    "error_context": e.context
                })
        return results


# Функция для обратной совместимости
def process_file(file_path: Path, background_tasks: Optional[Any] = None) -> Dict[str, Any]:
    """
    Обрабатывает файл (функция для обратной совместимости с api.py).
    
    Args:
        file_path: Путь к файлу
        background_tasks: BackgroundTasks (не используется, для совместимости)
    
    Returns:
        Словарь с результатами обработки
    """
    processor = FileProcessor()
    try:
        return processor.process_file(file_path)
    except ProcessingError as e:
        # Возвращаем ошибку в формате словаря для обратной совместимости
        return {
            "status": "error",
            "message": str(e),
            "unit_id": None,
            "file": str(file_path)
        }


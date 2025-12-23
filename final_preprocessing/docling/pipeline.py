"""
Основной orchestration pipeline для обработки UNIT через Docling.

Координирует все компоненты: bridge_docprep → config → runner → exporters.
"""
import logging
import time
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List

from .bridge_docprep import load_unit_from_ready2docling, get_main_file
from .config import build_docling_options, get_input_format_from_route
from .runner import run_docling_conversion
from .exporters.json import export_to_json
from .exporters.markdown import export_to_markdown
from .exporters.mongodb import export_to_mongodb

logger = logging.getLogger(__name__)


class DoclingPipeline:
    """
    Pipeline для обработки UNIT через Docling.

    Последовательность:
    1. Загрузка UNIT через bridge_docprep
    2. Построение Docling options через config
    3. Запуск конвертации через runner
    4. Экспорт результатов через exporters
    """

    def __init__(
        self,
        export_json: bool = True,
        export_markdown: bool = False,
        export_mongodb: bool = True,
        json_output_dir: Optional[Path] = None,
        markdown_output_dir: Optional[Path] = None,
        quarantine_dir: Optional[Path] = None,
        skip_failed: bool = True,
    ):
        """
        Инициализирует pipeline.

        Args:
            export_json: Экспортировать в JSON
            export_markdown: Экспортировать в Markdown
            export_mongodb: Экспортировать в MongoDB
            json_output_dir: Директория для JSON файлов (опционально)
            markdown_output_dir: Директория для Markdown файлов (опционально)
            quarantine_dir: Директория для проблемных UNIT (опционально)
            skip_failed: Пропускать неудачные UNIT и продолжать обработку
        """
        self.export_json = export_json
        self.export_markdown = export_markdown
        self.export_mongodb = export_mongodb
        self.json_output_dir = json_output_dir
        self.markdown_output_dir = markdown_output_dir
        self.quarantine_dir = quarantine_dir
        self.skip_failed = skip_failed

    def process_unit(self, unit_path: Path) -> Dict[str, Any]:
        """
        Обрабатывает UNIT через Docling pipeline.

        Args:
            unit_path: Путь к UNIT директории в Ready2Docling

        Returns:
            Словарь с результатами:
            - success: bool
            - unit_id: str
            - route: str
            - document: Document объект
            - exports: dict с путями к экспортированным файлам
            - processing_time: float
            - errors: list ошибок
        """
        start_time = time.time()
        result = {
            "success": False,
            "unit_id": None,
            "route": None,
            "document": None,
            "exports": {},
            "processing_time": 0.0,
            "errors": [],
        }

        try:
            # Шаг 1: Загрузка UNIT через bridge_docprep
            logger.info(f"Loading unit from Ready2Docling: {unit_path}")
            unit_data = load_unit_from_ready2docling(unit_path)

            manifest = unit_data["manifest"]
            unit_id = unit_data["unit_id"]
            route = unit_data["route"]
            files = unit_data["files"]

            result["unit_id"] = unit_id
            result["route"] = route

            # Шаг 2: Получаем главный файл для обработки
            main_file = get_main_file(unit_data)
            if not main_file:
                raise ValueError("No main file found in unit")

            logger.info(f"Processing file: {main_file} (route: {route})")

            # Шаг 3: Построение Docling options через config
            options = build_docling_options(route, manifest)
            input_format = get_input_format_from_route(route)

            if not options:
                logger.warning("Docling options not available, using defaults")

            # Шаг 4: Запуск конвертации через runner
            document = run_docling_conversion(
                main_file,
                options=options,
                input_format=input_format,
            )

            if not document:
                raise ValueError("Docling conversion returned None")

            result["document"] = document

            # Шаг 5: Экспорт результатов
            exports = {}

            # JSON экспорт
            if self.export_json:
                try:
                    if self.json_output_dir:
                        json_path = self.json_output_dir / f"{unit_id}.json"
                    else:
                        json_path = unit_path / f"{unit_id}_docling.json"

                    export_to_json(
                        document,
                        json_path,
                        metadata={
                            "unit_id": unit_id,
                            "route": route,
                            "protocol_date": manifest.get("protocol_date"),
                        },
                    )
                    exports["json"] = str(json_path)
                except Exception as e:
                    logger.error(f"JSON export failed: {e}")
                    result["errors"].append(f"JSON export: {str(e)}")

            # Markdown экспорт
            if self.export_markdown:
                try:
                    if self.markdown_output_dir:
                        md_path = self.markdown_output_dir / f"{unit_id}.md"
                    else:
                        md_path = unit_path / f"{unit_id}_docling.md"

                    export_to_markdown(
                        document,
                        md_path,
                        metadata={
                            "unit_id": unit_id,
                            "route": route,
                            "protocol_date": manifest.get("protocol_date"),
                        },
                    )
                    exports["markdown"] = str(md_path)
                except Exception as e:
                    logger.error(f"Markdown export failed: {e}")
                    result["errors"].append(f"Markdown export: {str(e)}")

            # MongoDB экспорт
            if self.export_mongodb:
                try:
                    doc_id = export_to_mongodb(document, manifest, unit_id)
                    exports["mongodb"] = doc_id
                except Exception as e:
                    logger.error(f"MongoDB export failed: {e}")
                    result["errors"].append(f"MongoDB export: {str(e)}")

            result["exports"] = exports
            result["success"] = True

        except Exception as e:
            logger.error(f"Pipeline failed for {unit_path}: {e}", exc_info=True)
            result["errors"].append(str(e))
            result["success"] = False
            
            # Детальное логирование ошибки
            error_details = {
                "unit_id": result.get("unit_id", unit_path.name),
                "route": result.get("route", "unknown"),
                "error_type": type(e).__name__,
                "error_message": str(e),
                "unit_path": str(unit_path),
            }
            logger.error(f"Error details: {error_details}")

        finally:
            result["processing_time"] = time.time() - start_time

        return result
    
    def _quarantine_unit(self, unit_path: Path, unit_id: str, error: str) -> Optional[Path]:
        """
        Копирует проблемный UNIT в quarantine директорию.

        Args:
            unit_path: Путь к UNIT директории
            unit_id: Идентификатор UNIT
            error: Сообщение об ошибке

        Returns:
            Путь к скопированному UNIT в quarantine или None
        """
        if not self.quarantine_dir:
            return None
        
        try:
            # Создаем директорию quarantine если нужно
            self.quarantine_dir.mkdir(parents=True, exist_ok=True)
            
            # Создаем целевую директорию для UNIT
            quarantine_unit_dir = self.quarantine_dir / unit_id
            quarantine_unit_dir.mkdir(parents=True, exist_ok=True)
            
            # Копируем все файлы из UNIT
            for item in unit_path.iterdir():
                if item.is_file():
                    shutil.copy2(item, quarantine_unit_dir / item.name)
                elif item.is_dir():
                    shutil.copytree(item, quarantine_unit_dir / item.name, dirs_exist_ok=True)
            
            # Создаем файл с информацией об ошибке
            error_file = quarantine_unit_dir / "error_info.txt"
            with open(error_file, "w", encoding="utf-8") as f:
                f.write(f"Unit ID: {unit_id}\n")
                f.write(f"Original Path: {unit_path}\n")
                f.write(f"Error: {error}\n")
                f.write(f"Quarantined at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            logger.info(f"Unit {unit_id} quarantined to {quarantine_unit_dir}")
            return quarantine_unit_dir
            
        except Exception as e:
            logger.error(f"Failed to quarantine unit {unit_id}: {e}")
            return None

    def process_directory(
        self,
        ready2docling_dir: Path,
        limit: Optional[int] = None,
        recursive: bool = True,
    ) -> Dict[str, Any]:
        """
        Обрабатывает все UNIT в директории Ready2Docling.

        Args:
            ready2docling_dir: Директория Ready2Docling (например, Data/2025-12-20/Ready2Docling)
            limit: Ограничение количества UNIT (опционально)
            recursive: Рекурсивный поиск UNIT

        Returns:
            Словарь с результатами:
            - total_units: int
            - processed: int
            - succeeded: int
            - failed: int
            - results: list результатов для каждого UNIT
        """
        # Находим все UNIT директории
        if recursive:
            unit_dirs = list(ready2docling_dir.rglob("UNIT_*"))
        else:
            unit_dirs = [d for d in ready2docling_dir.iterdir() if d.is_dir() and d.name.startswith("UNIT_")]

        if limit:
            unit_dirs = unit_dirs[:limit]

        logger.info(f"Found {len(unit_dirs)} units in {ready2docling_dir}")

        results = {
            "total_units": len(unit_dirs),
            "processed": 0,
            "succeeded": 0,
            "failed": 0,
            "results": [],
        }

        for unit_dir in unit_dirs:
            try:
                result = self.process_unit(unit_dir)
                results["processed"] += 1

                if result["success"]:
                    results["succeeded"] += 1
                else:
                    results["failed"] += 1
                    # Quarantine для неудачных UNIT
                    if self.quarantine_dir and result.get("errors"):
                        error_msg = "; ".join(result.get("errors", []))
                        quarantine_path = self._quarantine_unit(
                            unit_dir,
                            result.get("unit_id", unit_dir.name),
                            error_msg
                        )
                        if quarantine_path:
                            result["quarantine_path"] = str(quarantine_path)

                results["results"].append(result)

            except Exception as e:
                logger.error(f"Failed to process {unit_dir}: {e}", exc_info=True)
                results["failed"] += 1
                
                error_result = {
                    "success": False,
                    "unit_id": unit_dir.name,
                    "errors": [str(e)],
                    "processing_time": 0.0,
                }
                
                # Quarantine для исключений
                if self.quarantine_dir:
                    quarantine_path = self._quarantine_unit(unit_dir, unit_dir.name, str(e))
                    if quarantine_path:
                        error_result["quarantine_path"] = str(quarantine_path)
                
                results["results"].append(error_result)
                
                # Если skip_failed=False, останавливаем обработку при первой ошибке
                if not self.skip_failed:
                    logger.error(f"Stopping processing due to error (skip_failed=False)")
                    break

        logger.info(
            f"Processing completed: {results['succeeded']} succeeded, "
            f"{results['failed']} failed out of {results['total_units']} total"
        )

        return results


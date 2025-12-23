#!/usr/bin/env python3
"""
Тестовый скрипт для проверки интеграции docprep с docling.

Проверяет:
1. Загрузку UNIT через bridge_docprep
2. Определение route из manifest
3. Построение Docling options
4. Конвертацию через runner
5. Экспорт результатов
"""
import sys
import logging
from pathlib import Path
from typing import Dict, Any

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Добавляем пути для импорта
# Теперь docling находится в final_preprocessing/docling
_project_root = Path(__file__).parent.parent.parent  # final_preprocessing
sys.path.insert(0, str(_project_root))

from docling.pipeline import DoclingPipeline
from docling.bridge_docprep import load_unit_from_ready2docling, get_main_file
from docling.config import build_docling_options, get_input_format_from_route


def test_unit_loading(unit_path: Path) -> Dict[str, Any]:
    """Тестирует загрузку UNIT через bridge_docprep."""
    logger.info(f"Testing unit loading: {unit_path}")
    
    try:
        unit_data = load_unit_from_ready2docling(unit_path)
        
        logger.info(f"✅ Unit loaded successfully:")
        logger.info(f"  - Unit ID: {unit_data['unit_id']}")
        logger.info(f"  - Route: {unit_data['route']}")
        logger.info(f"  - Files: {len(unit_data['files'])}")
        
        # Проверяем manifest
        manifest = unit_data.get("manifest", {})
        processing = manifest.get("processing", {})
        route_from_manifest = processing.get("route")
        
        logger.info(f"  - Route from manifest: {route_from_manifest}")
        logger.info(f"  - Route determined: {unit_data['route']}")
        
        return {
            "success": True,
            "unit_data": unit_data,
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to load unit: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
        }


def test_config_mapping(route: str, manifest: Dict[str, Any]) -> Dict[str, Any]:
    """Тестирует маппинг route → Docling options."""
    logger.info(f"Testing config mapping for route: {route}")
    
    try:
        options = build_docling_options(route, manifest)
        input_format = get_input_format_from_route(route)
        
        if options:
            logger.info(f"✅ Docling options built successfully")
            logger.info(f"  - Input format: {input_format}")
            logger.info(f"  - Options type: {type(options).__name__}")
            
            # Проверяем специфичные настройки для PDF
            if hasattr(options, 'pdf') and options.pdf:
                logger.info(f"  - PDF OCR: {getattr(options.pdf, 'do_ocr', 'N/A')}")
                logger.info(f"  - PDF Table Structure: {getattr(options.pdf, 'do_table_structure', 'N/A')}")
            
            return {
                "success": True,
                "options": options,
                "input_format": input_format,
            }
        else:
            logger.warning(f"⚠️  Docling options not available (Docling not installed?)")
            return {
                "success": False,
                "error": "Docling options not available",
            }
            
    except Exception as e:
        logger.error(f"❌ Failed to build options: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
        }


def test_main_file_detection(unit_data: Dict[str, Any]) -> Dict[str, Any]:
    """Тестирует определение главного файла."""
    logger.info("Testing main file detection")
    
    try:
        main_file = get_main_file(unit_data)
        
        if main_file:
            logger.info(f"✅ Main file detected: {main_file}")
            logger.info(f"  - Exists: {main_file.exists()}")
            logger.info(f"  - Size: {main_file.stat().st_size if main_file.exists() else 0} bytes")
            return {
                "success": True,
                "main_file": main_file,
            }
        else:
            logger.warning("⚠️  No main file found")
            return {
                "success": False,
                "error": "No main file found",
            }
            
    except Exception as e:
        logger.error(f"❌ Failed to detect main file: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
        }


def test_pipeline_processing(unit_path: Path, limit: int = 3) -> Dict[str, Any]:
    """Тестирует полный pipeline обработки."""
    logger.info(f"Testing full pipeline processing (limit: {limit})")
    
    try:
        pipeline = DoclingPipeline(
            export_json=True,
            export_markdown=False,
            export_mongodb=False,  # Отключаем MongoDB для теста
        )
        
        # Обрабатываем один UNIT
        result = pipeline.process_unit(unit_path)
        
        if result["success"]:
            logger.info(f"✅ Pipeline processing successful:")
            logger.info(f"  - Unit ID: {result['unit_id']}")
            logger.info(f"  - Route: {result['route']}")
            logger.info(f"  - Processing time: {result['processing_time']:.2f}s")
            logger.info(f"  - Exports: {list(result['exports'].keys())}")
            return {
                "success": True,
                "result": result,
            }
        else:
            logger.error(f"❌ Pipeline processing failed:")
            logger.error(f"  - Errors: {result.get('errors', [])}")
            return {
                "success": False,
                "result": result,
            }
            
    except Exception as e:
        logger.error(f"❌ Pipeline processing failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
        }


def main():
    """Главная функция тестирования."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test docprep-docling integration")
    parser.add_argument(
        "data_dir",
        type=Path,
        help="Path to Data directory (e.g., Data/2025-03-20)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=3,
        help="Limit number of units to test (default: 3)",
    )
    parser.add_argument(
        "--unit-id",
        type=str,
        help="Test specific unit ID",
    )
    
    args = parser.parse_args()
    
    data_dir = args.data_dir
    ready2docling_dir = data_dir / "Ready2Docling"
    
    if not ready2docling_dir.exists():
        logger.error(f"❌ Ready2Docling directory not found: {ready2docling_dir}")
        logger.info("💡 Run docprep pipeline first to prepare data")
        return 1
    
    # Находим UNIT для тестирования
    if args.unit_id:
        unit_path = ready2docling_dir / args.unit_id
        if not unit_path.exists():
            # Ищем рекурсивно
            unit_path = next(ready2docling_dir.rglob(args.unit_id), None)
        if not unit_path or not unit_path.exists():
            logger.error(f"❌ Unit not found: {args.unit_id}")
            return 1
        unit_paths = [unit_path]
    else:
        # Находим первые N UNIT
        unit_paths = list(ready2docling_dir.rglob("UNIT_*"))[:args.limit]
        if not unit_paths:
            logger.error(f"❌ No UNIT directories found in {ready2docling_dir}")
            return 1
    
    logger.info(f"Found {len(unit_paths)} unit(s) to test")
    
    # Тестируем каждый UNIT
    results = []
    for unit_path in unit_paths:
        logger.info(f"\n{'='*80}")
        logger.info(f"Testing UNIT: {unit_path.name}")
        logger.info(f"{'='*80}")
        
        # Тест 1: Загрузка UNIT
        load_result = test_unit_loading(unit_path)
        if not load_result["success"]:
            results.append({"unit": unit_path.name, "status": "failed", "stage": "loading"})
            continue
        
        unit_data = load_result["unit_data"]
        manifest = unit_data["manifest"]
        route = unit_data["route"]
        
        # Тест 2: Определение главного файла
        main_file_result = test_main_file_detection(unit_data)
        if not main_file_result["success"]:
            results.append({"unit": unit_path.name, "status": "failed", "stage": "main_file"})
            continue
        
        # Тест 3: Маппинг route → options
        config_result = test_config_mapping(route, manifest)
        if not config_result["success"]:
            results.append({"unit": unit_path.name, "status": "failed", "stage": "config"})
            continue
        
        # Тест 4: Полный pipeline (опционально, если Docling доступен)
        try:
            pipeline_result = test_pipeline_processing(unit_path, limit=1)
            if pipeline_result["success"]:
                results.append({"unit": unit_path.name, "status": "success", "stage": "pipeline"})
            else:
                results.append({"unit": unit_path.name, "status": "failed", "stage": "pipeline"})
        except Exception as e:
            logger.warning(f"⚠️  Pipeline test skipped (Docling may not be available): {e}")
            results.append({"unit": unit_path.name, "status": "partial", "stage": "pipeline_skipped"})
    
    # Итоговый отчет
    logger.info(f"\n{'='*80}")
    logger.info("TEST SUMMARY")
    logger.info(f"{'='*80}")
    
    success_count = sum(1 for r in results if r["status"] == "success")
    failed_count = sum(1 for r in results if r["status"] == "failed")
    partial_count = sum(1 for r in results if r["status"] == "partial")
    
    logger.info(f"Total units tested: {len(results)}")
    logger.info(f"✅ Success: {success_count}")
    logger.info(f"⚠️  Partial: {partial_count}")
    logger.info(f"❌ Failed: {failed_count}")
    
    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())


#!/usr/bin/env python3
"""
Тестовый скрипт для обработки digital units через Docling pipeline.

Поддерживает:
- Ограничение количества UNIT (--limit)
- Фильтрацию по route (--route)
- Автоматическую проверку наличия contract
- Сохранение результатов в OutputDocling с сохранением структуры Ready2Docling
"""
import sys
import logging
import argparse
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# ВАЖНО: Добавляем site-packages в sys.path ПЕРЕД добавлением проекта
# Это необходимо для избежания конфликта имен (локальный модуль docling_integration не конфликтует с установленным пакетом docling)
import site
for site_dir in site.getsitepackages():
    if (Path(site_dir) / 'docling' / '__init__.py').exists():
        if site_dir not in sys.path:
            sys.path.insert(0, site_dir)
        break

# Добавляем путь к проекту после site-packages
_project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_project_root))

# Импортируем локальные модули
# Локальные модули используют установленный пакет docling через специальную логику в runner.py и config.py
from docling_integration.pipeline import DoclingPipeline
from docprep.core.contract import load_contract

# Настройка логирования (делаем это после импортов, чтобы logger был доступен)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_contracts(ready2docling_dir: Path, limit: Optional[int] = None) -> Dict[str, Any]:
    """
    Проверяет наличие contract файлов в UNIT.
    
    Args:
        ready2docling_dir: Директория Ready2Docling
        limit: Ограничение количества проверяемых UNIT
        
    Returns:
        Словарь с результатами проверки
    """
    unit_dirs = list(ready2docling_dir.rglob("UNIT_*"))
    unit_dirs = [d for d in unit_dirs if d.is_dir()]
    
    if limit:
        unit_dirs = unit_dirs[:limit]
    
    results = {
        "total": len(unit_dirs),
        "with_contract": 0,
        "without_contract": 0,
        "units_without_contract": [],
    }
    
    for unit_dir in unit_dirs:
        contract_path = unit_dir / "docprep.contract.json"
        if contract_path.exists():
            results["with_contract"] += 1
        else:
            results["without_contract"] += 1
            results["units_without_contract"].append(str(unit_dir.relative_to(ready2docling_dir)))
    
    return results


def filter_units_by_route(unit_dirs: list[Path], route: str) -> list[Path]:
    """
    Фильтрует UNIT по route из contract.
    
    Args:
        unit_dirs: Список путей к UNIT директориям
        route: Route для фильтрации
        
    Returns:
        Отфильтрованный список UNIT
    """
    filtered = []
    
    for unit_dir in unit_dirs:
        try:
            contract = load_contract(unit_dir)
            contract_route = contract.get("routing", {}).get("docling_route", "")
            if contract_route == route:
                filtered.append(unit_dir)
        except Exception:
            # Если contract не загружается, пропускаем
            continue
    
    return filtered


def main():
    """Главная функция."""
    parser = argparse.ArgumentParser(
        description="Test Docling pipeline processing for digital units"
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        required=True,
        help="Path to Data directory (e.g., Data/2025-03-04)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Limit number of units to process (default: 20)",
    )
    parser.add_argument(
        "--route",
        type=str,
        default=None,
        help="Filter units by route (e.g., pdf_text, docx, xlsx)",
    )
    parser.add_argument(
        "--skip-check",
        action="store_true",
        help="Skip contract check and proceed anyway",
    )
    parser.add_argument(
        "--no-markdown",
        action="store_true",
        help="Disable markdown export (enabled by default)",
    )
    parser.add_argument(
        "--no-mongodb",
        action="store_true",
        help="Disable MongoDB export",
    )
    
    args = parser.parse_args()
    
    data_dir = Path(args.data_dir).resolve()
    ready2docling_dir = data_dir / "Ready2Docling"
    output_dir = data_dir / "OutputDocling"
    quarantine_dir = data_dir / "Quarantine"
    
    if not ready2docling_dir.exists():
        logger.error(f"Ready2Docling directory not found: {ready2docling_dir}")
        logger.info("💡 Run docprep pipeline first to prepare data")
        return 1
    
    logger.info("=" * 60)
    logger.info("Docling Pipeline Testing")
    logger.info("=" * 60)
    logger.info(f"Data directory: {data_dir}")
    logger.info(f"Ready2Docling: {ready2docling_dir}")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Limit: {args.limit}")
    if args.route:
        logger.info(f"Route filter: {args.route}")
    logger.info("=" * 60)
    
    # Находим UNIT для обработки сначала
    logger.info(f"\nFinding UNIT directories...")
    unit_dirs = list(ready2docling_dir.rglob("UNIT_*"))
    unit_dirs = [d for d in unit_dirs if d.is_dir()]
    
    # Фильтруем по route если указан
    if args.route:
        logger.info(f"Filtering by route: {args.route}")
        unit_dirs = filter_units_by_route(unit_dirs, args.route)
        logger.info(f"Found {len(unit_dirs)} unit(s) with route '{args.route}'")
    
    # Применяем лимит
    if args.limit:
        unit_dirs = unit_dirs[:args.limit]
    
    if not unit_dirs:
        logger.error("No UNIT directories found to process")
        return 1
    
    logger.info(f"Will process {len(unit_dirs)} unit(s)")
    
    # Проверка наличия contract для UNIT которые будем обрабатывать
    if not args.skip_check:
        logger.info("Checking for contract files in selected units...")
        contract_check = {
            "total": len(unit_dirs),
            "with_contract": 0,
            "without_contract": 0,
            "units_without_contract": [],
        }
        
        for unit_dir in unit_dirs:
            contract_path = unit_dir / "docprep.contract.json"
            if contract_path.exists():
                contract_check["with_contract"] += 1
            else:
                contract_check["without_contract"] += 1
                contract_check["units_without_contract"].append(str(unit_dir.relative_to(ready2docling_dir)))
        
        logger.info(f"Contract check results:")
        logger.info(f"  Total units to process: {contract_check['total']}")
        logger.info(f"  With contract: {contract_check['with_contract']}")
        logger.info(f"  Without contract: {contract_check['without_contract']}")
        
        if contract_check['without_contract'] > 0:
            logger.warning(f"⚠️  {contract_check['without_contract']} unit(s) without contract:")
            for unit_path in contract_check['units_without_contract'][:10]:  # Показываем первые 10
                logger.warning(f"    - {unit_path}")
            if contract_check['without_contract'] > 10:
                logger.warning(f"    ... and {contract_check['without_contract'] - 10} more")
            
            logger.warning("💡 Run generate_contracts_for_ready2docling.py to generate contracts")
            if contract_check['with_contract'] == 0:
                logger.error("❌ No units with contracts found. Cannot proceed.")
                return 1
            else:
                logger.warning("⚠️  Will skip units without contracts...")
                # Фильтруем UNIT без contract
                unit_dirs = [d for d in unit_dirs if (d / "docprep.contract.json").exists()]
                logger.info(f"Proceeding with {len(unit_dirs)} unit(s) that have contracts")
    
    
    # Создаем директории
    output_dir.mkdir(parents=True, exist_ok=True)
    if quarantine_dir:
        quarantine_dir.mkdir(parents=True, exist_ok=True)
    
    # Инициализируем pipeline
    pipeline = DoclingPipeline(
        export_json=True,
        export_markdown=not args.no_markdown,  # Markdown включен по умолчанию
        export_mongodb=not args.no_mongodb,
        base_output_dir=output_dir,
        ready2docling_dir=ready2docling_dir,
        quarantine_dir=quarantine_dir,
        skip_failed=True,
    )
    
    # Обрабатываем UNIT напрямую
    logger.info("\n" + "=" * 60)
    logger.info("Starting pipeline processing...")
    logger.info("=" * 60)
    
    processed_results = {
        "total_units": len(unit_dirs),
        "processed": 0,
        "succeeded": 0,
        "failed": 0,
        "results": [],
    }
    
    for i, unit_dir in enumerate(unit_dirs, 1):
        logger.info(f"\n[{i}/{len(unit_dirs)}] Processing: {unit_dir.name}")
        try:
            result = pipeline.process_unit(unit_dir)
            processed_results["processed"] += 1
            # Удаляем несериализуемые объекты из result перед сохранением
            result_serializable = {k: v for k, v in result.items() if k != "document"}
            processed_results["results"].append(result_serializable)
            
            if result["success"]:
                processed_results["succeeded"] += 1
                logger.info(f"✅ Success: {result['unit_id']} (route: {result['route']}, time: {result['processing_time']:.2f}s)")
                if result.get("exports"):
                    logger.info(f"   Exports: {list(result['exports'].keys())}")
            else:
                processed_results["failed"] += 1
                logger.error(f"❌ Failed: {result['unit_id']}")
                for error in result.get("errors", []):
                    logger.error(f"   Error: {error}")
        except Exception as e:
            logger.error(f"❌ Exception processing {unit_dir.name}: {e}", exc_info=True)
            processed_results["failed"] += 1
            error_result = {
                "success": False,
                "unit_id": unit_dir.name,
                "errors": [str(e)],
                "processing_time": 0.0,
            }
            processed_results["results"].append(error_result)
    
    # Итоговая статистика
    logger.info("\n" + "=" * 60)
    logger.info("Processing Summary")
    logger.info("=" * 60)
    logger.info(f"Total units: {processed_results['total_units']}")
    logger.info(f"Processed: {processed_results['processed']}")
    logger.info(f"✅ Succeeded: {processed_results['succeeded']}")
    logger.info(f"❌ Failed: {processed_results['failed']}")
    
    # Сохраняем отчет
    report_path = output_dir / f"processing_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report = {
        "timestamp": datetime.now().isoformat(),
        "data_dir": str(data_dir),
        "ready2docling_dir": str(ready2docling_dir),
        "output_dir": str(output_dir),
        "parameters": {
            "limit": args.limit,
            "route_filter": args.route,
        },
        "results": processed_results,
    }
    
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    logger.info(f"\nReport saved to: {report_path}")
    logger.info("=" * 60)
    
    return 0 if processed_results["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())


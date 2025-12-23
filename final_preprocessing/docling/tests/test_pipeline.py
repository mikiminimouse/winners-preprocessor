#!/usr/bin/env python3
"""
Тестовый скрипт для проверки Docling pipeline на реальных UNIT.

Использование:
    python -m docling.tests.test_pipeline --date 2025-12-20 --limit 5
"""
import argparse
import logging
import sys
from pathlib import Path

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Добавляем путь для импорта
_project_root = Path(__file__).parent.parent.parent  # final_preprocessing
sys.path.insert(0, str(_project_root))

from docling.pipeline import DoclingPipeline

# Путь к данным
DATA_DIR = _project_root / "Data"


def test_single_unit(unit_path: Path):
    """Тестирует обработку одного UNIT."""
    print(f"\n{'='*60}")
    print(f"Testing unit: {unit_path.name}")
    print(f"{'='*60}")

    pipeline = DoclingPipeline(
        export_json=True,
        export_markdown=False,
        export_mongodb=True,
    )

    result = pipeline.process_unit(unit_path)

    if result["success"]:
        print(f"✅ SUCCESS")
        print(f"   Unit ID: {result['unit_id']}")
        print(f"   Route: {result['route']}")
        print(f"   Processing time: {result['processing_time']:.2f}s")
        print(f"   Exports:")
        for fmt, path in result["exports"].items():
            print(f"     - {fmt}: {path}")
    else:
        print(f"❌ FAILED")
        print(f"   Errors: {result['errors']}")

    return result


def test_directory(date: str, limit: int = None):
    """Тестирует обработку всех UNIT за дату."""
    ready2docling_dir = DATA_DIR / date / "Ready2Docling"

    if not ready2docling_dir.exists():
        print(f"❌ Directory not found: {ready2docling_dir}")
        return

    print(f"\n{'='*60}")
    print(f"Testing directory: {ready2docling_dir}")
    print(f"{'='*60}")

    pipeline = DoclingPipeline(
        export_json=True,
        export_markdown=False,
        export_mongodb=True,
    )

    results = pipeline.process_directory(
        ready2docling_dir,
        limit=limit,
        recursive=True,
    )

    print(f"\n{'='*60}")
    print(f"RESULTS")
    print(f"{'='*60}")
    print(f"Total units: {results['total_units']}")
    print(f"Processed: {results['processed']}")
    print(f"Succeeded: {results['succeeded']}")
    print(f"Failed: {results['failed']}")

    if results["failed"] > 0:
        print(f"\nFailed units:")
        for result in results["results"]:
            if not result["success"]:
                print(f"  - {result.get('unit_id', 'unknown')}: {result.get('errors', [])}")


def main():
    parser = argparse.ArgumentParser(description="Test Docling pipeline")
    parser.add_argument(
        "--date",
        type=str,
        required=True,
        help="Date in format YYYY-MM-DD (e.g., 2025-12-20)",
    )
    parser.add_argument(
        "--unit",
        type=str,
        help="Specific unit ID to test (e.g., UNIT_xxx)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of units to process",
    )
    parser.add_argument(
        "--route",
        type=str,
        help="Filter by route (pdf_text, pdf_scan, docx, etc.)",
    )

    args = parser.parse_args()

    ready2docling_dir = DATA_DIR / args.date / "Ready2Docling"

    if not ready2docling_dir.exists():
        print(f"❌ Directory not found: {ready2docling_dir}")
        sys.exit(1)

    if args.unit:
        # Тестируем конкретный UNIT
        unit_path = ready2docling_dir / args.unit
        if not unit_path.exists():
            # Пробуем найти рекурсивно
            unit_paths = list(ready2docling_dir.rglob(args.unit))
            if not unit_paths:
                print(f"❌ Unit not found: {args.unit}")
                sys.exit(1)
            unit_path = unit_paths[0]

        test_single_unit(unit_path)
    else:
        # Тестируем директорию
        test_directory(args.date, limit=args.limit)


if __name__ == "__main__":
    main()


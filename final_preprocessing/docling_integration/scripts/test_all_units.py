#!/usr/bin/env python3
"""
Комплексное тестирование всех UNIT форматов через Docling pipeline.

Тестирует:
- Native форматы: docx, xlsx, xml (без OCR)
- PDF text: текстовые PDF (без OCR)
- PDF scan: сканы PDF (с EasyOCR)
- Images: jpeg, png (с EasyOCR)

Использование:
    # Тест конкретного формата
    python3 scripts/test_all_units.py --format docx --limit 10
    python3 scripts/test_all_units.py --format pdf_text --limit 10
    python3 scripts/test_all_units.py --format pdf_scan --limit 5

    # Тест всех форматов
    python3 scripts/test_all_units.py --all --limit 5

    # Генерация отчёта
    python3 scripts/test_all_units.py --report

    # Указание директории
    python3 scripts/test_all_units.py --data-dir /path/to/Ready2Docling --format docx
"""
import argparse
import json
import logging
import os
import sys
import time
import tracemalloc
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed

# Добавляем родительскую директорию в путь для импорта
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir.parent))  # для docling_integration

# Импортируем как пакет
from docling_integration.pipeline import DoclingPipeline

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Ограничение параллелизма для OCR
MAX_PARALLEL_OCR = 3
MAX_PARALLEL_NATIVE = 6


@dataclass
class UnitTestResult:
    """Результат тестирования одного UNIT."""
    unit_id: str
    format_type: str
    route: str = ""
    success: bool = False
    time_sec: float = 0.0
    memory_mb: float = 0.0
    word_count: int = 0
    error: Optional[str] = None
    file_path: str = ""


@dataclass
class FormatTestResults:
    """Результаты тестирования одного формата."""
    format_type: str
    total_units: int = 0
    processed: int = 0
    succeeded: int = 0
    failed: int = 0
    avg_time_sec: float = 0.0
    avg_memory_mb: float = 0.0
    total_words: int = 0
    results: List[UnitTestResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class AllUnitsTest:
    """Комплексное тестирование всех форматов UNIT."""

    # Маппинг format -> subdirectory в Ready2Docling
    FORMAT_DIRS = {
        "docx": "docx",
        "xlsx": "xlsx",
        "xml": "xml",
        "pdf_text": "pdf/text",
        "pdf_scan": "pdf/scan",
        "jpeg": "jpeg",
        "png": "png",
        "image": "jpeg",  # alias
    }

    # Форматы, требующие OCR
    OCR_FORMATS = {"pdf_scan", "jpeg", "png", "image"}

    def __init__(
        self,
        data_dir: Path,
        output_dir: Optional[Path] = None,
        max_parallel_ocr: int = MAX_PARALLEL_OCR,
        max_parallel_native: int = MAX_PARALLEL_NATIVE,
    ):
        """
        Args:
            data_dir: Директория Ready2Docling
            output_dir: Директория для результатов (опционально)
            max_parallel_ocr: Макс. параллельных OCR процессов
            max_parallel_native: Макс. параллельных native процессов
        """
        self.data_dir = Path(data_dir)
        self.output_dir = Path(output_dir) if output_dir else None
        self.max_parallel_ocr = max_parallel_ocr
        self.max_parallel_native = max_parallel_native
        self.all_results: Dict[str, FormatTestResults] = {}

    def find_units(self, format_type: str, limit: Optional[int] = None) -> List[Path]:
        """
        Находит UNIT директории для указанного формата.

        Args:
            format_type: Тип формата (docx, pdf_scan, etc.)
            limit: Максимальное количество

        Returns:
            Список путей к UNIT директориям
        """
        subdir = self.FORMAT_DIRS.get(format_type)
        if not subdir:
            logger.error(f"Unknown format type: {format_type}")
            return []

        search_dir = self.data_dir / subdir
        if not search_dir.exists():
            logger.warning(f"Directory not found: {search_dir}")
            return []

        # Ищем UNIT_* директории
        units = list(search_dir.glob("UNIT_*"))
        units = [u for u in units if u.is_dir()]

        if limit:
            units = units[:limit]

        logger.info(f"Found {len(units)} units for {format_type} in {search_dir}")
        return units

    def test_unit(self, unit_path: Path, format_type: str) -> UnitTestResult:
        """
        Тестирует один UNIT.

        Args:
            unit_path: Путь к UNIT директории
            format_type: Тип формата

        Returns:
            UnitTestResult с метриками
        """
        result = UnitTestResult(
            unit_id=unit_path.name,
            format_type=format_type,
            file_path=str(unit_path),
        )

        try:
            # Создаем pipeline без MongoDB для тестов
            pipeline = DoclingPipeline(
                export_json=False,
                export_markdown=False,
                export_mongodb=False,
            )

            # Замер памяти и времени
            tracemalloc.start()
            start_time = time.time()

            # Обрабатываем UNIT
            pipeline_result = pipeline.process_unit(unit_path)

            end_time = time.time()
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            result.time_sec = round(end_time - start_time, 2)
            result.memory_mb = round(peak / 1024 / 1024, 2)
            result.success = pipeline_result.get("success", False)
            result.route = pipeline_result.get("route", "")

            # Подсчёт слов если успешно
            if result.success and pipeline_result.get("document"):
                try:
                    doc = pipeline_result["document"]
                    text = doc.export_to_markdown()
                    result.word_count = len(text.split())
                except Exception:
                    pass

            if not result.success:
                errors = pipeline_result.get("errors", [])
                result.error = "; ".join(errors) if errors else "Unknown error"

        except Exception as e:
            result.success = False
            result.error = str(e)
            logger.error(f"Error testing {unit_path.name}: {e}")

        return result

    def test_format(
        self,
        format_type: str,
        limit: Optional[int] = None,
        parallel: bool = False,
    ) -> FormatTestResults:
        """
        Тестирует все UNIT указанного формата.

        Args:
            format_type: Тип формата
            limit: Максимальное количество UNIT
            parallel: Использовать параллельную обработку

        Returns:
            FormatTestResults с агрегированными метриками
        """
        units = self.find_units(format_type, limit)
        results = FormatTestResults(
            format_type=format_type,
            total_units=len(units),
        )

        if not units:
            return results

        # Определяем уровень параллелизма
        is_ocr = format_type in self.OCR_FORMATS
        max_workers = self.max_parallel_ocr if is_ocr else self.max_parallel_native

        logger.info(f"Testing {len(units)} {format_type} units (OCR: {is_ocr}, workers: {max_workers})")

        if parallel and max_workers > 1:
            # Параллельная обработка
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(self.test_unit, unit, format_type): unit
                    for unit in units
                }
                for future in as_completed(futures):
                    unit_result = future.result()
                    results.results.append(unit_result)
                    results.processed += 1
                    if unit_result.success:
                        results.succeeded += 1
                    else:
                        results.failed += 1
                        if unit_result.error:
                            results.errors.append(f"{unit_result.unit_id}: {unit_result.error}")

                    # Прогресс
                    logger.info(
                        f"[{results.processed}/{results.total_units}] "
                        f"{unit_result.unit_id}: {'OK' if unit_result.success else 'FAIL'} "
                        f"({unit_result.time_sec}s, {unit_result.memory_mb}MB)"
                    )
        else:
            # Последовательная обработка
            for unit in units:
                unit_result = self.test_unit(unit, format_type)
                results.results.append(unit_result)
                results.processed += 1
                if unit_result.success:
                    results.succeeded += 1
                else:
                    results.failed += 1
                    if unit_result.error:
                        results.errors.append(f"{unit_result.unit_id}: {unit_result.error}")

                # Прогресс
                logger.info(
                    f"[{results.processed}/{results.total_units}] "
                    f"{unit_result.unit_id}: {'OK' if unit_result.success else 'FAIL'} "
                    f"({unit_result.time_sec}s, {unit_result.memory_mb}MB)"
                )

        # Вычисляем средние значения
        successful = [r for r in results.results if r.success]
        if successful:
            results.avg_time_sec = round(
                sum(r.time_sec for r in successful) / len(successful), 2
            )
            results.avg_memory_mb = round(
                sum(r.memory_mb for r in successful) / len(successful), 2
            )
            results.total_words = sum(r.word_count for r in successful)

        self.all_results[format_type] = results
        return results

    def test_all_formats(
        self,
        limit: Optional[int] = None,
        parallel: bool = False,
    ) -> Dict[str, FormatTestResults]:
        """
        Тестирует все форматы.

        Args:
            limit: Лимит UNIT на каждый формат
            parallel: Параллельная обработка

        Returns:
            Словарь результатов по форматам
        """
        formats_order = ["docx", "xlsx", "xml", "pdf_text", "pdf_scan", "jpeg"]

        for fmt in formats_order:
            logger.info(f"\n{'='*60}")
            logger.info(f"Testing format: {fmt}")
            logger.info(f"{'='*60}")
            self.test_format(fmt, limit=limit, parallel=parallel)

        return self.all_results

    def print_summary(self):
        """Выводит сводную таблицу результатов."""
        print("\n" + "=" * 80)
        print("TEST RESULTS SUMMARY")
        print("=" * 80)

        print(f"\n{'Format':<12} {'Total':<8} {'OK':<8} {'Fail':<8} {'Rate':<10} {'Avg Time':<12} {'Avg Mem':<10}")
        print("-" * 80)

        total_all = 0
        success_all = 0
        fail_all = 0

        for fmt, results in self.all_results.items():
            rate = f"{results.succeeded}/{results.total_units}" if results.total_units > 0 else "-"
            success_pct = (results.succeeded / results.total_units * 100) if results.total_units > 0 else 0

            print(
                f"{fmt:<12} {results.total_units:<8} {results.succeeded:<8} {results.failed:<8} "
                f"{rate:<10} {results.avg_time_sec:<12.2f}s {results.avg_memory_mb:<10.2f}MB"
            )

            total_all += results.total_units
            success_all += results.succeeded
            fail_all += results.failed

        print("-" * 80)
        overall_rate = f"{success_all}/{total_all}"
        print(f"{'TOTAL':<12} {total_all:<8} {success_all:<8} {fail_all:<8} {overall_rate:<10}")

        # Ошибки
        all_errors = []
        for fmt, results in self.all_results.items():
            all_errors.extend(results.errors[:5])  # Топ 5 ошибок на формат

        if all_errors:
            print("\n" + "=" * 80)
            print("TOP ERRORS")
            print("=" * 80)
            for err in all_errors[:20]:
                print(f"  - {err[:100]}")

    def save_report(self, output_path: Optional[Path] = None):
        """
        Сохраняет отчёт в JSON.

        Args:
            output_path: Путь для сохранения (опционально)
        """
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = Path(f"test_report_{timestamp}.json")

        report = {
            "timestamp": datetime.now().isoformat(),
            "data_dir": str(self.data_dir),
            "formats": {},
        }

        for fmt, results in self.all_results.items():
            report["formats"][fmt] = {
                "total_units": results.total_units,
                "succeeded": results.succeeded,
                "failed": results.failed,
                "avg_time_sec": results.avg_time_sec,
                "avg_memory_mb": results.avg_memory_mb,
                "total_words": results.total_words,
                "errors": results.errors[:10],
                "results": [asdict(r) for r in results.results],
            }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info(f"Report saved to {output_path}")
        return output_path


def find_ready2docling_dir() -> Optional[Path]:
    """Находит директорию Ready2Docling в стандартных местах."""
    base = Path(__file__).parent.parent.parent.parent  # winners_preprocessor

    candidates = [
        base / "Data" / "2025-12-20" / "Ready2Docling",
        base / "Data" / "2025-03-18" / "Ready2Docling",
        Path("/root/winners_preprocessor/final_preprocessing/Data/2025-12-20/Ready2Docling"),
    ]

    for d in candidates:
        if d.exists():
            return d

    return None


def main():
    parser = argparse.ArgumentParser(
        description="Test all UNIT formats through Docling pipeline"
    )
    parser.add_argument(
        "--format",
        choices=["docx", "xlsx", "xml", "pdf_text", "pdf_scan", "jpeg", "png"],
        help="Format to test"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Test all formats"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Max units per format (default: 10)"
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        help="Ready2Docling directory"
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Enable parallel processing"
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Save JSON report"
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        help="Path for JSON report"
    )
    args = parser.parse_args()

    # Находим директорию данных
    data_dir = args.data_dir or find_ready2docling_dir()
    if not data_dir or not data_dir.exists():
        logger.error("Ready2Docling directory not found. Use --data-dir to specify.")
        sys.exit(1)

    logger.info(f"Using data directory: {data_dir}")

    # Создаем тестер
    tester = AllUnitsTest(data_dir=data_dir)

    # Запускаем тесты
    if args.all:
        tester.test_all_formats(limit=args.limit, parallel=args.parallel)
    elif args.format:
        tester.test_format(args.format, limit=args.limit, parallel=args.parallel)
    else:
        logger.error("Specify --format or --all")
        parser.print_help()
        sys.exit(1)

    # Выводим результаты
    tester.print_summary()

    # Сохраняем отчёт
    if args.report:
        tester.save_report(args.report_path)


if __name__ == "__main__":
    main()

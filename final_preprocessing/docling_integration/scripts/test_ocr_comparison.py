#!/usr/bin/env python3
"""
OCR Comparison: Tesseract vs EasyOCR для русского языка.

Сравнивает качество распознавания текста двумя OCR движками
на тестовых PDF документах с русским текстом.

Метрики:
- Word Error Rate (WER) - если доступен эталонный текст
- Время обработки на страницу
- Использование памяти

Использование:
    python3 scripts/test_ocr_comparison.py --input-dir /path/to/pdfs --limit 10
    python3 scripts/test_ocr_comparison.py --sample  # Использует встроенные тестовые файлы
"""
import argparse
import logging
import sys
import time
import tracemalloc
from pathlib import Path
from typing import Dict, List, Optional, Any

# Добавляем родительскую директорию в путь для импорта
sys.path.insert(0, str(Path(__file__).parent.parent))

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    TesseractOcrOptions,
    EasyOcrOptions,
)


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OCRBenchmark:
    """Бенчмарк для сравнения OCR движков."""

    def __init__(self, ocr_type: str, lang: List[str]):
        """
        Args:
            ocr_type: "tesseract" или "easyocr"
            lang: Список языков для OCR
        """
        self.ocr_type = ocr_type
        self.lang = lang
        self.results: List[Dict[str, Any]] = []

    def create_pipeline_options(self) -> PdfPipelineOptions:
        """Создает PdfPipelineOptions с нужным OCR движком."""
        pdf_opts = PdfPipelineOptions()
        pdf_opts.do_ocr = True
        pdf_opts.do_table_structure = False  # Отключаем для скорости

        if self.ocr_type == "tesseract":
            pdf_opts.ocr_options = TesseractOcrOptions(lang=self.lang)
        elif self.ocr_type == "easyocr":
            pdf_opts.ocr_options = EasyOcrOptions(
                lang=self.lang,
                confidence_threshold=0.5,
                use_gpu=False
            )
        else:
            raise ValueError(f"Unknown OCR type: {self.ocr_type}")

        return pdf_opts

    def process_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Обрабатывает один PDF файл и собирает метрики.

        Returns:
            Словарь с метриками: time, memory, text_length, word_count
        """
        result = {
            "file": file_path.name,
            "ocr_type": self.ocr_type,
            "time_sec": 0,
            "memory_mb": 0,
            "text_length": 0,
            "word_count": 0,
            "success": False,
            "error": None,
        }

        try:
            # Создаем конвертер
            pdf_opts = self.create_pipeline_options()
            format_options = {
                InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_opts)
            }
            converter = DocumentConverter(format_options=format_options)

            # Запускаем с замером времени и памяти
            tracemalloc.start()
            start_time = time.time()

            doc = converter.convert(str(file_path))

            end_time = time.time()
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            # Извлекаем текст
            text = doc.document.export_to_markdown()
            words = text.split()

            result.update({
                "time_sec": round(end_time - start_time, 2),
                "memory_mb": round(peak / 1024 / 1024, 2),
                "text_length": len(text),
                "word_count": len(words),
                "success": True,
            })

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Error processing {file_path} with {self.ocr_type}: {e}")

        self.results.append(result)
        return result


def find_test_pdfs(input_dir: Optional[Path], limit: int = 10) -> List[Path]:
    """
    Находит PDF файлы для тестирования.

    Args:
        input_dir: Директория с PDF файлами
        limit: Максимальное количество файлов

    Returns:
        Список путей к PDF файлам
    """
    search_dirs = []

    if input_dir and input_dir.exists():
        search_dirs.append(input_dir)
    else:
        # Ищем в стандартных местах
        base = Path(__file__).parent.parent.parent.parent  # winners_preprocessor
        candidates = [
            base / "Data" / "2025-03-18" / "Ready2Docling" / "pdf" / "scan",
            base / "Data" / "2025-03-18" / "Merge" / "Direct",
            base / "test_data" / "pdf_scan",
        ]
        for d in candidates:
            if d.exists():
                search_dirs.append(d)

    pdf_files = []
    for d in search_dirs:
        for pdf in d.glob("**/*.pdf"):
            pdf_files.append(pdf)
            if len(pdf_files) >= limit:
                break
        if len(pdf_files) >= limit:
            break

    return pdf_files[:limit]


def print_comparison_table(tesseract_results: List[Dict], easyocr_results: List[Dict]):
    """Выводит таблицу сравнения результатов."""

    print("\n" + "=" * 80)
    print("OCR COMPARISON RESULTS")
    print("=" * 80)

    # Заголовок
    print(f"\n{'File':<30} {'OCR':<12} {'Time(s)':<10} {'Mem(MB)':<10} {'Words':<10} {'Status':<10}")
    print("-" * 80)

    # Объединяем результаты
    all_results = []
    for r in tesseract_results:
        all_results.append(r)
    for r in easyocr_results:
        all_results.append(r)

    # Группируем по файлам
    files = set(r["file"] for r in all_results)
    for f in sorted(files):
        for r in all_results:
            if r["file"] == f:
                status = "OK" if r["success"] else "FAIL"
                print(f"{r['file'][:29]:<30} {r['ocr_type']:<12} {r['time_sec']:<10} {r['memory_mb']:<10} {r['word_count']:<10} {status:<10}")

    # Статистика
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    for ocr_type, results in [("tesseract", tesseract_results), ("easyocr", easyocr_results)]:
        successful = [r for r in results if r["success"]]
        if successful:
            avg_time = sum(r["time_sec"] for r in successful) / len(successful)
            avg_memory = sum(r["memory_mb"] for r in successful) / len(successful)
            avg_words = sum(r["word_count"] for r in successful) / len(successful)
            print(f"\n{ocr_type.upper()}:")
            print(f"  Success rate: {len(successful)}/{len(results)}")
            print(f"  Avg time: {avg_time:.2f}s")
            print(f"  Avg memory: {avg_memory:.2f}MB")
            print(f"  Avg words: {avg_words:.0f}")


def main():
    parser = argparse.ArgumentParser(description="Compare Tesseract vs EasyOCR for Russian")
    parser.add_argument("--input-dir", type=Path, help="Directory with PDF files")
    parser.add_argument("--limit", type=int, default=10, help="Max files to process")
    parser.add_argument("--sample", action="store_true", help="Use sample test files")
    parser.add_argument("--tesseract-only", action="store_true", help="Test only Tesseract")
    parser.add_argument("--easyocr-only", action="store_true", help="Test only EasyOCR")
    args = parser.parse_args()

    # Находим PDF файлы
    pdf_files = find_test_pdfs(args.input_dir, args.limit)

    if not pdf_files:
        logger.error("No PDF files found for testing")
        logger.info("Specify --input-dir or place PDFs in standard locations")
        sys.exit(1)

    logger.info(f"Found {len(pdf_files)} PDF files for testing")

    # Tesseract benchmark
    tesseract_results = []
    if not args.easyocr_only:
        logger.info("Testing Tesseract OCR (rus, eng)...")
        tesseract = OCRBenchmark("tesseract", ["rus", "eng"])
        for pdf in pdf_files:
            logger.info(f"  Processing: {pdf.name}")
            tesseract.process_file(pdf)
        tesseract_results = tesseract.results

    # EasyOCR benchmark
    easyocr_results = []
    if not args.tesseract_only:
        logger.info("Testing EasyOCR (ru, en)...")
        easyocr = OCRBenchmark("easyocr", ["ru", "en"])
        for pdf in pdf_files:
            logger.info(f"  Processing: {pdf.name}")
            easyocr.process_file(pdf)
        easyocr_results = easyocr.results

    # Выводим сравнение
    print_comparison_table(tesseract_results, easyocr_results)


if __name__ == "__main__":
    main()

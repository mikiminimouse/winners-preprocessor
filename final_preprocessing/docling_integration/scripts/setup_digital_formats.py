#!/usr/bin/env python3
"""
Быстрая настройка Docling pipeline для digital форматов.
Запускает проверку системы и предлагает установку недостающих компонентов.
"""
import sys
import logging
from pathlib import Path

# Добавляем путь к проекту
_project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_project_root))

from docling_integration.system_check import run_system_check

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Главная функция."""
    logger.info("=" * 60)
    logger.info("Docling Pipeline Setup for Digital Formats")
    logger.info("=" * 60)
    logger.info("")

    # Проверка системы
    logger.info("Step 1: Checking system readiness...")
    logger.info("")
    check_result = run_system_check(verbose=True)
    logger.info("")

    # Финальный статус
    if check_result["overall_status"] == "ok":
        logger.info("✅ System ready for processing digital formats!")
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Prepare data: run docprep pipeline to populate Ready2Docling/")
        logger.info("2. Process documents:")
        logger.info("   cd /root/winners_preprocessor/final_preprocessing")
        logger.info("   python3 -m docling_integration.scripts.test_docling_pipeline \\")
        logger.info("     --data-dir Data/2025-12-20 \\")
        logger.info("     --limit 10")
        logger.info("")
        logger.info("Supported digital formats:")
        logger.info("  ✅ docx - Microsoft Word")
        logger.info("  ✅ xlsx - Microsoft Excel")
        logger.info("  ✅ pptx - Microsoft PowerPoint")
        logger.info("  ✅ pdf  - PDF with text layer")
        logger.info("  ✅ html - Web pages")
        logger.info("  ✅ xml  - Structured data")
        logger.info("  ✅ rtf  - Rich Text Format")
        return 0

    elif check_result["overall_status"] == "warning":
        logger.warning("⚠️ System ready with warnings.")
        logger.info("")
        logger.info("Some features may be disabled (e.g., MongoDB export).")
        logger.info("You can proceed with processing, but consider fixing warnings.")
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. (Optional) Fix warnings above")
        logger.info("2. Prepare data: run docprep pipeline")
        logger.info("3. Process documents with test_docling_pipeline.py")
        return 0

    else:
        logger.error("❌ System not ready. Please fix errors above.")
        logger.info("")
        logger.info("Common fixes:")
        logger.info("  • Install Docling: pip install docling>=2.0.0")
        logger.info("  • Install PyMongo: pip install pymongo>=4.0.0 (for MongoDB export)")
        logger.info("  • Start MongoDB: docker run -d -p 27018:27017 mongo (optional)")
        return 1


if __name__ == "__main__":
    sys.exit(main())

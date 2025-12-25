#!/usr/bin/env python3
"""
Скрипт для классификации файлов в директории docs
"""
import os
from pathlib import Path
from typing import Dict, List

DOCS_DIR = Path("/root/winners_preprocessor/docs")
PRESORT_DIR = Path("/root/winners_preprocessor/presort_root_files")

# Классификация файлов
CLASSIFICATION = {
    "receiver": [],
    "docprep": [],
    "docling": [],
    "OCR": [],
    "paddle": [],
    "archive": [],
    "delete": [],
    "general": []
}

# Ключевые слова для классификации
KEYWORDS = {
    "receiver": [
        "mcp", "MCP", "mongodb", "MongoDB", "mongo", "Mongo",
        "sync", "download", "zakupki", "vpn", "VPN",
        "protocol", "протокол", "receiver", "Receiver"
    ],
    "docprep": [
        "preprocessing", "Preprocessing", "PREPROCESSING",
        "docprep", "DocPrep", "DOCPREP",
        "pipeline", "Pipeline", "classifier", "converter",
        "обработка документов", "предобработка"
    ],
    "docling": [
        "docling", "Docling", "DOCLING",
        "smoldocling", "SmolDocling", "IBM Docling"
    ],
    "OCR": [
        "qwen", "Qwen", "QWEN", "qwen3",
        "granite", "Granite", "GRANITE",
        "ocr.*vision", "vision.*ocr"
    ],
    "paddle": [
        "paddleocr", "PaddleOCR", "PADDLEOCR",
        "paddle.*vl", "ocr.*vl", "paddleocr-vl"
    ]
}

# Специфичные файлы
SPECIFIC_FILES = {
    "receiver": [
        "MCP_QUICK_START.md",
        "MCP_ENV_CONFIG.md",
        "MCP_STATUS_CHECK.md",
        "USE_MCP_SERVER.md",
        "TEST_MONGODB_INSTRUCTIONS.md",
        "DOWNLOAD_PROBLEM_DIAGNOSIS.md",
        "DOWNLOAD_LIBRARIES_COMPARISON.md",
    ],
    "docprep": [
        "PREPROCESSING_ARCHIVED_COMPONENTS.md",
        "PIPELINE_ANALYSIS_CURRENT.md",
        "PIPELINE_SUMMARY.md",
        "PIPELINE_VISUALIZATION.md",
    ],
    "OCR": [
        "QWEN3_VISION_OCR_TEST.md",
        "QWEN3_VISION_TEST_README.md",
        "QWEN3_IMPLEMENTATION_REPORT.md",
        "OCR_METRICS_README.md",
    ],
    "paddle": [
        "DOCKER_BUILD_AND_PUSH_REPORT.md",
        "BUILD_AND_PUSH_REPORT_2.0.23.md",
        "cursor_docker_paddleocr_vl.md",
        "PIPELINE_ANALYSIS_CURRENT.md",  # Может быть и paddle, проверить
        "FASTAPI_FUNCTIONALITY_TEST_REPORT.md",
        "GRADIO_UI_IMPLEMENTATION_REPORT.md",
        "FINAL_VISUALIZATION_REPORT.md",
        "VISUALIZATION_IMPLEMENTATION_REPORT.md",
        "CLOUD_DEPLOYMENT_FIX_RECOMMENDATIONS.md",
        "CLOUD_DEPLOYMENT_ISSUES_REPORT.md",
        "FINAL_DEPLOYMENT_REPORT.md",
        "EXECUTION_SUMMARY.md",
        "USAGE_INSTRUCTIONS.md",
    ],
    "archive": [
        "COMPLETION_REPORT.md",
        "FINAL_COMPLETION_REPORT.md",
        "ULTIMATE_COMPLETION_REPORT.md",
        "PUSH_COMPLETION_REPORT.md",
        "FINAL_IMPLEMENTATION_REPORT.md",
        "DEPLOYMENT_REPORT.md",
        "TESTING_REPORT.md",
        "FINAL_REPORT.md",
        "COMPLETE_PROCESSING_REPORT.md",
        "docs_archive_list.md",
        "README_UPDATED.md",
    ],
    "general": [
        "PROJECT_OVERVIEW.md",
        "EXECUTIVE_SUMMARY.md",
        "DEVELOPMENT_ROADMAP.md",
        "TECHNICAL_ANALYSIS_REPORT.md",
        "BUSINESS_ANALYSIS_REPORT.md",
        "PROJECT_ANALYSIS_REPORT_BRIEF.md",
        "PROJECT_ANALYSIS_REPORT_INTERMEDIATE.md",
        "PROJECT_ANALYSIS_REPORT_INTERMEDIATE_FINAL.md",
        "PROJECT_ANALYSIS_REPORT_FULL.md",
        "CURRENT_STATE_ANALYSIS.md",
        "REORGANIZATION_REPORT.md",
        "SUMMARY.md",
        "DEPLOY.md",
        "DEVOPS_REQUEST_SHORT.md",
        "DEVOPS_REQUIREMENTS.md",
        "COMPARISON_cloudru_vs_local.md",
        "FINAL_PDF_PROCESSING_SOLUTION.md",
        "TEST_RESULTS_REPORT.md",
        "INFERENCE_TEST_README.md",
        "INFERENCE_TEST_RESULT.md",
        "QUICK_START_INFERENCE.md",
        "README.md",
    ]
}

def classify_file(filename: str) -> str:
    """Классифицирует файл"""
    filename_lower = filename.lower()
    
    # Проверка специфичных файлов
    for category, files_list in SPECIFIC_FILES.items():
        if filename in files_list:
            return category
    
    # Проверка по ключевым словам
    for category, keywords in KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in filename_lower:
                return category
    
    # По умолчанию - общие файлы
    return "general"

def main():
    """Основная функция"""
    print("Начинаю классификацию файлов в docs...")
    
    files = list(DOCS_DIR.glob("*.md"))
    print(f"Найдено файлов: {len(files)}")
    
    # Классифицируем файлы
    for file_path in files:
        category = classify_file(file_path.name)
        CLASSIFICATION[category].append(file_path.name)
    
    # Выводим статистику
    print("\nСтатистика классификации:")
    for category, files_list in CLASSIFICATION.items():
        print(f"  {category}: {len(files_list)} файлов")
    
    # Детальная классификация
    print("\n\nДетальная классификация:")
    for category, files_list in CLASSIFICATION.items():
        if files_list:
            print(f"\n{category}/ ({len(files_list)} файлов):")
            for filename in sorted(files_list):
                print(f"  - {filename}")
    
    # Сохраняем отчет
    report_path = PRESORT_DIR / "docs_classification_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Отчет о классификации файлов из docs\n\n")
        f.write("## Статистика\n\n")
        for category, files_list in CLASSIFICATION.items():
            f.write(f"- **{category}**: {len(files_list)} файлов\n")
        f.write("\n## Детальная классификация\n\n")
        for category, files_list in CLASSIFICATION.items():
            if files_list:
                f.write(f"### {category}\n\n")
                for filename in sorted(files_list):
                    f.write(f"- {filename}\n")
                f.write("\n")
    
    print(f"\nОтчет сохранен в: {report_path}")

if __name__ == "__main__":
    main()


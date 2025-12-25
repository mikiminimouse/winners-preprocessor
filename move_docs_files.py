#!/usr/bin/env python3
"""
Скрипт для перемещения файлов из docs в соответствующие директории presort_root_files
"""
import shutil
from pathlib import Path

DOCS_DIR = Path("/root/winners_preprocessor/docs")
PRESORT_DIR = Path("/root/winners_preprocessor/presort_root_files")

# Классификация файлов (из classify_docs_files.py)
FILES_TO_MOVE = {
    "receiver": [
        "DOWNLOAD_LIBRARIES_COMPARISON.md",
        "DOWNLOAD_PROBLEM_DIAGNOSIS.md",
        "MCP_ENV_CONFIG.md",
        "MCP_QUICK_START.md",
        "MCP_STATUS_CHECK.md",
        "TEST_MONGODB_INSTRUCTIONS.md",
        "USE_MCP_SERVER.md",
    ],
    "docprep": [
        "PIPELINE_SUMMARY.md",
        "PIPELINE_VISUALIZATION.md",
        "PREPROCESSING_ARCHIVED_COMPONENTS.md",
    ],
    "OCR": [
        "OCR_METRICS_README.md",
        "QWEN3_IMPLEMENTATION_REPORT.md",
        "QWEN3_VISION_OCR_TEST.md",
        "QWEN3_VISION_TEST_README.md",
    ],
    "paddle": [
        "BUILD_AND_PUSH_REPORT_2.0.23.md",
        "CLOUD_DEPLOYMENT_FIX_RECOMMENDATIONS.md",
        "CLOUD_DEPLOYMENT_ISSUES_REPORT.md",
        "DOCKER_BUILD_AND_PUSH_REPORT.md",
        "EXECUTION_SUMMARY.md",
        "FASTAPI_FUNCTIONALITY_TEST_REPORT.md",
        "FINAL_DEPLOYMENT_REPORT.md",
        "FINAL_VISUALIZATION_REPORT.md",
        "GRADIO_UI_IMPLEMENTATION_REPORT.md",
        "USAGE_INSTRUCTIONS.md",
        "VISUALIZATION_IMPLEMENTATION_REPORT.md",
        "cursor_docker_paddleocr_vl.md",
        "PIPELINE_ANALYSIS_CURRENT.md",
    ],
    "archive": [
        "COMPLETE_PROCESSING_REPORT.md",
        "COMPLETION_REPORT.md",
        "DEPLOYMENT_REPORT.md",
        "FINAL_COMPLETION_REPORT.md",
        "FINAL_IMPLEMENTATION_REPORT.md",
        "FINAL_REPORT.md",
        "PUSH_COMPLETION_REPORT.md",
        "README_UPDATED.md",
        "TESTING_REPORT.md",
        "ULTIMATE_COMPLETION_REPORT.md",
        "docs_archive_list.md",
    ],
}

def move_files():
    """Перемещает файлы по категориям"""
    moved_count = 0
    failed_count = 0
    
    for category, files_list in FILES_TO_MOVE.items():
        target_dir = PRESORT_DIR / category
        target_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"\nПеремещение файлов в {category}/:")
        for filename in files_list:
            source_path = DOCS_DIR / filename
            target_path = target_dir / filename
            
            if not source_path.exists():
                print(f"  ⚠️  {filename} - файл не найден")
                failed_count += 1
                continue
            
            try:
                if target_path.exists():
                    # Если файл уже существует, добавляем суффикс
                    base_name = source_path.stem
                    extension = source_path.suffix
                    counter = 1
                    while target_path.exists():
                        target_path = target_dir / f"{base_name}_{counter}{extension}"
                        counter += 1
                
                shutil.move(str(source_path), str(target_path))
                print(f"  ✅ {filename} → {target_path.name}")
                moved_count += 1
            except Exception as e:
                print(f"  ❌ {filename} - ошибка: {e}")
                failed_count += 1
    
    print(f"\n\nИтого:")
    print(f"  Успешно перемещено: {moved_count}")
    print(f"  Ошибок: {failed_count}")
    
    return moved_count, failed_count

if __name__ == "__main__":
    print("Начинаю перемещение файлов из docs...")
    move_files()


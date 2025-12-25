#!/usr/bin/env python3
"""
Скрипт для классификации и перемещения файлов из корня проекта
в соответствующие директории presort_root_files
"""
import os
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

# Базовые пути
ROOT_DIR = Path("/root/winners_preprocessor")
PRESORT_DIR = ROOT_DIR / "presort_root_files"

# Категории файлов
CATEGORIES = {
    "docprep": [],
    "receiver": [],
    "docling": [],
    "paddle": [],
    "archive": [],
    "delete": []
}

# Ключевые слова для классификации
KEYWORDS = {
    "docprep": [
        "preprocessing", "docprep", "PREPROCESSING", "DOCPREP",
        "pipeline", "PIPELINE", "cleanup", "CLEANUP", "refactoring", "REFACTORING"
    ],
    "receiver": [
        "receiver", "RECEIVER", "sync", "SYNC", "download", "DOWNLOAD",
        "webui", "WEBUI", "vpn", "VPN", "mongo", "MONGO", "mongodb", "MONGODB"
    ],
    "docling": [
        "docling", "DOCLING", "smoldocling", "SMOLDOCLING"
    ],
    "paddle": [
        "paddle", "PADDLE", "granite", "GRANITE", "qwen", "QWEN",
        "ocr", "OCR", "vision", "VISION", "vlm", "VLM"
    ]
}

# Файлы, которые должны остаться в корне
KEEP_IN_ROOT = {
    "README.md", ".gitignore", ".env", ".env.example",
    "pyproject.toml", "requirements.txt"
}

# Файлы для удаления (временные, тестовые без ценности)
DELETE_PATTERNS = [
    "=2.6.0", "=4.0.0",  # Версионные файлы
    "test_другой_файл.py",  # Тестовые файлы без смысла
    "metrics_download.csv",  # Временные CSV
    "vitaly_bychkov.ovpn",  # VPN конфиг (должен быть в другом месте)
    "token_only_test.py",  # Временные тесты
    "combined_token_test.py",  # Временные тесты
]

# Файлы для архива (устаревшие)
ARCHIVE_PATTERNS = [
    "FINAL_working_solution.py",
    "preprocessing_cli_temp.py",
    "requirements_test.txt",
]

# Специфичные файлы по категориям
SPECIFIC_FILES = {
    "receiver": [
        # CLI и документация receiver
        "CLI_LAUNCH_GUIDE.md", "CLI_ERRORS_FIXED.md", "CLI_FIXES_AND_TESTING.md",
        "SYNC_DB_CLI_TESTING_GUIDE.md", "TESTING_CLI.md", "TESTING_INSTRUCTIONS.md",
        # Отчеты receiver
        "RECEIVER_REFACTORING_REPORT.md", "RECEIVER_REFACTORING_COMPLETE.md",
        "RECEIVER_TESTING_REPORT.md", "RECEIVER_FINAL_STATUS_REPORT.md",
        "RECEIVER_WEBUI_REFACTORING_REPORT.md", "FINAL_RECEIVER_WEBUI_TEST_REPORT.md",
        # VPN и MongoDB
        "VPN_MONGO_SETUP_SUMMARY.md", "VPN_SETUP_COMPLETE.md", "VPN_SETUP_FINAL_REPORT.md",
        "MONGODB_TEST_INSTRUCTIONS.md",
        # WebUI
        "WEBUI_RESTART_INSTRUCTIONS.md", "WEBUI_RESTART_REPORT.md", "WEBUI_TEST_REPORT.md",
        # Скрипты receiver
        "restart_webui.sh", "route-up-zakupki.sh", "run_downloader.sh",
        "sync_remote_protocols.py", "process_protocols_worker.py",
        "download_one_simple.py", "vpn_download_test.py",
        # Тесты receiver
        "test_sync_db_cli.py", "test_sync_db_complete.py", "test_sync_db_vpn.py",
        "test_sync_performance.py", "test_sync_performance_fixed.py",
        "test_full_sync_db_functionality.py", "test_real_sync_fix.py",
        "test_manual_vpn_sync.py", "test_direct_mongo_connection.py",
        "test_mongo_direct.py", "test_mongodb.py",
        "test_download_alternative.py", "test_download_documents.py",
        "test_cli_date_range.py", "test_cli_full_sync.py",
        "test_cli_menu_1.py", "test_cli_simple.py",
        "test_webui_components.py", "test_webui_live.py", "test_webui_tabs.py",
        "test_complete_system.py", "test_functionality.py",
        "test_api_connection.py", "test_api_direct.py", "test_api_simple.py",
        "monitor_metrics.py", "mcp_http_server.py",
    ],
    "docprep": [
        # Отчеты docprep
        "PREPROCESSING_CLEANUP_FINAL_REPORT.md", "PREPROCESSING_CLEANUP_REPORT.md",
        "PREPROCESSING_COMPONENTS_ANALYSIS.md",
        "PREPROCESSING_REFACTORING_IMPLEMENTATION_REPORT.md",
        "PREPROCESSING_REFACTORING_WEBUI_PLAN_RU.md",
        "PREPROCESSING_REFATORING_WEBUI_PLAN_RU.md",
        # Pipeline отчеты
        "PIPELINE_TEST_FINAL_REPORT.md", "PIPELINE_TEST_REPORT.md",
        "FINAL_PIPELINE_REPORT.md", "FINAL_TESTING_REPORT.md",
        # Рефакторинг
        "REFACTORING_API_FINAL.md", "REFACTORING_COMPLETE.md",
        "REFACTORING_COMPLETE_PHASE2.md", "QUICK_START_REFACTORED.md",
        # Тесты docprep
        "test_pipeline_existing_files.py", "run_full_pipeline_test.py",
        "test_10_units_all_pages.py", "test_20_units_batch.py",
        "comparison_report_20_units.md",
        # Утилиты
        "clean_and_process.py", "fix_paths.py", "generate_final_report.py",
    ],
    "docling": [
        # Docling файлы
        "docling_api_example.py",
        # Smoldocling тесты
        "test_full_pdf_smoldocling.py", "test_real_pdf_smoldocling.py",
        "test_10_units_smoldocling.py", "test_smoldocling_3files.py",
        "test_smoldocling_fixed.py", "test_smoldocling_single.py",
        "simple_test_smoldocling.py",
        # Smoldocling процессоры
        "smoldocling_pdf_processor.py", "enhanced_pdf_smoldocling_processor.py",
        "real_pdf_processor.py",
        # Тесты docling
        "test_native_docling_with_remote_vlm.py",
        "test_pdf_direct.py", "test_pdf_direct_final.py",
        "test_single_pdf_direct.py", "test_specific_pdf.py",
        "test_10_pdfs_real.py", "REAL_test_10_pdfs.py",
        "final_test_10_pdfs.py",
        "test_pdf_thumbnail.py", "test_debug_thumbnail.py",
    ],
    "paddle": [
        # Granite файлы
        "CORRECT_granite_vlm_test.py", "debug_granite_metadata.py",
        # Qwen файлы
        "test_qwen3_vision_ocr.py", "test_qwen3_vision_ast.py",
        "test_qwen3_simple.py", "test_qwen3_ocr_metrics.py",
        # Paddle/OCR документация
        "cursor_docker_paddleocsr_vl.md",
        "BUILD_AND_PUSH_REPORT_2.0.24.md",  # Отчет о сборке OCR сервиса
        # S3 и инфраструктура
        "s3_check.py",
        # Тесты inference
        "test_inference.py", "test_inference_simple.py",
        # Другие тесты
        "test_visualization.py", "test_fixes.py",
        "test_paths_fix.py", "test_protocol_document_fix.py",
        "test_protocol_processing_fix.py",
    ],
    "archive": [
        # Устаревшие отчеты
        "COMPLETE_REPORT.md", "FIXES_REPORT.md", "FIXES_SUMMARY.md",
        "IMPLEMENTATION_REPORT.md", "TEST_RESULTS.md",
        # Миграция (устаревшие)
        "MIGRATION_PLAN.md", "MIGRATION_STATUS.md", "MIGRATION_SUMMARY.md",
        # Устаревшие скрипты
        "direct_api_test.py",
        # Устаревшие тесты
        "test_direct_mongo_connection.py",  # Дубликат
    ],
}

def classify_file(filename: str) -> str:
    """Классифицирует файл по категориям"""
    filename_lower = filename.lower()
    
    # Проверка на удаление
    if filename in DELETE_PATTERNS:
        return "delete"
    
    # Проверка на архив
    if filename in ARCHIVE_PATTERNS:
        return "archive"
    
    # Проверка специфичных файлов
    for category, files_list in SPECIFIC_FILES.items():
        if filename in files_list:
            return category
    
    # Проверка по ключевым словам
    for category, keywords in KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in filename_lower:
                return category
    
    # Специальные случаи
    if filename.startswith("test_"):
        # Тестовые файлы - проверяем по содержимому ключевых слов
        if any(kw in filename_lower for kw in ["receiver", "sync", "download", "vpn", "mongo"]):
            return "receiver"
        elif any(kw in filename_lower for kw in ["docling", "smoldocling"]):
            return "docling"
        elif any(kw in filename_lower for kw in ["paddle", "granite", "qwen", "ocr", "vision"]):
            return "paddle"
        elif any(kw in filename_lower for kw in ["preprocessing", "pipeline", "docprep"]):
            return "docprep"
        else:
            # Общие тесты - в архив
            return "archive"
    
    if filename.endswith("_report.md") or filename.endswith("_REPORT.md"):
        # Отчеты - классифицируем по ключевым словам
        if any(kw in filename_lower for kw in ["receiver", "sync", "download", "webui"]):
            return "receiver"
        elif any(kw in filename_lower for kw in ["preprocessing", "pipeline", "docprep"]):
            return "docprep"
        elif any(kw in filename_lower for kw in ["docling"]):
            return "docling"
        elif any(kw in filename_lower for kw in ["paddle", "granite", "qwen", "ocr"]):
            return "paddle"
        else:
            return "archive"
    
    # По умолчанию - в архив
    return "archive"

def get_files_to_process() -> List[Path]:
    """Получает список файлов для обработки"""
    files = []
    for item in ROOT_DIR.iterdir():
        if item.is_file() and item.name not in KEEP_IN_ROOT:
            files.append(item)
    return files

def move_file(file_path: Path, category: str) -> bool:
    """Перемещает файл в соответствующую директорию"""
    target_dir = PRESORT_DIR / category
    target_dir.mkdir(parents=True, exist_ok=True)
    
    target_path = target_dir / file_path.name
    
    try:
        if target_path.exists():
            # Если файл уже существует, добавляем суффикс
            base_name = file_path.stem
            extension = file_path.suffix
            counter = 1
            while target_path.exists():
                target_path = target_dir / f"{base_name}_{counter}{extension}"
                counter += 1
        
        shutil.move(str(file_path), str(target_path))
        return True
    except Exception as e:
        print(f"Ошибка при перемещении {file_path}: {e}")
        return False

def main():
    """Основная функция"""
    print("Начинаю классификацию и перемещение файлов...")
    
    files = get_files_to_process()
    print(f"Найдено файлов для обработки: {len(files)}")
    
    # Классифицируем файлы
    classification_results = {}
    for file_path in files:
        category = classify_file(file_path.name)
        classification_results[file_path] = category
        CATEGORIES[category].append(file_path.name)
    
    # Выводим статистику
    print("\nСтатистика классификации:")
    for category, files_list in CATEGORIES.items():
        print(f"  {category}: {len(files_list)} файлов")
    
    # Подтверждение
    print("\nФайлы будут перемещены в следующие директории:")
    for category, files_list in CATEGORIES.items():
        if files_list:
            print(f"\n{category}/ ({len(files_list)} файлов):")
            for filename in sorted(files_list)[:10]:  # Показываем первые 10
                print(f"  - {filename}")
            if len(files_list) > 10:
                print(f"  ... и еще {len(files_list) - 10} файлов")
    
    # Перемещаем файлы
    print("\n\nНачинаю перемещение файлов...")
    moved_count = 0
    failed_count = 0
    
    for file_path, category in classification_results.items():
        if move_file(file_path, category):
            moved_count += 1
        else:
            failed_count += 1
    
    print(f"\nПеремещение завершено:")
    print(f"  Успешно перемещено: {moved_count}")
    print(f"  Ошибок: {failed_count}")
    
    # Сохраняем отчет
    report_path = PRESORT_DIR / "classification_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Отчет о классификации файлов\n\n")
        f.write(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("## Статистика\n\n")
        for category, files_list in CATEGORIES.items():
            f.write(f"- **{category}**: {len(files_list)} файлов\n")
        f.write("\n## Детальная классификация\n\n")
        for category, files_list in CATEGORIES.items():
            if files_list:
                f.write(f"### {category}\n\n")
                for filename in sorted(files_list):
                    f.write(f"- {filename}\n")
                f.write("\n")
    
    print(f"\nОтчет сохранен в: {report_path}")

if __name__ == "__main__":
    main()


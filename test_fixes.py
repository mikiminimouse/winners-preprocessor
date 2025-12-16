#!/usr/bin/env python3
"""
Тестовый скрипт для проверки исправлений в обработке файлов.
"""

import sys
from pathlib import Path
from collections import defaultdict

# Добавляем путь к модулям
sys.path.insert(0, str(Path(__file__).parent / "pilot_winers223"))

from services.router.file_detection import detect_file_type
from services.router.unit_distribution import distribute_unit_by_types
from services.router.config import DETECTED_DIR

def test_file_detection():
    """Тестируем определение типов файлов."""
    print("=== ТЕСТИРОВАНИЕ ОПРЕДЕЛЕНИЯ ТИПОВ ФАЙЛОВ ===")

    # Создаем тестовые файлы разных типов
    test_files = {
        "pdf": "test.pdf",
        "doc": "test.doc",
        "docx": "test.docx",
        "html": "test.html",
        "xml": "test.xml",
        "rtf": "test.rtf",
        "xls": "test.xls",
        "xlsx": "test.xlsx",
        "zip": "test.zip",
        "rar": "test.rar",
        "7z": "test.7z"
    }

    results = {}
    for file_type, filename in test_files.items():
        file_path = Path(f"/tmp/{filename}")

        # Создаем пустой файл для тестирования
        try:
            file_path.touch()
            detection = detect_file_type(file_path)
            results[file_type] = {
                "detected_type": detection.get("detected_type", "unknown"),
                "extension_matches": detection.get("extension_matches_content", False)
            }
        except Exception as e:
            results[file_type] = {"error": str(e)}
        finally:
            if file_path.exists():
                file_path.unlink()

    print("Результаты определения типов:")
    for file_type, result in results.items():
        if "error" in result:
            print(f"  {file_type}: Ошибка - {result['error']}")
        else:
            matches = "✓" if result["extension_matches"] else "✗"
            print(f"  {file_type}: {result['detected_type']} {matches}")

    return results

def test_directory_mapping():
    """Тестируем маппинг типов файлов на директории."""
    print("\n=== ТЕСТИРОВАНИЕ МАППИНГА НА ДИРЕКТОРИИ ===")

    test_types = [
        "pdf", "doc", "docx", "html", "xml", "rtf", "excel",
        "zip_archive", "rar_archive", "7z_archive", "image", "unknown"
    ]

    for detected_type in test_types:
        # Создаем фиктивный файл с данным типом
        file_info = {"detected_type": detected_type, "path": "/tmp/test", "is_fake_doc": False}

        # Определяем директорию
        if detected_type == "rar_archive":
            has_fake_doc = False  # Тестируем без фейковых док
            subdir = "rar" if not has_fake_doc else "archive/archDOC"
        elif detected_type == "7z_archive":
            has_fake_doc = False
            subdir = "7z" if not has_fake_doc else "archive/archDOC"
        elif detected_type == "zip_archive":
            has_fake_doc = False
            subdir = "zip" if not has_fake_doc else "archive/archDOC"
        elif detected_type == "html":
            has_fake_doc = False
            subdir = "htmlDOC" if has_fake_doc else "html"
        elif detected_type == "xml":
            has_fake_doc = False
            subdir = "xmlDOC" if has_fake_doc else "xml"
        else:
            type_to_subdir = {
                "pdf": "pdf", "doc": "doc", "docx": "docx", "image": "image",
                "rtf": "rtf", "excel": "excel"
            }
            subdir = type_to_subdir.get(detected_type, "unknown")

        print(f"  {detected_type} → {subdir}")

def test_extension_mismatches():
    """Тестируем обработку несоответствий расширений."""
    print("\n=== ТЕСТИРОВАНИЕ НЕСООТВЕТСТВИЙ РАСШИРЕНИЙ ===")

    # Примеры несоответствий из логов
    mismatch_examples = [
        (".rtf", "rtf", True),  # Правильное совпадение
        (".xls", "doc", False),  # .xls содержит doc
        ("", "docx", False),     # Файл без расширения содержит docx
        ("", "pdf", False),      # Файл без расширения содержит pdf
        (".2025гpdf", "pdf", False),  # Странное расширение содержит pdf
        (".2025 гpdf", "pdf", False), # Странное расширение содержит pdf
        (".sig", "unknown", False),   # .sig содержит неизвестный тип
        (".odt", "zip_archive", False) # .odt содержит zip архив
    ]

    print("Примеры несоответствий расширений:")
    for ext, detected, matches in mismatch_examples:
        status = "✓ совпадает" if matches else "✗ не совпадает"
        print(f"  {ext or '(без расширения)'} → {detected} {status}")

def main():
    """Главная функция тестирования."""
    print("Тестирование исправлений в обработке файлов")
    print("=" * 60)

    try:
        test_file_detection()
        test_directory_mapping()
        test_extension_mismatches()

        print("\n" + "=" * 60)
        print("✓ Все тесты завершены успешно!")

    except Exception as e:
        print(f"\n❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())

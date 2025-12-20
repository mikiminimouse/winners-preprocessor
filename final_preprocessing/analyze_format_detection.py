#!/usr/bin/env python3
"""
Анализ определения форматов файлов.
"""
import sys
from pathlib import Path
from collections import Counter, defaultdict

# Добавляем путь к модулю
sys.path.insert(0, str(Path(__file__).parent))

from docprep.utils.file_ops import detect_file_type

def analyze_format_detection():
    """Анализ определения форматов файлов."""
    input_dir = Path("Data/2025-12-20/Input")
    
    if not input_dir.exists():
        print(f"Директория не найдена: {input_dir}")
        return
    
    # Находим все файлы
    files = []
    for unit_dir in input_dir.iterdir():
        if unit_dir.is_dir() and unit_dir.name.startswith("UNIT_"):
            for file_path in unit_dir.iterdir():
                if file_path.is_file() and file_path.name not in ["manifest.json", "audit.log.jsonl"]:
                    files.append(file_path)
    
    print(f"Найдено файлов: {len(files)}")
    
    # Анализируем определение форматов
    detection_results = []
    extension_to_detected = defaultdict(list)
    problems = []
    
    for file_path in files[:100]:  # Анализируем первые 100 файлов
        extension = file_path.suffix.lower().lstrip(".")
        detection = detect_file_type(file_path)
        
        detected_type = detection.get("detected_type", "unknown")
        mime_type = detection.get("mime_type", "unknown")
        classification = detection.get("classification", "unknown")
        
        detection_results.append({
            "file": file_path.name,
            "extension": extension,
            "detected_type": detected_type,
            "mime_type": mime_type,
            "classification": classification,
        })
        
        extension_to_detected[extension].append(detected_type)
        
        # Проверяем проблемы
        expected_types = {
            ".pdf": "pdf",
            ".docx": "docx",
            ".xlsx": "xlsx",
            ".pptx": "pptx",
            ".doc": "doc",
            ".xls": "xls",
            ".ppt": "ppt",
            ".zip": "zip_archive",
            ".rar": "rar_archive",
            ".7z": "7z_archive",
            ".jpg": "jpeg",
            ".jpeg": "jpeg",
            ".png": "png",
            ".rtf": "rtf",
        }
        
        expected = expected_types.get(file_path.suffix.lower())
        if expected and detected_type != expected:
            problems.append({
                "file": file_path.name,
                "extension": extension,
                "expected": expected,
                "detected": detected_type,
                "mime": mime_type,
            })
    
    # Статистика по расширениям
    print("\n📊 Статистика определения типов по расширениям:")
    for ext, detected_types in sorted(extension_to_detected.items()):
        type_counts = Counter(detected_types)
        print(f"\n  .{ext}:")
        for detected_type, count in type_counts.most_common():
            print(f"    {detected_type}: {count}")
    
    # Проблемы
    if problems:
        print(f"\n❌ Найдено проблем с определением форматов: {len(problems)}")
        for problem in problems[:20]:
            print(f"  {problem['file']}:")
            print(f"    Расширение: .{problem['extension']}")
            print(f"    Ожидалось: {problem['expected']}")
            print(f"    Определено: {problem['detected']}")
            print(f"    MIME: {problem['mime']}")
    else:
        print("\n✅ Проблем с определением форматов не найдено")

if __name__ == "__main__":
    analyze_format_detection()

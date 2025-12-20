#!/usr/bin/env python3
"""
Исправление структуры Ready2Docling:
1. Перемещение файлов из поддиректории files в корень UNIT
2. Перемещение PDF UNIT из корня pdf в pdf/scan или pdf/text
"""
import sys
from pathlib import Path
import shutil

sys.path.insert(0, str(Path(__file__).parent))

from docprep.utils.file_ops import detect_file_type
from docprep.core.manifest import load_manifest

def fix_files_subdirectory(date: str):
    """Перемещает файлы из поддиректории files в корень UNIT."""
    base_dir = Path("Data") / date / "Ready2Docling"
    
    print("ИСПРАВЛЕНИЕ ПОДДИРЕКТОРИИ FILES")
    print("=" * 80)
    
    fixed = 0
    for unit_dir in base_dir.rglob("UNIT_*"):
        if not unit_dir.is_dir():
            continue
        
        files_dir = unit_dir / "files"
        if files_dir.exists() and files_dir.is_dir():
            # Перемещаем файлы из files в корень UNIT
            files = [f for f in files_dir.iterdir() if f.is_file()]
            for file_path in files:
                target_file = unit_dir / file_path.name
                if not target_file.exists():
                    shutil.move(str(file_path), str(target_file))
                    fixed += 1
            
            # Удаляем пустую директорию files
            try:
                files_dir.rmdir()
            except:
                pass
    
    print(f"✅ Перемещено файлов: {fixed}")

def fix_pdf_sorting(date: str):
    """Перемещает PDF UNIT из корня pdf в pdf/scan или pdf/text."""
    base_dir = Path("Data") / date / "Ready2Docling" / "pdf"
    
    print("\nИСПРАВЛЕНИЕ СОРТИРОВКИ PDF")
    print("=" * 80)
    
    if not base_dir.exists():
        print("Директория pdf не существует")
        return
    
    # Находим UNIT в корне pdf
    root_units = [d for d in base_dir.iterdir() if d.is_dir() and d.name.startswith("UNIT_")]
    print(f"Найдено UNIT в корне pdf: {len(root_units)}")
    
    scan_dir = base_dir / "scan"
    text_dir = base_dir / "text"
    scan_dir.mkdir(parents=True, exist_ok=True)
    text_dir.mkdir(parents=True, exist_ok=True)
    
    moved_to_scan = 0
    moved_to_text = 0
    
    for unit_dir in root_units:
        # Определяем needs_ocr из manifest или файла
        manifest_path = unit_dir / "manifest.json"
        needs_ocr = True  # По умолчанию scan
        
        if manifest_path.exists():
            try:
                manifest = load_manifest(unit_dir)
                files = manifest.get("files", [])
                if files:
                    pdf_needs_ocr = []
                    for file_info in files:
                        needs_ocr_val = file_info.get("needs_ocr", True)
                        if needs_ocr_val is not None and needs_ocr_val != "unknown":
                            pdf_needs_ocr.append(bool(needs_ocr_val))
                    
                    if pdf_needs_ocr:
                        needs_ocr = all(pdf_needs_ocr) if pdf_needs_ocr else True
            except:
                pass
        
        # Если не нашли в manifest, проверяем файлы
        if needs_ocr is True:
            pdf_files = [f for f in unit_dir.iterdir() if f.is_file() and f.suffix.lower() == ".pdf"]
            if pdf_files:
                detection = detect_file_type(pdf_files[0])
                needs_ocr = detection.get("needs_ocr", True)
        
        # Перемещаем UNIT
        if needs_ocr:
            target_dir = scan_dir / unit_dir.name
            if not target_dir.exists():
                shutil.move(str(unit_dir), str(target_dir))
                moved_to_scan += 1
        else:
            target_dir = text_dir / unit_dir.name
            if not target_dir.exists():
                shutil.move(str(unit_dir), str(target_dir))
                moved_to_text += 1
    
    print(f"✅ Перемещено в pdf/scan: {moved_to_scan}")
    print(f"✅ Перемещено в pdf/text: {moved_to_text}")

if __name__ == "__main__":
    date = "2025-12-20"
    fix_files_subdirectory(date)
    fix_pdf_sorting(date)
    print("\n✅ ИСПРАВЛЕНИЕ ЗАВЕРШЕНО")


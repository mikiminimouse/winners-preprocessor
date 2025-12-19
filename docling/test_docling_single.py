#!/usr/bin/env python3
"""
Тестовый скрипт для обработки одного unit через Docling API.
"""
import requests
import json
import sys
from pathlib import Path

DOCLING_API = "http://localhost:8000/process"

def test_single_unit(unit_id: str):
    """Тестирует обработку одного unit."""
    print(f"\n{'='*80}")
    print(f"ТЕСТИРОВАНИЕ ОБРАБОТКИ UNIT: {unit_id}")
    print(f"{'='*80}\n")
    
    # Проверяем наличие unit'а в normalized
    unit_dir = Path(f"/root/winners_preprocessor/normalized/{unit_id}/files")
    if not unit_dir.exists():
        print(f"❌ Unit directory not found: {unit_dir}")
        return False
    
    files = list(unit_dir.glob("*"))
    if not files:
        print(f"❌ No files found in unit directory")
        return False
    
    print(f"✅ Found {len(files)} files in unit directory")
    
    # Подготавливаем запрос
    # Для теста используем упрощенный формат
    file_info = {
        "path": str(files[0]),
        "original_name": files[0].name,
        "detected_type": "pdf",  # Упрощенно
        "needs_ocr": False,
        "file_id": "test_file_id",
        "route": "pdf_text"
    }
    
    payload = {
        "unit_id": unit_id,
        "manifest": f"mongodb://{unit_id}",
        "files": [file_info],
        "route": "pdf_text"
    }
    
    print(f"\nОтправка запроса в Docling API...")
    print(f"  Unit ID: {unit_id}")
    print(f"  File: {files[0].name}")
    print(f"  Route: pdf_text\n")
    
    try:
        response = requests.post(
            DOCLING_API,
            json=payload,
            timeout=60
        )
        
        print(f"HTTP Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ Успешная обработка!")
            print(f"   Status: {result.get('status')}")
            print(f"   Processing time: {result.get('processing_time', 0):.2f}s")
            print(f"   Output files: {len(result.get('output_files', []))}")
            
            # Проверяем output файлы
            output_dir = Path(f"/root/winners_preprocessor/output/{unit_id}")
            if output_dir.exists():
                output_files = list(output_dir.glob("*"))
                print(f"\n✅ Output файлы созданы:")
                for of in output_files[:5]:
                    size = of.stat().st_size if of.exists() else 0
                    print(f"   - {of.name} ({size} bytes)")
            
            return True
        else:
            print(f"\n❌ Ошибка обработки:")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text[:500]}")
            return False
            
    except Exception as e:
        print(f"\n❌ Исключение при обработке:")
        print(f"   {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Получаем первый доступный unit_id
    unit_dirs = list(Path("/root/winners_preprocessor/normalized").glob("UNIT_*"))
    if not unit_dirs:
        print("❌ No units found in normalized/")
        sys.exit(1)
    
    test_unit_id = unit_dirs[0].name
    print(f"Выбран unit для теста: {test_unit_id}\n")
    
    success = test_single_unit(test_unit_id)
    sys.exit(0 if success else 1)


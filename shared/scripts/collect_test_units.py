#!/usr/bin/env python3
"""
Скрипт для сбора 10 UNIT'ов из normalized/ с needs_ocr: false для тестирования Qwen3-VL-8B.
"""
import json
import sys
from pathlib import Path
from typing import List, Dict, Any

NORMALIZED_DIR = Path("/root/winners_preprocessor/normalized")
OUTPUT_FILE = Path("/root/winners_preprocessor/test_units_list.json")


def scan_units() -> List[Dict[str, Any]]:
    """Сканирует все UNIT'ы в normalized/ и собирает информацию о них."""
    units = []
    
    if not NORMALIZED_DIR.exists():
        print(f"❌ Директория {NORMALIZED_DIR} не найдена")
        return units
    
    # Сканируем все директории UNIT_*
    for unit_dir in sorted(NORMALIZED_DIR.glob("UNIT_*")):
        manifest_path = unit_dir / "manifest.json"
        
        if not manifest_path.exists():
            continue
        
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            
            # Проверяем, есть ли файлы с needs_ocr: false
            files_without_ocr = [
                f for f in manifest.get("files", [])
                if not f.get("needs_ocr", True)
            ]
            
            if files_without_ocr:
                unit_info = {
                    "unit_id": manifest.get("unit_id"),
                    "route": manifest.get("processing", {}).get("route"),
                    "created_at": manifest.get("created_at"),
                    "files": files_without_ocr,
                    "manifest_path": str(manifest_path),
                    "unit_dir": str(unit_dir)
                }
                units.append(unit_info)
                
        except Exception as e:
            print(f"⚠️  Ошибка чтения {manifest_path}: {e}")
            continue
    
    return units


def select_diverse_units(units: List[Dict[str, Any]], count: int = 10) -> List[Dict[str, Any]]:
    """Выбирает разнообразные UNIT'ы (разные типы файлов)."""
    selected = []
    
    # Группируем по типам файлов
    by_type = {}
    for unit in units:
        file_type = unit["route"] or "unknown"
        if file_type not in by_type:
            by_type[file_type] = []
        by_type[file_type].append(unit)
    
    # Выбираем по одному из каждой категории, затем заполняем остальные
    types_order = ["pdf_text", "docx", "image_ocr", "html_text", "mixed"]
    
    for route_type in types_order:
        if route_type in by_type and len(selected) < count:
            selected.append(by_type[route_type].pop(0))
    
    # Заполняем остальные
    remaining = []
    for route_type, unit_list in by_type.items():
        remaining.extend(unit_list)
    
    while len(selected) < count and remaining:
        selected.append(remaining.pop(0))
    
    return selected[:count]


def main():
    """Главная функция."""
    print("=" * 70)
    print("СБОР UNIT'ОВ ДЛЯ ТЕСТИРОВАНИЯ QWEN3-VL-8B")
    print("=" * 70)
    print()
    
    print("📂 Сканирование normalized/...")
    all_units = scan_units()
    print(f"   Найдено UNIT'ов с needs_ocr: false: {len(all_units)}")
    
    if not all_units:
        print("❌ Не найдено UNIT'ов с needs_ocr: false")
        sys.exit(1)
    
    print("\n🎯 Выбор 10 разнообразных UNIT'ов...")
    selected_units = select_diverse_units(all_units, count=10)
    
    print(f"   Выбрано UNIT'ов: {len(selected_units)}")
    
    # Статистика по типам
    type_stats = {}
    for unit in selected_units:
        route = unit.get("route", "unknown")
        type_stats[route] = type_stats.get(route, 0) + 1
    
    print("\n📊 Распределение по типам:")
    for route, count in sorted(type_stats.items()):
        print(f"   - {route}: {count}")
    
    # Сохраняем список
    output_data = {
        "total_units": len(selected_units),
        "collected_at": str(Path(__file__).stat().st_mtime),
        "units": selected_units
    }
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Список сохранен: {OUTPUT_FILE}")
    print("\n📋 Выбранные UNIT'ы:")
    for i, unit in enumerate(selected_units, 1):
        files_info = ", ".join([f["original_name"] for f in unit["files"][:2]])
        if len(unit["files"]) > 2:
            files_info += f" (+{len(unit['files'])-2} еще)"
        print(f"   {i}. {unit['unit_id']} ({unit.get('route', 'unknown')}) - {files_info}")
    
    print("\n✅ Готово!")
    return 0


if __name__ == "__main__":
    sys.exit(main())


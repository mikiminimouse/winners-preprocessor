#!/usr/bin/env python3
import json
from pathlib import Path

# Загружаем список UNIT'ов
input_file = Path("/root/winners_preprocessor/test_ocr_units_list.json")
output_file = Path("/root/winners_preprocessor/test_ocr_units_fixed.json")

with open(input_file, "r", encoding="utf-8") as f:
    data = json.load(f)

# Корректируем пути
for unit in data["units"]:
    for file_info in unit["files"]:
        old_path = file_info["path"]
        # Заменяем /app/ на /root/winners_preprocessor/
        new_path = old_path.replace("/app/", "/root/winners_preprocessor/")
        file_info["path"] = new_path
        print(f"Исправлен путь: {old_path} -> {new_path}")

# Сохраняем исправленный файл
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"Исправленный файл сохранен: {output_file}")


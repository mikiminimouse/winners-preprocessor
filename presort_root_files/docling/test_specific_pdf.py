#!/usr/bin/env python3
"""Тест конкретного PDF который указал пользователь"""
import sys
sys.path.insert(0, "/root/winners_preprocessor")
from REAL_test_10_pdfs import extract_text_from_pdf, extract_metadata, create_markdown
from pathlib import Path
import json

pdf = Path("/root/winners_preprocessor/pilot_winers223/data/pending/direct/pdf/UNIT_0c3fb63690914cd8/files/Протокол 1348-1 от 27.11.2025 ПДО.pdf")

print(f"📄 Обработка: {pdf.name}\n")

# Извлечение
result = extract_text_from_pdf(pdf)
text = result["text"]
tables = result["tables"]

print(f"✅ Текст: {len(text)} символов")
print(f"✅ Таблицы: {len(tables)}")
print(f"✅ Это скан: {result.get('is_scan', False)}")

# Первые 1000 символов
print(f"\n📝 Первые 1000 символов:\n")
print(text[:1000])
print("\n...")

# Метаданные
print(f"\n🔍 Извлечение метаданных через Granite...\n")
metadata = extract_metadata(text)

print("📊 Метаданные:")
for k, v in metadata.items():
    if k not in ['полный_текст', 'таблицы']:
        print(f"   {k}: {v}")

# Сохранение
output = Path("output_SPECIFIC")
output.mkdir(exist_ok=True)

md = create_markdown(pdf.name, text, tables, metadata)
md_file = output / f"{pdf.stem}.md"
with open(md_file, 'w', encoding='utf-8') as f:
    f.write(md)

metadata["полный_текст"] = text
metadata["таблицы"] = tables
meta_file = output / f"{pdf.stem}_metadata.json"
with open(meta_file, 'w', encoding='utf-8') as f:
    json.dump(metadata, f, indent=2, ensure_ascii=False)

print(f"\n✅ Сохранено:")
print(f"   MD: {md_file}")
print(f"   JSON: {meta_file}")


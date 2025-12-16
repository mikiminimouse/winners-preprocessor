#!/usr/bin/env python3
"""Debug реального вызова extract_metadata"""
import sys
sys.path.insert(0, "/root/winners_preprocessor")
from REAL_test_10_pdfs import extract_text_from_pdf, extract_metadata
from pathlib import Path

pdf = Path("/root/winners_preprocessor/pilot_winers223/data/pending/direct/pdf/UNIT_0c3fb63690914cd8/files/Протокол 1348-1 от 27.11.2025 ПДО.pdf")

print("1️⃣ Извлечение текста...")
result = extract_text_from_pdf(pdf)
text = result["text"]
print(f"   Длина текста: {len(text)} символов\n")

print("2️⃣ Вызов extract_metadata...")
print(f"   Первые 500 символов текста:\n")
print(text[:500])
print("\n...")

metadata = extract_metadata(text, debug=True)

print("\n3️⃣ Результат:")
import json
print(json.dumps(metadata, indent=2, ensure_ascii=False))


#!/usr/bin/env python3
"""Debug: что именно возвращает VLM как DocTags"""
import openai
import base64
from pdf2image import convert_from_path
from io import BytesIO
from pathlib import Path

GRANITE_API = "https://8cb66180-db3a-4963-8068-51f87e716259.modelrun.inference.cloud.ru/v1"
GRANITE_TOKEN = "ZDRhOWQ3OTAtZjU4MC00MzA2LThhNTgtMDU1NGFlMjE4OWRl.85a830f9340966e0ad1fd1642884c7c8"

granite = openai.OpenAI(api_key=GRANITE_TOKEN, base_url=GRANITE_API)

pdf = Path("/root/winners_preprocessor/pilot_winers223/data/pending/direct/pdf/UNIT_0c3fb63690914cd8/files/Протокол 1348-1 от 27.11.2025 ПДО.pdf")

print("1️⃣ Конвертация первой страницы...")
images = convert_from_path(str(pdf), dpi=100, first_page=1, last_page=1)
image = images[0]

if image.width > 1024 or image.height > 1024:
    image.thumbnail((1024, 1024))

print(f"   Размер: {image.width}x{image.height}")

# Конвертация в base64
buffered = BytesIO()
image.save(buffered, format="PNG")
img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
print(f"   Base64: {len(img_base64)} символов")

print("\n2️⃣ Отправка к Granite-Docling VLM...")
messages = [
    {
        "role": "user",
        "content": [
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{img_base64}"
                }
            },
            {
                "type": "text",
                "text": "Convert this page to docling."
            }
        ]
    }
]

response = granite.chat.completions.create(
    model="granite-docling",
    messages=messages,
    max_tokens=4096,
    temperature=0.0
)

doctags = response.choices[0].message.content

print(f"\n3️⃣ Ответ VLM ({len(doctags)} символов):\n")
print("="*70)
print(doctags)
print("="*70)

# Сохранение
Path("output_DEBUG_DOCTAGS").mkdir(exist_ok=True)
with open("output_DEBUG_DOCTAGS/doctags_raw.txt", "w", encoding="utf-8") as f:
    f.write(doctags)

print(f"\n✅ Сохранено: output_DEBUG_DOCTAGS/doctags_raw.txt")


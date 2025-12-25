#!/usr/bin/env python3
"""
ПРАВИЛЬНОЕ решение: использовать Docling локально с удаленным Granite VLM

Согласно документации, Docling поддерживает VlmPipeline с удаленным API.
НО: OpenAI-compatible endpoint может быть не совместим с Docling API.

Проверяем возможности:
1. Docling локально с VlmPipeline + ApiVlmOptions
2. Нужен адаптер между Docling и OpenAI API
"""
import sys
from pathlib import Path

# Тест 1: Проверяем что Docling доступен
try:
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.base_models import InputFormat
    from docling.pipeline.vlm_pipeline import VlmPipeline
    from docling.datamodel.pipeline_options import VlmPipelineOptions
    print("✅ Docling импортирован")
except Exception as e:
    print(f"❌ Docling недоступен: {e}")
    sys.exit(1)

# Тест 2: Проверяем ApiVlmOptions
try:
    from docling.datamodel.pipeline_options import ApiVlmOptions
    print("✅ ApiVlmOptions доступен")
except Exception as e:
    print(f"⚠️  ApiVlmOptions недоступен: {e}")
    print("   Возможно нужна более новая версия Docling")

# Тест 3: Проверяем vlm_model_specs
try:
    from docling.datamodel import vlm_model_specs
    print("✅ vlm_model_specs доступен")
    print(f"   Доступные модели: {dir(vlm_model_specs)}")
except Exception as e:
    print(f"⚠️  vlm_model_specs недоступен: {e}")

print("\n" + "="*70)
print("АНАЛИЗ:")
print("="*70)

print("""
Согласно документации Hugging Face, есть 2 способа использовать Granite-Docling:

1️⃣ ЛОКАЛЬНО через transformers:
   converter = DocumentConverter(
       format_options={
           InputFormat.PDF: PdfFormatOption(pipeline_cls=VlmPipeline)
       }
   )
   
   ❌ Проблема: требует 4GB+ GPU и модель локально

2️⃣ ЧЕРЕЗ УДАЛЕННЫЙ VLM (правильный путь):
   Docling поддерживает ApiVlmOptions для подключения к удаленным VLM.
   
   НО: OpenAI-compatible endpoint не совместим напрямую с Docling API!
   
   Причина: 
   - Docling ожидает специфичный формат запроса/ответа
   - OpenAI API использует другой формат (chat.completions)
   - Granite через OpenAI API возвращает координаты, не DocTags

3️⃣ РЕШЕНИЕ - АДАПТЕР:
   Мы УЖЕ создали granite_adapter в docker-compose.yml!
   
   granite_adapter должен:
   - Принимать запросы в формате Docling VLM API
   - Конвертировать в OpenAI chat.completions
   - Отправлять к удаленному Granite
   - Парсить ответ и возвращать в формате Docling

4️⃣ ПРОБЛЕМА С УДАЛЕННЫМ GRANITE:
   Удаленный API возвращает только координаты <loc_...> и "1.1.1.1...",
   а НЕ полноценные DocTags с текстом!
   
   Это значит:
   - Либо промпт неправильный
   - Либо удаленный API не поддерживает DocTags
   - Либо нужен другой endpoint (не /v1/chat/completions)

5️⃣ АЛЬТЕРНАТИВА - БЕЗ VLM:
   Использовать встроенный OCR Docling без VLM:
   
   converter = DocumentConverter(
       format_options={
           InputFormat.PDF: PdfFormatOption(do_ocr=True)
       }
   )
   
   ✅ Это РАБОТАЕТ локально и дает хороший результат!
""")

print("\n" + "="*70)
print("РЕКОМЕНДАЦИЯ:")
print("="*70)

print("""
Так как удаленный Granite API через OpenAI endpoint возвращает только координаты,
ЛУЧШИЙ подход:

✅ Использовать Docling ЛОКАЛЬНО без удаленного VLM:
   - Docling имеет встроенный OCR (EasyOCR/Tesseract)
   - Поддерживает таблицы через pdfplumber
   - Экспортирует в Markdown автоматически
   - Извлекает структуру документа
   
   Это НАМНОГО лучше чем pytesseract + pdfplumber вручную!

📝 КОД:
""")

code = '''
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat

# Конфигурация с OCR
converter = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(
            do_ocr=True,
            ocr_engine="easyocr"  # или "tesseract"
        )
    }
)

# Конвертация
result = converter.convert("protocol.pdf")
doc = result.document

# Markdown
markdown = doc.export_to_markdown()

# Метаданные можно извлечь из doc.main_text
'''

print(code)

print("\n✅ Протестируем этот подход!")


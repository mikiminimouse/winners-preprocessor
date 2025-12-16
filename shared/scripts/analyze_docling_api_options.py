#!/usr/bin/env python3
"""
Анализ: может ли удаленный Granite работать через нативный Docling API
"""
import requests
import json

BASE_URL = "https://8cb66180-db3a-4963-8068-51f87e716259.modelrun.inference.cloud.ru"
TOKEN = "ZDRhOWQ3OTAtZjU4MC00MzA2LThhNTgtMDU1NGFlMjE4OWRl.85a830f9340966e0ad1fd1642884c7c8"

print("="*70)
print("АНАЛИЗ УДАЛЕННОГО API")
print("="*70)
print()

# 1. Проверяем доступные endpoints
print("1️⃣ Проверка доступных endpoints:\n")

endpoints_to_check = [
    "/",
    "/v1",
    "/v1/models",
    "/v1/chat/completions",
    "/health",
    "/api/v1",
    "/docling",
    "/process",
]

headers = {"Authorization": f"Bearer {TOKEN}"}

for endpoint in endpoints_to_check:
    url = BASE_URL + endpoint
    try:
        response = requests.get(url, headers=headers, timeout=5)
        print(f"   {endpoint}: {response.status_code}")
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"      Response: {json.dumps(data, indent=2)[:200]}...")
            except:
                print(f"      Response: {response.text[:200]}...")
    except Exception as e:
        print(f"   {endpoint}: ❌ {type(e).__name__}")

print("\n" + "="*70)
print("2️⃣ АНАЛИЗ ДОКУМЕНТАЦИИ Docling")
print("="*70)

print("""
Согласно документации Hugging Face:
https://huggingface.co/ibm-granite/granite-docling-258M

📖 СПОСОБЫ ИСПОЛЬЗОВАНИЯ GRANITE-DOCLING:

1️⃣ ЛОКАЛЬНО через transformers (CPU/GPU):
   ```python
   from transformers import AutoProcessor, AutoModelForVision2Seq
   
   processor = AutoProcessor.from_pretrained("ibm-granite/granite-docling-258M")
   model = AutoModelForVision2Seq.from_pretrained("ibm-granite/granite-docling-258M")
   ```
   ✅ Полная поддержка DocTags
   ❌ Требует 4GB+ GPU памяти

2️⃣ ЧЕРЕЗ DOCLING SDK локально:
   ```python
   from docling.document_converter import DocumentConverter, PdfFormatOption
   from docling.pipeline.vlm_pipeline import VlmPipeline
   
   converter = DocumentConverter(
       format_options={
           InputFormat.PDF: PdfFormatOption(pipeline_cls=VlmPipeline)
       }
   )
   ```
   ✅ Полная интеграция
   ❌ Модель загружается локально

3️⃣ ЧЕРЕЗ VLLM (удаленный inference):
   ```python
   from vllm import LLM
   llm = LLM(model="ibm-granite/granite-docling-258M", revision="untied")
   ```
   ✅ Быстрый batch inference
   ⚠️  Требует собственный VLLM сервер

4️⃣ ЧЕРЕЗ УДАЛЕННЫЙ API (ApiVlmOptions):
   Docling поддерживает ApiVlmOptions для подключения к удаленным VLM.
   
   НО! В документации НЕТ примеров с удаленным Granite API.
   Все примеры используют ЛОКАЛЬНУЮ модель.

""")

print("="*70)
print("3️⃣ ПРОБЛЕМА С OPENAI-COMPATIBLE ENDPOINT")
print("="*70)

print("""
Текущая ситуация:
- Удаленный сервер предоставляет OpenAI-compatible API (/v1/chat/completions)
- При запросе "Convert this page to docling." возвращает:
  ❌ Только координаты: <loc_59><loc_46>...
  ❌ Повторяющийся текст: 1.1.1.1.1.1...
  ❌ НЕТ полноценных DocTags с текстом

Причина:
OpenAI API формат НЕ совместим с форматом Docling VLM!

Granite-Docling ожидает:
- Специфичный формат запроса (не chat.completions)
- Возвращает DocTags в специальном SGML формате
- Требует integration через Docling SDK

OpenAI API endpoint:
- Обрабатывает изображения как vision model
- Возвращает text/coordinates в chat completion формате
- НЕ понимает "DocTags" как output формат
""")

print("="*70)
print("4️⃣ ВОЗМОЖНЫЕ РЕШЕНИЯ")
print("="*70)

print("""
Вариант А: Использовать удаленный API "как есть" ❌
   Проблема: Возвращает только координаты, не текст
   Статус: НЕ РАБОТАЕТ

Вариант Б: Создать адаптер для преобразования форматов ⚠️
   Нужно:
   1. Понять нативный протокол Docling VLM API
   2. Преобразовывать Docling VLM requests → OpenAI format
   3. Преобразовывать OpenAI responses → DocTags
   Проблема: OpenAI API не возвращает нужные данные!

Вариант В: Запросить нативный Docling endpoint у провайдера ❓
   Связаться с провайдером:
   https://8cb66180-db3a-4963-8068-51f87e716259.modelrun.inference.cloud.ru
   Спросить: "Есть ли нативный Docling API endpoint (не OpenAI)?"
   
Вариант Г: Использовать VLLM на отдельном сервере 💰
   Развернуть свой VLLM inference сервер с Granite-Docling
   Требует: GPU сервер (H100/A100)
   
Вариант Д: ТЕКУЩЕЕ РЕШЕНИЕ - OCR + pdfplumber ✅
   ✅ РАБОТАЕТ прямо сейчас
   ✅ 10/10 PDF обработаны успешно
   ✅ Метаданные извлечены (5.4 поля/файл)
   ✅ Не требует GPU/дорогой инфраструктуры
   ⚠️  Без использования Granite VLM
""")

print("="*70)
print("5️⃣ РЕКОМЕНДАЦИЯ")
print("="*70)

print("""
🎯 ОПТИМАЛЬНОЕ РЕШЕНИЕ НА СЕГОДНЯ:

Использовать текущее рабочее решение (FINAL_working_solution.py):
- Tesseract OCR для сканов
- pdfplumber для текстовых PDF
- Regex парсер для метаданных
- Markdown форматирование

РЕЗУЛЬТАТ: ✅ 10/10 PDF успешно обработаны

📩 ДОПОЛНИТЕЛЬНО:
Написать провайдеру API вопрос:
"Предоставляете ли вы нативный Docling API endpoint 
(не OpenAI-compatible), который возвращает полные DocTags с текстом?"

Если ДА → можно интегрировать через ApiVlmOptions
Если НЕТ → продолжать использовать текущее решение
""")

print("="*70)


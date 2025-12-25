#!/usr/bin/env python3
"""
ПРАВИЛЬНОЕ использование Granite-Docling VLM
VLM работает с ИЗОБРАЖЕНИЯМИ, не с текстом!
"""
import os
import sys
import json
import time
import openai
import base64
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
from pdf2image import convert_from_path
from io import BytesIO
from PIL import Image
from docling_core.types.doc import DoclingDocument
from docling_core.types.doc.document import DocTagsDocument

# Granite VLM конфигурация
GRANITE_API = "https://8cb66180-db3a-4963-8068-51f87e716259.modelrun.inference.cloud.ru/v1"
GRANITE_TOKEN = "ZDRhOWQ3OTAtZjU4MC00MzA2LThhNTgtMDU1NGFlMjE4OWRl.85a830f9340966e0ad1fd1642884c7c8"
GRANITE_MODEL = "granite-docling"

granite = openai.OpenAI(api_key=GRANITE_TOKEN, base_url=GRANITE_API)


def image_to_base64(image: Image.Image) -> str:
    """Конвертация PIL Image в base64"""
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')


def process_page_with_vlm(image: Image.Image, page_num: int) -> Dict[str, Any]:
    """
    Обработка ОДНОЙ страницы через Granite-Docling VLM
    
    VLM принимает изображение и возвращает DocTags
    """
    try:
        # Конвертируем изображение в base64
        img_base64 = image_to_base64(image)
        
        # Запрос к VLM с изображением
        # Согласно документации: "Convert this page to docling."
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
            model=GRANITE_MODEL,
            messages=messages,
            max_tokens=4096,  # Уменьшено для избежания лимита
            temperature=0.0
        )
        
        doctags = response.choices[0].message.content
        
        # Debug: показываем первые 500 символов
        # print(f"\n      [DocTags preview]: {doctags[:500]}...")
        
        return {
            "success": True,
            "doctags": doctags,
            "page": page_num
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "page": page_num
        }


def pdf_to_docling_markdown(pdf_path: Path, max_pages: int = 10) -> Dict[str, Any]:
    """
    Полная конвертация PDF → Markdown через Granite-Docling VLM
    
    1. PDF → изображения страниц
    2. Каждое изображение → Granite VLM → DocTags
    3. DocTags → DoclingDocument
    4. DoclingDocument → Markdown
    """
    print(f"📄 Обработка: {pdf_path.name}")
    start = time.time()
    
    # 1. Конвертация PDF в изображения (низкий DPI для VLM)
    print(f"   🖼️  Конвертация в изображения...", end=" ", flush=True)
    try:
        images = convert_from_path(
            str(pdf_path),
            dpi=100,  # Низкий DPI для уменьшения токенов
            first_page=1,
            last_page=max_pages
        )
        # Дополнительное уменьшение если изображения большие
        resized_images = []
        for img in images:
            if img.width > 1024 or img.height > 1024:
                img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
            resized_images.append(img)
        images = resized_images
        print(f"✅ {len(images)} страниц")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return {"success": False, "error": str(e)}
    
    # 2. Обработка каждой страницы через VLM
    print(f"   🤖 Обработка через Granite-Docling VLM...")
    all_doctags = []
    all_images = []
    
    for i, image in enumerate(images, 1):
        print(f"      Страница {i}/{len(images)}...", end=" ", flush=True)
        result = process_page_with_vlm(image, i)
        
        if result["success"]:
            all_doctags.append(result["doctags"])
            all_images.append(image)
            print(f"✅ {len(result['doctags'])} символов")
        else:
            print(f"❌ {result['error']}")
            # Продолжаем с пустым DocTags
            all_doctags.append("")
            all_images.append(image)
    
    if not any(all_doctags):
        return {
            "success": False,
            "error": "Ни одна страница не обработана"
        }
    
    # 3. Создание DoclingDocument из DocTags
    print(f"   📝 Создание DoclingDocument...", end=" ", flush=True)
    try:
        # Используем docling_core API
        doctags_doc = DocTagsDocument.from_doctags_and_image_pairs(
            all_doctags,
            all_images
        )
        doc = DoclingDocument.load_from_doctags(
            doctags_doc,
            document_name=pdf_path.stem
        )
        print("✅")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return {"success": False, "error": f"DocTags parsing: {e}"}
    
    # 4. Экспорт в Markdown
    print(f"   📄 Экспорт в Markdown...", end=" ", flush=True)
    try:
        markdown = doc.export_to_markdown()
        print(f"✅ {len(markdown)} символов")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return {"success": False, "error": f"Markdown export: {e}"}
    
    elapsed = time.time() - start
    print(f"   ⏱️  {elapsed:.1f}с")
    
    return {
        "success": True,
        "markdown": markdown,
        "doc": doc,
        "pages": len(images),
        "time": elapsed
    }


def extract_metadata_from_image(image: Image.Image) -> Dict[str, Any]:
    """
    Извлечение метаданных из первой страницы через VLM
    
    Используем специальный промпт для извлечения структурированных данных
    """
    try:
        img_base64 = image_to_base64(image)
        
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
                        "text": """Extract procurement protocol metadata as JSON:
{
  "номер_процедуры": "procedure number",
  "дата_протокола": "DD.MM.YYYY",
  "победитель": "winner company",
  "ИНН": "INN number",
  "КПП": "KPP number",
  "цена_победителя": "price",
  "валюта": "currency",
  "предмет_закупки": "subject",
  "заказчик": "customer"
}
Return ONLY JSON, use null if not found."""
                    }
                ]
            }
        ]
        
        response = granite.chat.completions.create(
            model=GRANITE_MODEL,
            messages=messages,
            max_tokens=2000,
            temperature=0.0
        )
        
        raw = response.choices[0].message.content
        
        # Парсинг JSON
        import re
        match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', raw, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        
        return {}
        
    except Exception as e:
        print(f"      ⚠️  Метаданные VLM: {e}")
        return {}


def test_one_pdf(pdf_path: Path, output_dir: Path):
    """Тест одного PDF"""
    # 1. Конвертация через VLM
    result = pdf_to_docling_markdown(pdf_path, max_pages=5)
    
    if not result["success"]:
        print(f"❌ Ошибка: {result['error']}")
        return
    
    markdown = result["markdown"]
    doc = result["doc"]
    
    # 2. Извлечение метаданных через VLM (первая страница)
    print(f"   🔍 Извлечение метаданных через VLM...", end=" ", flush=True)
    images_meta = convert_from_path(str(pdf_path), dpi=100, first_page=1, last_page=1)
    if images_meta and (images_meta[0].width > 1024 or images_meta[0].height > 1024):
        images_meta[0].thumbnail((1024, 1024), Image.Resampling.LANCZOS)
    metadata = extract_metadata_from_image(images_meta[0]) if images_meta else {}
    filled = sum(1 for v in metadata.values() if v)
    print(f"✅ {filled} полей")
    
    # 3. Сохранение
    base = pdf_path.stem
    
    # Markdown
    md_file = output_dir / f"{base}.md"
    md_content = f"# {pdf_path.name}\n\n"
    md_content += f"**Дата обработки:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    md_content += "---\n\n"
    md_content += "## 📊 Извлеченные метаданные (VLM)\n\n"
    for key, value in metadata.items():
        display_key = key.replace('_', ' ').title()
        md_content += f"- **{display_key}:** {value or 'не найдено'}\n"
    md_content += "\n---\n\n"
    md_content += markdown
    
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write(md_content)
    
    # JSON
    metadata["полный_markdown"] = markdown
    metadata["страниц_обработано"] = result["pages"]
    metadata["время_обработки"] = result["time"]
    
    meta_file = output_dir / f"{base}_metadata.json"
    with open(meta_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Сохранено: {md_file.name}")


def main():
    print("="*70)
    print("ПРАВИЛЬНЫЙ ТЕСТ: Granite-Docling VLM (изображения → DocTags)")
    print("="*70)
    print()
    
    # Тестовый PDF
    pdf = Path("/root/winners_preprocessor/pilot_winers223/data/pending/direct/pdf/UNIT_0c3fb63690914cd8/files/Протокол 1348-1 от 27.11.2025 ПДО.pdf")
    
    if not pdf.exists():
        print(f"❌ Файл не найден: {pdf}")
        sys.exit(1)
    
    output = Path("output_VLM_CORRECT")
    output.mkdir(exist_ok=True)
    print(f"📁 Output: {output}\n")
    
    test_one_pdf(pdf, output)
    
    print("\n" + "="*70)
    print("✅ ГОТОВО")
    print("="*70)


if __name__ == "__main__":
    main()


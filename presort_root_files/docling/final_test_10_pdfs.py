#!/usr/bin/env python3
"""
ФИНАЛЬНЫЙ тест: 10 PDF файлов с РЕАЛЬНЫМ извлечением текста и метаданных

Использует:
- pdfplumber для извлечения текста и таблиц
- pytesseract OCR для сканов
- Granite API для извлечения метаданных
"""
import sys
sys.path.insert(0, 'docling')

import os
import json
import time
import openai
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
from processor import DocumentProcessor

# Конфигурация Granite
GRANITE_API_URL = "https://8cb66180-db3a-4963-8068-51f87e716259.modelrun.inference.cloud.ru/v1"
GRANITE_API_TOKEN = "ZDRhOWQ3OTAtZjU4MC00MzA2LThhNTgtMDU1NGFlMjE4OWRl.85a830f9340966e0ad1fd1642884c7c8"

granite_client = openai.OpenAI(api_key=GRANITE_API_TOKEN, base_url=GRANITE_API_URL)


def find_test_pdfs(limit=10) -> List[Path]:
    """Найти тестовые PDF файлы"""
    base = Path("/root/winners_preprocessor/pilot_winers223/data/pending/direct/pdf")
    all_pdfs = []
    for unit_dir in base.iterdir():
        if unit_dir.is_dir() and unit_dir.name.startswith("UNIT_"):
            files_dir = unit_dir / "files"
            if files_dir.exists():
                all_pdfs.extend(list(files_dir.glob("*.pdf")))
    return all_pdfs[:limit]


def extract_metadata(text: str) -> Dict[str, Any]:
    """Извлечение метаданных через Granite"""
    if len(text.strip()) < 100:
        return get_empty_metadata()
    
    text_sample = text[:15000] if len(text) > 15000 else text
    
    prompt = f"""Извлеки метаданные из протокола закупки в JSON:

{text_sample}

Формат (null если нет):
{{
  "номер_процедуры": "номер",
  "номер_лота": "лот",
  "дата_протокола": "ДД.ММ.ГГГГ",
  "победитель": "название победителя",
  "ИНН": "ИНН",
  "КПП": "КПП",
  "цена_победителя": "цена число",
  "валюта": "RUB/USD/EUR",
  "предмет_закупки": "предмет",
  "дата_начала_подачи": "ДД.ММ.ГГГГ",
  "дата_окончания_подачи": "ДД.ММ.ГГГГ",
  "дата_проведения": "ДД.ММ.ГГГГ",
  "заказчик": "заказчик",
  "организатор": "организатор",
  "состав_комиссии": ["ФИО"],
  "участники": [{{"наименование": "", "статус": "", "сумма": "", "номер_заявки": ""}}]
}}

ТОЛЬКО JSON:"""
    
    try:
        response = granite_client.chat.completions.create(
            model="granite-docling",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000,
            temperature=0.0
        )
        
        raw = response.choices[0].message.content
        return parse_json(raw)
    except Exception as e:
        print(f"      ⚠️  Ошибка Granite: {e}")
        return get_empty_metadata()


def parse_json(text: str) -> Dict:
    import re
    text = text.strip()
    if text.startswith('```'):
        parts = text.split('```')
        if len(parts) >= 2:
            text = parts[1]
            if text.startswith('json'):
                text = text[4:]
    text = text.strip()
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except:
            pass
    return get_empty_metadata()


def get_empty_metadata() -> Dict:
    return {
        "номер_процедуры": None, "номер_лота": None, "дата_протокола": None,
        "победитель": None, "ИНН": None, "КПП": None, "цена_победителя": None,
        "валюта": None, "предмет_закупки": None, "дата_начала_подачи": None,
        "дата_окончания_подачи": None, "дата_проведения": None,
        "заказчик": None, "организатор": None, "состав_комиссии": [],
        "участники": []
    }


def process_pdf(pdf_path: Path, output_dir: Path) -> Dict:
    """Обработка одного PDF"""
    print(f"\n[{pdf_path.name}]")
    start_time = time.time()
    
    # Обработка через DocumentProcessor
    print(f"   📄 Извлечение текста...")
    processor = DocumentProcessor(
        unit_id="TEST",
        file_info={
            "path": str(pdf_path),
            "original_name": pdf_path.name,
            "detected_type": "pdf",
            "route": "pdf_text"
        },
        output_dir=output_dir
    )
    
    try:
        result = processor.process()
        
        if not result["success"]:
            print(f"      ❌ Ошибка: {result.get('error')}")
            return {"success": False, "error": result.get("error")}
        
        # Читаем результат из JSON
        output_files = result.get("output_files", [])
        json_file = next((f for f in output_files if f.endswith('.json')), None)
        
        if not json_file or not Path(json_file).exists():
            print(f"      ❌ JSON результат не найден")
            return {"success": False, "error": "No JSON output"}
        
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        text = data.get("text", "")
        tables = data.get("tables", [])
        
        print(f"      ✅ Текст: {len(text)} символов, Таблиц: {len(tables)}")
        
        # Извлечение метаданных
        print(f"   🔍 Извлечение метаданных...")
        metadata = extract_metadata(text)
        filled = sum(1 for v in metadata.values() if v and str(v).strip())
        print(f"      ✅ Извлечено полей: {filled}/16")
        
        # Создание итогового Markdown
        md_content = create_final_markdown(pdf_path.name, text, tables, metadata)
        
        # Сохранение
        base_name = pdf_path.stem
        final_md = output_dir / f"{base_name}_FINAL.md"
        with open(final_md, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        final_meta = output_dir / f"{base_name}_metadata.json"
        metadata["полный_текст"] = text
        metadata["таблицы"] = tables
        with open(final_meta, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        elapsed = time.time() - start_time
        print(f"      ⏱️  {elapsed:.1f}с")
        
        return {
            "success": True,
            "text_length": len(text),
            "tables_count": len(tables),
            "metadata_fields": filled,
            "time": elapsed
        }
        
    except Exception as e:
        print(f"      ❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


def create_final_markdown(filename: str, text: str, tables: List, metadata: Dict) -> str:
    """Создание финального Markdown"""
    md = f"# {filename}\n\n"
    md += f"**Дата обработки:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    md += "---\n\n"
    
    # Метаданные
    md += "## 📊 Извлеченные метаданные\n\n"
    md += f"- **Номер процедуры:** {metadata.get('номер_процедуры') or 'не найдено'}\n"
    md += f"- **Номер лота:** {metadata.get('номер_лота') or 'не найдено'}\n"
    md += f"- **Дата протокола:** {metadata.get('дата_протокола') or 'не найдено'}\n"
    md += f"- **Победитель:** {metadata.get('победитель') or 'не найдено'}\n"
    md += f"- **ИНН:** {metadata.get('ИНН') or 'не найдено'}\n"
    md += f"- **КПП:** {metadata.get('КПП') or 'не найдено'}\n"
    md += f"- **Цена:** {metadata.get('цена_победителя') or 'не найдено'} {metadata.get('валюта') or ''}\n"
    md += f"- **Предмет закупки:** {metadata.get('предмет_закупки') or 'не найдено'}\n"
    md += f"- **Заказчик:** {metadata.get('заказчик') or 'не найдено'}\n"
    md += f"- **Организатор:** {metadata.get('организатор') or 'не найдено'}\n\n"
    
    if metadata.get('состав_комиссии'):
        md += "### Состав комиссии\n\n"
        for member in metadata['состав_комиссии']:
            md += f"- {member}\n"
        md += "\n"
    
    if metadata.get('участники'):
        md += f"### Участники ({len(metadata['участники'])})\n\n"
        for i, p in enumerate(metadata['участники'][:5], 1):
            md += f"{i}. **{p.get('наименование', 'N/A')}** - {p.get('статус', 'N/A')}\n"
        md += "\n"
    
    # Текст
    md += "## 📄 Содержание документа\n\n"
    if len(text) > 5000:
        md += text[:5000] + "\n\n_(текст обрезан для читаемости)_\n\n"
    else:
        md += text + "\n\n"
    
    # Таблицы
    if tables:
        md += f"## 📊 Таблицы ({len(tables)})\n\n"
        for i, table in enumerate(tables[:2], 1):
            md += f"### Таблица {i}\n\n"
            if isinstance(table, list) and table:
                for r_idx, row in enumerate(table[:8]):
                    md += "| " + " | ".join(str(c or "") for c in row) + " |\n"
                    if r_idx == 0:
                        md += "|" + "|".join([" --- "] * len(row)) + "|\n"
            md += "\n"
        if len(tables) > 2:
            md += f"_(Показаны 2 из {len(tables)} таблиц)_\n\n"
    
    return md


def main():
    print("="*70)
    print("ФИНАЛЬНЫЙ ТЕСТ: 10 PDF файлов")
    print("="*70)
    print()
    
    # Поиск файлов
    print("1. Поиск PDF файлов...")
    pdfs = find_test_pdfs(10)
    print(f"   ✅ Найдено: {len(pdfs)} файлов\n")
    
    # Output
    output = Path("output_FINAL_10_pdfs")
    output.mkdir(exist_ok=True)
    print(f"2. Output: {output}\n")
    
    # Обработка
    print("3. Обработка файлов...")
    results = []
    for i, pdf in enumerate(pdfs, 1):
        print(f"\n[{i}/{len(pdfs)}]", end=" ")
        result = process_pdf(pdf, output)
        results.append({**result, "file": pdf.name})
    
    # Итоги
    print("\n")
    print("="*70)
    print("ИТОГИ")
    print("="*70)
    
    success = [r for r in results if r.get("success")]
    failed = [r for r in results if not r.get("success")]
    
    print(f"✅ Успешно: {len(success)}/{len(pdfs)}")
    if failed:
        print(f"❌ Ошибки: {len(failed)}")
        for f in failed:
            print(f"   - {f['file']}: {f.get('error', 'unknown')}")
    
    if success:
        total_text = sum(r.get("text_length", 0) for r in success)
        total_tables = sum(r.get("tables_count", 0) for r in success)
        total_meta = sum(r.get("metadata_fields", 0) for r in success)
        total_time = sum(r.get("time", 0) for r in success)
        
        print(f"\n📊 Извлечено:")
        print(f"   Текста: {total_text:,} символов")
        print(f"   Таблиц: {total_tables}")
        print(f"   Метаданных: {total_meta} полей (среднее: {total_meta/len(success):.1f} на файл)")
        print(f"   Время: {total_time:.1f}с (среднее: {total_time/len(success):.1f}с на файл)")
    
    print(f"\n📁 Результаты: {output}")
    print("="*70)


if __name__ == "__main__":
    main()


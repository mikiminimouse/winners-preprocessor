#!/usr/bin/env python3
"""
ФИНАЛЬНОЕ РАБОЧЕЕ РЕШЕНИЕ для извлечения данных из PDF
Без Granite VLM (так как удаленный API не возвращает текст)
"""
import os
import sys
import json
import time
import pdfplumber
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
from pdf2image import convert_from_path
import pytesseract
from PIL import Image
import re

def find_test_pdfs(limit=10) -> List[Path]:
    """Найти тестовые PDF"""
    base = Path("/root/winners_preprocessor/pilot_winers223/data/pending/direct/pdf")
    pdfs = []
    for unit_dir in sorted(base.iterdir())[:100]:
        if unit_dir.is_dir() and unit_dir.name.startswith("UNIT_"):
            files_dir = unit_dir / "files"
            if files_dir.exists():
                pdfs.extend(list(files_dir.glob("*.pdf")))
                if len(pdfs) >= limit:
                    break
    return pdfs[:limit]


def extract_text_from_pdf(pdf_path: Path) -> Dict[str, Any]:
    """Извлечение текста через pdfplumber + OCR"""
    all_text = []
    all_tables = []
    is_scan = False
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            pages = len(pdf.pages)
            
            # Проверка - скан или текст
            first_text = pdf.pages[0].extract_text() if pages > 0 else ""
            is_scan = not first_text or len(first_text.strip()) < 50
            
            if is_scan:
                # OCR для сканов
                max_pages = min(5, pages)
                images = convert_from_path(str(pdf_path), dpi=200, first_page=1, last_page=max_pages)
                
                for page_num, image in enumerate(images, 1):
                    ocr_text = pytesseract.image_to_string(image, lang='rus+eng')
                    if ocr_text.strip():
                        all_text.append(f"\n--- СТРАНИЦА {page_num} (OCR) ---\n{ocr_text}")
                
                # Таблицы
                for page_num, page in enumerate(pdf.pages[:max_pages], 1):
                    tables = page.extract_tables()
                    if tables:
                        for table in tables:
                            all_tables.append({"page": page_num, "data": table})
            else:
                # Текстовый слой
                for page_num, page in enumerate(pdf.pages[:10], 1):
                    text = page.extract_text()
                    if text:
                        all_text.append(f"\n--- СТРАНИЦА {page_num} ---\n{text}")
                    
                    tables = page.extract_tables()
                    if tables:
                        for table in tables:
                            all_tables.append({"page": page_num, "data": table})
            
            combined_text = "\n".join(all_text)
            
            return {
                "success": True,
                "text": combined_text,
                "tables": all_tables,
                "pages": pages,
                "is_scan": is_scan
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "text": "",
            "tables": []
        }


def extract_metadata_regex(text: str) -> Dict[str, Any]:
    """Извлечение метаданных через regex"""
    metadata = {}
    
    # Номер процедуры
    match = re.search(r'(?:№\s*|номер\s+)(\d{11})', text, re.IGNORECASE)
    metadata['номер_процедуры'] = match.group(1) if match else None
    
    # Номер лота
    match = re.search(r'[Лл]от[а]?\s*№?\s*(\d+)', text)
    metadata['номер_лота'] = match.group(1) if match else None
    
    # Дата
    match = re.search(r'«?(\d{1,2})»?\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+(\d{4})', text, re.IGNORECASE)
    if match:
        months = {'января':'01','февраля':'02','марта':'03','апреля':'04','мая':'05','июня':'06',
                  'июля':'07','августа':'08','сентября':'09','октября':'10','ноября':'11','декабря':'12'}
        day, month, year = match.groups()
        metadata['дата_протокола'] = f"{day.zfill(2)}.{months[month.lower()]}.{year}"
    else:
        match = re.search(r'(\d{2}\.\d{2}\.\d{4})', text)
        metadata['дата_протокола'] = match.group(1) if match else None
    
    # Победитель
    match = re.search(r'[Пп]обедител[ья]:\s*(.+?)(?:,\s*ИНН|\n|$)', text)
    if not match:
        match = re.search(r'[Зз]аключить.*?с\s+(ООО|АО|ЗАО|ОАО|ИП|ФГУП)\s+[«"]?([^»"\n,]+)', text)
        if match:
            metadata['победитель'] = f"{match.group(1)} {match.group(2).strip()}"
        else:
            metadata['победитель'] = None
    else:
        metadata['победитель'] = match.group(1).strip()
    
    # ИНН
    match = re.search(r'ИНН[:\s]*(\d{10,12})', text)
    metadata['ИНН'] = match.group(1) if match else None
    
    # КПП
    match = re.search(r'КПП[:\s]*(\d{9})', text)
    metadata['КПП'] = match.group(1) if match else None
    
    # Цена
    match = re.search(r'[Цц]ена.*?(\d[\d\s]+\d)\s*(?:рубл|RUB)', text)
    if match:
        metadata['цена_победителя'] = match.group(1).replace(' ', '')
    else:
        metadata['цена_победителя'] = None
    
    # Валюта
    metadata['валюта'] = 'RUB' if 'рубл' in text.lower() else None
    
    # Предмет
    match = re.search(r'[Пп]редмет\s+(?:закупки|договора)[:\s]*(.+?)(?:\n|Цена|Срок|$)', text, re.DOTALL)
    if match:
        subject = match.group(1).strip()[:200]
        metadata['предмет_закупки'] = re.sub(r'\s+', ' ', subject)
    else:
        metadata['предмет_закупки'] = None
    
    # Заказчик
    match = re.search(r'[Зз]аказчик[:\s]*(.+?)(?:\n|ИНН|Адрес|$)', text)
    if match:
        metadata['заказчик'] = match.group(1).strip()[:150]
    else:
        metadata['заказчик'] = None
    
    # Организатор
    match = re.search(r'[Оо]рганизатор[:\s]*(.+?)(?:\n|ИНН|Адрес|$)', text)
    if match:
        metadata['организатор'] = match.group(1).strip()[:150]
    else:
        metadata['организатор'] = None
    
    return metadata


def create_markdown(filename: str, text: str, tables: List, metadata: Dict, is_scan: bool) -> str:
    """Создание Markdown"""
    md = f"# {filename}\n\n"
    md += f"**Дата обработки:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    md += f"**Тип документа:** {'Скан (OCR)' if is_scan else 'PDF с текстовым слоем'}\n\n"
    md += "---\n\n"
    
    # Метаданные
    md += "## 📊 Извлеченные метаданные\n\n"
    fields_found = 0
    for key, value in metadata.items():
        if key not in ['полный_текст', 'таблицы']:
            display_key = key.replace('_', ' ').title()
            md += f"- **{display_key}:** {value if value else '❌ не найдено'}\n"
            if value:
                fields_found += 1
    md += f"\n**Извлечено полей:** {fields_found}/11\n\n"
    
    # Статистика
    md += "## 📈 Статистика\n\n"
    md += f"- **Текста:** {len(text):,} символов\n"
    md += f"- **Таблиц:** {len(tables)}\n\n"
    
    # Содержание
    md += "## 📄 Содержание\n\n"
    if len(text) > 5000:
        md += text[:5000] + "\n\n_(обрезано, полный текст в JSON)_\n\n"
    else:
        md += text + "\n\n"
    
    # Таблицы
    if tables:
        md += f"## 📊 Таблицы ({len(tables)})\n\n"
        for i, tbl in enumerate(tables[:3], 1):
            md += f"### Таблица {i} (стр. {tbl['page']})\n\n"
            data = tbl['data']
            if data and len(data) > 0:
                for r_idx, row in enumerate(data[:15]):
                    md += "| " + " | ".join(str(c or "").replace("|", "\\|") for c in row) + " |\n"
                    if r_idx == 0:
                        md += "|" + "|".join([" --- "] * len(row)) + "|\n"
            md += "\n"
        if len(tables) > 3:
            md += f"_(Показаны 3 из {len(tables)})_\n\n"
    
    return md


def process_one_pdf(pdf_path: Path, output_dir: Path, index: int, total: int) -> Dict:
    """Обработка одного PDF"""
    print(f"\n[{index}/{total}] {pdf_path.name}")
    start = time.time()
    
    # 1. Текст
    print(f"   📄 Извлечение...", end=" ", flush=True)
    result = extract_text_from_pdf(pdf_path)
    
    if not result["success"]:
        print(f"❌ {result['error']}")
        return {"success": False, "file": pdf_path.name}
    
    text = result["text"]
    tables = result["tables"]
    is_scan = result.get("is_scan", False)
    scan_label = " (OCR)" if is_scan else ""
    print(f"✅ {len(text)} символов{scan_label}, {len(tables)} таблиц")
    
    # 2. Метаданные
    print(f"   🔍 Метаданные...", end=" ", flush=True)
    metadata = extract_metadata_regex(text)
    filled = sum(1 for v in metadata.values() if v)
    print(f"✅ {filled}/11 полей")
    
    # 3. Markdown
    md = create_markdown(pdf_path.name, text, tables, metadata, is_scan)
    
    # 4. Сохранение
    base = pdf_path.stem
    md_file = output_dir / f"{base}.md"
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write(md)
    
    metadata["полный_текст"] = text
    metadata["таблицы"] = tables
    meta_file = output_dir / f"{base}_metadata.json"
    with open(meta_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    elapsed = time.time() - start
    print(f"   ⏱️  {elapsed:.1f}с")
    
    return {
        "success": True,
        "file": pdf_path.name,
        "text_length": len(text),
        "tables_count": len(tables),
        "metadata_fields": filled,
        "is_scan": is_scan,
        "time": elapsed
    }


def main():
    print("="*70)
    print("ФИНАЛЬНЫЙ ТЕСТ: 10 PDF файлов (OCR + pdfplumber + regex)")
    print("="*70)
    print()
    
    # Поиск
    print("Поиск PDF...")
    pdfs = find_test_pdfs(10)
    
    if not pdfs:
        print("❌ PDF не найдены")
        sys.exit(1)
    
    print(f"✅ Найдено: {len(pdfs)}\n")
    
    # Output
    output = Path("output_FINAL_WORKING")
    output.mkdir(exist_ok=True)
    print(f"📁 Output: {output}\n")
    
    # Обработка
    results = []
    for i, pdf in enumerate(pdfs, 1):
        result = process_one_pdf(pdf, output, i, len(pdfs))
        results.append(result)
    
    # Итоги
    print("\n" + "="*70)
    print("ИТОГИ")
    print("="*70)
    
    success = [r for r in results if r.get("success")]
    failed = [r for r in results if not r.get("success")]
    
    print(f"\n✅ Успешно: {len(success)}/{len(pdfs)}")
    
    if failed:
        print(f"❌ Ошибки: {len(failed)}")
    
    if success:
        scans = sum(1 for r in success if r.get("is_scan"))
        text_pdfs = len(success) - scans
        
        print(f"\n📊 Обработано:")
        print(f"   Сканов (OCR): {scans}")
        print(f"   PDF с текстом: {text_pdfs}")
        print(f"   Текста: {sum(r['text_length'] for r in success):,} символов")
        print(f"   Таблиц: {sum(r['tables_count'] for r in success)}")
        print(f"   Метаданных: {sum(r['metadata_fields'] for r in success)} полей")
        print(f"   Среднее: {sum(r['metadata_fields'] for r in success)/len(success):.1f} полей/файл")
        print(f"   Время: {sum(r['time'] for r in success):.1f}с (среднее: {sum(r['time'] for r in success)/len(success):.1f}с)")
    
    print(f"\n📁 Результаты: {output}")
    print("="*70)


if __name__ == "__main__":
    main()


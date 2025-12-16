#!/usr/bin/env python3
"""
ЧЕСТНЫЙ тест на РЕАЛЬНЫХ 10 PDF файлах
Простой подход: pdfplumber + Granite для метаданных
"""
import os
import sys
import json
import time
import openai
import pdfplumber
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Granite конфигурация
GRANITE_API = "https://8cb66180-db3a-4963-8068-51f87e716259.modelrun.inference.cloud.ru/v1"
GRANITE_TOKEN = "ZDRhOWQ3OTAtZjU4MC00MzA2LThhNTgtMDU1NGFlMjE4OWRl.85a830f9340966e0ad1fd1642884c7c8"

granite = openai.OpenAI(api_key=GRANITE_TOKEN, base_url=GRANITE_API)


def find_test_pdfs(limit=10) -> List[Path]:
    """Найти тестовые PDF"""
    base = Path("/root/winners_preprocessor/pilot_winers223/data/pending/direct/pdf")
    pdfs = []
    for unit_dir in sorted(base.iterdir())[:50]:  # Первые 50 unit'ов
        if unit_dir.is_dir() and unit_dir.name.startswith("UNIT_"):
            files_dir = unit_dir / "files"
            if files_dir.exists():
                pdfs.extend(list(files_dir.glob("*.pdf")))
                if len(pdfs) >= limit:
                    break
    return pdfs[:limit]


def extract_text_from_pdf(pdf_path: Path) -> Dict[str, Any]:
    """Извлечение текста через pdfplumber + OCR для сканов"""
    all_text = []
    all_tables = []
    is_scan = False
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            pages = len(pdf.pages)
            
            # Проверяем первую страницу - скан или текст
            first_text = pdf.pages[0].extract_text() if pages > 0 else ""
            is_scan = not first_text or len(first_text.strip()) < 50
            
            if is_scan:
                # ЭТО СКАН - используем OCR
                print(f"🔍 OCR...", end=" ", flush=True)
                from pdf2image import convert_from_path
                import pytesseract
                
                # Ограничиваем до 5 страниц для OCR
                max_pages_for_ocr = min(5, pages)
                images = convert_from_path(
                    str(pdf_path),
                    dpi=200,
                    first_page=1,
                    last_page=max_pages_for_ocr
                )
                
                for page_num, image in enumerate(images, 1):
                    ocr_text = pytesseract.image_to_string(image, lang='rus+eng')
                    if ocr_text.strip():
                        all_text.append(f"\n--- СТРАНИЦА {page_num} (OCR) ---\n{ocr_text}")
                
                # Таблицы пробуем извлечь из pdfplumber
                for page_num, page in enumerate(pdf.pages[:max_pages_for_ocr], 1):
                    tables = page.extract_tables()
                    if tables:
                        for table in tables:
                            all_tables.append({"page": page_num, "data": table})
            else:
                # Есть текстовый слой
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


def extract_metadata(text: str, debug=False) -> Dict[str, Any]:
    """Извлечение метаданных через regex парсинг"""
    import re
    
    if len(text.strip()) < 100:
        return get_empty_metadata()
    
    metadata = {}
    
    # Номер процедуры (ЕИС)
    match = re.search(r'(?:№\s*|номер\s+)(\d{11})', text, re.IGNORECASE)
    metadata['номер_процедуры'] = match.group(1) if match else None
    
    # Номер лота
    match = re.search(r'[Лл]от[а]?\s*№?\s*(\d+)', text)
    metadata['номер_лота'] = match.group(1) if match else None
    
    # Дата протокола
    match = re.search(r'«?(\d{1,2})»?\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+(\d{4})', text, re.IGNORECASE)
    if match:
        months = {'января': '01', 'февраля': '02', 'марта': '03', 'апреля': '04', 'мая': '05', 'июня': '06',
                  'июля': '07', 'августа': '08', 'сентября': '09', 'октября': '10', 'ноября': '11', 'декабря': '12'}
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
    
    # Предмет закупки
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
    
    if debug:
        import json
        print(f"   [DEBUG] Извлечено regex: {json.dumps(metadata, ensure_ascii=False, indent=2)}")
    
    return metadata


def parse_json(text: str) -> Dict:
    import re
    text = text.strip()
    
    # Удаляем markdown
    if '```' in text:
        parts = text.split('```')
        for part in parts:
            if '{' in part:
                text = part
                break
    if text.startswith('json'):
        text = text[4:]
    
    # Берем ПЕРВЫЙ JSON (Granite повторяет)
    lines = text.split('\n')
    json_lines = []
    brace_count = 0
    started = False
    
    for line in lines:
        if '{' in line and not started:
            started = True
        if started:
            json_lines.append(line)
            brace_count += line.count('{')
            brace_count -= line.count('}')
            if brace_count == 0 and '}' in line:
                break
    
    if json_lines:
        try:
            json_str = '\n'.join(json_lines)
            return json.loads(json_str)
        except Exception as e:
            pass
    
    # Фолбэк - regex
    match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except:
            pass
    
    return get_empty_metadata()


def get_empty_metadata() -> Dict:
    return {
        "номер_процедуры": None,
        "номер_лота": None,
        "дата_протокола": None,
        "победитель": None,
        "ИНН": None,
        "КПП": None,
        "цена_победителя": None,
        "валюта": None,
        "предмет_закупки": None,
        "заказчик": None,
        "организатор": None
    }


def create_markdown(filename: str, text: str, tables: List, metadata: Dict) -> str:
    """Создание Markdown"""
    md = f"# {filename}\n\n"
    md += f"**Дата обработки:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    md += "---\n\n"
    
    # Метаданные
    md += "## 📊 Извлеченные метаданные\n\n"
    for key, value in metadata.items():
        if key not in ['полный_текст', 'таблицы']:
            display_key = key.replace('_', ' ').title()
            md += f"- **{display_key}:** {value or 'не найдено'}\n"
    md += "\n"
    
    # Статистика
    md += "## 📈 Статистика извлечения\n\n"
    md += f"- **Текста извлечено:** {len(text):,} символов\n"
    md += f"- **Таблиц найдено:** {len(tables)}\n\n"
    
    # Текст (первые 3000 символов)
    md += "## 📄 Содержание документа\n\n"
    if len(text) > 3000:
        md += text[:3000] + "\n\n_(текст обрезан для читаемости, полный текст в JSON)_\n\n"
    else:
        md += text + "\n\n"
    
    # Таблицы (первые 2)
    if tables:
        md += f"## 📊 Таблицы\n\n"
        for i, tbl in enumerate(tables[:2], 1):
            md += f"### Таблица {i} (Страница {tbl['page']})\n\n"
            data = tbl['data']
            if data and len(data) > 0:
                for r_idx, row in enumerate(data[:10]):
                    md += "| " + " | ".join(str(c or "").replace("|", "\\|") for c in row) + " |\n"
                    if r_idx == 0:
                        md += "|" + "|".join([" --- "] * len(row)) + "|\n"
            md += "\n"
        if len(tables) > 2:
            md += f"_(Показаны 2 из {len(tables)} таблиц)_\n\n"
    
    return md


def process_one_pdf(pdf_path: Path, output_dir: Path, index: int, total: int) -> Dict:
    """Обработка одного PDF"""
    print(f"\n[{index}/{total}] {pdf_path.name}")
    start = time.time()
    
    # Извлечение текста
    print(f"   📄 Извлечение текста...", end=" ", flush=True)
    result = extract_text_from_pdf(pdf_path)
    
    if not result["success"]:
        print(f"❌ Ошибка: {result['error']}")
        return {"success": False, "file": pdf_path.name}
    
    text = result["text"]
    tables = result["tables"]
    print(f"✅ {len(text)} символов, {len(tables)} таблиц")
    
    # Метаданные
    print(f"   🔍 Извлечение метаданных...", end=" ", flush=True)
    metadata = extract_metadata(text)
    filled = sum(1 for v in metadata.values() if v)
    print(f"✅ {filled} полей")
    
    # Markdown
    md = create_markdown(pdf_path.name, text, tables, metadata)
    
    # Сохранение
    base = pdf_path.stem
    md_file = output_dir / f"{base}.md"
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write(md)
    
    meta_file = output_dir / f"{base}_metadata.json"
    metadata["полный_текст"] = text
    metadata["таблицы"] = tables
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
        "time": elapsed
    }


def main():
    print("="*70)
    print("РЕАЛЬНЫЙ ТЕСТ: 10 PDF файлов")
    print("="*70)
    print()
    
    # Поиск PDF
    print("Поиск PDF файлов...")
    pdfs = find_test_pdfs(10)
    
    if not pdfs:
        print("❌ PDF не найдены")
        sys.exit(1)
    
    print(f"✅ Найдено: {len(pdfs)} файлов\n")
    
    # Output
    output = Path("output_REAL_TEST_10")
    output.mkdir(exist_ok=True)
    print(f"📁 Output: {output}\n")
    
    # Обработка
    print("Обработка:")
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
        for f in failed[:5]:
            print(f"   - {f['file']}")
    
    if success:
        total_text = sum(r["text_length"] for r in success)
        total_tables = sum(r["tables_count"] for r in success)
        total_meta = sum(r["metadata_fields"] for r in success)
        total_time = sum(r["time"] for r in success)
        
        print(f"\n📊 Извлечено:")
        print(f"   Текста: {total_text:,} символов")
        print(f"   Таблиц: {total_tables}")
        print(f"   Метаданных: {total_meta} полей (среднее: {total_meta/len(success):.1f})")
        print(f"   Время: {total_time:.1f}с (среднее: {total_time/len(success):.1f}с)")
        
        # Примеры
        print(f"\n📄 Примеры извлеченных метаданных:")
        for r in success[:3]:
            meta_file = output / f"{Path(r['file']).stem}_metadata.json"
            if meta_file.exists():
                with open(meta_file, 'r') as f:
                    meta = json.load(f)
                print(f"\n   {r['file']}:")
                for k, v in list(meta.items())[:5]:
                    if k not in ['полный_текст', 'таблицы'] and v:
                        print(f"      {k}: {str(v)[:50]}")
    
    print(f"\n📁 Результаты: {output}")
    print("="*70)


if __name__ == "__main__":
    main()


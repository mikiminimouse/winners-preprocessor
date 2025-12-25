#!/usr/bin/env python3
"""
Тест обработки 10 PDF файлов через РАБОТАЮЩИЙ Docling API + метаданные через Granite
"""
import os
import sys
import json
import time
import openai
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Конфигурация
DOCLING_API_URL = "http://localhost:8000"
GRANITE_API_URL = "https://8cb66180-db3a-4963-8068-51f87e716259.modelrun.inference.cloud.ru/v1"
GRANITE_API_TOKEN = "ZDRhOWQ3OTAtZjU4MC00MzA2LThhNTgtMDU1NGFlMjE4OWRl.85a830f9340966e0ad1fd1642884c7c8"

# Инициализация Granite client
granite_client = openai.OpenAI(
    api_key=GRANITE_API_TOKEN,
    base_url=GRANITE_API_URL
)


def find_test_pdfs(base_dir: str, limit: int = 10) -> List[Path]:
    """Найти тестовые PDF файлы"""
    pdf_dir = Path(base_dir)
    all_pdfs = []
    
    # Ищем в структуре UNIT_*/files/*.pdf
    for unit_dir in pdf_dir.iterdir():
        if unit_dir.is_dir() and unit_dir.name.startswith("UNIT_"):
            files_dir = unit_dir / "files"
            if files_dir.exists():
                pdfs = list(files_dir.glob("*.pdf"))
                all_pdfs.extend(pdfs)
    
    return all_pdfs[:limit]


def process_pdf_via_docling(pdf_path: Path) -> Dict[str, Any]:
    """
    Обработка PDF через Docling API
    
    Returns:
        Dict с текстом, таблицами и метаданными от Docling
    """
    print(f"   📄 Отправка к Docling API...")
    
    try:
        # Читаем файл
        with open(pdf_path, 'rb') as f:
            files = {'file': (pdf_path.name, f, 'application/pdf')}
            
            # Отправляем POST запрос
            # Docling API использует processor.py который обрабатывает через pdfplumber/pytesseract
            response = requests.post(
                f"{DOCLING_API_URL}/process",
                files=files,
                timeout=300
            )
        
        if response.status_code != 200:
            raise Exception(f"Docling API error: {response.status_code} - {response.text[:200]}")
        
        result = response.json()
        
        # Извлекаем данные
        text = result.get("text", "")
        tables = result.get("tables", [])
        metadata = result.get("metadata", {})
        
        print(f"      ✅ Docling обработал: {len(text)} символов, {len(tables)} таблиц")
        
        return {
            "success": True,
            "text": text,
            "tables": tables,
            "docling_metadata": metadata
        }
        
    except Exception as e:
        print(f"      ❌ Ошибка Docling: {e}")
        return {
            "success": False,
            "error": str(e),
            "text": "",
            "tables": []
        }


def extract_metadata_via_granite(text: str) -> Dict[str, Any]:
    """
    Извлечение 17 полей метаданных через Granite API
    """
    print(f"   🔍 Извлечение метаданных через Granite...")
    
    if len(text.strip()) < 100:
        print(f"      ⚠️  Текст слишком короткий")
        return get_empty_metadata()
    
    # Ограничиваем текст
    max_chars = 15000
    text_for_extraction = text[:max_chars] if len(text) > max_chars else text
    
    prompt = f"""Проанализируй протокол закупки и извлеки метаданные в JSON.

Текст:
{text_for_extraction}

Извлеки поля (если отсутствует - null):
{{
  "номер_процедуры": "номер процедуры",
  "номер_лота": "номер лота",
  "дата_протокола": "ДД.ММ.ГГГГ",
  "победитель": "наименование победителя",
  "ИНН": "ИНН победителя",
  "КПП": "КПП победителя",
  "цена_победителя": "цена (число)",
  "валюта": "RUB/USD/EUR",
  "предмет_закупки": "предмет закупки",
  "дата_начала_подачи": "ДД.ММ.ГГГГ",
  "дата_окончания_подачи": "ДД.ММ.ГГГГ",
  "дата_проведения": "ДД.ММ.ГГГГ",
  "заказчик": "наименование заказчика",
  "организатор": "наименование организатора",
  "состав_комиссии": ["ФИО1", "ФИО2"],
  "участники": [{{"наименование": "name", "статус": "status", "сумма": "amount", "номер_заявки": "num"}}]
}}

Верни ТОЛЬКО JSON."""
    
    try:
        response = granite_client.chat.completions.create(
            model="granite-docling",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000,
            temperature=0.0
        )
        
        raw = response.choices[0].message.content
        metadata = parse_json(raw)
        
        filled = sum(1 for v in metadata.values() if v and str(v).strip())
        print(f"      ✅ Извлечено полей: {filled}/16")
        
        return metadata
        
    except Exception as e:
        print(f"      ❌ Ошибка Granite: {e}")
        return get_empty_metadata()


def parse_json(response: str) -> Dict[str, Any]:
    """Парсинг JSON из ответа"""
    import re
    
    response = response.strip()
    if response.startswith('```'):
        response = response.split('```')[1]
        if response.startswith('json'):
            response = response[4:]
    response = response.strip()
    
    match = re.search(r'\{.*\}', response, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except:
            pass
    
    return get_empty_metadata()


def get_empty_metadata() -> Dict[str, Any]:
    """Пустая структура метаданных"""
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
        "дата_начала_подачи": None,
        "дата_окончания_подачи": None,
        "дата_проведения": None,
        "заказчик": None,
        "организатор": None,
        "состав_комиссии": [],
        "участники": []
    }


def create_markdown(pdf_name: str, text: str, tables: List, metadata: Dict) -> str:
    """Создание Markdown документа"""
    md = f"# {pdf_name}\n\n"
    md += f"**Дата обработки:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    md += "---\n\n"
    
    # Метаданные
    md += "## 📊 Извлеченные метаданные\n\n"
    md += f"- **Номер процедуры:** {metadata.get('номер_процедуры') or 'не найдено'}\n"
    md += f"- **Победитель:** {metadata.get('победитель') or 'не найдено'}\n"
    md += f"- **ИНН:** {metadata.get('ИНН') or 'не найдено'}\n"
    md += f"- **Цена:** {metadata.get('цена_победителя') or 'не найдено'} {metadata.get('валюта') or ''}\n"
    md += f"- **Предмет закупки:** {metadata.get('предмет_закупки') or 'не найдено'}\n\n"
    
    # Текст
    md += "## 📄 Содержание документа\n\n"
    md += text[:5000] if len(text) > 5000 else text
    if len(text) > 5000:
        md += "\n\n...(текст обрезан для читаемости)...\n"
    md += "\n\n"
    
    # Таблицы
    if tables:
        md += f"## 📊 Таблицы ({len(tables)})\n\n"
        for i, table in enumerate(tables[:3], 1):  # Первые 3 таблицы
            md += f"### Таблица {i}\n\n"
            if isinstance(table, list) and table:
                for row_idx, row in enumerate(table[:10]):  # Первые 10 строк
                    md += "| " + " | ".join(str(cell or "") for cell in row) + " |\n"
                    if row_idx == 0:
                        md += "|" + "|".join([" --- "] * len(row)) + "|\n"
            md += "\n"
        if len(tables) > 3:
            md += f"\n_(Показаны первые 3 из {len(tables)} таблиц)_\n\n"
    
    return md


def save_results(output_dir: Path, pdf_name: str, markdown: str, metadata: Dict, full_data: Dict):
    """Сохранение результатов"""
    base_name = Path(pdf_name).stem
    
    # Markdown
    md_file = output_dir / f"{base_name}.md"
    with open(md_file, "w", encoding="utf-8") as f:
        f.write(markdown)
    
    # Метаданные
    meta_file = output_dir / f"{base_name}_metadata.json"
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    # Полные данные
    full_file = output_dir / f"{base_name}_full.json"
    with open(full_file, "w", encoding="utf-8") as f:
        json.dump(full_data, f, indent=2, ensure_ascii=False)
    
    print(f"      💾 Сохранено: {md_file.name}")


def main():
    print("="*70)
    print("ТЕСТ: 10 PDF файлов через Docling API + Granite метаданные")
    print("="*70)
    print()
    
    # Проверка Docling API
    print("1. Проверка Docling API...")
    try:
        response = requests.get(f"{DOCLING_API_URL}/health", timeout=5)
        if response.status_code == 200:
            print("   ✅ Docling API доступен")
        else:
            print(f"   ❌ Docling API недоступен: {response.status_code}")
            sys.exit(1)
    except Exception as e:
        print(f"   ❌ Ошибка подключения к Docling: {e}")
        sys.exit(1)
    
    # Поиск PDF файлов
    print("\n2. Поиск PDF файлов...")
    pdf_files = find_test_pdfs("/root/winners_preprocessor/pilot_winers223/data/pending/direct/pdf", limit=10)
    
    if not pdf_files:
        print("   ❌ PDF файлы не найдены")
        sys.exit(1)
    
    print(f"   ✅ Найдено: {len(pdf_files)} файлов")
    
    # Создание output директории
    output_dir = Path("output_final_test_10_pdfs")
    output_dir.mkdir(exist_ok=True)
    print(f"   📁 Output: {output_dir}")
    
    # Обработка файлов
    print(f"\n3. Обработка {len(pdf_files)} файлов...\n")
    
    results = []
    for i, pdf_file in enumerate(pdf_files, 1):
        print(f"[{i}/{len(pdf_files)}] {pdf_file.name}")
        start_time = time.time()
        
        # Обработка через Docling
        docling_result = process_pdf_via_docling(pdf_file)
        
        if not docling_result["success"]:
            print(f"   ❌ Пропуск из-за ошибки Docling\n")
            results.append({"file": pdf_file.name, "success": False, "error": docling_result.get("error")})
            continue
        
        # Извлечение метаданных
        metadata = extract_metadata_via_granite(docling_result["text"])
        metadata["полный_текст"] = docling_result["text"]
        metadata["таблицы"] = docling_result["tables"]
        
        # Создание Markdown
        markdown = create_markdown(
            pdf_file.name,
            docling_result["text"],
            docling_result["tables"],
            metadata
        )
        
        # Сохранение
        full_data = {
            "source": pdf_file.name,
            "processed_at": datetime.now().isoformat(),
            "text_length": len(docling_result["text"]),
            "tables_count": len(docling_result["tables"]),
            "metadata": metadata,
            "docling_metadata": docling_result.get("docling_metadata", {})
        }
        
        save_results(output_dir, pdf_file.name, markdown, metadata, full_data)
        
        elapsed = time.time() - start_time
        print(f"      ⏱️  Время: {elapsed:.2f}с\n")
        
        results.append({
            "file": pdf_file.name,
            "success": True,
            "text_length": len(docling_result["text"]),
            "tables_count": len(docling_result["tables"]),
            "time": elapsed
        })
    
    # Итоги
    print("="*70)
    print("ИТОГИ")
    print("="*70)
    
    success_count = sum(1 for r in results if r["success"])
    print(f"✅ Успешно обработано: {success_count}/{len(pdf_files)}")
    
    if success_count > 0:
        total_text = sum(r.get("text_length", 0) for r in results if r["success"])
        total_tables = sum(r.get("tables_count", 0) for r in results if r["success"])
        total_time = sum(r.get("time", 0) for r in results if r["success"])
        
        print(f"📊 Всего извлечено:")
        print(f"   Текста: {total_text:,} символов")
        print(f"   Таблиц: {total_tables}")
        print(f"   Время: {total_time:.1f}с (среднее: {total_time/success_count:.1f}с на файл)")
    
    print(f"\n📁 Результаты в: {output_dir}")
    print("="*70)


if __name__ == "__main__":
    main()


#!/usr/bin/env python3
"""
ПРАВИЛЬНЫЙ PDF процессор с РЕАЛЬНЫМ извлечением текста и метаданных

Использует:
- pdfplumber для PDF с текстовым слоем
- pytesseract для сканов
- OpenAI для извлечения метаданных из текста
"""
import os
import sys
import json
import time
import openai
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

try:
    import pdfplumber
    from pdf2image import convert_from_path
    import pytesseract
    from PIL import Image
    PDF_TOOLS_AVAILABLE = True
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("Установите: pip3 install pdfplumber pdf2image pytesseract pillow")
    sys.exit(1)

# Конфигурация
GRANITE_API_URL = os.getenv(
    "GRANITE_API_URL",
    "https://8cb66180-db3a-4963-8068-51f87e716259.modelrun.inference.cloud.ru/v1"
)
GRANITE_API_TOKEN = os.getenv(
    "GRANITE_API_TOKEN",
    "ZDRhOWQ3OTAtZjU4MC00MzA2LThhNTgtMDU1NGFlMjE4OWRl.85a830f9340966e0ad1fd1642884c7c8"
)
GRANITE_MODEL = os.getenv("GRANITE_MODEL", "granite-docling")


class RealPDFProcessor:
    """Процессор для РЕАЛЬНОГО извлечения текста из PDF"""
    
    def __init__(self, output_dir: str = "output_real_extraction"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Инициализация OpenAI клиента для извлечения метаданных
        self.client = openai.OpenAI(
            api_key=GRANITE_API_TOKEN,
            base_url=GRANITE_API_URL
        )
        
        print(f"✅ Процессор инициализирован")
        print(f"   Output: {self.output_dir}")
    
    def extract_text_from_pdf(self, pdf_path: Path) -> Dict[str, Any]:
        """
        Извлечение текста из PDF (текстовый слой + OCR для сканов)
        
        Returns:
            Dict с полным текстом, таблицами, метаданными
        """
        print(f"\n📄 Извлечение текста из: {pdf_path.name}")
        
        all_text = []
        all_tables = []
        pages_count = 0
        has_text_layer = False
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                pages_count = len(pdf.pages)
                print(f"   Страниц: {pages_count}")
                
                for page_num, page in enumerate(pdf.pages, 1):
                    print(f"   Страница {page_num}/{pages_count}...", end=" ")
                    
                    # Попытка извлечь текстовый слой
                    page_text = page.extract_text()
                    
                    if page_text and len(page_text.strip()) > 50:
                        # Есть текстовый слой
                        all_text.append(f"\n\n--- СТРАНИЦА {page_num} ---\n\n{page_text}")
                        has_text_layer = True
                        print("✅ текст", end="")
                    else:
                        # Скан - нужен OCR
                        print("🔍 OCR", end="")
                        ocr_text = self._ocr_page(pdf_path, page_num)
                        if ocr_text:
                            all_text.append(f"\n\n--- СТРАНИЦА {page_num} (OCR) ---\n\n{ocr_text}")
                    
                    # Извлечение таблиц
                    tables = page.extract_tables()
                    if tables:
                        print(f" + {len(tables)} табл.", end="")
                        for table_idx, table in enumerate(tables):
                            all_tables.append({
                                "page": page_num,
                                "table_number": table_idx + 1,
                                "data": table
                            })
                    
                    print()  # новая строка
            
            combined_text = "\n".join(all_text)
            
            print(f"\n✅ Извлечено:")
            print(f"   Текста: {len(combined_text)} символов")
            print(f"   Таблиц: {len(all_tables)}")
            print(f"   Метод: {'Текстовый слой' if has_text_layer else 'OCR'}")
            
            return {
                "success": True,
                "text": combined_text,
                "tables": all_tables,
                "pages": pages_count,
                "has_text_layer": has_text_layer,
                "method": "pdfplumber + pytesseract"
            }
            
        except Exception as e:
            print(f"\n❌ Ошибка: {e}")
            return {
                "success": False,
                "error": str(e),
                "text": "",
                "tables": []
            }
    
    def _ocr_page(self, pdf_path: Path, page_num: int) -> str:
        """OCR для отдельной страницы"""
        try:
            # Конвертируем страницу в изображение
            images = convert_from_path(
                str(pdf_path),
                dpi=200,
                first_page=page_num,
                last_page=page_num
            )
            
            if images:
                # OCR
                text = pytesseract.image_to_string(images[0], lang='rus+eng')
                return text
            
            return ""
        except Exception as e:
            print(f"\n      ⚠️  OCR ошибка: {e}")
            return ""
    
    def extract_metadata(self, text: str) -> Dict[str, Any]:
        """
        Извлечение метаданных из текста через Granite API
        """
        print(f"\n🔍 Извлечение метаданных из текста ({len(text)} символов)...")
        
        # Ограничиваем текст
        max_chars = 15000
        if len(text) > max_chars:
            text_for_extraction = text[:max_chars]
            print(f"   ⚠️  Текст обрезан: {len(text)} → {max_chars}")
        else:
            text_for_extraction = text
        
        if len(text_for_extraction.strip()) < 100:
            print(f"   ⚠️  Текст слишком короткий для извлечения метаданных")
            return self._get_empty_metadata()
        
        # Промпт
        prompt = f"""Проанализируй протокол закупки и извлеки метаданные в JSON формате.

Текст документа:
{text_for_extraction}

Извлеки следующие поля (если поле отсутствует, укажи null):

{{
  "номер_процедуры": "номер процедуры/закупки/тендера",
  "номер_лота": "номер лота",
  "дата_протокола": "дата протокола ДД.ММ.ГГГГ",
  "победитель": "полное наименование победителя",
  "ИНН": "ИНН победителя",
  "КПП": "КПП победителя",
  "цена_победителя": "цена контракта (число)",
  "валюта": "RUB/USD/EUR",
  "предмет_закупки": "предмет закупки",
  "дата_начала_подачи": "ДД.ММ.ГГГГ",
  "дата_окончания_подачи": "ДД.ММ.ГГГГ",
  "дата_проведения": "ДД.ММ.ГГГГ",
  "заказчик": "полное наименование заказчика",
  "организатор": "полное наименование организатора",
  "состав_комиссии": ["ФИО члена 1", "ФИО члена 2"],
  "участники": [
    {{
      "наименование": "название участника",
      "статус": "победитель/отклонен/допущен",
      "сумма": "сумма",
      "номер_заявки": "номер"
    }}
  ]
}}

ВАЖНО: Верни ТОЛЬКО валидный JSON без текста до/после."""
        
        try:
            response = self.client.chat.completions.create(
                model=GRANITE_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4000,
                temperature=0.0
            )
            
            raw_response = response.choices[0].message.content
            metadata = self._parse_json_response(raw_response)
            
            filled_fields = sum(1 for v in metadata.values() if v and v != "")
            print(f"   ✅ Извлечено полей: {filled_fields}/16")
            
            return metadata
            
        except Exception as e:
            print(f"   ❌ Ошибка извлечения метаданных: {e}")
            return self._get_empty_metadata()
    
    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Парсинг JSON из ответа"""
        import re
        
        response = response.strip()
        if response.startswith('```json'):
            response = response[7:]
        if response.startswith('```'):
            response = response[3:]
        if response.endswith('```'):
            response = response[:-3]
        response = response.strip()
        
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass
        
        return self._get_empty_metadata()
    
    def _get_empty_metadata(self) -> Dict[str, Any]:
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
    
    def process_pdf(self, pdf_path: Path) -> Dict[str, Any]:
        """Полная обработка PDF"""
        print(f"\n{'='*70}")
        print(f"🚀 ОБРАБОТКА: {pdf_path.name}")
        print(f"{'='*70}")
        
        start_time = time.time()
        
        # 1. Извлечение текста
        extraction = self.extract_text_from_pdf(pdf_path)
        
        if not extraction["success"]:
            return {
                "success": False,
                "error": extraction.get("error"),
                "pdf_path": str(pdf_path)
            }
        
        # 2. Извлечение метаданных
        metadata = self.extract_metadata(extraction["text"])
        metadata["полный_текст"] = extraction["text"]
        metadata["таблицы"] = extraction["tables"]
        
        # 3. Создание Markdown
        markdown = self._create_markdown(pdf_path, extraction["text"], extraction["tables"], metadata)
        
        # 4. Сохранение
        self._save_results(pdf_path, markdown, metadata, extraction)
        
        processing_time = time.time() - start_time
        
        print(f"\n✅ Готово за {processing_time:.2f}с")
        print(f"   Текста: {len(extraction['text'])} символов")
        print(f"   Таблиц: {len(extraction['tables'])}")
        
        return {
            "success": True,
            "pdf_path": str(pdf_path),
            "text_length": len(extraction["text"]),
            "tables_count": len(extraction["tables"]),
            "processing_time": processing_time
        }
    
    def _create_markdown(
        self,
        pdf_path: Path,
        text: str,
        tables: List[Dict],
        metadata: Dict[str, Any]
    ) -> str:
        """Создание форматированного Markdown"""
        md = f"# {pdf_path.name}\n\n"
        md += f"**Дата обработки:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        md += "---\n\n"
        
        # Метаданные
        md += "## 📊 Метаданные\n\n"
        md += f"- **Номер процедуры:** {metadata.get('номер_процедуры') or 'не найдено'}\n"
        md += f"- **Номер лота:** {metadata.get('номер_лота') or 'не найдено'}\n"
        md += f"- **Дата протокола:** {metadata.get('дата_протокола') or 'не найдено'}\n"
        md += f"- **Победитель:** {metadata.get('победитель') or 'не найдено'}\n"
        md += f"- **ИНН:** {metadata.get('ИНН') or 'не найдено'}\n"
        md += f"- **КПП:** {metadata.get('КПП') or 'не найдено'}\n"
        md += f"- **Цена:** {metadata.get('цена_победителя') or 'не найдено'} {metadata.get('валюта') or ''}\n"
        md += f"- **Предмет закупки:** {metadata.get('предмет_закупки') or 'не найдено'}\n"
        md += f"- **Заказчик:** {metadata.get('заказчик') or 'не найдено'}\n\n"
        
        # Текст документа
        md += "## 📄 Содержание документа\n\n"
        md += text + "\n\n"
        
        # Таблицы
        if tables:
            md += f"## 📊 Таблицы ({len(tables)})\n\n"
            for table_info in tables:
                md += f"### Таблица {table_info['table_number']} (Страница {table_info['page']})\n\n"
                table_data = table_info['data']
                if table_data:
                    # Markdown таблица
                    for i, row in enumerate(table_data):
                        md += "| " + " | ".join(str(cell or "") for cell in row) + " |\n"
                        if i == 0:
                            md += "|" + "|".join([" --- "] * len(row)) + "|\n"
                md += "\n"
        
        return md
    
    def _save_results(
        self,
        pdf_path: Path,
        markdown: str,
        metadata: Dict[str, Any],
        extraction: Dict[str, Any]
    ):
        """Сохранение результатов"""
        base_name = pdf_path.stem
        
        # Markdown
        md_file = self.output_dir / f"{base_name}.md"
        with open(md_file, "w", encoding="utf-8") as f:
            f.write(markdown)
        print(f"   💾 {md_file.name}")
        
        # Метаданные JSON
        metadata_file = self.output_dir / f"{base_name}_metadata.json"
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        print(f"   💾 {metadata_file.name}")
        
        # Полные данные
        full_file = self.output_dir / f"{base_name}_full.json"
        with open(full_file, "w", encoding="utf-8") as f:
            json.dump({
                "source": pdf_path.name,
                "processed_at": datetime.now().isoformat(),
                "extraction_info": {
                    "pages": extraction["pages"],
                    "has_text_layer": extraction["has_text_layer"],
                    "method": extraction["method"],
                    "text_length": len(extraction["text"]),
                    "tables_count": len(extraction["tables"])
                },
                "metadata": metadata
            }, f, indent=2, ensure_ascii=False)
        print(f"   💾 {full_file.name}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="РЕАЛЬНАЯ обработка PDF с извлечением текста")
    parser.add_argument("pdf_path", help="Путь к PDF файлу или директории")
    parser.add_argument("--output", "-o", default="output_real_extraction", help="Директория для результатов")
    parser.add_argument("--limit", "-l", type=int, help="Лимит файлов для обработки")
    
    args = parser.parse_args()
    
    pdf_path = Path(args.pdf_path)
    processor = RealPDFProcessor(output_dir=args.output)
    
    if pdf_path.is_file():
        # Один файл
        result = processor.process_pdf(pdf_path)
        sys.exit(0 if result["success"] else 1)
    
    elif pdf_path.is_dir():
        # Директория
        pdf_files = list(pdf_path.glob("*.pdf"))
        
        if not pdf_files:
            print(f"❌ PDF файлы не найдены в {pdf_path}")
            sys.exit(1)
        
        if args.limit:
            pdf_files = pdf_files[:args.limit]
        
        print(f"\n📁 Найдено PDF файлов: {len(pdf_files)}")
        
        success_count = 0
        for i, pdf_file in enumerate(pdf_files, 1):
            print(f"\n[{i}/{len(pdf_files)}]")
            result = processor.process_pdf(pdf_file)
            if result["success"]:
                success_count += 1
        
        print(f"\n{'='*70}")
        print(f"✅ Успешно: {success_count}/{len(pdf_files)}")
        print(f"   Результаты в: {processor.output_dir}")
        print(f"{'='*70}")
    
    else:
        print(f"❌ Путь не найден: {pdf_path}")
        sys.exit(1)


if __name__ == "__main__":
    main()


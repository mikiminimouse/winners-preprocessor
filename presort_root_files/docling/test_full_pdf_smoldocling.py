#!/usr/bin/env python3
"""
ПОЛНАЯ ОБРАБОТКА PDF ЧЕРЕЗ SMOLDOCLING
Извлечение всего текста, таблиц и структуры документа
"""
import os
import sys
import json
import time
import base64
from pathlib import Path
from datetime import datetime
from PIL import Image
import io

try:
    import openai
    OPENAI_SDK_AVAILABLE = True
except ImportError:
    OPENAI_SDK_AVAILABLE = False
    print("⚠️  openai SDK не установлен. Установите: pip install openai")

try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
    print("⚠️  pdf2image не установлен. Установите: pip install pdf2image")
    print("   Также требуется: sudo apt-get install poppler-utils")

# Конфигурация для SmolDocling
API_TOKEN = "ZDRhOWQ3OTAtZjU4MC00MzA2LThhNTgtMDU1NGFlMjE4OWRl.85a830f9340966e0ad1fd1642884c7c8"
BASE_URL = "https://d63e30af-085a-49f0-9724-8162da967af2.modelrun.inference.cloud.ru/v1"
MODEL_NAME = "model-run-4qigw-disease"

# Тестовый файл
TEST_FILE = "/root/winners_preprocessor/normalized/UNIT_43a02eedd2bbca86/files/! Протокол ЭМ-17.pdf"
OUTPUT_DIR = Path("/root/winners_preprocessor/output_full_pdf_test")

class FullSmolDoclingProcessor:
    def __init__(self):
        if not OPENAI_SDK_AVAILABLE:
            raise ImportError("openai SDK не установлен")

        self.client = openai.OpenAI(
            api_key=API_TOKEN,
            base_url=BASE_URL,
            timeout=300.0  # Увеличено для больших документов
        )
        self.model = MODEL_NAME
        OUTPUT_DIR.mkdir(exist_ok=True)

    def wait_for_server_ready(self, max_wait_time: int = 60) -> bool:
        """Wait for the inference server to be ready"""
        print(f"⏳ Ожидание готовности сервера SmolDocling (максимум {max_wait_time} секунд)...")

        start_time = time.time()
        while time.time() - start_time < max_wait_time:
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": "Hello"}],
                    max_tokens=10,
                    temperature=0.5
                )
                if response.choices[0].message.content:
                    print("✅ Сервер готов к работе")
                    return True
            except Exception as e:
                print(f"    Сервер еще не готов... ({str(e)[:50]}...)")
                time.sleep(5)

        print("❌ Сервер не стал доступен в течение отведенного времени")
        return False

    def get_pdf_pages_info(self, pdf_path: Path) -> dict:
        """Получить информацию о страницах PDF"""
        print(f"📄 Анализ PDF: {pdf_path.name}")

        try:
            # Попробуем получить все страницы
            all_pages = convert_from_path(str(pdf_path), dpi=72)  # Низкий DPI для быстрого анализа
            total_pages = len(all_pages)

            print(f"   Найдено страниц: {total_pages}")

            # Получить размеры первой страницы с высоким DPI
            if all_pages:
                first_page = convert_from_path(str(pdf_path), dpi=300, first_page=1, last_page=1)[0]
                print(f"   Размер первой страницы: {first_page.size} (при DPI=300)")

            return {
                'total_pages': total_pages,
                'first_page_size': first_page.size if all_pages else None,
                'file_size_mb': pdf_path.stat().st_size / (1024 * 1024)
            }

        except Exception as e:
            print(f"❌ Ошибка анализа PDF: {e}")
            return {'error': str(e)}

    def create_high_quality_thumbnail(self, pdf_path: Path, page_num: int = 1) -> str:
        """Создать высококачественный thumbnail для лучшего OCR"""
        print(f"   Создание HQ thumbnail страницы {page_num} из PDF: {pdf_path.name}")

        if not PDF2IMAGE_AVAILABLE:
            raise ImportError("pdf2image not installed")

        try:
            # Конвертировать с высоким DPI для лучшего качества
            pil_images = convert_from_path(
                str(pdf_path),
                dpi=300,  # Высокий DPI для лучшего OCR
                first_page=page_num,
                last_page=page_num
            )

            if not pil_images:
                raise ValueError(f"Не удалось конвертировать страницу {page_num}")

            img = pil_images[0]

            # Конвертировать в RGB если необходимо
            if img.mode != 'RGB':
                img = img.convert('RGB')

            # Максимальный размер 1500px по большей стороне для баланса качества/размера
            max_size = 1500
            if max(img.size) > max_size:
                ratio = max_size / max(img.size)
                new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)

            print(f"   Thumbnail размер: {img.size} (был оптимизирован до max {max_size}px)")

            # Сохранить как JPEG с высоким качеством
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='JPEG', quality=95, optimize=True)
            base64_img = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')

            print(f"   ✅ HQ Thumbnail создан: {len(base64_img)} chars base64")
            return base64_img

        except Exception as e:
            print(f"❌ Ошибка создания thumbnail: {e}")
            raise

    def process_page_with_different_prompts(self, base64_thumbnail: str, page_num: int) -> dict:
        """Обработать страницу с разными промптами для полного извлечения"""
        print(f"   Обработка страницы {page_num} с разными промптами...")

        prompts = [
            "Convert this document page to structured docling format with full text extraction and table recognition.",
            "Extract all text, tables, and layout information from this document page in docling format.",
            "Convert this page to docling with complete OCR, table detection, and text extraction.",
            "Process this document page for full text and table extraction using docling format."
        ]

        results = {}

        for i, prompt in enumerate(prompts):
            print(f"     Промпт {i+1}/{len(prompts)}: {prompt[:50]}...")

            try:
                image_url = f"data:image/jpeg;base64,{base64_thumbnail}"

                messages_content = [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_url}}
                ]

                start_time = time.time()
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": messages_content}],
                    max_tokens=8000,  # Увеличено для больших документов
                    temperature=0.0
                )

                processing_time = time.time() - start_time
                tokens_used = response.usage.total_tokens if response.usage else 0
                doctags = response.choices[0].message.content

                print(f"       ✅ УСПЕХ: {len(doctags)} символов, {tokens_used} токенов, {processing_time:.2f}сек")

                results[f'prompt_{i+1}'] = {
                    'doctags': doctags,
                    'tokens_used': tokens_used,
                    'processing_time': processing_time,
                    'success': True
                }

            except Exception as e:
                print(f"       ❌ Ошибка: {e}")
                results[f'prompt_{i+1}'] = {
                    'error': str(e),
                    'success': False
                }

        return results

    def combine_doctags_results(self, results: dict) -> str:
        """Комбинировать результаты из разных промптов для максимального покрытия"""
        print("   Комбинирование результатов из разных промптов...")

        all_doctags = []

        for prompt_key, result in results.items():
            if result.get('success') and 'doctags' in result:
                doctags = result['doctags'].strip()
                if doctags and len(doctags) > 10:  # Минимум 10 символов
                    all_doctags.append(doctags)

        # Объединить все результаты
        combined_doctags = '\n'.join(all_doctags)

        # Удалить дубликаты строк
        unique_lines = []
        seen_lines = set()
        for line in combined_doctags.split('\n'):
            line = line.strip()
            if line and line not in seen_lines:
                unique_lines.append(line)
                seen_lines.add(line)

        final_doctags = '\n'.join(unique_lines)
        print(f"   ✅ Комбинировано: {len(all_doctags)} промптов → {len(final_doctags)} символов финального текста")

        return final_doctags

    def doctags_to_markdown(self, doctags: str, pdf_path: Path, page_num: int = 1) -> str:
        """Конвертация DocTags в Markdown с поддержкой таблиц"""
        print("   Конвертация DocTags в Markdown с таблицами...")

        lines = doctags.strip().split('\n')
        markdown_parts = []
        current_paragraph = []
        table_rows = []

        for line in lines:
            if not line.strip():
                continue

            parts = line.split('>')
            if len(parts) >= 5:
                content = parts[-1].strip()  # Последняя часть - контент

                if content:
                    # Простая эвристика для таблиц (если много | или табуляций)
                    if '|' in content or '\t' in content or any(char.isdigit() for char in content[:10]):
                        # Возможная таблица
                        if not table_rows or content.count('|') != table_rows[-1].count('|'):
                            # Новая таблица
                            if table_rows:
                                # Завершить предыдущую таблицу
                                markdown_parts.append(self.format_table(table_rows))
                                table_rows = []

                        table_rows.append(content)
                    else:
                        # Обычный текст
                        if table_rows:
                            # Завершить таблицу перед текстом
                            markdown_parts.append(self.format_table(table_rows))
                            table_rows = []

                        current_paragraph.append(content)

        # Завершить последнюю таблицу
        if table_rows:
            markdown_parts.append(self.format_table(table_rows))

        # Добавить оставшийся текст
        if current_paragraph:
            full_text = ' '.join(current_paragraph)
            sentences = full_text.split('. ')
            for sentence in sentences:
                if sentence.strip():
                    markdown_parts.append(sentence.strip() + '.')

        markdown_content = '\n\n'.join(markdown_parts) if markdown_parts else "*Текст не распознан*"

        # Добавить заголовок
        header = f"# Полное содержимое документа: {pdf_path.name}\n\n"
        header += f"**Страница:** {page_num}\n"
        header += f"**Обработано через SmolDocling**\n"
        header += f"**Дата обработки:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        return header + markdown_content

    def format_table(self, table_rows: list) -> str:
        """Форматировать строки как Markdown таблицу"""
        if not table_rows:
            return ""

        # Простое форматирование таблиц
        markdown_table = []

        for i, row in enumerate(table_rows):
            # Заменить табуляции и множественные пробелы на |
            clean_row = row.replace('\t', '|').replace('  ', ' ')
            # Убедиться, что есть разделители
            if '|' not in clean_row:
                clean_row = clean_row.replace(' ', '|')

            markdown_table.append(clean_row)

            # Добавить разделитель после заголовка
            if i == 0 and len(table_rows) > 1:
                separators = ['---'] * len(clean_row.split('|'))
                markdown_table.append('|'.join(separators))

        return '\n'.join(markdown_table)

    def extract_detailed_winners_info(self, doctags: str) -> dict:
        """Детальный анализ информации о победителях"""
        print("   Детальный анализ информации о победителях...")

        text_content = doctags.replace('>', ' ').replace('<', ' ').lower()

        # Расширенный поиск
        winners_info = {
            "has_protocol": "протокол" in text_content,
            "has_winners": any(word in text_content for word in ["победител", "победил", "выиграл", "победит", "побед"]),
            "has_contract": any(word in text_content for word in ["контракт", "договор", "сделк", "закупк", "конкурс"]),
            "has_amount": any(word in text_content for word in ["рубл", "сумм", "стоимост", "цен", "тысяч", "миллион"]),
            "has_commission": any(word in text_content for word in ["комисси", "заседани", "рассмотрени", "член"]),
            "has_participants": any(word in text_content for word in ["участник", "поставщик", "заявк"]),
            "has_decision": any(word in text_content for word in ["решени", "определ", "выбор"]),
            "document_type": "protocol" if "протокол" in text_content else "tender_docs" if "закупк" in text_content else "unknown",
            "extracted_text_length": len(text_content.strip()),
            "confidence_score": self.calculate_confidence(text_content)
        }

        return winners_info

    def calculate_confidence(self, text: str) -> float:
        """Оценить уверенность распознавания"""
        score = 0.0

        # Ключевые слова протокола
        protocol_keywords = ["протокол", "заседани", "комисси", "решен"]
        score += sum(1 for keyword in protocol_keywords if keyword in text) * 0.2

        # Ключевые слова закупок
        tender_keywords = ["закупк", "контракт", "победител", "тендер"]
        score += sum(1 for keyword in tender_keywords if keyword in text) * 0.3

        # Длина текста
        if len(text) > 100:
            score += 0.3
        elif len(text) > 50:
            score += 0.2

        # Присутствие цифр (номера, суммы)
        if any(char.isdigit() for char in text):
            score += 0.2

        return min(score, 1.0)  # Максимум 1.0

    def process_full_document(self, pdf_path: Path) -> dict:
        """Полная обработка документа"""
        print(f"\n🔍 ПОЛНАЯ ОБРАБОТКА ДОКУМЕНТА: {pdf_path.name}")

        # Анализ PDF
        pdf_info = self.get_pdf_pages_info(pdf_path)
        print(f"📊 Информация о PDF: {pdf_info}")

        all_results = {}

        # Обработать каждую страницу
        total_pages = min(pdf_info.get('total_pages', 1), 5)  # Максимум 5 страниц для теста

        for page_num in range(1, total_pages + 1):
            print(f"\n📄 ОБРАБОТКА СТРАНИЦЫ {page_num}/{total_pages}")

            try:
                # Создать HQ thumbnail
                base64_thumbnail = self.create_high_quality_thumbnail(pdf_path, page_num)

                # Обработать с разными промптами
                prompt_results = self.process_page_with_different_prompts(base64_thumbnail, page_num)

                # Комбинировать результаты
                combined_doctags = self.combine_doctags_results(prompt_results)

                # Конвертировать в Markdown
                markdown_content = self.doctags_to_markdown(combined_doctags, pdf_path, page_num)

                # Детальный анализ
                winners_info = self.extract_detailed_winners_info(combined_doctags)

                page_result = {
                    'page_number': page_num,
                    'pdf_info': pdf_info,
                    'prompt_results': prompt_results,
                    'combined_doctags': combined_doctags,
                    'markdown_content': markdown_content,
                    'winners_info': winners_info,
                    'processing_timestamp': datetime.now().isoformat()
                }

                all_results[f'page_{page_num}'] = page_result

                # Сохранить результаты страницы
                page_dir = OUTPUT_DIR / f"page_{page_num}"
                page_dir.mkdir(exist_ok=True)

                # DocTags
                with open(page_dir / f"{pdf_path.stem}_page_{page_num}_doctags.txt", "w", encoding="utf-8") as f:
                    f.write(combined_doctags)

                # Markdown
                with open(page_dir / f"{pdf_path.stem}_page_{page_num}_content.md", "w", encoding="utf-8") as f:
                    f.write(markdown_content)

                # Анализ
                with open(page_dir / f"{pdf_path.stem}_page_{page_num}_analysis.json", "w", encoding="utf-8") as f:
                    json.dump({
                        'pdf_file': str(pdf_path),
                        'page_result': page_result
                    }, f, indent=2, ensure_ascii=False)

                print(f"💾 Результаты страницы {page_num} сохранены в {page_dir}")

            except Exception as e:
                print(f"❌ Ошибка обработки страницы {page_num}: {e}")
                all_results[f'page_{page_num}'] = {'error': str(e)}

        return all_results

    def create_final_summary(self, all_results: dict, pdf_path: Path):
        """Создать финальную сводку по всему документу"""
        print("\n📋 СОЗДАНИЕ ФИНАЛЬНОЙ СВОДКИ...")

        # Комбинировать все Markdown
        all_markdown_parts = []

        # Заголовок документа
        summary_header = f"# ПОЛНЫЙ АНАЛИЗ ДОКУМЕНТА: {pdf_path.name}\n\n"
        summary_header += f"**Всего обработано страниц:** {len(all_results)}\n"
        summary_header += f"**Дата полной обработки:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        all_markdown_parts.append(summary_header)

        # Собрать статистику
        total_text_length = 0
        all_winners_info = []

        for page_key, page_result in all_results.items():
            if 'error' in page_result:
                continue

            page_num = page_result['page_number']
            markdown = page_result['markdown_content']
            winners_info = page_result['winners_info']

            all_markdown_parts.append(f"## СТРАНИЦА {page_num}\n")
            all_markdown_parts.append(markdown)
            all_markdown_parts.append("\n---\n")

            total_text_length += winners_info.get('extracted_text_length', 0)
            all_winners_info.append(winners_info)

        # Добавить сводную информацию
        summary_info = "\n## СВОДНАЯ ИНФОРМАЦИЯ\n\n"
        summary_info += f"- **Общий объем извлеченного текста:** {total_text_length} символов\n"

        if all_winners_info:
            avg_confidence = sum(info.get('confidence_score', 0) for info in all_winners_info) / len(all_winners_info)
            summary_info += f"- **Средняя уверенность распознавания:** {avg_confidence:.2f}\n"

            # Агрегировать признаки
            has_protocol = any(info.get('has_protocol', False) for info in all_winners_info)
            has_contract = any(info.get('has_contract', False) for info in all_winners_info)
            has_winners = any(info.get('has_winners', False) for info in all_winners_info)

            summary_info += f"- **Тип документа:** {'Протокол' if has_protocol else 'Документы закупок' if has_contract else 'Неизвестный'}\n"
            summary_info += f"- **Содержит информацию о победителях:** {'Да' if has_winners else 'Нет'}\n"

        all_markdown_parts.append(summary_info)

        # Сохранить полный документ
        final_markdown = '\n'.join(all_markdown_parts)

        final_file = OUTPUT_DIR / f"{pdf_path.stem}_FULL_DOCUMENT.md"
        with open(final_file, "w", encoding="utf-8") as f:
            f.write(final_markdown)

        print(f"💾 Полный документ сохранен: {final_file}")
        print(f"📊 Общий объем текста: {total_text_length} символов")

        return final_markdown

    def run(self):
        print("🚀 ПОЛНАЯ ОБРАБОТКА PDF ЧЕРЕЗ SMOLDOCLING")
        print(f"Файл: {TEST_FILE}")

        if not self.wait_for_server_ready():
            print("❌ Сервер не готов к работе. Завершение.")
            return

        print("✅ Сервер готов к работе")

        pdf_path = Path(TEST_FILE)
        if not pdf_path.exists():
            print(f"❌ Файл не найден: {pdf_path}")
            return

        # Полная обработка документа
        all_results = self.process_full_document(pdf_path)

        # Создать финальную сводку
        final_markdown = self.create_final_summary(all_results, pdf_path)

        # Сохранить полный отчет
        report_file = OUTPUT_DIR / f"{pdf_path.stem}_full_report.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump({
                'pdf_file': str(pdf_path),
                'processing_timestamp': datetime.now().isoformat(),
                'all_results': all_results,
                'final_summary': {
                    'total_pages_processed': len(all_results),
                    'total_text_extracted': sum(
                        result.get('winners_info', {}).get('extracted_text_length', 0)
                        for result in all_results.values()
                        if 'error' not in result
                    )
                }
            }, f, indent=2, ensure_ascii=False)

        print(f"💾 Полный отчет сохранен: {report_file}")

        print("\n🎉 ПОЛНАЯ ОБРАБОТКА ЗАВЕРШЕНА!")
        print("📂 Результаты доступны в папке:")
        print(f"   {OUTPUT_DIR}")

        # Показать превью финального документа
        preview_length = 1000
        preview = final_markdown[:preview_length] + ("..." if len(final_markdown) > preview_length else "")
        print("\n📄 ПРЕВЬЮ ПОЛНОГО ДОКУМЕНТА:")
        print("-" * 60)
        print(preview)
        print("-" * 60)

if __name__ == "__main__":
    processor = FullSmolDoclingProcessor()
    processor.run()

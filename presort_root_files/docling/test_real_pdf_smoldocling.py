#!/usr/bin/env python3
"""
Тест обработки реального PDF файла через SmolDocling с конвертацией в Markdown
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
OUTPUT_DIR = Path("/root/winners_preprocessor/output_real_pdf_test")

class SmolDoclingProcessor:
    def __init__(self):
        if not OPENAI_SDK_AVAILABLE:
            raise ImportError("openai SDK не установлен")

        self.client = openai.OpenAI(
            api_key=API_TOKEN,
            base_url=BASE_URL,
            timeout=120.0
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

    def create_optimized_thumbnail(self, pdf_path: Path) -> str:
        """Создать оптимизированный thumbnail для SmolDocling"""
        print(f"   Создание thumbnail из PDF: {pdf_path.name}")

        if not PDF2IMAGE_AVAILABLE:
            raise ImportError("pdf2image not installed")

        # Конвертировать первую страницу с ВЫСОКИМ DPI для лучшего OCR
        pil_images = convert_from_path(str(pdf_path), dpi=300, first_page=1, last_page=1)
        img = pil_images[0]

        # Конвертировать в RGB если необходимо
        if img.mode != 'RGB':
            img = img.convert('RGB')

        # Создать thumbnail максимум 1200x1200 пикселей (увеличено!)
        img.thumbnail((1200, 1200), Image.Resampling.LANCZOS)

        # Сохранить как JPEG с качеством 85% (увеличено!)
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='JPEG', quality=85, optimize=True)
        base64_img = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')

        print(f"   ✅ Thumbnail создан: {img.size}, base64 длина: {len(base64_img)}")
        return base64_img

    def process_pdf_with_smoldocling(self, pdf_path: Path) -> str:
        """Обработать PDF через SmolDocling"""
        print(f"\n🧠 Обработка PDF через SmolDocling: {pdf_path.name}")

        try:
            # Создать thumbnail
            base64_thumbnail = self.create_optimized_thumbnail(pdf_path)

            # Подготовить запрос для SmolDocling
            prompt = "Convert this document page to structured docling format with full text extraction."
            image_url = f"data:image/jpeg;base64,{base64_thumbnail}"

            messages_content = [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_url}}
            ]

            print("   Отправка в SmolDocling...")
            start_time = time.time()

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": messages_content}],
                max_tokens=4000,  # Увеличено для лучшего качества
                temperature=0.0
            )

            processing_time = time.time() - start_time
            tokens_used = response.usage.total_tokens if response.usage else 0

            doctags = response.choices[0].message.content
            print(f"   ✅ УСПЕХ! Ответ получен за {processing_time:.2f} секунд")
            print(f"   Токенов использовано: {tokens_used}")
            print(f"   Длина DocTags: {len(doctags)} символов")

            return doctags

        except Exception as e:
            print(f"❌ Ошибка обработки {pdf_path.name}: {e}")
            return None

    def doctags_to_markdown(self, doctags: str, pdf_path: Path) -> str:
        """Простая конвертация DocTags в Markdown"""
        print("   Конвертация DocTags в Markdown...")

        # Разделить на строки
        lines = doctags.strip().split('\n')
        markdown_content = []
        current_text = []

        for line in lines:
            if not line.strip():
                continue

            parts = line.split('>')
            if len(parts) >= 5:  # x1>y1>x2>y2>content или type>x1>y1>x2>y2>page>content
                # Найти текстовую часть (последняя часть после координат)
                content = parts[-1] if len(parts) > 4 else ""
                if content.strip():
                    current_text.append(content.strip())

        # Объединить текст в параграфы
        if current_text:
            full_text = ' '.join(current_text)
            # Разбить на предложения для лучшей читаемости
            sentences = full_text.split('. ')
            for sentence in sentences:
                if sentence.strip():
                    markdown_content.append(sentence.strip() + '.')

        markdown = '\n\n'.join(markdown_content) if markdown_content else "*Текст не распознан*"

        # Добавить заголовок
        header = f"# Содержимое документа: {pdf_path.name}\n\n"
        header += f"**Обработано через SmolDocling**\n"
        header += f"**Дата обработки:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        return header + markdown

    def extract_winners_info(self, doctags: str) -> dict:
        """Извлечь информацию о победителях из DocTags"""
        print("   Извлечение информации о победителях...")

        # Очистить текст от координат и получить только читаемый контент
        text_content = doctags.replace('>', ' ').replace('<', ' ').lower()

        winners_info = {
            "has_protocol": "протокол" in text_content,
            "has_winners": any(word in text_content for word in ["победител", "победил", "выиграл", "победит"]),
            "has_contract": any(word in text_content for word in ["контракт", "договор", "сделк", "закупк"]),
            "has_amount": any(word in text_content for word in ["рубл", "сумм", "стоимост", "цен"]),
            "has_commission": any(word in text_content for word in ["комисси", "заседани", "рассмотрени"]),
            "document_type": "protocol" if "протокол" in text_content else "unknown",
            "extracted_text_length": len(text_content.strip())
        }

        return winners_info

    def run(self):
        print("🎯 ТЕСТ ОБРАБОТКИ РЕАЛЬНОГО PDF ЧЕРЕЗ SMOLDOCLING")
        print(f"Файл: {TEST_FILE}")

        if not self.wait_for_server_ready():
            print("❌ Сервер не готов к работе. Завершение.")
            return

        print("✅ Сервер готов к работе")

        pdf_path = Path(TEST_FILE)
        if not pdf_path.exists():
            print(f"❌ Файл не найден: {pdf_path}")
            return

        # Обработать PDF
        doctags = self.process_pdf_with_smoldocling(pdf_path)

        if not doctags:
            print("❌ Не удалось получить DocTags")
            return

        # Сохранить DocTags
        doctags_file = OUTPUT_DIR / f"{pdf_path.stem}_doctags.txt"
        with open(doctags_file, "w", encoding="utf-8") as f:
            f.write(doctags)
        print(f"💾 DocTags сохранены: {doctags_file}")

        # Конвертировать в Markdown
        markdown_content = self.doctags_to_markdown(doctags, pdf_path)

        # Сохранить Markdown
        markdown_file = OUTPUT_DIR / f"{pdf_path.stem}_content.md"
        with open(markdown_file, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        print(f"💾 Markdown сохранен: {markdown_file}")

        # Извлечь информацию о победителях
        winners_info = self.extract_winners_info(doctags)

        # Сохранить анализ победителей
        winners_file = OUTPUT_DIR / f"{pdf_path.stem}_winners_analysis.json"
        with open(winners_file, "w", encoding="utf-8") as f:
            json.dump({
                "pdf_file": str(pdf_path),
                "processing_date": datetime.now().isoformat(),
                "winners_info": winners_info,
                "doctags_preview": doctags[:500] + "..." if len(doctags) > 500 else doctags
            }, f, indent=2, ensure_ascii=False)
        print(f"💾 Анализ победителей сохранен: {winners_file}")

        # Вывести результаты
        print("\n🎉 ОБРАБОТКА ЗАВЕРШЕНА!")
        print(f"📄 Markdown длина: {len(markdown_content)} символов")
        print(f"🏆 Информация о победителях: {winners_info}")

        print("\n📋 ПРЕВЬЮ MARKDOWN:")
        print("-" * 50)
        preview = markdown_content[:1000] + "..." if len(markdown_content) > 1000 else markdown_content
        print(preview)
        print("-" * 50)

if __name__ == "__main__":
    processor = SmolDoclingProcessor()
    processor.run()

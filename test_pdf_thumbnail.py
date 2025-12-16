#!/usr/bin/env python3
"""
Тест обработки PDF через SmolDocling с минимальным thumbnail изображением
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
OUTPUT_DIR = Path("/root/winners_preprocessor/output_pdf_thumbnail")

class SmolDoclingThumbnailTester:
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

    def create_pdf_thumbnail(self, pdf_path: Path) -> str:
        """Create a minimal thumbnail image from PDF"""
        print(f"   Создание thumbnail из PDF: {pdf_path.name}")

        if not PDF2IMAGE_AVAILABLE:
            raise ImportError("pdf2image not installed")

        try:
            # Convert only first page with very low DPI
            pil_images = convert_from_path(str(pdf_path), dpi=50, first_page=1, last_page=1)
            if not pil_images:
                raise ValueError("Не удалось конвертировать PDF в изображение.")

            img = pil_images[0]

            # Create very small thumbnail
            img.thumbnail((200, 200), Image.Resampling.LANCZOS)

            # Convert to RGB if necessary
            if img.mode != 'RGB':
                img = img.convert('RGB')

            print(f"   Размер thumbnail: {img.size}")

            # Convert to base64
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='JPEG', quality=50, optimize=True)
            base64_img = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')

            print(f"   Размер base64: {len(base64_img)} символов")

            return base64_img

        except Exception as e:
            print(f"❌ Ошибка создания thumbnail: {e}")
            raise

    def test_thumbnail_processing(self):
        """Test SmolDocling with PDF thumbnail"""
        print("\n🧪 Тестирование обработки PDF через thumbnail...")

        try:
            # Create thumbnail
            base64_thumbnail = self.create_pdf_thumbnail(Path(TEST_FILE))

            # Test with SmolDocling prompt
            prompt = "Convert this page to docling."

            messages_content = [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_thumbnail}"}}
            ]

            print("   Отправка thumbnail в SmolDocling...")
            response_start_time = time.time()
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": messages_content}],
                max_tokens=2000,  # Conservative limit
                temperature=0.0
            )
            response_time = time.time() - response_start_time
            tokens_used = response.usage.total_tokens if response.usage else 0

            print(f"   ✅ Ответ получен за {response_time:.2f} секунд")
            print(f"   Токенов использовано: {tokens_used}")
            print(f"   Длина ответа: {len(response.choices[0].message.content)} символов")

            # Save successful result
            result = {
                "test_type": "pdf_thumbnail",
                "success": True,
                "response_time": response_time,
                "tokens_used": tokens_used,
                "thumbnail_size": len(base64_thumbnail),
                "response": response.choices[0].message.content,
                "pdf_file": TEST_FILE
            }

            result_path = OUTPUT_DIR / "thumbnail_test_result.json"
            with open(result_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"   💾 Результат сохранен: {result_path}")

            # Show response preview
            preview = response.choices[0].message.content[:300] + ("..." if len(response.choices[0].message.content) > 300 else "")
            print(f"   📄 Ответ: {preview}")

        except Exception as e:
            print(f"   ❌ Ошибка: {e}")

            # Save error result
            result = {
                "test_type": "pdf_thumbnail",
                "success": False,
                "error": str(e),
                "pdf_file": TEST_FILE
            }

            result_path = OUTPUT_DIR / "thumbnail_test_error.json"
            with open(result_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"   💾 Ошибка сохранена: {result_path}")

    def run(self):
        print("🧪 ТЕСТИРОВАНИЕ ОБРАБОТКИ PDF ЧЕРЕЗ THUMBNAIL")
        print(f"Файл: {TEST_FILE}")

        if not self.wait_for_server_ready():
            print("❌ Сервер не готов к работе. Завершение.")
            return

        print("✅ Сервер готов к работе")

        # Test thumbnail processing
        self.test_thumbnail_processing()

        print("\n✅ Тестирование завершено")

if __name__ == "__main__":
    tester = SmolDoclingThumbnailTester()
    tester.run()

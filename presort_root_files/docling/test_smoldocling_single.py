#!/usr/bin/env python3
"""
Тест обработки одного файла SmolDocling с минимальными изображениями
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

# Тестовый файл - самый маленький
TEST_FILE = "/root/winners_preprocessor/normalized/UNIT_11c6ba8e496155c1/files/tmp1jp9rv31.pdf"
OUTPUT_DIR = Path("/root/winners_preprocessor/output_single_test")

class SmolDoclingSingleTester:
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
        """Wait for the inference server to be ready (shorter timeout)"""
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
                time.sleep(5)  # Wait 5 seconds

        print("❌ Сервер не стал доступен в течение отведенного времени")
        return False

    def create_minimal_image(self, pdf_path: Path) -> str:
        """Create a minimal test image from PDF"""
        print("   Создание минимального тестового изображения...")

        if not PDF2IMAGE_AVAILABLE:
            raise ImportError("pdf2image not installed")

        try:
            # Convert only first page with very low DPI
            pil_images = convert_from_path(str(pdf_path), dpi=72, first_page=1, last_page=1)
            if not pil_images:
                raise ValueError("Не удалось конвертировать PDF в изображение.")

            img = pil_images[0]

            # Resize to very small size (400px max)
            width, height = img.size
            max_size = 400

            if width > height:
                if width > max_size:
                    new_width = max_size
                    new_height = int(height * (max_size / width))
                else:
                    new_width, new_height = width, height
            else:
                if height > max_size:
                    new_height = max_size
                    new_width = int(width * (max_size / height))
                else:
                    new_width, new_height = width, height

            # Resize
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Convert to RGB if necessary
            if img.mode != 'RGB':
                img = img.convert('RGB')

            print(f"   Размер изображения: {new_width}x{new_height}")

            # Convert to base64
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG', optimize=True, quality=70)
            base64_img = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')

            print(f"   Размер base64: {len(base64_img)} символов")

            return base64_img

        except Exception as e:
            print(f"❌ Ошибка создания минимального изображения: {e}")
            raise

    def test_with_minimal_image(self):
        """Test SmolDocling with a minimal image"""
        print("\n🧪 Тестирование с минимальным изображением...")

        try:
            # Create minimal image
            base64_image = self.create_minimal_image(Path(TEST_FILE))

            # Test with different prompts
            prompts_to_test = [
                "Convert this page to docling.",
                "Describe this image.",
                "What do you see in this image?"
            ]

            for i, prompt in enumerate(prompts_to_test, 1):
                print(f"\n--- Тест {i}: {prompt} ---")

                messages_content = [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
                ]

                try:
                    print("   Отправка запроса...")
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
                    print(f"   Ответ: {response.choices[0].message.content[:200]}...")

                    # Save successful result
                    result = {
                        "prompt": prompt,
                        "success": True,
                        "response_time": response_time,
                        "tokens_used": tokens_used,
                        "response": response.choices[0].message.content
                    }

                    result_path = OUTPUT_DIR / f"test_result_{i}.json"
                    with open(result_path, "w", encoding="utf-8") as f:
                        json.dump(result, f, indent=2, ensure_ascii=False)
                    print(f"   💾 Результат сохранен: {result_path}")

                except Exception as e:
                    print(f"   ❌ Ошибка: {e}")

                    # Save error result
                    result = {
                        "prompt": prompt,
                        "success": False,
                        "error": str(e)
                    }

                    result_path = OUTPUT_DIR / f"test_error_{i}.json"
                    with open(result_path, "w", encoding="utf-8") as f:
                        json.dump(result, f, indent=2, ensure_ascii=False)
                    print(f"   💾 Ошибка сохранена: {result_path}")

        except Exception as e:
            print(f"❌ Критическая ошибка: {e}")

    def run(self):
        print("🧪 ТЕСТИРОВАНИЕ SMOLDOCLING С МИНИМАЛЬНЫМ ИЗОБРАЖЕНИЕМ")

        if not self.wait_for_server_ready():
            print("❌ Сервер не готов к работе. Завершение.")
            return

        print("✅ Сервер готов к работе")

        # Test with minimal image
        self.test_with_minimal_image()

        print("\n✅ Тестирование завершено")

if __name__ == "__main__":
    tester = SmolDoclingSingleTester()
    tester.run()

#!/usr/bin/env python3
"""
Отладочный тест обработки PDF через SmolDocling с thumbnail изображениями
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
OUTPUT_DIR = Path("/root/winners_preprocessor/output_debug_thumbnail")

class SmolDoclingDebugTester:
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

    def create_test_thumbnails(self, pdf_path: Path) -> list:
        """Create multiple test thumbnails with different parameters"""
        print(f"   Создание тестовых thumbnails из PDF: {pdf_path.name}")

        if not PDF2IMAGE_AVAILABLE:
            raise ImportError("pdf2image not installed")

        thumbnails = []

        try:
            # Test different DPI values
            dpi_values = [50, 72, 96, 150]

            for dpi in dpi_values:
                print(f"   Создание thumbnail с DPI={dpi}...")

                # Convert first page
                pil_images = convert_from_path(str(pdf_path), dpi=dpi, first_page=1, last_page=1)
                if not pil_images:
                    print(f"     ⚠️  Не удалось конвертировать PDF с DPI={dpi}")
                    continue

                img = pil_images[0]

                # Create thumbnail with different max sizes
                max_sizes = [200, 150, 100]

                for max_size in max_sizes:
                    # Make a copy for each size
                    thumb_img = img.copy()

                    # Create thumbnail
                    thumb_img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

                    # Convert to RGB if necessary
                    if thumb_img.mode != 'RGB':
                        thumb_img = thumb_img.convert('RGB')

                    print(f"     Размер thumbnail: {thumb_img.size} (DPI={dpi}, max_size={max_size})")

                    # Test different formats and qualities
                    formats = ['JPEG', 'PNG']
                    qualities = [50, 70, 90] if 'JPEG' in formats else [None]

                    for fmt in formats:
                        for quality in (qualities if fmt == 'JPEG' else [None]):
                            # Convert to base64
                            img_byte_arr = io.BytesIO()
                            if fmt == 'JPEG':
                                thumb_img.save(img_byte_arr, format=fmt, quality=quality, optimize=True)
                            else:
                                thumb_img.save(img_byte_arr, format=fmt, optimize=True)

                            base64_img = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')

                            # Verify we can decode it back
                            try:
                                decoded = base64.b64decode(base64_img)
                                test_img = Image.open(io.BytesIO(decoded))
                                test_img.verify()
                                print(f"       ✅ {fmt} quality={quality}: {len(base64_img)} chars, size={thumb_img.size}")
                            except Exception as verify_error:
                                print(f"       ❌ {fmt} quality={quality}: Ошибка верификации - {verify_error}")
                                continue

                            thumbnails.append({
                                'dpi': dpi,
                                'max_size': max_size,
                                'format': fmt,
                                'quality': quality,
                                'size': thumb_img.size,
                                'base64': base64_img,
                                'base64_length': len(base64_img)
                            })

            print(f"   Создано {len(thumbnails)} тестовых thumbnails")
            return thumbnails

        except Exception as e:
            print(f"❌ Ошибка создания thumbnails: {e}")
            raise

    def test_thumbnail_variations(self):
        """Test different thumbnail variations"""
        print("\n🧪 Тестирование различных вариаций thumbnail...")

        try:
            # Create test thumbnails
            thumbnails = self.create_test_thumbnails(Path(TEST_FILE))

            if not thumbnails:
                print("❌ Не удалось создать ни одного thumbnail")
                return

            # Test each thumbnail
            for i, thumb in enumerate(thumbnails):
                print(f"\n--- Тест thumbnail {i+1}/{len(thumbnails)} ---")
                print(f"   DPI: {thumb['dpi']}, Size: {thumb['size']}, Format: {thumb['format']}, Quality: {thumb['quality']}")
                print(f"   Base64 length: {thumb['base64_length']} chars")

                # Test with SmolDocling prompt
                prompt = "Convert this page to docling."

                # Try different URL formats
                url_formats = [
                    f"data:image/{thumb['format'].lower()};base64,{thumb['base64']}",
                    f"data:image/jpeg;base64,{thumb['base64']}"  # Always try as JPEG
                ]

                for url_idx, image_url in enumerate(url_formats):
                    print(f"   Тест URL формата {url_idx+1}: {image_url[:50]}...")

                    messages_content = [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ]

                    try:
                        print("     Отправка в SmolDocling...")
                        response_start_time = time.time()
                        response = self.client.chat.completions.create(
                            model=self.model,
                            messages=[{"role": "user", "content": messages_content}],
                            max_tokens=2000,
                            temperature=0.0
                        )
                        response_time = time.time() - response_start_time
                        tokens_used = response.usage.total_tokens if response.usage else 0

                        print(f"     ✅ УСПЕХ! Ответ получен за {response_time:.2f} секунд")
                        print(f"     Токенов использовано: {tokens_used}")
                        print(f"     Длина ответа: {len(response.choices[0].message.content)} символов")

                        # Save successful result
                        result = {
                            'thumbnail_index': i,
                            'thumbnail_config': thumb,
                            'url_format': url_idx,
                            'success': True,
                            'response_time': response_time,
                            'tokens_used': tokens_used,
                            'response': response.choices[0].message.content,
                            'pdf_file': TEST_FILE
                        }

                        result_path = OUTPUT_DIR / f"success_thumb_{i}_format_{url_idx}.json"
                        with open(result_path, "w", encoding="utf-8") as f:
                            json.dump(result, f, indent=2, ensure_ascii=False)
                        print(f"     💾 Результат сохранен: {result_path}")

                        # Show response preview
                        preview = response.choices[0].message.content[:200] + ("..." if len(response.choices[0].message.content) > 200 else "")
                        print(f"     📄 Ответ: {preview}")

                        break  # If one URL format works, don't try others

                    except Exception as e:
                        error_msg = str(e)
                        print(f"     ❌ Ошибка: {error_msg[:100]}...")

                        # Save error result
                        result = {
                            'thumbnail_index': i,
                            'thumbnail_config': thumb,
                            'url_format': url_idx,
                            'success': False,
                            'error': error_msg,
                            'pdf_file': TEST_FILE
                        }

                        result_path = OUTPUT_DIR / f"error_thumb_{i}_format_{url_idx}.json"
                        with open(result_path, "w", encoding="utf-8") as f:
                            json.dump(result, f, indent=2, ensure_ascii=False)

        except Exception as e:
            print(f"❌ Критическая ошибка: {e}")

    def run(self):
        print("🧪 ОТЛАДОЧНЫЙ ТЕСТ THUMBNAIL ОБРАБОТКИ")
        print(f"Файл: {TEST_FILE}")

        if not self.wait_for_server_ready():
            print("❌ Сервер не готов к работе. Завершение.")
            return

        print("✅ Сервер готов к работе")

        # Test thumbnail variations
        self.test_thumbnail_variations()

        print("\n✅ Отладочное тестирование завершено")

if __name__ == "__main__":
    tester = SmolDoclingDebugTester()
    tester.run()

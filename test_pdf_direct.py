#!/usr/bin/env python3
"""
Тест прямой отправки PDF файла в SmolDocling без конвертации в изображения
"""
import os
import sys
import json
import time
import base64
from pathlib import Path
from datetime import datetime

try:
    import openai
    OPENAI_SDK_AVAILABLE = True
except ImportError:
    OPENAI_SDK_AVAILABLE = False
    print("⚠️  openai SDK не установлен. Установите: pip install openai")

# Конфигурация для SmolDocling
API_TOKEN = "ZDRhOWQ3OTAtZjU4MC00MzA2LThhNTgtMDU1NGFlMjE4OWRl.85a830f9340966e0ad1fd1642884c7c8"
BASE_URL = "https://d63e30af-085a-49f0-9724-8162da967af2.modelrun.inference.cloud.ru/v1"
MODEL_NAME = "model-run-4qigw-disease"

# Тестовый файл - самый маленький
TEST_FILE = "/root/winners_preprocessor/normalized/UNIT_11c6ba8e496155c1/files/tmp1jp9rv31.pdf"
OUTPUT_DIR = Path("/root/winners_preprocessor/output_pdf_direct")

class SmolDoclingPDFDirectTester:
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

    def pdf_to_base64(self, pdf_path: Path) -> str:
        """Convert PDF file to base64"""
        print(f"   Конвертация PDF в base64: {pdf_path.name}")

        with open(pdf_path, "rb") as f:
            pdf_data = f.read()

        base64_pdf = base64.b64encode(pdf_data).decode('utf-8')
        print(f"   Размер PDF: {len(pdf_data)} bytes")
        print(f"   Размер base64: {len(base64_pdf)} символов")

        return base64_pdf

    def test_pdf_direct(self):
        """Test sending PDF directly to SmolDocling"""
        print("\n🧪 Тестирование прямой отправки PDF файла...")

        try:
            # Convert PDF to base64
            base64_pdf = self.pdf_to_base64(Path(TEST_FILE))

            # Test different prompts
            prompts_to_test = [
                "Convert this PDF document to docling format.",
                "Analyze this PDF file and extract its structure.",
                "Process this PDF document.",
                f"data:application/pdf;base64,{base64_pdf}"  # Try sending as data URL
            ]

            for i, prompt in enumerate(prompts_to_test, 1):
                print(f"\n--- Тест {i}: Прямая отправка PDF ---")

                # Try different content formats
                if i == 4:
                    # Send as data URL in image_url format (even though it's PDF)
                    messages_content = [
                        {"type": "text", "text": "Convert this document to docling."},
                        {"type": "image_url", "image_url": {"url": prompt}}
                    ]
                else:
                    # Send base64 as text
                    messages_content = [
                        {"type": "text", "text": f"{prompt}\n\nPDF Content (base64): {base64_pdf[:1000]}..."}
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
                        "test_type": "pdf_direct",
                        "prompt_type": i,
                        "prompt": prompt,
                        "success": True,
                        "response_time": response_time,
                        "tokens_used": tokens_used,
                        "response": response.choices[0].message.content
                    }

                    result_path = OUTPUT_DIR / f"pdf_direct_test_{i}.json"
                    with open(result_path, "w", encoding="utf-8") as f:
                        json.dump(result, f, indent=2, ensure_ascii=False)
                    print(f"   💾 Результат сохранен: {result_path}")

                except Exception as e:
                    print(f"   ❌ Ошибка: {e}")

                    # Save error result
                    result = {
                        "test_type": "pdf_direct",
                        "prompt_type": i,
                        "prompt": prompt[:100] + "..." if len(prompt) > 100 else prompt,
                        "success": False,
                        "error": str(e)
                    }

                    result_path = OUTPUT_DIR / f"pdf_direct_error_{i}.json"
                    with open(result_path, "w", encoding="utf-8") as f:
                        json.dump(result, f, indent=2, ensure_ascii=False)
                    print(f"   💾 Ошибка сохранена: {result_path}")

        except Exception as e:
            print(f"❌ Критическая ошибка: {e}")

    def run(self):
        print("🧪 ТЕСТИРОВАНИЕ ПРЯМОЙ ОТПРАВКИ PDF В SMOLDOCLING")

        if not self.wait_for_server_ready():
            print("❌ Сервер не готов к работе. Завершение.")
            return

        print("✅ Сервер готов к работе")

        # Test direct PDF sending
        self.test_pdf_direct()

        print("\n✅ Тестирование завершено")

if __name__ == "__main__":
    tester = SmolDoclingPDFDirectTester()
    tester.run()

#!/usr/bin/env python3
"""
Тест прямой обработки одного PDF файла через SmolDocling без конвертации в изображения
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

# Тестовый файл
TEST_FILE = "/root/winners_preprocessor/normalized/UNIT_43a02eedd2bbca86/files/! Протокол ЭМ-17.pdf"
OUTPUT_DIR = Path("/root/winners_preprocessor/output_single_pdf_direct")

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
        print(f"   Чтение PDF файла: {pdf_path.name}")

        with open(pdf_path, "rb") as f:
            pdf_data = f.read()

        base64_pdf = base64.b64encode(pdf_data).decode('utf-8')
        print(f"   Размер PDF: {len(pdf_data)} bytes")
        print(f"   Размер base64: {len(base64_pdf)} символов")

        return base64_pdf

    def test_pdf_direct_processing(self):
        """Test direct PDF processing through SmolDocling"""
        print("\n🧪 Тестирование прямой обработки PDF файла...")

        try:
            # Read PDF file
            pdf_path = Path(TEST_FILE)
            if not pdf_path.exists():
                raise FileNotFoundError(f"Файл не найден: {pdf_path}")

            base64_pdf = self.pdf_to_base64(pdf_path)

            # Test different approaches for direct PDF processing
            test_cases = [
                {
                    "name": "Base64 in text message",
                    "prompt": f"This is a PDF document encoded in base64. Convert this PDF document to docling format.\n\nPDF Content (base64): {base64_pdf[:50000]}...",
                    "content_type": "text"
                },
                {
                    "name": "Full base64 as text",
                    "prompt": f"Convert this PDF document to docling format.\n\nPDF Base64: {base64_pdf}",
                    "content_type": "text"
                },
                {
                    "name": "PDF as file attachment (text)",
                    "prompt": f"Process this PDF file as PDF scan document.\n\nFile content (base64): {base64_pdf}",
                    "content_type": "text"
                },
                {
                    "name": "Direct PDF instruction",
                    "prompt": "Convert this PDF document to Docling format. Extract text, tables, and structure from the PDF file.",
                    "content_type": "text",
                    "attach_pdf": True
                }
            ]

            for i, test_case in enumerate(test_cases, 1):
                print(f"\n--- Тест {i}: {test_case['name']} ---")

                try:
                    messages_content = []

                    if test_case.get("attach_pdf"):
                        # Try to attach PDF as base64 in different ways
                        messages_content = [
                            {"type": "text", "text": test_case["prompt"]},
                            {"type": "text", "text": f"PDF Data: {base64_pdf[:10000]}..."}  # Truncate for API limits
                        ]
                    else:
                        messages_content = [
                            {"type": "text", "text": test_case["prompt"]}
                        ]

                    print("   Отправка запроса...")
                    response_start_time = time.time()
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=[{"role": "user", "content": messages_content}],
                        max_tokens=4000,  # Conservative limit
                        temperature=0.0
                    )
                    response_time = time.time() - response_start_time
                    tokens_used = response.usage.total_tokens if response.usage else 0

                    print(f"   ✅ Ответ получен за {response_time:.2f} секунд")
                    print(f"   Токенов использовано: {tokens_used}")
                    print(f"   Длина ответа: {len(response.choices[0].message.content)} символов")

                    # Save successful result
                    result = {
                        "test_name": test_case["name"],
                        "test_number": i,
                        "success": True,
                        "response_time": response_time,
                        "tokens_used": tokens_used,
                        "response": response.choices[0].message.content,
                        "pdf_file": str(pdf_path),
                        "pdf_size": len(base64_pdf)
                    }

                    result_path = OUTPUT_DIR / f"pdf_direct_test_{i}_{test_case['name'].replace(' ', '_').lower()}.json"
                    with open(result_path, "w", encoding="utf-8") as f:
                        json.dump(result, f, indent=2, ensure_ascii=False)
                    print(f"   💾 Результат сохранен: {result_path}")

                    # Also save response preview
                    preview = response.choices[0].message.content[:500] + ("..." if len(response.choices[0].message.content) > 500 else "")
                    print(f"   📄 Предварительный просмотр ответа: {preview}")

                except Exception as e:
                    print(f"   ❌ Ошибка: {e}")

                    # Save error result
                    result = {
                        "test_name": test_case["name"],
                        "test_number": i,
                        "success": False,
                        "error": str(e),
                        "pdf_file": str(pdf_path)
                    }

                    result_path = OUTPUT_DIR / f"pdf_direct_error_{i}_{test_case['name'].replace(' ', '_').lower()}.json"
                    with open(result_path, "w", encoding="utf-8") as f:
                        json.dump(result, f, indent=2, ensure_ascii=False)
                    print(f"   💾 Ошибка сохранена: {result_path}")

        except Exception as e:
            print(f"❌ Критическая ошибка: {e}")

    def run(self):
        print("🧪 ТЕСТИРОВАНИЕ ПРЯМОЙ ОБРАБОТКИ PDF ФАЙЛА SMOLDOCLING")
        print(f"Файл: {TEST_FILE}")

        if not self.wait_for_server_ready():
            print("❌ Сервер не готов к работе. Завершение.")
            return

        print("✅ Сервер готов к работе")

        # Test direct PDF processing
        self.test_pdf_direct_processing()

        print("\n✅ Тестирование завершено")

if __name__ == "__main__":
    tester = SmolDoclingPDFDirectTester()
    tester.run()

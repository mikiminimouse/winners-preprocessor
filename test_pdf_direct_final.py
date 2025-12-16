#!/usr/bin/env python3
"""
ФИНАЛЬНЫЙ ТЕСТ: ОБРАБОТКА PDF НАПРЯМУЮ ЧЕРЕЗ SMOLDOCLING
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
OUTPUT_DIR = Path("/root/winners_preprocessor/output_pdf_direct_final")

class DirectPDFProcessor:
    def __init__(self):
        if not OPENAI_SDK_AVAILABLE:
            raise ImportError("openai SDK не установлен")

        self.client = openai.OpenAI(
            api_key=API_TOKEN,
            base_url=BASE_URL,
            timeout=600.0  # Увеличено для больших файлов
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

    def encode_pdf_to_base64(self, pdf_path: Path) -> str:
        """Кодировать PDF файл в base64"""
        print(f"📄 Кодирование PDF в base64: {pdf_path.name}")

        with open(pdf_path, "rb") as pdf_file:
            pdf_data = pdf_file.read()

        base64_pdf = base64.b64encode(pdf_data).decode('utf-8')
        print(f"✅ PDF закодирован: {len(base64_pdf)} символов base64 ({len(pdf_data)} байт)")

        return base64_pdf

    def test_different_pdf_formats(self, base64_pdf: str, pdf_path: Path):
        """Тестировать разные форматы отправки PDF"""
        print("🧪 ТЕСТИРОВАНИЕ РАЗНЫХ ФОРМАТОВ PDF...")

        test_cases = [
            {
                'name': 'PDF as text message',
                'messages': [{"role": "user", "content": f"Process this PDF document: data:application/pdf;base64,{base64_pdf}"}],
                'description': 'PDF как текст в сообщении'
            },
            {
                'name': 'PDF as document attachment',
                'messages': [
                    {"role": "user", "content": [
                        {"type": "text", "text": "Extract all text and tables from this PDF document."},
                        {"type": "file", "file": {"file_data": f"data:application/pdf;base64,{base64_pdf}", "filename": pdf_path.name}}
                    ]}
                ],
                'description': 'PDF как file attachment'
            },
            {
                'name': 'PDF instruction only',
                'messages': [{"role": "user", "content": f"Here is a PDF document encoded in base64. Please extract all text, tables, and structured information: {base64_pdf[:1000]}..."}],
                'description': 'Только инструкция с base64'
            }
        ]

        results = {}

        for i, test_case in enumerate(test_cases):
            print(f"\n--- ТЕСТ {i+1}: {test_case['name']} ---")
            print(f"Описание: {test_case['description']}")

            try:
                start_time = time.time()
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=test_case['messages'],
                    max_tokens=8000,  # Увеличено для больших документов
                    temperature=0.0
                )

                processing_time = time.time() - start_time
                tokens_used = response.usage.total_tokens if response.usage else 0
                content = response.choices[0].message.content

                print("✅ УСПЕХ:")
                print(f"   Время: {processing_time:.2f} сек")
                print(f"   Токенов: {tokens_used}")
                print(f"   Длина ответа: {len(content)} символов")

                results[test_case['name']] = {
                    'success': True,
                    'content': content,
                    'tokens_used': tokens_used,
                    'processing_time': processing_time,
                    'method': test_case['description']
                }

                # Показать превью
                preview = content[:300] + "..." if len(content) > 300 else content
                print(f"   Превью: {preview}")

            except Exception as e:
                error_msg = str(e)
                print(f"❌ ОШИБКА: {error_msg[:100]}...")

                results[test_case['name']] = {
                    'success': False,
                    'error': error_msg,
                    'method': test_case['description']
                }

        return results

    def create_comprehensive_markdown(self, results: dict, pdf_path: Path) -> str:
        """Создать всесторонний Markdown отчет"""
        print("📝 Создание всестороннего Markdown отчета...")

        markdown_parts = []

        # Заголовок
        header = f"# ПОЛНЫЙ АНАЛИЗ PDF ДОКУМЕНТА: {pdf_path.name}\n\n"
        header += f"**Метод обработки:** Прямая отправка PDF в SmolDocling\n"
        header += f"**Дата обработки:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        header += f"**Размер файла:** {pdf_path.stat().st_size} байт\n\n"
        markdown_parts.append(header)

        # Результаты по каждому методу
        total_successful = 0
        total_text_length = 0

        for method_name, result in results.items():
            markdown_parts.append(f"## МЕТОД: {method_name}\n")

            if result['success']:
                total_successful += 1
                content = result['content']
                total_text_length += len(content)

                markdown_parts.append(f"**✅ УСПЕХ**\n")
                markdown_parts.append(f"- **Время обработки:** {result['processing_time']:.2f} сек\n")
                markdown_parts.append(f"- **Токенов использовано:** {result['tokens_used']}\n")
                markdown_parts.append(f"- **Длина извлеченного текста:** {len(content)} символов\n\n")

                # Анализировать контент
                content_analysis = self.analyze_extracted_content(content)
                markdown_parts.append(f"### АНАЛИЗ СОДЕРЖИМОГО\n")
                markdown_parts.append(f"- **Тип документа:** {content_analysis['document_type']}\n")
                markdown_parts.append(f"- **Содержит протокол:** {'Да' if content_analysis['has_protocol'] else 'Нет'}\n")
                markdown_parts.append(f"- **Содержит закупки:** {'Да' if content_analysis['has_procurement'] else 'Нет'}\n")
                markdown_parts.append(f"- **Содержит таблицы:** {'Да' if content_analysis['has_tables'] else 'Нет'}\n")
                markdown_parts.append(f"- **Уровень уверенности:** {content_analysis['confidence']:.2f}\n\n")

                # Показать извлеченный текст
                markdown_parts.append(f"### ИЗВЛЕЧЕННЫЙ ТЕКСТ\n\n")
                markdown_parts.append(f"```\n{content}\n```\n\n")

            else:
                markdown_parts.append(f"**❌ НЕУДАЧА**\n")
                markdown_parts.append(f"- **Ошибка:** {result['error'][:200]}...\n\n")

        # Сводка
        markdown_parts.append(f"## СВОДКА РЕЗУЛЬТАТОВ\n\n")
        markdown_parts.append(f"- **Всего методов протестировано:** {len(results)}\n")
        markdown_parts.append(f"- **Успешных методов:** {total_successful}\n")
        markdown_parts.append(f"- **Общий объем извлеченного текста:** {total_text_length} символов\n")

        if total_successful > 0:
            avg_length = total_text_length / total_successful
            markdown_parts.append(f"- **Средний объем текста на метод:** {avg_length:.0f} символов\n")

        # Выводы
        markdown_parts.append(f"## ВЫВОДЫ\n\n")

        if total_successful == 0:
            markdown_parts.append("❌ **SmolDocling не смог обработать PDF файл напрямую.**\n\n")
            markdown_parts.append("Возможные причины:\n")
            markdown_parts.append("- SmolDocling предназначен только для изображений\n")
            markdown_parts.append("- PDF файлы требуют предварительной конвертации в изображения\n")
            markdown_parts.append("- Сервер имеет ограничения на тип входных данных\n")
        else:
            markdown_parts.append(f"✅ **SmolDocling смог обработать PDF в {total_successful} из {len(results)} методов.**\n\n")
            markdown_parts.append("Рекомендации:\n")
            markdown_parts.append("- Использовать конвертацию PDF в изображения\n")
            markdown_parts.append("- Оптимизировать качество thumbnail\n")
            markdown_parts.append("- Комбинировать результаты разных подходов\n")

        return '\n'.join(markdown_parts)

    def analyze_extracted_content(self, content: str) -> dict:
        """Анализировать извлеченный контент"""
        text_lower = content.lower()

        analysis = {
            'has_protocol': 'протокол' in text_lower,
            'has_procurement': any(word in text_lower for word in ['закупк', 'тендер', 'конкурс', 'предложен']),
            'has_commission': any(word in text_lower for word in ['комисс', 'заседани', 'член']),
            'has_tables': '|' in content or '\t' in content or 'table' in text_lower,
            'has_numbers': any(char.isdigit() for char in content),
            'document_type': 'protocol' if 'протокол' in text_lower else 'procurement' if 'закупк' in text_lower else 'unknown',
            'confidence': 0.0
        }

        # Расчет уверенности
        confidence = 0.0
        if analysis['has_protocol']: confidence += 0.4
        if analysis['has_procurement']: confidence += 0.3
        if analysis['has_commission']: confidence += 0.2
        if analysis['has_numbers']: confidence += 0.1
        if len(content) > 100: confidence += 0.2

        analysis['confidence'] = min(confidence, 1.0)

        return analysis

    def run(self):
        print("🚀 ФИНАЛЬНЫЙ ТЕСТ: ОБРАБОТКА PDF НАПРЯМУЮ")
        print(f"Файл: {TEST_FILE}")

        if not self.wait_for_server_ready():
            print("❌ Сервер не готов к работе. Завершение.")
            return

        print("✅ Сервер готов к работе")

        pdf_path = Path(TEST_FILE)
        if not pdf_path.exists():
            print(f"❌ Файл не найден: {pdf_path}")
            return

        # Кодировать PDF
        base64_pdf = self.encode_pdf_to_base64(pdf_path)

        # Тестировать разные форматы
        results = self.test_different_pdf_formats(base64_pdf, pdf_path)

        # Создать всесторонний отчет
        comprehensive_markdown = self.create_comprehensive_markdown(results, pdf_path)

        # Сохранить результаты
        markdown_file = OUTPUT_DIR / f"{pdf_path.stem}_direct_pdf_analysis.md"
        with open(markdown_file, "w", encoding="utf-8") as f:
            f.write(comprehensive_markdown)

        json_file = OUTPUT_DIR / f"{pdf_path.stem}_direct_pdf_results.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump({
                'pdf_file': str(pdf_path),
                'processing_timestamp': datetime.now().isoformat(),
                'base64_length': len(base64_pdf),
                'original_size_bytes': pdf_path.stat().st_size,
                'test_results': results
            }, f, indent=2, ensure_ascii=False)

        print("\n🎉 АНАЛИЗ ЗАВЕРШЕН!")
        print(f"📁 Результаты сохранены в: {OUTPUT_DIR}")
        print(f"📄 Markdown отчет: {markdown_file}")
        print(f"📊 JSON результаты: {json_file}")

        # Показать превью отчета
        preview_length = 1500
        preview = comprehensive_markdown[:preview_length] + ("..." if len(comprehensive_markdown) > preview_length else "")
        print("\n📋 ПРЕВЬЮ ОТЧЕТА:")
        print("-" * 70)
        print(preview)
        print("-" * 70)

if __name__ == "__main__":
    processor = DirectPDFProcessor()
    processor.run()

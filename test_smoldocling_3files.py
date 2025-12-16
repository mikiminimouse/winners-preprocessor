#!/usr/bin/env python3
"""
Тестирование интеграции SmolDocling на 3 PDF файлах различного качества
"""
import os
import sys
import json
import time
import base64
from pathlib import Path
from typing import Dict, Any, List, Optional
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

# Конфигурация для SmolDocling (используем комбинированный токен)
API_TOKEN = "ZDRhOWQ3OTAtZjU4MC00MzA2LThhNTgtMDU1NGFlMjE4OWRl.85a830f9340966e0ad1fd1642884c7c8"
BASE_URL = "https://d63e30af-085a-49f0-9724-8162da967af2.modelrun.inference.cloud.ru/v1"
MODEL_NAME = "model-run-4qigw-disease"  # Имя модели для SmolDocling

# Пути к тестовым файлам
TEST_FILES = [
    {
        "id": "UNIT_13bd07b0fa0ef660",
        "path": "/root/winners_preprocessor/normalized/UNIT_13bd07b0fa0ef660/files/Протокол рассмотрения и оценки котировочных заявок № 35 от 19.11.2025.pdf",
        "description": "Скан книжного разворота"
    },
    {
        "id": "UNIT_11c6ba8e496155c1",
        "path": "/root/winners_preprocessor/normalized/UNIT_11c6ba8e496155c1/files/tmp1jp9rv31.pdf",
        "description": "Документ среднего качества"
    },
    {
        "id": "UNIT_6e44cf32b40a2035",
        "path": "/root/winners_preprocessor/normalized/UNIT_6e44cf32b40a2035/files/Протокол Труба ПЭ 560.pdf",
        "description": "Документ низкого качества"
    }
]

# Директория для результатов
OUTPUT_DIR = Path("/root/winners_preprocessor/output_smoldocling_3files")
OUTPUT_DIR.mkdir(exist_ok=True)

class SmolDoclingTester:
    def __init__(self):
        if not OPENAI_SDK_AVAILABLE:
            raise ImportError("openai SDK не установлен")
        
        # Используем стандартный OpenAI клиент с нашим токеном
        self.client = openai.OpenAI(
            api_key=API_TOKEN,
            base_url=BASE_URL,
            timeout=120.0
        )
        self.model = MODEL_NAME
        self.results = []

    def wait_for_server_ready(self, max_wait_time: int = 300) -> bool:
        """Wait for the inference server to be ready"""
        print(f"⏳ Ожидание готовности сервера SmolDocling (максимум {max_wait_time} секунд)...")
        
        start_time = time.time()
        while time.time() - start_time < max_wait_time:
            try:
                # Send a wake-up request to the server
                print("    Отправка запроса для пробуждения сервера...")
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": "Hello, wake up!"}],
                    max_tokens=10,
                    temperature=0.5
                )
                
                if response.choices[0].message.content:
                    print("✅ Сервер готов к работе")
                    return True
            except Exception as e:
                print(f"    Сервер еще не готов... ({str(e)[:50]}...)")
                time.sleep(15)  # Wait 15 seconds before retrying
        
        print("❌ Сервер не стал доступен в течение отведенного времени")
        return False

    def test_connection(self) -> bool:
        try:
            print("🔍 Тестирование подключения к SmolDocling...")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Привет"}],
                max_tokens=10,
                temperature=0.5
            )
            print(f"✅ Подключение успешно! Ответ: {response.choices[0].message.content.strip()}")
            return True
        except Exception as e:
            print(f"❌ Ошибка подключения: {e}")
            return False

    def image_to_base64(self, image_path: Path) -> str:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode('utf-8')

    def pdf_to_all_pages_images_base64(self, pdf_path: Path, output_dir: Path) -> List[str]:
        if not PDF2IMAGE_AVAILABLE:
            raise ImportError("pdf2image not installed")
        
        try:
            # Convert all pages of PDF to PIL images
            pil_images = convert_from_path(str(pdf_path), dpi=200)
            if not pil_images:
                raise ValueError("Не удалось конвертировать PDF в изображения.")
            
            base64_images = []
            for i, img in enumerate(pil_images):
                # Save image to disk
                image_filename = f"{pdf_path.stem}_page_{i+1}.png"
                image_path = output_dir / image_filename
                img.save(image_path, format='PNG')
                print(f"         🖼️  Сохранено изображение страницы {i+1}: {image_path.name}")
                
                # Convert PIL image to base64
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='PNG')
                base64_img = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
                base64_images.append(base64_img)
                
            return base64_images
        except Exception as e:
            print(f"❌ Ошибка конвертации PDF в изображения: {e}")
            raise

    def create_structure_prompt(self) -> str:
        """Создает промпт для извлечения структуры документа через SmolDocling"""
        return """Convert this page to docling with focus on extracting procurement protocol information.
Key fields to extract:
- Procedure number
- Lot number
- Protocol date
- Winner name
- Winner INN/KPP
- Contract price
- Currency
- Procurement subject
- Customer
- Organizer
- Commission members
- Participants list with applications"""

    def create_metadata_prompt(self) -> str:
        """Создает промпт для извлечения метаданных победителей"""
        return """Based on the extracted document structure, please provide the following information in JSON format:
{
  "procedure_number": "номер процедуры закупки",
  "lot_number": "номер лота",
  "protocol_date": "дата протокола",
  "winner": "наименование победителя",
  "inn": "ИНН победителя",
  "kpp": "КПП победителя",
  "price": "цена контракта",
  "currency": "валюта",
  "subject": "предмет закупки",
  "customer": "заказчик",
  "organizer": "организатор",
  "commission": ["член комиссии 1", "член комиссии 2", ...],
  "participants": [
    {
      "application_number": "номер заявки",
      "name": "наименование участника",
      "price_without_vat": "сумма без НДС",
      "price_with_vat": "сумма с НДС",
      "status": "статус"
    }
  ]
}"""

    def process_single_page(self, base64_image: str, prompt_text: str) -> Dict[str, Any]:
        """Process a single page/image with SmolDocling"""
        try:
            messages_content = [
                {"type": "text", "text": prompt_text},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
            ]
            
            print(f"      ➡️  Отправка запроса к SmolDocling...")
            response_start_time = time.time()
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": messages_content}],
                max_tokens=5000,
                temperature=0.0,  # Более детерминированный ответ для извлечения
                response_format={"type": "json_object"}  # Запрашиваем JSON
            )
            response_time = time.time() - response_start_time
            tokens_used = response.usage.total_tokens if response.usage else 0
            
            print(f"      ✅ Ответ получен за {response_time:.2f} секунд")
            print(f"         Длина ответа: {len(response.choices[0].message.content)} символов")
            
            # Parse JSON response
            try:
                output = json.loads(response.choices[0].message.content)
                print(f"      📦 Парсинг JSON...")
                return {
                    "success": True,
                    "data": output,
                    "response_time": response_time,
                    "tokens_used": tokens_used
                }
            except json.JSONDecodeError as e:
                print(f"      ❌ Ошибка парсинга JSON: {e}")
                return {
                    "success": False,
                    "error": f"JSON Decode Error: {e}",
                    "raw_response": response.choices[0].message.content,
                    "response_time": response_time,
                    "tokens_used": tokens_used
                }
                
        except Exception as e:
            print(f"      ❌ Ошибка обработки страницы: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def process_file(self, file_info: Dict[str, Any], file_index: int) -> Optional[Dict[str, Any]]:
        file_path = Path(file_info["path"])
        file_id = file_info["id"]
        description = file_info["description"]
        
        file_output_dir = OUTPUT_DIR / file_id
        file_output_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n{'='*80}")
        print(f"[{file_index+1}/3] Обработка файла: {file_path.name}")
        print(f"ID: {file_id}")
        print(f"Описание: {description}")
        print(f"Путь: {file_path}")
        print(f"{'='*80}")

        file_start_time = time.time()
        file_tokens_used = 0
        
        file_result = {
            "file_id": file_id,
            "file_name": file_path.name,
            "description": description,
            "path": str(file_path),
            "processing_time": 0.0,
            "tokens_used": 0,
            "pages": [],
            "status": "failed",
            "error": None
        }

        try:
            if not file_path.exists():
                raise FileNotFoundError(f"Файл не найден: {file_path}")
            
            print(f"   📄 Обработка PDF: {file_path.name}")
            print(f"      Размер файла: {file_path.stat().st_size / 1024:.1f} KB")
            if not PDF2IMAGE_AVAILABLE:
                raise ImportError("pdf2image not installed")
            
            print(f"      Конвертация всех страниц PDF в изображения...")
            base64_images = self.pdf_to_all_pages_images_base64(file_path, file_output_dir)
            print(f"      Всего страниц: {len(base64_images)}")
            
            # Process each page
            page_results = []
            for i, base64_image in enumerate(base64_images):
                page_num = i + 1
                print(f"      📄 Обработка страницы {page_num} из {len(base64_images)}")
                prompt_text = self.create_structure_prompt()
                page_result = self.process_single_page(base64_image, prompt_text)
                page_results.append(page_result)
                if page_result.get("success"):
                    file_tokens_used += page_result.get("tokens_used", 0)
            
            file_result["tokens_used"] = file_tokens_used
            
            # Save individual page results for reference
            page_results_path = file_output_dir / f"{file_path.stem}_page_results.json"
            with open(page_results_path, "w", encoding="utf-8") as f:
                json.dump(page_results, f, indent=2, ensure_ascii=False)
            print(f"      💾 Результаты по страницам сохранены: {page_results_path}")
            
            # Save raw results
            raw_results_path = file_output_dir / f"{file_path.stem}_raw_results.json"
            with open(raw_results_path, "w", encoding="utf-8") as f:
                json.dump(page_results, f, indent=2, ensure_ascii=False)
            print(f"      💾 Сырые результаты сохранены: {raw_results_path}")
            
            file_result["pages"] = page_results
            file_result["status"] = "success"
            
        except Exception as e:
            print(f"      ❌ Ошибка обработки: {e}")
            file_result["error"] = str(e)
        
        file_result["processing_time"] = time.time() - file_start_time
        self.results.append(file_result)
        
        return file_result

    def generate_markdown_report(self):
        """Generate a markdown report of the results"""
        print(f"\n📄 Генерация отчета...")
        report_path = OUTPUT_DIR / f"smoldocling_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(f"# Отчет о тестировании SmolDocling на 3 PDF файлах\n\n")
            f.write(f"**Дата отчета:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"## Общая статистика\n")
            f.write(f"- Всего файлов: 3\n")
            f.write(f"- Успешно обработано: {sum(1 for r in self.results if r['status'] == 'success')}\n")
            f.write(f"- Общее время обработки: {sum(r['processing_time'] for r in self.results):.2f} секунд\n")
            f.write(f"- Всего токенов использовано: {sum(r['tokens_used'] for r in self.results)}\n\n")

            f.write(f"## Детальный отчет по файлам\n\n")
            for file_result in self.results:
                f.write(f"### Файл: `{file_result['file_name']}`\n")
                f.write(f"- ID: `{file_result['file_id']}`\n")
                f.write(f"- Описание: {file_result['description']}\n")
                f.write(f"- Статус: **{file_result['status'].upper()}**\n")
                f.write(f"- Время обработки: {file_result['processing_time']:.2f} секунд\n")
                f.write(f"- Токенов использовано: {file_result['tokens_used']}\n")
                if file_result['error']:
                    f.write(f"- Ошибка: `{file_result['error']}`\n")
                f.write(f"\n")

                if file_result['status'] == 'success':
                    f.write(f"#### Результаты по страницам\n")
                    for i, page_result in enumerate(file_result['pages']):
                        f.write(f"**Страница {i+1}:** ")
                        if page_result.get('success'):
                            f.write(f"✅ Успешно ({page_result.get('response_time', 0):.2f} сек, {page_result.get('tokens_used', 0)} токенов)\n")
                            # Show sample of extracted data
                            data = page_result.get('data', {})
                            if data:
                                f.write(f"```json\n")
                                # Limit output to first few keys for brevity
                                sample_data = {k: v for k, v in list(data.items())[:3]}
                                f.write(json.dumps(sample_data, ensure_ascii=False, indent=2))
                                f.write(f"\n```\n")
                        else:
                            f.write(f"❌ Ошибка: {page_result.get('error', 'Unknown error')}\n")
                        f.write(f"\n")
                f.write(f"---\n\n")
        
        print(f"✅ Отчет сохранен: {report_path}")

    def run(self):
        print(f"\n{'='*80}")
        print(f"ТЕСТИРОВАНИЕ INTEGRАЦИИ SMOLDOCLING НА 3 PDF ФАЙЛАХ")
        print(f"{'='*80}")

        # Wait for server to be ready
        if not self.wait_for_server_ready():
            print("❌ Сервер не готов к работе. Завершение.")
            return

        if not self.test_connection():
            print("❌ Не удалось подключиться к API. Проверьте конфигурацию и доступность.")
            return

        print(f"📋 Загружено файлов для тестирования: {len(TEST_FILES)}")
        print(f"🎯 Будет обработано: {len(TEST_FILES)} файлов")

        for i, file_info in enumerate(TEST_FILES):
            self.process_file(file_info, i)
        
        self.generate_markdown_report()

        print(f"\n{'='*80}")
        print(f"✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
        print(f"{'='*80}")

if __name__ == "__main__":
    tester = SmolDoclingTester()
    tester.run()

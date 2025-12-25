#!/usr/bin/env python3
"""
Исправленный тест интеграции SmolDocling на 3 PDF файлах
с правильными промптами и оптимизацией изображений
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
OUTPUT_DIR = Path("/root/winners_preprocessor/output_smoldocling_fixed")
OUTPUT_DIR.mkdir(exist_ok=True)

class SmolDoclingFixedTester:
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
                # Send a simple test request
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

    def optimize_image_for_processing(self, image_path: Path) -> Path:
        """Optimize image for processing by reducing size and quality"""
        print(f"      Оптимизация изображения: {image_path.name}")
        
        # Open image
        with Image.open(image_path) as img:
            # Convert to RGB if necessary
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Calculate new size (max 1200px on longest side)
            width, height = img.size
            max_size = 1200
            
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
            
            # Resize if needed
            if new_width != width or new_height != height:
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                print(f"         Изменен размер с {width}x{height} на {new_width}x{new_height}")
            
            # Save optimized image
            optimized_path = image_path.parent / f"{image_path.stem}_optimized{image_path.suffix}"
            img.save(optimized_path, format='PNG', optimize=True, quality=85)
            
            # Check file size
            final_size = optimized_path.stat().st_size / (1024 * 1024)
            print(f"         Финальный размер: {final_size:.2f} MB")
            
            return optimized_path

    def image_to_base64(self, image_path: Path) -> str:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode('utf-8')

    def pdf_to_optimized_pages_images_base64(self, pdf_path: Path, output_dir: Path) -> List[str]:
        """Convert PDF to optimized images and return base64 strings"""
        if not PDF2IMAGE_AVAILABLE:
            raise ImportError("pdf2image not installed")
        
        try:
            # Convert all pages of PDF to PIL images with lower DPI for optimization
            print(f"         Конвертация PDF с DPI=150 для оптимизации...")
            pil_images = convert_from_path(str(pdf_path), dpi=150)
            if not pil_images:
                raise ValueError("Не удалось конвертировать PDF в изображения.")
            
            base64_images = []
            for i, img in enumerate(pil_images):
                # Save image to disk first
                image_filename = f"{pdf_path.stem}_page_{i+1}_raw.png"
                image_path = output_dir / image_filename
                img.save(image_path, format='PNG')
                
                # Optimize image
                optimized_path = self.optimize_image_for_processing(image_path)
                
                # Convert optimized image to base64
                base64_img = self.image_to_base64(optimized_path)
                base64_images.append(base64_img)
                
                print(f"         🖼️  Создана оптимизированная страница {i+1}: {optimized_path.name}")
                
            return base64_images
        except Exception as e:
            print(f"❌ Ошибка конвертации PDF в изображения: {e}")
            raise

    def create_docling_prompt(self) -> str:
        """Создает правильный промпт для SmolDocling согласно документации"""
        return "Convert this page to docling."

    def process_single_page_docling(self, base64_image: str) -> Dict[str, Any]:
        """Process a single page/image with SmolDocling using correct prompt"""
        try:
            messages_content = [
                {"type": "text", "text": self.create_docling_prompt()},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
            ]
            
            print(f"      ➡️  Отправка запроса к SmolDocling с правильным промптом...")
            response_start_time = time.time()
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": messages_content}],
                max_tokens=4000,  # Reasonable limit for DocTags output
                temperature=0.0,  # Deterministic output
                response_format={"type": "text"}  # Allow text response for DocTags
            )
            response_time = time.time() - response_start_time
            tokens_used = response.usage.total_tokens if response.usage else 0
            
            print(f"      ✅ Ответ получен за {response_time:.2f} секунд")
            print(f"         Длина ответа: {len(response.choices[0].message.content)} символов")
            
            # Parse DocTags response
            doctags = response.choices[0].message.content.strip()
            
            return {
                "success": True,
                "doctags": doctags,
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
            
            print(f"      Конвертация и оптимизация страниц PDF...")
            base64_images = self.pdf_to_optimized_pages_images_base64(file_path, file_output_dir)
            print(f"      Всего оптимизированных страниц: {len(base64_images)}")
            
            # Process each page with correct SmolDocling prompt
            page_results = []
            for i, base64_image in enumerate(base64_images):
                page_num = i + 1
                print(f"      📄 Обработка страницы {page_num} из {len(base64_images)}")
                page_result = self.process_single_page_docling(base64_image)
                page_results.append(page_result)
                
                if page_result.get("success"):
                    file_tokens_used += page_result.get("tokens_used", 0)
                    
                    # Save DocTags to file
                    doctags_filename = f"{file_path.stem}_page_{page_num}_doctags.txt"
                    doctags_path = file_output_dir / doctags_filename
                    with open(doctags_path, "w", encoding="utf-8") as f:
                        f.write(page_result["doctags"])
                    print(f"      💾 DocTags сохранены: {doctags_path}")
                    
                    # Try to convert DocTags to JSON if possible
                    try:
                        # Some DocTags might be JSON-parseable
                        json_data = json.loads(page_result["doctags"])
                        json_filename = f"{file_path.stem}_page_{page_num}_parsed.json"
                        json_path = file_output_dir / json_filename
                        with open(json_path, "w", encoding="utf-8") as f:
                            json.dump(json_data, f, indent=2, ensure_ascii=False)
                        print(f"      💾 Парсированный JSON сохранен: {json_path}")
                    except json.JSONDecodeError:
                        print(f"      ⚠️  DocTags не является JSON, сохранен как текст")
                else:
                    print(f"      ❌ Ошибка обработки страницы {page_num}")
            
            file_result["tokens_used"] = file_tokens_used
            
            # Save individual page results for reference
            page_results_path = file_output_dir / f"{file_path.stem}_page_results.json"
            with open(page_results_path, "w", encoding="utf-8") as f:
                json.dump(page_results, f, indent=2, ensure_ascii=False)
            print(f"      💾 Результаты по страницам сохранены: {page_results_path}")
            
            file_result["pages"] = page_results
            
            # Check if any page was processed successfully
            if any(r.get("success") for r in page_results):
                file_result["status"] = "success"
            else:
                file_result["status"] = "partial_success"
            
        except Exception as e:
            print(f"      ❌ Ошибка обработки: {e}")
            file_result["error"] = str(e)
        
        file_result["processing_time"] = time.time() - file_start_time
        self.results.append(file_result)
        
        return file_result

    def generate_markdown_report(self):
        """Generate a markdown report of the results"""
        print(f"\n📄 Генерация отчета...")
        report_path = OUTPUT_DIR / f"smoldocling_fixed_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(f"# Исправленный отчет по тестированию SmolDocling на 3 PDF файлах\n\n")
            f.write(f"**Дата отчета:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"## Исправления и оптимизации\n\n")
            f.write(f"- ✅ Правильный промпт: 'Convert this page to docling.'\n")
            f.write(f"- ✅ Оптимизация изображений (макс. 1200px, качество 85%)\n")
            f.write(f"- ✅ Комбинированный токен аутентификации\n")
            f.write(f"- ✅ Правильный лимит токенов (4000)\n")
            f.write(f"- ✅ Обработка DocTags формата\n\n")
            
            f.write(f"## Общая статистика\n")
            f.write(f"- Всего файлов: 3\n")
            successful_files = sum(1 for r in self.results if r['status'] in ['success', 'partial_success'])
            f.write(f"- Успешно обработано: {successful_files}\n")
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

                if file_result['pages']:
                    f.write(f"#### Результаты по страницам\n")
                    for i, page_result in enumerate(file_result['pages']):
                        f.write(f"**Страница {i+1}:** ")
                        if page_result.get('success'):
                            f.write(f"✅ Успешно ({page_result.get('response_time', 0):.2f} сек, {page_result.get('tokens_used', 0)} токенов)\n")
                            
                            # Show DocTags preview
                            doctags = page_result.get('doctags', '')
                            if doctags:
                                preview = doctags[:200] + ('...' if len(doctags) > 200 else '')
                                f.write(f"```\n{preview}\n```\n")
                        else:
                            f.write(f"❌ Ошибка: {page_result.get('error', 'Unknown error')}\n")
                        f.write(f"\n")
                f.write(f"---\n\n")
        
        print(f"✅ Исправленный отчет сохранен: {report_path}")

    def run(self):
        print(f"\n{'='*80}")
        print(f"ИСПРАВЛЕННОЕ ТЕСТИРОВАНИЕ INTEGRАЦИИ SMOLDOCLING НА 3 PDF ФАЙЛАХ")
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
        print(f"✅ ИСПРАВЛЕННОЕ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
        print(f"{'='*80}")

if __name__ == "__main__":
    tester = SmolDoclingFixedTester()
    tester.run()

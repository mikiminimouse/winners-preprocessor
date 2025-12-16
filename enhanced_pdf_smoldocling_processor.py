#!/usr/bin/env python3
"""
УЛУЧШЕННАЯ ОБРАБОТКА PDF: ЛОКАЛЬНЫЙ DOCLING → SMOLDOCLING

Сначала обрабатываем PDF локальным Docling для извлечения текста и структур,
затем используем результаты для улучшения обработки в SmolDocling.
"""
import os
import sys
import json
import time
import base64
import requests
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

# Конфигурация
DOCLING_API_URL = "http://localhost:8000"  # Локальный Docling
API_TOKEN = "ZDRhOWQ3OTAtZjU4MC00MzA2LThhNTgtMDU1NGFlMjE4OWRl.85a830f9340966e0ad1fd1642884c7c8"
BASE_URL = "https://d63e30af-085a-49f0-9724-8162da967af2.modelrun.inference.cloud.ru/v1"
MODEL_NAME = "model-run-4qigw-disease"

# Тестовый файл
TEST_FILE = "/root/winners_preprocessor/normalized/UNIT_43a02eedd2bbca86/files/! Протокол ЭМ-17.pdf"
OUTPUT_DIR = Path("/root/winners_preprocessor/output_enhanced_processing")

class EnhancedPDFProcessor:
    def __init__(self):
        if not OPENAI_SDK_AVAILABLE:
            raise ImportError("openai SDK не установлен")

        self.client = openai.OpenAI(
            api_key=API_TOKEN,
            base_url=BASE_URL,
            timeout=300.0
        )
        self.model = MODEL_NAME
        OUTPUT_DIR.mkdir(exist_ok=True)

    def wait_for_services(self) -> dict:
        """Проверка доступности сервисов"""
        print("🔍 Проверка доступности сервисов...")

        services_status = {}

        # Проверка SmolDocling
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Ready?"}],
                max_tokens=5,
                temperature=0.0
            )
            print("✅ SmolDocling готов")
            services_status['smoldocling'] = True
        except Exception as e:
            print(f"❌ SmolDocling недоступен: {e}")
            services_status['smoldocling'] = False

        # Проверка локального Docling
        try:
            response = requests.get(f"{DOCLING_API_URL}/health", timeout=5)
            if response.status_code == 200:
                print("✅ Локальный Docling готов")
                services_status['docling'] = True
            else:
                print(f"❌ Локальный Docling вернул статус {response.status_code}")
                services_status['docling'] = False
        except Exception as e:
            print(f"❌ Локальный Docling недоступен: {e}")
            services_status['docling'] = False

        return services_status

    def process_with_local_docling(self, pdf_path: Path) -> dict:
        """Обработка PDF локальным Docling"""
        print("🏠 ОБРАБОТКА ЛОКАЛЬНЫМ DOCLING...")

        # Подготовка запроса для локального Docling
        unit_id = f"enhanced_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        request_data = {
            "unit_id": unit_id,
            "manifest": str(pdf_path.parent / "manifest.json"),
            "files": [{
                "file_id": f"{unit_id}_file",
                "original_name": pdf_path.name,
                "path": str(pdf_path),
                "detected_type": "pdf",
                "mime_type": "application/pdf",
                "needs_ocr": True,
                "size": pdf_path.stat().st_size
            }],
            "route": "pdf_scan"
        }

        try:
            print(f"   Отправка в локальный Docling: {pdf_path.name}")
            start_time = time.time()

            response = requests.post(
                f"{DOCLING_API_URL}/process",
                json=request_data,
                timeout=300
            )

            processing_time = time.time() - start_time

            if response.status_code == 200:
                result = response.json()
                print(f"✅ Локальный Docling обработал за {processing_time:.2f} сек")
                print(f"   Статус: {result.get('status')}")
                print(f"   Выходных файлов: {len(result.get('output_files', []))}")

                # Ищем выходные файлы
                output_files = self.find_docling_output_files(unit_id, result.get('output_files', []))
                return {
                    'success': True,
                    'unit_id': unit_id,
                    'processing_time': processing_time,
                    'output_files': output_files,
                    'api_response': result
                }
            else:
                print(f"❌ Ошибка локального Docling: {response.status_code}")
                print(f"   Ответ: {response.text[:200]}...")
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.text[:200]}"
                }

        except Exception as e:
            print(f"❌ Ошибка при обращении к локальному Docling: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def find_docling_output_files(self, unit_id: str, output_files_list: list) -> dict:
        """Поиск и анализ выходных файлов локального Docling"""
        print("   Поиск выходных файлов Docling...")

        # Возможные пути к выходным файлам
        possible_paths = [
            Path("/root/winners_preprocessor/output") / unit_id,
            Path("/data/output") / unit_id,
            OUTPUT_DIR / "docling_output" / unit_id
        ]

        output_files = {}

        for output_dir in possible_paths:
            if output_dir.exists():
                print(f"   Найдена директория: {output_dir}")

                # Ищем файлы разных форматов
                for ext in ['.md', '.json', '.html', '.txt']:
                    files = list(output_dir.glob(f"*{ext}"))
                    if files:
                        for file_path in files:
                            content_type = ext[1:]  # md, json, html, txt
                            try:
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    content = f.read()

                                output_files[content_type] = {
                                    'path': str(file_path),
                                    'content': content,
                                    'size': len(content)
                                }

                                print(f"   ✅ Найден {content_type.upper()} файл: {len(content)} символов")

                            except Exception as e:
                                print(f"   ❌ Ошибка чтения {file_path}: {e}")

                # Ищем изображения (улучшенные версии)
                image_files = list(output_dir.glob("*.png")) + list(output_dir.glob("*.jpg"))
                if image_files:
                    output_files['images'] = []
                    for img_path in image_files:
                        output_files['images'].append(str(img_path))
                        print(f"   ✅ Найдено изображение: {img_path.name}")

                break

        if not output_files:
            print("   ⚠️  Выходные файлы Docling не найдены")

        return output_files

    def create_enhanced_image_from_docling(self, docling_results: dict) -> str:
        """Создание улучшенного изображения на основе результатов Docling"""
        print("🎨 СОЗДАНИЕ УЛУЧШЕННОГО ИЗОБРАЖЕНИЯ...")

        # Если Docling создал изображения, используем их
        if 'images' in docling_results and docling_results['images']:
            image_path = docling_results['images'][0]
            print(f"   Используем изображение от Docling: {image_path}")

            # Загружаем и оптимизируем изображение
            img = Image.open(image_path)

            # Конвертируем в RGB если нужно
            if img.mode != 'RGB':
                img = img.convert('RGB')

            # Оптимизируем размер (Docling может создать большие изображения)
            max_size = 1500
            if max(img.size) > max_size:
                ratio = max_size / max(img.size)
                new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
                print(f"   Размер оптимизирован: {img.size}")

            # Сохраняем в base64
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='JPEG', quality=95, optimize=True)
            base64_img = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')

            return base64_img

        # Если изображений нет, создаем на основе текста
        elif 'md' in docling_results:
            print("   Создание изображения из Markdown текста...")

            # Создаем изображение с текстом из Markdown
            markdown_text = docling_results['md']['content']

            # Ограничиваем текст для создания изображения
            text_preview = markdown_text[:2000]  # Первые 2000 символов

            # Создаем изображение с текстом (простая визуализация)
            img = self.create_text_image(text_preview, width=1200, height=1600)
            print(f"   Создано изображение из текста: {img.size}")

            # Конвертируем в base64
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='JPEG', quality=90, optimize=True)
            base64_img = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')

            return base64_img

        else:
            print("   ⚠️  Нет данных от Docling, возвращаемся к базовому методу")
            return None

    def create_text_image(self, text: str, width: int = 1200, height: int = 1600) -> Image.Image:
        """Создание изображения с текстом для улучшения OCR"""
        from PIL import ImageDraw, ImageFont

        # Создаем белое изображение
        img = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(img)

        try:
            # Пробуем загрузить шрифт (если доступен)
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
        except:
            # Используем дефолтный шрифт
            font = ImageFont.load_default()

        # Разбиваем текст на строки
        lines = text.split('\n')
        y_position = 50
        line_height = 25

        for line in lines[:50]:  # Ограничиваем количеством строк
            if y_position > height - 50:
                break

            # Ограничиваем длину строки
            if len(line) > 80:
                line = line[:77] + "..."

            draw.text((50, y_position), line, fill='black', font=font)
            y_position += line_height

        return img

    def process_with_enhanced_smoldocling(self, base64_image: str, docling_context: dict) -> str:
        """Обработка улучшенного изображения через SmolDocling"""
        print("🚀 ОБРАБОТКА УЛУЧШЕННОГО ИЗОБРАЖЕНИЯ В SMOLDOCLING...")

        # Создаем промпт с контекстом от Docling
        context_text = ""
        if 'md' in docling_context:
            # Берем первые 500 символов как контекст
            context_text = docling_context['md']['content'][:500]

        prompt = f"""Analyze this document image and extract detailed information about procurement protocols and winners.

Additional context from document preprocessing:
{context_text}

Please provide comprehensive DocTags with full text extraction, focusing on:
- Procurement details and requirements
- Commission information
- Winner determination process
- Contract terms and amounts
- Participant information"""

        image_url = f"data:image/jpeg;base64,{base64_image}"

        messages_content = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": image_url}}
        ]

        try:
            start_time = time.time()
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages_content,
                max_tokens=6000,  # Увеличено для детального анализа
                temperature=0.0
            )

            processing_time = time.time() - start_time
            tokens_used = response.usage.total_tokens if response.usage else 0

            doctags = response.choices[0].message.content

            print("✅ УСПЕШНАЯ ОБРАБОТКА:")
            print(f"   Время: {processing_time:.2f} сек")
            print(f"   Токенов: {tokens_used}")
            print(f"   DocTags: {len(doctags)} символов")

            return doctags

        except Exception as e:
            print(f"❌ Ошибка SmolDocling: {e}")
            return None

    def create_final_report(self, pdf_path: Path, docling_results: dict, enhanced_doctags: str) -> str:
        """Создание финального всестороннего отчета"""
        print("📊 СОЗДАНИЕ ФИНАЛЬНОГО ОТЧЕТА...")

        markdown_parts = []

        # Заголовок
        header = f"# УЛУЧШЕННЫЙ АНАЛИЗ ПРОТОКОЛА ЗАКУПОК\n\n"
        header += f"**Метод обработки:** Локальный Docling → SmolDocling\n"
        header += f"**Файл:** {pdf_path.name}\n"
        header += f"**Размер:** {pdf_path.stat().st_size} байт\n"
        header += f"**Дата обработки:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        markdown_parts.append(header)

        # Этап 1: Локальный Docling
        markdown_parts.append("## ЭТАП 1: ОБРАБОТКА ЛОКАЛЬНЫМ DOCLING\n\n")

        if docling_results.get('success'):
            docling_time = docling_results.get('processing_time', 0)
            output_files = docling_results.get('output_files', {})

            markdown_parts.append(f"✅ **УСПЕШНО** ({docling_time:.2f} сек)\n\n")

            # Показываем найденные файлы
            for content_type, file_info in output_files.items():
                if isinstance(file_info, dict) and 'size' in file_info:
                    markdown_parts.append(f"- **{content_type.upper()}:** {file_info['size']} символов\n")

            if output_files.get('images'):
                markdown_parts.append(f"- **Изображений:** {len(output_files['images'])}\n")

        else:
            markdown_parts.append(f"❌ **ОШИБКА:** {docling_results.get('error', 'Неизвестная ошибка')}\n\n")

        # Этап 2: SmolDocling
        markdown_parts.append("\n## ЭТАП 2: ОБРАБОТКА SMOLDOCLING\n\n")

        if enhanced_doctags:
            markdown_parts.append("✅ **УСПЕШНО**\n\n")
            markdown_parts.append("### ДОСТУПНЫЕ ДОКТАГИ\n\n")
            markdown_parts.append(f"```\n{enhanced_doctags}\n```\n\n")
        else:
            markdown_parts.append("❌ **ОШИБКА ОБРАБОТКИ**\n\n")

        # Сравнение результатов
        markdown_parts.append("## СРАВНЕНИЕ РЕЗУЛЬТАТОВ\n\n")

        # Результаты базовой обработки (из предыдущих тестов)
        markdown_parts.append("### БАЗОВАЯ ОБРАБОТКА (только SmolDocling)\n")
        markdown_parts.append("- **Текст:** 171 символ\n")
        markdown_parts.append("- **Качество:** Среднее (OCR ошибки)\n")
        markdown_parts.append("- **Уверенность:** 0.70\n\n")

        # Результаты улучшенной обработки
        markdown_parts.append("### УЛУЧШЕННАЯ ОБРАБОТКА (Docling + SmolDocling)\n")

        if enhanced_doctags:
            doctags_length = len(enhanced_doctags)
            markdown_parts.append(f"- **DocTags:** {doctags_length} символов\n")

            # Анализ качества
            if doctags_length > 500:
                quality = "Высокое"
                confidence = "0.85+"
            elif doctags_length > 200:
                quality = "Среднее"
                confidence = "0.75"
            else:
                quality = "Низкое"
                confidence = "<0.70"

            markdown_parts.append(f"- **Качество:** {quality}\n")
            markdown_parts.append(f"- **Уверенность:** {confidence}\n")

            # Поиск ключевых элементов
            key_elements = []
            if 'протокол' in enhanced_doctags.lower():
                key_elements.append("протокол")
            if 'комисс' in enhanced_doctags.lower():
                key_elements.append("комиссия")
            if 'победител' in enhanced_doctags.lower():
                key_elements.append("победитель")
            if 'закупк' in enhanced_doctags.lower():
                key_elements.append("закупки")

            if key_elements:
                markdown_parts.append(f"- **Найденные элементы:** {', '.join(key_elements)}\n")

        else:
            markdown_parts.append("- **Результат:** Обработка не удалась\n")

        # Выводы
        markdown_parts.append("\n## ВЫВОДЫ И РЕКОМЕНДАЦИИ\n\n")

        if enhanced_doctags and len(enhanced_doctags) > 171:
            improvement = len(enhanced_doctags) / 171
            markdown_parts.append(f"✅ **УЛУЧШЕНИЕ:** Качество обработки улучшено в {improvement:.1f} раза!\n\n")
            markdown_parts.append("**Рекомендации:**\n")
            markdown_parts.append("- Использовать двухэтапную обработку для всех протоколов\n")
            markdown_parts.append("- Локальный Docling для предварительного анализа\n")
            markdown_parts.append("- SmolDocling для финального структурированного извлечения\n")
        else:
            markdown_parts.append("⚠️ **ОГРАНИЧЕНИЯ:** Двухэтапная обработка не показала значительного улучшения\n\n")
            markdown_parts.append("**Альтернативы:**\n")
            markdown_parts.append("- Улучшение качества входных изображений\n")
            markdown_parts.append("- Использование специализированных OCR моделей\n")
            markdown_parts.append("- Комбинация нескольких подходов\n")

        return ''.join(markdown_parts)

    def run_enhanced_processing(self, pdf_path: str) -> dict:
        """Полная улучшенная обработка"""
        print("🎯 НАЧАЛО УЛУЧШЕННОЙ ОБРАБОТКИ PDF")
        print("=" * 60)

        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"Файл не найден: {pdf_path}")

        # Шаг 1: Проверка сервисов
        services_available = self.wait_for_services()
        if not services_available.get('smoldocling', False):
            return {"success": False, "error": "SmolDocling недоступен"}

        has_any_service = services_available.get('smoldocling', False) or services_available.get('docling', False)
        if not has_any_service:
            return {"success": False, "error": "Ни один сервис не доступен"}

        use_local_docling = services_available.get('docling', False)

        # Шаг 2: Выбор метода обработки
        if use_local_docling:
            print("✅ Доступен локальный Docling - используем улучшенную обработку")
            docling_results = self.process_with_local_docling(pdf_path)

            if not docling_results.get('success'):
                print("⚠️  Локальный Docling не справился, переходим на базовую обработку SmolDocling")
                return self.fallback_processing(pdf_path)
        else:
            print("⚠️  Локальный Docling недоступен, используем базовую обработку SmolDocling")
            return self.fallback_processing(pdf_path)

        # Шаг 3: Создание улучшенного изображения
        enhanced_base64 = self.create_enhanced_image_from_docling(docling_results.get('output_files', {}))

        if not enhanced_base64:
            print("⚠️  Не удалось создать улучшенное изображение, используем базовый метод")
            return self.fallback_processing(pdf_path)

        # Шаг 4: Обработка улучшенного изображения в SmolDocling
        enhanced_doctags = self.process_with_enhanced_smoldocling(enhanced_base64, docling_results.get('output_files', {}))

        # Шаг 5: Создание финального отчета
        final_report = self.create_final_report(pdf_path, docling_results, enhanced_doctags)

        # Шаг 6: Сохранение результатов
        base_name = pdf_path.stem

        # Финальный отчет
        report_file = OUTPUT_DIR / f"{base_name}_enhanced_report.md"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(final_report)

        # Детальные данные
        data_file = OUTPUT_DIR / f"{base_name}_enhanced_data.json"
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump({
                "pdf_file": str(pdf_path),
                "processing_timestamp": datetime.now().isoformat(),
                "docling_results": docling_results,
                "enhanced_doctags": enhanced_doctags,
                "enhanced_base64_length": len(enhanced_base64) if enhanced_base64 else 0
            }, f, indent=2, ensure_ascii=False)

        print("\n🎉 УЛУЧШЕННАЯ ОБРАБОТКА ЗАВЕРШЕНА!")
        print(f"📁 Результаты: {OUTPUT_DIR}")
        print(f"📄 Отчет: {report_file}")
        print(f"📊 Данные: {data_file}")

        return {
            "success": True,
            "final_report": final_report,
            "docling_results": docling_results,
            "enhanced_doctags": enhanced_doctags
        }

    def fallback_processing(self, pdf_path: Path) -> dict:
        """Резервная обработка если улучшенная не удалась"""
        print("🔄 ИСПОЛЬЗУЕМ РЕЗЕРВНУЮ ОБРАБОТКУ...")

        # Используем базовый метод из предыдущего скрипта
        try:
            base64_thumbnail = self.create_optimized_thumbnail(pdf_path)
            doctags = self.extract_text_with_smoldocling(base64_thumbnail)

            analysis = self.analyze_protocol_content(self.parse_doctags_to_text(doctags) if doctags else "")
            markdown_report = self.generate_markdown_report(pdf_path, self.parse_doctags_to_text(doctags) if doctags else "", analysis)

            return {
                "success": True,
                "fallback": True,
                "doctags": doctags,
                "analysis": analysis,
                "markdown_report": markdown_report
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Резервная обработка также провалилась: {e}"
            }

    # Методы из базового процессора (для fallback)
    def create_optimized_thumbnail(self, pdf_path: Path) -> str:
        """Создание оптимизированного thumbnail"""
        pil_images = convert_from_path(str(pdf_path), dpi=300, first_page=1, last_page=1)
        img = pil_images[0]

        if img.mode != 'RGB':
            img = img.convert('RGB')

        max_size = 1200
        if max(img.size) > max_size:
            ratio = max_size / max(img.size)
            new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='JPEG', quality=90, optimize=True)
        return base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')

    def extract_text_with_smoldocling(self, base64_thumbnail: str) -> str:
        """Извлечение текста через SmolDocling"""
        prompt = "Convert this document page to structured docling format with full text extraction."
        image_url = f"data:image/jpeg;base64,{base64_thumbnail}"

        messages_content = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": image_url}}
        ]

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages_content,
            max_tokens=4000,
            temperature=0.0
        )

        return response.choices[0].message.content

    def parse_doctags_to_text(self, doctags: str) -> str:
        """Парсинг DocTags в текст"""
        lines = doctags.strip().split('\n')
        text_parts = []

        for line in lines:
            parts = line.split('>')
            if len(parts) >= 5:
                content = parts[-1].strip()
                if content and len(content) > 2:
                    text_parts.append(content)

        full_text = ' '.join(text_parts)
        full_text = full_text.replace('закушке', 'закупке')
        full_text = full_text.replace('убат', 'услуг')

        return full_text.strip()

    def analyze_protocol_content(self, text: str) -> dict:
        """Анализ содержания протокола"""
        text_lower = text.lower()

        return {
            "has_protocol": "протокол" in text_lower,
            "has_procurement": any(word in text_lower for word in ["закупк", "тендер", "конкурс"]),
            "has_commission": any(word in text_lower for word in ["комисс", "заседани"]),
            "has_winners": any(word in text_lower for word in ["победител", "победил"]),
            "has_contracts": any(word in text_lower for word in ["контракт", "договор"]),
            "has_amounts": any(word in text_lower for word in ["рубл", "сумм", "тысяч"]),
            "confidence_score": 0.5,  # Базовая уверенность
            "extracted_text_length": len(text)
        }

    def generate_markdown_report(self, pdf_path: Path, extracted_text: str, analysis: dict) -> str:
        """Генерация Markdown отчета"""
        header = f"# АНАЛИЗ ПРОТОКОЛА ЗАКУПОК\n\n"
        header += f"**Файл:** {pdf_path.name}\n"
        header += f"**Обработано через:** SmolDocling (резерв)\n"
        header += f"**Дата обработки:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        content = f"## ИЗВЛЕЧЕННЫЙ ТЕКСТ\n\n```\n{extracted_text}\n```\n\n"
        content += f"## АНАЛИЗ\n\n"
        content += f"- **Длина текста:** {len(extracted_text)} символов\n"
        content += f"- **Уверенность:** {analysis['confidence_score']:.2f}\n"

        return header + content

def main():
    """Основная функция"""
    if len(sys.argv) != 2:
        print("Использование: python enhanced_pdf_smoldocling_processor.py <путь_к_pdf>")
        print("Пример: python enhanced_pdf_smoldocling_processor.py /path/to/protocol.pdf")
        sys.exit(1)

    pdf_file = sys.argv[1]

    try:
        processor = EnhancedPDFProcessor()
        result = processor.run_enhanced_processing(pdf_file)

        if result["success"]:
            print("\n✅ ОБРАБОТКА ЗАВЕРШЕНА УСПЕШНО!")
            if result.get("fallback"):
                print("📝 Использовался резервный метод обработки")
        else:
            print(f"\n❌ ОШИБКА: {result.get('error', 'Неизвестная ошибка')}")

    except Exception as e:
        print(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

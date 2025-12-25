#!/usr/bin/env python3
"""
ПРОДАКШЕН РЕШЕНИЕ: ОБРАБОТКА PDF ПРОТОКОЛОВ ЧЕРЕЗ SMOLDOCLING

Использует оптимальные параметры для максимального извлечения текста и анализа победителей.
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

class SmolDoclingPDFProcessor:
    def __init__(self, output_dir: str = "/root/winners_preprocessor/output_smoldocling_production"):
        if not OPENAI_SDK_AVAILABLE:
            raise ImportError("openai SDK не установлен")

        self.client = openai.OpenAI(
            api_key=API_TOKEN,
            base_url=BASE_URL,
            timeout=120.0
        )
        self.model = MODEL_NAME
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def wait_for_server_ready(self, max_wait_time: int = 60) -> bool:
        """Ожидание готовности сервера"""
        print("⏳ Проверка готовности SmolDocling сервера...")

        start_time = time.time()
        while time.time() - start_time < max_wait_time:
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": "Ready?"}],
                    max_tokens=5,
                    temperature=0.0
                )
                if response.choices[0].message.content:
                    print("✅ Сервер готов к работе")
                    return True
            except Exception as e:
                print(f"    Ожидание... ({str(e)[:40]}...)")
                time.sleep(3)

        print("❌ Сервер не доступен")
        return False

    def create_optimized_thumbnail(self, pdf_path: Path) -> str:
        """Создание оптимизированного thumbnail с лучшими параметрами"""
        print(f"📷 Создание HQ thumbnail: {pdf_path.name}")

        # Оптимальные параметры на основе тестирования
        pil_images = convert_from_path(str(pdf_path), dpi=300, first_page=1, last_page=1)
        img = pil_images[0]

        if img.mode != 'RGB':
            img = img.convert('RGB')

        # Оптимизация размера для баланса качества/производительности
        max_size = 1200  # Немного уменьшено для стабильности
        if max(img.size) > max_size:
            ratio = max_size / max(img.size)
            new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        print(f"   Размер: {img.size}, качество: 90%")

        # Конвертация в base64
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='JPEG', quality=90, optimize=True)
        base64_img = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')

        return base64_img

    def extract_text_with_smoldocling(self, base64_thumbnail: str) -> str:
        """Извлечение текста через SmolDocling с оптимальным промптом"""
        print("🧠 Извлечение текста через SmolDocling...")

        # Оптимальный промпт на основе тестирования
        prompt = "Convert this document page to structured docling format with full text extraction."

        image_url = f"data:image/jpeg;base64,{base64_thumbnail}"

        messages_content = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": image_url}}
        ]

        start_time = time.time()
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": messages_content}],
            max_tokens=4000,  # Оптимальное значение
            temperature=0.0
        )

        processing_time = time.time() - start_time
        tokens_used = response.usage.total_tokens if response.usage else 0

        print(f"   ✅ Обработано за {processing_time:.2f} сек, токенов: {tokens_used}")

        return response.choices[0].message.content

    def parse_doctags_to_text(self, doctags: str) -> str:
        """Парсинг DocTags в читаемый текст"""
        print("📝 Парсинг DocTags...")

        lines = doctags.strip().split('\n')
        text_parts = []

        for line in lines:
            if not line.strip():
                continue

            parts = line.split('>')
            if len(parts) >= 5:
                content = parts[-1].strip()
                if content and len(content) > 2:  # Минимум 3 символа
                    text_parts.append(content)

        # Объединение и очистка
        full_text = ' '.join(text_parts)
        # Исправление распространенных OCR ошибок
        full_text = full_text.replace('закушке', 'закупке')
        full_text = full_text.replace('убат', 'услуг')
        full_text = full_text.replace('товар,', 'товаров,')

        return full_text.strip()

    def analyze_protocol_content(self, text: str) -> dict:
        """Анализ содержания протокола для выявления информации о закупках"""
        print("🔍 Анализ содержания протокола...")

        text_lower = text.lower()

        analysis = {
            "document_type": "protocol" if "протокол" in text_lower else "unknown",
            "has_procurement": any(word in text_lower for word in ["закупк", "тендер", "конкурс", "предложен"]),
            "has_commission": any(word in text_lower for word in ["комисс", "заседани", "член"]),
            "has_winners": any(word in text_lower for word in ["победител", "победил", "выиграл"]),
            "has_contracts": any(word in text_lower for word in ["контракт", "договор", "сделк"]),
            "has_amounts": any(word in text_lower for word in ["рубл", "сумм", "тысяч", "миллион"]),
            "confidence_score": 0.0,
            "extracted_participants": [],
            "extracted_amounts": [],
            "protocol_number": None
        }

        # Расчет уверенности
        confidence = 0.0
        if analysis["has_procurement"]: confidence += 0.3
        if analysis["has_commission"]: confidence += 0.2
        if analysis["has_winners"]: confidence += 0.2
        if analysis["has_contracts"]: confidence += 0.1
        if len(text) > 50: confidence += 0.2
        if "протокол" in text_lower: confidence += 0.3

        analysis["confidence_score"] = min(confidence, 1.0)

        # Попытка извлечь номер протокола
        import re
        protocol_match = re.search(r'протокол[а-я\s]*(\d+[\-\.]?\d*)', text_lower)
        if protocol_match:
            analysis["protocol_number"] = protocol_match.group(1)

        return analysis

    def generate_markdown_report(self, pdf_path: Path, extracted_text: str, analysis: dict) -> str:
        """Генерация подробного Markdown отчета"""
        print("📄 Генерация Markdown отчета...")

        markdown_parts = []

        # Заголовок
        header = f"# АНАЛИЗ ПРОТОКОЛА ЗАКУПОК\n\n"
        header += f"**Файл:** {pdf_path.name}\n"
        header += f"**Обработано через:** SmolDocling (Cloud.ru)\n"
        header += f"**Дата обработки:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        header += f"**Размер файла:** {pdf_path.stat().st_size} байт\n\n"
        markdown_parts.append(header)

        # Результаты анализа
        markdown_parts.append("## РЕЗУЛЬТАТЫ АНАЛИЗА\n\n")
        markdown_parts.append(f"- **Тип документа:** {analysis['document_type'].title()}\n")
        markdown_parts.append(f"- **Содержит закупки:** {'✅ Да' if analysis['has_procurement'] else '❌ Нет'}\n")
        markdown_parts.append(f"- **Имеет комиссию:** {'✅ Да' if analysis['has_commission'] else '❌ Нет'}\n")
        markdown_parts.append(f"- **Содержит победителей:** {'✅ Да' if analysis['has_winners'] else '❌ Нет'}\n")
        markdown_parts.append(f"- **Имеет контракты:** {'✅ Да' if analysis['has_contracts'] else '❌ Нет'}\n")
        markdown_parts.append(f"- **Содержит суммы:** {'✅ Да' if analysis['has_amounts'] else '❌ Нет'}\n")
        markdown_parts.append(f"- **Уровень уверенности:** {analysis['confidence_score']:.2f}\n")

        if analysis['protocol_number']:
            markdown_parts.append(f"- **Номер протокола:** {analysis['protocol_number']}\n")

        markdown_parts.append("\n")

        # Извлеченный текст
        markdown_parts.append("## ИЗВЛЕЧЕННЫЙ ТЕКСТ\n\n")
        if extracted_text:
            markdown_parts.append(f"```\n{extracted_text}\n```\n\n")
        else:
            markdown_parts.append("*Текст не удалось извлечь*\n\n")

        # Метрики обработки
        markdown_parts.append("## МЕТРИКИ ОБРАБОТКИ\n\n")
        markdown_parts.append(f"- **Длина извлеченного текста:** {len(extracted_text)} символов\n")
        markdown_parts.append(f"- **Обнаружено ключевых слов:** {sum(analysis[key] for key in ['has_procurement', 'has_commission', 'has_winners', 'has_contracts', 'has_amounts'])}\n")

        # Рекомендации
        markdown_parts.append("## РЕКОМЕНДАЦИИ\n\n")
        if analysis['confidence_score'] > 0.7:
            markdown_parts.append("✅ **Высокая уверенность распознавания** - документ успешно обработан\n")
        elif analysis['confidence_score'] > 0.4:
            markdown_parts.append("⚠️ **Средняя уверенность** - рекомендуется дополнительная проверка\n")
        else:
            markdown_parts.append("❌ **Низкая уверенность** - требуется альтернативный метод обработки\n")

        if analysis['has_procurement'] and analysis['has_winners']:
            markdown_parts.append("✅ **Найдена информация о победителях закупок** - можно извлекать метаданные\n")

        return ''.join(markdown_parts)

    def process_pdf_protocol(self, pdf_path: Path) -> dict:
        """Полная обработка PDF протокола"""
        print(f"🚀 ОБРАБОТКА ПРОТОКОЛА: {pdf_path.name}")
        print("=" * 60)

        start_time = time.time()

        try:
            # Шаг 1: Создание thumbnail
            base64_thumbnail = self.create_optimized_thumbnail(pdf_path)

            # Шаг 2: Извлечение текста
            doctags = self.extract_text_with_smoldocling(base64_thumbnail)

            # Шаг 3: Парсинг текста
            extracted_text = self.parse_doctags_to_text(doctags)

            # Шаг 4: Анализ содержания
            analysis = self.analyze_protocol_content(extracted_text)

            # Шаг 5: Генерация отчета
            markdown_report = self.generate_markdown_report(pdf_path, extracted_text, analysis)

            processing_time = time.time() - start_time

            result = {
                "success": True,
                "pdf_file": str(pdf_path),
                "processing_time": processing_time,
                "extracted_text": extracted_text,
                "analysis": analysis,
                "markdown_report": markdown_report,
                "doctags": doctags,
                "thumbnail_size_kb": len(base64_thumbnail) // 1024
            }

        except Exception as e:
            processing_time = time.time() - start_time
            print(f"❌ Ошибка обработки: {e}")

            result = {
                "success": False,
                "pdf_file": str(pdf_path),
                "processing_time": processing_time,
                "error": str(e)
            }

        return result

    def save_results(self, result: dict, pdf_path: Path):
        """Сохранение результатов обработки"""
        if not result["success"]:
            print("❌ Обработка завершилась неудачей, результаты не сохранены")
            return

        base_name = pdf_path.stem

        # Markdown отчет
        markdown_file = self.output_dir / f"{base_name}_report.md"
        with open(markdown_file, "w", encoding="utf-8") as f:
            f.write(result["markdown_report"])

        # JSON с полными данными
        json_file = self.output_dir / f"{base_name}_data.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        # Исходные DocTags
        doctags_file = self.output_dir / f"{base_name}_doctags.txt"
        with open(doctags_file, "w", encoding="utf-8") as f:
            f.write(result["doctags"])

        print("💾 Результаты сохранены:")
        print(f"   📄 Отчет: {markdown_file}")
        print(f"   📊 Данные: {json_file}")
        print(f"   📝 DocTags: {doctags_file}")

    def process_single_file(self, pdf_path: str) -> dict:
        """Обработка одного PDF файла"""
        pdf_path = Path(pdf_path)

        if not pdf_path.exists():
            raise FileNotFoundError(f"Файл не найден: {pdf_path}")

        if not self.wait_for_server_ready():
            raise ConnectionError("Сервер SmolDocling недоступен")

        result = self.process_pdf_protocol(pdf_path)
        self.save_results(result, pdf_path)

        return result

def main():
    """Основная функция для командной строки"""
    if len(sys.argv) != 2:
        print("Использование: python smoldocling_pdf_processor.py <путь_к_pdf>")
        print("Пример: python smoldocling_pdf_processor.py /path/to/protocol.pdf")
        sys.exit(1)

    pdf_file = sys.argv[1]

    try:
        processor = SmolDoclingPDFProcessor()
        result = processor.process_single_file(pdf_file)

        if result["success"]:
            print("\n🎉 ОБРАБОТКА ЗАВЕРШЕНА УСПЕШНО!")
            print(f"📁 Результаты: {processor.output_dir}")
            print(f"⏱️ Время обработки: {result['processing_time']:.2f} сек")
            print(f"📊 Уверенность: {result['analysis']['confidence_score']:.2f}")

            # Превью извлеченного текста
            text_preview = result['extracted_text'][:200] + "..." if len(result['extracted_text']) > 200 else result['extracted_text']
            print(f"📝 Текст: {text_preview}")
        else:
            print(f"❌ Ошибка: {result.get('error', 'Неизвестная ошибка')}")
            sys.exit(1)

    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

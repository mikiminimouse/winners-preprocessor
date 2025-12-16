#!/usr/bin/env python3
"""
Массовая обработка 20 UNIT'ов через Qwen3-VL-8B для измерения метрик производительности.
"""
import os
import sys
import json
import time
import base64
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from PIL import Image
import io

try:
    from openai import OpenAI
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
API_KEY = "ZDRhOWQ3OTAtZjU4MC00MzA2LThhNTgtMDU1NGFlMjE4OWRl.85a830f9340966e0ad1fd1642884c7c8"
BASE_URL = "https://92ad3238-81c6-4396-a02a-fb9cef99bce3.modelrun.inference.cloud.ru/v1"
MODEL_NAME = "qwen3-vl-8b-instruct"

# Пути
NORMALIZED_DIR = Path("/root/winners_preprocessor/normalized")
OUTPUT_DIR = Path("/root/winners_preprocessor/output_qwen3_batch")
TEST_UNITS_FILE = Path("/root/winners_preprocessor/test_ocr_units_fixed.json")

class Qwen3BatchOCRProcessor:
    def __init__(self):
        if not OPENAI_SDK_AVAILABLE:
            raise ImportError("openai SDK не установлен")
        
        self.client = OpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=120.0)
        self.model = MODEL_NAME
        OUTPUT_DIR.mkdir(exist_ok=True)
        self.metrics = {
            "total_units": 0,
            "successful_units": 0,
            "total_files": 0,
            "successful_files": 0,
            "total_processing_time": 0.0,
            "total_tokens_used": 0,
            "unit_results": []
        }

    def test_connection(self) -> bool:
        try:
            print("🔍 Тестирование подключения...")
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

    def pdf_to_first_page_image_base64(self, pdf_path: Path) -> str:
        if not PDF2IMAGE_AVAILABLE:
            raise ImportError("pdf2image not installed")
        
        try:
            # Convert only first page of PDF to PIL image
            pil_images = convert_from_path(str(pdf_path), dpi=200, first_page=1, last_page=1)
            if not pil_images:
                raise ValueError("Не удалось конвертировать первую страницу PDF в изображение.")
            
            img = pil_images[0]
            # Convert PIL image to bytes and then to base64
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG') # Save as PNG for better quality
            return base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
        except Exception as e:
            print(f"❌ Ошибка конвертации PDF в изображение: {e}")
            raise

    def create_prompt(self, file_type: str) -> str:
        if file_type == "pdf":
            return """
            Пожалуйста, проанализируйте эту страницу PDF-документа, который является протоколом закупки.
            Извлеките следующую информацию в структурированном JSON формате.
            Если поле отсутствует, укажите null.
            
            Обязательные поля:
            - "номер_процедуры": string (например, "32515314610-01")
            - "номер_лота": string (например, "Лот 1", "1", "null" если нет)
            - "дата_протокола": string (в формате DD.MM.YYYY)
            - "победитель": string (наименование победителя)
            - "ИНН": string (ИНН победителя, только цифры)
            - "КПП": string (КПП победителя, только цифры)
            - "цена_победителя": string (сумма с разделителями, например, "10 025.00")
            - "валюта": string (например, "RUB", "руб.")
            - "предмет_закупки": string (описание предмета закупки)
            - "дата_начала_подачи": string (в формате DD.MM.YYYY)
            - "дата_окончания_подачи": string (в формате DD.MM.YYYY)
            - "дата_проведения": string (в формате DD.MM.YYYY)
            - "заказчик": string (наименование заказчика)
            - "организатор": string (наименование организатора)
            - "состав_комиссии": array of strings (список ФИО членов комиссии)
            
            Дополнительно, извлеките полную текстовую информацию из документа и все таблицы.
            Представьте результат в следующем JSON формате:
            {
                "text": "Полный текст документа",
                "tables": [
                    {
                        "type": "table",
                        "rows": [["Header1", "Header2"], ["Value1", "Value2"]],
                        "bbox": [x1, y1, x2, y2]
                    }
                ],
                "layout": {
                    "pages": [
                        {
                            "page_num": 1,
                            "blocks": [
                                {"type": "title", "text": "...", "bbox": [...]},
                                {"type": "paragraph", "text": "...", "bbox": [...]},
                                {"type": "table", "bbox": [...]}
                            ]
                        }
                    ]
                },
                "metadata": {
                    "номер_процедуры": "...",
                    "номер_лота": "...",
                    "дата_протокола": "...",
                    "победитель": "...",
                    "ИНН": "...",
                    "КПП": "...",
                    "цена_победителя": "...",
                    "валюта": "...",
                    "предмет_закупки": "...",
                    "дата_начала_подачи": "...",
                    "дата_окончания_подачи": "...",
                    "дата_проведения": "...",
                    "заказчик": "...",
                    "организатор": "...",
                    "состав_комиссии": ["...", "..."]
                }
            }
            """
        elif file_type == "image":
            return """
            Пожалуйста, проанализируйте это изображение, которое является сканом документа (протокола закупки).
            Извлеките следующую информацию в структурированном JSON формате.
            Если поле отсутствует, укажите null.
            
            Обязательные поля:
            - "номер_процедуры": string (например, "32515314610-01")
            - "номер_лота": string (например, "Лот 1", "1", "null" если нет)
            - "дата_протокола": string (в формате DD.MM.YYYY)
            - "победитель": string (наименование победителя)
            - "ИНН": string (ИНН победителя, только цифры)
            - "КПП": string (КПП победителя, только цифры)
            - "цена_победителя": string (сумма с разделителями, например, "10 025.00")
            - "валюта": string (например, "RUB", "руб.")
            - "предмет_закупки": string (описание предмета закупки)
            - "дата_начала_подачи": string (в формате DD.MM.YYYY)
            - "дата_окончания_подачи": string (в формате DD.MM.YYYY)
            - "дата_проведения": string (в формате DD.MM.YYYY)
            - "заказчик": string (наименование заказчика)
            - "организатор": string (наименование организатора)
            - "состав_комиссии": array of strings (список ФИО членов комиссии)
            
            Дополнительно, извлеките полную текстовую информацию из документа и все таблицы.
            Представьте результат в следующем JSON формате:
            {
                "text": "Полный текст документа",
                "tables": [
                    {
                        "type": "table",
                        "rows": [["Header1", "Header2"], ["Value1", "Value2"]],
                        "bbox": [x1, y1, x2, y2]
                    }
                ],
                "layout": {
                    "pages": [
                        {
                            "page_num": 1,
                            "blocks": [
                                {"type": "title", "text": "...", "bbox": [...]},
                                {"type": "paragraph", "text": "...", "bbox": [...]},
                                {"type": "table", "bbox": [...]}
                            ]
                        }
                    ]
                },
                "metadata": {
                    "номер_процедуры": "...",
                    "номер_лота": "...",
                    "дата_протокола": "...",
                    "победитель": "...",
                    "ИНН": "...",
                    "КПП": "...",
                    "цена_победителя": "...",
                    "валюта": "...",
                    "предмет_закупки": "...",
                    "дата_начала_подачи": "...",
                    "дата_окончания_подачи": "...",
                    "дата_проведения": "...",
                    "заказчик": "...",
                    "организатор": "...",
                    "состав_комиссии": ["...", "..."]
                }
            }
            """
        else:
            return "Пожалуйста, распознайте разметку этого документа и извлеките текст, таблицы, структуру и метаданные в формате Docling JSON."

    def process_unit(self, unit_info: Dict[str, Any], unit_index: int, total_units: int) -> Optional[Dict[str, Any]]:
        unit_id = unit_info["unit_id"]
        unit_dir = Path(unit_info["unit_dir"])
        files_in_unit = unit_info["files"]
        
        unit_output_dir = OUTPUT_DIR / unit_id
        unit_output_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n{'='*80}")
        print(f"[{unit_index+1}/{total_units}] Обработка UNIT: {unit_id}")
        print(f"{'='*80}")

        unit_start_time = time.time()
        unit_total_tokens = 0
        unit_successful_files = 0
        
        unit_result = {
            "unit_id": unit_id,
            "route": unit_info.get("route", "unknown"),
            "files_processed": [],
            "total_unit_time": 0.0,
            "total_unit_tokens": 0,
            "status": "failed",
            "error": None
        }

        for file_index, file_info in enumerate(files_in_unit):
            file_path = Path(file_info["path"])
            original_name = file_info["original_name"]
            detected_type = file_info["detected_type"]

            print(f"   📄 [{file_index+1}/{len(files_in_unit)}] Файл: {original_name} ({detected_type})")

            file_start_time = time.time()
            file_tokens_used = 0
            
            try:
                messages_content = []
                prompt_text = self.create_prompt(detected_type)

                if detected_type == "image":
                    print(f"\n      📷 Обработка изображения: {original_name}")
                    print(f"         Размер файла: {file_path.stat().st_size / (1024*1024):.1f} MB")
                    base64_image = self.image_to_base64(file_path)
                    print(f"         Конвертация в base64...")
                    print(f"         Base64 длина: {len(base64_image)} символов")
                    messages_content.append({"type": "text", "text": prompt_text})
                    messages_content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}})
                elif detected_type == "pdf":
                    print(f"\n      📄 Обработка PDF: {original_name}")
                    print(f"         Размер файла: {file_path.stat().st_size / 1024:.1f} KB")
                    if not PDF2IMAGE_AVAILABLE:
                        raise ImportError("pdf2image not installed")
                    
                    print(f"         Конвертация первой страницы PDF в изображение...")
                    base64_image = self.pdf_to_first_page_image_base64(file_path)
                    temp_image_path = unit_output_dir / f"{file_path.stem}.png"
                    with open(temp_image_path, "wb") as f:
                        f.write(base64.b64decode(base64_image))
                    print(f"         📷 Обработка изображения: {temp_image_path.name}")
                    print(f"         Размер файла: {temp_image_path.stat().st_size / (1024*1024):.1f} MB")
                    print(f"         Base64 длина: {len(base64_image)} символов")
                    messages_content.append({"type": "text", "text": prompt_text})
                    messages_content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}})
                else:
                    # Для других типов файлов (docx, html_text) пока не поддерживаем vision API
                    # Можно добавить логику для извлечения текста и отправки в обычный LLM
                    print(f"      ❌ Тип файла '{detected_type}' не поддерживается для Vision API. Пропускаем.")
                    continue

                print(f"      ➡️  Отправка запроса к Qwen3-VL-8B...")
                response_start_time = time.time()
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": messages_content}],
                    max_tokens=5000,
                    temperature=0.0, # Более детерминированный ответ для извлечения
                    response_format={"type": "json_object"} # Запрашиваем JSON
                )
                response_time = time.time() - response_start_time
                file_tokens_used = response.usage.total_tokens if response.usage else 0
                self.metrics["total_tokens_used"] += file_tokens_used

                print(f"      ✅ Ответ получен за {response_time:.2f} секунд")
                print(f"         Длина ответа: {len(response.choices[0].message.content)} символов")
                
                # Парсинг JSON ответа
                try:
                    llm_output = json.loads(response.choices[0].message.content)
                    print(f"      📦 Парсинг JSON...")
                except json.JSONDecodeError as e:
                    print(f"      ❌ Ошибка парсинга JSON: {e}")
                    llm_output = {"error": f"JSON Decode Error: {e}", "raw_response": response.choices[0].message.content}

                # Сохранение результатов
                output_filename = f"{file_path.stem}_qwen3_result.json"
                output_path = unit_output_dir / output_filename
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(llm_output, f, indent=2, ensure_ascii=False)
                print(f"      💾 Результаты сохранены: {output_path}")

                unit_successful_files += 1
                unit_result["files_processed"].append({
                    "file_name": original_name,
                    "detected_type": detected_type,
                    "status": "success",
                    "response_time": response_time,
                    "tokens_used": file_tokens_used,
                    "output_path": str(output_path),
                    "llm_output_preview": llm_output.get("text", "")[:200] + "..." if isinstance(llm_output.get("text"), str) else str(llm_output.get("text", ""))[:200] + "..."
                })

            except Exception as e:
                print(f"      ❌ Ошибка обработки: {e}")
                unit_result["files_processed"].append({
                    "file_name": original_name,
                    "detected_type": detected_type,
                    "status": "failed",
                    "error": str(e)
                })
        
        unit_result["total_unit_time"] = time.time() - unit_start_time
        unit_result["total_unit_tokens"] = unit_total_tokens
        if unit_successful_files > 0:
            unit_result["status"] = "success"
            self.metrics["successful_units"] += 1
            self.metrics["successful_files"] += unit_successful_files
        
        self.metrics["total_units"] += 1
        self.metrics["total_files"] += len(files_in_unit)
        self.metrics["total_processing_time"] += unit_result["total_unit_time"]
        self.metrics["unit_results"].append(unit_result)
        
        return unit_result

    def generate_summary_report(self):
        print(f"\n{'='*80}")
        print(f"ГЕНЕРАЦИЯ МЕТРИК")
        print(f"{'='*80}")

        total_units = self.metrics["total_units"]
        successful_units = self.metrics["successful_units"]
        total_files = self.metrics["total_files"]
        successful_files = self.metrics["successful_files"]
        total_time = self.metrics["total_processing_time"]
        total_tokens = self.metrics["total_tokens_used"]

        avg_time_per_file = total_time / successful_files if successful_files > 0 else 0
        avg_tokens_per_file = total_tokens / successful_files if successful_files > 0 else 0

        print(f"📊 Обработано успешно: {successful_units}/{total_units} ({successful_units/total_units*100:.1f}%)")
        print(f"⏱️  Среднее время на успешный файл: {avg_time_per_file:.2f} сек")
        print(f"🔢 Всего токенов использовано: {total_tokens}")

        # Экстраполяция
        estimated_100_units_time = avg_time_per_file * 100
        estimated_500_units_time = avg_time_per_file * 500

        print(f"📈 Оценка для 100 UNIT'ов: {estimated_100_units_time / 60:.1f} мин ({estimated_100_units_time / 3600:.2f} ч)")
        print(f"📈 Оценка для 500 UNIT'ов: {estimated_500_units_time / 60:.1f} мин ({estimated_500_units_time / 3600:.2f} ч)")

        metrics_summary = {
            "timestamp": datetime.now().isoformat(),
            "total_units_attempted": total_units,
            "successful_units": successful_units,
            "total_files_attempted": total_files,
            "successful_files": successful_files,
            "total_processing_time_seconds": total_time,
            "avg_time_per_successful_file_seconds": avg_time_per_file,
            "total_tokens_used": total_tokens,
            "avg_tokens_per_successful_file": avg_tokens_per_file,
            "extrapolation": {
                "estimated_100_units_minutes": estimated_100_units_time / 60,
                "estimated_100_units_hours": estimated_100_units_time / 3600,
                "estimated_500_units_minutes": estimated_500_units_time / 60,
                "estimated_500_units_hours": estimated_500_units_time / 3600
            }
        }
        metrics_output_path = OUTPUT_DIR / f"metrics_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(metrics_output_path, "w", encoding="utf-8") as f:
            json.dump(metrics_summary, f, indent=2, ensure_ascii=False)
        print(f"✅ Метрики сохранены: {metrics_output_path}")

        return metrics_summary

    def generate_comparison_report(self):
        print(f"\n📄 Генерация отчета сравнения...")
        report_path = OUTPUT_DIR / f"comparison_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(f"# Отчет о сравнении обработки UNIT'ов через Qwen3-VL-8B\n\n")
            f.write(f"**Дата отчета:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"## Общая статистика\n")
            f.write(f"- Всего UNIT'ов в тесте: {self.metrics['total_units']}\n")
            f.write(f"- Успешно обработано UNIT'ов: {self.metrics['successful_units']}\n")
            f.write(f"- Общее время обработки: {self.metrics['total_processing_time']:.2f} секунд\n")
            f.write(f"- Всего токенов использовано: {self.metrics['total_tokens_used']}\n\n")

            f.write(f"## Детальный отчет по UNIT'ам\n\n")
            for unit_result in self.metrics["unit_results"]:
                f.write(f"### UNIT ID: `{unit_result['unit_id']}`\n")
                f.write(f"- Статус: **{unit_result['status'].upper()}**\n")
                f.write(f"- Маршрут: `{unit_result['route']}`\n")
                f.write(f"- Время обработки UNIT'а: {unit_result['total_unit_time']:.2f} секунд\n")
                if unit_result['error']:
                    f.write(f"- Ошибка: `{unit_result['error']}`\n")
                f.write(f"\n")

                for file_proc_result in unit_result["files_processed"]:
                    f.write(f"#### Файл: `{file_proc_result['file_name']}`\n")
                    f.write(f"- Тип: `{file_proc_result['detected_type']}`\n")
                    f.write(f"- Статус обработки: **{file_proc_result['status'].upper()}**\n")
                    if file_proc_result['status'] == 'success':
                        f.write(f"- Время запроса к API: {file_proc_result['response_time']:.2f} секунд\n")
                        f.write(f"- Токенов использовано: {file_proc_result['tokens_used']}\n")
                        f.write(f"- Путь к результату JSON: `{file_proc_result['output_path']}`\n")
                        
                        # Сравнение исходного скана и MD документа
                        original_file_path = NORMALIZED_DIR / unit_result['unit_id'] / "files" / file_proc_result['file_name']
                        if original_file_path.exists():
                            f.write(f"\n##### Исходный документ:\n")
                            f.write(f"```\n")
                            f.write(f"Путь: {original_file_path}\n")
                            f.write(f"Тип: {file_proc_result['detected_type']}\n")
                            f.write(f"Размер: {original_file_path.stat().st_size / 1024:.1f} KB\n")
                            f.write(f"```\n")
                        else:
                            f.write(f"\n##### Исходный документ: Файл не найден по пути `{original_file_path}`\n")

                        # Загрузка и форматирование LLM output в Markdown
                        try:
                            with open(file_proc_result['output_path'], 'r', encoding='utf-8') as json_f:
                                llm_output = json.load(json_f)
                            
                            f.write(f"\n##### Результат обработки Qwen3-VL-8B (Docling AST -> Markdown):\n")
                            f.write(f"```markdown\n")
                            f.write(f"# {llm_output.get('metadata', {}).get('title', 'Без заголовка')}\n\n")
                            f.write(f"**Дата:** {llm_output.get('metadata', {}).get('date', 'Не указана')}\n\n")
                            f.write(f"## Извлеченный текст\n")
                            f.write(f"{llm_output.get('text', 'Текст не извлечен')}\n\n")
                            
                            if llm_output.get('tables'):
                                f.write(f"## Извлеченные таблицы\n")
                                for table in llm_output['tables']:
                                    f.write(f"```\n")
                                    # Простая конвертация таблицы в Markdown
                                    if 'rows' in table and table['rows']:
                                        header = table['rows'][0]
                                        body = table['rows'][1:]
                                        f.write("| " + " | ".join(header) + " |\n")
                                        f.write("|" + "---|".join(["---"] * len(header)) + "|\n")
                                        for row in body:
                                            f.write("| " + " | ".join(row) + " |\n")
                                    f.write("```\n\n")
                            
                            f.write(f"## Метаданные\n")
                            for key, value in llm_output.get('metadata', {}).items():
                                if key not in ['title', 'date']: # Уже выведены
                                    f.write(f"- **{key.replace('_', ' ').capitalize()}:** {value}\n")
                            f.write(f"```\n")

                        except Exception as e:
                            f.write(f"\n##### Ошибка при чтении/форматировании результата JSON: {e}\n")
                    else:
                        f.write(f"- Ошибка: `{file_proc_result['error']}`\n")
                    f.write(f"\n---\n\n")
        print(f"✅ Отчет сохранен: {report_path}")

    def run(self):
        print(f"\n{'='*80}")
        print(f"МАССОВАЯ ОБРАБОТКА 20 UNIT'ОВ ЧЕРЕЗ QWEN3-VL-8B")
        print(f"{'='*80}")

        if not self.test_connection():
            print("❌ Не удалось подключиться к API. Проверьте конфигурацию и доступность.")
            return

        try:
            with open(TEST_UNITS_FILE, "r", encoding="utf-8") as f:
                test_units_data = json.load(f)
                self.test_units = test_units_data["units"]
        except FileNotFoundError:
            print(f"❌ Файл со списком UNIT'ов не найден: {TEST_UNITS_FILE}")
            print("   Запустите collect_ocr_units.py для сбора UNIT'ов.")
            return

        print(f"📋 Загружено UNIT'ов для тестирования: {len(self.test_units)}")
        print(f"🎯 Будет обработано: {len(self.test_units)} UNIT'ов")

        for i, unit_info in enumerate(self.test_units):
            self.process_unit(unit_info, i, len(self.test_units))
        
        self.generate_summary_report()
        self.generate_comparison_report()

        print(f"\n{'='*80}")
        print(f"✅ МАССОВАЯ ОБРАБОТКА ЗАВЕРШЕНА")
        print(f"{'='*80}")

if __name__ == "__main__":
    processor = Qwen3BatchOCRProcessor()
    processor.run()

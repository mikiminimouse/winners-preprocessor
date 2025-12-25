#!/usr/bin/env python3
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
OUTPUT_DIR = Path("/root/winners_preprocessor/output_qwen3_all_pages")
TEST_UNITS_FILE = Path("/root/winners_preprocessor/test_ocr_units_fixed.json")

class Qwen3AllPagesProcessor:
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
        self.winners_analysis = []

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

    def pdf_to_all_pages_images_base64(self, pdf_path: Path, unit_output_dir: Path) -> List[str]:
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
                image_path = unit_output_dir / image_filename
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

    def create_prompt(self, file_type: str, page_number: Optional[int] = None) -> str:
        if file_type == "pdf":
            page_info = f" (страница {page_number})" if page_number else ""
            return f"""
            Пожалуйста, проанализируйте эту страницу{page_info} PDF-документа, который является протоколом закупки.
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
            - "участники": array of objects (информация обо всех участниках закупки)
              Каждый участник должен содержать:
              {{
                "номер_заявки": string,
                "наименование": string,
                "сумма_без_ндс": string,
                "сумма_с_ндс": string,
                "статус": string
              }}
            
            Дополнительно, извлеките полную текстовую информацию из документа и все таблицы.
            Представьте результат в следующем JSON формате:
            {{
                "text": "Полный текст документа",
                "tables": [
                    {{
                        "type": "table",
                        "rows": [["Header1", "Header2"], ["Value1", "Value2"]],
                        "bbox": [x1, y1, x2, y2]
                    }}
                ],
                "layout": {{
                    "pages": [
                        {{
                            "page_num": {page_number if page_number else 1},
                            "blocks": [
                                {{"type": "title", "text": "...", "bbox": [...]}}",
                                {{"type": "paragraph", "text": "...", "bbox": [...]}}",
                                {{"type": "table", "bbox": [...]}}"
                            ]
                        }}
                    ]
                }},
                "metadata": {{
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
                    "состав_комиссии": ["...", "..."],
                    "участники": [
                      {{
                        "номер_заявки": "...",
                        "наименование": "...",
                        "сумма_без_ндс": "...",
                        "сумма_с_ндс": "...",
                        "статус": "..."
                      }}
                    ]
                }}
            }}
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
            - "участники": array of objects (информация обо всех участниках закупки)
              Каждый участник должен содержать:
              {
                "номер_заявки": string,
                "наименование": string,
                "сумма_без_ндс": string,
                "сумма_с_ндс": string,
                "статус": string
              }
            
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
                    "состав_комиссии": ["...", "..."],
                    "участники": [
                      {
                        "номер_заявки": "...",
                        "наименование": "...",
                        "сумма_без_ндс": "...",
                        "сумма_с_ндс": "...",
                        "статус": "..."
                      }
                    ]
                }
            }
            """
        else:
            return "Пожалуйста, распознайте разметку этого документа и извлеките текст, таблицы, структуру и метаданные в формате Docling JSON."

    def process_single_page(self, base64_image: str, prompt_text: str, page_num: int) -> Dict[str, Any]:
        """Process a single page/image with the Qwen3-VL model"""
        try:
            messages_content = [
                {"type": "text", "text": prompt_text},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
            ]
            
            print(f"      ➡️  Отправка запроса к Qwen3-VL-8B для страницы {page_num}...")
            response_start_time = time.time()
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": messages_content}],
                max_tokens=5000,
                temperature=0.0, # Более детерминированный ответ для извлечения
                response_format={"type": "json_object"} # Запрашиваем JSON
            )
            response_time = time.time() - response_start_time
            tokens_used = response.usage.total_tokens if response.usage else 0
            
            print(f"      ✅ Ответ получен за {response_time:.2f} секунд")
            print(f"         Длина ответа: {len(response.choices[0].message.content)} символов")
            
            # Parse JSON response
            try:
                llm_output = json.loads(response.choices[0].message.content)
                print(f"      📦 Парсинг JSON...")
                return {
                    "success": True,
                    "data": llm_output,
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
            print(f"      ❌ Ошибка обработки страницы {page_num}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def merge_page_results(self, page_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge results from multiple pages into a single document result"""
        if not page_results:
            return {}
        
        # Initialize merged result with data from first successful page
        merged = {
            "text": "",
            "tables": [],
            "layout": {"pages": []},
            "metadata": {},
            "processing_info": {
                "total_pages": len(page_results),
                "successful_pages": 0,
                "failed_pages": 0,
                "total_response_time": 0,
                "total_tokens_used": 0
            }
        }
        
        for i, result in enumerate(page_results):
            page_num = i + 1
            if result.get("success"):
                merged["processing_info"]["successful_pages"] += 1
                merged["processing_info"]["total_response_time"] += result.get("response_time", 0)
                merged["processing_info"]["total_tokens_used"] += result.get("tokens_used", 0)
                
                page_data = result.get("data", {})
                
                # Merge text
                if page_data.get("text"):
                    merged["text"] += f"\n\n--- СТРАНИЦА {page_num} ---\n\n" + page_data.get("text", "")
                
                # Merge tables
                if page_data.get("tables"):
                    merged["tables"].extend(page_data.get("tables", []))
                
                # Merge layout
                if page_data.get("layout", {}).get("pages"):
                    merged["layout"]["pages"].extend(page_data["layout"]["pages"])
                else:
                    # Create a default page entry if none exists
                    merged["layout"]["pages"].append({
                        "page_num": page_num,
                        "blocks": []
                    })
                
                # Merge metadata (take from first page or merge if needed)
                if not merged["metadata"] and page_data.get("metadata"):
                    merged["metadata"] = page_data["metadata"]
                elif page_data.get("metadata"):
                    # Merge participants from all pages
                    if "участники" in page_data["metadata"]:
                        if "участники" not in merged["metadata"]:
                            merged["metadata"]["участники"] = []
                        merged["metadata"]["участники"].extend(page_data["metadata"]["участники"])
            else:
                merged["processing_info"]["failed_pages"] += 1
        
        return merged

    def analyze_winners(self, merged_result: Dict[str, Any], unit_id: str) -> Dict[str, Any]:
        """Analyze winner information from the merged result"""
        metadata = merged_result.get("metadata", {})
        participants = metadata.get("участники", [])
        
        winner_analysis = {
            "unit_id": unit_id,
            "winner_found": False,
            "winner_info": {},
            "total_participants": len(participants),
            "participants": participants,
            "procurement_info": {
                "procedure_number": metadata.get("номер_процедуры"),
                "lot_number": metadata.get("номер_лота"),
                "procurement_subject": metadata.get("предмет_закупки"),
                "protocol_date": metadata.get("дата_протокола")
            }
        }
        
        # Check for explicit winner information
        winner_name = metadata.get("победитель")
        if winner_name:
            winner_analysis["winner_found"] = True
            winner_analysis["winner_info"] = {
                "name": winner_name,
                "inn": metadata.get("ИНН"),
                "kpp": metadata.get("КПП"),
                "price": metadata.get("цена_победителя"),
                "currency": metadata.get("валюта")
            }
        else:
            # Try to determine winner from participants list
            # Look for participant with status indicating winner
            for participant in participants:
                status = participant.get("статус", "").lower()
                if "побед" in status or "winner" in status or status == "допущен":
                    winner_analysis["winner_found"] = True
                    winner_analysis["winner_info"] = {
                        "name": participant.get("наименование"),
                        "inn": None,  # Would need to extract from participant data
                        "kpp": None,
                        "price": participant.get("сумма_с_ндс"),
                        "currency": "RUB"
                    }
                    break
        
        # Add to global winners analysis
        self.winners_analysis.append(winner_analysis)
        
        return winner_analysis

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
                if detected_type == "image":
                    print(f"\n      📷 Обработка изображения: {original_name}")
                    print(f"         Размер файла: {file_path.stat().st_size / (1024*1024):.1f} MB")
                    base64_image = self.image_to_base64(file_path)
                    print(f"         Конвертация в base64...")
                    print(f"         Base64 длина: {len(base64_image)} символов")
                    
                    prompt_text = self.create_prompt(detected_type)
                    page_result = self.process_single_page(base64_image, prompt_text, 1)
                    
                    if page_result.get("success"):
                        llm_output = page_result["data"]
                        file_tokens_used = page_result.get("tokens_used", 0)
                        self.metrics["total_tokens_used"] += file_tokens_used
                        
                        # Save results
                        output_filename = f"{file_path.stem}_qwen3_result.json"
                        output_path = unit_output_dir / output_filename
                        with open(output_path, "w", encoding="utf-8") as f:
                            json.dump(llm_output, f, indent=2, ensure_ascii=False)
                        print(f"      💾 Результаты сохранены: {output_path}")
                        
                        # Analyze winners
                        winner_analysis = self.analyze_winners(llm_output, unit_id)
                        print(f"      🏆 Победитель найден: {'Да' if winner_analysis['winner_found'] else 'Нет'}")
                        
                        unit_successful_files += 1
                        unit_result["files_processed"].append({
                            "file_name": original_name,
                            "detected_type": detected_type,
                            "status": "success",
                            "response_time": page_result.get("response_time", 0),
                            "tokens_used": file_tokens_used,
                            "output_path": str(output_path),
                            "winner_found": winner_analysis["winner_found"],
                            "winner_info": winner_analysis["winner_info"]
                        })
                    else:
                        unit_result["files_processed"].append({
                            "file_name": original_name,
                            "detected_type": detected_type,
                            "status": "failed",
                            "error": page_result.get("error", "Unknown error")
                        })
                        
                elif detected_type == "pdf":
                    print(f"\n      📄 Обработка PDF: {original_name}")
                    print(f"         Размер файла: {file_path.stat().st_size / 1024:.1f} KB")
                    if not PDF2IMAGE_AVAILABLE:
                        raise ImportError("pdf2image not installed")
                    
                    print(f"         Конвертация всех страниц PDF в изображения...")
                    base64_images = self.pdf_to_all_pages_images_base64(file_path, unit_output_dir)
                    print(f"         Всего страниц: {len(base64_images)}")
                    
                    # Process each page
                    page_results = []
                    for i, base64_image in enumerate(base64_images):
                        page_num = i + 1
                        print(f"         📄 Обработка страницы {page_num} из {len(base64_images)}")
                        prompt_text = self.create_prompt(detected_type, page_num)
                        page_result = self.process_single_page(base64_image, prompt_text, page_num)
                        page_results.append(page_result)
                        if page_result.get("success"):
                            file_tokens_used += page_result.get("tokens_used", 0)
                    
                    self.metrics["total_tokens_used"] += file_tokens_used
                    
                    # Merge results from all pages
                    merged_result = self.merge_page_results(page_results)
                    
                    # Save merged results
                    output_filename = f"{file_path.stem}_qwen3_merged_result.json"
                    output_path = unit_output_dir / output_filename
                    with open(output_path, "w", encoding="utf-8") as f:
                        json.dump(merged_result, f, indent=2, ensure_ascii=False)
                    print(f"      💾 Объединенные результаты сохранены: {output_path}")
                    
                    # Analyze winners
                    winner_analysis = self.analyze_winners(merged_result, unit_id)
                    print(f"      🏆 Победитель найден: {'Да' if winner_analysis['winner_found'] else 'Нет'}")
                    
                    # Save individual page results for reference
                    page_results_path = unit_output_dir / f"{file_path.stem}_page_results.json"
                    with open(page_results_path, "w", encoding="utf-8") as f:
                        json.dump(page_results, f, indent=2, ensure_ascii=False)
                    print(f"      💾 Результаты по страницам сохранены: {page_results_path}")
                    
                    unit_successful_files += 1
                    unit_result["files_processed"].append({
                        "file_name": original_name,
                        "detected_type": detected_type,
                        "status": "success",
                        "total_pages": len(base64_images),
                        "successful_pages": merged_result.get("processing_info", {}).get("successful_pages", 0),
                        "failed_pages": merged_result.get("processing_info", {}).get("failed_pages", 0),
                        "total_response_time": merged_result.get("processing_info", {}).get("total_response_time", 0),
                        "tokens_used": file_tokens_used,
                        "output_path": str(output_path),
                        "winner_found": winner_analysis["winner_found"],
                        "winner_info": winner_analysis["winner_info"],
                        "total_participants": winner_analysis["total_participants"]
                    })
                    
                else:
                    # Для других типов файлов (docx, html_text) пока не поддерживаем vision API
                    print(f"      ❌ Тип файла '{detected_type}' не поддерживается для Vision API. Пропускаем.")
                    continue

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

        # Count winners found
        winners_found = sum(1 for w in self.winners_analysis if w["winner_found"])
        total_analyzed = len(self.winners_analysis)

        print(f"📊 Обработано успешно: {successful_units}/{total_units} ({successful_units/total_units*100:.1f}%)")
        print(f"⏱️  Среднее время на успешный файл: {avg_time_per_file:.2f} сек")
        print(f"🔢 Всего токенов использовано: {total_tokens}")
        print(f"🏆 Победителей найдено: {winners_found}/{total_analyzed} ({winners_found/max(total_analyzed, 1)*100:.1f}%)")

        # Extrapolation
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
            "winners_analysis": {
                "total_analyzed": total_analyzed,
                "winners_found": winners_found,
                "success_rate": winners_found/max(total_analyzed, 1)
            },
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
            f.write(f"# Отчет о сравнении обработки UNIT'ов через Qwen3-VL-8B (все страницы)\n\n")
            f.write(f"**Дата отчета:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"## Общая статистика\n")
            f.write(f"- Всего UNIT'ов в тесте: {self.metrics['total_units']}\n")
            f.write(f"- Успешно обработано UNIT'ов: {self.metrics['successful_units']}\n")
            f.write(f"- Общее время обработки: {self.metrics['total_processing_time']:.2f} секунд\n")
            f.write(f"- Всего токенов использовано: {self.metrics['total_tokens_used']}\n")
            f.write(f"- Победителей найдено: {sum(1 for w in self.winners_analysis if w['winner_found'])}/{len(self.winners_analysis)}\n\n")

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
                        if file_proc_result['detected_type'] == 'pdf':
                            f.write(f"- Всего страниц: {file_proc_result.get('total_pages', 'N/A')}\n")
                            f.write(f"- Успешно обработано страниц: {file_proc_result.get('successful_pages', 'N/A')}\n")
                            f.write(f"- Неудачно обработано страниц: {file_proc_result.get('failed_pages', 'N/A')}\n")
                            f.write(f"- Общее время обработки страниц: {file_proc_result.get('total_response_time', 0):.2f} секунд\n")
                        else:
                            f.write(f"- Время запроса к API: {file_proc_result['response_time']:.2f} секунд\n")
                        
                        f.write(f"- Токенов использовано: {file_proc_result['tokens_used']}\n")
                        f.write(f"- Путь к результату JSON: `{file_proc_result['output_path']}`\n")
                        f.write(f"- Победитель найден: **{'Да' if file_proc_result.get('winner_found', False) else 'Нет'}**\n")
                        
                        if file_proc_result.get('winner_found'):
                            winner_info = file_proc_result.get('winner_info', {})
                            f.write(f"- Информация о победителе:\n")
                            f.write(f"  - Название: {winner_info.get('name', 'N/A')}\n")
                            f.write(f"  - ИНН: {winner_info.get('inn', 'N/A')}\n")
                            f.write(f"  - КПП: {winner_info.get('kpp', 'N/A')}\n")
                            f.write(f"  - Цена: {winner_info.get('price', 'N/A')} {winner_info.get('currency', 'N/A')}\n")
                        
                        # Original document info
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

                        # LLM output preview
                        try:
                            with open(file_proc_result['output_path'], 'r', encoding='utf-8') as json_f:
                                llm_output = json.load(json_f)
                            
                            f.write(f"\n##### Результат обработки Qwen3-VL-8B (Docling AST -> Markdown):\n")
                            f.write(f"```markdown\n")
                            f.write(f"# {llm_output.get('metadata', {}).get('title', 'Без заголовка')}\n\n")
                            f.write(f"**Дата:** {llm_output.get('metadata', {}).get('date', 'Не указана')}\n\n")
                            f.write(f"## Извлеченный текст\n")
                            text_preview = llm_output.get('text', 'Текст не извлечен')
                            f.write(f"{text_preview[:1000]}{'...' if len(text_preview) > 1000 else ''}\n\n")
                            
                            if llm_output.get('tables'):
                                f.write(f"## Извлеченные таблицы\n")
                                for table in llm_output['tables'][:2]:  # Limit to first 2 tables
                                    f.write(f"```\n")
                                    if 'rows' in table and table['rows']:
                                        header = table['rows'][0]
                                        body = table['rows'][1:3] if len(table['rows']) > 1 else table['rows'][1:2]  # Limit rows
                                        f.write("| " + " | ".join(header) + " |\n")
                                        f.write("|" + "---|".join(["---"] * len(header)) + "|\n")
                                        for row in body:
                                            f.write("| " + " | ".join(row) + " |\n")
                                    f.write("```\n\n")
                            
                            f.write(f"## Метаданные\n")
                            for key, value in llm_output.get('metadata', {}).items():
                                if key not in ['title', 'date']: # Already shown
                                    if key == 'участники':
                                        f.write(f"- **Участники:** {len(value) if isinstance(value, list) else 'N/A'}\n")
                                    else:
                                        f.write(f"- **{key.replace('_', ' ').capitalize()}:** {value}\n")
                            f.write(f"```\n")

                        except Exception as e:
                            f.write(f"\n##### Ошибка при чтении/форматировании результата JSON: {e}\n")
                    else:
                        f.write(f"- Ошибка: `{file_proc_result['error']}`\n")
                    f.write(f"\n---\n\n")
        print(f"✅ Отчет сохранен: {report_path}")

    def generate_winners_analysis_report(self):
        """Generate a separate report focused on winners analysis"""
        print(f"\n🏆 Генерация отчета по анализу победителей...")
        winners_report_path = OUTPUT_DIR / f"winners_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # Enrich winners analysis with more details
        enriched_analysis = []
        for analysis in self.winners_analysis:
            # Find corresponding unit result for more details
            unit_result = next((u for u in self.metrics["unit_results"] if u["unit_id"] == analysis["unit_id"]), None)
            if unit_result:
                analysis["unit_details"] = {
                    "route": unit_result.get("route"),
                    "processing_time": unit_result.get("total_unit_time"),
                    "status": unit_result.get("status")
                }
            enriched_analysis.append(analysis)
        
        with open(winners_report_path, "w", encoding="utf-8") as f:
            json.dump(enriched_analysis, f, indent=2, ensure_ascii=False)
        print(f"✅ Отчет по победителям сохранен: {winners_report_path}")
        
        # Also generate a summary markdown report
        winners_md_path = OUTPUT_DIR / f"winners_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(winners_md_path, "w", encoding="utf-8") as f:
            f.write(f"# Анализ победителей по госзакупкам\n\n")
            f.write(f"**Дата отчета:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"## Сводная статистика\n")
            f.write(f"- Всего проанализировано документов: {len(enriched_analysis)}\n")
            f.write(f"- Документов с найденным победителем: {sum(1 for w in enriched_analysis if w['winner_found'])}\n")
            f.write(f"- Процент найденных победителей: {sum(1 for w in enriched_analysis if w['winner_found'])/max(len(enriched_analysis), 1)*100:.1f}%\n\n")
            
            f.write(f"## Документы с найденными победителями\n\n")
            for analysis in enriched_analysis:
                if analysis["winner_found"]:
                    f.write(f"### UNIT: `{analysis['unit_id']}`\n")
                    f.write(f"- Номер процедуры: {analysis['procurement_info'].get('procedure_number', 'N/A')}\n")
                    f.write(f"- Предмет закупки: {analysis['procurement_info'].get('procurement_subject', 'N/A')}\n")
                    f.write(f"- Дата протокола: {analysis['procurement_info'].get('protocol_date', 'N/A')}\n")
                    f.write(f"- Победитель: **{analysis['winner_info'].get('name', 'N/A')}**\n")
                    f.write(f"- ИНН: {analysis['winner_info'].get('inn', 'N/A')}\n")
                    f.write(f"- КПП: {analysis['winner_info'].get('kpp', 'N/A')}\n")
                    f.write(f"- Цена: {analysis['winner_info'].get('price', 'N/A')} {analysis['winner_info'].get('currency', 'N/A')}\n")
                    f.write(f"- Всего участников: {analysis['total_participants']}\n\n")
            
            f.write(f"## Документы без найденного победителя\n\n")
            for analysis in enriched_analysis:
                if not analysis["winner_found"]:
                    f.write(f"### UNIT: `{analysis['unit_id']}`\n")
                    f.write(f"- Номер процедуры: {analysis['procurement_info'].get('procedure_number', 'N/A')}\n")
                    f.write(f"- Предмет закупки: {analysis['procurement_info'].get('procurement_subject', 'N/A')}\n")
                    f.write(f"- Дата протокола: {analysis['procurement_info'].get('protocol_date', 'N/A')}\n")
                    f.write(f"- Всего участников: {analysis['total_participants']}\n")
                    f.write(f"- Статус UNIT'а: {analysis.get('unit_details', {}).get('status', 'N/A')}\n\n")
        
        print(f"✅ Сводный отчет по победителям сохранен: {winners_md_path}")

    def run(self):
        print(f"\n{'='*80}")
        print(f"МАССОВАЯ ОБРАБОТКА 10 UNIT'ОВ ЧЕРЕЗ QWEN3-VL-8B (ВСЕ СТРАНИЦЫ)")
        print(f"{'='*80}")

        if not self.test_connection():
            print("❌ Не удалось подключиться к API. Проверьте конфигурацию и доступность.")
            return

        try:
            with open(TEST_UNITS_FILE, "r", encoding="utf-8") as f:
                test_units_data = json.load(f)
                # Use only first 10 units instead of all 20
                self.test_units = test_units_data["units"][:10]
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
        self.generate_winners_analysis_report()

        print(f"\n{'='*80}")
        print(f"✅ МАССОВАЯ ОБРАБОТКА ЗАВЕРШЕНА")
        print(f"{'='*80}")

if __name__ == "__main__":
    processor = Qwen3AllPagesProcessor()
    processor.run()


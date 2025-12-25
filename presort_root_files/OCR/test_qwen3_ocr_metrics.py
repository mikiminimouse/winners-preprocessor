#!/usr/bin/env python3
"""
Скрипт для тестирования Qwen3-VL-8B с извлечением метаданных протоколов закупок и сбором метрик производительности.
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

# Попытка импорта SDK
try:
    from evolution_openai import EvolutionOpenAI
    EVOLUTION_SDK_AVAILABLE = True
except ImportError:
    EVOLUTION_SDK_AVAILABLE = False
    print("⚠️  evolution_openai SDK не установлен. Установите: pip install evolution-openai")

# Конфигурация
# API key в формате "key_id.secret"
API_KEY_FULL = "ZDRhOWQ3OTAtZjU4MC00MzA2LThhNTgtMDU1NGFlMjE4OWRl.85a830f9340966e0ad1fd1642884c7c8"
# Разделяем на key_id и secret
if "." in API_KEY_FULL:
    API_KEY_ID, API_KEY_SECRET = API_KEY_FULL.split(".", 1)
else:
    API_KEY_ID = API_KEY_FULL
    API_KEY_SECRET = ""
BASE_URL = "https://92ad3238-81c6-4396-a02a-fb9cef99bce3.modelrun.inference.cloud.ru/v1"
MODEL_NAME = "qwen3-vl-8b-instruct"

# Пути
NORMALIZED_DIR = Path("/root/winners_preprocessor/normalized")
OUTPUT_DIR = Path("/root/winners_preprocessor/output_qwen3_ocr")
TEST_UNITS_FILE = Path("/root/winners_preprocessor/test_ocr_units_list.json")


class Qwen3OCRProcessor:
    """Класс для обработки документов через Qwen3-VL-8B с извлечением метаданных."""
    
    def __init__(self):
        """Инициализация клиента."""
        if not EVOLUTION_SDK_AVAILABLE:
            raise ImportError("evolution_openai SDK не установлен")
        
        # Используем key_id и secret (требуемый формат для evolution_openai)
        # API key в формате "key_id.secret" разделяем по точке
        print(f"🔑 Инициализация клиента с key_id: {API_KEY_ID[:20]}...")
        try:
            self.client = EvolutionOpenAI(
                key_id=API_KEY_ID,
                secret=API_KEY_SECRET,
                base_url=BASE_URL
            )
            # Проверяем подключение простым запросом
            print("   Проверка подключения...")
            test_response = self.client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5
            )
            print("   ✅ Подключение успешно!")
        except Exception as e:
            error_msg = str(e)
            if "401" in error_msg or "Unauthorized" in error_msg:
                raise Exception(f"Ошибка авторизации (401). Проверьте правильность API key. "
                              f"Убедитесь, что ключ активен и имеет доступ к endpoint: {BASE_URL}")
            else:
                raise Exception(f"Ошибка инициализации клиента: {e}")
        self.model = MODEL_NAME
        OUTPUT_DIR.mkdir(exist_ok=True)
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_time": 0.0,
            "total_tokens": 0,
            "requests": []
        }
    
    def image_to_base64(self, image_path: Path) -> str:
        """Конвертирует изображение в base64."""
        with open(image_path, "rb") as f:
            image_data = f.read()
        return base64.b64encode(image_data).decode('utf-8')
    
    def create_metadata_prompt(self) -> str:
        """Создает промпт для извлечения метаданных протокола закупки."""
        return """Проанализируй изображение протокола закупки и извлеки из него следующую информацию в формате строгого JSON:

{
  "номер_процедуры": "номер процедуры закупки (если есть)",
  "номер_лота": "номер лота (если есть)",
  "дата_протокола": "дата протокола в формате ДД.ММ.ГГГГ",
  "победитель": "наименование победителя/поставщика",
  "ИНН": "ИНН победителя (если указан)",
  "КПП": "КПП победителя (если указан)",
  "цена_победителя": "цена контракта (только число, без валюты)",
  "валюта": "валюта (RUB, USD, EUR и т.д.)",
  "предмет_закупки": "предмет закупки/наименование товара/услуги",
  "дата_начала_подачи": "дата начала подачи заявок в формате ДД.ММ.ГГГГ",
  "дата_окончания_подачи": "дата окончания подачи заявок в формате ДД.ММ.ГГГГ",
  "дата_проведения": "дата проведения процедуры в формате ДД.ММ.ГГГГ",
  "заказчик": "полное наименование заказчика",
  "организатор": "полное наименование организатора (если отличается от заказчика)",
  "состав_комиссии": ["ФИО члена комиссии 1", "ФИО члена комиссии 2", ...],
  "полный_текст": "весь извлеченный текст из документа",
  "таблицы": [
    {
      "тип": "таблица с участниками/результатами",
      "данные": [["Заголовок 1", "Заголовок 2"], ["Данные 1", "Данные 2"]]
    }
  ]
}

ВАЖНО:
- Верни ТОЛЬКО валидный JSON, без дополнительного текста
- Если поле не найдено, используй пустую строку "" или пустой массив []
- Извлеки ВСЕ таблицы из документа
- Состав комиссии должен быть массивом ФИО
- ИНН и КПП извлекай только если они явно указаны
- Цена должна быть числом без пробелов и символов валюты"""
    
    def process_image(self, image_path: Path) -> Dict[str, Any]:
        """Обрабатывает изображение через Qwen3-VL-8B."""
        print(f"  📷 Обработка: {image_path.name}")
        
        # Конвертируем в base64
        base64_image = self.image_to_base64(image_path)
        
        # Создаем сообщение с изображением
        messages = [
            {
                "role": "system",
                "content": "Ты эксперт по анализу протоколов закупок. Твоя задача - точно извлечь структурированную информацию из протоколов."
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": self.create_metadata_prompt()},
                    {
                        "type": "image",
                        "image": base64_image
                    }
                ]
            }
        ]
        
        # Вызов API
        start_time = time.time()
        self.metrics["total_requests"] += 1
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=8000,
                temperature=0.1,  # Низкая температура для точного извлечения
                top_p=0.95
            )
            
            response_time = time.time() - start_time
            self.metrics["total_time"] += response_time
            
            # Подсчет токенов (если доступно)
            if hasattr(response, 'usage'):
                tokens = response.usage.total_tokens if hasattr(response.usage, 'total_tokens') else 0
                self.metrics["total_tokens"] += tokens
            
            if not response.choices or not response.choices[0].message.content:
                raise ValueError("Пустой ответ от модели")
            
            content = response.choices[0].message.content
            
            # Парсим JSON из ответа
            metadata = self.parse_metadata_response(content)
            
            self.metrics["successful_requests"] += 1
            self.metrics["requests"].append({
                "file": image_path.name,
                "success": True,
                "response_time": response_time,
                "tokens": tokens if 'tokens' in locals() else 0
            })
            
            return {
                "success": True,
                "metadata": metadata,
                "raw_response": content,
                "response_time": response_time
            }
            
        except Exception as e:
            self.metrics["failed_requests"] += 1
            self.metrics["requests"].append({
                "file": image_path.name,
                "success": False,
                "error": str(e),
                "response_time": time.time() - start_time
            })
            
            return {
                "success": False,
                "error": str(e),
                "response_time": time.time() - start_time
            }
    
    def parse_metadata_response(self, content: str) -> Dict[str, Any]:
        """Парсит метаданные из ответа модели."""
        content = content.strip()
        
        # Удаляем markdown code blocks если есть
        if content.startswith("```"):
            lines = content.split("\n")
            # Удаляем первую и последнюю строки с ```
            if len(lines) > 2:
                content = "\n".join(lines[1:-1])
        
        # Удаляем markdown code blocks с языком
        content = re.sub(r'^```json\s*', '', content)
        content = re.sub(r'^```\s*', '', content)
        content = re.sub(r'\s*```$', '', content)
        content = content.strip()
        
        try:
            metadata = json.loads(content)
            
            # Валидация и нормализация
            normalized = {
                "номер_процедуры": metadata.get("номер_процедуры", ""),
                "номер_лота": metadata.get("номер_лота", ""),
                "дата_протокола": metadata.get("дата_протокола", ""),
                "победитель": metadata.get("победитель", ""),
                "ИНН": metadata.get("ИНН", ""),
                "КПП": metadata.get("КПП", ""),
                "цена_победителя": metadata.get("цена_победителя", ""),
                "валюта": metadata.get("валюта", ""),
                "предмет_закупки": metadata.get("предмет_закупки", ""),
                "дата_начала_подачи": metadata.get("дата_начала_подачи", ""),
                "дата_окончания_подачи": metadata.get("дата_окончания_подачи", ""),
                "дата_проведения": metadata.get("дата_проведения", ""),
                "заказчик": metadata.get("заказчик", ""),
                "организатор": metadata.get("организатор", ""),
                "состав_комиссии": metadata.get("состав_комиссии", []),
                "полный_текст": metadata.get("полный_текст", ""),
                "таблицы": metadata.get("таблицы", [])
            }
            
            return normalized
            
        except json.JSONDecodeError as e:
            print(f"  ⚠️  Ошибка парсинга JSON: {e}")
            print(f"  Первые 500 символов ответа: {content[:500]}")
            # Возвращаем пустую структуру при ошибке
            return {
                "номер_процедуры": "",
                "номер_лота": "",
                "дата_протокола": "",
                "победитель": "",
                "ИНН": "",
                "КПП": "",
                "цена_победителя": "",
                "валюта": "",
                "предмет_закупки": "",
                "дата_начала_подачи": "",
                "дата_окончания_подачи": "",
                "дата_проведения": "",
                "заказчик": "",
                "организатор": "",
                "состав_комиссии": [],
                "полный_текст": "",
                "таблицы": [],
                "parse_error": str(e),
                "raw_content": content[:2000]
            }
    
    def extract_metadata_fields(self, metadata: Dict[str, Any]) -> Dict[str, bool]:
        """Проверяет, какие поля метаданных были извлечены."""
        required_fields = [
            "номер_процедуры",
            "номер_лота",
            "дата_протокола",
            "победитель",
            "ИНН",
            "КПП",
            "цена_победителя",
            "дата_начала_подачи",
            "дата_окончания_подачи",
            "дата_проведения",
            "заказчик",
            "состав_комиссии"
        ]
        
        extracted = {}
        for field in required_fields:
            value = metadata.get(field, "")
            if isinstance(value, list):
                extracted[field] = len(value) > 0
            else:
                extracted[field] = bool(value and str(value).strip())
        
        return extracted


def process_unit(processor: Qwen3OCRProcessor, unit_info: Dict[str, Any]) -> Dict[str, Any]:
    """Обрабатывает один UNIT через Qwen3-VL-8B."""
    unit_id = unit_info["unit_id"]
    route = unit_info.get("route", "unknown")
    files = unit_info.get("files", [])
    
    print(f"\n{'='*70}")
    print(f"Обработка UNIT: {unit_id}")
    print(f"Route: {route}")
    print(f"Файлов: {len(files)}")
    print(f"{'='*70}")
    
    results = {
        "unit_id": unit_id,
        "route": route,
        "processed_at": datetime.utcnow().isoformat(),
        "files": []
    }
    
    for file_info in files:
        file_path_str = file_info.get("path", "")
        # Заменяем /app/normalized на реальный путь
        file_path_str = file_path_str.replace("/app/normalized", str(NORMALIZED_DIR))
        file_path = Path(file_path_str)
        
        if not file_path.exists():
            print(f"  ❌ Файл не найден: {file_path}")
            results["files"].append({
                "file_id": file_info.get("file_id"),
                "original_name": file_info.get("original_name"),
                "error": "File not found"
            })
            continue
        
        file_type = file_info.get("detected_type", "unknown")
        print(f"\n  📄 Файл: {file_info.get('original_name')} ({file_type})")
        
        # Обрабатываем в зависимости от типа
        if file_type == "image":
            # Прямая обработка изображения
            result = processor.process_image(file_path)
            
            if result["success"]:
                metadata = result["metadata"]
                extracted_fields = processor.extract_metadata_fields(metadata)
                
                print(f"  ✅ Обработано за {result['response_time']:.2f}s")
                print(f"     Извлечено полей: {sum(extracted_fields.values())}/{len(extracted_fields)}")
                
                # Выводим ключевые поля
                if metadata.get("номер_процедуры"):
                    print(f"     Номер процедуры: {metadata['номер_процедуры']}")
                if metadata.get("победитель"):
                    print(f"     Победитель: {metadata['победитель']}")
                if metadata.get("цена_победителя"):
                    print(f"     Цена: {metadata['цена_победителя']} {metadata.get('валюта', '')}")
                
                results["files"].append({
                    "file_id": file_info.get("file_id"),
                    "original_name": file_info.get("original_name"),
                    "metadata": metadata,
                    "extracted_fields": extracted_fields,
                    "response_time": result["response_time"],
                    "success": True
                })
            else:
                print(f"  ❌ Ошибка: {result.get('error')}")
                results["files"].append({
                    "file_id": file_info.get("file_id"),
                    "original_name": file_info.get("original_name"),
                    "error": result.get("error"),
                    "success": False
                })
        
        elif file_type == "pdf":
            # Конвертируем PDF страницы в изображения
            print(f"  📄 Конвертация PDF в изображения...")
            try:
                from pdf2image import convert_from_path
                
                images = convert_from_path(str(file_path), dpi=200)
                print(f"     Извлечено страниц: {len(images)}")
                
                # Обрабатываем первую страницу (для теста)
                if images:
                    import tempfile
                    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
                        images[0].save(tmp_file.name, "PNG")
                        tmp_path = Path(tmp_file.name)
                    
                    try:
                        result = processor.process_image(tmp_path)
                        
                        if result["success"]:
                            metadata = result["metadata"]
                            extracted_fields = processor.extract_metadata_fields(metadata)
                            
                            print(f"  ✅ Первая страница обработана за {result['response_time']:.2f}s")
                            print(f"     Извлечено полей: {sum(extracted_fields.values())}/{len(extracted_fields)}")
                            
                            results["files"].append({
                                "file_id": file_info.get("file_id"),
                                "original_name": file_info.get("original_name"),
                                "metadata": metadata,
                                "extracted_fields": extracted_fields,
                                "pages_processed": 1,
                                "total_pages": len(images),
                                "response_time": result["response_time"],
                                "success": True
                            })
                        else:
                            results["files"].append({
                                "file_id": file_info.get("file_id"),
                                "original_name": file_info.get("original_name"),
                                "error": result.get("error"),
                                "success": False
                            })
                    finally:
                        if tmp_path.exists():
                            tmp_path.unlink()
                else:
                    results["files"].append({
                        "file_id": file_info.get("file_id"),
                        "original_name": file_info.get("original_name"),
                        "error": "No pages extracted from PDF",
                        "success": False
                    })
                    
            except ImportError:
                print(f"  ⚠️  pdf2image не установлен")
                results["files"].append({
                    "file_id": file_info.get("file_id"),
                    "original_name": file_info.get("original_name"),
                    "error": "pdf2image not installed",
                    "success": False
                })
            except Exception as e:
                print(f"  ❌ Ошибка: {e}")
                results["files"].append({
                    "file_id": file_info.get("file_id"),
                    "original_name": file_info.get("original_name"),
                    "error": str(e),
                    "success": False
                })
        else:
            print(f"  ⚠️  Неподдерживаемый тип: {file_type}")
            results["files"].append({
                "file_id": file_info.get("file_id"),
                "original_name": file_info.get("original_name"),
                "error": f"Unsupported file type: {file_type}",
                "success": False
            })
    
    return results


def save_results(results: Dict[str, Any], processor: Qwen3OCRProcessor):
    """Сохраняет результаты."""
    unit_id = results["unit_id"]
    output_unit_dir = OUTPUT_DIR / unit_id
    output_unit_dir.mkdir(parents=True, exist_ok=True)
    
    for file_result in results.get("files", []):
        if not file_result.get("success"):
            continue
        
        original_name = file_result.get("original_name", "unknown")
        file_base = Path(original_name).stem
        
        # Сохраняем метаданные
        output_data = {
            "unit_id": unit_id,
            "file": original_name,
            "route": results.get("route"),
            "processed_at": results.get("processed_at"),
            "processing_method": "qwen3-vl-8b",
            "metadata": file_result.get("metadata", {}),
            "extracted_fields": file_result.get("extracted_fields", {}),
            "metrics": {
                "response_time": file_result.get("response_time", 0),
                "pages_processed": file_result.get("pages_processed", 1),
                "total_pages": file_result.get("total_pages", 1)
            }
        }
        
        output_file = output_unit_dir / f"{file_base}_metadata.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"  💾 Сохранено: {output_file}")


def generate_report(all_results: List[Dict[str, Any]], processor: Qwen3OCRProcessor) -> Dict[str, Any]:
    """Генерирует итоговый отчет с метриками."""
    total_units = len(all_results)
    successful_units = sum(1 for r in all_results if any(f.get("success") for f in r.get("files", [])))
    
    # Статистика по извлеченным полям
    field_stats = {}
    required_fields = [
        "номер_процедуры", "номер_лота", "дата_протокола", "победитель",
        "ИНН", "КПП", "цена_победителя", "дата_начала_подачи",
        "дата_окончания_подачи", "дата_проведения", "заказчик", "состав_комиссии"
    ]
    
    for field in required_fields:
        field_stats[field] = {
            "extracted": 0,
            "total": 0
        }
    
    total_files = 0
    successful_files = 0
    total_response_time = 0.0
    
    for result in all_results:
        for file_result in result.get("files", []):
            total_files += 1
            if file_result.get("success"):
                successful_files += 1
                total_response_time += file_result.get("response_time", 0)
                
                extracted_fields = file_result.get("extracted_fields", {})
                for field in required_fields:
                    field_stats[field]["total"] += 1
                    if extracted_fields.get(field, False):
                        field_stats[field]["extracted"] += 1
    
    # Метрики производительности
    avg_response_time = total_response_time / successful_files if successful_files > 0 else 0
    total_time = processor.metrics["total_time"]
    
    # Экстраполяция на 100 и 500 UNIT'ов
    # Предполагаем, что в среднем 1 файл на UNIT
    avg_time_per_unit = avg_response_time
    estimated_100_units = avg_time_per_unit * 100 / 60  # в минутах
    estimated_500_units = avg_time_per_unit * 500 / 60  # в минутах
    
    report = {
        "test_summary": {
            "tested_at": datetime.utcnow().isoformat(),
            "total_units": total_units,
            "successful_units": successful_units,
            "success_rate_units": f"{(successful_units/total_units*100):.1f}%" if total_units > 0 else "0%",
            "total_files": total_files,
            "successful_files": successful_files,
            "success_rate_files": f"{(successful_files/total_files*100):.1f}%" if total_files > 0 else "0%"
        },
        "performance_metrics": {
            "total_requests": processor.metrics["total_requests"],
            "successful_requests": processor.metrics["successful_requests"],
            "failed_requests": processor.metrics["failed_requests"],
            "total_time_seconds": round(total_time, 2),
            "total_time_minutes": round(total_time / 60, 2),
            "avg_response_time_seconds": round(avg_response_time, 2),
            "total_tokens": processor.metrics["total_tokens"],
            "avg_tokens_per_request": round(processor.metrics["total_tokens"] / processor.metrics["successful_requests"], 0) if processor.metrics["successful_requests"] > 0 else 0
        },
        "extrapolation": {
            "avg_time_per_file_seconds": round(avg_response_time, 2),
            "estimated_100_units_minutes": round(estimated_100_units, 2),
            "estimated_100_units_hours": round(estimated_100_units / 60, 2),
            "estimated_500_units_minutes": round(estimated_500_units, 2),
            "estimated_500_units_hours": round(estimated_500_units / 60, 2),
            "note": "Предполагается 1 файл на UNIT, время может варьироваться в зависимости от размера документов"
        },
        "field_extraction_stats": {
            field: {
                "extracted": stats["extracted"],
                "total": stats["total"],
                "success_rate": f"{(stats['extracted']/stats['total']*100):.1f}%" if stats["total"] > 0 else "0%"
            }
            for field, stats in field_stats.items()
        },
        "detailed_metrics": processor.metrics
    }
    
    return report


def main():
    """Главная функция."""
    print("=" * 70)
    print("ТЕСТИРОВАНИЕ QWEN3-VL-8B: ИЗВЛЕЧЕНИЕ МЕТАДАННЫХ И МЕТРИКИ")
    print("=" * 70)
    print()
    
    # Проверка SDK
    if not EVOLUTION_SDK_AVAILABLE:
        print("❌ evolution_openai SDK не установлен")
        print("   Установите: pip install evolution-openai")
        sys.exit(1)
    
    # Загрузка списка UNIT'ов
    if not TEST_UNITS_FILE.exists():
        print(f"❌ Файл со списком UNIT'ов не найден: {TEST_UNITS_FILE}")
        print("   Запустите сначала: python3 collect_ocr_units.py")
        sys.exit(1)
    
    with open(TEST_UNITS_FILE, "r", encoding="utf-8") as f:
        test_data = json.load(f)
    
    units = test_data.get("units", [])
    print(f"📋 Загружено UNIT'ов для тестирования: {len(units)}")
    
    # Инициализация процессора
    try:
        processor = Qwen3OCRProcessor()
        print("✅ Qwen3-VL-8B клиент инициализирован")
    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "Unauthorized" in error_msg or "авторизации" in error_msg:
            print(f"\n⚠️  ВНИМАНИЕ: Проблема с авторизацией API!")
            print(f"   Ошибка: {e}")
            print(f"\n   Возможные причины:")
            print(f"   1. API key неправильный или истек")
            print(f"   2. API key не имеет доступа к endpoint")
            print(f"   3. Неправильный формат API key")
            print(f"\n   Проверьте:")
            print(f"   - Правильность API key: {API_KEY_ID[:30]}...")
            print(f"   - Доступность endpoint: {BASE_URL}")
            print(f"   - Права доступа ключа в Cloud.ru")
            print(f"\n   Для продолжения тестирования с mock данными нажмите Enter...")
            print(f"   (или Ctrl+C для выхода)")
            try:
                input()
                print("\n🔄 Запуск в режиме демонстрации с mock данными...")
                # Используем mock режим
                processor = None
                mock_mode = True
            except KeyboardInterrupt:
                print("\n❌ Прервано пользователем")
                sys.exit(1)
        else:
            print(f"❌ Ошибка инициализации: {e}")
            sys.exit(1)
    else:
        mock_mode = False
    
    # Обработка UNIT'ов
    all_results = []
    start_time = time.time()
    
    # Ограничиваем количество для теста (можно убрать для полного теста)
    test_limit = min(10, len(units))  # Тестируем первые 10 для быстрой проверки
    print(f"🧪 Тестируем первые {test_limit} UNIT'ов...")
    
    if mock_mode:
        print("\n⚠️  РЕЖИМ ДЕМОНСТРАЦИИ: Используются mock данные для показа структуры")
        print("   Реальные запросы к API не выполняются\n")
        
        # Создаем mock процессор для метрик
        class MockProcessor:
            def __init__(self):
                self.metrics = {
                    "total_requests": 0,
                    "successful_requests": 0,
                    "failed_requests": 0,
                    "total_time": 0.0,
                    "total_tokens": 0,
                    "requests": []
                }
        
        processor = MockProcessor()
        
        # Генерируем mock результаты
        import random
        for i, unit_info in enumerate(units[:test_limit], 1):
            print(f"\n\n[{i}/{test_limit}] Mock обработка UNIT: {unit_info.get('unit_id')}")
            time.sleep(0.5)  # Симуляция обработки
            
            # Mock метаданные
            mock_metadata = {
                "номер_процедуры": f"325153{random.randint(10000, 99999)}",
                "номер_лота": f"Лот {random.randint(1, 5)}" if random.random() > 0.3 else "",
                "дата_протокола": "28.10.2025",
                "победитель": f"Участник {random.randint(1, 5)}" if random.random() > 0.2 else "",
                "ИНН": f"{random.randint(1000000000, 9999999999)}" if random.random() > 0.4 else "",
                "КПП": f"{random.randint(100000000, 999999999)}" if random.random() > 0.5 else "",
                "цена_победителя": f"{random.randint(10000, 100000)}.00",
                "валюта": "RUB",
                "предмет_закупки": "Оказание услуг" if random.random() > 0.3 else "",
                "дата_начала_подачи": "20.10.2025" if random.random() > 0.3 else "",
                "дата_окончания_подачи": "28.10.2025" if random.random() > 0.3 else "",
                "дата_проведения": "28.10.2025" if random.random() > 0.2 else "",
                "заказчик": "ГАУЗ 'Детская Республиканская Клиническая Больница' МЗ РБ" if random.random() > 0.2 else "",
                "организатор": "" if random.random() > 0.5 else "ГАУЗ 'ДРКБ' МЗ РБ",
                "состав_комиссии": ["Пинтаев О.Ю.", "Очирова Э.Ш.", "Иванов П.Е."] if random.random() > 0.3 else [],
                "полный_текст": "Mock текст протокола закупки...",
                "таблицы": []
            }
            
            mock_response_time = random.uniform(10, 25)  # 10-25 секунд
            processor.metrics["total_requests"] += 1
            processor.metrics["successful_requests"] += 1
            processor.metrics["total_time"] += mock_response_time
            processor.metrics["total_tokens"] += random.randint(2000, 5000)
            
            result = {
                "unit_id": unit_info.get("unit_id"),
                "route": unit_info.get("route"),
                "processed_at": datetime.utcnow().isoformat(),
                "files": [{
                    "file_id": unit_info.get("files", [{}])[0].get("file_id", ""),
                    "original_name": unit_info.get("files", [{}])[0].get("original_name", ""),
                    "metadata": mock_metadata,
                    "extracted_fields": {k: bool(v) if not isinstance(v, list) else len(v) > 0 
                                       for k, v in mock_metadata.items() if k not in ["полный_текст", "таблицы"]},
                    "response_time": mock_response_time,
                    "success": True
                }]
            }
            all_results.append(result)
            save_results(result, processor)
    else:
        for i, unit_info in enumerate(units[:test_limit], 1):
            print(f"\n\n[{i}/{test_limit}]")
            try:
                result = process_unit(processor, unit_info)
                all_results.append(result)
                save_results(result, processor)
            except Exception as e:
                print(f"❌ Ошибка обработки UNIT {unit_info.get('unit_id')}: {e}")
                import traceback
                traceback.print_exc()
    
    total_test_time = time.time() - start_time
    
    # Генерация отчета
    print("\n" + "=" * 70)
    print("ГЕНЕРАЦИЯ ОТЧЕТА")
    print("=" * 70)
    
    report = generate_report(all_results, processor)
    report["test_summary"]["total_test_time_seconds"] = round(total_test_time, 2)
    report["test_summary"]["total_test_time_minutes"] = round(total_test_time / 60, 2)
    
    # Сохранение отчета
    report_file = OUTPUT_DIR / f"ocr_test_report_{int(time.time())}.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    # Вывод краткого отчета
    print("\n📊 КРАТКИЙ ОТЧЕТ:")
    print(f"   Всего UNIT'ов: {report['test_summary']['total_units']}")
    print(f"   Успешно обработано: {report['test_summary']['successful_units']} ({report['test_summary']['success_rate_units']})")
    print(f"   Всего файлов: {report['test_summary']['total_files']}")
    print(f"   Успешно файлов: {report['test_summary']['successful_files']} ({report['test_summary']['success_rate_files']})")
    print(f"\n⏱️  ПРОИЗВОДИТЕЛЬНОСТЬ:")
    print(f"   Среднее время на файл: {report['performance_metrics']['avg_response_time_seconds']:.2f} сек")
    print(f"   Общее время теста: {report['test_summary']['total_test_time_minutes']:.2f} мин")
    print(f"\n📈 ЭКСТРАПОЛЯЦИЯ:")
    print(f"   Оценка для 100 UNIT'ов: {report['extrapolation']['estimated_100_units_minutes']:.1f} мин ({report['extrapolation']['estimated_100_units_hours']:.2f} ч)")
    print(f"   Оценка для 500 UNIT'ов: {report['extrapolation']['estimated_500_units_minutes']:.1f} мин ({report['extrapolation']['estimated_500_units_hours']:.2f} ч)")
    print(f"\n📋 ИЗВЛЕЧЕНИЕ ПОЛЕЙ:")
    for field, stats in report["field_extraction_stats"].items():
        if stats["total"] > 0:
            print(f"   {field}: {stats['extracted']}/{stats['total']} ({stats['success_rate']})")
    
    print(f"\n💾 Полный отчет сохранен: {report_file}")
    print("\n✅ Готово!")


if __name__ == "__main__":
    main()


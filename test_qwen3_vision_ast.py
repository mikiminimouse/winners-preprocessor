#!/usr/bin/env python3
"""
Скрипт для тестирования Qwen3-VL-8B как внешнего ML inference для формирования AST JSON в формате Docling.

Использует Qwen3-VL-8B для:
- OCR (Image → text)
- Layout detection / segmentation
- Table extraction
- Формирование AST JSON (text, tables, layout, metadata)
"""
import os
import sys
import json
import time
import base64
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

# Попытка импорта SDK
try:
    from evolution_openai import EvolutionOpenAI
    EVOLUTION_SDK_AVAILABLE = True
except ImportError:
    EVOLUTION_SDK_AVAILABLE = False
    print("⚠️  evolution_openai SDK не установлен. Установите: pip install evolution-openai")

# Конфигурация
API_KEY = "ZDRhOWQ3OTAtZjU4MC00MzA2LThhNTgtMDU1NGFlMjE4OWRl.85a830f9340966e0ad1fd1642884c7c8"
BASE_URL = "https://92ad3238-81c6-4396-a02a-fb9cef99bce3.modelrun.inference.cloud.ru/v1"
MODEL_NAME = "qwen3-vl-8b-instruct"

# Пути
NORMALIZED_DIR = Path("/root/winners_preprocessor/normalized")
OUTPUT_DIR = Path("/root/winners_preprocessor/output_qwen3")
TEST_UNITS_FILE = Path("/root/winners_preprocessor/test_units_list.json")


class Qwen3VisionProcessor:
    """Класс для обработки документов через Qwen3-VL-8B."""
    
    def __init__(self):
        """Инициализация клиента."""
        if not EVOLUTION_SDK_AVAILABLE:
            raise ImportError("evolution_openai SDK не установлен")
        
        self.client = EvolutionOpenAI(
            api_key=API_KEY,
            base_url=BASE_URL
        )
        self.model = MODEL_NAME
        OUTPUT_DIR.mkdir(exist_ok=True)
    
    def image_to_base64(self, image_path: Path) -> str:
        """Конвертирует изображение в base64."""
        with open(image_path, "rb") as f:
            image_data = f.read()
        return base64.b64encode(image_data).decode('utf-8')
    
    def create_ast_prompt(self) -> str:
        """Создает промпт для формирования AST JSON в формате Docling."""
        return """Проанализируй изображение документа и извлеки из него всю информацию, включая текст, таблицы, структуру и метаданные.

Верни результат в формате строгого JSON со следующей структурой:

{
  "text": "полный извлеченный текст из документа",
  "tables": [
    {
      "type": "table",
      "rows": [
        ["Заголовок 1", "Заголовок 2"],
        ["Данные 1", "Данные 2"]
      ],
      "bbox": [x1, y1, x2, y2]
    }
  ],
  "layout": {
    "pages": [
      {
        "page_num": 1,
        "blocks": [
          {
            "type": "text" | "title" | "paragraph" | "list",
            "text": "содержимое блока",
            "bbox": [x1, y1, x2, y2]
          }
        ]
      }
    ],
    "sections": [
      {
        "title": "Название секции",
        "level": 1,
        "content": "текст секции"
      }
    ]
  },
  "metadata": {
    "title": "заголовок документа",
    "author": "автор (если есть)",
    "date": "дата (если есть)",
    "pages_count": 1
  }
}

ВАЖНО:
- Верни ТОЛЬКО валидный JSON, без дополнительного текста
- Если таблица не найдена, верни пустой массив []
- Координаты bbox должны быть в формате [x1, y1, x2, y2]
- Сохрани структуру документа (заголовки, параграфы, списки)
- Извлеки все таблицы с их данными"""
    
    def process_image(self, image_path: Path) -> Dict[str, Any]:
        """Обрабатывает изображение через Qwen3-VL-8B."""
        print(f"  📷 Обработка изображения: {image_path.name}")
        
        # Конвертируем в base64
        base64_image = self.image_to_base64(image_path)
        
        # Создаем сообщение с изображением
        messages = [
            {
                "role": "system",
                "content": "Ты эксперт по анализу документов. Твоя задача - извлечь структурированную информацию из изображений документов."
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": self.create_ast_prompt()},
                    {
                        "type": "image",
                        "image": base64_image
                    }
                ]
            }
        ]
        
        # Вызов API
        start_time = time.time()
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=8000,
                temperature=0.1,  # Низкая температура для более точного извлечения
                top_p=0.95
            )
            
            response_time = time.time() - start_time
            
            if not response.choices or not response.choices[0].message.content:
                raise ValueError("Пустой ответ от модели")
            
            content = response.choices[0].message.content
            
            # Парсим JSON из ответа
            ast_json = self.parse_ast_response(content)
            
            return {
                "success": True,
                "ast": ast_json,
                "raw_response": content,
                "response_time": response_time
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response_time": time.time() - start_time
            }
    
    def parse_ast_response(self, content: str) -> Dict[str, Any]:
        """Парсит AST JSON из ответа модели."""
        # Пытаемся найти JSON в ответе (может быть обернут в markdown или текст)
        content = content.strip()
        
        # Удаляем markdown code blocks если есть
        if content.startswith("```"):
            lines = content.split("\n")
            # Удаляем первую и последнюю строки с ```
            content = "\n".join(lines[1:-1])
        
        # Удаляем markdown code blocks с языком
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        
        content = content.strip()
        
        try:
            ast = json.loads(content)
            
            # Валидация структуры
            if not isinstance(ast, dict):
                raise ValueError("AST должен быть объектом")
            
            # Нормализация структуры
            normalized_ast = {
                "text": ast.get("text", ""),
                "tables": ast.get("tables", []),
                "layout": ast.get("layout", {
                    "pages": [],
                    "sections": [],
                    "blocks": []
                }),
                "metadata": ast.get("metadata", {})
            }
            
            return normalized_ast
            
        except json.JSONDecodeError as e:
            print(f"  ⚠️  Ошибка парсинга JSON: {e}")
            print(f"  Первые 500 символов ответа: {content[:500]}")
            # Возвращаем пустую структуру при ошибке
            return {
                "text": "",
                "tables": [],
                "layout": {"pages": [], "sections": [], "blocks": []},
                "metadata": {},
                "parse_error": str(e),
                "raw_content": content[:1000]
            }


def process_unit(processor: Qwen3VisionProcessor, unit_info: Dict[str, Any]) -> Dict[str, Any]:
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
                ast = result["ast"]
                print(f"  ✅ Обработано за {result['response_time']:.2f}s")
                print(f"     Текст: {len(ast.get('text', ''))} символов")
                print(f"     Таблиц: {len(ast.get('tables', []))}")
                
                results["files"].append({
                    "file_id": file_info.get("file_id"),
                    "original_name": file_info.get("original_name"),
                    "ast": ast,
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
                
                # Обрабатываем каждую страницу
                page_results = []
                combined_ast = {
                    "text": "",
                    "tables": [],
                    "layout": {"pages": [], "sections": [], "blocks": []},
                    "metadata": {"pages_count": len(images)}
                }
                
                for page_num, image in enumerate(images, 1):
                    print(f"     Обработка страницы {page_num}/{len(images)}...")
                    
                    # Сохраняем временное изображение
                    import tempfile
                    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
                        image.save(tmp_file.name, "PNG")
                        tmp_path = Path(tmp_file.name)
                    
                    try:
                        # Обрабатываем страницу
                        result = processor.process_image(tmp_path)
                        
                        if result["success"]:
                            page_ast = result["ast"]
                            # Объединяем результаты
                            combined_ast["text"] += f"\n\n--- Страница {page_num} ---\n\n{page_ast.get('text', '')}"
                            combined_ast["tables"].extend(page_ast.get("tables", []))
                            
                            # Добавляем страницу в layout
                            page_layout = {
                                "page_num": page_num,
                                "blocks": page_ast.get("layout", {}).get("blocks", [])
                            }
                            combined_ast["layout"]["pages"].append(page_layout)
                            
                            page_results.append({
                                "page": page_num,
                                "success": True,
                                "response_time": result["response_time"]
                            })
                        else:
                            page_results.append({
                                "page": page_num,
                                "success": False,
                                "error": result.get("error")
                            })
                    finally:
                        # Удаляем временный файл
                        if tmp_path.exists():
                            tmp_path.unlink()
                
                # Сохраняем объединенный результат
                results["files"].append({
                    "file_id": file_info.get("file_id"),
                    "original_name": file_info.get("original_name"),
                    "ast": combined_ast,
                    "pages_processed": len([r for r in page_results if r.get("success")]),
                    "total_pages": len(images),
                    "page_results": page_results,
                    "success": any(r.get("success") for r in page_results)
                })
                
                print(f"  ✅ PDF обработан: {len([r for r in page_results if r.get('success')])}/{len(images)} страниц")
                
            except ImportError:
                print(f"  ⚠️  pdf2image не установлен. Установите: pip install pdf2image")
                print(f"     Также требуется poppler-utils: sudo apt-get install poppler-utils")
                results["files"].append({
                    "file_id": file_info.get("file_id"),
                    "original_name": file_info.get("original_name"),
                    "error": "pdf2image not installed",
                    "success": False
                })
            except Exception as e:
                print(f"  ❌ Ошибка конвертации PDF: {e}")
                results["files"].append({
                    "file_id": file_info.get("file_id"),
                    "original_name": file_info.get("original_name"),
                    "error": str(e),
                    "success": False
                })
        
        elif file_type == "docx":
            # Для DOCX нужно конвертировать в изображения (через LibreOffice или python-docx + reportlab)
            print(f"  ⚠️  Конвертация DOCX в изображения требует дополнительных библиотек")
            print(f"     Рекомендуется: конвертировать DOCX в PDF, затем использовать PDF обработку")
            results["files"].append({
                "file_id": file_info.get("file_id"),
                "original_name": file_info.get("original_name"),
                "error": "DOCX to images conversion not implemented. Convert to PDF first.",
                "success": False
            })
        
        else:
            print(f"  ⚠️  Неподдерживаемый тип файла: {file_type}")
            results["files"].append({
                "file_id": file_info.get("file_id"),
                "original_name": file_info.get("original_name"),
                "error": f"Unsupported file type: {file_type}",
                "success": False
            })
    
    return results


def save_results(results: Dict[str, Any]):
    """Сохраняет результаты в формате Docling."""
    unit_id = results["unit_id"]
    output_unit_dir = OUTPUT_DIR / unit_id
    output_unit_dir.mkdir(parents=True, exist_ok=True)
    
    for file_result in results.get("files", []):
        if not file_result.get("success"):
            continue
        
        original_name = file_result.get("original_name", "unknown")
        file_base = Path(original_name).stem
        
        # Сохраняем AST JSON в формате Docling
        ast = file_result.get("ast", {})
        output_data = {
            "unit_id": unit_id,
            "file": original_name,
            "route": results.get("route"),
            "detected_type": "image",
            "needs_ocr": False,
            "status": "processed",
            "processing_method": "qwen3-vl-8b",
            "text": ast.get("text", ""),
            "tables": ast.get("tables", []),
            "metadata": ast.get("metadata", {}),
            "layout": ast.get("layout", {
                "pages": [],
                "sections": [],
                "blocks": []
            }),
            "metrics": {
                "unit_id": unit_id,
                "file_name": original_name,
                "route": results.get("route"),
                "processing_times": {
                    "qwen3_vision": file_result.get("response_time", 0)
                },
                "file_stats": {
                    "text_length": len(ast.get("text", "")),
                    "tables_extracted": len(ast.get("tables", [])),
                    "pages_count": len(ast.get("layout", {}).get("pages", []))
                },
                "status": "completed",
                "created_at": results.get("processed_at")
            }
        }
        
        output_file = output_unit_dir / f"{file_base}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"  💾 Сохранено: {output_file}")


def main():
    """Главная функция."""
    print("=" * 70)
    print("ТЕСТИРОВАНИЕ QWEN3-VL-8B ДЛЯ ФОРМИРОВАНИЯ AST JSON")
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
        print("   Запустите сначала: python3 collect_test_units.py")
        sys.exit(1)
    
    with open(TEST_UNITS_FILE, "r", encoding="utf-8") as f:
        test_data = json.load(f)
    
    units = test_data.get("units", [])
    print(f"📋 Загружено UNIT'ов для тестирования: {len(units)}")
    
    # Инициализация процессора
    try:
        processor = Qwen3VisionProcessor()
        print("✅ Qwen3-VL-8B клиент инициализирован")
    except Exception as e:
        print(f"❌ Ошибка инициализации: {e}")
        sys.exit(1)
    
    # Обработка UNIT'ов
    all_results = []
    for i, unit_info in enumerate(units, 1):
        print(f"\n\n[{i}/{len(units)}]")
        try:
            result = process_unit(processor, unit_info)
            all_results.append(result)
            save_results(result)
        except Exception as e:
            print(f"❌ Ошибка обработки UNIT {unit_info.get('unit_id')}: {e}")
            import traceback
            traceback.print_exc()
    
    # Итоговый отчет
    print("\n" + "=" * 70)
    print("ИТОГОВЫЙ ОТЧЕТ")
    print("=" * 70)
    
    total = len(all_results)
    successful = sum(1 for r in all_results if any(f.get("success") for f in r.get("files", [])))
    
    print(f"Всего UNIT'ов обработано: {total}")
    print(f"Успешно: {successful}")
    print(f"Результаты сохранены в: {OUTPUT_DIR}")
    
    # Сохраняем общий отчет
    report_file = OUTPUT_DIR / f"test_report_{int(time.time())}.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump({
            "tested_at": datetime.utcnow().isoformat(),
            "total_units": total,
            "successful_units": successful,
            "results": all_results
        }, f, indent=2, ensure_ascii=False)
    
    print(f"Отчет сохранен: {report_file}")
    print("\n✅ Готово!")


if __name__ == "__main__":
    main()


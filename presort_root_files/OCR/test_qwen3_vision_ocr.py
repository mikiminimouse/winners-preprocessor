#!/usr/bin/env python3
"""
Тестирование подключения к Qwen3-VL-8B для распознавания разметки документов.
Использует API key для подключения и отправляет изображения для OCR.
"""
import os
import sys
import json
import time
import base64
from pathlib import Path
from typing import Dict, Any, Optional

# Используем стандартный OpenAI клиент
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("⚠️  openai SDK не установлен. Установите: pip install openai")
    sys.exit(1)

# Конфигурация
API_KEY = "ZDRhOWQ3OTAtZjU4MC00MzA2LThhNTgtMDU1NGFlMjE4OWRl.85a830f9340966e0ad1fd1642884c7c8"
BASE_URL = "https://92ad3238-81c6-4396-a02a-fb9cef99bce3.modelrun.inference.cloud.ru/v1"
MODEL_NAME = "qwen3-vl-8b-instruct"

# Пути
NORMALIZED_DIR = Path("/root/winners_preprocessor/normalized")
OUTPUT_DIR = Path("/root/winners_preprocessor/output_qwen3_vision")
OUTPUT_DIR.mkdir(exist_ok=True)


def image_to_base64(image_path: Path) -> str:
    """Конвертирует изображение в base64."""
    with open(image_path, "rb") as f:
        image_data = f.read()
    return base64.b64encode(image_data).decode('utf-8')


def create_docling_ocr_prompt() -> str:
    """Создает промпт для распознавания разметки документа аналогично Docling OCR."""
    return """Проанализируй изображение документа и извлеки из него всю информацию, включая текст, таблицы, структуру и метаданные.

Твоя задача - распознать разметку документа аналогично тому, как это делает Docling OCR pipeline.

Верни результат в формате строгого JSON со следующей структурой (аналогично Docling):

{
  "text": "полный извлеченный текст из документа, сохраненный с сохранением структуры (заголовки, параграфы, списки)",
  "tables": [
    {
      "type": "table",
      "rows": [
        ["Заголовок колонки 1", "Заголовок колонки 2"],
        ["Данные строки 1 колонка 1", "Данные строки 1 колонка 2"],
        ["Данные строки 2 колонка 1", "Данные строки 2 колонка 2"]
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
            "type": "title" | "heading" | "paragraph" | "list" | "table",
            "text": "содержимое блока",
            "bbox": [x1, y1, x2, y2],
            "level": 1
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
    ],
    "blocks": [
      {
        "type": "text" | "title" | "table",
        "text": "содержимое",
        "bbox": [x1, y1, x2, y2]
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
- Верни ТОЛЬКО валидный JSON, без дополнительного текста до или после
- Сохрани структуру документа (заголовки разных уровней, параграфы, списки)
- Извлеки ВСЕ таблицы с их данными в формате строк и колонок
- Координаты bbox должны быть в формате [x1, y1, x2, y2] в пикселях
- Текст должен быть извлечен с сохранением логической структуры
- Если таблица не найдена, верни пустой массив []
- Если блок не найден, верни пустой объект {}"""


def test_connection(client: OpenAI) -> bool:
    """Тестирует подключение к API."""
    print("🔍 Тестирование подключения...")
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "Вы очень полезный ассистент."},
                {"role": "user", "content": "Скажи 'Привет' одним словом"}
            ],
            max_tokens=10,
            temperature=0.5
        )
        
        if response.choices and response.choices[0].message.content:
            print(f"✅ Подключение успешно! Ответ: {response.choices[0].message.content}")
            return True
        else:
            print("❌ Пустой ответ от API")
            return False
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return False


def process_image_ocr(client: OpenAI, image_path: Path) -> Dict[str, Any]:
    """Обрабатывает изображение через Qwen3-VL-8B для OCR и распознавания разметки."""
    print(f"\n📷 Обработка изображения: {image_path.name}")
    print(f"   Размер файла: {image_path.stat().st_size / 1024:.1f} KB")
    
    # Конвертируем изображение в base64
    print("   Конвертация в base64...")
    base64_image = image_to_base64(image_path)
    print(f"   Base64 длина: {len(base64_image)} символов")
    
    # Создаем сообщение с изображением в формате OpenAI API
    # Формат: data:image/jpeg;base64,{base64_image}
    image_data_url = f"data:image/jpeg;base64,{base64_image}"
    
    messages = [
        {
            "role": "system",
            "content": "Ты эксперт по анализу документов и распознаванию разметки. Твоя задача - извлечь структурированную информацию из изображений документов аналогично Docling OCR pipeline."
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": create_docling_ocr_prompt()},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": image_data_url
                    }
                }
            ]
        }
    ]
    
    # Вызов API
    print("   Отправка запроса к Qwen3-VL-8B...")
    start_time = time.time()
    
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            max_tokens=8000,
            temperature=0.1,  # Низкая температура для точного извлечения
            top_p=0.95,
            presence_penalty=0,
            timeout=120.0  # Таймаут 2 минуты для обработки изображений
        )
        
        response_time = time.time() - start_time
        
        if not response.choices or not response.choices[0].message.content:
            raise ValueError("Пустой ответ от модели")
        
        content = response.choices[0].message.content
        print(f"   ✅ Ответ получен за {response_time:.2f} секунд")
        print(f"   Длина ответа: {len(content)} символов")
        
        # Парсим JSON из ответа
        print("   Парсинг JSON...")
        docling_result = parse_docling_response(content)
        
        return {
            "success": True,
            "result": docling_result,
            "raw_response": content,
            "response_time": response_time,
            "tokens_used": getattr(response.usage, 'total_tokens', 0) if hasattr(response, 'usage') else 0
        }
        
    except Exception as e:
        error_msg = str(e)
        print(f"   ❌ Ошибка: {error_msg}")
        return {
            "success": False,
            "error": error_msg,
            "response_time": time.time() - start_time
        }


def parse_docling_response(content: str) -> Dict[str, Any]:
    """Парсит ответ модели в формат Docling."""
    import re
    
    content = content.strip()
    
    # Удаляем markdown code blocks если есть
    if content.startswith("```"):
        lines = content.split("\n")
        if len(lines) > 2:
            # Удаляем первую строку с ``` и последнюю с ```
            content = "\n".join(lines[1:-1])
    
    # Удаляем markdown code blocks с языком
    content = re.sub(r'^```json\s*', '', content, flags=re.MULTILINE)
    content = re.sub(r'^```\s*', '', content, flags=re.MULTILINE)
    content = re.sub(r'\s*```$', '', content, flags=re.MULTILINE)
    content = content.strip()
    
    try:
        result = json.loads(content)
        
        # Нормализация структуры под Docling формат
        normalized = {
            "text": result.get("text", ""),
            "tables": result.get("tables", []),
            "layout": result.get("layout", {
                "pages": [],
                "sections": [],
                "blocks": []
            }),
            "metadata": result.get("metadata", {})
        }
        
        # Валидация структуры
        if not isinstance(normalized["tables"], list):
            normalized["tables"] = []
        if not isinstance(normalized["layout"], dict):
            normalized["layout"] = {"pages": [], "sections": [], "blocks": []}
        if not isinstance(normalized["metadata"], dict):
            normalized["metadata"] = {}
        
        return normalized
        
    except json.JSONDecodeError as e:
        print(f"   ⚠️  Ошибка парсинга JSON: {e}")
        print(f"   Первые 500 символов ответа: {content[:500]}")
        
        # Возвращаем пустую структуру при ошибке
        return {
            "text": "",
            "tables": [],
            "layout": {"pages": [], "sections": [], "blocks": []},
            "metadata": {},
            "parse_error": str(e),
            "raw_content": content[:2000]
        }


def save_results(image_path: Path, result: Dict[str, Any], output_data: Dict[str, Any]):
    """Сохраняет результаты в формате Docling."""
    file_base = image_path.stem
    output_file = OUTPUT_DIR / f"{file_base}_docling_result.json"
    
    # Формируем результат в формате Docling
    docling_format = {
        "file": image_path.name,
        "route": "image_ocr",
        "detected_type": "image",
        "needs_ocr": True,
        "status": "processed",
        "processing_method": "qwen3-vl-8b-instruct",
        "text": output_data.get("text", ""),
        "tables": output_data.get("tables", []),
        "metadata": output_data.get("metadata", {}),
        "layout": output_data.get("layout", {
            "pages": [],
            "sections": [],
            "blocks": []
        }),
        "metrics": {
            "processing_times": {
                "ocr": result.get("response_time", 0),
                "total": result.get("response_time", 0)
            },
            "file_stats": {
                "text_length": len(output_data.get("text", "")),
                "tables_extracted": len(output_data.get("tables", [])),
                "pages_count": len(output_data.get("layout", {}).get("pages", []))
            },
            "tokens_used": result.get("tokens_used", 0)
        }
    }
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(docling_format, f, indent=2, ensure_ascii=False)
    
    print(f"   💾 Результаты сохранены: {output_file}")
    return output_file


def main():
    """Главная функция."""
    print("=" * 70)
    print("ТЕСТИРОВАНИЕ QWEN3-VL-8B: РАСПОЗНАВАНИЕ РАЗМЕТКИ ДОКУМЕНТОВ")
    print("=" * 70)
    print()
    
    print(f"🔑 API Key: {API_KEY[:30]}...")
    print(f"🌐 Base URL: {BASE_URL}")
    print(f"🤖 Модель: {MODEL_NAME}")
    print()
    
    # Инициализация клиента OpenAI
    try:
        print("🔌 Инициализация клиента OpenAI...")
        client = OpenAI(
            api_key=API_KEY,
            base_url=BASE_URL
        )
        print("✅ Клиент инициализирован")
    except Exception as e:
        print(f"❌ Ошибка инициализации клиента: {e}")
        sys.exit(1)
    
    # Тест подключения
    if not test_connection(client):
        print("\n❌ Не удалось подключиться к API. Проверьте:")
        print("   1. Правильность API key")
        print("   2. Доступность endpoint")
        print("   3. Права доступа ключа")
        sys.exit(1)
    
    # Поиск изображений для тестирования
    print("\n" + "=" * 70)
    print("ПОИСК ИЗОБРАЖЕНИЙ ДЛЯ ТЕСТИРОВАНИЯ")
    print("=" * 70)
    
    # Ищем изображения в normalized
    image_files = []
    for unit_dir in NORMALIZED_DIR.glob("UNIT_*"):
        files_dir = unit_dir / "files"
        if files_dir.exists():
            for img_file in files_dir.glob("*.jpg"):
                image_files.append(img_file)
            for img_file in files_dir.glob("*.jpeg"):
                image_files.append(img_file)
            for img_file in files_dir.glob("*.png"):
                image_files.append(img_file)
    
    if not image_files:
        print("❌ Изображения не найдены в normalized/")
        print("   Используйте изображение из UNIT_03f63c4b3ab3b09e для теста")
        # Пробуем найти конкретное изображение
        test_image = NORMALIZED_DIR / "UNIT_03f63c4b3ab3b09e" / "files" / "Изображение_2.jpg"
        if test_image.exists():
            image_files = [test_image]
            print(f"   ✅ Найдено тестовое изображение: {test_image}")
        else:
            sys.exit(1)
    
    print(f"📁 Найдено изображений: {len(image_files)}")
    
    # Обрабатываем первое изображение для теста
    test_image = image_files[0]
    print(f"\n🎯 Тестируем изображение: {test_image.name}")
    
    # Обработка изображения
    result = process_image_ocr(client, test_image)
    
    if result["success"]:
        print("\n" + "=" * 70)
        print("РЕЗУЛЬТАТЫ ОБРАБОТКИ")
        print("=" * 70)
        
        docling_result = result["result"]
        
        print(f"\n📊 Статистика:")
        print(f"   Время обработки: {result['response_time']:.2f} сек")
        print(f"   Токенов использовано: {result.get('tokens_used', 0)}")
        print(f"   Длина текста: {len(docling_result.get('text', ''))} символов")
        print(f"   Таблиц найдено: {len(docling_result.get('tables', []))}")
        print(f"   Страниц: {len(docling_result.get('layout', {}).get('pages', []))}")
        print(f"   Блоков: {len(docling_result.get('layout', {}).get('blocks', []))}")
        
        # Сохранение результатов
        output_file = save_results(test_image, result, docling_result)
        
        print(f"\n✅ Обработка завершена успешно!")
        print(f"📄 Результаты сохранены в: {output_file}")
        
        # Показываем первые 500 символов текста
        text_preview = docling_result.get("text", "")[:500]
        if text_preview:
            print(f"\n📝 Предпросмотр извлеченного текста:")
            print(f"   {text_preview}...")
        
    else:
        print(f"\n❌ Ошибка обработки: {result.get('error')}")
        sys.exit(1)
    
    print("\n" + "=" * 70)
    print("✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("=" * 70)


if __name__ == "__main__":
    main()


#!/usr/bin/env python3
"""
Скрипт для получения URLs документов через MCP сервер http://mcp.multitender.ru/mcp
Вместо прямого подключения к MongoDB использует MCP API.
"""
import sys
import json
import requests
from datetime import datetime
from typing import Dict, Any, Optional

MCP_SERVER_URL = "http://mcp.multitender.ru/mcp"


def get_protocols_via_mcp(date_str: str) -> Dict[str, Any]:
    """
    Получает протоколы по дате через MCP сервер.
    
    Args:
        date_str: Дата в формате YYYY-MM-DD
    
    Returns:
        Словарь с протоколами и URLs документов
    """
    try:
        # Валидация формата даты
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"Неверный формат даты '{date_str}'. Используйте формат YYYY-MM-DD")
    
    # Формируем запрос к MCP серверу
    payload = {
        "name": "get_protocols_by_date_223",
        "arguments": {
            "date": date_str
        }
    }
    
    print(f"Запрос к MCP серверу: {MCP_SERVER_URL}")
    print(f"Дата: {date_str}")
    print(f"Параметры: {json.dumps(payload, ensure_ascii=False)}")
    
    try:
        response = requests.post(
            f"{MCP_SERVER_URL}/tools/call",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        response.raise_for_status()
        
        result = response.json()
        
        # Проверяем формат ответа MCP
        if "result" in result and "content" in result["result"]:
            content = result["result"]["content"]
            if content and len(content) > 0:
                if "json" in content[0]:
                    protocols = content[0]["json"]
                    return protocols
                elif "text" in content[0]:
                    # Если вернулся текст, пытаемся распарсить как JSON
                    try:
                        protocols = json.loads(content[0]["text"])
                        return protocols
                    except json.JSONDecodeError:
                        raise ValueError(f"Не удалось распарсить ответ: {content[0]['text']}")
        
        raise ValueError(f"Неожиданный формат ответа: {result}")
        
    except requests.exceptions.RequestException as e:
        raise Exception(f"Ошибка при запросе к MCP серверу: {e}")
    except json.JSONDecodeError as e:
        raise Exception(f"Ошибка при парсинге JSON ответа: {e}")


def main():
    """Основная функция для тестирования MCP сервера."""
    print("=" * 60)
    print("Тестирование MCP сервера для получения протоколов")
    print("=" * 60)
    print(f"MCP Server: {MCP_SERVER_URL}")
    print()
    
    if len(sys.argv) < 2:
        print("Использование: python3 test_mcp_server.py <date>")
        print("Пример: python3 test_mcp_server.py 2025-01-17")
        sys.exit(1)
    
    date_str = sys.argv[1]
    
    try:
        print(f"1. Получение протоколов за дату: {date_str}...")
        protocols = get_protocols_via_mcp(date_str)
        
        print(f"\n✓ Получено протоколов: {len(protocols)}")
        
        # Подсчитываем общее количество URLs
        total_urls = 0
        for purchase_number, doc_info in protocols.items():
            if isinstance(doc_info, dict):
                total_urls += 1
            elif isinstance(doc_info, list):
                total_urls += len(doc_info)
        
        print(f"✓ Всего URLs документов: {total_urls}")
        
        # Сохраняем результаты в JSON
        output_file = f"test_protocols_mcp_{date_str}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "date": date_str,
                "source": "mcp_server",
                "mcp_server_url": MCP_SERVER_URL,
                "protocols_count": len(protocols),
                "total_urls": total_urls,
                "protocols": protocols
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n✓ Результаты сохранены в: {output_file}")
        
        # Показываем первые несколько протоколов
        print(f"\nПервые 3 протокола:")
        for i, (purchase_number, doc_info) in enumerate(list(protocols.items())[:3], 1):
            print(f"  {i}. {purchase_number}:")
            if isinstance(doc_info, dict):
                print(f"     URL: {doc_info.get('url', 'N/A')[:60]}...")
                print(f"     File: {doc_info.get('fileName', 'N/A')}")
            elif isinstance(doc_info, list):
                print(f"     Документов: {len(doc_info)}")
                for j, doc in enumerate(doc_info[:2], 1):
                    print(f"       {j}. {doc.get('url', 'N/A')[:60]}...")
        
        print(f"\n" + "=" * 60)
        print("Тестирование завершено успешно!")
        print("=" * 60)
        print(f"\nДля скачивания документов используйте:")
        print(f"  python3 test_download_documents.py {output_file} input/test_downloads 500")
        
    except Exception as e:
        print(f"\n✗ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()


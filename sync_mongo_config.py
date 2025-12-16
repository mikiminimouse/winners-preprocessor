#!/usr/bin/env python3
"""
Скрипт для синхронизации переменных MongoDB между MCP сервером и router.
Если указан mongoServer, использует его значение для MONGO_SERVER.
"""
import os
import re
from pathlib import Path
from dotenv import load_dotenv

def sync_mongo_config():
    """Синхронизирует переменные MongoDB в .env файле."""
    env_file = Path(".env")
    
    if not env_file.exists():
        print("ОШИБКА: Файл .env не найден")
        return False
    
    # Читаем .env файл
    with open(env_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Загружаем переменные для проверки
    load_dotenv()
    mongo_server_mcp = os.getenv("mongoServer")
    mongo_server_router = os.getenv("MONGO_SERVER")
    
    # Если mongoServer указан, а MONGO_SERVER нет - синхронизируем
    if mongo_server_mcp and not mongo_server_router:
        print(f"Синхронизация: используем mongoServer={mongo_server_mcp} для MONGO_SERVER")
        # Заменяем пустое значение MONGO_SERVER на значение mongoServer
        content = re.sub(
            r'^MONGO_SERVER=\s*$',
            f'MONGO_SERVER={mongo_server_mcp}',
            content,
            flags=re.MULTILINE
        )
        
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✓ MONGO_SERVER обновлен")
        return True
    elif mongo_server_router and not mongo_server_mcp:
        print(f"Синхронизация: используем MONGO_SERVER={mongo_server_router} для mongoServer")
        # Заменяем пустое значение mongoServer на значение MONGO_SERVER
        content = re.sub(
            r'^mongoServer=\s*$',
            f'mongoServer={mongo_server_router}',
            content,
            flags=re.MULTILINE
        )
        
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✓ mongoServer обновлен")
        return True
    elif mongo_server_mcp and mongo_server_router:
        if mongo_server_mcp != mongo_server_router:
            print(f"⚠️  ВНИМАНИЕ: Разные значения!")
            print(f"   mongoServer={mongo_server_mcp}")
            print(f"   MONGO_SERVER={mongo_server_router}")
            print("   Используются оба значения как есть")
        else:
            print(f"✓ Оба значения синхронизированы: {mongo_server_mcp}")
        return True
    else:
        print("⚠️  Адрес MongoDB сервера не указан ни в mongoServer, ни в MONGO_SERVER")
        print("   Укажите адрес в .env файле:")
        print("   mongoServer=host:port")
        print("   или")
        print("   MONGO_SERVER=host:port")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Синхронизация конфигурации MongoDB")
    print("=" * 60)
    print()
    sync_mongo_config()
    print()
    print("=" * 60)


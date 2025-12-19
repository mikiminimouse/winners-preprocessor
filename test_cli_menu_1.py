#!/usr/bin/env python3
"""
Скрипт для тестирования пункта меню 1 (sync_db) в CLI.
Симулирует выбор пункта 1 с тестовыми данными.
"""

import sys
import os
from pathlib import Path

# Добавляем пути
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "preprocessing"))

def test_menu_item_1():
    """Тестирование пункта меню 1 через прямой вызов."""
    print("🧪 ТЕСТИРОВАНИЕ ПУНКТА МЕНЮ 1: СИНХРОНИЗАЦИЯ ПРОТОКОЛОВ")
    print("=" * 60)

    # Импортируем функцию обработки
    from preprocessing.cli.handlers.load_handlers import handle_sync_protocols

    # Создаем mock CLI instance
    class MockCLI:
        pass

    cli_instance = MockCLI()

    # Имитируем пользовательский ввод через monkey patch
    import builtins
    original_input = builtins.input

    # Сценарий ввода: 1 (вчера) + Enter + 3 (лимит) + Enter
    inputs = iter(["1", "3"])

    def mock_input(prompt=""):
        try:
            value = next(inputs)
            print(f"📝 Ввод: {value} (на запрос: {prompt.strip()[:50]}...)")
            return value
        except StopIteration:
            print("❌ Недостаточно предопределенных вводов!")
            return "0"  # Выход

    # Заменяем input
    builtins.input = mock_input

    try:
        print("🚀 Запуск handle_sync_protocols...")
        print("Сценарий: вчерашний день, лимит 3 протокола")
        print()

        # Вызываем функцию
        handle_sync_protocols(cli_instance)

        print("\n✅ Тестирование завершено!")

    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Восстанавливаем оригинальный input
        builtins.input = original_input

if __name__ == "__main__":
    test_menu_item_1()

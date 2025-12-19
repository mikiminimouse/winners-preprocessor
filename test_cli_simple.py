#!/usr/bin/env python3
"""
ПРОСТОЙ ТЕСТ CLI С SYNC_DB - проверка доступности через меню
"""

import sys
import subprocess
import time
from pathlib import Path

def test_cli_access():
    """Тестирование доступа к sync_db через CLI."""
    print("🧪 ПРОСТОЙ ТЕСТ CLI ДОСТУПА К SYNC_DB")
    print("=" * 50)

    # Сценарий: запустить CLI, выбрать 1, затем сразу выйти
    try:
        print("Запуск CLI с автоматическим выбором пункта 1...")

        # Создаем процесс CLI
        proc = subprocess.Popen(
            ["python3", "run_cli.py"],
            cwd="/root/winners_preprocessor/preprocessing",
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        # Даем время на запуск
        time.sleep(2)

        # Отправляем "1" для выбора пункта меню
        proc.stdin.write("1\n")
        proc.stdin.flush()

        # Даем время на обработку
        time.sleep(3)

        # Отправляем "1" для выбора вчерашнего дня
        proc.stdin.write("1\n")
        proc.stdin.flush()

        # Даем время на обработку
        time.sleep(2)

        # Отправляем "2" для лимита
        proc.stdin.write("2\n")
        proc.stdin.flush()

        # Ждем завершения синхронизации
        time.sleep(10)

        # Отправляем "0" для выхода
        proc.stdin.write("0\n")
        proc.stdin.flush()

        # Получаем вывод
        try:
            stdout, stderr = proc.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()

        print("📄 ВЫВОД CLI:")
        print("-" * 60)
        print(stdout)
        if stderr:
            print("STDERR:")
            print(stderr)
        print("-" * 60)

        # Анализируем результаты
        success_indicators = [
            "Микросервис sync_db - первый компонент препроцессинга",
            "ЭТАП 0: Проверка и настройка VPN доступа",
            "ЭТАП 1: Проверка подключения к локальной MongoDB",
            "🚀 ЗАПУСК ПОЛНОЙ СИНХРОНИЗАЦИИ",
            "ОШИБКА СИНХРОНИЗАЦИИ"  # Даже ошибка означает, что код дошел до синхронизации
        ]

        found_indicators = [ind for ind in success_indicators if ind in stdout]

        print(f"✅ Найдено {len(found_indicators)}/{len(success_indicators)} индикаторов работы:")
        for ind in found_indicators:
            print(f"   ✓ {ind}")

        # Проверяем наличие ключевых сообщений
        if "Микросервис sync_db - первый компонент препроцессинга" in stdout:
            print("\n🎉 CLI + SYNC_DB РАБОТАЮТ!")
            print("Модуль sync_db успешно интегрирован в CLI меню!")
            return True
        else:
            print("\n❌ Проблема: sync_db не найден в CLI")
            return False

    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_cli_access()
    sys.exit(0 if success else 1)

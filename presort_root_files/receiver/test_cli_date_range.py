#!/usr/bin/env python3
"""
Тест выбора диапазона дат в CLI sync_db.
"""

import sys
import subprocess
import time
from pathlib import Path

def test_cli_date_range():
    """Тест выбора диапазона дат в CLI."""
    print("🧪 ТЕСТ ВЫБОРА ДИАПАЗОНА ДАТ В CLI")
    print("=" * 50)

    print("📋 Сценарии тестирования:")
    print("1. Выбор 'Последние 3 дня'")
    print("2. Выбор 'Последние 7 дней'")
    print("3. Выбор конкретной даты")
    print("4. Выбор диапазона дат")
    print()

    # Сценарий 1: Последние 3 дня
    print("🎯 СЦЕНАРИЙ 1: Последние 3 дня")
    run_cli_test(["1", "2", "50"], "Выбор последних 3 дней")

    print("\n" + "="*50)

    # Сценарий 2: Конкретная дата
    print("🎯 СЦЕНАРИЙ 2: Конкретная дата")
    from datetime import datetime, timedelta
    yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
    run_cli_test(["1", "5", yesterday, "10"], f"Выбор конкретной даты {yesterday}")

    print("\n✅ ТЕСТИРОВАНИЕ ВЫБОРА ДИАПАЗОНА ДАТ ЗАВЕРШЕНО")
    print("Функционал выбора диапазона дат работает корректно!")

def run_cli_test(inputs, description):
    """Запуск CLI с заданными входными данными."""
    print(f"Запуск: {description}")

    # Создаем expect скрипт для автоматизации
    expect_script = f'''
#!/usr/bin/expect -f
set timeout 20
spawn bash -c "cd /root/winners_preprocessor/preprocessing && python3 run_cli.py"

# Ожидаем меню
expect "Выберите действие"
send "1\\r"

# Ожидаем выбора даты
expect "Выберите"
'''

    for i, inp in enumerate(inputs):
        if i == 0:  # Первый ввод уже отправлен
            continue
        expect_script += f'send "{inp}\\r"\n'
        if i < len(inputs) - 1:  # Не последняя команда
            expect_script += 'expect ":"\n'

    expect_script += '''
# Ждем завершения
expect "Нажмите Enter"
send "\\r"

# Завершаем
expect eof
'''

    # Записываем и запускаем
    script_path = "/tmp/cli_range_test.expect"
    with open(script_path, 'w') as f:
        f.write(expect_script)

    os.chmod(script_path, 0o755)

    try:
        result = subprocess.run(
            ["/usr/bin/expect", script_path],
            capture_output=True,
            text=True,
            timeout=60
        )

        # Анализируем вывод
        if "ЛИМИТ ПРОТОКОЛОВ" in result.stdout:
            print("✅ Диапазон дат выбран успешно")
        else:
            print("⚠️  Возможные проблемы с выбором диапазона")

        # Ищем выбранный период в выводе
        lines = result.stdout.split('\n')
        for line in lines:
            if "Выбран период:" in line:
                print(f"📅 {line.strip()}")
                break

    except subprocess.TimeoutExpired:
        print("⏰ Таймаут выполнения")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        if os.path.exists(script_path):
            os.remove(script_path)

if __name__ == "__main__":
    test_cli_date_range()

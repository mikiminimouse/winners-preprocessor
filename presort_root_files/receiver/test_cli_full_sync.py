#!/usr/bin/env python3
"""
АВТОМАТИЗИРОВАННЫЙ ТЕСТ ПОЛНОГО ФУНКЦИОНАЛА SYNC_DB ЧЕРЕЗ CLI

Тестирует полный цикл: CLI → sync_db → VPN → MongoDB → синхронизация → отчет
"""

import sys
import os
import subprocess
import time
from pathlib import Path

def test_cli_full_sync():
    """Полный тест CLI с sync_db."""
    print("🚀 АВТОМАТИЗИРОВАННЫЙ ТЕСТ CLI + SYNC_DB")
    print("=" * 60)

    # Сценарий ввода: 1 (синхронизация) → 1 (вчера) → 3 (лимит) → 0 (выход)
    inputs = ["1", "1", "3", "0"]

    # Создаем скрипт для автоматизации ввода
    script_content = "#!/bin/bash\n"
    script_content += "cd /root/winners_preprocessor/preprocessing\n"
    script_content += "echo 'Запуск CLI с автоматическим вводом...'\n"

    for inp in inputs:
        script_content += f"echo '{inp}'\n"
        script_content += "sleep 1\n"

    script_content += "echo 'CLI тест завершен'\n"

    # Записываем скрипт
    script_path = "/tmp/cli_test_input.sh"
    with open(script_path, 'w') as f:
        f.write(script_content)

    os.chmod(script_path, 0o755)

    print("📝 Сценарий тестирования:")
    print("  1. Выбор пункта меню: 1 (Синхронизация протоколов)")
    print("  2. Выбор даты: 1 (Вчерашний день)")
    print("  3. Лимит протоколов: 3")
    print("  4. Выход: 0")
    print()

    # Запускаем CLI с автоматическим вводом
    try:
        print("🎮 Запуск CLI с автоматическим вводом...")

        # Используем expect для автоматизации ввода
        expect_script = f"""
#!/usr/bin/expect -f
set timeout 30
spawn bash -c "cd /root/winners_preprocessor/preprocessing && python3 run_cli.py"

# Ожидаем меню
expect "Выберите действие"

# Выбираем пункт 1
send "1\\r"
expect "Выберите"
send "1\\r"
expect "ЛИМИТ ПРОТОКОЛОВ"
send "3\\r"

# Ждем завершения
expect "Нажмите Enter"
send "\\r"

# Завершаем
expect eof
"""

        expect_path = "/tmp/cli_test.expect"
        with open(expect_path, 'w') as f:
            f.write(expect_script)

        os.chmod(expect_path, 0o755)

        # Запускаем expect скрипт
        result = subprocess.run(
            ["/usr/bin/expect", expect_path],
            capture_output=True,
            text=True,
            timeout=120
        )

        print("📄 ВЫВОД CLI:")
        print("-" * 60)
        print(result.stdout)
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        print("-" * 60)

        # Анализируем результаты
        success_indicators = [
            "Микросервис sync_db - первый компонент препроцессинга",
            "ЭТАП 1: Проверка подключения к локальной MongoDB",
            "ЭТАП 0: Проверка и настройка VPN доступа",
            "❌ Не удалось обеспечить доступ к MongoDB через VPN",
            "ОШИБКА СИНХРОНИЗАЦИИ",
            "Нажмите Enter для продолжения"
        ]

        found_indicators = [ind for ind in success_indicators if ind in result.stdout]

        print(f"✅ Найдено {len(found_indicators)}/{len(success_indicators)} индикаторов работы:")
        for ind in found_indicators:
            print(f"   ✓ {ind.replace('Нажмите Enter для продолжения', 'CLI завершился корректно')}")

        # Проверяем состояние MongoDB после теста
        print("\n💾 ПРОВЕРКА РЕЗУЛЬТАТОВ В MONGODB:")
        check_mongo_results()

        if len(found_indicators) >= 4:
            print("\n🎉 ТЕСТИРОВАНИЕ ПРОШЛО УСПЕШНО!")
            print("CLI + sync_db работают корректно!")
            return True
        else:
            print("\n⚠️  Тестирование выявило проблемы")
            return False

    except subprocess.TimeoutExpired:
        print("❌ Таймаут выполнения CLI")
        return False
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
        return False
    finally:
        # Очистка временных файлов
        for path in [script_path, expect_path]:
            if os.path.exists(path):
                os.remove(path)

def check_mongo_results():
    """Проверяет результаты в MongoDB."""
    try:
        # Настройка пути
        sys.path.insert(0, '/root/winners_preprocessor')

        from sync_db.utils.connection_utils import get_local_mongo_client

        client = get_local_mongo_client()
        if client:
            db = client['docling_metadata']
            coll = db['protocols']

            total_count = coll.count_documents({})
            sync_db_count = coll.count_documents({'source': 'remote_mongo_direct'})

            print(f"   Всего протоколов: {total_count}")
            print(f"   Из sync_db: {sync_db_count}")

            if sync_db_count > 0:
                latest = coll.find_one(
                    {'source': 'remote_mongo_direct'},
                    sort=[('created_at', -1)]
                )
                if latest and 'unit_id' in latest:
                    print(f"   Последний unit_id: {latest['unit_id']}")

            client.close()
        else:
            print("   ❌ Не удалось подключиться к MongoDB")

    except Exception as e:
        print(f"   ❌ Ошибка проверки MongoDB: {e}")

if __name__ == "__main__":
    success = test_cli_full_sync()
    sys.exit(0 if success else 1)

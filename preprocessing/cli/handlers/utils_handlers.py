"""
Handlers для служебных функций (пункты меню 25-27).

Включает функции:
- handle_cleanup_test_data: очистка данных
- handle_create_test_files: создание тестовых файлов
- handle_check_infrastructure: проверка инфраструктуры
"""
from .monitor_handlers import handle_check_mongodb


def handle_cleanup_test_data(cli_instance):
    """Очистка тестовых данных."""
    print("\n=== ОЧИСТКА ТЕСТОВЫХ ДАННЫХ ===")

    dirs_to_clean = [cli_instance.TEMP_DIR, cli_instance.EXTRACTED_DIR, cli_instance.NORMALIZED_DIR, cli_instance.ARCHIVE_DIR]

    for directory in dirs_to_clean:
        if directory.exists():
            print(f"🧹 Очистка {directory}...")
            for item in directory.glob("*"):
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    import shutil
                    shutil.rmtree(item)
            print(f"   ✅ Очищено")

    print("🎉 Очистка завершена")


def handle_create_test_files(cli_instance):
    """Создание тестовых файлов."""
    print("\n=== СОЗДАНИЕ ТЕСТОВЫХ ФАЙЛОВ ===")

    # Создаем простой текстовый файл
    test_file = cli_instance.INPUT_DIR / "test_document.txt"
    test_file.write_text("Это тестовый документ для проверки препроцессинга.")

    # Создаем простой PDF (если возможно)
    print("📄 Создан тестовый файл: test_document.txt")

    print("✅ Тестовые файлы созданы")


def handle_check_infrastructure(cli_instance):
    """Проверка инфраструктуры."""
    print("\n=== ПРОВЕРКА ИНФРАСТРУКТУРЫ ===")

    # Проверка директорий
    dirs_to_check = [
        ("INPUT_DIR", cli_instance.INPUT_DIR),
        ("TEMP_DIR", cli_instance.TEMP_DIR),
        ("OUTPUT_DIR", cli_instance.OUTPUT_DIR),
        ("EXTRACTED_DIR", cli_instance.EXTRACTED_DIR),
        ("NORMALIZED_DIR", cli_instance.NORMALIZED_DIR),
        ("ARCHIVE_DIR", cli_instance.ARCHIVE_DIR),
    ]

    print("📁 Проверка директорий:")
    for name, directory in dirs_to_check:
        if directory.exists():
            print(f"  ✅ {name}: {directory}")
        else:
            print(f"  ❌ {name}: не существует")
            try:
                directory.mkdir(parents=True, exist_ok=True)
                print(f"     📁 Создана: {directory}")
            except Exception as e:
                print(f"     ❌ Ошибка создания: {e}")

    # Проверка MongoDB
    print("\n" + "="*40)
    handle_check_mongodb(cli_instance)

    print("\n🎯 Инфраструктура проверена")

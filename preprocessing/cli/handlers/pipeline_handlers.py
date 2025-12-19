"""
Handlers для полного тестирования pipeline (пункты меню 20-21).

Включает функции:
- handle_full_pipeline_test: полный тест pipeline
- handle_integration_test: интеграционный тест API
"""

import requests


def handle_full_pipeline_test(cli_instance):
    """Полный тест всего pipeline."""
    print("\n=== ПОЛНЫЙ ТЕСТ PIPELINE ===")

    # Инициализируем метрики сессии
    cli_instance.metrics = cli_instance.init_processing_metrics()
    cli_instance.session_id = cli_instance.metrics["session_id"]

    print(f"🎯 Запуск полной сессии тестирования: {cli_instance.session_id}")

    # Этап 1: Проверка входных данных
    print("\n📋 ЭТАП 1: Проверка входных данных...")
    from .load_handlers import handle_check_input_files
    handle_check_input_files(cli_instance)

    # Этап 2: Определение типов
    print("\n🔍 ЭТАП 2: Определение типов файлов...")
    from .test_handlers import handle_test_file_type_detection
    handle_test_file_type_detection(cli_instance)

    # Этап 3: Распаковка архивов
    print("\n📦 ЭТАП 3: Распаковка архивов...")
    from .test_handlers import handle_test_archive_extraction
    handle_test_archive_extraction(cli_instance)

    # Этап 4: Нормализация
    print("\n🔄 ЭТАП 4: Нормализация unit'ов...")
    from .test_handlers import handle_test_normalization
    handle_test_normalization(cli_instance)

    # Этап 5: Создание manifest'ов
    print("\n📋 ЭТАП 5: Создание manifest'ов...")
    from .test_handlers import handle_test_manifest_creation
    handle_test_manifest_creation(cli_instance)

    # Этап 6: Docling обработка
    print("\n🤖 ЭТАП 6: Docling обработка...")
    from .test_handlers import handle_test_docling_processing
    handle_test_docling_processing(cli_instance)

    # Сохранение метрик
    if cli_instance.metrics:
        cli_instance.save_processing_metrics(cli_instance.metrics)

    print("\n🎉 ПОЛНЫЙ ТЕСТ ЗАВЕРШЕН!")
    print(f"📊 Session ID: {cli_instance.session_id}")


def handle_integration_test(cli_instance):
    """Интеграционный тест Router API."""
    print("\n=== ИНТЕГРАЦИОННЫЙ ТЕСТ ROUTER API ===")

    # Проверяем доступность router
    router_url = "http://router:8080/health"
    try:
        response = requests.get(router_url, timeout=5)
        if response.status_code == 200:
            print("✅ Router API доступен")
        else:
            print(f"⚠️  Router API вернул код {response.status_code}")
    except Exception as e:
        print(f"❌ Router API недоступен: {e}")
        print("💡 Убедитесь, что docker-compose запущен")
        return

    # Проверяем доступность Docling
    docling_url = cli_instance.DOCLING_API.replace("/process", "/health")
    try:
        response = requests.get(docling_url, timeout=5)
        if response.status_code == 200:
            print("✅ Docling API доступен")
        else:
            print(f"⚠️  Docling API вернул код {response.status_code}")
    except Exception as e:
        print(f"❌ Docling API недоступен: {e}")

    # Тест process_now endpoint
    print("\n🧪 Тестирование /process_now endpoint...")
    try:
        response = requests.post("http://router:8080/process_now", timeout=30)
        if response.status_code == 200:
            result = response.json()
            print("✅ process_now выполнен успешно")
            print(f"   Обработано файлов: {result.get('processed_count', 0)}")
            print(f"   Session ID: {result.get('session_id', 'N/A')}")
        else:
            print(f"❌ process_now вернул код {response.status_code}")
    except Exception as e:
        print(f"❌ Ошибка тестирования process_now: {e}")

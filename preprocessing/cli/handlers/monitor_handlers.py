"""
Handlers для мониторинга и статистики (пункты меню 22-24).

Включает функции:
- handle_view_metrics: просмотр метрик
- handle_view_logs: просмотр логов
- handle_check_mongodb: проверка MongoDB
"""


def handle_view_metrics(cli_instance):
    """Просмотр текущих метрик сессии."""
    print("\n=== ТЕКУЩИЕ МЕТРИКИ СЕССИИ ===")

    if not cli_instance.metrics:
        print("❌ Метрики сессии не инициализированы")
        print("💡 Запустите полный тест или инициализируйте метрики")
        return

    print(f"📊 Session ID: {cli_instance.metrics['session_id']}")
    print(f"🕐 Started: {cli_instance.metrics['started_at']}")
    print(f"🏁 Completed: {cli_instance.metrics.get('completed_at', 'In progress')}")

    summary = cli_instance.metrics.get("summary", {})
    print("\n📈 Summary:")
    print(f"   Input files: {summary.get('total_input_files', 0)}")
    print(f"   Archives: {summary.get('total_archives', 0)}")
    print(f"   Extracted: {summary.get('total_extracted', 0)}")
    print(f"   Units: {summary.get('total_units', 0)}")
    print(f"   Errors: {summary.get('total_errors', 0)}")


def handle_view_logs(cli_instance):
    """Просмотр логов обработки."""
    print("\n=== ЛОГИ ОБРАБОТКИ ===")

    # Проверяем логи в metrics
    if cli_instance.metrics:
        errors = cli_instance.metrics.get("errors", [])
        if errors:
            print("❌ Ошибки обработки:")
            for error in errors[-5:]:  # Последние 5 ошибок
                print(f"   {error['timestamp']}: {error['error']}")
        else:
            print("✅ Ошибок не найдено")

    # Предлагаем проверить логи контейнеров
    print("\n💡 Для просмотра полных логов используйте:")
    print("   docker-compose logs -f router")
    print("   docker-compose logs -f scheduler")
    print("   docker-compose logs -f docling")


def handle_check_mongodb(cli_instance):
    """Проверка MongoDB подключений."""
    print("\n=== ПРОВЕРКА MONGODB ПОДКЛЮЧЕНИЙ ===")

    # Проверка подключения к protocols MongoDB
    print("🔗 Проверка MongoDB для протоколов...")
    client = cli_instance.get_mongo_client()
    if client:
        try:
            client.admin.command('ping')
            print("✅ Protocols MongoDB: подключено")
        except Exception as e:
            print(f"❌ Protocols MongoDB: ошибка {e}")
    else:
        print("❌ Protocols MongoDB: не настроена")

    # Проверка подключения к metadata MongoDB
    print("🔗 Проверка MongoDB для метаданных...")
    client = cli_instance.get_mongo_metadata_client()
    if client:
        try:
            client.admin.command('ping')
            print("✅ Metadata MongoDB: подключено")
        except Exception as e:
            print(f"❌ Metadata MongoDB: ошибка {e}")
    else:
        print("❌ Metadata MongoDB: не настроена")

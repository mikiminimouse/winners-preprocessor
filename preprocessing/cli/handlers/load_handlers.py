"""
Handlers для загрузки и подготовки данных (пункты меню 1-3).

Включает функции:
- handle_sync_protocols: синхронизация протоколов из MongoDB
- handle_download_protocols: скачивание протоколов через VPN
- handle_check_input_files: проверка файлов в INPUT_DIR
"""

from datetime import datetime, timedelta
try:
    from ..utils import sanitize_filename
except ImportError:
    # Fallback для случаев когда импорт не работает
    def sanitize_filename(name: str) -> str:
        return name.replace('/', '_').replace('\\', '_')


def handle_sync_protocols(cli_instance):
    """Синхронизация протоколов из удалённой MongoDB в локальную."""
    print("\n=== СИНХРОНИЗАЦИЯ ПРОТОКОЛОВ ИЗ УДАЛЁННОЙ MONGODB ===")
    print("Микросервис sync_db - первый компонент препроцессинга")

    # Импорт нового микросервиса синхронизации
    try:
        from sync_db.service import SyncService
    except ImportError:
        print("❌ Модуль sync_microservice не найден. Убедитесь, что PYTHONPATH настроен корректно")
        return

    # Создаем сервис синхронизации
    try:
        sync_service = SyncService()
    except Exception as e:
        print(f"❌ Ошибка создания сервиса синхронизации: {e}")
        return

    # Выбор типа синхронизации
    print("\n📅 ВЫБОР ТИПА СИНХРОНИЗАЦИИ:")
    print("  1. Одна дата (по умолчанию)")
    print("  2. Диапазон дат (начало - конец)")
    print("  3. Начальная дата + количество дней")
    sync_type = input("  Выберите [1-3] или Enter для одной даты: ").strip() or "1"

    # Переменные для хранения дат
    target_date = None
    start_date = None
    end_date = None

    if sync_type == "1":
        # Одна дата
        print("\n📅 ВЫБОР ДАТЫ ДЛЯ СИНХРОНИЗАЦИИ:")
        print("  1. Вчерашний день (по умолчанию)")
        print("  2. Указать дату вручную (YYYY-MM-DD)")
        choice = input("  Выберите [1-2] или Enter для вчерашнего дня: ").strip()

        if choice == "2":
            date_str = input("  Введите дату (YYYY-MM-DD): ").strip()
            try:
                target_date = datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                print(f"✗ Неверный формат даты: {date_str}")
                return
        else:
            target_date = datetime.utcnow() - timedelta(days=1)
    elif sync_type == "2":
        # Диапазон дат
        print("\n📅 ВВОД ДИАПАЗОНА ДАТ:")
        start_str = input("  Введите начальную дату (YYYY-MM-DD): ").strip()
        end_str = input("  Введите конечную дату (YYYY-MM-DD): ").strip()
        
        try:
            start_date = datetime.strptime(start_str, "%Y-%m-%d")
            end_date = datetime.strptime(end_str, "%Y-%m-%d")
            
            if start_date > end_date:
                print("✗ Начальная дата должна быть меньше или равна конечной")
                return
        except ValueError as e:
            print(f"✗ Неверный формат даты: {e}")
            return
    elif sync_type == "3":
        # Начальная дата + количество дней
        print("\n📅 ВВОД НАЧАЛЬНОЙ ДАТЫ И КОЛИЧЕСТВА ДНЕЙ:")
        start_str = input("  Введите начальную дату (YYYY-MM-DD): ").strip()
        days_str = input("  Введите количество дней: ").strip()
        
        try:
            start_date = datetime.strptime(start_str, "%Y-%m-%d")
            days = int(days_str)
            if days <= 0:
                print("✗ Количество дней должно быть больше 0")
                return
            end_date = start_date + timedelta(days=days-1)
        except ValueError as e:
            print(f"✗ Ошибка ввода: {e}")
            return
    else:
        print("✗ Неверный выбор типа синхронизации")
        return

    # Лимит протоколов
    limit_str = input(f"\n🔢 ЛИМИТ ПРОТОКОЛОВ (по умолчанию: 200): ").strip()
    limit = int(limit_str) if limit_str else 200

    # Запуск полной синхронизации (5 этапов)
    print(f"\n🚀 ЗАПУСК ПОЛНОЙ СИНХРОНИЗАЦИИ:")
    if target_date:
        print(f"   Дата: {target_date.date()}")
    else:
        print(f"   Период: {start_date.date()} - {end_date.date()}")
    print(f"   Лимит: {limit}")
    print(f"   Микросервис: sync_db")

    # Выполняем синхронизацию
    if target_date:
        result = sync_service.sync_protocols_for_date(target_date, limit)
    else:
        result = sync_service.sync_protocols_for_date_range(start_date, end_date, limit)

    # Вывод результатов
    if result.success:
        print("\n✅ СИНХРОНИЗАЦИЯ ЗАВЕРШЕНА УСПЕШНО!")
        print("📊 РЕЗУЛЬТАТЫ:")
        print(f"   📅 Дата/Период: {result.date}")
        print(f"   🔍 Просмотрено документов: {result.scanned}")
        print(f"   💾 Новых протоколов: {result.inserted}")
        print(f"   ⏭️  Пропущено дубликатов: {result.skipped_existing}")
        print(f"   ⚠️  Ошибок обработки: {result.errors_count}")
        print(f"   ⏱️  Длительность: {result.duration:.2f} секунд")
        if result.errors_count > 0:
            print("   📝 Подробности ошибок:")
            for i, error in enumerate(result.errors[:3], 1):
                print(f"     {i}. {error[:100]}{'...' if len(error) > 100 else ''}")
            if len(result.errors) > 3:
                print(f"     ... и еще {len(result.errors) - 3} ошибок")
    else:
        print(f"\n❌ ОШИБКА СИНХРОНИЗАЦИИ: {result.message}")
        if hasattr(result, 'errors') and result.errors:
            print("   Подробности:")
            for error in result.errors[:3]:
                print(f"   • {error}")


def handle_download_protocols(cli_instance):
    """Скачивание протоколов из локальной MongoDB через VPN."""
    print("\n=== СКАЧИВАНИЕ ПРОТОКОЛОВ ИЗ MONGODB (С VPN) ===")

    # Проверяем доступность модулей скачивания
    try:
        from downloader.service import ProtocolDownloader
        from downloader.utils import check_zakupki_health
    except ImportError:
        print("❌ Модули скачивания не доступны")
        return

    # Проверка VPN подключения
    print("\n1. Проверка доступности zakupki.gov.ru через VPN...")
    if not check_zakupki_health():
        print("✗ zakupki.gov.ru недоступен (нет VPN / блокировка)")
        print("  Убедитесь, что VPN настроен через route-up-zakupki.sh")
        print("  Проверьте, что OpenVPN туннель активен")
        return

    print("✓ zakupki.gov.ru доступен через VPN")

    # Запрос лимита
    limit_str = input(f"\n2. Лимит протоколов/units для скачивания (по умолчанию: 200): ").strip()
    limit = int(limit_str) if limit_str else 200

    if limit <= 0:
        print("✗ Лимит должен быть больше 0")
        return

    # Запуск скачивания
    print(f"\n3. Запуск скачивания протоколов...")
    print(f"   Лимит: {limit} протоколов")
    print(f"   Директория: {cli_instance.INPUT_DIR.absolute()}")

    try:
        downloader = ProtocolDownloader(output_dir=cli_instance.INPUT_DIR)
        start_time = cli_instance.time.time()
        result = downloader.process_pending_protocols(limit=limit)
        duration = cli_instance.time.time() - start_time

        print("\n✓ Скачивание завершено!")
        print(f"   Время: {duration:.1f} сек")
        print(f"   Протоколы обработано: {result.get('processed', 0)}")
        print(f"   Документы скачано: {result.get('downloaded', 0)}")
        print(f"   Ошибок: {result.get('failed', 0)}")

    except Exception as e:
        print(f"❌ Ошибка скачивания: {e}")


def handle_check_input_files(cli_instance):
    """Проверка файлов в INPUT_DIR."""
    print("\n=== ПРОВЕРКА INPUT_DIR ===")

    if not cli_instance.INPUT_DIR.exists():
        print(f"❌ Директория {cli_instance.INPUT_DIR} не существует")
        return

    files = [f for f in cli_instance.INPUT_DIR.rglob("*") if f.is_file()]
    files = [f for f in files if f.is_file() and not f.name.startswith('.')]

    print(f"📁 Найдено файлов: {len(files)}")

    if files:
        print("\nФайлы:")
        for i, file_path in enumerate(files[:10], 1):  # Показываем первые 10
            size_mb = file_path.stat().st_size / (1024 * 1024)
            print(".1f")

        if len(files) > 10:
            print(f"... и еще {len(files) - 10} файлов")
    else:
        print("📭 INPUT_DIR пуст")

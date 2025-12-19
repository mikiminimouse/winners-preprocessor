"""
Handlers для тестирования этапов препроцессинга (пункты меню 4-8).

Включает функции:
- handle_test_file_type_detection: тест определения типов файлов
- handle_test_archive_extraction: тест распаковки архивов
- handle_test_normalization: тест нормализации units
- handle_test_manifest_creation: тест создания manifest'ов
- handle_test_docling_processing: тест Docling обработки
"""


def handle_test_file_type_detection(cli_instance):
    """Тест определения типа файла."""
    print("\n=== ТЕСТ: ОПРЕДЕЛЕНИЕ ТИПА ФАЙЛА ===")

    files = [f for f in cli_instance.INPUT_DIR.rglob("*") if f.is_file()]
    files = [f for f in files if f.is_file() and not f.name.startswith('.')]

    if not files:
        print("❌ Нет файлов в INPUT_DIR для тестирования")
        return

    # Импортируем функцию определения типа
    from main import detect_file_type

    print(f"🧪 Тестирование на {len(files)} файлах...")

    results = {}
    for file_path in files[:5]:  # Тестируем первые 5 файлов
        print(f"\n📄 {file_path.name}:")
        try:
            detection = detect_file_type(file_path)
            detected_type = detection.get("detected_type", "unknown")
            mime_type = detection.get("mime_type", "")
            needs_ocr = detection.get("needs_ocr", False)
            is_archive = detection.get("is_archive", False)

            print(f"  Тип: {detected_type}")
            print(f"  MIME: {mime_type}")
            print(f"  OCR нужен: {needs_ocr}")
            print(f"  Архив: {is_archive}")

            results[detected_type] = results.get(detected_type, 0) + 1

        except Exception as e:
            print(f"  ❌ Ошибка: {e}")

    print("\n📊 Статистика по типам:")
    for file_type, count in results.items():
        print(f"  {file_type}: {count}")


def handle_test_archive_extraction(cli_instance):
    """Тест распаковки архивов."""
    print("\n=== ТЕСТ: РАСПАКОВКА АРХИВОВ ===")

    files = [f for f in cli_instance.INPUT_DIR.rglob("*") if f.is_file()]
    archive_files = [f for f in files if f.is_file() and f.suffix.lower() in ['.zip', '.rar', '.7z']]

    if not archive_files:
        print("❌ Нет архивов в INPUT_DIR для тестирования")
        return

    from main import safe_extract_archive

    print(f"🧪 Тестирование распаковки {len(archive_files)} архивов...")

    for archive_path in archive_files:
        print(f"\n📦 {archive_path.name}:")

        extract_dir = cli_instance.EXTRACTED_DIR / f"test_{archive_path.stem}"
        extract_dir.mkdir(parents=True, exist_ok=True)

        try:
            extracted_files, success = safe_extract_archive(archive_path, extract_dir, "test")

            if success:
                print(f"  ✅ Распаковано файлов: {len(extracted_files)}")
                for ext_file in extracted_files[:3]:  # Показываем первые 3
                    print(f"    📄 {ext_file['original_name']}")
                if len(extracted_files) > 3:
                    print(f"    ... и еще {len(extracted_files) - 3} файлов")
            else:
                print("  ❌ Ошибка распаковки")

        except Exception as e:
            print(f"  ❌ Ошибка: {e}")


def handle_test_normalization(cli_instance):
    """Тест нормализации unit'ов."""
    print("\n=== ТЕСТ: НОРМАЛИЗАЦИЯ UNIT'ОВ ===")

    files = [f for f in cli_instance.INPUT_DIR.rglob("*") if f.is_file()]
    files = [f for f in files if f.is_file() and not f.name.startswith('.')]

    if not files:
        print("❌ Нет файлов в INPUT_DIR для тестирования")
        return

    print(f"🧪 Тестирование нормализации {len(files)} файлов...")

    # Импортируем функцию process_file
    from main import process_file

    processed = 0
    errors = 0

    for file_path in files[:3]:  # Тестируем первые 3 файла
        print(f"\n📄 Обработка {file_path.name}...")

        try:
            result = process_file(file_path, None)  # background_tasks = None для синхронной обработки

            if result.get("status") == "processed":
                print("  ✅ Обработано успешно")
                if "unit_id" in result:
                    print(f"    Unit ID: {result['unit_id']}")
                processed += 1
            else:
                print(f"  ❌ Ошибка: {result.get('message', 'Unknown error')}")
                errors += 1

        except Exception as e:
            print(f"  ❌ Ошибка: {e}")
            errors += 1

    print("\n📊 Результаты:")
    print(f"  ✅ Успешно: {processed}")
    print(f"  ❌ Ошибок: {errors}")


def handle_test_manifest_creation(cli_instance):
    """Тест создания manifest'ов."""
    print("\n=== ТЕСТ: СОЗДАНИЕ MANIFEST'ОВ ===")

    # Проверяем normalized units
    unit_dirs = [d for d in cli_instance.NORMALIZED_DIR.iterdir() if d.is_dir() and d.name.startswith("UNIT_")]

    if not unit_dirs:
        print("❌ Нет normalized units для тестирования manifest'ов")
        print("Сначала выполните нормализацию файлов")
        return

    print(f"🧪 Проверка manifest'ов в {len(unit_dirs)} units...")

    # Импортируем функции для работы с manifest
    from main import get_manifest_from_mongo

    manifests_found = 0
    manifests_valid = 0

    for unit_dir in unit_dirs[:5]:  # Проверяем первые 5
        unit_id = unit_dir.name
        print(f"\n📋 {unit_id}:")

        # Проверяем MongoDB manifest
        manifest = get_manifest_from_mongo(unit_id)

        if manifest:
            manifests_found += 1
            print("  ✅ Manifest найден в MongoDB")

            # Проверяем структуру
            required_fields = ["unit_id", "created_at", "processing", "files"]
            missing_fields = []

            for field in required_fields:
                if field not in manifest:
                    missing_fields.append(field)
                else:
                    if field == "unit_id":
                        print(f"    ✓ unit_id: {manifest[field]}")
                    elif field == "processing":
                        status = manifest.get("processing", {}).get("status", "unknown")
                        route = manifest.get("processing", {}).get("route", "unknown")
                        print(f"    ✓ status: {status}, route: {route}")
                    elif field == "files":
                        files_count = len(manifest.get("files", []))
                        print(f"    ✓ files: {files_count}")

            if missing_fields:
                print(f"  ⚠️  Отсутствующие поля: {', '.join(missing_fields)}")
            else:
                manifests_valid += 1
                print("    ✅ Структура manifest корректна")
        else:
            # Проверяем JSON файл
            manifest_path = unit_dir / "manifest.json"
            if manifest_path.exists():
                manifests_found += 1
                print("  ✅ Manifest найден в JSON файле")

                try:
                    with open(manifest_path, "r", encoding="utf-8") as f:
                        manifest = cli_instance.json.load(f)
                    manifests_valid += 1
                    print("    ✅ JSON валиден")
                except Exception as e:
                    print(f"    ❌ Ошибка чтения JSON: {e}")
            else:
                print("  ❌ Manifest не найден")

    print("\n📊 Результаты:")
    print(f"  📋 Manifest'ов найдено: {manifests_found}")
    print(f"  ✅ Валидных: {manifests_valid}")


def handle_test_docling_processing(cli_instance):
    """Тест Docling обработки."""
    print("\n=== ТЕСТ: DOCLING ОБРАБОТКА ===")

    # Проверяем normalized units
    unit_dirs = [d for d in cli_instance.NORMALIZED_DIR.iterdir() if d.is_dir() and d.name.startswith("UNIT_")]

    if not unit_dirs:
        print("❌ Нет normalized units для Docling обработки")
        print("Сначала выполните нормализацию файлов")
        return

    print(f"🧪 Отправка {len(unit_dirs)} units в Docling...")

    # Импортируем функцию trigger_docling
    from main import trigger_docling

    processed = 0
    errors = 0

    for unit_dir in unit_dirs[:3]:  # Тестируем первые 3
        unit_id = unit_dir.name
        print(f"\n🚀 Отправка {unit_id} в Docling...")

        try:
            trigger_docling(unit_id)
            processed += 1
            print("  ✅ Отправлено")

            # Небольшая пауза между отправками
            cli_instance.time.sleep(1)

        except Exception as e:
            print(f"  ❌ Ошибка: {e}")
            errors += 1

    print("\n📊 Результаты:")
    print(f"  🚀 Отправлено: {processed}")
    print(f"  ❌ Ошибок: {errors}")

    if processed > 0:
        print("\n💡 Проверьте логи Docling сервиса для результатов обработки")

"""
Handlers для расширенной статистики (пункты меню 15-17).

Включает функции:
- handle_view_pending_structure: просмотр структуры pending
- handle_category_statistics: статистика по категориям
- handle_units_report: отчет по units
"""


def handle_view_pending_structure(cli_instance):
    """Просмотр структуры pending директорий."""
    print("\n=== ПРОСМОТР СТРУКТУРЫ PENDING ДИРЕКТОРИЙ ===")

    pending_base = cli_instance.INPUT_DIR.parent / "pending"
    if not pending_base.exists():
        print("✗ Директория pending не существует")
        return

    print(f"📁 Базовая директория: {pending_base.absolute()}")

    categories = ["direct", "normalize", "convert", "extract", "special"]
    total_files = 0

    for category in categories:
        cat_dir = pending_base / category
        if cat_dir.exists():
            files = list(cat_dir.glob("*"))
            file_count = len([f for f in files if f.is_file()])
            dir_count = len([f for f in files if f.is_dir()])
            total_files += file_count

            print(f"\n📂 {category}/:")
            print(f"   Файлов: {file_count}")
            print(f"   Директорий: {dir_count}")

            if file_count > 0:
                print("   Примеры файлов:")
                for i, file_path in enumerate(files[:3]):
                    if file_path.is_file():
                        size = file_path.stat().st_size
                        print(f"     {i+1}. {file_path.name} ({size:,} bytes)")
        else:
            print(f"\n📂 {category}/: не существует")

    print(f"\n📊 Итого файлов во всех категориях: {total_files}")


def handle_category_statistics(cli_instance):
    """Детальная статистика по категориям."""
    print("\n=== ДЕТАЛЬНАЯ СТАТИСТИКА ПО КАТЕГОРИЯМ ===")

    pending_base = cli_instance.INPUT_DIR.parent / "pending"
    if not pending_base.exists():
        print("✗ Директория pending не существует")
        return

    categories = ["direct", "normalize", "convert", "extract", "special"]
    stats = {}

    for category in categories:
        cat_dir = pending_base / category
        if cat_dir.exists():
            files = list(cat_dir.glob("*"))
            files = [f for f in files if f.is_file()]

            # Статистика по типам файлов
            extensions = {}
            total_size = 0

            for file_path in files:
                ext = file_path.suffix.lower() or "no_ext"
                if ext not in extensions:
                    extensions[ext] = {"count": 0, "size": 0}
                extensions[ext]["count"] += 1
                extensions[ext]["size"] += file_path.stat().st_size
                total_size += file_path.stat().st_size

            stats[category] = {
                "file_count": len(files),
                "total_size": total_size,
                "extensions": extensions
            }

    # Вывод статистики
    for category, stat in stats.items():
        print(f"\n📊 Категория: {category}")
        print(f"   Всего файлов: {stat['file_count']}")
        print(f"   Общий размер: {stat['total_size']:,} bytes ({stat['total_size']/1024/1024:.1f} MB)")

        if stat["extensions"]:
            print("   По расширениям:")
            for ext, ext_stat in sorted(stat["extensions"].items()):
                avg_size = ext_stat["size"] / ext_stat["count"] if ext_stat["count"] > 0 else 0
                print(f"     {ext}: {ext_stat['count']} файлов, средний размер: {avg_size:,.0f} bytes")


def handle_units_report(cli_instance):
    """Отчет по обработанным units."""
    print("\n=== ОТЧЕТ ПО ОБРАБОТАННЫМ UNITS ===")

    # Получаем список units
    unit_dirs = [d for d in cli_instance.NORMALIZED_DIR.iterdir() if d.is_dir() and d.name.startswith("UNIT_")]

    if not unit_dirs:
        print("✗ Нет обработанных units в директории normalized")
        return

    print(f"📂 Найдено units: {len(unit_dirs)}")

    # Статистика по units
    total_files = 0
    file_types = {}
    units_with_manifest = 0
    units_with_errors = 0

    for unit_dir in unit_dirs:
        try:
            files_dir = unit_dir / "files"
            if files_dir.exists():
                files = list(files_dir.glob("*"))
                files = [f for f in files if f.is_file()]
                total_files += len(files)

                # Анализ типов файлов
                for file_path in files:
                    detection = cli_instance.detect_file_type(file_path)
                    file_type = detection.get("detected_type", "unknown")
                    if file_type not in file_types:
                        file_types[file_type] = 0
                    file_types[file_type] += 1

            # Проверка наличия manifest.json
            manifest_file = unit_dir / "manifest.json"
            if manifest_file.exists():
                units_with_manifest += 1

            # Проверка на ошибки (упрощенно)
            error_files = list(unit_dir.glob("*.error"))
            if error_files:
                units_with_errors += 1

        except Exception as e:
            print(f"  ❌ Ошибка анализа {unit_dir.name}: {e}")
            units_with_errors += 1

    # Вывод отчета
    print("\n📊 Общая статистика:")
    print(f"   Units всего: {len(unit_dirs)}")
    print(f"   С manifest.json: {units_with_manifest}")
    print(f"   С ошибками: {units_with_errors}")
    print(f"   Всего файлов: {total_files}")

    if file_types:
        print("\n📄 Распределение по типам файлов:")
        for file_type, count in sorted(file_types.items()):
            print(f"   {file_type}: {count} файлов")

    # Примеры units
    print("\n📋 Примеры units:")
    for i, unit_dir in enumerate(unit_dirs[:5]):
        files_count = 0
        if (unit_dir / "files").exists():
            files_count = len(list((unit_dir / "files").glob("*")))
        manifest_exists = (unit_dir / "manifest.json").exists()
        print(f"   {i+1}. {unit_dir.name}: {files_count} файлов, manifest: {'✓' if manifest_exists else '✗'}")

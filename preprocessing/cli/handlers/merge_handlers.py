"""
Handlers для merge операций (пункты меню 18-19).

Включает функции:
- handle_merge_dry_run: планирование merge
- handle_merge_real: выполнение merge
"""

import shutil


def handle_merge_dry_run(cli_instance):
    """Merge в ready_docling (DRY RUN)."""
    print("\n=== MERGE В READY_DOCLING (DRY RUN) ===")

    pending_base = cli_instance.INPUT_DIR.parent / "pending"
    ready_docling_dir = cli_instance.INPUT_DIR.parent / "ready_docling"

    if not pending_base.exists():
        print("✗ Директория pending не существует")
        return

    print(f"📁 Исходная директория: {pending_base.absolute()}")
    print(f"📁 Целевая директория: {ready_docling_dir.absolute()}")

    # Сбор статистики
    categories = ["direct", "normalize", "convert", "extract", "special"]
    total_files = 0
    operations = []

    for category in categories:
        cat_dir = pending_base / category
        if cat_dir.exists():
            files = list(cat_dir.glob("*"))
            files = [f for f in files if f.is_file()]

            if files:
                total_files += len(files)
                operations.append({
                    "category": category,
                    "source_dir": cat_dir,
                    "target_dir": ready_docling_dir / category,
                    "files": files
                })

    print("\n📊 DRY RUN - Планируемые операции:")
    print(f"   Всего файлов для merge: {total_files}")

    for op in operations:
        print(f"\n📂 Категория: {op['category']}")
        print(f"   Источник: {op['source_dir']}")
        print(f"   Назначение: {op['target_dir']}")
        print(f"   Файлов: {len(op['files'])}")

        # Показать примеры файлов
        for i, file_path in enumerate(op['files'][:3]):
            size = file_path.stat().st_size
            print(f"     {i+1}. {file_path.name} ({size:,} bytes)")

    print("\n⚠️  DRY RUN завершен. Файлы не были перемещены.")
    print("   Используйте 'Merge (РЕАЛЬНЫЙ)' для выполнения операций.")


def handle_merge_real(cli_instance):
    """Merge в ready_docling (РЕАЛЬНЫЙ)."""
    print("\n=== MERGE В READY_DOCLING (РЕАЛЬНЫЙ) ===")

    pending_base = cli_instance.INPUT_DIR.parent / "pending"
    ready_docling_dir = cli_instance.INPUT_DIR.parent / "ready_docling"

    if not pending_base.exists():
        print("✗ Директория pending не существует")
        return

    # Подтверждение операции
    confirm = input("⚠️  ВНИМАНИЕ: Эта операция переместит файлы из pending в ready_docling. Продолжить? (yes/no): ").strip().lower()
    if confirm not in ["yes", "y", "да"]:
        print("❌ Операция отменена пользователем")
        return

    print("🚀 Начинаем merge операции...")

    # Выполнение merge
    categories = ["direct", "normalize", "convert", "extract", "special"]
    total_moved = 0
    total_errors = 0

    for category in categories:
        cat_dir = pending_base / category
        target_dir = ready_docling_dir / category

        if cat_dir.exists():
            files = list(cat_dir.glob("*"))
            files = [f for f in files if f.is_file()]

            if files:
                target_dir.mkdir(parents=True, exist_ok=True)

                print(f"\n📂 Обрабатываем категорию: {category}")
                moved = 0
                errors = 0

                for file_path in files:
                    try:
                        target_path = target_dir / file_path.name
                        shutil.move(str(file_path), str(target_path))
                        moved += 1
                        print(f"  ✓ {file_path.name} → {category}/")
                    except Exception as e:
                        errors += 1
                        print(f"  ❌ {file_path.name}: {e}")

                print(f"  Результат: {moved} перемещено, {errors} ошибок")
                total_moved += moved
                total_errors += errors

    print("\n🎉 Merge завершен!")
    print(f"   Перемещено файлов: {total_moved}")
    if total_errors > 0:
        print(f"   Ошибок: {total_errors}")

    print(f"\n📁 Проверьте результаты в: {ready_docling_dir.absolute()}")

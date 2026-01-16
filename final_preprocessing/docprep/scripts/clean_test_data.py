#!/usr/bin/env python3
"""
Скрипт для очистки тестовых данных перед полноценным тестированием.

Удаляет все директории в Data/YYYY-MM-DD КРОМЕ Input,
для обеспечения чистого тестирования pipeline.
"""
import shutil
import argparse
from pathlib import Path


def clean_test_data(data_dir: Path, dry_run: bool = True):
    """
    Очищает тестовые данные, сохраняя только Input директорию.

    Args:
        data_dir: Путь к директории с данными (например, Data/2025-12-20)
        dry_run: Если True, только показывает что будет удалено
    """
    if not data_dir.exists():
        print(f"❌ Директория не существует: {data_dir}")
        return

    if not data_dir.is_dir():
        print(f"❌ Путь не является директорией: {data_dir}")
        return

    # Директории, которые нужно удалить
    dirs_to_remove = ["Processing", "Merge", "Exceptions"]

    total_removed = 0
    total_size_mb = 0.0

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Очистка данных в: {data_dir}\n")

    for dir_name in dirs_to_remove:
        dir_path = data_dir / dir_name
        if dir_path.exists() and dir_path.is_dir():
            # Вычисляем размер директории
            dir_size = sum(f.stat().st_size for f in dir_path.rglob('*') if f.is_file())
            dir_size_mb = dir_size / (1024 * 1024)

            # Считаем количество файлов и units
            file_count = len(list(dir_path.rglob('*')))
            unit_count = len(list(dir_path.glob("UNIT_*")))

            print(f"📂 {dir_name}:")
            print(f"   - Units: {unit_count}")
            print(f"   - Файлов: {file_count}")
            print(f"   - Размер: {dir_size_mb:.2f} MB")

            if not dry_run:
                try:
                    shutil.rmtree(dir_path)
                    print(f"   ✅ Удалена")
                    total_removed += unit_count
                    total_size_mb += dir_size_mb
                except Exception as e:
                    print(f"   ❌ Ошибка удаления: {e}")
            else:
                print(f"   [DRY RUN] Будет удалена")
                total_removed += unit_count
                total_size_mb += dir_size_mb
        else:
            print(f"⚠️  {dir_name}: не существует")

    # Проверяем Input директорию (не удаляем!)
    input_dir = data_dir / "Input"
    if input_dir.exists():
        unit_count = len(list(input_dir.glob("UNIT_*")))
        input_size = sum(f.stat().st_size for f in input_dir.rglob('*') if f.is_file())
        input_size_mb = input_size / (1024 * 1024)

        print(f"\n✅ Input (сохранена):")
        print(f"   - Units: {unit_count}")
        print(f"   - Размер: {input_size_mb:.2f} MB")
    else:
        print(f"\n⚠️  Input директория не найдена!")

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Итого:")
    print(f"   - Units удалено: {total_removed}")
    print(f"   - Освобождено: {total_size_mb:.2f} MB")

    if dry_run:
        print(f"\n💡 Для реальной очистки запустите с флагом --no-dry-run")


def main():
    parser = argparse.ArgumentParser(
        description="Очистка тестовых данных перед полноценным тестированием"
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("/root/winners_preprocessor/final_preprocessing/Data/2025-12-20"),
        help="Путь к директории с данными (по умолчанию: Data/2025-12-20)"
    )
    parser.add_argument(
        "--no-dry-run",
        action="store_true",
        help="Выполнить реальную очистку (без этого флага только показывает что будет удалено)"
    )

    args = parser.parse_args()

    clean_test_data(args.data_dir, dry_run=not args.no_dry_run)


if __name__ == "__main__":
    main()

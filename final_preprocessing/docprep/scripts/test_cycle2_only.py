#!/usr/bin/env python3
"""
Скрипт для тестирования ТОЛЬКО Cycle 2 без merge2docling.

Тестирует:
- Классификацию Merge_1 -> Processing_2/Merge_2/Exceptions_2
- Обработку Processing_2 (Convert, Extract, Normalize)
- Перемещение в Merge_2

Ready2Docling создается отдельным этапом (merge2docling).
"""
import sys
import time
from pathlib import Path
from datetime import datetime

# Добавляем корневую директорию проекта в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from docprep.core.config import (
    get_cycle_paths,
    get_processing_paths,
    get_data_paths,
    init_directory_structure,
)
from docprep.engine.classifier import Classifier
from docprep.engine.converter import Converter
from docprep.engine.extractor import Extractor
from docprep.engine.normalizers import NameNormalizer, ExtensionNormalizer
from docprep.utils.paths import find_all_units


def count_units_in_dir(dir_path: Path) -> int:
    """Подсчитывает количество UNIT директорий."""
    if not dir_path.exists():
        return 0
    return len(list(dir_path.rglob("UNIT_*")))


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Тестирование ТОЛЬКО Cycle 2")
    parser.add_argument("--date", type=str, default="2025-12-20", help="Дата протокола")
    parser.add_argument("--verbose", "-v", action="store_true", help="Подробный вывод")

    args = parser.parse_args()

    print("=" * 80)
    print("🧪 ТЕСТИРОВАНИЕ CYCLE 2")
    print("=" * 80)
    print(f"Дата: {args.date}\\n")

    # Инициализируем структуру
    init_directory_structure(date=args.date)

    data_paths = get_data_paths(args.date)

    # Input для Cycle 2 = Merge_1
    cycle1_paths = get_cycle_paths(1, data_paths["processing"], data_paths["merge"], data_paths["exceptions"])
    input_dir = cycle1_paths["merge"]

    # Проверяем Merge_1
    input_units = count_units_in_dir(input_dir)
    print(f"📥 Merge_1 (вход): {input_units} units\\n")

    if input_units == 0:
        print("❌ Нет units в Merge_1!")
        print("   Сначала запустите test_cycle1_only.py")
        return

    start_time = time.time()

    # ====================================================================
    # ШАГ 1/4: КЛАССИФИКАЦИЯ
    # ====================================================================
    print("=" * 80)
    print("📋 ШАГ 1/4: КЛАССИФИКАЦИЯ")
    print("=" * 80)

    classifier = Classifier()
    units = find_all_units(input_dir)

    print(f"Найдено {len(units)} units для классификации...\n")

    classified = 0
    errors_classify = []

    for i, unit_path in enumerate(units, 1):
        try:
            classifier.classify_unit(
                unit_path,
                cycle=2,
                protocol_date=args.date,
                dry_run=False
            )
            classified += 1

            if args.verbose and i % 100 == 0:
                print(f"  Классифицировано: {i}/{len(units)}")

        except Exception as e:
            errors_classify.append({"unit": unit_path.name, "error": str(e)})
            if args.verbose:
                print(f"  ❌ Ошибка {unit_path.name}: {e}")

    print(f"\\n✅ Классифицировано: {classified}/{len(units)} units")
    if errors_classify:
        print(f"⚠️  Ошибок классификации: {len(errors_classify)}")

    # Статистика после классификации
    processing_paths = get_processing_paths(2, data_paths["processing"])
    cycle_paths = get_cycle_paths(2, data_paths["processing"], data_paths["merge"], data_paths["exceptions"])

    convert_count = count_units_in_dir(processing_paths["Convert"])
    extract_count = count_units_in_dir(processing_paths["Extract"])
    normalize_count = count_units_in_dir(processing_paths["Normalize"])
    merge2_direct = count_units_in_dir(cycle_paths["merge"] / "Direct")
    exceptions_count = count_units_in_dir(cycle_paths["exceptions"])

    print(f"\\n📊 Результаты классификации:")
    print(f"  • Convert: {convert_count} units")
    print(f"  • Extract: {extract_count} units")
    print(f"  • Normalize: {normalize_count} units")
    print(f"  • Direct (Merge_2): {merge2_direct} units")
    print(f"  • Exceptions: {exceptions_count} units")
    print(f"  • Всего обработано: {convert_count + extract_count + normalize_count + merge2_direct + exceptions_count} units")

    # ====================================================================
    # ШАГ 2/4: ОБРАБОТКА CONVERT
    # ====================================================================
    print("\\n" + "=" * 80)
    print("🔄 ШАГ 2/4: ОБРАБОТКА CONVERT")
    print("=" * 80)

    converter = Converter()
    convert_dir = processing_paths["Convert"]

    if convert_count > 0:
        convert_units = find_all_units(convert_dir)
        print(f"Найдено {len(convert_units)} units для конвертации...")

        converted = 0
        errors_convert = []

        for i, unit_path in enumerate(convert_units, 1):
            try:
                converter.convert_unit(unit_path, cycle=2, protocol_date=args.date, dry_run=False)
                converted += 1

                if args.verbose and i % 10 == 0:
                    print(f"  Конвертировано: {i}/{len(convert_units)}")

            except Exception as e:
                errors_convert.append({"unit": unit_path.name, "error": str(e)})
                if args.verbose:
                    print(f"  ❌ Ошибка {unit_path.name}: {e}")

        print(f"\\n✅ Конвертировано: {converted}/{len(convert_units)} units")
        if errors_convert:
            print(f"⚠️  Ошибок конвертации: {len(errors_convert)}")

        # Проверяем, остались ли units в Processing_2/Convert
        remaining_convert = count_units_in_dir(convert_dir)
        print(f"  Осталось в Processing_2/Convert: {remaining_convert} units")

    else:
        print("⏭️  Нет units для конвертации, пропускаем...\\n")

    # ====================================================================
    # ШАГ 3/4: ОБРАБОТКА EXTRACT
    # ====================================================================
    print("\\n" + "=" * 80)
    print("📦 ШАГ 3/4: ОБРАБОТКА EXTRACT")
    print("=" * 80)

    extractor = Extractor()
    extract_dir = processing_paths["Extract"]

    if extract_count > 0:
        extract_units = find_all_units(extract_dir)
        print(f"Найдено {len(extract_units)} units для разархивации...")

        extracted = 0
        errors_extract = []

        for i, unit_path in enumerate(extract_units, 1):
            try:
                extractor.extract_unit(unit_path, cycle=2, protocol_date=args.date, dry_run=False)
                extracted += 1

                if args.verbose and i % 10 == 0:
                    print(f"  Разархивировано: {i}/{len(extract_units)}")

            except Exception as e:
                errors_extract.append({"unit": unit_path.name, "error": str(e)})
                if args.verbose:
                    print(f"  ❌ Ошибка {unit_path.name}: {e}")

        print(f"\\n✅ Разархивировано: {extracted}/{len(extract_units)} units")
        if errors_extract:
            print(f"⚠️  Ошибок разархивации: {len(errors_extract)}")

        # Проверяем, остались ли units в Processing_2/Extract
        remaining_extract = count_units_in_dir(extract_dir)
        print(f"  Осталось в Processing_2/Extract: {remaining_extract} units")

    else:
        print("⏭️  Нет units для разархивации, пропускаем...\\n")

    # ====================================================================
    # ШАГ 4/4: ОБРАБОТКА NORMALIZE
    # ====================================================================
    print("\\n" + "=" * 80)
    print("✨ ШАГ 4/4: ОБРАБОТКА NORMALIZE")
    print("=" * 80)

    name_normalizer = NameNormalizer()
    extension_normalizer = ExtensionNormalizer()
    normalize_dir = processing_paths["Normalize"]

    if normalize_count > 0:
        normalize_units = find_all_units(normalize_dir)
        print(f"Найдено {len(normalize_units)} units для нормализации...")

        normalized = 0
        errors_normalize = []

        for i, unit_path in enumerate(normalize_units, 1):
            try:
                # Name normalization
                name_normalizer.normalize_names(unit_path, cycle=2, protocol_date=args.date, dry_run=False)
                # Extension normalization
                extension_normalizer.normalize_extensions(unit_path, cycle=2, protocol_date=args.date, dry_run=False)
                normalized += 1

                if args.verbose and i % 5 == 0:
                    print(f"  Нормализовано: {i}/{len(normalize_units)}")

            except Exception as e:
                errors_normalize.append({"unit": unit_path.name, "error": str(e)})
                if args.verbose:
                    print(f"  ❌ Ошибка {unit_path.name}: {e}")

        print(f"\\n✅ Нормализовано: {normalized}/{len(normalize_units)} units")
        if errors_normalize:
            print(f"⚠️  Ошибок нормализации: {len(errors_normalize)}")

        # Проверяем, остались ли units в Processing_2/Normalize
        remaining_normalize = count_units_in_dir(normalize_dir)
        print(f"  Осталось в Processing_2/Normalize: {remaining_normalize} units")

    else:
        print("⏭️  Нет units для нормализации, пропускаем...\\n")

    # ====================================================================
    # ФИНАЛЬНАЯ СТАТИСТИКА
    # ====================================================================
    print("\\n" + "=" * 80)
    print("📊 ФИНАЛЬНАЯ СТАТИСТИКА CYCLE 2")
    print("=" * 80)

    # Подсчитываем units в Merge_2
    merge_2_dir = cycle_paths["merge"]
    merge_2_converted = count_units_in_dir(merge_2_dir / "Converted")
    merge_2_extracted = count_units_in_dir(merge_2_dir / "Extracted")
    merge_2_normalized = count_units_in_dir(merge_2_dir / "Normalized")
    merge_2_direct = count_units_in_dir(merge_2_dir / "Direct")

    print(f"\\n🔀 Merge_2:")
    print(f"  • Direct: {merge_2_direct} units")
    print(f"  • Converted: {merge_2_converted} units")
    print(f"  • Extracted: {merge_2_extracted} units")
    print(f"  • Normalized: {merge_2_normalized} units")
    print(f"  • Всего в Merge_2: {merge_2_direct + merge_2_converted + merge_2_extracted + merge_2_normalized} units")

    print(f"\\n⚠️  Exceptions_2:")
    print(f"  • Всего: {count_units_in_dir(cycle_paths['exceptions'])} units")

    # Проверяем, остались ли units в Processing_2
    total_remaining = (
        count_units_in_dir(processing_paths["Convert"])
        + count_units_in_dir(processing_paths["Extract"])
        + count_units_in_dir(processing_paths["Normalize"])
    )

    print(f"\\n⚙️  Осталось в Processing_2: {total_remaining} units")

    if total_remaining > 0:
        print("\\n⚠️  ВНИМАНИЕ: Не все units обработаны!")
        print("  Проверьте логи для деталей ошибок.")

    # Итого
    elapsed = time.time() - start_time
    print(f"\\n⏱️  Общее время выполнения: {elapsed:.1f} секунд")

    # Проверяем баланс
    total_input = input_units
    total_output = (
        merge_2_direct + merge_2_converted + merge_2_extracted + merge_2_normalized
        + count_units_in_dir(cycle_paths["exceptions"])
        + total_remaining
    )

    print(f"\\n📈 Баланс:")
    print(f"  • Input (Merge_1): {total_input} units")
    print(f"  • Output: {total_output} units")
    if total_input == total_output:
        print("  ✅ Баланс сходится!")
    else:
        print(f"  ⚠️  Расхождение: {total_input - total_output} units")

    # Проверяем, что Ready2Docling НЕ был создан
    ready2docling_path = data_paths.get("ready2docling", Path(f"Data/{args.date}/Ready2Docling"))
    if ready2docling_path.exists():
        ready_count = count_units_in_dir(ready2docling_path)
        if ready_count > 0:
            print(f"\n📦 Ready2Docling содержит {ready_count} units")
            print("  (Ready2Docling заполняется отдельным этапом merge2docling)")
        else:
            print("\n✅ Ready2Docling пуст (ожидаемо, merge2docling не запускался)")
    else:
        print("\n✅ Ready2Docling не создан (ожидаемо, merge2docling не запускался)")

    print("\\n" + "=" * 80)
    print("✅ ТЕСТИРОВАНИЕ CYCLE 2 ЗАВЕРШЕНО")
    print("=" * 80)


if __name__ == "__main__":
    main()

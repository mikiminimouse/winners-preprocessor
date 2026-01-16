#!/usr/bin/env python3
"""
Скрипт для тестирования ТОЛЬКО Cycle 1 без последующих циклов.

Тестирует:
- Классификацию Input -> Processing_1/Exceptions_1/Merge_0
- Обработку Processing_1 (Convert, Extract, Normalize)
- Перемещение в Merge_1

НЕ тестирует Cycle 2+ и НЕ делает merge2docling!
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

    parser = argparse.ArgumentParser(description="Тестирование ТОЛЬКО Cycle 1")
    parser.add_argument("--date", type=str, default="2025-12-20", help="Дата протокола")
    parser.add_argument("--verbose", "-v", action="store_true", help="Подробный вывод")

    args = parser.parse_args()

    print("=" * 80)
    print("🧪 ТЕСТИРОВАНИЕ CYCLE 1")
    print("=" * 80)
    print(f"Дата: {args.date}\n")

    # Инициализируем структуру
    init_directory_structure(date=args.date)

    data_paths = get_data_paths(args.date)
    input_dir = data_paths["input"]

    # Проверяем Input
    input_units = count_units_in_dir(input_dir)
    print(f"📥 Input: {input_units} units\n")

    if input_units == 0:
        print("❌ Нет units в Input!")
        return

    start_time = time.time()

    # ====================================================================
    # ШАТТЕСТИРОВАНИЕ 1: КЛАССИФИКАЦИЯ
    # ====================================================================
    print("=" * 80)
    print("📋 ШАГ 1/4: КЛАССИФИКАЦИЯ")
    print("=" * 80)

    classifier = Classifier()
    units = find_all_units(input_dir)

    print(f"Найдено {len(units)} units для классификации...")

    classified = 0
    errors_classify = []

    for i, unit_path in enumerate(units, 1):
        try:
            classifier.classify_unit(
                unit_path, cycle=1, protocol_date=args.date, dry_run=False
            )
            classified += 1

            if args.verbose and i % 100 == 0:
                print(f"  Классифицировано: {i}/{len(units)}")

        except Exception as e:
            errors_classify.append({"unit": unit_path.name, "error": str(e)})
            if args.verbose:
                print(f"  ❌ Ошибка {unit_path.name}: {e}")

    print(f"\n✅ Классифицировано: {classified}/{len(units)} units")
    if errors_classify:
        print(f"⚠️  Ошибок классификации: {len(errors_classify)}")

    # Статистика после классификации
    processing_paths = get_processing_paths(1, data_paths["processing"])
    cycle_paths = get_cycle_paths(1, data_paths["processing"], data_paths["merge"], data_paths["exceptions"])

    convert_count = count_units_in_dir(processing_paths["Convert"])
    extract_count = count_units_in_dir(processing_paths["Extract"])
    normalize_count = count_units_in_dir(processing_paths["Normalize"])
    # НОВАЯ СТРУКТУРА v2: Merge/Direct/ вместо Merge_0/Direct
    direct_count = count_units_in_dir(data_paths["merge"] / "Direct")
    # Exceptions/Direct/ для исключений до обработки в цикле 1
    exceptions_direct_count = count_units_in_dir(data_paths["exceptions"] / "Direct")

    print(f"\n📊 Результаты классификации:")
    print(f"  • Convert: {convert_count} units")
    print(f"  • Extract: {extract_count} units")
    print(f"  • Normalize: {normalize_count} units")
    print(f"  • Direct (Merge/Direct): {direct_count} units")
    print(f"  • Exceptions/Direct: {exceptions_direct_count} units")
    print(f"  • Всего обработано: {convert_count + extract_count + normalize_count + direct_count + exceptions_direct_count} units")

    # ====================================================================
    # ШАГ 2/4: ОБРАБОТКА CONVERT
    # ====================================================================
    print("\n" + "=" * 80)
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
                converter.convert_unit(unit_path, cycle=1, protocol_date=args.date, dry_run=False)
                converted += 1

                if args.verbose and i % 10 == 0:
                    print(f"  Конвертировано: {i}/{len(convert_units)}")

            except Exception as e:
                errors_convert.append({"unit": unit_path.name, "error": str(e)})
                if args.verbose:
                    print(f"  ❌ Ошибка {unit_path.name}: {e}")

        print(f"\n✅ Конвертировано: {converted}/{len(convert_units)} units")
        if errors_convert:
            print(f"⚠️  Ошибок конвертации: {len(errors_convert)}")

        # Проверяем, остались ли units в Processing_1/Convert
        remaining_convert = count_units_in_dir(convert_dir)
        print(f"  Осталось в Processing_1/Convert: {remaining_convert} units")

    else:
        print("⏭️  Нет units для конвертации, пропускаем...\n")

    # ====================================================================
    # ШАГ 3/4: ОБРАБОТКА EXTRACT
    # ====================================================================
    print("\n" + "=" * 80)
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
                extractor.extract_unit(unit_path, cycle=1, protocol_date=args.date, dry_run=False)
                extracted += 1

                if args.verbose and i % 10 == 0:
                    print(f"  Разархивировано: {i}/{len(extract_units)}")

            except Exception as e:
                errors_extract.append({"unit": unit_path.name, "error": str(e)})
                if args.verbose:
                    print(f"  ❌ Ошибка {unit_path.name}: {e}")

        print(f"\n✅ Разархивировано: {extracted}/{len(extract_units)} units")
        if errors_extract:
            print(f"⚠️  Ошибок разархивации: {len(errors_extract)}")

        # Проверяем, остались ли units в Processing_1/Extract
        remaining_extract = count_units_in_dir(extract_dir)
        print(f"  Осталось в Processing_1/Extract: {remaining_extract} units")

    else:
        print("⏭️  Нет units для разархивации, пропускаем...\n")

    # ====================================================================
    # ШАГ 4/4: ОБРАБОТКА NORMALIZE
    # ====================================================================
    print("\n" + "=" * 80)
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
                name_normalizer.normalize_names(unit_path, cycle=1, protocol_date=args.date, dry_run=False)
                # Extension normalization
                extension_normalizer.normalize_extensions(unit_path, cycle=1, protocol_date=args.date, dry_run=False)
                normalized += 1

                if args.verbose and i % 5 == 0:
                    print(f"  Нормализовано: {i}/{len(normalize_units)}")

            except Exception as e:
                errors_normalize.append({"unit": unit_path.name, "error": str(e)})
                if args.verbose:
                    print(f"  ❌ Ошибка {unit_path.name}: {e}")

        print(f"\n✅ Нормализовано: {normalized}/{len(normalize_units)} units")
        if errors_normalize:
            print(f"⚠️  Ошибок нормализации: {len(errors_normalize)}")

        # Проверяем, остались ли units в Processing_1/Normalize
        remaining_normalize = count_units_in_dir(normalize_dir)
        print(f"  Осталось в Processing_1/Normalize: {remaining_normalize} units")

    else:
        print("⏭️  Нет units для нормализации, пропускаем...\n")

    # ====================================================================
    # ФИНАЛЬНАЯ СТАТИСТИКА
    # ====================================================================
    print("\n" + "=" * 80)
    print("📊 ФИНАЛЬНАЯ СТАТИСТИКА CYCLE 1")
    print("=" * 80)

    # НОВАЯ СТРУКТУРА v2: Merge/Processed_1/ вместо Merge_1/
    processed_1_dir = data_paths["merge"] / "Processed_1"
    processed_1_converted = count_units_in_dir(processed_1_dir / "Converted")
    processed_1_extracted = count_units_in_dir(processed_1_dir / "Extracted")
    processed_1_normalized = count_units_in_dir(processed_1_dir / "Normalized")
    processed_1_direct = count_units_in_dir(processed_1_dir / "Direct")
    processed_1_mixed = count_units_in_dir(processed_1_dir / "Mixed")

    # Direct из классификации (без обработки)
    merge_direct = count_units_in_dir(data_paths["merge"] / "Direct")

    print(f"\n🔀 Merge/Direct (готовые напрямую):")
    print(f"  • Direct: {merge_direct} units")

    print(f"\n🔀 Merge/Processed_1 (обработанные в цикле 1):")
    print(f"  • Converted: {processed_1_converted} units")
    print(f"  • Extracted: {processed_1_extracted} units")
    print(f"  • Normalized: {processed_1_normalized} units")
    print(f"  • Direct: {processed_1_direct} units")
    print(f"  • Mixed: {processed_1_mixed} units")
    total_processed_1 = processed_1_converted + processed_1_extracted + processed_1_normalized + processed_1_direct + processed_1_mixed
    print(f"  • Всего в Processed_1: {total_processed_1} units")

    # НОВАЯ СТРУКТУРА v2: Exceptions/Direct и Exceptions/Processed_1
    exceptions_direct = count_units_in_dir(data_paths["exceptions"] / "Direct")
    exceptions_processed_1 = count_units_in_dir(data_paths["exceptions"] / "Processed_1")

    print(f"\n⚠️  Exceptions:")
    print(f"  • Exceptions/Direct: {exceptions_direct} units")
    print(f"  • Exceptions/Processed_1: {exceptions_processed_1} units")
    print(f"  • Всего исключений: {exceptions_direct + exceptions_processed_1} units")

    # Проверяем, остались ли units в Processing_1
    total_remaining = (
        count_units_in_dir(processing_paths["Convert"])
        + count_units_in_dir(processing_paths["Extract"])
        + count_units_in_dir(processing_paths["Normalize"])
    )

    print(f"\n⚙️  Осталось в Processing_1: {total_remaining} units")

    if total_remaining > 0:
        print("\n⚠️  ВНИМАНИЕ: Не все units обработаны!")
        print("  Проверьте логи для деталей ошибок.")

    # Итого
    elapsed = time.time() - start_time
    print(f"\n⏱️  Общее время выполнения: {elapsed:.1f} секунд")

    # Проверяем баланс
    total_input = input_units
    total_output = (
        merge_direct  # Merge/Direct
        + total_processed_1  # Merge/Processed_1/*
        + exceptions_direct  # Exceptions/Direct
        + exceptions_processed_1  # Exceptions/Processed_1
        + total_remaining  # Осталось в Processing_1
    )

    print(f"\n📈 Баланс:")
    print(f"  • Input: {total_input} units")
    print(f"  • Output: {total_output} units")
    print(f"    - Merge/Direct: {merge_direct}")
    print(f"    - Merge/Processed_1: {total_processed_1}")
    print(f"    - Exceptions/Direct: {exceptions_direct}")
    print(f"    - Exceptions/Processed_1: {exceptions_processed_1}")
    print(f"    - Processing_1 (осталось): {total_remaining}")
    if total_input == total_output:
        print("  ✅ Баланс сходится!")
    else:
        print(f"  ⚠️  Расхождение: {total_input - total_output} units")

    print("\n" + "=" * 80)
    print("✅ ТЕСТИРОВАНИЕ CYCLE 1 ЗАВЕРШЕНО")
    print("=" * 80)


if __name__ == "__main__":
    main()

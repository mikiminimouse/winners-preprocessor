#!/usr/bin/env python3
"""
Скрипт для последовательного тестирования циклов обработки WITHOUT merge2docling.

Тестирует каждый цикл отдельно:
- Cycle 1: Input -> Processing_1 -> Merge_1
- Cycle 2: Merge_1 -> Processing_2 -> Merge_2
- Cycle 3: Merge_2 -> Processing_3 -> Merge_3
- И так далее, пока есть что обработать

Останавливается, когда в Processing больше нет units для следующего цикла.
НЕ запускает финальный merge2docling!
"""
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

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


def get_cycle_statistics(cycle: int, data_paths: Dict[str, Path]) -> Dict[str, Any]:
    """Собирает статистику по циклу."""
    cycle_paths = get_cycle_paths(
        cycle, data_paths["processing"], data_paths["merge"], data_paths["exceptions"]
    )
    processing_paths = get_processing_paths(cycle, data_paths["processing"])

    stats = {
        "cycle": cycle,
        "processing": {},
        "merge": {},
        "exceptions": {},
    }

    # Processing
    for subdir_name, subdir_path in processing_paths.items():
        if subdir_path.exists():
            count = count_units_in_dir(subdir_path)
            if count > 0:
                stats["processing"][subdir_name] = count

    # НОВАЯ СТРУКТУРА v2: Merge/Processed_N/ вместо Merge_N/
    merge_dir = cycle_paths["merge"]  # = Merge/Processed_N/
    if merge_dir.exists():
        for category in ["Converted", "Extracted", "Normalized", "Direct", "Mixed"]:
            category_dir = merge_dir / category
            if category_dir.exists():
                count = count_units_in_dir(category_dir)
                if count > 0:
                    stats["merge"][category] = count

    # НОВАЯ СТРУКТУРА v2: Merge/Direct/ для первого цикла (файлы готовые напрямую)
    if cycle == 1:
        direct_dir = data_paths["merge"] / "Direct"
        if direct_dir.exists():
            count = count_units_in_dir(direct_dir)
            if count > 0:
                stats["merge"]["Direct_from_Input"] = count

    # НОВАЯ СТРУКТУРА v2: Exceptions/Direct и Exceptions/Processed_N
    # Exceptions/Processed_N для текущего цикла
    exceptions_processed_dir = cycle_paths["exceptions"]  # = Exceptions/Processed_N
    if exceptions_processed_dir.exists():
        for subdir in exceptions_processed_dir.iterdir():
            if subdir.is_dir():
                count = count_units_in_dir(subdir)
                if count > 0:
                    stats["exceptions"][f"Processed_{cycle}/{subdir.name}"] = count

    # Exceptions/Direct для цикла 1 (исключения до обработки)
    if cycle == 1:
        exceptions_direct_dir = data_paths["exceptions"] / "Direct"
        if exceptions_direct_dir.exists():
            for subdir in exceptions_direct_dir.iterdir():
                if subdir.is_dir():
                    count = count_units_in_dir(subdir)
                    if count > 0:
                        stats["exceptions"][f"Direct/{subdir.name}"] = count

    return stats


def print_cycle_header(cycle: int):
    """Печатает заголовок цикла."""
    print("\n" + "=" * 80)
    print(f"🔄 CYCLE {cycle}")
    print("=" * 80)


def print_statistics(stats: Dict[str, Any]):
    """Печатает статистику."""
    cycle = stats["cycle"]

    if stats["processing"]:
        print(f"\n⚙️  Processing_{cycle}:")
        total = sum(stats["processing"].values())
        print(f"   Всего: {total} units")
        for name, count in stats["processing"].items():
            print(f"   - {name}: {count} units")

    if stats["merge"]:
        # НОВАЯ СТРУКТУРА v2: Merge/Processed_N/ вместо Merge_N/
        print(f"\n🔀 Merge/Processed_{cycle}:")
        total = sum(stats["merge"].values())
        print(f"   Всего: {total} units")
        for name, count in stats["merge"].items():
            print(f"   - {name}: {count} units")

    if stats["exceptions"]:
        # НОВАЯ СТРУКТУРА v2: Exceptions/Direct или Exceptions/Processed_N
        if cycle == 1:
            print(f"\n⚠️  Exceptions/Direct & Exceptions/Processed_1:")
        else:
            print(f"\n⚠️  Exceptions/Processed_{cycle}:")
        total = sum(stats["exceptions"].values())
        print(f"   Всего: {total} units")
        for name, count in stats["exceptions"].items():
            print(f"   - {name}: {count} units")


def test_cycle_1(protocol_date: str, verbose: bool = False) -> Dict[str, Any]:
    """
    Тестирует Cycle 1: Input -> Processing_1 -> Merge_1.

    Returns:
        Статистика по циклу
    """
    print_cycle_header(1)

    data_paths = get_data_paths(protocol_date)
    input_dir = data_paths["input"]

    # Проверяем наличие input
    input_units = count_units_in_dir(input_dir)
    print(f"\n📥 Input: {input_units} units")

    if input_units == 0:
        print("❌ Нет units в Input директории!")
        return {}

    start_time = time.time()

    # 1. Классификация
    print(f"\n📋 Шаг 1/4: Классификация")
    classifier = Classifier()

    units = find_all_units(input_dir)
    processed = 0
    errors = 0

    for unit_path in units:
        try:
            result = classifier.classify_unit(
                unit_path, cycle=1, protocol_date=protocol_date, dry_run=False
            )
            processed += 1
            if verbose and processed % 100 == 0:
                print(f"   Классифицировано: {processed}/{len(units)}")
        except Exception as e:
            errors += 1
            if verbose:
                print(f"   ❌ Ошибка {unit_path.name}: {e}")

    print(f"   ✅ Классифицировано: {processed} units, ошибок: {errors}")

    # Собираем статистику после классификации
    stats_after_classify = get_cycle_statistics(1, data_paths)

    # 2. Обработка Processing_1
    print(f"\n⚙️  Шаг 2/4: Обработка Processing_1")

    processing_paths = get_processing_paths(1, data_paths["processing"])
    converter = Converter()
    extractor = Extractor()
    name_normalizer = NameNormalizer()
    extension_normalizer = ExtensionNormalizer()

    # Convert
    convert_dir = processing_paths["Convert"]
    if convert_dir.exists():
        convert_units = find_all_units(convert_dir)
        if convert_units:
            print(f"   🔄 Convert: {len(convert_units)} units")
            for unit_path in convert_units:
                try:
                    converter.convert_unit(
                        unit_path, cycle=1, protocol_date=protocol_date, dry_run=False
                    )
                except Exception as e:
                    if verbose:
                        print(f"      ❌ {unit_path.name}: {e}")

    # Extract
    extract_dir = processing_paths["Extract"]
    if extract_dir.exists():
        extract_units = find_all_units(extract_dir)
        if extract_units:
            print(f"   📦 Extract: {len(extract_units)} units")
            for unit_path in extract_units:
                try:
                    extractor.extract_unit(
                        unit_path, cycle=1, protocol_date=protocol_date, dry_run=False
                    )
                except Exception as e:
                    if verbose:
                        print(f"      ❌ {unit_path.name}: {e}")

    # Normalize
    normalize_dir = processing_paths["Normalize"]
    if normalize_dir.exists():
        normalize_units = find_all_units(normalize_dir)
        if normalize_units:
            print(f"   ✨ Normalize: {len(normalize_units)} units")
            for unit_path in normalize_units:
                try:
                    # Name normalization
                    name_normalizer.normalize_unit(
                        unit_path, cycle=1, protocol_date=protocol_date, dry_run=False
                    )
                    # Extension normalization
                    extension_normalizer.normalize_extensions(
                        unit_path, cycle=1, protocol_date=protocol_date, dry_run=False
                    )
                except Exception as e:
                    if verbose:
                        print(f"      ❌ {unit_path.name}: {e}")

    # 3. Проверка - все ли обработано
    print(f"\n🔍 Шаг 3/4: Проверка обработки")
    remaining_in_processing = sum(
        count_units_in_dir(p) for p in processing_paths.values()
    )
    print(f"   Осталось в Processing_1: {remaining_in_processing} units")

    if remaining_in_processing > 0:
        print(f"   ⚠️  ВНИМАНИЕ: Не все units обработаны!")

    # 4. Финальная статистика
    print(f"\n📊 Шаг 4/4: Финальная статистика")
    stats_final = get_cycle_statistics(1, data_paths)
    print_statistics(stats_final)

    elapsed = time.time() - start_time
    print(f"\n⏱️  Время выполнения Cycle 1: {elapsed:.1f} секунд")

    return stats_final


def test_cycle_n(cycle: int, protocol_date: str, verbose: bool = False) -> Dict[str, Any]:
    """
    Тестирует Cycle N (2, 3, ...): Merge_{N-1} -> Processing_N -> Merge_N.

    Args:
        cycle: Номер цикла (2, 3, ...)
        protocol_date: Дата протокола
        verbose: Подробный вывод

    Returns:
        Статистика по циклу
    """
    print_cycle_header(cycle)

    data_paths = get_data_paths(protocol_date)

    # Input для этого цикла = Merge_{cycle-1}
    prev_cycle_paths = get_cycle_paths(
        cycle - 1, data_paths["processing"], data_paths["merge"], data_paths["exceptions"]
    )
    input_dir = prev_cycle_paths["merge"]

    # Проверяем наличие input
    input_units = count_units_in_dir(input_dir)
    print(f"\n📥 Input (Merge_{cycle-1}): {input_units} units")

    if input_units == 0:
        print(f"✅ Нет units в Merge_{cycle-1}, цикл {cycle} не требуется!")
        return {}

    start_time = time.time()

    # 1. Классификация
    print(f"\n📋 Шаг 1/4: Классификация")
    classifier = Classifier()

    units = find_all_units(input_dir)
    processed = 0
    errors = 0

    for unit_path in units:
        try:
            result = classifier.classify_unit(
                unit_path, cycle=cycle, protocol_date=protocol_date, dry_run=False
            )
            processed += 1
            if verbose and processed % 50 == 0:
                print(f"   Классифицировано: {processed}/{len(units)}")
        except Exception as e:
            errors += 1
            if verbose:
                print(f"   ❌ Ошибка {unit_path.name}: {e}")

    print(f"   ✅ Классифицировано: {processed} units, ошибок: {errors}")

    # 2. Обработка Processing_N
    print(f"\n⚙️  Шаг 2/4: Обработка Processing_{cycle}")

    processing_paths = get_processing_paths(cycle, data_paths["processing"])
    converter = Converter()
    extractor = Extractor()
    name_normalizer = NameNormalizer()
    extension_normalizer = ExtensionNormalizer()

    # Convert
    convert_dir = processing_paths["Convert"]
    if convert_dir.exists():
        convert_units = find_all_units(convert_dir)
        if convert_units:
            print(f"   🔄 Convert: {len(convert_units)} units")
            for unit_path in convert_units:
                try:
                    converter.convert_unit(
                        unit_path, cycle=cycle, protocol_date=protocol_date, dry_run=False
                    )
                except Exception as e:
                    if verbose:
                        print(f"      ❌ {unit_path.name}: {e}")

    # Extract
    extract_dir = processing_paths["Extract"]
    if extract_dir.exists():
        extract_units = find_all_units(extract_dir)
        if extract_units:
            print(f"   📦 Extract: {len(extract_units)} units")
            for unit_path in extract_units:
                try:
                    extractor.extract_unit(
                        unit_path, cycle=cycle, protocol_date=protocol_date, dry_run=False
                    )
                except Exception as e:
                    if verbose:
                        print(f"      ❌ {unit_path.name}: {e}")

    # Normalize
    normalize_dir = processing_paths["Normalize"]
    if normalize_dir.exists():
        normalize_units = find_all_units(normalize_dir)
        if normalize_units:
            print(f"   ✨ Normalize: {len(normalize_units)} units")
            for unit_path in normalize_units:
                try:
                    # Name normalization
                    name_normalizer.normalize_unit(
                        unit_path, cycle=cycle, protocol_date=protocol_date, dry_run=False
                    )
                    # Extension normalization
                    extension_normalizer.normalize_extensions(
                        unit_path, cycle=cycle, protocol_date=protocol_date, dry_run=False
                    )
                except Exception as e:
                    if verbose:
                        print(f"      ❌ {unit_path.name}: {e}")

    # 3. Проверка - все ли обработано
    print(f"\n🔍 Шаг 3/4: Проверка обработки")
    remaining_in_processing = sum(
        count_units_in_dir(p) for p in processing_paths.values()
    )
    print(f"   Осталось в Processing_{cycle}: {remaining_in_processing} units")

    if remaining_in_processing > 0:
        print(f"   ⚠️  ВНИМАНИЕ: Не все units обработаны!")

    # 4. Финальная статистика
    print(f"\n📊 Шаг 4/4: Финальная статистика")
    stats_final = get_cycle_statistics(cycle, data_paths)
    print_statistics(stats_final)

    elapsed = time.time() - start_time
    print(f"\n⏱️  Время выполнения Cycle {cycle}: {elapsed:.1f} секунд")

    return stats_final


def main():
    """Главная функция - последовательное тестирование всех циклов."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Последовательное тестирование циклов WITHOUT merge2docling"
    )
    parser.add_argument(
        "--date",
        type=str,
        default="2025-12-20",
        help="Дата протокола (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--max-cycles",
        type=int,
        default=3,
        help="Максимальное количество циклов (по умолчанию 3)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Подробный вывод",
    )
    parser.add_argument(
        "--start-from",
        type=int,
        default=1,
        help="Начать с цикла N (по умолчанию 1)",
    )

    args = parser.parse_args()

    print("=" * 80)
    print("🧪 ПОСЛЕДОВАТЕЛЬНОЕ ТЕСТИРОВАНИЕ ЦИКЛОВ")
    print("=" * 80)
    print(f"Дата: {args.date}")
    print(f"Максимум циклов: {args.max_cycles}")
    print(f"Начало с цикла: {args.start_from}")
    print("=" * 80)

    # Инициализируем структуру директорий
    init_directory_structure(date=args.date)

    all_stats = {}
    overall_start = time.time()

    # Cycle 1
    if args.start_from <= 1:
        stats_1 = test_cycle_1(args.date, verbose=args.verbose)
        all_stats[1] = stats_1

        # Проверяем, нужен ли следующий цикл
        data_paths = get_data_paths(args.date)
        # Новая структура v2: Processed_N вместо Merge_N
        processed_1_units = count_units_in_dir(data_paths["merge"] / "Processed_1")

        if processed_1_units == 0:
            print("\n" + "=" * 80)
            print("✅ Cycle 1 завершен. Processed_1 пуст, дальнейшие циклы не требуются.")
            print("=" * 80)
            return

    # Циклы 2+
    for cycle in range(max(2, args.start_from), args.max_cycles + 1):
        # Проверяем, есть ли что обрабатывать
        data_paths = get_data_paths(args.date)
        # Новая структура v2: Processed_N вместо Merge_N
        prev_processed = data_paths["merge"] / f"Processed_{cycle-1}"
        prev_processed_units = count_units_in_dir(prev_processed)

        if prev_processed_units == 0:
            print("\n" + "=" * 80)
            print(f"✅ Processed_{cycle-1} пуст. Cycle {cycle} не требуется.")
            print("=" * 80)
            break

        stats_n = test_cycle_n(cycle, args.date, verbose=args.verbose)
        all_stats[cycle] = stats_n

        # Проверяем результаты (новая структура v2: Processed_N)
        current_processed = data_paths["merge"] / f"Processed_{cycle}"
        current_processed_units = count_units_in_dir(current_processed)

        if current_processed_units == 0:
            print("\n" + "=" * 80)
            print(f"✅ Cycle {cycle} завершен. Processed_{cycle} пуст, дальнейшие циклы не требуются.")
            print("=" * 80)
            break

    # Финальная сводка
    overall_elapsed = time.time() - overall_start
    print("\n" + "=" * 80)
    print("📊 ФИНАЛЬНАЯ СВОДКА")
    print("=" * 80)

    total_processed = 0
    total_exceptions = 0

    for cycle, stats in all_stats.items():
        if stats:
            merge_count = sum(stats.get("merge", {}).values())
            exceptions_count = sum(stats.get("exceptions", {}).values())
            total_processed += merge_count
            total_exceptions += exceptions_count

            print(f"\nCycle {cycle}:")
            print(f"  Merge: {merge_count} units")
            print(f"  Exceptions: {exceptions_count} units")

    print(f"\n📈 Итого:")
    print(f"  Обработано: {total_processed} units")
    print(f"  Исключений: {total_exceptions} units")
    print(f"  Общее время: {overall_elapsed:.1f} секунд")

    print("\n" + "=" * 80)
    print("✅ Тестирование завершено! Merge2Docling НЕ запускался.")
    print("=" * 80)


if __name__ == "__main__":
    main()

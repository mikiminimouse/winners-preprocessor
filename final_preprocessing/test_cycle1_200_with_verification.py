#!/usr/bin/env python3
"""
Детальный тест Cycle 1 на 200 UNITs с проверкой перемещения файлов
"""
import sys
import os
from pathlib import Path
import json
from collections import defaultdict
import shutil

from docprep.engine.classifier import Classifier

def check_unit_files(unit_path: Path):
    """Проверяет файлы в UNIT"""
    files = []
    if not unit_path.exists():
        return files

    for item in unit_path.iterdir():
        if item.is_file():
            # Игнорируем системные файлы
            if item.name not in ['manifest.json', 'audit.log.jsonl', 'unit.meta.json',
                                 'docprep.contract.json', 'raw_url_map.json']:
                files.append({
                    'name': item.name,
                    'size': item.stat().st_size,
                    'path': str(item)
                })
    return files

def test_cycle1_200units_with_verification():
    """Тестирует классификацию на 200 UNITs с проверкой файлов"""

    # Инициализируем классификатор
    classifier = Classifier()

    # Читаем список UNITs
    with open("/tmp/test_200_units_2025_03_18.txt", "r") as f:
        units = [line.strip() for line in f if line.strip()]

    input_dir = Path("/root/winners_preprocessor/final_preprocessing/Data/2025-03-18/Input")
    protocol_date = "2025-03-18"

    results = []
    stats = {
        'total': len(units),
        'processed': 0,
        'errors': 0,
        'files_moved': 0,
        'files_remained': 0,
        'by_category': defaultdict(int),
        'by_destination': defaultdict(list),
        'by_file_type': defaultdict(int),
        'exceptions_details': defaultdict(list),  # Детали Exceptions
    }

    print("=" * 80)
    print("ДЕТАЛЬНЫЙ ТЕСТ CYCLE 1: 200 UNITs с проверкой перемещения")
    print("=" * 80)
    print(f"\nДата: {protocol_date}")
    print(f"Всего UNITs: {len(units)}")
    print(f"Режим: dry_run=True (БЕЗ реального перемещения)")
    print("\nОбработка...")

    for i, unit_name in enumerate(units, 1):
        unit_path = input_dir / unit_name

        if not unit_path.exists():
            stats['errors'] += 1
            continue

        # Прогресс каждые 20 UNITs
        if i % 20 == 0:
            print(f"  [{i}/{len(units)}] обработано...")

        # 1. Проверяем файлы ДО
        files_before = check_unit_files(unit_path)

        try:
            # 2. Классифицируем UNIT (dry_run=True - БЕЗ перемещения)
            result = classifier.classify_unit(
                unit_path=unit_path,
                cycle=1,
                protocol_date=protocol_date,
                dry_run=True,  # ВАЖНО: сначала только тест
            )

            stats['processed'] += 1

            # Собираем статистику
            category = result['unit_category']
            stats['by_category'][category] += 1

            # Определяем destination
            target = result['target_directory']
            if 'Merge' in target and 'Direct' in target:
                destination = "Merge/Direct"
                destination_category = "merge_direct"
            elif 'Processing' in target:
                if 'Convert' in target:
                    destination = "Processing_1/Convert"
                    destination_category = "processing_convert"
                elif 'Extract' in target:
                    destination = "Processing_1/Extract"
                    destination_category = "processing_extract"
                elif 'Normalize' in target:
                    destination = "Processing_1/Normalize"
                    destination_category = "processing_normalize"
                else:
                    destination = "Processing_1/Other"
                    destination_category = "processing_other"
            elif 'Exception' in target:
                if 'Empty' in target:
                    destination = "Exceptions_1/Empty"
                    destination_category = "exceptions_empty"
                elif 'Special' in target:
                    destination = "Exceptions_1/Special"
                    destination_category = "exceptions_special"
                    # Записываем детали Special
                    stats['exceptions_details']['special'].append({
                        'unit': unit_name,
                        'files': [f['name'] for f in files_before]
                    })
                elif 'Ambiguous' in target:
                    destination = "Exceptions_1/Ambiguous"
                    destination_category = "exceptions_ambiguous"
                    # Записываем детали Ambiguous
                    stats['exceptions_details']['ambiguous'].append({
                        'unit': unit_name,
                        'files': [f['name'] for f in files_before]
                    })
                else:
                    destination = "Exceptions_1/Other"
                    destination_category = "exceptions_other"
            else:
                destination = "Unknown"
                destination_category = "unknown"

            stats['by_destination'][destination].append(unit_name)

            # Собираем типы файлов
            for fc in result.get('file_classifications', []):
                file_type = fc['classification'].get('detected_type', 'unknown')
                stats['by_file_type'][file_type] += 1

            # 3. Проверяем файлы ПОСЛЕ (в dry_run они не должны измениться)
            files_after = check_unit_files(unit_path)

            # Считаем сколько файлов
            files_count = len(files_before)
            if files_count > 0:
                # В dry_run файлы должны остаться
                if len(files_after) == len(files_before):
                    stats['files_remained'] += files_count
                else:
                    # Это странно в dry_run режиме
                    print(f"\n  ⚠️  {unit_name}: файлов ДО={len(files_before)}, ПОСЛЕ={len(files_after)}")

            results.append({
                'unit_name': unit_name,
                'category': category,
                'is_mixed': result['is_mixed'],
                'files_count_before': len(files_before),
                'files_count_after': len(files_after),
                'files_before': [f['name'] for f in files_before],
                'destination': destination,
                'destination_category': destination_category,
                'target_directory': str(result['target_directory']),
            })

        except Exception as e:
            stats['errors'] += 1
            print(f"\n  ❌ {unit_name}: {e}")
            results.append({
                'unit_name': unit_name,
                'error': str(e),
            })

    # Вывод статистики
    print("\n" + "=" * 80)
    print("ДЕТАЛЬНАЯ СТАТИСТИКА")
    print("=" * 80)

    print(f"\n✅ Обработано: {stats['processed']}/{stats['total']}")
    if stats['errors'] > 0:
        print(f"❌ Ошибок: {stats['errors']}")

    print("\n" + "─" * 80)
    print("📊 РАСПРЕДЕЛЕНИЕ ПО КАТЕГОРИЯМ")
    print("─" * 80)
    for category, count in sorted(stats['by_category'].items(), key=lambda x: -x[1]):
        percentage = (count / stats['processed']) * 100 if stats['processed'] > 0 else 0
        bar = "█" * int(percentage / 2)
        print(f"  {category:12} : {count:4} ({percentage:5.1f}%) {bar}")

    print("\n" + "─" * 80)
    print("📍 ДЕТАЛЬНОЕ РАСПРЕДЕЛЕНИЕ ПО МАРШРУТАМ")
    print("─" * 80)

    # Группируем
    merge_count = len(stats['by_destination'].get('Merge/Direct', []))
    processing_convert = len(stats['by_destination'].get('Processing_1/Convert', []))
    processing_extract = len(stats['by_destination'].get('Processing_1/Extract', []))
    processing_normalize = len(stats['by_destination'].get('Processing_1/Normalize', []))
    exceptions_empty = len(stats['by_destination'].get('Exceptions_1/Empty', []))
    exceptions_special = len(stats['by_destination'].get('Exceptions_1/Special', []))
    exceptions_ambiguous = len(stats['by_destination'].get('Exceptions_1/Ambiguous', []))

    processing_total = processing_convert + processing_extract + processing_normalize
    exceptions_total = exceptions_empty + exceptions_special + exceptions_ambiguous

    print(f"\n  🟢 Merge_0/Direct (готовы к Docling):")
    print(f"     {merge_count} UNITs ({(merge_count/stats['processed']*100):.1f}%)")

    print(f"\n  🔵 Processing_1 (требуют обработки):")
    print(f"     Всего: {processing_total} UNITs ({(processing_total/stats['processed']*100):.1f}%)")
    print(f"       • Convert:   {processing_convert}")
    print(f"       • Extract:   {processing_extract}")
    print(f"       • Normalize: {processing_normalize}")

    print(f"\n  🔴 Exceptions_1 (исключения):")
    print(f"     Всего: {exceptions_total} UNITs ({(exceptions_total/stats['processed']*100):.1f}%)")
    print(f"       • Empty:     {exceptions_empty}")
    print(f"       • Special:   {exceptions_special}")
    print(f"       • Ambiguous: {exceptions_ambiguous}")

    # Детали Exceptions (если есть)
    if exceptions_special > 0:
        print(f"\n  🔎 Детали Special Exceptions:")
        for item in stats['exceptions_details']['special'][:5]:  # первые 5
            print(f"     - {item['unit']}: {', '.join(item['files'][:3])}")

    if exceptions_ambiguous > 0:
        print(f"\n  🔎 Детали Ambiguous Exceptions:")
        for item in stats['exceptions_details']['ambiguous'][:5]:  # первые 5
            print(f"     - {item['unit']}: {', '.join(item['files'][:3])}")

    print("\n" + "─" * 80)
    print("📄 ТОП-15 ТИПОВ ФАЙЛОВ")
    print("─" * 80)
    top_types = sorted(stats['by_file_type'].items(), key=lambda x: -x[1])[:15]
    for file_type, count in top_types:
        print(f"  {file_type:25} : {count:4}")

    print("\n" + "─" * 80)
    print("📦 ПРОВЕРКА ПЕРЕМЕЩЕНИЯ ФАЙЛОВ")
    print("─" * 80)
    print(f"  Файлов осталось в Input (dry_run): {stats['files_remained']}")
    print(f"  ⚠️  dry_run=True режим - файлы НЕ перемещаются")

    # Сохраняем результаты
    output_file = "/tmp/cycle1_200units_2025_03_18_results.json"
    with open(output_file, "w") as f:
        json.dump({
            'stats': {
                'total': stats['total'],
                'processed': stats['processed'],
                'errors': stats['errors'],
                'files_remained': stats['files_remained'],
                'by_category': dict(stats['by_category']),
                'by_destination': {k: len(v) for k, v in stats['by_destination'].items()},
                'by_file_type': dict(stats['by_file_type']),
                'exceptions_details': {
                    'special': stats['exceptions_details']['special'],
                    'ambiguous': stats['exceptions_details']['ambiguous'],
                },
            },
            'results': results
        }, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Полные результаты сохранены: {output_file}")

    # Создаём детальный отчёт
    summary_file = "/tmp/cycle1_200units_2025_03_18_summary.txt"
    with open(summary_file, "w") as f:
        f.write("=" * 80 + "\n")
        f.write("ДЕТАЛЬНАЯ СВОДКА: CYCLE 1 TEST (200 UNITs из 2025-03-18)\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Обработано: {stats['processed']}/{stats['total']}\n")
        f.write(f"Ошибок: {stats['errors']}\n\n")
        f.write("РАСПРЕДЕЛЕНИЕ:\n")
        f.write(f"  ✅ Merge/Direct:          {merge_count:4} ({(merge_count/stats['processed']*100):.1f}%)\n")
        f.write(f"  🔄 Processing_1/Convert:  {processing_convert:4}\n")
        f.write(f"  📦 Processing_1/Extract:  {processing_extract:4}\n")
        f.write(f"  🔧 Processing_1/Normalize:{processing_normalize:4}\n")
        f.write(f"  ⚠️  Exceptions_1/Empty:    {exceptions_empty:4}\n")
        f.write(f"  ⚠️  Exceptions_1/Special:  {exceptions_special:4}\n")
        f.write(f"  ⚠️  Exceptions_1/Ambiguous:{exceptions_ambiguous:4}\n")
        f.write(f"\n  ВСЕГО Exceptions: {exceptions_total:4} ({(exceptions_total/stats['processed']*100):.1f}%)\n")

    print(f"📄 Краткая сводка: {summary_file}")
    print("\n" + "=" * 80)

    return results, stats


if __name__ == "__main__":
    test_cycle1_200units_with_verification()

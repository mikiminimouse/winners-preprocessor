#!/usr/bin/env python3
"""
Тест Cycle 1 на 100 случайных UNITs
"""
import sys
from pathlib import Path
import json
from collections import defaultdict

from docprep.engine.classifier import Classifier

def test_cycle1_100units():
    """Тестирует классификацию на 100 UNITs"""

    # Инициализируем классификатор
    classifier = Classifier()

    # Читаем список UNITs для теста
    with open("/tmp/test_100_units.txt", "r") as f:
        units = [line.strip() for line in f if line.strip()]

    input_dir = Path("/root/winners_preprocessor/final_preprocessing/Data/2025-03-04/Input")
    protocol_date = "2025-03-04"

    results = []
    stats = {
        'total': len(units),
        'processed': 0,
        'errors': 0,
        'by_category': defaultdict(int),
        'by_destination': defaultdict(list),
        'by_file_type': defaultdict(int),
    }

    print("=" * 80)
    print("ТЕСТ CYCLE 1: 100 случайных UNITs")
    print("=" * 80)
    print(f"\nВсего UNITs: {len(units)}")
    print(f"Protocol Date: {protocol_date}")
    print("\nОбработка...")

    for i, unit_name in enumerate(units, 1):
        unit_path = input_dir / unit_name

        if not unit_path.exists():
            stats['errors'] += 1
            continue

        # Прогресс каждые 10 UNITs
        if i % 10 == 0:
            print(f"  [{i}/{len(units)}] обработано...")

        try:
            # Классифицируем UNIT (dry_run=True)
            result = classifier.classify_unit(
                unit_path=unit_path,
                cycle=1,
                protocol_date=protocol_date,
                dry_run=True,
            )

            stats['processed'] += 1

            # Собираем статистику
            category = result['unit_category']
            stats['by_category'][category] += 1

            # Определяем destination
            target = result['target_directory']
            if 'Merge' in target and 'Direct' in target:
                destination = "Merge/Direct"
            elif 'Processing' in target:
                if 'Convert' in target:
                    destination = "Processing_1/Convert"
                elif 'Extract' in target:
                    destination = "Processing_1/Extract"
                elif 'Normalize' in target:
                    destination = "Processing_1/Normalize"
                else:
                    destination = "Processing_1/Other"
            elif 'Exception' in target:
                if 'Empty' in target:
                    destination = "Exceptions_1/Empty"
                elif 'Special' in target:
                    destination = "Exceptions_1/Special"
                elif 'Ambiguous' in target:
                    destination = "Exceptions_1/Ambiguous"
                else:
                    destination = "Exceptions_1/Other"
            else:
                destination = "Unknown"

            stats['by_destination'][destination].append(unit_name)

            # Собираем типы файлов
            for fc in result.get('file_classifications', []):
                file_type = fc['classification'].get('detected_type', 'unknown')
                stats['by_file_type'][file_type] += 1

            results.append({
                'unit_name': unit_name,
                'category': category,
                'is_mixed': result['is_mixed'],
                'file_count': len(result.get('file_classifications', [])),
                'destination': destination,
                'target_directory': str(result['target_directory']),
            })

        except Exception as e:
            stats['errors'] += 1
            results.append({
                'unit_name': unit_name,
                'error': str(e),
            })

    # Вывод статистики
    print("\n" + "=" * 80)
    print("СТАТИСТИКА РЕЗУЛЬТАТОВ")
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
        print(f"  {category:12} : {count:3} ({percentage:5.1f}%) {bar}")

    print("\n" + "─" * 80)
    print("📍 РАСПРЕДЕЛЕНИЕ ПО МАРШРУТАМ (Web UI Cycle 1)")
    print("─" * 80)

    # Группируем по основным направлениям
    merge_count = len(stats['by_destination'].get('Merge/Direct', []))
    processing_convert = len(stats['by_destination'].get('Processing_1/Convert', []))
    processing_extract = len(stats['by_destination'].get('Processing_1/Extract', []))
    processing_normalize = len(stats['by_destination'].get('Processing_1/Normalize', []))
    exceptions_total = sum(len(v) for k, v in stats['by_destination'].items() if 'Exception' in k)

    processing_total = processing_convert + processing_extract + processing_normalize

    print(f"\n  🟢 Merge_0/Direct (готовы к Docling):")
    print(f"     {merge_count} UNITs ({(merge_count/stats['processed']*100):.1f}%)")

    print(f"\n  🔵 Processing_1 (требуют обработки):")
    print(f"     Всего: {processing_total} UNITs ({(processing_total/stats['processed']*100):.1f}%)")
    print(f"       • Convert:   {processing_convert}")
    print(f"       • Extract:   {processing_extract}")
    print(f"       • Normalize: {processing_normalize}")

    print(f"\n  🔴 Exceptions_1 (исключения):")
    print(f"     {exceptions_total} UNITs ({(exceptions_total/stats['processed']*100):.1f}%)")
    for dest, units_list in sorted(stats['by_destination'].items()):
        if 'Exception' in dest:
            print(f"       • {dest.split('/')[-1]}: {len(units_list)}")

    print("\n" + "─" * 80)
    print("📄 ТОП-10 ТИПОВ ФАЙЛОВ")
    print("─" * 80)
    top_types = sorted(stats['by_file_type'].items(), key=lambda x: -x[1])[:10]
    for file_type, count in top_types:
        print(f"  {file_type:20} : {count:3}")

    # Детальный список для каждого направления (первые 5)
    print("\n" + "─" * 80)
    print("📋 ПРИМЕРЫ UNITS ПО НАПРАВЛЕНИЯМ")
    print("─" * 80)

    for dest in ['Merge/Direct', 'Processing_1/Convert', 'Processing_1/Extract', 'Exceptions_1/Empty']:
        units_list = stats['by_destination'].get(dest, [])
        if units_list:
            print(f"\n  {dest}: (показано {min(5, len(units_list))} из {len(units_list)})")
            for unit in units_list[:5]:
                print(f"    - {unit}")

    # Сохраняем результаты
    output_file = "/tmp/cycle1_100units_results.json"
    with open(output_file, "w") as f:
        json.dump({
            'stats': {
                'total': stats['total'],
                'processed': stats['processed'],
                'errors': stats['errors'],
                'by_category': dict(stats['by_category']),
                'by_destination': {k: len(v) for k, v in stats['by_destination'].items()},
                'by_file_type': dict(stats['by_file_type']),
            },
            'results': results
        }, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Полные результаты сохранены: {output_file}")

    # Создаём краткий отчёт
    summary_file = "/tmp/cycle1_100units_summary.txt"
    with open(summary_file, "w") as f:
        f.write("=" * 80 + "\n")
        f.write("КРАТКАЯ СВОДКА: CYCLE 1 TEST (100 UNITs)\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Обработано: {stats['processed']}/{stats['total']}\n")
        f.write(f"Ошибок: {stats['errors']}\n\n")
        f.write("РАСПРЕДЕЛЕНИЕ:\n")
        f.write(f"  ✅ Merge/Direct:         {merge_count} ({(merge_count/stats['processed']*100):.1f}%)\n")
        f.write(f"  🔄 Processing_1/Convert: {processing_convert}\n")
        f.write(f"  📦 Processing_1/Extract: {processing_extract}\n")
        f.write(f"  🔧 Processing_1/Normalize: {processing_normalize}\n")
        f.write(f"  ⚠️  Exceptions_1:         {exceptions_total} ({(exceptions_total/stats['processed']*100):.1f}%)\n")

    print(f"📄 Краткая сводка: {summary_file}")
    print("\n" + "=" * 80)

    return results, stats


if __name__ == "__main__":
    test_cycle1_100units()

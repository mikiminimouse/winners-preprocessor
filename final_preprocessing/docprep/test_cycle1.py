#!/usr/bin/env python3
"""
Тестовый скрипт для проверки Cycle 1 классификации
"""
import sys
from pathlib import Path
import json

# Добавляем путь к модулю
sys.path.insert(0, str(Path(__file__).parent))

from engine.classifier import Classifier

def test_cycle1_sample():
    """Тестирует классификацию на выборке из 10 UNITs"""

    # Инициализируем классификатор
    classifier = Classifier()

    # Читаем список UNITs для теста
    with open("/tmp/test_units.txt", "r") as f:
        units = [line.strip() for line in f if line.strip()]

    input_dir = Path("/root/winners_preprocessor/final_preprocessing/Data/2025-03-04/Input")
    protocol_date = "2025-03-04"

    results = []

    print("=" * 80)
    print("ТЕСТ CYCLE 1: Классификация и Distribution")
    print("=" * 80)
    print(f"\nВсего UNITs для теста: {len(units)}")
    print(f"Protocol Date: {protocol_date}")
    print("\n" + "-" * 80)

    for i, unit_name in enumerate(units, 1):
        unit_path = input_dir / unit_name

        if not unit_path.exists():
            print(f"\n[{i}/{len(units)}] ❌ {unit_name}: НЕ НАЙДЕН")
            continue

        print(f"\n[{i}/{len(units)}] 🔍 {unit_name}")
        print("-" * 80)

        try:
            # Классифицируем UNIT (dry_run=True)
            result = classifier.classify_unit(
                unit_path=unit_path,
                cycle=1,
                protocol_date=protocol_date,
                dry_run=True,
            )

            # Выводим результаты
            print(f"  Категория UNIT: {result['unit_category']}")
            print(f"  Is Mixed: {result['is_mixed']}")
            print(f"  Файлов: {len(result.get('file_classifications', []))}")

            if result.get('file_classifications'):
                print(f"\n  Классификация файлов:")
                for fc in result['file_classifications']:
                    file_name = Path(fc['file_path']).name
                    classification = fc['classification']
                    print(f"    • {file_name}")
                    print(f"      Category: {classification['category']}")
                    print(f"      Type: {classification.get('detected_type', 'unknown')}")
                    print(f"      MIME: {classification.get('mime_type', 'unknown')}")
                    if classification.get('needs_conversion'):
                        print(f"      ⚠️  Требует конвертации")
                    if classification.get('needs_extraction'):
                        print(f"      📦 Требует разархивации")
                    if classification.get('needs_normalization'):
                        print(f"      🔧 Требует нормализации")

            print(f"\n  🎯 Целевая директория:")
            print(f"     {result['target_directory']}")

            # Определяем куда пойдёт UNIT
            target = result['target_directory']
            if 'Merge' in target and 'Direct' in target:
                destination = "✅ Merge/Direct (готов)"
            elif 'Processing' in target:
                if 'Convert' in target:
                    destination = "🔄 Processing_1/Convert"
                elif 'Extract' in target:
                    destination = "📦 Processing_1/Extract"
                elif 'Normalize' in target:
                    destination = "🔧 Processing_1/Normalize"
                else:
                    destination = "📁 Processing_1"
            elif 'Exception' in target:
                if 'Empty' in target:
                    destination = "⚠️  Exceptions_1/Empty"
                elif 'Special' in target:
                    destination = "⚠️  Exceptions_1/Special"
                elif 'Ambiguous' in target:
                    destination = "⚠️  Exceptions_1/Ambiguous"
                else:
                    destination = "⚠️  Exceptions_1"
            else:
                destination = "❓ Неизвестно"

            print(f"\n  📍 Маршрут: {destination}")

            results.append({
                'unit_name': unit_name,
                'category': result['unit_category'],
                'is_mixed': result['is_mixed'],
                'file_count': len(result.get('file_classifications', [])),
                'destination': destination,
                'target_directory': str(result['target_directory']),
            })

        except Exception as e:
            print(f"  ❌ ОШИБКА: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                'unit_name': unit_name,
                'error': str(e),
            })

    # Сводка
    print("\n" + "=" * 80)
    print("СВОДКА РЕЗУЛЬТАТОВ")
    print("=" * 80)

    # Подсчёт по маршрутам
    destinations = {}
    for r in results:
        if 'destination' in r:
            dest = r['destination']
            if dest not in destinations:
                destinations[dest] = []
            destinations[dest].append(r['unit_name'])

    print("\n📊 Распределение по маршрутам:")
    for dest, units_list in sorted(destinations.items()):
        print(f"\n  {dest}: {len(units_list)} UNITs")
        for unit in units_list:
            print(f"    - {unit}")

    # Сохраняем результаты
    output_file = "/tmp/cycle1_test_results.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Результаты сохранены: {output_file}")
    print("\n" + "=" * 80)

    return results


if __name__ == "__main__":
    test_cycle1_sample()

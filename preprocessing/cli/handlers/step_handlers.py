"""
Handlers для пошаговой обработки (пункты меню 9-14).

Включает функции:
- handle_step1_scan_and_detect: сканирование и детекция типов
- handle_step2_classify: классификация файлов
- handle_step3_check_duplicates: проверка дубликатов
- handle_step4_check_mixed: определение mixed units
- handle_step5_distribute: распределение по pending
- handle_full_processing: полная обработка всех шагов
"""

from pathlib import Path
import shutil
from typing import Optional
from ...router.iterative_processor import IterativeProcessor
from ...router.merge import final_merge_to_ready_docling
from ...router.config import PROCESSING_BASE_DIR, PENDING_1_DIR, MERGE_1_DIR, MERGE_2_DIR, MERGE_3_DIR
from ..utils import calculate_sha256


def handle_step1_scan_and_detect(cli_instance, limit: Optional[int] = None):
    """ШАГ 1: Сканирование и детекция типов файлов."""
    print("\n=== ШАГ 1: СКАНИРОВАНИЕ И ДЕТЕКЦИЯ ТИПОВ ФАЙЛОВ ===")

    if limit is None:
        limit_str = input("Лимит файлов для обработки (Enter = все): ").strip()
        limit = int(limit_str) if limit_str else None

    print(f"🔍 Сканирование INPUT_DIR: {cli_instance.INPUT_DIR}")

    files = [f for f in cli_instance.INPUT_DIR.rglob("*") if f.is_file()]
    files = [f for f in files if f.is_file() and not f.name.startswith('.')]

    if limit:
        files = files[:limit]

    print(f"📄 Найдено файлов: {len(files)}")

    processed = 0
    for file_path in files:
        try:
            # Используем существующую функцию детекции
            detection = cli_instance.detect_file_type(file_path)
            detected_type = detection.get("detected_type", "unknown")
            mime_type = detection.get("mime_type", "")
            needs_ocr = detection.get("needs_ocr", False)

            print(f"  📄 {file_path.name} → {detected_type} ({mime_type})")
            processed += 1

        except Exception as e:
            print(f"  ❌ {file_path.name}: {e}")

    print(f"\n✅ ШАГ 1 завершен!")
    print(f"   Обработано файлов: {processed}")


def handle_step2_classify(cli_instance, limit: Optional[int] = None):
    """ШАГ 2: Классификация файлов по категориям."""
    print("\n=== ШАГ 2: КЛАССИФИКАЦИЯ ФАЙЛОВ ПО КАТЕГОРИЯМ ===")

    if limit is None:
        limit_str = input("Лимит файлов для обработки (Enter = все): ").strip()
        limit = int(limit_str) if limit_str else None

    print("📋 Классификация файлов...")
    print("   Категории: direct, normalize, convert, extract, special, mixed")

    files = [f for f in cli_instance.INPUT_DIR.rglob("*") if f.is_file()]
    files = [f for f in files if f.is_file() and not f.name.startswith('.')]

    if limit:
        files = files[:limit]

    categories = {
        "direct": 0,
        "normalize": 0,
        "convert": 0,
        "extract": 0,
        "special": 0
    }

    for file_path in files:
        try:
            detection = cli_instance.detect_file_type(file_path)
            detected_type = detection.get("detected_type", "unknown")

            # Простая классификация
            if detected_type in ["pdf", "docx", "txt"]:
                category = "direct"
            elif detected_type in ["doc", "xls", "ppt"]:
                category = "convert"
            elif detected_type in ["zip", "rar", "7z"]:
                category = "extract"
            else:
                category = "special"

            categories[category] += 1
            print(f"  📄 {file_path.name} → {category} ({detected_type})")

        except Exception as e:
            print(f"  ❌ {file_path.name}: {e}")

    print("\n📊 Статистика по категориям:")
    for category, count in categories.items():
        print(f"   {category}: {count}")

    print("\n✅ ШАГ 2 завершен!")


def handle_step3_check_duplicates(cli_instance, limit: Optional[int] = None):
    """ШАГ 3: Проверка дубликатов."""
    print("\n=== ШАГ 3: ПРОВЕРКА ДУБЛИКАТОВ ===")

    if limit is None:
        limit_str = input("Лимит файлов для проверки (Enter = все): ").strip()
        limit = int(limit_str) if limit_str else None

    print("🔍 Поиск дубликатов по хэшам...")

    files = [f for f in cli_instance.INPUT_DIR.rglob("*") if f.is_file()]
    files = [f for f in files if f.is_file() and not f.name.startswith('.')]

    if limit:
        files = files[:limit]

    hashes = {}
    duplicates = []

    for file_path in files:
        try:
            file_hash = calculate_sha256(file_path)
            if file_hash in hashes:
                duplicates.append((file_path, hashes[file_hash]))
                print(f"  🔄 Дубликат: {file_path.name} == {hashes[file_hash].name}")
            else:
                hashes[file_hash] = file_path
                print(f"  ✅ Уникальный: {file_path.name}")

        except Exception as e:
            print(f"  ❌ {file_path.name}: {e}")

    print(f"\n📊 Результаты проверки дубликатов:")
    print(f"   Уникальных файлов: {len(hashes)}")
    print(f"   Дубликатов: {len(duplicates)}")

    print("\n✅ ШАГ 3 завершен!")


def handle_step4_check_mixed(cli_instance, limit: Optional[int] = None):
    """ШАГ 4: Определение mixed units."""
    print("\n=== ШАГ 4: ОПРЕДЕЛЕНИЕ MIXED UNITS ===")

    if limit is None:
        limit_str = input("Лимит units для проверки (Enter = все): ").strip()
        limit = int(limit_str) if limit_str else None

    print("🔍 Анализ units на смешанный контент...")

    # Получаем список units
    unit_dirs = [d for d in cli_instance.NORMALIZED_DIR.iterdir() if d.is_dir() and d.name.startswith("UNIT_")]

    if limit:
        unit_dirs = unit_dirs[:limit]

    mixed_units = []
    simple_units = []

    for unit_dir in unit_dirs:
        try:
            files = list(unit_dir.glob("files/*"))
            file_types = set()

            for file_path in files:
                detection = cli_instance.detect_file_type(file_path)
                file_types.add(detection.get("detected_type", "unknown"))

            if len(file_types) > 1:
                mixed_units.append((unit_dir.name, file_types))
                print(f"  🔀 Mixed: {unit_dir.name} ({', '.join(file_types)})")
            else:
                simple_units.append(unit_dir.name)
                print(f"  📄 Simple: {unit_dir.name} ({list(file_types)[0] if file_types else 'empty'})")

        except Exception as e:
            print(f"  ❌ {unit_dir.name}: {e}")

    print(f"\n📊 Результаты анализа:")
    print(f"   Simple units: {len(simple_units)}")
    print(f"   Mixed units: {len(mixed_units)}")

    print("\n✅ ШАГ 4 завершен!")


def handle_step5_distribute(cli_instance, limit: Optional[int] = None):
    """ШАГ 5: Распределение по pending директориям."""
    print("\n=== ШАГ 5: РАСПРЕДЕЛЕНИЕ ПО PENDING ДИРЕКТОРИЯМ ===")

    if limit is None:
        limit_str = input("Лимит файлов для распределения (Enter = все): ").strip()
        limit = int(limit_str) if limit_str else None

    print("📦 Распределение файлов по категориям...")
    print("   Директории: direct/, normalize/, convert/, extract/")

    # Создаем pending директории если нужно
    pending_base = cli_instance.INPUT_DIR.parent / "pending"
    categories = ["direct", "normalize", "convert", "extract", "special"]

    for category in categories:
        (pending_base / category).mkdir(parents=True, exist_ok=True)

    files = [f for f in cli_instance.INPUT_DIR.rglob("*") if f.is_file()]
    files = [f for f in files if f.is_file() and not f.name.startswith('.')]

    if limit:
        files = files[:limit]

    distributed = {cat: 0 for cat in categories}

    for file_path in files:
        try:
            detection = cli_instance.detect_file_type(file_path)
            detected_type = detection.get("detected_type", "unknown")

            # Определяем категорию для распределения
            if detected_type in ["pdf", "docx", "txt"]:
                category = "direct"
            elif detected_type in ["doc", "xls", "ppt"]:
                category = "convert"
            elif detected_type in ["zip", "rar", "7z"]:
                category = "extract"
            else:
                category = "special"

            # Копируем файл в соответствующую директорию
            dest_dir = pending_base / category
            dest_path = dest_dir / file_path.name

            shutil.copy2(file_path, dest_path)
            distributed[category] += 1

            print(f"  📦 {file_path.name} → {category}/")

        except Exception as e:
            print(f"  ❌ {file_path.name}: {e}")

    print("\n📊 Распределение по категориям:")
    for category, count in distributed.items():
        print(f"   {category}: {count} файлов")

    total_distributed = sum(distributed.values())
    print(f"   Всего распределено: {total_distributed}")

    print("\n✅ ШАГ 5 завершен!")


def handle_full_processing(cli_instance, limit: Optional[int] = None):
    """Полная обработка: все шаги 1-5."""
    print("\n=== ПОЛНАЯ ОБРАБОТКА: ВСЕ ШАГИ (1-5) ===")

    if limit is None:
        limit_str = input("Лимит для каждого шага (Enter = без ограничений): ").strip()
        limit = int(limit_str) if limit_str else None

    print("🚀 Запуск полной обработки...")
    print("   ШАГ 1: Сканирование и детекция")
    print("   ШАГ 2: Классификация")
    print("   ШАГ 3: Проверка дубликатов")
    print("   ШАГ 4: Определение mixed units")
    print("   ШАГ 5: Распределение")
    print()

    # Выполняем все шаги последовательно
    try:
        print("📋 ШАГ 1...")
        handle_step1_scan_and_detect(cli_instance, limit)

        print("\n📋 ШАГ 2...")
        handle_step2_classify(cli_instance, limit)

        print("\n📋 ШАГ 3...")
        handle_step3_check_duplicates(cli_instance, limit)

        print("\n📋 ШАГ 4...")
        handle_step4_check_mixed(cli_instance, limit)

        print("\n📋 ШАГ 5...")
        handle_step5_distribute(cli_instance, limit)

        print("\n🎉 ПОЛНАЯ ОБРАБОТКА ЗАВЕРШЕНА!")

    except Exception as e:
        print(f"\n❌ Ошибка в полной обработке: {e}")


def handle_iterative_processing(cli_instance, unit_id: Optional[str] = None, limit: Optional[int] = None):
    """
    Итеративная обработка UNIT согласно PRD раздел 8.
    
    Обрабатывает UNIT через циклы:
    - Cycle 1: Classifier → Pending_1/Merge_1/Exceptions_1
    - Cycle 2: Pending_1 → обработка → Classifier → Merge_2/Pending_2/Exceptions_2
    - Cycle 3: Pending_2 → обработка → Classifier → Merge_3/Exceptions_3
    """
    print("\n=== ИТЕРАТИВНАЯ ОБРАБОТКА UNIT ===")
    
    if unit_id is None:
        unit_id_str = input("ID UNIT для обработки (Enter = все из Pending_1): ").strip()
        unit_id = unit_id_str if unit_id_str else None
    
    if limit is None and unit_id is None:
        limit_str = input("Лимит UNIT для обработки (Enter = все): ").strip()
        limit = int(limit_str) if limit_str else None
    
    # Находим UNIT для обработки
    if unit_id:
        unit_ids = [unit_id]
    else:
        # Ищем все UNIT в Pending_1
        unit_ids = []
        if PENDING_1_DIR.exists():
            for unit_dir in PENDING_1_DIR.rglob("UNIT_*"):
                if unit_dir.is_dir():
                    unit_ids.append(unit_dir.name)
        
        if limit:
            unit_ids = unit_ids[:limit]
    
    if not unit_ids:
        print("❌ UNIT не найдены в Pending_1")
        return
    
    print(f"📋 Найдено UNIT для обработки: {len(unit_ids)}")
    
    results = []
    for uid in unit_ids:
        try:
            print(f"\n🔄 Обработка {uid}...")
            
            # Находим manifest
            manifest_path = None
            for search_dir in [PENDING_1_DIR, MERGE_1_DIR, MERGE_2_DIR, MERGE_3_DIR]:
                if search_dir.exists():
                    manifest_candidates = list(search_dir.rglob(f"{uid}/manifest.json"))
                    if manifest_candidates:
                        manifest_path = manifest_candidates[0]
                        break
            
            # Создаем IterativeProcessor
            processor = IterativeProcessor(uid, manifest_path)
            
            # Обрабатываем все циклы
            result = processor.process_all_cycles()
            results.append(result)
            
            print(f"  ✅ {uid}: {result.get('final_state', 'unknown')}")
            print(f"     Циклов обработано: {len(result.get('cycles_processed', []))}")
            
        except Exception as e:
            print(f"  ❌ {uid}: {e}")
            results.append({
                "unit_id": uid,
                "status": "error",
                "error": str(e)
            })
    
    # Статистика
    print("\n📊 Результаты итеративной обработки:")
    successful = sum(1 for r in results if r.get("status") == "completed")
    errors = sum(1 for r in results if r.get("status") == "error")
    
    print(f"   Успешно обработано: {successful}")
    print(f"   Ошибок: {errors}")
    
    final_states = {}
    for r in results:
        state = r.get("final_state", "unknown")
        final_states[state] = final_states.get(state, 0) + 1
    
    if final_states:
        print("\n   Финальные состояния:")
        for state, count in sorted(final_states.items()):
            print(f"     {state}: {count}")
    
    print("\n✅ Итеративная обработка завершена!")


def handle_final_merge(cli_instance, dry_run: bool = False, limit: Optional[int] = None):
    """
    Финальный Merge из Merge_1/2/3 в Ready2Docling согласно PRD раздел 9.
    
    Объединяет все UNIT из Merge кластеров в Ready2Docling с сохранением
    сортировки по расширениям и дополнительной сортировкой PDF на scan/text.
    """
    print("\n=== ФИНАЛЬНЫЙ MERGE В READY2DOCLING ===")
    
    if dry_run:
        print("🔍 РЕЖИМ DRY RUN - изменения не будут применены")
    
    if limit is None:
        limit_str = input("Лимит UNIT для merge (Enter = все): ").strip()
        limit = int(limit_str) if limit_str else None
    
    print("📦 Объединение UNIT из Merge_1/2/3 в Ready2Docling...")
    print("   Сохранение сортировки по расширениям")
    print("   Дополнительная сортировка PDF на scan/text")
    
    try:
        result = final_merge_to_ready_docling(dry_run=dry_run, limit=limit)
        
        print(f"\n📊 Результаты merge:")
        print(f"   Обработано UNIT: {result['units_processed']}")
        print(f"   Перемещено файлов: {result['files_moved']}")
        
        if result['files_by_type']:
            print("\n   По типам файлов:")
            for file_type, count in sorted(result['files_by_type'].items()):
                print(f"     {file_type}: {count}")
        
        if result['pdf_by_category']:
            print("\n   PDF по категориям:")
            print(f"     scan: {result['pdf_by_category']['scan']}")
            print(f"     text: {result['pdf_by_category']['text']}")
        
        if result['errors']:
            print(f"\n   ⚠ Ошибок: {len(result['errors'])}")
            for error in result['errors'][:5]:
                print(f"     - {error.get('error', 'Unknown error')}")
        
        print(f"\n   Начало: {result['started_at']}")
        print(f"   Завершение: {result.get('completed_at', 'В процессе...')}")
        
        print("\n✅ Финальный Merge завершен!")
        
    except Exception as e:
        print(f"\n❌ Ошибка в финальном Merge: {e}")
        import traceback
        traceback.print_exc()

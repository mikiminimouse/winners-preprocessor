#!/usr/bin/env python3
"""
CLI для тестирования и управления этапами препроцессинга документов.

Интегрирует функции из router/main.py и добавляет возможности тестирования
всех этапов pipeline: загрузка, распаковка, нормализация, Docling обработка.
"""
import sys
import json
import time
import requests
import shutil
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

# Импортируем функции из router модулей
try:
    from router.config import (
        INPUT_DIR, TEMP_DIR, OUTPUT_DIR, EXTRACTED_DIR, NORMALIZED_DIR, ARCHIVE_DIR,
        DOCLING_API, PENDING_DIR, PENDING_DIRECT_DIR, PENDING_NORMALIZE_DIR,
        PENDING_CONVERT_DIR, PENDING_EXTRACT_DIR, PENDING_SPECIAL_DIR, PENDING_MIXED_DIR,
        READY_DOCLING_DIR, init_directories
    )
    from router.mongo import (
        get_mongo_metadata_client, get_manifest_from_mongo, get_protocols_by_date, get_mongo_client
    )
    from router.api import process_file, download_document
    from router.metrics import (
        init_processing_metrics, save_processing_metrics, get_current_metrics
    )
    from router.file_detection import detect_file_type
    from router.file_classifier import classify_file
    from router.archive import safe_extract_archive
    from router.utils import calculate_sha256, sanitize_filename
    from router.merge import merge_to_ready_docling, get_ready_docling_statistics, print_merge_summary
    from router.unit_distribution_new import distribute_unit_by_new_structure, get_unit_statistics
    
    ROUTER_AVAILABLE = True
    print("✓ Router модули загружены успешно")
except ImportError as e:
    # Fallback для случаев, когда router не доступен (Docker, etc.)
    import os
    ROUTER_AVAILABLE = False
    INPUT_DIR = Path(os.environ.get("INPUT_DIR", "/app/input"))
    TEMP_DIR = Path(os.environ.get("TEMP_DIR", "/app/temp"))
    OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/app/output"))
    EXTRACTED_DIR = Path(os.environ.get("EXTRACTED_DIR", "/app/extracted"))
    NORMALIZED_DIR = Path(os.environ.get("NORMALIZED_DIR", "/app/normalized"))
    ARCHIVE_DIR = Path(os.environ.get("ARCHIVE_DIR", "/app/archive"))
    DOCLING_API = os.environ.get("DOCLING_API", "http://localhost:8001/process")
    PENDING_DIR = Path(os.environ.get("PENDING_DIR", "/app/pending"))
    PENDING_DIRECT_DIR = PENDING_DIR / "direct"
    PENDING_NORMALIZE_DIR = PENDING_DIR / "normalize"
    PENDING_CONVERT_DIR = PENDING_DIR / "convert"
    PENDING_EXTRACT_DIR = PENDING_DIR / "extract"
    PENDING_SPECIAL_DIR = PENDING_DIR / "special"
    PENDING_MIXED_DIR = PENDING_DIR / "mixed"
    READY_DOCLING_DIR = Path(os.environ.get("READY_DOCLING_DIR", "/app/ready_docling"))

    def get_protocols_by_date(*args, **kwargs):
        return {}

    def download_document(*args, **kwargs):
        return False

    def process_file(*args, **kwargs):
        return {"status": "error", "message": "Router not available"}

    def init_processing_metrics(*args, **kwargs):
        return {"session_id": "fallback", "started_at": datetime.utcnow().isoformat()}

    def save_processing_metrics(*args, **kwargs):
        pass

    def get_manifest_from_mongo(*args, **kwargs):
        return None

    def get_mongo_metadata_client(*args, **kwargs):
        return None

    def get_mongo_client(*args, **kwargs):
        return None

    def get_current_metrics(*args, **kwargs):
        return None

    def detect_file_type(file_path):
        """Fallback для detect_file_type."""
        return {"detected_type": "unknown", "mime_type": "application/octet-stream"}

    def classify_file(file_path, detection_result=None):
        """Fallback для classify_file."""
        return {"category": "special", "detected_type": "unknown"}

    def safe_extract_archive(archive_path, extract_to, archive_id):
        """Fallback для safe_extract_archive."""
        return [], False

    def calculate_sha256(file_path):
        """Fallback для calculate_sha256."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def sanitize_filename(filename):
        """Fallback для sanitize_filename."""
        return Path(filename).name

    def merge_to_ready_docling(*args, **kwargs):
        """Fallback для merge_to_ready_docling."""
        return {"error": "Router not available"}

    def get_ready_docling_statistics():
        """Fallback для get_ready_docling_statistics."""
        return {"total_units": 0, "total_files": 0, "by_type": {}}

    def print_merge_summary(result):
        """Fallback для print_merge_summary."""
        print(f"Merge result: {result}")

    def distribute_unit_by_new_structure(*args, **kwargs):
        """Fallback для distribute_unit_by_new_structure."""
        return {"error": "Router not available"}

    def get_unit_statistics(*args, **kwargs):
        """Fallback для get_unit_statistics."""
        return {}

    def init_directories():
        """Fallback для init_directories."""
        for d in [INPUT_DIR, TEMP_DIR, OUTPUT_DIR, EXTRACTED_DIR, NORMALIZED_DIR, 
                  ARCHIVE_DIR, PENDING_DIR, READY_DOCLING_DIR]:
            d.mkdir(parents=True, exist_ok=True)

    print(f"⚠️  Router модули не доступны: {e}")

# Импорт микросервисов
try:
    from sync_db.service import SyncService
    from downloader.service import ProtocolDownloader
    from downloader.utils import check_zakupki_health
    print("✓ Микросервисы загружены успешно")
except ImportError as e:
    print(f"⚠️  Ошибка при импорте микросервисов: {e}")
    SyncService = None
    ProtocolDownloader = None
    check_zakupki_health = None


class PreprocessingTestCLI:
    """CLI для тестирования препроцессинга."""

    def __init__(self):
        self.metrics = None
        self.session_id = None
        self.local_metrics_dir = Path(__file__).parent / "local_metrics"
        self.local_metrics_dir.mkdir(exist_ok=True)
    
    @staticmethod
    def find_input_files(limit: Optional[int] = None) -> List[Path]:
        """
        Находит все файлы в INPUT_DIR, включая файлы внутри UNIT_* директорий.
        
        Args:
            limit: Ограничение на количество файлов
        
        Returns:
            Список путей к файлам
        """
        # Сначала ищем файлы в корне INPUT_DIR
        files = list(INPUT_DIR.glob("*"))
        files = [f for f in files if f.is_file() and not f.name.startswith('.')]
        
        # Если файлов нет в корне, ищем внутри UNIT_* директорий
        if len(files) == 0:
            unit_dirs = [d for d in INPUT_DIR.iterdir() if d.is_dir() and d.name.startswith("UNIT_")]
            for unit_dir in unit_dirs:
                unit_files = list(unit_dir.glob("*"))
                unit_files = [f for f in unit_files if f.is_file() and not f.name.startswith('.')]
                files.extend(unit_files)
        
        # Применяем лимит
        if limit:
            files = files[:limit]
        
        return files
    
    def save_metrics_local(self, metrics: Optional[Dict[str, Any]] = None) -> bool:
        """Сохраняет метрики локально в JSON файл (fallback если MongoDB недоступна)."""
        if metrics is None:
            metrics = self.metrics
        
        if not metrics:
            return False
        
        try:
            # Обновляем время завершения
            if not metrics.get("completed_at"):
                metrics["completed_at"] = datetime.utcnow().isoformat()
            
            # Сохраняем в JSON файл
            session_id = metrics.get("session_id", "unknown")
            metrics_file = self.local_metrics_dir / f"metrics_{session_id}.json"
            
            with open(metrics_file, "w", encoding="utf-8") as f:
                json.dump(metrics, f, ensure_ascii=False, indent=2)
            
            print(f"💾 Метрики сохранены локально: {metrics_file}")
            return True
        except Exception as e:
            print(f"❌ Ошибка сохранения локальных метрик: {e}")
            return False
    
    def load_metrics_local(self, session_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Загружает метрики из локального JSON файла."""
        try:
            if session_id:
                metrics_file = self.local_metrics_dir / f"metrics_{session_id}.json"
            else:
                # Загружаем последний файл
                metrics_files = sorted(self.local_metrics_dir.glob("metrics_*.json"), key=lambda p: p.stat().st_mtime)
                if not metrics_files:
                    return None
                metrics_file = metrics_files[-1]
            
            if not metrics_file.exists():
                return None
            
            with open(metrics_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Ошибка загрузки локальных метрик: {e}")
            return None

    def show_menu(self):
        """Показывает главное меню."""
        print("\n" + "=" * 60)
        print("=== ПРЕПРОЦЕССИНГ ДОКУМЕНТОВ - CLI ТЕСТИРОВАНИЯ ===")
        print("=" * 60)

        print("\n=== ЗАГРУЗКА И ПОДГОТОВКА ДАННЫХ ===")
        print("1. Синхронизация протоколов из MongoDB")
        print("2. Скачивание протоколов за дату")
        print("3. Проверка доступности файлов в INPUT_DIR")

        print("\n=== ТЕСТИРОВАНИЕ ЭТАПОВ ПРЕПРОЦЕССИНГА ===")
        print("4. ТЕСТ 1: Определение типа файла")
        print("5. ТЕСТ 2: Распаковка архивов")
        print("6. ТЕСТ 3: Нормализация unit'ов")
        print("7. ТЕСТ 4: Создание manifest'ов")
        print("8. ТЕСТ 5: Docling обработка")

        print("\n=== ПОШАГОВАЯ ОБРАБОТКА ===")
        print("9. ШАГ 1: Сканирование и детекция типов файлов")
        print("10. ШАГ 2: Классификация файлов по категориям")
        print("11. ШАГ 3: Проверка дубликатов")
        print("12. ШАГ 4: Определение mixed units")
        print("13. ШАГ 5: Распределение по pending директориям")
        print("14. ПОЛНАЯ ОБРАБОТКА: Все шаги (1-5)")

        print("\n=== РАСШИРЕННАЯ СТАТИСТИКА ===")
        print("15. Просмотр структуры pending директорий")
        print("16. Детальная статистика по категориям")
        print("17. Отчет по обработанным units")

        print("\n=== MERGE И ФИНАЛИЗАЦИЯ ===")
        print("18. Merge (DRY RUN)")
        print("19. Merge (РЕАЛЬНЫЙ)")

        print("\n=== ПОЛНОЕ ТЕСТИРОВАНИЕ PIPELINE ===")
        print("20. ПОЛНЫЙ ТЕСТ: Весь pipeline (шаги 1-5)")
        print("21. ИНТЕГРАЦИОННЫЙ ТЕСТ: Router API")

        print("\n=== МОНИТОРИНГ И СТАТИСТИКА ===")
        print("22. Просмотр текущих метрик сессии")
        print("23. Просмотр логов обработки")
        print("24. Статус MongoDB подключений")

        print("\n=== СЛУЖЕБНЫЕ ФУНКЦИИ ===")
        print("25. Очистка тестовых данных")
        print("26. Создание тестовых файлов")
        print("27. Проверка инфраструктуры")

        print("\n0. Выход")
        print("\n" + "-" * 60)

    def handle_sync_protocols(self):
        """Синхронизация протоколов из удалённой MongoDB в локальную."""
        print("\n=== СИНХРОНИЗАЦИЯ ПРОТОКОЛОВ ИЗ УДАЛЁННОЙ MONGODB ===")

        # Проверка доступности SyncService
        if not SyncService:
            print("❌ SyncService не доступен")
            print("💡 Убедитесь, что модуль sync_db установлен и настроен")
            return

        # Выбор даты
        print("\n1. Выбор даты для синхронизации:")
        print("  1. Вчерашний день (по умолчанию)")
        print("  2. Указать дату вручную (YYYY-MM-DD)")
        choice = input("  Выберите [1-2] или Enter для вчерашнего дня: ").strip()

        target_date = None
        if choice == "2":
            date_str = input("  Введите дату (YYYY-MM-DD): ").strip()
            try:
                target_date = datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                print(f"✗ Неверный формат даты: {date_str}")
                return
        else:
            target_date = datetime.utcnow() - timedelta(days=1)

        # Лимит протоколов
        limit_str = input(f"\n2. Лимит протоколов для синхронизации (по умолчанию: 200): ").strip()
        limit = int(limit_str) if limit_str else 200

        # Запуск синхронизации
        print(f"\n3. Запуск синхронизации...")
        print(f"   Дата: {target_date.date()}")
        print(f"   Лимит: {limit}")

        try:
            sync_service = SyncService()
            result = sync_service.sync_protocols_for_date(target_date, limit)
            
            print("\n✓ Синхронизация завершена!")
            print(f"   Время: {result.duration:.2f} сек")
            print(f"   Просмотрено: {result.scanned}")
            print(f"   Вставлено: {result.inserted}")
            print(f"   Пропущено: {result.skipped_existing}")
            if result.errors_count > 0:
                print(f"   Ошибок: {result.errors_count}")
        except Exception as e:
            print(f"\n✗ Ошибка синхронизации: {e}")
            import traceback
            traceback.print_exc()

    def handle_download_protocols(self):
        """Скачивание протоколов из локальной MongoDB через VPN."""
        print("\n=== СКАЧИВАНИЕ ПРОТОКОЛОВ ИЗ MONGODB (С VPN) ===")

        if not ProtocolDownloader or not check_zakupki_health:
            print("❌ Модули скачивания не доступны")
            return

        # Проверка VPN подключения
        print("\n1. Проверка доступности zakupki.gov.ru через VPN...")
        if not check_zakupki_health():
            print("✗ zakupki.gov.ru недоступен (нет VPN / блокировка)")
            print("  Убедитесь, что VPN настроен через route-up-zakupki.sh")
            print("  Проверьте, что OpenVPN туннель активен")
            return

        print("✓ zakupki.gov.ru доступен через VPN")

        # Запрос лимита
        limit_str = input(f"\n2. Лимит протоколов/units для скачивания (по умолчанию: 200): ").strip()
        limit = int(limit_str) if limit_str else 200

        if limit <= 0:
            print("✗ Лимит должен быть больше 0")
            return

        # Запуск скачивания
        print(f"\n3. Запуск скачивания протоколов...")
        print(f"   Лимит: {limit} протоколов")
        print(f"   Директория: {INPUT_DIR.absolute()}")

        try:
            # Всегда используем новый API (SimpleProtocolDownloader)
            downloader = ProtocolDownloader(output_dir=INPUT_DIR)
            result = downloader.process_pending_protocols(limit=limit)
            duration = result.duration

            print("\n✓ Скачивание завершено!")
            print(f"   Время: {duration:.1f} сек")
            print(f"   Протоколы обработано: {result.processed}")
            print(f"   Документы скачано: {result.downloaded}")
            print(f"   Ошибок: {result.failed}")

            if result.errors:
                print(f"   Подробности ошибок: {len(result.errors)} ошибок")

        except Exception as e:
            print(f"❌ Ошибка скачивания: {e}")
            import traceback
            traceback.print_exc()

    def handle_check_input_files(self):
        """Проверка файлов в INPUT_DIR."""
        print("\n=== ПРОВЕРКА INPUT_DIR ===")

        if not INPUT_DIR.exists():
            print(f"❌ Директория {INPUT_DIR} не существует")
            return

        files = list(INPUT_DIR.glob("*"))
        files = [f for f in files if f.is_file() and not f.name.startswith('.')]

        print(f"📁 Найдено файлов: {len(files)}")

        if files:
            print("\nФайлы:")
            for i, file_path in enumerate(files[:10], 1):  # Показываем первые 10
                size_mb = file_path.stat().st_size / (1024 * 1024)
                print(f"  {i}. {file_path.name} ({size_mb:.1f} MB)")

            if len(files) > 10:
                print(f"... и еще {len(files) - 10} файлов")
        else:
            print("📭 INPUT_DIR пуст")

    def handle_test_file_type_detection(self):
        """Тест определения типа файла."""
        print("\n=== ТЕСТ: ОПРЕДЕЛЕНИЕ ТИПА ФАЙЛА ===")

        files = list(INPUT_DIR.glob("*"))
        files = [f for f in files if f.is_file() and not f.name.startswith('.')]

        if not files:
            print("❌ Нет файлов в INPUT_DIR для тестирования")
            return

        # Импортируем функцию определения типа
        from router.file_detection import detect_file_type

        print(f"🧪 Тестирование на {len(files)} файлах...")

        results = {}
        for file_path in files[:5]:  # Тестируем первые 5 файлов
            print(f"\n📄 {file_path.name}:")
            try:
                detection = detect_file_type(file_path)
                detected_type = detection.get("detected_type", "unknown")
                mime_type = detection.get("mime_type", "")
                needs_ocr = detection.get("needs_ocr", False)
                is_archive = detection.get("is_archive", False)

                print(f"  Тип: {detected_type}")
                print(f"  MIME: {mime_type}")
                print(f"  OCR нужен: {needs_ocr}")
                print(f"  Архив: {is_archive}")

                results[detected_type] = results.get(detected_type, 0) + 1

            except Exception as e:
                print(f"  ❌ Ошибка: {e}")

        print("\n📊 Статистика по типам:")
        for file_type, count in results.items():
            print(f"  {file_type}: {count}")

    def handle_test_archive_extraction(self):
        """Тест распаковки архивов."""
        print("\n=== ТЕСТ: РАСПАКОВКА АРХИВОВ ===")

        files = list(INPUT_DIR.glob("*"))
        archive_files = [f for f in files if f.is_file() and f.suffix.lower() in ['.zip', '.rar', '.7z']]

        if not archive_files:
            print("❌ Нет архивов в INPUT_DIR для тестирования")
            return

        from router.archive import safe_extract_archive

        print(f"🧪 Тестирование распаковки {len(archive_files)} архивов...")

        for archive_path in archive_files:
            print(f"\n📦 {archive_path.name}:")

            extract_dir = EXTRACTED_DIR / f"test_{archive_path.stem}"
            extract_dir.mkdir(parents=True, exist_ok=True)

            try:
                extracted_files, success = safe_extract_archive(archive_path, extract_dir, "test")

                if success:
                    print(f"  ✅ Распаковано файлов: {len(extracted_files)}")
                    for ext_file in extracted_files[:3]:  # Показываем первые 3
                        print(f"    📄 {ext_file['original_name']}")
                    if len(extracted_files) > 3:
                        print(f"    ... и еще {len(extracted_files) - 3} файлов")
                else:
                    print("  ❌ Ошибка распаковки")

            except Exception as e:
                print(f"  ❌ Ошибка: {e}")

    def handle_test_normalization(self):
        """Тест нормализации unit'ов."""
        print("\n=== ТЕСТ: НОРМАЛИЗАЦИЯ UNIT'ОВ ===")

        files = list(INPUT_DIR.glob("*"))
        files = [f for f in files if f.is_file() and not f.name.startswith('.')]

        if not files:
            print("❌ Нет файлов в INPUT_DIR для тестирования")
            return

        print(f"🧪 Тестирование нормализации {len(files)} файлов...")

        # Импортируем функцию process_file
        processed = 0
        errors = 0

        for file_path in files[:3]:  # Тестируем первые 3 файла
            print(f"\n📄 Обработка {file_path.name}...")

            try:
                result = process_file(file_path, None)  # background_tasks = None для синхронной обработки

                if result.get("status") == "processed":
                    print("  ✅ Обработано успешно")
                    if "unit_id" in result:
                        print(f"    Unit ID: {result['unit_id']}")
                    processed += 1
                else:
                    print(f"  ❌ Ошибка: {result.get('message', 'Unknown error')}")
                    errors += 1

            except Exception as e:
                print(f"  ❌ Ошибка: {e}")
                errors += 1

        print("\n📊 Результаты:")
        print(f"  ✅ Успешно: {processed}")
        print(f"  ❌ Ошибок: {errors}")

    def handle_test_manifest_creation(self):
        """Тест создания manifest'ов."""
        print("\n=== ТЕСТ: СОЗДАНИЕ MANIFEST'ОВ ===")

        # Проверяем normalized units
        unit_dirs = [d for d in NORMALIZED_DIR.iterdir() if d.is_dir() and d.name.startswith("UNIT_")]

        if not unit_dirs:
            print("❌ Нет normalized units для тестирования manifest'ов")
            print("Сначала выполните нормализацию файлов")
            return

        print(f"🧪 Проверка manifest'ов в {len(unit_dirs)} units...")

        # Импортируем функции для работы с manifest
        # get_manifest_from_mongo уже импортирован в начале файла

        manifests_found = 0
        manifests_valid = 0

        for unit_dir in unit_dirs[:5]:  # Проверяем первые 5
            unit_id = unit_dir.name
            print(f"\n📋 {unit_id}:")

            # Проверяем MongoDB manifest
            manifest = get_manifest_from_mongo(unit_id)

            if manifest:
                manifests_found += 1
                print("  ✅ Manifest найден в MongoDB")

                # Проверяем структуру
                required_fields = ["unit_id", "created_at", "processing", "files"]
                valid = all(field in manifest for field in required_fields)

                if valid:
                    manifests_valid += 1
                    status = manifest.get("processing", {}).get("status", "unknown")
                    route = manifest.get("processing", {}).get("route", "unknown")
                    files_count = len(manifest.get("files", []))
                    print(f"    Статус: {status}")
                    print(f"    Route: {route}")
                    print(f"    Файлов: {files_count}")
                else:
                    print("  ⚠️  Структура manifest неполная")
            else:
                # Проверяем JSON файл
                manifest_path = unit_dir / "manifest.json"
                if manifest_path.exists():
                    manifests_found += 1
                    print("  ✅ Manifest найден в JSON файле")

                    try:
                        with open(manifest_path, "r", encoding="utf-8") as f:
                            manifest = json.load(f)
                        manifests_valid += 1
                        print("    ✅ JSON валиден")
                    except Exception as e:
                        print(f"    ❌ Ошибка чтения JSON: {e}")
                else:
                    print("  ❌ Manifest не найден")

        print("\n📊 Результаты:")
        print(f"  📋 Manifest'ов найдено: {manifests_found}")
        print(f"  ✅ Валидных: {manifests_valid}")

    def handle_test_docling_processing(self):
        """Тест Docling обработки."""
        print("\n=== ТЕСТ: DOCLING ОБРАБОТКА ===")

        # Проверяем normalized units
        unit_dirs = [d for d in NORMALIZED_DIR.iterdir() if d.is_dir() and d.name.startswith("UNIT_")]

        if not unit_dirs:
            print("❌ Нет normalized units для Docling обработки")
            print("Сначала выполните нормализацию файлов")
            return

        print(f"🧪 Отправка {len(unit_dirs)} units в Docling...")

        # Отправка в Docling через API
        processed = 0
        errors = 0

        for unit_dir in unit_dirs[:3]:  # Тестируем первые 3
            unit_id = unit_dir.name
            print(f"\n🚀 Отправка {unit_id} в Docling...")

            try:
                # Отправляем запрос в Docling API
                manifest = get_manifest_from_mongo(unit_id)
                if manifest:
                    response = requests.post(
                        DOCLING_API,
                        json={"unit_id": unit_id, "manifest": manifest},
                        timeout=30
                    )
                    if response.status_code == 200:
                        processed += 1
                        print("  ✅ Отправлено")
                    else:
                        print(f"  ❌ Ошибка API: {response.status_code}")
                        errors += 1
                else:
                    print("  ⚠️  Manifest не найден, пропускаем")
                    errors += 1

                # Небольшая пауза между отправками
                time.sleep(1)

            except Exception as e:
                print(f"  ❌ Ошибка: {e}")
                errors += 1

        print("\n📊 Результаты:")
        print(f"  🚀 Отправлено: {processed}")
        print(f"  ❌ Ошибок: {errors}")

        if processed > 0:
            print("\n💡 Проверьте логи Docling сервиса для результатов обработки")

    def handle_full_pipeline_test(self):
        """Полный тест всего pipeline."""
        print("\n=== ПОЛНЫЙ ТЕСТ PIPELINE ===")

        # Инициализируем метрики сессии
        self.metrics = init_processing_metrics()
        self.session_id = self.metrics["session_id"]

        print(f"🎯 Запуск полной сессии тестирования: {self.session_id}")

        # Этап 1: Проверка входных данных
        print("\n📋 ЭТАП 1: Проверка входных данных...")
        self.handle_check_input_files()

        # Этап 2: Определение типов
        print("\n🔍 ЭТАП 2: Определение типов файлов...")
        self.handle_test_file_type_detection()

        # Этап 3: Распаковка архивов
        print("\n📦 ЭТАП 3: Распаковка архивов...")
        self.handle_test_archive_extraction()

        # Этап 4: Нормализация
        print("\n🔄 ЭТАП 4: Нормализация unit'ов...")
        self.handle_test_normalization()

        # Этап 5: Создание manifest'ов
        print("\n📋 ЭТАП 5: Создание manifest'ов...")
        self.handle_test_manifest_creation()

        # Этап 6: Docling обработка
        print("\n🤖 ЭТАП 6: Docling обработка...")
        self.handle_test_docling_processing()

        # Сохранение метрик
        if self.metrics:
            # Пытаемся сохранить в MongoDB
            saved = save_processing_metrics(self.metrics)
            if not saved:
                # Fallback на локальное сохранение
                print("⚠️  MongoDB недоступна, сохраняем метрики локально...")
                self.save_metrics_local(self.metrics)

        print("\n🎉 ПОЛНЫЙ ТЕСТ ЗАВЕРШЕН!")
        print(f"📊 Session ID: {self.session_id}")

    def handle_integration_test(self):
        """Интеграционный тест Router API."""
        print("\n=== ИНТЕГРАЦИОННЫЙ ТЕСТ ROUTER API ===")

        # Проверяем доступность router
        router_url = "http://router:8080/health"
        try:
            response = requests.get(router_url, timeout=5)
            if response.status_code == 200:
                print("✅ Router API доступен")
            else:
                print(f"⚠️  Router API вернул код {response.status_code}")
        except Exception as e:
            print(f"❌ Router API недоступен: {e}")
            print("💡 Убедитесь, что docker-compose запущен")
            return

        # Проверяем доступность Docling
        docling_url = DOCLING_API.replace("/process", "/health")
        try:
            response = requests.get(docling_url, timeout=5)
            if response.status_code == 200:
                print("✅ Docling API доступен")
            else:
                print(f"⚠️  Docling API вернул код {response.status_code}")
        except Exception as e:
            print(f"❌ Docling API недоступен: {e}")

        # Тест process_now endpoint
        print("\n🧪 Тестирование /process_now endpoint...")
        try:
            response = requests.post("http://router:8080/process_now", timeout=30)
            if response.status_code == 200:
                result = response.json()
                print("✅ process_now выполнен успешно")
                print(f"   Обработано файлов: {result.get('processed_count', 0)}")
                print(f"   Session ID: {result.get('session_id', 'N/A')}")
            else:
                print(f"❌ process_now вернул код {response.status_code}")
        except Exception as e:
            print(f"❌ Ошибка тестирования process_now: {e}")

    def handle_view_metrics(self):
        """Просмотр текущих метрик сессии."""
        print("\n=== ТЕКУЩИЕ МЕТРИКИ СЕССИИ ===")

        # Пытаемся загрузить из MongoDB или локального файла
        if not self.metrics:
            # Пытаемся загрузить последние метрики
            if ROUTER_AVAILABLE:
                metrics = get_current_metrics()
                if metrics:
                    self.metrics = metrics
                else:
                    # Пытаемся загрузить из локального файла
                    self.metrics = self.load_metrics_local()
        
        if not self.metrics:
            print("❌ Метрики сессии не найдены")
            print("💡 Запустите полный тест или инициализируйте метрики")
            print(f"💡 Локальные метрики: {self.local_metrics_dir}")
            return

        print(f"📊 Session ID: {self.metrics['session_id']}")
        print(f"🕐 Started: {self.metrics['started_at']}")
        print(f"🏁 Completed: {self.metrics.get('completed_at', 'In progress')}")

        summary = self.metrics.get("summary", {})
        print("\n📈 Summary:")
        print(f"   Input files: {summary.get('total_input_files', 0)}")
        print(f"   Archives: {summary.get('total_archives', 0)}")
        print(f"   Extracted: {summary.get('total_extracted', 0)}")
        print(f"   Units: {summary.get('total_units', 0)}")
        print(f"   Errors: {summary.get('total_errors', 0)}")
        
        # Показываем источник метрик
        if (self.local_metrics_dir / f"metrics_{self.metrics['session_id']}.json").exists():
            print(f"\n💾 Метрики также сохранены локально: {self.local_metrics_dir}")

    def handle_view_logs(self):
        """Просмотр логов обработки."""
        print("\n=== ЛОГИ ОБРАБОТКИ ===")

        # Проверяем логи в metrics
        if self.metrics:
            errors = self.metrics.get("errors", [])
            if errors:
                print("❌ Ошибки обработки:")
                for error in errors[-5:]:  # Последние 5 ошибок
                    print(f"   {error['timestamp']}: {error['error']}")
            else:
                print("✅ Ошибок не найдено")

        # Предлагаем проверить логи контейнеров
        print("\n💡 Для просмотра полных логов используйте:")
        print("   docker-compose logs -f router")
        print("   docker-compose logs -f scheduler")
        print("   docker-compose logs -f docling")

    def handle_check_mongodb(self):
        """Проверка MongoDB подключений."""
        print("\n=== ПРОВЕРКА MONGODB ПОДКЛЮЧЕНИЙ ===")

        # Проверка подключения к protocols MongoDB
        print("🔗 Проверка MongoDB для протоколов...")
        client = get_mongo_client()
        if client:
            try:
                client.admin.command('ping')
                print("✅ Protocols MongoDB: подключено")
            except Exception as e:
                print(f"❌ Protocols MongoDB: ошибка {e}")
        else:
            print("❌ Protocols MongoDB: не настроена")

        # Проверка подключения к metadata MongoDB
        print("🔗 Проверка MongoDB для метаданных...")
        client = get_mongo_metadata_client()
        if client:
            try:
                client.admin.command('ping')
                print("✅ Metadata MongoDB: подключено")
            except Exception as e:
                print(f"❌ Metadata MongoDB: ошибка {e}")
        else:
            print("❌ Metadata MongoDB: не настроена")

    def handle_cleanup_test_data(self):
        """Очистка тестовых данных."""
        print("\n=== ОЧИСТКА ТЕСТОВЫХ ДАННЫХ ===")

        dirs_to_clean = [TEMP_DIR, EXTRACTED_DIR, NORMALIZED_DIR, ARCHIVE_DIR]

        for directory in dirs_to_clean:
            if directory.exists():
                print(f"🧹 Очистка {directory}...")
                for item in directory.glob("*"):
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        import shutil
                        shutil.rmtree(item)
                print(f"   ✅ Очищено")

        print("🎉 Очистка завершена")

    def handle_create_test_files(self):
        """Создание тестовых файлов."""
        print("\n=== СОЗДАНИЕ ТЕСТОВЫХ ФАЙЛОВ ===")

        # Создаем простой текстовый файл
        test_file = INPUT_DIR / "test_document.txt"
        test_file.write_text("Это тестовый документ для проверки препроцессинга.")

        # Создаем простой PDF (если возможно)
        print("📄 Создан тестовый файл: test_document.txt")

        print("✅ Тестовые файлы созданы")

    def handle_check_infrastructure(self):
        """Проверка инфраструктуры."""
        print("\n=== ПРОВЕРКА ИНФРАСТРУКТУРЫ ===")

        # Проверка директорий
        dirs_to_check = [
            ("INPUT_DIR", INPUT_DIR),
            ("TEMP_DIR", TEMP_DIR),
            ("OUTPUT_DIR", OUTPUT_DIR),
            ("EXTRACTED_DIR", EXTRACTED_DIR),
            ("NORMALIZED_DIR", NORMALIZED_DIR),
            ("ARCHIVE_DIR", ARCHIVE_DIR),
        ]

        print("📁 Проверка директорий:")
        for name, directory in dirs_to_check:
            if directory.exists():
                print(f"  ✅ {name}: {directory}")
            else:
                print(f"  ❌ {name}: не существует")
                try:
                    directory.mkdir(parents=True, exist_ok=True)
                    print(f"     📁 Создана: {directory}")
                except Exception as e:
                    print(f"     ❌ Ошибка создания: {e}")

        # Проверка MongoDB
        print("\n" + "="*40)
        self.handle_check_mongodb()

        print("\n🎯 Инфраструктура проверена")

    def run(self):
        """Главный цикл CLI."""
        print("\n🚀 ЗАПУСК CLI ТЕСТИРОВАНИЯ ПРЕПРОЦЕССИНГА")
        print("=" * 60)

        while True:
            try:
                self.show_menu()
                choice = input("\nВыберите действие [0-27]: ").strip()

                if choice == "0":
                    print("👋 Выход...")
                    break

                elif choice == "1":
                    self.handle_sync_protocols()

                elif choice == "2":
                    self.handle_download_protocols()

                elif choice == "3":
                    self.handle_check_input_files()

                elif choice == "4":
                    self.handle_test_file_type_detection()

                elif choice == "5":
                    self.handle_test_archive_extraction()

                elif choice == "6":
                    self.handle_test_normalization()

                elif choice == "7":
                    self.handle_test_manifest_creation()

                elif choice == "8":
                    self.handle_test_docling_processing()

                elif choice == "9":
                    self.handle_step1_scan_and_detect()

                elif choice == "10":
                    self.handle_step2_classify()

                elif choice == "11":
                    self.handle_step3_check_duplicates()

                elif choice == "12":
                    self.handle_step4_check_mixed()

                elif choice == "13":
                    self.handle_step5_distribute()

                elif choice == "14":
                    self.handle_full_processing()

                elif choice == "15":
                    self.handle_view_pending_structure()

                elif choice == "16":
                    self.handle_category_statistics()

                elif choice == "17":
                    self.handle_units_report()

                elif choice == "18":
                    self.handle_merge_dry_run()

                elif choice == "19":
                    self.handle_merge_real()

                elif choice == "20":
                    self.handle_full_pipeline_test()

                elif choice == "21":
                    self.handle_integration_test()

                elif choice == "22":
                    self.handle_view_metrics()

                elif choice == "23":
                    self.handle_view_logs()

                elif choice == "24":
                    self.handle_check_mongodb()

                elif choice == "25":
                    self.handle_cleanup_test_data()

                elif choice == "26":
                    self.handle_create_test_files()

                elif choice == "27":
                    self.handle_check_infrastructure()

                else:
                    print("❌ Неверный выбор. Попробуйте снова.")

                input("\n⏎ Нажмите Enter для продолжения...")

            except KeyboardInterrupt:
                print("\n\n👋 Выход...")
                break
            except Exception as e:
                print(f"\n❌ Ошибка: {e}")
                import traceback
                traceback.print_exc()
                input("\n⏎ Нажмите Enter для продолжения...")


    def handle_step1_scan_and_detect(self, limit: Optional[int] = None):
        """ШАГ 1: Сканирование и детекция типов файлов."""
        print("\n=== ШАГ 1: СКАНИРОВАНИЕ И ДЕТЕКЦИЯ ТИПОВ ФАЙЛОВ ===")

        if limit is None:
            limit_str = input("Лимит файлов для обработки (Enter = все): ").strip()
            limit = int(limit_str) if limit_str else None

        print(f"🔍 Сканирование INPUT_DIR: {INPUT_DIR}")

        files = self.find_input_files(limit=limit)

        print(f"📄 Найдено файлов: {len(files)}")

        processed = 0
        for file_path in files:
            try:
                # Используем существующую функцию детекции
                detection = detect_file_type(file_path)
                detected_type = detection.get("detected_type", "unknown")
                mime_type = detection.get("mime_type", "")
                needs_ocr = detection.get("needs_ocr", False)

                print(f"  📄 {file_path.name} → {detected_type} ({mime_type})")
                processed += 1

            except Exception as e:
                print(f"  ❌ {file_path.name}: {e}")

        print("\n✅ ШАГ 1 завершен!")
        print(f"   Обработано файлов: {processed}")

    def handle_step2_classify(self, limit: Optional[int] = None):
        """ШАГ 2: Классификация файлов по категориям."""
        print("\n=== ШАГ 2: КЛАССИФИКАЦИЯ ФАЙЛОВ ПО КАТЕГОРИЯМ ===")

        if limit is None:
            limit_str = input("Лимит файлов для обработки (Enter = все): ").strip()
            limit = int(limit_str) if limit_str else None

        print("📋 Классификация файлов...")
        print("   Категории: direct, normalize, convert, extract, special, mixed")

        files = self.find_input_files(limit=limit)

        categories = {
            "direct": 0,
            "normalize": 0,
            "convert": 0,
            "extract": 0,
            "special": 0
        }

        for file_path in files:
            try:
                detection = detect_file_type(file_path)
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

    def handle_step3_check_duplicates(self, limit: Optional[int] = None):
        """ШАГ 3: Проверка дубликатов."""
        print("\n=== ШАГ 3: ПРОВЕРКА ДУБЛИКАТОВ ===")

        if limit is None:
            limit_str = input("Лимит файлов для проверки (Enter = все): ").strip()
            limit = int(limit_str) if limit_str else None

        print("🔍 Поиск дубликатов по хэшам...")

        files = self.find_input_files(limit=limit)

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

        print("\n📊 Результаты проверки дубликатов:")
        print(f"   Уникальных файлов: {len(hashes)}")
        print(f"   Дубликатов: {len(duplicates)}")

        print("\n✅ ШАГ 3 завершен!")

    def handle_step4_check_mixed(self, limit: Optional[int] = None):
        """ШАГ 4: Определение mixed units в PENDING директориях."""
        print("\n=== ШАГ 4: ОПРЕДЕЛЕНИЕ MIXED UNITS ===")

        if limit is None:
            limit_str = input("Лимит units для проверки (Enter = все): ").strip()
            limit = int(limit_str) if limit_str else None

        print("🔍 Анализ units на смешанный контент...")
        print(f"   Поиск в PENDING директориях: {PENDING_DIR}")

        # Собираем все units из PENDING директорий
        all_unit_dirs = []
        pending_dirs = [PENDING_DIRECT_DIR, PENDING_NORMALIZE_DIR, PENDING_CONVERT_DIR, 
                        PENDING_EXTRACT_DIR, PENDING_SPECIAL_DIR, PENDING_MIXED_DIR]
        
        for pending_dir in pending_dirs:
            if pending_dir.exists():
                # Ищем units в директории и поддиректориях
                for item in pending_dir.rglob("UNIT_*"):
                    if item.is_dir():
                        all_unit_dirs.append(item)

        if not all_unit_dirs:
            print("   ℹ️  Нет units в PENDING директориях")
            print("   💡 Сначала выполните ШАГ 5 (Распределение) для создания units")
            return

        if limit:
            all_unit_dirs = all_unit_dirs[:limit]

        print(f"   Найдено units для анализа: {len(all_unit_dirs)}")

        mixed_units = []
        simple_units = []

        for unit_dir in all_unit_dirs:
            try:
                files_dir = unit_dir / "files"
                if not files_dir.exists():
                    continue
                    
                files = [f for f in files_dir.iterdir() if f.is_file()]
                file_types = set()

                for file_path in files:
                    detection = detect_file_type(file_path)
                    file_types.add(detection.get("detected_type", "unknown"))

                if len(file_types) > 1:
                    mixed_units.append((unit_dir.name, file_types))
                    print(f"  🔀 Mixed: {unit_dir.name} ({', '.join(file_types)})")
                else:
                    simple_units.append(unit_dir.name)
                    file_type = list(file_types)[0] if file_types else 'empty'
                    print(f"  📄 Simple: {unit_dir.name} ({file_type})")

            except Exception as e:
                print(f"  ❌ {unit_dir.name}: {e}")

        print("\n📊 Результаты анализа:")
        print(f"   Simple units: {len(simple_units)}")
        print(f"   Mixed units: {len(mixed_units)}")

        print("\n✅ ШАГ 4 завершен!")

    def handle_step5_distribute(self, limit: Optional[int] = None):
        """ШАГ 5: Распределение файлов из INPUT_DIR в PENDING директории с созданием units."""
        print("\n=== ШАГ 5: РАСПРЕДЕЛЕНИЕ ПО PENDING ДИРЕКТОРИЯМ ===")

        if limit is None:
            limit_str = input("Лимит файлов для распределения (Enter = все): ").strip()
            limit = int(limit_str) if limit_str else None

        print("📦 Распределение файлов по категориям с созданием units...")
        print(f"   Исходная директория: {INPUT_DIR}")
        print(f"   Целевая директория: {PENDING_DIR}")
        print("   Категории: direct/, normalize/, convert/, extract/, special/")

        # Инициализируем директории
        init_directories()

        files = self.find_input_files(limit=limit)

        if not files:
            print("\n   ℹ️  Нет файлов в INPUT_DIR для распределения")
            return

        print(f"\n   Найдено файлов: {len(files)}")

        # Инициализируем метрики
        init_processing_metrics()

        distributed = {
            "direct": 0,
            "normalize": 0,
            "convert": 0,
            "extract": 0,
            "special": 0,
            "mixed": 0
        }
        errors = 0
        units_created = []

        for file_path in files:
            try:
                # Используем process_file из router.api для полной обработки
                result = process_file(file_path)
                
                if result.get("status") == "processed":
                    unit_id = result.get("unit_id", "unknown")
                    category = result.get("category", "special")
                    detected_type = result.get("detected_type", "unknown")
                    
                    if category in distributed:
                        distributed[category] += 1
                    else:
                        distributed["special"] += 1
                    
                    units_created.append(unit_id)
                    print(f"  ✅ {file_path.name} → {category}/ [{detected_type}] (unit: {unit_id})")
                else:
                    errors += 1
                    error_msg = result.get("message", "Unknown error")
                    print(f"  ❌ {file_path.name}: {error_msg}")

            except Exception as e:
                errors += 1
                print(f"  ❌ {file_path.name}: {e}")

        # Сохраняем метрики
        saved = save_processing_metrics()
        if not saved:
            # Fallback на локальное сохранение
            print("⚠️  MongoDB недоступна, сохраняем метрики локально...")
            self.save_metrics_local()

        print("\n📊 Распределение по категориям:")
        for category, count in distributed.items():
            if count > 0:
                print(f"   {category}: {count} файлов")

        total_distributed = sum(distributed.values())
        print(f"   ---")
        print(f"   Всего распределено: {total_distributed}")
        print(f"   Создано units: {len(units_created)}")
        if errors > 0:
            print(f"   Ошибок: {errors}")

        # Показываем статистику по PENDING
        print("\n📁 Статистика PENDING после распределения:")
        pending_stats = get_unit_statistics(PENDING_DIR)
        for category, stats in pending_stats.items():
            if stats["units"] > 0 or stats["files"] > 0:
                print(f"   {category}: {stats['units']} units, {stats['files']} файлов")

        print("\n✅ ШАГ 5 завершен!")

    def handle_full_processing(self, limit: Optional[int] = None):
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
            self.handle_step1_scan_and_detect(limit)

            print("\n📋 ШАГ 2...")
            self.handle_step2_classify(limit)

            print("\n📋 ШАГ 3...")
            self.handle_step3_check_duplicates(limit)

            print("\n📋 ШАГ 4...")
            self.handle_step4_check_mixed(limit)

            print("\n📋 ШАГ 5...")
            self.handle_step5_distribute(limit)

            print("\n🎉 ПОЛНАЯ ОБРАБОТКА ЗАВЕРШЕНА!")

        except Exception as e:
            print(f"\n❌ Ошибка в полной обработке: {e}")

    def handle_view_pending_structure(self):
        """Просмотр структуры pending директорий из config."""
        print("\n=== ПРОСМОТР СТРУКТУРЫ PENDING ДИРЕКТОРИЙ ===")

        if not PENDING_DIR.exists():
            print(f"✗ Директория PENDING не существует: {PENDING_DIR}")
            print("💡 Выполните ШАГ 5 (Распределение) для создания структуры")
            return

        print(f"📁 Базовая директория: {PENDING_DIR}")

        pending_dirs = {
            "direct": PENDING_DIRECT_DIR,
            "normalize": PENDING_NORMALIZE_DIR,
            "convert": PENDING_CONVERT_DIR,
            "extract": PENDING_EXTRACT_DIR,
            "special": PENDING_SPECIAL_DIR,
            "mixed": PENDING_MIXED_DIR
        }
        
        total_units = 0
        total_files = 0

        for category, cat_dir in pending_dirs.items():
            if cat_dir.exists():
                # Считаем units (директории UNIT_*)
                units = list(cat_dir.rglob("UNIT_*"))
                units = [u for u in units if u.is_dir()]
                
                # Считаем файлы в units
                files_count = 0
                for unit_dir in units:
                    files_dir = unit_dir / "files"
                    if files_dir.exists():
                        files_count += len([f for f in files_dir.iterdir() if f.is_file()])
                
                total_units += len(units)
                total_files += files_count

                print(f"\n📂 {category}/:")
                print(f"   Units: {len(units)}")
                print(f"   Файлов: {files_count}")

                # Показываем примеры units
                if units:
                    print("   Примеры units:")
                    for i, unit_dir in enumerate(units[:3]):
                        unit_files_dir = unit_dir / "files"
                        unit_files_count = 0
                        if unit_files_dir.exists():
                            unit_files_count = len([f for f in unit_files_dir.iterdir() if f.is_file()])
                        print(f"     {i+1}. {unit_dir.name}: {unit_files_count} файлов")
            else:
                print(f"\n📂 {category}/: не существует")

        print(f"\n📊 Итого:")
        print(f"   Units во всех категориях: {total_units}")
        print(f"   Файлов во всех units: {total_files}")

    def handle_category_statistics(self):
        """Детальная статистика по категориям в PENDING директориях."""
        print("\n=== ДЕТАЛЬНАЯ СТАТИСТИКА ПО КАТЕГОРИЯМ ===")

        if not PENDING_DIR.exists():
            print(f"✗ Директория PENDING не существует: {PENDING_DIR}")
            return

        pending_dirs = {
            "direct": PENDING_DIRECT_DIR,
            "normalize": PENDING_NORMALIZE_DIR,
            "convert": PENDING_CONVERT_DIR,
            "extract": PENDING_EXTRACT_DIR,
            "special": PENDING_SPECIAL_DIR,
            "mixed": PENDING_MIXED_DIR
        }
        
        stats = {}

        for category, cat_dir in pending_dirs.items():
            if cat_dir.exists():
                # Собираем все файлы из units в категории
                all_files = []
                for unit_dir in cat_dir.rglob("UNIT_*"):
                    if unit_dir.is_dir():
                        files_dir = unit_dir / "files"
                        if files_dir.exists():
                            all_files.extend([f for f in files_dir.iterdir() if f.is_file()])

                # Статистика по типам файлов
                extensions = {}
                detected_types = {}
                total_size = 0

                for file_path in all_files:
                    # Статистика по расширениям
                    ext = file_path.suffix.lower() or "no_ext"
                    if ext not in extensions:
                        extensions[ext] = {"count": 0, "size": 0}
                    extensions[ext]["count"] += 1
                    file_size = file_path.stat().st_size
                    extensions[ext]["size"] += file_size
                    total_size += file_size
                    
                    # Статистика по определенным типам
                    try:
                        detection = detect_file_type(file_path)
                        detected_type = detection.get("detected_type", "unknown")
                        detected_types[detected_type] = detected_types.get(detected_type, 0) + 1
                    except:
                        detected_types["unknown"] = detected_types.get("unknown", 0) + 1

                stats[category] = {
                    "file_count": len(all_files),
                    "total_size": total_size,
                    "extensions": extensions,
                    "detected_types": detected_types
                }

        # Вывод статистики
        total_all_files = 0
        total_all_size = 0
        
        for category, stat in stats.items():
            if stat["file_count"] == 0:
                continue
                
            print(f"\n📊 Категория: {category}")
            print(f"   Всего файлов: {stat['file_count']}")
            print(f"   Общий размер: {stat['total_size']:,} bytes ({stat['total_size']/1024/1024:.1f} MB)")
            
            total_all_files += stat["file_count"]
            total_all_size += stat["total_size"]

            if stat["extensions"]:
                print("   По расширениям:")
                for ext, ext_stat in sorted(stat["extensions"].items()):
                    avg_size = ext_stat["size"] / ext_stat["count"] if ext_stat["count"] > 0 else 0
                    print(f"     {ext}: {ext_stat['count']} файлов, средний размер: {avg_size:,.0f} bytes")
            
            if stat["detected_types"]:
                print("   По определенным типам:")
                for dtype, count in sorted(stat["detected_types"].items()):
                    print(f"     {dtype}: {count} файлов")
        
        print(f"\n📊 ИТОГО по всем категориям:")
        print(f"   Файлов: {total_all_files}")
        print(f"   Размер: {total_all_size:,} bytes ({total_all_size/1024/1024:.1f} MB)")

    def handle_units_report(self):
        """Отчет по обработанным units в PENDING и READY_DOCLING директориях."""
        print("\n=== ОТЧЕТ ПО ОБРАБОТАННЫМ UNITS ===")

        # 1. Статистика по PENDING директориям
        print("\n📁 PENDING директории:")
        pending_stats = get_unit_statistics(PENDING_DIR)
        
        total_pending_units = 0
        total_pending_files = 0
        for category, stats in pending_stats.items():
            if stats["units"] > 0 or stats["files"] > 0:
                print(f"   {category}: {stats['units']} units, {stats['files']} файлов")
                total_pending_units += stats["units"]
                total_pending_files += stats["files"]
        
        if total_pending_units == 0:
            print("   (пусто)")
        else:
            print(f"   ---")
            print(f"   Итого PENDING: {total_pending_units} units, {total_pending_files} файлов")

        # 2. Статистика по READY_DOCLING директории
        print("\n📁 READY_DOCLING директория:")
        ready_stats = get_ready_docling_statistics()
        
        if ready_stats["total_units"] == 0:
            print("   (пусто)")
        else:
            print(f"   Всего units: {ready_stats['total_units']}")
            print(f"   Всего файлов: {ready_stats['total_files']}")
            
            if ready_stats["by_type"]:
                print("\n   По типам файлов:")
                for file_type, type_stats in sorted(ready_stats["by_type"].items()):
                    print(f"     {file_type}: {type_stats['units']} units, {type_stats['files']} файлов")

        # 3. Детальный анализ units в PENDING директориях
        print("\n📋 Детальный анализ units в PENDING:")
        
        pending_dirs = {
            "direct": PENDING_DIRECT_DIR,
            "normalize": PENDING_NORMALIZE_DIR,
            "convert": PENDING_CONVERT_DIR,
            "extract": PENDING_EXTRACT_DIR,
            "special": PENDING_SPECIAL_DIR,
            "mixed": PENDING_MIXED_DIR
        }
        
        all_units = []
        file_types = {}
        
        for category, cat_dir in pending_dirs.items():
            if not cat_dir.exists():
                continue
            
            # Ищем units в категории (включая поддиректории для типов файлов)
            for item in cat_dir.rglob("UNIT_*"):
                if item.is_dir():
                    files_dir = item / "files"
                    if files_dir.exists():
                        files = [f for f in files_dir.iterdir() if f.is_file()]
                        for file_path in files:
                            try:
                                detection = detect_file_type(file_path)
                                file_type = detection.get("detected_type", "unknown")
                                file_types[file_type] = file_types.get(file_type, 0) + 1
                            except:
                                file_types["unknown"] = file_types.get("unknown", 0) + 1
                        
                        all_units.append({
                            "unit_id": item.name,
                            "category": category,
                            "files_count": len(files),
                            "path": str(item)
                        })
        
        if file_types:
            print("\n   Распределение по типам файлов:")
            for file_type, count in sorted(file_types.items()):
                print(f"     {file_type}: {count} файлов")
        
        # Примеры units
        if all_units:
            print(f"\n   Примеры units (всего {len(all_units)}):")
            for i, unit_info in enumerate(all_units[:5]):
                print(f"     {i+1}. {unit_info['unit_id']} [{unit_info['category']}]: {unit_info['files_count']} файлов")
        else:
            print("   Нет units в PENDING директориях")

    def handle_merge_dry_run(self):
        """Merge в ready_docling (DRY RUN) - использует router.merge."""
        print("\n=== MERGE В READY_DOCLING (DRY RUN) ===")

        if not PENDING_DIR.exists():
            print(f"✗ Директория PENDING не существует: {PENDING_DIR}")
            return

        print(f"📁 Исходная директория: {PENDING_DIR}")
        print(f"📁 Целевая директория: {READY_DOCLING_DIR}")

        # Запрос лимита
        limit_str = input("Лимит units для merge (Enter = все): ").strip()
        limit = int(limit_str) if limit_str else None

        print("\n🔍 Анализ файлов для merge (DRY RUN)...")
        
        # Выполняем merge в режиме dry_run
        result = merge_to_ready_docling(dry_run=True, limit=limit)
        
        # Выводим результаты
        print_merge_summary(result)
        
        print("\n⚠️  DRY RUN завершен. Файлы НЕ были перемещены.")
        print("   Используйте пункт 19 'Merge (РЕАЛЬНЫЙ)' для выполнения операций.")

    def handle_merge_real(self):
        """Merge в ready_docling (РЕАЛЬНЫЙ) - использует router.merge."""
        print("\n=== MERGE В READY_DOCLING (РЕАЛЬНЫЙ) ===")

        if not PENDING_DIR.exists():
            print(f"✗ Директория PENDING не существует: {PENDING_DIR}")
            return

        print(f"📁 Исходная директория: {PENDING_DIR}")
        print(f"📁 Целевая директория: {READY_DOCLING_DIR}")

        # Подтверждение операции
        confirm = input("\n⚠️  ВНИМАНИЕ: Эта операция ПЕРЕМЕСТИТ файлы из pending в ready_docling.\n   Продолжить? (yes/no): ").strip().lower()
        if confirm not in ["yes", "y", "да"]:
            print("❌ Операция отменена пользователем")
            return

        # Запрос лимита
        limit_str = input("Лимит units для merge (Enter = все): ").strip()
        limit = int(limit_str) if limit_str else None

        print("\n🚀 Начинаем merge операции...")
        
        # Выполняем реальный merge
        result = merge_to_ready_docling(dry_run=False, limit=limit)
        
        # Выводим результаты
        print_merge_summary(result)
        
        print(f"\n📁 Проверьте результаты в: {READY_DOCLING_DIR}")
        
        # Показываем статистику ready_docling после merge
        print("\n📊 Статистика READY_DOCLING после merge:")
        ready_stats = get_ready_docling_statistics()
        print(f"   Всего units: {ready_stats['total_units']}")
        print(f"   Всего файлов: {ready_stats['total_files']}")
        
        if ready_stats["by_type"]:
            print("   По типам:")
            for file_type, type_stats in sorted(ready_stats["by_type"].items()):
                print(f"     {file_type}: {type_stats['units']} units, {type_stats['files']} файлов")


def main():
    """Точка входа для CLI."""
    cli = PreprocessingTestCLI()
    cli.run()


if __name__ == "__main__":
    main()

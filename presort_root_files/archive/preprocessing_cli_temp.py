class PreprocessingCLI:
    """Интерактивный CLI для управления preprocessing."""
    
    def __init__(self):
        self.state_manager = StateManager()
        self.limits = get_limits()
    
    def show_menu(self):
        """Показывает главное меню."""
        print("\n" + "=" * 50)
        print("=== Winners223 Preprocessing CLI ===")
        print("=" * 50)
        
        print("\n=== ЗАГРУЗКА И СИНХРОНИЗАЦИЯ ===")
        print("1. Скачать протоколы из MongoDB (с VPN)")
        print("2. Синхронизация протоколов из удалённой MongoDB")
        
        # print("\n=== ОБРАБОТКА (СТАРАЯ СИСТЕМА) ===")
        # print("3. Определить тип файла(ов)")
        # print("4. Распаковать архив(ы)")
        # print("5. Конвертировать DOC → DOCX")
        # print("6. Нормализовать файл(ы)")
        # print("7. Создать manifest")
        # print("8. Сортировка PDF на text_pdf и scan_pdf")
        # print("9. Конвертация DOC → HTML/XML")
        # print("10. Автоматическая обработка (полный пайплайн)")
        
        print("\n=== НОВАЯ СИСТЕМА (PENDING) - ПОШАГОВАЯ ОБРАБОТКА ===")
        print("3. ШАГ 1: Сканирование и детекция типов файлов")
        print("4. ШАГ 2: Классификация файлов по категориям")
        print("5. ШАГ 3: Проверка дубликатов")
        print("6. ШАГ 4: Определение mixed units")
        print("7. ШАГ 5: Распределение по pending директориям")
        print("8. ПОЛНАЯ ОБРАБОТКА: Все шаги (3-7)")
        
        print("\n=== СТАТИСТИКА И ПРОСМОТР ===")
        print("9. Просмотр pending структуры")
        print("10. Детальная статистика по категориям (+ mixed units)")
        print("11. Отчет по обработанным units")
        
        print("\n=== MERGE В READY_DOCLING ===")
        print("12. Merge (DRY RUN)")
        print("13. Merge (РЕАЛЬНЫЙ)")
        
        print("\n=== СЛУЖЕБНЫЕ ОПЕРАЦИИ ===")
        print("14. Просмотр статистики")
        print("15. Просмотр метрик")
        print("16. Настройки лимитов")
        print("17. Очистка директорий")
        print("18. Проверка отсортированных units")
        print("19. Анализ проблем определения типов")
        
        print("\n0. Выход")
        print("\n" + "-" * 50)
    
    def handle_sync_protocols(self):
        """Обработка синхронизации протоколов из удалённой MongoDB."""
        print("\n=== Синхронизация протоколов из удалённой MongoDB ===")
        
        # Проверка подключения к удалённой MongoDB
        print("\n1. Проверка подключения к удалённой MongoDB...")
        remote_client = get_remote_mongo_client()
        if not remote_client:
            print("✗ Не удалось подключиться к удалённой MongoDB")
            print("  Проверьте настройки в .env:")
            print("    - mongoServer или MONGO_SERVER")
            print("    - readAllUser или MONGO_USER")
            print("    - readAllPassword или MONGO_PASSWORD")
            print("    - sslCertPath или MONGO_SSL_CERT")
            return
        
        remote_client.close()
        print("✓ Подключение к удалённой MongoDB успешно")
        
        # Проверка подключения к локальной MongoDB
        print("\n2. Проверка подключения к локальной MongoDB...")
        local_client = get_local_mongo_client()
        if not local_client:
            print("✗ Не удалось подключиться к локальной MongoDB")
            print("  Проверьте настройки:")
            print("    - LOCAL_MONGO_SERVER (по умолчанию: localhost:27017)")
            print("    - MONGO_METADATA_USER")
            print("    - MONGO_METADATA_PASSWORD")
            return
        
        local_client.close()
        print("✓ Подключение к локальной MongoDB успешно")
        
        # Выбор даты
        print("\n3. Выбор даты для синхронизации:")
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
        
        # Лимит
        limit_str = input(f"\n4. Лимит протоколов для синхронизации (по умолчанию: 200): ").strip()
        limit = int(limit_str) if limit_str else 200
        
        # Запуск синхронизации
        print(f"\n5. Запуск синхронизации...")
        print(f"   Дата: {target_date.date()}")
        print(f"   Лимит: {limit}")
        
        result = sync_protocols_for_date(target_date, limit)
        
        if result.get("status") == "success":
            print("\n✓ Синхронизация завершена успешно!")
            print(f"   Просмотрено: {result.get('scanned', 0)}")
            print(f"   Вставлено: {result.get('inserted', 0)}")
            print(f"   Пропущено: {result.get('skipped_existing', 0)}")
            if result.get("errors_count", 0) > 0:
                print(f"   Ошибок: {result.get('errors_count', 0)}")
        else:
            print(f"\n✗ Ошибка синхронизации: {result.get('message', 'Unknown error')}")
    
    def handle_download_protocols(self):
        """Обработка скачивания протоколов из MongoDB через VPN."""
        print("\n=== Скачивание протоколов из MongoDB (с VPN) ===")
        
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
            downloader = ProtocolDownloader(output_dir=INPUT_DIR)
            start_time = time.time()
            result = downloader.process_pending_protocols(limit=limit)
            duration = time.time() - start_time
            
            if result.get("health_ok"):
                print("\n" + "=" * 80)
                print("✓ СКАЧИВАНИЕ ЗАВЕРШЕНО")
                print("=" * 80)
                print(f"  Успешно обработано: {result.get('processed_ok', 0)} протоколов")
                print(f"  Ошибок: {result.get('processed_error', 0)} протоколов")
                print(f"  Скачано файлов: {result.get('downloaded_files_count', 0)}")
                print(f"  Ошибок скачивания файлов: {result.get('failed_files_count', 0)}")
                print(f"  Время выполнения: {duration:.2f} сек")
                if result.get('processed_ok', 0) > 0:
                    avg_time = duration / result.get('processed_ok', 1)
                    print(f"  Среднее время на протокол: {avg_time:.2f} сек")
            else:
                print("\n✗ Скачивание не выполнено из-за проблем с VPN")
                
        except Exception as e:
            print(f"\n✗ Ошибка при скачивании протоколов: {e}")
            import traceback
            traceback.print_exc()
    
    def handle_detect_type(self, limit: Optional[int] = None):
        """Обработка определения типа файла на уровне unit'ов (протоколов)."""
        print("\n=== Определение типа файла (на уровне unit'ов) ===")
        if limit is None:
            limit_str = input(f"Лимит обработки (0 = все, текущий: {LIMIT_DETECT_TYPE}): ").strip()
            limit = int(limit_str) if limit_str else LIMIT_DETECT_TYPE
        
        print(f"\nОбработка файлов из input/ с лимитом {limit if limit > 0 else 'без ограничений'}...")
        print("Файлы одного протокола/юнита обрабатываются вместе и не разделяются.")
        
        try:
            # Импортируем необходимые модули
            from services.router.unit_distribution import distribute_unit_by_types
            from services.router.mongo import save_file_detection_metadata, save_unit_distribution_metadata
            from services.router.config import INPUT_DIR, ensure_directories
            from pathlib import Path
            import time
            from collections import defaultdict
            
            ensure_directories()
            
            # Получаем список unit'ов
            unit_dirs = [d for d in INPUT_DIR.iterdir() if d.is_dir() and d.name.startswith("UNIT_")]
            total_units = len(unit_dirs)
            
            if limit > 0:
                unit_dirs = unit_dirs[:limit]
            
            print(f"\nНайдено unit'ов: {total_units}")
            print(f"Обрабатывается: {len(unit_dirs)}")
            print(f"{'='*80}\n")
            
            # Статистика
            stats = {
                "processed_units": 0,
                "processed_files": 0,
                "mixed_units": 0,
                "duplicates_found": 0,
                "extension_mismatches": 0,
                "errors": 0,
                "file_types": defaultdict(int),
                "target_dirs": defaultdict(int),
                "unprocessed_units": [],  # Units которые не были обработаны с причинами
                "extension_mismatch_details": []  # Детали несоответствий расширений
            }
            
            start_time = time.time()
            
            for idx, unit_dir in enumerate(unit_dirs, 1):
                unit_id = unit_dir.name
                files = [f for f in unit_dir.iterdir() if f.is_file() and not f.name.startswith('.')]
                
                if not files:
                    # Отслеживаем units без файлов
                    stats["unprocessed_units"].append({
                        "unit_id": unit_id,
                        "reason": "no_files",
                        "message": "Unit не содержит файлов"
                    })
                    continue
                
                print(f"[{idx}/{len(unit_dirs)}] {unit_id} ({len(files)} файл(ов))...", end=" ", flush=True)
                
                try:
                    # Подготавливаем список файлов
                    files_list = [{"path": str(f)} for f in files]
                    
                    # Распределяем unit
                    distribution_result = distribute_unit_by_types(
                        unit_id=unit_id,
                        files=files_list,
                        unit_metadata=None
                    )
                    
                    # Сохраняем метаданные
                    for file_info in distribution_result["files"]:
                        try:
                            save_file_detection_metadata(
                                file_path=file_info["path"],
                                file_info=file_info,
                                unit_id=unit_id,
                                protocol_info=None
                            )
                        except Exception:
                            pass  # Игнорируем ошибки MongoDB
                    
                    try:
                        save_unit_distribution_metadata(unit_id, distribution_result)
                    except Exception:
                        pass
                    
                    # Обновляем статистику
                    stats["processed_units"] += 1
                    stats["processed_files"] += len(distribution_result["files"])
                    
                    if distribution_result["is_mixed"]:
                        stats["mixed_units"] += 1
                    
                    if distribution_result["duplicates_detected"]:
                        stats["duplicates_found"] += 1
                    
                    extension_mismatches = len(distribution_result["distribution_details"].get("extension_mismatches", []))
                    stats["extension_mismatches"] += extension_mismatches
                    
                    # Сохраняем детали несоответствий расширений
                    for file_info in distribution_result["files"]:
                        if not file_info.get("extension_matches_content", True):
                            mismatch_detail = {
                                "unit_id": unit_id,
                                "file_name": file_info.get("original_name", "unknown"),
                                "extension": file_info.get("extension", "unknown"),
                                "expected_type": file_info.get("extension", "").replace(".", ""),
                                "detected_type": file_info.get("detected_type", "unknown"),
                                "mime_type": file_info.get("mime_type", "unknown")
                            }
                            stats["extension_mismatch_details"].append(mismatch_detail)
                    
                    for file_type in distribution_result["file_types"]:
                        stats["file_types"][file_type] += 1
                    
                    # Определяем целевую директорию для статистики
                    target_dir = Path(distribution_result["target_dir"])
                    if "mixed" in str(target_dir):
                        stats["target_dirs"]["mixed"] += 1
                    else:
                        parent_name = target_dir.parent.name if target_dir.parent.name != "detected" else target_dir.name
                        stats["target_dirs"][parent_name] += 1
                    
                    # Выводим результат
                    status_icon = "🔀" if distribution_result["is_mixed"] else "✓"
                    print(f"{status_icon} {', '.join(distribution_result['file_types'])}")
                
                except Exception as e:
                    stats["errors"] += 1
                    error_msg = str(e)
                    print(f"✗ Ошибка: {error_msg[:50]}")
                    # Отслеживаем units с ошибками
                    stats["unprocessed_units"].append({
                        "unit_id": unit_id,
                        "reason": "error",
                        "message": error_msg,
                        "error_type": type(e).__name__
                    })
            
            duration = time.time() - start_time
            
            # Выводим итоговую статистику
            print(f"\n{'='*80}")
            print("РЕЗУЛЬТАТЫ ОБРАБОТКИ")
            print(f"{'='*80}")
            print(f"Обработано unit'ов: {stats['processed_units']}/{len(unit_dirs)}")
            print(f"Обработано файлов: {stats['processed_files']}")
            print(f"Время выполнения: {duration:.2f} сек")
            if stats['processed_units'] > 0:
                print(f"Среднее время на unit: {duration/stats['processed_units']:.2f} сек")
            
            print(f"\nРаспределение по типам:")
            for file_type, count in sorted(stats['file_types'].items()):
                print(f"  {file_type}: {count}")
            
            print(f"\nРаспределение по директориям:")
            for target_dir, count in sorted(stats['target_dirs'].items()):
                print(f"  {target_dir}: {count} unit'ов")
            
            print(f"\nОсобые случаи:")
            print(f"  Mixed units: {stats['mixed_units']}")
            print(f"  Дубликаты: {stats['duplicates_found']} unit'ов")
            print(f"  Несоответствий расширений: {stats['extension_mismatches']}")
            print(f"  Ошибок: {stats['errors']}")
            
            # Выводим информацию о необработанных units
            unprocessed_count = len(stats.get("unprocessed_units", []))
            if unprocessed_count > 0:
                print(f"\nНеобработанные units: {unprocessed_count}")
                # Группируем по причинам
                by_reason = defaultdict(list)
                for unit in stats["unprocessed_units"]:
                    by_reason[unit["reason"]].append(unit)
                
                for reason, units in sorted(by_reason.items()):
                    reason_name = {
                        "no_files": "Без файлов",
                        "error": "Ошибка обработки"
                    }.get(reason, reason)
                    print(f"  {reason_name}: {len(units)} unit'ов")
                    if len(units) <= 10:
                        for unit_info in units:
                            uid = unit_info["unit_id"]
                            diagnosis = unit_info.get("diagnosis", {})
                            if diagnosis:
                                reasons = diagnosis.get("possible_reasons", [])
                                if reasons:
                                    print(f"    - {uid}: {reasons[0]}")
                                else:
                                    print(f"    - {uid}")
                            else:
                                print(f"    - {uid}")
                    else:
                        for unit_info in units[:5]:
                            uid = unit_info["unit_id"]
                            diagnosis = unit_info.get("diagnosis", {})
                            if diagnosis:
                                reasons = diagnosis.get("possible_reasons", [])
                                if reasons:
                                    print(f"    - {uid}: {reasons[0]}")
                                else:
                                    print(f"    - {uid}")
                            else:
                                print(f"    - {uid}")
                        print(f"    ... и еще {len(units) - 5} unit'ов")
            
            # Выводим детали несоответствий расширений
            if stats.get("extension_mismatch_details"):
                print(f"\nДетали несоответствий расширений:")
                # Группируем по типам несоответствий
                mismatch_groups = defaultdict(int)
                for detail in stats["extension_mismatch_details"]:
                    key = f"{detail['extension']} → {detail['detected_type']}"
                    mismatch_groups[key] += 1
                
                for mismatch_type, count in sorted(mismatch_groups.items(), key=lambda x: x[1], reverse=True):
                    print(f"  {mismatch_type}: {count}")
            
            print(f"{'='*80}\n")
        
        except ImportError as e:
            print(f"\n✗ Ошибка импорта модулей: {e}")
            print("Убедитесь, что все зависимости установлены.")
        except Exception as e:
            print(f"\n✗ Ошибка обработки: {e}")
            import traceback
            traceback.print_exc()
    
    def handle_extract_archive(self, limit: Optional[int] = None):
        """Обработка распаковки архивов."""
        print("\n=== Распаковка архивов ===")
        if limit is None:
            limit_str = input(f"Лимит обработки (0 = все, текущий: {LIMIT_EXTRACT_ARCHIVE}): ").strip()
            limit = int(limit_str) if limit_str else LIMIT_EXTRACT_ARCHIVE
        
        print(f"Обработка архивов с лимитом {limit if limit > 0 else 'без ограничений'}...")
        print("Используйте API endpoint: POST /trigger/extract_archive")
    
    
    def handle_normalize(self, limit: Optional[int] = None):
        """Обработка нормализации файлов."""
        print("\n=== Нормализация файлов ===")
        if limit is None:
            limit_str = input(f"Лимит обработки (0 = все, текущий: {LIMIT_NORMALIZE}): ").strip()
            limit = int(limit_str) if limit_str else LIMIT_NORMALIZE
        
        print(f"Нормализация файлов с лимитом {limit if limit > 0 else 'без ограничений'}...")
        print("Используйте API endpoint: POST /trigger/normalize")
    
    def handle_create_manifest(self, limit: Optional[int] = None):
        """Обработка создания manifest."""
        print("\n=== Создание manifest ===")
        if limit is None:
            limit_str = input(f"Лимит обработки (0 = все, текущий: {LIMIT_CREATE_MANIFEST}): ").strip()
            limit = int(limit_str) if limit_str else LIMIT_CREATE_MANIFEST
        
        print(f"Создание manifest с лимитом {limit if limit > 0 else 'без ограничений'}...")
        print("Используйте API endpoint: POST /trigger/create_manifest")
    
    def show_statistics(self):
        """Показывает статистику по этапам."""
        print("\n=== Статистика по этапам ===")
        stats = self.state_manager.get_statistics()
        
        print(f"\nЭтап 1 (uploaded):     {len(list(INPUT_DIR.iterdir()))} файлов в input/")
        print(f"Этап 2 (detected):     {stats['detected']['count']} файлов")
        print(f"  По типам: {stats['detected']['by_type']}")
        print(f"Этап 3 (extracted):    {stats['extracted']['count']} файлов (из {stats['extracted']['archives_processed']} архивов)")
        print(f"Этап 4 (converted):    {stats['converted']['count']} файлов")
        print(f"Этап 5 (normalized):   {stats['normalized']['count']} unit'ов")
        print(f"Этап 6 (ready):        {stats['ready']['count']} unit'ов готовы для Docling")
        
        print("\nТекущие лимиты:")
        limits = get_limits()
        for stage, limit in limits.items():
            print(f"  {stage}: {limit if limit > 0 else 'без ограничений'}")
    
    def show_metrics(self, stage: Optional[str] = None):
        """Показывает метрики обработки."""
        print("\n=== Метрики обработки ===")
        metrics = get_processing_summary()
        
        if not metrics:
            print("Метрики не найдены")
            return
        
        summary = metrics.get("summary", {})
        print(f"\nСессия: {metrics.get('session_id', 'N/A')}")
        print(f"Начало: {metrics.get('started_at', 'N/A')}")
        print(f"Завершение: {metrics.get('completed_at', 'N/A')}")
        print(f"\nСтатистика:")
        print(f"  Всего файлов: {summary.get('total_input_files', 0)}")
        print(f"  Всего архивов: {summary.get('total_archives', 0)}")
        print(f"  Всего unit'ов: {summary.get('total_units', 0)}")
        print(f"  Ошибок: {summary.get('total_errors', 0)}")
    
    def show_logs(self, filter_by: Optional[str] = None):
        """Показывает логи."""
        print("\n=== Логи ===")
        print("Логи доступны через API endpoint: GET /metrics/processing")
        print("Или проверьте логи сервиса router")
    
    def configure_limits(self):
        """Настройка лимитов обработки."""
        print("\n=== Настройки лимитов обработки ===")
        limits = get_limits()
        
        print("\nТекущие лимиты:")
        print("1. Определение типа:     ", limits.get("detect_type", 0), "(0 = без ограничений)")
        print("2. Распаковка архивов:   ", limits.get("extract_archive", 0), "(0 = без ограничений)")
        print("3. Конвертация DOC:      ", limits.get("convert_doc", 0), "(0 = без ограничений)")
        print("4. Нормализация:         ", limits.get("normalize", 0), "(0 = без ограничений)")
        print("5. Создание manifest:    ", limits.get("create_manifest", 0), "(0 = без ограничений)")
        
        choice = input("\nИзменить лимит [1-5] или 0 для возврата: ").strip()
        
        if choice == "0":
            return
        
        stage_map = {
            "1": "detect_type",
            "2": "extract_archive",
            "3": "convert_doc",
            "4": "normalize",
            "5": "create_manifest"
        }
        
        if choice in stage_map:
            stage = stage_map[choice]
            new_limit = input(f"Введите новое значение (0 = без ограничений): ").strip()
            try:
                limit_value = int(new_limit)
                if update_limit(stage, limit_value):
                    print(f"Лимит для {stage} обновлен: {limit_value}")
                else:
                    print("Ошибка обновления лимита")
            except ValueError:
                print("Неверное значение")
        else:
            print("Неверный выбор")
    
    def run_full_pipeline(self, limits: Optional[Dict[str, int]] = None):
        """Запуск полного пайплайна."""
        print("\n=== Автоматическая обработка ===")
        print("Запуск полного пайплайна для всех файлов из input/")
        print("Используйте API endpoint: POST /process_now")
        print("Или запустите через API клиент")
    
    def run(self):
        """Главный цикл CLI."""
        while True:
            try:
                self.show_menu()
                choice = input("\nВыберите действие [0-18]: ").strip()
                
                if choice == "0":
                    print("Выход...")
                    break
                elif choice == "1":
                    self.handle_download_protocols()
                elif choice == "2":
                    self.handle_detect_type()
                elif choice == "3":
                    self.handle_extract_archive()
                elif choice == "4":
                    self.handle_convert_doc()
                elif choice == "5":
                    self.handle_normalize()
                elif choice == "6":
                    self.handle_create_manifest()
                elif choice == "7":
                    self.show_statistics()
                elif choice == "8":
                    self.show_metrics()
                elif choice == "9":
                    self.show_logs()
                elif choice == "10":
                    self.configure_limits()
                elif choice == "11":
                    self.run_full_pipeline()
                else:
                    print("Неверный выбор. Попробуйте снова.")
                
                input("\nНажмите Enter для продолжения...")
            
            except KeyboardInterrupt:
                print("\n\nВыход...")
                break
            except Exception as e:
                print(f"\nОшибка: {e}")
                import traceback
                traceback.print_exc()
                input("\nНажмите Enter для продолжения...")


    def handle_sync_protocols(self):
        """Обработка синхронизации протоколов из удалённой MongoDB."""
        print("\n=== Синхронизация протоколов из удалённой MongoDB ===")
        
        # Проверка подключения к удалённой MongoDB
        print("\n1. Проверка подключения к удалённой MongoDB...")
        remote_client = get_remote_mongo_client()
        if not remote_client:
            print("✗ Не удалось подключиться к удалённой MongoDB")
            print("  Проверьте настройки в .env:")
            print("    - mongoServer или MONGO_SERVER")
            print("    - readAllUser или MONGO_USER")
            print("    - readAllPassword или MONGO_PASSWORD")
            print("    - sslCertPath или MONGO_SSL_CERT")
            return
        
        remote_client.close()
        print("✓ Подключение к удалённой MongoDB успешно")
        
        # Проверка подключения к локальной MongoDB
        print("\n2. Проверка подключения к локальной MongoDB...")
        local_client = get_local_mongo_client()
        if not local_client:
            print("✗ Не удалось подключиться к локальной MongoDB")
            print("  Проверьте настройки:")
            print("    - LOCAL_MONGO_SERVER (по умолчанию: localhost:27017)")
            print("    - MONGO_METADATA_USER")
            print("    - MONGO_METADATA_PASSWORD")
            return
        
        local_client.close()
        print("✓ Подключение к локальной MongoDB успешно")
        
        # Выбор даты
        print("\n3. Выбор даты для синхронизации:")
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
        
        # Лимит
        limit_str = input(f"\n4. Лимит протоколов для синхронизации (по умолчанию: 200): ").strip()
        limit = int(limit_str) if limit_str else 200
        
        # Запуск синхронизации
        print(f"\n5. Запуск синхронизации...")
        print(f"   Дата: {target_date.date()}")
        print(f"   Лимит: {limit}")
        
        result = sync_protocols_for_date(target_date, limit)
        
        if result.get("status") == "success":
            print("\n✓ Синхронизация завершена успешно!")
            print(f"   Просмотрено: {result.get('scanned', 0)}")
            print(f"   Вставлено: {result.get('inserted', 0)}")
            print(f"   Пропущено: {result.get('skipped_existing', 0)}")
            if result.get("errors_count", 0) > 0:
                print(f"   Ошибок: {result.get('errors_count', 0)}")
        else:
            print(f"\n✗ Ошибка синхронизации: {result.get('message', 'Unknown error')}")
    
    
    def handle_download_protocols(self):
        """Обработка скачивания протоколов из MongoDB через VPN."""
        print("\n=== Скачивание протоколов из MongoDB (с VPN) ===")
        
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
            downloader = ProtocolDownloader(output_dir=INPUT_DIR)
            start_time = time.time()
            result = downloader.process_pending_protocols(limit=limit)
            duration = time.time() - start_time
            
            if result.get("health_ok"):
                print("\n" + "=" * 80)
                print("✓ СКАЧИВАНИЕ ЗАВЕРШЕНО")
                print("=" * 80)
                print(f"  Успешно обработано: {result.get('processed_ok', 0)} протоколов")
                print(f"  Ошибок: {result.get('processed_error', 0)} протоколов")
                print(f"  Скачано файлов: {result.get('downloaded_files_count', 0)}")
                print(f"  Ошибок скачивания файлов: {result.get('failed_files_count', 0)}")
                print(f"  Время выполнения: {duration:.2f} сек")
                if result.get('processed_ok', 0) > 0:
                    avg_time = duration / result.get('processed_ok', 1)
                    print(f"  Среднее время на протокол: {avg_time:.2f} сек")
            else:
                print("\n✗ Скачивание не выполнено из-за проблем с VPN")
                
        except Exception as e:
            print(f"\n✗ Ошибка при скачивании протоколов: {e}")
            import traceback
            traceback.print_exc()
    
    def handle_detect_type(self, limit: Optional[int] = None):
        """Обработка определения типа файла на уровне unit'ов (протоколов)."""
        print("\n=== Определение типа файла (на уровне unit'ов) ===")
        if limit is None:
            limit_str = input(f"Лимит обработки (0 = все, текущий: {LIMIT_DETECT_TYPE}): ").strip()
            limit = int(limit_str) if limit_str else LIMIT_DETECT_TYPE
        
        print(f"\nОбработка файлов из input/ с лимитом {limit if limit > 0 else 'без ограничений'}...")
        print("Файлы одного протокола/юнита обрабатываются вместе и не разделяются.")
        
        try:
            # Импортируем необходимые модули
            from services.router.unit_distribution import distribute_unit_by_types
            from services.router.mongo import save_file_detection_metadata, save_unit_distribution_metadata
            from services.router.config import INPUT_DIR, ensure_directories
            from pathlib import Path
            import time
            from collections import defaultdict
            
            ensure_directories()
            
            # Получаем список unit'ов
            unit_dirs = [d for d in INPUT_DIR.iterdir() if d.is_dir() and d.name.startswith("UNIT_")]
            total_units = len(unit_dirs)
            
            if limit > 0:
                unit_dirs = unit_dirs[:limit]
            
            print(f"\nНайдено unit'ов: {total_units}")
            print(f"Обрабатывается: {len(unit_dirs)}")
            print(f"{'='*80}\n")
            
            # Статистика
            stats = {
                "processed_units": 0,
                "processed_files": 0,
                "mixed_units": 0,
                "duplicates_found": 0,
                "extension_mismatches": 0,
                "errors": 0,
                "file_types": defaultdict(int),
                "target_dirs": defaultdict(int),
                "unprocessed_units": [],  # Units которые не были обработаны с причинами
                "extension_mismatch_details": []  # Детали несоответствий расширений
            }
            
            start_time = time.time()
            
            for idx, unit_dir in enumerate(unit_dirs, 1):
                unit_id = unit_dir.name
                files = [f for f in unit_dir.iterdir() if f.is_file() and not f.name.startswith('.')]
                
                if not files:
                    # Отслеживаем units без файлов
                    stats["unprocessed_units"].append({
                        "unit_id": unit_id,
                        "reason": "no_files",
                        "message": "Unit не содержит файлов"
                    })
                    continue
                
                print(f"[{idx}/{len(unit_dirs)}] {unit_id} ({len(files)} файл(ов))...", end=" ", flush=True)
                
                try:
                    # Подготавливаем список файлов
                    files_list = [{"path": str(f)} for f in files]
                    
                    # Распределяем unit
                    distribution_result = distribute_unit_by_types(
                        unit_id=unit_id,
                        files=files_list,
                        unit_metadata=None
                    )
                    
                    # Сохраняем метаданные
                    for file_info in distribution_result["files"]:
                        try:
                            save_file_detection_metadata(
                                file_path=file_info["path"],
                                file_info=file_info,
                                unit_id=unit_id,
                                protocol_info=None
                            )
                        except Exception:
                            pass  # Игнорируем ошибки MongoDB
                    
                    try:
                        save_unit_distribution_metadata(unit_id, distribution_result)
                    except Exception:
                        pass
                    
                    # Обновляем статистику
                    stats["processed_units"] += 1
                    stats["processed_files"] += len(distribution_result["files"])
                    
                    if distribution_result["is_mixed"]:
                        stats["mixed_units"] += 1
                    
                    if distribution_result["duplicates_detected"]:
                        stats["duplicates_found"] += 1
                    
                    extension_mismatches = len(distribution_result["distribution_details"].get("extension_mismatches", []))
                    stats["extension_mismatches"] += extension_mismatches
                    
                    # Сохраняем детали несоответствий расширений
                    for file_info in distribution_result["files"]:
                        if not file_info.get("extension_matches_content", True):
                            mismatch_detail = {
                                "unit_id": unit_id,
                                "file_name": file_info.get("original_name", "unknown"),
                                "extension": file_info.get("extension", "unknown"),
                                "expected_type": file_info.get("extension", "").replace(".", ""),
                                "detected_type": file_info.get("detected_type", "unknown"),
                                "mime_type": file_info.get("mime_type", "unknown")
                            }
                            stats["extension_mismatch_details"].append(mismatch_detail)
                    
                    for file_type in distribution_result["file_types"]:
                        stats["file_types"][file_type] += 1
                    
                    # Определяем целевую директорию для статистики
                    target_dir = Path(distribution_result["target_dir"])
                    if "mixed" in str(target_dir):
                        stats["target_dirs"]["mixed"] += 1
                    else:
                        parent_name = target_dir.parent.name if target_dir.parent.name != "detected" else target_dir.name
                        stats["target_dirs"][parent_name] += 1
                    
                    # Выводим результат
                    status_icon = "🔀" if distribution_result["is_mixed"] else "✓"
                    print(f"{status_icon} {', '.join(distribution_result['file_types'])}")
                
                except Exception as e:
                    stats["errors"] += 1
                    error_msg = str(e)
                    print(f"✗ Ошибка: {error_msg[:50]}")
                    # Отслеживаем units с ошибками
                    stats["unprocessed_units"].append({
                        "unit_id": unit_id,
                        "reason": "error",
                        "message": error_msg,
                        "error_type": type(e).__name__
                    })
            
            duration = time.time() - start_time
            
            # Выводим итоговую статистику
            print(f"\n{'='*80}")
            print("РЕЗУЛЬТАТЫ ОБРАБОТКИ")
            print(f"{'='*80}")
            print(f"Обработано unit'ов: {stats['processed_units']}/{len(unit_dirs)}")
            print(f"Обработано файлов: {stats['processed_files']}")
            print(f"Время выполнения: {duration:.2f} сек")
            if stats['processed_units'] > 0:
                print(f"Среднее время на unit: {duration/stats['processed_units']:.2f} сек")
            
            print(f"\nРаспределение по типам:")
            for file_type, count in sorted(stats['file_types'].items()):
                print(f"  {file_type}: {count}")
            
            print(f"\nРаспределение по директориям:")
            for target_dir, count in sorted(stats['target_dirs'].items()):
                print(f"  {target_dir}: {count} unit'ов")
            
            print(f"\nОсобые случаи:")
            print(f"  Mixed units: {stats['mixed_units']}")
            print(f"  Дубликаты: {stats['duplicates_found']} unit'ов")
            print(f"  Несоответствий расширений: {stats['extension_mismatches']}")
            print(f"  Ошибок: {stats['errors']}")
            
            # Выводим информацию о необработанных units
            unprocessed_count = len(stats.get("unprocessed_units", []))
            if unprocessed_count > 0:
                print(f"\nНеобработанные units: {unprocessed_count}")
                # Группируем по причинам
                by_reason = defaultdict(list)
                for unit in stats["unprocessed_units"]:
                    by_reason[unit["reason"]].append(unit)
                
                for reason, units in sorted(by_reason.items()):
                    reason_name = {
                        "no_files": "Без файлов",
                        "error": "Ошибка обработки"
                    }.get(reason, reason)
                    print(f"  {reason_name}: {len(units)} unit'ов")
                    if len(units) <= 10:
                        for unit_info in units:
                            uid = unit_info["unit_id"]
                            diagnosis = unit_info.get("diagnosis", {})
                            if diagnosis:
                                reasons = diagnosis.get("possible_reasons", [])
                                if reasons:
                                    print(f"    - {uid}: {reasons[0]}")
                                else:
                                    print(f"    - {uid}")
                            else:
                                print(f"    - {uid}")
                    else:
                        for unit_info in units[:5]:
                            uid = unit_info["unit_id"]
                            diagnosis = unit_info.get("diagnosis", {})
                            if diagnosis:
                                reasons = diagnosis.get("possible_reasons", [])
                                if reasons:
                                    print(f"    - {uid}: {reasons[0]}")
                                else:
                                    print(f"    - {uid}")
                            else:
                                print(f"    - {uid}")
                        print(f"    ... и еще {len(units) - 5} unit'ов")
            
            # Выводим детали несоответствий расширений
            if stats.get("extension_mismatch_details"):
                print(f"\nДетали несоответствий расширений:")
                # Группируем по типам несоответствий
                mismatch_groups = defaultdict(int)
                for detail in stats["extension_mismatch_details"]:
                    key = f"{detail['extension']} → {detail['detected_type']}"
                    mismatch_groups[key] += 1
                
                for mismatch_type, count in sorted(mismatch_groups.items(), key=lambda x: x[1], reverse=True):
                    print(f"  {mismatch_type}: {count}")
            
            print(f"{'='*80}\n")
        
        except ImportError as e:
            print(f"\n✗ Ошибка импорта модулей: {e}")
            print("Убедитесь, что все зависимости установлены.")
        except Exception as e:
            print(f"\n✗ Ошибка обработки: {e}")
            import traceback
            traceback.print_exc()
    
    def handle_extract_archive(self, limit: Optional[int] = None):
        """Обработка распаковки архивов."""
        print("\n=== Распаковка архивов ===")
        if limit is None:
            limit_str = input(f"Лимит обработки (0 = все, текущий: {LIMIT_EXTRACT_ARCHIVE}): ").strip()
            limit = int(limit_str) if limit_str else LIMIT_EXTRACT_ARCHIVE
        
        print(f"Обработка архивов с лимитом {limit if limit > 0 else 'без ограничений'}...")
        print("Используйте API endpoint: POST /trigger/extract_archive")
    
    
    def handle_normalize(self, limit: Optional[int] = None):
        """Обработка нормализации файлов."""
        print("\n=== Нормализация файлов ===")
        if limit is None:
            limit_str = input(f"Лимит обработки (0 = все, текущий: {LIMIT_NORMALIZE}): ").strip()
            limit = int(limit_str) if limit_str else LIMIT_NORMALIZE
        
        print(f"Нормализация файлов с лимитом {limit if limit > 0 else 'без ограничений'}...")
        print("Используйте API endpoint: POST /trigger/normalize")
    
    def handle_create_manifest(self, limit: Optional[int] = None):
        """Обработка создания manifest."""
        print("\n=== Создание manifest ===")
        if limit is None:
            limit_str = input(f"Лимит обработки (0 = все, текущий: {LIMIT_CREATE_MANIFEST}): ").strip()
            limit = int(limit_str) if limit_str else LIMIT_CREATE_MANIFEST
        
        print(f"Создание manifest с лимитом {limit if limit > 0 else 'без ограничений'}...")
        print("Используйте API endpoint: POST /trigger/create_manifest")
    
    def show_statistics(self):
        """Показывает статистику по этапам."""
        print("\n=== Статистика по этапам ===")
        stats = self.state_manager.get_statistics()
        
        print(f"\nЭтап 1 (uploaded):     {len(list(INPUT_DIR.iterdir()))} файлов в input/")
        print(f"Этап 2 (detected):     {stats['detected']['count']} файлов")
        print(f"  По типам: {stats['detected']['by_type']}")
        print(f"Этап 3 (extracted):    {stats['extracted']['count']} файлов (из {stats['extracted']['archives_processed']} архивов)")
        print(f"Этап 4 (converted):    {stats['converted']['count']} файлов")
        print(f"Этап 5 (normalized):   {stats['normalized']['count']} unit'ов")
        print(f"Этап 6 (ready):        {stats['ready']['count']} unit'ов готовы для Docling")
        
        print("\nТекущие лимиты:")
        limits = get_limits()
        for stage, limit in limits.items():
            print(f"  {stage}: {limit if limit > 0 else 'без ограничений'}")
    
    def show_metrics(self, stage: Optional[str] = None):
        """Показывает метрики обработки."""
        print("\n=== Метрики обработки ===")
        metrics = get_processing_summary()
        
        if not metrics:
            print("Метрики не найдены")
            return
        
        summary = metrics.get("summary", {})
        print(f"\nСессия: {metrics.get('session_id', 'N/A')}")
        print(f"Начало: {metrics.get('started_at', 'N/A')}")
        print(f"Завершение: {metrics.get('completed_at', 'N/A')}")
        print(f"\nСтатистика:")
        print(f"  Всего файлов: {summary.get('total_input_files', 0)}")
        print(f"  Всего архивов: {summary.get('total_archives', 0)}")
        print(f"  Всего unit'ов: {summary.get('total_units', 0)}")
        print(f"  Ошибок: {summary.get('total_errors', 0)}")
    
    def show_logs(self, filter_by: Optional[str] = None):
        """Показывает логи."""
        print("\n=== Логи ===")
        print("Логи доступны через API endpoint: GET /metrics/processing")
        print("Или проверьте логи сервиса router")
    
    def configure_limits(self):
        """Настройка лимитов обработки."""
        print("\n=== Настройки лимитов обработки ===")
        limits = get_limits()
        
        print("\nТекущие лимиты:")
        print("1. Определение типа:     ", limits.get("detect_type", 0), "(0 = без ограничений)")
        print("2. Распаковка архивов:   ", limits.get("extract_archive", 0), "(0 = без ограничений)")
        print("3. Конвертация DOC:      ", limits.get("convert_doc", 0), "(0 = без ограничений)")
        print("4. Нормализация:         ", limits.get("normalize", 0), "(0 = без ограничений)")
        print("5. Создание manifest:    ", limits.get("create_manifest", 0), "(0 = без ограничений)")
        
        choice = input("\nИзменить лимит [1-5] или 0 для возврата: ").strip()
        
        if choice == "0":
            return
        
        stage_map = {
            "1": "detect_type",
            "2": "extract_archive",
            "3": "convert_doc",
            "4": "normalize",
            "5": "create_manifest"
        }
        
        if choice in stage_map:
            stage = stage_map[choice]
            new_limit = input(f"Введите новое значение (0 = без ограничений): ").strip()
            try:
                limit_value = int(new_limit)
                if update_limit(stage, limit_value):
                    print(f"Лимит для {stage} обновлен: {limit_value}")
                else:
                    print("Ошибка обновления лимита")
            except ValueError:
                print("Неверное значение")
        else:
            print("Неверный выбор")
    
    def run_full_pipeline(self, limits: Optional[Dict[str, int]] = None):
        """Запуск полного пайплайна."""
        print("\n=== Автоматическая обработка ===")
        print("Запуск полного пайплайна для всех файлов из input/")
        print("Используйте API endpoint: POST /process_now")
        print("Или запустите через API клиент")
    
    def handle_cleanup(self):
        """Очистка директорий и данных из MongoDB."""
        print("\n=== Очистка директорий и данных из MongoDB ===")
        print("\n⚠️  ВНИМАНИЕ: Эта операция удалит:")
        print("  - Все файлы из директорий обработки (НОВАЯ СИСТЕМА)")
        print("  - Все данные из коллекций MongoDB")
        print("\nДиректории для очистки:")
        print(f"  - {INPUT_DIR}")
        print(f"  - {PENDING_DIR}")
        print(f"  - {READY_DOCLING_DIR}")
        print(f"  - {TEMP_DIR}")
        print("\nКоллекции MongoDB для очистки:")
        print(f"  - {MONGO_METADATA_DB}.protocols")
        print(f"  - {MONGO_METADATA_DB}.file_detections")
        print(f"  - {MONGO_METADATA_DB}.unit_distributions")
        print(f"  - {MONGO_METADATA_DB}.{MONGO_METADATA_COLLECTION}")
        print(f"  - {MONGO_METADATA_DB}.{MONGO_METRICS_COLLECTION}")
        
        confirm = input("\nПродолжить очистку? (yes/no): ").strip().lower()
        if confirm != "yes":
            print("Очистка отменена.")
            return
        
        print("\nНачало очистки...")
        
        # Очистка директорий
        directories = [
            INPUT_DIR, PENDING_DIR, READY_DOCLING_DIR, TEMP_DIR
        ]
        
        dirs_cleaned = 0
        files_removed = 0
        
        for directory in directories:
            if not directory.exists():
                continue
            
            try:
                file_count = sum(1 for _ in directory.rglob("*") if _.is_file())
                files_removed += file_count
                
                for item in directory.iterdir():
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
                
                dirs_cleaned += 1
                print(f"  ✓ Очищена директория: {directory.name} ({file_count} файлов)")
            except Exception as e:
                print(f"  ✗ Ошибка при очистке {directory.name}: {e}")
        
        # Очистка MongoDB коллекций
        client = None
        try:
            print("\nОчистка коллекций MongoDB...")
            client = get_metadata_client()
            if not client:
                print("  ✗ Не удалось подключиться к MongoDB")
            else:
                db = client[MONGO_METADATA_DB]
                collections_to_clean = [
                    ("protocols", "Протоколы"),
                    ("file_detections", "Метаданные файлов"),
                    ("unit_distributions", "Распределения unit'ов"),
                    (MONGO_METADATA_COLLECTION, "Манифесты"),
                    (MONGO_METRICS_COLLECTION, "Метрики обработки"),
                ]
                
                for coll_name, description in collections_to_clean:
                    try:
                        coll = db[coll_name]
                        count = coll.count_documents({})
                        if count > 0:
                            coll.delete_many({})
                            print(f"  ✓ Очищена коллекция {coll_name} ({description}): {count} документов")
                        else:
                            print(f"  - Коллекция {coll_name} уже пуста")
                    except Exception as e:
                        print(f"  ✗ Ошибка при очистке {coll_name}: {e}")
        
        except Exception as e:
            print(f"\n✗ Ошибка при подключении к MongoDB: {e}")
        finally:
            if client:
                client.close()
        
        print("\n" + "=" * 80)
        print("✓ ОЧИСТКА ЗАВЕРШЕНА")
        print("=" * 80)
        print(f"  Очищено директорий: {dirs_cleaned}")
        print(f"  Удалено файлов: {files_removed}")
        print("\nВсе данные удалены. Можно начинать новый цикл обработки.")
    
    def handle_check_sorted_units(self):
        """Проверка отсортированных units после определения типов."""
        print("\n=== Проверка отсортированных units ===")
        
        try:
            import subprocess
            import sys
            from pathlib import Path
            
            script_path = Path(__file__).parent.parent.parent / "scripts" / "check_sorted_units.py"
            
            if not script_path.exists():
                print(f"✗ Скрипт не найден: {script_path}")
                return
            
            print("\nЗапуск проверки...")
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=False,
                text=True
            )
            
            if result.returncode != 0:
                print("\n⚠ Обнаружены проблемы при проверке")
            else:
                print("\n✓ Проверка завершена успешно")
        
        except Exception as e:
            print(f"\n✗ Ошибка при проверке: {e}")
            import traceback
            traceback.print_exc()
    
    
    def handle_analyze_detection_issues(self):
        """Анализ проблем определения типов файлов."""
        print("\n=== Анализ проблем определения типов файлов ===")
        
        session_id = input("ID сессии для анализа (Enter = последняя сессия): ").strip()
        session_id = session_id if session_id else None
        
        try:
            import subprocess
            import sys
            from pathlib import Path
            
            script_path = Path(__file__).parent.parent.parent / "scripts" / "analyze_detection_issues.py"
            
            if not script_path.exists():
                print(f"✗ Скрипт не найден: {script_path}")
                return
            
            print("\nЗапуск анализа...")
            cmd = [sys.executable, str(script_path)]
            if session_id:
                cmd.extend(["--session-id", session_id])
            
            result = subprocess.run(
                cmd,
                capture_output=False,
                text=True
            )
            
            if result.returncode != 0:
                print("\n⚠ Обнаружены проблемы при анализе")
            else:
                print("\n✓ Анализ завершен успешно")
        
        except Exception as e:
            print(f"\n✗ Ошибка при анализе: {e}")
            import traceback
            traceback.print_exc()
    
    def handle_convert_doc_to_html(self):
        """Конвертация DOC → HTML (для файлов из detected/htmlDOC/)."""
        print("\n=== Конвертация DOC → HTML ===")
        
        html_doc_dir = DETECTED_DIR / "htmlDOC"
        if not html_doc_dir.exists():
            print(f"✗ Директория не найдена: {html_doc_dir}")
            return
        
        from .html_processor import process_fake_doc_html
        
        unit_dirs = [d for d in html_doc_dir.iterdir() if d.is_dir() and d.name.startswith("UNIT_")]
        if not unit_dirs:
            print("✓ Нет units для обработки")
            return
        
        print(f"\nНайдено {len(unit_dirs)} units для обработки")
        
        processed = 0
        errors = 0
        
        for unit_dir in unit_dirs:
            unit_id = unit_dir.name
            files_dir = unit_dir / "files"
            
            if not files_dir.exists():
                continue
            
            doc_files = list(files_dir.glob("*.doc"))
            for doc_file in doc_files:
                try:
                    new_path, metadata = process_fake_doc_html(doc_file, unit_id)
                    print(f"✓ {doc_file.name} → {new_path.name}")
                    processed += 1
                except Exception as e:
                    print(f"✗ Ошибка при обработке {doc_file.name}: {e}")
                    errors += 1
        
        print(f"\n✓ Обработано: {processed}, ошибок: {errors}")
    
    def handle_convert_doc_to_xml(self):
        """Конвертация DOC → XML (для файлов из detected/xmlDOC/)."""
        print("\n=== Конвертация DOC → XML ===")
        
        xml_doc_dir = DETECTED_DIR / "xmlDOC"
        if not xml_doc_dir.exists():
            print(f"✗ Директория не найдена: {xml_doc_dir}")
            return
        
        from .xml_processor import process_fake_doc_xml
        
        unit_dirs = [d for d in xml_doc_dir.iterdir() if d.is_dir() and d.name.startswith("UNIT_")]
        if not unit_dirs:
            print("✓ Нет units для обработки")
            return
        
        print(f"\nНайдено {len(unit_dirs)} units для обработки")
        
        processed = 0
        errors = 0
        
        for unit_dir in unit_dirs:
            unit_id = unit_dir.name
            files_dir = unit_dir / "files"
            
            if not files_dir.exists():
                continue
            
            doc_files = list(files_dir.glob("*.doc"))
            for doc_file in doc_files:
                try:
                    new_path, metadata = process_fake_doc_xml(doc_file, unit_id)
                    print(f"✓ {doc_file.name} → {new_path.name}")
                    processed += 1
                except Exception as e:
                    print(f"✗ Ошибка при обработке {doc_file.name}: {e}")
                    errors += 1
        
        print(f"\n✓ Обработано: {processed}, ошибок: {errors}")
    
    def handle_sort_pdf(self):
        """Сортировка PDF на text_pdf и scan_pdf."""
        print("\n=== Сортировка PDF на text_pdf и scan_pdf ===")
        
        limit_str = input("Лимит units для обработки (Enter = все): ").strip()
        limit = int(limit_str) if limit_str else None
        
        from .pdf_sorter import sort_pdf_units, cleanup_already_sorted_units
        
        try:
            result = sort_pdf_units(limit=limit)
            
            if result.get("success"):
                stats = result["statistics"]
                print(f"\n✓ Сортировка завершена")
                print(f"\nСтатистика:")
                print(f"  Всего units: {stats['total_units']}")
                print(f"  Обработано: {stats['processed_units']}")
                if stats.get('skipped_units', 0) > 0:
                    print(f"  Пропущено: {stats['skipped_units']}")
                print(f"  text_pdf: {stats['text_pdf_units']} ({stats['text_pdf_percentage']:.1f}%)")
                print(f"  scan_pdf: {stats['scan_pdf_units']} ({stats['scan_pdf_percentage']:.1f}%)")
                print(f"  Ошибок: {stats['errors']}")
                
                # Очищаем уже отсортированные директории
                print(f"\nОчистка уже отсортированных units...")
                cleanup_result = cleanup_already_sorted_units()
                if cleanup_result.get("success"):
                    removed = cleanup_result.get("removed_count", 0)
                    if removed > 0:
                        print(f"  ✓ Удалено уже отсортированных units: {removed}")
                    else:
                        print(f"  ✓ Нет уже отсортированных units для удаления")
                    if cleanup_result.get("errors"):
                        print(f"  ⚠ Ошибок при очистке: {len(cleanup_result['errors'])}")
                
                # Выводим детали пропущенных units
                if stats.get('skipped_details'):
                    print(f"\nПропущенные units:")
                    by_reason = {}
                    for skipped in stats['skipped_details']:
                        reason = skipped.get('reason', 'unknown')
                        if reason not in by_reason:
                            by_reason[reason] = []
                        by_reason[reason].append(skipped['unit_id'])
                    
                    for reason, unit_ids in sorted(by_reason.items()):
                        reason_name = {
                            "no_files_dir": "Без директории files/",
                            "no_pdf_files": "Без PDF файлов"
                        }.get(reason, reason)
                        print(f"  {reason_name}: {len(unit_ids)} unit'ов")
                        if len(unit_ids) <= 10:
                            for uid in unit_ids:
                                print(f"    - {uid}")
                        else:
                            for uid in unit_ids[:5]:
                                print(f"    - {uid}")
                            print(f"    ... и еще {len(unit_ids) - 5} unit'ов")
            else:
                print(f"\n✗ Ошибка: {result.get('error', 'Неизвестная ошибка')}")
        
        except Exception as e:
            print(f"\n✗ Ошибка при сортировке: {e}")
            import traceback
            traceback.print_exc()
    
    def handle_pending_directories(self):
        """Просмотр содержимого промежуточных директорий."""
        print("\n=== Просмотр промежуточных директорий ===")
        
        # Проверяем существование директорий
        pending_dirs = {
            "PENDING_NORMALIZE_DIR": PENDING_NORMALIZE_DIR,
            "PENDING_CONVERT_DIR": PENDING_CONVERT_DIR,
            "PENDING_EXTRACT_DIR": PENDING_EXTRACT_DIR
        }
        
        for dir_name, dir_path in pending_dirs.items():
            print(f"\n{dir_name}: {dir_path}")
            if not dir_path.exists():
                print("  ✗ Директория не существует")
                continue
            
            # Считаем количество unit'ов
            unit_dirs = [d for d in dir_path.rglob("UNIT_*") if d.is_dir()]
            print(f"  Найдено unit'ов: {len(unit_dirs)}")
            
            # Показываем первые 5 unit'ов
            if unit_dirs:
                print("  Первые unit'ы:")
                for unit_dir in sorted(unit_dirs)[:5]:
                    files_dir = unit_dir / "files"
                    if files_dir.exists():
                        files = [f for f in files_dir.iterdir() if f.is_file()]
                        print(f"    {unit_dir.name}: {len(files)} файлов")
                    else:
                        print(f"    {unit_dir.name}: нет директории files/")
                
                if len(unit_dirs) > 5:
                    print(f"    ... и еще {len(unit_dirs) - 5} unit'ов")
        
        # Показываем статистику по ReadyDocling
        print(f"\nREADY_DOCLING_DIR: {READY_DOCLING_DIR}")
        if READY_DOCLING_DIR.exists():
            # Считаем PDF файлы
            text_pdf_dir = READY_DOCLING_DIR / "pdf" / "text"
            scan_pdf_dir = READY_DOCLING_DIR / "pdf" / "scan"
            
            text_units = []
            scan_units = []
            
            if text_pdf_dir.exists():
                text_units = [d for d in text_pdf_dir.iterdir() if d.is_dir() and d.name.startswith("UNIT_")]
            if scan_pdf_dir.exists():
                scan_units = [d for d in scan_pdf_dir.iterdir() if d.is_dir() and d.name.startswith("UNIT_")]
            
            print(f"  PDF с текстовым слоем: {len(text_units)} unit'ов")
            print(f"  PDF сканы (требуют OCR): {len(scan_units)} unit'ов")
            
            # Считаем другие типы файлов
            other_types = ["docx", "html", "excel", "rtf", "doc", "zip", "rar", "7z", "unknown", "signature"]
            for file_type in other_types:
                type_dir = READY_DOCLING_DIR / file_type
                if type_dir.exists():
                    units = [d for d in type_dir.iterdir() if d.is_dir() and d.name.startswith("UNIT_")]
                    if units:
                        print(f"  {file_type.upper()}: {len(units)} unit'ов")
        else:
            print("  ✗ Директория не существует")
    
    def handle_detailed_metrics(self):
        """Просмотр детализированных метрик."""
        print("\n=== Детализированные метрики ===")
        
        try:
            from .metrics import get_current_metrics, get_processing_summary
            
            # Получаем текущие метрики
            current_metrics = get_current_metrics()
            if current_metrics:
                print("\nТекущая сессия обработки:")
                print(f"  Session ID: {current_metrics.get('session_id', 'N/A')}")
                started_at = current_metrics.get('started_at')
                if started_at:
                    print(f"  Начало: {started_at}")
                
                # Статистика по промежуточным директориям
                pending_processing = current_metrics.get("pending_processing", {})
                if pending_processing:
                    print("\n  Промежуточные директории:")
                    for stage, items in pending_processing.items():
                        print(f"    {stage}: {len(items)} файлов")
                
                # Статистика по дубликатам
                duplicates = current_metrics.get("duplicates", [])
                if duplicates:
                    print(f"\n  Дубликаты:")
                    print(f"    Групп дубликатов: {len(duplicates)}")
                    total_dups = sum(d.get('duplicate_count', 0) for d in duplicates)
                    print(f"    Всего дубликатов: {total_dups}")
            else:
                print("  Нет активной сессии обработки")
            
            # Получаем последние сохраненные метрики
            print("\nПоследняя сохраненная сессия:")
            last_metrics = get_processing_summary()
            if last_metrics:
                print(f"  Session ID: {last_metrics.get('session_id', 'N/A')}")
                started_at = last_metrics.get('started_at')
                completed_at = last_metrics.get('completed_at')
                if started_at:
                    print(f"  Начало: {started_at}")
                if completed_at:
                    print(f"  Завершение: {completed_at}")
                
                # Summary статистика
                summary = last_metrics.get("summary", {})
                if summary:
                    print(f"\n  Общая статистика:")
                    print(f"    Входных файлов: {summary.get('total_input_files', 0)}")
                    print(f"    Архивов: {summary.get('total_archives', 0)}")
                    print(f"    Извлечено файлов: {summary.get('total_extracted', 0)}")
                    print(f"    Unit'ов: {summary.get('total_units', 0)}")
                    print(f"    Ошибок: {summary.get('total_errors', 0)}")
                    
                    # Статистика по промежуточным директориям
                    pending_stats = summary.get("pending_statistics", {})
                    if pending_stats:
                        print(f"\n  Промежуточные директории:")
                        print(f"    В pending/normalize: {pending_stats.get('files_in_pending_normalize', 0)}")
                        print(f"    В pending/convert: {pending_stats.get('files_in_pending_convert', 0)}")
                        print(f"    В pending/extract: {pending_stats.get('files_in_pending_extract', 0)}")
                        print(f"    Обработано из pending: {pending_stats.get('files_processed_from_pending', 0)}")
                    
                    # Статистика по дубликатам
                    duplicate_stats = summary.get("duplicate_statistics", {})
                    if duplicate_stats:
                        print(f"\n  Дубликаты:")
                        print(f"    Всего дубликатов: {duplicate_stats.get('total_duplicate_files', 0)}")
                        print(f"    Групп дубликатов: {duplicate_stats.get('duplicate_groups_count', 0)}")
            else:
                print("  Нет сохраненных метрик")
                
        except Exception as e:
            print(f"✗ Ошибка при получении метрик: {e}")
            import traceback
            traceback.print_exc()
    
    def handle_force_cleanup(self):
        """Принудительная очистка пустых директорий."""
        print("\n=== Принудительная очистка пустых директорий ===")
        
        try:
            from .utils import cleanup_all_empty_unit_directories
            
            # Список базовых директорий для очистки
            base_directories = [
                PENDING_NORMALIZE_DIR,
                PENDING_CONVERT_DIR,
                PENDING_EXTRACT_DIR,
                DETECTED_DIR,
                EXTRACTED_DIR,
                CONVERTED_DIR,
                NORMALIZED_DIR
            ]
            
            # Получаем список всех unit'ов для очистки
            unit_ids = set()
            for base_dir in base_directories:
                if base_dir.exists():
                    for unit_dir in base_dir.rglob("UNIT_*"):
                        if unit_dir.is_dir():
                            unit_ids.add(unit_dir.name)
            
            print(f"Найдено unit'ов для проверки: {len(unit_ids)}")
            
            if not unit_ids:
                print("Нет unit'ов для очистки")
                return
            
            # Запрашиваем подтверждение
            confirm = input(f"Выполнить очистку пустых директорий для {len(unit_ids)} unit'ов? (y/N): ").strip().lower()
            if confirm != 'y':
                print("Очистка отменена")
                return
            
            # Выполняем очистку для каждого unit'а
            total_removed = 0
            errors = []
            
            for i, unit_id in enumerate(sorted(unit_ids), 1):
                if i % 100 == 0:
                    print(f"[{i}/{len(unit_ids)}] Обработано...")
                try:
                    result = cleanup_all_empty_unit_directories(unit_id, base_directories)
                    if result["success"]:
                        total_removed += result["total_removed"]
                    else:
                        errors.extend(result["errors"])
                except Exception as e:
                    errors.append(f"{unit_id}: {e}")
            
            print(f"\nИтоги очистки:")
            print(f"  Удалено директорий: {total_removed}")
            print(f"  Ошибок: {len(errors)}")
            
            if errors:
                print("Первые ошибки:")
                for error in errors[:10]:
                    print(f"  {error}")
                if len(errors) > 10:
                    print(f"  ... и еще {len(errors) - 10} ошибок")
                    
        except Exception as e:
            print(f"✗ Ошибка при очистке: {e}")
            import traceback
            traceback.print_exc()
    
    def handle_view_pending_structure(self):
        """Просмотр новой pending структуры."""
        print("\n=== Новая Pending Структура ===")
        
        try:
            from .unit_distribution_new import get_unit_statistics
            
            stats = get_unit_statistics()
            
            print("\nСтатистика по категориям:")
            for category, data in stats.items():
                if data["units"] > 0 or data["files"] > 0:
                    print(f"\n{category.upper()}:")
                    print(f"  Unit'ов: {data['units']}")
                    print(f"  Файлов: {data['files']}")
            
            # Показываем структуру директорий
            from .config import (
                PENDING_DIRECT_DIR, PENDING_NORMALIZE_DIR, PENDING_CONVERT_DIR,
                PENDING_EXTRACT_DIR, PENDING_SPECIAL_DIR
            )
            
            dirs = {
                "DIRECT": PENDING_DIRECT_DIR,
                "NORMALIZE": PENDING_NORMALIZE_DIR,
                "CONVERT": PENDING_CONVERT_DIR,
                "EXTRACT": PENDING_EXTRACT_DIR,
                "SPECIAL": PENDING_SPECIAL_DIR
            }
            
            print("\n\nПути к директориям:")
            for name, path in dirs.items():
                exists = "✓" if path.exists() else "✗"
                print(f"{exists} {name}: {path}")
                
        except Exception as e:
            print(f"✗ Ошибка: {e}")
            import traceback
            traceback.print_exc()
    
    def handle_category_statistics(self):
        """Статистика по категориям обработки."""
        print("\n=== Статистика по категориям ===")
        
        try:
            from .unit_distribution_new import get_unit_statistics
            from .mixed_unit_handler import get_mixed_units_statistics
            from .merge import get_ready_docling_statistics
            
            # Статистика pending
            print("\n📁 PENDING (промежуточная обработка):")
            pending_stats = get_unit_statistics()
            
            # Добавляем mixed статистику
            mixed_stats = get_mixed_units_statistics(include_extraction=True)
            
            total_pending_units = sum(cat["units"] for cat in pending_stats.values())
            total_pending_files = sum(cat["files"] for cat in pending_stats.values())
            
            print(f"\n  Всего unit'ов: {total_pending_units}")
            print(f"  Всего файлов: {total_pending_files}")
            
            print("\n  По категориям:")
            for category in ["direct", "normalize", "convert", "extract", "special", "mixed"]:
                data = pending_stats.get(category, {"units": 0, "files": 0})
                if data["units"] > 0:
                    print(f"    {category:12} - {data['units']:4} unit'ов, {data['files']:5} файлов")
            
            # Показываем mixed units детально если есть
            if mixed_stats["total_mixed"]["units"] > 0:
                print(f"\n  🔀 Mixed units (детально):")
                if mixed_stats["detection_mixed"]["units"] > 0:
                    print(f"    └─ из detection:  {mixed_stats['detection_mixed']['units']:4} unit'ов, {mixed_stats['detection_mixed']['files']:5} файлов")
                if mixed_stats["extraction_mixed"]["units"] > 0:
                    print(f"    └─ из extraction: {mixed_stats['extraction_mixed']['units']:4} unit'ов, {mixed_stats['extraction_mixed']['files']:5} файлов")
            
            # Статистика ready_docling
            print("\n\n✅ READY_DOCLING (готово для Docling):")
            ready_stats = get_ready_docling_statistics()
            
            print(f"\n  Всего unit'ов: {ready_stats['total_units']}")
            print(f"  Всего файлов: {ready_stats['total_files']}")
            
            if ready_stats['by_type']:
                print("\n  По типам файлов:")
                for file_type, data in sorted(ready_stats['by_type'].items()):
                    print(f"    {file_type:12} - {data['units']:4} unit'ов, {data['files']:5} файлов")
            
        except Exception as e:
            print(f"✗ Ошибка: {e}")
            import traceback
            traceback.print_exc()
    
    def handle_merge_dry_run(self):
        """Merge в ready_docling (DRY RUN режим)."""
        print("\n=== Merge в ready_docling (DRY RUN) ===")
        print("Режим имитации - файлы НЕ будут перемещены\n")
        
        try:
            from .merge import merge_to_ready_docling, print_merge_summary
            
            # Запрашиваем лимит
            limit_input = input("Лимит unit'ов (Enter = без ограничений): ").strip()
            limit = int(limit_input) if limit_input else None
            
            print("\nВыполняю merge в режиме DRY RUN...")
            result = merge_to_ready_docling(dry_run=True, limit=limit)
            
            print_merge_summary(result)
            
        except Exception as e:
            print(f"✗ Ошибка: {e}")
            import traceback
            traceback.print_exc()
    
    def handle_merge_real(self):
        """Merge в ready_docling (РЕАЛЬНЫЙ режим)."""
        print("\n=== Merge в ready_docling (РЕАЛЬНЫЙ РЕЖИМ) ===")
        print("⚠️  ВНИМАНИЕ: Файлы будут РЕАЛЬНО перемещены!\n")
        
        try:
            from .merge import merge_to_ready_docling, print_merge_summary
            
            # Запрашиваем лимит
            limit_input = input("Лимит unit'ов (Enter = без ограничений): ").strip()
            limit = int(limit_input) if limit_input else None
            
            # Подтверждение
            confirm = input(f"\nПеремещать файлы в ready_docling? (y/N): ").strip().lower()
            if confirm != 'y':
                print("Отменено")
                return
            
            print("\nВыполняю РЕАЛЬНЫЙ merge...")
            result = merge_to_ready_docling(dry_run=False, limit=limit)
            
            print_merge_summary(result)
            
            if result['files_moved'] > 0:
                print("\n✓ Merge завершен успешно!")
                
                # Предлагаем очистку
                cleanup = input("\nОчистить pending директории после merge? (y/N): ").strip().lower()
                if cleanup == 'y':
                    from .merge import cleanup_pending_after_merge
                    unit_ids = [f["unit_id"] for f in result.get("distributed_files", [])]
                    cleanup_result = cleanup_pending_after_merge(unit_ids, dry_run=False)
                    print(f"Очищено unit'ов: {cleanup_result['cleaned_units']}")
                    print(f"Удалено директорий: {cleanup_result['cleaned_directories']}")
            
        except Exception as e:
            print(f"✗ Ошибка: {e}")
            import traceback
            traceback.print_exc()
    
    def handle_step1_scan_and_detect(self, limit: Optional[int] = None):
        """ШАГ 1: Сканирование input/ и детекция типов файлов."""
        print("\n=== ШАГ 1: Сканирование и детекция типов файлов ===")
        
        if limit is None:
            limit_str = input(f"Лимит units (Enter = без ограничений): ").strip()
            limit = int(limit_str) if limit_str else None
        
        try:
            from .file_detection import detect_file_type
            from pathlib import Path
            from collections import defaultdict
            import time
            
            # Получаем список unit'ов
            unit_dirs = [d for d in INPUT_DIR.iterdir() if d.is_dir() and d.name.startswith("UNIT_")]
            total_units = len(unit_dirs)
            
            if limit:
                unit_dirs = unit_dirs[:limit]
            
            print(f"\nНайдено unit'ов: {total_units}")
            print(f"Обрабатывается: {len(unit_dirs)}")
            print(f"{'='*80}\n")
            
            start_time = time.time()
            
            # Статистика
            stats = {
                "units_scanned": 0,
                "files_scanned": 0,
                "by_extension": defaultdict(int),
                "by_detected_type": defaultdict(int),
                "extension_mismatches": 0,
                "empty_units": 0
            }
            
            for idx, unit_dir in enumerate(unit_dirs, 1):
                unit_id = unit_dir.name
                files = [f for f in unit_dir.iterdir() if f.is_file() and not f.name.startswith('.')]
                
                if not files:
                    stats["empty_units"] += 1
                    continue
                
                print(f"[{idx}/{len(unit_dirs)}] {unit_id} ({len(files)} файл(ов)):")
                stats["units_scanned"] += 1
                
                for file_path in files:
                    try:
                        # Определяем тип
                        detection = detect_file_type(file_path)
                        
                        ext = file_path.suffix.lower()
                        detected_type = detection.get("detected_type", "unknown")
                        mime = detection.get("mime_type", "unknown")
                        
                        stats["files_scanned"] += 1
                        stats["by_extension"][ext or ".no_ext"] += 1
                        stats["by_detected_type"][detected_type] += 1
                        
                        # Проверка соответствия расширения
                        mismatch = not detection.get("extension_matches_content", True)
                        if mismatch:
                            stats["extension_mismatches"] += 1
                        
                        # Вывод
                        mismatch_flag = " ⚠ MISMATCH" if mismatch else ""
                        print(f"  {file_path.name:40} | {ext:8} → {detected_type:12} | {mime:30}{mismatch_flag}")
                        
                    except Exception as e:
                        print(f"  ✗ {file_path.name}: {str(e)[:40]}")
                
                print()  # Пустая строка между units
            
            duration = time.time() - start_time
            
            # Итоговая статистика
            print(f"{'='*80}")
            print(f"ИТОГИ СКАНИРОВАНИЯ:")
            print(f"{'='*80}")
            print(f"Units обработано: {stats['units_scanned']}")
            print(f"Units пустых: {stats['empty_units']}")
            print(f"Файлов просканировано: {stats['files_scanned']}")
            print(f"Несоответствий расширений: {stats['extension_mismatches']}")
            print(f"Время: {duration:.2f} сек")
            
            print(f"\nПо расширениям:")
            for ext, count in sorted(stats["by_extension"].items(), key=lambda x: -x[1])[:10]:
                print(f"  {ext:15} - {count:4} файл(ов)")
            
            print(f"\nПо определенным типам:")
            for dtype, count in sorted(stats["by_detected_type"].items(), key=lambda x: -x[1])[:10]:
                print(f"  {dtype:15} - {count:4} файл(ов)")
        
        except Exception as e:
            print(f"✗ Ошибка: {e}")
            import traceback
            traceback.print_exc()
    
    def handle_step2_classify(self, limit: Optional[int] = None):
        """ШАГ 2: Классификация файлов по категориям."""
        print("\n=== ШАГ 2: Классификация файлов по категориям ===")
        
        if limit is None:
            limit_str = input(f"Лимит units (Enter = без ограничений): ").strip()
            limit = int(limit_str) if limit_str else None
        
        try:
            from .file_detection import detect_file_type
            from .file_classifier import classify_file
            from collections import defaultdict
            import time
            
            unit_dirs = [d for d in INPUT_DIR.iterdir() if d.is_dir() and d.name.startswith("UNIT_")]
            total_units = len(unit_dirs)
            
            if limit:
                unit_dirs = unit_dirs[:limit]
            
            print(f"\nНайдено unit'ов: {total_units}")
            print(f"Обрабатывается: {len(unit_dirs)}")
            print(f"{'='*80}\n")
            
            start_time = time.time()
            
            stats = {
                "units_classified": 0,
                "files_classified": 0,
                "by_category": defaultdict(int),
                "by_action": defaultdict(int)
            }
            
            for idx, unit_dir in enumerate(unit_dirs, 1):
                unit_id = unit_dir.name
                files = [f for f in unit_dir.iterdir() if f.is_file() and not f.name.startswith('.')]
                
                if not files:
                    continue
                
                print(f"[{idx}/{len(unit_dirs)}] {unit_id}:")
                stats["units_classified"] += 1
                
                for file_path in files:
                    try:
                        detection = detect_file_type(file_path)
                        classification = classify_file(file_path, detection)
                        
                        category = classification["category"]
                        action = classification["action"]
                        reason = classification.get("reason", "")
                        
                        stats["files_classified"] += 1
                        stats["by_category"][category] += 1
                        stats["by_action"][action] += 1
                        
                        print(f"  {file_path.name:40} → {category:12} | {action:15} | {reason}")
                        
                    except Exception as e:
                        print(f"  ✗ {file_path.name}: {str(e)[:40]}")
                
                print()
            
            duration = time.time() - start_time
            
            print(f"{'='*80}")
            print(f"ИТОГИ КЛАССИФИКАЦИИ:")
            print(f"{'='*80}")
            print(f"Units обработано: {stats['units_classified']}")
            print(f"Файлов классифицировано: {stats['files_classified']}")
            print(f"Время: {duration:.2f} сек")
            
            print(f"\nПо категориям:")
            for cat, count in sorted(stats["by_category"].items(), key=lambda x: -x[1]):
                print(f"  {cat:15} - {count:4} файл(ов)")
            
            print(f"\nПо действиям:")
            for act, count in sorted(stats["by_action"].items(), key=lambda x: -x[1]):
                print(f"  {act:15} - {count:4} файл(ов)")
        
        except Exception as e:
            print(f"✗ Ошибка: {e}")
            import traceback
            traceback.print_exc()
    
    def handle_step3_check_duplicates(self, limit: Optional[int] = None):
        """ШАГ 3: Проверка дубликатов."""
        print("\n=== ШАГ 3: Проверка дубликатов ===")
        
        if limit is None:
            limit_str = input(f"Лимит units (Enter = без ограничений): ").strip()
            limit = int(limit_str) if limit_str else None
        
        try:
            from .file_detection import detect_file_type
            from .file_classifier import classify_file
            from .duplicate_detection import detect_duplicates_in_unit
            import time
            
            unit_dirs = [d for d in INPUT_DIR.iterdir() if d.is_dir() and d.name.startswith("UNIT_")]
            total_units = len(unit_dirs)
            
            if limit:
                unit_dirs = unit_dirs[:limit]
            
            print(f"\nНайдено unit'ов: {total_units}")
            print(f"Обрабатывается: {len(unit_dirs)}")
            print(f"{'='*80}\n")
            
            start_time = time.time()
            
            stats = {
                "units_checked": 0,
                "units_with_duplicates": 0,
                "total_duplicate_groups": 0,
                "total_duplicate_files": 0
            }
            
            for idx, unit_dir in enumerate(unit_dirs, 1):
                unit_id = unit_dir.name
                files = [f for f in unit_dir.iterdir() if f.is_file() and not f.name.startswith('.')]
                
                if not files:
                    continue
                
                print(f"[{idx}/{len(unit_dirs)}] {unit_id}:")
                stats["units_checked"] += 1
                
                # Подготавливаем данные для проверки
                classified_files = []
                for file_path in files:
                    try:
                        detection = detect_file_type(file_path)
                        classification = classify_file(file_path, detection)
                        classified_files.append({
                            "path": str(file_path),
                            "original_name": file_path.name,
                            **detection,
                            "classification": classification
                        })
                    except Exception as e:
                        print(f"  ✗ Ошибка обработки {file_path.name}: {e}")
                
                # Проверяем дубликаты
                duplicates_map = detect_duplicates_in_unit(classified_files)
                
                if duplicates_map:
                    stats["units_with_duplicates"] += 1
                    stats["total_duplicate_groups"] += len(duplicates_map)
                    
                    print(f"  ⚠ Найдено {len(duplicates_map)} групп(ы) дубликатов:")
                    
                    for hash_value, dup_files in duplicates_map.items():
                        stats["total_duplicate_files"] += len(dup_files)
                        print(f"\n    Группа (hash: {hash_value[:12]}...):")
                        for dup_file in dup_files:
                            print(f"      - {dup_file.get('original_name')}")
                else:
                    print(f"  ✓ Дубликатов не найдено")
                
                print()
            
            duration = time.time() - start_time
            
            print(f"{'='*80}")
            print(f"ИТОГИ ПРОВЕРКИ ДУБЛИКАТОВ:")
            print(f"{'='*80}")
            print(f"Units проверено: {stats['units_checked']}")
            print(f"Units с дубликатами: {stats['units_with_duplicates']}")
            print(f"Всего групп дубликатов: {stats['total_duplicate_groups']}")
            print(f"Всего файлов-дубликатов: {stats['total_duplicate_files']}")
            print(f"Время: {duration:.2f} сек")
        
        except Exception as e:
            print(f"✗ Ошибка: {e}")
            import traceback
            traceback.print_exc()
    
    def handle_step4_check_mixed(self, limit: Optional[int] = None):
        """ШАГ 4: Определение mixed units."""
        print("\n=== ШАГ 4: Определение mixed units ===")
        
        if limit is None:
            limit_str = input(f"Лимит units (Enter = без ограничений): ").strip()
            limit = int(limit_str) if limit_str else None
        
        try:
            from .file_classifier import classify_unit_files
            import time
            
            unit_dirs = [d for d in INPUT_DIR.iterdir() if d.is_dir() and d.name.startswith("UNIT_")]
            total_units = len(unit_dirs)
            
            if limit:
                unit_dirs = unit_dirs[:limit]
            
            print(f"\nНайдено unit'ов: {total_units}")
            print(f"Обрабатывается: {len(unit_dirs)}")
            print(f"{'='*80}\n")
            
            start_time = time.time()
            
            stats = {
                "units_checked": 0,
                "mixed_units": 0,
                "homogeneous_units": 0
            }
            
            for idx, unit_dir in enumerate(unit_dirs, 1):
                unit_id = unit_dir.name
                files = [f for f in unit_dir.iterdir() if f.is_file() and not f.name.startswith('.')]
                
                if not files:
                    continue
                
                stats["units_checked"] += 1
                
                # Классифицируем unit
                unit_classification = classify_unit_files(files, unit_id)
                
                is_mixed = unit_classification["is_mixed"]
                unit_category = unit_classification["unit_category"]
                type_dist = unit_classification["type_distribution"]
                
                if is_mixed:
                    stats["mixed_units"] += 1
                    print(f"[{idx}/{len(unit_dirs)}] {unit_id}: 🔀 MIXED")
                    print(f"  Распределение по категориям:")
                    for cat, count in type_dist.items():
                        print(f"    {cat:15} - {count} файл(ов)")
                else:
                    stats["homogeneous_units"] += 1
                    print(f"[{idx}/{len(unit_dirs)}] {unit_id}: ✓ Однородный ({unit_category})")
                
                print()
            
            duration = time.time() - start_time
            
            print(f"{'='*80}")
            print(f"ИТОГИ ОПРЕДЕЛЕНИЯ MIXED UNITS:")
            print(f"{'='*80}")
            print(f"Units проверено: {stats['units_checked']}")
            print(f"Mixed units: {stats['mixed_units']}")
            print(f"Однородных units: {stats['homogeneous_units']}")
            print(f"Время: {duration:.2f} сек")
        
        except Exception as e:
            print(f"✗ Ошибка: {e}")
            import traceback
            traceback.print_exc()
    
    def handle_step5_distribute(self, limit: Optional[int] = None):
        """ШАГ 5: Распределение по pending директориям."""
        print("\n=== ШАГ 5: Распределение по pending директориям ===")
        
        if limit is None:
            limit_str = input(f"Лимит units (Enter = без ограничений): ").strip()
            limit = int(limit_str) if limit_str else None
        
        try:
            from .unit_distribution_new import distribute_unit_by_new_structure
            from .mixed_unit_handler import get_mixed_units_statistics
            from collections import defaultdict
            import time
            
            unit_dirs = [d for d in INPUT_DIR.iterdir() if d.is_dir() and d.name.startswith("UNIT_")]
            total_units = len(unit_dirs)
            
            if limit:
                unit_dirs = unit_dirs[:limit]
            
            print(f"\nНайдено unit'ов: {total_units}")
            print(f"Обрабатывается: {len(unit_dirs)}")
            print(f"{'='*80}\n")
            
            start_time = time.time()
            
            stats = {
                "units_processed": 0,
                "files_moved": 0,
                "by_category": defaultdict(int),
                "mixed_units": 0,
                "errors": 0
            }
            
            for idx, unit_dir in enumerate(unit_dirs, 1):
                unit_id = unit_dir.name
                files = [f for f in unit_dir.iterdir() if f.is_file() and not f.name.startswith('.')]
                
                if not files:
                    continue
                
                print(f"[{idx}/{len(unit_dirs)}] {unit_id} ({len(files)} файлов)...", end=" ", flush=True)
                
                try:
                    files_list = [{"path": str(f)} for f in files]
                    result = distribute_unit_by_new_structure(unit_id, files_list)
                    
                    stats["units_processed"] += 1
                    stats["files_moved"] += result["files_processed"]
                    
                    if result.get("is_mixed"):
                        stats["mixed_units"] += 1
                        print(f"🔀 MIXED → pending/mixed/")
                    else:
                        # Определяем основную категорию
                        main_cat = max(result["files_by_category"].items(), key=lambda x: x[1])[0] if result["files_by_category"] else "unknown"
                        stats["by_category"][main_cat] += 1
                        print(f"✓ → pending/{main_cat}/")
                    
                    # Показываем детали
                    if result.get("errors"):
                        print(f"     ⚠ Ошибок: {len(result['errors'])}")
                    if result.get("duplicates_detected"):
                        print(f"     ⚠ Дубликаты: {result['duplicate_count']} групп")
                    
                except Exception as e:
                    print(f"✗ Ошибка: {str(e)[:50]}")
                    stats["errors"] += 1
            
            duration = time.time() - start_time
            
            print(f"\n{'='*80}")
            print(f"ИТОГИ РАСПРЕДЕЛЕНИЯ:")
            print(f"{'='*80}")
            print(f"Units обработано: {stats['units_processed']}")
            print(f"Файлов перемещено: {stats['files_moved']}")
            print(f"Mixed units: {stats['mixed_units']}")
            print(f"Ошибок: {stats['errors']}")
            print(f"Время: {duration:.2f} сек")
            
            print(f"\nРаспределение по категориям:")
            for cat, count in sorted(stats["by_category"].items(), key=lambda x: -x[1]):
                print(f"  {cat:15} - {count:4} unit(ов)")
            
            # Финальная статистика mixed units
            mixed_stats = get_mixed_units_statistics(include_extraction=False)
            if mixed_stats["total_mixed"]["units"] > 0:
                print(f"\n🔀 Mixed units (детально):")
                print(f"  Units: {mixed_stats['total_mixed']['units']}")
                print(f"  Файлов: {mixed_stats['total_mixed']['files']}")
        
        except Exception as e:
            print(f"✗ Ошибка: {e}")
            import traceback
            traceback.print_exc()
    
    def handle_full_processing(self, limit: Optional[int] = None):
        """ПОЛНАЯ ОБРАБОТКА: Все шаги (3-7)."""
        print("\n=== ПОЛНАЯ ОБРАБОТКА: Все шаги (Сканирование → Распределение) ===")
        
        if limit is None:
            limit_str = input(f"Лимит units (Enter = без ограничений): ").strip()
            limit = int(limit_str) if limit_str else None
        
        print(f"\n{'='*80}")
        print("ЗАПУСК ПОЛНОЙ ОБРАБОТКИ")
        print(f"{'='*80}\n")
        
        # Запускаем все шаги последовательно (только распределение, остальные уже включены)
        self.handle_step5_distribute(limit=limit)
    
    def handle_units_report(self):
        """Отчет по обработанным units."""
        print("\n=== Отчет по обработанным units ===")
        
        try:
            from .config import PENDING_DIR
            import json
            
            categories = {
                "direct": PENDING_DIRECT_DIR,
                "normalize": PENDING_NORMALIZE_DIR,
                "convert": PENDING_CONVERT_DIR,
                "extract": PENDING_EXTRACT_DIR,
                "special": PENDING_SPECIAL_DIR,
                "mixed": PENDING_MIXED_DIR
            }
            
            total_units = 0
            total_files = 0
            
            for category, cat_dir in categories.items():
                if not cat_dir.exists():
                    continue
                
                units = [d for d in cat_dir.iterdir() if d.is_dir() and d.name.startswith("UNIT_")]
                
                if not units:
                    continue
                
                print(f"\n{'='*80}")
                print(f"Категория: {category.upper()}")
                print(f"{'='*80}")
                print(f"Units: {len(units)}\n")
                
                for unit_dir in units[:10]:  # Показываем первые 10
                    unit_id = unit_dir.name
                    files_dir = unit_dir / "files"
                    metadata_file = unit_dir / "metadata.json"
                    
                    files_count = 0
                    if files_dir.exists():
                        files = [f for f in files_dir.iterdir() if f.is_file()]
                        files_count = len(files)
                        total_files += files_count
                    
                    total_units += 1
                    
                    print(f"  {unit_id}: {files_count} файл(ов)")
                    
                    # Показываем метаданные если есть
                    if metadata_file.exists():
                        try:
                            with open(metadata_file, 'r') as f:
                                metadata = json.load(f)
                                dist_result = metadata.get("distribution_result", {})
                                if dist_result.get("duplicates_detected"):
                                    print(f"    ⚠ Дубликаты: {dist_result.get('duplicate_count', 0)} групп")
                                if dist_result.get("errors"):
                                    print(f"    ✗ Ошибок: {len(dist_result['errors'])}")
                        except:
                            pass
                
                if len(units) > 10:
                    print(f"  ... и еще {len(units) - 10} unit(ов)")
            
            print(f"\n{'='*80}")
            print(f"ИТОГО:")
            print(f"{'='*80}")
            print(f"Units обработано: {total_units}")
            print(f"Файлов всего: {total_files}")
        
        except Exception as e:
            print(f"✗ Ошибка: {e}")
            import traceback
            traceback.print_exc()
    
    def handle_new_structure_detection(self, limit: Optional[int] = None):
        """Определение типов файлов с использованием новой pending структуры."""
        print("\n=== Определение типов (НОВАЯ СИСТЕМА с pending/) ===")
        
        if limit is None:
            limit_str = input(f"Лимит обработки (Enter = без ограничений): ").strip()
            limit = int(limit_str) if limit_str else None
        
        try:
            from .unit_distribution_new import distribute_unit_by_new_structure, print_distribution_summary
            from .mixed_unit_handler import get_mixed_units_statistics
            from pathlib import Path
            import time
            
            # Получаем список unit'ов
            unit_dirs = [d for d in INPUT_DIR.iterdir() if d.is_dir() and d.name.startswith("UNIT_")]
            total_units = len(unit_dirs)
            
            if limit:
                unit_dirs = unit_dirs[:limit]
            
            print(f"\nНайдено unit'ов: {total_units}")
            print(f"Обрабатывается: {len(unit_dirs)}")
            print(f"{'='*80}\n")
            
            start_time = time.time()
            processed = 0
            errors = 0
            
            for idx, unit_dir in enumerate(unit_dirs, 1):
                unit_id = unit_dir.name
                files = [f for f in unit_dir.iterdir() if f.is_file() and not f.name.startswith('.')]
                
                if not files:
                    continue
                
                print(f"[{idx}/{len(unit_dirs)}] {unit_id} ({len(files)} файлов)...", end=" ", flush=True)
                
                try:
                    files_list = [{"path": str(f)} for f in files]
                    result = distribute_unit_by_new_structure(unit_id, files_list)
                    
                    if result.get("is_mixed"):
                        print(f"🔀 MIXED")
                    else:
                        print(f"✓")
                    
                    processed += 1
                except Exception as e:
                    print(f"✗ {str(e)[:30]}")
                    errors += 1
            
            duration = time.time() - start_time
            
            print(f"\n{'='*80}")
            print(f"Обработано: {processed}/{len(unit_dirs)}")
            print(f"Ошибок: {errors}")
            print(f"Время: {duration:.2f} сек")
            
            # После обработки показываем статистику mixed units
            mixed_stats = get_mixed_units_statistics(include_extraction=False)
            if mixed_stats["total_mixed"]["units"] > 0:
                print(f"\n🔀 Mixed units обнаружено: {mixed_stats['total_mixed']['units']}")
                print(f"  Файлов в mixed units: {mixed_stats['total_mixed']['files']}")
        
        except Exception as e:
            print(f"✗ Ошибка: {e}")
            import traceback
            traceback.print_exc()
    
    def run(self):
        """Главный цикл CLI."""
        while True:
            try:
                self.show_menu()
                choice = input("\nВыберите действие [0-19]: ").strip()
                
                if choice == "0":
                    print("Выход...")
                    break
                
                # === ЗАГРУЗКА И СИНХРОНИЗАЦИЯ ===
                elif choice == "1":
                    self.handle_download_protocols()
                elif choice == "2":
                    self.handle_sync_protocols()
                
                # === НОВАЯ СИСТЕМА (PENDING) - ПОШАГОВАЯ ОБРАБОТКА ===
                elif choice == "3":
                    self.handle_step1_scan_and_detect()
                elif choice == "4":
                    self.handle_step2_classify()
                elif choice == "5":
                    self.handle_step3_check_duplicates()
                elif choice == "6":
                    self.handle_step4_check_mixed()
                elif choice == "7":
                    self.handle_step5_distribute()
                elif choice == "8":
                    self.handle_full_processing()
                
                # === СТАТИСТИКА И ПРОСМОТР ===
                elif choice == "9":
                    self.handle_view_pending_structure()
                elif choice == "10":
                    self.handle_category_statistics()
                elif choice == "11":
                    self.handle_units_report()
                
                # === MERGE В READY_DOCLING ===
                elif choice == "12":
                    self.handle_merge_dry_run()
                elif choice == "13":
                    self.handle_merge_real()
                
                # === СЛУЖЕБНЫЕ ОПЕРАЦИИ ===
                elif choice == "14":
                    self.show_statistics()
                elif choice == "15":
                    self.show_metrics()
                elif choice == "16":
                    self.configure_limits()
                elif choice == "17":
                    self.handle_cleanup()
                elif choice == "18":
                    self.handle_check_sorted_units()
                elif choice == "19":
                    self.handle_analyze_detection_issues()
                
                else:
                    print("Неверный выбор. Попробуйте снова.")
                
                input("\nНажмите Enter для продолжения...")
            
            except KeyboardInterrupt:
                print("\n\nВыход...")
                break
            except Exception as e:
                print(f"\nОшибка: {e}")
                import traceback
                traceback.print_exc()
                input("\нНажмите Enter для продолжения...")


    def handle_convert_doc(self, limit: Optional[int] = None):
        """Обработка конвертации DOC → DOCX."""
        print("\n=== Конвертация DOC → DOCX ===")

        limit_str = input("Лимит units для конвертации (Enter = все): ").strip()
        limit = int(limit_str) if limit_str else None

        try:
            from services.router.doc_conversion import convert_doc_to_docx, validate_docx
            from services.router.file_detection import detect_file_type
            from services.router.config import DETECTED_DIR, CONVERTED_DIR
            from services.router.mongo import save_conversion_metric
            from pathlib import Path
            import time
            from collections import defaultdict

            # Рабочая директория с DOC файлами
            doc_dir = DETECTED_DIR / "doc"
            if not doc_dir.exists():
                print(f"✗ Директория с DOC файлами не найдена: {doc_dir}")
                return

            # Сканируем все units и собираем файлы для конвертации
            doc_files_to_convert = []
            stats = {
                "processed_units": 0,
                "total_files": 0,
                "successful": 0,
                "failed": 0,
                "skipped_fake": 0,
                "skipped_no_conv": 0,
                "errors": defaultdict(int)
            }

            print("Сбор файлов для конвертации...")

            unit_dirs = [d for d in doc_dir.iterdir() if d.is_dir() and d.name.startswith("UNIT_")]
            if limit:
                unit_dirs = unit_dirs[:limit]

            for unit_dir in unit_dirs:
                unit_id = unit_dir.name
                files_dir = unit_dir / "files"

                if not files_dir.exists():
                    continue

                # Находим все .doc файлы в unit'е
                doc_files = [f for f in files_dir.iterdir() if f.is_file() and f.suffix.lower() == ".doc"]

                for doc_file in doc_files:
                    # Определяем тип файла
                    file_info = detect_file_type(doc_file)
                    detected_type = file_info.get("detected_type", "unknown")
                    is_fake_doc = file_info.get("is_fake_doc", False)
                    requires_conversion = file_info.get("requires_conversion", False)

                    # Пропускаем фейковые DOC
                    if is_fake_doc:
                        stats["skipped_fake"] += 1
                        continue

                    # Пропускаем файлы, которые не требуют конвертации
                    if not requires_conversion or detected_type != "doc":
                        stats["skipped_no_conv"] += 1
                        continue

                    doc_files_to_convert.append((doc_file, unit_id))
                    stats["total_files"] += 1

            if not doc_files_to_convert:
                print("✓ Нет подходящих файлов для конвертации")
                return

            print(f"\nНайдено units: {len(unit_dirs)}")
            print(f"Файлов для конвертации: {len(doc_files_to_convert)}")
            print(f"Пропущено фейковых: {stats['skipped_fake']}")
            print(f"Пропущено неподходящих: {stats['skipped_no_conv']}")
            print(f"{'='*80}\n")

            # Запрашиваем количество потоков
            workers_str = input("Количество потоков для конвертации (1 = последовательно, 2+ = параллельно, Enter = 1): ").strip()
            max_workers = int(workers_str) if workers_str else 1

            if max_workers < 1:
                max_workers = 1

            start_time = time.time()
            from services.router.doc_conversion import (
                convert_doc_files_sequential,
                convert_doc_files_parallel,
                _cleanup_empty_directories
            )
            from services.router.config import CONVERTED_DIR, DETECTED_DIR

            # Выбираем режим обработки
            if max_workers == 1:
                print(f"Режим: последовательная обработка (1 поток)")
                conversion_results = convert_doc_files_sequential(doc_files_to_convert)
            else:
                print(f"Режим: параллельная обработка ({max_workers} потоков)")
                # Ограничиваем максимальное количество процессов
                max_workers = min(max_workers, len(doc_files_to_convert), 5)
                conversion_results = convert_doc_files_parallel(doc_files_to_convert, max_workers=max_workers)

            # Обрабатываем результаты
            for result in conversion_results["results"]:
                if result["success"]:
                    stats["successful"] += 1
                    # Сохраняем метрику
                    try:
                        save_conversion_metric({
                            "unit_id": result["unit_id"],
                            "original_file": Path(result["doc_path"]).name,
                            "success": True,
                            "conversion_time": result["details"].get("conversion_time", 0),
                            "total_time": result["details"].get("conversion_time", 0)
                        })
                    except:
                        pass
                else:
                    stats["failed"] += 1
                    error_msg = result["details"].get("error", "unknown error")
                    stats["errors"][error_msg] += 1

            # Очистка пустых директорий
            print("\nОчистка пустых директорий...")
            removed_converted = _cleanup_empty_directories(CONVERTED_DIR, "docx")
            removed_detected = _cleanup_empty_directories(DETECTED_DIR, "doc")
            if removed_converted > 0:
                print(f"  ✓ Удалено пустых директорий в converted/docx: {removed_converted}")
            if removed_detected > 0:
                print(f"  ✓ Удалено пустых директорий в detected/doc: {removed_detected}")

            duration = time.time() - start_time

            # Итоговая статистика
            print(f"\n{'='*80}")
            print("ОТЧЕТ О КОНВЕРТАЦИИ DOC → DOCX")
            print(f"{'='*80}")
            print(f"Обработано файлов: {stats['total_files']}")
            print(f"Успешно конвертировано: {stats['successful']}")
            print(f"Ошибок: {stats['failed']}")
            print(f"Пропущено фейковых: {stats['skipped_fake']}")
            print(f"Пропущено не требующих: {stats['skipped_no_conv']}")
            print(f"Время выполнения: {conversion_results['total_time']:.2f} сек")
            if max_workers == 1:
                print(f"Режим: последовательная обработка")
            else:
                print(f"Параллельных процессов: {max_workers}")

            if stats["successful"] > 0:
                avg_time = conversion_results['total_time'] / stats["successful"]
                print(f"Среднее время на файл: {avg_time:.2f} сек")

            if stats["errors"]:
                print(f"\nОшибки по типам:")
                for error_type, count in sorted(stats["errors"].items(), key=lambda x: x[1], reverse=True):
                    print(f"  {error_type}: {count}")

            print(f"{'='*80}\n")

            if stats["successful"] > 0:
                print("✓ Конвертация завершена успешно")
            else:
                print("⚠ Конвертация завершена с ошибками")

        except ImportError as e:
            print(f"\n✗ Ошибка импорта: {e}")
        except Exception as e:
            print(f"\n✗ Ошибка конвертации: {e}")
            import traceback
            traceback.print_exc()


def main():
    """Точка входа для CLI."""
    cli = PreprocessingCLI()
    cli.run()


if __name__ == "__main__":
    main()


```

Проверю linter:

Отлично! Теперь протестируем:

Отлично! Меню работает! Вижу опечатку в последней строке (`\н` вместо `\n`). Исправлю:

```python
"""
CLI для интерактивного управления процессом preprocessing.
"""
import sys
import json
from pathlib import Path
from typing import Optional, Dict, Any

from .config import (
    INPUT_DIR, TEMP_DIR,
    PENDING_DIR, PENDING_NORMALIZE_DIR, PENDING_CONVERT_DIR, PENDING_EXTRACT_DIR,
    PENDING_DIRECT_DIR, PENDING_SPECIAL_DIR, PENDING_MIXED_DIR,
    READY_DOCLING_DIR,
    get_limits, update_limit, LIMIT_DETECT_TYPE, LIMIT_EXTRACT_ARCHIVE,
    LIMIT_CONVERT_DOC, LIMIT_NORMALIZE, LIMIT_CREATE_MANIFEST,
    MONGO_METADATA_DB, MONGO_METADATA_COLLECTION, MONGO_METRICS_COLLECTION
)
from .state_manager import StateManager

# Заглушки для старых директорий (для совместимости со старыми функциями)
DETECTED_DIR = PENDING_DIR / "_legacy_detected"
EXTRACTED_DIR = PENDING_DIR / "_legacy_extracted"
CONVERTED_DIR = PENDING_DIR / "_legacy_converted"
NORMALIZED_DIR = PENDING_DIR / "_legacy_normalized"
READY_DIR = PENDING_DIR / "_legacy_ready"
MIXED_DIR = PENDING_DIR / "_legacy_mixed"
ARCHIVE_DIR = PENDING_DIR / "_legacy_archive"

from .metrics import get_processing_summary
from .protocol_sync import (
    get_remote_mongo_client, get_local_mongo_client, sync_protocols_for_date
)
from ..downloader import ProtocolDownloader, check_zakupki_health
from ..downloader.manager import get_metadata_client, MONGO_METADATA_PROTOCOLS_COLLECTION
from .mongo import get_mongo_metadata_client
from datetime import datetime, timedelta
import time
import shutil
from pymongo.errors import PyMongoError


class PreprocessingCLI:
    """Интерактивный CLI для управления preprocessing."""
    
    def __init__(self):
        self.state_manager = StateManager()
        self.limits = get_limits()
    
    def show_menu(self):
        """Показывает главное меню."""
        print("\n" + "=" * 50)
        print("=== Winners223 Preprocessing CLI ===")
        print("=" * 50)
        
        print("\n=== ЗАГРУЗКА И СИНХРОНИЗАЦИЯ ===")
        print("1. Скачать протоколы из MongoDB (с VPN)")
        print("2. Синхронизация протоколов из удалённой MongoDB")
        
        # print("\n=== ОБРАБОТКА (СТАРАЯ СИСТЕМА) ===")
        # print("3. Определить тип файла(ов)")
        # print("4. Распаковать архив(ы)")
        # print("5. Конвертировать DOC → DOCX")
        # print("6. Нормализовать файл(ы)")
        # print("7. Создать manifest")
        # print("8. Сортировка PDF на text_pdf и scan_pdf")
        # print("9. Конвертация DOC → HTML/XML")
        # print("10. Автоматическая обработка (полный пайплайн)")
        
        print("\n=== НОВАЯ СИСТЕМА (PENDING) - ПОШАГОВАЯ ОБРАБОТКА ===")
        print("3. ШАГ 1: Сканирование и детекция типов файлов")
        print("4. ШАГ 2: Классификация файлов по категориям")
        print("5. ШАГ 3: Проверка дубликатов")
        print("6. ШАГ 4: Определение mixed units")
        print("7. ШАГ 5: Распределение по pending директориям")
        print("8. ПОЛНАЯ ОБРАБОТКА: Все шаги (3-7)")
        
        print("\n=== СТАТИСТИКА И ПРОСМОТР ===")
        print("9. Просмотр pending структуры")
        print("10. Детальная статистика по категориям (+ mixed units)")
        print("11. Отчет по обработанным units")
        
        print("\n=== MERGE В READY_DOCLING ===")
        print("12. Merge (DRY RUN)")
        print("13. Merge (РЕАЛЬНЫЙ)")
        
        print("\n=== СЛУЖЕБНЫЕ ОПЕРАЦИИ ===")
        print("14. Просмотр статистики")
        print("15. Просмотр метрик")
        print("16. Настройки лимитов")
        print("17. Очистка директорий")
        print("18. Проверка отсортированных units")
        print("19. Анализ проблем определения типов")
        
        print("\n0. Выход")
        print("\n" + "-" * 50)
    
    def handle_sync_protocols(self):
        """Обработка синхронизации протоколов из удалённой MongoDB."""
        print("\n=== Синхронизация протоколов из удалённой MongoDB ===")
        
        # Проверка подключения к удалённой MongoDB
        print("\n1. Проверка подключения к удалённой MongoDB...")
        remote_client = get_remote_mongo_client()
        if not remote_client:
            print("✗ Не удалось подключиться к удалённой MongoDB")
            print("  Проверьте настройки в .env:")
            print("    - mongoServer или MONGO_SERVER")
            print("    - readAllUser или MONGO_USER")
            print("    - readAllPassword или MONGO_PASSWORD")
            print("    - sslCertPath или MONGO_SSL_CERT")
            return
        
        remote_client.close()
        print("✓ Подключение к удалённой MongoDB успешно")
        
        # Проверка подключения к локальной MongoDB
        print("\n2. Проверка подключения к локальной MongoDB...")
        local_client = get_local_mongo_client()
        if not local_client:
            print("✗ Не удалось подключиться к локальной MongoDB")
            print("  Проверьте настройки:")
            print("    - LOCAL_MONGO_SERVER (по умолчанию: localhost:27017)")
            print("    - MONGO_METADATA_USER")
            print("    - MONGO_METADATA_PASSWORD")
            return
        
        local_client.close()
        print("✓ Подключение к локальной MongoDB успешно")
        
        # Выбор даты
        print("\n3. Выбор даты для синхронизации:")
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
        
        # Лимит
        limit_str = input(f"\n4. Лимит протоколов для синхронизации (по умолчанию: 200): ").strip()
        limit = int(limit_str) if limit_str else 200
        
        # Запуск синхронизации
        print(f"\n5. Запуск синхронизации...")
        print(f"   Дата: {target_date.date()}")
        print(f"   Лимит: {limit}")
        
        result = sync_protocols_for_date(target_date, limit)
        
        if result.get("status") == "success":
            print("\n✓ Синхронизация завершена успешно!")
            print(f"   Просмотрено: {result.get('scanned', 0)}")
            print(f"   Вставлено: {result.get('inserted', 0)}")
            print(f"   Пропущено: {result.get('skipped_existing', 0)}")
            if result.get("errors_count", 0) > 0:
                print(f"   Ошибок: {result.get('errors_count', 0)}")
        else:
            print(f"\n✗ Ошибка синхронизации: {result.get('message', 'Unknown error')}")
    
    def handle_download_protocols(self):
        """Обработка скачивания протоколов из MongoDB через VPN."""
        print("\n=== Скачивание протоколов из MongoDB (с VPN) ===")
        
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
            downloader = ProtocolDownloader(output_dir=INPUT_DIR)
            start_time = time.time()
            result = downloader.process_pending_protocols(limit=limit)
            duration = time.time() - start_time
            
            if result.get("health_ok"):
                print("\n" + "=" * 80)
                print("✓ СКАЧИВАНИЕ ЗАВЕРШЕНО")
                print("=" * 80)
                print(f"  Успешно обработано: {result.get('processed_ok', 0)} протоколов")
                print(f"  Ошибок: {result.get('processed_error', 0)} протоколов")
                print(f"  Скачано файлов: {result.get('downloaded_files_count', 0)}")
                print(f"  Ошибок скачивания файлов: {result.get('failed_files_count', 0)}")
                print(f"  Время выполнения: {duration:.2f} сек")
                if result.get('processed_ok', 0) > 0:
                    avg_time = duration / result.get('processed_ok', 1)
                    print(f"  Среднее время на протокол: {avg_time:.2f} сек")
            else:
                print("\n✗ Скачивание не выполнено из-за проблем с VPN")
                
        except Exception as e:
            print(f"\n✗ Ошибка при скачивании протоколов: {e}")
            import traceback
            traceback.print_exc()
    
    def handle_detect_type(self, limit: Optional[int] = None):
        """Обработка определения типа файла на уровне unit'ов (протоколов)."""
        print("\n=== Определение типа файла (на уровне unit'ов) ===")
        if limit is None:
            limit_str = input(f"Лимит обработки (0 = все, текущий: {LIMIT_DETECT_TYPE}): ").strip()
            limit = int(limit_str) if limit_str else LIMIT_DETECT_TYPE
        
        print(f"\nОбработка файлов из input/ с лимитом {limit if limit > 0 else 'без ограничений'}...")
        print("Файлы одного протокола/юнита обрабатываются вместе и не разделяются.")
        
        try:
            # Импортируем необходимые модули
            from services.router.unit_distribution import distribute_unit_by_types
            from services.router.mongo import save_file_detection_metadata, save_unit_distribution_metadata
            from services.router.config import INPUT_DIR, ensure_directories
            from pathlib import Path
            import time
            from collections import defaultdict
            
            ensure_directories()
            
            # Получаем список unit'ов
            unit_dirs = [d for d in INPUT_DIR.iterdir() if d.is_dir() and d.name.startswith("UNIT_")]
            total_units = len(unit_dirs)
            
            if limit > 0:
                unit_dirs = unit_dirs[:limit]
            
            print(f"\nНайдено unit'ов: {total_units}")
            print(f"Обрабатывается: {len(unit_dirs)}")
            print(f"{'='*80}\n")
            
            # Статистика
            stats = {
                "processed_units": 0,
                "processed_files": 0,
                "mixed_units": 0,
                "duplicates_found": 0,
                "extension_mismatches": 0,
                "errors": 0,
                "file_types": defaultdict(int),
                "target_dirs": defaultdict(int),
                "unprocessed_units": [],  # Units которые не были обработаны с причинами
                "extension_mismatch_details": []  # Детали несоответствий расширений
            }
            
            start_time = time.time()
            
            for idx, unit_dir in enumerate(unit_dirs, 1):
                unit_id = unit_dir.name
                files = [f for f in unit_dir.iterdir() if f.is_file() and not f.name.startswith('.')]
                
                if not files:
                    # Отслеживаем units без файлов
                    stats["unprocessed_units"].append({
                        "unit_id": unit_id,
                        "reason": "no_files",
                        "message": "Unit не содержит файлов"
                    })
                    continue
                
                print(f"[{idx}/{len(unit_dirs)}] {unit_id} ({len(files)} файл(ов))...", end=" ", flush=True)
                
                try:
                    # Подготавливаем список файлов
                    files_list = [{"path": str(f)} for f in files]
                    
                    # Распределяем unit
                    distribution_result = distribute_unit_by_types(
                        unit_id=unit_id,
                        files=files_list,
                        unit_metadata=None
                    )
                    
                    # Сохраняем метаданные
                    for file_info in distribution_result["files"]:
                        try:
                            save_file_detection_metadata(
                                file_path=file_info["path"],
                                file_info=file_info,
                                unit_id=unit_id,
                                protocol_info=None
                            )
                        except Exception:
                            pass  # Игнорируем ошибки MongoDB
                    
                    try:
                        save_unit_distribution_metadata(unit_id, distribution_result)
                    except Exception:
                        pass
                    
                    # Обновляем статистику
                    stats["processed_units"] += 1
                    stats["processed_files"] += len(distribution_result["files"])
                    
                    if distribution_result["is_mixed"]:
                        stats["mixed_units"] += 1
                    
                    if distribution_result["duplicates_detected"]:
                        stats["duplicates_found"] += 1
                    
                    extension_mismatches = len(distribution_result["distribution_details"].get("extension_mismatches", []))
                    stats["extension_mismatches"] += extension_mismatches
                    
                    # Сохраняем детали несоответствий расширений
                    for file_info in distribution_result["files"]:
                        if not file_info.get("extension_matches_content", True):
                            mismatch_detail = {
                                "unit_id": unit_id,
                                "file_name": file_info.get("original_name", "unknown"),
                                "extension": file_info.get("extension", "unknown"),
                                "expected_type": file_info.get("extension", "").replace(".", ""),
                                "detected_type": file_info.get("detected_type", "unknown"),
                                "mime_type": file_info.get("mime_type", "unknown")
                            }
                            stats["extension_mismatch_details"].append(mismatch_detail)
                    
                    for file_type in distribution_result["file_types"]:
                        stats["file_types"][file_type] += 1
                    
                    # Определяем целевую директорию для статистики
                    target_dir = Path(distribution_result["target_dir"])
                    if "mixed" in str(target_dir):
                        stats["target_dirs"]["mixed"] += 1
                    else:
                        parent_name = target_dir.parent.name if target_dir.parent.name != "detected" else target_dir.name
                        stats["target_dirs"][parent_name] += 1
                    
                    # Выводим результат
                    status_icon = "🔀" if distribution_result["is_mixed"] else "✓"
                    print(f"{status_icon} {', '.join(distribution_result['file_types'])}")
                
                except Exception as e:
                    stats["errors"] += 1
                    error_msg = str(e)
                    print(f"✗ Ошибка: {error_msg[:50]}")
                    # Отслеживаем units с ошибками
                    stats["unprocessed_units"].append({
                        "unit_id": unit_id,
                        "reason": "error",
                        "message": error_msg,
                        "error_type": type(e).__name__
                    })
            
            duration = time.time() - start_time
            
            # Выводим итоговую статистику
            print(f"\n{'='*80}")
            print("РЕЗУЛЬТАТЫ ОБРАБОТКИ")
            print(f"{'='*80}")
            print(f"Обработано unit'ов: {stats['processed_units']}/{len(unit_dirs)}")
            print(f"Обработано файлов: {stats['processed_files']}")
            print(f"Время выполнения: {duration:.2f} сек")
            if stats['processed_units'] > 0:
                print(f"Среднее время на unit: {duration/stats['processed_units']:.2f} сек")
            
            print(f"\nРаспределение по типам:")
            for file_type, count in sorted(stats['file_types'].items()):
                print(f"  {file_type}: {count}")
            
            print(f"\nРаспределение по директориям:")
            for target_dir, count in sorted(stats['target_dirs'].items()):
                print(f"  {target_dir}: {count} unit'ов")
            
            print(f"\nОсобые случаи:")
            print(f"  Mixed units: {stats['mixed_units']}")
            print(f"  Дубликаты: {stats['duplicates_found']} unit'ов")
            print(f"  Несоответствий расширений: {stats['extension_mismatches']}")
            print(f"  Ошибок: {stats['errors']}")
            
            # Выводим информацию о необработанных units
            unprocessed_count = len(stats.get("unprocessed_units", []))
            if unprocessed_count > 0:
                print(f"\nНеобработанные units: {unprocessed_count}")
                # Группируем по причинам
                by_reason = defaultdict(list)
                for unit in stats["unprocessed_units"]:
                    by_reason[unit["reason"]].append(unit)
                
                for reason, units in sorted(by_reason.items()):
                    reason_name = {
                        "no_files": "Без файлов",
                        "error": "Ошибка обработки"
                    }.get(reason, reason)
                    print(f"  {reason_name}: {len(units)} unit'ов")
                    if len(units) <= 10:
                        for unit_info in units:
                            uid = unit_info["unit_id"]
                            diagnosis = unit_info.get("diagnosis", {})
                            if diagnosis:
                                reasons = diagnosis.get("possible_reasons", [])
                                if reasons:
                                    print(f"    - {uid}: {reasons[0]}")
                                else:
                                    print(f"    - {uid}")
                            else:
                                print(f"    - {uid}")
                    else:
                        for unit_info in units[:5]:
                            uid = unit_info["unit_id"]
                            diagnosis = unit_info.get("diagnosis", {})
                            if diagnosis:
                                reasons = diagnosis.get("possible_reasons", [])
                                if reasons:
                                    print(f"    - {uid}: {reasons[0]}")
                                else:
                                    print(f"    - {uid}")
                            else:
                                print(f"    - {uid}")
                        print(f"    ... и еще {len(units) - 5} unit'ов")
            
            # Выводим детали несоответствий расширений
            if stats.get("extension_mismatch_details"):
                print(f"\nДетали несоответствий расширений:")
                # Группируем по типам несоответствий
                mismatch_groups = defaultdict(int)
                for detail in stats["extension_mismatch_details"]:
                    key = f"{detail['extension']} → {detail['detected_type']}"
                    mismatch_groups[key] += 1
                
                for mismatch_type, count in sorted(mismatch_groups.items(), key=lambda x: x[1], reverse=True):
                    print(f"  {mismatch_type}: {count}")
            
            print(f"{'='*80}\n")
        
        except ImportError as e:
            print(f"\n✗ Ошибка импорта модулей: {e}")
            print("Убедитесь, что все зависимости установлены.")
        except Exception as e:
            print(f"\n✗ Ошибка обработки: {e}")
            import traceback
            traceback.print_exc()
    
    def handle_extract_archive(self, limit: Optional[int] = None):
        """Обработка распаковки архивов."""
        print("\n=== Распаковка архивов ===")
        if limit is None:
            limit_str = input(f"Лимит обработки (0 = все, текущий: {LIMIT_EXTRACT_ARCHIVE}): ").strip()
            limit = int(limit_str) if limit_str else LIMIT_EXTRACT_ARCHIVE
        
        print(f"Обработка архивов с лимитом {limit if limit > 0 else 'без ограничений'}...")
        print("Используйте API endpoint: POST /trigger/extract_archive")
    
    
    def handle_normalize(self, limit: Optional[int] = None):
        """Обработка нормализации файлов."""
        print("\n=== Нормализация файлов ===")
        if limit is None:
            limit_str = input(f"Лимит обработки (0 = все, текущий: {LIMIT_NORMALIZE}): ").strip()
            limit = int(limit_str) if limit_str else LIMIT_NORMALIZE
        
        print(f"Нормализация файлов с лимитом {limit if limit > 0 else 'без ограничений'}...")
        print("Используйте API endpoint: POST /trigger/normalize")
    
    def handle_create_manifest(self, limit: Optional[int] = None):
        """Обработка создания manifest."""
        print("\n=== Создание manifest ===")
        if limit is None:
            limit_str = input(f"Лимит обработки (0 = все, текущий: {LIMIT_CREATE_MANIFEST}): ").strip()
            limit = int(limit_str) if limit_str else LIMIT_CREATE_MANIFEST
        
        print(f"Создание manifest с лимитом {limit if limit > 0 else 'без ограничений'}...")
        print("Используйте API endpoint: POST /trigger/create_manifest")
    
    def show_statistics(self):
        """Показывает статистику по этапам."""
        print("\n=== Статистика по этапам ===")
        stats = self.state_manager.get_statistics()
        
        print(f"\nЭтап 1 (uploaded):     {len(list(INPUT_DIR.iterdir()))} файлов в input/")
        print(f"Этап 2 (detected):     {stats['detected']['count']} файлов")
        print(f"  По типам: {stats['detected']['by_type']}")
        print(f"Этап 3 (extracted):    {stats['extracted']['count']} файлов (из {stats['extracted']['archives_processed']} архивов)")
        print(f"Этап 4 (converted):    {stats['converted']['count']} файлов")
        print(f"Этап 5 (normalized):   {stats['normalized']['count']} unit'ов")
        print(f"Этап 6 (ready):        {stats['ready']['count']} unit'ов готовы для Docling")
        
        print("\nТекущие лимиты:")
        limits = get_limits()
        for stage, limit in limits.items():
            print(f"  {stage}: {limit if limit > 0 else 'без ограничений'}")
    
    def show_metrics(self, stage: Optional[str] = None):
        """Показывает метрики обработки."""
        print("\n=== Метрики обработки ===")
        metrics = get_processing_summary()
        
        if not metrics:
            print("Метрики не найдены")
            return
        
        summary = metrics.get("summary", {})
        print(f"\nСессия: {metrics.get('session_id', 'N/A')}")
        print(f"Начало: {metrics.get('started_at', 'N/A')}")
        print(f"Завершение: {metrics.get('completed_at', 'N/A')}")
        print(f"\nСтатистика:")
        print(f"  Всего файлов: {summary.get('total_input_files', 0)}")
        print(f"  Всего архивов: {summary.get('total_archives', 0)}")
        print(f"  Всего unit'ов: {summary.get('total_units', 0)}")
        print(f"  Ошибок: {summary.get('total_errors', 0)}")
    
    def show_logs(self, filter_by: Optional[str] = None):
        """Показывает логи."""
        print("\n=== Логи ===")
        print("Логи доступны через API endpoint: GET /metrics/processing")
        print("Или проверьте логи сервиса router")
    
    def configure_limits(self):
        """Настройка лимитов обработки."""
        print("\n=== Настройки лимитов обработки ===")
        limits = get_limits()
        
        print("\nТекущие лимиты:")
        print("1. Определение типа:     ", limits.get("detect_type", 0), "(0 = без ограничений)")
        print("2. Распаковка архивов:   ", limits.get("extract_archive", 0), "(0 = без ограничений)")
        print("3. Конвертация DOC:      ", limits.get("convert_doc", 0), "(0 = без ограничений)")
        print("4. Нормализация:         ", limits.get("normalize", 0), "(0 = без ограничений)")
        print("5. Создание manifest:    ", limits.get("create_manifest", 0), "(0 = без ограничений)")
        
        choice = input("\nИзменить лимит [1-5] или 0 для возврата: ").strip()
        
        if choice == "0":
            return
        
        stage_map = {
            "1": "detect_type",
            "2": "extract_archive",
            "3": "convert_doc",
            "4": "normalize",
            "5": "create_manifest"
        }
        
        if choice in stage_map:
            stage = stage_map[choice]
            new_limit = input(f"Введите новое значение (0 = без ограничений): ").strip()
            try:
                limit_value = int(new_limit)
                if update_limit(stage, limit_value):
                    print(f"Лимит для {stage} обновлен: {limit_value}")
                else:
                    print("Ошибка обновления лимита")
            except ValueError:
                print("Неверное значение")
        else:
            print("Неверный выбор")
    
    def run_full_pipeline(self, limits: Optional[Dict[str, int]] = None):
        """Запуск полного пайплайна."""
        print("\n=== Автоматическая обработка ===")
        print("Запуск полного пайплайна для всех файлов из input/")
        print("Используйте API endpoint: POST /process_now")
        print("Или запустите через API клиент")
    
    def run(self):
        """Главный цикл CLI."""
        while True:
            try:
                self.show_menu()
                choice = input("\nВыберите действие [0-18]: ").strip()
                
                if choice == "0":
                    print("Выход...")
                    break
                elif choice == "1":
                    self.handle_download_protocols()
                elif choice == "2":
                    self.handle_detect_type()
                elif choice == "3":
                    self.handle_extract_archive()
                elif choice == "4":
                    self.handle_convert_doc()
                elif choice == "5":
                    self.handle_normalize()
                elif choice == "6":
                    self.handle_create_manifest()
                elif choice == "7":
                    self.show_statistics()
                elif choice == "8":
                    self.show_metrics()
                elif choice == "9":
                    self.show_logs()
                elif choice == "10":
                    self.configure_limits()
                elif choice == "11":
                    self.run_full_pipeline()
                else:
                    print("Неверный выбор. Попробуйте снова.")
                
                input("\nНажмите Enter для продолжения...")
            
            except KeyboardInterrupt:
                print("\n\nВыход...")
                break
            except Exception as e:
                print(f"\nОшибка: {e}")
                import traceback
                traceback.print_exc()
                input("\nНажмите Enter для продолжения...")


    def handle_sync_protocols(self):
        """Обработка синхронизации протоколов из удалённой MongoDB."""
        print("\n=== Синхронизация протоколов из удалённой MongoDB ===")
        
        # Проверка подключения к удалённой MongoDB
        print("\n1. Проверка подключения к удалённой MongoDB...")
        remote_client = get_remote_mongo_client()
        if not remote_client:
            print("✗ Не удалось подключиться к удалённой MongoDB")
            print("  Проверьте настройки в .env:")
            print("    - mongoServer или MONGO_SERVER")
            print("    - readAllUser или MONGO_USER")
            print("    - readAllPassword или MONGO_PASSWORD")
            print("    - sslCertPath или MONGO_SSL_CERT")
            return
        
        remote_client.close()
        print("✓ Подключение к удалённой MongoDB успешно")
        
        # Проверка подключения к локальной MongoDB
        print("\n2. Проверка подключения к локальной MongoDB...")
        local_client = get_local_mongo_client()
        if not local_client:
            print("✗ Не удалось подключиться к локальной MongoDB")
            print("  Проверьте настройки:")
            print("    - LOCAL_MONGO_SERVER (по умолчанию: localhost:27017)")
            print("    - MONGO_METADATA_USER")
            print("    - MONGO_METADATA_PASSWORD")
            return
        
        local_client.close()
        print("✓ Подключение к локальной MongoDB успешно")
        
        # Выбор даты
        print("\n3. Выбор даты для синхронизации:")
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
        
        # Лимит
        limit_str = input(f"\n4. Лимит протоколов для синхронизации (по умолчанию: 200): ").strip()
        limit = int(limit_str) if limit_str else 200
        
        # Запуск синхронизации
        print(f"\n5. Запуск синхронизации...")
        print(f"   Дата: {target_date.date()}")
        print(f"   Лимит: {limit}")
        
        result = sync_protocols_for_date(target_date, limit)
        
        if result.get("status") == "success":
            print("\n✓ Синхронизация завершена успешно!")
            print(f"   Просмотрено: {result.get('scanned', 0)}")
            print(f"   Вставлено: {result.get('inserted', 0)}")
            print(f"   Пропущено: {result.get('skipped_existing', 0)}")
            if result.get("errors_count", 0) > 0:
                print(f"   Ошибок: {result.get('errors_count', 0)}")
        else:
            print(f"\n✗ Ошибка синхронизации: {result.get('message', 'Unknown error')}")
    
    
    def handle_download_protocols(self):
        """Обработка скачивания протоколов из MongoDB через VPN."""
        print("\n=== Скачивание протоколов из MongoDB (с VPN) ===")
        
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
            downloader = ProtocolDownloader(output_dir=INPUT_DIR)
            start_time = time.time()
            result = downloader.process_pending_protocols(limit=limit)
            duration = time.time() - start_time
            
            if result.get("health_ok"):
                print("\n" + "=" * 80)
                print("✓ СКАЧИВАНИЕ ЗАВЕРШЕНО")
                print("=" * 80)
                print(f"  Успешно обработано: {result.get('processed_ok', 0)} протоколов")
                print(f"  Ошибок: {result.get('processed_error', 0)} протоколов")
                print(f"  Скачано файлов: {result.get('downloaded_files_count', 0)}")
                print(f"  Ошибок скачивания файлов: {result.get('failed_files_count', 0)}")
                print(f"  Время выполнения: {duration:.2f} сек")
                if result.get('processed_ok', 0) > 0:
                    avg_time = duration / result.get('processed_ok', 1)
                    print(f"  Среднее время на протокол: {avg_time:.2f} сек")
            else:
                print("\n✗ Скачивание не выполнено из-за проблем с VPN")
                
        except Exception as e:
            print(f"\n✗ Ошибка при скачивании протоколов: {e}")
            import traceback
            traceback.print_exc()
    
    def handle_detect_type(self, limit: Optional[int] = None):
        """Обработка определения типа файла на уровне unit'ов (протоколов)."""
        print("\n=== Определение типа файла (на уровне unit'ов) ===")
        if limit is None:
            limit_str = input(f"Лимит обработки (0 = все, текущий: {LIMIT_DETECT_TYPE}): ").strip()
            limit = int(limit_str) if limit_str else LIMIT_DETECT_TYPE
        
        print(f"\nОбработка файлов из input/ с лимитом {limit if limit > 0 else 'без ограничений'}...")
        print("Файлы одного протокола/юнита обрабатываются вместе и не разделяются.")
        
        try:
            # Импортируем необходимые модули
            from services.router.unit_distribution import distribute_unit_by_types
            from services.router.mongo import save_file_detection_metadata, save_unit_distribution_metadata
            from services.router.config import INPUT_DIR, ensure_directories
            from pathlib import Path
            import time
            from collections import defaultdict
            
            ensure_directories()
            
            # Получаем список unit'ов
            unit_dirs = [d for d in INPUT_DIR.iterdir() if d.is_dir() and d.name.startswith("UNIT_")]
            total_units = len(unit_dirs)
            
            if limit > 0:
                unit_dirs = unit_dirs[:limit]
            
            print(f"\nНайдено unit'ов: {total_units}")
            print(f"Обрабатывается: {len(unit_dirs)}")
            print(f"{'='*80}\n")
            
            # Статистика
            stats = {
                "processed_units": 0,
                "processed_files": 0,
                "mixed_units": 0,
                "duplicates_found": 0,
                "extension_mismatches": 0,
                "errors": 0,
                "file_types": defaultdict(int),
                "target_dirs": defaultdict(int),
                "unprocessed_units": [],  # Units которые не были обработаны с причинами
                "extension_mismatch_details": []  # Детали несоответствий расширений
            }
            
            start_time = time.time()
            
            for idx, unit_dir in enumerate(unit_dirs, 1):
                unit_id = unit_dir.name
                files = [f for f in unit_dir.iterdir() if f.is_file() and not f.name.startswith('.')]
                
                if not files:
                    # Отслеживаем units без файлов
                    stats["unprocessed_units"].append({
                        "unit_id": unit_id,
                        "reason": "no_files",
                        "message": "Unit не содержит файлов"
                    })
                    continue
                
                print(f"[{idx}/{len(unit_dirs)}] {unit_id} ({len(files)} файл(ов))...", end=" ", flush=True)
                
                try:
                    # Подготавливаем список файлов
                    files_list = [{"path": str(f)} for f in files]
                    
                    # Распределяем unit
                    distribution_result = distribute_unit_by_types(
                        unit_id=unit_id,
                        files=files_list,
                        unit_metadata=None
                    )
                    
                    # Сохраняем метаданные
                    for file_info in distribution_result["files"]:
                        try:
                            save_file_detection_metadata(
                                file_path=file_info["path"],
                                file_info=file_info,
                                unit_id=unit_id,
                                protocol_info=None
                            )
                        except Exception:
                            pass  # Игнорируем ошибки MongoDB
                    
                    try:
                        save_unit_distribution_metadata(unit_id, distribution_result)
                    except Exception:
                        pass
                    
                    # Обновляем статистику
                    stats["processed_units"] += 1
                    stats["processed_files"] += len(distribution_result["files"])
                    
                    if distribution_result["is_mixed"]:
                        stats["mixed_units"] += 1
                    
                    if distribution_result["duplicates_detected"]:
                        stats["duplicates_found"] += 1
                    
                    extension_mismatches = len(distribution_result["distribution_details"].get("extension_mismatches", []))
                    stats["extension_mismatches"] += extension_mismatches
                    
                    # Сохраняем детали несоответствий расширений
                    for file_info in distribution_result["files"]:
                        if not file_info.get("extension_matches_content", True):
                            mismatch_detail = {
                                "unit_id": unit_id,
                                "file_name": file_info.get("original_name", "unknown"),
                                "extension": file_info.get("extension", "unknown"),
                                "expected_type": file_info.get("extension", "").replace(".", ""),
                                "detected_type": file_info.get("detected_type", "unknown"),
                                "mime_type": file_info.get("mime_type", "unknown")
                            }
                            stats["extension_mismatch_details"].append(mismatch_detail)
                    
                    for file_type in distribution_result["file_types"]:
                        stats["file_types"][file_type] += 1
                    
                    # Определяем целевую директорию для статистики
                    target_dir = Path(distribution_result["target_dir"])
                    if "mixed" in str(target_dir):
                        stats["target_dirs"]["mixed"] += 1
                    else:
                        parent_name = target_dir.parent.name if target_dir.parent.name != "detected" else target_dir.name
                        stats["target_dirs"][parent_name] += 1
                    
                    # Выводим результат
                    status_icon = "🔀" if distribution_result["is_mixed"] else "✓"
                    print(f"{status_icon} {', '.join(distribution_result['file_types'])}")
                
                except Exception as e:
                    stats["errors"] += 1
                    error_msg = str(e)
                    print(f"✗ Ошибка: {error_msg[:50]}")
                    # Отслеживаем units с ошибками
                    stats["unprocessed_units"].append({
                        "unit_id": unit_id,
                        "reason": "error",
                        "message": error_msg,
                        "error_type": type(e).__name__
                    })
            
            duration = time.time() - start_time
            
            # Выводим итоговую статистику
            print(f"\n{'='*80}")
            print("РЕЗУЛЬТАТЫ ОБРАБОТКИ")
            print(f"{'='*80}")
            print(f"Обработано unit'ов: {stats['processed_units']}/{len(unit_dirs)}")
            print(f"Обработано файлов: {stats['processed_files']}")
            print(f"Время выполнения: {duration:.2f} сек")
            if stats['processed_units'] > 0:
                print(f"Среднее время на unit: {duration/stats['processed_units']:.2f} сек")
            
            print(f"\nРаспределение по типам:")
            for file_type, count in sorted(stats['file_types'].items()):
                print(f"  {file_type}: {count}")
            
            print(f"\nРаспределение по директориям:")
            for target_dir, count in sorted(stats['target_dirs'].items()):
                print(f"  {target_dir}: {count} unit'ов")
            
            print(f"\nОсобые случаи:")
            print(f"  Mixed units: {stats['mixed_units']}")
            print(f"  Дубликаты: {stats['duplicates_found']} unit'ов")
            print(f"  Несоответствий расширений: {stats['extension_mismatches']}")
            print(f"  Ошибок: {stats['errors']}")
            
            # Выводим информацию о необработанных units
            unprocessed_count = len(stats.get("unprocessed_units", []))
            if unprocessed_count > 0:
                print(f"\nНеобработанные units: {unprocessed_count}")
                # Группируем по причинам
                by_reason = defaultdict(list)
                for unit in stats["unprocessed_units"]:
                    by_reason[unit["reason"]].append(unit)
                
                for reason, units in sorted(by_reason.items()):
                    reason_name = {
                        "no_files": "Без файлов",
                        "error": "Ошибка обработки"
                    }.get(reason, reason)
                    print(f"  {reason_name}: {len(units)} unit'ов")
                    if len(units) <= 10:
                        for unit_info in units:
                            uid = unit_info["unit_id"]
                            diagnosis = unit_info.get("diagnosis", {})
                            if diagnosis:
                                reasons = diagnosis.get("possible_reasons", [])
                                if reasons:
                                    print(f"    - {uid}: {reasons[0]}")
                                else:
                                    print(f"    - {uid}")
                            else:
                                print(f"    - {uid}")
                    else:
                        for unit_info in units[:5]:
                            uid = unit_info["unit_id"]
                            diagnosis = unit_info.get("diagnosis", {})
                            if diagnosis:
                                reasons = diagnosis.get("possible_reasons", [])
                                if reasons:
                                    print(f"    - {uid}: {reasons[0]}")
                                else:
                                    print(f"    - {uid}")
                            else:
                                print(f"    - {uid}")
                        print(f"    ... и еще {len(units) - 5} unit'ов")
            
            # Выводим детали несоответствий расширений
            if stats.get("extension_mismatch_details"):
                print(f"\nДетали несоответствий расширений:")
                # Группируем по типам несоответствий
                mismatch_groups = defaultdict(int)
                for detail in stats["extension_mismatch_details"]:
                    key = f"{detail['extension']} → {detail['detected_type']}"
                    mismatch_groups[key] += 1
                
                for mismatch_type, count in sorted(mismatch_groups.items(), key=lambda x: x[1], reverse=True):
                    print(f"  {mismatch_type}: {count}")
            
            print(f"{'='*80}\n")
        
        except ImportError as e:
            print(f"\n✗ Ошибка импорта модулей: {e}")
            print("Убедитесь, что все зависимости установлены.")
        except Exception as e:
            print(f"\n✗ Ошибка обработки: {e}")
            import traceback
            traceback.print_exc()
    
    def handle_extract_archive(self, limit: Optional[int] = None):
        """Обработка распаковки архивов."""
        print("\n=== Распаковка архивов ===")
        if limit is None:
            limit_str = input(f"Лимит обработки (0 = все, текущий: {LIMIT_EXTRACT_ARCHIVE}): ").strip()
            limit = int(limit_str) if limit_str else LIMIT_EXTRACT_ARCHIVE
        
        print(f"Обработка архивов с лимитом {limit if limit > 0 else 'без ограничений'}...")
        print("Используйте API endpoint: POST /trigger/extract_archive")
    
    
    def handle_normalize(self, limit: Optional[int] = None):
        """Обработка нормализации файлов."""
        print("\n=== Нормализация файлов ===")
        if limit is None:
            limit_str = input(f"Лимит обработки (0 = все, текущий: {LIMIT_NORMALIZE}): ").strip()
            limit = int(limit_str) if limit_str else LIMIT_NORMALIZE
        
        print(f"Нормализация файлов с лимитом {limit if limit > 0 else 'без ограничений'}...")
        print("Используйте API endpoint: POST /trigger/normalize")
    
    def handle_create_manifest(self, limit: Optional[int] = None):
        """Обработка создания manifest."""
        print("\n=== Создание manifest ===")
        if limit is None:
            limit_str = input(f"Лимит обработки (0 = все, текущий: {LIMIT_CREATE_MANIFEST}): ").strip()
            limit = int(limit_str) if limit_str else LIMIT_CREATE_MANIFEST
        
        print(f"Создание manifest с лимитом {limit if limit > 0 else 'без ограничений'}...")
        print("Используйте API endpoint: POST /trigger/create_manifest")
    
    def show_statistics(self):
        """Показывает статистику по этапам."""
        print("\n=== Статистика по этапам ===")
        stats = self.state_manager.get_statistics()
        
        print(f"\nЭтап 1 (uploaded):     {len(list(INPUT_DIR.iterdir()))} файлов в input/")
        print(f"Этап 2 (detected):     {stats['detected']['count']} файлов")
        print(f"  По типам: {stats['detected']['by_type']}")
        print(f"Этап 3 (extracted):    {stats['extracted']['count']} файлов (из {stats['extracted']['archives_processed']} архивов)")
        print(f"Этап 4 (converted):    {stats['converted']['count']} файлов")
        print(f"Этап 5 (normalized):   {stats['normalized']['count']} unit'ов")
        print(f"Этап 6 (ready):        {stats['ready']['count']} unit'ов готовы для Docling")
        
        print("\nТекущие лимиты:")
        limits = get_limits()
        for stage, limit in limits.items():
            print(f"  {stage}: {limit if limit > 0 else 'без ограничений'}")
    
    def show_metrics(self, stage: Optional[str] = None):
        """Показывает метрики обработки."""
        print("\n=== Метрики обработки ===")
        metrics = get_processing_summary()
        
        if not metrics:
            print("Метрики не найдены")
            return
        
        summary = metrics.get("summary", {})
        print(f"\nСессия: {metrics.get('session_id', 'N/A')}")
        print(f"Начало: {metrics.get('started_at', 'N/A')}")
        print(f"Завершение: {metrics.get('completed_at', 'N/A')}")
        print(f"\nСтатистика:")
        print(f"  Всего файлов: {summary.get('total_input_files', 0)}")
        print(f"  Всего архивов: {summary.get('total_archives', 0)}")
        print(f"  Всего unit'ов: {summary.get('total_units', 0)}")
        print(f"  Ошибок: {summary.get('total_errors', 0)}")
    
    def show_logs(self, filter_by: Optional[str] = None):
        """Показывает логи."""
        print("\n=== Логи ===")
        print("Логи доступны через API endpoint: GET /metrics/processing")
        print("Или проверьте логи сервиса router")
    
    def configure_limits(self):
        """Настройка лимитов обработки."""
        print("\n=== Настройки лимитов обработки ===")
        limits = get_limits()
        
        print("\nТекущие лимиты:")
        print("1. Определение типа:     ", limits.get("detect_type", 0), "(0 = без ограничений)")
        print("2. Распаковка архивов:   ", limits.get("extract_archive", 0), "(0 = без ограничений)")
        print("3. Конвертация DOC:      ", limits.get("convert_doc", 0), "(0 = без ограничений)")
        print("4. Нормализация:         ", limits.get("normalize", 0), "(0 = без ограничений)")
        print("5. Создание manifest:    ", limits.get("create_manifest", 0), "(0 = без ограничений)")
        
        choice = input("\nИзменить лимит [1-5] или 0 для возврата: ").strip()
        
        if choice == "0":
            return
        
        stage_map = {
            "1": "detect_type",
            "2": "extract_archive",
            "3": "convert_doc",
            "4": "normalize",
            "5": "create_manifest"
        }
        
        if choice in stage_map:
            stage = stage_map[choice]
            new_limit = input(f"Введите новое значение (0 = без ограничений): ").strip()
            try:
                limit_value = int(new_limit)
                if update_limit(stage, limit_value):
                    print(f"Лимит для {stage} обновлен: {limit_value}")
                else:
                    print("Ошибка обновления лимита")
            except ValueError:
                print("Неверное значение")
        else:
            print("Неверный выбор")
    
    def run_full_pipeline(self, limits: Optional[Dict[str, int]] = None):
        """Запуск полного пайплайна."""
        print("\n=== Автоматическая обработка ===")
        print("Запуск полного пайплайна для всех файлов из input/")
        print("Используйте API endpoint: POST /process_now")
        print("Или запустите через API клиент")
    
    def handle_cleanup(self):
        """Очистка директорий и данных из MongoDB."""
        print("\n=== Очистка директорий и данных из MongoDB ===")
        print("\n⚠️  ВНИМАНИЕ: Эта операция удалит:")
        print("  - Все файлы из директорий обработки (НОВАЯ СИСТЕМА)")
        print("  - Все данные из коллекций MongoDB")
        print("\nДиректории для очистки:")
        print(f"  - {INPUT_DIR}")
        print(f"  - {PENDING_DIR}")
        print(f"  - {READY_DOCLING_DIR}")
        print(f"  - {TEMP_DIR}")
        print("\nКоллекции MongoDB для очистки:")
        print(f"  - {MONGO_METADATA_DB}.protocols")
        print(f"  - {MONGO_METADATA_DB}.file_detections")
        print(f"  - {MONGO_METADATA_DB}.unit_distributions")
        print(f"  - {MONGO_METADATA_DB}.{MONGO_METADATA_COLLECTION}")
        print(f"  - {MONGO_METADATA_DB}.{MONGO_METRICS_COLLECTION}")
        
        confirm = input("\nПродолжить очистку? (yes/no): ").strip().lower()
        if confirm != "yes":
            print("Очистка отменена.")
            return
        
        print("\nНачало очистки...")
        
        # Очистка директорий
        directories = [
            INPUT_DIR, PENDING_DIR, READY_DOCLING_DIR, TEMP_DIR
        ]
        
        dirs_cleaned = 0
        files_removed = 0
        
        for directory in directories:
            if not directory.exists():
                continue
            
            try:
                file_count = sum(1 for _ in directory.rglob("*") if _.is_file())
                files_removed += file_count
                
                for item in directory.iterdir():
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
                
                dirs_cleaned += 1
                print(f"  ✓ Очищена директория: {directory.name} ({file_count} файлов)")
            except Exception as e:
                print(f"  ✗ Ошибка при очистке {directory.name}: {e}")
        
        # Очистка MongoDB коллекций
        client = None
        try:
            print("\nОчистка коллекций MongoDB...")
            client = get_metadata_client()
            if not client:
                print("  ✗ Не удалось подключиться к MongoDB")
            else:
                db = client[MONGO_METADATA_DB]
                collections_to_clean = [
                    ("protocols", "Протоколы"),
                    ("file_detections", "Метаданные файлов"),
                    ("unit_distributions", "Распределения unit'ов"),
                    (MONGO_METADATA_COLLECTION, "Манифесты"),
                    (MONGO_METRICS_COLLECTION, "Метрики обработки"),
                ]
                
                for coll_name, description in collections_to_clean:
                    try:
                        coll = db[coll_name]
                        count = coll.count_documents({})
                        if count > 0:
                            coll.delete_many({})
                            print(f"  ✓ Очищена коллекция {coll_name} ({description}): {count} документов")
                        else:
                            print(f"  - Коллекция {coll_name} уже пуста")
                    except Exception as e:
                        print(f"  ✗ Ошибка при очистке {coll_name}: {e}")
        
        except Exception as e:
            print(f"\n✗ Ошибка при подключении к MongoDB: {e}")
        finally:
            if client:
                client.close()
        
        print("\n" + "=" * 80)
        print("✓ ОЧИСТКА ЗАВЕРШЕНА")
        print("=" * 80)
        print(f"  Очищено директорий: {dirs_cleaned}")
        print(f"  Удалено файлов: {files_removed}")
        print("\nВсе данные удалены. Можно начинать новый цикл обработки.")
    
    def handle_check_sorted_units(self):
        """Проверка отсортированных units после определения типов."""
        print("\n=== Проверка отсортированных units ===")
        
        try:
            import subprocess
            import sys
            from pathlib import Path
            
            script_path = Path(__file__).parent.parent.parent / "scripts" / "check_sorted_units.py"
            
            if not script_path.exists():
                print(f"✗ Скрипт не найден: {script_path}")
                return
            
            print("\nЗапуск проверки...")
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=False,
                text=True
            )
            
            if result.returncode != 0:
                print("\n⚠ Обнаружены проблемы при проверке")
            else:
                print("\n✓ Проверка завершена успешно")
        
        except Exception as e:
            print(f"\n✗ Ошибка при проверке: {e}")
            import traceback
            traceback.print_exc()
    
    
    def handle_analyze_detection_issues(self):
        """Анализ проблем определения типов файлов."""
        print("\n=== Анализ проблем определения типов файлов ===")
        
        session_id = input("ID сессии для анализа (Enter = последняя сессия): ").strip()
        session_id = session_id if session_id else None
        
        try:
            import subprocess
            import sys
            from pathlib import Path
            
            script_path = Path(__file__).parent.parent.parent / "scripts" / "analyze_detection_issues.py"
            
            if not script_path.exists():
                print(f"✗ Скрипт не найден: {script_path}")
                return
            
            print("\nЗапуск анализа...")
            cmd = [sys.executable, str(script_path)]
            if session_id:
                cmd.extend(["--session-id", session_id])
            
            result = subprocess.run(
                cmd,
                capture_output=False,
                text=True
            )
            
            if result.returncode != 0:
                print("\n⚠ Обнаружены проблемы при анализе")
            else:
                print("\n✓ Анализ завершен успешно")
        
        except Exception as e:
            print(f"\n✗ Ошибка при анализе: {e}")
            import traceback
            traceback.print_exc()
    
    def handle_convert_doc_to_html(self):
        """Конвертация DOC → HTML (для файлов из detected/htmlDOC/)."""
        print("\n=== Конвертация DOC → HTML ===")
        
        html_doc_dir = DETECTED_DIR / "htmlDOC"
        if not html_doc_dir.exists():
            print(f"✗ Директория не найдена: {html_doc_dir}")
            return
        
        from .html_processor import process_fake_doc_html
        
        unit_dirs = [d for d in html_doc_dir.iterdir() if d.is_dir() and d.name.startswith("UNIT_")]
        if not unit_dirs:
            print("✓ Нет units для обработки")
            return
        
        print(f"\nНайдено {len(unit_dirs)} units для обработки")
        
        processed = 0
        errors = 0
        
        for unit_dir in unit_dirs:
            unit_id = unit_dir.name
            files_dir = unit_dir / "files"
            
            if not files_dir.exists():
                continue
            
            doc_files = list(files_dir.glob("*.doc"))
            for doc_file in doc_files:
                try:
                    new_path, metadata = process_fake_doc_html(doc_file, unit_id)
                    print(f"✓ {doc_file.name} → {new_path.name}")
                    processed += 1
                except Exception as e:
                    print(f"✗ Ошибка при обработке {doc_file.name}: {e}")
                    errors += 1
        
        print(f"\n✓ Обработано: {processed}, ошибок: {errors}")
    
    def handle_convert_doc_to_xml(self):
        """Конвертация DOC → XML (для файлов из detected/xmlDOC/)."""
        print("\n=== Конвертация DOC → XML ===")
        
        xml_doc_dir = DETECTED_DIR / "xmlDOC"
        if not xml_doc_dir.exists():
            print(f"✗ Директория не найдена: {xml_doc_dir}")
            return
        
        from .xml_processor import process_fake_doc_xml
        
        unit_dirs = [d for d in xml_doc_dir.iterdir() if d.is_dir() and d.name.startswith("UNIT_")]
        if not unit_dirs:
            print("✓ Нет units для обработки")
            return
        
        print(f"\nНайдено {len(unit_dirs)} units для обработки")
        
        processed = 0
        errors = 0
        
        for unit_dir in unit_dirs:
            unit_id = unit_dir.name
            files_dir = unit_dir / "files"
            
            if not files_dir.exists():
                continue
            
            doc_files = list(files_dir.glob("*.doc"))
            for doc_file in doc_files:
                try:
                    new_path, metadata = process_fake_doc_xml(doc_file, unit_id)
                    print(f"✓ {doc_file.name} → {new_path.name}")
                    processed += 1
                except Exception as e:
                    print(f"✗ Ошибка при обработке {doc_file.name}: {e}")
                    errors += 1
        
        print(f"\n✓ Обработано: {processed}, ошибок: {errors}")
    
    def handle_sort_pdf(self):
        """Сортировка PDF на text_pdf и scan_pdf."""
        print("\n=== Сортировка PDF на text_pdf и scan_pdf ===")
        
        limit_str = input("Лимит units для обработки (Enter = все): ").strip()
        limit = int(limit_str) if limit_str else None
        
        from .pdf_sorter import sort_pdf_units, cleanup_already_sorted_units
        
        try:
            result = sort_pdf_units(limit=limit)
            
            if result.get("success"):
                stats = result["statistics"]
                print(f"\n✓ Сортировка завершена")
                print(f"\nСтатистика:")
                print(f"  Всего units: {stats['total_units']}")
                print(f"  Обработано: {stats['processed_units']}")
                if stats.get('skipped_units', 0) > 0:
                    print(f"  Пропущено: {stats['skipped_units']}")
                print(f"  text_pdf: {stats['text_pdf_units']} ({stats['text_pdf_percentage']:.1f}%)")
                print(f"  scan_pdf: {stats['scan_pdf_units']} ({stats['scan_pdf_percentage']:.1f}%)")
                print(f"  Ошибок: {stats['errors']}")
                
                # Очищаем уже отсортированные директории
                print(f"\nОчистка уже отсортированных units...")
                cleanup_result = cleanup_already_sorted_units()
                if cleanup_result.get("success"):
                    removed = cleanup_result.get("removed_count", 0)
                    if removed > 0:
                        print(f"  ✓ Удалено уже отсортированных units: {removed}")
                    else:
                        print(f"  ✓ Нет уже отсортированных units для удаления")
                    if cleanup_result.get("errors"):
                        print(f"  ⚠ Ошибок при очистке: {len(cleanup_result['errors'])}")
                
                # Выводим детали пропущенных units
                if stats.get('skipped_details'):
                    print(f"\nПропущенные units:")
                    by_reason = {}
                    for skipped in stats['skipped_details']:
                        reason = skipped.get('reason', 'unknown')
                        if reason not in by_reason:
                            by_reason[reason] = []
                        by_reason[reason].append(skipped['unit_id'])
                    
                    for reason, unit_ids in sorted(by_reason.items()):
                        reason_name = {
                            "no_files_dir": "Без директории files/",
                            "no_pdf_files": "Без PDF файлов"
                        }.get(reason, reason)
                        print(f"  {reason_name}: {len(unit_ids)} unit'ов")
                        if len(unit_ids) <= 10:
                            for uid in unit_ids:
                                print(f"    - {uid}")
                        else:
                            for uid in unit_ids[:5]:
                                print(f"    - {uid}")
                            print(f"    ... и еще {len(unit_ids) - 5} unit'ов")
            else:
                print(f"\n✗ Ошибка: {result.get('error', 'Неизвестная ошибка')}")
        
        except Exception as e:
            print(f"\n✗ Ошибка при сортировке: {e}")
            import traceback
            traceback.print_exc()
    
    def handle_pending_directories(self):
        """Просмотр содержимого промежуточных директорий."""
        print("\n=== Просмотр промежуточных директорий ===")
        
        # Проверяем существование директорий
        pending_dirs = {
            "PENDING_NORMALIZE_DIR": PENDING_NORMALIZE_DIR,
            "PENDING_CONVERT_DIR": PENDING_CONVERT_DIR,
            "PENDING_EXTRACT_DIR": PENDING_EXTRACT_DIR
        }
        
        for dir_name, dir_path in pending_dirs.items():
            print(f"\n{dir_name}: {dir_path}")
            if not dir_path.exists():
                print("  ✗ Директория не существует")
                continue
            
            # Считаем количество unit'ов
            unit_dirs = [d for d in dir_path.rglob("UNIT_*") if d.is_dir()]
            print(f"  Найдено unit'ов: {len(unit_dirs)}")
            
            # Показываем первые 5 unit'ов
            if unit_dirs:
                print("  Первые unit'ы:")
                for unit_dir in sorted(unit_dirs)[:5]:
                    files_dir = unit_dir / "files"
                    if files_dir.exists():
                        files = [f for f in files_dir.iterdir() if f.is_file()]
                        print(f"    {unit_dir.name}: {len(files)} файлов")
                    else:
                        print(f"    {unit_dir.name}: нет директории files/")
                
                if len(unit_dirs) > 5:
                    print(f"    ... и еще {len(unit_dirs) - 5} unit'ов")
        
        # Показываем статистику по ReadyDocling
        print(f"\nREADY_DOCLING_DIR: {READY_DOCLING_DIR}")
        if READY_DOCLING_DIR.exists():
            # Считаем PDF файлы
            text_pdf_dir = READY_DOCLING_DIR / "pdf" / "text"
            scan_pdf_dir = READY_DOCLING_DIR / "pdf" / "scan"
            
            text_units = []
            scan_units = []
            
            if text_pdf_dir.exists():
                text_units = [d for d in text_pdf_dir.iterdir() if d.is_dir() and d.name.startswith("UNIT_")]
            if scan_pdf_dir.exists():
                scan_units = [d for d in scan_pdf_dir.iterdir() if d.is_dir() and d.name.startswith("UNIT_")]
            
            print(f"  PDF с текстовым слоем: {len(text_units)} unit'ов")
            print(f"  PDF сканы (требуют OCR): {len(scan_units)} unit'ов")
            
            # Считаем другие типы файлов
            other_types = ["docx", "html", "excel", "rtf", "doc", "zip", "rar", "7z", "unknown", "signature"]
            for file_type in other_types:
                type_dir = READY_DOCLING_DIR / file_type
                if type_dir.exists():
                    units = [d for d in type_dir.iterdir() if d.is_dir() and d.name.startswith("UNIT_")]
                    if units:
                        print(f"  {file_type.upper()}: {len(units)} unit'ов")
        else:
            print("  ✗ Директория не существует")
    
    def handle_detailed_metrics(self):
        """Просмотр детализированных метрик."""
        print("\n=== Детализированные метрики ===")
        
        try:
            from .metrics import get_current_metrics, get_processing_summary
            
            # Получаем текущие метрики
            current_metrics = get_current_metrics()
            if current_metrics:
                print("\nТекущая сессия обработки:")
                print(f"  Session ID: {current_metrics.get('session_id', 'N/A')}")
                started_at = current_metrics.get('started_at')
                if started_at:
                    print(f"  Начало: {started_at}")
                
                # Статистика по промежуточным директориям
                pending_processing = current_metrics.get("pending_processing", {})
                if pending_processing:
                    print("\n  Промежуточные директории:")
                    for stage, items in pending_processing.items():
                        print(f"    {stage}: {len(items)} файлов")
                
                # Статистика по дубликатам
                duplicates = current_metrics.get("duplicates", [])
                if duplicates:
                    print(f"\n  Дубликаты:")
                    print(f"    Групп дубликатов: {len(duplicates)}")
                    total_dups = sum(d.get('duplicate_count', 0) for d in duplicates)
                    print(f"    Всего дубликатов: {total_dups}")
            else:
                print("  Нет активной сессии обработки")
            
            # Получаем последние сохраненные метрики
            print("\nПоследняя сохраненная сессия:")
            last_metrics = get_processing_summary()
            if last_metrics:
                print(f"  Session ID: {last_metrics.get('session_id', 'N/A')}")
                started_at = last_metrics.get('started_at')
                completed_at = last_metrics.get('completed_at')
                if started_at:
                    print(f"  Начало: {started_at}")
                if completed_at:
                    print(f"  Завершение: {completed_at}")
                
                # Summary статистика
                summary = last_metrics.get("summary", {})
                if summary:
                    print(f"\n  Общая статистика:")
                    print(f"    Входных файлов: {summary.get('total_input_files', 0)}")
                    print(f"    Архивов: {summary.get('total_archives', 0)}")
                    print(f"    Извлечено файлов: {summary.get('total_extracted', 0)}")
                    print(f"    Unit'ов: {summary.get('total_units', 0)}")
                    print(f"    Ошибок: {summary.get('total_errors', 0)}")
                    
                    # Статистика по промежуточным директориям
                    pending_stats = summary.get("pending_statistics", {})
                    if pending_stats:
                        print(f"\n  Промежуточные директории:")
                        print(f"    В pending/normalize: {pending_stats.get('files_in_pending_normalize', 0)}")
                        print(f"    В pending/convert: {pending_stats.get('files_in_pending_convert', 0)}")
                        print(f"    В pending/extract: {pending_stats.get('files_in_pending_extract', 0)}")
                        print(f"    Обработано из pending: {pending_stats.get('files_processed_from_pending', 0)}")
                    
                    # Статистика по дубликатам
                    duplicate_stats = summary.get("duplicate_statistics", {})
                    if duplicate_stats:
                        print(f"\n  Дубликаты:")
                        print(f"    Всего дубликатов: {duplicate_stats.get('total_duplicate_files', 0)}")
                        print(f"    Групп дубликатов: {duplicate_stats.get('duplicate_groups_count', 0)}")
            else:
                print("  Нет сохраненных метрик")
                
        except Exception as e:
            print(f"✗ Ошибка при получении метрик: {e}")
            import traceback
            traceback.print_exc()
    
    def handle_force_cleanup(self):
        """Принудительная очистка пустых директорий."""
        print("\n=== Принудительная очистка пустых директорий ===")
        
        try:
            from .utils import cleanup_all_empty_unit_directories
            
            # Список базовых директорий для очистки
            base_directories = [
                PENDING_NORMALIZE_DIR,
                PENDING_CONVERT_DIR,
                PENDING_EXTRACT_DIR,
                DETECTED_DIR,
                EXTRACTED_DIR,
                CONVERTED_DIR,
                NORMALIZED_DIR
            ]
            
            # Получаем список всех unit'ов для очистки
            unit_ids = set()
            for base_dir in base_directories:
                if base_dir.exists():
                    for unit_dir in base_dir.rglob("UNIT_*"):
                        if unit_dir.is_dir():
                            unit_ids.add(unit_dir.name)
            
            print(f"Найдено unit'ов для проверки: {len(unit_ids)}")
            
            if not unit_ids:
                print("Нет unit'ов для очистки")
                return
            
            # Запрашиваем подтверждение
            confirm = input(f"Выполнить очистку пустых директорий для {len(unit_ids)} unit'ов? (y/N): ").strip().lower()
            if confirm != 'y':
                print("Очистка отменена")
                return
            
            # Выполняем очистку для каждого unit'а
            total_removed = 0
            errors = []
            
            for i, unit_id in enumerate(sorted(unit_ids), 1):
                if i % 100 == 0:
                    print(f"[{i}/{len(unit_ids)}] Обработано...")
                try:
                    result = cleanup_all_empty_unit_directories(unit_id, base_directories)
                    if result["success"]:
                        total_removed += result["total_removed"]
                    else:
                        errors.extend(result["errors"])
                except Exception as e:
                    errors.append(f"{unit_id}: {e}")
            
            print(f"\nИтоги очистки:")
            print(f"  Удалено директорий: {total_removed}")
            print(f"  Ошибок: {len(errors)}")
            
            if errors:
                print("Первые ошибки:")
                for error in errors[:10]:
                    print(f"  {error}")
                if len(errors) > 10:
                    print(f"  ... и еще {len(errors) - 10} ошибок")
                    
        except Exception as e:
            print(f"✗ Ошибка при очистке: {e}")
            import traceback
            traceback.print_exc()
    
    def handle_view_pending_structure(self):
        """Просмотр новой pending структуры."""
        print("\n=== Новая Pending Структура ===")
        
        try:
            from .unit_distribution_new import get_unit_statistics
            
            stats = get_unit_statistics()
            
            print("\nСтатистика по категориям:")
            for category, data in stats.items():
                if data["units"] > 0 or data["files"] > 0:
                    print(f"\n{category.upper()}:")
                    print(f"  Unit'ов: {data['units']}")
                    print(f"  Файлов: {data['files']}")
            
            # Показываем структуру директорий
            from .config import (
                PENDING_DIRECT_DIR, PENDING_NORMALIZE_DIR, PENDING_CONVERT_DIR,
                PENDING_EXTRACT_DIR, PENDING_SPECIAL_DIR
            )
            
            dirs = {
                "DIRECT": PENDING_DIRECT_DIR,
                "NORMALIZE": PENDING_NORMALIZE_DIR,
                "CONVERT": PENDING_CONVERT_DIR,
                "EXTRACT": PENDING_EXTRACT_DIR,
                "SPECIAL": PENDING_SPECIAL_DIR
            }
            
            print("\n\nПути к директориям:")
            for name, path in dirs.items():
                exists = "✓" if path.exists() else "✗"
                print(f"{exists} {name}: {path}")
                
        except Exception as e:
            print(f"✗ Ошибка: {e}")
            import traceback
            traceback.print_exc()
    
    def handle_category_statistics(self):
        """Статистика по категориям обработки."""
        print("\n=== Статистика по категориям ===")
        
        try:
            from .unit_distribution_new import get_unit_statistics
            from .mixed_unit_handler import get_mixed_units_statistics
            from .merge import get_ready_docling_statistics
            
            # Статистика pending
            print("\n📁 PENDING (промежуточная обработка):")
            pending_stats = get_unit_statistics()
            
            # Добавляем mixed статистику
            mixed_stats = get_mixed_units_statistics(include_extraction=True)
            
            total_pending_units = sum(cat["units"] for cat in pending_stats.values())
            total_pending_files = sum(cat["files"] for cat in pending_stats.values())
            
            print(f"\n  Всего unit'ов: {total_pending_units}")
            print(f"  Всего файлов: {total_pending_files}")
            
            print("\n  По категориям:")
            for category in ["direct", "normalize", "convert", "extract", "special", "mixed"]:
                data = pending_stats.get(category, {"units": 0, "files": 0})
                if data["units"] > 0:
                    print(f"    {category:12} - {data['units']:4} unit'ов, {data['files']:5} файлов")
            
            # Показываем mixed units детально если есть
            if mixed_stats["total_mixed"]["units"] > 0:
                print(f"\n  🔀 Mixed units (детально):")
                if mixed_stats["detection_mixed"]["units"] > 0:
                    print(f"    └─ из detection:  {mixed_stats['detection_mixed']['units']:4} unit'ов, {mixed_stats['detection_mixed']['files']:5} файлов")
                if mixed_stats["extraction_mixed"]["units"] > 0:
                    print(f"    └─ из extraction: {mixed_stats['extraction_mixed']['units']:4} unit'ов, {mixed_stats['extraction_mixed']['files']:5} файлов")
            
            # Статистика ready_docling
            print("\n\n✅ READY_DOCLING (готово для Docling):")
            ready_stats = get_ready_docling_statistics()
            
            print(f"\n  Всего unit'ов: {ready_stats['total_units']}")
            print(f"  Всего файлов: {ready_stats['total_files']}")
            
            if ready_stats['by_type']:
                print("\n  По типам файлов:")
                for file_type, data in sorted(ready_stats['by_type'].items()):
                    print(f"    {file_type:12} - {data['units']:4} unit'ов, {data['files']:5} файлов")
            
        except Exception as e:
            print(f"✗ Ошибка: {e}")
            import traceback
            traceback.print_exc()
    
    def handle_merge_dry_run(self):
        """Merge в ready_docling (DRY RUN режим)."""
        print("\n=== Merge в ready_docling (DRY RUN) ===")
        print("Режим имитации - файлы НЕ будут перемещены\n")
        
        try:
            from .merge import merge_to_ready_docling, print_merge_summary
            
            # Запрашиваем лимит
            limit_input = input("Лимит unit'ов (Enter = без ограничений): ").strip()
            limit = int(limit_input) if limit_input else None
            
            print("\nВыполняю merge в режиме DRY RUN...")
            result = merge_to_ready_docling(dry_run=True, limit=limit)
            
            print_merge_summary(result)
            
        except Exception as e:
            print(f"✗ Ошибка: {e}")
            import traceback
            traceback.print_exc()
    
    def handle_merge_real(self):
        """Merge в ready_docling (РЕАЛЬНЫЙ режим)."""
        print("\n=== Merge в ready_docling (РЕАЛЬНЫЙ РЕЖИМ) ===")
        print("⚠️  ВНИМАНИЕ: Файлы будут РЕАЛЬНО перемещены!\n")
        
        try:
            from .merge import merge_to_ready_docling, print_merge_summary
            
            # Запрашиваем лимит
            limit_input = input("Лимит unit'ов (Enter = без ограничений): ").strip()
            limit = int(limit_input) if limit_input else None
            
            # Подтверждение
            confirm = input(f"\nПеремещать файлы в ready_docling? (y/N): ").strip().lower()
            if confirm != 'y':
                print("Отменено")
                return
            
            print("\nВыполняю РЕАЛЬНЫЙ merge...")
            result = merge_to_ready_docling(dry_run=False, limit=limit)
            
            print_merge_summary(result)
            
            if result['files_moved'] > 0:
                print("\n✓ Merge завершен успешно!")
                
                # Предлагаем очистку
                cleanup = input("\nОчистить pending директории после merge? (y/N): ").strip().lower()
                if cleanup == 'y':
                    from .merge import cleanup_pending_after_merge
                    unit_ids = [f["unit_id"] for f in result.get("distributed_files", [])]
                    cleanup_result = cleanup_pending_after_merge(unit_ids, dry_run=False)
                    print(f"Очищено unit'ов: {cleanup_result['cleaned_units']}")
                    print(f"Удалено директорий: {cleanup_result['cleaned_directories']}")
            
        except Exception as e:
            print(f"✗ Ошибка: {e}")
            import traceback
            traceback.print_exc()
    
    def handle_step1_scan_and_detect(self, limit: Optional[int] = None):
        """ШАГ 1: Сканирование input/ и детекция типов файлов."""
        print("\n=== ШАГ 1: Сканирование и детекция типов файлов ===")
        
        if limit is None:
            limit_str = input(f"Лимит units (Enter = без ограничений): ").strip()
            limit = int(limit_str) if limit_str else None
        
        try:
            from .file_detection import detect_file_type
            from pathlib import Path
            from collections import defaultdict
            import time
            
            # Получаем список unit'ов
            unit_dirs = [d for d in INPUT_DIR.iterdir() if d.is_dir() and d.name.startswith("UNIT_")]
            total_units = len(unit_dirs)
            
            if limit:
                unit_dirs = unit_dirs[:limit]
            
            print(f"\nНайдено unit'ов: {total_units}")
            print(f"Обрабатывается: {len(unit_dirs)}")
            print(f"{'='*80}\n")
            
            start_time = time.time()
            
            # Статистика
            stats = {
                "units_scanned": 0,
                "files_scanned": 0,
                "by_extension": defaultdict(int),
                "by_detected_type": defaultdict(int),
                "extension_mismatches": 0,
                "empty_units": 0
            }
            
            for idx, unit_dir in enumerate(unit_dirs, 1):
                unit_id = unit_dir.name
                files = [f for f in unit_dir.iterdir() if f.is_file() and not f.name.startswith('.')]
                
                if not files:
                    stats["empty_units"] += 1
                    continue
                
                print(f"[{idx}/{len(unit_dirs)}] {unit_id} ({len(files)} файл(ов)):")
                stats["units_scanned"] += 1
                
                for file_path in files:
                    try:
                        # Определяем тип
                        detection = detect_file_type(file_path)
                        
                        ext = file_path.suffix.lower()
                        detected_type = detection.get("detected_type", "unknown")
                        mime = detection.get("mime_type", "unknown")
                        
                        stats["files_scanned"] += 1
                        stats["by_extension"][ext or ".no_ext"] += 1
                        stats["by_detected_type"][detected_type] += 1
                        
                        # Проверка соответствия расширения
                        mismatch = not detection.get("extension_matches_content", True)
                        if mismatch:
                            stats["extension_mismatches"] += 1
                        
                        # Вывод
                        mismatch_flag = " ⚠ MISMATCH" if mismatch else ""
                        print(f"  {file_path.name:40} | {ext:8} → {detected_type:12} | {mime:30}{mismatch_flag}")
                        
                    except Exception as e:
                        print(f"  ✗ {file_path.name}: {str(e)[:40]}")
                
                print()  # Пустая строка между units
            
            duration = time.time() - start_time
            
            # Итоговая статистика
            print(f"{'='*80}")
            print(f"ИТОГИ СКАНИРОВАНИЯ:")
            print(f"{'='*80}")
            print(f"Units обработано: {stats['units_scanned']}")
            print(f"Units пустых: {stats['empty_units']}")
            print(f"Файлов просканировано: {stats['files_scanned']}")
            print(f"Несоответствий расширений: {stats['extension_mismatches']}")
            print(f"Время: {duration:.2f} сек")
            
            print(f"\nПо расширениям:")
            for ext, count in sorted(stats["by_extension"].items(), key=lambda x: -x[1])[:10]:
                print(f"  {ext:15} - {count:4} файл(ов)")
            
            print(f"\nПо определенным типам:")
            for dtype, count in sorted(stats["by_detected_type"].items(), key=lambda x: -x[1])[:10]:
                print(f"  {dtype:15} - {count:4} файл(ов)")
        
        except Exception as e:
            print(f"✗ Ошибка: {e}")
            import traceback
            traceback.print_exc()
    
    def handle_step2_classify(self, limit: Optional[int] = None):
        """ШАГ 2: Классификация файлов по категориям."""
        print("\n=== ШАГ 2: Классификация файлов по категориям ===")
        
        if limit is None:
            limit_str = input(f"Лимит units (Enter = без ограничений): ").strip()
            limit = int(limit_str) if limit_str else None
        
        try:
            from .file_detection import detect_file_type
            from .file_classifier import classify_file
            from collections import defaultdict
            import time
            
            unit_dirs = [d for d in INPUT_DIR.iterdir() if d.is_dir() and d.name.startswith("UNIT_")]
            total_units = len(unit_dirs)
            
            if limit:
                unit_dirs = unit_dirs[:limit]
            
            print(f"\nНайдено unit'ов: {total_units}")
            print(f"Обрабатывается: {len(unit_dirs)}")
            print(f"{'='*80}\n")
            
            start_time = time.time()
            
            stats = {
                "units_classified": 0,
                "files_classified": 0,
                "by_category": defaultdict(int),
                "by_action": defaultdict(int)
            }
            
            for idx, unit_dir in enumerate(unit_dirs, 1):
                unit_id = unit_dir.name
                files = [f for f in unit_dir.iterdir() if f.is_file() and not f.name.startswith('.')]
                
                if not files:
                    continue
                
                print(f"[{idx}/{len(unit_dirs)}] {unit_id}:")
                stats["units_classified"] += 1
                
                for file_path in files:
                    try:
                        detection = detect_file_type(file_path)
                        classification = classify_file(file_path, detection)
                        
                        category = classification["category"]
                        action = classification["action"]
                        reason = classification.get("reason", "")
                        
                        stats["files_classified"] += 1
                        stats["by_category"][category] += 1
                        stats["by_action"][action] += 1
                        
                        print(f"  {file_path.name:40} → {category:12} | {action:15} | {reason}")
                        
                    except Exception as e:
                        print(f"  ✗ {file_path.name}: {str(e)[:40]}")
                
                print()
            
            duration = time.time() - start_time
            
            print(f"{'='*80}")
            print(f"ИТОГИ КЛАССИФИКАЦИИ:")
            print(f"{'='*80}")
            print(f"Units обработано: {stats['units_classified']}")
            print(f"Файлов классифицировано: {stats['files_classified']}")
            print(f"Время: {duration:.2f} сек")
            
            print(f"\nПо категориям:")
            for cat, count in sorted(stats["by_category"].items(), key=lambda x: -x[1]):
                print(f"  {cat:15} - {count:4} файл(ов)")
            
            print(f"\nПо действиям:")
            for act, count in sorted(stats["by_action"].items(), key=lambda x: -x[1]):
                print(f"  {act:15} - {count:4} файл(ов)")
        
        except Exception as e:
            print(f"✗ Ошибка: {e}")
            import traceback
            traceback.print_exc()
    
    def handle_step3_check_duplicates(self, limit: Optional[int] = None):
        """ШАГ 3: Проверка дубликатов."""
        print("\n=== ШАГ 3: Проверка дубликатов ===")
        
        if limit is None:
            limit_str = input(f"Лимит units (Enter = без ограничений): ").strip()
            limit = int(limit_str) if limit_str else None
        
        try:
            from .file_detection import detect_file_type
            from .file_classifier import classify_file
            from .duplicate_detection import detect_duplicates_in_unit
            import time
            
            unit_dirs = [d for d in INPUT_DIR.iterdir() if d.is_dir() and d.name.startswith("UNIT_")]
            total_units = len(unit_dirs)
            
            if limit:
                unit_dirs = unit_dirs[:limit]
            
            print(f"\nНайдено unit'ов: {total_units}")
            print(f"Обрабатывается: {len(unit_dirs)}")
            print(f"{'='*80}\n")
            
            start_time = time.time()
            
            stats = {
                "units_checked": 0,
                "units_with_duplicates": 0,
                "total_duplicate_groups": 0,
                "total_duplicate_files": 0
            }
            
            for idx, unit_dir in enumerate(unit_dirs, 1):
                unit_id = unit_dir.name
                files = [f for f in unit_dir.iterdir() if f.is_file() and not f.name.startswith('.')]
                
                if not files:
                    continue
                
                print(f"[{idx}/{len(unit_dirs)}] {unit_id}:")
                stats["units_checked"] += 1
                
                # Подготавливаем данные для проверки
                classified_files = []
                for file_path in files:
                    try:
                        detection = detect_file_type(file_path)
                        classification = classify_file(file_path, detection)
                        classified_files.append({
                            "path": str(file_path),
                            "original_name": file_path.name,
                            **detection,
                            "classification": classification
                        })
                    except Exception as e:
                        print(f"  ✗ Ошибка обработки {file_path.name}: {e}")
                
                # Проверяем дубликаты
                duplicates_map = detect_duplicates_in_unit(classified_files)
                
                if duplicates_map:
                    stats["units_with_duplicates"] += 1
                    stats["total_duplicate_groups"] += len(duplicates_map)
                    
                    print(f"  ⚠ Найдено {len(duplicates_map)} групп(ы) дубликатов:")
                    
                    for hash_value, dup_files in duplicates_map.items():
                        stats["total_duplicate_files"] += len(dup_files)
                        print(f"\n    Группа (hash: {hash_value[:12]}...):")
                        for dup_file in dup_files:
                            print(f"      - {dup_file.get('original_name')}")
                else:
                    print(f"  ✓ Дубликатов не найдено")
                
                print()
            
            duration = time.time() - start_time
            
            print(f"{'='*80}")
            print(f"ИТОГИ ПРОВЕРКИ ДУБЛИКАТОВ:")
            print(f"{'='*80}")
            print(f"Units проверено: {stats['units_checked']}")
            print(f"Units с дубликатами: {stats['units_with_duplicates']}")
            print(f"Всего групп дубликатов: {stats['total_duplicate_groups']}")
            print(f"Всего файлов-дубликатов: {stats['total_duplicate_files']}")
            print(f"Время: {duration:.2f} сек")
        
        except Exception as e:
            print(f"✗ Ошибка: {e}")
            import traceback
            traceback.print_exc()
    
    def handle_step4_check_mixed(self, limit: Optional[int] = None):
        """ШАГ 4: Определение mixed units."""
        print("\n=== ШАГ 4: Определение mixed units ===")
        
        if limit is None:
            limit_str = input(f"Лимит units (Enter = без ограничений): ").strip()
            limit = int(limit_str) if limit_str else None
        
        try:
            from .file_classifier import classify_unit_files
            import time
            
            unit_dirs = [d for d in INPUT_DIR.iterdir() if d.is_dir() and d.name.startswith("UNIT_")]
            total_units = len(unit_dirs)
            
            if limit:
                unit_dirs = unit_dirs[:limit]
            
            print(f"\nНайдено unit'ов: {total_units}")
            print(f"Обрабатывается: {len(unit_dirs)}")
            print(f"{'='*80}\n")
            
            start_time = time.time()
            
            stats = {
                "units_checked": 0,
                "mixed_units": 0,
                "homogeneous_units": 0
            }
            
            for idx, unit_dir in enumerate(unit_dirs, 1):
                unit_id = unit_dir.name
                files = [f for f in unit_dir.iterdir() if f.is_file() and not f.name.startswith('.')]
                
                if not files:
                    continue
                
                stats["units_checked"] += 1
                
                # Классифицируем unit
                unit_classification = classify_unit_files(files, unit_id)
                
                is_mixed = unit_classification["is_mixed"]
                unit_category = unit_classification["unit_category"]
                type_dist = unit_classification["type_distribution"]
                
                if is_mixed:
                    stats["mixed_units"] += 1
                    print(f"[{idx}/{len(unit_dirs)}] {unit_id}: 🔀 MIXED")
                    print(f"  Распределение по категориям:")
                    for cat, count in type_dist.items():
                        print(f"    {cat:15} - {count} файл(ов)")
                else:
                    stats["homogeneous_units"] += 1
                    print(f"[{idx}/{len(unit_dirs)}] {unit_id}: ✓ Однородный ({unit_category})")
                
                print()
            
            duration = time.time() - start_time
            
            print(f"{'='*80}")
            print(f"ИТОГИ ОПРЕДЕЛЕНИЯ MIXED UNITS:")
            print(f"{'='*80}")
            print(f"Units проверено: {stats['units_checked']}")
            print(f"Mixed units: {stats['mixed_units']}")
            print(f"Однородных units: {stats['homogeneous_units']}")
            print(f"Время: {duration:.2f} сек")
        
        except Exception as e:
            print(f"✗ Ошибка: {e}")
            import traceback
            traceback.print_exc()
    
    def handle_step5_distribute(self, limit: Optional[int] = None):
        """ШАГ 5: Распределение по pending директориям."""
        print("\n=== ШАГ 5: Распределение по pending директориям ===")
        
        if limit is None:
            limit_str = input(f"Лимит units (Enter = без ограничений): ").strip()
            limit = int(limit_str) if limit_str else None
        
        try:
            from .unit_distribution_new import distribute_unit_by_new_structure
            from .mixed_unit_handler import get_mixed_units_statistics
            from collections import defaultdict
            import time
            
            unit_dirs = [d for d in INPUT_DIR.iterdir() if d.is_dir() and d.name.startswith("UNIT_")]
            total_units = len(unit_dirs)
            
            if limit:
                unit_dirs = unit_dirs[:limit]
            
            print(f"\nНайдено unit'ов: {total_units}")
            print(f"Обрабатывается: {len(unit_dirs)}")
            print(f"{'='*80}\n")
            
            start_time = time.time()
            
            stats = {
                "units_processed": 0,
                "files_moved": 0,
                "by_category": defaultdict(int),
                "mixed_units": 0,
                "errors": 0
            }
            
            for idx, unit_dir in enumerate(unit_dirs, 1):
                unit_id = unit_dir.name
                files = [f for f in unit_dir.iterdir() if f.is_file() and not f.name.startswith('.')]
                
                if not files:
                    continue
                
                print(f"[{idx}/{len(unit_dirs)}] {unit_id} ({len(files)} файлов)...", end=" ", flush=True)
                
                try:
                    files_list = [{"path": str(f)} for f in files]
                    result = distribute_unit_by_new_structure(unit_id, files_list)
                    
                    stats["units_processed"] += 1
                    stats["files_moved"] += result["files_processed"]
                    
                    if result.get("is_mixed"):
                        stats["mixed_units"] += 1
                        print(f"🔀 MIXED → pending/mixed/")
                    else:
                        # Определяем основную категорию
                        main_cat = max(result["files_by_category"].items(), key=lambda x: x[1])[0] if result["files_by_category"] else "unknown"
                        stats["by_category"][main_cat] += 1
                        print(f"✓ → pending/{main_cat}/")
                    
                    # Показываем детали
                    if result.get("errors"):
                        print(f"     ⚠ Ошибок: {len(result['errors'])}")
                    if result.get("duplicates_detected"):
                        print(f"     ⚠ Дубликаты: {result['duplicate_count']} групп")
                    
                except Exception as e:
                    print(f"✗ Ошибка: {str(e)[:50]}")
                    stats["errors"] += 1
            
            duration = time.time() - start_time
            
            print(f"\n{'='*80}")
            print(f"ИТОГИ РАСПРЕДЕЛЕНИЯ:")
            print(f"{'='*80}")
            print(f"Units обработано: {stats['units_processed']}")
            print(f"Файлов перемещено: {stats['files_moved']}")
            print(f"Mixed units: {stats['mixed_units']}")
            print(f"Ошибок: {stats['errors']}")
            print(f"Время: {duration:.2f} сек")
            
            print(f"\nРаспределение по категориям:")
            for cat, count in sorted(stats["by_category"].items(), key=lambda x: -x[1]):
                print(f"  {cat:15} - {count:4} unit(ов)")
            
            # Финальная статистика mixed units
            mixed_stats = get_mixed_units_statistics(include_extraction=False)
            if mixed_stats["total_mixed"]["units"] > 0:
                print(f"\n🔀 Mixed units (детально):")
                print(f"  Units: {mixed_stats['total_mixed']['units']}")
                print(f"  Файлов: {mixed_stats['total_mixed']['files']}")
        
        except Exception as e:
            print(f"✗ Ошибка: {e}")
            import traceback
            traceback.print_exc()
    
    def handle_full_processing(self, limit: Optional[int] = None):
        """ПОЛНАЯ ОБРАБОТКА: Все шаги (3-7)."""
        print("\n=== ПОЛНАЯ ОБРАБОТКА: Все шаги (Сканирование → Распределение) ===")
        
        if limit is None:
            limit_str = input(f"Лимит units (Enter = без ограничений): ").strip()
            limit = int(limit_str) if limit_str else None
        
        print(f"\n{'='*80}")
        print("ЗАПУСК ПОЛНОЙ ОБРАБОТКИ")
        print(f"{'='*80}\n")
        
        # Запускаем все шаги последовательно (только распределение, остальные уже включены)
        self.handle_step5_distribute(limit=limit)
    
    def handle_units_report(self):
        """Отчет по обработанным units."""
        print("\n=== Отчет по обработанным units ===")
        
        try:
            from .config import PENDING_DIR
            import json
            
            categories = {
                "direct": PENDING_DIRECT_DIR,
                "normalize": PENDING_NORMALIZE_DIR,
                "convert": PENDING_CONVERT_DIR,
                "extract": PENDING_EXTRACT_DIR,
                "special": PENDING_SPECIAL_DIR,
                "mixed": PENDING_MIXED_DIR
            }
            
            total_units = 0
            total_files = 0
            
            for category, cat_dir in categories.items():
                if not cat_dir.exists():
                    continue
                
                units = [d for d in cat_dir.iterdir() if d.is_dir() and d.name.startswith("UNIT_")]
                
                if not units:
                    continue
                
                print(f"\n{'='*80}")
                print(f"Категория: {category.upper()}")
                print(f"{'='*80}")
                print(f"Units: {len(units)}\n")
                
                for unit_dir in units[:10]:  # Показываем первые 10
                    unit_id = unit_dir.name
                    files_dir = unit_dir / "files"
                    metadata_file = unit_dir / "metadata.json"
                    
                    files_count = 0
                    if files_dir.exists():
                        files = [f for f in files_dir.iterdir() if f.is_file()]
                        files_count = len(files)
                        total_files += files_count
                    
                    total_units += 1
                    
                    print(f"  {unit_id}: {files_count} файл(ов)")
                    
                    # Показываем метаданные если есть
                    if metadata_file.exists():
                        try:
                            with open(metadata_file, 'r') as f:
                                metadata = json.load(f)
                                dist_result = metadata.get("distribution_result", {})
                                if dist_result.get("duplicates_detected"):
                                    print(f"    ⚠ Дубликаты: {dist_result.get('duplicate_count', 0)} групп")
                                if dist_result.get("errors"):
                                    print(f"    ✗ Ошибок: {len(dist_result['errors'])}")
                        except:
                            pass
                
                if len(units) > 10:
                    print(f"  ... и еще {len(units) - 10} unit(ов)")
            
            print(f"\n{'='*80}")
            print(f"ИТОГО:")
            print(f"{'='*80}")
            print(f"Units обработано: {total_units}")
            print(f"Файлов всего: {total_files}")
        
        except Exception as e:
            print(f"✗ Ошибка: {e}")
            import traceback
            traceback.print_exc()
    
    def handle_new_structure_detection(self, limit: Optional[int] = None):
        """Определение типов файлов с использованием новой pending структуры."""
        print("\n=== Определение типов (НОВАЯ СИСТЕМА с pending/) ===")
        
        if limit is None:
            limit_str = input(f"Лимит обработки (Enter = без ограничений): ").strip()
            limit = int(limit_str) if limit_str else None
        
        try:
            from .unit_distribution_new import distribute_unit_by_new_structure, print_distribution_summary
            from .mixed_unit_handler import get_mixed_units_statistics
            from pathlib import Path
            import time
            
            # Получаем список unit'ов
            unit_dirs = [d for d in INPUT_DIR.iterdir() if d.is_dir() and d.name.startswith("UNIT_")]
            total_units = len(unit_dirs)
            
            if limit:
                unit_dirs = unit_dirs[:limit]
            
            print(f"\nНайдено unit'ов: {total_units}")
            print(f"Обрабатывается: {len(unit_dirs)}")
            print(f"{'='*80}\n")
            
            start_time = time.time()
            processed = 0
            errors = 0
            
            for idx, unit_dir in enumerate(unit_dirs, 1):
                unit_id = unit_dir.name
                files = [f for f in unit_dir.iterdir() if f.is_file() and not f.name.startswith('.')]
                
                if not files:
                    continue
                
                print(f"[{idx}/{len(unit_dirs)}] {unit_id} ({len(files)} файлов)...", end=" ", flush=True)
                
                try:
                    files_list = [{"path": str(f)} for f in files]
                    result = distribute_unit_by_new_structure(unit_id, files_list)
                    
                    if result.get("is_mixed"):
                        print(f"🔀 MIXED")
                    else:
                        print(f"✓")
                    
                    processed += 1
                except Exception as e:
                    print(f"✗ {str(e)[:30]}")
                    errors += 1
            
            duration = time.time() - start_time
            
            print(f"\n{'='*80}")
            print(f"Обработано: {processed}/{len(unit_dirs)}")
            print(f"Ошибок: {errors}")
            print(f"Время: {duration:.2f} сек")
            
            # После обработки показываем статистику mixed units
            mixed_stats = get_mixed_units_statistics(include_extraction=False)
            if mixed_stats["total_mixed"]["units"] > 0:
                print(f"\n🔀 Mixed units обнаружено: {mixed_stats['total_mixed']['units']}")
                print(f"  Файлов в mixed units: {mixed_stats['total_mixed']['files']}")
        
        except Exception as e:
            print(f"✗ Ошибка: {e}")
            import traceback
            traceback.print_exc()
    
    def run(self):
        """Главный цикл CLI."""
        while True:
            try:
                self.show_menu()
                choice = input("\nВыберите действие [0-19]: ").strip()
                
                if choice == "0":
                    print("Выход...")
                    break
                
                # === ЗАГРУЗКА И СИНХРОНИЗАЦИЯ ===
                elif choice == "1":
                    self.handle_download_protocols()
                elif choice == "2":
                    self.handle_sync_protocols()
                
                # === НОВАЯ СИСТЕМА (PENDING) - ПОШАГОВАЯ ОБРАБОТКА ===
                elif choice == "3":
                    self.handle_step1_scan_and_detect()
                elif choice == "4":
                    self.handle_step2_classify()
                elif choice == "5":
                    self.handle_step3_check_duplicates()
                elif choice == "6":
                    self.handle_step4_check_mixed()
                elif choice == "7":
                    self.handle_step5_distribute()
                elif choice == "8":
                    self.handle_full_processing()
                
                # === СТАТИСТИКА И ПРОСМОТР ===
                elif choice == "9":
                    self.handle_view_pending_structure()
                elif choice == "10":
                    self.handle_category_statistics()
                elif choice == "11":
                    self.handle_units_report()
                
                # === MERGE В READY_DOCLING ===
                elif choice == "12":
                    self.handle_merge_dry_run()
                elif choice == "13":
                    self.handle_merge_real()
                
                # === СЛУЖЕБНЫЕ ОПЕРАЦИИ ===
                elif choice == "14":
                    self.show_statistics()
                elif choice == "15":
                    self.show_metrics()
                elif choice == "16":
                    self.configure_limits()
                elif choice == "17":
                    self.handle_cleanup()
                elif choice == "18":
                    self.handle_check_sorted_units()
                elif choice == "19":
                    self.handle_analyze_detection_issues()
                
                else:
                    print("Неверный выбор. Попробуйте снова.")
                
                input("\nНажмите Enter для продолжения...")
            
            except KeyboardInterrupt:
                print("\n\nВыход...")
                break
            except Exception as e:
                print(f"\nОшибка: {e}")
                import traceback
                traceback.print_exc()
                input("\nНажмите Enter для продолжения...")


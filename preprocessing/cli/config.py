"""
Конфигурация CLI приложения.
"""

# Настройки меню
MENU_TITLE = "=== ПРЕПРОЦЕССИНГ ДОКУМЕНТОВ - CLI ТЕСТИРОВАНИЯ ==="
MENU_SEPARATOR = "=" * 60

# Категории меню с их пунктами
MENU_CATEGORIES = {
    "load": {
        "title": "ЗАГРУЗКА И ПОДГОТОВКА ДАННЫХ",
        "items": [
            "1. Синхронизация протоколов из MongoDB",
            "2. Скачивание протоколов за дату",
            "3. Проверка доступности файлов в INPUT_DIR"
        ]
    },
    "test": {
        "title": "ТЕСТИРОВАНИЕ ЭТАПОВ ПРЕПРОЦЕССИНГА",
        "items": [
            "4. ТЕСТ 1: Определение типа файла",
            "5. ТЕСТ 2: Распаковка архивов",
            "6. ТЕСТ 3: Нормализация unit'ов",
            "7. ТЕСТ 4: Создание manifest'ов",
            "8. ТЕСТ 5: Docling обработка"
        ]
    },
    "step": {
        "title": "ПОШАГОВАЯ ОБРАБОТКА",
        "items": [
            "9. ШАГ 1: Сканирование и детекция типов файлов",
            "10. ШАГ 2: Классификация файлов по категориям",
            "11. ШАГ 3: Проверка дубликатов",
            "12. ШАГ 4: Определение mixed units",
            "13. ШАГ 5: Распределение по pending директориям",
            "14. ПОЛНАЯ ОБРАБОТКА: Все шаги (1-5)"
        ]
    },
    "stats": {
        "title": "РАСШИРЕННАЯ СТАТИСТИКА",
        "items": [
            "15. Просмотр структуры pending директорий",
            "16. Детальная статистика по категориям",
            "17. Отчет по обработанным units"
        ]
    },
    "merge": {
        "title": "MERGE И ФИНАЛИЗАЦИЯ",
        "items": [
            "18. Merge (DRY RUN)",
            "19. Merge (РЕАЛЬНЫЙ)"
        ]
    },
    "pipeline": {
        "title": "ПОЛНОЕ ТЕСТИРОВАНИЕ PIPELINE",
        "items": [
            "20. ПОЛНЫЙ ТЕСТ: Весь pipeline (шаги 1-5)",
            "21. ИНТЕГРАЦИОННЫЙ ТЕСТ: Router API"
        ]
    },
    "monitor": {
        "title": "МОНИТОРИНГ И СТАТИСТИКА",
        "items": [
            "22. Просмотр текущих метрик сессии",
            "23. Просмотр логов обработки",
            "24. Статус MongoDB подключений"
        ]
    },
    "utils": {
        "title": "СЛУЖЕБНЫЕ ФУНКЦИИ",
        "items": [
            "25. Очистка тестовых данных",
            "26. Создание тестовых файлов",
            "27. Проверка инфраструктуры"
        ]
    }
}

# Маппинг номеров пунктов меню к категориям и функциям
MENU_MAPPING = {
    # Load handlers (1-3)
    1: ("load", "sync_protocols"),
    2: ("load", "download_protocols"),
    3: ("load", "check_input_files"),

    # Test handlers (4-8)
    4: ("test", "test_file_type_detection"),
    5: ("test", "test_archive_extraction"),
    6: ("test", "test_normalization"),
    7: ("test", "test_manifest_creation"),
    8: ("test", "test_docling_processing"),

    # Step handlers (9-14)
    9: ("step", "step1_scan_and_detect"),
    10: ("step", "step2_classify"),
    11: ("step", "step3_check_duplicates"),
    12: ("step", "step4_check_mixed"),
    13: ("step", "step5_distribute"),
    14: ("step", "full_processing"),

    # Stats handlers (15-17)
    15: ("stats", "view_pending_structure"),
    16: ("stats", "category_statistics"),
    17: ("stats", "units_report"),

    # Merge handlers (18-19)
    18: ("merge", "merge_dry_run"),
    19: ("merge", "merge_real"),

    # Pipeline handlers (20-21)
    20: ("pipeline", "full_pipeline_test"),
    21: ("pipeline", "integration_test"),

    # Monitor handlers (22-24)
    22: ("monitor", "view_metrics"),
    23: ("monitor", "view_logs"),
    24: ("monitor", "check_mongodb"),

    # Utils handlers (25-27)
    25: ("utils", "cleanup_test_data"),
    26: ("utils", "create_test_files"),
    27: ("utils", "check_infrastructure")
}

# Настройки CLI
CLI_SETTINGS = {
    "max_menu_choice": 27,
    "exit_choice": 0,
    "prompt_template": "\nВыберите действие [0-27]: "
}

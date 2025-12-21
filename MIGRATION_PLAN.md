# План миграции устаревших компонентов в архив

## Обзор

Этот документ описывает пошаговый план миграции устаревших компонентов из `preprocessing/router` в `archive/` после реализации эталонного решения в `final_preprocessing/docprep`.

## Этап 1: Подготовка (Завершено)

### Задачи:
- [x] Проведен анализ компонентов
- [x] Создана документация по миграции
- [x] Подготовлен план действий

## Этап 2: Создание архива

### Задачи:
- [x] Создать директорию `archive/preprocessing_router/`
- [x] Скопировать все содержимое `preprocessing/router/` в архив

```bash
# Создание архива
mkdir -p /root/winners_preprocessor/archive/preprocessing_router
cp -r /root/winners_preprocessor/preprocessing/router/* /root/winners_preprocessor/archive/preprocessing_router/
```

## Этап 3: Миграция устаревших CLI handlers

### Задачи:
- [ ] Переместить устаревшие handlers в архив
- [ ] Обновить конфигурацию CLI
- [ ] Проверить работоспособность

#### Файлы для перемещения:
```
preprocessing/cli/handlers/
├── test_handlers.py        → archive/preprocessing_cli/test_handlers.py
├── step_handlers.py         → archive/preprocessing_cli/step_handlers.py
├── stats_handlers.py        → archive/preprocessing_cli/stats_handlers.py
├── pipeline_handlers.py     → archive/preprocessing_cli/pipeline_handlers.py
├── merge_handlers.py        → archive/preprocessing_cli/merge_handlers.py
└── monitor_handlers.py      → archive/preprocessing_cli/monitor_handlers.py (частично)
```

#### Команды для выполнения:
```bash
# Создание архивной директории для CLI
mkdir -p /root/winners_preprocessor/archive/preprocessing_cli

# Копирование устаревших handlers
cp /root/winners_preprocessor/preprocessing/cli/handlers/test_handlers.py /root/winners_preprocessor/archive/preprocessing_cli/
cp /root/winners_preprocessor/preprocessing/cli/handlers/step_handlers.py /root/winners_preprocessor/archive/preprocessing_cli/
cp /root/winners_preprocessor/preprocessing/cli/handlers/stats_handlers.py /root/winners_preprocessor/archive/preprocessing_cli/
cp /root/winners_preprocessor/preprocessing/cli/handlers/pipeline_handlers.py /root/winners_preprocessor/archive/preprocessing_cli/
cp /root/winners_preprocessor/preprocessing/cli/handlers/merge_handlers.py /root/winners_preprocessor/archive/preprocessing_cli/
cp /root/winners_preprocessor/preprocessing/cli/handlers/monitor_handlers.py /root/winners_preprocessor/archive/preprocessing_cli/
```

## Этап 4: Обновление CLI конфигурации

### Задачи:
- [ ] Удалить ссылки на устаревшие handlers из `preprocessing/cli/config.py`
- [ ] Обновить меню CLI
- [ ] Проверить работоспособность

#### Изменения в config.py:
```python
# Удалить устаревшие категории
# Оставить только:
MENU_CATEGORIES = {
    "load": {
        "title": "ЗАГРУЗКА И ПОДГОТОВКА ДАННЫХ",
        "items": [
            "1. Синхронизация протоколов из MongoDB",
            "2. Скачивание протоколов за дату",
            "3. Проверка доступности файлов в INPUT_DIR"
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

# Обновить маппинг
MENU_MAPPING = {
    # Load handlers (1-3)
    1: ("load", "sync_protocols"),
    2: ("load", "download_protocols"),
    3: ("load", "check_input_files"),

    # Utils handlers (25-27)
    25: ("utils", "cleanup_test_data"),
    26: ("utils", "create_test_files"),
    27: ("utils", "check_infrastructure")
}
```

## Этап 5: Обновление документации

### Задачи:
- [ ] Обновить README.md
- [ ] Добавить уведомления об устаревших компонентах
- [ ] Обновить техническую документацию

## Этап 6: Тестирование

### Задачи:
- [ ] Проверить работоспособность sync_db
- [ ] Проверить работоспособность downloader
- [ ] Проверить работоспособность scheduler
- [ ] Проверить работоспособность CLI
- [ ] Проверить зависимости

## Этап 7: Уведомление команды

### Задачи:
- [ ] Отправить уведомление о миграции
- [ ] Обновить внутреннюю документацию
- [ ] Провести обучение (при необходимости)

## Откат изменений

В случае проблем можно выполнить откат:

```bash
# Восстановление router компонента
cp -r /root/winners_preprocessor/archive/preprocessing_router/* /root/winners_preprocessor/preprocessing/router/

# Восстановление CLI handlers
cp /root/winners_preprocessor/archive/preprocessing_cli/* /root/winners_preprocessor/preprocessing/cli/handlers/

# Восстановление конфигурации
# Вернуть предыдущую версию preprocessing/cli/config.py
```

## Проверка успешности миграции

### Критерии успеха:
1. [ ] Все активные компоненты (sync_db, downloader, scheduler) работают корректно
2. [ ] CLI корректно отображает только актуальные пункты меню
3. [ ] Устаревшие компоненты находятся в архиве
4. [ ] Нет критических зависимостей от удаленных компонентов
5. [ ] Документация обновлена

## Заключение

После завершения миграции структура проекта станет более чистой и понятной:
- `preprocessing/` будет содержать только компоненты для загрузки и синхронизации данных
- `final_preprocessing/docprep/` будет содержать эталонное решение для обработки документов
- Устаревшие компоненты будут сохранены в архиве для возможного восстановления

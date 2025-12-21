# Анализ компонентов Preprocessing - Что оставить, что переместить в архив

## Обзор

После реализации эталонного компонента `final_preprocessing/docprep`, который заменяет функциональность `preprocessing/router`, необходимо провести анализ компонентов в `preprocessing` и определить, какие из них можно переместить в архив как устаревшие.

## Компоненты, которые НУЖНО ОСТАВИТЬ

### 1. preprocessing/downloader
**Статус: АКТИВЕН**
- Отвечает за загрузку протоколов с zakupki.gov.ru через VPN
- Не дублируется в final_preprocessing/docprep
- Критически важен для получения исходных данных

### 2. preprocessing/sync_db
**Статус: АКТИВЕН**
- Отвечает за синхронизацию коллекции протоколов из удаленной MongoDB в локальную
- Не дублируется в final_preprocessing/docprep
- Критически важен для подготовки данных к обработке

### 3. preprocessing/scheduler
**Статус: АКТИВЕН**
- Отвечает за планирование и автоматический запуск задач
- Управляет cron-задачами для синхронизации и обработки
- Не дублируется в final_preprocessing/docprep

## Компоненты, которые МОЖНО ПЕРЕМЕСТИТЬ В АРХИВ

### 4. preprocessing/router (ПОЛНОСТЬЮ)
**Статус: УСТАРЕЛ**
- **Причина**: Полностью заменен `final_preprocessing/docprep`
- **Функциональность перенесена**:
  - Классификация файлов → `final_preprocessing/docprep/engine/classifier.py`
  - Конвертация → `final_preprocessing/docprep/engine/converter.py`
  - Извлечение из архивов → `final_preprocessing/docprep/engine/extractor.py`
  - Нормализация → `final_preprocessing/docprep/engine/normalizers/`
  - Объединение файлов → `final_preprocessing/docprep/engine/merger.py`
  - State machine → `final_preprocessing/docprep/core/state_machine.py`
  - Manifest v2 → `final_preprocessing/docprep/core/manifest.py`
  - Метрики и аудит → `final_preprocessing/docprep/core/audit.py`

**Файлы для перемещения**:
```
preprocessing/router/
├── api.py                 # Заменено CLI в final_preprocessing
├── archive.py             # Заменено engine/ в final_preprocessing
├── config.py               # Заменено core/config.py в final_preprocessing
├── cycle_manager.py        # Заменено cli/cycle.py в final_preprocessing
├── duplicate_detection.py   # Заменено engine/validator.py в final_preprocessing
├── exceptions_handler.py    # Заменено core/error_policy.py в final_preprocessing
├── file_classifier.py      # Заменено engine/classifier.py в final_preprocessing
├── file_detection.py       # Заменено engine/classifier.py в final_preprocessing
├── iterative_processor.py   # Заменено core/unit_processor.py в final_preprocessing
├── manifest.py             # Заменено core/manifest.py в final_preprocessing
├── merge_cluster.py        # Заменено engine/merger.py в final_preprocessing
├── merge.py                # Заменено engine/merger.py в final_preprocessing
├── metrics.py              # Заменено core/audit.py в final_preprocessing
├── mixed_unit_handler.py    # Заменено engine/classifier.py в final_preprocessing
├── processing.py           # Заменено core/unit_processor.py в final_preprocessing
├── state_machine.py        # Заменено core/state_machine.py в final_preprocessing
├── state_manager.py        # Заменено core/state_machine.py в final_preprocessing
├── unit_distribution_new.py # Заменено engine/classifier.py в final_preprocessing
├── utils.py               # Заменено utils/ в final_preprocessing
└── core/                  # Полностью заменено core/ в final_preprocessing
```

### 5. preprocessing/cli (ЧАСТИЧНО)
**Статус: ЧАСТИЧНО УСТАРЕЛ**
- **Функциональность по обработке файлов**: УСТАРЕЛА (заменена `final_preprocessing/docprep/cli/`)
- **Функциональность по синхронизации и загрузке**: АКТИВНА

**Файлы для перемещения**:
```
preprocessing/cli/handlers/
├── test_handlers.py        # Заменено тестами в final_preprocessing
├── step_handlers.py        # Заменено cli/stage.py в final_preprocessing
├── stats_handlers.py       # Заменено cli/stats.py в final_preprocessing
├── pipeline_handlers.py    # Заменено cli/pipeline.py в final_preprocessing
├── merge_handlers.py       # Заменено cli/merge.py в final_preprocessing
└── monitor_handlers.py     # Частично актуальны, частично устарели
```

**Файлы для сохранения**:
```
preprocessing/cli/handlers/
├── load_handlers.py        # Работа с sync_db и downloader - АКТИВЕН
└── utils_handlers.py      # Инфраструктурные проверки - АКТИВЕН
```

## Рекомендации по миграции

### Немедленные действия:
1. **Создать архивную директорию**: `archive/preprocessing_router/`
2. **Переместить router компонент**: Полностью скопировать `preprocessing/router/` в архив
3. **Переместить устаревшие CLI handlers**: Часть `preprocessing/cli/handlers/`

### Постепенные действия:
1. **Обновить CLI конфигурацию**: Удалить ссылки на устаревшие handlers
2. **Обновить документацию**: Отметить устаревшие компоненты
3. **Обновить зависимости**: Удалить неиспользуемые зависимости

## Преимущества миграции

1. **Упрощение архитектуры**: Устранение дублирующихся компонентов
2. **Снижение поддержки**: Меньше кода для поддержки
3. **Улучшенная стабильность**: Использование единого эталонного решения
4. **Более четкое разделение ответственности**: 
   - `preprocessing` - только загрузка и синхронизация
   - `final_preprocessing/docprep` - только обработка

## План действий

### Этап 1: Подготовка (1 день)
- [x] Создать архивную директорию
- [x] Задокументировать текущее состояние

### Этап 2: Миграция router (2 дня)
- [ ] Переместить `preprocessing/router/` в `archive/preprocessing_router/`
- [ ] Обновить документацию
- [ ] Проверить зависимости

### Этап 3: Миграция CLI handlers (1 день)
- [ ] Переместить устаревшие handlers в архив
- [ ] Обновить CLI конфигурацию
- [ ] Проверить работоспособность

### Этап 4: Финальная проверка (1 день)
- [ ] Тестирование всех активных компонентов
- [ ] Обновление документации
- [ ] Уведомление команды о изменениях

## Заключение

После реализации `final_preprocessing/docprep` компонент `preprocessing/router` стал полностью избыточным и может быть перемещен в архив. Однако компоненты `preprocessing/downloader`, `preprocessing/sync_db` и `preprocessing/scheduler` остаются критически важными для получения и подготовки исходных данных.

Рекомендуется немедленно начать процесс миграции устаревших компонентов в архив для упрощения архитектуры и снижения нагрузки по поддержке.

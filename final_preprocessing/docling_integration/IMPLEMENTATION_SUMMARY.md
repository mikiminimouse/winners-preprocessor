# Сводка реализации: Contract-only архитектура

## Статус: ✅ ВЫПОЛНЕНО

**Дата:** 2026-01-16
**Версия:** 1.1.0

---

## Обновление 1.1.0: Оптимизация производительности

### Изменения в config.py
- Функция `_build_options_from_template()` теперь применяет **ВСЕ** настройки из YAML:
  - `models.layout` - управление layout detection
  - `models.tables` - управление table extraction
  - `models.ocr` - настройки OCR
  - `docling.images_scale` - масштаб изображений
  - `docling.generate_page_images` / `generate_picture_images`
  - `docling.extract_tables`

### Оптимизированный pdf_text.yaml
- `layout: off` - отключена модель publaynet_detectron2
- `tables: off` - отключен table-transformer
- `extract_tables: false` - отключено извлечение таблиц
- `images_scale: 0.5` - уменьшен масштаб
- `max_runtime_sec: 60` - уменьшен timeout

### Новый pdf_text_tables.yaml
Для документов с таблицами:
- `layout: publaynet_detectron2` - включено
- `tables: table-transformer` - включено
- `extract_tables: true` - включено

### Улучшенное логирование (runner.py)
Добавлено логирование применяемых PDF опций для диагностики:
```
[pdf_text] Table extraction DISABLED (tables=False, extract_tables=False)
[pdf_text] Layout detection DISABLED
[pdf_text] PDF options: do_ocr=False, do_table_structure=False
```

### Результаты тестирования (2026-01-16)

| Формат | Кол-во | Success | Время avg |
|--------|--------|---------|-----------|
| DOCX | 17 | 100% | **0.16 сек** |
| XLSX | 1 | 100% | **0.34 сек** |
| PDF (digital) | 5 | 100% | ~68 сек* |
| Image OCR | 3 | 100% | 107 сек |

*PDF время зависит от размера документа: от 12 сек (маленькие) до 200 сек (большие)

### Известные ограничения
1. Docling загружает OCR/layout модели при инициализации даже если они отключены
2. XML формат (ODF) не поддерживается напрямую
3. Сканированные PDF требуют OCR и медленны на CPU

---

## Ключевые изменения

### 1. Переименование contract файла

**Было:** `manifest.contract.json`  
**Стало:** `docprep.contract.json`

**Изменено в файлах:**
- `docprep/core/contract.py`
- `docprep/engine/merger.py`
- `docling/bridge_docprep.py`
- `docling/tests/test_contract_integration.py`

---

### 2. Удаление использования manifest.json как входа для Docling

**Критическое изменение:** Docling использует **ТОЛЬКО** `docprep.contract.json`

#### Изменения в `bridge_docprep.py`:
- ❌ Удален fallback на `manifest.json`
- ❌ Удален импорт `load_manifest`
- ❌ Удалена функция `_determine_route_from_path()`
- ✅ Добавлена строгая проверка наличия contract
- ✅ Явная ошибка при отсутствии contract

#### Изменения в `pipeline.py`:
- ❌ Убрана логика выбора между contract и manifest
- ✅ Использование только contract для всех метаданных

#### Изменения в `exporters/mongodb.py`:
- ❌ Параметр `manifest` заменен на `contract`
- ✅ Все данные извлекаются из contract

---

## Результаты тестирования

### Unit тесты

```
============================================================
Testing Contract Integration
============================================================
✓ Contract generation test passed
✓ Contract route validation test passed (route: pdf_text)
✓ Cost estimation for pdf_text: 20s, $0.000278
✓ Cost estimation for pdf_scan: 90s, $0.001250
✓ Cost estimation for pdf_scan_table: 230s, $0.003194
✓ Cost estimation for image_ocr: 125s, $0.001736
✓ Cost estimation for docx: 5s, $0.000069
✓ Contract absence correctly raises error
✓ Bridge loads contract successfully
============================================================
All tests passed!
============================================================
```

**Статус:** ✅ Все тесты прошли успешно

---

## Архитектурные принципы

### Контрактная строгость

1. **DocPrep генерирует contract** в merger.py
2. **Docling использует ТОЛЬКО contract** для обработки
3. **manifest.json не используется** Docling как вход
4. **Route никогда не "mixed"** в Ready2Docling

### Разделение ответственности

- **DocPrep:** Генерация contract, валидация route
- **Docling:** Использование contract, обработка документа
- **Contract:** Единственный источник истины для Docling

---

## Проверка корректности

### ✅ Линтер
- Нет ошибок линтера
- Все импорты корректны
- Нет циклических зависимостей

### ✅ Тесты
- Все unit тесты проходят
- Интеграционные тесты работают
- Валидация route работает корректно

### ✅ Именование
- Все упоминания обновлены
- Нет старых имен в коде
- Комментарии актуальны

---

## Важные замечания

1. **Contract обязателен:** Без contract UNIT не может быть обработан Docling
2. **Генерация автоматическая:** Merger автоматически генерирует contract
3. **Валидация многоуровневая:** Route проверяется на всех этапах
4. **Обратная совместимость:** DocPrep работает как раньше, изменения только для Docling

---

## Следующие шаги

1. ✅ Все изменения выполнены
2. ✅ Все тесты пройдены
3. ⏳ Мониторинг в продакшене
4. ⏳ Обновление документации (если нужно)

**Готовность к использованию:** ✅ ДА


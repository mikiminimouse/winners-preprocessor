# Миграция на Granite-Docling Remote API

## Обзор

Данная документация описывает миграцию с SmolDocling на **Granite-Docling Remote API** для извлечения метаданных из протоколов закупок.

## Что изменилось

### 1. API Endpoint

**Старый (SmolDocling):**
```python
BASE_URL = "https://d63e30af-085a-49f0-9724-8162da967af2.modelrun.inference.cloud.ru/v1"
MODEL_NAME = "model-run-4qigw-disease"
```

**Новый (Granite-Docling):**
```python
BASE_URL = "https://8cb66180-db3a-4963-8068-51f87e716259.modelrun.inference.cloud.ru/v1"
MODEL_NAME = "granite-docling"
```

### 2. Промпт для извлечения структуры

**Старый (JSON-промпт):**
```python
prompt = f"""Extract ALL text and tables from this document page {page_num} in structured JSON format.

Your response MUST be a valid JSON object with this structure:
{{
  "full_text": "...",
  "tables": [...]
}}
...
"""
```

**Новый (Granite-Docling промпт):**
```python
prompt = "Convert this page to docling."
```

Согласно [документации Granite-Docling](https://huggingface.co/ibm-granite/granite-docling-258M), это стандартный промпт для конвертации.

### 3. Формат ответа

**Старый:** JSON
**Новый:** DocTags (SGML-подобный формат)

Пример DocTags:
```
<loc_59><loc_46><loc_195><loc_53>Текст здесь</loc_53></loc_195></loc_46></loc_59>
<text>Еще текст</text>
<table>...</table>
```

### 4. Парсинг DocTags

Добавлен новый метод `parse_doctags_to_structure()` который:
- Извлекает текст из тегов
- Находит таблицы
- Конвертирует в структурированный формат

### 5. Лимиты токенов

Granite-Docling имеет лимит **8192 токена** для контекста.

При извлечении метаданных:
- Промпт: ~1500 токенов
- Completion: 2000 токенов  
- Остается: ~4700 токенов для текста
- Ограничиваем входной текст до **3000 символов** (~750 токенов)

## Новые файлы

### 1. `granite_docling_extractor.py`

Основной скрипт с обновленной логикой:
- Подключение к Granite-Docling API
- Промпт "Convert this page to docling."
- Парсинг DocTags формата
- Извлечение метаданных
- Последовательная обработка файлов

### 2. `test_granite_docling_remote.py`

Тестовый скрипт для одного файла:
- Проверка подключения
- Обработка 1 PDF (первые 2 страницы)
- Детальные логи
- Анализ результата

### 3. `test_granite_batch.py`

Тестовый скрипт для 3-5 файлов:
- Пакетная обработка
- Задержка между файлами
- Статистика

## Использование

### Тест на 1 файле

```bash
cd /root/winners_preprocessor
python3 test_granite_docling_remote.py
```

### Тест на 3-5 файлах

```bash
python3 test_granite_batch.py
```

### Обработка своих файлов

```bash
python3 granite_docling_extractor.py file1.pdf file2.pdf
```

или

```bash
python3 granite_docling_extractor.py /path/to/directory/
```

## Результаты

Для каждого PDF создается 3 файла:

1. **`{filename}_full_result.json`** - полный результат с:
   - Текстом по страницам
   - DocTags (сырой формат)
   - Метаданными
   - Статистикой

2. **`{filename}_metadata.json`** - только метаданные:
   ```json
   {
     "номер_процедуры": "...",
     "победитель": "...",
     "ИНН": "...",
     ...
   }
   ```

3. **`{filename}_report.md`** - читаемый отчет

## Известные проблемы и решения

### Проблема 1: "Зацикливание" на одной фразе

**Решение:** Использовать точный промпт "Convert this page to docling." вместо длинного JSON-промпта.

### Проблема 2: Лимит токенов при извлечении метаданных

**Ошибка:**
```
Error code: 400 - Requested token count exceeds the model's maximum context length
```

**Решение:**
- Ограничить входной текст до 3000 символов
- Уменьшить `max_tokens` для completion до 2000

### Проблема 3: Ответ не в JSON формате (DocTags)

**Решение:**
- DocTags это нормальный формат для Granite-Docling
- Используйте `parse_doctags_to_structure()` для парсинга

### Проблема 4: "Extra data" при парсинге JSON метаданных

**Причина:** Модель возвращает текст до/после JSON

**Решение:** Добавить очистку ответа перед парсингом:
```python
response_text = response.choices[0].message.content
# Найти JSON в ответе
json_start = response_text.find('{')
json_end = response_text.rfind('}') + 1
if json_start != -1 and json_end > json_start:
    response_text = response_text[json_start:json_end]
metadata = json.loads(response_text)
```

## Производительность

На основе тестов:

| Метрика | Granite-Docling |
|---------|-----------------|
| Время на страницу | ~30 сек |
| Токенов на страницу | ~8000 |
| Качество OCR | ✅ Хорошее (DocTags) |
| Извлечение текста | ✅ Работает |
| Извлечение таблиц | ⚠️ Требует доработки |

**Оценка для продакшена:**
- 1 файл (1 страница): ~30-40 сек
- 10 файлов: ~6-8 мин
- 100 файлов: ~60-80 мин
- 500 файлов: ~5-7 часов

## Сравнение: SmolDocling vs Granite-Docling

| Параметр | SmolDocling | Granite-Docling |
|----------|-------------|-----------------|
| **Endpoint** | d63e30af-085a... | 8cb66180-db3a... |
| **Промпт** | Длинный JSON | "Convert this page to docling." |
| **Формат ответа** | JSON (с ошибками) | DocTags (стабильно) |
| **Проблема "зацикливания"** | ❌ Да | ✅ Нет |
| **Лимит токенов** | ? | 8192 |
| **Качество OCR** | ⚠️ Среднее | ✅ Хорошее |
| **Документация** | ❌ Нет | ✅ [HuggingFace](https://huggingface.co/ibm-granite/granite-docling-258M) |

## Рекомендации

### Для продакшена

1. **Используйте `granite_docling_extractor.py`** вместо старого скрипта
2. **Обрабатывайте файлы последовательно** с задержкой `delay_between=1.0`
3. **Ограничьте страницы** для теста (`max_pages=2`)
4. **Мониторьте лимиты токенов** - если документ большой, обрабатывайте по частям

### Для больших документов

Если PDF имеет много страниц (>5):
- Обрабатывайте каждую страницу отдельно
- Объединяйте результаты
- Используйте пакетную обработку с задержками

### Оптимизация

Для ускорения:
- Уменьшите DPI: `dpi=200` вместо `300`
- Уменьшите max_size: `max_size=1536` вместо `2048`
- Обрабатывайте только важные страницы

## Checklist миграции

- [ ] Обновлен endpoint и model_name
- [ ] Промпт изменен на "Convert this page to docling."
- [ ] Добавлен парсер DocTags
- [ ] Ограничен входной текст (3000 символов)
- [ ] Уменьшен max_tokens (2000)
- [ ] Протестировано на 1 файле
- [ ] Протестировано на 3-5 файлах
- [ ] Проверена последовательная обработка
- [ ] Документация создана

## Полезные ссылки

- [Granite-Docling на HuggingFace](https://huggingface.co/ibm-granite/granite-docling-258M)
- [Docling Documentation](https://docling-project.github.io/docling/)
- [Granite-Docling Demo](https://huggingface.co/spaces/ibm-granite/granite-docling-258m-demo)

## Контакты и поддержка

При возникновении проблем:
1. Проверьте логи в консоли
2. Посмотрите raw_doctags в результатах
3. Проверьте лимиты токенов
4. Убедитесь что endpoint доступен

---

**Дата:** 2025-12-01  
**Версия:** 1.0  
**Статус:** ✅ Готово к использованию



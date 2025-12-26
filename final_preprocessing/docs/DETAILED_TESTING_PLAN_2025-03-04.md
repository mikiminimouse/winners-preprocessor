# Детальный план пошагового тестирования пайплайна docprep для Data/2025-03-04

## 🎯 Цель тестирования

Провести детальное тестирование пайплайна docprep на датасете 2025-03-04 для подтверждения корректности:
1. Классификации всех 6125 UNIT
2. Обработки по циклам 1→2→3
3. Корректного распределения по категориям (convert, extract, normalize, direct)
4. Отсутствия потерь данных
5. Соответствия документации и best practices

## 📋 Общая информация о датасете

- **Дата**: 2025-03-04
- **Всего UNIT**: 6125
- **Статус**: Чистый, без предыдущих обработок
- **Структура**: Input/ содержит все исходные UNIT

## 🧪 Этап 1: Подготовка и проверка исходных данных

### 1.1 Проверка целостности Input

```bash
# Подсчет общего количества UNIT
find /root/winners_preprocessor/final_preprocessing/Data/2025-03-04/Input -maxdepth 1 -type d -name "UNIT_*" | wc -l

# Создание эталонного списка UNIT
find /root/winners_preprocessor/final_preprocessing/Data/2025-03-04/Input -maxdepth 1 -type d -name "UNIT_*" | sort > /tmp/input_units_2025-03-04.txt

# Сбор статистики по расширениям файлов
python3 -m docprep.utils.statistics collect-input-stats /root/winners_preprocessor/final_preprocessing/Data/2025-03-04/Input
```

### 1.2 Инициализация структуры директорий

Уже выполнено: структура создана корректно.

## 🔄 Этап 2: Пошаговое тестирование (Цикл 1)

### 2.1 Тест классификации (dry-run)

```bash
# Тест классификации в режиме dry-run для проверки логики
cd /root/winners_preprocessor/final_preprocessing
python3 -m docprep.cli.main stage classifier \
  --cycle 1 \
  --input Data/2025-03-04/Input \
  --date 2025-03-04 \
  --dry-run \
  --verbose

# Проверка, что ничего не переместилось
find Data/2025-03-04/Processing/Processing_1 -type d -name "UNIT_*" 2>/dev/null | wc -l
```

### 2.2 Реальная классификация небольшой выборки

```bash
# Создание тестовой выборки из 10 UNIT
mkdir -p /tmp/test_sample_2025-03-04
find Data/2025-03-04/Input -maxdepth 1 -type d -name "UNIT_*" | head -10 | xargs -I {} cp -r {} /tmp/test_sample_2025-03-04/

# Классификация тестовой выборки
python3 -m docprep.cli.main stage classifier \
  --cycle 1 \
  --input /tmp/test_sample_2025-03-04 \
  --date 2025-03-04 \
  --verbose

# Проверка результатов
echo "=== Результаты классификации тестовой выборки ==="
find Data/2025-03-04/Processing/Processing_1 -type d -name "UNIT_*" | wc -l
find Data/2025-03-04/Processing/Processing_1 -type d -name "UNIT_*" | head -5

# Проверка manifest.json
find Data/2025-03-04/Processing/Processing_1 -name "manifest.json" | head -1 | xargs cat | python3 -m json.tool | grep -E "(current_state|route|category)"

# Проверка распределения по категориям
echo "=== Распределение по категориям ==="
find Data/2025-03-04/Processing/Processing_1/Convert -type d -name "UNIT_*" 2>/dev/null | wc -l && echo "Convert"
find Data/2025-03-04/Processing/Processing_1/Extract -type d -name "UNIT_*" 2>/dev/null | wc -l && echo "Extract"
find Data/2025-03-04/Processing/Processing_1/Normalize -type d -name "UNIT_*" 2>/dev/null | wc -l && echo "Normalize"
find Data/2025-03-04/Merge/Merge_0/Direct -type d -name "UNIT_*" 2>/dev/null | wc -l && echo "Direct"
find Data/2025-03-04/Exceptions/Exceptions_1 -type d -name "UNIT_*" 2>/dev/null | wc -l && echo "Exceptions"
```

### 2.3 Полная классификация всех UNIT

```bash
# Классификация всех 6125 UNIT
python3 -m docprep.cli.main stage classifier \
  --cycle 1 \
  --input Data/2025-03-04/Input \
  --date 2025-03-04 \
  --verbose

# Статистика после классификации
python3 -m docprep.cli.main utils stats Data/2025-03-04/Processing/Processing_1 --verbose

# Проверка распределения по категориям
echo "=== Полное распределение по категориям ==="
convert_count=$(find Data/2025-03-04/Processing/Processing_1/Convert -type d -name "UNIT_*" 2>/dev/null | wc -l)
extract_count=$(find Data/2025-03-04/Processing/Processing_1/Extract -type d -name "UNIT_*" 2>/dev/null | wc -l)
normalize_count=$(find Data/2025-03-04/Processing/Processing_1/Normalize -type d -name "UNIT_*" 2>/dev/null | wc -l)
direct_count=$(find Data/2025-03-04/Merge/Merge_0/Direct -type d -name "UNIT_*" 2>/dev/null | wc -l)
exceptions_count=$(find Data/2025-03-04/Exceptions/Exceptions_1 -type d -name "UNIT_*" 2>/dev/null | wc -l)

echo "Convert: $convert_count"
echo "Extract: $extract_count"
echo "Normalize: $normalize_count"
echo "Direct: $direct_count"
echo "Exceptions: $exceptions_count"
echo "Всего: $((convert_count + extract_count + normalize_count + direct_count + exceptions_count))"
```

### 2.4 Валидация классификации

```bash
# Запуск нашего валидационного скрипта
python3 scripts/validate_classification.py --date 2025-03-04 --base-dir Data
```

## 🔧 Этап 3: Тестирование обработки (Цикл 1)

### 3.1 Обработка конвертации

```bash
# Тест конвертации (dry-run)
python3 -m docprep.cli.main substage convert run \
  --input Data/2025-03-04/Processing/Processing_1/Convert \
  --cycle 1 \
  --date 2025-03-04 \
  --dry-run \
  --verbose

# Реальная конвертация
python3 -m docprep.cli.main substage convert run \
  --input Data/2025-03-04/Processing/Processing_1/Convert \
  --cycle 1 \
  --date 2025-03-04 \
  --verbose

# Проверка результатов
find Data/2025-03-04/Merge/Merge_1/Converted -type d -name "UNIT_*" | wc -l
```

### 3.2 Обработка архивов

```bash
# Тест извлечения архивов (dry-run)
python3 -m docprep.cli.main substage extract run \
  --input Data/2025-03-04/Processing/Processing_1/Extract \
  --cycle 1 \
  --date 2025-03-04 \
  --dry-run \
  --verbose

# Реальное извлечение
python3 -m docprep.cli.main substage extract run \
  --input Data/2025-03-04/Processing/Processing_1/Extract \
  --cycle 1 \
  --date 2025-03-04 \
  --verbose

# Проверка результатов
find Data/2025-03-04/Merge/Merge_1/Extracted -type d -name "UNIT_*" | wc -l
```

### 3.3 Обработка нормализации

```bash
# Тест нормализации (dry-run)
python3 -m docprep.cli.main substage normalize run \
  --input Data/2025-03-04/Processing/Processing_1/Normalize \
  --cycle 1 \
  --date 2025-03-04 \
  --dry-run \
  --verbose

# Реальная нормализация
python3 -m docprep.cli.main substage normalize run \
  --input Data/2025-03-04/Processing/Processing_1/Normalize \
  --cycle 1 \
  --date 2025-03-04 \
  --verbose

# Проверка результатов
find Data/2025-03-04/Merge/Merge_1/Normalized -type d -name "UNIT_*" | wc -l
```

## 🔀 Этап 4: Тестирование Merge (Цикл 1)

### 4.1 Перемещение в Merge_1

```bash
# Перемещение всех результатов в Merge_1
python3 -m docprep.cli.main stage merge \
  --cycle 1 \
  --source-base Data/2025-03-04 \
  --target-base Data/2025-03-04 \
  --date 2025-03-04 \
  --verbose

# Проверка результатов
find Data/2025-03-04/Merge/Merge_1 -type d -name "UNIT_*" | wc -l
```

## 🔄 Этап 5: Тестирование полного цикла

### 5.1 Запуск одного полного цикла

```bash
# Запуск цикла 1 (классификация + обработка + merge)
python3 -m docprep.cli.main cycle run 1 \
  --input Data/2025-03-04/Input \
  --date 2025-03-04 \
  --verbose

# Проверка результатов
echo "=== Результаты цикла 1 ==="
python3 -m docprep.cli.main utils stats Data/2025-03-04/Merge/Merge_1 --verbose
```

### 5.2 Запуск всех 3 циклов

```bash
# Полный pipeline (3 цикла подряд)
python3 -m docprep.cli.main pipeline run \
  Data/2025-03-04/Input \
  Data/2025-03-04/Ready2Docling \
  --max-cycles 3 \
  --verbose

# Проверка результатов
find Data/2025-03-04/Ready2Docling -type d -name "UNIT_*" | wc -l
```

## 📊 Этап 6: Финальная валидация

### 6.1 Проверка баланса файлов

```bash
# Проверка, что все UNIT учтены
input_count=$(find Data/2025-03-04/Input -maxdepth 1 -type d -name "UNIT_*" | wc -l)
ready_count=$(find Data/2025-03-04/Ready2Docling -type d -name "UNIT_*" | wc -l)
exceptions_count=$(find Data/2025-03-04/Exceptions -type d -name "UNIT_*" | wc -l)

echo "Input: $input_count"
echo "Ready2Docling: $ready_count"
echo "Exceptions: $exceptions_count"
echo "Баланс: $((ready_count + exceptions_count)) из $input_count"
```

### 6.2 Запуск валидационного скрипта

```bash
# Полная валидация
python3 scripts/validate_classification.py --date 2025-03-04 --base-dir Data
```

### 6.3 Генерация финального отчета

```bash
# Сбор статистики
python3 -m docprep.utils.statistics generate-report 2025-03-04 Data/2025-03-04/Input Data/2025-03-04/Ready2Docling
```

## 🧪 Специальные тесты для проверки рефакторинга

### Тест 1: Проверка идемпотентности

```bash
# Повторный запуск классификации на уже обработанных данных
# Должен показать, что все UNIT уже классифицированы
python3 -m docprep.cli.main stage classifier \
  --cycle 1 \
  --input Data/2025-03-04/Input \
  --date 2025-03-04 \
  --dry-run \
  --verbose
```

### Тест 2: Проверка обработки смешанных UNIT

```bash
# Поиск и анализ смешанных UNIT
find Data/2025-03-04/Exceptions/Exceptions_1/Mixed -type d -name "UNIT_*" | head -5
for unit in $(find Data/2025-03-04/Exceptions/Exceptions_1/Mixed -type d -name "UNIT_*" | head -3); do
  echo "=== UNIT: $(basename $unit) ==="
  cat "$unit/manifest.json" | python3 -m json.tool | grep -E "(files|applied_operations|processing)"
done
```

### Тест 3: Проверка маршрутизации PDF

```bash
# Проверка правильной сортировки PDF файлов
find Data/2025-03-04/Ready2Docling/pdf/text -type d -name "UNIT_*" | wc -l
find Data/2025-03-04/Ready2Docling/pdf/scan -type d -name "UNIT_*" | wc -l
find Data/2025-03-04/Ready2Docling/pdf/mixed -type d -name "UNIT_*" | wc -l
```

## 📋 Чеклист тестирования

- [ ] Инициализация структуры директорий ✅
- [ ] Классификация UNIT (dry-run)
- [ ] Классификация UNIT (реальная)
- [ ] Обработка convert
- [ ] Обработка archives
- [ ] Обработка normalize
- [ ] Перемещение в Merge
- [ ] Полный цикл 1
- [ ] Полный цикл 2
- [ ] Полный цикл 3
- [ ] Merge в Ready2Docling
- [ ] Проверка сортировки PDF (scan/text/mixed)
- [ ] Валидация UNIT
- [ ] Проверка audit log
- [ ] Проверка manifest
- [ ] Проверка баланса файлов
- [ ] Проверка идемпотентности
- [ ] Проверка обработки смешанных UNIT
- [ ] Генерация финального отчета

## ⚠️ Возможные проблемы и решения

### Проблема 1: Ошибки LibreOffice
**Решение:** Убедиться, что LibreOffice установлен и доступен в PATH

### Проблема 2: Ошибки извлечения архивов
**Решение:** Проверить наличие необходимых библиотек (py7zr, rarfile)

### Проблема 3: Проблемы с правами доступа
**Решение:** Проверить права на запись в директории

### Проблема 4: Ошибки маршрутизации
**Решение:** Проверить логику в routing.py и manifest.json
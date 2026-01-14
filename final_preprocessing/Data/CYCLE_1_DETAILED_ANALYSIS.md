# Детальный Анализ: Цикл 1 (Cycle 1)

**Дата анализа:** 2026-01-14
**Сопоставление:** Web UI (ProcessingControl.tsx) ↔ Backend (docprep/classifier.py)

---

## 1. Описание Цикла 1 в Web UI

**Источник:** `/webui_docprep/components/ProcessingControl.tsx`

```typescript
cycle1: {
  id: 'cycle1',
  title: 'Cycle 1: Ingestion & Classify',
  description: 'Magic byte detection and initial routing of raw Input.',
  source: 'Input',
  stages: ['classification', 'distribution'],
  outputs: {
    merge: 'Rady2Merge/Direct',
    next: 'Processing/Processing_1',
    exception: 'Exceptions/Exceptions_1'
  }
}
```

### Визуальная схема (Web UI):

```
Input (RAW)
   ↓
┌──────────────────┐
│ Classification   │ ← Magic Byte Detection & Type Recognition
└──────────────────┘
   ↓
┌──────────────────┐
│  Distribution    │ ← Routing to targets
└──────────────────┘
   ↓
   ├─→ Rady2Merge/Direct        (готовые файлы)
   ├─→ Processing/Processing_1  (требуют обработки)
   └─→ Exceptions/Exceptions_1  (ошибки/спец.файлы)
```

---

## 2. Реальная Реализация в Backend

**Источник:** `/docprep/engine/classifier.py`

### 2.1. Точка входа

**Метод:** `Classifier.classify_unit()`

**Параметры:**
- `unit_path`: Путь к UNIT в Input директории
- `cycle`: 1 (для первого цикла)
- `protocol_date`: Дата протокола (опционально)
- `protocol_id`: ID протокола (опционально)
- `dry_run`: Режим предпросмотра (без изменений)
- `copy_mode`: Копировать вместо перемещения (для Input автоматически True)

### 2.2. Пошаговый процесс

#### ШАГ 1: Чтение файлов из UNIT

```python
files = get_unit_files(unit_path)  # Получаем все файлы кроме системных
```

**Исключения:**
- `manifest.json`
- `audit.log.jsonl`
- `unit.meta.json`
- `docprep.contract.json`

#### ШАГ 2: Обработка пустых UNIT

```python
if not files:
    # → Exceptions/Exceptions_1/Empty/
    state = UnitState.EXCEPTION_1
```

**Маршрут:** `Data/{date}/Exceptions/Exceptions_1/Empty/`
**State:** `EXCEPTION_1`
**Причина:** "empty_unit"

---

#### ШАГ 3: Классификация каждого файла

**Метод:** `_classify_file(file_path)`

**Логика классификации:**

| Условие | Категория | Действие |
|---------|-----------|----------|
| `.sig`, `.p7s`, `.pem` | `special` | → Exceptions/Special |
| `.exe`, `.dll`, `.tmp` | `special` | → Exceptions/Special |
| `.zip`, `.rar`, `.7z` | `extract` | → Processing_1/Extract |
| `.doc`, `.xls`, `.ppt`, `.rtf` | `convert` | → Processing_1/Convert |
| Несоответствие расширения | `normalize` | → Processing_1/Normalize |
| PDF, DOCX, XLSX, PPTX (OK) | `direct` | → Merge_0/Direct |
| Неопределенный тип | `unknown` | → Exceptions/Ambiguous |

**Использует Decision Engine:**
```python
detection = detect_file_type(file_path)  # Magic bytes, MIME, расширение
```

**Результат:**
```python
{
    "category": "direct|convert|extract|normalize|special|unknown",
    "detected_type": "pdf|docx|doc|zip|...",
    "mime_type": "application/pdf|...",
    "needs_conversion": True/False,
    "needs_extraction": True/False,
    "needs_normalization": True/False,
    "extension_matches_content": True/False,
}
```

---

#### ШАГ 4: Определение категории UNIT

**Логика:**
1. **Один тип файлов** → категория = тип первого файла
2. **Разные типы** → `is_mixed = True`, `unit_category = "mixed"`
3. **Разные категории** → `is_mixed = True`, выбор приоритета:
   - `extract` > `convert` > `normalize` > `direct`

**Примеры:**

| Файлы в UNIT | Категория UNIT | is_mixed |
|--------------|----------------|----------|
| 3x PDF | `direct` | False |
| 2x DOC | `convert` | False |
| 1x PDF + 1x DOCX | `direct` | True (разные типы) |
| 1x PDF + 1x DOC | `mixed` | True (разные категории) |
| 1x ZIP + 1x DOC | `mixed` (extract) | True |

---

#### ШАГ 5: Создание/Обновление Manifest

**Структура manifest.json:**

```json
{
  "schema_version": "2.0",
  "unit_id": "UNIT_abc123...",
  "protocol_id": "123456",
  "protocol_date": "2025-03-04",
  "files": [
    {
      "original_name": "Протокол.pdf",
      "current_name": "Протокол.pdf",
      "mime_type": "application/pdf",
      "detected_type": "pdf",
      "needs_ocr": false,
      "transformations": []
    }
  ],
  "processing": {
    "route": "pdf_text",
    "category": "direct",
    "is_mixed": false
  },
  "state_machine": {
    "initial_state": "RAW",
    "current_state": "MERGED_DIRECT",
    "final_state": "MERGED_DIRECT",
    "state_trace": ["RAW", "MERGED_DIRECT"]
  },
  "files_metadata": {
    "Протокол.pdf": {
      "detected_type": "pdf",
      "needs_ocr": false,
      "mime_type": "application/pdf",
      "pages_or_parts": 1
    }
  }
}
```

**Route определяется в `_determine_route_from_files()`:**
- `pdf_text` - обычный PDF
- `pdf_scan` - PDF с изображениями (needs_ocr=true)
- `docx` - DOCX файл
- `xlsx` - XLSX файл
- `image` - изображения
- `mixed` - разные типы

---

#### ШАГ 6: Маршрутизация (Distribution)

**Метод:** `move_unit_to_target()`

##### 6.1. DIRECT файлы (cycle=1)

```python
if unit_category == "direct" and cycle == 1:
    target = "Data/{date}/Merge/Merge_0/Direct/{extension}/"
    new_state = UnitState.MERGED_DIRECT
```

**Пример:**
- `UNIT_abc123/Протокол.pdf` → `Merge/Merge_0/Direct/pdf/UNIT_abc123/`

**Сортировка по расширению:**
- `/pdf/` - PDF файлы
- `/docx/` - DOCX файлы
- `/xlsx/` - XLSX файлы
- `/jpeg/` - изображения

##### 6.2. CONVERT файлы

```python
if unit_category == "convert":
    target = "Data/{date}/Processing/Processing_1/Convert/{extension}/"
    new_state = UnitState.CLASSIFIED_1
```

**Примеры:**
- DOC → `Processing/Processing_1/Convert/doc/`
- XLS → `Processing/Processing_1/Convert/xls/`
- PPT → `Processing/Processing_1/Convert/ppt/`

##### 6.3. EXTRACT файлы

```python
if unit_category == "extract":
    target = "Data/{date}/Processing/Processing_1/Extract/{extension}/"
    new_state = UnitState.CLASSIFIED_1
```

**Примеры:**
- ZIP → `Processing/Processing_1/Extract/zip/`
- RAR → `Processing/Processing_1/Extract/rar/`
- 7Z → `Processing/Processing_1/Extract/7z/`

##### 6.4. NORMALIZE файлы

```python
if unit_category == "normalize":
    target = "Data/{date}/Processing/Processing_1/Normalize/{extension}/"
    new_state = UnitState.CLASSIFIED_1
```

**Примеры:**
- PDF с неправильным расширением → `Processing/Processing_1/Normalize/pdf/`

##### 6.5. SPECIAL/UNKNOWN файлы

```python
if unit_category in ["special", "unknown"]:
    subcategory = "Special" if unit_category == "special" else "Ambiguous"
    target = "Data/{date}/Exceptions/Exceptions_1/{subcategory}/"
    new_state = UnitState.EXCEPTION_1
```

**Примеры:**
- `.sig`, `.p7s` → `Exceptions/Exceptions_1/Special/`
- Неопределенные файлы → `Exceptions/Exceptions_1/Ambiguous/`

##### 6.6. MIXED файлы

```python
if unit_category == "mixed":
    # Выбираем приоритетную категорию
    priority = ["extract", "convert", "normalize", "direct"]
    chosen_category = # первая найденная в файлах

    target = _get_target_directory_base(chosen_category, cycle)
    new_state = UnitState.CLASSIFIED_1 (если не direct)
    new_state = UnitState.MERGED_DIRECT (если direct)
```

**Примеры:**
- PDF + DOC → `Processing/Processing_1/Convert/` (приоритет convert)
- PDF + ZIP → `Processing/Processing_1/Extract/` (приоритет extract)

---

#### ШАГ 7: Обновление State Machine

**Переходы состояний (Cycle 1):**

```
RAW (начальное)
 ↓
 ├─→ MERGED_DIRECT       (direct файлы в Merge_0/Direct/)
 ├─→ CLASSIFIED_1        (convert/extract/normalize в Processing_1/)
 └─→ EXCEPTION_1         (special/unknown/empty в Exceptions_1/)
```

**Код обновления:**

```python
update_unit_state(
    unit_path=target_dir,
    new_state=new_state,
    cycle=cycle,
    operation={
        "type": "classify",
        "category": unit_category,
        "is_mixed": is_mixed,
        "file_count": len(files),
    },
)
```

**Обновляет manifest.json:**
```json
{
  "state_machine": {
    "initial_state": "RAW",
    "current_state": "MERGED_DIRECT",
    "final_state": null,
    "state_trace": ["RAW", "MERGED_DIRECT"]
  }
}
```

---

#### ШАГ 8: Запись Audit Log

**Метод:** `audit_logger.log_event()`

**Структура audit.log.jsonl:**

```json
{
  "timestamp": "2026-01-14T10:30:45Z",
  "unit_id": "UNIT_abc123...",
  "event_type": "operation",
  "operation": "classify",
  "correlation_id": "uuid-correlation-id",
  "details": {
    "cycle": 1,
    "category": "direct",
    "is_mixed": false,
    "file_count": 1,
    "category_distribution": {"direct": 1},
    "extension": "pdf",
    "target_directory": "/path/to/Merge/Merge_0/Direct/pdf"
  },
  "state_before": "RAW",
  "state_after": "MERGED_DIRECT"
}
```

**Записывается в:** `{target_dir}/audit.log.jsonl`

**Формат:** JSONL (JSON Lines) - каждое событие на новой строке

---

## 3. Сопоставление Web UI ↔ Backend

| Web UI Stage | Backend Operation | Метод/Класс |
|--------------|-------------------|-------------|
| **source: Input** | Чтение UNIT из Input | `get_unit_files()` |
| **classification** | Классификация файлов | `_classify_file()` → `detect_file_type()` |
| **distribution** | Маршрутизация по категориям | `_get_target_directory_base()` + `move_unit_to_target()` |
| **outputs.merge** | `Merge_0/Direct/{ext}/` | `unit_category="direct"` |
| **outputs.next** | `Processing_1/{Convert\|Extract\|Normalize}/{ext}/` | `unit_category="convert\|extract\|normalize"` |
| **outputs.exception** | `Exceptions_1/{Special\|Ambiguous\|Empty}/` | `unit_category="special\|unknown\|empty"` |

---

## 4. Детальные Примеры Обработки

### 4.1. Пример: Direct PDF

**Input:**
```
Data/2025-03-04/Input/UNIT_abc123/
├── Протокол.pdf (5 MB, text PDF)
```

**Процесс:**
1. **Classify:** `_classify_file()` → category=`direct`, detected_type=`pdf`
2. **Manifest:**
   - route=`pdf_text`
   - category=`direct`
   - is_mixed=`false`
3. **State:** `RAW` → `MERGED_DIRECT`
4. **Move:** → `Data/2025-03-04/Merge/Merge_0/Direct/pdf/UNIT_abc123/`
5. **Audit log:**
   ```json
   {
     "operation": "classify",
     "category": "direct",
     "state_before": "RAW",
     "state_after": "MERGED_DIRECT"
   }
   ```

**Результат:**
```
Data/2025-03-04/Merge/Merge_0/Direct/pdf/UNIT_abc123/
├── Протокол.pdf
├── manifest.json (с route="pdf_text", state="MERGED_DIRECT")
└── audit.log.jsonl
```

---

### 4.2. Пример: DOC файл (требует конвертации)

**Input:**
```
Data/2025-03-04/Input/UNIT_xyz789/
├── Протокол.doc (1.2 MB, old Word format)
```

**Процесс:**
1. **Classify:** category=`convert`, needs_conversion=`true`
2. **Manifest:**
   - route=`docx` (будет после конвертации)
   - category=`convert`
3. **State:** `RAW` → `CLASSIFIED_1`
4. **Move:** → `Data/2025-03-04/Processing/Processing_1/Convert/doc/UNIT_xyz789/`

**Результат:**
```
Data/2025-03-04/Processing/Processing_1/Convert/doc/UNIT_xyz789/
├── Протокол.doc (исходный файл)
├── manifest.json (state="CLASSIFIED_1")
└── audit.log.jsonl
```

**Следующий шаг:** Цикл 2 - Converter обработает файл

---

### 4.3. Пример: ZIP архив

**Input:**
```
Data/2025-03-04/Input/UNIT_def456/
├── Протоколы.zip (10 MB, содержит 5 PDF)
```

**Процесс:**
1. **Classify:** category=`extract`, needs_extraction=`true`
2. **Manifest:** category=`extract`
3. **State:** `RAW` → `CLASSIFIED_1`
4. **Move:** → `Data/2025-03-04/Processing/Processing_1/Extract/zip/UNIT_def456/`

**Результат:**
```
Data/2025-03-04/Processing/Processing_1/Extract/zip/UNIT_def456/
├── Протоколы.zip
├── manifest.json (state="CLASSIFIED_1")
└── audit.log.jsonl
```

**Следующий шаг:** Цикл 2 - Extractor разархивирует содержимое

---

### 4.4. Пример: Mixed UNIT (PDF + DOC)

**Input:**
```
Data/2025-03-04/Input/UNIT_ghi111/
├── Протокол.pdf (2 MB)
└── Приложение.doc (500 KB)
```

**Процесс:**
1. **Classify:**
   - `Протокол.pdf` → category=`direct`
   - `Приложение.doc` → category=`convert`
   - **UNIT category:** `mixed` (is_mixed=`true`)
   - **Chosen route:** `convert` (приоритет выше)

2. **Manifest:**
   ```json
   {
     "processing": {
       "route": "mixed",
       "category": "mixed",
       "chosen_route_category": "convert"
     },
     "files_metadata": {
       "Протокол.pdf": {"detected_type": "pdf"},
       "Приложение.doc": {"detected_type": "doc"}
     }
   }
   ```

3. **State:** `RAW` → `CLASSIFIED_1`
4. **Move:** → `Data/2025-03-04/Processing/Processing_1/Convert/doc/UNIT_ghi111/`

**Результат:**
```
Data/2025-03-04/Processing/Processing_1/Convert/doc/UNIT_ghi111/
├── Протокол.pdf (останется без изменений)
├── Приложение.doc (будет сконвертирован)
├── manifest.json (is_mixed=true, chosen_route_category="convert")
└── audit.log.jsonl
```

**Следующий шаг:** Цикл 2 - Converter обработает только .doc, PDF останется

---

### 4.5. Пример: Подпись (.p7s)

**Input:**
```
Data/2025-03-04/Input/UNIT_jkl222/
├── Протокол.pdf.p7s (100 KB, signature file)
```

**Процесс:**
1. **Classify:** category=`special` (signature extension)
2. **Manifest:** category=`special`
3. **State:** `RAW` → `EXCEPTION_1`
4. **Move:** → `Data/2025-03-04/Exceptions/Exceptions_1/Special/UNIT_jkl222/`

**Результат:**
```
Data/2025-03-04/Exceptions/Exceptions_1/Special/UNIT_jkl222/
├── Протокол.pdf.p7s
├── manifest.json (state="EXCEPTION_1")
└── audit.log.jsonl
```

**Финальное состояние:** EXCEPTION_1 (не обрабатывается дальше)

---

### 4.6. Пример: Пустой UNIT

**Input:**
```
Data/2025-03-04/Input/UNIT_mno333/
(нет файлов, только директория)
```

**Процесс:**
1. **Check:** `files = []` → empty unit
2. **Manifest:** category=`empty`, file_count=0
3. **State:** `RAW` → `EXCEPTION_1`
4. **Move:** → `Data/2025-03-04/Exceptions/Exceptions_1/Empty/UNIT_mno333/`

**Результат:**
```
Data/2025-03-04/Exceptions/Exceptions_1/Empty/UNIT_mno333/
├── manifest.json (error="No files found in UNIT")
└── audit.log.jsonl
```

---

## 5. Ключевые Отличия Web UI ↔ Backend

| Аспект | Web UI | Backend Reality |
|--------|--------|-----------------|
| **Сортировка** | Не указана | По расширениям: `/pdf/`, `/doc/`, `/zip/` |
| **Mixed handling** | Не детализирован | Приоритетная маршрутизация с выбором категории |
| **State transitions** | Упрощенные | Детальные с trace: RAW → CLASSIFIED_1/MERGED_DIRECT/EXCEPTION_1 |
| **Metadata** | Не показаны | manifest.json + audit.log.jsonl + route determination |
| **Decision Engine** | "Magic Bytes" | Полноценный detect_file_type() с MIME + magic bytes + extension check |
| **Copy mode** | Не упомянут | Автоматически включается для Input (сохранение оригиналов) |

---

## 6. Граф состояний (Cycle 1)

```
                    ┌──────────┐
                    │   RAW    │ (Input)
                    └────┬─────┘
                         │
                ┌────────┴────────┐
                │  CLASSIFICATION  │
                └────────┬─────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
   ┌────▼────┐   ┌──────▼──────┐   ┌────▼────────┐
   │ DIRECT  │   │ CONVERT/    │   │ SPECIAL/    │
   │         │   │ EXTRACT/    │   │ UNKNOWN/    │
   │         │   │ NORMALIZE   │   │ EMPTY       │
   └────┬────┘   └──────┬──────┘   └────┬────────┘
        │               │               │
        │               │               │
   ┌────▼─────────┐ ┌──▼──────────┐ ┌──▼──────────┐
   │MERGED_DIRECT │ │CLASSIFIED_1 │ │EXCEPTION_1  │
   └──────────────┘ └─────────────┘ └─────────────┘
        │               │               │
   Merge_0/Direct  Processing_1/   Exceptions_1/
                   [Conv/Ext/Norm]
```

---

## 7. Резюме: Что происходит с UNIT в Цикле 1

1. **Вход:** UNIT в `Data/{date}/Input/UNIT_xxx/`
2. **Чтение:** Все файлы кроме системных (manifest, audit, etc.)
3. **Классификация:** Каждый файл анализируется Decision Engine
4. **Определение категории:** Единая или mixed с приоритетом
5. **Создание manifest.json:** Метаданные + route + files_metadata
6. **Маршрутизация:**
   - **Direct** → `Merge_0/Direct/{ext}/` (state: MERGED_DIRECT)
   - **Convert** → `Processing_1/Convert/{ext}/` (state: CLASSIFIED_1)
   - **Extract** → `Processing_1/Extract/{ext}/` (state: CLASSIFIED_1)
   - **Normalize** → `Processing_1/Normalize/{ext}/` (state: CLASSIFIED_1)
   - **Special** → `Exceptions_1/Special/` (state: EXCEPTION_1)
   - **Unknown** → `Exceptions_1/Ambiguous/` (state: EXCEPTION_1)
   - **Empty** → `Exceptions_1/Empty/` (state: EXCEPTION_1)
7. **Перемещение:** UNIT копируется в целевую директорию (copy_mode для Input)
8. **Обновление состояния:** State machine transition в manifest
9. **Audit log:** Запись события в audit.log.jsonl
10. **Возврат:** Результат классификации с путями и метаданными

---

## 8. Готовность к Циклу 2

**После Цикла 1:**

| Целевая директория | Следующий шаг |
|-------------------|---------------|
| `Merge_0/Direct/` | → Merger (финальная стадия) |
| `Processing_1/Convert/` | → Cycle 2: Converter (DOC→DOCX) |
| `Processing_1/Extract/` | → Cycle 2: Extractor (ZIP→files) |
| `Processing_1/Normalize/` | → Cycle 2: Normalizer (fix extensions) |
| `Exceptions_1/` | → Финальное состояние (не обрабатывается) |

---

**Конец анализа Цикла 1**


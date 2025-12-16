# Анализ работы pipeline preprocesor и docling
_Exported on 28/11/2025 at 21:55:15 GMT+7 from Cursor (2.1.39)_

---

**User**

давай проанализируем пошаново как работает наш pipeline preprocesor и docling, 

давай выпишим схему как и что промзодит в какой последовательности.



---

**Cursor**

Сначала выясню текущий контекст проекта: прочитаю Memory Bank и найду в коде/скриптах, где реализован pipeline препроцессора и Docling, затем составлю поэтапную схему работы (блок-схема в текстовом виде) и, если надо, уточню детали по каждому шагу.

Сейчас вытащу из репо документацию и ключевые скрипты по pipeline и Docling, чтобы на их основе составить поэтапную схему, а потом сверим/уточним детали.

### Общая картина

**Если упростить до одной линии:**

1. **Файл появляется** (в `input/` или через `POST /upload` в `router`).
2. **Preprocessor/Router**:
   - определяет тип файла, распаковывает архивы, конвертит DOC→DOCX, решает нужен ли OCR,
   - собирает файлы в unit и пишет `manifest.json` в `normalized/UNIT_*/`.
3. **Scheduler/trigger_docling**:
   - по маршруту (`route` из manifest) отправляет unit в Docling `/process`.
4. **Docling**:
   - по route выбирает конкретный pipeline (pdf_scan/pdf_text/docx/html_text/mixed/…),
   - делает OCR/извлечение текста/лейаут/таблицы,
   - пишет результаты в `output/UNIT_*/` (JSON + Markdown),
   - сохраняет метрики в Mongo.
5. **Router API** (`/status/{unit_id}`, `/metrics/*`) позволяет посмотреть статус и статистику.

Ниже разложу **пошагово** и по **слоям пайплайна**.

---

### 1. Вход в систему

- **Вариант 1 — файлы кладутся на диск**:
  - Файлы/архивы попадают в `input/` (обычно смонтирована в контейнер router’а).
  - Scheduler периодически дергает `router` (endpoint `/process_now`), чтобы забрать все новое из `input/`.

- **Вариант 2 — API-загрузка**:
  - Клиент делает `POST /upload` на `router` (порт 8080) с `multipart/form-data`.
  - Router сохраняет файл в `input/` и сразу запускает для него предобработку (как если бы scheduler его нашёл).

---

### 2. Preprocessor / Router: пошаговый pipeline

**Основная функция: условно `process_file()` (router/main.py, см. PIPELINE_ANALYSIS.md).**

1. **Определение типа файла (`detect_file_type()`)**
   - Читает **magic bytes + mimetype**:
     - отличает настоящий DOC от фейкового (DOC-расширение, но там HTML или архив),
     - отличает обычный файл от архива (ZIP/RAR/7z),
     - отличает PDF от изображения и т.д.
   - Для PDF ещё отдельно:
     - читает несколько страниц через `pypdf`,
     - решает, есть ли текстовый слой → `needs_ocr = False/True`.

2. **Ветка: архив (`is_archive = true`)**
   - Вызывается `safe_extract_archive()`:
     - распаковывает в `extracted/ARCHIVE_xxx/`,
     - **ограничения**: `MAX_UNPACK_SIZE_MB`, `MAX_FILES_IN_ARCHIVE`,
     - санитизирует имена (убирает `../`, странные символы, защита от path traversal).
   - Каждый извлечённый файл **повторно прогоняется через `detect_file_type()`**.
   - Создаётся unit:
     - `unit_id = "UNIT_ARCHIVE_..."`,
     - `archive.is_archive = true`,
     - в `files[]` кладутся все распакованные файлы с их `detected_type`, `route` для каждого (pdf_scan/pdf_text/docx/html/image/...).
   - Если в архиве разные типы (DOCX + PDF + картинки) → **`processing.route = "mixed"`**.

3. **Ветка: DOC (старый формат)**
   - `detected_type = "doc"`, `requires_conversion = true`.
   - Файл кладётся в специальную директорию, которую мониторит сервис `libreoffice`.
   - LibreOffice (headless):
     - конвертит `*.doc` → `*.docx` в output-директорию,
     - Router либо ждёт/проверяет появление `.docx`, либо явно вызывает `soffice` (см. предложение `convert_doc_to_docx()` в `PIPELINE_ANALYSIS.md).
   - В manifest пишется уже **DOCX-файл** в `files[]` c route `docx`.

4. **Ветка: PDF**
   - После `pypdf`:
     - если есть текстовый слой → `processing.route = "pdf_text"`, `needs_ocr = false`;
     - если нет → `processing.route = "pdf_scan"`, `needs_ocr = true`.
   - Файл перемещается/копируется в `normalized/UNIT_xxx/files/`.

5. **Ветка: HTML / фейковые DOC**
   - Если magic bytes показывают HTML, но расширение `.doc`:
     - `detected_type = "html"`,
     - `processing.route = "html_text"`.
   - Обрабатывается как текст через BeautifulSoup (в текущей реализации Docling-пайплайна fallback).

6. **Ветка: изображения (JPEG/PNG)**  
   - Router их уже **распознаёт** (`detected_type = "image"`, `needs_ocr = true`).
   - В manifest можно (и по задумке нужно) ставить route `image_ocr`, хотя сейчас в Docling обработка image_ocr частично/не до конца реализована (см. `PIPELINE_ANALYSIS.md` — это одна из запланированных доработок).

7. **Формирование Unit + manifest (`create_manifest()`)**
   - Уровень данных:

     ```json
     {
       "unit_id": "UNIT_abc123",
       "created_at": "...",
       "processing": {
         "status": "ready",
         "route": "pdf_scan|pdf_text|docx|html_text|image_ocr|mixed|unknown"
       },
       "files": [
         {
           "file_id": "uuid",
           "original_name": "document.pdf",
           "path": "/app/normalized/UNIT_abc123/files/document.pdf",
           "detected_type": "pdf",
           "mime_type": "application/pdf",
           "needs_ocr": true,
           "requires_conversion": false,
           "sha256": "...",
           "size": 12345
         }
       ],
       "archive": {
         "is_archive": false,
         "archive_id": null
       }
     }
     ```

   - manifest:
     - сохраняется как файл в `normalized/UNIT_xxx/manifest.json`,
     - дублируется в MongoDB (коллекция `manifests`) — основное хранилище метаданных.

8. **Сохранение метрик**
   - Router пишет в MongoDB:
     - по каждому файлу/unit — время классификации, распаковки, конвертации и т.д.
     - агрегированные метрики (через `collect_metrics_from_output.py`, `analyze_metrics.py`, см. `FULL_PIPELINE_REPORT.md`, `COMPLETE_PROCESSING_REPORT.md`).

---

### 3. Связка Preprocessor → Docling

1. **Когда unit готов (status=ready)**:
   - либо Scheduler дергает Docling сразу пачкой unit’ов,
   - либо Router/внешний вызов делает `POST /process` на Docling-сервис (порт 8000).

2. **Типичный payload в Docling `/process`:**

```json
{
  "unit_id": "UNIT_...",
  "manifest": "mongodb://UNIT_...",  // или сам объект manifest inline
  "files": [...],
  "route": "pdf_text|pdf_scan|docx|html_text|mixed|image_ocr|unknown"
}
```

3. **Docling при старте запроса:**
   - Если `manifest` — ссылка на Mongo → забирает манифест по `unit_id` из БД.
   - Если в манифесте пути `/app/normalized/...`, а реальные в контейнере `/data/normalized/...` — применяет внутреннюю логику ремапа путей (см. DOCLING_FINAL_REPORT: добавили авто‑поиск в `'/data/normalized/UNIT_*/files/'`).
   - Подтягивает список файлов и route.

---

### 4. Внутренний pipeline Docling: пошагово

**Главная идея:** на каждый unit и каждый файл в нём Docling выбирает **route** и обрабатывает по конкретной ветке.

1. **Определение маршрута**
   - Берётся `processing.route` из manifest:
     - `pdf_scan`
     - `pdf_text`
     - `docx`
     - `html_text`
     - `mixed`
     - `image_ocr`
     - `unknown` (fallback)
   - Для `mixed` Docling смотрит внутри `files[]` и для каждого файла подбирает свой под-route (pdf_scan/pdf_text/docx/html/…).

2. **Подготовка Docling Converter / fallback-логики**
   - Если установлен `docling-core`:
     - создаётся `DocumentConverter` с `PdfPipelineOptions(do_ocr=needs_ocr, do_table_structure=True)` и т.п.
     - (по анализу — сейчас конвертер создаётся один раз, а надо бы динамически под file/route; в `PIPELINE_ANALYSIS.md` описан вариант `_get_docling_converter()`).
   - Если Docling недоступен → fallback:
     - `pdfplumber` для PDF,
     - `python-docx` для DOCX,
     - `beautifulsoup` для HTML,
     - `pytesseract` для изображений (в предложенных улучшениях).

3. **Route: pdf_scan**
   - Используется **OCR-пайплайн**:
     - Docling OCR → по страницам извлекает текст.
     - Layout Analysis:
       - абзацы, заголовки, колонки, порядок чтения.
     - Table Extraction:
       - структуры таблиц, ячейки, заголовки.
   - Метрики:
     - `ocr`, `text_extraction`, `layout_analysis`, `total` — сохраняются по unit/файлу (см. DOCLING_PROCESSING_REPORT/FULL_PIPELINE_REPORT).

4. **Route: pdf_text**
   - Text Extraction **без OCR**:
     - либо Docling, либо fallback `pdfplumber`.
   - Затем:
     - Layout Analysis,
     - Table Extraction (Docling/или pdfplumber fallback).
   - Время обработки ориентировочно ~0.3–0.5s на файл по отчётам.

5. **Route: docx**
   - Text Extraction через Docling или `python-docx`.
   - Layout Analysis (заголовки, разделы).
   - Извлечение таблиц как структуры (в Docling) или простыми списками (fallback).
   - Результат: текст, таблицы, метаданные, layout.

6. **Route: html_text**
   - Файлы, которые оказались HTML (в т.ч. под видом `.doc`).
   - Обработка:
     - `beautifulsoup`/Docling HTML-parser,
     - извлечение текстового содержания,
     - упрощённый layout.
   - Статистика по ним видна как route = `html_text` в отчетах.

7. **Route: image_ocr** (задумано/частично)
   - Идея:
     - либо Docling напрямую обрабатывает изображения через свой OCR,
     - либо fallback через `pytesseract`.
   - В `PIPELINE_ANALYSIS.md` уже есть предложенная реализация `_process_image_ocr()` + `_process_image_ocr_fallback()` и ветка `elif self.route == "image_ocr"` — то есть архитектурно предусмотрено.

8. **Route: mixed**
   - Unit содержит несколько файлов с разными типами (см. DOCLING_FINAL_REPORT, mixed unit’ы `UNIT_ARCHIVE_*`).
   - Сейчас:
     - каждый файл обрабатывается своим route (pdf_scan/pdf_text/docx),
     - создаются отдельные outputs по каждому файлу.
   - План/идея (описано в PIPELINE_ANALYSIS.md):
     - функция `merge_mixed_results(processing_results)`:
       - сортирует файлы (сначала DOCX, потом PDF, потом картинки),
       - объединяет текст с маркерами источника,
       - мерджит таблицы и метаданные по файлам.

9. **Route: unknown**
   - Файл не классифицировался нормально.
   - Минимальная обработка, иногда только stub + layout=empty; но в метриках он учитывается как `unknown`.

10. **Сохранение результатов**
    - Для каждого обработанного файла:
      - JSON → `output/UNIT_xxx/*.json`:
        - unit_id, имя файла, route, флаг `needs_ocr`, извлечённый текст/таблицы/metadata.
      - Markdown → `output/UNIT_xxx/*.md`:
        - человекочитаемый отчёт (шапка с метаданными + контент).
    - Пример структуры:

      ```text
      output/
        UNIT_abc123/
          document.pdf.json
          document.pdf.md
      ```

    - По отчётам: создаётся по 2 файла на каждый входной файл (JSON + MD).

11. **Метрики Docling**
    - Хранятся в MongoDB (`processing_metrics`):
      - время по этапам (ocr, text_extraction, layout_analysis, total),
      - статистика по страницам, таблицам,
      - распределение по библиотекам (pdfplumber, python-docx, beautifulsoup, fallback).
    - Сводные отчёты формируются скриптами (`test_docling_*`, `collect_metrics_from_output.py`) и сведены в:
      - `DOCLING_PROCESSING_REPORT.md`,
      - `DOCLING_FINAL_REPORT.md`.

---

### 5. Scheduler и общий цикл

1. **Scheduler (APScheduler, сервис `scheduler/`)**
   - По cron (`SCHEDULE_CRON` в env) периодически:
     - вызывает Router `/process_now` → Router сканирует `input/`, создаёт unit’ы.
     - вызывает Docling `/process` для очереди unit’ов со статусом `ready` (реализация может быть как pull из Mongo, так и push из Router’а).

2. **Статус и мониторинг**
   - Router:
     - `GET /status/{unit_id}` — единичный статус unit’а,
     - `GET /metrics/processing`, `/metrics/summary` — метрики по пайплайну (см. README_DOCLING_READY).
   - Логи:
     - `docker-compose logs -f router|docling|scheduler`.
   - Отчеты верхнего уровня:
     - `FULL_PIPELINE_REPORT.md`, `COMPLETE_PROCESSING_REPORT.md`, `PIPELINE_ANALYSIS.md`, `PIPELINE_TEST_SUMMARY.md`.

---

### 6. Итоговая «линейка» этапов по времени

**Для одного файла (любой формат):**

1. **Input**: файл появляется в `input/` или через `/upload`.
2. **Router**:
   1. `detect_file_type()` → тип, mime, спец. случаи.
   2. (опционально) `safe_extract_archive()` → множество файлов.
   3. (опционально) конвертация DOC→DOCX через LibreOffice.
   4. Классификация PDF (text vs scan) → `needs_ocr`.
   5. Формирование unit’а + копирование файлов в `normalized/UNIT_*/files/`.
   6. Создание `manifest.json` + запись в Mongo.
3. **Trigger Docling**:
   - Scheduler/Router делает HTTP-запрос на Docling `/process` с `unit_id` и route.
4. **Docling**:
   1. Загружает manifest (из Mongo или запроса).
   2. Для каждого файла выбирает ветку route.
   3. Выполняет OCR/извлечение текста/лейаут/таблицы.
   4. Пишет JSON+MD в `output/UNIT_*/`.
   5. Пишет метрики в Mongo.
5. **Post-processing/аналитика**:
   - агрегация метрик, отчёты, мониторинг.

---

Если хочешь, следующим шагом могу:
- либо нарисовать **строгое текстовое FSM/диаграмму** для каждого route (pdf_scan, pdf_text, docx, mixed, image_ocr),
- либо пройтись по **конкретному unit’у** из реального лога/отчёта и разложить его путь от `input/` до `output/UNIT_xxx/*.md` по конкретным вызовам и полям из manifest.

```json
     {
       "unit_id": "UNIT_abc123",
       "created_at": "...",
       "processing": {
         "status": "ready",
         "route": "pdf_scan|pdf_text|docx|html_text|image_ocr|mixed|unknown"
       },
       "files": [
         {
           "file_id": "uuid",
           "original_name": "document.pdf",
           "path": "/app/normalized/UNIT_abc123/files/document.pdf",
           "detected_type": "pdf",
           "mime_type": "application/pdf",
           "needs_ocr": true,
           "requires_conversion": false,
           "sha256": "...",
           "size": 12345
         }
       ],
       "archive": {
         "is_archive": false,
         "archive_id": null
       }
     }
     ```

   - manifest:
     - сохраняется как файл в `normalized/UNIT_xxx/manifest.json`,
     - дублируется в MongoDB (коллекция `manifests`) — основное хранилище метаданных.

8. **Сохранение метрик**
   - Router пишет в MongoDB:
     - по каждому файлу/unit — время классификации, распаковки, конвертации и т.д.
     - агрегированные метрики (через `collect_metrics_from_output.py`, `analyze_metrics.py`, см. `FULL_PIPELINE_REPORT.md`, `COMPLETE_PROCESSING_REPORT.md`).

---

### 3. Связка Preprocessor → Docling

1. **Когда unit готов (status=ready)**:
   - либо Scheduler дергает Docling сразу пачкой unit’ов,
   - либо Router/внешний вызов делает `POST /process` на Docling-сервис (порт 8000).

2. **Типичный payload в Docling `/process`:**

```json
{
  "unit_id": "UNIT_...",
  "manifest": "mongodb://UNIT_...",  // или сам объект manifest inline
  "files": [...],
  "route": "pdf_text|pdf_scan|docx|html_text|mixed|image_ocr|unknown"
}
```

3. **Docling при старте запроса:**
   - Если `manifest` — ссылка на Mongo → забирает манифест по `unit_id` из БД.
   - Если в манифесте пути `/app/normalized/...`, а реальные в контейнере `/data/normalized/...` — применяет внутреннюю логику ремапа путей (см. DOCLING_FINAL_REPORT: добавили авто‑поиск в `'/data/normalized/UNIT_*/files/'`).
   - Подтягивает список файлов и route.

---

### 4. Внутренний pipeline Docling: пошагово

**Главная идея:** на каждый unit и каждый файл в нём Docling выбирает **route** и обрабатывает по конкретной ветке.

1. **Определение маршрута**
   - Берётся `processing.route` из manifest:
     - `pdf_scan`
     - `pdf_text`
     - `docx`
     - `html_text`
     - `mixed`
     - `image_ocr`
     - `unknown` (fallback)
   - Для `mixed` Docling смотрит внутри `files[]` и для каждого файла подбирает свой под-route (pdf_scan/pdf_text/docx/html/…).

2. **Подготовка Docling Converter / fallback-логики**
   - Если установлен `docling-core`:
     - создаётся `DocumentConverter` с `PdfPipelineOptions(do_ocr=needs_ocr, do_table_structure=True)` и т.п.
     - (по анализу — сейчас конвертер создаётся один раз, а надо бы динамически под file/route; в `PIPELINE_ANALYSIS.md` описан вариант `_get_docling_converter()`).
   - Если Docling недоступен → fallback:
     - `pdfplumber` для PDF,
     - `python-docx` для DOCX,
     - `beautifulsoup` для HTML,
     - `pytesseract` для изображений (в предложенных улучшениях).

3. **Route: pdf_scan**
   - Используется **OCR-пайплайн**:
     - Docling OCR → по страницам извлекает текст.
     - Layout Analysis:
       - абзацы, заголовки, колонки, порядок чтения.
     - Table Extraction:
       - структуры таблиц, ячейки, заголовки.
   - Метрики:
     - `ocr`, `text_extraction`, `layout_analysis`, `total` — сохраняются по unit/файлу (см. DOCLING_PROCESSING_REPORT/FULL_PIPELINE_REPORT).

4. **Route: pdf_text**
   - Text Extraction **без OCR**:
     - либо Docling, либо fallback `pdfplumber`.
   - Затем:
     - Layout Analysis,
     - Table Extraction (Docling/или pdfplumber fallback).
   - Время обработки ориентировочно ~0.3–0.5s на файл по отчётам.

5. **Route: docx**
   - Text Extraction через Docling или `python-docx`.
   - Layout Analysis (заголовки, разделы).
   - Извлечение таблиц как структуры (в Docling) или простыми списками (fallback).
   - Результат: текст, таблицы, метаданные, layout.

6. **Route: html_text**
   - Файлы, которые оказались HTML (в т.ч. под видом `.doc`).
   - Обработка:
     - `beautifulsoup`/Docling HTML-parser,
     - извлечение текстового содержания,
     - упрощённый layout.
   - Статистика по ним видна как route = `html_text` в отчетах.

7. **Route: image_ocr** (задумано/частично)
   - Идея:
     - либо Docling напрямую обрабатывает изображения через свой OCR,
     - либо fallback через `pytesseract`.
   - В `PIPELINE_ANALYSIS.md` уже есть предложенная реализация `_process_image_ocr()` + `_process_image_ocr_fallback()` и ветка `elif self.route == "image_ocr"` — то есть архитектурно предусмотрено.

8. **Route: mixed**
   - Unit содержит несколько файлов с разными типами (см. DOCLING_FINAL_REPORT, mixed unit’ы `UNIT_ARCHIVE_*`).
   - Сейчас:
     - каждый файл обрабатывается своим route (pdf_scan/pdf_text/docx),
     - создаются отдельные outputs по каждому файлу.
   - План/идея (описано в PIPELINE_ANALYSIS.md):
     - функция `merge_mixed_results(processing_results)`:
       - сортирует файлы (сначала DOCX, потом PDF, потом картинки),
       - объединяет текст с маркерами источника,
       - мерджит таблицы и метаданные по файлам.

9. **Route: unknown**
   - Файл не классифицировался нормально.
   - Минимальная обработка, иногда только stub + layout=empty; но в метриках он учитывается как `unknown`.

10. **Сохранение результатов**
    - Для каждого обработанного файла:
      - JSON → `output/UNIT_xxx/*.json`:
        - unit_id, имя файла, route, флаг `needs_ocr`, извлечённый текст/таблицы/metadata.
      - Markdown → `output/UNIT_xxx/*.md`:
        - человекочитаемый отчёт (шапка с метаданными + контент).
    - Пример структуры:

      ```text
      output/
        UNIT_abc123/
          document.pdf.json
          document.pdf.md
      ```

    - По отчётам: создаётся по 2 файла на каждый входной файл (JSON + MD).

11. **Метрики Docling**
    - Хранятся в MongoDB (`processing_metrics`):
      - время по этапам (ocr, text_extraction, layout_analysis, total),
      - статистика по страницам, таблицам,
      - распределение по библиотекам (pdfplumber, python-docx, beautifulsoup, fallback).
    - Сводные отчёты формируются скриптами (`test_docling_*`, `collect_metrics_from_output.py`) и сведены в:
      - `DOCLING_PROCESSING_REPORT.md`,
      - `DOCLING_FINAL_REPORT.md`.

---

### 5. Scheduler и общий цикл

1. **Scheduler (APScheduler, сервис `scheduler/`)**
   - По cron (`SCHEDULE_CRON` в env) периодически:
     - вызывает Router `/process_now` → Router сканирует `input/`, создаёт unit’ы.
     - вызывает Docling `/process` для очереди unit’ов со статусом `ready` (реализация может быть как pull из Mongo, так и push из Router’а).

2. **Статус и мониторинг**
   - Router:
     - `GET /status/{unit_id}` — единичный статус unit’а,
     - `GET /metrics/processing`, `/metrics/summary` — метрики по пайплайну (см. README_DOCLING_READY).
   - Логи:
     - `docker-compose logs -f router|docling|scheduler`.
   - Отчеты верхнего уровня:
     - `FULL_PIPELINE_REPORT.md`, `COMPLETE_PROCESSING_REPORT.md`, `PIPELINE_ANALYSIS.md`, `PIPELINE_TEST_SUMMARY.md`.

---

### 6. Итоговая «линейка» этапов по времени

**Для одного файла (любой формат):**

1. **Input**: файл появляется в `input/` или через `/upload`.
2. **Router**:
   1. `detect_file_type()` → тип, mime, спец. случаи.
   2. (опционально) `safe_extract_archive()` → множество файлов.
   3. (опционально) конвертация DOC→DOCX через LibreOffice.
   4. Классификация PDF (text vs scan) → `needs_ocr`.
   5. Формирование unit’а + копирование файлов в `normalized/UNIT_*/files/`.
   6. Создание `manifest.json` + запись в Mongo.
3. **Trigger Docling**:
   - Scheduler/Router делает HTTP-запрос на Docling `/process` с `unit_id` и route.
4. **Docling**:
   1. Загружает manifest (из Mongo или запроса).
   2. Для каждого файла выбирает ветку route.
   3. Выполняет OCR/извлечение текста/лейаут/таблицы.
   4. Пишет JSON+MD в `output/UNIT_*/`.
   5. Пишет метрики в Mongo.
5. **Post-processing/аналитика**:
   - агрегация метрик, отчёты, мониторинг.

---

Если хочешь, следующим шагом могу:
- либо нарисовать **строгое текстовое FSM/диаграмму** для каждого route (pdf_scan, pdf_text, docx, mixed, image_ocr),
- либо пройтись по **конкретному unit’у** из реального лога/отчёта и разложить его путь от `input/` до `output/UNIT_xxx/*.md` по конкретным вызовам и полям из manifest.
```

```plaintext
      output/
        UNIT_abc123/
          document.pdf.json
          document.pdf.md
```


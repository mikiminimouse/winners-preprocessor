---
title: "Анализ модели Granite"
source: "https://chatgpt.com/c/692ce707-cd30-8323-bb4b-904a970b6aaa"
author:
  - "[[ChatGPT]]"
published:
created: 2025-12-01
description: "ChatGPT — ваш чат-бот с искусственным интеллектом для повседневного использования. Общайтесь с самым продвинутым искусственным интеллектом, чтобы изучать идеи, решать проблемы и учиться быстрее."
tags:
  - "clippings"
---
Ниже — сжатый, практичный план «как настроить, отладить и использовать Docling (в Docker) как ядро + подключить удалённый Granite-Docling (VLM) по API» и готовые примеры кода/конфигураций. Яследовал документации Docling и странице модели Granite и привожу конкретные шаги, проверки и фрагменты кода, чтобы у вас получилось устойчивое PDF → Markdown + метаданные решение без «повторяющихся» MD-файлов. [docling-project.github.io+4GitHub+4huggingface.co+4](https://github.com/docling-project/docling-serve?utm_source=chatgpt.com)

---

# 1 — Ключевая архитектура (кратко)

1. Docling (локально, в Docker) — **ядро** для приёма PDF/DOCX/PPTX, рендеринга страниц, определения наличия текстового слоя, таблиц, запуск OCR и сборки `DoclingDocument`. Docling умеет экспортировать MD/HTML/JSON. [GitHub+1](https://github.com/docling-project/docling-serve?utm_source=chatgpt.com)
2. Granite-Docling (VLM model) — **внешняя визуальная модель**, которая Docling использует для улучшенного визуального парсинга страниц (layout + OCR/structure). Granite может запускаться локально (модель-сервер, LM Studio / vllm / ollama / huggingface inference) или в облаке. Docling поддерживает remote VLM через `VlmPipelineOptions` / `ApiVlmOptions`. [huggingface.co+1](https://huggingface.co/ibm-granite/granite-docling-258M?utm_source=chatgpt.com)
3. Взаимодействие: Docling рендерит страницы → если включён VLM pipeline, Docling отправляет страницы (изображения) к Granite API → Granite возвращает DocTags/структуру → Docling собирает `DoclingDocument` → экспорт в Markdown + сбор метаданных. [docling-project.github.io](https://docling-project.github.io/docling/examples/minimal_vlm_pipeline/?utm_source=chatgpt.com)

---

# 2 — Общие причины повторяющегося/одинакового Markdown и меры (быстро)

- **Повтор/кеш/реиспользование потока**: каждый PDF **обязательно** передавать как новый `DocumentStream` (BytesIO) и вызывать convert заново.
- **Batch неправильно настроен**: не объединяйте потоки без явной разбивки.
- **OCR выключен для сканов** → пустые шаблоны; включайте `do_ocr=True`.
- **Используется Smol/неподходящая модель для языка** → замените на Granite-Docling (более полноценная).  
	(см. детальниее в разделе «проверки» ниже). [GitHub+1](https://github.com/docling-project/docling/discussions/1401?utm_source=chatgpt.com)

---

# 3 — Как подставить/перенастроить Docling в Docker и подключить remote Granite

### A) Докер: рекомендованный образ

Используйте официальный `docling-serve` образ (или ваш собственный билд) — он уже содержит API-слой для приёма файлов. (Repo: docling-serve). [GitHub](https://github.com/docling-project/docling-serve?utm_source=chatgpt.com)

Пример `docker-compose.yml` (минимум — docling-serve + опция для Granite если вы хостите локально):

```
version: "3.8"
services:
  docling:
    image: ghcr.io/docling-project/docling-serve:latest
    restart: unless-stopped
    ports:
      - "8080:8080"                 # API docling
    environment:
      - DOCING_LOG_LEVEL=INFO
    volumes:
      - ./data:/data

  granite_api:                       # опционально: если вы хостите модель локально (например Ollama/LMStudio)
    image: your-granite-server-image  # либо запускать модель через vllm/ollama/transformers server
    ports:
      - "8501:8501"
    # настройка зависит от сервера для модели
```

Если Granite развёрнут отдельно (например, Hugging Face Inference / LM Studio / ollama), просто указываете url в Docling (см. ниже). [GitHub+1](https://github.com/docling-project/docling-serve?utm_source=chatgpt.com)

### B) Версия Docling в контейнере

- Если текущая версия `docling-serve` в контейнере **старее** чем та, что поддерживает `vlm`/`api vlm` опции — пересоберите контейнер с нужной версией `docling`/`docling-core` (в `requirements.txt`/Dockerfile замените на `pip install 'docling==X.Y.Z'`), либо используйте публичный `docling-serve` tag, где VLM уже поддерживается. (в репо есть образы и описания). [GitHub+1](https://github.com/docling-project/docling/blob/main/Dockerfile?utm_source=chatgpt.com)

---

# 4 — Конфигурация Docling для вызова **удалённого Granite API** (без промптов)

Docling предоставляет `VlmPipelineOptions(enable_remote_services=True)` и `ApiVlmOptions` для конфигурации remote VLM. Ниже — минимальный Python-пример (встраивается в сервис/скрипт, который будет запускаться в контейнере):

```
from docling.datamodel.pipeline_options import VlmPipelineOptions, ApiVlmOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat, DocumentStream
from io import BytesIO
from pathlib import Path

# --- Конфиг: remote VLM API (Granite)
api_opts = ApiVlmOptions(
    url="https://granite.internal.api/v1/process",     # ваш endpoint
    method="POST",
    headers={"Authorization": "Bearer YOUR_TOKEN"},
    params={},  # при необходимости
    timeout=60
)

vlm_opts = VlmPipelineOptions(enable_remote_services=True, api_vlm_options=api_opts)

pdf_opts = PdfFormatOption(pipeline_options=vlm_opts, do_ocr=True)

converter = DocumentConverter(format_options={InputFormat.PDF: pdf_opts})

def pdf_to_md(path: Path, out_md: Path):
    body = path.read_bytes()
    src = DocumentStream(name=path.name, stream=BytesIO(body))
    res = converter.convert(source=src)
    md = res.document.export_to_markdown()
    meta = {
      "pages": len(res.document.pages),
      "title": getattr(res.document, "title", None),
      "created": getattr(res.document, "created", None),
      "language": getattr(res.document, "language", None)
    }
    out_md.write_text(md, encoding="utf-8")
    return meta
```

Пояснения:

- `ApiVlmOptions` описывает как Docling вызывает внешнюю VLM — передаётся URL, headers, timeout; Docling отправит страницу-изображения и ожидает DocTags/структуру в ответ. Это **без промптов** — машинный поток: вход image → структурированный ответ. [docling-project.github.io+1](https://docling-project.github.io/docling/examples/vlm_pipeline_api_model/?utm_source=chatgpt.com)

---

# 5 — Как развернуть Granite как удалённый сервис

Варианты:

- **Hugging Face Inference API** — быстрее старт (облачный). Granite модель есть на HF; Docling может вызывать HTTP endpoint HF. (обратите внимание на формат запросов/ответов, возможно нужен адаптер). [huggingface.co](https://huggingface.co/ibm-granite/granite-docling-258M?utm_source=chatgpt.com)
- **Self-host (recommended for speed/control)**: LM Studio / vllm / ollama / FastAPI wrapper на `transformers` — деплой granite weights и expose HTTP endpoint `/process` который принимает изображение и возвращает DocTags JSON (см. пример SDK в репо granite). Документация Docling содержит примеры remote VLM endpoints. [docling-project.github.io+1](https://docling-project.github.io/docling/examples/vlm_pipeline_api_model/?utm_source=chatgpt.com)

---

# 6 — Извлечение метаданных (что брать, как)

Используйте поля `res.document`:

- `title`, `author`, `created` / `modified` (из PDF metadata)
- `pages` — количество страниц
- `language` — определённый Docling/ocr результат
- `tables` — массив таблиц (экспортируйте в CSV/JSON)
- `images` — пути/встроенные
- `ocr_confidence` — если поддерживается OCR движком
- дополнительное: NER / named entities — можно запустить LLM/VLM анализ на экспортированном MD (опционально).

Пример вывода meta (см. код выше). [docling-project.github.io](https://docling-project.github.io/docling/getting_started/installation/?utm_source=chatgpt.com)

---

# 7 — Проверки/защиты от ошибок (чтобы не было одинаковых MD)

1. **Per-file fresh stream**: всегда `DocumentStream(name=..., stream=BytesIO(body))`.
2. **After convert — assert**:
	- `res is not None and res.document is not None`
	- `len(res.document.pages) > 0` (если нет — логировать и сохранить исход PDF для анализа)
3. **Fallback**: если `pages==0` → попробовать `do_ocr=True`/change backend и повторить.
4. **Atomic write**: при записи MD — писать в temp файл, затем переименовать (чтобы избежать перезаписи).
5. **Логирование**: логируйте входной filename + номер страниц + размер MD + sha256(MD) — для детекции дублирования.
6. **Тестовый набор**: создайте набор “контрольных” PDF (текстовый, скан, сложный layout) и прогоните их после сборки; сравните результаты. [GitHub](https://github.com/docling-project/docling/discussions/1401?utm_source=chatgpt.com)

---

# 8 — Разница Granite vs SmolDocling (коротко)

- **Granite-Docling** — полнофункциональная VLM версия, лучше для сложных layout и non-latin языков; даёт больше точности для генерации DocTags. [huggingface.co](https://huggingface.co/ibm-granite/granite-docling-258M?utm_source=chatgpt.com)
- **SmolDocling** — облегчённая версия, быстрее и легче, но хуже на сложных/не-латинских документах; для production с разнородными сканами рекомендую Granite. [huggingface.co+1](https://huggingface.co/ibm-granite/granite-docling-258M?utm_source=chatgpt.com)

---

# 9 — Быстрая инструкция действий (шаги, чтобы сделать сейчас)

1. Обновить/проверить `docling-serve` образ → если старый — пересобрать с нужной версией docling. [GitHub](https://github.com/docling-project/docling-serve?utm_source=chatgpt.com)
2. Развернуть remote Granite API (HuggingFace inference / LM Studio / ollama / custom FastAPI), убедиться что endpoint возвращает DocTags JSON по формату, ожидаемому Docling. [huggingface.co+1](https://huggingface.co/ibm-granite/granite-docling-258M?utm_source=chatgpt.com)
3. В `docling` включить VLM remote: `VlmPipelineOptions(enable_remote_services=True, api_vlm_options=ApiVlmOptions(...))` и протестировать конвертацию одного PDF. (см. код выше). [docling-project.github.io](https://docling-project.github.io/docling/examples/vlm_pipeline_api_model/?utm_source=chatgpt.com)
4. Добавить логирование/ассерты + temp-write + контрольный набор PDF.
5. Пакетная обработка: loop по файлам — для каждого файл: fresh stream → convert → validate → export → save meta.

---

# 10 — Короткий checklist (готовый к вставке в ваш prompt/курсёр)

- [ ] Использовать `docling-serve:latest` (или пересобрать) как API-ядро. [GitHub](https://github.com/docling-project/docling-serve?utm_source=chatgpt.com)
- [ ] Развернуть Granite-Docling как HTTP-endpoint (HF/LM Studio/ollama) и проверить `/process` поведение. [huggingface.co](https://huggingface.co/ibm-granite/granite-docling-258M?utm_source=chatgpt.com)
- [ ] В Docling включить `VlmPipelineOptions(enable_remote_services=True)` + `ApiVlmOptions(url=..., headers=...)`. [docling-project.github.io](https://docling-project.github.io/docling/examples/vlm_pipeline_api_model/?utm_source=chatgpt.com)
- [ ] Для каждого PDF: fresh `DocumentStream`, `do_ocr=True` для сканов, validate `res.document.pages>0`.
- [ ] Собирать метаданные: title, pages, language, tables, ocr\_confidence → сохранять рядом с MD. [docling-project.github.io](https://docling-project.github.io/docling/getting_started/installation/?utm_source=chatgpt.com)
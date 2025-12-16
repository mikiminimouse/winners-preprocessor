# ПОЛНЫЙ ОТЧЕТ ОБ ОБРАБОТКЕ PIPELINE

**Время начала:** 2025-11-20T14:14:55.020697
**Время завершения:** 2025-11-20T14:15:25.982154

---

## ОБЩАЯ СТАТИСТИКА

| Этап | Время | Детали |
|------|-------|--------|
| **Разархивирование** | 0.34s | 71 файлов |
| **Preprocessing** | 2.31s | 83 unit'ов |
| **Docling Processing** | 15.96s | 66/66 успешно |
| **ИТОГО** | **18.62s** | Полный pipeline |

---

## СТАТИСТИКА ПО РАСШИРЕНИЯМ ФАЙЛОВ

| Расширение | Количество | Routes | Среднее время |
|------------|------------|--------|---------------|
| `.doc` | 5 | html_text(4), None(1) | 0.008s |
| `.docx` | 18 | docx(18) | 1.275s |
| `.pdf` | 43 | pdf_scan(26), pdf_text(17) | 0.348s |
| `unknown` | 17 | unknown(17) | 0.000s |

### Детальная статистика по расширениям:

#### .doc
- Количество файлов: 5
- Routes: {'html_text': 4, None: 1}

Времена обработки:
  - total: avg=0.008s, min=0.002s, max=0.014s
  - text_extraction: avg=0.004s, min=0.002s, max=0.006s
  - layout_analysis: avg=0.003s, min=0.000s, max=0.004s

#### .docx
- Количество файлов: 18
- Routes: {'docx': 18}

Времена обработки:
  - total: avg=1.275s, min=0.013s, max=6.857s
  - text_extraction: avg=0.630s, min=0.005s, max=3.559s
  - layout_analysis: avg=0.639s, min=0.002s, max=3.287s

#### .pdf
- Количество файлов: 43
- Routes: {'pdf_scan': 26, 'pdf_text': 17}

Времена обработки:
  - total: avg=0.348s, min=0.006s, max=3.017s
  - text_extraction: avg=0.437s, min=0.106s, max=1.540s
  - ocr: avg=0.006s, min=0.001s, max=0.015s
  - layout_analysis: avg=0.165s, min=0.001s, max=1.471s

#### unknown
- Количество файлов: 17
- Routes: {'unknown': 17}

Времена обработки:

---

## СТАТИСТИКА ПО ЭТАПАМ ОБРАБОТКИ

| Этап | Количество | Общее время | Среднее | Мин | Макс |
|------|------------|-------------|---------|-----|------|
| `layout_analysis` | 66 | 18.60s | 0.282s | 0.000s | 3.287s |
| `ocr` | 26 | 0.15s | 0.006s | 0.001s | 0.015s |
| `text_extraction` | 39 | 18.79s | 0.482s | 0.002s | 3.559s |
| `total` | 66 | 37.95s | 0.575s | 0.002s | 6.857s |

---

## СТАТИСТИКА ПО ИСПОЛЬЗУЕМЫМ БИБЛИОТЕКАМ/LLM

| Библиотека | Использований | Общее время | Среднее время | Этапы |
|------------|---------------|-------------|---------------|-------|
| **beautifulsoup** | 4 | 0.04s | 0.010s | html_text |
| **fallback/unknown** | 18 | 0.00s | 0.000s | unknown |
| **pdfplumber** | 44 | 14.96s | 0.340s | docx, pdf_scan, pdf_text |
| **python-docx** | 22 | 22.95s | 1.043s | docx, pdf_scan, pdf_text |

### Детальная информация по библиотекам:

#### beautifulsoup
- Количество использований: 4
- Общее время: 0.04s
- Среднее время: 0.010s

Использование по этапам:
  - Route: html_text, Method: beautifulsoup
    - text_extraction: 0.002s
    - layout_analysis: 0.003s
    - total: 0.008s
  - Route: html_text, Method: beautifulsoup
    - text_extraction: 0.006s
    - layout_analysis: 0.004s
    - total: 0.014s
  - Route: html_text, Method: beautifulsoup
    - text_extraction: 0.003s
    - layout_analysis: 0.003s
    - total: 0.009s
  - Route: html_text, Method: beautifulsoup
    - text_extraction: 0.003s
    - layout_analysis: 0.004s
    - total: 0.010s

#### fallback/unknown
- Количество использований: 18
- Общее время: 0.00s
- Среднее время: 0.000s

Использование по этапам:
  - Route: unknown, Method: unknown
  - Route: None, Method: fallback
    - layout_analysis: 0.000s
    - total: 0.002s
  - Route: unknown, Method: unknown
  - Route: unknown, Method: unknown
  - Route: unknown, Method: unknown

#### pdfplumber
- Количество использований: 44
- Общее время: 14.96s
- Среднее время: 0.340s

Использование по этапам:
  - Route: pdf_scan, Method: pdfplumber_fallback
    - ocr: 0.006s
    - layout_analysis: 0.004s
    - total: 0.019s
  - Route: pdf_scan, Method: pdfplumber_fallback
    - ocr: 0.004s
    - layout_analysis: 0.004s
    - total: 0.013s
  - Route: pdf_scan, Method: pdfplumber_fallback
    - ocr: 0.009s
    - layout_analysis: 0.006s
    - total: 0.024s
  - Route: pdf_text, Method: pdfplumber_fallback
    - text_extraction: 0.292s
    - layout_analysis: 0.215s
    - total: 0.511s
  - Route: pdf_scan, Method: pdfplumber_fallback
    - ocr: 0.004s
    - layout_analysis: 0.003s
    - total: 0.012s

#### python-docx
- Количество использований: 22
- Общее время: 22.95s
- Среднее время: 1.043s

Использование по этапам:
  - Route: docx, Method: python-docx_fallback
    - text_extraction: 0.007s
    - layout_analysis: 0.012s
    - total: 0.022s
  - Route: docx, Method: python-docx_fallback
    - text_extraction: 0.005s
    - layout_analysis: 0.010s
    - total: 0.017s
  - Route: docx, Method: python-docx_fallback
    - text_extraction: 0.021s
    - layout_analysis: 0.020s
    - total: 0.043s
  - Route: docx, Method: python-docx_fallback
    - text_extraction: 3.559s
    - layout_analysis: 3.287s
    - total: 6.857s
  - Route: docx, Method: python-docx_fallback
    - text_extraction: 0.030s
    - layout_analysis: 0.036s
    - total: 0.071s

---

## ВЫВОДЫ

- **Успешность обработки:** 100.0%
- **Всего обработано:** 66 unit'ов
- **Успешно:** 66
- **Ошибок:** 0

- **Наиболее используемая библиотека:** pdfplumber (44 использований)

---

**Отчет сгенерирован:** 2025-11-20T14:15:25.982479
# OCR компоненты

Эта директория содержит файлы, связанные с OCR обработкой документов, но не относящиеся к PaddleOCR-VL.

## Содержимое

### Qwen3-VL тесты
- `test_qwen3_vision_ocr.py` - тестирование Qwen3-VL-8B для OCR
- `test_qwen3_vision_ast.py` - тестирование Qwen3-VL для AST
- `test_qwen3_simple.py` - простые тесты Qwen3
- `test_qwen3_ocr_metrics.py` - метрики OCR для Qwen3

### Granite тесты
- `CORRECT_granite_vlm_test.py` - правильное использование Granite-Docling VLM
- `debug_granite_metadata.py` - отладка метаданных Granite

### Общие OCR утилиты
- `test_inference.py` - тестирование подключения к Cloud.RU ML Inference
- `test_inference_simple.py` - простые тесты inference
- `s3_check.py` - проверка загрузки в S3

### Тесты исправлений
- `test_fixes.py` - тесты исправлений в обработке файлов
- `test_paths_fix.py` - тесты исправлений путей
- `test_protocol_document_fix.py` - тесты исправлений протокольных документов
- `test_protocol_processing_fix.py` - тесты исправлений обработки протоколов

## Примечание

Файлы, специфичные для PaddleOCR-VL, находятся в `ocr_vl/` директории проекта.

## История

Эти файлы были перемещены из `presort_root_files/paddle/` в процессе организации структуры проекта, так как они относятся к OCR, но не к PaddleOCR-VL.


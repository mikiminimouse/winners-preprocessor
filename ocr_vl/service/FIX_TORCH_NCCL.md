# Исправление проблемы torch/NCCL для PaddleOCR-VL

## Проблема

```
ImportError: /usr/local/lib/python3.10/site-packages/torch/lib/libtorch_cuda.so: undefined symbol: ncclCommWindowRegister
```

## Причина

Базовый образ `paddlex-genai-vllm-server` содержит несовместимые версии torch и NCCL библиотек.

## Решение

### 1. Переустановка torch в Dockerfile

Добавлено в Dockerfile:
```dockerfile
# Исправляем проблему torch/NCCL: переустанавливаем torch для CUDA 12.6
RUN python3 -m pip uninstall -y torch torchvision torchaudio || true && \
    python3 -m pip install --no-cache-dir \
    torch==2.4.1+cu121 \
    torchvision==0.19.1+cu121 \
    torchaudio==2.4.1+cu121 \
    --index-url https://download.pytorch.org/whl/cu121
```

### 2. Улучшенная обработка ошибок в server.py

- Добавлена обработка `ImportError` с детальными сообщениями
- Определение проблемы torch/NCCL по тексту ошибки
- Возврат корректного HTTP статуса (503) для недоступного сервиса

### 3. Альтернативный импорт PaddleOCR-VL

Пробуем несколько способов импорта:
```python
try:
    from paddleocr import PaddleOCRVL
except ImportError:
    try:
        from paddleocr.doc_vlm import DocVLM
        PaddleOCRVL = DocVLM
    except ImportError:
        PaddleOCRVL = None
```

## Что сделано

1. ✅ Переустановка torch с правильной версией для CUDA 12.1/12.6
2. ✅ Улучшенная обработка ошибок импорта
3. ✅ Альтернативные способы импорта PaddleOCR-VL
4. ✅ Детальное логирование проблем

## Тестирование

После обновления образа на Cloud.ru:

1. Проверить логи при старте - должны появиться:
   ```
   PaddleOCRVL imported successfully
   ```

2. Отправить тестовый OCR запрос и проверить:
   - PaddleOCR-VL инициализируется
   - OCR обработка работает
   - Результаты сохраняются в MD формат

## Версия образа

**Версия:** 1.0.5

**Digest:** (будет обновлен после push)

## Важно

⚠️ **Требуется пересборка образа** - изменения в Dockerfile требуют полной пересборки для установки новой версии torch.


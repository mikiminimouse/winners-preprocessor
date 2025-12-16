#!/bin/bash
# ============================================
# PaddleOCR-VL Service Entrypoint для локального тестирования
# Отключает GPU для работы на слабом оборудовании
# ============================================
# Режимы запуска:
#   server      - FastAPI сервер (по умолчанию)
#   ui          - Gradio Web UI
# ============================================

set -e

# Установка переменных окружения для путей к моделям
export PADDLEX_HOME=${PADDLEX_HOME:-/home/paddleocr/.paddlex}
export HF_HOME=${HF_HOME:-/home/paddleocr/.cache/huggingface}
export OUTPUT_DIR=${OUTPUT_DIR:-/workspace/output}
export LOG_LEVEL=${LOG_LEVEL:-DEBUG}
export COMPANY_NAME=${COMPANY_NAME:-"Winners Preprocessor"}
export DISABLE_MODEL_SOURCE_CHECK=${DISABLE_MODEL_SOURCE_CHECK:-True}

# Отключаем GPU для локального тестирования
export CUDA_VISIBLE_DEVICES=""

# Отключаем static graph mode
export FLAGS_enable_eager_mode=1
export FLAGS_eager_delete_tensor_gb=0
export FLAGS_use_mkldnn=0

# Определение режима: сначала из аргумента, затем автоматически по PORT
MODE="${1:-}"

# Автоматическое определение режима по PORT
# Если PORT установлен и соответствует известным значениям, используем его для определения режима
if [ -n "$PORT" ]; then
    if [ "$PORT" = "7860" ]; then
        MODE="ui"
    elif [ "$PORT" = "8081" ]; then
        MODE="server"
    fi
fi

# Если MODE все еще не установлен, используем значение по умолчанию
if [ -z "$MODE" ]; then
    MODE="ui"  # По умолчанию запускаем Web UI для отладки
fi

echo "============================================"
echo "PaddleOCR-VL Service (Local Testing - CPU Only)"
echo "============================================"
if [ -n "$PORT" ]; then
    echo "Режим: $MODE (определен по PORT=$PORT)"
else
    echo "Режим: $MODE"
fi
echo "GPU: Отключено для локального тестирования"
echo ""

# Создаем директории
mkdir -p /workspace/output /app/output /app/temp 2>/dev/null || true
chmod -R 777 /workspace/output /app/output /app/temp 2>/dev/null || true

case "$MODE" in
    server)
        echo "Запуск FastAPI handler на порту ${PORT:-8081}..."
        echo "Using offline image with pre-loaded models"
        echo "PADDLEX_HOME=$PADDLEX_HOME"
        echo "HF_HOME=$HF_HOME"
        echo "OUTPUT_DIR=$OUTPUT_DIR"
        echo "LOG_LEVEL=$LOG_LEVEL"
        echo "COMPANY_NAME=$COMPANY_NAME"
        echo "GPU: Отключено"
        echo "Dynamic graph mode enabled (FLAGS_enable_eager_mode=1)"
        
        cd /app
        exec uvicorn server:app --host 0.0.0.0 --port ${PORT:-8081} --workers 1 --log-level debug
        ;;
    ui)
        echo "Запуск Gradio Web UI на порту ${PORT:-7860}..."
        echo "Using offline image with pre-loaded models"
        echo "PADDLEX_HOME=$PADDLEX_HOME"
        echo "HF_HOME=$HF_HOME"
        echo "OUTPUT_DIR=$OUTPUT_DIR"
        echo "LOG_LEVEL=$LOG_LEVEL"
        echo "COMPANY_NAME=$COMPANY_NAME"
        echo "GPU: Отключено"
        echo "Dynamic graph mode enabled (FLAGS_enable_eager_mode=1)"
        
        cd /app
        exec python3 gradio_app.py
        ;;
    *)
        echo "Неизвестный режим: $MODE"
        echo ""
        echo "Доступные режимы:"
        echo "  server      - FastAPI сервер (порт 8081)"
        echo "  ui          - Gradio Web UI (порт 7860)"
        exit 1
        ;;
esac

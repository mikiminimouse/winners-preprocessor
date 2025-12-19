#!/bin/bash
# ============================================
# PaddleOCR-VL Service Enhanced Entrypoint
# ============================================
# Режимы запуска:
#   dual        - Запуск обоих сервисов (FastAPI на 8081, Gradio на 7860)
#   server      - Только FastAPI сервер (порт 8081)
#   ui          - Только Gradio Web UI (порт 7860) - serverless режим
# ============================================

set -e

# Установка переменных окружения для путей к моделям
export PADDLEX_HOME=${PADDLEX_HOME:-/home/paddleocr/.paddlex}
export HF_HOME=${HF_HOME:-/home/paddleocr/.cache/huggingface}
export OUTPUT_DIR=${OUTPUT_DIR:-/workspace/output}
export LOG_LEVEL=${LOG_LEVEL:-DEBUG}
export COMPANY_NAME=${COMPANY_NAME:-"Winners Preprocessor"}
# КРИТИЧНО: PaddleX читает именно PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK (а не DISABLE_MODEL_SOURCE_CHECK)
# Поэтому фиксируем оба значения в True для офлайн-режима без сетевых проверок.
export PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=${PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK:-True}
export DISABLE_MODEL_SOURCE_CHECK=${DISABLE_MODEL_SOURCE_CHECK:-True}

# КРИТИЧНО: Отключаем static graph mode
export FLAGS_enable_eager_mode=1
export FLAGS_eager_delete_tensor_gb=0
export FLAGS_use_mkldnn=0

# Определение режима только через переменную MODE
# По умолчанию serverless режим (только UI)
MODE="${MODE:-ui}"

echo "============================================"
echo "PaddleOCR-VL Service (Enhanced Mode)"
echo "============================================"
echo "Режим: $MODE"
echo ""

# Создаем директории
mkdir -p /workspace/output /app/output /app/temp 2>/dev/null || true
chmod -R 777 /workspace/output /app/output /app/temp 2>/dev/null || true

# Функция для корректного завершения
cleanup() {
    echo "Shutting down services..."
    # Завершаем процессы в обратном порядке
    if [ -n "$GRADIO_PID" ]; then
        kill $GRADIO_PID 2>/dev/null || true
    fi
    if [ -n "$FASTAPI_PID" ]; then
        kill $FASTAPI_PID 2>/dev/null || true
    fi
    # Ждем завершения всех процессов
    if [ -n "$GRADIO_PID" ]; then
        wait $GRADIO_PID 2>/dev/null || true
    fi
    if [ -n "$FASTAPI_PID" ]; then
        wait $FASTAPI_PID 2>/dev/null || true
    fi
    echo "Services stopped."
}

# Обрабатываем сигналы завершения
trap cleanup SIGTERM SIGINT EXIT

case "$MODE" in
    server)
        echo "Запуск FastAPI handler на порту 8081..."
        echo "Using offline image with pre-loaded models"
        echo "PADDLEX_HOME=$PADDLEX_HOME"
        echo "HF_HOME=$HF_HOME"
        echo "OUTPUT_DIR=$OUTPUT_DIR"
        echo "LOG_LEVEL=$LOG_LEVEL"
        echo "COMPANY_NAME=$COMPANY_NAME"
        echo "Dynamic graph mode enabled (FLAGS_enable_eager_mode=1)"
        
        cd /app
        exec uvicorn server:app --host 0.0.0.0 --port 8081 --workers 1 --log-level debug
        ;;
    ui)
        echo "Запуск Gradio Web UI на порту 7860 (serverless режим)..."
        echo "Using offline image with pre-loaded models"
        echo "PADDLEX_HOME=$PADDLEX_HOME"
        echo "HF_HOME=$HF_HOME"
        echo "OUTPUT_DIR=$OUTPUT_DIR"
        echo "LOG_LEVEL=$LOG_LEVEL"
        echo "COMPANY_NAME=$COMPANY_NAME"
        echo "Dynamic graph mode enabled (FLAGS_enable_eager_mode=1)"
        
        cd /app
        exec python3 gradio_app.py
        ;;
    dual)
        echo "Запуск обоих сервисов: FastAPI (8081) и Gradio UI (7860)..."
        echo "Using offline image with pre-loaded models"
        echo "PADDLEX_HOME=$PADDLEX_HOME"
        echo "HF_HOME=$HF_HOME"
        echo "OUTPUT_DIR=$OUTPUT_DIR"
        echo "LOG_LEVEL=$LOG_LEVEL"
        echo "COMPANY_NAME=$COMPANY_NAME"
        echo "Dynamic graph mode enabled (FLAGS_enable_eager_mode=1)"
        
        # Запускаем FastAPI handler в фоне
        echo "Starting FastAPI handler on port 8081..."
        cd /app
        uvicorn server:app --host 0.0.0.0 --port 8081 --workers 1 --log-level debug &
        FASTAPI_PID=$!
        echo "FastAPI PID: $FASTAPI_PID"
        
        # Запускаем Gradio UI в фоне
        echo "Starting Gradio UI on port 7860..."
        python3 gradio_app.py &
        GRADIO_PID=$!
        echo "Gradio PID: $GRADIO_PID"
        
        # Ждем завершения процессов
        wait $FASTAPI_PID $GRADIO_PID
        ;;
    *)
        echo "Неизвестный режим: $MODE"
        echo ""
        echo "Доступные режимы:"
        echo "  dual        - Запуск обоих сервисов (FastAPI на 8081, Gradio на 7860)"
        echo "  server      - Только FastAPI сервер (порт 8081)"
        echo "  ui          - Только Gradio Web UI (порт 7860) - serverless режим"
        exit 1
        ;;
esac

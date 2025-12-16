#!/bin/bash
# ============================================
# PaddleOCR-VL Service Enhanced Entrypoint
# ============================================
# Режимы запуска:
#   dual        - Запуск обоих сервисов (по умолчанию)
#   server      - Только FastAPI сервер
#   ui          - Только Gradio Web UI
# ============================================

set -e

# Установка переменных окружения для путей к моделям
export PADDLEX_HOME=${PADDLEX_HOME:-/home/paddleocr/.paddlex}
export HF_HOME=${HF_HOME:-/home/paddleocr/.cache/huggingface}
export OUTPUT_DIR=${OUTPUT_DIR:-/workspace/output}
export LOG_LEVEL=${LOG_LEVEL:-DEBUG}
export COMPANY_NAME=${COMPANY_NAME:-"Winners Preprocessor"}
export DISABLE_MODEL_SOURCE_CHECK=${DISABLE_MODEL_SOURCE_CHECK:-True}

# КРИТИЧНО: Отключаем static graph mode
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
    MODE="dual"  # По умолчанию запускаем оба сервиса
fi

echo "============================================"
echo "PaddleOCR-VL Service (Enhanced Mode)"
echo "============================================"
echo "Режим: $MODE"
if [ -n "$PORT" ]; then
    echo "PORT: $PORT (для одиночных режимов)"
fi
echo ""

# Создаем директории
mkdir -p /workspace/output /app/output /app/temp 2>/dev/null || true
chmod -R 777 /workspace/output /app/output /app/temp 2>/dev/null || true

# Функция для корректного завершения
cleanup() {
    echo "Shutting down services..."
    kill $FASTAPI_PID $GRADIO_PID 2>/dev/null || true
    wait $FASTAPI_PID $GRADIO_PID 2>/dev/null || true
    echo "Services stopped."
}

# Обрабатываем сигналы завершения
trap cleanup SIGTERM SIGINT

case "$MODE" in
    server)
        echo "Запуск FastAPI handler на порту ${PORT:-8081}..."
        echo "Using offline image with pre-loaded models"
        echo "PADDLEX_HOME=$PADDLEX_HOME"
        echo "HF_HOME=$HF_HOME"
        echo "OUTPUT_DIR=$OUTPUT_DIR"
        echo "LOG_LEVEL=$LOG_LEVEL"
        echo "COMPANY_NAME=$COMPANY_NAME"
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
        echo "  ui          - Только Gradio Web UI (порт 7860)"
        exit 1
        ;;
esac

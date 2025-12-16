#!/bin/bash
set -e

# Устанавливаем переменные окружения
export PADDLEX_HOME=${PADDLEX_HOME:-/home/paddleocr/.paddlex}
export HF_HOME=${HF_HOME:-/home/paddleocr/.cache/huggingface}
export OUTPUT_DIR=${OUTPUT_DIR:-/workspace/output}
export USE_VLM_API=true
export VLLM_URL=${VLLM_URL:-http://127.0.0.1:8080/v1/markdown}

# Настройка PaddlePaddle для dynamic graph mode
export FLAGS_enable_eager_mode=1
export FLAGS_eager_delete_tensor_gb=0
export FLAGS_use_mkldnn=0

echo "=========================================="
echo "Starting PaddleOCR-VL Service (Variant B)"
echo "=========================================="
echo "PADDLEX_HOME: $PADDLEX_HOME"
echo "HF_HOME: $HF_HOME"
echo "OUTPUT_DIR: $OUTPUT_DIR"
echo "VLLM_URL: ${VLLM_URL}"
echo "USE_VLM_API: ${USE_VLM_API}"
echo "=========================================="
echo ""

# Проверяем наличие моделей
if [ -d "$PADDLEX_HOME/official_models" ]; then
    echo "✅ Models directory found: $PADDLEX_HOME/official_models"
    model_count=$(find "$PADDLEX_HOME/official_models" -mindepth 1 -maxdepth 1 -type d | wc -l)
    echo "   Found $model_count model directories"
else
    echo "⚠️  Models directory not found: $PADDLEX_HOME/official_models"
fi

# (Optional) Запуск paddlex vLLM сервера, если базовый образ не запускает его автоматически
# Проверяем, не запущен ли уже vLLM
if [ "${USE_VLM_API}" = "true" ]; then
    vllm_port=${VLLM_PORT:-8080}
    if ! nc -z localhost $vllm_port 2>/dev/null; then
        echo "⚠️  vLLM server not detected on port $vllm_port"
        echo "   Assuming vLLM is started by base image or external service"
        # Если нужно запустить вручную, раскомментируйте:
        # echo "Starting vLLM server in background..."
        # /path/to/start_vllm.sh &
        # sleep 10
    else
        echo "✅ vLLM server detected on port $vllm_port"
    fi
fi

# Ожидание стабилизации сервисов
sleep 3

# Запуск warmup (non-blocking) для компиляции kernels, если доступен тестовый образ
if [ -f "/app/warmup.py" ]; then
    echo "Running warmup..."
    python3 /app/warmup.py || echo "Warmup skipped or failed (non-critical)"
fi

# Запуск FastAPI сервера
# Используем 1 worker для GPU-bound processing (масштабирование через k8s при необходимости)
echo ""
echo "Starting FastAPI server on port 8081..."
echo ""

cd /app
exec uvicorn server:app --host 0.0.0.0 --port 8081 --workers 1 --log-level info


#!/bin/bash
# ============================================
# Enhanced Health Check Script для PaddleOCR-VL Service
# Проверяет доступность сервисов в зависимости от режима запуска
# ============================================

# Определяем режим запуска только через переменную MODE
# По умолчанию режим dual
MODE="${MODE:-dual}"

# Если MODE не установлен или пустой, используем dual
if [ -z "$MODE" ]; then
    MODE="dual"
fi

echo "Health check for mode: $MODE"

# Функция для HTTP healthcheck (предпочтительно, потому что ss/netstat/lsof/nc могут отсутствовать в образе)
check_http() {
    local url="$1"
    if command -v curl >/dev/null 2>&1; then
        curl -fsS --max-time 2 "$url" >/dev/null 2>&1
        return $?
    fi
    return 127
}

check_http_with_retry() {
    local url="$1"
    local attempts="${2:-15}"  # ~30s max (15 * 2s + sleeps)
    local sleep_sec="${3:-2}"
    local i
    for i in $(seq 1 "$attempts"); do
        if check_http "$url"; then
            return 0
        fi
        sleep "$sleep_sec"
    done
    return 1
}

# Функция для проверки процесса по имени
check_process() {
    local process_name="$1"
    if pgrep -f "$process_name" > /dev/null; then
        return 0
    else
        return 1
    fi
}

# Функция для проверки порта
check_port() {
    local port="$1"
    # Проверяем через различные утилиты
    if command -v ss >/dev/null 2>&1; then
        if ss -tln | grep -q ":$port "; then
            return 0
        fi
    elif command -v netstat >/dev/null 2>&1; then
        if netstat -tln | grep -q ":$port "; then
            return 0
        fi
    elif command -v lsof >/dev/null 2>&1; then
        if lsof -i :$port | grep -q LISTEN; then
            return 0
        fi
    elif command -v nc >/dev/null 2>&1; then
        if nc -z localhost $port 2>/dev/null; then
            return 0
        fi
    fi
    return 1
}

# Проверка в зависимости от режима
case "$MODE" in
    server)
        # Проверяем FastAPI сервер (сначала HTTP, потом process/port)
        if check_http_with_retry "http://127.0.0.1:8081/health" 15 2; then
            echo "Health check passed - FastAPI /health is reachable on port 8081"
            exit 0
        fi
        if check_process "uvicorn.*server:app" && check_port 8081; then
            echo "Health check passed - FastAPI server is running on port 8081"
            exit 0
        else
            echo "Health check failed - FastAPI server is not running properly"
            exit 1
        fi
        ;;
    ui)
        # Проверяем Gradio UI (сначала HTTP, потом process/port)
        if check_http_with_retry "http://127.0.0.1:7860/" 15 2; then
            echo "Health check passed - Gradio UI is reachable on port 7860"
            exit 0
        fi
        if check_process "python.*gradio_app" && check_port 7860; then
            echo "Health check passed - Gradio UI is running on port 7860"
            exit 0
        else
            echo "Health check failed - Gradio UI is not running properly"
            exit 1
        fi
        ;;
    dual|*)
        # Проверяем оба сервиса
        FASTAPI_OK=false
        GRADIO_OK=false

        # Быстрый путь: HTTP checks
        if check_http_with_retry "http://127.0.0.1:8081/health" 15 2; then
            FASTAPI_OK=true
            echo "FastAPI /health is reachable on port 8081"
        fi
        if check_http_with_retry "http://127.0.0.1:7860/" 15 2; then
            GRADIO_OK=true
            echo "Gradio UI is reachable on port 7860"
        fi
        
        if [ "$FASTAPI_OK" = false ] && check_process "uvicorn.*server:app"; then
            if check_port 8081; then
                FASTAPI_OK=true
                echo "FastAPI server is running on port 8081"
            else
                echo "FastAPI server process found but port 8081 is not listening"
            fi
        else
            if [ "$FASTAPI_OK" = false ]; then
                echo "FastAPI server process not found"
            fi
        fi
        
        if [ "$GRADIO_OK" = false ] && check_process "python.*gradio_app"; then
            if check_port 7860; then
                GRADIO_OK=true
                echo "Gradio UI is running on port 7860"
            else
                echo "Gradio UI process found but port 7860 is not listening"
            fi
        else
            if [ "$GRADIO_OK" = false ]; then
                echo "Gradio UI process not found"
            fi
        fi
        
        if [ "$FASTAPI_OK" = true ] && [ "$GRADIO_OK" = true ]; then
            echo "Health check passed - Both services are running properly"
            exit 0
        elif [ "$FASTAPI_OK" = true ] && [ "$MODE" = "dual" ]; then
            echo "Partial health check passed - FastAPI server is running (Gradio may be starting)"
            exit 0
        elif [ "$GRADIO_OK" = true ] && [ "$MODE" = "dual" ]; then
            echo "Partial health check passed - Gradio UI is running (FastAPI may be starting)"
            exit 0
        else
            echo "Health check failed - One or both services are not running properly"
            exit 1
        fi
        ;;
esac
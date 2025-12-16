# Базовый офлайн-образ с предзагруженными моделями PaddleOCR-VL
# Модели уже включены в образ, не требуется доступ к интернету в runtime
FROM ccr-2vdh3abv-pub.cnc.bj.baidubce.com/paddlepaddle/paddleocr-vl:latest-gpu-sm120-offline

# Переключаемся на root для создания директорий и установки прав
USER root

# Установка системных зависимостей (если нужно)
# Примечание: curl может быть уже установлен в базовом образе
# RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Устанавливаем зависимости для FastAPI handler и Gradio UI
COPY ocr_vl/service/requirements.txt /tmp/requirements.txt
RUN python3 -m pip install --no-cache-dir -r /tmp/requirements.txt || true

# Создаем рабочую директорию
WORKDIR /app

# Создаем директории для выходных файлов
RUN mkdir -p /app/output /app/temp /app/models /app/assets && \
    chmod -R 777 /app

# Копируем код FastAPI handler и Gradio UI
COPY ocr_vl/service/server.py /app/server.py
COPY ocr_vl/service/gradio_app.py /app/gradio_app.py
COPY ocr_vl/service/assets/ /app/assets/
COPY ocr_vl/service/start.sh /app/start.sh
COPY ocr_vl/service/start_local.sh /app/start_local.sh
COPY ocr_vl/service/start_dual.sh /app/start_dual.sh
COPY ocr_vl/service/start_enhanced.sh /app/start_enhanced.sh
COPY ocr_vl/service/health_check.sh /app/health_check.sh

# Устанавливаем права на выполнение для скриптов
RUN chmod +x /app/start.sh /app/start_local.sh /app/start_dual.sh /app/start_enhanced.sh /app/health_check.sh

# Проверка наличия моделей в офлайн-образе
RUN python3 << 'EOF'
from pathlib import Path
import os

print("=" * 70)
print("ПРОВЕРКА ОФЛАЙН-ОБРАЗА С ПРЕДЗАГРУЖЕННЫМИ МОДЕЛЯМИ")
print("=" * 70)
print()

# Проверяем директории с моделями
model_dirs = [
    '/root/.paddlex',
    '/root/.cache',
    '/.paddlex',
    '/home/.paddlex',
]

models_found = False
for model_dir in model_dirs:
    if Path(model_dir).exists():
        files = list(Path(model_dir).rglob('*'))
        files_count = len([f for f in files if f.is_file()])
        
        if files_count > 0:
            total_size = sum(f.stat().st_size for f in files if f.is_file())
            print(f"✅ Найдена директория с моделями: {model_dir}")
            print(f"   Файлов: {files_count}")
            print(f"   Размер: {total_size / (1024*1024*1024):.2f} GB")
            models_found = True

if models_found:
    print()
    print("✅ Модели найдены в офлайн-образе!")
else:
    print("⚠️  Модели не найдены в стандартных директориях")
    print("⚠️  Они могут быть в других местах образа")

print("=" * 70)
EOF

# Возвращаемся к пользователю paddleocr
USER paddleocr

# Открываем порты
# 8081 - FastAPI handler (основной сервис OCR)
# 7860 - Gradio UI (веб-интерфейс)
EXPOSE 8081
EXPOSE 7860

# Entrypoint - выбор режима запуска
ENTRYPOINT ["/app/start_enhanced.sh"]

# Default command - Enhanced mode (оба сервиса)
CMD ["dual"]
FROM python:3.11-slim

# Установка системных зависимостей для magic и архиваторов
RUN apt-get update && apt-get install -y \
    libmagic1 \
    p7zip-full \
    unrar-free \
    unzip \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Установка unrar из исходников (если unrar-free недостаточно)
RUN wget -q https://www.rarlab.com/rar/unrarsrc-7.13.tar.gz -O /tmp/unrar.tar.gz && \
    cd /tmp && \
    tar -xzf unrar.tar.gz && \
    cd unrar && \
    make && \
    cp unrar /usr/local/bin/ && \
    rm -rf /tmp/unrar* || true

WORKDIR /app

# Копируем requirements и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код приложения
COPY main.py .

# Запускаем приложение
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]




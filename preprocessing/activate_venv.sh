#!/bin/bash

# Скрипт активации виртуального окружения для работы с preprocessing

echo "=== Активация виртуального окружения preprocessing ==="

# Путь к venv
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="$SCRIPT_DIR/venv"

# Проверка существования venv
if [ ! -d "$VENV_PATH" ]; then
    echo "❌ Виртуальное окружение не найдено: $VENV_PATH"
    echo "💡 Создайте venv командой: python3 -m venv venv"
    exit 1
fi

# Активация venv
echo "🔄 Активация venv..."
source "$VENV_PATH/bin/activate"

# Загрузка переменных окружения из .env файла
if [ -f "$SCRIPT_DIR/.env" ]; then
    echo "🔧 Загрузка переменных окружения из .env..."
    set -a
    source "$SCRIPT_DIR/.env"
    set +a
    echo "✅ Переменные окружения загружены"
fi

# Установка PYTHONPATH для корректного импорта модулей
export PYTHONPATH="$SCRIPT_DIR:$SCRIPT_DIR/../:$PYTHONPATH"

echo "✅ Venv активировано!"
echo "📁 PYTHONPATH: $PYTHONPATH"
echo "🐍 Python: $(which python)"
echo ""
echo "💡 Для запуска CLI используйте:"
echo "   python run_cli.py"
echo "   # или"
echo "   python -c 'from cli import main; main()'"
echo ""
echo "💡 Для выхода из venv выполните: deactivate"

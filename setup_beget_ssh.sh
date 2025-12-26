#!/bin/bash
# Быстрая настройка SSH для подключения к beget без пароля

echo "=== Настройка SSH для сервера beget ==="
echo ""

# Шаг 1: Создаем приватный ключ, если его нет
if [ ! -f ~/.ssh/id_ed25519 ]; then
    echo "Создание нового SSH ключа..."
    ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -C "vit@aspire-ubuntu-vit" -N ""
    chmod 600 ~/.ssh/id_ed25519
    echo "✓ Приватный ключ создан"
else
    echo "✓ Приватный ключ уже существует"
fi

# Шаг 2: Добавляем публичный ключ на сервер (если есть доступ по паролю)
echo ""
echo "Добавление публичного ключа на сервер..."
echo "Введите пароль для root@83.222.27.170 (если требуется):"
ssh-copy-id -i ~/.ssh/id_ed25519.pub root@83.222.27.170

# Шаг 3: Добавляем второй ключ (rsa) на сервер
echo ""
echo "Добавление второго ключа (beget-access-key) на сервер..."
echo "Подключитесь к серверу и выполните на сервере:"
echo ""
echo "mkdir -p ~/.ssh && chmod 700 ~/.ssh"
echo "echo 'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAAAgQCz2Cqn8rwfgYVFU2hyK3TKtKswVFI/lkiZfOz5fMaSNpYsHYIgSx11nLqAEhOWS0raaCaTk7pLM+m9I45FWCRECRbCm6gRgwXWHu3bR0UM/URQ6LruiJTPiBo9+lp/hJHHHzlXxV5v78a4QqTLpe7BAupBZpERZlXtd2wabdzvnw== beget-access-key; generated at 2025-02-08T15:57:48+03:00' >> ~/.ssh/authorized_keys"
echo "chmod 600 ~/.ssh/authorized_keys"
echo ""

# Шаг 4: Тестируем подключение
echo "Проверка подключения..."
ssh -i ~/.ssh/id_ed25519 -o ConnectTimeout=5 root@83.222.27.170 "echo '✓ Подключение успешно!'" 2>/dev/null && echo "✓ Все работает!" || echo "⚠ Проверьте, что ключи добавлены на сервер"

echo ""
echo "=== Готово ==="
echo "Теперь можно подключаться:"
echo "ssh -i ~/.ssh/id_ed25519 root@83.222.27.170"

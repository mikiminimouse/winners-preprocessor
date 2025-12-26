#!/bin/bash
# Скрипт для добавления SSH ключей на сервер beget

SERVER="83.222.27.170"
USER="root"
PUBLIC_KEYS=(
    "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIIvlYrgVyx5QNshaZNSEs4dJEgUrBzihyUgCjxPLgHAO vit@aspire-ubuntu-vit"
    "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAAAgQCz2Cqn8rwfgYVFU2hyK3TKtKswVFI/lkiZfOz5fMaSNpYsHYIgSx11nLqAEhOWS0raaCaTk7pLM+m9I45FWCRECRbCm6gRgwXWHu3bR0UM/URQ6LruiJTPiBo9+lp/hJHHHzlXxV5v78a4QqTLpe7BAupBZpERZlXtd2wabdzvnw== beget-access-key; generated at 2025-02-08T15:57:48+03:00"
)

echo "Добавление SSH ключей на сервер beget..."

# Создаем временный файл с ключами
TEMP_FILE=$(mktemp)
for key in "${PUBLIC_KEYS[@]}"; do
    echo "$key" >> "$TEMP_FILE"
done

# Копируем ключи на сервер
# Вариант 1: Если у вас уже есть доступ к серверу по паролю или другому ключу
echo "Копирование ключей на сервер..."
ssh "$USER@$SERVER" "mkdir -p ~/.ssh && chmod 700 ~/.ssh"

# Добавляем ключи в authorized_keys на сервере
cat "$TEMP_FILE" | ssh "$USER@$SERVER" "cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"

# Удаляем временный файл
rm "$TEMP_FILE"

echo "Ключи успешно добавлены на сервер!"
echo ""
echo "Теперь вы можете подключиться командой:"
echo "ssh -i ~/.ssh/id_ed25519 root@83.222.27.170"

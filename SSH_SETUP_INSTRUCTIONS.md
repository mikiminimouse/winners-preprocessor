# Инструкция по настройке SSH для подключения к серверу beget

## Важно понимать:
- **Публичные ключи** (те, что вы показали) → добавляются **НА СЕРВЕР** в `/root/.ssh/authorized_keys`
- **Приватный ключ** → должен быть **локально** в `~/.ssh/id_ed25519`

## Шаг 1: Проверка наличия приватного ключа локально

```bash
ls -la ~/.ssh/id_ed25519
```

### Если ключа НЕТ - создайте его:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -C "vit@aspire-ubuntu-vit"
# Нажмите Enter для пропуска пароля (или введите пароль, если нужен)
chmod 600 ~/.ssh/id_ed25519
```

### Если ключ ЕСТЬ - проверьте, что публичный ключ соответствует:

```bash
cat ~/.ssh/id_ed25519.pub
# Должен совпадать с: ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIIvlYrgVyx5QNshaZNSEs4dJEgUrBzihyUgCjxPLgHAO
```

## Шаг 2: Добавление публичных ключей на сервер beget

### Вариант A: Если у вас УЖЕ ЕСТЬ доступ к серверу (по паролю или другому ключу)

```bash
# Подключитесь к серверу
ssh root@83.222.27.170

# На сервере выполните:
mkdir -p ~/.ssh
chmod 700 ~/.ssh
nano ~/.ssh/authorized_keys
# Добавьте оба ключа в файл:
# ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIIvlYrgVyx5QNshaZNSEs4dJEgUrBzihyUgCjxPLgHAO vit@aspire-ubuntu-vit
# ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAAAgQCz2Cqn8rwfgYVFU2hyK3TKtKswVFI/lkiZfOz5fMaSNpYsHYIgSx11nLqAEhOWS0raaCaTk7pLM+m9I45FWCRECRbCm6gRgwXWHu3bR0UM/URQ6LruiJTPiBo9+lp/hJHHHzlXxV5v78a4QqTLpe7BAupBZpERZlXtd2wabdzvnw== beget-access-key; generated at 2025-02-08T15:57:48+03:00

chmod 600 ~/.ssh/authorized_keys
exit
```

### Вариант B: Автоматическое добавление через ssh-copy-id (только первый ключ)

```bash
ssh-copy-id -i ~/.ssh/id_ed25519.pub root@83.222.27.170
```

Затем вручную добавьте второй ключ (rsa) на сервер.

### Вариант C: Использование готового скрипта

```bash
chmod +x add_ssh_keys_to_beget.sh
./add_ssh_keys_to_beget.sh
```

## Шаг 3: Подключение к серверу

После добавления ключей на сервер, подключитесь:

```bash
ssh -i ~/.ssh/id_ed25519 root@83.222.27.170
```

## Шаг 4: (Опционально) Настройка SSH config для удобства

Добавьте в `~/.ssh/config`:

```
Host beget
    HostName 83.222.27.170
    User root
    IdentityFile ~/.ssh/id_ed25519
    Port 22
```

Тогда можно подключаться просто:
```bash
ssh beget
```

## Проверка работоспособности

```bash
# Проверка подключения
ssh -i ~/.ssh/id_ed25519 root@83.222.27.170 "echo 'Подключение успешно!'"
```

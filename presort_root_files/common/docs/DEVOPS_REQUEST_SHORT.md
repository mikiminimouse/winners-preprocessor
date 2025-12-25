# Запрос к DevOps: Данные для MCP Server

## Что нужно получить от DevOps

### 1. MongoDB подключение (обязательно)

```bash
# Адреса хостов MongoDB
mongoServer=host1:port1,host2:port2,host3:port3

# Пользователь с правами чтения
readAllUser=readonly_user

# Пароль пользователя
readAllPassword=secure_password

# SSL сертификат MongoDB
sslCertPath=/path/to/mongodb-ca.pem
```

### 2. Подтверждение структуры БД

- База: `protocols223`
- Коллекция: `purchaseProtocol`
- Поле даты: `loadDate` (datetime)

### 3. Сетевая доступность

- Доступ к MongoDB из окружения MCP сервера
- Порт для MCP сервера (по умолчанию 8000)

## Минимальный набор для старта

1. ✅ Адреса хостов MongoDB
2. ✅ Учетные данные (user + password)
3. ✅ SSL сертификат

## Подробности

См. `DEVOPS_REQUIREMENTS.md` для полного списка требований и вопросов.



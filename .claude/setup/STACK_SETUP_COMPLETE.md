# ✅ Установка стека Claude Code + AgentOS + Ralph завершена

## 📊 ИТОГОВАЯ СТРУКТУРА НАСТРОЕК

### 1️⃣ Глобальный уровень (/root/.claude/)

```
/root/.claude/
├── settings.json          # Глобальные настройки, модель, язык, плагины
├── hooks/                 # Глобальные хуки для всех проектов
│   ├── block-at-submit.sh        # Блокировка коммитов без тестов
│   ├── check-completion.sh       # Проверка завершения Ralph loop
│   └── validate-file-write.sh    # Валидация записи файлов
└── plugins/               # Установленные плагины

НАСТРОЕНО:
✅ Модель: sonnet
✅ Язык: Russian
✅ 11 плагинов включены (включая ralph-loop)
✅ 4 хука PreToolUse (WebSearch, git commit, dangerous commands, file write)
✅ 1 хук Stop (check-completion)
```

### 2️⃣ Уровень проекта (winners_preprocessor/.claude/)

```
winners_preprocessor/
├── .claude/
│   ├── settings.local.json         # Проектные настройки
│   ├── commands/agent-os/          # 6 команд AgentOS
│   │   ├── shape-spec.md           # Создание спецификации через Q&A
│   │   ├── write-spec.md           # Написание детальной спеки
│   │   ├── create-tasks.md         # Декомпозиция на задачи
│   │   ├── implement-tasks.md      # Реализация задач
│   │   ├── orchestrate-tasks.md    # Оркестрация выполнения
│   │   └── plan-product.md         # Планирование продукта
│   ├── agents/agent-os/            # 8 субагентов AgentOS
│   │   ├── spec-shaper.md          # Q&A для сбора требований
│   │   ├── spec-writer.md          # Написание спецификаций
│   │   ├── tasks-list-creator.md   # Создание списка задач
│   │   ├── implementer.md          # Реализация кода
│   │   ├── spec-initializer.md     # Инициализация спеки
│   │   ├── spec-verifier.md        # Проверка спецификации
│   │   ├── product-planner.md      # Планирование продукта
│   │   └── implementation-verifier.md  # Проверка реализации
│   ├── Architecture diagrams stack.md   # Диаграммы архитектуры
│   ├── Final stack specification.md     # Полная спецификация стека
│   └── Quick start.md                   # Быстрый старт
├── .mcp.json              # Конфигурация MCP серверов (ccglm-mcp)
├── agent-os/
│   ├── config.yml         # Конфигурация AgentOS
│   └── standards/         # 15 файлов стандартов кодирования
│       ├── backend/       # API, migrations, models, queries
│       ├── frontend/      # Components, CSS, accessibility, responsive
│       ├── global/        # Coding style, conventions, tech stack
│       └── testing/       # Test writing standards
└── scripts/
    ├── prepare-ralph-session.sh    # Подготовка Ralph session
    └── check-ralph-status.sh       # Проверка статуса выполнения

НАСТРОЕНО:
✅ Проектные разрешения (WebFetch, pip install, chmod, python3)
✅ MCP сервер: ccglm-mcp (GLM-4.7 для делегирования кода)
✅ Стиль вывода: Learning
✅ AgentOS команды установлены (6 команд)
✅ AgentOS субагенты установлены (8 агентов)
✅ Стандарты кодирования установлены (15 файлов)
```

### 3️⃣ Системный уровень (~/agent-os/)

```
/root/agent-os/             # Базовая установка AgentOS
├── config.yml              # Глобальная конфигурация
├── profiles/default/       # Профиль по умолчанию
└── scripts/                # Скрипты установки и обновления
    ├── project-install.sh
    ├── project-update.sh
    └── common-functions.sh

НАСТРОЕНО:
✅ AgentOS установлен глобально
✅ Профиль: default
✅ Claude Code команды: enabled
✅ Субагенты: enabled
```

---

## 🔄 КАК РАБОТАЕТ ИНТЕГРАЦИЯ

### Потоки данных

```
1. CONTEXT BUILDING (AgentOS)
   User → /shape-spec → Q&A → requirements.md
        → /write-spec → specification.md
        → /create-tasks → tasks.md

2. CONTEXT TRANSFER (Scripts)
   tasks.md → @fix_plan.md (checkbox format)
   spec.md → PROMPT.md (reference)

3. AUTONOMOUS EXECUTION (Ralph + Claude Code)
   Ralph Loop:
     ├─ Читает PROMPT.md
     ├─ Находит unchecked task в @fix_plan.md
     ├─ Claude анализирует → решает использовать GLM или сам
     ├─ Генерирует код
     ├─ PostToolUse hook → запускает тесты
     ├─ PreToolUse hook → проверяет тесты перед commit
     ├─ Commit → отмечает task [x]
     └─ Stop hook → проверяет завершение

4. QUALITY GATES (Hooks)
   PreToolUse:  git commit → block-at-submit.sh → проверка тестов
                dangerous → блокировка rm -rf, sudo, chmod 777
                file write → валидация путей

   Stop:        завершение → check-completion.sh → нужна ли помощь?

5. DELEGATION (GLM MCP)
   Boilerplate код → ccglm-mcp (GLM-4.7) → быстро и дешево
   Architecture → Claude (Sonnet 4.5) → качественно
```

---

## 🚀 ИСПОЛЬЗОВАНИЕ СТЕКА

### Базовый workflow

#### 1. Создание спецификации (5-10 минут)

```bash
cd /root/winners_preprocessor
claude

# В Claude Code:
> /shape-spec feature-name
# Отвечаете на 1-3 вопроса (остальные из qa-defaults.md)

> /write-spec
# Создается agent-os/specs/feature-name/spec.md

> /create-tasks
# Создается agent-os/specs/feature-name/tasks.md

> /exit
```

#### 2. Подготовка Ralph session (1 минута)

```bash
./scripts/prepare-ralph-session.sh feature-name

# Создает:
# - @fix_plan.md (задачи в checkbox формате)
# - PROMPT.md (инструкции для Ralph)
# - logs/session-YYYY-MM-DD-HHmm.md (лог сессии)
```

#### 3. Запуск автономного выполнения (overnight)

```bash
claude

> /ralph-loop "Execute PROMPT.md" \
    --max-iterations 100 \
    --timeout 15 \
    --completion-promise "ALL_TASKS_COMPLETE"
```

#### 4. Мониторинг (опционально, в другом терминале)

```bash
# Простой мониторинг
watch -n 10 'cat @fix_plan.md'

# Проверка статуса
./scripts/check-ralph-status.sh

# Просмотр логов
tail -f logs/session-*.md
```

#### 5. Review и merge (утром, 20 минут)

```bash
# Проверить прогресс
cat @fix_plan.md

# Проверить изменения
git log --oneline -10
git diff main...

# Проверить тесты
pytest  # или npm test

# Создать PR
gh pr create --title "feat: feature-name"
```

---

## 📋 ДОСТУПНЫЕ КОМАНДЫ

### Команды AgentOS (в Claude Code)

```bash
/shape-spec <feature-name>    # Интерактивное создание спецификации через Q&A
/write-spec                    # Написать детальную спецификацию
/create-tasks                  # Декомпозировать на задачи
/implement-tasks               # Реализовать задачи
/orchestrate-tasks             # Оркестрация выполнения задач
/plan-product                  # Планирование продукта
```

### Ralph команды

```bash
/ralph-loop <prompt> [options]  # Запуск автономного loop
  --max-iterations N            # Максимум итераций
  --timeout N                   # Таймаут в секундах
  --completion-promise "TEXT"   # Условие завершения
```

### Helper скрипты (в bash)

```bash
./scripts/prepare-ralph-session.sh <feature-name>  # Подготовка сессии
./scripts/check-ralph-status.sh                     # Проверка статуса
```

---

## 🎯 ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ

### Пример 1: Простая feature

```bash
# Вечер (10 минут)
claude
> /shape-spec user-profile-edit
> /write-spec
> /create-tasks
> /exit

./scripts/prepare-ralph-session.sh user-profile-edit

claude
> /ralph-loop "Execute PROMPT.md" --max-iterations 50

# Ночь: Ralph работает автономно

# Утро (15 минут)
./scripts/check-ralph-status.sh
git diff main...
pytest
gh pr create
```

### Пример 2: Если Ralph застрял

```bash
# Проверить статус
./scripts/check-ralph-status.sh

# Если есть .needs_human_intervention
cat .needs_human_intervention

# Решить проблему
# ... исправить код или дать дополнительный контекст ...

# Удалить маркер
rm .needs_human_intervention

# Продолжить
claude
> /ralph-loop "Continue from @fix_plan.md" --max-iterations 30
```

### Пример 3: Использование GLM для boilerplate

AgentOS автоматически делегирует простой код GLM MCP, но можно явно:

```bash
# В Claude Code, во время реализации:
"Use ccglm-mcp to generate CRUD operations for User model"
```

---

## 🔧 НАСТРОЙКА СТАНДАРТОВ ПРОЕКТА

### Обновление стандартов кодирования

Стандарты хранятся в `agent-os/standards/`. Отредактируйте файлы под ваш проект:

```bash
# Пример: обновить tech stack
nano agent-os/standards/global/tech-stack.md

# Добавить свои стандарты
cp my-custom-standard.md agent-os/standards/global/
```

AgentOS будет использовать эти стандарты при создании спецификаций и реализации кода.

---

## ⚙️ КОНФИГУРАЦИЯ

### Глобальная конфигурация (/root/.claude/settings.json)

- **model**: sonnet | opus | haiku
- **language**: Russian | English
- **hooks**: PreToolUse, PostToolUse, Stop
- **enabledPlugins**: список активных плагинов

### Проектная конфигурация (.claude/settings.local.json)

- **permissions.allow**: разрешенные операции
- **enabledMcpjsonServers**: список MCP серверов
- **outputStyle**: Learning | Concise | Detailed

### AgentOS конфигурация (agent-os/config.yml)

- **profile**: default | custom-profile-name
- **claude_code_commands**: true | false
- **use_claude_code_subagents**: true | false

---

## 🐛 TROUBLESHOOTING

### Ralph не перезапускается после ошибки

```bash
# Проверить Stop hook
cat ~/.claude/settings.json | grep -A 10 '"Stop"'
chmod +x ~/.claude/hooks/check-completion.sh
```

### Коммиты проходят без тестов

```bash
# Проверить Block-at-Submit hook
cat ~/.claude/settings.json | grep -A 5 'git commit'
bash ~/.claude/hooks/block-at-submit.sh
```

### GLM MCP не работает

```bash
# Проверить конфигурацию
cat .mcp.json

# Проверить сервер
python3 /root/ccglm-mcp/ccglm_mcp_server.py --help
```

### AgentOS команды не видны

```bash
# Проверить установку
ls -la .claude/commands/agent-os/

# Переустановить если нужно
cd ~/agent-os
./scripts/project-install.sh --re-install
```

---

## 📚 ПОЛЕЗНЫЕ ССЫЛКИ

- **AgentOS документация**: https://buildermethods.com/agent-os
- **Claude Code CLI**: https://docs.claude.ai/code
- **GLM API**: https://open.bigmodel.cn/
- **Ralph Plugin**: включен в Claude Code официальные плагины

---

## 🎉 ВСЁ ГОТОВО!

Ваш стек полностью настроен и готов к работе. Попробуйте создать первую feature:

```bash
cd /root/winners_preprocessor
claude
> /shape-spec test-feature
```

**Human time на фичу: ~30-60 минут**
**AI time: 4-8 часов (автономно)**
**Total wall time: overnight**

Счастливого кодирования! 🚀

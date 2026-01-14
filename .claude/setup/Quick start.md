# 🚀 Quick Start Guide
## Claude Code + Agent OS + Ralph Pipeline
### Запуск за 2 часа

---

## Минимальная установка (30 минут)

```bash
# 1. Установить Ralph plugin
claude
/plugin install ralph-wiggum
/exit

# 2. Установить Agent OS
git clone https://github.com/your-org/agent-os.git ~/agent-os
# Или: npm install -g agent-os-cli

# 3. Настроить GLM MCP в ~/.claude/settings.json
cat >> ~/.claude/settings.json << 'EOF'
{
  "mcpServers": {
    "glm-coder": {
      "command": "node",
      "args": ["/path/to/glm-mcp-server/index.js"],
      "env": {
        "Z_AI_API_KEY": "your-api-key"
      }
    }
  }
}
EOF

# 4. Создать основные hooks
mkdir -p ~/.claude/hooks

# Block-at-Submit hook
cat > ~/.claude/hooks/block-at-submit.sh << 'EOF'
#!/bin/bash
PASS_FILE="/tmp/tests-passed-$(basename $(pwd))"
if [ -f "$PASS_FILE" ]; then
    rm -f "$PASS_FILE"
    echo '{"decision": "approve"}'
else
    echo '{"decision": "deny", "reason": "Run tests first"}'
fi
EOF
chmod +x ~/.claude/hooks/block-at-submit.sh
```

---

## Инициализация проекта (30 минут)

```bash
cd your-project

# 1. Инициализировать Agent OS
agent-os init

# 2. Создать qa-defaults.md
cat > .claude/context/qa-defaults.md << 'EOF'
# Project Q&A Defaults

## Technology Stack
- Backend: Node.js + Express + TypeScript
- Frontend: React + TypeScript + Tailwind
- Database: PostgreSQL + Prisma
- Testing: Jest + Playwright

## Code Style
- 2 spaces indentation
- ESLint + Prettier
- Conventional commits
EOF

# 3. Создать CLAUDE.md
cat > CLAUDE.md << 'EOF'
# Project Memory

## Quick Reference
- Tech stack: @.claude/context/qa-defaults.md
- Current work: @fix_plan.md
- Specs: @agent-os/specs/

## Rules
- Test-first development
- Small commits (<200 lines)
- Descriptive commit messages
EOF

# 4. Создать helper script
mkdir -p scripts
cat > scripts/prepare-ralph.sh << 'EOF'
#!/bin/bash
SPEC="$1"
[ -z "$SPEC" ] && { echo "Usage: $0 <spec-name>"; exit 1; }

SPEC_DIR="agent-os/specs/$SPEC"
[ ! -d "$SPEC_DIR" ] && { echo "Spec not found: $SPEC_DIR"; exit 1; }

# Convert tasks to checklist
echo "# Implementation Plan: $SPEC" > @fix_plan.md
grep -E "^[-*] " "$SPEC_DIR/tasks.md" | sed 's/^[-*] /- [ ] /' >> @fix_plan.md

# Create PROMPT.md
cat > PROMPT.md << PROMPT
# Autonomous Execution: $SPEC

## Context
- Specification: @$SPEC_DIR/specification.md
- Tasks: @@fix_plan.md
- Rules: @CLAUDE.md

## Instructions
1. Find first unchecked task in @@fix_plan.md
2. Implement using TDD
3. Use /implement-with-glm for boilerplate
4. Mark task done: - [x]
5. Commit and proceed

## Exit
When ALL tasks [x]: <promise>ALL_TASKS_COMPLETE</promise>
PROMPT

echo "✅ Ready for Ralph"
EOF
chmod +x scripts/prepare-ralph.sh
```

---

## Первый запуск (1 час)

```bash
# 1. Создать спецификацию
claude
> /shape-spec test-feature
# Ответить на вопросы (1-3 минуты)
> /write-spec
> /create-tasks
> /exit

# 2. Подготовить для Ralph
./scripts/prepare-ralph.sh test-feature

# 3. Запустить Ralph
claude
> /ralph-loop "Execute PROMPT.md" \
    --max-iterations 20 \
    --completion-promise "ALL_TASKS_COMPLETE"

# 4. (В другом терминале) Мониторинг
watch -n 5 'cat @fix_plan.md'
```

---

## Базовые команды

```bash
# Проверить статус
cat @fix_plan.md                    # Прогресс задач
git log --oneline -10               # Последние коммиты
git diff main...                    # Все изменения

# Если нужна помощь
cat .needs_human_intervention       # Проверить блокеры
rm .needs_human_intervention        # После решения

# Завершение
npm test                            # Проверить тесты
gh pr create                        # Создать PR
```

---

## Типичный workflow

```
Evening (30 min):
  claude → /shape-spec feature → /write-spec → /create-tasks

  ./scripts/prepare-ralph.sh feature
  
  claude → /ralph-loop "Execute PROMPT.md" --max-iterations 100

Overnight:
  Ralph работает автономно
  Hooks обеспечивают качество
  Commits создаются автоматически

Morning (20 min):
  cat @fix_plan.md                  # Проверить прогресс
  git diff main...                  # Review изменений
  npm test                          # Проверить тесты
  gh pr create                      # Создать PR

Total human time: ~50 минут
```

---

## Troubleshooting

**Ralph не перезапускается:**
```bash
# Проверить Stop hook
cat ~/.claude/settings.json | jq '.hooks.Stop'
chmod +x ~/.claude/hooks/check-completion.sh
```

**Коммиты без тестов:**
```bash
# Проверить Block-at-Submit hook
cat ~/.claude/settings.json | jq '.hooks.PreToolUse'
bash ~/.claude/hooks/block-at-submit.sh
```

**GLM MCP не работает:**
```bash
# Проверить MCP сервер
echo $Z_AI_API_KEY
ps aux | grep glm-mcp
claude --restart-mcp
```

---

## Next Steps

1. **Расширить qa-defaults.md** — добавить больше project-specific answers
2. **Настроить уведомления** — ntfy.sh для alerting
3. **Создать skills** — autonomous-execution, error-recovery
4. **Добавить commands** — /start-feature, /implement-with-glm
5. **Настроить мониторинг** — tmux layout для live tracking

---

## Дополнительные ресурсы

📖 **Полная документация:** FINAL-STACK-SPECIFICATION.md  
🔧 **Примеры настроек:** В разделе "Конфигурация"  
🎯 **Best practices:** В разделе "Оптимизация"  
❓ **FAQ:** В разделе "Troubleshooting"

---

*Этот Quick Start даёт минимальную рабочую конфигурацию.*  
*Для production использования см. полную спецификацию.*
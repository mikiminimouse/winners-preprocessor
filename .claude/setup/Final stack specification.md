# 🏗️ Финальная спецификация стека разработки
## Claude Code CLI + Agent OS + Ralph (Anthropic)
### Полностью интегрированный автономный pipeline с Human-in-the-Loop

---

## 📋 Executive Summary

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ФИНАЛЬНЫЙ СТЕК v1.0                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ОТКАЗЫВАЕМСЯ ОТ:                                                          │
│   ❌ Claude-Flow (слишком сложная обёртка)                                  │
│   ❌ Vibe Kanban (отдельный продукт, избыточен)                            │
│                                                                              │
│   ИСПОЛЬЗУЕМ:                                                               │
│   ✅ Claude Code CLI (нативная основа)                                      │
│   ✅ Agent OS (spec-driven development)                                     │
│   ✅ Ralph (Anthropic official plugin)                                      │
│   ✅ GLM MCP (делегирование кодинга)                                        │
│                                                                              │
│   ФИЛОСОФИЯ:                                                                 │
│   "Максимум нативных возможностей Claude Code,                              │
│    минимум сторонних обёрток"                                               │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 1️⃣ Архитектура стека

### 1.1 Компоненты и их роли

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    АРХИТЕКТУРА СТЕКА (СЛОИ)                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   СЛОЙ 1: Context Building (Agent OS)                                       │
│   ════════════════════════════════════                                      │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  • /shape-spec → Интерактивный сбор требований (Q&A)                │   │
│   │  • /write-spec → Создание формальной спецификации                   │   │
│   │  • /create-tasks → Декомпозиция на задачи                           │   │
│   │                                                                      │   │
│   │  Outputs:                                                            │   │
│   │  └─ agent-os/specs/{feature}/                                       │   │
│   │     ├── requirements.md    (результат Q&A)                           │   │
│   │     ├── specification.md   (детальная спека)                        │   │
│   │     └── tasks.md           (список задач)                           │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    ▼                                         │
│   СЛОЙ 2: Task Execution (Ralph + Claude Code)                              │
│   ══════════════════════════════════════════                                │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  Ralph Plugin:                                                       │   │
│   │  ├── Stop Hook → Перехватывает выход Claude                         │   │
│   │  ├── Loop Control → Проверяет completion promise                    │   │
│   │  └── Re-injection → Продолжает работу если не готово               │   │
│   │                                                                      │   │
│   │  Claude Code CLI (нативный):                                        │   │
│   │  ├── Commands → Кастомные slash-команды                             │   │
│   │  ├── Skills → Автоприменяемые знания                                │   │
│   │  ├── Hooks → Перехваты операций (Pre/Post)                          │   │
│   │  ├── Subagents → Делегирование подзадач                             │   │
│   │  ├── Memories → Контекст между сессиями                             │   │
│   │  └── MCP Servers → Интеграция с внешними tools                      │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    ▼                                         │
│   СЛОЙ 3: Code Delegation (GLM MCP)                                         │
│   ═══════════════════════════════════                                       │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  GLM MCP Server:                                                     │   │
│   │  ├── generate_code → Генерация boilerplate                          │   │
│   │  ├── complete_code → Автодополнение                                 │   │
│   │  ├── generate_tests → Генерация тестов                              │   │
│   │  └── refactor_code → Рефакторинг                                    │   │
│   │                                                                      │   │
│   │  Стратегия: Claude для архитектуры, GLM для кодинга                │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    ▼                                         │
│   СЛОЙ 4: Quality Gates (Hooks)                                             │
│   ════════════════════════════════                                          │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  PreToolUse Hooks:                                                   │   │
│   │  ├── Block dangerous commands                                       │   │
│   │  ├── Validate file operations                                       │   │
│   │  └── Block-at-Submit (тесты перед commit)                           │   │
│   │                                                                      │   │
│   │  PostToolUse Hooks:                                                  │   │
│   │  ├── Run tests after code changes                                   │   │
│   │  ├── Type checking                                                   │   │
│   │  ├── Linting                                                         │   │
│   │  └── Create test pass marker                                        │   │
│   │                                                                      │   │
│   │  Stop Hooks:                                                         │   │
│   │  ├── Check completion status                                        │   │
│   │  ├── Error escalation to human                                      │   │
│   │  └── Session logging                                                │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    ▼                                         │
│   СЛОЙ 5: Visualization (Terminal-based)                                    │
│   ═══════════════════════════════════════                                   │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  Glow:                                                               │   │
│   │  └── Рендеринг @fix_plan.md с checkboxes                           │   │
│   │                                                                      │   │
│   │  ralph-monitor (опционально):                                       │   │
│   │  └── Live статус Ralph loop                                         │   │
│   │                                                                      │   │
│   │  tmux/screen (опционально):                                         │   │
│   │  └── Мультиплексирование терминалов                                 │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Информационные потоки

```
User Input
    │
    ▼
Agent OS (/shape-spec)
    │
    ├── Задаёт уточняющие вопросы (Q&A)
    ├── Читает qa-defaults.md для автоответов
    └── Создаёт requirements.md
    │
    ▼
Agent OS (/write-spec)
    │
    └── Создаёт specification.md
    │
    ▼
Agent OS (/create-tasks)
    │
    └── Создаёт tasks.md
    │
    ▼
Context Transfer (скрипты)
    │
    ├── tasks.md → @fix_plan.md (checkbox format)
    └── specification.md → inject в PROMPT.md
    │
    ▼
Ralph Loop
    │
    ├── Читает PROMPT.md
    ├── Читает @fix_plan.md
    │   │
    │   ▼
    │   Claude Code CLI
    │   │
    │   ├── Выполняет задачу
    │   ├── Использует MCP (GLM) для кодинга
    │   ├── Hooks проверяют качество
    │   └── Обновляет @fix_plan.md
    │   │
    │   ▼
    │   Stop Hook (Ralph)
    │   │
    │   ├── Проверяет completion promise
    │   │
    │   ├── Если НЕ готово → re-inject, continue loop
    │   └── Если готово → exit
    │
    └── Loop continues until ALL_TASKS_COMPLETE
    │
    ▼
Human Review
    │
    ├── Review git diff
    ├── Run tests
    └── Merge
```

---

## 2️⃣ Установка и настройка

### 2.1 Prerequisites

```bash
# Минимальные требования
node >= 18.0.0
npm >= 9.0.0
claude-code-cli >= 2.1.0
git >= 2.30.0

# Опционально
glow >= 1.5.0         # Для красивого отображения markdown
tmux >= 3.0           # Для мультиплексирования
ntfy.sh account       # Для push-уведомлений
```

### 2.2 Установка Claude Code CLI (если ещё нет)

```bash
# macOS
brew install anthropic/claude/claude

# Linux
curl -fsSL https://claude.ai/install.sh | sh

# Проверка
claude --version
```

### 2.3 Установка Agent OS

```bash
# Клонировать репозиторий
git clone https://github.com/your-username/agent-os.git
cd agent-os

# Или установить как npm пакет (если доступен)
npm install -g agent-os-cli

# Инициализация в проекте
cd your-project
agent-os init
```

**Структура после инициализации:**
```
your-project/
├── agent-os/
│   ├── product/
│   │   ├── mission.md
│   │   ├── roadmap.md
│   │   └── tech-stack.md
│   ├── profiles/
│   │   └── default/
│   │       └── standards/
│   │           ├── global/
│   │           ├── frontend/
│   │           └── backend/
│   └── specs/
│       └── (будут создаваться фичи)
└── .claude/
    └── commands/
        ├── plan-product.md
        ├── create-spec.md
        ├── write-spec.md
        ├── create-tasks.md
        └── implement-tasks.md
```

### 2.4 Установка Ralph Plugin

```bash
# Метод 1: Через Claude CLI (рекомендуется)
claude
/plugin install ralph-wiggum
/plugins list

# Метод 2: Вручную (если Anthropic plugin недоступен)
# Использовать frankbria/ralph-on-steroids
git clone https://github.com/frankbria/ralph-on-steroids.git ~/.claude/plugins/ralph
```

### 2.5 Настройка GLM MCP Server

```bash
# Установка GLM MCP
npm install -g @glm/mcp-server

# Или клонировать custom версию
git clone https://github.com/your-org/glm-mcp-server.git ~/glm-mcp

# Добавить в ~/.claude/settings.json
cat >> ~/.claude/settings.json << 'EOF'
{
  "mcpServers": {
    "glm-coder": {
      "command": "node",
      "args": ["/path/to/glm-mcp-server/index.js"],
      "env": {
        "Z_AI_API_KEY": "your-zhipu-api-key"
      }
    }
  }
}
EOF
```

---

## 3️⃣ Конфигурация Claude Code

### 3.1 ~/.claude/settings.json (полная конфигурация)

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash(git commit*)",
        "hooks": [
          {
            "type": "command",
            "command": "~/.claude/hooks/block-at-submit.sh"
          }
        ]
      },
      {
        "matcher": "Bash(rm -rf*)|Bash(sudo *)|Bash(chmod 777*)",
        "hooks": [
          {
            "type": "command",
            "command": "echo '{\"decision\": \"deny\", \"reason\": \"Dangerous command blocked\"}'"
          }
        ]
      },
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "~/.claude/hooks/validate-file-write.sh"
          }
        ]
      }
    ],
    
    "PostToolUse": [
      {
        "matcher": "Edit:*.ts|Edit:*.tsx|Edit:*.js|Edit:*.jsx",
        "hooks": [
          {
            "type": "command",
            "command": "npm run type:check --noEmit 2>/dev/null || true"
          }
        ]
      },
      {
        "matcher": "Edit:src/**/*",
        "hooks": [
          {
            "type": "command",
            "command": "npm test -- --related --passWithNoTests 2>/dev/null && touch /tmp/tests-passed-$(basename $(pwd)) || true"
          }
        ]
      }
    ],
    
    "PermissionRequest": [
      {
        "matcher": "Bash(npm *)|Bash(npx *)|Bash(git status*)|Bash(git diff*)",
        "hooks": [
          {
            "type": "command",
            "command": "echo '{\"decision\": \"approve\", \"reason\": \"Safe command\"}'"
          }
        ]
      }
    ],
    
    "Stop": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "~/.claude/hooks/check-completion.sh"
          }
        ]
      }
    ]
  },
  
  "mcpServers": {
    "glm-coder": {
      "command": "node",
      "args": ["/Users/you/glm-mcp-server/index.js"],
      "env": {
        "Z_AI_API_KEY": "${Z_AI_API_KEY}"
      }
    }
  },
  
  "permissions": {
    "allow": [
      "Bash(npm *)",
      "Bash(npx *)",
      "Bash(git status*)",
      "Bash(git diff*)",
      "Bash(git add*)",
      "Read",
      "Write",
      "Edit",
      "Glob",
      "Grep",
      "mcp__glm-coder__generate_code",
      "mcp__glm-coder__complete_code"
    ],
    "deny": [
      "Bash(rm -rf /)",
      "Bash(sudo rm *)",
      "Bash(chmod 777 *)"
    ]
  }
}
```

### 3.2 Hooks Scripts

#### ~/.claude/hooks/block-at-submit.sh

```bash
#!/bin/bash
# Block-at-Submit Pattern: Prevent commits without passing tests

PROJECT_NAME=$(basename $(pwd))
PASS_FILE="/tmp/tests-passed-${PROJECT_NAME}"

# Проверка наличия маркера успешных тестов
if [ -f "$PASS_FILE" ]; then
    # Тесты прошли - разрешить commit
    rm -f "$PASS_FILE"  # One-time use
    echo '{"decision": "approve", "reason": "Tests passed, commit allowed"}'
else
    # Тестов не было или они failed
    echo '{"decision": "deny", "reason": "Tests must pass before commit. Run tests first, then retry commit."}'
fi
```

#### ~/.claude/hooks/check-completion.sh

```bash
#!/bin/bash
# Проверка завершения работы или необходимости human intervention

NEEDS_HUMAN_FILE=".needs_human_intervention"

# Читаем stop reason из stdin
STOP_INPUT=$(cat)
STOP_REASON=$(echo "$STOP_INPUT" | jq -r '.stop_reason // empty')

# Проверка на ошибки или блокировки
if echo "$STOP_REASON" | grep -qiE "blocked|error|failed|cannot|unable|stuck"; then
    # Создать маркер для human intervention
    echo "{
      \"reason\": \"$STOP_REASON\",
      \"timestamp\": \"$(date -Iseconds)\",
      \"context\": {
        \"cwd\": \"$(pwd)\",
        \"git_branch\": \"$(git branch --show-current 2>/dev/null || echo 'unknown')\"
      }
    }" > "$NEEDS_HUMAN_FILE"
    
    # Отправить notification (если настроено)
    if command -v ntfy &> /dev/null && [ -n "$NTFY_TOPIC" ]; then
        ntfy publish "$NTFY_TOPIC" "🚨 Agent needs help: $STOP_REASON"
    fi
    
    echo '{"continue": false, "stopReason": "Human intervention needed. Check .needs_human_intervention file."}'
else
    # Нормальное завершение
    echo '{"continue": true}'
fi
```

#### ~/.claude/hooks/validate-file-write.sh

```bash
#!/bin/bash
# Валидация операций записи файлов

TOOL_INPUT=$(cat)
FILE_PATH=$(echo "$TOOL_INPUT" | jq -r '.path // empty')

# Блокировать запись в критичные файлы
PROTECTED_PATTERNS=(
    "^\.env$"
    "^\.git/"
    "^node_modules/"
    "package-lock\.json$"
)

for pattern in "${PROTECTED_PATTERNS[@]}"; do
    if echo "$FILE_PATH" | grep -qE "$pattern"; then
        echo "{\"decision\": \"deny\", \"reason\": \"Protected file: $FILE_PATH\"}"
        exit 0
    fi
done

echo '{"decision": "approve"}'
```

### 3.3 Commands

#### .claude/commands/autonomous/start-feature.md

```markdown
---
description: Start working on a feature with full context loading and autonomous execution
argument-hint: <feature-name>
---

# Start Feature: Autonomous Mode

Feature: $ARGUMENTS

## Phase 1: Load Context

1. **Load Agent OS context**:
   - Read specification: @agent-os/specs/$ARGUMENTS/specification.md
   - Read tasks: @agent-os/specs/$ARGUMENTS/tasks.md
   - Read project rules: @CLAUDE.md
   - Read QA defaults: @.claude/context/qa-defaults.md

2. **Verify context completeness**:
   - [ ] Specification exists and is valid
   - [ ] Tasks are broken down and clear
   - [ ] No missing prerequisites
   - [ ] No blocking .needs_human_intervention file

If any check fails → report and wait for human.

## Phase 2: Setup Execution Environment

1. **Prepare tracking**:
   - Convert tasks.md to @fix_plan.md with checkboxes
   - Initialize session log
   - Record starting context

2. **Verify tooling**:
   - [ ] Tests are passing
   - [ ] No uncommitted changes (or stashed intentionally)
   - [ ] Dependencies installed

## Phase 3: Autonomous Implementation

For each unchecked task in @fix_plan.md:

1. **Analyze task**:
   - Understand requirements
   - Identify affected files
   - Plan approach

2. **Implement** (TDD):
   - Write test first (if applicable)
   - Use /implement-with-glm for boilerplate
   - Implement minimal code to pass
   - Run tests (automatic via PostToolUse hook)
   - Refactor if needed

3. **Commit**:
   - Tests must pass (enforced by Block-at-Submit)
   - Write descriptive commit message
   - Update @fix_plan.md: mark task [x]

4. **Continue**:
   - Proceed to next unchecked task
   - If error > 3 times on same task → escalate to human

## Exit Conditions

Stop when:
- ✅ All tasks in @fix_plan.md are [x]
- ⚠️ Consecutive errors threshold reached
- ⚠️ Human intervention explicitly requested
- ⚠️ Context window > 80% full

## Final Actions

1. Update @fix_plan.md with final status
2. Create session summary in logs/
3. Output completion status:
   - If complete: `<promise>ALL_TASKS_COMPLETE</promise>`
   - If need help: `<promise>NEEDS_HUMAN_HELP</promise>`
```

#### .claude/commands/autonomous/implement-with-glm.md

```markdown
---
description: Delegate code generation to GLM MCP, Claude reviews and integrates
argument-hint: <task-description>
---

# Implement with GLM Delegation

Task: $ARGUMENTS

## Strategy: Claude (architecture) + GLM (coding)

1. **Claude analyzes** (current agent):
   - Understand task requirements
   - Identify affected files
   - Design approach
   - Specify test requirements

2. **Call GLM MCP** for code generation:
   ```
   Use MCP tool: mcp__glm-coder__generate_code
   Input: {
     "task": "$ARGUMENTS",
     "context": {
       "files": [relevant files],
       "framework": "detected from package.json",
       "style": "project conventions"
     }
   }
   ```

3. **Claude reviews** GLM output:
   - Check adherence to requirements
   - Validate code quality
   - Ensure test coverage
   - Refactor if needed

4. **Integrate**:
   - Apply changes to codebase
   - Run tests
   - Commit if passing

## When to use GLM:

✅ Use GLM for:
- Boilerplate code
- CRUD operations
- Test scaffolding
- Data transformation functions
- API endpoint implementations

❌ Claude handles:
- Architecture decisions
- Complex algorithms
- Security-critical code
- Performance optimization
- Code review and refactoring
```

#### .claude/commands/autonomous/request-human.md

```markdown
---
description: Request human intervention when stuck or unclear
argument-hint: <reason>
---

# Request Human Intervention

Reason: $ARGUMENTS

## Actions:

1. **Create intervention request file**:
   
   Write to `.needs_human_intervention`:
   ```json
   {
     "timestamp": "[current ISO timestamp]",
     "reason": "$ARGUMENTS",
     "context": {
       "current_task": "[from @fix_plan.md]",
       "last_action": "[what was attempted]",
       "error": "[if applicable]",
       "attempts": "[number of retry attempts]"
     },
     "suggestions": [
       "[possible solution 1]",
       "[possible solution 2]"
     ],
     "severity": "[low|medium|high]"
   }
   ```

2. **Update @fix_plan.md**:
   
   Add blocker note:
   ```markdown
   > ⚠️ **BLOCKED**: $ARGUMENTS
   > Waiting for human input.
   > Created: [timestamp]
   ```

3. **Send notification** (if configured):
   - Push notification via ntfy
   - Update status.json

4. **Stop execution gracefully**:
   - Save current state
   - Output: `<promise>NEEDS_HUMAN_HELP</promise>`
   - Do not continue until human responds

## Human Response Flow

When human returns:
1. They read `.needs_human_intervention`
2. They provide answer/fix
3. They delete the marker file
4. Work continues (either resume Ralph or manual /continue)
```

### 3.4 Skills

#### .claude/skills/autonomous-execution/SKILL.md

```markdown
---
name: autonomous-execution
description: Patterns for autonomous development without constant human supervision. Use when working in Ralph loop or overnight runs.
tools: Read, Write, Edit, Bash, Glob, Grep, mcp__glm-coder__*
---

# Autonomous Execution Skill

## When to Activate

This skill auto-activates when:
- Working in Ralph loop (/ralph-loop active)
- PROMPT.md or @fix_plan.md detected in workspace
- User explicitly requests autonomous mode

## Core Principles

### 1. Fail Fast, Recover Gracefully

- If something doesn't work after 2 attempts → try alternative approach
- After 3 failed alternatives → request human help via /request-human
- Always leave codebase in working state (passing tests)

### 2. Small, Atomic Changes

- Each commit should be independently reviewable
- Keep diffs under 200 lines when possible
- One logical change per commit
- Descriptive commit messages following convention:
  ```
  <type>(<scope>): <description>
  
  [optional body]
  
  [optional footer]
  ```

### 3. Test Before Commit

- Run relevant tests after each code change (automatic via hooks)
- Don't attempt commit if tests fail (enforced by Block-at-Submit)
- Create tests for new functionality before implementation (TDD)
- Use GLM MCP for test scaffolding when appropriate

### 4. Progress Tracking

- Update @fix_plan.md after completing each task
- Mark tasks: `- [x] Task description`
- Add session notes for important decisions
- Log blockers and questions in comments

### 5. Context Preservation

- Don't lose important context on errors
- Save working state before risky operations
- Use git stash for experimental changes
- Reference specifications when making decisions

## Delegation Strategy: Claude vs GLM

### Use GLM MCP for:
- Boilerplate code generation
- CRUD operations
- Test scaffolding
- Data transformations
- Repetitive patterns

### Claude handles:
- Architecture decisions
- Complex business logic
- Security-critical code
- Code review and refactoring
- Integration and orchestration

Example delegation:
```
Task: "Create REST endpoint for user registration"

Claude analyzes:
- Design API contract
- Identify validation requirements
- Specify error handling

GLM generates:
- Controller boilerplate
- Validation schemas
- Test scaffolding

Claude reviews & integrates:
- Verify security practices
- Add business logic
- Refactor for clarity
```

## Error Recovery Patterns

### Compilation Error
1. Read error message carefully
2. Fix the obvious issue
3. If unclear → search codebase for similar patterns
4. If still stuck after 3 attempts → try alternative approach
5. If 3 alternatives fail → /request-human

### Test Failure
1. Read test output and failure message
2. Identify failing assertion
3. Check if real bug or test issue
4. Fix and re-run
5. If flaky → investigate environment/timing
6. If stuck → /request-human with test output

### Merge Conflict
1. Identify conflicting files
2. Understand both changes
3. Merge semantically (preserve intent of both changes)
4. Run tests after resolution
5. If complex conflict → /request-human

### Stuck on Task
If attempting same task > 3 times:
1. Document attempts in @fix_plan.md
2. Outline what was tried
3. /request-human with context
4. Move to next task if possible (mark current as blocked)

## Quality Gates (enforced by hooks)

Before each commit:
- [ ] Tests pass (enforced automatically)
- [ ] No linting errors
- [ ] Type checking passes (TypeScript)
- [ ] No TODO comments for critical issues
- [ ] Commit message is descriptive

## Session Logging

Create logs/session-YYYY-MM-DD-HHmm.md with:
```markdown
# Session Log: [feature name]

**Started**: [timestamp]
**Branch**: [git branch]

## Completed Tasks
- [x] Task 1: Description
  - Approach: ...
  - Files: ...
  - Commit: abc123

## Blocked Tasks
- [ ] Task 2: Description
  - Blocker: ...
  - Attempted: ...
  - Needs: ...

## Decisions Made
1. Chose X over Y because...
2. Refactored Z to improve...

## Context for Next Session
- Current state: ...
- Next steps: ...
```

## Checklist Before Stopping

- [ ] All started tasks are either completed or documented as blocked
- [ ] Tests are passing
- [ ] No uncommitted changes (or stashed with clear note)
- [ ] @fix_plan.md is updated with current status
- [ ] Session log created
- [ ] .needs_human_intervention created if blocked
```

#### .claude/skills/error-recovery/SKILL.md

```markdown
---
name: error-recovery
description: Systematic approach to recovering from errors in autonomous execution
tools: Read, Write, Edit, Bash
---

# Error Recovery Skill

## Circuit Breaker Pattern

Track consecutive errors on same operation:

```
Error Count: 0
├── Attempt operation
│   ├── Success → Reset count to 0
│   └── Error → Increment count
│       ├── Count < 3 → Retry with variation
│       ├── Count = 3 → Try alternative approach
│       └── Count > 5 → Escalate to human
```

## Error Categories & Responses

### 1. Syntax/Compilation Errors
- **Strategy**: Fast feedback loop
- **Action**:
  1. Read error message
  2. Fix syntax
  3. Re-run
- **Escalation**: After 2 attempts

### 2. Test Failures
- **Strategy**: Understand intent
- **Action**:
  1. Read test and assertion
  2. Verify expectation is correct
  3. Fix implementation or test
  4. Re-run
- **Escalation**: After 3 attempts

### 3. Runtime Errors
- **Strategy**: Defensive programming
- **Action**:
  1. Add error handling
  2. Add logging
  3. Add null checks
  4. Re-run with better observability
- **Escalation**: After 4 attempts

### 4. Integration Errors
- **Strategy**: Isolation testing
- **Action**:
  1. Test component in isolation
  2. Verify dependencies
  3. Check environment variables
  4. Add integration test
- **Escalation**: After 3 attempts

### 5. Performance Issues
- **Strategy**: Measure, don't guess
- **Action**:
  1. Add performance measurement
  2. Profile the code
  3. Identify bottleneck
  4. Optimize specific area
- **Escalation**: Immediate (requires human judgment)

## Retry Strategies

### Retry with Variation
Don't retry the exact same thing:
- Change variable names
- Try different library function
- Adjust approach slightly
- Add more error handling

### Alternative Approaches
If retry fails 3 times:
1. Research alternative pattern in codebase
2. Try completely different implementation
3. Simplify requirements temporarily
4. Document trade-off

### Graceful Degradation
If all approaches fail:
1. Implement minimal working version
2. Add TODO for improvement
3. Document limitation
4. Continue with other tasks
5. Flag for human review

## Recovery Checklist

When recovering from error:
- [ ] Understand root cause
- [ ] Fix issue
- [ ] Add test to prevent regression
- [ ] Update documentation if needed
- [ ] Log decision in session notes
```

---

## 4️⃣ Workflow: От идеи до merge

### 4.1 Полный цикл разработки фичи

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ПОЛНЫЙ WORKFLOW ОДНОЙ ФИЧИ                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ДЕНЬ 1 (Вечер): Context Building — 30 минут                               │
│   ═══════════════════════════════════════════                               │
│                                                                              │
│   1. Запустить Claude Code:                                                 │
│      $ claude                                                                │
│                                                                              │
│   2. Создать спецификацию (Agent OS):                                       │
│      > /shape-spec user-notifications                                       │
│      # spec-shaper задаёт 5-10 вопросов                                     │
│      # Многие отвечены из qa-defaults.md автоматически                      │
│      # Human отвечает на 1-3 уникальных вопроса                             │
│                                                                              │
│      > /write-spec                                                           │
│      # Создан: agent-os/specs/user-notifications/specification.md           │
│                                                                              │
│      > /create-tasks                                                         │
│      # Создан: agent-os/specs/user-notifications/tasks.md                   │
│                                                                              │
│   3. Review артефактов (опционально):                                       │
│      $ glow agent-os/specs/user-notifications/specification.md              │
│      $ glow agent-os/specs/user-notifications/tasks.md                      │
│                                                                              │
│      # Если всё OK → approve                                                │
│      # Если нужны правки → редактировать файлы вручную                      │
│                                                                              │
│   ──────────────────────────────────────────────────────────────────────   │
│                                                                              │
│   ДЕНЬ 1 (Ночь): Autonomous Execution — 0 минут human time                  │
│   ══════════════════════════════════════════════════════════                │
│                                                                              │
│   1. Подготовить для Ralph (скрипт):                                        │
│      $ ./scripts/prepare-ralph-session.sh user-notifications                │
│      # Автоматически:                                                       │
│      # - Конвертирует tasks.md → @fix_plan.md                               │
│      # - Создаёт PROMPT.md с инструкциями                                   │
│      # - Инициализирует session log                                         │
│                                                                              │
│   2. Запустить Ralph loop (overnight):                                      │
│      $ claude                                                                │
│      > /ralph-loop "Execute /start-feature user-notifications" \            │
│          --max-iterations 100 \                                              │
│          --timeout 15 \                                                      │
│          --completion-promise "ALL_TASKS_COMPLETE"                           │
│                                                                              │
│   3. (Опционально) Мониторинг в отдельном терминале:                       │
│      $ watch -n 10 -c 'glow @fix_plan.md'                                   │
│                                                                              │
│   → Claude работает автономно всю ночь:                                     │
│      • Читает задачи из @fix_plan.md                                        │
│      • Реализует каждую задачу                                              │
│      • Использует GLM MCP для boilerplate                                   │
│      • Hooks обеспечивают качество:                                         │
│        - PostToolUse запускает тесты                                        │
│        - Block-at-Submit не даёт commit без тестов                          │
│      • Помечает задачи [x] в @fix_plan.md                                   │
│      • Делает commit после каждой задачи                                    │
│      • Stop hook проверяет нужна ли помощь                                  │
│                                                                              │
│   ВОЗМОЖНЫЕ ПРЕРЫВАНИЯ:                                                     │
│   • Если agent застрял → создаёт .needs_human_intervention                  │
│   • Если ошибок > threshold → circuit breaker открывается                   │
│   • Notification отправляется (ntfy, если настроено)                        │
│                                                                              │
│   ──────────────────────────────────────────────────────────────────────   │
│                                                                              │
│   ДЕНЬ 2 (Утро): Human Review — 20 минут                                    │
│   ═══════════════════════════════════════                                   │
│                                                                              │
│   1. Проверить статус:                                                      │
│      $ glow @fix_plan.md                                                     │
│      # Сколько задач выполнено? Есть ли блокеры?                            │
│                                                                              │
│   2. Проверить изменения:                                                   │
│      $ git log --oneline -20                                                 │
│      $ git diff main...HEAD                                                  │
│                                                                              │
│   3. Запустить тесты:                                                       │
│      $ npm test                                                              │
│      # Должны проходить (гарантировано hooks)                               │
│                                                                              │
│   4. Проверить session log:                                                 │
│      $ glow logs/session-2026-01-14-2300.md                                  │
│      # Какие решения принял agent? Были ли проблемы?                        │
│                                                                              │
│   5. Если есть .needs_human_intervention:                                   │
│      $ cat .needs_human_intervention                                         │
│      # Ответить на вопрос или исправить проблему                            │
│      $ rm .needs_human_intervention                                          │
│      # Опционально: продолжить Ralph loop для завершения                    │
│                                                                              │
│   ──────────────────────────────────────────────────────────────────────   │
│                                                                              │
│   ДЕНЬ 2 (Утро): Finalization — 10 минут                                    │
│   ═══════════════════════════════════════                                   │
│                                                                              │
│   1. Создать PR:                                                            │
│      $ gh pr create \                                                        │
│          --title "feat(notifications): User notification system" \           │
│          --body "$(cat agent-os/specs/user-notifications/specification.md)" │
│                                                                              │
│   2. В GitHub:                                                              │
│      • Review PR                                                             │
│      • Проверить CI/CD (если настроен)                                      │
│      • Approve                                                               │
│      • Merge                                                                 │
│                                                                              │
│   3. Cleanup:                                                                │
│      $ rm @fix_plan.md PROMPT.md                                             │
│      $ git checkout main && git pull                                         │
│                                                                              │
│   ✅ DONE!                                                                  │
│                                                                              │
│   ═══════════════════════════════════════════════════════════════════════   │
│                                                                              │
│   ИТОГО HUMAN TIME:                                                         │
│   • Context building: 30 мин                                                │
│   • Review: 20 мин                                                          │
│   • Finalization: 10 мин                                                    │
│   TOTAL: ~60 минут на фичу                                                  │
│                                                                              │
│   AI TIME:                                                                  │
│   • Autonomous execution: 4-8 часов (overnight)                             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Вспомогательные скрипты

#### scripts/prepare-ralph-session.sh

```bash
#!/bin/bash
# Подготовка Ralph session для фичи

FEATURE_NAME="$1"

if [ -z "$FEATURE_NAME" ]; then
    echo "Usage: $0 <feature-name>"
    echo ""
    echo "Available specs:"
    ls -1 agent-os/specs/
    exit 1
fi

SPEC_DIR="agent-os/specs/$FEATURE_NAME"

if [ ! -d "$SPEC_DIR" ]; then
    echo "❌ Spec not found: $SPEC_DIR"
    exit 1
fi

echo "🔧 Preparing Ralph session for: $FEATURE_NAME"

# 1. Конвертировать tasks.md → @fix_plan.md
if [ -f "$SPEC_DIR/tasks.md" ]; then
    echo "# Implementation Plan: $FEATURE_NAME" > @fix_plan.md
    echo "" >> @fix_plan.md
    echo "Source: $SPEC_DIR/tasks.md" >> @fix_plan.md
    echo "Created: $(date)" >> @fix_plan.md
    echo "" >> @fix_plan.md
    
    # Конвертировать tasks в checkbox format
    grep -E "^[-*•] " "$SPEC_DIR/tasks.md" | while read -r line; do
        task="${line#[-*•] }"
        echo "- [ ] $task" >> @fix_plan.md
    done
    
    echo "✅ Created @fix_plan.md with $(grep -c '\[ \]' @fix_plan.md) tasks"
else
    echo "⚠️  No tasks.md found, creating empty @fix_plan.md"
    echo "# Implementation Plan: $FEATURE_NAME" > @fix_plan.md
    echo "- [ ] TODO: Define tasks" >> @fix_plan.md
fi

# 2. Создать PROMPT.md
cat > PROMPT.md << EOF
# Autonomous Execution: $FEATURE_NAME

## Context
- Specification: @$SPEC_DIR/specification.md
- Tasks: @@fix_plan.md
- Project rules: @CLAUDE.md
- QA defaults: @.claude/context/qa-defaults.md

## Instructions

Use /start-feature command to begin autonomous implementation.

The command will:
1. Load all context
2. Verify prerequisites
3. Implement tasks from @fix_plan.md
4. Use TDD approach
5. Delegate boilerplate to GLM MCP
6. Mark tasks done as completed
7. Commit changes incrementally

## Exit Conditions

Stop when:
- All tasks in @fix_plan.md are [x]
- Human help is needed (.needs_human_intervention created)
- Max iterations reached
- Circuit breaker opens

## Quality Requirements

- All tests must pass before commit (enforced by hooks)
- Keep commits small and focused
- Write descriptive commit messages
- Update @fix_plan.md after each task
EOF

echo "✅ Created PROMPT.md"

# 3. Инициализировать session log
mkdir -p logs
SESSION_LOG="logs/session-$(date +%Y-%m-%d-%H%M).md"

cat > "$SESSION_LOG" << EOF
# Session Log: $FEATURE_NAME

**Started**: $(date)
**Branch**: $(git branch --show-current)
**Spec**: $SPEC_DIR

## Status

- [ ] Context loaded
- [ ] Tasks initialized
- [ ] Execution started
- [ ] Execution completed

## Tasks Progress

See @fix_plan.md for live status

## Notes

(Will be updated during execution)

## Completed Tasks

(Will be updated as tasks complete)

## Blockers

(Will be updated if issues arise)
EOF

echo "✅ Created session log: $SESSION_LOG"

# 4. Проверить prerequisites
echo ""
echo "📋 Pre-flight checks:"

# Проверка что нет активных изменений
if ! git diff-index --quiet HEAD --; then
    echo "⚠️  Warning: You have uncommitted changes"
    echo "   Consider stashing them before starting Ralph loop"
fi

# Проверка что тесты проходят
if command -v npm &> /dev/null && [ -f "package.json" ]; then
    echo "Running test suite..."
    if npm test --silent; then
        echo "✅ Tests passing"
    else
        echo "⚠️  Warning: Some tests failing"
        echo "   Fix tests before starting autonomous execution"
    fi
fi

# Проверка на существующий .needs_human_intervention
if [ -f ".needs_human_intervention" ]; then
    echo "⚠️  Warning: .needs_human_intervention file exists"
    echo "   Previous session may have been blocked"
    echo "   Review and remove before continuing"
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "✅ Ralph session prepared!"
echo ""
echo "Next steps:"
echo "  1. Review @fix_plan.md and PROMPT.md"
echo "  2. Start Ralph loop:"
echo ""
echo "     claude"
echo "     > /ralph-loop \"Execute PROMPT.md\" \\"
echo "         --max-iterations 100 \\"
echo "         --timeout 15 \\"
echo "         --completion-promise \"ALL_TASKS_COMPLETE\""
echo ""
echo "  3. (Optional) Monitor in another terminal:"
echo "     watch -n 10 -c 'glow @fix_plan.md'"
echo ""
echo "═══════════════════════════════════════════════════════════"
```

#### scripts/check-ralph-status.sh

```bash
#!/bin/bash
# Проверка статуса Ralph session

echo "📊 Ralph Session Status"
echo "════════════════════════════════════════════════════════"

# 1. Проверка @fix_plan.md
if [ -f "@fix_plan.md" ]; then
    TOTAL_TASKS=$(grep -c '- \[.\]' @fix_plan.md)
    COMPLETED_TASKS=$(grep -c '- \[x\]' @fix_plan.md)
    PENDING_TASKS=$(grep -c '- \[ \]' @fix_plan.md)
    
    echo ""
    echo "Tasks Progress:"
    echo "  Total: $TOTAL_TASKS"
    echo "  Completed: $COMPLETED_TASKS"
    echo "  Pending: $PENDING_TASKS"
    echo "  Progress: $(( COMPLETED_TASKS * 100 / TOTAL_TASKS ))%"
else
    echo ""
    echo "⚠️  No @fix_plan.md found"
fi

# 2. Проверка на human intervention
if [ -f ".needs_human_intervention" ]; then
    echo ""
    echo "🚨 HUMAN INTERVENTION NEEDED:"
    cat .needs_human_intervention | jq '.'
else
    echo ""
    echo "✅ No intervention needed"
fi

# 3. Git статус
echo ""
echo "Git Status:"
COMMITS_AHEAD=$(git rev-list --count HEAD ^main 2>/dev/null || echo "0")
echo "  Commits ahead of main: $COMMITS_AHEAD"
echo "  Current branch: $(git branch --show-current)"

# 4. Последние коммиты
if [ "$COMMITS_AHEAD" -gt 0 ]; then
    echo ""
    echo "Recent commits:"
    git log --oneline -5
fi

# 5. Test status
echo ""
echo "Test Status:"
if npm test --silent 2>&1 | tail -1; then
    echo "  ✅ Tests passing"
else
    echo "  ❌ Tests failing"
fi

# 6. Session logs
echo ""
echo "Session Logs:"
if ls logs/session-*.md 1> /dev/null 2>&1; then
    LATEST_LOG=$(ls -t logs/session-*.md | head -1)
    echo "  Latest: $LATEST_LOG"
    echo "  View: glow $LATEST_LOG"
else
    echo "  No session logs found"
fi

echo ""
echo "════════════════════════════════════════════════════════"
```

---

## 5️⃣ Context Building: Минимизация Human-in-the-Loop

### 5.1 QA Defaults File

Создайте `.claude/context/qa-defaults.md` для автоматических ответов:

```markdown
# Project Q&A Defaults

> Этот файл содержит стандартные ответы на частые вопросы spec-shaper.
> Agent OS будет использовать эти ответы автоматически,
> спрашивая human только если ответа здесь нет.

## Technology Stack

**Backend:**
- Runtime: Node.js 20 LTS
- Framework: Express.js 4.x
- Language: TypeScript 5.x
- Database: PostgreSQL 15
- ORM: Prisma 5.x
- Auth: JWT (jsonwebtoken)
- Validation: Zod

**Frontend:**
- Framework: React 18
- Language: TypeScript 5.x
- Styling: Tailwind CSS 3.x
- State: Zustand
- Routing: React Router 6
- HTTP: Axios
- Build: Vite

**Testing:**
- Unit: Jest + React Testing Library
- E2E: Playwright
- Coverage target: > 80%

**Infrastructure:**
- Deployment: Docker + Kubernetes
- CI/CD: GitHub Actions
- Monitoring: Prometheus + Grafana
- Logging: Winston (backend), console (frontend)

## Security Requirements

**Authentication:**
- JWT tokens with 15 min expiry
- Refresh tokens with 7 day expiry
- HTTPOnly cookies for tokens
- CSRF protection required

**Password Policy:**
- Min 12 characters
- Must include: uppercase, lowercase, number, special char
- Hashing: bcrypt with 12 rounds
- Prevent common passwords (list of 10k)

**API Security:**
- Rate limiting: 100 req/min per IP
- CORS: Whitelist specific origins
- Input validation on all endpoints
- SQL injection prevention (use Prisma)
- XSS prevention (sanitize inputs)

**Data Protection:**
- Encrypt sensitive data at rest
- HTTPS only
- Secure headers (helmet.js)
- Regular dependency updates

## Code Style & Conventions

**General:**
- 2 spaces for indentation
- UTF-8 encoding
- LF line endings
- Max line length: 100 characters
- ESLint + Prettier enforced

**Naming:**
- Files: kebab-case (user-service.ts)
- Classes: PascalCase (UserService)
- Functions: camelCase (getUserById)
- Constants: UPPER_SNAKE_CASE (MAX_RETRIES)
- Components: PascalCase (UserProfile.tsx)

**TypeScript:**
- Strict mode enabled
- No `any` type (use `unknown`)
- Prefer interfaces over types
- Use const assertions where appropriate

**React:**
- Functional components only
- Hooks over HOCs
- Custom hooks for reusable logic
- Props destructuring in function signature

**Testing:**
- Test file naming: `*.test.ts` or `*.spec.ts`
- One describe block per function/component
- AAA pattern: Arrange, Act, Assert
- Mock external dependencies

**Git:**
- Commit message format: `<type>(<scope>): <description>`
- Types: feat, fix, docs, style, refactor, test, chore
- Max subject line: 50 chars
- Body: wrap at 72 chars

## Architecture Patterns

**Backend:**
- Layered architecture:
  - Controller → Service → Repository
- Repository pattern for data access
- Dependency injection via constructor
- Error handling middleware
- Request validation middleware

**Frontend:**
- Feature-based folder structure
- Container/Presenter pattern
- Custom hooks for business logic
- Context for shared state
- API layer abstraction

**Error Handling:**
- Structured error responses:
  ```json
  {
    "error": {
      "code": "VALIDATION_ERROR",
      "message": "Human readable message",
      "details": { /* field-level errors */ }
    }
  }
  ```

**Logging:**
- Structured logs (JSON)
- Levels: error, warn, info, debug
- Include correlation IDs
- No sensitive data in logs

## Common Decisions

**Database:**
- Migrations: Prisma migrate
- Seeding: npm run db:seed
- Backup: Daily automated
- Transactions: Use Prisma transactions for multi-step operations

**Caching:**
- Strategy: Cache-aside
- TTL: 5 minutes default
- Invalidation: On write operations
- Storage: Redis (if needed)

**File Uploads:**
- Max size: 10MB
- Allowed types: images (jpg, png, gif), docs (pdf)
- Storage: Local filesystem (dev), S3 (prod)
- Virus scanning: Required in production

**Pagination:**
- Default page size: 20
- Max page size: 100
- Format: `GET /resource?page=1&limit=20`
- Response includes: `total`, `page`, `limit`, `data`

**API Versioning:**
- Strategy: URL versioning (`/api/v1/`)
- Support 2 versions concurrently
- Deprecation notice: 6 months

## Environment-Specific Answers

**Development:**
- Debug logging enabled
- Hot reload enabled
- Relaxed CORS
- Mock external services

**Staging:**
- Same config as production
- Synthetic data
- Automated testing

**Production:**
- Error logging only
- Strict security
- Real external services
- Monitoring enabled

## Project-Specific Context

**User Roles:**
- admin: Full access
- manager: Read/write for assigned resources
- user: Read own data, write own profile

**Feature Flags:**
- System: LaunchDarkly
- Toggle via env variables
- Default: disabled in prod

**Compliance:**
- GDPR: User data export/delete required
- Data retention: 2 years
- Audit logging: All admin actions

## Common Feature Requirements

**CRUD Operations:**
- Always include: create, read, update, delete, list
- Soft delete preferred (mark as deleted)
- Include timestamps: createdAt, updatedAt
- Include audit fields: createdBy, updatedBy

**User Management:**
- Email verification required
- Password reset via email
- Account lockout after 5 failed attempts
- Session management

**Notifications:**
- Support: email, in-app, push (future)
- User preferences for each type
- Templates stored in database
- Queue for async sending

**Search:**
- Full-text search for text fields
- Filters for categorical fields
- Sorting support
- Pagination required
```

### 5.2 Как spec-shaper использует qa-defaults.md

```markdown
<!-- Внутренний механизм Agent OS -->

Когда spec-shaper задаёт вопрос:

1. Формирует вопрос на основе контекста
2. Проверяет qa-defaults.md на наличие ответа
3. Если ответ найден → использует автоматически
4. Если ответа нет → спрашивает human
5. Human ответ может быть добавлен в qa-defaults.md для будущего

Пример:

spec-shaper думает: "Нужно спросить про authentication method"
spec-shaper проверяет: qa-defaults.md → "Authentication: JWT tokens..."
spec-shaper использует: Ответ из файла, не спрашивает human

spec-shaper думает: "Нужно спросить про интеграцию с Stripe"
spec-shaper проверяет: qa-defaults.md → Ничего про Stripe
spec-shaper спрашивает: "Should we integrate with Stripe for payments?"
human отвечает: "Yes, use Stripe Elements"
(Опционально) human добавляет в qa-defaults.md секцию "Payment Processing"
```

---

## 6️⃣ Monitoring & Visualization

### 6.1 Glow для красивого отображения

```bash
# Установка Glow
brew install glow  # macOS
# или
go install github.com/charmbracelet/glow@latest  # Linux

# Использование
glow @fix_plan.md                    # Просмотр с пролистыванием
glow -p @fix_plan.md                 # Pager mode
watch -n 5 -c 'glow @fix_plan.md'   # Live update каждые 5 сек
```

**Aliases для удобства:**

```bash
# Добавить в ~/.bashrc или ~/.zshrc
alias tasks='glow -p @fix_plan.md'
alias tasks-watch='watch -n 5 -c "glow @fix_plan.md"'
alias spec='glow -p agent-os/specs/$(basename $(pwd))/specification.md'
alias session-log='glow -p logs/session-*.md | tail -1'
```

### 6.2 Tmux layout для мониторинга

```bash
#!/bin/bash
# scripts/monitor-ralph.sh
# Создаёт tmux layout для мониторинга Ralph session

SESSION_NAME="ralph-monitor"

# Создать новую tmux session
tmux new-session -d -s $SESSION_NAME

# Окно 1: Tasks progress (live)
tmux rename-window -t $SESSION_NAME:0 'Tasks'
tmux send-keys -t $SESSION_NAME:0 'watch -n 5 -c "glow @fix_plan.md"' C-m

# Окно 2: Git log (live)
tmux new-window -t $SESSION_NAME:1 -n 'Git'
tmux send-keys -t $SESSION_NAME:1 'watch -n 10 "git log --oneline --graph -10"' C-m

# Окно 3: Test status
tmux new-window -t $SESSION_NAME:2 -n 'Tests'
tmux send-keys -t $SESSION_NAME:2 'watch -n 30 "npm test 2>&1 | tail -20"' C-m

# Окно 4: Session log
tmux new-window -t $SESSION_NAME:3 -n 'Log'
tmux send-keys -t $SESSION_NAME:3 'tail -f logs/session-*.md | glow -' C-m

# Attach to session
tmux attach-session -t $SESSION_NAME
```

**Использование:**

```bash
# В одном терминале: запустить Ralph
claude
/ralph-loop "Execute PROMPT.md" --max-iterations 100

# В другом терминале: мониторинг
./scripts/monitor-ralph.sh
```

### 6.3 Уведомления (ntfy.sh)

```bash
# Настройка ntfy
# 1. Зарегистрироваться на ntfy.sh (или self-host)
# 2. Создать topic (например: ralph-alerts-yourname)

# Добавить в ~/.bashrc
export NTFY_TOPIC="ralph-alerts-yourname"

# Установить ntfy CLI
brew install ntfy    # macOS
# или
pip install ntfy     # Linux

# Тест
ntfy publish "$NTFY_TOPIC" "🚀 Ralph session started"
```

**Hooks будут автоматически отправлять уведомления:**
- ✅ Когда все задачи выполнены
- ⚠️ Когда нужна помощь человека
- ❌ Когда circuit breaker открывается
- 🔄 Каждые N задач (опционально)

---

## 7️⃣ Оптимизация и Best Practices

### 7.1 Token Optimization

**Стратегия делегирования Claude → GLM:**

```
┌─────────────────────────────────────────────────────────────────┐
│         КОГДА ИСПОЛЬЗОВАТЬ GLM VS CLAUDE                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   CLAUDE (дорого, но качественно):                              │
│   ═════════════════════════════════                             │
│   • Архитектурные решения                                       │
│   • Сложная бизнес-логика                                       │
│   • Рефакторинг                                                 │
│   • Code review                                                 │
│   • Security-critical код                                       │
│   • Интеграция компонентов                                      │
│   • Обработка ошибок                                            │
│                                                                 │
│   GLM через MCP (дёшево, быстро):                               │
│   ══════════════════════════════════                            │
│   • CRUD operations                                             │
│   • Boilerplate code                                            │
│   • API endpoints (стандартные)                                 │
│   • Test scaffolding                                            │
│   • Data transformations                                        │
│   • Form validation                                             │
│   • Database queries (Prisma)                                   │
│   • CSS styling                                                 │
│                                                                 │
│   ЭКОНОМИЯ:                                                     │
│   • Claude Opus: ~$15 / 1M input tokens                         │
│   • GLM-4: ~$0.50 / 1M input tokens                             │
│   • Экономия: ~97% на boilerplate tasks                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Пример оптимального workflow:**

```
Task: "Create user registration endpoint"

Claude анализирует (100 tokens):
- API contract design
- Validation requirements
- Security considerations
- Error handling strategy

GLM генерирует (5000 tokens):
- Controller boilerplate
- Validation schemas (Zod)
- Repository methods
- Test scaffolding
- Database migration

Claude review (500 tokens):
- Проверяет security
- Добавляет error handling
- Refactor для читабельности
- Approve и commit

Total Claude: 600 tokens
Total GLM: 5000 tokens
Savings: ~90% на Claude tokens
```

### 7.2 Context Window Management

**Ralph loop может "съесть" контекст. Стратегии:**

1. **Incremental commits** — Каждая задача = отдельный commit
   - Context reset после commit (git history сохраняет результат)
   
2. **Subagents для изоляции** — Использовать Claude Code subagents для подзадач
   - Subagent имеет свой context window
   - Результат передаётся обратно parent
   
3. **Skills вместо inline instructions** — Вынести паттерны в skills
   - Загружаются on-demand
   - Не съедают context постоянно

4. **Memories для cross-session context** — Claude Code Memories
   - Сохраняют важные решения
   - Доступны между sessions

### 7.3 Quality Gates

**Многоуровневая система проверки качества:**

```
┌─────────────────────────────────────────────────────────────────┐
│                    QUALITY GATES ПИРАМИДА                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│                       ▲                                         │
│                      / \                                        │
│                     /   \                                       │
│                    /  5  \         HUMAN REVIEW                 │
│                   /       \        • Final approval             │
│                  /_________\       • Merge decision             │
│                 /           \                                   │
│                /      4      \     STOP HOOK                    │
│               /               \    • Check completion           │
│              /   Error Check   \   • Escalate if stuck          │
│             /___________________\                               │
│            /                     \                              │
│           /          3            \ BLOCK-AT-SUBMIT             │
│          /                         \• Tests must pass           │
│         /    Commit Gate            \                           │
│        /_____________________________\                          │
│       /                               \                         │
│      /               2                 \ POSTTOOLUSE            │
│     /                                   \• Run tests            │
│    /      Test Validation                \• Type check          │
│   /_______________________________________\• Lint               │
│  /                                         \                    │
│ /                  1                        \ PRETOOLUSE        │
│/                                             \• Block dangerous  │
│          Input Validation                     \• Validate args  │
│_______________________________________________\                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Каждый уровень — это checkpoint:**
- Уровень 1-3: Автоматические (hooks)
- Уровень 4: Условный (только при проблемах)
- Уровень 5: Обязательный (human в финале)

---

## 8️⃣ Troubleshooting

### 8.1 Частые проблемы и решения

#### Ralph не перезапускается после ошибки

**Симптомы:**
- Ralph loop завершается после первой ошибки
- Stop hook не срабатывает

**Решение:**

```bash
# Проверить что Stop hook настроен
cat ~/.claude/settings.json | jq '.hooks.Stop'

# Проверить что hook исполняемый
chmod +x ~/.claude/hooks/check-completion.sh

# Проверить логи hook
cat ~/.claude/hooks/check-completion.sh
# Должен возвращать JSON с "continue": true/false
```

#### Block-at-Submit не работает

**Симптомы:**
- Claude коммитит без прохождения тестов

**Решение:**

```bash
# Проверить PreToolUse hook на Bash(git commit*)
cat ~/.claude/settings.json | jq '.hooks.PreToolUse[] | select(.matcher | contains("git commit"))'

# Проверить что скрипт работает
bash ~/.claude/hooks/block-at-submit.sh

# Проверить что маркер создаётся после тестов
npm test && echo "Pass file: /tmp/tests-passed-$(basename $(pwd))"
ls -la /tmp/tests-passed-*
```

#### GLM MCP не отвечает

**Симптомы:**
- `mcp__glm-coder__*` tools недоступны
- Timeout при вызове GLM

**Решение:**

```bash
# Проверить что MCP сервер запущен
ps aux | grep glm-mcp-server

# Проверить логи MCP
cat ~/.claude/logs/mcp-glm-coder.log

# Проверить API key
echo $Z_AI_API_KEY

# Перезапустить Claude Code
claude --restart-mcp
```

#### @fix_plan.md не обновляется

**Симптомы:**
- Tasks остаются unchecked
- Ralph loop продолжается бесконечно

**Решение:**

```bash
# Проверить что PROMPT.md содержит инструкцию обновлять @fix_plan.md
grep "fix_plan" PROMPT.md

# Вручную обновить (если нужно)
# Заменить - [ ] на - [x] для выполненных задач
nano @fix_plan.md

# Проверить что completion promise учитывает @fix_plan.md
# В PROMPT.md должно быть: "When ALL tasks in @fix_plan.md are [x]"
```

### 8.2 Debugging Techniques

#### Логирование hook outputs

```bash
# Обернуть hook для логирования
# ~/.claude/hooks/logged-block-at-submit.sh

#!/bin/bash
LOG_FILE="/tmp/claude-hooks.log"

echo "$(date) - Block-at-Submit called" >> "$LOG_FILE"

# Оригинальная логика
PROJECT_NAME=$(basename $(pwd))
PASS_FILE="/tmp/tests-passed-${PROJECT_NAME}"

if [ -f "$PASS_FILE" ]; then
    rm -f "$PASS_FILE"
    DECISION='{"decision": "approve", "reason": "Tests passed"}'
else
    DECISION='{"decision": "deny", "reason": "Tests must pass"}'
fi

echo "$(date) - Decision: $DECISION" >> "$LOG_FILE"
echo "$DECISION"
```

#### Dry-run режим для Ralph

```markdown
<!-- .claude/commands/debug/ralph-dry-run.md -->
---
description: Test Ralph loop without actual execution
---

# Ralph Dry-Run

Test the Ralph loop setup without making real changes.

## Instructions

1. Read PROMPT.md to understand the plan
2. Read @fix_plan.md to see tasks
3. For each task:
   - Explain what you WOULD do
   - Identify files that WOULD be changed
   - List tests that WOULD be run
   - Do NOT actually execute
4. Output summary of planned actions

This helps verify the setup before committing to long-running execution.
```

---

## 9️⃣ Advanced: Multi-Feature Parallelism

### 9.1 Git Worktrees для параллельной работы

```bash
# scripts/parallel-ralph.sh
# Запуск нескольких Ralph sessions для разных фич

FEATURES=("user-auth" "notifications" "dashboard")

for FEATURE in "${FEATURES[@]}"; do
    # Создать worktree
    git worktree add "../worktree-$FEATURE" -b "feature/$FEATURE"
    
    # Перейти в worktree
    cd "../worktree-$FEATURE"
    
    # Подготовить Ralph session
    ./scripts/prepare-ralph-session.sh "$FEATURE"
    
    # Запустить Ralph в background
    claude --mode=headless <<EOF &
/ralph-loop "Execute PROMPT.md" \\
  --max-iterations 50 \\
  --completion-promise "ALL_TASKS_COMPLETE"
EOF
    
    # Вернуться
    cd -
done

echo "✅ Started ${#FEATURES[@]} parallel Ralph sessions"
echo "Monitor worktrees:"
for FEATURE in "${FEATURES[@]}"; do
    echo "  cd ../worktree-$FEATURE && watch -n 5 'glow @fix_plan.md'"
done
```

**Мониторинг параллельных sessions:**

```bash
#!/bin/bash
# scripts/monitor-all-worktrees.sh

SESSION_NAME="ralph-parallel"
WORKTREES=(../worktree-*)

tmux new-session -d -s $SESSION_NAME

for i in "${!WORKTREES[@]}"; do
    WORKTREE="${WORKTREES[$i]}"
    FEATURE_NAME=$(basename "$WORKTREE" | sed 's/worktree-//')
    
    if [ $i -eq 0 ]; then
        tmux rename-window -t $SESSION_NAME:0 "$FEATURE_NAME"
        tmux send-keys -t $SESSION_NAME:0 "cd $WORKTREE && watch -n 5 -c 'glow @fix_plan.md'" C-m
    else
        tmux new-window -t $SESSION_NAME:$i -n "$FEATURE_NAME"
        tmux send-keys -t $SESSION_NAME:$i "cd $WORKTREE && watch -n 5 -c 'glow @fix_plan.md'" C-m
    fi
done

tmux attach-session -t $SESSION_NAME
```

---

## 🔟 Финальный чеклист развёртывания

```
┌─────────────────────────────────────────────────────────────────┐
│              DEPLOYMENT CHECKLIST                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ☐ PREREQUISITES                                               │
│   ├─ Node.js >= 18                                              │
│   ├─ Claude Code CLI >= 2.1.0                                   │
│   ├─ Git >= 2.30                                                │
│   ├─ Glow (optional)                                            │
│   └─ tmux (optional)                                            │
│                                                                 │
│   ☐ AGENT OS SETUP                                              │
│   ├─ Клонировать/установить Agent OS                           │
│   ├─ Запустить agent-os init в проекте                         │
│   ├─ Заполнить agent-os/product/                               │
│   ├─ Настроить profiles/default/standards/                     │
│   └─ Проверить что commands доступны в Claude                  │
│                                                                 │
│   ☐ RALPH SETUP                                                 │
│   ├─ Установить ralph-wiggum plugin                            │
│   ├─ Проверить /ralph-loop command                             │
│   └─ Проверить /plugins list                                   │
│                                                                 │
│   ☐ GLM MCP SETUP                                               │
│   ├─ Установить GLM MCP server                                 │
│   ├─ Добавить в ~/.claude/settings.json mcpServers             │
│   ├─ Проверить Z_AI_API_KEY env variable                       │
│   └─ Проверить mcp__glm-coder tools в Claude                   │
│                                                                 │
│   ☐ HOOKS CONFIGURATION                                         │
│   ├─ Создать ~/.claude/hooks/ директорию                       │
│   ├─ Создать block-at-submit.sh                                │
│   ├─ Создать check-completion.sh                               │
│   ├─ Создать validate-file-write.sh                            │
│   ├─ chmod +x все hook scripts                                 │
│   └─ Добавить hooks в ~/.claude/settings.json                  │
│                                                                 │
│   ☐ COMMANDS & SKILLS                                           │
│   ├─ Создать .claude/commands/autonomous/                      │
│   ├─ Создать start-feature.md                                  │
│   ├─ Создать implement-with-glm.md                             │
│   ├─ Создать request-human.md                                  │
│   ├─ Создать .claude/skills/autonomous-execution/              │
│   └─ Создать SKILL.md                                          │
│                                                                 │
│   ☐ CONTEXT FILES                                               │
│   ├─ Создать .claude/context/qa-defaults.md                    │
│   ├─ Заполнить своими project defaults                         │
│   ├─ Создать CLAUDE.md в корне проекта                         │
│   └─ Заполнить project rules и conventions                     │
│                                                                 │
│   ☐ HELPER SCRIPTS                                              │
│   ├─ Создать scripts/prepare-ralph-session.sh                  │
│   ├─ Создать scripts/check-ralph-status.sh                     │
│   ├─ Создать scripts/monitor-ralph.sh (tmux)                   │
│   ├─ chmod +x все scripts                                      │
│   └─ Добавить aliases в ~/.bashrc                              │
│                                                                 │
│   ☐ TESTING                                                     │
│   ├─ Создать тестовый spec через /shape-spec                   │
│   ├─ Запустить prepare-ralph-session.sh                        │
│   ├─ Запустить Ralph с --max-iterations 5                      │
│   ├─ Проверить что hooks срабатывают                           │
│   ├─ Проверить что GLM MCP работает                            │
│   └─ Проверить что @fix_plan.md обновляется                    │
│                                                                 │
│   ☐ MONITORING (OPTIONAL)                                       │
│   ├─ Настроить ntfy.sh account                                 │
│   ├─ Добавить NTFY_TOPIC env variable                          │
│   ├─ Проверить уведомления работают                            │
│   └─ Настроить tmux monitoring layout                          │
│                                                                 │
│   ☐ DOCUMENTATION                                               │
│   ├─ Документировать project-specific conventions              │
│   ├─ Обновить README с инструкциями                            │
│   ├─ Создать CONTRIBUTING.md                                    │
│   └─ Задокументировать custom commands/skills                  │
│                                                                 │
│   ✅ READY FOR PRODUCTION                                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📚 Дополнительные ресурсы

### Официальная документация:
- [Claude Code CLI Docs](https://docs.claude.ai/code)
- [Agent OS GitHub](https://github.com/your-org/agent-os)
- [Ralph Plugin](https://github.com/anthropics/ralph-wiggum)
- [GLM MCP Server](https://github.com/zhipuai/glm-mcp)

### Community Resources:
- Discord: Claude Code Community
- Reddit: r/ClaudeAI
- GitHub Discussions: agent-os/discussions

### Примеры проектов:
- [Example: E-commerce with Agent OS + Ralph](https://github.com/examples/ecommerce)
- [Example: SaaS Starter with full pipeline](https://github.com/examples/saas-starter)

---

## 🎯 Заключение

Этот стек даёт вам:

✅ **Spec-driven development** через Agent OS  
✅ **Автономное выполнение** через Ralph  
✅ **Качество кода** через hooks и skills  
✅ **Экономию токенов** через GLM MCP  
✅ **100% нативная интеграция** с Claude Code  

**Минимальное человеческое участие:**
- 30 мин на context building
- 20 мин на review
- 10 мин на merge

**Итого: ~60 минут на фичу** вместо 4-8 часов ручной работы.

---

*Версия: 1.0*  
*Дата: Январь 2026*  
*Стек: Claude Code CLI 2.1 + Agent OS + Ralph + GLM MCP*
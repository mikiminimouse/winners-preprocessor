#!/bin/bash
#═══════════════════════════════════════════════════════════════════════════════
# ПОЛНАЯ УСТАНОВКА СТЕКА: Claude Code + Agent OS + Ralph + CCGLM MCP
# Для Ubuntu Server
#═══════════════════════════════════════════════════════════════════════════════

set -e  # Остановка при ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Логирование
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✅]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[⚠️]${NC} $1"; }
log_error() { echo -e "${RED}[❌]${NC} $1"; }

# Переменные
HOME_DIR="${HOME:-/root}"
IA_DIR="$HOME_DIR/IA"
CLAUDE_DIR="$HOME_DIR/.claude"

echo ""
echo "═══════════════════════════════════════════════════════════════════════════════"
echo "  🚀 УСТАНОВКА СТЕКА: Claude Code + Agent OS + Ralph + CCGLM MCP"
echo "═══════════════════════════════════════════════════════════════════════════════"
echo ""

#───────────────────────────────────────────────────────────────────────────────
# ШАГ 1: Проверка Prerequisites
#───────────────────────────────────────────────────────────────────────────────
echo ""
log_info "ШАГ 1: Проверка prerequisites..."

# Проверка Node.js
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version | sed 's/v//')
    MAJOR_VERSION=$(echo $NODE_VERSION | cut -d. -f1)
    if [ "$MAJOR_VERSION" -ge 18 ]; then
        log_success "Node.js $NODE_VERSION найден"
    else
        log_warning "Node.js $NODE_VERSION слишком старый. Требуется >= 18"
        log_info "Установка Node.js 20..."
        curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
        sudo apt-get install -y nodejs
    fi
else
    log_warning "Node.js не найден. Установка..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y nodejs
fi

# Проверка Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    log_success "Python $PYTHON_VERSION найден"
else
    log_warning "Python3 не найден. Установка..."
    sudo apt-get install -y python3 python3-pip python3-venv
fi

# Проверка Git
if command -v git &> /dev/null; then
    GIT_VERSION=$(git --version | awk '{print $3}')
    log_success "Git $GIT_VERSION найден"
else
    log_warning "Git не найден. Установка..."
    sudo apt-get install -y git
fi

# Установка дополнительных инструментов
log_info "Установка дополнительных инструментов..."
sudo apt-get install -y curl jq tmux 2>/dev/null || true

# Установка glow (optional)
if ! command -v glow &> /dev/null; then
    log_info "Установка glow для рендеринга markdown..."
    sudo mkdir -p /etc/apt/keyrings
    curl -fsSL https://repo.charm.sh/apt/gpg.key | sudo gpg --dearmor -o /etc/apt/keyrings/charm.gpg 2>/dev/null || true
    echo "deb [signed-by=/etc/apt/keyrings/charm.gpg] https://repo.charm.sh/apt/ * *" | sudo tee /etc/apt/sources.list.d/charm.list 2>/dev/null || true
    sudo apt update && sudo apt install glow 2>/dev/null || log_warning "Не удалось установить glow (опционально)"
fi

log_success "Prerequisites проверены"

#───────────────────────────────────────────────────────────────────────────────
# ШАГ 2: Создание директорий
#───────────────────────────────────────────────────────────────────────────────
echo ""
log_info "ШАГ 2: Создание директорий..."

mkdir -p "$IA_DIR"
mkdir -p "$CLAUDE_DIR/hooks"
mkdir -p "$CLAUDE_DIR/commands"
mkdir -p "$CLAUDE_DIR/plugins"
mkdir -p "$CLAUDE_DIR/skills"
mkdir -p "$CLAUDE_DIR/agents"
mkdir -p "$CLAUDE_DIR/templates"

log_success "Директории созданы"

#───────────────────────────────────────────────────────────────────────────────
# ШАГ 3: Установка Claude Code CLI
#───────────────────────────────────────────────────────────────────────────────
echo ""
log_info "ШАГ 3: Установка Claude Code CLI..."

if command -v claude &> /dev/null; then
    CLAUDE_VERSION=$(claude --version 2>/dev/null || echo "unknown")
    log_success "Claude Code CLI уже установлен: $CLAUDE_VERSION"
else
    log_info "Установка Claude Code CLI через npm..."
    npm install -g @anthropic-ai/claude-code
    
    if command -v claude &> /dev/null; then
        log_success "Claude Code CLI установлен"
    else
        log_error "Не удалось установить Claude Code CLI"
        exit 1
    fi
fi

#───────────────────────────────────────────────────────────────────────────────
# ШАГ 4: Установка Agent OS
#───────────────────────────────────────────────────────────────────────────────
echo ""
log_info "ШАГ 4: Установка Agent OS..."

AGENT_OS_DIR="$HOME_DIR/agent-os"

if [ -d "$AGENT_OS_DIR" ]; then
    log_info "Agent OS уже существует. Обновление..."
    cd "$AGENT_OS_DIR"
    git pull origin main 2>/dev/null || log_warning "Не удалось обновить Agent OS"
else
    log_info "Клонирование Agent OS..."
    git clone https://github.com/buildermethods/agent-os.git "$AGENT_OS_DIR"
fi

# Создание конфигурации Agent OS
log_info "Настройка конфигурации Agent OS..."
cat > "$AGENT_OS_DIR/config.yml" << 'EOF'
# Agent OS Configuration
# Оптимизировано для Claude Code с subagents и Skills

defaults:
  profile: default
  
  # Claude Code интеграция
  claude_code_commands: true      # Slash-команды в Claude Code
  use_claude_code_subagents: true # Делегирование на subagents
  standards_as_claude_code_skills: true # Standards как Skills
  
  # Для других инструментов (отключено)
  agent_os_commands: false
EOF

log_success "Agent OS установлен в: $AGENT_OS_DIR"

#───────────────────────────────────────────────────────────────────────────────
# ШАГ 5: Установка CCGLM MCP Server
#───────────────────────────────────────────────────────────────────────────────
echo ""
log_info "ШАГ 5: Установка CCGLM MCP Server..."

CCGLM_DIR="$IA_DIR/ccglm-mcp"

if [ -d "$CCGLM_DIR" ]; then
    log_info "CCGLM MCP уже существует. Обновление..."
    cd "$CCGLM_DIR"
    git pull origin main 2>/dev/null || log_warning "Не удалось обновить CCGLM MCP"
else
    log_info "Клонирование CCGLM MCP..."
    git clone https://github.com/nosolosoft/ccglm-mcp.git "$CCGLM_DIR"
fi

# Установка Python зависимостей
cd "$CCGLM_DIR"
if [ -f "requirements.txt" ]; then
    log_info "Установка Python зависимостей для CCGLM..."
    pip install -r requirements.txt --break-system-packages 2>/dev/null || \
    pip install -r requirements.txt 2>/dev/null || \
    log_warning "Не удалось установить некоторые зависимости"
fi

# Создание .env файла (пустой шаблон)
if [ ! -f "$CCGLM_DIR/.env" ]; then
    log_info "Создание шаблона .env для CCGLM..."
    cat > "$CCGLM_DIR/.env" << 'EOF'
# CCGLM MCP Configuration
# Получите токен на https://z.ai

GLM_BASE_URL=https://api.z.ai/api/anthropic
GLM_AUTH_TOKEN=ВСТАВЬТЕ_ВАШ_ТОКЕН_ЗДЕСЬ
EOF
    chmod 600 "$CCGLM_DIR/.env"
    log_warning "⚠️  Отредактируйте $CCGLM_DIR/.env и добавьте ваш GLM токен!"
fi

log_success "CCGLM MCP установлен в: $CCGLM_DIR"

#───────────────────────────────────────────────────────────────────────────────
# ШАГ 6: Установка Ralph (Community версия)
#───────────────────────────────────────────────────────────────────────────────
echo ""
log_info "ШАГ 6: Установка Ralph..."

RALPH_DIR="$IA_DIR/ralph-on-steroids"

if [ -d "$RALPH_DIR" ]; then
    log_info "Ralph уже существует. Обновление..."
    cd "$RALPH_DIR"
    git pull origin main 2>/dev/null || log_warning "Не удалось обновить Ralph"
else
    log_info "Клонирование Ralph-on-Steroids..."
    git clone https://github.com/frankbria/ralph-on-steroids.git "$RALPH_DIR" 2>/dev/null || \
    log_warning "Не удалось клонировать Ralph (репозиторий может быть недоступен)"
fi

log_success "Ralph установлен (если доступен)"

#───────────────────────────────────────────────────────────────────────────────
# ШАГ 7: Создание Hooks
#───────────────────────────────────────────────────────────────────────────────
echo ""
log_info "ШАГ 7: Создание Hooks..."

# Ralph Completion Check Hook
cat > "$CLAUDE_DIR/hooks/ralph-check-completion.sh" << 'EOF'
#!/bin/bash
# Ralph Completion Check Hook
# Проверяет, выполнены ли все задачи

FIX_PLAN="${PROJECT_ROOT:-$(pwd)}/@fix_plan.md"

if [[ ! -f "$FIX_PLAN" ]]; then
    echo '{"continue": false, "message": "No fix plan found"}'
    exit 0
fi

# Подсчёт незавершённых задач
INCOMPLETE=$(grep -c "^\s*- \[ \]" "$FIX_PLAN" 2>/dev/null || echo "0")

if [[ "$INCOMPLETE" -gt 0 ]]; then
    echo "{\"continue\": true, \"message\": \"$INCOMPLETE tasks remaining\", \"inject\": \"Continue with the next uncompleted task in @fix_plan.md\"}"
else
    echo '{"continue": false, "message": "All tasks completed!"}'
fi
EOF

# Block at Submit Hook
cat > "$CLAUDE_DIR/hooks/block-at-submit.sh" << 'EOF'
#!/bin/bash
# Block commit if tests haven't passed

MARKER="/tmp/tests-passed-$(basename $(pwd))"

if [[ -f "$MARKER" ]]; then
    echo '{"decision": "approve"}'
    rm -f "$MARKER"
else
    echo '{"decision": "deny", "reason": "Please run tests before committing"}'
fi
EOF

# Validate File Write Hook
cat > "$CLAUDE_DIR/hooks/validate-file-write.sh" << 'EOF'
#!/bin/bash
# Validate file writes - block writes to sensitive files

FILE_PATH="$1"

BLOCKED_PATTERNS=(".env" ".env.local" "*.pem" "*.key" "id_rsa*" "secrets*")

for pattern in "${BLOCKED_PATTERNS[@]}"; do
    if [[ "$FILE_PATH" == $pattern ]]; then
        echo "{\"decision\": \"deny\", \"reason\": \"Cannot write to sensitive file: $FILE_PATH\"}"
        exit 0
    fi
done

echo '{"decision": "approve"}'
EOF

# Установка прав
chmod +x "$CLAUDE_DIR/hooks/"*.sh

log_success "Hooks созданы"

#───────────────────────────────────────────────────────────────────────────────
# ШАГ 8: Создание Claude settings.json
#───────────────────────────────────────────────────────────────────────────────
echo ""
log_info "ШАГ 8: Создание конфигурации Claude Code..."

# Определяем реальный путь к CCGLM
CCGLM_SCRIPT="$CCGLM_DIR/ccglm_mcp_server.py"

cat > "$CLAUDE_DIR/settings.json" << EOF
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash(git commit*)",
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_DIR/hooks/block-at-submit.sh"
          }
        ]
      },
      {
        "matcher": "Bash(rm -rf*)|Bash(sudo rm*)|Bash(chmod 777*)",
        "hooks": [
          {
            "type": "command",
            "command": "echo '{\"decision\": \"deny\", \"reason\": \"Dangerous command blocked\"}'"
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
            "command": "npm run lint --fix 2>/dev/null || true"
          }
        ]
      }
    ],
    
    "PermissionRequest": [
      {
        "matcher": "Bash(npm *)|Bash(npx *)|Bash(git status*)|Bash(git diff*)|Bash(git add*)",
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
            "command": "$CLAUDE_DIR/hooks/ralph-check-completion.sh"
          }
        ]
      }
    ]
  },
  
  "mcpServers": {
    "ccglm-mcp": {
      "command": "python3",
      "args": ["$CCGLM_SCRIPT"],
      "timeout": 300000
    }
  },
  
  "permissions": {
    "allow": [
      "Bash(npm *)",
      "Bash(npx *)",
      "Bash(git status*)",
      "Bash(git diff*)",
      "Bash(git add*)",
      "Bash(ls *)",
      "Bash(cat *)",
      "Read",
      "Glob",
      "Grep"
    ],
    "deny": [
      "Bash(rm -rf /)",
      "Bash(sudo rm*)",
      "Bash(chmod 777*)"
    ]
  }
}
EOF

log_success "settings.json создан"

#───────────────────────────────────────────────────────────────────────────────
# ШАГ 9: Создание шаблонов
#───────────────────────────────────────────────────────────────────────────────
echo ""
log_info "ШАГ 9: Создание шаблонов..."

cat > "$CLAUDE_DIR/templates/PROMPT.md" << 'EOF'
# Task Execution Context

## Specification
Read the specification at: `agent-os/specs/{FEATURE}/specification.md`

## Task Plan
Follow the tasks in: `@fix_plan.md`

## Instructions

1. Read the specification completely before starting
2. Execute tasks one at a time
3. Mark each task as complete by changing `- [ ]` to `- [x]`
4. After completing a task, verify it works
5. Continue until ALL tasks are marked complete

## Completion Promise

I will mark ALL_TASKS_COMPLETE when:
- All checkboxes in @fix_plan.md are marked [x]
- All tests pass
- Code is properly formatted

---

Begin execution now. Start with the first uncompleted task.
EOF

log_success "Шаблоны созданы"

#───────────────────────────────────────────────────────────────────────────────
# ШАГ 10: Создание алиасов
#───────────────────────────────────────────────────────────────────────────────
echo ""
log_info "ШАГ 10: Создание алиасов..."

# Определяем shell config файл
if [ -f "$HOME_DIR/.zshrc" ]; then
    SHELL_RC="$HOME_DIR/.zshrc"
elif [ -f "$HOME_DIR/.bashrc" ]; then
    SHELL_RC="$HOME_DIR/.bashrc"
else
    SHELL_RC="$HOME_DIR/.bashrc"
    touch "$SHELL_RC"
fi

# Проверяем, есть ли уже алиасы
if ! grep -q "# Claude Code Stack Aliases" "$SHELL_RC" 2>/dev/null; then
    cat >> "$SHELL_RC" << EOF

# Claude Code Stack Aliases
# Добавлено автоматически установщиком стека

# Agent OS
alias aos='cd $AGENT_OS_DIR'
alias aos-install='$AGENT_OS_DIR/scripts/project-install.sh'

# CCGLM
alias ccglm='ANTHROPIC_BASE_URL=https://api.z.ai/api/anthropic claude --dangerously-skip-permissions -c'

# Быстрый запуск Claude в текущем проекте
alias cc='claude'

# Проверка стека
alias stack-check='echo "Claude: \$(claude --version 2>/dev/null || echo not installed)"; echo "Agent OS: \$([[ -d ~/agent-os ]] && echo installed || echo not found)"; echo "CCGLM: \$([[ -f ~/IA/ccglm-mcp/ccglm_mcp_server.py ]] && echo installed || echo not found)"'
EOF
    log_success "Алиасы добавлены в $SHELL_RC"
else
    log_info "Алиасы уже существуют"
fi

#───────────────────────────────────────────────────────────────────────────────
# ФИНАЛ: Проверка установки
#───────────────────────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════════════════════════"
echo "  📋 ПРОВЕРКА УСТАНОВКИ"
echo "═══════════════════════════════════════════════════════════════════════════════"
echo ""

echo -n "Claude Code CLI: "
if command -v claude &> /dev/null; then
    echo -e "${GREEN}✅ $(claude --version 2>/dev/null || echo 'installed')${NC}"
else
    echo -e "${RED}❌ не установлен${NC}"
fi

echo -n "Agent OS: "
if [ -d "$AGENT_OS_DIR" ]; then
    echo -e "${GREEN}✅ $AGENT_OS_DIR${NC}"
else
    echo -e "${RED}❌ не найден${NC}"
fi

echo -n "CCGLM MCP: "
if [ -f "$CCGLM_SCRIPT" ]; then
    echo -e "${GREEN}✅ $CCGLM_DIR${NC}"
else
    echo -e "${RED}❌ не найден${NC}"
fi

echo -n "Hooks: "
if [ -f "$CLAUDE_DIR/hooks/ralph-check-completion.sh" ]; then
    echo -e "${GREEN}✅ настроены${NC}"
else
    echo -e "${RED}❌ не настроены${NC}"
fi

echo -n "Settings: "
if [ -f "$CLAUDE_DIR/settings.json" ]; then
    echo -e "${GREEN}✅ создан${NC}"
else
    echo -e "${RED}❌ не создан${NC}"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════════════════════"
echo "  🎉 УСТАНОВКА ЗАВЕРШЕНА!"
echo "═══════════════════════════════════════════════════════════════════════════════"
echo ""
echo "📌 СЛЕДУЮЩИЕ ШАГИ:"
echo ""
echo "  1. Отредактируйте GLM токен:"
echo "     nano $CCGLM_DIR/.env"
echo ""
echo "  2. Перезагрузите shell:"
echo "     source $SHELL_RC"
echo ""
echo "  3. Авторизуйтесь в Claude Code:"
echo "     claude"
echo "     (следуйте инструкциям)"
echo ""
echo "  4. Проверьте MCP серверы:"
echo "     claude mcp list"
echo ""
echo "  5. Установите Agent OS в проект:"
echo "     cd /ваш/проект"
echo "     ~/agent-os/scripts/project-install.sh"
echo ""
echo "═══════════════════════════════════════════════════════════════════════════════"
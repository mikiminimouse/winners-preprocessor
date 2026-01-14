#!/bin/bash
# Подготовка Ralph session для фичи

FEATURE_NAME="$1"

if [ -z "$FEATURE_NAME" ]; then
    echo "Usage: $0 <feature-name>"
    echo ""
    echo "Available specs:"
    ls -1 agent-os/specs/ 2>/dev/null || echo "  No specs found. Run /shape-spec first."
    exit 1
fi

SPEC_DIR="agent-os/specs/$FEATURE_NAME"

if [ ! -d "$SPEC_DIR" ]; then
    echo "❌ Spec not found: $SPEC_DIR"
    echo ""
    echo "Create spec first:"
    echo "  claude"
    echo "  > /shape-spec $FEATURE_NAME"
    echo "  > /write-spec"
    echo "  > /create-tasks"
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

    TASK_COUNT=$(grep -c '\[ \]' @fix_plan.md)
    echo "✅ Created @fix_plan.md with $TASK_COUNT tasks"
else
    echo "⚠️  No tasks.md found in $SPEC_DIR"
    echo "# Implementation Plan: $FEATURE_NAME" > @fix_plan.md
    echo "" >> @fix_plan.md
    echo "- [ ] TODO: Run /create-tasks to generate tasks" >> @fix_plan.md
    TASK_COUNT=1
fi

# 2. Создать PROMPT.md
cat > PROMPT.md << EOF
# Autonomous Execution: $FEATURE_NAME

## Context
- Specification: @$SPEC_DIR/spec.md (если существует)
- Tasks: @@fix_plan.md
- Project rules: @.claude/
- Standards: @agent-os/standards/

## Instructions

Use AgentOS commands to implement this feature:

1. Load context from specification
2. For each unchecked task in @fix_plan.md:
   - Analyze requirements
   - Implement using TDD approach
   - Use GLM MCP for boilerplate (if available)
   - Run tests
   - Commit changes
   - Mark task [x] in @fix_plan.md
3. Continue until all tasks complete

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

When ALL tasks complete, output: <promise>ALL_TASKS_COMPLETE</promise>
EOF

echo "✅ Created PROMPT.md"

# 3. Инициализировать session log
mkdir -p logs
SESSION_LOG="logs/session-$(date +%Y-%m-%d-%H%M).md"

cat > "$SESSION_LOG" << EOF
# Session Log: $FEATURE_NAME

**Started**: $(date)
**Branch**: $(git branch --show-current 2>/dev/null || echo "not a git repo")
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
if git diff-index --quiet HEAD -- 2>/dev/null; then
    echo "  ✅ No uncommitted changes"
else
    echo "  ⚠️  Warning: You have uncommitted changes"
    echo "     Consider committing or stashing them before starting Ralph loop"
fi

# Проверка на существующий .needs_human_intervention
if [ -f ".needs_human_intervention" ]; then
    echo "  ⚠️  Warning: .needs_human_intervention file exists"
    echo "     Previous session may have been blocked"
    echo "     Review and remove before continuing"
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
echo "     watch -n 10 'cat @fix_plan.md'"
echo ""
echo "═══════════════════════════════════════════════════════════"

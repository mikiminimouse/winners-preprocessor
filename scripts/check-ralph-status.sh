#!/bin/bash
# Проверка статуса Ralph session

echo "📊 Ralph Session Status"
echo "════════════════════════════════════════════════════════"

# 1. Проверка @fix_plan.md
if [ -f "@fix_plan.md" ]; then
    TOTAL_TASKS=$(grep -c '- \[.\]' @fix_plan.md 2>/dev/null || echo "0")
    COMPLETED_TASKS=$(grep -c '- \[x\]' @fix_plan.md 2>/dev/null || echo "0")
    PENDING_TASKS=$(grep -c '- \[ \]' @fix_plan.md 2>/dev/null || echo "0")

    if [ "$TOTAL_TASKS" -gt 0 ]; then
        PROGRESS=$((COMPLETED_TASKS * 100 / TOTAL_TASKS))
        echo ""
        echo "Tasks Progress:"
        echo "  Total: $TOTAL_TASKS"
        echo "  Completed: $COMPLETED_TASKS"
        echo "  Pending: $PENDING_TASKS"
        echo "  Progress: ${PROGRESS}%"
    else
        echo ""
        echo "  No tasks found in @fix_plan.md"
    fi
else
    echo ""
    echo "⚠️  No @fix_plan.md found"
    echo "   Run: ./scripts/prepare-ralph-session.sh <feature-name>"
fi

# 2. Проверка на human intervention
if [ -f ".needs_human_intervention" ]; then
    echo ""
    echo "🚨 HUMAN INTERVENTION NEEDED:"
    if command -v jq &> /dev/null; then
        cat .needs_human_intervention | jq '.'
    else
        cat .needs_human_intervention
    fi
else
    echo ""
    echo "✅ No intervention needed"
fi

# 3. Git статус
if git rev-parse --git-dir > /dev/null 2>&1; then
    echo ""
    echo "Git Status:"
    COMMITS_AHEAD=$(git rev-list --count HEAD ^main 2>/dev/null || git rev-list --count HEAD ^master 2>/dev/null || echo "0")
    echo "  Commits ahead of main: $COMMITS_AHEAD"
    echo "  Current branch: $(git branch --show-current)"

    # 4. Последние коммиты
    if [ "$COMMITS_AHEAD" -gt 0 ]; then
        echo ""
        echo "Recent commits:"
        git log --oneline -5
    fi
else
    echo ""
    echo "⚠️  Not a git repository"
fi

# 5. Session logs
echo ""
echo "Session Logs:"
if ls logs/session-*.md 1> /dev/null 2>&1; then
    LATEST_LOG=$(ls -t logs/session-*.md | head -1)
    echo "  Latest: $LATEST_LOG"
    echo "  View: cat $LATEST_LOG"
else
    echo "  No session logs found"
fi

echo ""
echo "════════════════════════════════════════════════════════"

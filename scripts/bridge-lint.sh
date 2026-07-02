#!/bin/bash
# bridge-lint.sh — manufacturing-bridge 태그 검증 (Tier 2)
# Reads patterns registry from harness/patterns/manufacturing-bridge.md frontmatter
# Asserts that changed .md files carry valid manufacturing-bridge: tags
set -eo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BRIDGE_FILE="$ROOT/harness/patterns/manufacturing-bridge.md"

get_pattern_ids() {
    awk '/^patterns:/{f=1;next} f&&/^  - id:/{print $NF} f&&/^[a-z]/&&!/^  /{exit}' "$BRIDGE_FILE"
}

check_file() {
    local file="$1"
    local rel="${file#$ROOT/}"

    case "$rel" in .git/*|P2-hippocampus/*|node_modules/*|venv/*|__pycache__/*|cron/output/*|logs/*) return 0;; esac
    # Tier 2 enforcement: 패턴 정의/규칙 파일만 검사
    case "$rel" in harness/*|P0-brainstem/*|AGENTS.md) ;; *) return 0;; esac

    local tags
    tags=$(grep -o 'manufacturing-bridge:[a-z0-9_-]*' "$file" 2>/dev/null || true)

    if [ -z "$tags" ]; then
        echo "  [WARN] $rel — no manufacturing-bridge tag"
        return 1
    fi

    local valid_ids
    valid_ids=$(get_pattern_ids)
    local has_error=0

    while IFS= read -r tag; do
        [ -z "$tag" ] && continue
        local tag_id="${tag#manufacturing-bridge:}"
        if ! echo "$valid_ids" | grep -qxF "$tag_id"; then
            echo "  [WARN] $rel — unknown tag '$tag'"
            has_error=1
        fi
    done <<< "$tags"

    return $has_error
}

PATTERN_COUNT=$(get_pattern_ids | wc -l | tr -d ' ')
echo "=== bridge-lint (Tier 2) — 등록 패턴: $PATTERN_COUNT ==="

CHANGED=$(git -C "$ROOT" diff --name-only HEAD 2>/dev/null; echo; git -C "$ROOT" diff --name-only --cached 2>/dev/null || true)

if [ -z "$(echo "$CHANGED" | tr -d '[:space:]')" ]; then
    echo "변경 없음. pass."
    exit 0
fi

ERRORS=0
while IFS= read -r file; do
    [ -z "$file" ] && continue
    [ ! -f "$ROOT/$file" ] && continue
    check_file "$ROOT/$file" || ERRORS=$((ERRORS + 1))
done <<< "$CHANGED"

if [ "$ERRORS" -gt 0 ]; then
    echo "---"
    echo "bridge-lint: $ERRORS WARNING (Tier 2)"
    echo "provenance에 manufacturing-bridge:<패턴id> 태그 추가 필요"
    echo "정본: harness/patterns/manufacturing-bridge.md"
else
    echo "bridge-lint: pass"
fi

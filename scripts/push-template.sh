#!/usr/bin/env bash
# push-template.sh — Push local changes to public template repo
# Automatically sanitizes personal data, filters runtime state, pushes to public/main
set -euo pipefail

PUBLIC_REMOTE="public"
PUBLIC_BRANCH="main"
WORKTREE="/tmp/drewgent-push-$$"
TRACKING_FILE=".last-template-push"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔══════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  opencode-drewgent → Public Template Push   ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════╝${NC}"

# ── Step 0: Fetch latest public state ──
echo -e "\n${BLUE}[0/5] Fetching public remote...${NC}"
git fetch "$PUBLIC_REMOTE" 2>&1 | head -3
echo -e "${GREEN}  ✓ public/main at $(git rev-parse --short $PUBLIC_REMOTE/$PUBLIC_BRANCH)${NC}"

# ── Step 1: Detect changes since last push ──
echo -e "\n${BLUE}[1/5] Detecting changes since last template push...${NC}"

# Use tracking file if available, otherwise diff against public/main
if [[ -f "$TRACKING_FILE" ]]; then
  BASE=$(cat "$TRACKING_FILE")
  echo -e "  Using tracking file: ${YELLOW}$BASE${NC}"
else
  BASE="$PUBLIC_REMOTE/$PUBLIC_BRANCH"
  echo -e "  No tracking file — diffing against ${YELLOW}$BASE${NC}"
fi

CHANGED_FILES=$(git diff --name-only "$BASE" --diff-filter=ACMR HEAD 2>/dev/null || echo "")

if [[ -z "$CHANGED_FILES" ]]; then
  echo -e "${YELLOW}  No changes detected since last push.${NC}"
  exit 0
fi

echo -e "${GREEN}  ${CHANGED_FILES} files changed${NC}"

# ── Step 2: Filter template-safe files ──
echo -e "\n${BLUE}[2/5] Filtering template-safe files...${NC}"

# Files that should NEVER go to public
EXCLUDE_PATTERNS=(
  "^agent-dashboard-state"
  "^config\.yaml"
  "^\.env"
  "^kanban\.db"
  "^agent/"
  "^agents/"
  "^@memory/"
  "^cron/jobs\.json"
  "^P2-hippocampus/kanban/"
  "^P2-hippocampus/knowledge/"
  "^P2-hippocampus/memories/"
  "^P5-ego/config/"
  "^P5-ego/state/"
  "^P5-ego/wiki/compiled/"
  "^scripts/archive/"
  "^cron/output/"
  "node_modules/"
  "\.omo/"
  "\.plans/"
  "nix/"
  "flake\."
  "^plans/"
  "\.log$"
  "cache/"
  "^source/"
  "^website/"
)

TEMPLATE_FILES=()
for f in $CHANGED_FILES; do
  skip=false
  for pattern in "${EXCLUDE_PATTERNS[@]}"; do
    if [[ "$f" =~ $pattern ]]; then
      echo -e "  ${RED}✗${NC} $f (personal)"
      skip=true
      break
    fi
  done
  if [[ "$skip" == false ]]; then
    TEMPLATE_FILES+=("$f")
    echo -e "  ${GREEN}✓${NC} $f"
  fi
done

if [[ ${#TEMPLATE_FILES[@]} -eq 0 ]]; then
  echo -e "${YELLOW}  No template-safe files to push.${NC}"
  exit 0
fi

# ── Step 3: Create worktree ──
echo -e "\n${BLUE}[3/5] Creating worktree from public/$PUBLIC_BRANCH...${NC}"
git worktree add "$WORKTREE" "$PUBLIC_REMOTE/$PUBLIC_BRANCH" 2>&1 | head -3

# ── Step 4: Copy + sanitize files ──
echo -e "\n${BLUE}[4/5] Copying and sanitizing files...${NC}"

for f in "${TEMPLATE_FILES[@]}"; do
  if [[ -f "$f" ]]; then
    mkdir -p "$(dirname "$WORKTREE/$f")"
    cp "$f" "$WORKTREE/$f"
    # Sanitize: replace personal domain
    if grep -q "humanerd\.kr" "$WORKTREE/$f" 2>/dev/null; then
      sed -i '' 's/humanerd\.kr/YOUR_DOMAIN/g' "$WORKTREE/$f"
      echo -e "  ${YELLOW}↻${NC} $f (sanitized YOUR_DOMAIN)"
    fi
    # Sanitize: replace personal email
    if grep -q "drew@humanerd" "$WORKTREE/$f" 2>/dev/null; then
      sed -i '' 's/drew@humanerd\.ai/your-email@example.com/g' "$WORKTREE/$f"
      echo -e "  ${YELLOW}↻${NC} $f (sanitized email)"
    fi
    # Sanitize: replace personal Docker Hub
    if grep -q "YOUR_DOCKER_USER/" "$WORKTREE/$f" 2>/dev/null; then
      sed -i '' 's/humanerdkr\//YOUR_DOCKER_USER\//g' "$WORKTREE/$f"
      echo -e "  ${YELLOW}↻${NC} $f (sanitized docker user)"
    fi
    # Sanitize: replace personal ARD identifiers
    if grep -q "urn:air:humanerd\." "$WORKTREE/$f" 2>/dev/null; then
      sed -i '' 's/urn:air:humanerd[^:]*/urn:air:YOUR_DOMAIN/g' "$WORKTREE/$f"
      echo -e "  ${YELLOW}↻${NC} $f (sanitized ARD identifier)"
    fi
  fi
done

# ── Step 5: Commit + push ──
echo -e "\n${BLUE}[5/5] Committing and pushing...${NC}"

cd "$WORKTREE"
git add -A

if git diff --cached --quiet; then
  echo -e "${YELLOW}  No changes to commit (all were filtered or already in template).${NC}"
else
  # Generate commit message from changed files
  CHANGED_LIST=$(git diff --cached --name-only | head -10 | tr '\n' ' ')
  git commit -m "template: sync $(date +%Y-%m-%d)" -m "Files: $CHANGED_LIST"
  git push "$PUBLIC_REMOTE" "HEAD:$PUBLIC_BRANCH" 2>&1 | tail -5
  echo -e "${GREEN}  ✓ Pushed to $PUBLIC_REMOTE/$PUBLIC_BRANCH${NC}"
fi

# Cleanup
cd /Users/drew/.drewgent
git worktree remove "$WORKTREE"

# Update tracking file
git rev-parse HEAD > "$TRACKING_FILE"
echo -e "  ✓ Updated tracking file"

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Done! Template is live.                    ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"

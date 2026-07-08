#!/usr/bin/env bash
# push-template.sh — Push local changes to public template repo
# Automatically sanitizes personal data, filters runtime state, pushes to public/main
set -euo pipefail

PUBLIC_REMOTE="public"
PUBLIC_BRANCH="main"
WORKTREE="/tmp/loragent-push-$$"
TRACKING_FILE=".last-template-push"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔══════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  opencode-loragent → Public Template Push   ║${NC}"
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
  # ── Runtime / personal ──
  "^agent-dashboard-state"
  "^config\.yaml"
  "^\.env$"
  "^\.envrc$"
  "^kanban\.db"
  "^@memory/"
  "^@identity/"
  "^cron/jobs\.json"
  "^cron/output/"

  # ── Hermes legacy (dead code, removed 2026-07-07) ──
  "^agent/"
  "^agents/"
  "^acp_adapter/"
  "^acp_registry/"
  "^brain/"
  "^customize/"
  "^datagen-config-examples/"
  "^docker/"
  "^docs/"
  "^loragent_cli/"
  "^environments/"
  "^gateway/"
  "^hooks/"
  "^kanban/"
  "^landingpage/"
  "^modules/"
  "^optional-skills/"
  "^packaging/"
  "^plugins/"
  "^tools/"
  "^tests/"
  "^run_agent\.py"
  "^cli\.py"
  "^rl_cli\.py"
  "^batch_runner\.py"
  "^cron_runner\.py"
  "^mcp_serve\.py"
  "^mini_swe_runner\.py"
  "^model_tools\.py"
  "^toolsets\.py"
  "^toolset_distributions\.py"
  "^trajectory_compressor\.py"
  "^utils\.py"
  "^check_loragent_update\.py"
  "^loragent_constants\.py"
  "^loragent_logging\.py"
  "^loragent_state\.py"
  "^loragent_time\.py"
  "^loragent$"
  "^loragent-architecture\.html"
  "^cli-config\.yaml\.example"
  "^MANIFEST\.in"
  "^pyproject\.toml"
  "^setup-loragent\.sh"
  "^SOUL\.md$"
  "^DOCKERHUB\.md$"
  "^kanban-orchestrator\.md"
  "^cq-all-zones\.png"
  "^Dockerfile$"
  "^Dockerfile\.simple$"
  "^\.gitmodules$"

  # ── Private scripts (agent infra, not template-worthy) ──
  "^scripts/content_"
  "^scripts/cron_seo_"
  "^scripts/ingest_"
  "^scripts/recall\.py$"
  "^scripts/seo_"
  "^scripts/trend_"
  "^scripts/n8n_trigger_runner\.py$"
  "^scripts/oneshot_digest\.py$"
  "^scripts/loragent_gbrain_watchdog\.sh$"
  "^scripts/wordpress-mcp-server\.js$"

  # ── Junk / Hermes-era releases ──
  "^Ep\.[2-8]\.html$"
  "^compression-checkpoint-phase1\.md$"
  "^refactor_plan_phase_[abc]\.md$"
  "^RELEASE_v0\.[2-7]\.0\.md$"

  # ── Content / site-specific ──
  "^content-graph-engine/"
  "^wordpress/"
  "^seo-i-backend/"

  # ── Build / infra ──
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

# ── Step 2.5: Secret scan ──
echo -e "\n${BLUE}[2.5/5] Scanning for hardcoded secrets...${NC}"

SECRET_PATTERNS=(
  'discord\.com/api/webhooks/'        # Discord webhooks
  'slack\.com/api/webhooks/'          # Slack webhooks
  'api\.telegram\.org/bot'            # Telegram bot tokens
  'sk-[A-Za-z0-9]{20,}'              # OpenAI/Anthropic keys
  'ghp_[A-Za-z0-9]{36}'              # GitHub personal access tokens
  'gho_[A-Za-z0-9]{36}'              # GitHub OAuth tokens
  'xox[baprs]-[A-Za-z0-9-]{24,}'     # Slack tokens
  'AKIA[0-9A-Z]{16}'                 # AWS access keys
)

SECRET_FOUND=false
for f in "${TEMPLATE_FILES[@]}"; do
  if [[ -f "$f" ]]; then
    for pattern in "${SECRET_PATTERNS[@]}"; do
      if grep -qE "$pattern" "$f" 2>/dev/null; then
        matches=$(grep -oE "$pattern" "$f" | head -1)
        echo -e "  ${RED}⚠ SECRET DETECTED${NC} in $f: ${YELLOW}$matches${NC}"
        SECRET_FOUND=true
      fi
    done
  fi
done

if [[ "$SECRET_FOUND" == true ]]; then
  echo -e "\n${RED}╔═══════════════════════════════════════════════════════════╗${NC}"
  echo -e "${RED}║  BLOCKED: Hardcoded secrets detected in template files.   ║${NC}"
  echo -e "${RED}║  Fix them (use env vars, not literals) before re-pushing. ║${NC}"
  echo -e "${RED}╚═══════════════════════════════════════════════════════════╝${NC}"
  git worktree remove "$WORKTREE" 2>/dev/null || true
  exit 1
fi

echo -e "${GREEN}  ✓ No secrets detected${NC}"

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

# ── Step 4.5: Remove excluded files from worktree ──
echo -e "\n${BLUE}[4.5/5] Removing excluded/stale files from worktree...${NC}"

REMOVED_COUNT=0
# Remove files that match EXCLUDE_PATTERNS
while IFS= read -r f; do
  skip=false
  for pattern in "${EXCLUDE_PATTERNS[@]}"; do
    if [[ "$f" =~ $pattern ]]; then
      skip=true
      break
    fi
  done
  if [[ "$skip" == true ]] && [[ -f "$WORKTREE/$f" ]]; then
    rm "$WORKTREE/$f"
    echo -e "  ${RED}✗${NC} $f (excluded)"
    ((REMOVED_COUNT++))
  fi
done < <(cd "$WORKTREE" && git ls-files 2>/dev/null)

# Remove empty directories that had all their files removed
(cd "$WORKTREE" && find . -type d -empty -not -path './.git/*' -delete 2>/dev/null) || true

if [[ $REMOVED_COUNT -gt 0 ]]; then
  echo -e "  ${GREEN}  Removed $REMOVED_COUNT excluded file(s)${NC}"
else
  echo -e "  ${YELLOW}  No excluded files to remove${NC}"
fi

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
cd /Users/drew/.loragent
git worktree remove "$WORKTREE"

# Update tracking file
git rev-parse HEAD > "$TRACKING_FILE"
echo -e "  ✓ Updated tracking file"

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Done! Template is live.                    ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"

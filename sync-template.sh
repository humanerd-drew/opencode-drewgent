#!/usr/bin/env bash
# sync-template.sh — Sync template-worthy files from ~/.{{AGENT_NAME_LOWER}}/ to opencode-drewgent/
# Direct push to humanerd-drew/opencode-drewgent.
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

TEMPLATE_DIR="$(cd "$(dirname "$0")" && pwd)"
SOURCE_DIR="$(dirname "$TEMPLATE_DIR")"

echo -e "${BLUE}╔══════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  opencode-drewgent → Template Sync          ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════╝${NC}"

# ── Tooling paths (sync from ~/.{{AGENT_NAME_LOWER}}/ to template) ──
# Blueprint docs (AGENTS.md, README, @identity/, @action/) are maintained
# directly in the template repo — NOT synced.
PATHS=(
  .opencode opencode.jsonc
  .env.example .gitignore .github
  services cron harness
  skills
  .well-known
)

# ── Copy from SOURCE_DIR → TEMPLATE_DIR ──
echo -e "\n${BLUE}[1/3] Copying template files from drewgent...${NC}"
for p in "${PATHS[@]}"; do
  src="$SOURCE_DIR/$p"
  dst="$TEMPLATE_DIR/$p"
  if [[ -e "$src" ]]; then
    rsync -a --delete "${src}/" "${dst}/" 2>/dev/null || (cp -Rf "$src" "$dst" && echo "  ⚠ fallback cp used")
    echo -e "  ${GREEN}✓${NC} $p"
  else
    echo -e "  ${YELLOW}⚠${NC} $p (not found)"
  fi
done

# ── Sanitize personal data ──
echo -e "\n${BLUE}[2/3] Sanitizing personal data...${NC}"

cd "$TEMPLATE_DIR"

# Sanitize function: find and replace in non-binary files
sanitize() {
  local pattern="$1" replacement="$2"
  while IFS= read -r f; do
    if grep -q "$pattern" "$f" 2>/dev/null; then
      sed -i '' "s/$pattern/$replacement/g" "$f"
      echo -e "  ${YELLOW}↻${NC} $(echo "$f" | sed "s|$TEMPLATE_DIR/||")"
    fi
  done < <(git ls-files 2>/dev/null | xargs -I{} file "$TEMPLATE_DIR/{}" 2>/dev/null | grep text | cut -d: -f1)
}

# ── Personal data patterns ──
sanitize "humanerd\.kr" "YOUR_DOMAIN"
sanitize "drew@humanerd\.ai" "your-email@example.com"
sanitize "humanerdkr/" "YOUR_DOCKER_USER/"
sanitize "/Users/drew/" "~/"
sanitize "drewgent-agent\.humanerd\.ai" "docs.YOUR_AGENT_DOMAIN"
sanitize "@humanerd" "@yourname"
sanitize "/Volumes/humanerd/" "/Volumes/YOUR_NAS/"
sanitize "id_ed25519_dr2w247" "YOUR_SSH_KEY"
sanitize "Drew Kim" "Your Name"
sanitize "100\.110\.130\.54" "YOUR_NAS_IP"
sanitize "port 8528" "port 22"
sanitize "\-p 8528" "-p 22"
sanitize "8528 (LAN)" "22 (LAN)"
sanitize "dr2w247@github\.com" "your-github@example.com"

# ── Commit + push ──
echo -e "\n${BLUE}[3/3] Committing and pushing...${NC}"

cd "$TEMPLATE_DIR"

if git diff --quiet && git diff --cached --quiet; then
  echo -e "${YELLOW}  No changes${NC}"
else
  git add -A
  CHANGED=$(git diff --cached --name-only | head -10 | tr '\n' ' ')
  git commit -m "template: sync $(date +%Y-%m-%d)" -m "Files: $CHANGED"
  git push origin main 2>&1 | tail -5
  echo -e "${GREEN}  ✓ Pushed to origin/main${NC}"
fi

echo -e "\n${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Done! Template is live.                   ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"

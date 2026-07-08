#!/usr/bin/env bash
set -euo pipefail

# init-template.sh — Initialize a fork of opencode-loragent
# Usage: bash scripts/init-template.sh [--name yourgent]

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔══════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     opencode-loragent Template Setup        ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════╝${NC}"
echo ""

# Parse args
NAME=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --name) NAME="$2"; shift 2 ;;
    -n) NAME="$2"; shift 2 ;;
    *) echo "Unknown: $1"; exit 1 ;;
  esac
done

# Determine agent name
DIRNAME=$(basename "$(cd "$(dirname "$0")/.." && pwd)")

if [[ -z "$NAME" ]]; then
  case "$DIRNAME" in
    .loragent|loragent|opencode-loragent)
      echo -e "${YELLOW}Detected generic directory name: $DIRNAME${NC}"
      read -rp "Enter your agent name (e.g., 'alex' for 'alexgent'): " NAME
      ;;
    *)
      NAME="$DIRNAME"
      ;;
  esac
fi

AGENT_NAME="${NAME}gent"
echo -e "${GREEN}Setting up: $AGENT_NAME${NC}"
echo ""

# 1. Create personal directories
echo -e "${BLUE}[1/4] Creating personal data directories...${NC}"
mkdir -p "@memory/growth" "@memory/knowledge" "@memory/memories" "@memory/sessions"
mkdir -p "@action/incidents"
mkdir -p "P5-ego/config"
echo -e "${GREEN}  ✓ Created @memory/, @action/incidents/, P5-ego/config/${NC}"

# 2. Customize @identity/ templates
echo -e "${BLUE}[2/4] Customizing agent identity...${NC}"
if grep -q "{{AGENT_NAME}}" @identity/SELF_MODEL.md 2>/dev/null; then
  find @identity/ -name "*.md" -exec sed -i '' "s/{{AGENT_NAME}}/$AGENT_NAME/g" {} \;
  find @identity/ -name "*.md" -exec sed -i '' "s/{{PURPOSE}}/A personal AI engineering assistant/g" {} \;
  find @identity/ -name "*.md" -exec sed -i '' "s/{{ROLE}}/Autonomous software engineering agent/g" {} \;
  find @identity/ -name "*.md" -exec sed -i '' "s/{{TONE}}/Direct, precise, warm/g" {} \;
  find @identity/ -name "*.md" -exec sed -i '' "s/{{STYLE}}/Concise but thorough/g" {} \;
  find @identity/ -name "*.md" -exec sed -i '' "s/{{VALUES}}/Taste, leverage, provenance, governance/g" {} \;
  echo -e "${GREEN}  ✓ Replaced placeholders with $AGENT_NAME${NC}"
else
  echo -e "${YELLOW}  ⚠ No placeholders found — @identity/ may already be customized${NC}"
fi

# 3. Rename references (optional)
echo -e "${BLUE}[3/4] Renaming 'loragent' → '$AGENT_NAME'...${NC}"
# Only rename if this is a fresh clone (contains "loragent" extensively)
if grep -r "loragent" --include="*.md" --include="*.jsonc" --include="*.json" --include="*.sh" --include="*.py" . 2>/dev/null | grep -q "loragent"; then
  echo -e "${YELLOW}  Found loragent references. Replace all? [y/N]${NC}"
  read -r CONFIRM
  if [[ "$CONFIRM" =~ ^[yY] ]]; then
    find . \( -name "*.md" -o -name "*.jsonc" -o -name "*.json" -o -name "*.sh" -o -name "*.py" \) \
      -not -path "*/node_modules/*" -not -path "*/.git/*" \
      -exec sed -i '' "s/loragent/$AGENT_NAME/g" {} \;
    echo -e "${GREEN}  ✓ Renamed loragent → $AGENT_NAME${NC}"
  else
    echo -e "${YELLOW}  ⚠ Skipped rename (run skill(\"rename-loragent\") later)${NC}"
  fi
else
  echo -e "${GREEN}  ✓ No loragent references to rename${NC}"
fi

# 4. Gitignore check
echo -e "${BLUE}[4/4] Verifying gitignore...${NC}"
if [[ -f .gitignore ]]; then
  for pattern in "agent-dashboard-state.json" "config.yaml" "kanban.db" "@memory/"; do
    if grep -q "$pattern" .gitignore 2>/dev/null; then
      echo -e "${GREEN}  ✓ $pattern is gitignored${NC}"
    else
      echo -e "${YELLOW}  ⚠ $pattern NOT in .gitignore — add it${NC}"
    fi
  done
fi

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     Setup complete!                         ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo "Next steps:"
echo "  1. Edit @identity/SELF_MODEL.md with your agent's purpose"
echo "  2. Edit @identity/persona/SOUL.md with your agent's voice"
echo "  3. Review opencode.jsonc and configure MCP servers"
echo "  4. Start opencode: opencode"
echo ""

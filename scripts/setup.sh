#!/usr/bin/env bash
# setup.sh — First-run setup for opencode-drewgent
# Run after cloning: bash scripts/setup.sh
set -euo pipefail

AGENT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔══════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     opencode-drewgent Setup                  ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════╝${NC}"

ERRORS=0

# ── 1. Python version ──
echo -e "\n${BLUE}[1/5] Checking Python...${NC}"
PY=$(command -v python3 || command -v python || echo "")
if [ -z "$PY" ]; then
    echo -e "  ${RED}✗ Python not found. Install Python 3.11+${NC}"
    ERRORS=$((ERRORS + 1))
else
    VER=$("$PY" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
    if echo "$VER" | cut -d. -f1 | grep -qE '^[3-9]$'; then
        echo -e "  ${GREEN}✓${NC} $("$PY" --version)"
    else
        echo -e "  ${RED}✗ Need Python 3.11+, found $("$PY" --version)${NC}"
        ERRORS=$((ERRORS + 1))
    fi
fi

# ── 2. Install dependencies ──
echo -e "\n${BLUE}[2/5] Installing dependencies...${NC}"
if [ -f "$AGENT_DIR/requirements.txt" ]; then
    "$PY" -m pip install --user -r "$AGENT_DIR/requirements.txt" -q 2>&1 | grep -v "PEP 668\|hint:\|breaking\|WARNING:.*pip" | tail -3 || true
    echo -e "  ${GREEN}✓${NC} pip install complete"
else
    echo -e "  ${YELLOW}⚠ requirements.txt not found${NC}"
fi

# ── 3. Environment file ──
echo -e "\n${BLUE}[3/5] Checking environment...${NC}"
if [ -f "$AGENT_DIR/.env" ]; then
    echo -e "  ${GREEN}✓${NC} .env exists"
else
    echo -e "  ${YELLOW}⚠ .env not found — creating from .env.example${NC}"
    cp "$AGENT_DIR/.env.example" "$AGENT_DIR/.env"
    echo -e "  ${YELLOW}  → Edit .env and add your API keys:${NC}"
    echo -e "  ${YELLOW}    OPENCODE_API_KEY     (required — opencode serve)${NC}"
    echo -e "  ${YELLOW}    DISCORD_BOT_TOKEN    (optional — Discord integration)${NC}"
    echo -e "  ${YELLOW}    OLLAMA_HOST           (optional — knowledge.db vector search)${NC}"
fi

# ── 4. Platform services ──
echo -e "\n${BLUE}[4/5] Platform services...${NC}"
SVC_DIR="$AGENT_DIR/services"
if [ -d "$SVC_DIR" ]; then
    case "$(uname)" in
        Darwin)
            COUNT=$(ls "$SVC_DIR/launchd"/*.plist.example 2>/dev/null | wc -l | tr -d ' ')
            echo -e "  ${GREEN}✓${NC} $COUNT launchd templates found in services/launchd/"
            echo -e "  ${YELLOW}  To install:${NC}"
            echo -e "  ${YELLOW}    for f in services/launchd/*.plist.example; do${NC}"
            echo -e "  ${YELLOW}      n=\$(basename \"\$f\" .example)${NC}"
            echo -e "  ${YELLOW}      cp \"\$f\" ~/Library/LaunchAgents/\"\$n\"${NC}"
            echo -e "  ${YELLOW}      launchctl load ~/Library/LaunchAgents/\"\$n\"${NC}"
            echo -e "  ${YELLOW}    done${NC}"
            echo -e "  ${YELLOW}  (Edit plists first to replace {{PLACEHOLDERS}})${NC}"
            ;;
        Linux)
            COUNT=$(ls "$SVC_DIR/systemd"/*.service 2>/dev/null | wc -l | tr -d ' ')
            echo -e "  ${GREEN}✓${NC} $COUNT systemd templates found in services/systemd/"
            echo -e "  ${YELLOW}  To install:${NC}"
            echo -e "  ${YELLOW}    sudo cp services/systemd/*.service /etc/systemd/system/${NC}"
            echo -e "  ${YELLOW}    sudo systemctl enable --now yourgent-*${NC}"
            echo -e "  ${YELLOW}  (Edit .service files first to replace {{PLACEHOLDERS}})${NC}"
            ;;
        *)
            echo -e "  ${YELLOW}  See services/windows/ for setup instructions${NC}"
            ;;
    esac
fi

# ── 5. Ontology initialization ──
echo -e "\n${BLUE}[5/8] Ontology layer...${NC}"
if "$PY" -c "import numpy" 2>/dev/null; then
    echo -e "  ${GREEN}✓${NC} numpy (required for embeddings)"
else
    echo -e "  ${YELLOW}⚠ Installing numpy...${NC}"
    "$PY" -m pip install --user numpy -q 2>&1 | tail -1 || echo -e "  ${RED}✗ numpy install failed${NC}"
fi
if "$PY" "$AGENT_DIR/scripts/ontology_setup.py" 2>&1; then
    echo -e "  ${GREEN}✓${NC} ontology schema initialized"
else
    echo -e "  ${YELLOW}⚠ ontology init failed — run manually: python3 scripts/ontology_setup.py${NC}"
fi
if "$PY" "$AGENT_DIR/scripts/ingest_instructions.py" 2>&1; then
    echo -e "  ${GREEN}✓${NC} instructions ingested into knowledge.db"
else
    echo -e "  ${YELLOW}⚠ instruction ingest failed — run manually: python3 scripts/ingest_instructions.py${NC}"
fi

# ── 6. Launchd services (macOS only) ──
echo -e "\n${BLUE}[7/8] Quick verify...${NC}"
"$PY" -c "import croniter" 2>/dev/null && echo -e "  ${GREEN}✓${NC} croniter (scheduler)" || echo -e "  ${YELLOW}⚠ croniter not found — cron schedule parsing limited${NC}"
"$PY" -c "import yaml" 2>/dev/null && echo -e "  ${GREEN}✓${NC} pyyaml (config)" || echo -e "  ${YELLOW}⚠ pyyaml not found${NC}"
if [ -f "$AGENT_DIR/kanban.db" ]; then
    echo -e "  ${GREEN}✓${NC} kanban.db exists"
else
    echo -e "  ${YELLOW}⚠ kanban.db not found — created on first kanban task${NC}"
fi

echo ""
if [ "$ERRORS" -gt 0 ]; then
    echo -e "${RED}Setup incomplete — fix errors above and re-run.${NC}"
    exit 1
else
    echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  Setup complete!                             ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "Next:"
    echo -e "  1. Start opencode: ${BLUE}opencode${NC}"
    echo -e "  2. Run the lint gate: ${BLUE}bash scripts/bridge-lint.sh${NC}"
    echo -e "  3. (Recommended) Rename: ${BLUE}skill(\"rename-{{AGENT_NAME_LOWER}}\")${NC}"
    echo -e "  4. (macOS) Install launchd: follow instructions above"
    echo -e "  5. (Optional) Set up Discord: add DISCORD_BOT_TOKEN to .env"
    echo -e "  6. (Optional) Set up knowledge.db: ${BLUE}brew install ollama && ollama pull nomic-embed-text${NC}"
    echo -e "  7. (Optional) Upgrade relations: ${BLUE}python3 scripts/upgrade_relations.py${NC}"
fi

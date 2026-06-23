#!/bin/bash
# SEO Article Harvester — no_agent wrapper
# Calls the full harvester pipeline: RSS collect → crawl → label → report
set -euo pipefail

DREW_HOME="$HOME/.drewgent"
VENV_PYTHON="$DREW_HOME/venv/bin/python3"

# Load env for DISCORD_WEBHOOK_SEO
if [ -f "$DREW_HOME/.env" ]; then
    set -a; source "$DREW_HOME/.env"; set +a
fi

cd "$DREW_HOME"
exec "$VENV_PYTHON" "$DREW_HOME/scripts/cron_seo_harvester.py" "$@"

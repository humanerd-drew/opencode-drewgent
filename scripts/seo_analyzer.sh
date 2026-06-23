#!/bin/bash
# SEO Article Analyzer — no_agent wrapper
# Runs LLM analysis on newly collected articles in _new/
set -euo pipefail

DREW_HOME="$HOME/.drewgent"
VENV_PYTHON="$DREW_HOME/venv/bin/python3"

cd "$DREW_HOME"
exec "$VENV_PYTHON" "$DREW_HOME/skills/seo-article-harvester/scripts/analyzer.py" "$@"

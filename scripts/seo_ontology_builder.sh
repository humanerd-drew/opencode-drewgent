#!/bin/bash
# SEO Ontology Builder — weekly cron wrapper
set -euo pipefail

DREW_HOME="$HOME/.drewgent"
VENV_PYTHON="$DREW_HOME/venv/bin/python3"

cd "$DREW_HOME"
exec "$VENV_PYTHON" "$DREW_HOME/scripts/seo_ontology_builder.py" "$@"

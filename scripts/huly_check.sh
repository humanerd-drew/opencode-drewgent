#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR" || exit 1
HULY_KEY="$(grep '^HULY_KEY=' "$HOME/.hermes/.env" | head -1 | cut -d= -f2-)"
export HULY_KEY
# Run silently: suppress node warnings, only pass clean stdout through
exec 2>/dev/null
node huly_check.js

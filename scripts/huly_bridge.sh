#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR" || exit 1
# Read Huly API key from .env
HULY_KEY="$(grep '^HULY_KEY=' "$HOME/.hermes/.env" | head -1 | cut -d= -f2-)"
export HULY_KEY
exec node --no-warnings huly_bridge.js

#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR" || exit 1
HULY_KEY="$(grep '^HULY_KEY=' "$HOME/.hermes/.env" | head -1 | cut -d= -f2-)"
export HULY_KEY
exec 2>/dev/null
node huly_sync.js

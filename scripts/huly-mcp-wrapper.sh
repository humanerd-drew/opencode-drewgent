#!/bin/bash
# huly-mcp-wrapper.sh — Reads HULY_KEY from .hermes/.env and bridges to HULY_TOKEN
# Keeps the JWT token out of config.yaml by reading it at runtime.
# Used by Hermes config.yaml mcp_servers.huly

DIR="$(cd "$(dirname "$0")" && pwd)"
export HULY_URL="https://huly.app"
export HULY_WORKSPACE="humanerd"

# Read HULY_KEY safely from .env (strip quotes, trailing whitespace)
HULY_KEY="$(grep '^HULY_KEY=' "$HOME/.hermes/.env" | head -1 | sed 's/^HULY_KEY=//' | sed 's/^"//;s/"$//' | tr -d '[:space:]')"
export HULY_TOKEN="$HULY_KEY"

exec npx -y "@bgx4k3p/huly-mcp-server@latest" "$@"

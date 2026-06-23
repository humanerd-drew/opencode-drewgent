#!/bin/bash
set -euo pipefail

# gbrain watchdog — gbrain CLI health check.
# gbrain MCP tools are built into the platform; no daemon needed.
# Just verify the CLI is responsive and alert if not.

alerts=()
if ! command -v gbrain &>/dev/null; then
  alerts+=("⚠ gbrain: CLI not found in PATH")
else
  health_json=$(gbrain health --json 2>/dev/null || true)
  if [ -z "$health_json" ]; then
    alerts+=("⚠ gbrain: health check returned empty")
  fi
fi

if [ ${#alerts[@]} -eq 0 ]; then
  exit 0
fi

timestamp=$(date '+%Y-%m-%d %H:%M:%S %Z')
message="🚨 **gbrain watchdog** @ $timestamp

${alerts[*]}"

if [ -n "${HERMES_DISCORD_WEBHOOK:-}" ]; then
  curl -s -X POST -H "Content-Type: application/json" \
    -d "$(jq -n --arg c "$message" '{content: $c}')" \
    "$HERMES_DISCORD_WEBHOOK" >/dev/null
fi

printf '%s\n' "$message"

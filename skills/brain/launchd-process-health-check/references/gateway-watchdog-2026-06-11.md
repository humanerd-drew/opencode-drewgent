# Gateway Watchdog — Launchd-Based Self Healing (2026-06-11)

## Purpose

A `launchd`-based watchdog that runs every 5 minutes, independent of the gateway process. Checks:
1. `launchctl list ai.drewgent.gateway` → PID present and > 0?
2. `kill -0 <pid>` → process actually alive?
3. If either fails → `launchctl start ai.drewgent.gateway` to restart

## Files

| Path | Purpose |
|------|---------|
| `~/.drewgent/scripts/gateway_watchdog.sh` | Bash script: PID check + restart |
| `~/Library/LaunchAgents/ai.drewgent.gateway-watchdog.plist` | launchd job: run every 300s |
| `~/.drewgent/scripts/drewgent_launchd_watchdog.sh` | Symlink → gateway_watchdog.sh (cron-runner fallback) |
| `~/.drewgent/logs/gateway_watchdog.log` | Log output |

## Installation

```bash
# Load the watchdog
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ai.drewgent.gateway-watchdog.plist

# Verify
launchctl list ai.drewgent.gateway-watchdog
```

## How It Works

1. launchd runs `gateway_watchdog.sh` every 300s (StartInterval)
2. Script queries `launchctl list` JSON output, extracts PID
3. If PID == 0 or empty → `launchctl start` (gateway not active)
4. If PID exists but `kill -0` fails → `launchctl start` (stale PID)
5. Otherwise → log health OK and exit

## Why Not Use Cron

The drewgent cron runner runs **inside** the gateway process. If the gateway is dead, the cron runner is also dead. A launchd-based watchdog is independent and will still fire when the gateway has crashed.

## Related

- `launchd-process-health-check` skill — all sub-patterns of launchd failure
- `~/.drewgent/scripts/gateway_watchdog.sh` — the script
- `~/Library/LaunchAgents/ai.drewgent.gateway-watchdog.plist` — the plist

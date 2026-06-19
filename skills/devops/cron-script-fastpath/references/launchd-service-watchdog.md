# Launchd Service Watchdog Pattern

When a critical background process (gateway, cron-runner, etc.) needs automatic recovery independent of the process itself, use a **separate launchd watchdog** plist.

## Architecture

```
launchd process manager
  ├── ai.drewgent.gateway          (main service, KeepAlive on crash)
  └── ai.drewgent.gateway-watchdog (runs every 5 min, checks health)
```

The watchdog must be a **separate launchd job** because if the main process is dead, its internal cron ticker is also dead. A watchdog that runs inside the gateway cannot recover the gateway.

## Watchdog plist

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>ai.drewgent.MYSERVICE-watchdog</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>/path/to/watchdog.sh</string>
    </array>
    <key>StartInterval</key>
    <integer>300</integer>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/path/to/logs/watchdog.log</string>
    <key>StandardErrorPath</key>
    <string>/path/to/logs/watchdog.error.log</string>
</dict>
</plist>
```

Key settings:
- `StartInterval 300` — runs every 5 minutes (300 seconds)
- `RunAtLoad true` — runs immediately on load/boot
- Omit `KeepAlive` — this job runs on timer, not continuously

## Watchdog script pattern

```bash
#!/bin/bash
# watchdog.sh — health check + auto-restart for a managed service

PLIST_LABEL="ai.drewgent.myservice"
LOG="/path/to/logs/watchdog.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# 1. Is launchd reporting the service as active?
LAUNCHD_OUTPUT=$(launchctl list "$PLIST_LABEL" 2>/dev/null)
LAUNCHD_PID=$(echo "$LAUNCHD_OUTPUT" | python3 -c "
import sys, json; data = json.load(sys.stdin); print(data.get('PID', ''))
" 2>/dev/null)

if [ -z "$LAUNCHD_PID" ] || [ "$LAUNCHD_PID" = "0" ]; then
    echo "$TIMESTAMP [RESTART] launchd reports not active — starting..." >> "$LOG"
    launchctl start "$PLIST_LABEL" 2>&1 >> "$LOG"
    exit 0
fi

# 2. Is the reported PID actually alive?
if ! kill -0 "$LAUNCHD_PID" 2>/dev/null; then
    echo "$TIMESTAMP [RESTART] PID $LAUNCHD_PID stale — restarting..." >> "$LOG"
    launchctl start "$PLIST_LABEL" 2>&1 >> "$LOG"
    exit 0
fi

# 3. (Optional) Check for error accumulation
#    Only restart if errors exceed threshold, to avoid restart loops
RECENT_ERRORS=$(grep -c "Traceback\|NameError\|AttributeError" /path/to/logs/error.log 2>/dev/null || echo 0)
if [ "$RECENT_ERRORS" -gt 10 ]; then
    echo "$TIMESTAMP [RESTART] $RECENT_ERRORS recent errors — kickstarting..." >> "$LOG"
    launchctl kickstart -k "$PLIST_LABEL" 2>&1 >> "$LOG"
    exit 0
fi

echo "$TIMESTAMP [OK] PID $LAUNCHD_PID healthy" >> "$LOG"
exit 0
```

## Health check strategies

| Check | What it detects | When to restart |
|-------|----------------|-----------------|
| `launchctl list` PID presence | Process crashed, not launched | Immediately |
| `kill -0 PID` | PID is stale/zombie | Immediately |
| Error log threshold | Repeated failures without crash | After N errors |
| Log activity staleness | Process hung but not dead | After N minutes without log activity |
| Recent "connected" messages | Platform adapter disconnected | After N minutes without reconnect |

## Installation

```bash
# Load the watchdog
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ai.drewgent.myservice-watchdog.plist

# Or (older macOS):
launchctl load ~/Library/LaunchAgents/ai.drewgent.myservice-watchdog.plist

# Verify
launchctl list ai.drewgent.myservice-watchdog

# Check its first run output
cat /path/to/logs/watchdog.log
```

## Distinction from KeepAlive

- `KeepAlive { SuccessfulExit: false }` — restarts CRASHES (non-zero exit). Does NOT restart clean exits (exit 0).
- Watchdog — restarts STALE processes. Checks regular intervals, catches hangs and zombie PIDs.
- **Both layers are needed**: KeepAlive for instant crash recovery, watchdog for periodic health verification.

## Log management

Watchdog scripts generate log entries every check interval. Keep them bounded:
- Use `~/.drewgent/logs/` directory which has rotated logging
- Or log to a file that macOS rotates via `/etc/asl.conf` / `log rotate`

# 2026-06-10 launchd mass-failure — verified fix recipe

This reference is the **playbook that was actually executed on 2026-06-10**, distilled into a reproducible recipe. The 6/10 incident left 4 services dead (gateway, n8n, quartz-fswatch, quartz-deploy) and 22 days of cron stalled, undetected. The skill's main SKILL.md describes the diagnostic patterns; this file describes what to do once you've identified the gap.

---

## 0. Detection — the 5-min watchdog

Before the recipe: **install a watchdog first.** Without one, the next incident goes undetected for days. The watchdog used on 6/10 is canonical:

**Path**: `~/.hermes/scripts/drewgent_launchd_watchdog.sh` (symlink to `~/.drewgent/P4-cortex/scripts/drewgent_launchd_watchdog.sh`)

**Why `~/.hermes/scripts/`**: Hermes `cronjob` tool with `no_agent=True` requires scripts under that path (relative; the tool resolves the home directory).

**The script** (verbatim — paste into the path above):

```bash
#!/bin/bash
# drewgent_launchd_watchdog.sh
# 5분마다 launchd 서비스 상태를 검사하고, 1개 이상 PID=-면 Discord webhook으로 알림.

set -euo pipefail

WATCHED_LABELS=(
  "ai.drewgent.cron-runner"
  "ai.drewgent.gateway"
  "ai.drewgent.kanban-dashboard"
  "ai.drewgent.n8n"
  "com.drewgent.quartz-fswatch"
  "com.drewgent.quartz-deploy"
)

alerts=()
ok_count=0

for label in "${WATCHED_LABELS[@]}"; do
  line=$(launchctl list 2>/dev/null | awk -v lbl="$label" '$3 == lbl { print; exit }')
  if [ -z "$line" ]; then
    alerts+=("❌ $label: not registered")
    continue
  fi
  pid=$(echo "$line" | awk '{print $1}')
  exit_code=$(echo "$line" | awk '{print $2}')
  if [ "$pid" = "-" ]; then
    if [ "$exit_code" = "0" ]; then
      ok_count=$((ok_count+1))   # graceful stop — not an alert
    else
      alerts+=("⚠ $label: PID=- exit=$exit_code")
    fi
  else
    ok_count=$((ok_count+1))
  fi
done

total=${#WATCHED_LABELS[@]}
timestamp=$(date '+%Y-%m-%d %H:%M:%S %Z')

if [ ${#alerts[@]} -eq 0 ]; then
  exit 0  # silent when all ok (no_agent=True pattern: empty stdout = silent)
fi

message="🚨 **Drewgent launchd watchdog** @ $timestamp
$ok_count/$total services running

${alerts[*]}"

# Discord push (optional; HERMES_DISCORD_WEBHOOK env var)
if [ -n "${HERMES_DISCORD_WEBHOOK:-}" ]; then
  curl -s -X POST -H "Content-Type: application/json" \
    -d "$(jq -n --arg c "$message" '{content: $c}')" \
    "$HERMES_DISCORD_WEBHOOK" >/dev/null
fi

printf '%s\n' "$message"
```

**Cron registration** (Hermes tool call):

```
cronjob(action="create", name="Drewgent launchd watchdog",
        no_agent=True, schedule="every 5m",
        script="drewgent_launchd_watchdog.sh")
```

Script is bare filename (no path) — Hermes resolves it from `~/.hermes/scripts/`.

---

## 1. The canonical KeepAlive block

Apply this to **every** launchd plist. Verified pattern from 6/10 fix (5 plists patched simultaneously).

```xml
<key>KeepAlive</key>
<dict>
    <key>SuccessfulExit</key>
    <false/>
    <key>ThrottleInterval</key>
    <integer>10</integer>
</dict>
```

**Why these three keys**:
- `SuccessfulExit: false` → "treat exit 0 as a normal stop, don't restart" — actually means "restart on anything else, including graceful SIGTERM (Node.js/Python exit 0 trap)."
- `ThrottleInterval: 10` → bound restart storm; launchd waits ≥10s between respawns.

**Three anti-patterns to flag in any plist audit**:
| Form | Symptom | Failure mode |
|---|---|---|
| `<key>KeepAlive</key><true/>` | bare true | graceful SIGTERM → exit 0 → never restart |
| `<key>KeepAlive</key><false/>` | bare false | crash → never restart (literal config) |
| `<key>KeepAlive</key>` missing | no key | crash → restart only on next StartInterval tick (up to 60s gap) |

---

## 2. Plist audit — 5 plists in `~/Library/LaunchAgents/`

Standard Drewgent plist inventory (verify these exist + the Label key matches the filename):

| Filename | Label | Notes |
|---|---|---|
| `ai.drewgent.cron-runner.plist` | `ai.drewgent.cron-runner` | dispatcher loop, StartInterval=60 |
| `ai.drewgent.gateway.plist` | `ai.drewgent.gateway` | **label MUST match filename** (see Sub-pattern 4) |
| `ai.drewgent.kanban-dashboard.plist` | `ai.drewgent.kanban-dashboard` | flask on port 5555 |
| `ai.drewgent.n8n.plist` | `ai.drewgent.n8n` | may be missing — n8n case study in Sub-pattern 1 |
| `com.drewgent.quartz-fswatch.plist` | `com.drewgent.quartz-fswatch` | vault → wrangler pipeline |
| `com.drewgent.quartz-deploy.plist` | `com.drewgent.quartz-deploy` | explicit deploy trigger |

**Label mismatch (Sub-pattern 4)** is silent: `launchctl bootout ai.drewgent.gateway` returns "No such process" because the registered label is `ai.custom-agent.gateway` (the value inside the plist). Always cross-check filename vs. `<Label>` before restart commands.

---

## 3. Restart sequence (after plist edit)

```bash
UID_NUM=$(id -u)
SERVICE="ai.drewgent.gateway"  # the LABEL, not the filename

# 1. Unload (in case old label is still registered)
launchctl bootout gui/$UID_NUM/$SERVICE 2>/dev/null || true

# 2. Bootstrap (loads plist into launchd, but does not start)
launchctl bootstrap gui/$UID_NUM ~/Library/LaunchAgents/ai.drewgent.gateway.plist

# 3. Kickstart (actually starts the process)
launchctl kickstart -k gui/$UID_NUM/$SERVICE

# 4. Verify
sleep 3
launchctl list | grep $SERVICE
ps aux | grep <process-pattern> | grep -v grep
tail -10 <log-path>
```

**Note**: `kickstart -k` = "kill if running, then start fresh." Use this after plist edits to pick up new config.

**If launchd can't track the process (PID=- but process alive)**: this is launchd's known behavior for detached processes (cron-runner pattern). Don't conclude "stopped" from `launchctl list` alone — verify with `ps aux` and log mtime.

---

## 4. jobs.json fast-forward (gateway pattern)

When the gateway restarts, it does NOT re-read jobs.json into a fresh in-memory state from scratch — it re-reads once, but its `cron.jobs.get_due_jobs()` fast-forwards missed schedules.

**Verified on 6/10**: gateway started at 16:31:05 → log shows:
```
cron.jobs: Job 'SEO Article Harvester' missed its scheduled time (2026-05-19T18:00:00, grace=7200s).
            Fast-forwarding to next run: 2026-06-10T18:00:00
```

**Implication**: a gateway restart is **the** canonical recovery for stale jobs.json `next_run_at`. Don't manually patch jobs.json `next_run_at = now-5s` while the gateway is dead — the patch is invisible to the in-memory loop. **Restart first, then verify next_run_at future-dated.**

Sub-pattern 6 (verified): patching jobs.json `next_run_at` does NOT trigger execution if the scheduler process is dead. The in-memory state was loaded at gateway start; a JSON file edit does not propagate.

---

## 5. Quartz path (single source of truth)

**Source**: `~/.drewgent/humanerd-site/content/`
**Watch list** (in `quartz-fswatch.sh`):
- `~/.drewgent/memories/insights`
- `~/.drewgent/P4-cortex/growth`
- `~/.drewgent/P4-cortex/knowledge`
- `~/.drewgent/humanerd-site/content`

**Not source** (don't deploy from these):
- `~/Sites/quartz` — Quartz github template clone (no `content/` dir, 0 .md files). Harmless, leave alone.
- `~/humanerd` — old path in memory, not used. Don't recreate.

**Don't trust `last_status=ok` in jobs.json** — it's a stale marker from before any failure. Verify with cron output dir mtime + last log mtime.

---

## 6. Verification checklist (post-fix)

Use this on every launchd incident fix:

- [ ] `launchctl list | grep drewgent` → count of running (PID present) vs. stopped (PID=-)
- [ ] For each running service: `ps aux | grep <pattern>` confirms actual process
- [ ] For each listening service (gateway, kanban-dashboard, n8n): `lsof -i :<port>` shows LISTEN
- [ ] `~/.drewgent/cron/jobs.json`: all `enabled` jobs have future-dated `next_run_at`
- [ ] `~/.drewgent/P6-prefrontal/logs/cron-runner.log` mtime < 5 min (means scheduler is ticking)
- [ ] `~/.drewgent/logs/gateway.log` last entry is recent + "Cron ticker started" / equivalent
- [ ] Watchdog cron (`hermes cron list | grep -A3 watchdog`) is enabled, every 5m, no_agent
- [ ] All 5+ plists have `KeepAlive { SuccessfulExit: false, ThrottleInterval: 10 }`
- [ ] All plist `Label` keys match filenames
- [ ] Incident doc written to `~/.drewgent/P6-prefrontal/incidents/<descriptive-name>-<YYYYMMDD>.md` with: symptoms, root causes (multi-factor), resolution steps, verification, lessons

---

## 7. Common pitfalls (the 6/10 fix actually hit)

1. **`launchctl bootstrap` fails with "Input/output error"** — service is already registered under a different label. Use `launchctl bootout <old-label>` first. Verify with `launchctl print gui/$UID_NUM/<label>`.
2. **`launchctl kickstart` returns no error but process still won't start** — check `StandardErrorPath` log, often the binary is wrong path or missing dependency.
3. **Patch jobs.json `next_run_at = now-5s` and wait 90s → still nothing fires** — the gateway is dead. Restart it (Sub-pattern 6).
4. **Watchdog script path error**: must be under `~/.hermes/scripts/` (Hermes `cronjob no_agent=True` constraint). If you put it elsewhere, you get "Script path must be relative to ~/.hermes/scripts/" error.
5. **Plist edit doesn't take effect**: launchd caches plist at load time. You must `bootout` + `bootstrap` (not just `kickstart`) for plist changes to apply.
6. **Gateway `Cron ticker started` but no jobs run** — look for "missed its scheduled time" lines. Some jobs may have been past their grace window. Check `cron/jobs.py` grace constants.
7. **Label/filename mismatch silent failure** — `launchctl bootout/load <filename-without-ext>` looks for the Label, not the file. If they differ, the command silently does nothing. Always read the `<Label>` key directly from the plist before issuing commands.

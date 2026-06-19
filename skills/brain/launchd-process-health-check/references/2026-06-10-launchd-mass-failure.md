# 2026-06-10 Launchd Mass Failure — Raw Data

Session-specific detail captured during the 2026-06-10 status checkup. Used to ground the new "Reverse Pattern: Process Died and launchd Didn't Restart" section in the main SKILL.md.

## Snapshot at 2026-06-10 15:35 KST

```
$ launchctl list | grep drewgent
-	0	ai.drewgent.cron-runner
-	1	com.drewgent.quartz-deploy
1543	0	ai.drewgent.kanban-dashboard
-	0	com.drewgent.quartz-fswatch
-	64	com.drewgent.nas-mount
```

Five drewgent services; only `kanban-dashboard` (PID 1543) had a real PID. Four had `-` (dead). The fact that no service had crashed and recovered — no pattern of "died, restarted" — tells us KeepAlive was not actually keeping them up.

## Per-service findings

| Service | launchctl state | Last log mtime | Symptom |
|---|---|---|---|
| `ai.drewgent.cron-runner` | PID=- exit 0 | cron-runner.log absent (no per-tick logging) | All jobs.json last_run_at stuck at 2026-05-19 |
| `ai.drewgent.n8n` | PID=- (no row even) | n8n.log mtime 2026-06-04 16:41, ends with "Received SIGTERM. Shutting down..." | Port 5678 not listening |
| `com.drewgent.quartz-fswatch` | active count = 0, "not running" | unknown | Source path `~/humanerd` missing entirely |
| `com.drewgent.quartz-deploy` | "spawn scheduled" (not yet attempted) | unknown | Same source-path issue; deploy never got to its 5s debounce |
| `ai.drewgent.kanban-dashboard` | running PID 1543 | log mtime 6/10 (alive) | Port 5555 returns HTTP 000 — process alive but socket not bound |

## jobs.json state (sample, from `~/.drewgent/cron/jobs.json`)

```json
{
  "id": "96ad18409db7",
  "name": "SEO Article Harvester",
  "schedule": {"kind": "cron", "expr": "0 */6 * * *"},
  "next_run_at": "2026-05-19T18:00:00+09:00",
  "last_run_at": "2026-05-19T12:03:08.724854+09:00",
  "last_status": "ok"
}
```

22-day stale `next_run_at`. `last_status: ok` is a stale marker, not proof of recent run. **All four jobs** in the file showed the same `last_run_at = 2026-05-19` cluster.

## Memory contradiction that triggered the checkup

Memory entry dated 2026-06-01:

> "Drewgent cron infra — cron-runner (`ai.drewgent.cron-runner` + `scripts/cron_runner.py`)는 3 board dispatcher만. jobs.json cron expression (SEO/Trend/kanban-maintenance/cron-output-cleanup)은 별도 process (gateway 내부 scheduler?). 두 in-memory state 분리. **jobs.json 신규 entry는 in-memory state에 안 들어감** — patch로 next_run_at set해도 dispatch 안 됨. fix: process restart. plist: StartInterval=60, **KeepAlive 없음** (60초 공백)."

Read literally, this says "5/30 fix 복구됨" and describes the in-memory state quirk as a known limitation with a known workaround (process restart). But there was no follow-through evidence: no record of the restart being performed after 6/1, no `cron-runner.log` mtime indicating recent activity, no `cron/output/*/` files newer than 6/5.

The 6/1 incident doc (`P6-prefrontal/incidents/cron-runner-launchd-detached-20260601.md`) describes the same in-memory state quirk and the recovery branch fix, but does NOT verify the fix stayed working 24h/7d later. That's the gap.

## What actually happened (best reconstruction)

1. **5/30~6/1** — incident, fix applied (recovery branch in `cron/jobs.py`)
2. **6/1~6/4** — scheduler working, cron-runner.log + cron/output/*/ updated
3. **6/4 16:41** — n8n received SIGTERM (source unknown: OOM? manual? logrotate? macOS update? no n8n.error.log entry) and exited cleanly → KeepAlive either not set or set with bare `<true/>` → no restart
4. **6/4~6/6** — gateway/cron-runner process likely also died around the same time (correlated — could be same event, could be independent, hard to tell from logs alone since cron-runner doesn't log per-tick)
5. **6/5~6/6** — last cron sessions visible in `hermes sessions list` (cron_96ad18409db7_20260605_120042 etc.) → some dispatchers were still alive this far
6. **6/6~6/10** — silent. No watchdog. No alerts. Discovery via the user's manual checkup.

## Concrete fix sequence (for the next session that picks up this incident)

1. **Add `KeepAlive: { SuccessfulExit: false, ThrottleInterval: 10 }` to every plist** that has bare `<true/>` or no `KeepAlive` at all. Current candidates:
   - `~/Library/LaunchAgents/ai.drewgent.cron-runner.plist` (no KeepAlive per memory)
   - `~/Library/LaunchAgents/ai.drewgent.n8n.plist` (had `<true/>` per memory — bare form, vulnerable to SIGTERM→exit0 trap)
   - `~/Library/LaunchAgents/com.drewgent.quartz-fswatch.plist`
   - `~/Library/LaunchAgents/com.drewgent.quartz-deploy.plist`
   - `~/Library/LaunchAgents/ai.drewgent.kanban-dashboard.plist`
2. **Register the watchdog cron** in the main SKILL.md — no_agent=True, every 5 min, Discord webhook
3. **Resolve Quartz source path** — `~/humanerd` is gone; need to pick one of `~/Sites/quartz` vs `~/.drewgent/humanerd-site` as canonical, symlink the other, then fix fswatch script to use the symlink
4. **Patch all stale `next_run_at` to `now-5s`** in jobs.json AFTER gateway restart (the in-memory state still won't pick this up — need to restart gateway once after the fix)
5. **Write a 2026-06-10 incident doc** at `P6-prefrontal/incidents/cron-runner-launchd-detached-20260610.md` (or similar) so the 6/1 doc gets a "see also" and the gap is documented
6. **Update memory entry** for the 5/30 cron incident — annotate that the fix was incomplete (in-memory state) and the actual sustained-recovery verification was never performed

## What this incident did NOT find

- No kanban worker stuckness (board had 0 tasks — clean state)
- No P0 brainstem rule violations
- No memory corruption (entries dated 6/1, 6/2, 6/9 all readable)
- No Quartz vault content loss (vault path moved, but content itself presumably intact at the new location)
- No credential leaks (n8n.config encryptionKey not touched)

The damage is purely "automation was offline." No data loss, no security incident.

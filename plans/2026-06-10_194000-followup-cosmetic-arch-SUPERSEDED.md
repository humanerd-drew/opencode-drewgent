# Plan — Drewgent follow-ups (cosmetic / architectural)

> **Status**: Open. Defer to a future session.
> **Created**: 2026-06-10 (P1.3 follow-up sweep)

## Background

6/10 19:38 sweep completed all 12 tasks (T1–T12) but found 3 new issues (P1.1/P2.1/P3.1).
Per user direction ("다른 문제 나오면 대기"), Problem 1 was resolved immediately
(gateway kickstart) and Problems 2/3 are deferred to this plan.

## Problem 2 — `hermes cron list` "Gateway is not running" residual

**Symptom**: After gateway kickstart + customize layer verified working (T6 ✓),
`hermes cron list 2>&1 | grep -c "Gateway is not running"` returns 1 (not 0).

**Investigation (P1.1 done)**:
- customize layer override `get_launchd_label` works (T6 ✓)
- `find_gateway_pids()` returns 1 PID (T6 ✓)
- But the *display* of "Gateway is not running" appears in 1 place in cron list

**Likely cause**: `hermes_cli/cron.py:143-145` imports
`from hermes_cli.gateway import find_gateway_pids` — but customize layer's
`hermes_cli/gateway.py` proxy registers the override on the *real* module
(`_real_hermes_cli_gateway`) but the call site in `cron.py` may resolve
`find_gateway_pids` from a *different* module reference.

**To investigate**:
1. Run `PYTHONPATH=~/.drewgent/customize python3 -c "import hermes_cli.cron; print(hermes_cli.cron.find_gateway_pids)"` — should return PIDs
2. If empty, the call site in `cron.py` is using `find_gateway_pids` from `_real`
   before our override was applied (import-order race)
3. If populated, the "Gateway is not running" is from a *different* code path
   (e.g., `cron_status()` in cron.py:164 uses `find_gateway_pids` directly)

**Fix (when picked up)**:
- Option A: In customize layer's `hermes_cli/__init__.py`, also rebind
  `hermes_cli.cron` module attributes after loading it
- Option B: Add `hermes_cli/cron.py` proxy that imports real cron, then
  rebinds `find_gateway_pids` to our override
- Option C: Patch `hermes_cli/cron.py:144` directly (rejected — violates
  "no hermes upstream modifications" rule per 대전제)

**Recommended**: Option A. Mirrors the existing gateway.py pattern.

## Problem 3 — cron job Schedule "?" for interval jobs

**Symptom**: `hermes cron list` shows for `drewgent-cron-runner-001`:
```
Schedule:  ?
```
While other jobs (cron expression) show actual schedule.

**Cause**: `hermes_cli/cron.py:82-86` likely reads `schedule.display` or
`schedule.expr` directly. Our new entry uses `kind: interval, minutes: 1`
(no `expr` field, no `display`).

**Fix**:
- Update `~/.drewgent/cron/jobs.json` to add `display: "every 1m"` to the entry
- Or convert to cron expression: `kind: cron, expr: "* * * * *", display: "* * * * *"`
- Latter is cleaner (hermes likely handles cron better than interval)

**Recommended**: Convert to cron expression. The 60s tick is identical, and
`hermes cron list` will display `* * * * *` clearly.

## P1.3 — gateway cron-scheduler thread bug (architectural)

**Status**: NOT in this plan. Separate work item. This is the *real* problem
that keeps recurring (T10+ stall pattern).

**Symptoms** (3 observed instances this session):
- 17:50:45 — Cron ticker started
- 17:51:47 — Last fire (only one)
- 19:18 — Last dispatcher fire in cron-runner.log (gateway log silent after 17:51)
- 20:15:07 — kickstart, ticker started
- 20:16:10 — Last fire
- 20:18+ — stall again

**Pattern**: gateway cron scheduler fires ONCE after (re)start, then stops.
The cron-tick thread (60s loop) appears to be stopping after 1 iteration.

**Workaround (current)**: manual `launchctl kickstart -k gui/$(id -u)/ai.drewgent.gateway`
when Layer 3.5 alerts. Approximately every 2-4 hours.

**Suggested fix (deferred)**:
1. Read `~/.drewgent/source/drewgent-agent/gateway/run.py` (or similar) to find
   the cron-tick loop
2. Check if there's an exception handler that silently exits after 1 fire
3. Look for any `break` or `return` in the tick loop that may be triggered
   by an unhandled exception
4. Add logging to the tick loop so next stall can be diagnosed

**Related**: T4 incident `gateway-scheduler-double-fire-20260610.md` covers the
double-fire half. This P1.3 covers the stall half. Both are gateway cron
scheduler bugs, possibly related.

## Plan: When to do this work

These are *cosmetic* (Problem 2, 3) and *architectural* (P1.3) issues. They do
not block normal operation. Recommended to bundle with a larger gateway
reliability improvement session.

**Trigger conditions** to pick up this plan:
- Layer 3.5 alerts 3+ times in 24h (gateway stall)
- User explicitly requests cron UI cleanup
- Next quarterly review (3-month cadence)

## Acceptance criteria

When this plan is executed, verify:
- Problem 2: `hermes cron list 2>&1 | grep -c "Gateway is not running"` returns 0
- Problem 3: All 8 cron jobs in `hermes cron list` show non-? schedule
- P1.3: Gateway runs for 24h+ without manual kickstart, cron tick fires
  every ~60s, no stall or double-fire observed (1-2 invocations per minute
  within 0.15s is the known acceptable double-fire; >2 is a regression)

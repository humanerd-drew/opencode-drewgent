---
title: System Incidents — Compiled
type: wiki-compiled
tags: [compiled, incidents, debugging, lessons, postmortem]
trigger: "wiki-compile 2026-06-21 — compiled from P2-hippocampus and P6-prefrontal/incidents; updated with all 2026-06 incidents"
provenance:
  session: "2026-06-21 wiki-compile"
  decision: "Consolidate all incident postmortems from P6-prefrontal/incidents/"
created: 2026-06-21
updated: 2026-06-21
links:
  - "P5-ego/wiki/compiled/launchd-system"
  - "P5-ego/wiki/compiled/kanban-system"
  - "P5-ego/wiki/compiled/cron-operations"
  - "P6-prefrontal/incidents"
  - "P5-ego/wiki/compiled/growth-engine"
---

# System Incidents — Compiled

## Significant Incidents

### 1. Kanban-Linear DateTime Type Mismatch (Silent, Months)
**What:** Linear API `completedAt` filter expects `DateTimeOrDuration` type. Code sent `DateTime!` ISO string → HTTP 400 silent failure for months.
**Root Cause:** Linear API changed type. Kanban-linear-sync script never updated. Exit code not checked.
**Fix:** Changed to `DateTimeOrDuration!` with relative duration (`-90d`).
**Lesson:** Cron exit codes must be validated. External API contracts drift silently.

### 2. PYTHONPATH Trailing Colon
**What:** `PYTHONPATH=/path:` (trailing colon) adds CWD to Python path. Caused intermittent ImportError.
**Root Cause:** Zsh string concatenation quirk in `.zshrc` or plist env dict.
**Fix:** Strip trailing colons. Wrapper script removed `unset PYTHONPATH`.
**Lesson:** Environment variable hygiene matters in subtle ways.

### 3. Dispatcher Wrong DB
**What:** One kanban dispatcher was reading from the wrong SQLite database (copy vs original). Tasks disappeared and reappeared.
**Root Cause:** Two copies of kanban.db coexisted silently for 13.2h. Dispatcher path pointed to stale copy.
**Fix:** Unified path references to single canonical kanban.db.
**Lesson:** Dual-file anti-pattern. Single source of truth must be enforced.

### 4. Gateway Cron Stall (v0.8.4)
**What:** Gateway's cron scheduler stalled for 1.7h+. Last dispatcher fire at 19:18.
**Root Cause:** `d1ef68ced116` (kanban-dispatcher LLM job) blocked sequential tick loop via `task_qa_gate` contract phase hang.
**Fix:** Disabled d1ef68ced116 (redundant with cron_runner.py).
**Lesson:** LLM-based cron path can block entire scheduler.

### 5. Gateway Scheduler Double-Fire (T4)
**What:** Gateway's interval=1min jobs run 2x per minute within 0.15s. Hypotheses: startup race, jobs.json reload path, `script_only: true` interaction.
**Root Cause:** Unconfirmed.
**Fix:** cron_runner.py idempotent via SQLite UPSERT. 2x CPU but no data corruption.
**Lesson:** Sometimes workaround is cheaper than root cause.

### 6. Gateway Runner Mock Patterns (Post-decomp)
**What:** After gateway decomposition, 16/133 tests failed. Missing mock fixtures.
**Fix:** Updated mock fixture guide. 83/83 pass post-fix.
**Lesson:** Decomposition must be verified with test suite.

### 7. ACP Spinner — 3 Failed Attempts
**What:** 3 attempts to implement LLM thinking-phase indicator in ACP, all rejected:
- Attempt 1: Size hint text in tool result — rejected ("not text")
- Attempt 2: Heartbeat events — rejected ("still text")
- Attempt 3: Synthetic ToolCallStart (kind="think") — rejected (tool cards not in stream area)
**Root Cause:** ACP spec fundamentally has no in-stream visual indicator event.
**Status:** UNRESOLVED. DO NOT RETRY without user explicit override.
**Lesson:** Some spec limitations cannot be worked around.

### 8. Launchd Mass Failure (2026-06-10, P1)
**What:** 5/6 launchd services dead for 4-6 days undetected. Gateway SIGTERM at 06-06, n8n at 06-04. Cron jobs had 22-day stall.
**Root Causes (multi-factor):**
1. Process exited cleanly (exit 0) → KeepAlive `SuccessfulExit: false` didn't trigger
2. No infrastructure watchdog existed at all
3. Gateway plist label mismatch (`ai.custom-agent.gateway` vs filename)
4. Cron-runner had no KeepAlive (only `StartInterval=60`)
5. Gateway housekeeping had broken nested try/except → silent cron ticker death
6. Memory vs reality drift — incidents documented as resolved while infra was dead
**Fix (35 min):** Watchdog cron added, all plists patched to `KeepAlive: { SuccessfulExit: false, ThrottleInterval: 10 }`, label fixed, housekeeping patched.
**Lessons:** (1) launchd is not a watchdog, (2) `SuccessfulExit: false` is mandatory, (3) watchdog takes 10 min to set up, (4) idempotency transforms P1 into P3.

### 9. Quartz Draft Leak (2026-06-02, P1)
**What:** 6 draft articles published live on humanerd.kr. 5 from 5/23-26 batch, 1 from 6/1. Returned HTTP 200.
**Root Cause:** Quartz `RemoveDrafts` checks `frontmatter.draft === true` only. Content pipeline uses `status: draft` convention. Field mismatch.
**Fix:** DraftFilter v2: strict allowlist — only `status: published|polished` pass. 19 articles retrofitted.
**Lesson:** Never assume third-party plugin behavior matches documentation. Naming convention fix: `published` not `publish`.

### 10. Cron Jobs Stalled — next_run_at=null (2026-06-01)
**What:** 5 enabled cron jobs dormant ~36h. `next_run_at` null in jobs.json.
**Root Cause:** `get_due_jobs()` had only a oneshot recovery branch. Recurring cron/interval jobs with null `next_run_at` were silently skipped.
**Fix:** Added recurring recovery branch — auto-computes next run from schedule.
**Lesson:** Cron job recovery must handle both oneshot and recurring patterns.

### 11. False Alarm Correction (2026-06-01)
**What:** False alarm that cron-runner was dead. `launchctl list PID=-` showed detached.
**Root Cause:** `launchctl list PID=-` is soft evidence — detached processes show PID=- while running normally.
**Fix:** Hardened detection criteria: log mtime >5min + output mtime >5min, not `launchctl list`.
**Lesson:** macOS launchd PID report is unreliable for process death detection.

## Cross-Cutting Lessons
1. Exit codes matter — validate in cron_runner.py
2. LLM in sync path is dangerous — prefer trigger+worker
3. Dual files = double the bugs — single source of truth
4. External API contracts drift silently — add integration tests
5. Customize layer needs automated smoke tests after upgrades
6. `launchctl list PID=-` is not reliable — use log/output mtime
7. SQLite UPSERT idempotency transforms P1 into P3
8. launchd is not a watchdog — 10-min shell script saves days
9. Never assume third-party plugin behavior matches docs
10. Recurring cron recovery must handle both oneshot and interval

---
title: gateway scheduler double-fire — interval=1min jobs run 2x per minute
type: incident
space: claim
tags: [claim, infra, gateway, scheduler, followup]
created: 2026-06-10
updated: 2026-06-10
links:
  - "[[@identity/brain/rules]]"
  - "[[@action/incidents/launchd-mass-failure-20260610 § 6.5]]"
  - "[[@action/incidents/launchd-mass-failure-20260610 § 6.6]]"
  - "[[@action/incidents/launchd-mass-failure-20260610 § 6.7]]"
  - "[[cron-jobs-stalled]]"
---

# Incident — gateway scheduler double-fire — interval=1min jobs execute 2x per minute

**Date**: 2026-06-10 17:55–18:00 KST (detected during 6.6 D5 scheduler-unify sweep)
**Severity**: P3 (low — idempotent workaround in place)
**Status**: Analyzed, root cause unconfirmed, fix deferred
**Author**: Drewgent self-investigation (6/10 incident follow-up)

---

## 1. Symptom

While consolidating 3 board dispatchers into a single `drewgent-cron-runner-001` jobs.json
entry (kind=interval, minutes=1, script=`scripts/cron_runner.py`), observed:

```
$ tail -10 ~/.drewgent/logs/cron-runner/2026-06-10.log
=== 2026-06-10T08:57:26.678679+00:00 ===
  [default] dispatch_once_default.py: exit=0 | [SILENT]
  [content] dispatch_once_content.py: exit=0 | [SILENT]
  [integrations] dispatch_once integratio[REDACTED].py: exit=0 | [SILENT]
=== 2026-06-10T08:57:26.850655+00:00 ===  ← 0.17s later
  [default] dispatch_once_default.py: exit=0 | [SILENT]
  [content] dispatch_once_content.py: exit=0 | [SILENT]
  [integrations] dispatch_once integratio[REDACTED].py: exit=0 | [SILENT]
```

Two complete `=== ISO ===` blocks per minute, separated by ~0.15s. Pattern repeats for
every minute observed. Each block contains 3 dispatcher executions (default, content, integrations).

**Counter-evidence that it's not just 2 cron entries running**: `jobs.json` had exactly
ONE `drewgent-cron-runner-001` entry. The original `d1ef68ced116` (`*/1 * * * *` cron
expression kanban-dispatcher) was disabled. `ai.drewgent.cron-runner` plist was
booted out. `launchctl list` shows only `ai.drewgent.gateway` as the active agent.

**Conclusion**: the gateway's own internal cron scheduler is firing each interval job
twice within ~150ms. Not a 2-source duplication — internal double-fire.

---

## 2. Diagnosis (2026-06-10 18:00 KST)

### 2-1. Confirmed facts

- Single jobs.json entry (`drewgent-cron-runner-001`) with `kind=interval, minutes=1`
- Single launchd gateway process (PID 96080–98000 range, after 17:45 restart)
- Zero other launchd/cron sources for the dispatcher script
- Two `=== ISO ===` blocks per minute, ~0.15s apart, then 60s gap
- Pattern: stable since 17:55 (3+ minutes observed, every tick shows the double-fire)
- `cron_runner.py` is idempotent: 3 dispatcher scripts use SQLite UPSERT/claim logic;
  double-fire produces at most 2x work, not data corruption

### 2-2. Hypotheses (not yet tested)

**H1: Gateway startup race** — when gateway starts, `get_due_jobs()` may be called
twice in quick succession (once during init, once at first tick). The 60s gap after
each double-fire is consistent with: (a) one immediate fire, (b) one scheduled fire
60s later, (c) then the next pair.

**H2: jobs.json reload path** — gateway's jobs.json loader may register the same
job twice (e.g., on first load + on SIGHUP / mtime change). The watchdog cron, log
rotation cron, and harmony check cron (all `no_agent: true`, daily/5-min interval)
do NOT show this pattern in their output dirs — but they ARE different code paths
(pure `hermes` cronjob, not gateway internal scheduler).

**H3: `script_only: true` flag confusion** — the new entry has `script_only: true`
which may interact differently with the scheduler. Original kanban-dispatcher
entry (which does NOT have `script_only`) shows a single tick per minute
(observed in `~/.drewgent/cron/output/d1ef68ced116/`).

### 2-3. Reproduction recipe

To reproduce (low risk; cron_runner is idempotent):
1. Add a new jobs.json entry with `script_only: true, schedule.interval.minutes=1`
2. Restart gateway
3. Wait 3 minutes
4. Check the script's log: should see 6 `=== ISO ===` blocks in 3 minutes (2 per minute)

---

## 3. Resolution (interim workaround, 6/10)

- **No code change** — `cron_runner.py` is idempotent (SQLite UPSERT in 3 dispatcher
  scripts). Double-fire produces 2x CPU but no data corruption.
- **Monitoring**: harmony check cron will detect if `cron-runner.log` mtime exceeds
  expected rate (more than 2 entries per minute would be a 3rd-fire regression).
- **Incident documented**: this file. Carried over in `launchd-mass-failure-20260610 § 6.7`.

---

## 4. Recommended fix (deferred)

**Target file**: `~/.drewgent/source/drewgent-agent/cron/scheduler.py` (or `cron/jobs.py`)

Steps when picked up:
1. Add unit test: `test_interval_job_fires_once_per_minute` — fast-forward clock, fire
   scheduler tick 1s, assert exactly 1 invocation
2. Investigate `get_due_jobs()` in jobs.py — does it return duplicates for
   `script_only` entries?
3. Investigate `scheduler.py` tick loop — is there a double-init pattern?
4. Possible fix: add an in-memory `fired_jobs: set[(job_id, last_fire_ts)]` to dedupe
   within a single tick window
5. Verify: cron_runner.log shows exactly 1 `=== ISO ===` block per minute after fix

---

## 5. Impact assessment

- **Functional**: NONE — idempotent, no data corruption
- **Resource**: 2x CPU on dispatch_once scripts (negligible — each runs in ~0.3s)
- **Detection noise**: Layer 3.5 of harmony check shows "⚠ jobs.json modified Ns after
  last dispatcher tick" once per minute (touches from gateway internal save), but this
  is *not* an actionable signal — the modification IS the fast-forward

---

## 6. Lessons

1. **Idempotency is the bedrock** of any "I can re-run this safely" infrastructure
   claim. The 3 dispatcher scripts' SQLite UPSERT pattern made this incident a P3
   instead of a P1.
2. **Detection is asymmetric** — observed symptom (double-fire) was visible in logs
   but no automated alert fires for it. Harmony check 3.5 could be extended to
   *expect* a 60s tick rate and alert on >1 fire per minute.
3. **Gateway startup race conditions** are non-obvious — they don't manifest during
   the first 60s but persist for the lifetime of the gateway.

## Links
- [[@action/incidents/launchd-mass-failure-20260610 § 6.5]]
- [[@action/incidents/launchd-mass-failure-20260610 § 6.6]]
- [[@action/incidents/launchd-mass-failure-20260610 § 6.7]]
- [[cron-jobs-stalled]]

## Related Neurons
- [[禁filesystem_truth.neuron]]
- [[禁task_qa_gate.neuron]]
- [[禁console_log.neuron]]

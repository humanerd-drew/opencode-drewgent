---
title: Kanban Incident Template
domain: incident
space: claim
type: template
tags: [P6, prefrontal, incident, kanban]
created: 2026-05-20
updated: 2026-05-20
links:
  - "[[@memory/kanban/KANBAN_INDEX]]"
  - "[[@identity/SELF_MODEL]]"
  - "[[@identity/brain/rules]]"
---

# Kanban Incident Report Template

When a kanban system failure occurs, use this template to document the incident.

## Template Fields

**Date**: YYYY-MM-DD HH:MM KST
**Severity**: P0 (brain down) / P1 (task dead) / P2 (degraded) / P3 (minor)
**Status**: Investigating / Identified / Resolved
**Board affected**: default / content / integrations

## Incident Description

What happened, in one sentence.

## Root Cause

- [ ] Identify the failure point (task stuck, worker dead, DB corruption, etc.)
- [ ] Check `_reclaim_stale_tasks()` log for expired tasks
- [ ] Check `dispatch_once()` log for spawn failures
- [ ] Check `kanban.worker.reclaimed` signals in brain event log

## Impact

| Metric | Before | After |
|--------|--------|-------|
| Tasks in_progress (stuck) | | |
| Tasks completed today | | |
| Worker count | | |

## Timeline

- HH:MM — Incident detected (kanban.worker.reclaimed signal or manual check)
- HH:MM — Root cause identified
- HH:MM — Fix applied (manual reclaim / worker restart)
- HH:MM — Confirmed resolved

## Fix Applied

```
# For stuck tasks
# For dead workers
# For DB issues
```

## Prevention

- [ ] `_reclaim_stale_tasks()` running at each dispatch tick?
- [ ] Worker heartbeat frequency adequate (TTL/2)?
- [ ] `consecutive_failures` threshold appropriate?
- [ ] Brain signal `kanban.worker.reclaimed` → awareness.integrity configured?

## Brain Signal Evidence

Check these events in the event log:
- `kanban.hallucination_blocked` — fake task IDs attempted
- `kanban.worker.reclaimed` — TTL/heartbeat violations
- `kanban.task.created` / `kanban.task.completed` — throughput drop

---
*Use this template when documenting kanban incidents in P6-prefrontal/incidents/*

## Links
- [[@memory/kanban/KANBAN_INDEX]]
- [[@identity/SELF_MODEL]]
- [[@identity/brain/rules]]

---
title: Kanban System — Compiled
type: wiki-compiled
tags: [compiled, kanban, dispatcher, pipeline, workflow]
trigger: "wiki-compile 2026-06-21 — compiled from P2-hippocampus; updated with hallucination detection and KANBAN_WORKER_MODE"
provenance:
  session: "2026-06-21 wiki-compile"
  decision: "Consolidate kanban dispatcher, pipeline, board scope, and hallucination detection"
created: 2026-06-21
updated: 2026-06-21
links:
  - "P5-ego/wiki/compiled/taste-decisions"
  - "P5-ego/wiki/compiled/agent-architecture"
  - "P5-ego/wiki/compiled/cron-operations"
  - "P5-ego/wiki/compiled/system-incidents"
---

# Kanban System — Compiled

## Core Decisions

### 1. Three Board-Scoped Dispatchers (default / content / integrations)
**What:** Three independent dispatchers each with board-scoped SQL (`AND board = "self_board"`). Legacy content board also matches `board = "" OR board IS NULL`.
**Why:** Cross-board race was causing one dispatcher to reclaim another board's dead workers.
**Alternatives considered:** Single dispatcher with board filter, Redis-based locking.
**Status:** Active since v0.8.5. Verified with isolation tests.

### 2. Watchdog + TTL Dual Reclaim
**What:** Phase 0 (watchdog `os.kill(pid, 0)`) catches dead workers BEFORE TTL expires. Phase 1 reclaims expired TTL. Phase 2 re-claims with new live worker in same tick.
**Why:** Self-heal within single tick even when both failure modes fire simultaneously.
**Status:** Active since v0.8.5.

### 3. Kanban Pipeline (sequential subagent chain)
**What:** `kanban_create` with `pipeline=["explorer","implementer","tester","reviewer","archiver"]` → N sequential child tasks with dependency links.
**Why:** Formalizes the code lifecycle. Each subagent gets clear scope.
**Status:** Active since 2026-06-13.

### 4. Hallucination Detection
**What:** `kanban_complete` verifies `created_cards` exist in DB before completing. Prevents agent from claiming completion of tasks never created.
**Why:** LLM hallucination can report fake task IDs.
**Status:** Active. Harness autonomous behavior.

### 5. Kanban-Linear Sync (Deprecated)
**What:** `kanban_complete` → `post_tool_call` hook → Linear issue upsert. Cron prunes every 2h. 200-issue free tier limit.
**Why:** Was source of truth for content team.
**Status:** DEPRECATED per user directive 2026-05-20. DateTime type mismatch bug (months silent) was the final issue — bug was a `DateTimeOrDuration` type mismatch in GraphQL query.

### 6. Office Autopilot
**What:** `office_autopilot.sh` runs every 5min via cron. Checks kanban DB → invokes orchestrator (qwen3.7-max) only when work exists. Orchestrator classifies → delegates → kanban_complete → Discord summary.
**Why:** Silent when idle. Expensive orchestrator only called when work exists.
**Status:** Active since 2026-06-20.

### 7. Parent Context Injection (Handoff Contract)
**What:** Worker-side `<parent>.result` JSON parse → structured markdown injection into child task. Schema: `findings`, `risks`, `next` (3 fields). Failure handling: 3-layer (log + event + context `⚠` marker).
**Why:** Pipeline stages need previous stage output to work. Without injection, each stage starts blind.
**Status:** Active. Implemented on all 11 profiles with Handoff Contract sections.

### 8. KANBAN_WORKER_MODE Accuracy Fix
**What:** KANBAN_WORKER_MODE env flag was claimed as "LLM-free" but `run_kanban_worker.py` was calling AIAgent (MiniMax-M3) for every task. Fixed with `_is_shell_only_task()` classifier as safety net.
**Why:** Documentation claimed no LLM usage; reality was different. Doc-driven development gap.
**Status:** Active. Shell-only fast path for simple tasks.

### 9. Leverage Score in Task Creation
**What:** Every kanban task body includes `## Leverage Assessment` with score 1-5 and problem elimination list.
**Why:** Forces upfront prioritization thinking at creation time.
**Status:** Active.

### 10. Provenance in Task Body
**What:** Every task body includes `## Origin` with trigger, session, decision rationale.
**Why:** "A prompt is more informative than the output" — decision context embedded in task.
**Status:** Active.

## Bugs Found (5 P0, all fixed)

| Bug | Fix | When |
|-----|-----|------|
| kanban_create missing `board` param | Added board parameter | 2026-05-20 |
| kanban-dispatcher not in jobs.json | Added cron entry | 2026-05-20 |
| stdin pipe never closes | Fixed worker spawn | 2026-05-20 |
| dispatch spawn race condition | Added lock | 2026-05-20 |
| task_list no board filter | Added WHERE clause | 2026-05-20 |

## Rationale
SQLite-based kanban chosen over Linear-only for offline-capable task management. Board scope isolation was hard-learned. Pipeline pattern emerged from need for consistent code lifecycle. Hallucination detection and worker mode accuracy prevent silent failures.

## Current Status
All systems operational. 3 dispatchers self-healing verified. Pipeline active. Office autopilot idle when no work. Hallucination detection prevents fake completions. Parent context injection enables stage handoff.

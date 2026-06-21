---
title: Cron Operations — Compiled
type: wiki-compiled
tags: [compiled, cron, operations, scheduling, jobs]
trigger: "wiki-compile 2026-06-21 — compiled from P2-hippocampus; updated with stalled jobs incident and script-fastpath"
provenance:
  session: "2026-06-21 wiki-compile"
  decision: "Cron infrastructure decisions consolidated from MEMORY_wiki.md and incidents"
created: 2026-06-21
updated: 2026-06-21
links:
  - "P5-ego/wiki/compiled/launchd-system"
  - "P5-ego/wiki/compiled/kanban-system"
  - "P5-ego/wiki/compiled/content-pipeline"
  - "P5-ego/wiki/compiled/system-incidents"
  - "P5-ego/wiki/compiled/discord-infrastructure"
---

# Cron Operations — Compiled

## Core Decisions

### 1. Unified Cron Dispatcher (drewgent-cron-runner-001)
**What:** Single `jobs.json` entry running `scripts/cron_runner.py` every 60s. Replaced 3 separate board dispatchers and gateway internal scheduler.
**Why:** 3 board dispatchers + gateway internal scheduler caused dual in-memory state drift. Unified entry eliminates sync issues.
**Alternatives considered:** Keep 3 separate plists, use system cron (macOS cron daemon).
**Status:** Active as of 2026-06-10.

### 2. Idempotent Cron_runner.py
**What:** All cron operations use SQLite UPSERT for idempotency. Double-fire (2 fires/min 0.15s apart) is benign.
**Why:** Gateway scheduler has a known double-fire race. SQLite UPSERT transforms potential P1 into P3.
**Alternatives considered:** Fix gateway scheduler race (root cause unconfirmed), add mutex/lock.
**Status:** Active. Double-fire root cause not fixed but benign.

### 3. jobs.json on-disk vs in-memory gap
**What:** Patching `next_run_at` on disk does NOT affect in-memory state — gateway restart required for new entries.
**Why:** Gateway scheduler loads jobs.json at startup only.
**Alternatives considered:** Hot-reload mechanism, SIGHUP handler.
**Status:** Known limitation. Established entries run fine.

### 4. Watchdog Chain (3-tier no-LLM crons)
**What:** Three no-LLM cron jobs form safety net:
- Watchdog (5min) — launchd health poll, Discord alert on failure
- Harmony check (09:00 daily) — 4-layer cross-diff (launchd/ps/jobs.json/memory)
- Log rotation (04:00 daily) — 100MB/7d threshold, .gz + truncate, 30d retention
**Why:** LLM-dependent monitoring risks blind spots when LLM is down.
**Status:** Active.

### 5. Trigger + Kanban-Worker Pattern
**What:** All LLM-bearing cron jobs split into shell trigger (0 LLM) + kanban worker (full reasoning).
**Why:** 600s timeout insufficient for monolithic LLM jobs. 279 Trend Harvester keep items sat unapplied.
**Status:** Active. See [[P5-ego/wiki/compiled/taste-decisions]].

### 6. Script Fastpath (No-LLM Execution)
**What:** Jobs with `script` field in jobs.json bypass LLM entirely — `subprocess.run()` via `_run_script_subprocess()`. Returns same `(success, output, final_response, error)` tuple.
**Why:** Simple shell jobs ("Run: python3 xxx.py") waste LLM round-trip. Script path is faster and more reliable.
**Caveats:**
- PATH not inherited from user shell — must explicitly set for Homebrew tools
- `.sh` → bash; everything else → `sys.executable` (Python). Node.js scripts need `.sh` wrapper.
**Status:** Active.

### 7. Cron Job Schedules (Complete Table)
**What:** 14+ jobs managed via `cron/jobs.json`:
| Interval | Jobs |
|----------|------|
| 2 min | trend-evaluate |
| 5 min | launchd watchdog, dashboard push |
| 15 min | gbrain watchdog |
| 6 hours | trend-collect, seo-harvester |
| Daily 04:00 | log rotation, wiki-lint |
| Daily 06:00 | usage-watch |
| Daily 09:00 | harmony-check |
| Daily 12:00 | seo-analyze |
| Daily 20:00 | daily-retro |
| Weekly Sun 03:00 | wiki-compile |
| Weekly Sun 10:00 | trend-retire |
| Weekly Sun 14:00 | seo-trend report |
| Tue/Fri 10:00 | taste-review |
**Status:** Active. All entries in jobs.json with unique hex IDs.

## Rationale
Cron infrastructure evolved from n8n → Hermes internal scheduler → launchd cron. Each iteration removed a layer. Current state: 1 plist, 1 cron_runner.py, unified jobs.json with 14+ jobs, script fastpath for no-LLM execution.

## Current Status
All cron jobs operational. Double-fire race benign. Watchdog chain provides safety net. Script fastpath active for simple jobs. Stalled job recovery branch prevents dead jobs.

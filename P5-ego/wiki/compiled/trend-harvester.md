---
title: Trend Harvester Pipeline — Compiled
type: wiki-compiled
tags: [compiled, trends, pipeline, scoring, taste-review]
trigger: "wiki-compile 2026-06-21 — compiled from P3-sensors skills and P4-cortex growth records"
provenance:
  session: "2026-06-21 wiki-compile"
  decision: "Document collection→scoring→keep→apply→retire pipeline"
created: 2026-06-21
updated: 2026-06-21
links:
  - "P5-ego/wiki/compiled/taste-decisions"
  - "P5-ego/wiki/compiled/cron-operations"
  - "P5-ego/wiki/compiled/growth-engine"
---

# Trend Harvester Pipeline — Compiled

## Core Decisions

### 1. 5-Axis Philosophy Filter Scoring
**What:** Each trend is scored on 5 axes: Relevance, Direct Impact, Actionability, Novelty, Credibility. Threshold: score ≥ 6.0 → `keep`.
**Why:** Systematic quality gate prevents noise. Multi-axis prevents single-dimension bias.
**Alternatives considered:** Manual curation, single-score rating.
**Status:** Active. Philosophy axes defined in `trend-harvester/philosophy_axes.json`.

### 2. Full Pipeline: Collect → Evaluate → Keep → Apply → Retire
**What:** 5-stage lifecycle:
1. Collect: Cron trigger gathers GitHub trending repos + RSS feeds
2. Evaluate: LLM agent scores each item on 5 axes
3. Analyze: ≥6.0 items go to `analyzed/keep/` for human review
4. Apply: Selected items integrated into Drewgent (skills, config, tools)
5. Retire: Aged items moved to `graveyard/`
**Why:** Pipeline prevents the "one-way flow" problem (279 keep items, 0 applied).
**Alternatives considered:** Ad-hoc evaluation, no retirement.
**Status:** Active. State directories: `collected/`, `evaluated/`, `analyzed/`, `applied/`, `graveyard/`, `pending/`.

### 3. Trigger + Kanban-Worker Pattern
**What:** LLM-heavy pipeline steps run as kanban workers, not direct cron jobs. Cron trigger is a 0-LLM fast script.
**Why:** 600s cron timeout was insufficient for LLM evaluation. Trigger+worker gives each step its own timeout budget.
**Status:** Active. Applied after pipeline redesign 2026-06-14.

### 4. Taste Review (bi-weekly extraction)
**What:** Every Tuesday/Friday 10:00 KST, deeply analyze 1 quality tool from keep list. 5-question framework: one-liner, stolen taste decisions, architecture insight, Drewgent applicability, leverage score (1-5).
**Why:** 279 kept items were never applied. Taste review forces deep analysis and extraction of actionable decisions.
**Status:** Active. Results stored in `P4-cortex/taste-reviews/`. Cron job ID: `29ccd2c5d019`.

### 5. Pipeline Redesign Trigger (2026-06-14)
**What:** Taste review introduced because 279 keep items existed in `analyzed/keep/` with 0 in `applied/`. The pipeline was one-way: collection worked, application didn't.
**Why:** Pipeline redesign from monolithic cron to trigger+kanban-worker enabled granular application steps.
**Status:** Resolved. Keep→applied pipeline now functional.

### 6. Scheduler Cadence
**What:**
- Trend-collect: every 6 hours
- Trend-evaluate: every 2 minutes (after new collection)
- Trend-retire: monthly 10:00
- Taste review: Tuesday/Friday 10:00
**Status:** Active. Defined in `cron/jobs.json`.

## Rationale
Systematic pipeline prevents noise accumulation and ensures trends are actually applied, not just collected. 5-axis scoring provides objective filtering. Taste review extracts maximum value from each quality item.

## Current Status
Pipeline operational. 279 legacy keep items in analyze phase. Taste review runs bi-weekly. Apply/retire lifecycle functional. Pipeline redesign resolved the one-way flow problem.

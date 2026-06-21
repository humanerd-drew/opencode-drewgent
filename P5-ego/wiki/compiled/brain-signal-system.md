---
title: Brain Signal System & GBrain — Compiled
type: wiki-compiled
tags: [compiled, gbrain, brain-signals, memory, facts]
trigger: "wiki-compile 2026-06-21 — compiled from P3-sensors skills and P4-cortex knowledge"
provenance:
  session: "2026-06-21 wiki-compile"
  decision: "Consolidate gbrain MCP tools, signal processing, fact extraction, and memory hierarchy"
created: 2026-06-21
updated: 2026-06-21
links:
  - "P5-ego/wiki/compiled/memory-knowledge"
  - "P5-ego/wiki/compiled/agent-architecture"
  - "P3-sensors/skills/agent-architecture/brain-signal-system"
---

# Brain Signal System & GBrain — Compiled

## Core Decisions

### 1. GBrain 3-Pillar Knowledge Architecture
**What:** Three-pillar approach: (1) Git-versioned wikilinked vault = ground truth, (2) Compiled procedures in P5-ego/wiki/compiled/ = query target, (3) Graph traversal via `drewgent_graph_lookup.sh` + gap analysis via `drewgent_graph_gap_analysis.sh`.
**Why:** Structured knowledge without external DB dependency. Vault is always source of truth; compiled pages are agent-facing summaries.
**Alternatives considered:** Full GBrain server, Notion, Roam, vector DB only.
**Status:** Active. Scripts at `~/.hermes/scripts/`. Complemented by gbrain MCP server (89 tools).

### 2. Gbrain MCP Server Integration
**What:** gbrain runs as PGLite + Ollama local backend. 89 MCP tools available: search, query, backlinks, traverse_graph, get_page, find_orphans, get_stats, etc.
**Why:** Hybrid search (vector + keyword + multi-query expansion) over the entire vault. Local-only (no API costs).
**Key constraint:** `embedding_disabled: true` because Ollama's OpenAI-compatible endpoint is rejected by OpenAI client key validation. Requires Ollama restart + config toggle to re-enable.
**Status:** Active. Embedding recovery was needed 2026-06-16 (brain score 13/100 → 45/100).

### 3. Brain Signal Processing (P0 Priority)
**What:** Event bus + signal processor + awareness reporter + brain monitor. 8 automatic behaviors:
- QA gate contract placeholder detection → blocks delivery (P0)
- Violation summary injection into system prompt (top-3 violations, self-aware)
- Cross-session learning via `violation_memory.json` → agent self-corrects
- Dangerous ops (severity=high) → BLOCK_AND_CONFIRM
- Workflow prediction from completed patterns
- Violation pattern persistence across sessions
**Why:** Self-healing agent behavior. Agent sees "console.log=3x past 5 sessions" and self-corrects without human intervention.
**Status:** Active. Violation memory at `P2-hippocampus/memories/violation_memory.json`.

### 4. Fact Extraction System (Hot Memory)
**What:** Extracts personal-knowledge facts (events, preferences, commitments, beliefs) from conversation turns into per-source hot memory. Uses Haiku for extraction, cosine fast-path + classifier dedup pipeline.
**Why:** Structured facts survive session boundaries. Powers recall, trajectory analysis, and entity tracking.
**Key features:**
- `gbrain recall` — query facts by entity, session, date range
- `gbrain forget_fact` — strike through fact with reason
- `gbrain find_trajectory` — time-series view of entity metrics
- `gbrain takes_list` / `takes_scorecard` — calibration tracking
**Status:** Active since v0.31. Visibility filtering (private/world) for remote callers.

### 5. Takes System (Calibrated Judgments)
**What:** Typed/weighted/attributed claims system: fact / take / bet / hunch. Calibration profiles track Brier score and accuracy per holder.
**Why:** Quantified judgment enables self-calibration. The brain tracks how often its predictions are right and adjusts confidence.
**Status:** Active. Scorecard available via `gbrain takes_scorecard --holder garry`.

### 6. Dream System
**What:** Persistent value observations saved to `~/.drewgent/dreams/` and injected into future session prompts. `emit_dream_candidate()` → `signal_processor._on_dream_candidate()` → writes `YYYYMMDD_<slug>.md` → prompt_builder loads at session start.
**Why:** Cross-session insight persistence. "Dreams" surface in future sessions as ambient context.
**Alternatives considered:** In-memory only (lost on session end), MEMORY.md only (too coarse).
**Status:** Phase 1 infrastructure complete.

### 7. Knowledge Bus (Singleton)
**What:** `bus.py` singleton knowledge store connecting NeuronFS, VerificationEngine, GrowthEngine, RevisionLoop. JSON persistence at `drewgent_knowledge.json` (1,778 lines).
**Why:** Central knowledge bus prevents 4 modules from each managing their own state.
**Status:** Active. Contains verification failures, test data, revision results.

## Rationale
GBrain 3-pillar + MCP tools provide comprehensive knowledge management without external services. Signal system ensures agent self-awareness and self-correction. Takes system brings quantified calibration to agent judgment.

## Current Status
All systems active. Embedding recovery resolved (2026-06-16). Takes system operational. Dream system in Phase 1. Brain signal system processes 8 automatic behaviors.

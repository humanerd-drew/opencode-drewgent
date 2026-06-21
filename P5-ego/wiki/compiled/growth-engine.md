---
title: Growth Engine & P4-Cortex — Compiled
type: wiki-compiled
tags: [compiled, growth, improvements, learning, cortex]
trigger: "wiki-compile 2026-06-21 — compiled from P4-cortex/growth and knowledge"
provenance:
  session: "2026-06-21 wiki-compile"
  decision: "Consolidate growth records, improvements, and knowledge artifacts"
created: 2026-06-21
updated: 2026-06-21
links:
  - "P5-ego/wiki/compiled/taste-decisions"
  - "P5-ego/wiki/compiled/skill-system"
  - "P5-ego/wiki/compiled/brain-signal-system"
  - "P5-ego/wiki/compiled/trend-harvester"
---

# Growth Engine & P4-Cortex — Compiled

## Core Decisions

### 1. Context Compression Improvements (v0.7 → v0.9)
**What:** Compression threshold raised from 0.5 → 0.9 (compress at 90% capacity). 4-step aggressive pruning: acknowledgment removal, duplicate dedup, old tool result → placeholder, error trace truncation. Last Exchange section preserved verbatim.
**Why:** M3 1M context provides 5x headroom. Premature compression was destroying useful context.
**Important lesson:** Doc written 2026-05-21 but config NOT patched until 2026-06-01. Doc-driven development gap identified.
**Status:** Active since 2026-06-01.

### 2. Token Compression Headroom (4-Layer) with 40/60 Split
**What:** 4 tool layers with standardized output truncation:
- Layer 1: `terminal` `tail_lines` — long stdout capped
- Layer 2: `read_file` `max_chars 20,000` — 80% savings
- Layer 3: `kanban_list` `include_body=false` + `body_chars` — 78% savings
- Layer 4: `kanban_get` `body_chars 5,000` — 59% savings
**Why 40/60 split:** Head contains schema/metadata, tail contains last error/result (critical for next action), middle rows are skippable.
**Status:** Active. `headroom_ai` library NOT installed (POC showed 0% gain on plain text/code).

### 3. Harness Autonomous Behaviors (8 automatic actions)
**What:** 8 behaviors that run without agent request:
1. Cron tick → `dispatch_once()`
2. TTL expiry → `_reclaim_stale_tasks()`
3. kanban_complete → hallucination check
4. task_link → DFS cycle detection
5. Integration workflow start → auto task creation
6. Cron failure → retry → fallback delivery
7. Turn end → dangerous ops detection
8. Kanban task events → brain signal awareness
**Boundary:** Harness cannot decide to use kanban, integrate new skills, pass QA gate, create/delete cron jobs.
**Status:** Active.

### 4. No Silent Failure Principle
**What:** 3-phase cron flow: Phase 1 (primary, timeout), Phase 2 (1 retry), Phase 3 (always deliver — even partial status).
**Why:** Silent failures caused hidden outages (incidents 2026-06-01, 2026-06-10).
**Status:** Active. Applied to Trend Harvester, SEO Article Harvester.

### 5. Integration Protocol (3-File Rule)
**What:** Any new tool/skill requires 3 files: tool code, schema registration, toolset registration. Gadfly rule: cross-reference with existing files before adding.
**Why:** Prevents orphan tools and ensures proper registration.
**Status:** Active. P0 rule `禁tool_integration_3file`.

### 6. Obsidian Skills Integration
**What:** Integrated from kepano/obsidian-skills (MIT, 32.6k stars): `obsidian-markdown` (OFM syntax) + `obsidian-cli` (vault CLI ops).
**Not imported:** obsidian-bases (Drewgent kanban equivalent), defuddle (URL handled), json-canvas (low relevance).
**Status:** Active. 4 complementary skills: basics + markdown + CLI + harvester-sync.

### 7. Terminal Context Isolation
**What:** `drewgent acp --stdio` → independent Python processes per terminal. Default ACP STDIO mode.
**Why:** Same API key across terminals caused context cross-contamination.
**Status:** Active since 2026-05-27.

### 8. Discord Token Resilience Protocol (3-layer)
**What:** 3-layer defense against Discord gateway rate-limit → token reset → crash-loop:
1. Discord adapter: 401/LoginFailure → `retryable=False`
2. Gateway: all platforms fail → keep running (cron continues)
3. Startup failure → exit code 0 (launchd doesn't restart)
**Status:** Active since 2026-05-23.

### 9. Garry Tan Concepts Applied
**What:** Key Garry Tan framework concepts adopted:
- **Thin Harness, Fat Skills:** Drewgent's 110+ skills directory, run_agent.py awaiting decomposition
- **Resolver Pattern:** `RESOLVER.md` created for context routing
- **Latent vs Deterministic:** `_is_latent_task()` → 3-phase QA gate
- **Complexity Ratchet:** 禁task_qa_gate implementation
**Status:** Active. Resolver has 11 keyword branches.

### 10. GBrain Embedding Recovery (2026-06-16)
**What:** `embedding_disabled: true` in gbrain config → brain score 13/100, 38,443 unembedded chunks. Fix: Ollama restart, `embedding_disabled: false`, PGLite reinit, full sync + embed.
**Result:** Brain score 13 → 45/100, Embed 35/35 max.
**Status:** Resolved.

## Rationale
Growth engine systematically tracks improvements and applies learnings. Key pattern: doc-driven development has a gap between documentation and actual config application — mitigated by making config changes immediately after documenting.

## Current Status
All growth improvements active. Context compression working at threshold 0.9. 8 autonomous behaviors operational. No Silent Failure principle applied. Discord token resilience active. GBrain embedding recovered.

---
title: Memory & Knowledge Management — Compiled
type: wiki-compiled
tags: [compiled, memory, knowledge, gbrain, wiki-compile, facts]
trigger: "wiki-compile 2026-06-21 — compiled from P2-hippocampus; updated with fact extraction and MEMORY split pattern"
provenance:
  session: "2026-06-21 wiki-compile"
  decision: "Karpathy compile pattern and memory architecture, fact extraction, half-life routing"
created: 2026-06-21
updated: 2026-06-21
links:
  - "P5-ego/wiki/index"
  - "P5-ego/wiki/compiled/brain-signal-system"
  - "P5-ego/SELF_MODEL"
  - "P2-hippocampus/README"
---

# Memory & Knowledge Management — Compiled

## Core Decisions

### 1. Karpathy Compile Pattern (P2 → P5)
**What:** Two-tier knowledge: P2-hippocampus = raw archive (read-only, agent fingers off), P5-ego/wiki/compiled/ = compiled knowledge (query-first target).
**Why:** Raw data is unstructured and bulky. Compiled pages extract decisions, rationale, status.
**Alternatives considered:** Single knowledge store, vector DB only, graph DB only.
**Status:** Active since 2026-06-21. This wiki-compile creates/maintains compiled pages.

### 2. Query Routing Priority (Strict)
**What:** 1. P5-ego/wiki/compiled/ → 2. P2-hippocampus/memories/ → 3. P2-hippocampus/knowledge/ → 4. P2-hippocampus/sessions/. If you go beyond step 1, note what's missing.
**Why:** Most-to-least structured. Minimizes token waste on raw search.
**Status:** Active. Enforced via AGENTS.md and index.md.

### 3. MEMORY.md Canonical + Split Pattern
**What:** `P2-hippocampus/memories/MEMORY.md` is sole canonical memory (8KB cap). When cap hit, split into: `MEMORY.md` (canonical, 5KB) + `MEMORY_wiki.md` (agent's private file, 9.5KB). Also has `MEMORY_compact.md` (memory tool variant).
**Why:** 8KB cap forces structured content. Split preserves critical operational facts while reducing main file.
**Status:** Active. `~/.codex/memories/MEMORY.md` is Codex-CLI artifact — ignored.

### 4. Fact Half-Life Routing
**What:** Fact routing by type:
- Procedural rules → incident doc
- Class-level patterns → skill
- One-off preferences → memory tool
**Why:** Type-appropriate persistence. Rules need incident docs; preferences need quick recall.
**Status:** Active.

### 5. Fact Extraction System (Hot Memory - GBrain)
**What:** Extracts personal-knowledge facts (events, preferences, commitments, beliefs) from conversation turns into per-source hot memory. Haiku extraction → cosine + classifier dedup → INSERT.
**Why:** Structured facts survive session boundaries. Powers recall, trajectory, entity tracking.
**Status:** Active. `gbrain recall`, `gbrain forget_fact`, `gbrain find_trajectory` available.

### 6. Compression Threshold 0.9
**What:** M3 1M context, threshold 900K, post-compress 180-225K, target_ratio 0.2-0.25, 5x headroom.
**Why:** M3's 1M context allows much higher threshold. Prevents premature compression.
**Important lesson:** Doc written 5/21, config not patched until 6/1. Doc-driven development gap.
**Status:** Active since 2026-06-01.

### 7. GBrain 3-Pillar (Local)
**What:** 1. Repo = git-versioned wikilinked vault, 2. Compiled procedures in memory, 3. Graph traversal scripts, 4. Gap analysis.
**Why:** Structured without external DB dependency.
**Alternatives considered:** Full GBrain server, Notion, Roam.
**Status:** Active. Complemented by gbrain MCP server (89 tools).

### 8. Wiki Compile Cron
**What:** `wiki-compile` cron job (Sunday 03:00, archiver profile): compiles new P2 data → wiki pages. `wiki-lint` (daily 04:00, explorer profile): checks wiki health, reports issues.
**Why:** Regular compile keeps compiled pages current. Lint catches issues early.
**Status:** Both active.

## Rationale
The Karpathy compile pattern chosen over flat archive because agents need structured knowledge for efficient querying. Fact half-life routing ensures appropriate persistence per content type.

## Current Status
17 compiled pages active (up from 10). Query routing enforced. Fact extraction via GBrain. MEMORY.md canonical with split pattern. Weekly compile + daily lint cron active. Lint report needs population.

---
title: Taste Decisions — Compiled
type: wiki-compiled
tags: [compiled, taste, engineering-culture, provenance, leverage, design-patterns]
trigger: "wiki-compile 2026-06-21 — compiled from P2-hippocampus; updated with cross-cutting design patterns"
provenance:
  session: "2026-06-21 wiki-compile"
  decision: "Consolidate taste decisions from Pratik-inspired architecture overhaul and skill design patterns"
created: 2026-06-21
updated: 2026-06-21
links:
  - "P5-ego/wiki/compiled/agent-architecture"
  - "P5-ego/wiki/compiled/content-pipeline"
  - "P5-ego/wiki/compiled/kanban-system"
  - "P5-ego/wiki/compiled/skill-system"
  - "P5-ego/wiki/compiled/growth-engine"
  - "P1-limbic/persona/writing-style-guide"
  - "AGENTS.md"
---

# Taste Decisions — Compiled

## Core Decisions

### 1. Provenance Convention
**What:** Every artifact (skill, memory, config, kanban task, compiled page) carries `trigger` and `provenance` blocks documenting origin and decision rationale.
**Why:** "Prompt alongside PR" — the most expensive knowledge work is rediscovery. Without provenance, decisions lose context within weeks.
**Alternatives considered:** Git commit messages only (insufficient granularity), separate decision log (diverges from artifact).
**Status:** Active since 2026-06-14. Applied to AGENTS.md, all skills, kanban tasks, compiled pages.

### 2. Kanban Leverage Score
**What:** Every kanban task includes `## Leverage Assessment` with 1-5 score: how many other problems auto-resolve when this task is done. 5 = root cause (kills 10+ subproblems), 1 = surface change.
**Why:** Forces prioritization at creation time.
**Alternatives considered:** Priority tags only (P0/P1/P2), story points (too heavyweight).
**Status:** Active since 2026-06-14.

### 3. Tiered Autonomy (T1-T4)
**What:** 4-tier decision authority: T1 (docs/typos → autonomous), T2 (existing patterns → autonomous + provenance), T3 (structural → propose first), T4 (architecture → human only). Default to T3 when uncertain.
**Why:** Remove unnecessary confirmation friction for safe changes; ensure human oversight for risky ones.
**Alternatives considered:** Always ask (slow), never ask (risky).
**Status:** Active since 2026-06-14.

### 4. Answer-First Communication
**What:** Complex responses: summary/conclusion first → details only if needed → appendix. Exception: debugging (process-first).
**Why:** CLI environment demands immediate value. User wants outcome before process.
**Alternatives considered:** Process-first (traditional), TL;DR at end (forces scroll).
**Status:** Active since 2026-06-14.

### 5. Trigger + Kanban-Worker Pipeline
**What:** All LLM cron jobs split into: cron (shell, 0 LLM calls) → trigger (fast model, 5s) → kanban worker (full LLM reasoning).
**Why:** 279 keep items sat unapplied in Trend Harvester. Monolithic cron jobs timed out (600s), were fragile, debug-unfriendly.
**Alternatives considered:** Monolithic cron with longer timeout, synchronous pipeline.
**Status:** Active. Applied to Trend Harvester, Taste Review, SEO Article Harvester.

### 6. Ponytail — Lazy Senior Dev Mode
**What:** 6-question checklist before writing code: YAGNI → stdlib → native platform → existing deps → one line → minimal. Guardrails exempt from minimization: security, a11y, data-loss prevention.
**Why:** 80-94% less code, 3-6x faster. Prevents over-engineering.
**Alternatives considered:** No code review gate, full test-first always.
**Status:** Active since 2026-06-15. Integrated into implementer and reviewer profiles.

### 7. Baseline UI Quality Standard
**What:** Consolidated frontend quality bar: 13 priority tiers from Stack Defaults through Anti-Slop. Coherence meta-law: "One Choice Per Axis" — pick exactly one value per design axis.
**Why:** UI quality was inconsistent across projects. Scattered rules consolidated into single authoritative skill.
**Alternatives considered:** Per-project UI guidelines, no standard.
**Status:** Active since 2026-06-17.

### 8. Taste Review (bi-weekly)
**What:** Every Tuesday/Friday 10:00 KST, deeply analyze 1 high-quality tool from Trend Harvester keep list. 5-question framework: one-liner, stolen taste decisions, architecture insight, Drewgent applicability, leverage score.
**Why:** Systematically extract taste decisions from high-quality external projects.
**Status:** Active. Results stored in `P4-cortex/taste-reviews/`.

### 9. Cross-Cutting Design Patterns (from Skills)
**What:** Patterns that emerged across all skills:
- **Ruleset-only adoption (H1):** Import portable rules, skip platform-specific bits (ponytail, external-eval)
- **Try first, evaluate later:** User preference — test rather than decide by imagination
- **SILENT is correct:** Produce nothing when no output is valuable
- **PII protection:** localStorage→sessionStorage, credential stripping, env filtering
- **Three options as default:** Always 2-3 alternatives with recommendation
- **$0 over paid APIs:** SVG, Mermaid, Excalidraw over DALL-E/FAL
- **Same-tuple contract:** New code returns same shape as old (zero caller changes)
- **Subagent audit after mechanical split:** Subagents silently change behavior — path trace audit required
**Why:** These patterns reduce wasted output, improve security, and prevent regression.
**Status:** Active. Documented in individual skill SKILL.md files.

### 10. 40/60 Output Truncation Convention
**What:** Standardized 40/60 head/tail split for all tool output truncation: head contains schema/metadata, tail contains last error/result.
**Why:** Middle rows are skippable. Last result is critical for next action.
**Status:** Active. Applied to terminal, read_file, kanban_list, kanban_get.

## Rationale
Pratik Bhavsar's "30x AI Engineer with Taste" framework triggered the architecture overhaul. Three gaps identified: no provenance, no leverage scoring, no tiered autonomy. All implemented within 24 hours and cascaded into pipeline redesigns and skill design patterns.

## Current Status
All 10 taste decisions active. Provenance convention has broadest impact. Cross-cutting patterns documented across 100+ skills. Taste review runs bi-weekly.

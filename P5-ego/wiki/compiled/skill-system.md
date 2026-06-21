---
title: Skill System Architecture — Compiled
type: wiki-compiled
tags: [compiled, skills, system, architecture, curation]
trigger: "wiki-compile 2026-06-21 — compiled from skills/ directory inventory"
provenance:
  session: "2026-06-21 wiki-compile"
  decision: "Document skill system structure, curation, and loading mechanics"
created: 2026-06-21
updated: 2026-06-21
links:
  - "P5-ego/wiki/compiled/agent-architecture"
  - "P4-cortex/knowledge/NEURONFS_RULES"
---

# Skill System Architecture — Compiled

## Core Decisions

### 1. Flat Skill Hierarchy with on-demand Loading
**What:** 100+ skills across 62 directories under `~/.drewgent/skills/`. Each skill is `SKILL.md` in a named directory (e.g. `skills/software-development/ponytail/SKILL.md`). Loaded via `skill("name")` tool.
**Why:** Flat hierarchy is simple to navigate. On-demand loading prevents prompt bloat.
**Alternatives considered:** Deep nesting (hard to find), always-loaded (wastes context).
**Status:** Active. Bundled skills at `~/.config/opencode/skills/`.

### 2. Two Source Locations
**What:** Skills live in two locations:
- `~/.config/opencode/skills/` — opencode-bundled skills (cloudflare, agents-sdk, wrangler, etc.)
- `~/.drewgent/skills/` — Drewgent-custom skills (62 categories)
**Why:** Separation of concerns. Bundled = platform, custom = project-specific.
**Status:** Active. Custom manifest at `skills/.bundled_manifest`.

### 3. Skill Categories (62)
**What:** Organized by function: autonomous-ai-agents, brain, content, creative, devops, gaming, mcp, mlops, productivity, software-development, ui, apple, etc.
**Why:** Category prefix enables namespace isolation and easy discovery.
**Status:** Active with usage tracking at `skills/.usage.json`.

### 4. Skill Design Patterns (Cross-Cutting)
**What:** Common patterns across all skills:
- **Ruleset-only adoption (H1):** Import portable rules, skip platform-specific infrastructure (ponytail, external-tool-evaluation)
- **Provenance in frontmatter:** Every skill records `trigger`, `provenance.session`, `provenance.decision`
- **Three-option presentation:** Always offer 2-3 alternatives with recommendation
- **$0 visuals:** SVG, Mermaid, Excalidraw over paid APIs
- **SILENT is correct:** Produce nothing when no output is valuable
**Status:** Active. Enforced via curation process.

### 5. Skill Provenance Convention
**What:** Every SKILL.md frontmatter includes `trigger`, `provenance` (session, decision), `created`, `updated`.
**Why:** "Prompt alongside PR" — the most expensive knowledge work is rediscovery.
**Status:** Active since 2026-06-14. All new skills follow this convention.

### 6. Skill Optimization (SkillOpt)
**What:** System for benchmarking and optimizing skills via `gbrain run_skillopt`. Supports epochs, batch size, held-out test sets.
**Why:** Skills degrade as platform APIs change. Automated optimization maintains quality.
**Status:** Active. Requires skillopt-benchmark.jsonl per skill.

## Key Skill Clusters

### Agent Architecture
- `agent-profiles` — 14 profile definitions, delegate mechanism, dispatch patterns
- `acp-thinking-spinner` — ACP protocol spinner (UNRESOLVED)
- `brain-signal-system` — Event bus, signal processor, awareness
- `self-replicating-agent-tdd` — Branching agent architecture

### Software Development
- `ponytail` — 6-rung minimization checklist (lazy senior dev)
- `cf-worker-modular-architecture` — Router→Controllers→Engine→Utils
- `codebase-consolidation` — Single source of truth migration
- `codebase-refactoring` — Safe incremental refactoring
- `model-routing` — 3-tier flash/pro/max model selection
- `subagent-driven-development` — Parallel delegation patterns
- `mpa-url-state-bridge` — URL query param state persistence

### Design & Creative
- `baseline-ui` — 13-tier consolidated UI quality bar
- `claude-design` — Process-aware HTML artifact design
- `sketch` — 2-3 variant HTML mockup exploration
- `architecture-diagram` — Dark-themed SVG architecture diagrams
- `humanizer` — 29-pattern AI-ism removal

### Content & Publishing
- `content-pipeline` — Multi-stage editorial pipeline
- `content-manager` — CMO-style autonomous content agent
- `wordpress-cms` — Docker + Blocksy + MCP publishing
- `humanerd-site` — Site-specific quartz publishing

### Brain & Memory
- `daily-retro` — Structured daily reflection (30/70 human zone)
- `memory-md-cleanup` — MEMORY.md 8K cap management
- `vault-health` — Obsidian graph connectivity maintenance
- `vault-naming-convention` — Filename deduplication and wikilink safety

### DevOps
- `cron-script-fastpath` — `script` field bypasses LLM for simple jobs
- `kanban-orchestrator` — Decomposition playbook with anti-temptation rules
- `agent-dashboard-cf` — Cloudflare Workers dashboard (4 tabs, 23 collectors)
- `cloudflare-workers-deploy` — Secrets, diagnostics, deployment workflow

## Rationale
Flat hierarchy + on-demand loading minimizes system prompt size. Two-location split (bundled vs custom) enables platform upgrades without breaking Drewgent-specific skills. Provenance in every skill ensures decision context is never lost.

## Current Status
100+ skills active across 62 categories. Skill usage tracked. SkillOpt available for optimization. New skills follow provenance convention. Bundled + custom separation maintained.

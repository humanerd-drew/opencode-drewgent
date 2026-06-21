---
title: Agent Architecture — Compiled
type: wiki-compiled
tags: [compiled, agent-architecture, brain, subagents]
trigger: "wiki-compile 2026-06-21 — compiled from P2-hippocampus; updated with subagent profiles and office autopilot"
provenance:
  session: "2026-06-21 wiki-compile"
  decision: "Consolidate agent architecture decisions from memories/insights"
created: 2026-06-21
updated: 2026-06-21
links:
  - "P5-ego/wiki/compiled/taste-decisions"
  - "P5-ego/wiki/compiled/kanban-system"
  - "P5-ego/wiki/compiled/governance-system"
  - "P5-ego/wiki/compiled/model-routing"
  - "P5-ego/SELF_MODEL"
  - "P0-brainstem/brain/rules"
  - "AGENTS.md"
---

# Agent Architecture — Compiled

## Core Decisions

### 1. P-Layer Brain (7-layer subsumption architecture)
**What:** Drewgent brain organized as Obsidian vault P0-P6 with strict subsumption ordering. P0-brainstem rules override all others.
**Why:** NeuronFS-style governance — higher layers cannot contradict lower layers. P0 rules are immutable; P6-prefrontal handles ephemeral reflection.
**Alternatives considered:** Flat neuron file system, single-brain approach, external graph DB (Neo4j). P-layer chosen for Obsidian-native wikilink graph + filesystem-based governance.
**Status:** Active. All 7 layers operational.

### 2. Native Agent System (14 subagent profiles)
**What:** 14 subagent profiles at `~/.config/opencode/agents/*.md` in opencode native format. Profiles set model, provider, toolsets, instructions.
**Profile Roles:**
- **Flash tier:** explorer (research), implementer (code-gen), tester (verify), designer (mockups), sre (infra), analyst (data), archiver (docs)
- **Pro tier:** reviewer (code review), content-manager (CMO), editor (Korean QA), security-reviewer (security audit)
- **Max tier:** reviewer-critical (deep review), planner (task breakdown), orchestrator (pipeline management)
**ESCALATE mechanism:** Flash-tier profiles emit `ESCALATE: <reason>` when task exceeds their reasoning → orchestrator reroutes to higher tier.
**Why:** Replaced Hermes-Agent subagent system. opencode native profiles are zero-config (auto-discovered), support model-per-profile, and eliminate the Hermes dependency.
**Alternatives considered:** Hermes subagent system (removed), Claude Code subagent protocol, manual function calling.
**Status:** Active since 2026-06-18.

### 3. Agent Office — task() vs delegate()
**What:** Two-tier subagent dispatch:
- `task(subagent_type)` — fast, inherits parent model (same session)
- `delegate(name)` — spawns new session with profile model via `~/.config/opencode/tools/delegate.ts`
**Why:** Same-model tasks avoid cold-start latency. Different-model delegation ensures profile-specific model (e.g. kimi-k2.7-code for implementer) is actually used.
**Important rule:** Profiles with different models from parent MUST use `delegate()`. `task()` silently ignores profile model and uses parent's.
**Alternatives considered:** Always delegate (cold start every time), always task (profile model ignored).
**Status:** Active.

### 4. Office Autopilot
**What:** `office_autopilot.sh` runs every 5min via cron. Checks kanban DB for pending tasks → invokes orchestrator (qwen3.7-max) only when work exists. Orchestrator classifies task → delegates to appropriate subagent → kanban_complete on success → Discord summary.
**Why:** Silent when idle. Expensive orchestrator only called when needed. Fully autonomous task processing.
**Status:** Active since 2026-06-20.

### 5. Customize Layer (Drewgent ↔ Hermes integration)
**What:** `~/.drewgent/customize/` overrides `hermes_cli/{gateway,cron}.py` to patch `get_launchd_label` (→ `ai.drewgent.gateway`) and `find_gateway_pids` (macOS Sonoma+ plist format). Activated via `PYTHONPATH=~/.drewgent/customize`.
**Why:** Need to customize Hermes without forking the repo. Allows launchd label override, cron pid resolution fix.
**Key fix applied:** Removed `unset PYTHONPATH` from wrapper script (was killing customize layer). Original kept as `hermes.bak`.
**Alternatives considered:** Forking Hermes (maintenance burden), config-only customization (insufficient for code-level patches).
**Status:** Active. Smoke test cron T6 verifies after any Hermes upgrade.

### 6. OpenCode as Primary Runtime
**What:** Drewgent operates opencode-centric. Hermes-Agent removed. n8n removed (replaced by launchd cron).
**Why:** Eliminate redundant layers. opencode handles interactive (CLI/ACP/Discord), cron (launchd), and subagent dispatch natively.
**Alternatives considered:** Keep Hermes as orchestrator, keep n8n for cron.
**Status:** Active as of 2026-06-18 system overhaul.

### 7. ACP Thinking-Phase Indicator — UNRESOLVED
**What:** Cannot display LLM thinking-phase indicator in ACP clients. 3 attempts all rejected: `update_agent_thought_text` not rendered, heartbeat misunderstood, `ToolCallStart` not in stream area.
**Why:** ACP spec fundamentally has no in-stream visual indicator event.
**Alternatives considered:** Custom ACP extension, polling-based approach, terminal spinner workaround.
**Status:** UNRESOLVED. Do not retry without user explicit override.

### 8. Pre-Coding Ritual
**What:** Before writing code, read `禁karpathy_coding_principles.neuron` for project context discipline.
**Why:** Reinforces TDD, DRY, YAGNI, frequent commits before starting any coding work.
**Status:** Active.

### 9. Harmony Check (4-Layer Cross-Diff)
**What:** Daily 09:00 check comparing launchd state / ps state / jobs.json mtime / memory claims. Alerts on Discord when discrepancies found.
**Why:** Memory vs reality drift was a recurring incident cause (launchd mass failure).
**Status:** Active. Layer 3.5 monitors all services.

## Rationale
Subsumption architecture chosen over flat governance because AI agents need unambiguous rule priority. Native profiles over Hermes subagents because opencode is now the primary runtime. Customize layer over fork because Hermes upgrade compatibility without merge conflicts.

## Current Status
All architecture decisions active. 14 subagent profiles with ESCALATE mechanism. Office autopilot processing tasks silently. Harmony check monitors daily. ACP thinking-phase is the only unresolved item.

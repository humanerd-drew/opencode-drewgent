---
title: Model Routing & Cost — Compiled
type: wiki-compiled
tags: [compiled, models, routing, cost, providers, subagents]
trigger: "wiki-compile 2026-06-21 — compiled from P2-hippocampus; updated with ESCALATE and subagent model assignment"
provenance:
  session: "2026-06-21 wiki-compile"
  decision: "Model tier system, subagent assignment, and ESCALATE mechanism"
created: 2026-06-21
updated: 2026-06-21
links:
  - "P5-ego/wiki/compiled/agent-architecture"
  - "P5-ego/wiki/compiled/taste-decisions"
---

# Model Routing & Cost — Compiled

## Core Decisions

### 1. OpenCode Go Subscription (Primary)
**What:** OpenCode GO subscription provides all models across 3 tiers: Flash (deepseek-v4-flash, kimi-k2.7-code), Pro (deepseek-v4-pro, glm-5.2, minimax-m3), Max (qwen3.7-max, qwen3.7-plus).
**Why:** Zero per-call marginal cost for interactive use. Single aggregator manages all provider routing.
**Alternatives considered:** Direct provider API calls (per-call cost), OpenAI subscription only.
**Status:** Active.

### 2. Three-Tier Model Pyramid (Flash / Pro / Max)
**What:** 3-tier pyramid matching capability to complexity:
- **Flash:** deepseek-v4-flash, kimi-k2.7-code — fast, cheap, daily tasks
- **Pro:** deepseek-v4-pro, glm-5.2, minimax-m3 — balanced, subagents
- **Max:** qwen3.7-max, qwen3.7-plus — complex reasoning, architecture
**Why:** Right model for right task. Subscription billing (fixed cost) changes optimization from "minimize tokens" to "match capability."
**Status:** Active.

### 3. Subagent Model Assignment (Per-Profile)
**What:** 14 profiles with specific model assignments:
| Tier | Profiles | Model |
|------|----------|-------|
| Flash | explorer, implementer, tester, designer, sre, analyst, archiver | deepseek-v4-flash |
| Flash-kimi | implementer (code-gen) | kimi-k2.7-code |
| Pro | reviewer, content-manager, editor, security-reviewer | deepseek-v4-pro / glm-5.2 / minimax-m3 |
| Max | reviewer-critical, planner, orchestrator | qwen3.7-max / qwen3.7-plus |
**Important nuance:** kimi-k2.7-code is the code-gen model (Flash tier). deepseek-v4-pro is general Pro tier.
**Status:** Active.

### 4. ESCALATE Mechanism
**What:** Flash-tier profiles emit `ESCALATE: <reason>` when task exceeds their reasoning capability. Orchestrator reroutes to higher tier (Pro or Max).
**Why:** Graceful capability escalation without over-assigning expensive models.
**Status:** Active. Implemented in agent profiles.

### 5. task() vs delegate() Model Dispatch
**What:** `task(subagent_type)` inherits parent model (fast). `delegate(name)` spawns new session with profile model.
**Why:** Profiles with different models from parent must use `delegate()`. `task()` ignores profile model.
**Status:** Active. Critical for implementer (kimi-k2.7-code) and orchestrator (qwen3.7-max).

### 6. MiniMax-M3 (1M Context) for Background
**What:** MiniMax-M3 replaces M2.7 for run_kanban_worker, hindsight, auxiliary_client×2. M2.5 kept as legacy flag.
**Why:** M3 is M2.7 superset with 1M context. Reduces compression frequency. Per-call credits under Token Plan.
**Alternatives considered:** M2.5/2.7 only, opencode-go for everything.
**Status:** Active.

### 7. Token Plan Credits (Separate from Subscription)
**What:** MiniMax Token Plan (per-call credits) for background LLM work. Not to be confused with opencode-go subscription.
**Why:** Separate billing for background (cheap per-call) vs interactive (flat subscription).
**Status:** Active. `OPENCODE_GO_BASE_URL` intentionally unset to keep them separate.

### 8. Model Routing for Subagent Types
**What:** Same-model → `task()` (fast path). Different-model → `delegate()` (profile model).
**Why:** Implementer needs kimi-k2.7-code for code-gen. Orchestrator needs qwen3.7-max for reasoning.
**Status:** Active. Delegate tool at `~/.config/opencode/tools/delegate.ts`.

## Rationale
Three-tier system balances capability vs cost. Subscription eliminates per-call anxiety. ESCALATE ensures flash-tier profiles don't fail silently on complex tasks. kimi-k2.7-code chosen for code generation based on benchmark performance.

## Current Status
All routes active. OpenCode Go subscription provides 10+ models. MiniMax Token Plan covers background. ESCALATE mechanism operational. No tier changes since 2026-06-18 overhaul.

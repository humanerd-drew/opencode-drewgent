---
name: model-routing
description: Cost-aware multi-tier model selection strategy. Assigns models to roles (main agent, subagent, auxiliary) by capability tier under subscription billing. Defines the 3-tier flash/pro/max pyramid and the escalation path. Supersedes the per-call era cost-optimization-background-llm skill.
version: 1.1.0
created: 2026-06-13
updated: 2026-06-15
tags: [routing, cost, model, provider, subscription, opencode-go, minimax]
related_skills: [cost-optimization-background-llm, kanban-orchestrator, hermes-model-routing, agent-dashboard-cf, fusion-agent]
---

# Model Routing — Subscription-Era Cost-Aware Strategy

## Core Principle

OpenCode Go = **fixed cost** ($10/month). Every call through OpenCode Go has **zero marginal cost**. The optimization problem shifts from "minimize per-token spend" to "match model capability to task complexity without wasting user time."

Direct MiniMax API = **per-call credits** (Token Plan). Use only when OpenCode Go's proxy doesn't deliver equivalent quality for a specific capability.

## The 3-Tier Model Pyramid

| Tier | Model | Profiles | Latency | When to Use |
|------|-------|----------|---------|-------------|
| **Flash** | `deepseek-v4-flash` | explorer, implementer, tester, archiver | Fastest | Read-only analysis, simple implementation, tests, docs. The default workhorse. |
| **Pro** | `deepseek-v4-pro` | reviewer | Moderate | General code review. Stronger reasoning needed. |
| **Max** | `qwen3.7-max` | planner, reviewer-critical, security-reviewer | Slowest | Complex planning, critical review, security audit. Use sparingly. |

## Routing Configuration

### Config.yaml (active 2026-06-13)

```yaml
model:
  default: "opencode-go/deepseek-v4-flash"
  provider: "opencode-go"

delegation:
  provider: "opencode-go"
  model: "deepseek-v4-pro"       # subagent gets stronger model for quality

auxiliary:
  vision:
    provider: "opencode-go"
    model: "mimo-v2.5-pro"       # only multimodal option on OpenCode Go
  web_extract:
    provider: "opencode-go"
    model: "deepseek-v4-flash"
  session_search:
    provider: "opencode-go"
    model: "deepseek-v4-flash"
```

### Agent Profiles (`~/.drewgent/agents/*.md`)

8 pre-defined roles, each with model/provider/toolsets/instructions. Loaded via `task(subagent_type="reviewer", description="...", prompt="...")`. The `subagent_type` parameter is built into the `task` tool schema — every agent sees it.

### Pipeline (Tier-Adaptive)

```
Tier 1 (simple):   Implementer(flash) → Archiver(flash)
Tier 2 (moderate): Explorer(flash) → Implementer(flash) ↔ Tester(flash) [≤2 loops] → Archiver(flash)
Tier 3 (complex):  Planner(max) → Explorer(flash) → Implementer(flash) ↔ Tester(flash) [≤3 loops]
                    → Reviewer(pro) → [security? → Security-reviewer(max)]
                    → [critical? → Reviewer-critical(max)] → Archiver(flash)
```

### ESCALATE Mechanism

Flash-tier profiles can emit `ESCALATE: <reason>` when the task exceeds their reasoning capability. The caller detects this and re-routes to a stronger model.

## User Preference: Cost in Every Proposal

Every architecture or model proposal MUST include a cost analysis section. Structure:
- Which cost model applies (subscription vs per-call)
- Marginal cost per additional call
- Tier assignment rationale (why flash/pro/max for each role)
- Fallback strategy (what happens if the primary provider is rate-limited)

## Available Providers

- **OpenCode Go** (`opencode-go`): $10/mo subscription. All models included at zero marginal cost. API at `https://opencode.ai/zen/go/v1`. Key: `OPENCODE_GO_API_KEY`.
- **MiniMax direct** (`minimax`): Token Plan per-call credits. API at `https://api.minimax.io/anthropic` (Anthropic format). Key: `MINIMAX_API_KEY`. Use only as fallback.
- **OpenCode Zen** (`opencode-zen`): Pay-as-you-go at `https://opencode.ai/zen/v1`. Not active in current setup.

## Pitfalls

### Duplicate Provider Keys Cause HTTP 400 on Session Restore

If both `OPENROUTER_API_KEY` and `OPENCODE_GO_API_KEY` are present in `.env`, the agent may use the wrong provider on session restore (`restore_primary` picks up openrouter). The model name `opencode-go/deepseek-v4-flash` only works on OpenCode Go — OpenRouter returns HTTP 400 "not a valid model ID".

**Symptom**: Dashboard shows repeated `HTTP 400: opencode-go/deepseek-v4-flash is not a valid model ID` errors. Agent log shows `provider=openrouter model=opencode-go/deepseek-v4-flash` → fail → `Fallback activated: deepseek-v4-flash (opencode-go)` → success.

**Fix**: Remove the unused provider's API key from `.env`. Keep only the active provider's key.

**Model naming convention**: When provider is `opencode-go`, use bare model name (`deepseek-v4-flash`). When provider is `opencode-go`, the config model name includes provider prefix (`opencode-go/deepseek-v4-flash`) which works with the main agent but breaks on fallback providers.

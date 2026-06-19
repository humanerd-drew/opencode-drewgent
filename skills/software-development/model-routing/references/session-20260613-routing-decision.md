# Model Routing — Session Detail (2026-06-13)

## Trigger

User asked: "OpenCode Go에서 제공하는 모델들을 적극적으로 라우팅하면서 사용할 수 있나?"
Current state: single deepseek-v4-flash doing everything, MiniMax key unused.

## Decision Rationale

1. **OpenCode Go first** — Already paying $10/month. Marginal cost = $0 per call. Not using it = wasting money.
2. **MiniMax direct as fallback** — Token Plan is per-call cost. Only use when OpenCode Go's proxy of MiniMax-M3 doesn't deliver equivalent quality, or when OpenCode Go is rate-limited.
3. **3-tier model pyramid** — Flash (fast, $0) for most work, Pro for review, Max for planning/security. Prevents user from waiting on heavy models for simple tasks.
4. **Agent profiles** — Prevents each session from re-deriving role definitions. Built into delegate_task tool schema for discoverability.
5. **ESCALATE mechanism** — Flash-tier models can admit defeat and request escalation. Prevents silent quality degradation.

## Loop Engineering Assessment

The [addyo essay](https://addyo.substack.com/p/loop-engineering) defines 5 building blocks + 1 memory store:

| # | Component | Drewgent Status | Gap |
|---|-----------|----------------|-----|
| 1 | Automations (scheduled discovery/triage) | ✅ Strong — cron + kanban dispatcher | No /goal in main session (kanban goal_mode covers it) |
| 2 | Worktrees (parallel file isolation) | ⚠️ Adequate — kanban_create workspace_kind=worktree exists but not default | Subagent worktree isolation missing |
| 3 | Skills (written project knowledge) | ✅ Excellent — 100+ skills, SKILL.md format | Auto-matching weak (manual load needed) |
| 4 | Connectors/Plugins (MCP) | ✅ Strong — native MCP client | MCP discoverability on-demand |
| 5 | Sub-agents (maker/checker split) | ✅ Strong — delegate_task + agent profiles | No static agent definition files (TOML in Codex) |
| 6 | Memory (durable state) | ✅ Excellent — kanban + vault + MEMORY.md | |

## Cost Analysis per Pipeline Run

### Tier 1 (simple)
- Implementer(flash) 1 call → Archiver(flash) 1 call
- Total: 2 flash calls, $0 marginal cost

### Tier 2 (moderate)
- Explorer(flash) 1 call → Implementer(flash) 1 call ↔ Tester(flash) ≤2 calls → Archiver(flash) 1 call
- Total: 4-5 flash calls, $0 marginal cost

### Tier 3 (complex)
- Planner(max) 1 call → Explorer(flash) 1 call → Implementer(flash) 1 call ↔ Tester(flash) ≤3 calls
- → Reviewer(pro) 1 call → [optional Security-reviewer(max) 1 call]
- → [optional Reviewer-critical(max) 1 call] → Archiver(flash) 1 call
- Total: 1 max + 1 pro + 4-6 flash = $0 (all OpenCode Go)

## Provider Auto-Resolution Order

When `model.provider: "auto"`, Hermes checks PROVIDER_REGISTRY in insertion order:
1. OPENAI_API_KEY/OPENROUTER_API_KEY → openrouter
2. Individual API keys: minimax (MINIMAX_API_KEY) → deepseek → ... → opencode-zen → opencode-go

Since MINIMAX_API_KEY is checked BEFORE OPENCODE_GO_API_KEY, `auto` resolves to "minimax" first. To use OpenCode Go, the provider must be explicitly set.

## Previously Used Cost Profile (Legacy — Per-Call Era)

Before 2026-06-13, routing used:
- Main: `opencode-go/deepseek-v4-flash` (via OpenRouter/OpenCode)
- MiniMax-M3 for kanban worker, hindsight, auxiliary×2 (Token Plan per-call credits)
- Cost optimization meant routing cheap work to MiniMax-M2.5 and expensive work to MiniMax-M3

This was replaced by the current subscription-based strategy where ALL traffic routes through OpenCode Go. The cost-optimization-background-llm skill documents the legacy approach.

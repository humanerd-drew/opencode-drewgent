# Loop Engineering Assessment — Drewgent (2026-06-13, updated 2026-06-13)

Assessment of Drewgent against the [loop engineering framework](https://addyo.substack.com/p/loop-engineering): 5 building blocks + 1 memory store.

## 1. Automations (Heartbeat)

**Score: ★★★★☆**

| Requirement | Drewgent |
|---|---|
| Scheduled auto-discovery | `cronjob` tool — cron, interval, ISO |
| Background triage | Kanban dispatcher + cron-runner |
| Skill-based automation | Cron job `skills:` field |
| Silent runs | `no_agent=True` — empty stdout = silent |
| In-session /goal loop | Missing from CLI (exists in kanban `goal_mode`) |

**Gap:** No `/goal` or `/loop` CLI primitive. Kanban `goal_mode` covers background use.

## 2. Worktrees (Parallel Isolation)

**Score: ★★★☆☆**

| Requirement | Drewgent |
|---|---|
| Git worktree | `kanban_create(workspace_kind="worktree")` |
| Config toggle | `config.yaml worktree: true/false` (commented) |
| Auto-cleanup | `scratch` workspace auto-GC'd |
| Subagent isolation | `delegate_task` separate terminal, no worktree |

**Gap:** Worktree not default. Subagents share filesystem.

## 3. Skills (Project Knowledge)

**Score: ★★★★★**

| Requirement | Drewgent |
|---|---|
| SKILL.md format | Full YAML frontmatter + body, 100+ skills |
| Trigger conditions | `trigger:` field in frontmatter |
| Skill auto-load | Manual via `skill_view()`, cron via `skills:` |
| Shared across repos | `skill_manage` tool |

**Note:** Skills captured from this session (2026-06-13):
- `devops/kanban-orchestrator` — updated with agent profiles, cost-aware pipeline, Drewgent design principles
- `devops/kanban-worker` — updated with agent profile references and Linear hook side-effect

## 4. Plugins & Connectors (MCP)

**Score: ★★★★☆**

| Requirement | Drewgent |
|---|---|
| MCP protocol | Native MCP client + mcporter |
| Connectors | gbrain, specification-website, linear MCP (installed) |
| Plugin packaging | Plugin system + shell hooks |
| Event-driven integration | `post_tool_call` hook on `kanban_complete` → Linear sync |

**Gap:** MCP tools on-demand via `tool_search`.

## 5. Sub-agents (Maker/Checker Split)

**Score: ★★★★★**

| Requirement | Drewgent |
|---|---|
| Sub-agent spawning | `delegate_task` single + batch |
| Per-agent model override | `agent_profile` parameter (baked into `delegate_task` schema) |
| Static agent profiles | 8 roles at `~/.drewgent/agents/*.md` |
| Pipeline | `kanban_create(pipeline=[...])` auto-decomposition |
| ESCALATE mechanism | Flash-tier profiles can signal `ESCALATE: <reason>` |
| Cost-aware tiers | Flash/Pro/Max — complexity determines routing |

## 6. Memory (Durable State = Spine)

**Score: ★★★★★**

| Requirement | Drewgent |
|---|---|
| Durable task state | Kanban SQLite board |
| Cross-session context | `memory()` tool + `session_search()` FTS5 |
| Knowledge vault | P0-P6 Obsidian vault with wikilinks |
| External visibility | Linear bridge (kanban_complete → hook → Linear issue) |

## Pipeline Design (Tiered, Cost-Aware)

```
Tier 1: Implementer(flash) → Archiver(flash)
Tier 2: Explorer(flash) → Implementer(flash) ↔ Tester(flash) [≤2] → Archiver(flash)
Tier 3: Planner(max) → Explorer → Implementer ↔ Tester [≤3] → Reviewer(pro)
        → [security/auth?] → Security-reviewer(max)
        → [critical?] → Reviewer-critical(max)
        → Archiver(flash)
```

## Cost Structure

| Infra | Model | Cost | Strategy |
|-------|-------|------|----------|
| OpenCode Go ($10/mo) | deepseek-v4-flash/pro, qwen3.7-max, etc. | Fixed | Saturate — marginal cost $0 |
| MiniMax Token Plan | MiniMax-M3 (via direct API) | Per-call | Fallback only |

## Drewgent Design Principles (2026-06-13)

Established from the loop engineering essay analysis and multi-agent architecture discussion:

1. **Event-driven over polling.** Prefer `post_tool_call` hooks over cron for event-triggered work. Cron reserved for periodic maintenance (prune, health checks).
2. **Cost-aware routing.** Maximize fixed-cost infrastructure (OpenCode Go sub) before using per-call billing. Model tiers (Flash/Pro/Max) match capability to task complexity.
3. **Self-cleaning defaults.** Auto-prune completed issues after 7 days. If a maintenance task is always needed, build it into the flow rather than requiring manual intervention.
4. **Gap analysis before finalizing.** Always ask "are there gaps?" covering: tier assignment, retry loops/model limits, ESCALATE path, and security gate.
5. **Maker/checker split.** The agent that writes code should NOT review it. Separate `reviewer` profile, different model (pro vs flash), different instructions.
6. **Security as a distinct gate.** Not a sub-check of review. Separate `security-reviewer` profile with OWASP/crypto/auth checklist, invoked when labels include security/auth/payment/crypto.

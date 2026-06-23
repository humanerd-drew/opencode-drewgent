# Loop Engineering — Drewgent Assessment

Source: [addyo's essay](https://addyo.substack.com/p/loop-engineering)  
Assessed: 2026-06-13  
Framework: 5 building blocks + 1 memory store

## Core Thesis

> "You shouldn't be prompting coding agents anymore. You should be designing loops that prompt your agents." — Peter Steinberger

## Drewgent Assessment by Component

### 1. Automations (Heartbeat)

**Score: ★★★★☆ Strong**

| Requirement | Drewgent Status |
|-------------|----------------|
| Scheduled auto-discovery | `cronjob` tool — cron expressions, intervals, ISO timestamps |
| Background triage | Kanban dispatcher + cron-runner auto-publishes tasks |
| Skill-based automation | Cron jobs accept `skills: [...]` list |
| Silent runs (no findings = silent) | `no_agent=True` mode — empty stdout = no delivery |
| In-session recurring loop | ❌ Missing. No `/goal` or `/loop` equivalent in main CLI session |

**Key gap**: `/goal` (keep going until condition met, separate judge model) only exists in kanban `goal_mode` (for dispatched workers). Main CLI session lacks it. But for Drewgent's architecture, kanban `goal_mode` is the right place — detached background worker beats a blocking in-session loop.

### 2. Worktrees (Parallel Isolation)

**Score: ★★★☆☆ Adequate**

| Requirement | Drewgent Status |
|-------------|----------------|
| Git worktree for parallel agents | `kanban_create(workspace_kind="worktree")` supported |
| Config toggle | `config.yaml` has `worktree: true/false` (commented out) |
| Auto-cleanup | `scratch` workspace = tmpdir; `worktree` = git cleanup |
| Subagent worktree isolation | `delegate_task` subagents have isolated terminal sessions but share the repo directory |

**Key gap**: Worktree isolation not default. Subagents working in parallel on the same repo risk file collisions. For complex work, route through kanban with `workspace_kind="worktree"`. For simple delegate_task work, the risk is low.

### 3. Skills (Project Knowledge)

**Score: ★★★★★ Excellent**

| Requirement | Drewgent Status |
|-------------|----------------|
| SKILL.md format (frontmatter + body) | Fully supported. 100+ skills across categories |
| Trigger conditions | `trigger:` frontmatter field (provenance convention) |
| Skill auto-load via matching | Manual via `skill_view(name)`. Cron jobs accept `skills: [...]` |
| Shared across repos | `skill_manage` tool + `~/.drewgent/skills/` |
| Intent capture | 禁 `.neuron` files, P0-P6 vault, provenance convention |

**Key gap**: Auto-matching (task description triggers skill load) is weak. Currently needs explicit `skill_view()` call.

### 4. Plugins & Connectors (MCP)

**Score: ★★★★☆ Strong**

| Requirement | Drewgent Status |
|-------------|----------------|
| MCP protocol | Native MCP client built-in + mcporter CLI |
| Service connectors | MCP catalog (gbrain, specification-website) |
| Plugin packaging | Plugin system (model-providers, hooks, gateway plugins) |
| Shell hooks | `hooks:` config section — pre/post tool call, LLM call |

**Key gap**: MCP servers are on-demand (loaded via tool_search). Agent must discover them explicitly. Linear MCP is pre-packaged at `optional-mcps/linear/manifest.yaml` but not yet configured.

### 5. Sub-agents (Maker/Checker Split)

**Score: ★★★★☆ Strong**

| Requirement | Drewgent Status |
|-------------|----------------|
| Sub-agent spawning | `delegate_task` — single + batch (parallel up to max_concurrent) |
| Per-subagent model override | `delegation.provider`/`model` in config ✅, now also via `agent_profile` |
| Maker/Checker split | Supported via separate `agent_profile` assignments |
| Agent definition files | ✅ **NEW**: `~/.drewgent/agents/*.md` — 8 profiles with frontmatter |
| Static profile format | Markdown + YAML frontmatter (same format as SKILL.md) |

**Key improvement**: The agent profile system (built this session) adds static role definitions with model/provider/toolsets/instructions, integrated directly into `task(subagent_type="reviewer")`.

### 6. Memory (External State = Spine)

**Score: ★★★★★ Excellent**

| Requirement | Drewgent Status |
|-------------|----------------|
| Kanban board as durable state | `kanban_create`/`kanban_complete` — SQLite, survives restarts |
| Cron context chaining | `context_from: [job_id]` — upstream output injection |
| Session persistence | `memory()` tool (two stores) + `session_search()` (FTS5) |
| Vault as knowledge spine | P0-P6 Obsidian vault + wikilinks + AGENTS.md |
| State file | MEMORY.md, USER.md, P6-prefrontal/incidents/ |

**Strongest component**. Triple redundancy: vault (long-term), memory (session-to-session), kanban (task-level).

## Applying the Framework in Drewgent

### The 3-Layer Loop Architecture

```
┌─────────────────────────────────────────────────┐
│  Layer 3: Linear Bridge (Human Visibility)       │
│  Kanban → Linear sync via MCP                    │
│  Labels → Discord/CLI feedback loop              │
├─────────────────────────────────────────────────┤
│  Layer 2: Kanban (Task Orchestration)            │
│  goal_mode + agent profiles + cron dispatch      │
│  explorer→implementer↔tester→reviewer→archiver   │
├─────────────────────────────────────────────────┤
│  Layer 1: Agent Profiles (Subagent Roles)        │
│  8 profiles, 3 cost tiers, ESCALATE mechanism    │
│  task(subagent_type="...")               │
└─────────────────────────────────────────────────┘
```

### Key Principles for Drewgent

1. **Maker/checker split.** The implementer and reviewer must be different agents with different models. Current implementation: implementer=flash, reviewer=pro.

2. **Cost-aware routing.** All models through OpenCode Go ($10/mo subscription). Marginal cost = $0 for all calls. MiniMax direct API is fallback only (per-call credits, only when OpenCode Go is rate-limited).

3. **State on disk.** Kanban board SQLite is the durable spine. The worker forgets between spawns; the board doesn't.

4. **Tiered pipeline.** Not all work needs the full 8-profile sequence. Tier 1 (2 calls) vs Tier 2 (4 calls) vs Tier 3 (6+ calls with max model).

5. **ESCALATE mechanism.** Flash-tier models can signal "beyond my capability" and get re-routed to Max-tier. Prevents spinning on impossible tasks.

6. **Comprehension debt awareness.** Faster loops widen the gap between what exists and what you understand. Every kanban complete should produce a reviewable handoff.

7. **Cognitive surrender risk.** Designing the loop is the cure when done with judgement; the accelerant when done to avoid thinking. Always route with intent.

### When designing a kanban task graph, ask:

- Which tier does this task belong to?
- Where is the maker/checker split?
- Is a security reviewer needed? (auth/crypto/payment labels?)
- What happens if this runs unattended for 24 hours?
- Does the implementer have a tester feedback loop?
- Is the handoff reviewable by a human?

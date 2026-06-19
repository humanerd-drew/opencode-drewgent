---
name: kanban-orchestrator
description: Decomposition playbook + anti-temptation rules for an orchestrator profile routing work through Kanban. The "don't do the work yourself" rule and the basic lifecycle are auto-injected into every kanban worker's system prompt; this skill is the deeper playbook when you're specifically playing the orchestrator role.
version: 3.0.0
platforms: [linux, macos, windows]
environments: [kanban]
metadata:
  hermes:
    tags: [kanban, multi-agent, orchestration, routing]
    related_skills: [kanban-worker]
links:
  - "[[P0-brainstem/brain/rules]]"
  - "[[P3-sensors/skills/SKILL-INDEX]]"
---

# Kanban Orchestrator — Decomposition Playbook

> The **core worker lifecycle** (including the `kanban_create` fan-out pattern and the "decompose, don't execute" rule) is auto-injected into every kanban process via the `KANBAN_GUIDANCE` system-prompt block. This skill is the deeper playbook when you're an orchestrator profile whose whole job is routing.

## Profiles are user-configured — not a fixed roster

Hermes setups vary widely. Some users run a single profile that does everything; some run a small fleet (`docker-worker`, `cron-worker`); some run a curated specialist team they've named themselves. There is **no default specialist roster** — the orchestrator skill does not know what profiles exist on this machine.

Before fanning out, you must ground the decomposition in the profiles that actually exist. The dispatcher silently fails to spawn unknown assignee names — it doesn't autocorrect, doesn't suggest, doesn't fall back. So a card assigned to `researcher` on a setup that only has `docker-worker` just sits in `ready` forever.

**Step 0: discover available profiles before planning.**

Use one of these:

- `hermes profile list` — prints the table of profiles configured on this machine. Run it through your terminal tool if you have one; otherwise ask the user.
- `kanban_list(assignee="<some-name>")` — sanity-check a single name. Returns an empty list (rather than an error) for an unknown assignee, so this only confirms a name you're already considering.
- **Just ask the user.** "What profiles do you have set up?" is a fine first turn when the goal needs more than one specialist.

Cache the result in your working memory for the rest of the conversation. Re-asking every turn wastes a tool call.

## When to use the board (vs. just doing the work)

Create Kanban tasks when any of these are true:

1. **Multiple specialists are needed.** Research + analysis + writing is three profiles.
2. **The work should survive a crash or restart.** Long-running, recurring, or important.
3. **The user might want to interject.** Human-in-the-loop at any step.
4. **Multiple subtasks can run in parallel.** Fan-out for speed.
5. **Review / iteration is expected.** A reviewer profile loops on drafter output.
6. **The audit trail matters.** Board rows persist in SQLite forever.

If *none* of those apply — it's a small one-shot reasoning task — use `delegate_task` instead or answer the user directly.

## The anti-temptation rules

Your job description says "route, don't execute." The rules that enforce that:

- **Do not execute the work yourself.** Your restricted toolset usually doesn't even include terminal/file/code/web for implementation. If you find yourself "just fixing this quickly" — stop and create a task for the right specialist.
- **For any concrete task, create a Kanban task and assign it.** Every single time.
- **Split multi-lane requests before creating cards.** A user prompt can contain several independent workstreams. Extract those lanes first, then create one card per lane instead of bundling unrelated work into a single implementer card.
- **Run independent lanes in parallel.** If two cards do not need each other's output, leave them unlinked so the dispatcher can fan them out. Link only true data dependencies.
- **Never create dependent work as independent ready cards.** If a card must wait for another card, pass `parents=[...]` in the original `kanban_create` call. Do not create it first and link it later, and do not rely on prose like "wait for T1" inside the body.
- **If no specialist fits the available profiles, ask the user which profile to create or which existing profile to use.** Do not invent profile names; the dispatcher will silently drop unknown assignees.
- **Decompose, route, and summarize — that's the whole job.**

## Decomposition playbook

### Step 1 — Understand the goal

Ask clarifying questions if the goal is ambiguous. Cheap to ask; expensive to spawn the wrong fleet.

### Step 2 — Sketch the task graph

Before creating anything, draft the graph out loud (in your response to the user). Treat every concrete workstream as a candidate card:

1. Extract the lanes from the request.
2. Map each lane to one of the profiles you discovered in Step 0. If a lane doesn't fit any existing profile, ask the user which to use or create.
3. Decide whether each lane is independent or gated by another lane.
4. Create independent lanes as parallel cards with no parent links.
5. Create synthesis/review/integration cards with parent links to the lanes they depend on. A child created with unfinished parents starts in `todo`; the dispatcher promotes it to `ready` only after every parent is done.

Examples of prompts that should fan out (using placeholder profile names — substitute whatever exists on the user's setup):

- "Build an app" → one card to a design-oriented profile for product/UI direction, one or two cards to engineering profiles for implementation, plus a later integration/review card if the user has a reviewer profile.
- "Fix blockers and check model variants" → one implementation card for the blocker fixes plus one discovery/research card for config/source verification. A final reviewer card can depend on both.
- "Research docs and implement" → a docs-research card can run in parallel with a codebase-discovery card; implementation waits only if it truly needs those findings.
- "Analyze this screenshot and find the related code" → one card to a vision-capable profile for the visual analysis while another searches the codebase.

Words like "also," "finally," or "and" do not automatically imply a dependency. They often mean "make sure this is covered before reporting back." Only link tasks when one card cannot start until another card's output exists.

Show the graph to the user before creating cards. Let them correct it — including which actual profile name should own each lane.

### Step 3 — Create tasks and link

Use the profile names from Step 0. The example below uses placeholders `<profile-A>`, `<profile-B>`, `<profile-C>` — replace them with what the user actually has.

```python
t1 = kanban_create(
    title="research: Postgres cost vs current",
    assignee="<profile-A>",  # whichever profile handles research on this setup
    body="Compare estimated infrastructure costs, migration costs, and ongoing ops costs over a 3-year window. Sources: AWS/GCP pricing, team time estimates, current Postgres bills from peers.",
    tenant=os.environ.get("HERMES_TENANT"),
)["task_id"]

t2 = kanban_create(
    title="research: Postgres performance vs current",
    assignee="<profile-A>",  # same profile, run in parallel
    body="Compare query latency, throughput, and scaling characteristics at our expected data volume (~500GB, 10k QPS peak). Sources: benchmark papers, public case studies, pgbench results if easy.",
)["task_id"]

t3 = kanban_create(
    title="synthesize migration recommendation",
    assignee="<profile-B>",  # whichever profile does synthesis/analysis
    body="Read the findings from T1 (cost) and T2 (performance). Produce a 1-page recommendation with explicit trade-offs and a go/no-go call.",
    parents=[t1, t2],
)["task_id"]

t4 = kanban_create(
    title="draft decision memo",
    assignee="<profile-C>",  # whichever profile drafts user-facing prose
    body="Turn the analyst's recommendation into a 2-page memo for the CTO. Match the tone of previous decision memos in the team's knowledge base.",
    parents=[t3],
)["task_id"]
```

`parents=[...]` gates promotion — children stay in `todo` until every parent reaches `done`, then auto-promote to `ready`. No manual coordination needed; the dispatcher and dependency engine handle it.

If the task graph has dependencies, create the parent cards first, capture their returned ids, and include those ids in the child card's `parents` list during the child `kanban_create` call. Avoid creating all cards in parallel and linking them afterward; that creates a window where the dispatcher can claim a child before its inputs exist.

### Step 4 — Complete your own task

If you were spawned as a task yourself (e.g. a planner profile was assigned `T0: "investigate Postgres migration"`), mark it done with a summary of what you created:

```python
kanban_complete(
    summary="decomposed into T1-T4: 2 research lanes in parallel, 1 synthesis on their outputs, 1 prose draft on the recommendation",
    metadata={
        "task_graph": {
            "T1": {"assignee": "<profile-A>", "parents": []},
            "T2": {"assignee": "<profile-A>", "parents": []},
            "T3": {"assignee": "<profile-B>", "parents": ["T1", "T2"]},
            "T4": {"assignee": "<profile-C>", "parents": ["T3"]},
        },
    },
)
```

### Step 5 — Report back to the user

Tell them what you created in plain prose, naming the actual profiles you used:

> I've queued 4 tasks:
> - **T1** (`<profile-A>`): cost comparison
> - **T2** (`<profile-A>`): performance comparison, in parallel with T1
> - **T3** (`<profile-B>`): synthesizes T1 + T2 into a recommendation
> - **T4** (`<profile-C>`): turns T3 into a CTO memo
>
> The dispatcher will pick up T1 and T2 now. T3 starts when both finish. You'll get a gateway ping when T4 completes. Use the dashboard or `hermes kanban tail <id>` to follow along.

## Common patterns

**Fan-out + fan-in (research → synthesize):** N research-style cards with no parents, one synthesis card with all of them as parents.

**Parallel implementation + validation:** one implementer card makes the change while one explorer/researcher card verifies config, docs, or source mapping. A reviewer card can depend on both. Do not make the implementer own unrelated verification just because the user mentioned both in one sentence.

**Pipeline with gates:** `planner → implementer → reviewer`. Each stage's `parents=[previous_task]`. Reviewer blocks or completes; if reviewer blocks, the operator unblocks with feedback and respawns.

**Same-profile queue:** N tasks, all assigned to the same profile, no dependencies between them. Dispatcher serializes — that profile processes them in priority order, accumulating experience in its own memory.

**Human-in-the-loop:** Any task can `kanban_block()` to wait for input. Dispatcher respawns after `/unblock`. The comment thread carries the full context.

## Pitfalls

**Inventing profile names that don't exist.** The dispatcher silently fails to spawn unknown assignees — the card just sits in `ready` forever. Always assign to a profile from your Step 0 discovery; ask the user if you're unsure.

**Bundling independent lanes into one card.** If the user asks for two independent outcomes, create two cards. Example: "fix blockers and check model variants" is not one fixer task; create a fixer/engineer card for the fixes and an explorer/researcher card for the variant check, then optionally gate review on both.

**Over-linking because of wording.** "Finally check X" may still be parallel with implementation if X is static config, docs, or source discovery. Link it after implementation only when the check depends on the implementation result.

**Forgetting dependency links.** If the task graph says `research -> implement -> review`, do not create all tasks as independent ready cards. Use parent links so implement/review cannot run before their inputs exist.

**Reassignment vs. new task.** If a reviewer blocks with "needs changes," create a NEW task linked from the reviewer's task — don't re-run the same task with a stern look. The new task is assigned to the original implementer profile.

**Argument order for links.** `kanban_link(parent_id=..., child_id=...)` — parent first. Mixing them up demotes the wrong task to `todo`.

**Don't pre-create the whole graph if the shape depends on intermediate findings.** If T3's structure depends on what T1 and T2 find, let T3 exist as a "synthesize findings" task whose own first step is to read parent handoffs and plan the rest. Orchestrators can spawn orchestrators.

**Tenant inheritance.** If `HERMES_TENANT` is set in your env, pass `tenant=os.environ.get("HERMES_TENANT")` on every `kanban_create` call so child tasks stay in the same namespace.

**Dual-kanban-DB mismatch (Drewgent-specific).** On Drewgent's setup there are TWO separate kanban databases:
- **Hermes native kanban** at `HERMES_HOME/kanban.db` (~/.drewgent/kanban.db) — used by the `kanban_*` tools.
- **Drewgent legacy kanban** at `~/.drewgent/P2-hippocampus/kanban/state/drewgent_tasks.db` — used by the old `dispatch_once_*` scripts in `cron_runner.py`.

Tasks created via `kanban_create` go into the Hermes native DB. The legacy `dispatch_once_*` scripts check the legacy DB. This means tasks can sit in "ready" forever — the dispatcher is checking the wrong database.

**Fix:** Replace the `dispatch_once_*` scripts with `hermes kanban dispatch` (the native Hermes CLI command). This reads from the correct DB, handles claim locks, worker spawning, and failure detection. Test with `hermes kanban dispatch --dry-run --json`.

## Provenance Convention — record why each task exists

Every `kanban_create` call should include the **trigger/context** that motivated the task. This turns kanban from a flat todo list into a traceable decision log.

### Task body must include:

```markdown
## Origin
- Trigger: [what problem or request spawned this task]
- Session: [YYYY-MM-DD topic or session id]
- Decision rationale: [why this approach, not alternatives]
```

### When to add provenance

- **Every top-level task** created from a user request or discussion
- **Decomposed subtasks** should inherit the parent's origin and add their lane-specific rationale
- Omit only for trivial self-evident tasks (typo fix, routine maintenance) where the trigger is obvious from the title

### Why

From the "30x AI Engineer with Taste" framework: **a prompt is more informative than the output.** When reviewing a completed task months later, the provenance tells you *why* it was done, not just *what* was done. This is the kanban equivalent of OpenAI's "require the prompt alongside the PR" policy.

---

## Leverage Score — prioritize by force multiplication

Include a leverage assessment in every non-trivial task body. The question: *"If this task is solved well, how many other problems disappear?"*

### Task body

```markdown
## Leverage Assessment
- 이 작업 해결 시 자동 해결되는 문제:
  1. ...
  2. ...
- Leverage Score (1-5): N
- 근거: why this score
```

### Completion metadata

```python
kanban_complete(
    metadata={
        "leverage_score": 4,
        "problems_eliminated": ["problem A", "problem B"],
        "taste_decision": "brief rationale for the approach taken",
        # ... existing metadata
    },
)
```

### Score table

| Score | Meaning | Example |
|-------|---------|---------|
| 5 | Root cause, eliminates entire class | Architecture change removes whole module |
| 4 | Solves multiple sub-problems at once | Shared utility extracted, N duplicates removed |
| 3 | Clear improvement + 1-2 side effects | Config cleanup eliminates manual step |
| 2 | Local improvement, no ripple | Bug fix |
| 1 | Surface change, minimal impact | Typo, docs update, single-line refactor |

### When to skip

- Leverage 1 tasks (typos, trivial updates) — the score is implicit, don't waste lines
- Routine recurring maintenance where the leverage is obvious

---

## Agent Profiles — reusable subagent role definitions

Drewgent supports a **static agent profile system** at `~/.drewgent/agents/<name>.md`. These profiles define reusable subagent roles — model, provider, instructions, and tool constraints — in a single file, then referenced by name when spawning work.

### delegate_task integration (built-in)

The `delegate_task` tool now has a built-in `agent_profile` parameter. When set, the tool reads `$HERMES_HOME/agents/<name>.md`, overrides the subagent's model/provider/toolsets from the profile, and prepends the profile's instructions to the subagent's context:

```python
delegate_task(
    agent_profile="reviewer",
    goal="Review PR #42 for security issues",
)
```

The integration lives in `tools/delegate_tool.py` — function `_resolve_agent_profile()`. No YAML parsing library needed; uses stdlib regex for frontmatter.

### Profile format

Each profile is a Markdown file with YAML frontmatter:

```markdown
---
name: reviewer
description: Reviews code against project conventions. Does NOT make changes.
model: qwen3.7-max
provider: opencode-go
toolsets: [terminal, file, search]
created: 2026-06-13
---

# Reviewer

You are a code review agent. ...
```

### Frontmatter fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | yes | Profile identifier, matches assignee or agent_profile reference |
| `description` | yes | One-liner for discovery and auto-matching |
| `model` | yes | Model ID (e.g. `deepseek-v4-flash`, `qwen3.7-max`) |
| `provider` | yes | Hermes provider slug (e.g. `opencode-go`) |
| `toolsets` | no | Toolset whitelist, e.g. `[terminal, file, search]` |
| `instructions` | yes | Full role definition in the Markdown body |

### Using profiles with kanban tasks

The profile's **instructions** and **model** should be embedded directly in the kanban task body so the dispatched worker has self-contained context:

```python
kanban_create(
    title="review PR #42",
    assignee="<dispatcher-profile>",
    skills=["kanban-worker"],
    body=f"""
    ## Agent Profile: reviewer
    Model: qwen3.7-max | Provider: opencode-go

    You are a code review agent. ...
    """,
)
```

The `.md` file is the **canonical reference** — update it when the role definition changes, and all future tasks that copy from it stay consistent.

### Cost-Aware Model Tiers

All models run through OpenCode Go ($10/mo subscription — marginal cost = $0). Tier determines capability, latency, and rate-limit impact:

| Tier | Model | Profiles | Latency | Use Case |
|------|-------|----------|---------|----------|
| **Flash** | `deepseek-v4-flash` | explorer, implementer, tester, archiver | Fastest | Read-only analysis, simple impl, tests, docs |
| **Pro** | `deepseek-v4-pro` | reviewer | Moderate | General code review |
| **Max** | `qwen3.7-max` | planner, reviewer-critical, security-reviewer | Slowest | Planning, critical review, security audit |

### ESCALATE mechanism

Flash-tier profiles contain an **ESCALATE signal** in their instructions. When the model determines the task requires stronger reasoning than it can provide, it responds with:

```
ESCALATE: <reason>
```

And stops. The caller detects this pattern and re-routes to a Max-tier model.

### Current profiles (8 roles)

```
~/.drewgent/agents/
├── README.md
├── explorer.md              flash  읽기 전용 분석 (ESCALATE 가능)
├── implementer.md           flash  구현 (ESCALATE 가능)
├── tester.md                flash  테스트 (ESCALATE 가능)
├── archiver.md              flash  문서화/기록
├── reviewer.md              pro    일반 코드 리뷰
├── reviewer-critical.md     max    중요 변경 심층 리뷰
├── security-reviewer.md     max    보안 감사 (OWASP, crypto, auth)
└── planner.md               max    태스크 분해/계획 (Tier 결정 포함)
```

### Pipeline (cost-aware, 3-tier)

Not all tasks need the full pipeline. The planner determines the complexity tier, then adapts:

**Tier 1 (단순)** — typo fix, trivial rename:
  `Implementer(flash) → Archiver(flash)`

**Tier 2 (보통)** — new function, moderate change:
  `Explorer(flash) → Implementer(flash) ↔ Tester(flash) [≤2회 loop] → Archiver(flash)`

**Tier 3 (복잡)** — architecture change, cross-cutting:
  `Planner(max) → Explorer(flash) → Implementer(flash) ↔ Tester(flash) [≤3회 loop]`
  `→ Reviewer(pro)`
  `→ [security/auth/payment labels?] → Security-reviewer(max)`
  `→ [critical/large label?] → Reviewer-critical(max)`
  `→ Archiver(flash)`

Implementer↔tester loop: tester fails → report to implementer → retry (max 2-3 attempts). After that, failure propagates up for human intervention.

### Using agent profiles with delegate_task

Pre-defined subagent profiles live at `~/.drewgent/agents/*.md` and are loaded via:

```
delegate_task(agent_profile="reviewer", goal="review this PR")
```

The `agent_profile` parameter is **baked into the delegate_task tool schema** — every agent sees it as an option in every session. No skills or memory needed to discover it; the tool description documents it.

| Profile | File | Model | Role |
|---------|------|-------|------|
| planner | `agents/planner.md` | qwen3.7-max | Task decomposition + tier assignment |
| explorer | `agents/explorer.md` | deepseek-v4-flash | Read-only codebase analysis |
| implementer | `agents/implementer.md` | deepseek-v4-flash | Code implementation |
| tester | `agents/tester.md` | deepseek-v4-flash | Test writing + verification |
| reviewer | `agents/reviewer.md` | deepseek-v4-pro | General code review |
| reviewer-critical | `agents/reviewer-critical.md` | qwen3.7-max | In-depth review for large/architectural changes |
| security-reviewer | `agents/security-reviewer.md` | qwen3.7-max | Security audit |
| archiver | `agents/archiver.md` | deepseek-v4-flash | Documentation, changelog, summary |

Each profile sets model, provider, toolsets, and instructions. The caller's explicit parameters (goal, context, toolsets) override profile defaults. Some profiles (explorer, implementer, tester) can emit `ESCALATE: <reason>` to signal the task needs a stronger model.

**Pipeline pattern in kanban workers:**

```python
delegate_task(tasks=[
    {"goal": "analyze current auth code", "agent_profile": "explorer"},
    {"goal": "implement login validation", "agent_profile": "implementer"},
    {"goal": "write tests for login", "agent_profile": "tester"},
])
```

The profile system lives at `$HERMES_HOME/agents/`. For drewgent this is `~/.drewgent/agents/`. Add new profiles by dropping a `.md` file there.

### Pipeline auto-decomposition via `kanban_create`

The `kanban_create` tool now supports a `pipeline` parameter that automatically creates sequential child tasks:

```
kanban_create(
    title="Add login validation",
    pipeline=["explorer", "implementer", "tester", "reviewer", "archiver"],
    body="...",
)
```

This creates 5 tasks in dependency order:
- `explorer: Add login validation` (no deps) → ready immediately
- `implementer: Add login validation` (depends on explorer) → promotes when explorer done
- `tester: Add login validation` (depends on implementer)
- `reviewer: Add login validation` (depends on tester)
- `archiver: Add login validation` (depends on reviewer)

Each task has `skills=[stage_name]` so the dispatched worker loads the corresponding agent profile. The `assignee` is set automatically per stage (no need to pass `assignee` with pipeline).

The `pipeline` parameter is documented in the `kanban_create` tool schema — every orchestrator agent sees it as an option.

## Linear Bridge (hook-based — PAUSED 2026-06-14)

**Status: PAUSED.** The kanban-linear sync cron job was paused on 2026-06-14 after two bugs were found in the sync script. Linear is under retirement evaluation (possible Huly migration).

### Bugs found (fixed in script, cron paused)

1. **Wrong default kanban DB path**: the script defaulted to `~/.hermes/kanban/boards.db` (doesn't exist). Actual DB is at `HERMES_HOME/kanban.db` (usually `~/.drewgent/kanban.db`).
2. **Prune query type error**: `$co:DateTime!` should be `$co:DateTimeOrDuration!` for the Linear GraphQL API. Caused silent HTTP 400 errors (script caught and swallowed them, exiting 0).

### When it was active

- **Event-driven**: fires immediately on `kanban_complete`, no polling
- **Scope**: only syncs tasks needing human visibility (review-required, blocked, critical)
- **Cron backup**: every 2h for prune + feedback label check
- **Archive**: issues completed >7d auto-archived
- **Limit**: 250 issue free tier, safety margin at 200

The hook script: `~/.hermes/agent-hooks/kanban-linear-sync.py`
(The Drewgent copy at `~/.drewgent/scripts/kanban_linear_sync.py` has both fixes applied.)

If Linear is re-enabled, unpause the cron job `02e28cd0a6aa`.

---

## Loop Engineering — assessment framework

The loop engineering framework (from [addyo's essay](https://addyo.substack.com/p/loop-engineering)) defines 5 building blocks + 1 memory store for autonomous agent systems. Use this as a vocabulary and checklist when evaluating or designing multi-agent workflows.

### The six components

| # | Component | Kanban equivalent | Drewgent status |
|---|-----------|-------------------|-----------------|
| 1 | **Automations** — scheduled discovery and triage | Cron jobs, kanban dispatcher | ✅ Strong |
| 2 | **Worktrees** — parallel file isolation | `workspace_kind: worktree` in kanban_create | ⚠️ Adequate, not default |
| 3 | **Skills** — written project knowledge | SKILL.md system (100+ skills) | ✅ Excellent |
| 4 | **Connectors/Plugins** — MCP, real tool integration | MCP client, hooks, plugins | ✅ Strong |
| 5 | **Sub-agents** — maker/checker split | delegate_task + kanban profiles | ✅ Strong, profile system new |
| 6 | **Memory** — durable external state | Kanban board + vault + MEMORY.md | ✅ Excellent |

### Key principles for kanban orchestration

1. **Maker/checker split.** The agent that writes code should NOT be the one that reviews it. Use separate kanban tasks or subagents with different models (e.g. implementer=deepseek-v4-pro, reviewer=qwen3.7-max). A separate small model should judge completion, not the worker.

2. **State on disk, not in context.** The kanban board SQLite is the durable spine. The agent forgets between runs; the board doesn't. Every `kanban_complete` writes immutable state.

3. **Comprehension debt awareness.** The faster the loop ships code you didn't write, the bigger the gap between what exists and what you understand. Every kanban task should produce a handoff that the human can review (summary + metadata + provenance).

4. **Cognitive surrender risk.** Designing the loop is the cure when done with judgement, and the accelerant when done to avoid thinking. Same action, opposite result. Always route with intent, not habit.

### Drewgent design principles (user preferences, established 2026-06-13)

When designing task graphs, pipelines, or multi-agent flows:

- **Event-driven over polling.** Hooks on kanban_complete > cron. Cron only for periodic maintenance (prune, cleanup).
- **Cost-aware routing.** Saturate fixed-cost infra (OpenCode Go $10/mo) before per-call billing (MiniMax Token Plan). Model tiers (Flash/Pro/Max) match capability to complexity.
- **Automated maintenance.** Self-cleaning defaults (7-day archive, auto-prune). If always needed, build into the flow.
- **Gap analysis before commit.** Ask the question (are there gaps?). Common gaps: tier decision, retry loops, escalation (ESCALATE signal), security gate.
- **Pipeline cost varies by complexity.** Tier 1 = 2 stages, Tier 3 = full pipeline with security gate.


### Applying the framework

When designing a kanban task graph, ask:

See `references/loop-engineering-assessment.md` for the full Drewgent assessment against this framework.
- Which of these 6 components does this workflow rely on?
- Where is the maker/checker split?
- What happens if this runs unattended for 24 hours?
- Can I walk away and trust the verifier?

---

## Goal-mode cards (persistent workers)

By default a dispatched worker gets **one shot** at its card: it does its work, calls `kanban_complete`/`kanban_block`, and exits. For open-ended cards where one turn rarely finishes the job, pass `goal_mode=True` to wrap that worker in a Ralph-style goal loop — the same engine behind the `/goal` slash command:

```python
kanban_create(
    title="Translate the full docs site to French",
    body="Acceptance: every page translated, no English left, links intact.",
    assignee="<translator-profile>",
    goal_mode=True,        # judge re-checks the card after each turn
    goal_max_turns=15,     # optional budget (default 20)
)["task_id"]
```

How it behaves:
- After each worker turn, an auxiliary judge evaluates the worker's response against the card's **title + body** (treated as the acceptance criteria).
- Not done + budget remains → the worker keeps going **in the same session** (full context retained — not a fresh respawn).
- Worker calls `kanban_complete`/`kanban_block` itself → loop stops, normal lifecycle.
- Budget exhausted without completion → the card is **blocked** for human review (sticky), never a silent exit.

When to use it: long, multi-step, or "keep going until X is true" cards. When NOT to: cheap one-shot cards (translation of a single string, a quick lookup) — the judge overhead isn't worth it, and the dispatcher's existing retry/circuit-breaker already handles transient worker failures.

Write the body as **explicit acceptance criteria** — the judge is only as good as the goal text. "Translate the README" is weaker than "Translate every section of the README to French; no English sentences remain."

## Recovering stuck workers

When a worker profile keeps crashing, hallucinating, or getting blocked by its own mistakes (usually: wrong model, missing skill, broken credential), the kanban dashboard flags the task with a ⚠ badge and opens a **Recovery** section in the drawer. Three primary actions:

1. **Reclaim** (or `hermes kanban reclaim <task_id>`) — abort the running worker immediately and reset the task to `ready`. The existing claim TTL is ~15 min; this is the fast path out.
2. **Reassign** (or `hermes kanban reassign <task_id> <new-profile> --reclaim`) — switch the task to a different profile (one that exists on this setup) and let the dispatcher pick it up with a fresh worker.
3. **Change profile model** — the dashboard prints a copy-paste hint for `hermes -p <profile> model` since profile config lives on disk; edit it in a terminal, then Reclaim to retry with the new model.

Hallucination warnings appear on tasks where a worker's `kanban_complete(created_cards=[...])` claim included card ids that don't exist or weren't created by the worker's profile (the gate blocks the completion), or where the free-form summary references `t_<hex>` ids that don't resolve (advisory prose scan, non-blocking). Both produce audit events that persist even after recovery actions — the trail stays for debugging.

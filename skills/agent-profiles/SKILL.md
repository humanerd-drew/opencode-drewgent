---
name: agent-profiles
description: Authoring and using agent profiles — pre-defined subagent roles that set model, provider, toolsets, and instructions in one task() call. Covers profile format, the 14 standard roles, pipeline patterns, cost-tiered model assignment, and the ESCALATE mechanism for capability routing.
category: autonomous-ai-agents
created: 2026-06-13
  session: "2026-06-13 model-routing-and-loop-engineering"
  decision: "Profiles as .md files with YAML frontmatter (same convention as SKILL.md) for consistency. Flash-tier as default workhorse, pro/max for quality-critical steps."
tags: [agent, subagent, profile, routing, delegation, pipeline]
links:
  - "[[skills/devops/kanban-orchestrator]]"
  - "[[skills/devops/kanban-worker]]"
  - "[[@identity/brain/rules]]"
---

# Agent Profiles

Agent profiles are pre-defined subagent roles loaded by `task(subagent_type="<name>", description="summary", prompt="...")`. Each profile sets model, provider, toolsets, and system instructions in one call.

## Location

Profiles live at `$HERMES_HOME/agents/*.md`. For Drewgent: `~/.drewgent/agents/`.

## Format

Each profile is a Markdown file with YAML frontmatter and markdown body:

```markdown
---
name: profile-name
description: >
  Brief description of this profile's purpose.
model: deepseek-v4-flash
provider: opencode-go
toolsets: [terminal, file, search]
created: YYYY-MM-DD
---

# Profile Name

You are a [role definition]. Your job is to...

## Rules

- Specific constraints (read-only, write-only, review-only, etc.)

## Escalation

When creating new autonomous capabilities, **prefer assigning a single agent profile over building a multi-stage pipeline.**

| Approach | When | Why |
|----------|------|-----|
| **Profile-first** | Agent acts autonomously (observe → decide → act) | Simpler, faster to iterate, one agent owns the full cycle |
| **Pipeline-first** | Multi-stage processing with distinct roles | Necessary when stages need different models/tools or parallel execution |

**Origin:** The CMO agent (content-manager) started as a 5-stage pipeline design. The user corrected it: "워크플로우 만들어두고 에이전트 배정하고 기록 뒤져서 바로 만들어볼 수 있지 않겠니." The simpler approach won — one agent profile + cron scheduling + one narrative tracking file. Pipelines add accidental complexity. Start with a profile; split into stages only when there's a clear reason.

## The 8 Standard Profiles

### Flash Tier ($0 marginal cost — OpenCode Go subscription)

| Profile | Model | Role | ESCALATE? |
|---------|-------|------|-----------|
| **explorer** | deepseek-v4-flash | Read-only codebase analysis, context gathering | ✅ |
| **implementer** | deepseek-v4-flash | Code implementation, file creation | ✅ |
| **tester** | deepseek-v4-flash | Test writing + verification | ✅ |
| **archiver** | deepseek-v4-flash | Documentation, changelog, completion summary | ❌ |

### Pro/Max Tier (stronger models, selective use)\n\n| Profile | Model | Role |\n|---------|-------|------|\n| **content-manager** | deepseek-v4-pro | CMO agent — observes work, produces multi-format content (blog + SVG cover + X thread + Excalidraw PNG), tracks narrative arc. Runs daily via cron, delivers to Discord. |\n| **reviewer** | deepseek-v4-pro | General code review (logic, style, edge cases) |\n| **reviewer-critical** | qwen3.7-max | In-depth review for large/architectural changes |\n| **security-reviewer** | qwen3.7-max | Security audit (auth, crypto, injection, secrets) |\n| **planner** | qwen3.7-max | Task decomposition, tier assignment, pipeline design |

## Pipeline Pattern

Sequential multi-stage workflows use individual `task()` calls:

```python
task(
    subagent_type="explorer",
    description="Analyze auth code",
    prompt="analyze the existing auth code"
)
task(
    subagent_type="implementer",
    description="Implement login validation",
    prompt="implement login validation"
)
task(
    subagent_type="tester",
    description="Write tests",
    prompt="write tests for login"
)
task(
    subagent_type="reviewer",
    description="Review auth changes",
    prompt="review the auth changes"
)
```

Or via kanban pipeline automation:
```python
kanban_create(
    title="Add login validation",
    pipeline=["explorer", "implementer", "tester", "reviewer", "archiver"],
    body="...",
)
```

## Tiered Pipeline by Complexity

**Tier 1 (trivial):** `Implementer(flash) → Archiver(flash)` — typo fix, rename
**Tier 2 (moderate):** `Explorer(flash) → Implementer(flash) ↔ Tester(flash) [≤2 loops] → Archiver(flash)`
**Tier 3 (complex):** `Planner(max) → Explorer(flash) → Implementer(flash) ↔ Tester(flash) [≤3 loops] → Reviewer(pro) → [security?] → Security-reviewer(max) → [critical?] → Reviewer-critical(max) → Archiver(flash)`

## Design Principles

**1. Never assume provider topology.** The user may route through any provider (OpenCode Go, OpenRouter, MiniMax direct, etc.). Always verify the actual config before designing routing strategy.

**2. Cost awareness first, capability second.** Every model assignment must consider:
   - **Marginal cost** — OpenCode Go subscription = $0 per call. Use it maximally.
   - **Latency cost** — flash models respond faster than pro/max. Interactive UX demands speed.
   - **Quality cost** — wrong model for the task produces bad output = rework.
   - **Rate limit cost** — heavy models on subscription plans can hit fair-use caps.
   
   When user asks "does this make sense?" about routing, explicitly enumerate cost dimensions. They expect this analysis unprompted.

**3. Tier by complexity, not by default.** Not every task needs a 6-stage pipeline:
   - Tier 1 (trivial): 2 flash profiles. No review.
   - Tier 2 (moderate): 3-4 flash profiles. Minimal review.
   - Tier 3 (complex): Planner(max) + full pipeline with pro/max review gates.

## Cost Awareness

- All flash-tier profiles cost $0 marginal (OpenCode Go $10/month subscription).
- Pro/max profiles consume the same subscription but are slower — use only for quality-critical steps.
- The `ESCALATE` mechanism prevents flash models from struggling silently: they signal "too complex" and a stronger model takes over.

## Adding New Profiles

1. Create `$HERMES_HOME/agents/<name>.md`
2. Add YAML frontmatter with model, provider, toolsets
3. Write instructions in the body
4. The profile is immediately available via `task(subagent_type="<name>", description="...", prompt="...")`
5. Update the table in the kanban-orchestrator skill if it's a reusable role

## Technical Integration

The `subagent_type` parameter is **baked into the `task` tool schema**. Every agent in every session sees it as an option. Resolution logic:
1. Profile file is read from `~/.config/opencode/agents/<name>.md`
2. Frontmatter model/provider override delegation config
3. Profile toolsets used as default (caller's explicit toolsets win)
4. Profile instructions prepended to caller's context

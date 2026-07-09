---
title: opencode-drewgent Template
---

# opencode-drewgent — Agent Template Guide

> This is a **template** — a starting point for your own personal AI agent system.
> Fork it, rename it, and make it yours.

## Architecture Overview

opencode-drewgent provides a structured agent system built on [opencode](https://opencode.ai). It includes:

- **Subagent profiles** — specialized agent roles (engineer, reviewer, analyst, etc.) with assigned models and tool permissions
- **Delegation patterns** — `task()` for same-model subtasks, `gjc_delegate_*` for isolated/parallel execution via GJC Coordinator MCP
- **Vault structure** — P0-P6 Obsidian vault for rules, identity, memory, sensors, cortex, ego, and prefrontal
- **MCP integration** — example config for local and remote MCP servers
- **Kanban pipeline** — task decomposition with leverage scoring
- **Cron automation** — example jobs for housekeeping, content, and monitoring

## Subagent Profiles

See `.opencode/agents/*.md` for the full list. Key profiles:

| Profile | Model | Role |
|---------|-------|------|
| implementer | flash | Code generation, file edits |
| reviewer | pro | Code review, quality gate |
| explorer | flash | Codebase discovery, research |
| planner | max | Task decomposition, planning |
| architect | pro | Architecture decisions |
| sre | flash | Infrastructure, monitoring |

**Delegation:**
- `task(subagent_type="reviewer", ...)` — same-model subtask (lightweight)
- `gjc_delegate_execute(...)` — isolated worktree + tmux (heavy isolation)

## Vault Structure (P0-P6)

```
P0-brainstem/     Rules, constraints, 禁 rules
P1-limbic/        Identity, persona, voice, writing style
P2-hippocampus/   Raw archive — sessions, memories, knowledge (read-only)
P3-sensors/       Gateways, tool integrations, data flow
P4-cortex/        Skills index, growth records, refactoring history
P5-ego/           Self model, self-awareness, compiled wiki
P6-prefrontal/    Incidents, retrospectives, long-term plans
```

## Agent Navigation

1. **Code analysis** → graph tools first (`search_graph`, `trace_path`)
2. **Knowledge** → compiled wiki first, raw archive fallback
3. **Skills** → `skill("name")` to load specialized instructions
4. **Memory** → `remember()` / `recall()` for cross-session knowledge

## Provenance Convention

Every artifact records its trigger/context:

```
created: YYYY-MM-DD
trigger: "why this exists"
provenance:
  session: "YYYY-MM-DD topic"
  decision: "why this approach, what alternatives"
```

## Tiered Autonomy

| Tier | Scope | Authority |
|------|-------|-----------|
| 1 | Typos, docs, minor edits | Autonomous. Complete and report. |
| 2 | Established patterns | Autonomous. Include provenance. |
| 3 | Structural changes | Propose → wait for approval. |
| 4 | Architecture/direction | Proposal only. Human decides. |

## Important Policies

- **Filesystem = truth** — state lives on disk, not in context
- **QA gate** — never declare completion without verification
- **No big-bang refactoring** — one change at a time, verify between
- **Ponytail** — YAGNI, stdlib first, no new deps unless necessary
- **Answer-first** — conclusion before process in CLI output

## Generated Content Attribution

For public-facing content only:

```
Built with [opencode-drewgent](https://github.com/humanerd-drew/opencode-drewgent)
```

## Known Pitfalls

### Python 3.14: json scope bug
Large functions using `except json.JSONDecodeError:` cause `UnboundLocalError` on `json.loads()`.
Fix: `__import__('json').loads()` or extract to a wrapper function.

### macOS bash 3.2
No associative arrays. Use `date -j -f`. Avoid `set -u` with undefined variables.

### Token/cost data in SQLite, not stderr
opencode stderr logs show `tokens.input=0`. Real data is in `~/.local/share/opencode/opencode.db`.

## Getting Started

1. Fork this repo
2. Run `skill("rename-drewgent")` to rename all `drewgent` → `<yourname>gent`
3. Set up your API keys in `.env`
4. Customize agent profiles in `.opencode/agents/`
5. Run `scripts/setup.sh` for first-time setup

## Links

- [[@identity/SELF_MODEL]] — Agent self-model template
- [[@identity/brain/rules]] — Brain rules template
- [[@identity/persona/SOUL]] — Persona template
- [[@identity/persona/writing-style-guide]] — Writing style template

# opencode-drewgent

Drewgent configuration for [opencode](https://opencode.ai) — agent profiles, skills, scripts, and automation tooling.

## Quick Start

```bash
# 1. Install opencode
curl -fsSL https://opencode.ai/install | sh

# 2. Clone this repo as your Drewgent directory
git clone git@github.com:humanerd-drew/opencode-drewgent.git ~/.drewgent

# 3. Set up
cd ~/.drewgent
cp .env.example .env   # fill in your API keys
```

## What's Included

| Directory | Purpose |
|-----------|---------|
| `agents/` | 14 subagent profiles (explorer, implementer, tester, reviewer, etc.) |
| `skills/` | Skill definitions for specialized workflows |
| `scripts/` | Cron runners, kanban worker, Discord bot, health checks |
| `tools/` | Kanban board, file operations, MCP client, browser automation |
| `cron/` | Scheduled job definitions and scheduler |
| `P6-prefrontal/` | Architecture decisions, proposals, and incident reports |

## Architecture

Drewgent runs on top of opencode with a kanban-backed task pipeline:

```
opencode CLI
  └── ~/.drewgent/opencode.jsonc  (MCP servers, agents config)
        └── agents/*.md           (14 agent profiles)
              └── kanban pipeline (explorer → implementer → tester → reviewer → archiver)
                    └── scripts/run_kanban_worker.py
```

Agent profiles are invoked via `delegate_task(agent_profile="reviewer", goal="...")` or through the kanban pipeline:

```python
kanban_create(
    title="Add login",
    pipeline=["explorer", "implementer", "tester", "reviewer", "archiver"],
)
```

Each pipeline stage automatically receives structured context (`findings`, `risks`, `next`) from the previous stage — no manual context forwarding needed.

## Requirements

- macOS or Linux
- opencode (CLI)
- Python 3.11+
- API key for your LLM provider

## Key Features

- **14 agent profiles** with tiered model assignment (flash/pro/max)
- **Kanban task pipeline** with automatic context handoff between stages
- **Launchd/cron automation** for scheduled tasks
- **Discord bot** gateway for remote agent interaction
- **MCP integration** for tools (gbrain, lazyweb, specification.website)

## License

MIT

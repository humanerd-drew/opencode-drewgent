# Session: 2026-06-13 — Agent Profile System Build

## Context

Built the full agent profile system in a single session: 8 profiles, delegate_task
agent_profile parameter, kanban pipeline parameter, Linear MCP + sync cron.

## Key Decisions

### Cost-Aware Tier Assignment

| Profile | Originally Proposed | Final (Cost-Aware) | Reason |
|---------|-------------------|-------------------|--------|
| implementer | deepseek-v4-pro | deepseek-v4-flash | Flash sufficient for most implementations. ESCALATE for hard cases. |
| reviewer | qwen3.7-max | deepseek-v4-pro | Pro sufficient for general review. Max reserved for critical changes. |
| reviewer-critical | (new) | qwen3.7-max | New profile for large/important changes needing deeper analysis. |
| security-reviewer | (new) | qwen3.7-max | New profile. Security audit needs best reasoning. |

### Pipeline Tier Decision

Agent should NOT self-assess tier on every call (always picks safest = most expensive).
Instead, kanban task body has implicit tiering by pipeline length:
- Tier 1: just implementer + archiver
- Tier 2: explorer + implementer + tester + archiver
- Tier 3: planner + explorer + implementer + tester + pro/max reviewer + archiver

### ESCALATE Mechanism

Flash profiles (explorer, implementer, tester) can emit `ESCALATE: <reason>`.
The caller must detect this and re-route to a stronger model. Critically:
ESCALATE without handler = silent failure. Pipeline orchestrators should
include ESCALATE detection between stages.

### Profile System Integration Points

- `delegate_tool.py` — agent_profile parameter, file loader, merge logic
- `kanban_tools.py` — pipeline parameter, auto-decomposition into child tasks
- `devops/kanban-orchestrator` skill — full pipeline+profile documentation
- `devops/kanban-worker` skill — brief profile reference
- `config.yaml` — delegation/auxiliary sections set OpenCode Go as default provider

# opencode-loragent

Loragent configuration for [opencode](https://opencode.ai) — agent profiles, skills, kanban task pipeline, and automation tooling designed for autonomous software engineering.

This is **not** a standalone agent framework. It's the configuration and extension layer that sits on top of opencode, providing:

- 14 specialized agent profiles with role-based model assignment
- Kanban-backed multi-agent task pipeline with automatic context handoff
- 100+ skills for domain-specific workflows
- Launchd/cron-based background automation
- Discord bot gateway for remote agent interaction
- MCP server integrations (gbrain, lazyweb, specification.website)

## Quick Start

```bash
# 1. Install opencode
curl -fsSL https://opencode.ai/install | sh

# 2. Clone this repo as your Loragent directory
git clone git@github.com:humanerd-drew/opencode-loragent.git ~/.loragent

# 3. Configure API keys
cd ~/.loragent
cp .env.example .env
# Edit .env with your LLM provider API keys

# 4. Start using opencode with Loragent configuration
opencode
```

### Requirements

- **macOS** or **Linux**
- **opencode** CLI (v1.x+)
- **Python** 3.11+
- **API key** for your LLM provider (OpenRouter, MiniMax, etc.)

## Architecture

### Overview

```
opencode CLI session
  ├── opencode.jsonc          (MCP servers, skill paths, model config)
  ├── AGENTS.md               (system instructions — loaded by opencode)
  ├── agents/*.md             (14 subagent profiles for delegate_task)
  ├── skills/                 (domain-specific skill definitions)
  ├── tools/                  (tool implementations: kanban, file ops, etc.)
  └── cron/jobs.json          (scheduled background jobs)
        └── scripts/
              ├── run_kanban_worker.py    (kanban task executor)
              ├── loragent_cron.py        (60s cron dispatcher via launchd)
              ├── discord_bot.py          (Discord ↔ opencode gateway)
              └── ...
```

### Multi-Agent Pipeline

Loragent's core workflow is a kanban-backed pipeline where each stage is handled by a specialized agent profile. The pipeline automatically manages dependencies, context handoff, and failure recovery:

```python
kanban_create(
    title="Add login validation",
    pipeline=["explorer", "implementer", "tester", "reviewer", "archiver"],
)
```

This creates 5 sequential tasks with dependency ordering:

```
explorer → implementer → tester → reviewer → archiver
   │            │            │         │          │
   │  findings  │  changes   │  test   │  review  │  docs
   └────────────┘────────────┘─────────┘──────────┘
              ↓ Each stage auto-receives structured context
         Context from previous step:
           **Findings:** auth code in src/auth/*.ts
           **Risks:** no refresh token rotation
           **Next:** implement token refresh
```

**Key properties:**
- **Automatic context handoff**: Each stage receives `findings`, `risks`, and `next` from the previous stage as structured JSON — no manual context forwarding
- **Failure tracking**: Unparseable handoffs are logged as `handoff_failed` events and visually marked in the prompt
- **Fan-in support**: Tasks can have multiple parents; context from all parents is merged

### Complexity Tiers

Not every task needs the full pipeline. The orchestrator adapts based on tier:

| Tier | Pipeline | Use Case |
|------|----------|----------|
| **1** (simple) | Implementer → Archiver | Typo fix, config change, trivial rename |
| **2** (moderate) | Explorer → Implementer ↔ Tester → Archiver | New function, moderate feature |
| **3** (complex) | Planner → Explorer → Implementer ↔ Tester → Reviewer → Security → Archiver | Architecture change, cross-cutting, auth |

## Agent Profiles

14 specialized subagent roles, each with a specific model, toolset, and instructions. Invoked via `delegate_task(agent_profile="<name>", goal="...")`.

### Flash Tier ($0 marginal cost — OpenCode Go subscription)

| Profile | Model | Role |
|---------|-------|------|
| **explorer** | deepseek-v4-flash | Read-only codebase analysis, context gathering |
| **implementer** | deepseek-v4-flash | Code implementation, file creation |
| **tester** | deepseek-v4-flash | Test writing and verification |
| **archiver** | deepseek-v4-flash | Documentation, changelog, completion summary |
| **designer** | deepseek-v4-flash | UI/UX mockups, SVG assets, design tokens |
| **sre** | deepseek-v4-flash | Infrastructure, launchd, cron, incident response |

### Pro Tier (stronger reasoning)

| Profile | Model | Role |
|---------|-------|------|
| **reviewer** | deepseek-v4-pro | Code review (logic, edge cases, style) |
| **editor** | deepseek-v4-pro | Content QA, Korean language quality |
| **content-manager** | deepseek-v4-pro | CMO agent — observes work, produces multi-format content |

### Max Tier (deep reasoning)

| Profile | Model | Role |
|---------|-------|------|
| **planner** | qwen3.7-max | Task decomposition, pipeline design |
| **reviewer-critical** | qwen3.7-max | Architecture-level review |
| **security-reviewer** | qwen3.7-max | Security audit (auth, crypto, injection) |
| **orchestrator** | qwen3.7-max | Work decomposition and pipeline orchestration |

### Handoff Contract

Every pipeline-capable profile includes a `## Handoff Contract` section in its instructions. When completing a pipeline task, agents structure their `result` as JSON with three fields:

```python
kanban_complete(
    task_id="t_xxx",
    summary="Human-readable completion summary",
    result=json.dumps({
        "findings": ["What was discovered or produced"],
        "risks": ["Concerns for the next stage"],
        "next": ["Recommended next actions"],
    }),
)
```

- `findings` — discoveries, files changed, decisions made
- `risks` — edge cases, incomplete parts, blocking issues
- `next` — what the next profile should focus on

All fields are optional. If the result is not valid JSON, the system falls back to plain text with a warning.

## Pipeline Stages

| Stage | What it does | Handoff output |
|-------|-------------|----------------|
| **Explorer** | Analyzes codebase, finds patterns, identifies risks | `findings`: file paths, patterns. `risks`: concerns. `next`: implementation recommendations |
| **Implementer** | Writes code, creates patches | `findings`: files changed, approach. `risks`: edge cases. `next`: test focus areas |
| **Tester** | Writes and runs tests | `findings`: test results, bugs found. `risks`: flaky tests. `next`: reviewer attention points |
| **Reviewer** | Reviews code quality and logic | `findings`: issues with severity. `risks`: blocking issues. `next`: APPROVE/CHANGES_REQUESTED |
| **Security** | Security audit | `findings`: vulnerabilities. `risks`: CRITICAL/HIGH. `next`: required fixes |
| **Archiver** | Documents changes | `findings`: docs produced. `risks`: coverage gaps. `next`: future doc needs |

## Directory Structure

```
~/.loragent/
├── opencode.jsonc           # opencode configuration (model, MCP, skill paths)
├── AGENTS.md                # System instructions loaded by opencode
├── agents/                  # 14 subagent profile definitions
│   ├── explorer.md
│   ├── implementer.md
│   ├── tester.md
│   ├── reviewer.md
│   ├── planner.md
│   └── ...
├── skills/                  # 100+ skill definitions
│   ├── ui/
│   │   └── baseline-ui/     # UI quality bar (12 priority tiers)
│   ├── devops/
│   │   ├── kanban-orchestrator/
│   │   └── kanban-worker/
│   ├── software-development/
│   ├── mlops/
│   ├── creative/
│   └── ...
├── scripts/                 # Runtime automation scripts
│   ├── run_kanban_worker.py # Kanban task executor
│   ├── loragent_cron.py     # Cron dispatcher (60s interval)
│   ├── discord_bot.py       # Discord ↔ opencode gateway
│   ├── discord_send.py      # Discord message chunk sender
│   ├── n8n_trigger_runner.py# LLM-generated cron triggers
│   ├── brain_html_dashboard.py  # Agent dashboard generator
│   ├── agent_dashboard_push.py  # Cloudflare dashboard pusher
│   ├── opencode_health_check.py # LLM health monitor
│   ├── cron_trend_harvester.py  # AI trend collection
│   ├── cron_seo_harvester.py    # SEO article collection
│   └── ...
├── tools/                   # Tool implementations
│   ├── kanban_tools.py      # Task queue (create, complete, claim, link)
│   ├── delegate_tool.py     # Subagent delegation (agent_profile support)
│   ├── registry.py          # Tool registration
│   ├── terminal_tool.py     # Terminal execution
│   ├── gbrain_tool.py       # Hybrid search tool
│   └── ...
├── cron/                    # Scheduled job definitions
│   ├── jobs.json            # Job schedule (every 2min, 5min, 6h, daily, etc.)
│   ├── scheduler.py         # Schedule resolver
│   └── jobs.py              # Job data management
├── hooks/
│   └── kanban-notify/       # Kanban completion notification hooks
├── P6-prefrontal/           # Architecture documentation
│   ├── proposals/           # Design proposals (with tier, leverage score)
│   ├── incidents/           # Incident reports and recovery patterns
│   ├── plans/               # Long-term plans
│   └── migrations/          # Architecture migration records
├── .github/workflows/       # CI: tests, Docker publish, docs checks
├── .env.example             # API key configuration template
├── Dockerfile               # Containerized deployment
└── LICENSE                  # MIT
```

## Configuration

### opencode.jsonc

The main configuration file for opencode. Key sections:

```jsonc
{
  // Default model for the main agent
  "model": "opencode-go/deepseek-v4-flash",

  // Skill directories (loaded in order)
  "skills": {
    "paths": [
      "~/.loragent/skills",           // Loragent custom skills
      "~/.config/opencode/skills"     // opencode built-in skills
    ]
  },

  // MCP servers
  "mcp": {
    "gbrain": {
      "command": ["gbrain", "serve"],  // Local PGLite brain
      "enabled": true
    },
    "lazyweb": {
      "type": "remote",                 // UI design reference search
      "url": "https://www.lazyweb.com/mcp",
      "headers": { "Authorization": "Bearer {env:LAZYWEB_API_KEY}" }
    }
  }
}
```

### MCP Servers

| Server | Type | Purpose |
|--------|------|---------|
| **gbrain** | local (stdio) | Hybrid search over personal knowledge base. PGLite-backed vector + keyword search, call graph analysis, entity tracking |
| **lazyweb** | remote (HTTP) | 281k+ real app screenshots for UI design reference. Paywall/pricing/onboarding pattern research |
| **specification-website** | remote (HTTP) | Web spec checklists (SEO, a11y, security, performance). Site audit reference |

## Cron Jobs

Loragent uses a launchd-driven 60-second tick that dispatches `loragent_cron.py`. The scheduler in `cron/jobs.json` defines the job roster:

| Interval | Job | Script |
|----------|-----|--------|
| 2 min | trend-evaluate | n8n_trigger_runner.py |
| 5 min | launchd watchdog, dashboard push | shell / agent_dashboard_push.py |
| 15 min | gbrain watchdog | shell |
| 6 hours | trend-collect, seo-harvester | cron_trend_harvester.py |
| Daily 04:00 | log rotation | shell |
| Daily 06:00 | usage watch | minimax_usage.py |
| Daily 09:00 | harmony check | shell |
| Daily 12:00 | seo-analyze | n8n_trigger_runner.py |
| Daily 20:00 | daily retro | n8n_trigger_runner.py |
| Monthly | trend-retire, seo-trend report | n8n_trigger_runner.py |
| Tue/Fri 10:00 | taste review | n8n_trigger_runner.py |

## Skills

Skills are Markdown files with YAML frontmatter that provide specialized instructions for specific tasks. Loragent includes 100+ skills organized by category:

| Category | Description |
|----------|-------------|
| `ui/` | Baseline UI quality bar, design system conventions |
| `devops/` | Kanban orchestration, cron, deployment, LLM cost audit |
| `software-development/` | Refactoring, code review, payment integration, testing |
| `creative/` | SVG/HTML mockups, infographics (21 layouts × 21 styles), music gen |
| `mlops/` | Axolotl, Unsloth, vLLM, fine-tuning (LoRA/QLoRA/GRPO) |
| `content/` | Content pipeline, WordPress publishing, SEO |
| `brain/` | Memory management, vault health, daily retro |
| `mcp/` | MCP server integration (gbrain, mcporter, native) |

## Discord Integration

Loragent includes a Discord bot gateway (`scripts/discord_bot.py`) that bridges Discord channels to opencode:

- Connects to the opencode daemon via `--attach` mode
- Creates threads for each conversation
- Routes messages to the appropriate agent context
- Supports file attachments and long message chunking

## Related

- [opencode](https://opencode.ai) — The CLI agent platform Loragent runs on
- [gbrain](https://github.com/anomalyco/gbrain) — Local brain server for hybrid search
- [lazyweb](https://lazyweb.com) — UI design reference search

## License

MIT — see [LICENSE](LICENSE)

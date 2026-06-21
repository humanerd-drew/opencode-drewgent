# opencode-drewgent

[🇰🇷 한국어](README.ko.md)

Drewgent is an **autonomous software engineering agent system** built on [opencode](https://opencode.ai). It orchestrates specialized subagents through a kanban-backed pipeline, providing structured context handoff, failure tracking, and background automation.

This is **not** a standalone agent framework. It's the configuration and extension layer — agent profiles, skills, scripts, tools, and automation — that sits on top of opencode.

## Philosophy

### Why "Drewgent"?

**Drew** + A**gent**. Your name, your rules, your workflows.

Most agent systems are generic — one-size-fits-none. Drewgent starts from the opposite premise: **an agent should be as unique as the person building it.** The name is the first assertion of that identity. Fork it, rename it, make it yours. The `rename-drewgent` skill exists so you don't have to edit 2000+ files by hand.

### Why a 7-Layer Brain?

Most agent architectures are flat: one model, one context window, one prompt. Drewgent models itself on the **hierarchical structure of the human brain** — not because it's trendy, but because it solves a real problem: **how do you make an agent that remembers, governs itself, and grows over time?**

```
P0-brainstem    → Survival. Absolute rules that cannot be overridden.
P1-limbic       → Values. Tone, persona, communication style.
P2-hippocampus  → Memory. Session persistence, knowledge base.
P3-sensors      → Input. Tool routing, skill dispatch, gateway integration.
P4-cortex       → Growth. Pattern recognition, learning, taste.
P5-ego          → Identity. Self-model, calibration, awareness.
P6-prefrontal   → Strategy. Planning, proposals, incident reflection.
```

The hierarchy emerges from what overrides what:

- **Bottom-up** (sensation → action): P3 detects input → P2 loads context → P4 recognizes patterns → P5 and P6 decide
- **Top-down** (identity governs behavior): P5 says "I am thorough" → P1 shapes tone → P3 selects careful tools → P0 blocks dangerous operations
- **P0 always wins**: A brainstem rule like `禁rm_rf_root` cannot be bypassed by any upper layer, no matter how clever the argument

This is not documentation. These are **enforced constraints** — the `.neuron` files in `P0-brainstem/` are loaded at runtime and actively gate behavior.

### Why Obsidian as the Knowledge Graph?

The agent needs a persistent memory that:
1. **Survives restarts** — no "blank slate" on every session
2. **Is queryable by both humans and agents** — you can open the same files in Obsidian
3. **Has structure** — not a flat pile of text, but a connected graph
4. **Can be version-controlled** — git tracks every change, every decision, every incident

A database can do 1 and 2. Only **files with wikilinks** can do all four.

The P-layer directories *are* an Obsidian vault. Every file has YAML frontmatter, typed tags, and `[[wikilinks]]` to other files. This means:
- An agent can `gbrain_query("what's the refresh token policy?")` and get a ranked answer from the knowledge graph
- A human can open the same directory in Obsidian and see the exact same graph, with backlinks, graph views, and local graphs
- Git tracks who changed what, when, and why — the full audit trail of every architectural decision

### Filesystem = Truth

Most agent systems store state in ephemeral context windows or opaque databases. Drewgent's principle: **the filesystem is the canonical source.**

- Kanban board? SQLite file at `P2-hippocampus/kanban/state/drewgent_tasks.db`
- Session history? SQLite with FTS5 full-text search
- Agent profiles? `.md` files in `agents/`
- Skills? `.md` files in `skills/`
- Architecture decisions? `.md` files in `P6-prefrontal/proposals/`
- Governance rules? `.neuron` files in `P0-brainstem/`

If it matters, it's on disk. If it's on disk, it's in git (or gitignored by design). No opaque state, no "trust me, the agent remembers."

### Governance as Code

Rules in Drewgent are not advisory prompts — they are **enforced constraints** written as `.neuron` files in `P0-brainstem/`. Each rule is a self-contained constraint that the signal processor checks at runtime:

```
禁blind_write         → Cannot write a file without reading it first
禁task_qa_gate        → Cannot declare done without verification
禁secrets_in_code     → API keys detected in code → blocked
禁karpathy_coding     → Over-engineering, speculative abstraction → flagged
```

These are not "best practices." They are **gates** — the signal processor fires violations at `turn.end`, the awareness reporter surfaces them, and the agent cannot bypass them by saying "I'll be careful this time."

### Taste Over Volume

Drewgent prioritizes **decision quality over output quantity**. Every kanban task includes a leverage score: "If this is solved well, how many other problems disappear?"

| Score | Meaning | Example |
|-------|---------|---------|
| 5 | Root cause, eliminates entire class | Architecture change removes whole module |
| 4 | Solves multiple sub-problems | Shared utility removes N duplicates |
| 3 | Clear improvement + 1-2 side effects | Config cleanup eliminates manual step |
| 2 | Local improvement, no ripple | Bug fix |
| 1 | Surface change, minimal impact | Typo, docs update |

Low-leverage work (score 1-2) is not rejected — but it's deprioritized behind high-leverage work. The system is designed to **find the highest-leverage thing to do next**, not to generate busywork.

### Provenance Convention

Every architectural decision in this repo records **why it was made**:

- Skill frontmatter includes `trigger` and `provenance` fields
- Proposals include `tier`, `leverage_score`, and session context
- Kanban tasks include origin, session, and decision rationale

The principle: **the prompt is more informative than the output.** When you read a completed proposal six months later, the provenance tells you *why*, not just *what*.

---

## Quick Start

```bash
# 1. Install opencode
curl -fsSL https://opencode.ai/install | sh

# 2. Clone this repo as your Drewgent directory
git clone git@github.com:humanerd-drew/opencode-drewgent.git ~/.drewgent

# 3. Configure API keys
cd ~/.drewgent
cp .env.example .env
# Edit .env with your LLM provider API keys

# 4. Start opencode
opencode
```

### Requirements

- **macOS** or **Linux**
- **opencode** CLI (v1.x+)
- **Python** 3.11+
- **API key** for your LLM provider

---

## Obsidian Vault

The entire `~/.drewgent/` directory is an **Obsidian vault**. P0 through P6 form a connected wiki with wikilinks (`[[Page Name]]`), YAML frontmatter, and typed tags. This is not documentation-as-decoration — it's a living knowledge graph that agents query and write to.

```
~/.drewgent/               ← Obsidian vault root
├── P0-brainstem/          ← Governance rules
├── P1-limbic/             ← Identity and persona
├── P2-hippocampus/        ← Memory and knowledge (runtime)
├── P3-sensors/            ← Skills and gateway docs
├── P4-cortex/             ← Growth, references, plans
├── P5-ego/                ← Self-model
├── P6-prefrontal/         ← Strategy, proposals, incidents
└── AGENTS.md              ← Agent system guide (also vault doc)
```

### Wikilinks Across Layers

Files reference each other across layers via `[[wikilinks]]`. For example:

- `AGENTS.md` links to `[[P5-ego/SELF_MODEL]]`, `[[P0-brainstem/brain/rules]]`, `[[P1-limbic/persona/SOUL]]`
- `P0-brainstem/brain/rules.md` links to specific `.neuron` constraint files
- Skill files link to architecture docs and other skills
- Proposal documents link to incident reports and plans

This cross-linking creates a **knowledge graph** that agents can traverse — not a flat file tree.

### Graph Connectivity

The vault is designed for high backlink density. Key principles:

- Every architectural decision in `P6-prefrontal/proposals/` links to related incidents and skills
- Every skill documents its trigger context and provenance in frontmatter
- Every agent profile links to its governing rules and related profiles
- Skills from `P3-sensors/skills/` are loaded by opencode alongside `skills/`

### Obsidian-Specific Conventions

- **Frontmatter**: Every `.md` file has YAML frontmatter with `title`, `type`, `space`, `tags`, and `links`
- **Naming**: Slugs are kebab-case, unique across the vault to prevent wikilink ambiguity
- **Tags**: Used for cross-cutting categorization (`concept`, `guide`, `incident`, `proposal`)
- **Wiki-attachment images**: Referenced via `![[file.png]]` syntax
- **Excluded from Obsidian**: Runtime data directories (`P2-hippocampus/kanban/`, `logs/`, `cache/`, etc.) — configured in `.obsidian/` at runtime (not in repo)

### Querying the Vault

Agents query the vault via gbrain (MCP server for hybrid search):

```
gbrain_query("auth patterns")             → semantic + keyword search
gbrain_get_backlinks("P5-ego/SELF_MODEL") → find all pages that reference self-model
gbrain_find_orphans()                      → find pages with no inbound links
```

For local Obsidian CLI operations, the `skills/obsidian-cli/` skill provides workflows.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
  - [7-Layer Brain Architecture](#7-layer-brain-architecture)
  - [Multi-Agent Pipeline](#multi-agent-pipeline)
  - [Complexity Tiers](#complexity-tiers)
- [Agent Profiles](#agent-profiles)
  - [Flash Tier](#flash-tier)
  - [Pro Tier](#pro-tier)
  - [Max Tier](#max-tier)
  - [Handoff Contract](#handoff-contract)
- [Pipeline Stages](#pipeline-stages)
- [Subagent System](#subagent-system)
  - [delegate_task](#delegate_task)
  - [Kanban Pipeline Auto-Decomposition](#kanban-pipeline-auto-decomposition)
  - [Context Handoff Protocol](#context-handoff-protocol)
  - [ESCALATE Mechanism](#escalate-mechanism)
  - [Ponytail Principle](#ponytail-principle)
- [Configuration](#configuration)
  - [opencode.jsonc](#opencodejsonc)
  - [MCP Servers](#mcp-servers)
- [Cron & Automation](#cron--automation)
- [Skills](#skills)
- [Discord Integration](#discord-integration)
- [Repository Structure](#repository-structure)
  - [What's in the Repo](#whats-in-the-repo)
  - [What's NOT in the Repo (Personal Data)](#whats-not-in-the-repo-personal-data)
- [Related](#related)
- [License](#license)

---

## Architecture Overview

### 7-Layer Brain Architecture

Drewgent models its architecture on the hierarchical structure of the human brain. Each layer has a distinct role:

```
P6-prefrontal  Strategy    Long-term planning, proposals, incident reports
P5-ego         Identity    Self-model, self-awareness, calibration
P4-cortex      Growth      Learning, pattern recognition, taste development
P3-sensors     Input       Tool routing, gateway integration, skill dispatch
P2-hippocampus Memory      Session persistence, knowledge base, kanban state
P1-limbic      Values      Persona, tone, writing style, SOUL
P0-brainstem   Survival    Absolute rules (禁), governance as code
```

**Bottom-up flow:** P3 detects input → P2 loads context → P4 recognizes patterns → P5 integrates → P6 decides

**Top-down flow:** P5 shapes behavior → P1 influences tone → P3 selects tools → P0 blocks violations

**P0 overrides everything:** Brainstem rules (`.neuron` files) are enforced at runtime and cannot be bypassed by any upper layer. These are not advisory — they are active constraints embedded in the signal processing system.

### Multi-Agent Pipeline

Drewgent's core workflow is a kanban-backed pipeline where each stage is handled by a specialized agent:

```
kanban_create(
    title="Add login validation",
    pipeline=["explorer", "implementer", "tester", "reviewer", "archiver"],
)
```

This creates 5 sequential tasks with automatic dependency management:

```
explorer ──→ implementer ──→ tester ──→ reviewer ──→ archiver
    │              │            │           │            │
    │  findings    │  changes   │  tests    │  review    │  docs
    └──────┬───────┴─────┬──────┴─────┬─────┴──────┬─────┘
           │             │            │            │
           ↓             ↓            ↓            ↓
     Context from previous step automatically injected into prompt:
     **Findings:** auth code in src/auth/*.ts
     **Risks:** no refresh token rotation
     **Next:** implement token refresh
```

**Key properties:**
- **Automatic context handoff**: Each stage receives `findings`, `risks`, `next` as structured JSON
- **Failure tracking**: Unparseable handoffs fire `handoff_failed` events and visually mark the prompt
- **Fan-in support**: Tasks with multiple parents merge context from all sources
- **Worker-side resolution**: Worker reads parent results at runtime — no DB migration, no promotion-time injection

### Complexity Tiers

| Tier | Pipeline | Use Case |
|------|----------|----------|
| **1** (simple) | Implementer → Archiver | Typo fix, config change, trivial rename |
| **2** (moderate) | Explorer → Implementer ↔ Tester → Archiver | New function, moderate feature |
| **3** (complex) | Planner → Explorer → Implementer ↔ Tester → Reviewer → Security → Archiver | Architecture change, cross-cutting, auth-sensitive |

---

## Agent Profiles

14 specialized subagent roles. Each defines: model, provider, toolsets, and system instructions. Invoked via `delegate_task(agent_profile="<name>", goal="...")`.

### Flash Tier

OpenCode Go subscription ($0 marginal cost per call). Fast, for most day-to-day work.

| Profile | Model | Role | ESCALATE |
|---------|-------|------|----------|
| **explorer** | deepseek-v4-flash | Read-only codebase analysis | ✅ |
| **implementer** | deepseek-v4-flash | Code implementation | ✅ |
| **tester** | deepseek-v4-flash | Test writing and verification | ✅ |
| **archiver** | deepseek-v4-flash | Documentation, changelog | ❌ |
| **designer** | deepseek-v4-flash | UI/UX mockups, SVG assets | ✅ |
| **sre** | deepseek-v4-flash | Infrastructure, incident response | ✅ |
| **analyst** | deepseek-v4-flash | Data analysis, kanban/git queries | ❌ |

### Pro Tier

Stronger reasoning, for quality-critical steps.

| Profile | Model | Role |
|---------|-------|------|
| **reviewer** | deepseek-v4-pro | Code review (logic, edge cases, style) |
| **editor** | deepseek-v4-pro | Content QA, Korean language quality |
| **content-manager** | deepseek-v4-pro | CMO agent — observes work, produces drafts |

### Max Tier

Deep reasoning for architecture, planning, and security.

| Profile | Model | Role |
|---------|-------|------|
| **planner** | qwen3.7-max | Task decomposition, pipeline design |
| **reviewer-critical** | qwen3.7-max | Architecture-level review |
| **security-reviewer** | qwen3.7-max | Security audit (auth, crypto, injection) |
| **orchestrator** | qwen3.7-max | Work decomposition and pipeline orchestration |

### Handoff Contract

Every pipeline-capable profile includes a structured handoff section. When completing a pipeline task, agents structure their `result` as JSON:

```python
kanban_complete(
    task_id="t_xxx",
    summary="Human-readable completion report",
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

All fields are optional. If `result` is not valid JSON, the system logs a `handoff_failed` event, prints a warning to stdout, and visually marks the fallback in the prompt. This ensures failures are visible and traceable.

---

## Pipeline Stages

| Stage | What it does | Files it touches | Handoff output |
|-------|-------------|------------------|----------------|
| **Explorer** | Analyzes codebase, finds patterns | Read-only | `findings`: file paths, patterns. `risks`: concerns. `next`: implementation recommendations |
| **Implementer** | Writes code, creates patches | Source files | `findings`: files changed, approach. `risks`: edge cases. `next`: test focus areas |
| **Tester** | Writes and runs tests | Test files | `findings`: test results, bugs found. `risks`: flaky tests. `next`: reviewer attention points |
| **Reviewer** | Reviews code quality | Read-only | `findings`: issues with severity. `risks`: blocking issues. `next`: APPROVE/CHANGES_REQUESTED |
| **Security** | Security audit | Read-only | `findings`: vulnerabilities with CWE. `risks`: CRITICAL/HIGH. `next`: required fixes |
| **Archiver** | Documents changes | Docs | `findings`: docs produced. `risks`: coverage gaps. `next`: future doc needs |
| **Planner** | Designs the task graph | Plan docs | `findings`: plan structure. `risks`: complexity. `next`: execution order |
| **Designer** | Creates mockups, SVGs | HTML, SVG | `findings`: design decisions. `risks`: accessibility. `next`: dev handoff |
| **Editor** | Polishes content | Drafts | `findings`: edits made. `risks`: remaining concerns. `next`: ACCEPT/REJECT |
| **Content Manager** | Produces multi-format drafts | Drafts | `findings`: content produced. `risks`: timing. `next`: editor focus |

---

## Subagent System

### delegate_task

The primary mechanism for invoking subagents within a session:

```python
delegate_task(
    agent_profile="reviewer",
    goal="Review the auth changes in src/auth/*.ts",
    context="Files changed: src/auth/login.ts, src/auth/refresh.ts",
)
```

The `agent_profile` parameter:
1. Reads the profile file from `~/.drewgent/agents/<name>.md`
2. Overrides model/provider/toolsets from the profile's frontmatter
3. Prepends the profile's system instructions to the subagent's context
4. Spawns the subagent in an isolated session

### Kanban Pipeline Auto-Decomposition

For multi-stage work that should survive crashes and allow human review:

```python
kanban_create(
    title="Add login validation",
    pipeline=["explorer", "implementer", "tester", "reviewer", "archiver"],
    body="Implement login with email + password, JWT tokens, refresh token rotation",
)
```

This creates N sequential tasks linked via `task_links`:
- First task starts as `ready`
- Each subsequent task starts as `todo` (waits for parent)
- When a parent completes, dependency engine checks all parents — if all done, child promotes to `ready`
- Each task is dispatched as a separate worker process

### Context Handoff Protocol

When a child task starts, the worker (`scripts/run_kanban_worker.py`) automatically:

1. Queries `task_links` for parent task IDs
2. Reads each parent's `tasks.result`
3. Tries JSON parsing — if valid dict with `findings`/`risks`/`next`, formats as structured markdown
4. If not valid JSON, logs a `handoff_failed` event + warning + visual marker in the prompt
5. Prepends the context block to the current task's body

This happens at runtime in the worker — zero DB migration, zero schema changes, 100% backward compatible.

### ESCALATE Mechanism

Flash-tier profiles (explorer, implementer, tester, designer, sre, analyst) can signal that a task exceeds their capability:

```
ESCALATE: This refactoring involves cross-module dependency analysis
that requires stronger reasoning. Recommend routing to planner + reviewer.
```

The caller detects this pattern and re-routes to a Max-tier model.

### Ponytail Principle

Before writing code, every agent applies the minimization checklist:
1. Is this code really needed? (YAGNI) → no: don't write it
2. Does the standard library have it? → use it
3. Does the native platform support it? → use it (`<input type="date">` etc.)
4. Does an installed dependency solve it? → use it (no new deps)
5. Can it be one line? → one line
6. Still needed? → minimum viable implementation

---

## Configuration

### opencode.jsonc

```jsonc
{
  "model": "opencode-go/deepseek-v4-flash",

  "small_model": "opencode-go/deepseek-v4-pro",

  "instructions": ["AGENTS.md"],

  "skills": {
    "paths": [
      "~/.drewgent/skills",
      "~/.drewgent/P3-sensors/skills",
      "~/.config/opencode/skills"
    ]
  },

  "mcp": {
    "gbrain": {
      "type": "local",
      "command": ["gbrain", "serve"],
      "enabled": true,
      "timeout": 120000
    },
    "lazyweb": {
      "type": "remote",
      "url": "https://www.lazyweb.com/mcp",
      "enabled": true,
      "headers": { "Authorization": "Bearer {env:LAZYWEB_API_KEY}" },
      "timeout": 60000
    },
    "specification-website": {
      "type": "remote",
      "url": "https://mcp.specification.website/mcp",
      "enabled": true,
      "timeout": 60000
    }
  }
}
```

### MCP Servers

| Server | Type | Purpose | Auth |
|--------|------|---------|------|
| **gbrain** | local (stdio) | Hybrid search over personal knowledge base. PGLite-backed vector + keyword search, code call graph analysis, entity tracking, takes/calibration | `OPENAI_API_KEY` env |
| **lazyweb** | remote (HTTP) | 281k+ real app screenshots for UI design reference. Paywall, pricing, onboarding, checkout pattern research | `LAZYWEB_API_KEY` env |
| **specification-website** | remote (HTTP) | Web spec checklists: SEO, accessibility, security, performance, resilience, i18n. Site audit reference | None (public) |

---

## Cron & Automation

Drewgent uses a launchd-driven 60-second tick that dispatches `scripts/drewgent_cron.py`. The scheduler (`cron/scheduler.py`) reads `cron/jobs.json` and fires jobs at their scheduled intervals.

| Interval | Job | Description | Script |
|----------|-----|-------------|--------|
| 2 min | trend-evaluate | Evaluate collected trends against philosophy filter | n8n_trigger_runner.py |
| 5 min | launchd watchdog | Check all services are running | shell |
| 5 min | dashboard push | Push agent state to Cloudflare dashboard | agent_dashboard_push.py |
| 15 min | gbrain watchdog | Ensure gbrain brain sync is healthy | shell |
| 6 hours | trend-collect | Scrape GitHub trending repos | cron_trend_harvester.py |
| 6 hours | seo-harvester | Collect SEO articles from RSS feeds | cron_seo_harvester.py |
| Daily 04:00 | log rotation | Rotate and compress logs | shell |
| Daily 06:00 | usage watch | Track token usage and costs | minimax_usage.py |
| Daily 09:00 | harmony check | Verify vault graph integrity | shell |
| Daily 12:00 | seo-analyze | Analyze collected SEO articles | n8n_trigger_runner.py |
| Daily 20:00 | daily retro | Generate daily work summary | n8n_trigger_runner.py |
| Monthly | trend-retire | Retire stale evaluated trends | n8n_trigger_runner.py |
| Monthly | seo-trend report | Generate SEO trend report | n8n_trigger_runner.py |
| Tue/Fri 10:00 | taste review | Deep analysis of high-quality tools | n8n_trigger_runner.py |

---

## Skills

Skills are Markdown files with YAML frontmatter that provide specialized instructions for specific tasks. The opencode `skill()` tool loads them on demand.

Included categories (~100+ skills total):

| Category | Description | Example Skills |
|----------|-------------|----------------|
| `ui/` | UI quality bar, design system | baseline-ui (12 priority tiers) |
| `devops/` | Infrastructure and deployment | kanban-orchestrator, kanban-worker, cron-script-fastpath, llm-cost-audit, wordpress-deployment |
| `software-development/` | Engineering practices | ponytail, codebase-refactoring, subagent-profiles, payment-integration, mpa-url-state-bridge, m-log-development |
| `creative/` | Visual and audio content | baoyu-infographic (21 layouts × 21 styles), sketch, claude-design, architecture-diagram, comfyui, audiocraft, pretext |
| `mlops/` | ML training and inference | axolotl, unsloth, trl-fine-tuning, grpo-rl-training, vllm, guidances, outlines, gguf |
| `brain/` | Agent system maintenance | memory-md-cleanup, vault-naming-convention, daily-retro, drewgent-runtime-checkup |
| `content/` | Content production pipeline | content-pipeline, content-manager, seo-article-harvester, wordpress-cms |
| `mcp/` | MCP server integration | gbrain-integration, native-mcp, mcporter |
| `security/` | Security audit (from P3-sensors) | security-reviewer checks, godmode (red-teaming) |
| `autonomous-ai-agents/` | Agent architecture patterns | acp-thinking-spinner, hermes-agent, content-management, drewgent-update-checker |
| `gaming/` | Game automation | pokemon-player, minecraft-modpack-server |
| `nas-synology-ssh-automation/` | NAS management | read-only diagnostics, supervised operations |
| `taste-review/` | Trend analysis framework | 5-question analysis framework, leverage scoring |
| `agent-profiles/` | Profile system documentation | agent-profile authoring, delegate_task patterns |

Skills are loaded via:
```
skill("baseline-ui")
skill("ponytail")
```

---

## Discord Integration

`scripts/discord_bot.py` connects Discord channels to the opencode agent:

- Connects via opencode's `--attach` mode (port 8642)
- Creates a thread for each conversation
- Routes messages to the agent for processing
- Supports file attachments (images, documents, code)
- Chunks long messages (>2000 chars) across multiple messages
- Configured as a launchd service (`ai.drewgent.discord-bot`) with auto-recovery

---

## Repository Structure

### What's in the Repo

```
~/.drewgent/
│
├── opencode.jsonc              opencode configuration (model, MCP, skills)
├── AGENTS.md                   System instructions loaded by opencode
├── .env.example                API key configuration template
├── Dockerfile                  Containerized deployment
├── .gitignore                  Excludes personal runtime data
│
├── agents/                     14 subagent profile definitions
│   ├── explorer.md             Read-only analysis (flash)
│   ├── implementer.md          Code implementation (flash)
│   ├── tester.md               Test writing (flash)
│   ├── reviewer.md             Code review (pro)
│   ├── reviewer-critical.md    Architecture review (max)
│   ├── security-reviewer.md    Security audit (max)
│   ├── planner.md              Task decomposition (max)
│   ├── orchestrator.md         Pipeline orchestration (max)
│   ├── designer.md             UI/UX design (flash)
│   ├── editor.md               Content editing (pro)
│   ├── content-manager.md      Content production (pro)
│   ├── archiver.md             Documentation (flash)
│   ├── sre.md                  Infrastructure (flash)
│   ├── analyst.md              Data analysis (flash)
│   └── README.md
│
├── skills/                     100+ skill definitions
│   ├── ui/                     UI quality standards
│   ├── devops/                 Infrastructure and automation
│   ├── software-development/   Engineering practices
│   ├── creative/               Visual and audio content
│   ├── mlops/                  ML training and inference
│   ├── brain/                  Agent maintenance
│   ├── content/                Content pipeline
│   └── ...
│
├── P3-sensors/skills/          Additional architecture skills
│   ├── agent-architecture/     Brain signal system, self-replicating agent
│   ├── agent-protocol/         Goose ACP integration
│   ├── brain-broken-link-fix/  Vault health maintenance
│   ├── brain-dashboard-system/ Brain monitoring dashboard
│   ├── trend-harvester/        AI trend collection and filtering
│   ├── session-pattern-archiver/
│   ├── harsh-critic/           Utility
│   └── ...
│
├── scripts/                    39 automation scripts
│   ├── run_kanban_worker.py    Kanban task executor
│   ├── drewgent_cron.py        Cron dispatcher (60s interval)
│   ├── discord_bot.py          Discord ↔ opencode gateway
│   ├── discord_send.py         Discord message chunk sender
│   ├── n8n_trigger_runner.py   LLM-generated cron triggers
│   ├── opencode_health_check.py Health monitoring
│   ├── agent_dashboard_push.py Cloudflare dashboard
│   ├── brain_html_dashboard.py Agent dashboard generator
│   ├── cron_trend_harvester.py AI trend collection
│   ├── cron_seo_harvester.py   SEO article collection
│   └── ...
│
├── tools/                      57 tool implementations
│   ├── kanban_tools.py         Task queue (create, complete, link, claim)
│   ├── delegate_tool.py        Subagent delegation
│   ├── registry.py             Tool registration system
│   ├── terminal_tool.py        Terminal execution
│   ├── gbrain_tool.py          Hybrid search brain tool
│   ├── file_tools.py           File operations
│   ├── web_tools.py            Web fetching and search
│   └── ...
│
├── cron/                       Scheduled job definitions
│   ├── jobs.json               Job schedule (intervals, scripts)
│   ├── scheduler.py            Schedule resolver and dispatcher
│   └── cron_agent.py           Agent-based job executor
│
├── hooks/                      Event hooks
│   └── kanban-notify/          Kanban completion notifications
│
├── P0-brainstem/               Survival layer — governance rules
│   ├── brain/rules.md           P0 rule documentation
│   └── brain/Drewgent-brain/   18 .neuron constraint files
│
├── P1-limbic/                  Identity layer
│   ├── persona/SOUL.md          Agent identity and personality
│   └── persona/writing-style-guide.md  Communication conventions
│
├── P2-hippocampus/             Memory layer (stub — data gitignored)
│   └── README.md
│
├── P3-sensors/                 Input layer
│   ├── skills/                 Architecture-specific skills
│   └── gateway/drewgent-architecture-dataflow.md  Data flow docs
│
├── P4-cortex/                  Growth layer
│   ├── knowledge/              Architecture references, UX wiki, templates
│   │   ├── NEURONFS_RULES.md
│   │   ├── OPENCRAB_ONTOLOGY.md
│   │   ├── laws-of-ux-wiki/
│   │   └── prd-template.md
│   ├── growth/                 Implementation plans and reviews
│   │   ├── KANBAN-USER-GUIDE.md
│   │   ├── drewgent-kanban-implementation-plan.md
│   │   └── ...
│   └── README.md
│
├── P5-ego/                     Identity layer
│   ├── SELF_MODEL.md            Self-model and integration rules
│   └── README.md
│
├── P6-prefrontal/              Strategy layer
│   ├── proposals/              Design proposals (tier + leverage score)
│   ├── incidents/              Incident reports and recovery patterns
│   ├── plans/                  Long-term growth plans
│   └── migrations/             Architecture migration records
│
└── .github/workflows/          CI: tests, Docker, docs checks
```

### What's NOT in the Repo (Personal Data)

These directories exist in `~/.drewgent` at runtime but are excluded from git:

| Directory | Contents | Why Excluded |
|-----------|----------|--------------|
| `P2-hippocampus/kanban/` | Kanban task board SQLite | Personal task data |
| `P2-hippocampus/knowledge/` | SEO article collection | Personal research |
| `P2-hippocampus/memories/` | Session insights | Personal learnings |
| `P4-cortex/content/` | Brand guide, narrative arc | Personal branding |
| `P4-cortex/growth/` | Runtime growth state | Generated state |
| `P4-cortex/insights/` | Extracted patterns | Personal |
| `P5-ego/config/` | API keys, secrets | Security |
| `P5-ego/state/` | Runtime metrics | Generated state |
| `P3-sensors/cron/output/` | Cron job output | Generated |
| `P3-sensors/gateway_state/` | Gateway runtime state | Generated |
| `config.yaml` | Personal configuration | API keys, paths |
| `kanban.db` | Kanban database | Personal tasks |
| Any `.db`, `.log`, `cache/` | Runtime data | Generated |

The `.gitignore` is configured to exclude all of these. If you clone this repo, you'll get the architecture and tooling without any personal data.

---

## Naming Convention

**Drewgent** = **Drew** + A**gent**.

The name reflects that this is a personalized agent system — your name, your rules, your workflows. The convention is designed for easy forking:

```
<yourname>gent
```

Examples:
- `drewgent` (Drew + agent) — this repo
- `alexgent` (Alex + agent)
- `saragent` (Sara + agent)
- `devgent` (Dev + agent)

### Renaming

If you fork this repo for your own use, run the rename skill:

```
skill("rename-drewgent")
```

This will:
1. Replace all "drewgent" → "<yourname>gent" across 2000+ references
2. Rename `~/.drewgent` → `~/.<yourname>gent`
3. Update config paths in opencode.jsonc, scripts, and skills
4. Update AGENTS.md and all documentation references

The rename skill is at `skills/software-development/rename-drewgent/SKILL.md`.

---

## Related

- [opencode](https://opencode.ai) — The CLI agent platform Drewgent runs on
- [gbrain](https://github.com/anomalyco/gbrain) — Local PGLite brain server for hybrid search
- [lazyweb](https://lazyweb.com) — 281k+ real app screenshots for UI design reference
- [specification.website](https://specification.website) — Web spec checklists and best practices

---

## Credits

opencode-drewgent is built on the shoulders of these open-source projects:

| Project | Author | Purpose | License |
|---------|--------|---------|---------|
| [opencode](https://opencode.ai) | [Anomaly](https://github.com/anomalyco) | AI coding agent platform | MIT |
| [oh-my-openagent](https://github.com/code-yeongyu/oh-my-openagent) | [code-yeongyu](https://github.com/code-yeongyu) | Multi-agent orchestration (Sisyphus, ultrawork) | SUL-1.0 |
| [oh-my-claudecode](https://github.com/Yeachan-Heo/oh-my-claudecode) | [Yeachan-Heo](https://github.com/Yeachan-Heo) | Team mode multi-agent pattern reference | MIT |
| [gbrain](https://github.com/anomalyco/gbrain) | Anomaly | MCP-based knowledge graph & hybrid search | — |
| [codebase-memory-mcp](https://github.com/anomalyco/opencode) | Anomaly | Codebase knowledge graph | MIT |
| [lazyweb](https://lazyweb.com) | [Ali Boulata](https://github.com/aboul3ata) | UI design reference MCP | — |
| [Karpathy LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) | Andrej Karpathy | Compile-pattern knowledge base concept | — |
| [Ponytail](https://github.com/DietrichGebert/ponytail) | Dietrich Gebert | Code minimalization checklist | — |
| [NeuronFS](https://github.com/drewgent/neuronfs) | HUMANERD | Brain-based governance system | — |
| [specification.website](https://specification.website) | [Joost de Valk](https://github.com/jdevalk) | Web spec checklists MCP | — |

No third-party source code is directly included — all dependencies are referenced or installed via package managers. Each project respects its own license.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) — one change per PR, no new deps, include provenance.

## Security

See [SECURITY.md](SECURITY.md) — report vulnerabilities by email, not public issues.

## License

MIT — see [LICENSE](LICENSE)

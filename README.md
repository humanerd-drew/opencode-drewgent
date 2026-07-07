# opencode-drewgent

[🇰🇷 한국어](README.ko.md)

[![Built for opencode](https://img.shields.io/badge/Built%20for-opencode-8A2BE2)](https://opencode.ai)
[![YOUR_DOMAIN](https://img.shields.io/badge/blog-YOUR_DOMAIN-8B7355)](https://YOUR_DOMAIN)

Drewgent is an **autonomous software engineering agent system** built on [opencode](https://opencode.ai). It orchestrates specialized subagents through opencode's built-in `task()` and GJC Coordinator MCP for isolated/parallel execution, with a kanban-backed pipeline for structured context handoff, failure tracking, and background automation.

This is **not** a standalone agent framework. It's the configuration and extension layer — skills, scripts, tools, MCP servers, automation, and a persistent knowledge graph — that sits on top of opencode.

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
- An agent can `recall("refresh token policy")` and get ranked results from the knowledge base (SQLite FTS5 + vector search)
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

# 2. Clone this repo
git clone git@github.com:humanerd-drew/opencode-drewgent.git ~/.drewgent
cd ~/.drewgent

# 3. Run the setup script
bash scripts/setup.sh
```

### First-run Checklist (post clone)

| # | Step | Command / Action | Required? |
|---|------|-----------------|-----------|
| 1 | Run setup | `bash scripts/setup.sh` — installs deps, creates .env, checks environment | ✅ |
| 2 | Set API keys | Edit `~/.drewgent/.env` — add `OPENCODE_API_KEY` (required), `DISCORD_BOT_TOKEN` (optional), `OPENAI_API_KEY` (optional) | ✅ |
| 3 | Rename (optional) | `skill("rename-drewgent")` — replaces all `drewgent` → `<yourname>gent` | 🔄 |
| 4 | Verify | `bash scripts/bridge-lint.sh` — checks manufacturing-bridge tag compliance | 🔄 |
| 5 | Install launchd (macOS) | `for f in launchd/*.plist.example; do n=$(basename "$f" .example); cp "$f" ~/Library/LaunchAgents/"$n" && launchctl load ~/Library/LaunchAgents/"$n"; done` — enables cron, opencode serve, Discord bot daemons | 🔄 |
| 6 | Start opencode | `opencode` — interactive session | ✅ |

**Not working?** See [Troubleshooting](#troubleshooting) below. Missing API keys? Check `~/.drewgent/.env`.

### Requirements

- **macOS** or **Linux**
- **opencode** CLI (v1.x+)
- **Python** 3.11+
- **Model subscription** (opencode-go or bring-your-own provider)

---

## Getting Started as a Fork

This repo is designed to be **forked and customized**. Here's the recommended workflow:

### 1. Fork on GitHub

Fork the repo at [humanerd-drew/opencode-drewgent](https://github.com/humanerd-drew/opencode-drewgent).

### 2. Clone your fork

```bash
git clone git@github.com:YOUR_USERNAME/opencode-drewgent.git ~/.drewgent
```

### 3. Rename (optional but recommended)

This will replace all `drewgent` references with your own agent name:

```bash
# Run the rename skill from within opencode
skill("rename-drewgent")

# Or run the init script directly
bash scripts/init-template.sh --name yourname
```

The rename convention is `<yourname>gent`:
- `drewgent` (Drew + agent)
- `alexgent` (Alex + agent)
- `devgent` (Dev + agent)

### 4. Customize your identity

Edit the files under `@identity/` to match your agent's personality:

| File | What to customize |
|------|-------------------|
| `@identity/SELF_MODEL.md` | Agent name, purpose, core directives |
| `@identity/persona/SOUL.md` | Tone, style, values, voice |
| `@identity/persona/writing-style-guide.md` | Writing conventions, templates |
| `@identity/brain/rules.md` | P0 governance rules (keep the strict ones) |

### 5. Start opencode

```bash
cd ~/.drewgent
opencode
```

### Template vs Personal Files

| In repo (template) | Gitignored (your personal data) |
|--------------------|---------------------------------|
| P0-P6 layer structure | `@memory/` — session logs, growth data |
| Skill definitions | `@action/incidents/` — personal incident reports |
| Agent profiles | `P5-ego/config/` — API keys, secrets |
| Scripts & cron examples | `config.yaml`, `kanban.db` |
| `@identity/` (template) | `agent-dashboard-state.json` |

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

### Querying the Knowledge Base

Agents query the knowledge base via recall/remember tools (SQLite FTS5 + Ollama vector search):

```
recall("auth patterns")             → semantic + keyword search (cosine sim + FTS5 fallback)
memory-stats()                      → DB statistics, embedding coverage
remember("decision: ...")           → store a fact with auto-embedding
```

For cross-session memory, opencode's built-in `memory()` tool is used. The knowledge.db replaces gbrain's PGLite — zero daemon, zero API cost.

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
  - [task() — Same-Model Delegation](#task--same-model-delegation)
  - [gjc_delegate_execute() — Isolated/Parallel Execution](#gjc_delegate_execute--isolatedparallel-execution)
  - [gjc_delegate_team() — Parallel Team Runs](#gjc_delegate_team--parallel-team-runs)
  - [Kanban Pipeline Auto-Decomposition](#kanban-pipeline-auto-decomposition)
  - [Context Handoff Protocol](#context-handoff-protocol)
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

Drewgent's core workflow uses opencode's built-in `task()` for same-model delegation and GJC Coordinator MCP (`gjc_delegate_*`) for model-specific or isolated work. A kanban-backed pipeline handles crash-surviving multi-stage work:

```
kanban_create(
    title="Add login validation",
    pipeline=["explorer", "implementer", "reviewer"],
)
```

This creates 3 sequential tasks with automatic dependency management:

```
explorer ──→ implementer ──→ reviewer
    │              │            │
    │  findings    │  changes   │  review
    └──────┬───────┴─────┬──────┘
           │             │
           ↓             ↓
     Context from previous step automatically injected into prompt:
     **Findings:** auth code in src/auth/*.ts
     **Risks:** no refresh token rotation
     **Next:** implement token refresh
```

Archiver auto-runs on completion as a post-hook.

**Key properties:**
- **Automatic context handoff**: Each stage receives `findings`, `risks`, `next` as structured JSON
- **Failure tracking**: Unparseable handoffs fire `handoff_failed` events and visually mark the prompt
- **Fan-in support**: Tasks with multiple parents merge context from all sources
- **Worker-side resolution**: Worker reads parent results at runtime — no DB migration, no promotion-time injection
- **Two delegation modes**: `task()` inherits parent model (fast), `gjc_delegate_execute()` uses profile model with worktree isolation

### Complexity Tiers

| Tier | Pipeline | Use Case |
|------|----------|----------|
| **1** (simple) | Implementer → (auto-archive) | Typo fix, config change, trivial rename |
| **2** (moderate) | Explorer → Implementer → Reviewer | New function, moderate feature |
| **3** (complex) | Planner → Explorer → Implementer ↔ Reviewer-critical → Reviewer | Architecture change, cross-cutting, auth-sensitive |

---

## Agent Profiles

Specialized subagent roles invoked via opencode's built-in `task(subagent_type="<name>")` for same-model work, or `gjc_delegate_execute()` for profile-model work with worktree isolation. Profiles define: model, provider, toolsets, and system instructions.

### Flash Tier

OpenCode Go subscription ($0 marginal cost per call). Fast, for most day-to-day work.

| Profile | Model | Role |
|---------|-------|------|
| **explorer** | deepseek-v4-flash | Read-only codebase analysis |
| **implementer** | deepseek-v4-flash | Code implementation |
| **archiver** | deepseek-v4-flash | Documentation, changelog |
| **designer** | deepseek-v4-flash | UI/UX mockups, SVG assets |
| **analyst** | deepseek-v4-flash | Data analysis, kanban/git queries |

### Pro Tier

Stronger reasoning, for quality-critical steps.

| Profile | Model | Role |
|---------|-------|------|
| **reviewer** | deepseek-v4-pro | Code review (logic, edge cases, style) |
| **editor** | deepseek-v4-pro | Content QA, Korean language quality |
| **content-manager** | deepseek-v4-pro | CMO agent — observes work, produces drafts |
| **orchestrator** | deepseek-v4-pro | Work decomposition and pipeline orchestration |
| **sre** | deepseek-v4-pro | Infrastructure, incident response |

### Max Tier

Deep reasoning for architecture, planning, and security.

| Profile | Model | Role |
|---------|-------|------|
| **planner** | qwen3.7-max | Task decomposition, pipeline design |
| **reviewer-critical** | qwen3.7-max | Architecture-level review |
| **security-reviewer** | qwen3.7-max | Security audit (auth, crypto, injection) |

### Task Profiles (opencode built-in, no profile file needed)

| Name | Model | Role |
|------|-------|------|
| **tester** | (inherits parent) | Test writing and verification |
| **reviewer** | (inherits parent) | Standard code review |

### Model Assignment Strategy

The profile-to-model mapping above reflects the **cost-optimized** assignment. The original **performance-optimized** assignment used stronger models for all execution tasks — the shift was motivated by OpenCode Go's subscription quota ($30/week): execution tasks (writing, code generation, doc compilation) perform just as well on flash-tier models, while planning and review remain on pro/max.

| Profile | Performance Opt. (original) | Cost Opt. (current) | Cost delta |
|---------|---------------------------|-------------------|------------|
| implementer | kimi-k2.7-code ($0.012/call) | deepseek-v4-flash ($0.00038/call) | **-97%** |
| content-manager (periodic) | deepseek-v4-pro ($0.0035/call) | openai/gpt-oss-120b via Groq (free) | free |
| wiki-compile | deepseek-v4-pro ($0.0035/call) | deepseek-v4-flash ($0.00038/call) | -89% |
| reviewer | deepseek-v4-pro | unchanged | — |
| planner | qwen3.7-max | unchanged | — |
| reviewer-critical | qwen3.7-max | unchanged | — |

The `content-manager` periodic cron job for `YOUR_DOMAIN` uses Groq Free Tier (`openai/gpt-oss-120b`, 500 t/s, 30 RPM, 1K RPD) — zero cost with 120B parameters. Direct `task()` calls still use the profile-defined `deepseek-v4-pro`.

### Handoff Contract

Every pipeline-capable profile includes a structured handoff section. When completing a pipeline task, agents structure their `kanban_complete` `result` as JSON:

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
| **Implementer** | Writes code, creates patches | Source files | `findings`: files changed, approach. `risks`: edge cases. `next`: reviewer focus areas |
| **Reviewer** | Reviews code quality | Read-only | `findings`: issues with severity. `risks`: blocking issues. `next`: APPROVE/CHANGES_REQUESTED |
| **Archiver** (auto post-hook) | Documents changes | Docs | `findings`: docs produced. `risks`: coverage gaps. `next`: future doc needs |
| **Planner** | Designs the task graph | Plan docs | `findings`: plan structure. `risks`: complexity. `next`: execution order |
| **Designer** | Creates mockups, SVGs | HTML, SVG | `findings`: design decisions. `risks`: accessibility. `next`: dev handoff |
| **Editor** | Polishes content | Drafts | `findings`: edits made. `risks`: remaining concerns. `next`: ACCEPT/REJECT |
| **Content Manager** | Produces multi-format drafts | Drafts | `findings`: content produced. `risks`: timing. `next`: editor focus |
| **Security Reviewer** | Security audit | Read-only | `findings`: vulnerabilities with CWE. `risks`: CRITICAL/HIGH. `next`: required fixes |

---

## Subagent System

### task() — Same-Model Delegation

The primary mechanism for invoking subagents when the agent model is sufficient:

```python
task(
    subagent_type="reviewer",
    description="Review auth changes",
    prompt="Analyze the existing auth implementation in src/auth/*.ts...",
)
```

- Inherits parent model (fast, no context switching)
- No profile file needed for built-in subagent types
- For custom profiles, passes through `agents/<name>.md` profile settings

### gjc_delegate_execute() — Isolated/Parallel Execution

When you need a specific model or isolated execution environment:

```python
gjc_delegate_execute(
    goal="Refactor auth module",
    worktree="refactor-auth",
    acceptance=["all tests pass", "API compatible"],
    model="kimi-k2.7-code",
)
```

- Uses GJC Coordinator MCP for worktree isolation + tmux parallel execution
- Applies profile-specific model (unlike `task()` which inherits parent)
- Returns durable turn status and artifact references

### gjc_delegate_team() — Parallel Team Runs

```python
gjc_delegate_team(
    goals=[
        { "id": "A", "desc": "..." },
        { "id": "B", "desc": "..." },
        { "id": "C", "desc": "..." },
    ]
)
```

Spawns N parallel tmux sessions, each with worktree isolation.

### Kanban Pipeline Auto-Decomposition

For multi-stage work that should survive crashes and allow human review:

```python
kanban_create(
    title="Add login validation",
    pipeline=["explorer", "implementer", "reviewer"],
    body="Implement login with email + password, JWT tokens, refresh token rotation",
)
```

This creates N sequential tasks linked via `task_links`:
- First task starts as `ready`
- Each subsequent task starts as `todo` (waits for parent)
- When a parent completes, dependency engine checks all parents — if all done, child promotes to `ready`
- Archiver auto-runs as a post-hook on kanban_complete
- Each task is dispatched as a separate worker process via Office Autopilot

### Context Handoff Protocol

When a child task starts, the worker (`scripts/run_kanban_worker.py`) automatically:

1. Queries `task_links` for parent task IDs
2. Reads each parent's `tasks.result`
3. Tries JSON parsing — if valid dict with `findings`/`risks`/`next`, formats as structured markdown
4. If not valid JSON, logs a `handoff_failed` event + warning + visual marker in the prompt
5. Prepends the context block to the current task's body

This happens at runtime in the worker — zero DB migration, zero schema changes, 100% backward compatible.

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
      "~/.drewgent/@action/skills",
      "~/.config/opencode/skills"
    ]
  },

  "mcp": {
    "discord": {
      "type": "local",
      "command": ["discord-mcp"],
      "env": { "DISCORD_TOKEN": "{env:DISCORD_BOT_TOKEN}" }
    },
    "wordpress": {
      "type": "local",
      "command": ["node", "scripts/wordpress-mcp-server.js"]
    },
    "gajae-code": {
      "type": "local",
      "command": ["gjc", "mcp-serve", "coordinator"],
      "env": { "OPENCODE_API_KEY": "{env:OPENCODE_API_KEY}" }
    }
  }
}
```

### MCP Servers

| Server | Type | Purpose | Auth |
|--------|------|---------|------|
| **codebase-memory-mcp** | local (stdio) | Codebase knowledge graph — search functions, trace callers/callees, read source | None (local) |
| **discord** | local (stdio) | Discord message read/write, channel history, attachment handling | `DISCORD_BOT_TOKEN` env |
| **wordpress** | local (stdio) | WordPress post/category/media management via wp-cli on Docker | None (local) |
| **gajae-code** | local (stdio) | GJC Coordinator — worktree isolation, tmux parallel execution, structured delegation | `OPENCODE_API_KEY` env |
| **portone** | local (stdio) | PortOne (포트원) V2 payment gateway — docs, test channels, payment queries | None (local) |
| **opencode-knowledge** | built-in | Cross-session memory — recall, remember, memory-stats | None (local) |

---

## Vault Secrets

All API keys and tokens are stored **encrypted** using Drewgent's vault system. No plaintext secrets on disk.

### Architecture

```
User provides key → vault_cli.py set KEY VALUE
                           ↓
                    Fernet encrypt → vault.enc
                    Master key in OS keyring (macOS Keychain / Win Credential Manager / Linux libsecret)
                           ↓
                    Shell hook → eval "$(vault env)" → export ENV vars
                           ↓
                    opencode.jsonc → {env:VAR} reference
```

### Quick Start

```bash
pip install cryptography keyring
python3 scripts/vault_cli.py init
vault set OPENAI_API_KEY "sk-..."     # encrypted immediately
vault set DISCORD_TOKEN "MT-..."      # never in .zshrc
vault list                            # stored keys
eval "$(vault env)"                   # export to environment
```

### Agent Rule

When the agent receives a key, it **must** use `vault set KEY VALUE` — never write plaintext to `.zshrc`, `.env`, or `opencode.jsonc`. Config references use `{env:VAR}` syntax only.

### Setup for New Installs

1. `pip install cryptography keyring`
2. `python3 scripts/vault_cli.py init` (creates master key in OS keyring)
3. Add shell hook to `.zshrc`: `eval "$(python3 ~/.drewgent/scripts/vault_cli.py env 2>/dev/null)" || true`
4. `vault scan` to find existing plaintext keys
5. `vault migrate` to encrypt and replace with `{env:VAR}`

The skill `skill("vault-secrets")` documents the full protocol.

---

## Cron & Automation

Drewgent uses a launchd-driven 60-second tick that dispatches `scripts/drewgent_cron.py`. The scheduler (`cron/scheduler.py`) reads `cron/jobs.json` and fires jobs at their scheduled intervals.

| Interval | Job | Description | Method |
|----------|-----|-------------|--------|
| 5 min | launchd watchdog | Check all launchd services running | shell |
| 5 min | dashboard push | Push agent state to Cloudflare dashboard | agent_dashboard_push.py |
| 5 min | office autopilot | Auto-process kanban pending tasks | office_autopilot.sh |
| 60 min | housekeeper | Brain pulse check, cleanup | drewgent_housekeeper.py |
| 3 hours | content-manager-periodic | Content draft production | opencode run (deepseek-v4-pro) |
| 6 hours | SEO article harvester | Collect SEO articles from RSS feeds | cron_seo_harvester.sh |
| 6 hours | trend-collect | Scrape GitHub trending repos (8 workers) | trend_harvester.py |
| 6 hours | trend-scorer | Heuristic trend scoring (30 min after collect) | trend_scorer.py |
| Daily 03:00 | seo-analyze | Analyze collected SEO articles | seo_analyzer.sh |
| Daily 04:00 | housekeeper (deep clean) | Log rotation, wiki lint, QA digest, knowledge.db maintenance | drewgent_housekeeper.py |
| Daily 05:00 | content taste diff | Content taste diff analysis | content_diff_analyzer.py |
| Daily 05:00 | cron health check | Full cron system health verification | cron_health_check.py |
| Daily 06:00 | usage watch | Track token usage and adoption | trend_usage_watch.py |
| Daily 06:00 | content graph engine | TF-IDF + taxonomy link recommendations | content_graph_builder.py |
| Daily 09:00 | harmony check | Verify vault graph integrity | drewgent_harmony_check.sh |
| Daily 10:00 | trend-evaluate-trigger | Check for new trends to evaluate | opencode run (flash) |
| Daily 20:00 | daily retro | Generate daily work summary | opencode run |
| Weekly Sun 03:00 | wiki-compile | Compile P2 raw data → P5-ego/wiki pages | opencode run (archiver) |
| Weekly Mon 10:00 | trend-retire-trigger | Retire stale evaluated trends | opencode run (flash) |
| Weekly Mon 14:00 | seo-trend-trigger | Generate SEO trend report | opencode run (flash) |
| Tue/Fri 10:00 | taste-review-trigger | Deep analysis of high-quality tools | opencode run (flash) |

---

## Skills

Skills are Markdown files with YAML frontmatter that provide specialized instructions for specific tasks. The opencode `skill()` tool loads them on demand.

Included categories (36 categories, 100+ skills total):

| Category | Description | Example Skills |
|----------|-------------|----------------|
| `ui/` | UI quality bar, design system | baseline-ui (12 priority tiers) |
| `devops/` | Infrastructure and deployment | kanban-orchestrator, cron-script-fastpath, llm-cost-audit |
| `software-development/` | Engineering practices | ponytail, codebase-refactoring, cf-worker-modular-architecture, model-routing |
| `creative/` | Visual and audio content | baoyu-infographic (21×21 styles), sketch, claude-design, architecture-diagram, comfyui, pretext |
| `mlops/` | ML training and inference | axolotl, unsloth, trl-fine-tuning, grpo-rl-training, vllm, guidance, outlines, gguf |
| `brain/` | Agent system maintenance | memory-md-cleanup, vault-naming-convention, drewgent-runtime-checkup |
| `content/` | Content production pipeline | content-pipeline, content-management, seo-article-harvester |
| `mcp/` | MCP server integration | native-mcp, mcporter |
| `autonomous-ai-agents/` | Agent architecture patterns | acp-thinking-spinner, content-management, drewgent-update-checker |
| `gaming/` | Game automation | pokemon-player, minecraft-modpack-server |
| `taste-review/` | Trend analysis framework | 5-question analysis, leverage scoring |
| `apple/` | macOS automation | macos-computer-use |
| `social-media/` | X/Twitter integration | xitter, xurl |
| `payment/` | Korean payment gateways | payment-gateway-integration, portone-payment-integration |
| `cloudflare-workers-local-dev/` | CF Workers local dev | wrangler, workers-best-practices, cloudflare-workers-local-dev |

Skills are loaded via:
```
skill("baseline-ui")
skill("ponytail")
```

---

## Discord Integration

Two Discord integration paths:

**Discord Bot** — `scripts/discord_bot.py` connects Discord channels to opencode via `--attach` mode (port 8642):
- Creates a thread for each conversation
- Routes messages to the agent for processing
- Supports file attachments (images, documents, code)
- Chunks long messages (>2000 chars) across multiple messages
- Configured as launchd service (`ai.drewgent.discord-bot`) with auto-recovery

**Discord MCP** — `discord-mcp` stdio server for direct tool access:
- Send/edit/delete messages, reactions, file uploads
- Channel history, search, attachment download
- Presence and DM management
- Used by opencode directly for Discord operations

---

## Repository Structure

### What's in the Repo

```
~/.drewgent/
│
├── opencode.jsonc              opencode configuration (model, MCP, skills)
├── AGENTS.md                   System instructions loaded by opencode
├── .env.example                API key configuration template
├── CHANGELOG.md                Release history
├── CONTRIBUTING.md             Contribution guidelines
├── .gitignore                  Excludes personal runtime data
│
├── harness/                    Quality engineering patterns
│   └── patterns/
│       └── manufacturing-bridge.md  6‑pattern quality bridge (3‑tier enforcement)
├── launchd/                    Launchd plist templates (macOS daemons)
│   ├── ai.yourgent.opencode.plist.example
│   ├── ai.yourgent.cron.plist.example
│   └── ai.yourgent.discord-bot.plist.example
│
├── agents/                     16 subagent profile definitions
│   ├── explorer.md             Read-only analysis (flash)
│   ├── implementer.md          Code implementation (flash)
│   ├── reviewer.md             Code review (pro)
│   ├── reviewer-critical.md    Architecture review (max)
│   ├── planner.md              Task decomposition (max)
│   ├── orchestrator.md         Pipeline orchestration (pro)
│   ├── archiver.md             Documentation (flash)
│   ├── designer.md             UI/UX design (flash)
│   ├── editor.md               Content editing (pro)
│   ├── content-manager.md      Content production (pro)
│   ├── sre.md                  Infrastructure (pro)
│   ├── analyst.md              Data analysis (flash)
│   ├── security-reviewer.md    Security audit (max)
│   ├── tester.md               Test writing (inherits model)
│   └── README.md
│
├── skills/                     60+ skill categories with 100+ skills
│   ├── ui/                     UI quality standards
│   ├── devops/                 Infrastructure and automation
│   ├── software-development/   Engineering practices
│   ├── creative/               Visual and audio content
│   ├── mlops/                  ML training and inference
│   ├── brain/                  Agent maintenance
│   ├── content/                Content pipeline
│   ├── apple/                  macOS automation
│   ├── payment/                Payment gateway integration
│   └── ...
│
├── @action/                    Action-layer skills and records
│   ├── skills/                 Architecture-specific skills
│   │   ├── brain-signal-system/
│   │   ├── trend-harvester/
│   │   ├── vault-health/
│   │   └── self-replicating-agent-tdd/
│   ├── proposals/              Design proposals (tier + leverage score)
│   ├── incidents/              Incident reports and recovery patterns
│   ├── plans/                  Long-term growth plans
│   └── migrations/             Architecture migration records
│
├── @memory/                    Memory, growth, and raw data (runtime)
│   ├── growth/                 Trend harvester output, taste reviews
│   ├── knowledge/              Collected knowledge
│   ├── memories/               Session insights
│   └── sessions/               Raw session logs
│
├── scripts/                    27 automation scripts
│   ├── drewgent_cron.py        Cron dispatcher (60s interval)
│   ├── office_autopilot.sh     Kanban pending → orchestrator dispatcher
│   ├── discord_bot.py          Discord ↔ opencode gateway
│   ├── discord_send.py         Discord message chunk sender
│   ├── run_kanban_worker.py    Kanban task executor
│   ├── content_graph_builder.py Content graph engine (TF-IDF + taxonomy)
│   ├── content_diff_analyzer.py Content taste diff analysis
│   ├── trend_harvester.py      AI trend collection (GitHub)
│   ├── trend_scorer.py         Heuristic trend scoring
│   ├── trend_usage_watch.py    Trend adoption tracking
│   ├── cron_health_check.py    Health monitoring
│   ├── agent_dashboard_push.py Cloudflare dashboard pusher
│   ├── ard_query.py            ARD Registry query client
│   ├── drewgent_housekeeper.py Brain pulse + cleanup
│   ├── seo_analyzer.sh         SEO article analysis
│   ├── cron_seo_harvester.sh   SEO article collection
│   └── ...
│
├── P0-brainstem/               Survival layer — governance rules
│   ├── brain/rules.md          P0 rule documentation
│   └── brain/Drewgent-brain/   .neuron constraint files
│
├── P1-limbic/                  Identity layer
│   ├── persona/SOUL.md         Agent identity and personality
│   └── persona/writing-style-guide.md  Communication conventions
│
├── P2-hippocampus/             Memory layer (stub — data gitignored)
│   └── README.md
│
├── P3-sensors/                 Input layer (runtime gateway state)
│   ├── cron/                   Cron output, lock files
│   ├── gateway/                Gateway state and resolver
│   ├── sandboxes/              Container sandboxes
│   └── skills/                 Additional skills (deprecated — use @action/)
│
├── P4-cortex/                  Growth layer
│   ├── content/                Brand guides, narrative arc, content assets
│   ├── growth/                 Skill index, implementation plans
│   ├── knowledge/              Architecture references, templates
│   ├── insights/               Extracted patterns and learnings
│   └── README.md
│
├── P5-ego/                     Identity layer
│   ├── SELF_MODEL.md           Self-model and integration rules
│   ├── wiki/                    Compiled knowledge (LLM Wiki)
│   │   ├── index.md            Wiki master index
│   │   ├── compiled/           Compiled knowledge pages
│   │   └── lint-report.md      Wiki health report
│   └── README.md
│
├── P6-prefrontal/              Strategy layer (deprecated — use @action/)
│   └── README.md
│
└── cron/                       Scheduled job definitions
    ├── jobs.json               Job schedule (intervals, scripts)
    └── scheduler.py            Schedule resolver and dispatcher
```

### What's NOT in the Repo (Personal Data)

These directories exist in `~/.drewgent` at runtime but are excluded from git:

| Directory | Contents | Why Excluded |
|-----------|----------|--------------|
| `@memory/` | Growth data, knowledge, session logs | Personal/generated |
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

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `opencode` not found | Install: `curl -fsSL https://opencode.ai/install \| sh` or `brew install anomalyco/tap/opencode` |
| knowledge.db not found | Created automatically on first `recall()` call. Requires Ollama with `nomic-embed-text` model for embeddings |
| Rename script fails on macOS `sed` | macOS `sed` uses BSD syntax. If errors occur: `brew install gnu-sed` |
| Cron jobs don't trigger | Ensure `cron/` directory exists and `jobs.json` has `"enabled": true`. Requires `drewgent_cron.py` scheduler running |
| Merge conflicts on `git pull upstream` | `git checkout --ours <file>` to keep your version, `--theirs` to accept upstream template |
| `@identity/` placeholders showing | Edit `@identity/SELF_MODEL.md`, `@identity/persona/SOUL.md`, and `writing-style-guide.md` with your agent's identity |

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
- [lazyweb](https://lazyweb.com) — 281k+ real app screenshots for UI design reference
- [specification.website](https://specification.website) — Web spec checklists and best practices

---

## Credits

opencode-drewgent is built on the shoulders of these open-source projects:

| Project | Author | Purpose | License |
|---------|--------|---------|---------|
| [opencode](https://opencode.ai) | [Anomaly](https://github.com/anomalyco) | AI coding agent platform | MIT |
| [codebase-memory-mcp](https://github.com/anomalyco/opencode) | Anomaly | Codebase knowledge graph | MIT |
| [Gajae-Code](https://github.com/Yeachan-Heo/gajae-code) | [Yeachan-Heo](https://github.com/Yeachan-Heo) | GJC Coordinator MCP — worktree isolation, tmux parallel execution | — |
| [discord-mcp](https://github.com/anomalyco/discord-mcp) | Anomaly | Discord MCP server | MIT |
| [PortOne](https://developers.portone.io) | PortOne | Korean payment gateway SDK | — |
| [Cloudflare Agents SDK](https://developers.cloudflare.com/agents) | Cloudflare | Stateful agent framework for Workers | MIT |
| [Karpathy LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) | Andrej Karpathy | Compile-pattern knowledge base concept | — |
| [Ponytail](https://github.com/DietrichGebert/ponytail) | Dietrich Gebert | Code minimalization checklist | — |
| [NeuronFS](https://github.com/rhino-acoustic/NeuronFS) | [rhino-acoustic](https://github.com/rhino-acoustic) | Brain-based governance system | — |
| [Baseline UI](https://github.com/anomalyco/opencode) | Anomaly | UI quality standards (ibelick, claude-design, sketch) | — |
| [specification.website](https://specification.website) | [Joost de Valk](https://github.com/jdevalk) | Web spec checklists MCP | — |
| [ARD Spec](https://agenticresourcediscovery.org) | Google/MS | Agentic Resource Discovery standard | — |
| [agent-wiki](https://github.com/lazymac2x/agent-wiki) | lazymac2x | Manufacturing↔Agent harness isomorphism concept | MIT |

No third-party source code is directly included — all dependencies are referenced or installed via package managers. Each project respects its own license.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) — one change per PR, no new deps, include provenance.

## License

MIT — see [LICENSE](LICENSE). Replace with your own license when forking.

# opencode-drewgent

[🇰🇷 한국어](README.ko.md)

A personal AI agent template built on [opencode](https://opencode.ai).

This repo is a **starter kit** for building your own personal AI agent. It gives you the architecture patterns, skill system, and automation infrastructure that a solo developer would otherwise build from scratch. Fork it, rename it, and make it yours.

---

## Quick Start

```bash
# 1. Install opencode
curl -fsSL https://opencode.ai/install | sh

# 2. Fork this repo on GitHub, then clone your fork
git clone git@github.com:YOUR_USERNAME/opencode-drewgent.git ~/.youragent
cd ~/.youragent

# 3. Install dependencies and create .env
bash scripts/setup.sh

# 4. Rename everything from "drewgent" to your agent name
#    (inside opencode, run:)
skill("rename-drewgent")

# 5. Start opencode
opencode
```

---

## Architecture

### Agent System

The template uses opencode's built-in `task(subagent_type="...")` for multi-step work, plus optional GJC Coordinator MCP for isolated worktree execution. Key agent profiles are defined in `.opencode/agents/*.md`:

| Profile | Model | Purpose |
|---------|-------|---------|
| implementer | flash | Code generation, file edits |
| reviewer | pro | Code review, quality gate |
| explorer | flash | Codebase discovery, research |
| planner | pro/max | Task decomposition, planning |
| sre | flash | Infrastructure, monitoring |
| architect | pro | Architecture decisions |

### Vault (P0-P6)

The vault is an Obsidian-compatible folder structure that organizes agent identity, knowledge, and memory:

| Layer | Path | Content |
|-------|------|---------|
| **P0-brainstem** | `@identity/brain/` | Rules, constraints, 禁 (never-do) rules |
| **P1-limbic** | `@identity/persona/` | Personality, voice, writing style |
| **P2-hippocampus** | `P2-hippocampus/` | Raw archives — sessions, memories, knowledge |
| **P3-sensors** | `@action/` | Tool integrations, gateway configs |
| **P4-cortex** | `skills/` | Skill definitions, growth records |
| **P5-ego** | `@identity/SELF_MODEL.md` | Self-awareness, compiled wiki |
| **P6-prefrontal** | `P6-prefrontal/` | Incidents, retrospectives, plans |

### MCP Servers

Example MCP server configs in `opencode.jsonc`:

| Server | Type | Purpose |
|--------|------|---------|
| `codebase-memory-mcp` | local stdio | Codebase knowledge graph |
| `gajae-code` | local stdio | GJC Coordinator for isolated delegation |
| `safari` | local stdio | Web browsing |
| `astryx` | remote HTTP | Meta Astryx design system |
| `discord` | local stdio | Discord integration |

### Skill System

Skills are specialized instruction files loaded on demand via `skill("name")`. The template ships with 100+ skills organized by category:

- `skills/software-development/` — Coding patterns, refactoring, testing
- `skills/devops/` — Infrastructure, deployment, monitoring
- `skills/mlops/` — ML training, inference, fine-tuning
- `skills/creative/` — Design, architecture diagrams, content
- `skills/productivity/` — External tool integrations
- `skills/seo/` — SEO and content optimization

### Cron Automation

The template includes a cron scheduler (`scripts/drewgent_cron.py`) driven by `cron/jobs.json`. See `cron/jobs.json` for example jobs and the cron skill for setup details.

### Kanban Task Pipeline

Tasks are tracked in a SQLite kanban board (`kanban.db`). Each task can have a pipeline of subagent roles (e.g., explorer → implementer → reviewer) and a leverage score for prioritization.

---

## Customization Guide

### 1. Rename the Agent

The entire repo uses "drewgent" as a placeholder project name. Rename it:

```bash
# Option A: Inside opencode
skill("rename-drewgent")

# Option B: Manual find/replace
find ~/.youragent -type f -name "*.md" -o -name "*.py" -o -name "*.sh" -o -name "*.json" | \
  xargs sed -i '' 's/drewgent/youragent/g'
```

### 2. Set Your Identity

Edit these files to define your agent's personality:

- `@identity/SELF_MODEL.md` — Agent purpose, role, core directives
- `@identity/persona/SOUL.md` — Tone, voice, communication style
- `@identity/persona/writing-style-guide.md` — Writing conventions
- `@identity/brain/rules.md` — Behavioral rules and constraints

### 3. Configure MCP Servers

Edit `opencode.jsonc` to add your own MCP servers. The template includes configs for:
- Discord bot (requires `DISCORD_BOT_TOKEN`)
- Gajae-Code coordinator (requires `OPENCODE_API_KEY`)
- WordPress MCP server (for content management)
- Safari web browsing (macOS only)

### 4. Set Up Cron Jobs

Edit `cron/jobs.json` to add your automation. Example job format:

```json
{
  "id": "my-job",
  "name": "My Job Name",
  "enabled": true,
  "schedule": { "kind": "cron", "expr": "0 6 * * *" },
  "deliver": { "kind": "script", "script": "scripts/my_script.py" },
  "workdir": "~/",
  "max_runtime": 600
}
```

### 5. Build Your Skill Library

Remove skills you don't need, add your own. Each skill is a directory under `skills/` with a `SKILL.md` file. Browse available skills:

```bash
ls skills/*/SKILL.md
```

---

## Key Concepts

### Delegation Patterns

- **`task(subagent_type="reviewer", ...)`** — Same-model subtask. Lightweight, fast.
- **`gjc_delegate_execute(...)`** — Isolated worktree + tmux. Heavy isolation, parallel execution.
- **`gjc_delegate_team(...)`** — Parallel multi-agent orchestration.

### Provenance Convention

Every artifact records why it was created:

```yaml
trigger: "what problem or request caused this"
provenance:
  session: "YYYY-MM-DD topic"
  decision: "why this approach, what alternatives"
```

### Tiered Autonomy

| Tier | Scope | Authority |
|------|-------|-----------|
| 1 | Typos, minor edits | Autonomous. Complete and report. |
| 2 | Established patterns | Autonomous. Include provenance. |
| 3 | Structural changes | Propose → wait for approval. |
| 4 | Architecture/roadmap | Proposal only. Human decides. |

### Important Policies

- **Filesystem = truth** — State and preferences live on disk, not in context
- **QA gate** — Never declare completion without verification
- **No big-bang refactoring** — One change at a time, verify between each
- **Ponytail principle** — YAGNI, stdlib first, no new dependencies unless necessary
- **Answer-first** — Conclusion before process in CLI output

---

## Generated Content Attribution

For public-facing content only (blog posts, tweets, demos):

```
Built with [opencode-drewgent](https://github.com/humanerd-drew/opencode-drewgent)
```

---

## Known Pitfalls

### Python 3.14: json scope bug
Large functions using `except json.JSONDecodeError:` cause `UnboundLocalError` on `json.loads()`. Fix: `__import__('json').loads()` or extract to a wrapper function.

### macOS bash 3.2
No associative arrays. Use `date -j -f`. Avoid `set -u` with undefined variables.

### Launchd plist pattern
All services should use `KeepAlive { SuccessfulExit: false, ThrottleInterval: 10 }`. Do not use bare `<true/>` or `<false/>`.

### Token/cost data = SQLite, not stderr
opencode stderr logs show `tokens.input=0`. Real usage data is in `~/.local/share/opencode/opencode.db`.

---

## License

MIT — replace with your own license when forking.

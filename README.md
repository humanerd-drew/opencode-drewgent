---

title: Drewgent Root README
type: guide
space: concept
tags: [concept]
created: 2026-05-20
updated: 2026-06-23
links:
  - "[[@identity/SELF_MODEL]]"
---


# Drewgent Agent ☤

> **Drewgent** is a **Stateful Agent** — not just a tool, but a persistent, self-evolving presence that remembers, grows, and governs itself over time.

<p align="center">
  <a href="https://github.com/humanerd-drew/opencode-drewgent"><img src="https://img.shields.io/badge/GitHub-humanerd--drew/opencode--drewgent-orange?style=for-the-badge" alt="GitHub"></a>
  <a href="https://github.com/humanerd-drew/opencode-drewgent/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License: MIT"></a>
</p>

---

## The Problem

Most agents today are **stateless by design**. Every conversation starts fresh. Every session loses context. The agent has no memory, no identity continuity, no growth.

```
Stateless Agent:  User → [Session 1] → [Session 2] → [Session 3] → ...
                  Each session: isolated, no memory, no growth

Stateful Agent:   User → [Session 1] → [accumulated memory] → [Session N]
                  Drewgent persists context, refines behavior, remembers everything
```

This isn't just about remembering chat history. It's about a system that:

- **Persists identity** — knows who it is and how it differs from other agents
- **Maintains memory** — learns from every session, not just the current one
- **Governs itself** — follows rules that persist across all interactions
- **Grows continuously** — improves its own behavior through structured feedback

Drewgent implements this through a **7-layer subsumption architecture** modeled on biological brain structure, where each layer has a distinct role in maintaining statefulness.

---

## 7-Layer Architecture

Drewgent's architecture is modeled on the hierarchical structure of the human brain — from brainstem (survival) through limbic system (emotion/values) to prefrontal cortex (strategy).

```
╔══════════════════════════════════════════════════════════════╗
║  P6-prefrontal  │  Strategy  │  Long-term planning, goals     ║
╠══════════════════════════════════════════════════════════════╣
║  P5-ego         │  Identity  │  Self-model, integration rules  ║
╠══════════════════════════════════════════════════════════════╣
║  P4-cortex      │  Growth    │  Learning, pattern recognition  ║
╠══════════════════════════════════════════════════════════════╣
║  P3-sensors     │  Input     │  Tool/skill routing, triggers  ║
╠══════════════════════════════════════════════════════════════╣
║  P2-hippocampus │  Memory    │  Context persistence, wiki      ║
╠══════════════════════════════════════════════════════════════╣
║  P1-limbic      │  Values    │  Tone, persona, communication  ║
╠══════════════════════════════════════════════════════════════╣
║  P0-brainstem   │  Survival  │  CRITICAL: absolute prohibitions ║
╚══════════════════════════════════════════════════════════════╝
```

### Information Flow

**Bottom-Up (sensation → memory → growth → identity → strategy)**

```
P3-sensors:  Detects input, routes to appropriate tools
P2-hippocampus: Stores context, loads relevant memories
P4-cortex:   Recognizes patterns, triggers learning
P5-ego:      Integrates new information into self-model
P6-prefrontal: Forms strategic decisions based on all above
```

**Top-Down (identity governs behavior)**

```
P5-ego: "I am a careful, thorough agent"
         → shapes P3 tool selection
         → influences P1 tone
         → guides P4 learning direction
```

### P0 Overrides Everything

The most critical design principle: **P0 (brainstem) rules cannot be bypassed by any upper layer.**

```
Example: User asks to "rm -rf /"
  → P0-brainstem detects dangerous operation
  → Blocks before any tool execution
  → No upper layer (P1-P6) can override
```

This is **Governance as Code** — not advisory principles, but enforced constraints.

---

## Deep Dive: Critical Layers

### P0-brainstem: Governance as Code

The brainstem contains **forbidden rules (禁)** that are never bypassed, no matter what the user or upper layers request.

Each rule is a `.neuron` file — a self-contained constraint with:

```
# Rule: 禁RULE_NAME
# Token: 禁RULE_NAME
# Priority: P0 (HIGHEST)
# FORBIDDEN: what is not allowed
# REASON: why this rule exists
```

**Core P0 rules:**

| Rule | Forbidden Behavior | Why |
|------|-------------------|-----|
| `禁rm_rf_root` | `rm -rf` on root/system paths | Catastrophic data loss risk |
| `禁blind_write` | Writing code without reading first | Corruption, misalignment |
| `禁secrets_in_code` | Hardcoded API keys, tokens in code | Security breach risk |
| `禁console_log` | `console.log` / `print()` in production | Log pollution, debugging leaks |
| `禁task_qa_gate` | Declaring done without QA verification | Completion bias defense |
| `禁tool_integration_3file` | Tool integration without all 3 files | Incomplete integration breaks workflows |
| `禁karpathy_coding_principles` | Violating any of 4 coding principles | Common LLM coding mistakes |
| `禁auto_validate` | Dangerous ops without validation | Pre-validation hook required |
| `禁subagent_verify` | Subagent output unverified | Verification checklist required |
| `禁filesystem_truth` | Trust tool output over file read | Must read file directly |
| `禁rebac_integration` | RBAC integration without full chain | Incomplete access control |
| `禁rebac_kanban` | Kanban state without manifest sync | Kanban-orphan task drift |

**How it works:** At runtime, `brain_processor.py` classifies every task by type (coding, dangerous operation, tool integration, etc.) and fires relevant P0 rules as **actionable constraints** — not passive injection, but active gating.

**Where rules live:** `~/.drewgent/brain/Drewgent-brain/P0-brainstem/`

---

### P2-hippocampus: Memory Persistence

The hippocampus handles all forms of persistence — session state, long-term knowledge, and learned patterns.

#### Session Continuity (SQLite + FTS5)

`drewgent_state.py` provides persistent session storage:

```python
# WAL mode for concurrent access
# FTS5 virtual table for full-text search across all sessions
# Session chains: parent_session_id links compressed sessions
# Source tagging: 'cli', 'telegram', 'discord' — filterable
```

Every message, tool call, and token count is persisted. Sessions are searchable by content. When Drewgent starts a new session, it can retrieve relevant context from previous sessions.

#### Knowledge Base (Obsidian Wiki)

`auto_learn.py` maintains an Obsidian-compatible wiki at `~/.drewgent/memories/`:

```
entities/          # User profile, preferences, corrections
concepts/          # Learned concepts, patterns
insights/          # Extracted insights (daily logs)
retired/           # Retired/merged entries
```

**What gets stored:**
- User communication style (concise/detailed preferences)
- Environment facts (OS, installed tools, project conventions)
- Corrections (what the user rejected and why)
- Learned patterns (successful workflows)

**How it works:** After every session, `AutoLearner.run_maintenance()` runs:
- `retire_stale_entries()` — decision-matrix retirement (180d hard, 90d cold)
- `deduplicate_wiki()` — removes duplicate daily logs
- `detect_knowledge_gaps()` — identifies topics without wiki coverage

**Access pattern:**
```python
query_wiki() → loads relevant entries → injects into prompt context
             → records access frequency for retirement decisions
```

---

### P4-cortex: Self-Growth Loop

The cortex recognizes patterns and drives autonomous improvement.

#### AutoLearner: Knowledge Pipeline

```
Session End → Extract patterns → Classify insight type
           → Write to wiki (entities/concepts/insights)
           → Detect knowledge gaps → Suggest exploration
```

**Insight classification:**

| Type | Wiki Category | Tags |
|------|--------------|------|
| `preference` | entities/preferences | user, preference |
| `correction` | entities/corrections | user, correction |
| `os` / `tool` / `project` | entities/environment | environment |
| `style_concise` / `style_detailed` | entities/communication-style | user, communication |

#### Knowledge Gap Detection

`detect_knowledge_gaps()` identifies topics the user works on but the wiki doesn't cover. `fill_gap()` can autonomously explore and record new knowledge.

#### Brain Signal System

`signal_processor.py` tracks integration workflows and emits awareness signals. This is Drewgent's **event-driven P0-brainstem enforcement** — not scattered if-checks, but centralized signal handlers.

**Event Chain:**

```
turn.start
  └→ _on_turn_start()
        └→ pattern detect: rm -rf / chmod 777 / sudo
        └→ emit("dangerous.op") → _on_dangerous_op()
                                      └→ _dangerous_ops_history += [op]
                                      └→ awareness.integrity (if severity=high)

turn.end
  └→ _on_turn_end()
        └→ check 禁blind_write: write_file without prior read
        └→ check 禁secrets_in_code: sk-/ghp-/password= in tool args
        └→ check 禁console_log: console.log/print() in code
        └→ emit("rule.violation") → _on_rule_violation()
                                      └→ _violation_history += [{rule, tool, severity}]
                                      └→ awareness.integrity

agent.complete
  └→ _on_agent_complete()
        ├→ for wf in _active_workflows:
        │    if not wf.completed:
        │        emit("workflow.incomplete") → _on_workflow_incomplete()
        │                                            └→ _workflow_history += archived
        └→ emit("session.violations") (by-rule summary)

integration.complete → _on_integration_complete() → awareness.integrity
```

**Tracking State:**

| Field | Type | Purpose |
|-------|------|---------|
| `_violation_history` | `List[dict]` | All rule.violation events across session |
| `_dangerous_ops_history` | `List[dict]` | All dangerous.op events across session |
| `_workflow_history` | `List[dict]` | Archived incomplete workflows |
| `_active_workflows` | `Dict[corr_id, IntegrationWorkflow]` | Active tool/skill integrations |

**IntegrationWorkflow States:**

```
detected → started → step_1 → step_2 → completed
                      ↓
                   (P4 provides next hint)
```

**12 P0-Brainstem Rules (Enforced by signal_processor):**

| Rule | Token | Enforcement |
|------|-------|-------------|
| `禁rm_rf_root` | `rm -rf` on root paths | Pre-validation before execution |
| `禁blind_write` | write_file without prior read | `turn.end` → `rule.violation` |
| `禁task_qa_gate` | Complete without QA | Contract-first QA gate required |
| `禁secrets_in_code` | API keys hardcoded in code | `turn.end` → `rule.violation` |
| `禁auto_validate` | Dangerous ops without validation | Pre-validation hook required |
| `禁console_log` | console.log/print() in production | `turn.end` → `rule.violation` |
| `禁subagent_verify` | Subagent output unverified | Verification checklist required |
| `禁filesystem_truth` | Trust tool output over file read | Must read file directly |
| `禁tool_integration_3file` | Partial tool integration | `turn.end` → `workflow.incomplete` |
| `禁karpathy_coding_principles` | Violating 4 coding principles | `turn.end` → `rule.violation` |
| `禁rebac_integration` | RBAC integration without full chain | `turn.end` → `rule.violation` |
| `禁rebac_kanban` | Kanban state without manifest sync | `turn.end` → `rule.violation` |

**ArchitectureModel:**

```python
class ArchitectureModel:
    TOOL_INTEGRATION_FILES = ["tools/", "model_tools.py", "toolsets.py"]
    SKILL_INTEGRATION_FILES = ["skills/", "agent/skill_commands.py"]

    detect_tool_integration_progress(source_file)
        → is_complete + missing_files + next_hint

    detect_skill_integration_progress(source_file)
        → is_complete + missing_files + next_hint
```

**Components:**

| Component | File | Role |
|-----------|------|------|
| `SignalEmitter` | `agent/brain_signals.py` | API for emitting events |
| `BrainEvent + EventBus` | `agent/event_bus.py` | Singleton pub/sub event bus |
| `SignalProcessor` | `agent/signal_processor.py` | All P0 handlers + IntegrationWorkflow tracking |
| `AwarenessReporter` | `agent/awareness_reporter.py` | Hint generation + delivery |

---

### P5-ego: Identity Integration

The ego maintains Drewgent's self-model — what it knows about its own architecture and how it differs from other agents.

#### ArchitectureModel

`signal_processor.py` contains the `ArchitectureModel` singleton:

```python
class ArchitectureModel:
    # Tracks tool/skill integration status
    # Loads rules from P0-brainstem neurons
    # Emits hints for active workflows

    TOOL_INTEGRATION_FILES = ["tools/", "model_tools.py", "toolsets.py"]
    SKILL_INTEGRATION_FILES = ["skills/", "agent/skill_commands.py"]
```

**What it does:**
- Detects incomplete integrations (3-file rule enforcement)
- Maintains meta-awareness of current workflows
- Injects contextual hints into user messages at turn boundaries

#### Self-Branching

`agent/self_brancher.py` enables the agent to create and manage parallel working contexts — exploring alternatives without losing the primary task.

---

## Stateful Implementation: How It Actually Works

### Signal Flow Per Turn

```
1. User message arrives
2. BrainProcessor.classify(task_type)
   → P3-sensors detects task category
   → P0-brainstem fires relevant forbidden rules
   → P2-hippocampus loads relevant memories
3. Hint injection: active workflows append guidance to prompt
4. LLM call — guided by P0 constraints + P2 context
5. Tool execution → signal emission (tool_start, agent_modifying, tool_complete)
6. Session end → AutoLearner extracts + writes to wiki
7. Workflow persistence → saved to SQLite for next session
```

### Session Persistence

```python
# Every session logged to SQLite
SessionDB.insert_message(role, content, tool_calls, tokens)
SessionDB.search(query)  # FTS5 full-text search across all history
SessionDB.get_context(session_id, limit=10)  # recent conversation
SessionDB.get_insights(user_id)  # accumulated learnings
```

### Memory Continuity

```
[Session N]
    ↑
    │  ← draws from P2-hippocampus (last session's context, wiki)
    │
[Session N-1] → AutoLearner extracts patterns → wiki
[Session N-2] → ...
[Session 1]   → ...
```

Drewgent doesn't just remember the current conversation — it remembers the relationship across all sessions.

---

## Governance as Code: P0 Rules in Practice

### Example: `禁tool_integration_3file`

When the user asks to add a new tool:

```
1. BrainProcessor classifies → TOOL_INTEGRATION task
2. P0 fires 禁tool_integration_3file rule
3. ArchitectureModel.detect_tool_integration_progress() tracks
4. Agent MUST complete all 3 files:
   - tools/<name>_tool.py (handler + registry.register())
   - model_tools.py (_discover_tools() import)
   - toolsets.py (toolset assignment)
5. QA gate: cannot declare done until all 3 verified
```

If the agent tries to skip any step, P0 blocks completion.

### Example: `禁karpathy_coding_principles`

When working on code:

```
1. Task classified as CODING → P0 fires karpathy rules
2. Before writing: state assumptions (Rule 1)
3. Minimum code: no overengineering (Rule 2)
4. Surgical: only touch what must be touched (Rule 3)
5. Goal-driven: success criteria defined, tests written (Rule 4)
6. Completion: Harsh Critic check before declaring done
```

These aren't suggestions — they're enforced by P0 at runtime.

---

## Project Structure

```
drewgent/
├── run_agent.py           # Core agent loop, tool dispatch, brain loop
├── drewgent_state.py         # SQLite session store (FTS5 search)
├── model_tools.py          # Tool registry, _discover_tools(), dispatch
├── toolsets.py             # Tool groupings (HERMES_CORE_TOOLS, etc.)
├── agent/
│   ├── brain_processor.py     # Organic runtime — task classification, P0-P6 weights
│   ├── signal_processor.py     # ArchitectureModel, workflow tracking, hints
│   ├── brain_signals.py        # Signal emission (tool_start, agent_modifying, ...)
│   ├── auto_learn.py           # Obsidian wiki maintenance, insight extraction
│   ├── brain_monitor.py        # Real-time brain state monitoring
│   ├── context_compressor.py   # Auto context compression
│   └── display.py              # KawaiiSpinner, tool preview formatting
├── drewgent_cli/
│   ├── brain_manager.py        # Brain loading, P0 neuron scanning
│   ├── skin_engine.py          # YAML-based skin/theme customization
│   └── commands.py              # Slash command registry
├── tools/                  # Tool implementations (one file per tool)
├── gateway/               # Messaging platform gateway (Discord, Telegram, etc.)
└── brain/
    └── Drewgent-brain/
        └── P0-brainstem/   # 禁rules — enforced constraints (.neuron files)
```

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/humanerd-drew/opencode-drewgent.git
cd drewgent

# 2. Install
uv venv .venv --python 3.11
source .venv/bin/activate
uv pip install -e ".[all]"

# 3. Configure
cp .env.example .env
# Edit .env — add your MiniMax (M3) API key

# 4. Run
drewgent
```

### Configuration

Provider selection and skin customization are in `~/.drewgent/config.yaml` (created on first run via `drewgent setup`).

**Important:** If your `.drewgent` directory is on an external volume or different path, set `DREW_HOME`:
```bash
export DREW_HOME=/Volumes/drew/.drewgent
```
The runtime resolves `DREW_HOME` first; without it, defaults to `~/.drewgent`.

**Provider setup** (`$DREW_HOME/.env`):
```bash
MINIMAX_API_KEY=***      # default
OPENROUTER_API_KEY=***
GOOGLE_API_KEY=***
```

**Skin selection**:
```yaml
display:
  skin: ares      # alternatives: default, mono, slate, ares
```

Or change at runtime: `/skin ares`

---

## What Makes Drewgent Different

| Aspect | Traditional Agent | Drewgent |
|--------|------------------|----------|
| Session start | Blank slate | Loads accumulated memory from P2 |
| Identity | Generic | ArchitectureModel tracks self-knowledge |
| Rules | Advisory | P0-brainstem enforces — cannot bypass |
| Learning | Session-only | Continuous: wiki + gap detection |
| Growth | None | AutoLearner + self-brancher |
| Tool integration | Partial | 3-file rule enforced by P0 |
| Context | Current chat only | FTS5 search across all sessions |

---

## Recent Changes

### v0.8 — 2026-06-22: Architecture Compression

#### P-Layer 7→3 Restructuring

The most significant change: the original 7-layer P0–P6 vault structure has been logically consolidated into 3 top-level directories. The P-layer directories (`P0-brainstem/` … `P6-prefrontal/`) still exist on disk for local runtime compatibility but are now **gitignored** — all tracked content lives under the new `@-` prefix structure.

| New Path | Contains | Former P-Layers |
|----------|----------|-----------------|
| `@identity/` | Self-model, rules, persona, voice, writing style | P0-brainstem, P1-limbic, P5-ego |
| `@memory/` | Raw archive, memories, sessions, knowledge (gitignored — runtime data) | P2-hippocampus, P4-cortex (archive) |
| `@action/` | Skills, plans, incidents, migrations, proposals | P3-sensors, P4-cortex (active), P6-prefrontal |

**28,347 wikilinks** updated across the codebase from `[[P[0-6]-*` references to `@identity/`, `@memory/`, `@action/` paths. All internal cross-references, AGENTS.md links, and vault graph connections migrated.

#### Agent Profiles 14→6

| Merged Profile | Absorbed Roles | Model |
|---------------|----------------|-------|
| explorer | analyst | deepseek-v4-flash |
| implementer | tester | kimi-k2.7-code |
| reviewer | editor | deepseek-v4-pro |
| reviewer-critical | security-reviewer | qwen3.7-plus |
| planner | orchestrator, sre | qwen3.7-max |
| archiver | content-manager | deepseek-v4-flash |

Profile count halved. The `designer` role migrated from an agent profile to the `skills/ui/designer/SKILL.md` skill — loadable on demand rather than consuming a slot.

#### Pipeline 5→3

Pipeline stages reduced from 5 (explore → implement → test → review → archive) to 3 (explore → implement → review). The tester and archiver stages are removed from the pipeline definition; **archiver now runs automatically as a post-hook** when a task completes, without requiring an explicit pipeline slot.

#### MCP Conditional Activation

Previously all 3 MCP servers ran continuously:
- **gbrain** — always-on (the brain)
- **lazyweb** — now `enabled: false` in `opencode.jsonc`; activated via `skill("lazyweb")`
- **specification-website** — now `enabled: false`; activated on demand

This reduces baseline resource usage. Both remain available when their skills are loaded.

#### Scripts & Tools Cleanup

| Category | Before | After | Archived |
|----------|--------|-------|----------|
| Scripts | 43 | 25 active | 18 archived |
| Tools | 58 | 36 active | 22 archived |

Archived files are removed from the repository but remain in git history. The `scripts/INDEX.md` documents which scripts are active vs archived.

#### Provenance Frontmatter Removed

The `trigger:` and `provenance:` frontmatter fields originally added to track decision provenance were removed from 27 SKILL.md files. These fields were not being consumed by any runtime process and added visual noise to every skill file. The provenance convention is preserved as an operational guideline in AGENTS.md — files are no longer required to carry it in frontmatter.

#### .gitignore Changes

- `/P0-brainstem/` … `/P5-ego/` — **added** (runtime-only symlinks, not tracked)
- `/P6-prefrontal/archive/`, `checkpoints/`, `recovery-journal/` — **added** (runtime output)
- `@identity/` — **removed** from gitignore (must be tracked — core identity files)
- `@action/skills/.hub/` — **added** (runtime cache)
- scripts that were archived are no longer tracked

#### Files Affected

127 files changed, 9,574 insertions, 16,890 deletions across the repository.

Full details in [`CHANGELOG.md`](CHANGELOG.md).

---

## Getting Started (Fork + Customize)

This repository is a **template** for building your own opencode-based AI agent. Fork it, rename it, configure it, and run.

### Prerequisites

- **[opencode](https://opencode.ai)** CLI installed (`brew install opencode` or via GitHub Releases)
- **Git** with SSH access to GitHub
- **Python 3.11+** (for agent scripts and cron tools)
- **(Optional) [gbrain](https://github.com/garrytan/gbrain)** for persistent knowledge graph (MCP server)

### 1. Fork

```bash
# 1. Fork on GitHub → https://github.com/humanerd-drew/opencode-drewgent
# 2. Clone your fork:
git clone git@github.com:YOUR_USER/opencode-YOURAGENT.git
cd opencode-YOURAGENT

# 3. Add upstream to receive future updates:
git remote add upstream git@github.com:humanerd-drew/opencode-drewgent.git
git fetch upstream
```

### 2. Rename

Two options — use the automated script or do it manually.

#### Option A: Automated (recommended)

```bash
bash scripts/rename-drewgent.sh "youragent"
```

This script replaces all `drewgent` references across 2000+ files:

| What | Example Change |
|------|---------------|
| Directory name | `~/.drewgent/` → `~/.youragent/` |
| Config paths | `~/.drewgent/skills` → `~/.youragent/skills` |
| Env vars | `DREW_HOME` → `YOURAGENT_HOME` |
| Project name | `Drewgent` → `Youragent` (capitalized) |
| Code references | `drewgent` → `youragent` in inline paths |
| Script headers | `Drewgent agent system` → `Youragent agent system` |
| `opencode.jsonc` | Updated skill paths, MCP commands |
| `AGENTS.md` | All references rewritten |

After running, verify with:
```bash
grep -r "drewgent" . --include="*.md" --include="*.py" --include="*.json" --include="*.jsonc" 2>/dev/null | head -5
# Should return nothing (all replaced)
```

#### Option B: Manual

If the script doesn't fit your needs, update these files by hand:

- **`opencode.jsonc`** — change `model`, skill `paths`, MCP server `command`
- **`AGENTS.md`** — update project name, links, identity references
- **`cron/jobs.json`** — set your Discord channel IDs in `deliver` fields
- **`@identity/`** — rewrite `SELF_MODEL.md`, `SOUL.md`, `brain/rules.md` for your agent's persona
- **`scripts/`** — update hardcoded paths in shell scripts
- **`~/.config/opencode/opencode.jsonc`** — point to your fork's config

### 3. Configure Core Files

#### `opencode.jsonc`

| Field | What to Set |
|-------|-------------|
| `model` | Your default model, e.g. `opencode-go/deepseek-v4-flash` |
| `small_model` | Fallback model for simple tasks |
| `skills.paths` | Directories where opencode looks for skills |
| `mcp.gbrain` | gbrain MCP server command (set to `gbrain serve` or disable) |
| `mcp.lazyweb` | Optional UI design MCP — set `enabled: false` if unused |
| `mcp.specification-website` | Optional web spec MCP — set `enabled: false` if unused |

#### `cron/jobs.json`

Open `cron/jobs.json` and replace every `discord:YOUR_*_CHANNEL_ID` with your actual Discord channel IDs. Jobs with `"deliver": "local"` run without Discord delivery — they're safe as-is.

Jobs include:
- `kanban-dispatcher` — checks kanban tasks every minute (auto-enabled if you use kanban)
- `trend-collect` — collects GitHub trending repos (requires Discord channel)
- `seo-article-harvester` — RSS feed monitoring (requires Discord channel)
- `wiki-compile` / `wiki-lint` — weekly wiki compilation
- `daily retro` — daily work summary (requires Discord channel)

#### `AGENTS.md`

This is your agent's **constitution** — rewrite it for your persona:
- Tone: how your agent communicates (concise? detailed? casual?)
- Rules: P0-brainstem prohibitions (what must never be done)
- Identity: what your agent knows about itself
- Skills: which skills are loaded by default
- Kanban pipeline: how work flows through your agent

#### `@identity/` (Agent Identity)

| File | Purpose |
|------|---------|
| `SELF_MODEL.md` | What your agent knows about itself — architecture, capabilities |
| `SOUL.md` | Core personality, tone, and voice |
| `brain/rules.md` | P0-brainstem absolute prohibitions |
| `persona/writing-style-guide.md` | Writing conventions |

### 4. Run

```bash
# Start opencode with your config:
opencode --config opencode.jsonc
```

Your agent will load:
1. `AGENTS.md` as system instructions
2. All skills from configured paths
3. MCP servers (gbrain for knowledge, optional servers)
4. Cron jobs from `cron/jobs.json` (if cron is enabled)

### Staying Updated

```bash
git pull upstream main
```

This pulls the latest v0.8+ updates from the template. If there are conflicts:

```bash
# Accept upstream changes for template files (losing your customizations):
git checkout --theirs opencode.jsonc
# Or keep your version:
git checkout --ours opencode.jsonc
# Then commit the merge:
git commit
```

**Important:** The `rename-drewgent.sh` script and `README.md` are designed to be overwritten by upstream — your personal config lives in `opencode.jsonc`, `cron/jobs.json`, `AGENTS.md`, and `@identity/`.

### Troubleshooting

| Problem | Solution |
|---------|----------|
| `opencode` not found | Install opencode: `brew install anomalyco/tap/opencode` or download from [releases](https://github.com/anomalyco/opencode/releases) |
| `gbrain` not found | Install from [garrytan/gbrain](https://github.com/garrytan/gbrain) or set `"enabled": false` in `opencode.jsonc` |
| Rename script fails on macOS `sed` | macOS `sed` handles BSD syntax. If you see errors, install GNU sed: `brew install gnu-sed` |
| Cron jobs don't trigger | Check `cron/` directory exists and `jobs.json` has `"enabled": true`. Cron requires `drewgent_cron.py` scheduler running |
| Merge conflicts on `git pull upstream` | `git checkout --ours <file>` to keep your version, or `--theirs` to accept upstream. Then commit |

---

## License

MIT — [YOUR_PROJECT_NAME](https://your-domain.example)
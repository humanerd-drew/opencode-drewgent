---

title: Contributing
type: guide
space: concept
tags: [concept]
created: 2026-05-20
updated: 2026-05-20
links: []
links:
  - "[[P5-ego/SELF_MODEL]]"
---


# Contributing to Drewgent Agent

Thank you for contributing to Drewgent Agent! This guide covers everything you need: setting up your dev environment, understanding the architecture, deciding what to build, and getting your PR merged.

---

## Contribution Priorities

We value contributions in this order:

1. **Bug fixes** — crashes, incorrect behavior, data loss. Always top priority.
2. **Cross-platform compatibility** — Windows, macOS, different Linux distros, different terminal emulators. We want Drewgent to work everywhere.
3. **Security hardening** — shell injection, prompt injection, path traversal, privilege escalation. See [Security](#security-considerations).
4. **Performance and robustness** — retry logic, error handling, graceful degradation.
5. **New skills** — but only broadly useful ones. See [Should it be a Skill or a Tool?](#should-it-be-a-skill-or-a-tool)
6. **New tools** — rarely needed. Most capabilities should be skills. See below.
7. **Documentation** — fixes, clarifications, new examples.

---

## Should it be a Skill or a Tool?

This is the most common question for new contributors. The answer is almost always **skill**.

### Make it a Skill when:

- The capability can be expressed as instructions + shell commands + existing tools
- It wraps an external CLI or API that the agent can call via `terminal` or `web_extract`
- It doesn't need custom Python integration or API key management baked into the agent
- Examples: arXiv search, git workflows, Docker management, PDF processing, email via CLI tools

### Make it a Tool when:

- It requires end-to-end integration with API keys, auth flows, or multi-component configuration managed by the agent harness
- It needs custom processing logic that must execute precisely every time (not "best effort" from LLM interpretation)
- It handles binary data, streaming, or real-time events that can't go through the terminal
- Examples: browser automation (Browserbase session management), TTS (audio encoding + platform delivery), vision analysis (base64 image handling)

### Should the Skill be bundled?

Bundled skills (in `skills/`) ship with every Drewgent install. They should be **broadly useful to most users**:

- Document handling, web research, common dev workflows, system administration
- Used regularly by a wide range of people

If your skill is official and useful but not universally needed (e.g., a paid service integration, a heavyweight dependency), put it in **`optional-skills/`** — it ships with the repo but isn't activated by default. Users can discover it via `drewgent skills browse` (labeled "official") and install it with `drewgent skills install` (no third-party warning, builtin trust).

If your skill is specialized, community-contributed, or niche, it's better suited for a **Skills Hub** — upload it to a skills registry and share it in the [HUMANERD Discord](https://discord.gg/NousResearch). Users can install it with `drewgent skills install`.

---

## Development Setup

### Prerequisites

| Requirement | Notes |
|-------------|-------|
| **Git** | With `--recurse-submodules` support |
| **Python 3.11+** | uv will install it if missing |
| **uv** | Fast Python package manager ([install](https://docs.astral.sh/uv/)) |
| **Node.js 18+** | Optional — needed for browser tools and WhatsApp bridge |

### Clone and install

```bash
git clone --recurse-submodules https://github.com/NousResearch/drewgent-agent.git
cd drewgent-agent

# Create venv with Python 3.11
uv venv venv --python 3.11
export VIRTUAL_ENV="$(pwd)/venv"

# Install with all extras (messaging, cron, CLI menus, dev tools)
uv pip install -e ".[all,dev]"

# Optional: RL training submodule
# git submodule update --init tinker-atropos && uv pip install -e "./tinker-atropos"

# Optional: browser tools
npm install
```

### Configure for development

```bash
mkdir -p ~/.drewgent/{cron,sessions,logs,memories,skills}
cp cli-config.yaml.example ~/.drewgent/config.yaml
touch ~/.drewgent/.env

# Add at minimum an LLM provider key:
echo 'OPENROUTER_API_KEY=sk-or-v1-your-key' >> ~/.drewgent/.env
```

### Run

```bash
# Symlink for global access
mkdir -p ~/.local/bin
ln -sf "$(pwd)/venv/bin/hermes" ~/.local/bin/hermes

# Verify
drewgent doctor
hermes chat -q "Hello"
```

### Run tests

```bash
pytest tests/ -v
```

---

## Project Structure

```
drewgent-agent/
├── run_agent.py              # AIAgent class — core conversation loop, tool dispatch, session persistence
├── cli.py                    # DrewgentCLI class — interactive TUI, prompt_toolkit integration
├── model_tools.py            # Tool orchestration (thin layer over tools/registry.py)
├── toolsets.py               # Tool groupings and presets (drewgent-cli, drewgent-telegram, etc.)
├── drewgent_state.py           # SQLite session database with FTS5 full-text search, session titles
├── batch_runner.py           # Parallel batch processing for trajectory generation
│
├── agent/                    # Agent internals (extracted modules)
│   ├── prompt_builder.py         # System prompt assembly (identity, skills, context files, memory)
│   ├── context_compressor.py     # Auto-summarization when approaching context limits
│   ├── auxiliary_client.py       # Resolves auxiliary OpenAI clients (summarization, vision)
│   ├── display.py                # KawaiiSpinner, tool progress formatting
│   ├── model_metadata.py         # Model context lengths, token estimation
│   └── trajectory.py             # Trajectory saving helpers
│
├── drewgent_cli/               # CLI command implementations
│   ├── main.py                   # Entry point, argument parsing, command dispatch
│   ├── config.py                 # Config management, migration, env var definitions
│   ├── setup.py                  # Interactive setup wizard
│   ├── auth.py                   # Provider resolution, OAuth, Nous Portal
│   ├── models.py                 # OpenRouter model selection lists
│   ├── banner.py                 # Welcome banner, ASCII art
│   ├── commands.py               # Central slash command registry (CommandDef), autocomplete, gateway helpers
│   ├── callbacks.py              # Interactive callbacks (clarify, sudo, approval)
│   ├── doctor.py                 # Diagnostics
│   ├── skills_hub.py             # Skills Hub CLI + /skills slash command
│   └── skin_engine.py            # Skin/theme engine — data-driven CLI visual customization
│
├── tools/                    # Tool implementations (self-registering)
│   ├── registry.py               # Central tool registry (schemas, handlers, dispatch)
│   ├── approval.py               # Dangerous command detection + per-session approval
│   ├── terminal_tool.py          # Terminal orchestration (sudo, env lifecycle, backends)
│   ├── file_operations.py        # read_file, write_file, search, patch, etc.
│   ├── web_tools.py              # web_search, web_extract (Parallel/Firecrawl + Gemini summarization)
│   ├── vision_tools.py           # Image analysis via multimodal models
│   ├── delegate_tool.py          # Subagent spawning and parallel task execution
│   ├── code_execution_tool.py    # Sandboxed Python with RPC tool access
│   ├── session_search_tool.py    # Search past conversations with FTS5 + summarization
│   ├── cronjob_tools.py          # Scheduled task management
│   ├── skill_tools.py            # Skill search, load, manage
│   └── environments/             # Terminal execution backends
│       ├── base.py                   # BaseEnvironment ABC
│       ├── local.py, docker.py, ssh.py, singularity.py, modal.py, daytona.py
│
├── gateway/                  # Messaging gateway
│   ├── run.py                    # GatewayRunner — platform lifecycle, message routing, cron
│   ├── config.py                 # Platform configuration resolution
│   ├── session.py                # Session store, context prompts, reset policies
│   └── platforms/                # Platform adapters
│       ├── telegram.py, discord_adapter.py, slack.py, whatsapp.py
│
├── scripts/                  # Installer and bridge scripts
│   ├── install.sh                # Linux/macOS installer
│   ├── install.ps1               # Windows PowerShell installer
│   └── whatsapp-bridge/          # Node.js WhatsApp bridge (Baileys)
│
├── skills/                   # Bundled skills (copied to ~/.drewgent/skills/ on install)
├── optional-skills/          # Official optional skills (discoverable via hub, not activated by default)
├── environments/             # RL training environments (Atropos integration)
├── tests/                    # Test suite
├── website/                  # Documentation site (drewgent-agent.humanerd.ai)
│
├── cli-config.yaml.example   # Example configuration (copied to ~/.drewgent/config.yaml)
└── AGENTS.md                 # Development guide for AI coding assistants
```

### User configuration (stored in `~/.drewgent/`)

| Path | Purpose |
|------|---------|
| `~/.drewgent/config.yaml` | Settings (model, terminal, toolsets, compression, etc.) |
| `~/.drewgent/.env` | API keys and secrets |
| `~/.drewgent/auth.json` | OAuth credentials (Nous Portal) |
| `~/.drewgent/skills/` | All active skills (bundled + hub-installed + agent-created) |
| `~/.drewgent/memories/` | Persistent memory (MEMORY.md, USER.md) |
| `~/.drewgent/state.db` | SQLite session database |
| `~/.drewgent/sessions/` | JSON session logs |
| `~/.drewgent/cron/` | Scheduled job data |
| `~/.drewgent/whatsapp/session/` | WhatsApp bridge credentials |

---

## Architecture Overview

### Core Loop

```
User message → AIAgent._run_agent_loop()
  ├── Build system prompt (prompt_builder.py)
  ├── Build API kwargs (model, messages, tools, reasoning config)
  ├── Call LLM (OpenAI-compatible API)
  ├── If tool_calls in response:
  │     ├── Execute each tool via registry dispatch
  │     ├── Add tool results to conversation
  │     └── Loop back to LLM call
  ├── If text response:
  │     ├── Persist session to DB
  │     └── Return final_response
  └── Context compression if approaching token limit
```

### Key Design Patterns

- **Self-registering tools**: Each tool file calls `registry.register()` at import time. `model_tools.py` triggers discovery by importing all tool modules.
- **Toolset grouping**: Tools are grouped into toolsets (`web`, `terminal`, `file`, `browser`, etc.) that can be enabled/disabled per platform.
- **Session persistence**: All conversations are stored in SQLite (`drewgent_state.py`) with full-text search and unique session titles. JSON logs go to `~/.drewgent/sessions/`.
- **Ephemeral injection**: System prompts and prefill messages are injected at API call time, never persisted to the database or logs.
- **Provider abstraction**: The agent works with any OpenAI-compatible API. Provider resolution happens at init time (Nous Portal OAuth, OpenRouter API key, or custom endpoint).
- **Provider routing**: When using OpenRouter, `provider_routing` in config.yaml controls provider selection (sort by throughput/latency/price, allow/ignore specific providers, data retention policies). These are injected as `extra_body.provider` in API requests.

---

## Code Style

- **PEP 8** with practical exceptions (we don't enforce strict line length)
- **Comments**: Only when explaining non-obvious intent, trade-offs, or API quirks. Don't narrate what the code does — `# increment counter` adds nothing
- **Error handling**: Catch specific exceptions. Log with `logger.warning()`/`logger.error()` — use `exc_info=True` for unexpected errors so stack traces appear in logs
- **Cross-platform**: Never assume Unix. See [Cross-Platform Compatibility](#cross-platform-compatibility)

---

## Adding a New Tool

Before writing a tool, ask: [should this be a skill instead?](#should-it-be-a-skill-or-a-tool)

Tools self-register with the central registry. Each tool file co-locates its schema, handler, and registration:

```python
"""my_tool — Brief description of what this tool does."""

import json
from tools.registry import registry


def my_tool(param1: str, param2: int = 10, **kwargs) -> str:
    """Handler. Returns a string result (often JSON)."""
    result = do_work(param1, param2)
    return json.dumps(result)


MY_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "my_tool",
        "description": "What this tool does and when the agent should use it.",
        "parameters": {
            "type": "object",
            "properties": {
                "param1": {"type": "string", "description": "What param1 is"},
                "param2": {"type": "integer", "description": "What param2 is", "default": 10},
            },
            "required": ["param1"],
        },
    },
}


def _check_requirements() -> bool:
    """Return True if this tool's dependencies are available."""
    return True


registry.register(
    name="my_tool",
    toolset="my_toolset",
    schema=MY_TOOL_SCHEMA,
    handler=lambda args, **kw: my_tool(**args, **kw),
    check_fn=_check_requirements,
)
```

Then add the import to `model_tools.py` in the `_modules` list (line ~133):

```python
# _modules is imported at module level — importing a tool file triggers
# its registry.register() call, so the tool becomes available system-wide.
_modules = [
    # ... existing modules ...
    "tools.my_tool",
]
```

**How registration works**: `_discover_tools()` (called at the bottom of `model_tools.py`) imports all modules in `_modules`. Each tool file runs `registry.register(...)` at module level during import, which adds the tool to the central registry. The registry then exposes schemas to the LLM and dispatches calls to the handler.

**`registry.register()` fields**:

| Field | Type | Description |
|---|---|---|
| `name` | `str` | Tool name — must match `schema.function.name` |
| `toolset` | `str` | Toolset this tool belongs to (e.g. `"terminal"`, `"file"`) |
| `schema` | `dict` | OpenAI function-calling schema (name, description, parameters) |
| `handler` | `callable` | Function that receives `(args, **kwargs)` and returns a string |
| `check_fn` | `callable` | Optional — returns `True` if tool is available (env vars, API keys, etc.) |
| `requires_env` | `list[str]` | Optional — env var names the tool needs |

If it's a new toolset, add it to `toolsets.py` and to the relevant platform presets.

---

## Database Usage Guidelines

Drewgent uses **SQLite** as its primary data store. Multiple components share this pattern — understanding the conventions below keeps the codebase consistent and avoids subtle concurrency bugs.

### When to Use the SessionDB

`SessionDB` (`drewgent_state.py`) is the **official interface** for all session-related data:

```python
from drewgent_state import SessionDB

db = SessionDB()                     # Default: ~/.drewgent/state.db
db = SessionDB(db_path=Path(...))    # Custom path (use only in tests)
```

**Do not** call `sqlite3.connect()` directly for session data. The `SessionDB` class handles:
- WAL mode + concurrent readers / single writer
- Application-level retry with random jitter (avoids SQLite's built-in convoy effect)
- FTS5 full-text search via auto-synced triggers
- Schema versioning and migrations

### SessionDB Write Pattern

Every write goes through `_execute_write()`:

```python
def _execute_write(self, fn: Callable[[sqlite3.Connection], T]) -> T:
    for attempt in range(self._WRITE_MAX_RETRIES):
        try:
            with self._lock:
                self._conn.execute("BEGIN IMMEDIATE")   # Lock at tx start
                result = fn(self._conn)
                self._conn.commit()
        except sqlite3.OperationalError as exc:
            if "locked" in str(exc).lower():
                time.sleep(random.uniform(0.020, 0.150))  # Jitter back-off
                continue
            raise
    # WAL checkpoint every 50 writes
    if self._write_count % 50 == 0:
        self._try_wal_checkpoint()
```

Key settings:

| Parameter | Value | Reason |
|---|---|---|
| `timeout` | 1 second | Short — we handle retries at app level |
| `isolation_level` | `None` | We manage transactions explicitly |
| `PRAGMA journal_mode` | `WAL` | Concurrent reads + single writer |
| `PRAGMA foreign_keys` | `ON` | Enforce parent_session_id referential integrity |

### Adding a New DB File

If you need a **separate SQLite file** (not session data), follow this template:

```python
from pathlib import Path
from drewgent_constants import get_drewgent_home
import sqlite3, threading, random, time

def open_my_db() -> sqlite3.Connection:
    db_path = get_drewgent_home() / "my_feature.db"
    conn = sqlite3.connect(str(db_path), timeout=10.0, isolation_level=None)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn

class MyFeatureDB:
    _WRITE_MAX_RETRIES = 15
    _WRITE_RETRY_MIN_S = 0.020
    _WRITE_RETRY_MAX_S = 0.150

    def __init__(self):
        self._conn = open_my_db()
        self._lock = threading.Lock()

    def _write(self, fn):
        for attempt in range(self._WRITE_MAX_RETRIES):
            try:
                with self._lock:
                    self._conn.execute("BEGIN IMMEDIATE")
                    result = fn(self._conn)
                    self._conn.commit()
                    return result
            except sqlite3.OperationalError as exc:
                if "locked" in str(exc).lower() and attempt < self._WRITE_MAX_RETRIES - 1:
                    time.sleep(random.uniform(self._WRITE_RETRY_MIN_S, self._WRITE_RETRY_MAX_S))
                    continue
                raise
```

### Path Management (Critical)

**Never hardcode `~/.drewgent`** in code. Use:

```python
from drewgent_constants import get_drewgent_home, display_drewgent_home

db_path = get_drewgent_home() / "state.db"      # For code paths
# display_drewgent_home() for user-facing messages
```

`get_drewgent_home()` respects the `HERMES_HOME` environment variable (profile isolation).

### FTS5 Full-Text Search

If your feature needs text search, use FTS5 with triggers — **never sync manually**:

```sql
CREATE VIRTUAL TABLE IF NOT EXISTS my_fts USING fts5(content, content=my_table, content_rowid=id);

CREATE TRIGGER IF NOT EXISTS my_fts_insert AFTER INSERT ON my_table BEGIN
    INSERT INTO my_fts(rowid, content) VALUES (new.id, new.content);
END;

CREATE TRIGGER IF NOT EXISTS my_fts_delete AFTER DELETE ON my_table BEGIN
    INSERT INTO my_fts(my_fts, rowid, content) VALUES('delete', old.id, old.content);
END;

CREATE TRIGGER IF NOT EXISTS my_fts_update AFTER UPDATE ON my_table BEGIN
    INSERT INTO my_fts(my_fts, rowid, content) VALUES('delete', old.id, old.content);
    INSERT INTO my_fts(rowid, content) VALUES (new.id, new.content);
END;
```

### Schema Migrations

Use the `schema_version` table pattern:

```python
def _init_schema(self):
    cursor = self._conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)")
    cursor.execute("SELECT version FROM schema_version LIMIT 1")
    row = cursor.fetchone()
    if row is None:
        cursor.execute("INSERT INTO schema_version (version) VALUES (?)", (1,))
    else:
        current = row[0] if isinstance(row, sqlite3.Row) else row[0]
        if current < 2:
            self._migrate_v2(cursor)
            cursor.execute("UPDATE schema_version SET version = 2")
        if current < 3:
            self._migrate_v3(cursor)
            cursor.execute("UPDATE schema_version SET version = 3")

def _migrate_v2(self, cursor):
    try:
        cursor.execute("ALTER TABLE my_table ADD COLUMN new_col TEXT")
    except sqlite3.OperationalError:
        pass  # Already exists
```

### Reference Implementations

| Component | DB File | Key Patterns |
|---|---|---|
| `drewgent_state.py` — `SessionDB` | `state.db` | WAL + retry + checkpoint + FTS5 + migrations |
| `modules/logging_v2.py` | `logging_v2.db` | WAL + `synchronous=NORMAL` + `cache_size=-64000` |
| `plugins/memory/holographic/store.py` — `MemoryStore` | `memory_store.db` | WAL + `threading.RLock()` + migration |
| `plugins/memory/retaindb/__init__.py` — `_WriteQueue` | `pending.db` | Thread-local connections + crash-safe pending row replay |

---

## Adding a Skill

Bundled skills live in `skills/` organized by category. Official optional skills use the same structure in `optional-skills/`:

```
skills/
├── research/
│   └── arxiv/
│       ├── SKILL.md              # Required: main instructions
│       └── scripts/              # Optional: helper scripts
│           └── search_arxiv.py
├── productivity/
│   └── ocr-and-documents/
│       ├── SKILL.md
│       ├── scripts/
│       └── references/
└── ...
```

### SKILL.md format

```markdown
---
name: my-skill
description: Brief description (shown in skill search results)
version: 1.0.0
author: Your Name
license: MIT
platforms: [macos, linux]          # Optional — restrict to specific OS platforms
                                   #   Valid: macos, linux, windows
                                   #   Omit to load on all platforms (default)
required_environment_variables:    # Optional — secure setup-on-load metadata
  - name: MY_API_KEY
    prompt: API key
    help: Where to get it
    required_for: full functionality
prerequisites:                     # Optional legacy runtime requirements
  env_vars: [MY_API_KEY]           #   Backward-compatible alias for required env vars
  commands: [curl, jq]             #   Advisory only; does not hide the skill
metadata:
  hermes:
    tags: [Category, Subcategory, Keywords]
    related_skills: [other-skill-name]
    fallback_for_toolsets: [web]       # Optional — show only when toolset is unavailable
    requires_toolsets: [terminal]      # Optional — show only when toolset is available
---

# Skill Title

Brief intro.

## When to Use
Trigger conditions — when should the agent load this skill?

## Quick Reference
Table of common commands or API calls.

## Procedure
Step-by-step instructions the agent follows.

## Pitfalls
Known failure modes and how to handle them.

## Verification
How the agent confirms it worked.
```

### Platform-specific skills

Skills can declare which OS platforms they support via the `platforms` frontmatter field. Skills with this field are automatically hidden from the system prompt, `skills_list()`, and slash commands on incompatible platforms.

```yaml
platforms: [macos]            # macOS only (e.g., iMessage, Apple Reminders)
platforms: [macos, linux]     # macOS and Linux
platforms: [windows]          # Windows only
```

If the field is omitted or empty, the skill loads on all platforms (backward compatible). See `skills/apple/` for examples of macOS-only skills.

### Conditional skill activation

Skills can declare conditions that control when they appear in the system prompt, based on which tools and toolsets are available in the current session. This is primarily used for **fallback skills** — alternatives that should only be shown when a primary tool is unavailable.

Four fields are supported under `metadata.hermes`:

```yaml
metadata:
  hermes:
    fallback_for_toolsets: [web]      # Show ONLY when these toolsets are unavailable
    requires_toolsets: [terminal]     # Show ONLY when these toolsets are available
    fallback_for_tools: [web_search]  # Show ONLY when these specific tools are unavailable
    requires_tools: [terminal]        # Show ONLY when these specific tools are available
```

**Semantics:**
- `fallback_for_*`: The skill is a backup. It is **hidden** when the listed tools/toolsets are available, and **shown** when they are unavailable. Use this for free alternatives to premium tools.
- `requires_*`: The skill needs certain tools to function. It is **hidden** when the listed tools/toolsets are unavailable. Use this for skills that depend on specific capabilities (e.g., a skill that only makes sense with terminal access).
- If both are specified, both conditions must be satisfied for the skill to appear.
- If neither is specified, the skill is always shown (backward compatible).

**Examples:**

```yaml
# DuckDuckGo search — shown when Firecrawl (web toolset) is unavailable
metadata:
  hermes:
    fallback_for_toolsets: [web]

# Smart home skill — only useful when terminal is available
metadata:
  hermes:
    requires_toolsets: [terminal]

# Local browser fallback — shown when Browserbase is unavailable
metadata:
  hermes:
    fallback_for_toolsets: [browser]
```

The filtering happens at prompt build time in `agent/prompt_builder.py`. The `build_skills_system_prompt()` function receives the set of available tools and toolsets from the agent and uses `_skill_should_show()` to evaluate each skill's conditions.

### Skill setup metadata

Skills can declare secure setup-on-load metadata via the `required_environment_variables` frontmatter field. Missing values do not hide the skill from discovery; they trigger a CLI-only secure prompt when the skill is actually loaded.

```yaml
required_environment_variables:
  - name: TENOR_API_KEY
    prompt: Tenor API key
    help: Get a key from https://developers.google.com/tenor
    required_for: full functionality
```

The user may skip setup and keep loading the skill. Drewgent only exposes metadata (`stored_as`, `skipped`, `validated`) to the model — never the secret value.

Legacy `prerequisites.env_vars` remains supported and is normalized into the new representation.

```yaml
prerequisites:
  env_vars: [TENOR_API_KEY]       # Legacy alias for required_environment_variables
  commands: [curl, jq]            # Advisory CLI checks
```

Gateway and messaging sessions never collect secrets in-band; they instruct the user to run `drewgent setup` or update `~/.drewgent/.env` locally.

**When to declare required environment variables:**
- The skill uses an API key or token that should be collected securely at load time
- The skill can still be useful if the user skips setup, but may degrade gracefully

**When to declare command prerequisites:**
- The skill relies on a CLI tool that may not be installed (e.g., `himalaya`, `openhue`, `ddgs`)
- Treat command checks as guidance, not discovery-time hiding

See `skills/gifs/gif-search/` and `skills/email/himalaya/` for examples.

### Skill guidelines

- **No external dependencies unless absolutely necessary.** Prefer stdlib Python, curl, and existing Drewgent tools (`web_extract`, `terminal`, `read_file`).
- **Progressive disclosure.** Put the most common workflow first. Edge cases and advanced usage go at the bottom.
- **Include helper scripts** for XML/JSON parsing or complex logic — don't expect the LLM to write parsers inline every time.
- **Test it.** Run `drewgent --toolsets skills -q "Use the X skill to do Y"` and verify the agent follows the instructions correctly.

---

## Adding a Skin / Theme

Drewgent uses a data-driven skin system — no code changes needed to add a new skin.

**Option A: User skin (YAML file)**

Create `~/.drewgent/skins/<name>.yaml`:

```yaml
name: mytheme
description: Short description of the theme

colors:
  banner_border: "#HEX"     # Panel border color
  banner_title: "#HEX"      # Panel title color
  banner_accent: "#HEX"     # Section header color
  banner_dim: "#HEX"        # Muted/dim text color
  banner_text: "#HEX"       # Body text color
  response_border: "#HEX"   # Response box border

spinner:
  waiting_faces: ["(⚔)", "(⛨)"]
  thinking_faces: ["(⚔)", "(⌁)"]
  thinking_verbs: ["forging", "plotting"]
  wings:                     # Optional left/right decorations
    - ["⟪⚔", "⚔⟫"]

branding:
  agent_name: "My Agent"
  welcome: "Welcome message"
  response_label: " ⚔ Agent "
  prompt_symbol: "⚔ ❯ "

tool_prefix: "╎"             # Tool output line prefix
```

All fields are optional — missing values inherit from the default skin.

**Option B: Built-in skin**

Add to `_BUILTIN_SKINS` dict in `drewgent_cli/skin_engine.py`. Use the same schema as above but as a Python dict. Built-in skins ship with the package and are always available.

**Activating:**
- CLI: `/skin mytheme` or set `display.skin: mytheme` in config.yaml
- Config: `display: { skin: mytheme }`

See `drewgent_cli/skin_engine.py` for the full schema and existing skins as examples.

---

## Cross-Platform Compatibility

Drewgent runs on Linux, macOS, and Windows. When writing code that touches the OS:

### Critical rules

1. **`termios` and `fcntl` are Unix-only.** Always catch both `ImportError` and `NotImplementedError`:
   ```python
   try:
       from simple_term_menu import TerminalMenu
       menu = TerminalMenu(options)
       idx = menu.show()
   except (ImportError, NotImplementedError):
       # Fallback: numbered menu for Windows
       for i, opt in enumerate(options):
           print(f"  {i+1}. {opt}")
       idx = int(input("Choice: ")) - 1
   ```

2. **File encoding.** Windows may save `.env` files in `cp1252`. Always handle encoding errors:
   ```python
   try:
       load_dotenv(env_path)
   except UnicodeDecodeError:
       load_dotenv(env_path, encoding="latin-1")
   ```

3. **Process management.** `os.setsid()`, `os.killpg()`, and signal handling differ on Windows. Use platform checks:
   ```python
   import platform
   if platform.system() != "Windows":
       kwargs["preexec_fn"] = os.setsid
   ```

4. **Path separators.** Use `pathlib.Path` instead of string concatenation with `/`.

5. **Shell commands in installers.** If you change `scripts/install.sh`, check if the equivalent change is needed in `scripts/install.ps1`.

---

## Security Considerations

Drewgent has terminal access. Security matters.

### Existing protections

| Layer | Implementation |
|-------|---------------|
| **Sudo password piping** | Uses `shlex.quote()` to prevent shell injection |
| **Dangerous command detection** | Regex patterns in `tools/approval.py` with user approval flow |
| **Cron prompt injection** | Scanner in `tools/cronjob_tools.py` blocks instruction-override patterns |
| **Write deny list** | Protected paths (`~/.ssh/authorized_keys`, `/etc/shadow`) resolved via `os.path.realpath()` to prevent symlink bypass |
| **Skills guard** | Security scanner for hub-installed skills (`tools/skills_guard.py`) |
| **Code execution sandbox** | `execute_code` child process runs with API keys stripped from environment |
| **Container hardening** | Docker: all capabilities dropped, no privilege escalation, PID limits, size-limited tmpfs |

### When contributing security-sensitive code

- **Always use `shlex.quote()`** when interpolating user input into shell commands
- **Resolve symlinks** with `os.path.realpath()` before path-based access control checks
- **Don't log secrets.** API keys, tokens, and passwords should never appear in log output
- **Catch broad exceptions** around tool execution so a single failure doesn't crash the agent loop
- **Test on all platforms** if your change touches file paths, process management, or shell commands

If your PR affects security, note it explicitly in the description.

---

## Pull Request Process

### Branch naming

```
fix/description        # Bug fixes
feat/description       # New features
docs/description       # Documentation
test/description       # Tests
refactor/description   # Code restructuring
```

### Before submitting

1. **Run tests**: `pytest tests/ -v`
2. **Test manually**: Run `drewgent`` and exercise the code path you changed
3. **Check cross-platform impact**: If you touch file I/O, process management, or terminal handling, consider Windows and macOS
4. **Keep PRs focused**: One logical change per PR. Don't mix a bug fix with a refactor with a new feature.

### PR description

Include:
- **What** changed and **why**
- **How to test** it (reproduction steps for bugs, usage examples for features)
- **What platforms** you tested on
- Reference any related issues

### Commit messages

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>
```

| Type | Use for |
|------|---------|
| `fix` | Bug fixes |
| `feat` | New features |
| `docs` | Documentation |
| `test` | Tests |
| `refactor` | Code restructuring (no behavior change) |
| `chore` | Build, CI, dependency updates |

Scopes: `cli`, `gateway`, `tools`, `skills`, `agent`, `install`, `whatsapp`, `security`, etc.

Examples:
```
fix(cli): prevent crash in save_config_value when model is a string
feat(gateway): add WhatsApp multi-user session isolation
fix(security): prevent shell injection in sudo password piping
test(tools): add unit tests for file_operations
```

---

## Reporting Issues

- Use [GitHub Issues](https://github.com/NousResearch/drewgent-agent/issues)
- Include: OS, Python version, Drewgent version (`drewgent` version`), full error traceback
- Include steps to reproduce
- Check existing issues before creating duplicates
- For security vulnerabilities, please report privately

---

## Community

- **Discord**: [discord.gg/NousResearch](https://discord.gg/NousResearch) — for questions, showcasing projects, and sharing skills
- **GitHub Discussions**: For design proposals and architecture discussions
- **Skills Hub**: Upload specialized skills to a registry and share them with the community

---

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).

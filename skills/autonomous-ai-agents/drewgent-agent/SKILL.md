---
name: drewgent-agent
description: Complete guide to using and extending Drewgent Agent — CLI usage, setup, configuration, spawning additional agents, gateway platforms, skills, voice, tools, profiles, and a concise contributor reference. Load this skill when helping users configure Drewgent, troubleshoot issues, spawn agent instances, or make code contributions.
version: 2.0.0
author: Drewgent Agent + Teknium
license: MIT
metadata:
  drewgent:
    tags: [opencode, setup, configuration, multi-agent, spawning, cli, gateway, development]
    homepage: https://github.com/NousResearch/drewgent-agent
    related_skills: [claude-code, codex, opencode]
links:
  - "[[@identity/brain/rules]]"
links:
  - "[[@action/skills/SKILL-INDEX]]"
  - "[[@identity/brain/rules]]"
---

# Drewgent Agent

Drewgent Agent is an open-source AI agent framework by HUMANERD that runs in your terminal, messaging platforms, and IDEs. It belongs to the same category as Claude Code (Anthropic), Codex (OpenAI), and OpenClaw — autonomous coding and task-execution agents that use tool calling to interact with your system. Drewgent works with any LLM provider (OpenRouter, Anthropic, OpenAI, DeepSeek, local models, and 15+ others) and runs on Linux, macOS, and WSL.

What makes Drewgent different:

- **Self-improving through skills** — Drewgent learns from experience by saving reusable procedures as skills. When it solves a complex problem, discovers a workflow, or gets corrected, it can persist that knowledge as a skill document that loads into future sessions. Skills accumulate over time, making the agent better at your specific tasks and environment.
- **Persistent memory across sessions** — remembers who you are, your preferences, environment details, and lessons learned. Pluggable memory backends (built-in, Honcho, Mem0, and more) let you choose how memory works.
- **Multi-platform gateway** — the same agent runs on Telegram, Discord, Slack, WhatsApp, Signal, Matrix, Email, and 8+ other platforms with full tool access, not just chat.
- **Provider-agnostic** — swap models and providers mid-workflow without changing anything else. Credential pools rotate across multiple API keys automatically.
- **Profiles** — run multiple independent Drewgent instances with isolated configs, sessions, skills, and memory.
- **Extensible** — plugins, MCP servers, custom tools, webhook triggers, cron scheduling, and the full Python ecosystem.

People use Drewgent for software development, research, system administration, data analysis, content creation, home automation, and anything else that benefits from an AI agent with persistent context and full system access.

**This skill helps you work with Drewgent Agent effectively** — setting it up, configuring features, spawning additional agent instances, troubleshooting issues, finding the right commands and settings, and understanding how the system works when you need to extend or contribute to it.

**Docs:** https://drewgent-agent.humanerd.ai/docs/

## Quick Start

```bash
# Install
curl -fsSL https://raw.githubusercontent.com/NousResearch/drewgent-agent/main/scripts/install.sh | bash

# Drewgent now runs via opencode (the hermes CLI has been removed).
# Interactive chat (default)
opencode

# Single query
opencode run -q "What is the capital of France?"

# Setup wizard
drewgent setup

# Change model/provider
# Use opencode's model selection or edit ~/.config/opencode/opencode.jsonc

# Check health
drewgent doctor
```

---

## CLI Reference (DEPRECATED — hermes CLI removed)

The `hermes` CLI has been removed from the system. All interaction now goes through `opencode` (the OpenCode CLI). The commands below are historical reference only.

### Global Flags (opencode equivalents)

```
opencode [flags] [command]

  --version, -V             Show version
  --resume, -r SESSION      Resume session by ID or title
  --continue, -c [NAME]     Resume by name, or most recent session
  --skills, -s SKILL        Preload skills (comma-separate or repeat)
  --yolo                    Skip dangerous command approval
```

No subcommand defaults to interactive chat.

### Chat

```
opencode [flags]
  -q, --query TEXT          Single query, non-interactive
  -m, --model MODEL         Model (e.g. deepseek-v4-flash)
  -v, --verbose             Verbose output
  -Q, --quiet               Suppress banner, spinner, tool previews
```

### Configuration

```
drewgent setup [section]      Interactive wizard (model|terminal|gateway|tools|agent)
drewgent config               View current config
drewgent config edit          Open config in $EDITOR
drewgent config set KEY VAL   Set a config value
drewgent config path          Print config path
drewgent config check         Check for missing/outdated config
drewgent doctor [--fix]       Check dependencies and config
drewgent status [--all]       Show component status
```

### Tools & Skills

```
drewgent tools                Interactive tool enable/disable (curses UI)
drewgent tools list           Show all tools and status
drewgent tools enable NAME    Enable a toolset
drewgent tools disable NAME   Disable a toolset

drewgent skills list          List installed skills
drewgent skills search QUERY  Search the skills hub
drewgent skills install ID    Install a skill
drewgent skills inspect ID    Preview without installing
drewgent skills update        Update outdated skills
drewgent skills uninstall N   Remove a hub skill
```

### MCP Servers

MCP servers are configured in `~/.config/opencode/opencode.jsonc`. Use the opencode native MCP integration.

### Gateway (Messaging Platforms)

```
drewgent gateway run          Start gateway foreground
drewgent gateway install      Install as background service
drewgent gateway start/stop   Control the service
drewgent gateway restart      Restart the service
drewgent gateway status       Check status
drewgent gateway setup        Configure platforms
```

### Sessions

Sessions are managed through opencode's native session system. Use `opencode --resume` or `opencode --continue`.

### Cron Jobs

Cron jobs are managed through `~/.drewgent/cron/jobs.json` and the launchd cron dispatcher. Edit `jobs.json` directly or use the Python cron API.

### Profiles

Agent profiles live at `~/.config/opencode/agents/*.md`. List with `ls ~/.config/opencode/agents/`.

```
drewgent profile list         List all profiles
drewgent profile create NAME  Create (--clone, --clone-all, --clone-from)
drewgent profile use NAME     Set sticky default
drewgent profile delete NAME  Delete a profile
drewgent profile show NAME    Show details
```

### Other

```
drewgent insights [--days N]  Usage analytics
drewgent update               Update to latest version
drewgent honcho setup/status  Honcho memory integration
drewgent memory setup/status/off  Memory provider config
drewgent acp                  ACP server (IDE integration)
```

---

## Slash Commands (In-Session)

Type these during an interactive chat session.

### Session Control
```
/new (/reset)        Fresh session
/clear               Clear screen + new session (CLI)
/retry               Resend last message
/undo                Remove last exchange
/title [name]        Name the session
/compress            Manually compress context
/stop                Kill background processes
/rollback [N]        Restore filesystem checkpoint
/background <prompt> Run prompt in background
/queue <prompt>      Queue for next turn
/resume [name]       Resume a named session
```

### Configuration
```
/config              Show config (CLI)
/model [name]        Show or change model
/provider            Show provider info
/prompt [text]       View/set system prompt (CLI)
/personality [name]  Set personality
/reasoning [level]   Set reasoning (none|low|medium|high|xhigh|show|hide)
/verbose             Cycle: off → new → all → verbose
/voice [on|off|tts]  Voice mode
/yolo                Toggle approval bypass
/skin [name]         Change theme (CLI)
/statusbar           Toggle status bar (CLI)
```

### Tools & Skills
```
/tools               Manage tools (CLI)
/toolsets            List toolsets (CLI)
/skills              Search/install skills (CLI)
/skill <name>        Load a skill into session
/cron                Manage cron jobs (CLI)
/reload-mcp          Reload MCP servers
/plugins             List plugins (CLI)
```

### Info
```
/help                Show commands
/commands [page]     Browse all commands (gateway)
/usage               Token usage
/insights [days]     Usage analytics
/status              Session info (gateway)
/profile             Active profile info
```

### Exit
```
/quit (/exit, /q)    Exit CLI
```

---

## Key Paths & Config

```
~/.drewgent/config.yaml       Main configuration
~/.drewgent/.env              API keys and secrets
~/.drewgent/skills/           Installed skills
~/.drewgent/sessions/         Session transcripts
~/.drewgent/logs/             Gateway and error logs
~/.drewgent/auth.json         OAuth tokens and credential pools
~/.drewgent/drewgent-agent/     Source code (if git-installed)
```

Profiles use `~/.drewgent/profiles/<name>/` with the same layout.

### Config Sections

Edit with `drewgent` config edit` or `drewgent` config set section.key value`.

| Section | Key options |
|---------|-------------|
| `model` | `default`, `provider`, `base_url`, `api_key`, `context_length` |
| `agent` | `max_turns` (90), `tool_use_enforcement` |
| `terminal` | `backend` (local/docker/ssh/modal), `cwd`, `timeout` (180) |
| `compression` | `enabled`, `threshold` (0.50), `target_ratio` (0.20) |
| `display` | `skin`, `tool_progress`, `show_reasoning`, `show_cost` |
| `stt` | `enabled`, `provider` (local/groq/openai) |
| `tts` | `provider` (edge/elevenlabs/openai/kokoro/fish) |
| `memory` | `memory_enabled`, `user_profile_enabled`, `provider` |
| `security` | `tirith_enabled`, `website_blocklist` |
| `delegation` | `model`, `provider`, `max_iterations` (50) |
| `smart_model_routing` | `enabled`, `cheap_model` |
| `checkpoints` | `enabled`, `max_snapshots` (50) |

Full config reference: https://drewgent-agent.humanerd.ai/docs/user-guide/configuration

### Providers

18 providers supported. Set via `drewgent` model` or `drewgent setup`.

| Provider | Auth | Key env var |
|----------|------|-------------|
| OpenRouter | API key | `OPENROUTER_API_KEY` |
| Anthropic | API key | `ANTHROPIC_API_KEY` |
| Nous Portal | OAuth | `drewgent` login --provider nous` |
| OpenAI Codex | OAuth | `drewgent` login --provider openai-codex` |
| GitHub Copilot | Token | `COPILOT_GITHUB_TOKEN` |
| DeepSeek | API key | `DEEPSEEK_API_KEY` |
| Hugging Face | Token | `HF_TOKEN` |
| Z.AI / GLM | API key | `GLM_API_KEY` |
| MiniMax | API key | `MINIMAX_API_KEY` |
| Kimi / Moonshot | API key | `KIMI_API_KEY` |
| Alibaba / DashScope | API key | `DASHSCOPE_API_KEY` |
| Kilo Code | API key | `KILOCODE_API_KEY` |
| Custom endpoint | Config | `model.base_url` + `model.api_key` in config.yaml |

Plus: AI Gateway, OpenCode Zen, OpenCode Go, MiniMax CN, GitHub Copilot ACP.

Full provider docs: https://drewgent-agent.humanerd.ai/docs/integrations/providers

### Toolsets

Enable/disable via `drewgent` tools` (interactive) or `drewgent` tools enable/disable NAME`.

| Toolset | What it provides |
|---------|-----------------|
| `web` | Web search and content extraction |
| `browser` | Browser automation (Browserbase, Camofox, or local Chromium) |
| `terminal` | Shell commands and process management |
| `file` | File read/write/search/patch |
| `code_execution` | Sandboxed Python execution |
| `vision` | Image analysis |
| `image_gen` | AI image generation |
| `tts` | Text-to-speech |
| `skills` | Skill browsing and management |
| `memory` | Persistent cross-session memory |
| `session_search` | Search past conversations |
| `delegation` | Subagent task delegation |
| `cronjob` | Scheduled task management |
| `clarify` | Ask user clarifying questions |
| `moa` | Mixture of Agents (off by default) |
| `homeassistant` | Smart home control (off by default) |

Tool changes take effect on `/reset` (new session). They do NOT apply mid-conversation to preserve prompt caching.

---

## Voice & Transcription

### STT (Voice → Text)

Voice messages from messaging platforms are auto-transcribed.

Provider priority (auto-detected):
1. **Local faster-whisper** — free, no API key: `pip install faster-whisper`
2. **Groq Whisper** — free tier: set `GROQ_API_KEY`
3. **OpenAI Whisper** — paid: set `VOICE_TOOLS_OPENAI_KEY`

Config:
```yaml
stt:
  enabled: true
  provider: local        # local, groq, openai
  local:
    model: base          # tiny, base, small, medium, large-v3
```

### TTS (Text → Voice)

| Provider | Env var | Free? |
|----------|---------|-------|
| Edge TTS | None | Yes (default) |
| ElevenLabs | `ELEVENLABS_API_KEY` | Free tier |
| OpenAI | `VOICE_TOOLS_OPENAI_KEY` | Paid |
| Kokoro (local) | None | Free |
| Fish Audio | `FISH_AUDIO_API_KEY` | Free tier |

Voice commands: `/voice on` (voice-to-voice), `/voice tts` (always voice), `/voice off`.

---

## Spawning Additional Drewgent Instances

Run additional Drewgent processes as fully independent subprocesses — separate sessions, tools, and environments.

### When to Use This vs delegate_task

| | `delegate_task` | Spawning `drewgent`` process |
|-|-----------------|--------------------------|
| Isolation | Separate conversation, shared process | Fully independent process |
| Duration | Minutes (bounded by parent loop) | Hours/days |
| Tool access | Subset of parent's tools | Full tool access |
| Interactive | No | Yes (PTY mode) |
| Use case | Quick parallel subtasks | Long autonomous missions |

### One-Shot Mode

```
terminal(command="opencode run -q 'Research GRPO papers and write summary to ~/research/grpo.md'", timeout=300)

# Background for long tasks:
terminal(command="opencode run -q 'Set up CI/CD for ~/myapp'", background=true)
```

### Interactive PTY Mode (via tmux)

Drewgent uses prompt_toolkit, which requires a real terminal. Use tmux for interactive spawning:

```
# Start
terminal(command="tmux new-session -d -s agent1 -x 120 -y 40 'opencode'", timeout=10)

# Wait for startup, then send a message
terminal(command="sleep 8 && tmux send-keys -t agent1 'Build a FastAPI auth service' Enter", timeout=15)

# Read output
terminal(command="sleep 20 && tmux capture-pane -t agent1 -p", timeout=5)

# Send follow-up
terminal(command="tmux send-keys -t agent1 'Add rate limiting middleware' Enter", timeout=5)

# Exit
terminal(command="tmux send-keys -t agent1 '/exit' Enter && sleep 2 && tmux kill-session -t agent1", timeout=10)
```

### Multi-Agent Coordination

```
# Agent A: backend
terminal(command="tmux new-session -d -s backend -x 120 -y 40 'drewgent -w'", timeout=10)
terminal(command="sleep 8 && tmux send-keys -t backend 'Build REST API for user management' Enter", timeout=15)

# Agent B: frontend
terminal(command="tmux new-session -d -s frontend -x 120 -y 40 'drewgent -w'", timeout=10)
terminal(command="sleep 8 && tmux send-keys -t frontend 'Build React dashboard for user management' Enter", timeout=15)

# Check progress, relay context between them
terminal(command="tmux capture-pane -t backend -p | tail -30", timeout=5)
terminal(command="tmux send-keys -t frontend 'Here is the API schema from the backend agent: ...' Enter", timeout=5)
```

### Session Resume

```
# Resume most recent session
terminal(command="tmux new-session -d -s resumed 'opencode --continue'", timeout=10)

# Resume specific session
terminal(command="tmux new-session -d -s resumed 'drewgent --resume 20260225_143052_a1b2c3'", timeout=10)
```

### Tips

- **Prefer `delegate_task` for quick subtasks** — less overhead than spawning a full process
- **Use `-w` (worktree mode)** when spawning agents that edit code — prevents git conflicts
- **Set timeouts** for one-shot mode — complex tasks can take 5-10 minutes
- **Use `opencode run -q` for fire-and-forget** — no PTY needed
- **Use tmux for interactive sessions** — raw PTY mode has `\r` vs `\n` issues with prompt_toolkit
- **For scheduled tasks**, use the `cronjob` tool instead of spawning — handles delivery and retry

---

## Troubleshooting

### Voice not working
1. Check `stt.enabled: true` in config.yaml
2. Verify provider: `pip install faster-whisper` or set API key
3. Restart gateway: `/restart`

### Tool not available
1. `drewgent` tools` — check if toolset is enabled for your platform
2. Some tools need env vars (check `.env`)
3. `/reset` after enabling tools

### Model/provider issues
1. `drewgent doctor` — check config and dependencies
2. `drewgent` login` — re-authenticate OAuth providers
3. Check `.env` has the right API key

### Changes not taking effect
- **Tools/skills:** `/reset` starts a new session with updated toolset
- **Config changes:** `/restart` reloads gateway config
- **Code changes:** Restart the CLI or gateway process

### Skills not showing
1. `drewgent skills list` — verify installed
2. `drewgent skills config` — check platform enablement
3. Load explicitly: `/skill name` or `drewgent` -s name`

### Gateway issues
Check logs first:
```bash
grep -i "failed to send\|error" ~/.drewgent/logs/gateway.log | tail -20
```

---

## Where to Find Things

| Looking for... | Location |
|----------------|----------|
| Config options | `drewgent` config edit` or [Configuration docs](https://drewgent-agent.humanerd.ai/docs/user-guide/configuration) |
| Available tools | `drewgent` tools list` or [Tools reference](https://drewgent-agent.humanerd.ai/docs/reference/tools-reference) |
| Slash commands | `/help` in session or [Slash commands reference](https://drewgent-agent.humanerd.ai/docs/reference/slash-commands) |
| Skills catalog | `drewgent skills browse` or [Skills catalog](https://drewgent-agent.humanerd.ai/docs/reference/skills-catalog) |
| Provider setup | `drewgent` model` or [Providers guide](https://drewgent-agent.humanerd.ai/docs/integrations/providers) |
| Platform setup | `drewgent gateway setup` or [Messaging docs](https://drewgent-agent.humanerd.ai/docs/user-guide/messaging/) |
| MCP servers | `drewgent` mcp list` or [MCP guide](https://drewgent-agent.humanerd.ai/docs/user-guide/features/mcp) |
| Profiles | `drewgent` profile list` or [Profiles docs](https://drewgent-agent.humanerd.ai/docs/user-guide/profiles) |
| Cron jobs | `drewgent` cron list` or [Cron docs](https://drewgent-agent.humanerd.ai/docs/user-guide/features/cron) |
| Memory | `drewgent` memory status` or [Memory docs](https://drewgent-agent.humanerd.ai/docs/user-guide/features/memory) |
| Env variables | `drewgent` config env-path` or [Env vars reference](https://drewgent-agent.humanerd.ai/docs/reference/environment-variables) |
| CLI commands | `drewgent --help` or [CLI reference](https://drewgent-agent.humanerd.ai/docs/reference/cli-commands) |
| Gateway logs | `~/.drewgent/logs/gateway.log` |
| Session files | `~/.drewgent/sessions/` or `drewgent` sessions browse` |
| Source code | `~/.drewgent/drewgent-agent/` |

---

## Contributor Quick Reference

For occasional contributors and PR authors. Full developer docs: https://drewgent-agent.humanerd.ai/docs/developer-guide/

### Project Layout

```
drewgent-agent/
├── run_agent.py          # AIAgent — core conversation loop
├── model_tools.py        # Tool discovery and dispatch
├── toolsets.py           # Toolset definitions
├── cli.py                # Interactive CLI (DrewgentCLI)
├── drewgent_state.py       # SQLite session store
├── agent/                # Prompt builder, compression, display, adapters
├── drewgent_cli/           # CLI subcommands, config, setup, commands
│   ├── commands.py       # Slash command registry (CommandDef)
│   ├── config.py         # DEFAULT_CONFIG, env var definitions
│   └── main.py           # CLI entry point and argparse
├── tools/                # One file per tool
│   └── registry.py       # Central tool registry
├── gateway/              # Messaging gateway
│   └── platforms/        # Platform adapters (telegram, discord, etc.)
├── cron/                 # Job scheduler
├── tests/                # ~3000 pytest tests
└── website/              # Docusaurus docs site
```

Config: `~/.drewgent/config.yaml` (settings), `~/.drewgent/.env` (API keys).

### Adding a Tool (3 files)

**1. Create `tools/your_tool.py`:**
```python
import json, os
from tools.registry import registry

def check_requirements() -> bool:
    return bool(os.getenv("EXAMPLE_API_KEY"))

def example_tool(param: str, task_id: str = None) -> str:
    return json.dumps({"success": True, "data": "..."})

registry.register(
    name="example_tool",
    toolset="example",
    schema={"name": "example_tool", "description": "...", "parameters": {...}},
    handler=lambda args, **kw: example_tool(
        param=args.get("param", ""), task_id=kw.get("task_id")),
    check_fn=check_requirements,
    requires_env=["EXAMPLE_API_KEY"],
)
```

**2. Add import** in `model_tools.py` → `_discover_tools()` list.

**3. Add to `toolsets.py`** → `_HERMES_CORE_TOOLS` list.

All handlers must return JSON strings. Use `get_drewgent_home()` for paths, never hardcode `~/.drewgent`.

### Adding a Slash Command

1. Add `CommandDef` to `COMMAND_REGISTRY` in `drewgent_cli/commands.py`
2. Add handler in `cli.py` → `process_command()`
3. (Optional) Add gateway handler in `gateway/run.py`

All consumers (help text, autocomplete, Telegram menu, Slack mapping) derive from the central registry automatically.

### Agent Loop (High Level)

```
run_conversation():
  1. Build system prompt
  2. Loop while iterations < max:
     a. Call LLM (OpenAI-format messages + tool schemas)
     b. If tool_calls → dispatch each via handle_function_call() → append results → continue
     c. If text response → return
  3. Context compression triggers automatically near token limit
```

### Testing

```bash
source venv/bin/activate  # or .venv/bin/activate
python -m pytest tests/ -o 'addopts=' -q   # Full suite
python -m pytest tests/tools/ -q            # Specific area
```

- Tests auto-redirect `DREW_HOME` to temp dirs — never touch real `~/.drewgent/`
- Run full suite before pushing any change
- Use `-o 'addopts='` to clear any baked-in pytest flags

### Commit Conventions

```
type: concise subject line

Optional body.
```

Types: `fix:`, `feat:`, `refactor:`, `docs:`, `chore:`

### Key Rules

- **Never break prompt caching** — don't change context, tools, or system prompt mid-conversation
- **Message role alternation** — never two assistant or two user messages in a row
- Use `get_drewgent_home()` from `drewgent_constants` for all paths (profile-safe)
- Config values go in `config.yaml`, secrets go in `.env`
- New tools need a `check_fn` so they only appear when requirements are met

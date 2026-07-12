# Architecture

## Agent System

Three-layer execution:
- **`task(subagent_type="...")`** — opencode built-in, multi-step delegation
- **Direct execution** — simple tasks, no delegation needed
- **MCP tools** — for external service integration

## Directory Structure

```
.opencode/
  instructions/     ← This directory (lazy-loaded)
  plugins/          ← opencode plugins
  agents/           ← Agent definitions (.md)

scripts/            ← Automation scripts (ontology, ingest, etc.)
kanban.db           ← Task database (SQLite)
knowledge.db        ← Knowledge + ontology database (SQLite)
P0-P6/              ← Wiki layers (Obsidian vault)
```

## Ontology Layer

The project uses a typed entity-relation graph on top of knowledge.db:

```
entities (typed nodes)
  ├── artifact → doc/code/project
  ├── agent → persona/tool/script/skill
  ├── decision → pattern/preference
  ├── event → incident/session
  ├── knowledge → concept/paper/reference
  └── meta → category/_task/fact

relations (typed edges)
  ├── references     any → doc
  ├── depends_on     decision → tool/script
  ├── led_to         decision → decision
  ├── fixed_by       incident → decision/pattern
  └── ...
```

Run `python3 scripts/ontology_setup.py` to initialize.

## Self-Healing

- launchd (macOS) or systemd (Linux): auto-restart on crash
- Housekeeper: daily health checks at 04:00
- Cron health: detect stalled jobs automatically

# opencode-{agent-name}

[🇰🇷 한국어](README.ko.md)

A personal AI agent template built on [opencode](https://opencode.ai).

This repo is a starting point for your own agent system: subagent profiles, skill library, cron automation, and a P0–P6 vault structure. Fork it, rename it, and customize it.

## Quick Start

```bash
# 1. Install opencode
curl -fsSL https://opencode.ai/install | sh

# 2. Fork this repo on GitHub, then clone your fork
git clone git@github.com:YOUR_USERNAME/opencode-drewgent.git ~/.youragent
cd ~/.youragent

# 3. Run setup
bash scripts/setup.sh

# 4. Start opencode
opencode
```

## Minimum Structure

```
~/.youragent/
├── AGENTS.md                   # System guide loaded by opencode
├── opencode.jsonc              # Model, MCP servers, skill paths
├── .opencode/agents/*.md       # Subagent profile templates
├── skills/                     # Skill library
├── cron/jobs.json              # Example cron jobs
├── launchd/*.plist.example     # macOS daemon templates
├── scripts/                    # Automation scripts
└── P0-brainstem/ ... P6-prefrontal/  # Vault layers
```

## Customize

1. Rename `drewgent` → `youragent` across the repo (use `skill("rename-drewgent")` or a find/replace).
2. Edit `@identity/SELF_MODEL.md`, `@identity/persona/SOUL.md`, and `@identity/persona/writing-style-guide.md` to match your agent's identity.
3. Add/remove skills under `skills/`.
4. Edit `cron/jobs.json` for your automation needs.

See [AGENTS.md](AGENTS.md) for the full guide.

## License

MIT — replace with your own license when forking.

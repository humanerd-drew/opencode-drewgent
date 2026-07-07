# opencode-drewgent

[🇰🇷 한국어](README.ko.md)

[![Built for opencode](https://img.shields.io/badge/Built%20for-opencode-8A2BE2)](https://opencode.ai)

**Blueprint for your private AI agent on opencode.**

This repo is a starting point — not a framework. It provides the conventions, tooling, and infrastructure patterns for building a personal AI agent that runs on [opencode](https://opencode.ai). Fork it, rename it, make it yours.

---

## Quick Start

```bash
git clone https://github.com/humanerd-drew/opencode-drewgent.git my-agent
cd my-agent
# 1. Edit @identity/ — set your name, rules, persona
# 2. Copy .env.example → .env and set OPENAI_API_KEY
# 3. Run: opencode
```

See [AGENTS.md](AGENTS.md) for the full agent guide.

---

## What's Inside

```
@identity/            → Your agent's identity (SELF_MODEL, rules, persona)
@action/              → Skills, proposals, migrations
.opencode/            → Agent profiles, MCP tools
launchd/              → macOS service templates (opencode serve, cron, discord)
cron/                 → Scheduled job dispatcher
harness/patterns/     → Quality patterns (manufacturing-bridge)
skills/               → 100+ skill definitions
scripts/              → Setup, install, sync, housekeeping
```

---

## Key Concepts

**7-Layer Brain (P0-P6):** Your agent's decision hierarchy. Rules in `P0-brainstem/` override everything. Identity in `P5-ego/` governs behavior. [More in AGENTS.md](AGENTS.md#vault-structure-p0-p6)

**Obsidian Vault as Knowledge Graph:** The P-layer directories ARE your agent's long-term memory — queryable by both the agent (`recall()`) and you (open in Obsidian).

**Governance as Code:** Rules are enforced `.neuron` constraints, not advisory prompts. `harness/patterns/manufacturing-bridge.md` documents the 6 quality patterns.

**Tiered Autonomy:** Your agent decides what to do autonomously (Tier 1-2), proposes actions (Tier 3), or asks for direction (Tier 4). [See AGENTS.md](AGENTS.md#tiered-autonomy)

---

## Customization

| Step | What to do |
|------|------------|
| Rename | `bash scripts/rename-drewgent.sh YourAgentName` |
| Identity | Edit `@identity/SELF_MODEL.md`, `@identity/persona/SOUL.md` |
| Rules | Edit `@identity/brain/rules.md` |
| MCP servers | Edit `opencode.jsonc` |
| Cron jobs | Edit `cron/jobs.json` |
| Launchd services | Copy `launchd/*.plist.example` → `~/Library/LaunchAgents/` |

---

## License

MIT

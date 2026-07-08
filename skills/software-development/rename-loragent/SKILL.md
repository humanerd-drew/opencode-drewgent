---
title: rename-loragent
description: "Rename Loragent to your own agent name — replaces all references across 2000+ files, renames directories, updates configs."
category: software-development
trigger: "User wants to fork Loragent under their own name"
created: 2026-06-19
provenance:
  session: "2026-06-19 opencode-loragent repo creation"
  decision: "Naming convention: <name>gent. Single script replaces all 2000+ references via ripgrep + sed."
---

# Rename Loragent

Replace all "loragent" references across the repo with your own agent name.

## Convention

`<yourname>gent` — e.g., loragent → alexgent, saragent, devgent.

## Usage

```bash
bash ~/.loragent/scripts/rename-loragent.sh "alexgent"
```

The script must:
1. Replace `loragent` → `<new_name>` in all `.md`, `.py`, `.json`, `.jsonc`, `.yaml`, `.yml`, `.sh`, `.js`, `.html` files (case-insensitive for filename patterns, case-sensitive for code references)
2. Rename `~/.loragent` → `~/.<new_name>gent` (symlink or move)
3. Update paths in `opencode.jsonc` and `AGENTS.md`
4. Update the frontmatter `title` fields where "Loragent" appears as a project name
5. Keep `DREW_HOME` env var or rename to `<NAME>_HOME`

## What It Replaces

| Pattern | Example → New |
|---------|---------------|
| Directory name | `~/.loragent/` → `~/.alexgent/` |
| Config paths | `~/.loragent/skills` → `~/.alexgent/skills` |
| Env vars | `DREW_HOME` → `ALEX_HOME` |
| Project name | `Loragent` → `Alexgent` (capitalized) |
| Code references | `loragent` → `alexgent` in inline paths |
| Script headers | `Loragent agent system` → `Alexgent agent system` |
| opencode.jsonc | skill paths, MCP paths |
| AGENTS.md | all references |

## What It Does NOT Replace

- The `opencode` CLI name (kept as-is)
- External project names (opencode, gbrain, lazyweb)
- Git remote URLs (must be changed separately)

## Verification

After running, verify:

```bash
# No remaining old name
grep -r "loragent" ~/.alexgent/ --include="*.md" --include="*.py" --include="*.json" --include="*.jsonc" 2>/dev/null | head -5
# Should return nothing

# opencode loads correctly
opencode --version

# Config paths resolve
ls ~/.alexgent/opencode.jsonc
```

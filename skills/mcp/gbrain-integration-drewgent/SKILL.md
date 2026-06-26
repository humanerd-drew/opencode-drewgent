---
title: gbrain-integration-drewgent
name: gbrain-integration-drewgent
description: Install and configure GBrain as a Hermes MCP server for Drewgent vault hybrid search
type: skill
tags: [gbrain, mcp, vault, search, drewgent]

links:
  - "[[mcp/native-mcp]]"
  - "[[mcp/mcporter]]"
  - "[[@action/skills/SKILL-INDEX]]"
  - "[[@identity/brain/rules]]"
---

# GBrain Integration for Drewgent

Integrate GBrain (by Garry Tan) as an MCP server into Drewgent/Hermes for hybrid search over the `.drewgent` Obsidian vault.

## Prerequisites

- Homebrew
- Ollama running with embedding model (mxbai-embed-large or nomic-embed-text)
- Hermes Agent

## Steps

### 1. Install Bun + GBrain

brew install oven-sh/bun/bun
git clone https://github.com/garrytan/gbrain.git ~/gbrain
cd ~/gbrain && bun install
bun run build:all
bun link

### 2. Initialize PGLite Brain

export PATH="$HOME/.bun/bin:$PATH"
gbrain init --pglite --embedding-model openai:mxbai-embed-large --embedding-dimensions 1536

### 3. Configure Ollama as Embedding Backend

Write to ~/.gbrain/config.json with embedding_disabled: true,
provider_base_urls: { openai: "http://localhost:11434/v1" }

Note: embedding_disabled: true because Ollama's OpenAI-compatible endpoint
is rejected by OpenAI client key validation. Vector search needs real key.

### 4. Import Vault

gbrain sources add drewgent --path /Users/drew/.drewgent --name "Drewgent Vault"
gbrain sources default drewgent
gbrain import /Users/drew/.drewgent/P0-brainstem --source drewgent --yes --no-embed
gbrain extract links --yes

### 5. Register MCP Server

Add to config.yaml under mcp_servers:
  gbrain:
    command: /Users/drew/.bun/bin/gbrain
    args: ["serve"]
    env:
      OPENAI_API_KEY: "ollama-local"

Set env via Python to ensure proper YAML dict format:
import yaml
with open('/Users/drew/.drewgent/config.yaml') as f:
    d = yaml.safe_load(f)
d['mcp_servers']['gbrain']['env'] = {'OPENAI_API_KEY': 'ollama-local'}
with open('/Users/drew/.drewgent/config.yaml', 'w') as f:
    yaml.dump(d, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

### 6. Verify

Verify gbrain is connected via the MCP tools (check `gbrain get_stats` or `gbrain search "test query"`). The MCP server is configured in `~/.config/opencode/opencode.jsonc`.

gbrain search "test query"

### 7. New Session

Start a new agent session for MCP tools to be discovered.

## Available MCP Tools (89)

Key tools: search (keyword FTS), query (hybrid), get_backlinks,
traverse_graph (depth 1-10), get_page, find_orphans, get_stats

## Troubleshooting

### Symptom: MCP timeout / "Connection failed"

```
$ gbrain get_stats
✗ Connection failed (42142ms): MCP call timed out after 40.1s
```

**Step 1 — Count running instances:**
```bash
ps aux | grep "gbrain serve" | grep -v grep
```

If more than one process, **you have a lock contention problem.** PGLite is a single-writer database — multiple `gbrain serve` instances fight for the write lock and only one can respond.

**Step 2 — Identify orphans vs legitimate:**
```bash
for pid in $(ps aux | grep "gbrain serve" | grep -v grep | awk '{print $2}'); do
  ppid=$(ps -o ppid= -p $pid 2>/dev/null | tr -d ' ')
  pcmd=$(ps -o command= -p $ppid 2>/dev/null | head -1)
  echo "gbrain PID $pid ← parent PID $ppid ($pcmd)"
done
```

Two types of parent:
- **Gateway** (`drewgent_cli.main gateway run --replace`) — KEEP this one
- **Hermes CLI** (`hermes` binary, often already terminated) — KILL these

**Step 3 — Fix:**
```bash
# Kill orphans only (gateway's child stays)
kill <orphan-pid-1> <orphan-pid-2>

# Or if you want a clean restart: kill ALL, then gateway restarts its own
killall -m "gbrain serve"

# Verify by calling a gbrain tool directly (e.g. gbrain get_stats)
```

Expected: `✓ Connected (<1s)`, `✓ Tools discovered: 89`

### Symptom: CLI says "Timed out waiting for PGLite lock"

Same root cause as above — multiple gbrain processes competing. Run the diagnostic in step 1-2.

### Symptom: gbrain works then stops after MCP test

Running an MCP test or CLI session can spawn a temporary gbrain subprocess. If the session exits and the child is orphaned, it stays alive holding the PGLite lock, blocking the gateway's gbrain.

**Root cause:** MCP stdio transport does not always clean up child processes when the parent session exits. This is a known pattern with subprocess-based MCP servers — the runtime doesn't detect stdin closure and auto-exit.

## Maintenance

### Automated watchdog (recommended)

A no-agent cron job runs every 15 minutes to detect and kill orphaned gbrain processes:

```bash
# Script: ~/.drewgent/scripts/drewgent_gbrain_watchdog.sh
# Cron:   gbrain-watchdog (ID: 0fb33852686c)
```

The script detects gbrain processes whose parent PID is dead (not launchd-adopted) and kills them. Silent when nothing to clean; reports via cron delivery when cleanup happened.

**Implementation notes:**
- Uses `ps -eo pid,ppid,comm` — never `ps aux` for PPID detection (`ps aux` shows %CPU in column 3, not PPID)
- bash 3.2 compatible (macOS default — no associative arrays)
- Skips processes whose parent PID is 1 (legitimately re-parented by launchd)

### Periodic orphan check (manual)

Run this to detect accumulated orphans:
```bash
orphans=0
for pid in $(ps aux | grep "gbrain serve" | grep -v grep | awk '{print $2}'); do
  ppid=$(ps -o ppid= -p $pid 2>/dev/null | tr -d ' ')
  pcmd=$(ps -o command= -p $ppid 2>/dev/null)
  if ! echo "$pcmd" | grep -q "gateway run"; then
    echo "ORPHAN: gbrain PID $pid (parent $ppid: $pcmd)"
    orphans=$((orphans + 1))
  fi
done
echo "Found $orphans orphan(s)"
```

⚠ **Caveat:** the `ps aux` approach works here because each PID is resolved individually via `ps -o ppid= -p $pid` — never parse the shared `ps aux` output to extract $3 as PPID. Column 3 of `ps aux` is %CPU, not PPID.

### Clean restart (if gateway is down for maintenance)

```bash
killall -m "gbrain serve"
# Gateway will re-spawn gbrain on its next MCP tool call
```

## Pitfalls

- **Orphan accumulation**: each MCP test or CLI session can leave a gbrain orphan. Monitor if you run these frequently.
- **PGLite lock**: single-writer database. Never run concurrent `gbrain serve` instances.
- **OpenAI key validation**: blocks Ollama even with provider_base_urls set. Use `embedding_disabled: true` for local-only.
- **args and env fields**: must be proper YAML dicts in config.yaml, not JSON strings. Use Python YAML writer to fix.
- **MCP tools availability**: only available in sessions started AFTER the MCP server config is saved. Verify by checking the MCP server config in `~/.config/opencode/opencode.jsonc` before starting the session.
- **Parent PID 1**: after gateway restart, old gbrain instances whose parent PID became 1 are also orphans — kill them.

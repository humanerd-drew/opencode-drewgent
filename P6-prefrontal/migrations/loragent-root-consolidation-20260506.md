---
title: Loragent Root Consolidation 2026-05-06
domain: operations
space: claim
type: report
tags: [P6, prefrontal, migration, operations]
created: 2026-05-06
updated: 2026-05-14
links:
  - "[[P5-ego/SELF_MODEL]]"
  - "[[P0-brainstem/brain/rules]]"
  - "[[P4-cortex/knowledge/NEURONFS_RULES]]"
---

# Loragent Root Consolidation - 2026-05-06

## Canonical Runtime

- Runtime home: `~/.loragent`
- Canonical source: `~/.loragent/source/loragent-agent`
- Active launchd plist: `~/Library/LaunchAgents/ai.loragent.gateway.plist`
- Gateway command: `~/.loragent/source/loragent-agent/.venv/bin/python -m loragent_cli.main gateway run --replace`
- Gateway lock directory: `~/.loragent/run/gateway-locks`

## Quarantined Local Roots

The following local Loragent roots were moved under:

`~/.loragent/P6-prefrontal/archive/quarantine-20260506-0224`

- `~/loragent_workspace`
- `~/.loragent.backup.20260501_000957`
- `~/.loragent-lora`
- `~/.local/state/loragent`
- `~/loragent`
- disabled historical Loragent launchd plists under `~/Library/LaunchAgents`
- `~/.codex/skills/loragent-orchestrator`
- `~/.config/opencode/agents/loragent.md`
- `~/bin/loragent-nas-mount.sh`
- `~/SynologyDrive/loragent`
- `~/Library/LaunchAgents/ai.loragent.gateway.plist`
- `~/Library/LaunchAgents/com.loragent.colima.plist`
- `~/Library/LaunchAgents/com.loragent.docker.plist`

## Deliberately Not Moved

These are outside the runtime root but were left in place because moving them can affect sync services, host services, or Codex/OpenCode integration:

- `~/Library/CloudStorage/SynologyDrive-loragent`
- `/Library/LaunchAgents/com.loragent.nas-mount.plist`

`~/Library/CloudStorage/SynologyDrive-loragent` is a Synology File Provider root with delete protection. It was marked hidden, but moving it requires disconnecting/removing the Synology Drive provider or elevated macOS permission.

`/Library/LaunchAgents/com.loragent.nas-mount.plist` is root-owned and was not loaded after consolidation. Moving it requires administrator permission.

## Generic Active Launch Agent

The active gateway launch agent was renamed to remove the Loragent name outside the runtime root:

- `~/Library/LaunchAgents/ai.custom-agent.gateway.plist`
- label: `ai.custom-agent.gateway`

## Verification

- Targeted gateway/CLI tests passed from the canonical source root.
- Gateway restarted from the canonical source root.
- Runtime lock moved from `~/.local/state/loragent` to `.loragent/run/gateway-locks`.

## Links
- [[P5-ego/SELF_MODEL]]
- [[P0-brainstem/brain/rules]]
- [[P4-cortex/knowledge/NEURONFS_RULES]]

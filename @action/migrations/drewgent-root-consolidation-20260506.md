---
title: Drewgent Root Consolidation 2026-05-06
domain: operations
space: claim
type: report
tags: [P6, prefrontal, migration, operations]
created: 2026-05-06
updated: 2026-05-14
links:
  - "[[@identity/SELF_MODEL]]"
  - "[[@identity/brain/rules]]"
  - "[[@memory/knowledge/NEURONFS_RULES]]"
---

# Drewgent Root Consolidation - 2026-05-06

## Canonical Runtime

- Runtime home: `/Users/drew/.drewgent`
- Canonical source: `/Users/drew/.drewgent/source/drewgent-agent`
- Active launchd plist: `/Users/drew/Library/LaunchAgents/ai.drewgent.gateway.plist`
- Gateway command: `/Users/drew/.drewgent/source/drewgent-agent/.venv/bin/python -m drewgent_cli.main gateway run --replace`
- Gateway lock directory: `/Users/drew/.drewgent/run/gateway-locks`

## Quarantined Local Roots

The following local Drewgent roots were moved under:

`/Users/drew/.drewgent/P6-prefrontal/archive/quarantine-20260506-0224`

- `/Users/drew/drewgent_workspace`
- `/Users/drew/.drewgent.backup.20260501_000957`
- `/Users/drew/.drewgent-lora`
- `/Users/drew/.local/state/drewgent`
- `/Users/drew/loragent`
- disabled historical Drewgent launchd plists under `/Users/drew/Library/LaunchAgents`
- `/Users/drew/.codex/skills/drewgent-orchestrator`
- `/Users/drew/.config/opencode/agents/drewgent.md`
- `/Users/drew/bin/drewgent-nas-mount.sh`
- `/Users/drew/SynologyDrive/drewgent`
- `/Users/drew/Library/LaunchAgents/ai.drewgent.gateway.plist`
- `/Users/drew/Library/LaunchAgents/com.drewgent.colima.plist`
- `/Users/drew/Library/LaunchAgents/com.drewgent.docker.plist`

## Deliberately Not Moved

These are outside the runtime root but were left in place because moving them can affect sync services, host services, or Codex/OpenCode integration:

- `/Users/drew/Library/CloudStorage/SynologyDrive-drewgent`
- `/Library/LaunchAgents/com.drewgent.nas-mount.plist`

`/Users/drew/Library/CloudStorage/SynologyDrive-drewgent` is a Synology File Provider root with delete protection. It was marked hidden, but moving it requires disconnecting/removing the Synology Drive provider or elevated macOS permission.

`/Library/LaunchAgents/com.drewgent.nas-mount.plist` is root-owned and was not loaded after consolidation. Moving it requires administrator permission.

## Generic Active Launch Agent

The active gateway launch agent was renamed to remove the Drewgent name outside the runtime root:

- `/Users/drew/Library/LaunchAgents/ai.custom-agent.gateway.plist`
- label: `ai.custom-agent.gateway`

## Verification

- Targeted gateway/CLI tests passed from the canonical source root.
- Gateway restarted from the canonical source root.
- Runtime lock moved from `~/.local/state/drewgent` to `.drewgent/run/gateway-locks`.

## Links
- [[@identity/SELF_MODEL]]
- [[@identity/brain/rules]]
- [[@memory/knowledge/NEURONFS_RULES]]

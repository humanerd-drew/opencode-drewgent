---
title: harvester-memory-sync
description: Sync trend-harvester analyzed output to P2-hippocampus memories — bidirectional bridge between P4-cortex growth engine and P2-hippocampus long-term memory
space: outcome
type: document
tags: [growth, memory, sync, P2, P4, harvester]
links:
  - "[[@action/skills/brain/DESCRIPTION]]"
  - "[[@action/skills/SKILL-INDEX]]"
source: Drewgent P4→P2 pipeline, Loopy-Era integration
---

# Harvester Memory Sync — P4→P2 Bridge

## Purpose

Sync trend-harvester's analyzed trends to P2-hippocampus long-term memory.
Keeps P2-hippocampus/memories/insights/ in sync with P4-cortex/growth/trend-harvester/ analyzed output.

This closes the P4→P2 downstream flow: trend-harvester output must reach
P2-hippocampus/memories/ so the full memory layer benefits from growth insights.

## Trigger

- **Primary**: Run automatically after trend-harvester-001 job completes
- **Fallback**: Run on-demand via `python3 scripts/harvester_memory_sync.py`

## Data Flow

```
P4-cortex/growth/trend-harvester/
  collected/     ← raw data (NOT synced)
  analyzed/      ← scored trends → COPY to P2 memories
    keep/        ← score ≥ 6.0 → insights/YYYY-MM.md
    review/      ← 4.0 ≤ score < 6.0 → insights/pending/
    graveyard/   ← NOT synced
  pending/       ← approved trends → concepts/
  applied/       ← applied trends → concepts/ + notes

P2-hippocampus/memories/
  insights/      ← trend insights (by date)
  concepts/      ← applied concept files
```

## Sync Rules

| Source (P4) | Destination (P2) | Action |
|---|---|---|
| `analyzed/keep/*.json` | `insights/YYYY-MM.md` | Append to monthly insight |
| `analyzed/review/*.json` | `insights/pending/` | Create pending insight file |
| `analyzed/graveyard/*.json` | — | Skip (no sync) |
| `pending/*.json` | `concepts/` | Create/update concept file |
| `applied/*.json` | `concepts/` | Create/update concept + tag `trend-applied` |

## Anti-Duplication

- Use content hash (MD5 of trend URL or description) as dedup key
- Check if same hash already exists in target before writing
- Track synced hashes in `drewgent_hidden_state.json["harvester_synced_hashes"]`

## State Tracking

Read/write from `P4-cortex/knowledge/drewgent_hidden_state.json`:

```json
{
  "harvester_synced_hashes": ["hash1", "hash2"],
  "last_sync_at": "2026-05-12T10:00:00+09:00",
  "last_sync_job": "trend-harvester-001",
  "synced_count": 42
}
```

## Script Usage

```bash
# Manual run
python3 scripts/harvester_memory_sync.py

# Dry run (show what would be synced)
python3 scripts/harvester_memory_sync.py --dry-run
```

## Exit Codes

- `0`: Sync complete, no errors
- `1`: Partial sync (some files failed)
- `2`: No trend-harvester output found (not an error — job may not have run yet)

## Related
- [[@action/skills/SKILL-INDEX]]
- [[@action/skills/brain/DESCRIPTION]]

# P2-hippocampus — Memory

Persistent memory and knowledge storage. Runtime data lives here and is **not** committed to git (see `.gitignore`).

## Structure

| Directory | Purpose | In repo? |
|-----------|---------|----------|
| `kanban/` | Kanban task board SQLite DB | ❌ personal |
| `knowledge/` | Long-term knowledge base | ❌ personal |
| `memories/` | Session insights, learned patterns | ❌ personal |
| `qa-evidence/` | QA verification artifacts | ❌ personal |

## Runtime Files

- `logging_v2.db` — structured agent log
- `response_store.db` — cached responses

All `.db` files are gitignored.

## See Also

- `P4-cortex/` — growth, pattern recognition, content
- `skills/brain/` — memory management skills

# Cron Output Graph Bloat — Session Diagnosis

**Date**: 2026-06-14
**Trigger**: User asked "옵시디언 그래프뷰를 보니까 칸반과 관련한 클러스터가 엄청 큰데 왜 그런거야?"

## Findings

### Scale
- Vault: 11,324 `.md` files
- Cron output files: **6,038** under `~/.drewgent/cron/output/a4f8c2e1b123/`
- Top wikilink hits:
  - `[[@memory/growth/drewgent-kanban-implementation-plan]]` — 11,576
  - `[[kanban-orchestrator]]` — 11,565
  - `[[kanban-dashboard]]` — 11,564

### Root Cause
The `kanban-dispatcher-content` cron job (ID `a4f8c2e1b123`) runs every minute. Each output file embeds the full **kanban-worker** skill text (frontmatter + body), which contains 3 wikilinks in its `links:` field:
```yaml
links:
  - "[[@memory/growth/drewgent-kanban-implementation-plan]]"
  - "[[kanban-dashboard]]"
  - "[[kanban-orchestrator]]"
```
Each cron output → 3 graph edges. 6,038 × 3 = ~18,000 edges from cron alone.

### Non-Cron Files
Only ~18 files outside `cron/output/` reference these kanban hub pages — mostly actual Skill files and their own reference docs. The real kanban cluster would be ~18 nodes, not 6,000+.

### Diagnosis Steps Used
1. Counted files mentioning "kanban": `grep -rli 'kanban' ~/.drewgent --include='*.md' | wc -l` → 5,883
2. Found most common wikilinks: `grep -roh '\[\[[^]]*[Kk]anban[^]]*\]\]' | sort | uniq -c | sort -rn` → 3 nodes with 11K+ hits each
3. Traced to cron output dir: `find ~/.drewgent/cron/output -name '*.md' | wc -l` → 6,038
4. Verified content: `head -30 <cron-output> | grep -A5 '^links:'` → confirmed skill frontmatter embedded

## Fix Options (in priority order)

| # | Approach | Command |
|---|----------|---------|
| 1 | Exclude from Obsidian | Add `cron/output/*` to `.obsidian/app.json` excludedFiles |
| 2 | Clean old outputs | `find ~/.drewgent/cron/output -name '*.md' -mtime +7 -delete` |
| 3 | Fix cron template | Strip skill frontmatter from cron output template |

## Related
- `kanban-dispatcher-hardening` skill — kanban dispatcher infrastructure
- `vault-health` skill (this umbrella) — graph health section

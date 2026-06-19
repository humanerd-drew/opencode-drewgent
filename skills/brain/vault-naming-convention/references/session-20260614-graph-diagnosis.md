# Session Reference: 2026-06-14 Vault Graph Bloat & Naming Diagnosis

## Problem

Obsidian Graph View showed a massive kanban cluster that dwarfed the rest of the vault.

## Root Cause Analysis

Three layers of issues:

### Layer 1: Cron Output Graph Bloat (Surface)

3 kanban-dispatcher cron jobs (a4f8c2e1b123, d1ef68ced116, cb909be06e0e) ran every 1 minute, each saving output to `cron/output/<job_id>/`. Each output file embedded the full kanban-worker skill text (including frontmatter with 3 wikilinks).

Stats:
- Total files: ~9,600
- Total size: ~45MB
- Hub nodes: `drewgent-kanban-implementation-plan` (11,576 hits), `kanban-orchestrator` (11,565), `kanban-dashboard` (11,564)
- Fake graph edges created: ~56,000

Fix: Moved to `.trash/` + Obsidian exclusion on `cron/output/`.

### Layer 2: Filename Collisions (Structural)

| File | Duplicates | Resolution |
|------|-----------|------------|
| SOUL.md | 4 | Root copy deleted (identical to P1-limbic/persona/SOUL.md). Docker copies excluded via source/ exclusion. **Note**: Hermes Agent's `_ensure_default_soul_md()` recreates root SOUL.md if missing — renamed to `HERMES_SYSTEM_PROMPT.md` to avoid regeneration conflict. |
| SCHEMA.md | 3 | Nested ~/.drewgent/~/.drewgent/ moved to .trash. Source copy excluded. |
| index.md | 29 | Must use full-path wikilinks. |
| SKILL.md | 316 | By design — referenced via path context. |

### Layer 3: Sparse Mesh Connectivity (Cultural)

- Average wikilinks per file: 3.2 (target: 5-10)
- 3 dominant star clusters (SEO articles → INTEGRATION_PROTOCOL, SEO → harvester, various → SKILL-INDEX)
- Very few sideways or downward connections

## User's Insight

"SEO를 생각해보면 중복 이름 자체가 노이즈" — duplicate filenames waste resolution budget. Fix the root cause (unique naming), not the symptom (using full canonical paths).

## Resolution Steps Taken

1. Moved 3 cron output directories to `.trash/` (9,600 files, ~45MB)
2. Renamed root SOUL.md → HERMES_SYSTEM_PROMPT.md (Hermes system prompt, not Drewgent identity)
3. Renamed docker/SOUL.md → DOCKER_PERSONA.md
4. Moved nested ~/.drewgent/~/.drewgent/ to .trash/
5. Added `cron/output`, `source`, `.trash`, `_agent` to Obsidian exclusion in `app.json`
6. Created `vault-naming-convention` and `vault-health` skills with naming rules and exclusion docs

## P-Layer Mesh Cross-Links Added (2026-06-14)

16 new wikilinks added to core P-layer files to create bidirectional mesh topology:

| File | Before | After | New Links |
|------|--------|-------|-----------|
| P0-brainstem/brain/rules.md | 22 | 25 | INTEGRATION_PROTOCOL, SCHEMA, NEURONFS_RULES |
| P1-limbic/persona/writing-style-guide.md | 4 | 6 | rules, SELF_MODEL |
| P2-hippocampus/memories/index.md | 0 (no links section) | 4 | SELF_MODEL, rules, SCHEMA, INTEGRATION_PROTOCOL |
| P2-hippocampus/memories/SCHEMA.md | 8 (incl. 2 short-name) | 10 | SELF_MODEL, rules (also fixed concepts/index and insights/index to full paths) |
| P3-sensors/gateway/drewgent-architecture-dataflow.md | 8 | 9 | NEURONFS_RULES |
| P4-cortex/growth/INTEGRATION_PROTOCOL.md | 5 | 8 | SKILL-INDEX, NEURONFS_RULES, SCHEMA |
| P4-cortex/knowledge/NEURONFS_RULES.md | 5 | 7 | SKILL-INDEX, INTEGRATION_PROTOCOL |
| P5-ego/SELF_MODEL.md | 22 | 24 | index, MEMORY_wiki |

Resulting mesh topology:
```
SELF_MODEL ↔ rules ↔ SCHEMA ↔ SELF_MODEL          (bidirectional triangle)
SELF_MODEL ↔ rules ↔ INTEGRATION_PROTOCOL ↔ NEURONFS_RULES ↔ SKILL-INDEX ↔ SELF_MODEL
                                  ↕
                              SCHEMA
style-guide → rules, SELF_MODEL                   (new upward)
arch-dataflow → NEURONFS_RULES                    (new sideways)
SELF_MODEL → index, MEMORY_wiki                   (new downward)
```

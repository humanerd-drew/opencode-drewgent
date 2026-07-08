---
name: vault-health
title: Vault Health
type: skill
space: outcome
description: Maintain .drewgent as an Obsidian vault — graph connectivity overhaul (P-layer mesh, skill clusters, SEO article web), broken link detection, backlink density verification via Obsidian CLI, filename deduplication, bidirectional linking, auto-generated orphan management, cron output graph bloat prevention, and Obsidian compatibility.
tags: [outcome, vault, obsidian, graph]
created: 2026-06-11
updated: 2026-06-14
links:
  - "[[@identity/brain/Drewgent-brain/P0-brainstem/禁/禁brain_obsidian_graph.neuron]]"
  - "[[@identity/brain/rules]]"
  - "[[@identity/persona/SOUL]]"
  - "[[@memory/kanban/KANBAN_INDEX]]"
  - "[[@action/gateway/drewgent-architecture-dataflow]]"
  - "[[@action/skills/SKILL-INDEX]]"
  - "[[@memory/growth/INTEGRATION_PROTOCOL]]"
  - "[[@memory/knowledge/NEURONFS_RULES]]"
  - "[[@identity/SELF_MODEL]]"
---


# Vault Health

Drewgent's internal knowledge base (.drewgent/) IS an Obsidian vault. This skill covers maintaining its health — broken link detection, backlink density, graph connectivity, auto-generated orphan management, and Obsidian compatibility.

## Principles

1. **Prevention over detection.** Fix the root cause so nothing needs ongoing management. "관리할 일이 안생기게 애초에 잘하던가." A rule/cronjob that only reports problems is not a solution — fix the source.
2. **Every file should have ≥1 inbound and ≥1 outbound wikilink.** Orphans defeat the graph.
3. **Body wikilinks > frontmatter `links:`.** Obsidian Graph View prioritizes body links. Frontmatter links should be mirrored in body.
4. **Bidirectional linking.** If A links to B, B should link back to A (or be reachable via a hub node). After any linking pass, verify bidirectionality.
5. **Unique filenames are essential.** Duplicate filenames (e.g., `SOUL.md` × 4, `index.md` × 29) cause broken wikilinks and ambiguous resolution. Every `.md` file in the vault should have a unique slug. Before creating a file, check for naming collisions. This is the vault's SEO: each resource gets one canonical name.
6. **Obsidian compatibility.** `.neuron` files must be registered as markdown extensions. Template variables (`{doc_name}`) are acceptable orphans.
7. **Auto-generated orphans are by design.** Telemetry/log files that are write-only (never read back) should be excluded from graph view or deleted. Their inbound link count is 0 and will stay 0 — that's correct.
8. **Operational files stay out of the graph.** `cron/output`, `source/`, `.trash/`, `_agent/`, `venv/` should be in Obsidian `userIgnoreFilters`. They are runtime artifacts, not knowledge.

## Detection

```bash
# Dangling wikilinks (MEMORY.md targets that don't exist as files)
bash ~/.hermes/scripts/drewgent_graph_gap_analysis.sh

# Full vault audit (Python — see references/vault-audit.py)
python3 references/vault-audit.py
```

## 3-Step Vault Health Protocol

### Step 1: Obsidian `.neuron` Compatibility

`.neuron` files are the actual rule definitions (13 P0 neurons), but Obsidian ignores non-`.md` extensions.

**Fix** (`~/.drewgent/.obsidian/app.json`):
```json
{
  "extensionOverrides": [".neuron"]
}
```

This single change makes `[[禁task_qa_gate.neuron]]` resolve in Obsidian Graph View. No file renames, no path changes.

### Step 2: frontmatter `links:` → Body Wikilinks

Many vault files define crosslinks ONLY in YAML frontmatter. Obsidian Graph View sees these weakly or not at all. Mirror them into the body at the end of the file.

**Script approach** (one-time, across all core files):
1. Parse YAML frontmatter for `links:` list
2. Extract wikilink targets from each list item
3. Check which targets already appear in body wikilinks
4. Add missing targets under a `## Links` section at the file end

### Step 3: Bidirectional Crosslinks (incident ↔ neuron)

Incident docs (P6-prefrontal/incidents/) and neurons (P0-brainstem/禁*.neuron) should link to each other. Without this, the graph has two disconnected clusters.

**Mapping**: by topic affinity. Each incident doc gets `## Related Neurons`; each neuron gets `## Related Incidents`.

## ~~GBrain~~ → Knowledge DB (SQLite FTS5 + Ollama)

GBrain was removed on 2026-07-04/05. Replaced by:
- **`knowledge.db`** — SQLite FTS5 (keyword) + Ollama nomic-embed-text (vector)
- **`recall()` / `remember()`** — opencode native MCP tools (auto-discovered)
- **`scripts/recall.py`** — CLI equivalent

See AGENTS.md "Knowledge Management" section for full architecture.

## Auto-Generated Orphan Management

### Brain Signal Pattern (brain_signals_*.md)

The agent's `BrainSignalMonitor` writes session telemetry to `monitor/brain_signals_{ts}.md` when DeliveryRouter is unavailable. These files:

- Are **write-only by design** — agent never reads them back
- Accumulate rapidly (~170/day, 5000+/month)
- Clutter the Obsidian Graph as orphan nodes (0 inbound links)
- Duplicate data already in `gateway.log` and `brain_signal_log.jsonl`

**Fix**:
1. **Stop generating them**: remove the fallback `_deliver_fallback()` call in `brain_monitor.py:_deliver()`
2. **Delete existing**: `rm monitor/brain_signals_*.md`
3. **Keep**: `brain_signal_log.jsonl` (compressed, single-file alternative)

### General Pattern

When encountering auto-generated orphans:
1. Check if any code reads them back → if no, they're write-only telemetry
2. Check if the same data exists elsewhere (log files, JSONL) → if yes, the .md files are redundant
3. Decision: stop generating OR filter from graph view

## Cron Output Graph Bloat

Cron job output files (`~/.drewgent/cron/output/<job_id>/`) accumulate every run as `.md` files. When a cron job loads a skill with frontmatter `links:` containing wikilinks, each output file embeds those links — creating a **massive star cluster** in the Obsidian graph view where a few hub nodes each have thousands of connections.

**Signature**: 3-5 hub nodes with 10K+ inbound edges each, forming a cluster that dwarfs the rest of the graph. The hub nodes are skill pages or implementation plans referenced in cron job context.

**Diagnosis**:
```bash
# Find the most common wikilinks — rank by frequency
grep -roh '\[\[[^]]*\]\]' ~/.drewgent --include='*.md' | sort | uniq -c | sort -rn | head -20

# Check cron output volume
find ~/.drewgent/cron/output -name '*.md' | wc -l

# Verify cron output embeds a skill with frontmatter links
head -30 ~/.drewgent/cron/output/<job_id>/<recent-run>.md | grep -A5 '^links:'
```

**Root cause**: Cron job loads a skill → output template includes full skill text (frontmatter + body) → frontmatter `links:` wikilinks get baked into every output file → N runs × M links = N×M extra graph edges.

**Fix options** (in priority order):

| Option | When to use | How |
|--------|-------------|-----|
| 1. Exclude from Obsidian | Cron outputs are reference-only (agent reads via `session_search`, not vault browser) | Add `"userIgnoreFilters": ["cron/output"]` to `~/.drewgent/.obsidian/app.json`. Note: use `cron/output` (not `cron/output/*`) — Obsidian interprets directory patterns as recursive. |
| 2. Move to `.trash/` | Need recovery option before deletion | `mkdir -p ~/.drewgent/.trash && mv ~/.drewgent/cron/output/<job_id> ~/.drewgent/.trash/<label>-$(date +%Y%m%d)` |
| 3. Periodic cleanup | Old outputs accumulate without value | `find ~/.drewgent/cron/output -name '*.md' -mtime +X -delete` as a cron job |
| 4. Fix cron template | You control the cron job; skill inline is unnecessary overhead | Strip frontmatter from output template, or remove wikilinks from stored artifact |

**Reference**: `references/cron-output-graph-bloat.md` has a full session diagnosis with concrete numbers and commands used. Read it when investigating an active graph bloat incident.

**Prevention**: Before adding a cron job that loads a skill, check whether the output format includes the full skill text. If yes, either strip frontmatter from the output, exclude the path from Obsidian, or use `no_agent=True` (script-only) jobs when possible — they don't load skills.

## Vault File Size Health

Core vault files (structural zones P0-P6 excluding auto-generated SEO articles) should be:
- **>50 bytes**: below this → likely empty/stub
- **<100 KB**: above this → candidate for splitting

Use `references/vault-audit.py` for file-size analysis.

## Broken Link Types and Fixes

| Type | Pattern | Fix |
|------|---------|-----|
| 1 | `[[concepts]]`, `[[insights]]` — directory exists, no index.md | Create `index.md` |
| 2 | `[[preferences.md]]` — entity in `.archive/` | Restore to `entities/` |
| 3 | `[[pagename]]` — SCHEMA.md syntax examples | HTML escape |
| 4 | `{doc_name}` — template variables | Leave as-is (intentional) |
| 5 | `[[brain-broken-link-fix]]` — wrong path | Fix to `[[skills/brain-broken-link-fix/SKILL]]` |
| 6 | `monitor/brain_signals_*.md` — auto-generated orphans | Delete or graph-hide |
| 7 | `[[@identity/.../禁/禁xxx]]` — missing `.neuron` extension | Add `.neuron`: `[[.../禁/禁xxx.neuron]]` |
| 8 | `[[skills/content-pipeline]]` — SKILL.md is nested under directory | Use `[[skills/content-pipeline/SKILL]]` |
| 9 | `[[@memory/knowledge/index]]` — ambiguous (29 `index.md` files) | Use full path or disambiguate |

## Graph Connectivity Overhaul Methodology

When the vault graph has poor connectivity (star patterns, disconnected clusters, low average links per node), use this systematic 3-layer approach:

### Layer 1: P-layer Mesh (the skeleton)

The 10 core P-layer files (rules, SOUL, writing-style, index, SCHEMA, arch-dataflow, SKILL-INDEX, INTEGRATION_PROTOCOL, NEURONFS_RULES, SELF_MODEL) form the vault's structural skeleton. They should form a **mesh** (not a star/hub topology):

1. **Check current links**: read each file's frontmatter `links:` section
2. **Add missing sideways links**: P2→P5, P3→P4, P0→P4, etc. — not just UPWARD (child→parent) but SIDEWAYS (peer→peer) and DOWNWARD (parent→child)
3. **Verify bidirectionality**: run `obsidian backlinks path="<file>.md" total` for each core file to confirm Obsidian sees the links
4. **Target**: 8-25 outbound links per core file, with cycles (A→B→C→A) for organic graph appearance

### Layer 2: Skill Clusters (the muscles)

Skills are organized by category directory, but each SKILL.md typically only links to SKILL-INDEX. To create mesh within categories:

1. **Identify natural clusters**: skills that share a workflow or dependency chain (e.g., refactoring cluster: `codebase-refactoring`, `incremental-refactoring`, `codebase-structure-audit`, `codebase-consolidation`, `simplify-code`, `project-code-audit`)
2. **Add bidirectional links** between skills in the same cluster
3. **Link to P-layer rules**: `[[@identity/brain/rules]]` — every skill is governed by the rules
4. **Link to SKILL-INDEX**: `[[@action/skills/SKILL-INDEX]]` — every skill is indexed
5. **Convert `related_skills` metadata** to actual frontmatter `links:` wikilinks (metadata is machine-readable but doesn't create Obsidian graph edges)
6. **Batch edit via Python**: find the `links:` section or closing `---`, insert new entries, write back

### Layer 3: SEO Article Web (the knowledge base)

SEO articles (2,500+ files in `P2-hippocampus/knowledge/seo-articles/`) often link to only 2 hub pages. To create a content mesh:

1. **Analyze metadata**: check for `keyword:`, `cluster:`, `hub:`, `tags:` fields
2. **Convert plain-text hub refs to wikilinks**: replace `hub_name` with `[[hub_name]]` in `links:` sections
3. **Add hub→hub links**: related hubs link to each other (e.g., onpage_seo ↔ technical_seo)
4. **Add See also sections**: add `## See also` with topic hub links to article bodies (creates inline body wikilinks)
5. **Source-domain clustering**: for articles without cluster metadata (2026 articles), group by source domain in `tags:` and cross-link within groups

## Obsidian CLI Verification

After any graph modification, verify with Obsidian's own resolver (not grep):

```bash
# Check backlink counts for core files
obsidian backlinks path="P0-brainstem/brain/rules.md" total
obsidian backlinks path="P5-ego/SELF_MODEL.md" total
obsidian backlinks path="P1-limbic/persona/SOUL.md" total

# Check skill backlinks
obsidian backlinks path="skills/software-development/test-driven-development/SKILL.md" total
obsidian backlinks path="skills/neuron-fs-brain/SKILL.md" total

# Check SEO hub backlinks
obsidian backlinks path="P2-hippocampus/knowledge/seo-articles/2026/SEO_ai_llm_search_Hub.md" total

# Check linking direction: does file A link to file B?
# (Obsidian doesn't have a "links to" command, so use grep on frontmatter)

# Verify Obsidian exclusion list
cat ~/.drewgent/.obsidian/app.json

# Tag distribution
obsidian tags sort=count counts
```

Obsidian's backlink count is the source of truth — it uses the actual graph resolver, not filesystem grep. If Obsidian sees it, it's a real edge.

---
name: vault-naming-convention
title: Vault Naming Convention
type: skill
space: outcome
description: Filename uniqueness, wikilink resolution safety, P-layer identity in naming, and Obsidian exclusion boundaries. Prevents duplicate-name ambiguity and graph pollution.
tags: [outcome, vault, obsidian, naming, graph]
created: 2026-06-14
updated: 2026-06-14
links:
  - "[[P0-brainstem/brain/rules]]"
  - "[[P1-limbic/persona/SOUL]]"
  - "[[P5-ego/SELF_MODEL]]"
  - "[[P4-cortex/knowledge/NEURONFS_RULES]]"
  - "[[brain-broken-link-fix/vault-health]]"
---

# Vault Naming Convention

Every file in the Drewgent vault is a node in the knowledge graph. **Filename uniqueness** ensures wikilinks resolve deterministically. **P-layer prefix** preserves priority identity. **Exclusion boundaries** keep operational noise out of the graph.

## Why This Matters (The SEO of Knowledge)

Duplicate filenames waste "resolution budget" — the same way duplicate content wastes search engine crawl budget:

- `[[SOUL]]` with 4 `SOUL.md` files → Obsidian guesses, possibly wrong
- `[[SCHEMA]]` with 3 `SCHEMA.md` files → ambiguous reference
- Agent reading the vault must resolve ambiguity → compute waste

From NeuronFS: the P-layer prefix (P0-P6) is structural IDENTITY, not just a folder. Losing it in a short-name link loses priority information.

## Rule: Unique Basenames in Structural Zones

**Structural zones** = paths that form the knowledge graph:
- `P0-brainstem/` through `P6-prefrontal/`
- `skills/` (each skill has its own `SKILL.md`)
- `humanerd-site/`

**Non-structural zones** (excluded from Obsidian, can have duplicates):
- `source/` — drewgent-agent upstream code
- `cron/output/` — operational logs
- `.trash/` — recovery staging
- `_agent/` — runtime state
- `node_modules/`, `archive/`

### Enforcement

Every `.md` file in structural zones must have a unique basename (case-sensitive):

```bash
find ~/.drewgent -name '*.md' \
  -not -path '*/cron/*' -not -path '*/.trash/*' \
  -not -path '*/source/*' -not -path '*/_agent/*' \
  -not -path '*/node_modules/*' -not -path '*/archive/*' \
  2>/dev/null | while read f; do basename "$f"; done \
  | sort | uniq -c | sort -rn | awk '$1 > 1 {print $1, $2}'
```

## Wikilink Convention by Scope

| Scope | Recommended Style | Example |
|-------|------------------|---------|
| Unique filename | Short name `[[Slug]]` | `[[SELF_MODEL]]`, `[[rules]]` |
| Non-unique filename | Full path `[[P-layer/path/Slug]]` | `[[P1-limbic/persona/SOUL]]` (not bare `[[SOUL]]`) |
| Skill file | `[[skills/category/name/SKILL]]` | `[[skills/devops/kanban-worker/SKILL]]` |
| Neuron file | `[[P0-brainstem/禁/slug]]` | `[[P0-brainstem/禁/禁task_qa_gate.neuron]]` |

## Obsidian Exclusion Configuration

`~/.drewgent/.obsidian/app.json` controls what Obsidian indexes:

```json
{
  "extensionOverrides": [".neuron"],
  "userIgnoreFilters": [
    "cron/output",
    "source",
    ".trash",
    "_agent"
  ]
}
```

### When to Exclude a Directory

A directory should be excluded from Obsidian when it contains:
- **Operational logs** (cron outputs, telemetry) — write-only by design, create fake graph edges
- **Source code** (drewgent-agent upstream) — not vault content, 725MB of noise
- **Recovery staging** (.trash) — temporary, should not be in the graph
- **Runtime state** (_agent) — ephemeral, changes every session

## Graph Quality Metrics

A healthy vault graph has:

| Metric | Target | Current (2026-06-14) |
|--------|--------|----------------------|
| Files with ≥1 wikilink | >90% | 76% |
| Average wikilinks per file | 5-10 | 3.2 |
| Bidirectional pairs | >60% | unknown |
| Dominant star cluster size | <5% of files | ~55% (SEO articles → INTEGRATION_PROTOCOL) |

### Star vs Mesh Pattern

**Star**: One hub node connected to thousands of leaves. Leaves connect to nothing else.
- Problem: No traversal value. The graph looks connected but isn't useful.
- Causes: Cron output bloat, SEO articles with only hub links, auto-generated indexes.

**Mesh**: Nodes have 3-10 connections to related content. Cycles exist (A↔B↔C↔A).
- Benefit: Traversal finds meaningful related content. Graph is "organic."
- How to achieve: Add bidirectional cross-links, topic-based clustering, avoid hub-only linking.

### Real-Time Verification (Obsidian CLI)

The `obsidian` CLI queries a running Obsidian instance and returns **true** resolved backlink counts (not grep estimates):

```bash
# Real backlinks for a specific file
obsidian backlinks path="P5-ego/SELF_MODEL.md" total

# Check if generic 'Skill' title makes node anonymous
# Any SKILL.md with `title: Skill` in frontmatter renders as "SKILL" in graph view
grep -rl '^title: Skill$' ~/.drewgent/skills --include='SKILL.md' \
  --exclude-dir=optional-skills --exclude-dir=plugins

# Fix: replace with directory-derived name
# test-driven-development/SKILL.md → title: Test Driven Development
```

**Note**: Each `obsidian backlinks` call takes ~3-5s. Do NOT batch-iterate over all files — use grep for bulk estimates, then Obsidian CLI for spot-check verification.

### Diagnosis Commands

```bash
# Inbound link distribution (identify star hubs)
grep -roh '\[\[[^]]*\]\]' ~/.drewgent --include='*.md' \
  | sed 's/\[\[//;s/\]\]//' | sort | uniq -c | sort -rn | head -20

# Files with N=1 outbound link (daisy chain)
grep -c '\[\[[^]]*\]\]' ~/.drewgent/P0-brainstem/**/*.md 2>/dev/null

# Orphan files (0 inbound, 0 outbound)
# Use gbrain find_orphans or scan manually
```

## Philosophy: Build It Right Once

The vault should require **zero maintenance** for naming hygiene. Not a monitoring cron job, not a report — just the right conventions enforced at creation time.

**User's explicit correction (2026-06-14)**: When investigating a vault problem, do NOT default to "let's set up a cron job that reports X." Instead, fix the root cause so there is nothing to report. "리포트를 보내면 끝? 관리를 해야지... 더 중요한건 관리할 일이 안생기게 애초에 잘하던가."

This applies to every vault-hygiene task: prefer structural fixes (rename, exclude, solve at source) over detection/reporting loops.

### Zero-Maintenance Principle

| Instead of this | Do this |
|----------------|---------|
| Cron job that reports duplicates | Ensure unique names at file creation |
| Monthly cleanup of noise files | Exclude operational dirs from Obsidian at vault setup |
| Script to fix broken wikilinks | Always use full-path `[[P-layer/path/Slug]]` for ambiguous names |
| Monitoring dashboard | One-time structural fix (the current state) |

**Decision tree**: when you spot a recurring vault issue, ask "can I make it impossible for this to happen again?" If yes, do that. A report/cron/alert is the fallback only when the root cause genuinely cannot be eliminated.

**When to exclude from Obsidian** (not "when to add a cleanup job"):
- `cron/output/` — operational logs, creates fake graph edges
- `source/` — upstream code, not vault content
- `.trash/` — recovery staging
- `_agent/` — runtime state, ephemeral

### Dual-Namespace Reality

`~/.drewgent/` is shared by two systems:

| Namespace | Owner | Convention | Example files |
|-----------|-------|-----------|--------------|
| Root level | **Hermes Agent** runtime | No vault wikilinks to root files | `SOUL.md`, `config.yaml`, `.env`, `CHANGELOG.md` |
| P-layer dirs | **Drewgent vault** knowledge | Always use full-path wikilinks | `P1-limbic/persona/SOUL.md`, `P0-brainstem/brain/rules.md` |

Hermes Agent's `_ensure_default_soul_md()` in `hermes_cli/config.py` seeds `~/SOUL.md` if missing — this is correct behavior. The root `SOUL.md` is the **Hermes system prompt**, not Drewgent's identity document. Drewgent's identity lives at `P1-limbic/persona/SOUL.md`.

**Rule**: Never create a vault wikilink to a root-level file. Root = Hermes runtime. P-layers = Drewgent knowledge.

## Organic Mesh Connectivity

### Priority Order

When improving graph connectivity, follow this order (per user preference, 2026-06-14):

1. **P-layer core** — rules.md, SOUL.md, SELF_MODEL.md, SCHEMA.md, SKILL-INDEX.md, INTEGRATION_PROTOCOL.md, NEURONFS_RULES.md — add missing bidirectional, downward, and sideways links
2. **Skills** — related-skill cross-links between SKILL.md files in the same category
Content — SEO articles topic-based cross-links (lowest priority; see `references/seo-article-crosslinking-20260614.md` for full pipeline)

### Reference: Skill Cross-Linking Session

See `references/skill-cross-linking-20260614.md` for the detailed session log: which skills were linked, broken links found, and the `related_skills → wikilinks` conversion technique.

## Broken Link Audit Methodology

When auditing vault wikilinks, **most "broken" links found by naive grep are false positives**. The real broken count is far smaller. Always apply these filters:

### False Positive Categories

| Source of false positive | Pattern | Why it's OK |
|--------------------------|---------|-------------|
| **Template variables** | `[[{{project_id}}]]`, `[[projects/{{slug}}]]` | In `.episodes-template.md` and similar — never meant to resolve |
| **SEO article short-names** | `[[10 ChatGPT SEO Tools That Help You Rank Higher]]` | Obsidian resolves by basename — file is in `2025/` subdir |
| **Code block content** | `[[elapsedTime]]`, `[[totalTime]]`, `[[count]]` | Inside code fences — grep finds them, Obsidian ignores |
| **Script references** | `[[scripts/run_kanban_worker.py]]` | Not .md files — referenced as documentation, not graph nodes |

### Audit Protocol

```python
import re, os

vault_root = "/Users/drew/.drewgent"
all_md = []
for root, dirs, files in os.walk(vault_root):
    dirs[:] = [d for d in dirs if d not in EXCLUDED]
    for f in files:
        if f.endswith('.md'):
            all_md.append(os.path.join(root, f))

# Build basename resolution map (Obsidian's actual behavior)
basename_map = {}
for fp in all_md:
    bn = os.path.basename(fp).replace('.md', '')
    basename_map.setdefault(bn, []).append(fp)

def resolves(target):
    t = target if target.endswith('.md') else target + '.md'
    if os.path.exists(os.path.join(vault_root, t)):
        return True
    bn = target.replace('.md', '')
    if bn in basename_map:
        return True  # Obsidian resolves by basename
    if '.neuron' in target:
        for r, d, f in os.walk(vault_root):
            if os.path.basename(target) in f:
                return True
    return False

# True audit with code block filtering
for fp in all_md:
    with open(fp, errors='replace') as f:
        content = f.read()
    # Strip code blocks to avoid false positives
    clean = re.sub(r'```.*?```', '', content, flags=re.DOTALL)
    clean = re.sub(r'`[^`]+`', '', clean)
    
    found = re.findall(r'\[\[([^\]]+?)(?:\|[^\]]+)?\]\]', clean)
    for link in found:
        target = link.strip()
        if target.endswith(('.png', '.jpg', '.svg', '.gif', '.py')):
            continue
        if not resolves(target):
            TRULY_BROKEN.append((target, fp))
```

### Common Fix Patterns

| Detected broken link | Cause | Fix |
|----------------------|-------|-----|
| `[[P0-brainstem/.../禁/禁xxx]]` | Missing `.neuron` extension | Add `.neuron` → `[[P0-brainstem/.../禁/禁xxx.neuron]]` |
| `[[skills/content-pipeline]]` | SKILL.md nested under directory | Change to `[[skills/content-pipeline/SKILL]]` |
| `[[skills/seo-article-harvester]]` | Same pattern | Change to `[[skills/seo-article-harvester/SKILL]]` |

## Orphan & Passive File Detection

**Orphans**: 0 inbound + 0 outbound links. Usually archive, template, or write-only telemetry.

**Passive files**: inbound > 0 but outbound = 0. These receive links but never reciprocate — they're dead-ends in graph traversal.

### Passive File Fix (bulk)

DESCRIPTION.md files in `skills/` categories are the most common passive files:
- They're linked from SKILL-INDEX (inbound > 0)
- They have no `links:` section (outbound = 0)

Fix: add outbound links to SKILL-INDEX and rules:
```python
fixed = 0
for fp in glob.glob("skills/*/DESCRIPTION.md"):
    content = read(fp)
    if 'links:' in content[:500]:
        continue
    # Insert links before closing ---
    content = content.replace(
        '\n---\n\n',
        '\nlinks:\n  - "[[P3-sensors/skills/SKILL-INDEX]]"\n  - "[[P0-brainstem/brain/rules]]"\n---\n\n'
    )
    write(fp, content)
```

### Detection Script

```python
# Build inbound/outbound maps
for fp in all_md:
    with open(fp) as f:
        content = f.read()
    clean = re.sub(r'```.*?```', '', content, flags=re.DOTALL)
    links = re.findall(r'\[\[([^\]]+?)(?:\|[^\]]+)?\]\]', clean)
    for link in links:
        target = link.strip().replace('.md', '')
        if resolves(target):
            inbound[target].add(slug)
            outbound[slug].add(target)

# Find passive files
passive = [(s, len(inbound[s])) for s in all_slugs 
           if len(outbound.get(s, set())) == 0 and len(inbound.get(s, set())) > 0]
```

## Bulk Cross-Linking Technique (for SEO articles)

When facing 2,500+ articles that need cross-links, use a 3-phase approach:

### Phase 1: Convert Article → Hub (plain text → wikilink)

Many articles reference hub pages as plain text in their `links:` section:
```yaml
links:
- SEO_ai_llm_search_Hub        # Plain text — NOT a graph edge
- "[[P2-hippocampus/.../index-by-topic]]"  # Proper wikilink
```

Fix: replace `SEO_X_Hub` with `[[SEO_X_Hub]]` in the links list. Creates bidirectional edges since hubs already link to articles.

### Phase 2: Hub → Hub Related Links

Hub pages (one per topic cluster) link to articles but not to each other. Add related-topic links:
```python
hub_relations = {
    'SEO_ai_llm_search_Hub': ['SEO_general_Hub', 'SEO_algorithm_updates_Hub'],
    'SEO_technical_seo_Hub': ['SEO_onpage_seo_Hub', 'SEO_analytics_tools_Hub'],
    # ... one pair per hub
}
```

### Phase 3: Article ↔ Article within Cluster

For articles sharing the same `cluster` field, add cross-links:
```python
for cluster, articles in cluster_groups.items():
    all_fnames = [fn for _, fn in articles]
    for fpath, fname, content in articles:
        candidates = [fn for fn in all_fnames if fn != fname and fn not in existing_links]
        targets = random.sample(candidates, min(3, len(candidates)))
        # Add [[target]] to links section
```

### Source-Domain Clustering (when no cluster field)

For articles that only have source-domain tags (e.g., `tags: [seo, ahrefs.com]`):
```python
source_groups = defaultdict(list)
for fpath, content in articles:
    tags = extract_tags(content)
    source = [t for t in tags if '.' in t and t not in ('resource', 'seo')]
    if source:
        source_groups[source[0]].append((fpath, fname))
# Link articles sharing the same source domain
```

## Inline Wikilink Injection (See Also Sections)

Frontmatter `links:` creates graph edges, but **body wikilinks carry more weight** in Obsidian Graph View. For articles with keyword/topic metadata, inject a `## See also` section at the end:

```python
# For SEO articles with keyword: field
keyword_to_topic = {
    '온페이지 SEO': 'SEO_onpage_seo_Hub',
    '콘텐츠 전략': 'SEO_content_strategy_Hub',
    # ... map keywords to hub pages
}

for fp in article_files:
    kw_match = re.search(r'^keyword:\s*(.+)', content, re.MULTILINE)
    if not kw_match:
        continue
    topics = {keyword_to_topic[k.strip()] for k in kw_match.group(1).split(',') 
              if k.strip() in keyword_to_topic}
    if not topics:
        continue
    # Add at end:
    topic_links = '\n'.join([f'- [[{t}]]' for t in sorted(topics)])
    content += f'\n\n## See also\n{topic_links}\n'
```

This is safe for automation: it never modifies frontmatter, never breaks existing formatting, and only adds content at the very end of the file.

### Mesh Linking Strategy

A healthy knowledge graph has cycles (A↔B↔C) not just stars (hub→leaves). Add links in three directions:

```
UPWARD:   child → parent concept     (P2-memory → P5-ego/SELF_MODEL)
DOWNWARD: parent → child detail      (rules.md → specific neuron file)
SIDEWAYS: peer → peer related         (P2-SCHEMA ↔ P4-INTEGRATION_PROTOCOL)
```

For each core file, check:
- ✅ **Upward**: Does it link to SELF_MODEL, rules, or its parent layer?
- ❌ **Downward**: Does the parent link back to its children?
- ❌ **Sideways**: Does it link to related files in other P-layers?

### Bidirectional Completeness

If `A → B` exists, `B → A` should too, unless `B` is a pure index/hub page (SKILL-INDEX, index-by-topic). Reasonable exception: SEO article hub pages don't need backlinks from every article.

### Cross-Linking Technique: Systematic Audit

When adding cross-links to a cluster (P-layer, skill category, etc.), use this 4-step process:

```bash
# Step 1: Identify the cluster
# Scan all files in a category/directory for current link counts
for f in ~/.drewgent/path/to/cluster/*/SKILL.md; do
  name=$(basename "$(dirname "$f")")
  count=$(sed -n '/^links:/,/^---/p' "$f" | grep -c '\[\[\|')
  echo "$count $name"
done | sort -rn

# Step 2: Identify natural relationships
# Check for `related_skills` in metadata that are NOT yet in `links:`
grep -A2 'related_skills:' ~/.drewgent/path/to/cluster/*/SKILL.md

# Step 3: For each skill with related_skills in metadata,
# add those as actual `links:` wikilinks (metadata doesn't create graph edges)
# Then add bidirectional links between sibling skills

# Step 4: Verify all new wikilinks resolve
for link in "list/of/newly/added/links"; do
  find ~/.drewgent -path "*/${link}.md" | grep -q . && echo "OK" || echo "BROKEN"
done
```

### Converting `related_skills` (Metadata) to `links` (Graph Edges)

Many SKILL.md files have `related_skills` in their YAML metadata (`metadata.hermes.related_skills`) but no actual `links:` in frontmatter. Metadata is machine-readable but does NOT create Obsidian graph edges.

**Pattern found (2026-06-14)**: ~15 skills across `software-development/` and `brain/` had `related_skills` arrays that were never converted to wikilinks. Example:
- `python-debugpy` had `related_skills: [systematic-debugging, node-inspect-debugger]` in metadata but no `links:` section
- `simplify-code` had `related_skills: [requesting-code-review, test-driven-development, plan]` in metadata

**Fix**: Add a `links:` section to the YAML frontmatter with the same relationships as actual wikilinks.

## Pitfalls

### Generic `title: Skill` Renders as Anonymous Node

SKILL.md files with `title: Skill` (or no title) appear in Obsidian Graph View as undifferentiated **"SKILL"** nodes. With 21+ such files, the graph is full of identical labels — impossible to navigate.

**Fix**: Each SKILL.md should have a unique `title:` derived from its directory name:

```yaml
# Before (graph shows "SKILL")
title: Skill

# After (graph shows "Kanban Worker")
title: Kanban Worker
```

Script to find offenders:
```bash
grep -rl '^title: Skill$' ~/.drewgent/skills --include='SKILL.md' \
  --exclude-dir=optional-skills --exclude-dir=plugins
```

### Short-Name Wikilinks in Hub Pages

Hub pages (e.g., `SEO_ai_llm_search_Hub.md`) use short-name wikilinks like `[[10 ChatGPT SEO Tools...]]`. These resolve in Obsidian by basename scan, but they are **fragile** — a filename collision in any subdirectory breaks resolution. Keep hub pages in a predictable location and verify with `obsidian backlinks`.

### Optional-Skills Creates Phantom Isolated Nodes

`optional-skills/` contains 45+ skills with 0 links. They're completely disconnected from the graph. If they're not actively used, **exclude from Obsidian** (`userIgnoreFilters: ["optional-skills"]`) rather than adding maintenance scaffolding.

### Template for Cross-Link Audit

When auditing a P-layer file's links:

```markdown
| Direction | Existing | Missing | Action |
|-----------|----------|---------|--------|
| Upward    | rules.md | - | OK |
| Downward  | - | specific neurons | Add |
| Sideways  | SELF_MODEL | INTEGRATION_PROTOCOL | Add |
```

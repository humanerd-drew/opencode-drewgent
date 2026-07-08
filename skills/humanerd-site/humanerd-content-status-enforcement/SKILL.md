---
title: humanerd-content-status-enforcement
name: humanerd-content-status-enforcement
description: When creating or editing a vault .md file in any of the 3 pillars (insights, portfolio, blog) or services/about, ensure frontmatter has a valid `status` field. Without it, DraftFilter (default-draft strict) excludes the file from humanerd.kr permanently (404). Use this skill BEFORE write_file or patch on these paths.
type: document
space: growth
tags: [growth, quartz, humanerd-site, frontmatter, status, content-pipeline, enforcement]
created: 2026-06-02
updated: 2026-06-02
links:
  - "[[skills/humanerd-site]]"
  - "[[P4-cortex/portfolio/quartz-publishing]]"
  - "[[P4-cortex/growth/humanerd-site-url-mapping]]"
  - "[[P3-sensors/skills/obsidian-markdown]]"
  - "[[P0-brainstem/brain/rules]]"---

# humanerd.kr — Content Status Field Enforcement

**When Loragent creates or edits content destined for humanerd.kr, the `status` frontmatter field determines live visibility.** A missing or unrecognized status value → permanent 404 (default-draft, strict).

## When to Apply

This skill applies to ALL of the following operations:

| Operation | Vault path | Frontmatter required |
|---|---|---|
| New article (blog) | `memories/insights/{YYYY-MM-DD}-{slug}.md` | yes |
| New article (insights) | `P4-cortex/knowledge/{slug}.md` | yes |
| New article (portfolio) | `P4-cortex/portfolio/{slug}.md` | yes |
| New page (services) | `humanerd-site/content/services/{slug}.md` | yes |
| Edit existing (any of above) | (same paths) | preserve or transition status |
| New monthly log | `memories/insights/{YYYY-MM}.md` | yes |
| New Insights index | `memories/insights/Insights.md` | yes |
| Site home | `humanerd-site/content/index.md` | yes |
| About | `humanerd-site/content/about.md` | yes |

**Exempt (frontmatter optional, but recommended)**:
- `humanerd-site/content/landingpage/**` (legacy, ignorePatterns)
- `humanerd-site/content/skills/**` (skills are also symlinked; Obsidian-only, but if exposed, needs status)
- `humanerd-site/content/scripts/**`, `persona/**`, `plans/**` (legacy, mostly symlinks — if exposed, needs status)
- Anything inside `growth/**` or `lab/**` (ignorePatterns — never exposed)

## Frontmatter Status Convention

```yaml
---
title: "..."
type: document
space: claim
tags: [...]
created: YYYY-MM-DD
updated: YYYY-MM-DD
status: draft   # ← MUST EXIST
---
```

### Valid status values

| Value | Meaning | Quartz plugin | humanerd.kr |
|---|---|---|---|
| `published` | Reviewed, ready, live | INCLUDE | ✅ 200 |
| `polished` | Auto-polished by LLM, awaiting human review | INCLUDE | ✅ 200 |
| `draft` | Being written, not yet reviewed | EXCLUDE | ❌ 404 |
| `in_review` | Re-reviewing after feedback | EXCLUDE | ❌ 404 |
| `archived` | Removed from public | EXCLUDE | ❌ 404 |
| `publish` (단수) | **WRONG — naming convention violation** | EXCLUDE (default) | ❌ 404 |
| (no field) | **Strict default-draft** | EXCLUDE | ❌ 404 |
| `domain: draft` | Domain-level draft marker | EXCLUDE | ❌ 404 |

## Decision Tree — When Creating New Content

```
[User asks for new blog/insights/portfolio entry]
    │
    ├─ User explicitly says "publish" / "발행해줘" / "라이브" ?
    │   ├─ YES → status: published
    │   └─ NO → status: draft (default — human reviews before going live)
    │
    └─ Polished by LLM (next-phase: LLM 자동 윤문)
        ├─ YES → status: polished (after LLM polish, awaiting human)
        └─ NO → status: draft
```

**Default rule**: 새 article은 무조건 `status: draft`. user가 명시적으로 publish를 요청하지 않는 한.

## Pre-flight Check (Before write_file / patch)

Before writing a vault .md file in any of the affected paths, run this check:

```python
import re
from pathlib import Path

def check_status(path: Path) -> str:
    text = path.read_text() if path.exists() else ""
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return "MISSING_FRONTMATTER"
    fm = m.group(1)
    m_status = re.search(r"^status:\s*(\S+)", fm, re.MULTILINE)
    if not m_status:
        return "MISSING_STATUS"
    val = m_status.group(1).strip('"').strip("'")
    if val.lower() in ("publish", "polishes", "polish"):
        return f"WRONG_STATUS ({val}) — must be 'published' or 'polished'"
    if val.lower() in ("published", "polished", "draft", "in_review", "archived"):
        return f"OK ({val})"
    return f"UNKNOWN_STATUS ({val})"
```

If the check returns `MISSING_*` or `WRONG_STATUS` or `UNKNOWN_STATUS`, **fix the frontmatter before writing**.

## Recovery Procedure — For Existing Files

If a file is missing `status` (or has wrong value) and is supposed to be live:

1. Read the file
2. Find the frontmatter block
3. If frontmatter exists, add `status: published` after the `title:` line (or as the first key)
4. If no frontmatter, prepend:
   ```yaml
   ---
   status: published
   ---
   ```
5. Verify with `npx quartz build` that the file is no longer in the EXCLUDE list

**Example recovery** (used 2026-06-02 for 19 files):

```python
# scripts/enforce_status.py
from pathlib import Path
import re

def add_status_published(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return "MISSING_FM"
    fm = m.group(1)
    if re.search(r"^status:", fm, re.MULTILINE):
        return "SKIP"  # already set
    lines = fm.split("\n")
    new_lines = []
    inserted = False
    for line in lines:
        new_lines.append(line)
        if not inserted and line.startswith("title:"):
            new_lines.append("status: published")
            inserted = True
    if not inserted:
        new_lines.insert(0, "status: published")
    new_fm = "\n".join(new_lines)
    new_text = text[:m.start(1)] + new_fm + text[m.end(1):]
    path.write_text(new_text, encoding="utf-8")
    return "OK"
```

## Verification

```bash
# After editing/creating content, verify status field:
cd ~/.loragent/humanerd-site
npx quartz build 2>&1 | grep "DraftFilter"

# Expected:
# [DraftFilter] EXCLUDE ... (only for files that SHOULD be excluded)
# (no EXCLUDE for the file you just created/edited)
```

If the file you intended to publish shows EXCLUDE, fix the `status` field.

## Edge Cases

### Edge case 1: cron auto-generated articles
- `seo-article-harvester` cron writes to `memories/insights/`
- These should default to `status: draft` so they require human review
- **Do NOT** auto-set `status: published` in cron scripts — that defeats the review gate

### Edge case 2: aliases
- If an article is moved/renamed, add `aliases: ['/old/url']` to the new file
- The new file must have a valid `status` field too
- Old file's status doesn't matter (file no longer linked, won't be picked up by Quartz)

### Edge case 3: cross-pillar moves
- Moving an article from `memories/insights/` to `P4-cortex/knowledge/` requires:
  1. Update frontmatter (status, title, tags)
  2. Add aliases for old URL (so /blog/YYYY/MM-slug → /insights/slug redirect works)
  3. Verify build

### Edge case 4: frontmatter reordering
- Some Quartz features depend on field order
- Recommended order: title → type → space → tags → created → updated → status → links → aliases
- `status: published` after `title:` is the safe spot

## When NOT to Apply This Skill

- **Internal process docs** (`growth/**`, `lab/**`) — ignorePatterns, never exposed
- **Brain rules** (`.neuron` files) — different frontmatter convention
- **P-layer memory** (`P2-hippocampus/memories/**`, `P5-ego/**`, etc.) — internal, not exposed
- **Skills** (`~/.loragent/skills/**`) — internal skill format, not exposed
- **Quartz plugin source** (`humanerd-site/quartz/**`) — TypeScript, no frontmatter
- **Build output** (`humanerd-site/public/**`) — auto-generated, don't edit

## Self-Check Questions (for agent)

When creating a new vault .md file destined for humanerd.kr:

1. Which pillar does this belong to? (insights / portfolio / blog / services / about)
2. Did the user explicitly say "publish" / "발행" / "라이브"?
3. If yes: `status: published`
4. If no: `status: draft` (default — human reviews)
5. Did I add wikilinks to existing vault nodes?
6. Did I add aliases if this is a renamed/moved article?

## Related

- [[skills/humanerd-site]] — main site management skill
- [[P4-cortex/portfolio/quartz-publishing]] — pipeline overview
- [[P4-cortex/growth/humanerd-site-url-mapping]] — 3-pillar URL mapping
- [[P3-sensors/skills/obsidian-markdown]] — OFM writing skill

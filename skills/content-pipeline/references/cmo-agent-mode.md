# CMO Agent Mode — Implementation Guide

## Overview

Mode B of the content pipeline: a single autonomous agent profile (`content-manager`) that observes Drew's recent work activity and produces multi-format content without being told what to write.

## Key Difference from Mode A (Aggregator)

| Aspect | Mode A | Mode B |
|--------|--------|--------|
| Source | External trends, SEO, RSS | Drew's own work (git, sessions, kanban) |
| Trigger | Kanban task dispatch | Cron + `delegate_task` |
| Cadence | Every 3 hours | Daily at 12:00 KST |
| Output | Blog draft | Blog + SVG cover + X thread + Excalidraw PNG |
| Human in loop | Review before publish | Review before publish |

## Agent Profile

File: `~/.drewgent/agents/content-manager.md`
Model: `deepseek-v4-pro` (opencode-go)
Toolsets: `terminal, file, search, session_search, kanban, web`

### Profile Instructions (summary)

The profile includes:
- Knowledge base loading (brand guide, glossary, content inventory, narrative arc)
- Context gathering (session search, git log, kanban completions)
- Story mining with editorial scoring (reader value, drew-angle, narrative fit)
- Multi-format drafting (blog + SVG cover + X thread + Excalidraw + meme)
- Narrative arc tracking and content inventory updates
- Quality gates (SILENT if nothing new, one story per cycle)

Full content: see `~/.drewgent/agents/content-manager.md`.

## Cron Job

| Property | Value |
|----------|-------|
| Job ID | `d0d0b98c845b` |
| Name | `content-manager-periodic` |
| Schedule | `0 12 * * *` (daily at 12:00 KST) |
| Model | `deepseek-v4-pro` (opencode-go) |
| Delivery | Discord channel `1492883985473208522` (#content) |
| Workdir | `/Users/drew/.drewgent` |
| Toolsets | `terminal, file, search, session_search, kanban, web` |

The cron prompt is self-contained with the full workflow. It references the agent profile file for full detail.

## Knowledge Base Files (read every cycle)

| File | Path | Purpose |
|------|------|---------|
| Brand guide | `P4-cortex/content/brand-guide.md` | Voice, audience, positioning |
| Glossary | `P4-cortex/content/glossary.md` | Project terms (Drewgent, M-LOG, etc.) |
| Content inventory | `P4-cortex/content/content-inventory.md` | Published/drafted dedup |
| Narrative arc | `P4-cortex/content/narrative_arc.md` | Episode tracking, season continuity |

## Visual Assets Per Post

Created alongside every blog post:

| Asset | Path | Tool |
|-------|------|------|
| SVG cover | `memories/insights/YYYY-MM-DD-slug-cover.svg` | Model writes XML |
| Mermaid diagrams | Inline in `.md` | ` ```mermaid` |
| Excalidraw JSON | `memories/insights/YYYY-MM-DD-slug.excalidraw.json` | Model writes JSON |
| Excalidraw PNG | `memories/insights/YYYY-MM-DD-slug.png` | `excalidraw-to-png.js` (Puppeteer) |
| Meme SVG | `memories/insights/YYYY-MM-DD-slug-meme.svg` | Model writes XML (optional) |
| X thread | `memories/insights/YYYY-MM-DD-slug-thread.txt` | Model writes text |

## Narrative Tracking

The `narrative_arc.md` file maintains a "season/episode" structure:

```yaml
current_season: "Season name"
episodes:
  - date: 2026-06-14
    title: "Episode title"
    pillar: SYSTEMS
    platform: blog
threads:
  - name: "Thread name"
    status: active
    published: [...]
```

Each cycle, the agent:
1. Reads the current arc
2. Places the new story within it (new episode or continuation)
3. Writes the update

## First Run Test

Tested via `delegate_task(agent_profile="content-manager", goal="...")` (since cron doesn't trigger immediately). First run produced:
- Blog post: 9.7KB with 4 Mermaid diagrams
- SVG cover: 5.8KB illustration
- Excalidraw JSON + PNG: architecture diagram
- X thread: 15 tweets
- narrative_arc.md + content-inventory.md updates

## Pitfalls

- **Paths must be absolute.** Use `/Users/drew/.drewgent/P2-hippocampus/memories/insights/`, not relative paths.
- **Do NOT reference existing drafts** from before the current session. Explicitly exclude them.
- **SILENT is correct** — if nothing worth publishing, report "no new material" and stop.
- **SVG validation**: ensure XML is well-formed. Run `python3 -c "import xml.etree.ElementTree as ET; ET.parse('file.svg')"` if unsure.
- **Excalidraw JSON validation**: no trailing commas in the JSON. The `write_file` lint catches this, but inline generation in tool output may produce invalid JSON. Always validate before the export step.

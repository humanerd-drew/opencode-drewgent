---
name: content-management
description: >  
  CMO-style autonomous content agent. Observes user's work activity (sessions, git, kanban),
  curates narrative-worthy material, produces multi-format drafts (blog + X thread),
  maintains narrative arc continuity, and generates visual assets (SVG cover, Mermaid, Excalidraw PNG).
trigger: "2026-06-14 — Designed and built the content-manager agent after user rejected multi-stage pipeline in favor of a single agent profile + cron"
provenance:
  session: "2026-06-14 content-manager-cmo-agent"
  decision: "Agent profile + cron trigger + narrative_arc.md tracking file (not a multi-stage pipeline). SVG over paid image API (user: '비용 발생안시키고 싶어'). Excalidraw→PNG via Puppeteer for architecture diagrams."
category: autonomous-ai-agents
tags: [agent, content, cmo, publishing, narrative, svg, excalidraw, mermaid]
created: 2026-06-14
updated: 2026-06-14
links:
  - "[[agent-profiles]]"
  - "[[skills/content-pipeline]]"
  - "[[P4-cortex/content/narrative_arc.md]]"
---

# Content Management — CMO Agent

Autonomous content manager that observes what the user builds and turns it into publishable content with rich visuals. Uses a single agent profile + cron trigger, NOT a multi-stage pipeline.

## Architecture

```
Agent profile: content-manager (deepseek-v4-pro)
Cron: daily at 12:00 KST
Knowledge base: brand-guide + glossary + narrative_arc + content-inventory
All files under: P4-cortex/content/

Per-run output:
  memories/insights/
    ├── YYYY-MM-DD-slug.md                ← Blog post (with Mermaid diagrams inline)
    ├── YYYY-MM-DD-slug-cover.svg          ← SVG cover illustration (1200x630, dark theme)
    ├── YYYY-MM-DD-slug.excalidraw.json    ← Excalidraw architecture diagram
    ├── YYYY-MM-DD-slug.png                ← Excalidraw exported to PNG
    ├── YYYY-MM-DD-slug-thread.txt         ← X thread (10-15 tweets)
    └── YYYY-MM-DD-slug.excalidraw         ← Excalidraw binary (from CLI)
  
  P4-cortex/content/
    ├── narrative_arc.md                   ← Updated with new episode
    └── content-inventory.md               ← Updated with new entry
```

## Agent Profile

Defined at `~/.drewgent/agents/content-manager.md`. Full instructions include:

1. **Load Knowledge Base** — Read brand-guide, glossary, content-inventory, narrative_arc
2. **Gather Context** — session_search, git log, kanban completions
3. **Mine for Stories** — Score 1-10 (reader value, drew-angle, narrative fit). ≥7 proceed
4. **Draft Content** — Blog post with embedded SVG cover + Mermaid + Excalidraw PNG
5. **Update Tracking Files** — narrative_arc.md + content-inventory.md

## Web Research

Content-manager has `web` toolset enabled. Before drafting, optionally search for:
- Related projects or approaches (what others are doing)
- Technical background to strengthen the narrative
- Memes or cultural references that fit the story
- Related blog posts / discussions

Search results strengthen the draft's credibility and relevance.

## Visual Asset Pipeline

Three types of images produced per post, all $0 cost, plus optional meme SVGs:

### 1. SVG Cover Illustration
Model writes SVG XML directly (1200×630). Supports paths, gradients, filters, transforms.
- Dark theme: `#0d0d1a` → `#1a1a30` gradient
- Accent: `#7b5f3d` (amber), `#4a90d9` (blue), `#50c878` (teal)
- Embed: `![[YYYY-MM-DD-slug-cover.svg|800]]`
- References: `references/svg-cover-design.md`, `references/svg-meme-templates.md`

### 1b. Meme SVG (optional — cultural reference)

If the story has a natural meme angle, create a companion SVG. Recognizable meme formats:

| Template | Use Case |
|----------|----------|
| **Drake Reject/Approve** | Before/after comparison, old vs new |
| **"This is fine" (burning)** | Recognizable pain, debugging stories |
| **Galaxy brain** | Escalating understanding, growing insight |
| **Distracted boyfriend** | Three-way comparison, options trade-off |

See `references/svg-meme-templates.md` for SVG code templates.

### 2. Mermaid Diagrams
Inline ````mermaid` code blocks. Quartz renders natively as SVG.
Types: graph TD/LR, sequenceDiagram, flowchart

### 3. Excalidraw → PNG
For complex architecture/flow diagrams. Two-step process:
1. Create `.excalidraw.json` file with elements array (rectangles, text, arrows, etc.)
2. Convert to PNG via headless Chrome: `scripts/excalidraw-to-png.js`

```
NODE_PATH=/Users/drew/.drewgent/scripts/node_modules \
  node /Users/drew/.drewgent/scripts/excalidraw-to-png.js \
    input.excalidraw.json \
    output.png
```

## Knowledge Base Files

| File | Path | Purpose |
|------|------|---------|
| **brand-guide** | `P4-cortex/content/brand-guide.md` | Voice, audience, platform strategy |
| **glossary** | `P4-cortex/content/glossary.md` | Project terms (Drewgent, M-LOG, etc.) |
| **narrative_arc** | `P4-cortex/content/narrative_arc.md` | Published content continuity tracking |
| **content-inventory** | `P4-cortex/content/content-inventory.md` | All drafts/published with dedup topics |

## Content Pillars (Editorial Judgment)

1. **BUILD LOG** — Drewgent infra, architecture, troubleshooting
2. **AI & TOOLS** — Agent systems, tool reviews, pattern discovery
3. **SYSTEMS** — Design philosophy, decision frameworks, taste
4. **CREATIVE** — M-LOG, side projects, experiments

## Pitfalls

- **No existing insights reference**: The agent must NOT reference existing files in `memories/insights/` from before its first run. Those are from a previous system.
- **SILENT is correct**: If nothing worth publishing, produce nothing. Don't force output.
- **Quality over quantity**: One great post per run beats five mediocre ones. The cron runs daily, backlog clears over time.
- **Never ask Drew what to write**: The CMO decides. Present the draft.
- **SVG over paid APIs**: User explicitly rejected FAL.ai and other paid image generation. SVG is the primary cover format. Excalidraw PNG for architecture. No DALL-E, Midjourney, FLUX, etc.
- **Try first, retreat when proven**: User explicitly corrected: "변화를 두려워 하지마. 상상만으로 결정하지마. 상정한 방향을 현재 환경에 최대한 적용해보고, 그래도 비효율이면 그때 물러서." Apply the best approach to the current environment first; only retreat when the data says it's inefficient — not from imagined objections.

## WordPress Publishing Pipeline

Content-manager can publish to the humanerd.kr WordPress site via a custom STDIO MCP server.

**MCP server**: `~/scripts/wordpress-mcp-server.js` — wraps wp-cli commands as JSON-RPC 2.0 tools:
- `create_post` — title, content, category, tags, status, featured_image
- `upload_media` — file upload by path
- `list_posts` / `get_post` — read content
- `create_category` — manage taxonomy
- `set_site_option` / `set_theme_mod` — site config

**Registered in Hermes config**: `mcp_servers.wordpress` at `~/.hermes/config.yaml`

**WordPress setup**: Docker Compose at `~/.drewgent/wordpress/`, data on NAS `/Volumes/humanerd/docker/wordpress/`. Admin at `http://localhost:8080/wp-admin`.

**Theme**: Blocksy (free). Customized with:
- Color palette (bronze accent #8b7355)
- Google Fonts: Noto Sans KR + Noto Serif KR + JetBrains Mono
- Custom CSS for typography and card layouts
- Logo uploaded and set
- Pages: Home / Blog / About — categories match content pillars

Reference: `references/wordpress-mcp-publishing.md`

## Relationship to content-pipeline Skill

This skill supersedes the older `content-pipeline` skill which was based on trend-harvester/SEO sources with a 3-hour cycle. The new approach:
- **Source**: User's own work (sessions, git, kanban) vs external trends/SEO
- **Cycle**: Daily, material-driven vs fixed 3-hour
- **Agent**: Single autonomous profile vs multi-stage kanban pipeline
- **Images**: SVG + Excalidraw PNG + Mermaid vs text-only drafts

The two overlap. Consolidation deferred to background curator.

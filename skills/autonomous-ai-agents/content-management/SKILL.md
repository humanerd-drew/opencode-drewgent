---
name: content-management
description: >  
  CMO-style autonomous content agent. Observes user's work activity (sessions, git, kanban),
  curates narrative-worthy material, produces multi-format drafts (blog + X thread),
  maintains narrative arc continuity, and generates visual assets (SVG cover, Mermaid, Excalidraw PNG).
  session: "2026-06-14 content-manager-cmo-agent"
  decision: "Agent profile + cron trigger + narrative_arc.md tracking file (not a multi-stage pipeline). SVG over paid image API (user: '비용 발생안시키고 싶어'). Excalidraw→PNG via Puppeteer for architecture diagrams."
category: autonomous-ai-agents
tags: [agent, content, cmo, publishing, narrative, svg, excalidraw, mermaid]
created: 2026-06-14
updated: 2026-06-14
links:
  - "[[agent-profiles]]"
  - "[[skills/content-pipeline]]"
  - "[[@memory/content/narrative_arc.md]]"
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

## Data Sources

In addition to direct work activity, content-manager monitors two automated collection pipelines:

### 1. Trend Harvester
- **Location**: `@memory/growth/trend-harvester/{collected,applied,evaluated}/`
- **Content**: GitHub trending repos scored via 5-axis philosophy filter (6h cycle)
- **Use**: Pick applied/evaluated items with high scores → write "AI Tool of the Week" posts or deep-dives into tools that got integrated into {{AGENT_NAME}}

### 2. SEO Article Harvester
- **Location**: `P2-hippocampus/knowledge/seo-articles/YYYY/`
- **Content**: 1,642+ SEO/marketing articles from 28 RSS feeds (6h cycle)
- **Use**: Surface notable Google updates, agentic web trends, or shifts in AI/discovery landscape → write analysis/opinion posts linking to YOUR_DOMAIN's own ARD integration

## Agent Profile

Defined at `~/.{{AGENT_NAME_LOWER}}/agents/content-manager.md`. Full instructions include:

1. **Load Knowledge Base** — Read brand-guide, glossary, content-inventory, narrative_arc
2. **Gather Context** — session_search, git log, kanban completions, harvester outputs
3. **Mine for Stories** — Score 1-10 (reader value, drew-angle, narrative fit). ≥7 proceed
4. **Draft Content** — Blog post with embedded SVG cover + Mermaid + Excalidraw PNG
5. **Publish Draft** — `create_post` via WordPress MCP (status=draft)
6. **Update Tracking Files** — narrative_arc.md + content-inventory.md

## Web Research

Content-manager has `web` toolset enabled. Before drafting, optionally search for:
- Related projects or approaches (what others are doing)
- Technical background to strengthen the narrative
- Memes or cultural references that fit the story
- Related blog posts / discussions

Search results strengthen the draft's credibility and relevance.

## Visual Asset Pipeline

Three types of images produced per post, all $0 cost, plus optional meme SVGs:

### 1. Cover Image (CF Workers AI, $0, 1024×512)
AI-generated conceptual illustration via FLUX on Cloudflare Workers AI. Four scene templates:
- **garden** — 태양 정원 (Creative)
- **city** — 덩굴 도시 (Build Log)
- **shepherd** — 사막의 양치기 (AI & Tools)
- **connector** — 연결자 (Systems)

All feature: anthropomorphic blue sheep, lion silhouette, geometric sun, cracked earth.
See `scripts/cover_gen.py` for prompts. Featured image via MCP `create_post(featured_image=...)`.
Fallback: SVG templates at `references/svg-templates/`.

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
NODE_PATH=~/.{{AGENT_NAME_LOWER}}/scripts/node_modules \
  node ~/.{{AGENT_NAME_LOWER}}/scripts/excalidraw-to-png.js \
    input.excalidraw.json \
    output.png
```

## Knowledge Base Files

| File | Path | Purpose |
|------|------|---------|
| **brand-guide** | `P4-cortex/content/brand-guide.md` | Voice, audience, platform strategy |
| **glossary** | `P4-cortex/content/glossary.md` | Project terms ({{AGENT_NAME}}, M-LOG, etc.) |
| **narrative_arc** | `P4-cortex/content/narrative_arc.md` | Published content continuity tracking |
| **content-inventory** | `P4-cortex/content/content-inventory.md` | All drafts/published with dedup topics |
| **writing-style-guide** | `P1-limbic/persona/writing-style-guide.md` | Tone, forbidden expressions, Korean voice |
| **form-template** | `https://dev.to/siiddhantt/building-reefwatch-a-coral-powered-production-triage-agent-23hf` | Canonical blog post 구조 — 반드시 이 형태를 따라라 |

## Post-Publish Enrichment — Links & References

After drafting, enrich the post with links before saving as draft:

1. **내부 링크**: Scan `narrative_arc.md` and `content-inventory.md` for existing posts on related topics. Add internal links where natural (e.g., "v0.8 simplification post ([link])에서 다뤘듯이...")
2. **외부 참조**: Check SEO harvester articles for relevant sources (e.g., Google announcements, agentic web trends). Link to original sources where cited.
3. **상호 참조 클러스터**: Posts on the same pillar (BUILD LOG, AI & TOOLS, SYSTEMS, CREATIVE) should interlink. Episode 1→2→3 of a season should form a chain.
4. **용어 링크**: First mention of {{AGENT_NAME}}/M-LOG/ARD 등 should link to the glossary or relevant explanation if it's the first post in a series.

Format example:
```html
<!-- wp:paragraph -->
<p><strong>덜어내는 작업</strong>은 <a href="/?p=XX">v0.8 architecture compression 포스트</a>에서 자세히 다뤘다. 이번 글은 그 연장선에 있는 <strong>연결하기</strong>에 대한 이야기다.</p>
<!-- /wp:paragraph -->
```

## Voice & Form (Critical — Read Before Drafting)

### Form Template (ReefWatch)

이 구조를 반드시 따라라. 모든 포스트는 이 템플릿을 프레임으로 사용한다.

```
1. Hook-first opening — 짧고 강한 문장. 문제를 직접 던진다.
   "Production incidents almost never break in one place."
   "A normal chatbot... But that is not triage. That is a polished to-do list."

2. Problem → Decision → Build Path
   "I wanted something more useful: an agent that could..."
   "The design constraint from the start: no evidence, no answer."

3. "What This Guide Builds" — bullet list of deliverables
4. Why <technology> section — "Why [X] belongs at the center" — 결정 이유
5. Build path (slices) — numbered slices showing progressive build:
   "Slice 1: Prove [X] Can Be The Data Plane"
   "Slice 2: Keep [X] Warm"
   Structure: What I Built → Why It Mattered
6. Architecture diagrams (Mermaid 또는 SVG)
7. Key design decisions with failure modes table
8. Personal closing ("Thanks for reading...")
```

### Voice Rules

1. **반말 + 1인칭** ("저", "나"). 독자에게 "당신"으로 직접 말한다.
2. **금지**: "이 글은", 추상 주어, 존댓말, AI투 카피 ("~에 대해 알아보겠습니다")
3. **Bold** 로 핵심 문장 강조
4. **짧은 문장**. 문제 → 바로 해결.
5. **개인적인 깨달음을 중심으로**: "That was useful because it proved..."
6. **거대한 시스템 프롬프트를 거부한다**: "I stopped trying to make one heroic system prompt do everything"
7. **숫자를 써라**: "14→6 agents", "43→25 scripts"
8. **딱 하나의 주장만**: 포스트 하나에 하나의 테제

Before drafting, study `https://YOUR_DOMAIN/` `s published posts (ID 12, 13) to absorb Drew's actual voice.

## Content Pillars (Editorial Judgment)

1. **BUILD LOG** — {{AGENT_NAME}} infra, architecture, troubleshooting
2. **AI & TOOLS** — Agent systems, tool reviews, pattern discovery
3. **SYSTEMS** — Design philosophy, decision frameworks, taste
4. **CREATIVE** — M-LOG, side projects, experiments

## Pitfalls

- **Draft must feel like Drew wrote it, not an AI**: If the draft sounds like generic LLM content, rewrite it. If you can't match the voice, produce nothing.
- **SILENT is correct**: If nothing worth publishing, produce nothing. Don't force output.
- **Quality over quantity**: One great post per run beats five mediocre ones. The cron runs daily, backlog clears over time.
- **Never ask Drew what to write**: The CMO decides. Present the draft.
- **CF Workers AI FLUX for covers**: Free tier, $0. `cover_gen.py` generates 1024×512 PNG via 4 scene templates. SVG templates as fallback only.
- **Excalidraw PNG for architecture**: Complex diagrams via headless Chrome export.
- **Try first, retreat when proven**: User explicitly corrected: "변화를 두려워 하지마. 상상만으로 결정하지마. 상정한 방향을 현재 환경에 최대한 적용해보고, 그래도 비효율이면 그때 물러서." Apply the best approach to the current environment first; only retreat when the data says it's inefficient — not from imagined objections.

## WordPress Publishing Pipeline

Content-manager publishes to YOUR_DOMAIN (WordPress + GeneratePress) via the WordPress MCP server.

**MCP server**: Registered in `~/.config/opencode/opencode.jsonc` as `mcp.wordpress`.
Script: `~/scripts/wordpress-mcp-server.js` — wraps `wp-cli` via `docker exec`.
Tools: `create_post`, `upload_media`, `list_posts`, `get_post`, `create_category`, `set_site_option`, `set_theme_mod`.

### Content Format (Critical)

WordPress uses the Gutenberg block editor. **Post content MUST be Gutenberg-compatible HTML, NOT raw Markdown.**

Good:
```html
<!-- wp:paragraph -->
<p><strong>핵심 문장은 Bold로.</strong> 이렇게 써야 제대로 렌더링된다.</p>
<!-- /wp:paragraph -->

<!-- wp:heading {"level":2} -->
<h2>슬라이스 제목</h2>
<!-- /wp:heading -->

<!-- wp:code -->
<pre class="wp-block-code"><code>code block here</code></pre>
<!-- /wp:code -->
```

Bad (will show raw text):
```markdown
## Markdown 제목
**볼드** _이탤릭_
```

**Rules:**
- NO YAML frontmatter — WordPress stores metadata separately
- NO raw Markdown (`#`, `##`, `**`, `*`, `- `) — use HTML tags
- ALL content must be wrapped in Gutenberg comment blocks (`<!-- wp:paragraph -->...<!-- /wp:paragraph -->`)
- Use `<!-- wp:list -->` for lists, `<!-- wp:code -->` for code blocks, `<!-- wp:heading {"level":2} -->` for headings
- Use `<!-- wp:html -->...<!-- /wp:html -->` for custom HTML sections (cards, hero, etc.)

### Pipeline (2026-07-01 redesign)

```
content-curator (script, 08:00/15:00, $0)
  → reads: trend keep, SEO articles, git, kanban, narrative arc, backlog
  → heuristic dedup + scoring
  → kanban INSERT (content-write / trend-review / creative-write)
  → office-autopilot (5m) picks up → orchestrator → content-manager agent
    → writes post (Gutenberg HTML, SVG cover)
    → calls create_post(status="publish")  (creative-write만 draft)
    → content-editor (agent, 12:00/20:00) → 사후 QA
    → updates narrative_arc + content-inventory
```

**규칙:**
- **No CLI approval needed.** Pipeline is fully autonomous.
- `create_post` 호출 시 **반드시** `slug`, `author`, `category` 전달. `tags`는 절대 전달 금지.
- `slug`: 영어 kebab-case (예: `model-routing-architecture`). 절대 한글/빈 값 금지.
- `author`: `1` (YOUR_USERNAME) — 전 카테고리 공통
- `category`: 카테고리 **이름**(ID 아님): `"Build Log"`, `"AI & Tools"`, `"Systems"`, `"Creative"`
- **Creative pillar는 explicit-only.** 자동 감지 금지. kanban task / 사용자 요청 / `creative-backlog.md` 참조 시에만 작성.
- SVG cover를 생성했다면 `featured_image`에 절대 경로 전달
- Draft 생성 후 editor agent가 자동 QA → 수정 → publish
- 사용자가 마음에 안 들면 wp-admin에서 unpublish → 다음 run 때 반영
- "이건 publish하지 마" 같은 피드백은 memory에 저장되어 다음 draft에 반영됨

### Site Config

| Property | Value |
|----------|-------|
| URL | `https://YOUR_DOMAIN` |
| Admin | `https://YOUR_DOMAIN/wp-admin` |
| Theme | GeneratePress 3.6.1 |
| Fonts | Noto Sans KR (body), Noto Serif KR (headings), JetBrains Mono (code) |
| Colors | `#fafaf8` bg, `#8b7355` accent, `#1c1c1a` text |
| Layout | no-sidebar, separate-containers |
| Tunnel | Cloudflare Tunnel (launchd: `ai.{{AGENT_NAME_LOWER}}.cloudflared-wp`) |

## Relationship to content-pipeline Skill

This skill supersedes the older `content-pipeline` skill which was based on trend-harvester/SEO sources with a 3-hour cycle. The new approach:
- **Source**: User's own work (sessions, git, kanban) vs external trends/SEO
- **Cycle**: Daily, material-driven vs fixed 3-hour
- **Agent**: Single autonomous profile vs multi-stage kanban pipeline
- **Images**: SVG + Excalidraw PNG + Mermaid vs text-only drafts

The two overlap. Consolidation deferred to background curator.

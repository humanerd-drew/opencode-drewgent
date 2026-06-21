---
title: Content Pipeline — Compiled
type: wiki-compiled
tags: [compiled, content, pipeline, wordpress, quartz, publishing, reefwatch]
trigger: "wiki-compile 2026-06-21 — compiled from P2-hippocampus; updated with ReefWatch style, narrative arc, CMO agent"
provenance:
  session: "2026-06-21 wiki-compile"
  decision: "Content pipeline architecture from memories/insights and growth engine"
created: 2026-06-21
updated: 2026-06-21
links:
  - "P5-ego/wiki/compiled/taste-decisions"
  - "P5-ego/wiki/compiled/seo-insights"
  - "P5-ego/wiki/compiled/brand-and-persona"
  - "P5-ego/wiki/compiled/system-incidents"
---

# Content Pipeline — Compiled

## Core Decisions

### 1. Trigger + Kanban-Worker Pipeline
**What:** Content pipeline split into cron trigger (shell, 0 LLM) → kanban worker (full reasoning). Same pattern as Trend Harvester and Taste Review.
**Why:** Monolithic cron timed out at 600s. Separation allows each worker its own timeout budget.
**Alternatives considered:** Longer timeout, async cron.
**Status:** Active.

### 2. Method A vs Method B
**What:** Two content generation modes:
- **Method A (Aggregator):** External sources (trend-harvester, SEO) → kanban task → content-writer worker (3-hour cycle)
- **Method B (CMO Agent):** Internal work observation → single autonomous agent (daily) — supersedes multi-stage pipeline
**Why:** Method B eliminates complexity. User preference: "하나로 해" (do it as one).
**Status:** Both active. Method B preferred.

### 3. Editorial North Star
**What:** `public-worthy content = 기록 + 해석 + 재사용 가능한 통찰` (record + interpretation + reusable insight). 5-axis scoring: Drew-angle, Insight, Evidence, Portfolio value, Specificity. ≥7/10 passes.
**Why:** Quality gate prevents noise. Only content with reusable insight passes.
**Status:** Active.

### 4. ReefWatch Writing Template
**What:** 7-point structure adapted from dev.to/siiddhantt/building-reefwatch:
1. Problem framing → Bold claim → Design constraint
2. One-sentence summary → Show-before-explain images
3. Outcomes table → Build path table
**Why:** Structured templates produce more compelling technical content. Emphasizes problem framing and design constraints.
**Status:** Active. Applied in content-manager skill.

### 5. Narrative Arc (Season 1: Taste Engineering)
**What:** Content organized as seasons. Season 1: 4 published episodes + 3 active threads (Taste Engineering, Code Architecture, Pipeline Evolution).
**Why:** Narrative continuity across pieces. Each builds on the previous.
**Status:** Active. Documented at `P4-cortex/content/narrative_arc.md`.

### 6. Quartz Publish Safety — DraftFilter v2
**What:** DraftFilter v2 includes only `status: published|polished`. Never use `publish` singular.
**Why:** Quartz' `RemoveDrafts` checks `draft === true` only → `publish` singular leaks draft content (6 articles leaked 2026-06-02).
**Alternatives considered:** Rely on Quartz default filter (leaks drafts).
**Status:** Active. Plugin order: `FrontMatter() → DraftFilter() → transformers`.

### 7. Content Manager Agent (CMO-style)
**What:** Subagent profile `content-manager` (deepseek-v4-pro). Observes user work (sessions, git, kanban), curates narrative-worthy material, produces multi-format drafts (blog + X thread + LinkedIn), maintains narrative arc continuity.
**Why:** Automated content creation from actual work output. Eliminates separate writing workflow.
**Alternatives considered:** Human-only content creation, separate writing tools.
**Status:** Active. Daily cron (material-driven, not fixed).

### 8. Editor / Humanizer Pipeline
**What:** Content passes through editor (glm-5.2) for Korean language QA + humanizer for AI-ism removal. 29-pattern detection + voice calibration.
**Why:** Korean quality needs polish. Humanizer detects "AI smells."
**Alternatives considered:** Single model for all writing, no editorial pass.
**Status:** Active. Korean editing step is mandatory.

### 9. WordPress Deployment
**What:** WordPress on Docker (colima) with Blocksy theme, custom fonts. Data on Synology NAS (`/Volumes/humanerd/docker/wordpress/`). Custom MCP server (7 tools) for agent publishing.
**Why:** Need CMS with MCP integration. Blocksy for performance + customization.
**Alternatives considered:** Static site only (Quartz, humanerd.kr), headless CMS.
**Status:** Active. Served behind Cloudflare.

### 10. $0 Visuals Policy
**What:** SVG (model writes XML), Mermaid (inline), Excalidraw→PNG (Puppeteer). No paid APIs.
**Why:** User rejected DALL-E/FAL costs.
**Status:** Active.

## Rationale
Content pipeline evolved from manual → monolithic cron → trigger+kanban-worker. Method B (CMO agent) preferred over Method A (multi-stage). ReefWatch template adopted for compelling technical content.

## Current Status
All pipeline components active. DraftFilter v2 prevents leaks. CMO agent produces daily content. Korean editorial step mandatory. WordPress deployed with MCP. humanerd.kr via Quartz. Season 1 narrative arc in progress.

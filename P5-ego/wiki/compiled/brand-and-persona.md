---
title: Brand, Persona & Content Identity — Compiled
type: wiki-compiled
tags: [compiled, brand, persona, identity, content, narrative]
trigger: "wiki-compile 2026-06-21 — compiled from P1-limbic and P4-cortex content records"
provenance:
  session: "2026-06-21 wiki-compile"
  decision: "Consolidate brand identity, persona, writing style, and narrative arc"
created: 2026-06-21
updated: 2026-06-21
links:
  - "P5-ego/SELF_MODEL"
  - "P1-limbic/persona/SOUL"
  - "P1-limbic/persona/writing-style-guide"
  - "P5-ego/wiki/compiled/content-pipeline"
  - "P5-ego/wiki/compiled/taste-decisions"
---

# Brand, Persona & Content Identity — Compiled

## Core Decisions

### 1. Identity: Humanerd (Never "Hugh Kim")
**What:** Brand identity is "humanerd" — never "Hugh Kim" or any other name. Vault = source of truth for both brain and public site (humanerd.kr).
**Why:** Consistent identity across all channels. Vault-to-site mapping via Quartz + Cloudflare Pages.
**Status:** Active. Brand guide at `P4-cortex/content/brand-guide.md`.

### 2. Brand Positioning
**What:** "Build in Public" + "Taste Engineering" as core brand pillars. Target audience: Korean developers, AI system builders.
**Why:** User's work (Drewgent, M-LOG, trend analysis) is inherently a build-in-public narrative. Taste engineering differentiates from generic AI content.
**Status:** Active. Documented in brand-guide.md.

### 3. Tone and Voice
**What:** Korean+English bilingual. Core voice characteristics:
- Direct, opinionated, answer-first
- "제대로" (properly) > speed
- Root cause focus (근본 원인 해결)
- Try-first philosophy, not fear-based
**Status:** Active. Writing style guide at `P1-limbic/persona/writing-style-guide.md`.

### 4. SOUL (Persona Document)
**What:** P1-limbic/persona/SOUL.md defines the agent's persona: what it values, how it communicates, its relationship with the user.
**Why:** Consistent agent behavior across all interactions. Persona is the first layer of the subsumption hierarchy (after P0 rules).
**Status:** Active. Loaded automatically by opencode.

### 5. Narrative Arc: Season 1 "Taste Engineering"
**What:** Content narrative organized as seasons. Season 1 = "Taste Engineering" covering:
- Published (4 episodes): Blog posts on taste-driven AI engineering
- Active threads: Taste Engineering, Code Architecture, Pipeline Evolution
**Why:** Narrative continuity across content pieces. Each piece builds on the previous.
**Status:** Active. Narrative arc documented at `P4-cortex/content/narrative_arc.md`.

### 6. Writing Style Guidelines
**What:** Key conventions documented in writing-style-guide.md:
- Answer-first: conclusion → details → appendix
- Korean technical writing patterns
- Specific terminology (Drewgent, Hermes, Gateway, M-LOG, PDC, Kanban)
- Glossary at `P4-cortex/content/glossary.md`
**Status:** Active.

### 7. ReefWatch Content Writing Template
**What:** 7-point writing structure adapted from `dev.to/siiddhantt/building-reefwatch`:
1. Problem framing → Bold claim → Design constraint
2. One-sentence summary → Show-before-explain images
3. Outcomes table → Build path table
**Why:** Structured templates produce more compelling technical content. ReefWatch pattern emphasizes problem framing and design constraints.
**Status:** Active. Applied in content-manager skill.

### 8. $0 Visuals Policy
**What:** All content visuals generated via SVG (model writes XML), Mermaid (inline), Excalidraw→PNG (Puppeteer). No paid APIs (DALL-E, FAL, Midjourney).
**Why:** User explicitly rejected paid image generation costs.
**Status:** Active. SVG covers, Mermaid diagrams, Excalidraw architecture drawings.

### 9. Content Status State Machine
**What:** Content pipeline state machine: `draft → in_review → polished → published → [live]` or `→ archived → [excluded]`.
**Why:** Clear lifecycle prevents premature publishing.
**Status:** Active. Quartz DraftFilter v2 enforces: only `published|polished` pass.

## Rationale
Brand identity is grounded in the user's actual work (build-in-public) and differentiated by taste engineering focus. Persona (SOUL) ensures consistent agent behavior. Narrative arc provides content continuity across seasons.

## Current Status
All identity and persona decisions active. Season 1 narrative arc in progress with 4 published episodes + 3 active threads. Content follows ReefWatch template. $0 visuals policy active. State machine prevents publishing errors.

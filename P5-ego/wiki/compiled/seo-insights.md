---
title: SEO Insights — Compiled
type: wiki-compiled
tags: [compiled, seo, search, ai-overviews, content-strategy, ontology]
trigger: "wiki-compile 2026-06-21 — compiled from P2-hippocampus/knowledge/seo-articles; updated with ontology and corpus details"
provenance:
  session: "2026-06-21 wiki-compile"
  decision: "Collect SEO knowledge from harvester articles and ontology"
created: 2026-06-21
updated: 2026-06-21
links:
  - "P5-ego/wiki/compiled/content-pipeline"
  - "P5-ego/wiki/compiled/taste-decisions"
  - "P5-ego/wiki/compiled/trend-harvester"
---

# SEO Insights — Compiled

## Core Decisions

### 1. SEO Article Harvester
**What:** Automated RSS feed monitoring → article collection → trending analysis pipeline. Articles stored in `P2-hippocampus/knowledge/seo-articles/` organized by year.
**Why:** Stay current on AI search, Google core updates, and agentic web trends without manual monitoring.
**Alternatives considered:** Manual RSS reading, newsletter subscriptions.
**Status:** Active. Uses trigger+kanban-worker pattern.

### 2. Corpus Scale and Sources
**What:** 2,853+ curated articles from 25+ sources: Ahrefs, Google, SEMrush, Yoast, Moz, SearchEngineJournal, SearchEngineLand, SEOPress, Copyblogger, GrowthMK (Korean), Wired, etc.
**Why:** Broad coverage across English and Korean SEO sources.
**Archive management:** 301 archived duplicates cleaned (naming normalization). `_new/` for incoming, organized by year.
**Status:** Active. GrowthMK (Korean) primary for local insights.

### 3. SEO Ontology (v0.2.0)
**What:** 143 nodes, 243 edges covering: Technical SEO, On-Page SEO, Google Algorithm, Core Web Vitals, Structured Data, Content Strategy, Link Building, Local SEO, AI & LLM Search, SEO Analytics.
**Why:** Structured ontology enables targeted queries and trend analysis.
**Status:** Generated 2026-06-20. Active.

### 4. Key SEO Themes Collected (2026)
**What:** Topics identified from 2,853+ collected articles:
- Google AI Overviews / AI Mode replacing classic search
- Agentic Web readiness (Lighthouse agentic browsing category)
- GEO (Generative Engine Optimization) vs traditional SEO
- Google May 2026 Core Update — intent matching
- UK publishers opt-out requirements for AI search
- E-E-A-T refinement for AI era
- llms.txt standardization for AI agent discovery
**Status:** Collection ongoing. AI/agentic search is dominant theme.

### 5. AI Performance Reporting
**What:** Google added AI performance reports to Search Console and Merchant Center. Agentic browsing category in Lighthouse.
**Why:** Traditional SEO metrics are insufficient for AI-driven search traffic.
**Status:** Monitor trend. Align humanerd.kr and m-log with AI search requirements.

### 6. Korean SEO Focus
**What:** 200+ Korean-language SEO articles covering Naver search, Korean payment gateway SEO, local marketing strategies.
**Why:** Primary market is Korean-speaking users. Naver has different ranking factors than Google.
**Status:** Active collection.

## Rationale
SEO landscape shifting from keyword optimization to AI/agent discoverability. Traditional backlinks less relevant; entity optimization and structured data for AI answers more critical. Korean SEO requires separate Naver strategy.

## Current Status
SEO harvester operational. 2,853+ articles collected. Ontology v0.2.0 (143 nodes). Focus shifting to agentic web readiness and AI overview optimization. Korean SEO pipeline active.

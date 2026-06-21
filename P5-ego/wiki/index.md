---
title: LLM Wiki Index
type: wiki-index
space: concept
tags: [wiki, compiled-knowledge]
created: 2026-06-21
trigger: "Karpathy compile pattern — compile raw P2 data into structured wiki"
provenance:
  session: "2026-06-21 wiki-compile"
  decision: "P2 = Raw Archive (read-only), P5-ego/wiki = Compiled Wiki. Agents query wiki first."
schedule:
  compile: "0 3 * * 0 (weekly Sunday 03:00)"
  lint: "0 4 * * * (daily 04:00)"
links:
  - "P2-hippocampus/README"
  - "P5-ego/SELF_MODEL"
  - "P5-ego/wiki/lint-report"
---

# LLM Wiki Index

Compiled knowledge base for the Drewgent system. This is the canonical query target for agents — **always search here before reading raw P2 data**.

## Architecture

```
P2-hippocampus/         ← Raw Archive (unstructured, read-only)
  memories/               Raw memory files
  sessions/               Raw session logs
  knowledge/              Raw collected knowledge

P5-ego/wiki/            ← Compiled Wiki (structured, query-first)
  compiled/               Weekly-compiled wiki pages
  queries/                Saved query patterns
  index.md                This index
  lint-report.md          Daily lint status
```

### Query Routing

1. Search `P5-ego/wiki/compiled/` for relevant wiki pages
2. If not found, search `P2-hippocampus/memories/` or `P2-hippocampus/knowledge/`
3. If still not found, search `P2-hippocampus/sessions/`
4. File a wiki-compile candidate if you had to go to raw data

## Compiled Pages

### System Architecture

| Page | Topic | Status |
|------|-------|--------|
| [[P5-ego/wiki/compiled/agent-architecture]] | P-layer brain, 14 subagent profiles, delegate/task dispatch, office autopilot, customize layer, ACP, harmony check | Active |
| [[P5-ego/wiki/compiled/governance-system]] | P0-brainstem rules, 禁 neurons, OpenCrab ontology, ReBAC, 3-phase QA gate, tiered autonomy, knowledge bus | Active |
| [[P5-ego/wiki/compiled/model-routing]] | 3-tier Flash/Pro/Max, subagent model assignment, ESCALATE mechanism, task vs delegate, Token Plan | Active |
| [[P5-ego/wiki/compiled/skill-system]] | 100+ skill architecture, 62 categories, provenance convention, design patterns, SkillOpt | Active |

### Operations

| Page | Topic | Status |
|------|-------|--------|
| [[P5-ego/wiki/compiled/launchd-system]] | KeepAlive template, 3 services, self-healing, mass failure postmortem, log rotation | Active |
| [[P5-ego/wiki/compiled/cron-operations]] | Unified dispatcher, jobs.json, idempotent runner, script fastpath, watchdog chain, full schedule table | Active |
| [[P5-ego/wiki/compiled/kanban-system]] | 3 board dispatchers, dual reclaim, pipeline, hallucination detection, office autopilot, parent context injection | Active |
| [[P5-ego/wiki/compiled/discord-infrastructure]] | Gateway bot, send pipeline, token resilience protocol, MCP server, notification pipeline | Active |

### Knowledge & Intelligence

| Page | Topic | Status |
|------|-------|--------|
| [[P5-ego/wiki/compiled/memory-knowledge]] | Karpathy compile, query routing, MEMORY.md split pattern, fact half-life, GBrain 3-pillar, wiki cron | Active |
| [[P5-ego/wiki/compiled/brain-signal-system]] | GBrain MCP tools, brain signal processing, fact extraction, takes/calibration, dream system, knowledge bus | Active |
| [[P5-ego/wiki/compiled/growth-engine]] | Context compression, token headroom, 8 autonomous behaviors, No Silent Failure, 3-file rule, Garry Tan concepts | Active |

### Decisions & Culture

| Page | Topic | Status |
|------|-------|--------|
| [[P5-ego/wiki/compiled/taste-decisions]] | Provenance, leverage score, tiered autonomy, answer-first, ponytail, baseline-ui, taste review, cross-cutting patterns | Active |
| [[P5-ego/wiki/compiled/trend-harvester]] | 5-axis scoring, collect→evaluate→keep→apply→retire pipeline, taste review, schedule | Active |

### Content & Brand

| Page | Topic | Status |
|------|-------|--------|
| [[P5-ego/wiki/compiled/content-pipeline]] | Trigger+worker, Method A/B, ReefWatch template, narrative arc, DraftFilter v2, CMO agent, WordPress | Active |
| [[P5-ego/wiki/compiled/brand-and-persona]] | Brand identity (humanerd), tone/voice, SOUL, narrative arc Season 1, writing style, $0 visuals, state machine | Active |
| [[P5-ego/wiki/compiled/seo-insights]] | SEO article harvester, 2,853+ articles, ontology v0.2.0, AI overviews, Korean SEO | Active |

### Incidents

| Page | Topic | Status |
|------|-------|--------|
| [[P5-ego/wiki/compiled/system-incidents]] | 11 postmortems: DateTime mismatch, PYTHONPATH, dual DB, cron stall, double-fire, ACP spinner, mass failure, draft leak, stalled jobs, false alarm | Active |

## Saved Queries

<!-- see queries/ directory -->

## Lint Status

<!-- See lint-report.md for daily health status -->
<!-- lint-report.md currently needs population from wiki-lint cron -->

---
title: "Trend Discussion — Agent Memory Systems (Engram, MemOS, Cognee)"
type: analysis
tags: [trend-discuss, memory, gbrain, eng, integration]
created: 2026-06-29
leverage_score: 3
provenance:
  session: "2026-06-29 trend-discuss-memory-systems"
  trigger: "Trend Harvester keep items with scores 7.05-7.86 for memory system alternatives"
  decision: "Engram is the only drop-in candidate; MemOS is too heavy; Cognee overlaps gbrain"
---

# Agent Memory Systems — Comparative Analysis

**Executive Summary:** Three trending agent memory systems were evaluated against Drewgent's existing gbrain (PGLite) memory architecture. **Engram** (4.7k★) is the most promising — a lightweight Go binary with native MCP and direct `engram setup opencode` support that could serve as a complementary session-memory layer. **MemOS** (10k★) has impressive benchmarks (+43.7% accuracy vs OpenAI Memory, 35.24% token savings) but requires Neo4j+Qdrant+Redis infrastructure with no stdio MCP transport, making it a poor fit for Drewgent's local-first approach. **Cognee** (24.9k★) overlaps heavily with gbrain's knowledge graph capabilities and would be redundant. **Recommendation: integrate Engram as a session-memory supplement to gbrain; skip MemOS and Cognee.**

---

## Current Baseline: gbrain (PGLite)

| Metric | Value |
|--------|-------|
| Pages | 23 |
| Chunks | 49 (100% embedded) |
| Links | 0 (link density score: 0) |
| Orphans | 23 (100%) |
| Brain Score | 45/100 |

gbrain provides vector+keyword hybrid search, knowledge graph, takes/calibration, and fact extraction through MCP tools. Its weakness is **session memory** — gbrain is document-oriented (pages), not interaction-oriented. It has no concept of session lifecycle, no automatic capture of agent decisions mid-session, and no compaction survival mechanism. The wiki-compile cron tries to bridge this but is batch/daily.

---

## Per-Item Analysis

---

### 1. Engram — `Gentleman-Programming/engram` (Score: 7.86)

**One-line value prop:** Lightweight Go binary + SQLite + MCP that gives any MCP-compatible coding agent persistent session-to-session memory with zero dependencies.

**Key stats:** 4.7k★ | 540 forks | 93 releases (v1.17.0) | 352 commits | MIT | Go

**Architecture:**
```
Agent (Claude Code / OpenCode / Gemini CLI / ...)
    ↓ MCP stdio
Engram (single Go binary, ~10MB)
    ↓
SQLite + FTS5 (~/.engram/engram.db)
```

**20 MCP tools organized as:**
- **Save & Update:** `mem_save`, `mem_update`, `mem_delete`, `mem_suggest_topic_key`
- **Search & Retrieve:** `mem_search`, `mem_context`, `mem_timeline`, `mem_get_observation`
- **Session Lifecycle:** `mem_session_start`, `mem_session_end`, `mem_session_summary`
- **Conflict Surfacing:** `mem_judge`, `mem_compare`
- **Lifecycle Review:** `mem_review`
- **Utilities:** `mem_save_prompt`, `mem_stats`, `mem_capture_passive`, `mem_merge_projects`, `mem_current_project`, `mem_doctor`

**Comparison to gbrain:**
- gbrain = persistent knowledge graph (pages, links, takes). Good for structured, long-lived knowledge.
- Engram = persistent session memory (observations, decisions, context). Good for ephemeral agent reasoning.
- **These are complementary, not overlapping.** gbrain has no session lifecycle. Engram has no knowledge graph.
- Engram's conflict detection (`mem_judge`/`mem_compare`) is unique — gbrain has nothing like it.

**Direct `opencode` support:** `engram setup opencode` auto-wires MCP config. The OpenCode plugin uses `engram serve` (HTTP API on :7437) for session tracking in the background.

**Infrastructure overhead:** Zero. Single binary, single SQLite file. `brew install gentleman-programming/tap/engram`.

**Token savings:** Not quantified (it's context injection, not compression), but having relevant session memory reduces LLM re-learning cost.

**Decision: INTEGRATE as session-memory supplement to gbrain.**

---

### 2. MemOS — `MemTensor/MemOS` (Score: 7.05)

**One-line value prop:** Self-evolving memory OS + MCP claiming 35.24% token savings via L1/L2/L3 tiered memory and crystallized skills driven by feedback.

**Key stats:** 10k★ | 911 forks | 31 releases (v2.0.20) | 1,828 commits | Apache 2.0 | TypeScript/Python

**Architecture:**
```
Agent (Hermes / OpenClaw)
    ↓ MCP plugin
MemOS API Server (Docker)
    ↓
MySQL + Neo4j + Qdrant + Redis Streams
```

**Memory layers (L1/L2/L3):**
- **L1 Traces:** Raw interaction history (ephemeral, high-volume)
- **L2 Policies:** Learned preferences and behaviors (compressed)
- **L3 World Model:** User understanding and persona (structured)
- **Crystallized Skills:** Reusable patterns extracted from feedback

**Benchmark claims:**
| Benchmark | Result | Improvement |
|-----------|--------|-------------|
| LoCoMo | 75.80 | — |
| LongMemEval | +40.43% vs baseline | — |
| PrefEval-10 | +2568% | — |
| PersonaMem | +40.75% | — |
| vs OpenAI Memory | +43.70% Accuracy | — |
| Token Savings | 35.24% | — |

**Comparison to gbrain:**
- MemOS is an *operating system* for memory — it requires Neo4j (graph), Qdrant (vector), MySQL (relational), Redis (scheduling). This is a full-stack infra commitment.
- gbrain is a self-contained PGLite database with integrated vector+keyword+graph.
- MemOS has no stdio MCP transport — it's HTTP API only, requiring a running server.
- The L1/L2/L3 self-evolving memory concept is genuinely interesting, but the implementation complexity is an order of magnitude beyond what Drewgent needs.

**Drewgent-fit concerns:**
- Requires Docker + 4 backing services. Violates ponytail principle.
- MemOS is designed for Hermes Agent and OpenClaw, not opencode. The "plugin" for opencode doesn't exist — only Hermes and OpenClaw plugins ship.
- Token savings claim (35.24%) is on API-based LLM calls to a hosted MemOS cloud service — unclear how much applies to opencode's local subscription model.
- The comparison table admits it's black-box graph memory (not inspectable like gbrain).

**Decision: SKIP.** Infrastructure overhead too high for the benefit. If token savings in coding-agent context were validated, reconsider, but the benchmarks are on social/persona tasks, not code reasoning.

---

### 3. Cognee — `topoteretes/cognee` (Score: 7.05)

**One-line value prop:** Open-source knowledge graph engine that gives AI agents persistent long-term memory across sessions with a unified remember/recall API.

**Key stats:** 24.9k★ | 2.3k forks | 121 releases (v1.2.2) | 8,426 commits | Apache 2.0 | Python

**Architecture:**
```
Agent (Claude Code / OpenClaw / any)
    ↓ MCP stdio or HTTP
Cognee API Server (Python/Docker)
    ↓
PostgreSQL + PGVector (or Neo4j + Qdrant)
    ↓
Knowledge Graph + Vector Store
```

**API surface:**
- `cognee.remember(data)` — ingest and store in knowledge graph
- `cognee.recall(query)` — auto-routing search (vector + graph)
- `cognee.forget(dataset)` — delete
- `cognee.improve()` — optimize ontologies
- MCP server with `remember` / `recall` / `forget` tools

**Benchmarks (BEAM):**
| Setting | Cognee | Previous SOTA | Baseline |
|---------|--------|---------------|----------|
| 100K tokens | 0.79 | 0.735 | ~0.33 |
| 10M tokens | 0.67 | 0.641 | ~0.33 |

**Comparison to gbrain:**
- Cognee and gbrain are **near-identical in purpose**: both are knowledge graph engines with vector+graph hybrid search.
- gbrain does everything Cognee does (ingest → chunk → embed → graph → search) but with tighter integration (MCP tools built into the opencode platform), a simpler architecture (PGLite vs Postgres+PGVector), and no Docker requirement.
- Cognee has more sophisticated ontology generation and Claude Code plugin. gbrain has takes/calibration/facts that Cognee lacks.

**Drewgent-fit concerns:**
- **Direct overlap with gbrain.** Adding Cognee would mean two knowledge graph systems competing for the same role — fragmentation, not synergy.
- Requires Postgres (or Neo4j+Qdrant). gbrain runs on PGLite with zero setup.
- Cognee MCP server runs inside Docker — adds deployment complexity.
- The Claude Code plugin would need adaptation for opencode.
- Cognee's remember/recall API maps almost 1:1 to gbrain's put_page/query. Redundant.

**Decision: SKIP.** gbrain already covers this space with lower overhead. If gbrain's brain score (45/100) is a concern, invest in improving gbrain's wiki pipeline and link density rather than adding a parallel system.

---

## Comparison Matrix

| Axis | Engram | MemOS | Cognee | gbrain (current) |
|------|--------|-------|--------|-----------------|
| **Primary role** | Session memory | Memory OS | Knowledge graph | Knowledge graph |
| **Backend** | SQLite + FTS5 | MySQL+Neo4j+Qdrant+Redis | Postgres+PGVector | PGLite (Postgres) |
| **MCP transport** | stdio (native) | HTTP (plugin) | stdio + HTTP | stdio (built-in) |
| **OpenCode support** | ✅ `engram setup opencode` | ❌ Hermes/OpenClaw only | ❌ Claude Code/OpenClaw | ✅ Built-in |
| **Dependencies** | None (single binary) | Docker + 4 services | Docker + Postgres | None (built-in) |
| **Stars** | 4.7k | 10k | 24.9k | — |
| **Session lifecycle** | ✅ Full | ✅ Full | ❌ (document-based) | ❌ (page-based) |
| **Conflict detection** | ✅ mem_judge/mem_compare | ❌ | ❌ | ❌ |
| **Knowledge graph** | ❌ | ✅ (Neo4j) | ✅ (PG/Neo4j) | ✅ (PGLite) |
| **Self-evolving** | ❌ | ✅ L1/L2/L3 + Skills | ❌ | ❌ |
| **Token savings claim** | No data | 35.24% | No data | — |

---

## Recommendation Matrix

| System | Verdict | Rationale |
|--------|---------|-----------|
| **Engram** | ✅ **INTEGRATE** | Low risk, high complementarity. Single binary, native opencode support, fills the session-memory gap gbrain doesn't cover. |
| **MemOS** | ❌ **SKIP** | Heavy infrastructure for unclear benefit in code-reasoning context. No opencode plugin. L1/L2/L3 concept worth monitoring. |
| **Cognee** | ❌ **SKIP** | Direct overlap with gbrain. Redundant. Invest improvements in gbrain instead. |

---

## Engram Integration Plan (recommended)

### Phase 1 — Try (30 min)
```bash
brew install gentleman-programming/tap/engram
engram setup opencode
```
This auto-wires Engram MCP into opencode.jsonc. Validate the MCP tools appear and a `mem_save`/`mem_search` round-trip works in-session.

### Phase 2 — Evaluate (1 week)
- Use in daily sessions. Does `mem_context` inject relevant prior-session context?
- Does Engram survive opencode context compaction? (Engram's MCP is stdio-based, so the subprocess re-launches each session — should survive.)
- Measure: how many `mem_search` calls per session? What quality of prior context does it retrieve?

### Phase 3 — Wire into brain signal system (if Phase 2 passes)
- `mem_save` call from `@identity/brain/rules.md` or signal processor on significant agent decisions
- `mem_capture_passive` for automatic background capture during development
- Consider `mem_judge` integration for detecting conflicting architectural decisions

### Risk: Duplication cost
Engram and gbrain both embed information. If `mem_save` creates a memory in Engram while gbrain also stores a page for the same decision, there's conceptual duplication. Mitigation: use Engram for **session/decision** memory (what the agent did/learned this session) and gbrain for **knowledge** memory (structured, long-lived wiki content). They serve different purposes.

---

## Leverage Assessment

- **Problems this solves if Engram is integrated:**
  1. Agent forgets context between sessions (primary problem — affects every interaction)
  2. No automatic capture of architectural decisions during a session
  3. No compaction survival mechanism for session context
  4. No way to detect conflicting decisions across sessions

- **Leverage Score: 3/5** — Solves a real daily pain (context loss between sessions). Not a 4 because gbrain partially addresses memory via wiki, and not a 5 because it's an additive supplement, not a root-cause fix. The token savings are indirect (fewer re-explanation rounds).

---

## Data Sources

- Engram: https://github.com/Gentleman-Programming/engram (README, docs/ARCHITECTURE.md)
- MemOS: https://github.com/MemTensor/MemOS (README, arXiv:2507.03724)
- Cognee: https://github.com/topoteretes/cognee (README, arXiv:2505.24478)
- gbrain: gbrain MCP tools (get_stats, get_health), AGENTS.md

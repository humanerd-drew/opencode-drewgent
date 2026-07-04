---
title: "Trend Discuss: Code Intelligence Tools"
date: 2026-06-29
task: trend-discuss-code-intelligence
status: draft
tags: [trends, code-intelligence, codebase-memory-mcp, gortex, codegraph-rust, code-review-graph]
---

# Trend Discuss: Code Intelligence Tools

**Date:** 2026-06-29
**Question:** Worth replacing/supplementing `codebase-memory-mcp`?

---

## Executive Summary

The code intelligence layer is the most competitive segment in the agent tooling stack right now. Gortex (8.27) is the clear leader — a Go-based graph engine with 257 languages, 50× token reduction, MCP server, and cross-repo analysis. Code-review-graph (7.68, 19k stars) and codegraph-rust (7.73, 819 stars) are strong contenders. None justifies replacing `codebase-memory-mcp` today, but gortex deserves a **POC evaluation** as a supplement for its superior language coverage (257 vs ~20), blast-radius analysis, and cross-repo API contract detection — capabilities beyond our current MCP server.

---

## Per-Item Analysis

### gortex (8.27) — zzet/gortex
**One-liner:** Go-based code intelligence engine with 257-language tree-sitter parsing, MCP server, CLI, Web UI, and 175 MCP tools.

**Key features:**
- 257 languages via tree-sitter with LSP-grade resolution for 17 languages
- 50× token reduction via graph-native lookups instead of naive file reads
- Built-in MCP server with 175 tools + 16 resources + 3 prompts
- Cross-repo API contract detection (HTTP routes, gRPC, GraphQL, message topics, env vars)
- Blast-radius analysis and `preview_edit` / `simulate_chain` for speculative edits
- Embedded GloVe-50d semantic search (zero deps), opt-in MiniLM/Ollama/OpenAI
- Token savings dashboard (`gortex savings` — $168.69 saved on 11M tokens in benchmarks)
- Daemon mode with live fsnotify, on-disk snapshots, OS-supervised lifecycle
- Single static binary, Apache 2.0, 772 stars, 2,062 commits, 91 releases
- Built-in support for 17 AI coding agents including OpenCode

### codegraph-rust (7.73) — Jakedismo/codegraph-rust
**One-liner:** Rust-based code graphRAG with AST+FastML parsing, SurrealDB backend, and 4 consolidated agentic tools.

**Key features:**
- Full graph-based RAG with node/edge architecture plus semantic embeddings (hybrid 70/30 vector/keyword)
- 4 "agentic tools" that do multi-step reasoning: agentic_context, agentic_impact, agentic_architecture, agentic_quality
- Multi-tier indexing (fast/balanced/full) with LSP integration for balanced+ tiers
- Context overflow protection with per-tool truncation and accumulation guards
- Agent architecture flexibility: Rig (default), ReAct, or LATS reasoning strategies
- Requires SurrealDB (external dependency) — significantly more complex setup
- MIT license, 819 stars, 761 commits, no formal releases yet

### code-review-graph (7.68) — tirth8205/code-review-graph
**One-liner:** Python-based MCP/CLI code intelligence with 82× median token reduction, focused on PR review and blast-radius.

**Key features:**
- 30 MCP tools + 5 workflow prompt templates — purpose-built for code review
- 82× median per-question token reduction (range 38× – 528×)
- Blast-radius analysis with risk-scored PR reviews via GitHub Action
- ~30+ language coverage via tree-sitter (broad but narrower than gortex)
- Incremental updates <2 seconds via SHA-256 hash diffing
- GitHub Action integration with sticky PR comments and optional `fail-on-risk`
- SQLite storage, local-first, multi-repo daemon support
- MIT license, **19k stars**, 493 commits, Python 3.10+
- Token savings panel in CLI (`detect-changes --brief`)

### Understand-Anything (7.32) — Egonex-AI/Understand-Anything
**One-liner:** Everything-to-knowledge-graph tool with multi-agent LLM pipeline — more for onboarding than daily code intelligence.

**Key features:**
- Multi-agent pipeline (project-scanner, file-analyzer, architecture-analyzer, tour-builder, graph-reviewer)
- Works with Claude Code, Codex, Cursor, Copilot, Gemini CLI, OpenCode, and 13+ other platforms
- Interactive 3D web dashboard with search, guided tours, persona-adaptive UI
- Karpathy-pattern LLM wiki analysis (`/understand-knowledge`)
- Tree-sitter deterministic parsing + LLM semantic enrichment hybrid
- NOT an MCP server — it's a plugin/skill that produces a static knowledge graph JSON
- **68.9k stars**, MIT license, TypeScript
- Token-expensive on first run (LLM-driven file analysis)

---

## Comparison to Current Drewgent Setup

| Capability | codebase-memory-mcp | gortex | codegraph-rust | code-review-graph |
|---|---|---|---|---|
| MCP Server | ✅ Built-in | ✅ 175 tools | ✅ 4 agentic tools | ✅ 30 tools |
| Language count | ~20 | **257** | ~13 | ~30 |
| Cross-repo analysis | ❌ | **✅** | ❌ | ✅ (multi-repo registry) |
| Token savings | Good | **50×** | Moderate | **82×** median |
| Blast radius | ✅ Basic | ✅ Depth-3 | ✅ Full | ✅ Full |
| PR review | ❌ | ✅ PR tools | ❌ | **✅ Native GitHub Action** |
| Semantic search | ✅ | ✅ Embedded | ✅ Hybrid | ✅ Optional |
| Web UI | ❌ | ✅ Force-directed graph | ❌ | ✅ D3.js graph |
| OpenCode support | ✅ Built-in | ✅ | ❌ | ✅ |
| Setup complexity | Zero (built-in) | Single binary | SurrealDB needed | pip install |
| Stars | — | 772 | 819 | **19,000** |

**Key gap in current setup:** codebase-memory-mcp lacks:
1. Cross-repo analysis — can't track API contracts across repos
2. PR review integration — no GitHub Action for risk-scored reviews
3. Token savings visibility — no `gortex savings` style dashboard
4. 257-language parity — gortex handles every repo language

---

## Recommendation

### Primary: **Evaluate gortex as a supplement** (Integrate)

**Rationale:**
- Gortex supports OpenCode natively — minimal integration friction
- 257 language coverage eliminates blind spots in polyglot repos
- Cross-repo API contract detection is unique and valuable for microservice architectures
- Token savings dashboard provides hard ROI data for decision-making
- Single binary, no external deps — low operational cost
- The 50× token reduction claim is benchmarked and reproducible

**Suggested POC scope:**
1. Install gortex alongside codebase-memory-mcp on a representative repo
2. Compare symbol resolution accuracy and blast-radius quality for one week
3. Measure actual token savings in real opencode sessions
4. Evaluate cross-repo contract detection for multi-repo projects

### code-review-graph: **Evaluate for PR workflow enhancement** (Evaluate)

The 19k stars and GitHub Action integration make this worth evaluating specifically for our PR review pipeline. The risk-scored PR comments and fail-on-risk gate could tighten our QA workflow.

### codegraph-rust: **Skip** (too heavy, experimental)

SurrealDB dependency and pre-1.0 status make this too risky. Design is solid but setup overhead outweighs benefits.

### Understand-Anything: **Skip for code intelligence** (but note for wiki)

Not an MCP server — it's a Claude Code plugin. The Karpathy wiki analysis feature is interesting but Drewgent already has knowledge.db + wiki-compile for that.

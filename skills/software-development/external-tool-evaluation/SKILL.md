---
name: external-tool-evaluation
title: External Tool Evaluation
description: Evaluate a third-party GitHub repo or external tool for Drewgent integration. Use raw markdown curl + GitHub API to bypass UI, identify algorithm taxonomy, map to Drewgent hot spots, score 3-4 integration modes, recommend POC-first.
domain: software-development
space: outcome
type: workflow
tags: [external-tool, evaluation, github, integration, drewgent]
created: 2026-06-02
updated: 2026-06-14
links:
  - "[[P4-cortex/growth/INTEGRATION_PROTOCOL]]"
  - "[[P3-sensors/skills/SKILL-INDEX]]"
  - "[[P4-cortex/knowledge/garry-tan-unified-architecture-drewgent-review]]"
  - "[[skills/llm-model-migration]]"
  - "[[skills/gateway-module-extraction]]"
  - "[[P0-brainstem/brain/rules]]"
---

# External Tool Evaluation — Drewgent Integration Workflow

## When to use

User shares a GitHub repo link OR asks "what about X for Drewgent" / "should we use X" / "evaluate X for integration." Trigger keywords: "토큰 똑똑하게", "이 도구 쓸 수 있을까", "X 통합 검토", "headroom / RTK / lean-ctx / kompress / X 평가해줘".

## Why a skill is needed

GitHub UI via `mcp_browser_navigate` returns ~700-element accessibility tree with 95% chrome. Raw markdown via curl gives the actual content in 1 call. Repo root `docs/` is often a Next.js site, not source — `docs/spec/` or `crates/` is where architecture lives. Without this method, the agent spends 5+ browser tool calls extracting what `curl | head` returns in 1.

## Workflow (7 steps)

### 1. Raw markdown fetch (bypass GitHub UI)
```bash
curl -sL https://raw.githubusercontent.com/{owner}/{repo}/main/README.md | head -200
# 4.3k stars + last-commit 3h ago = maturity check satisfied
```

### 2. Repo health snapshot
```bash
curl -sL https://api.github.com/repos/{owner}/{repo}
# Check: stars, last_push_at (NOT updated_at), default_branch, license
```

### 3. Find actual architecture/spec files
```bash
# root docs/ is often a Next.js site — list subdirs
curl -sL https://api.github.com/repos/{owner}/{repo}/contents/docs
# For Rust+Python repos: look in crates/, headroom/transforms/, sdk/
# For docs-heavy repos: docs/spec/, docs/content/spec/
```
Pitfall: `docs/README.md` is often the website's README (Vercel deploy info), not the source README.

### 4. Identify the algorithm/feature taxonomy
Read 2-3 spec files or core source files. Extract:
- What it does (1-line)
- Algorithm list (each with 1-line description)
- Integration modes (proxy / library / wrap / MCP / middleware)
- Benchmarks (savings %, accuracy preserved)
- Reversibility (can original be retrieved?)

**Special category: Agent behavior rulesets.** Some tools (ponytail, caveman, etc.) don't have traditional algorithms — they ship a **ruleset/prompt** that modifies how the agent thinks before writing code. For these, extract:

- **Core ruleset** (the checklist/philosophy — this is what matters, portable across agent platforms)
- **Guardrails** (what the ruleset explicitly exempts from minimization — security, validation, data-loss, etc.)
- **Plugin/infrastructure** (commands, intensity levels, cross-platform adapters — platform-specific delivery, separate value from the ruleset)
- **Benchmarks** (measure the ruleset's impact, not the plugin's — rulesets are portable, plugins are not)
- **Deferral mechanism** (how shortcuts are tracked — e.g. `ponytail:` comments noting ceiling + upgrade path. Without this, minimizations become unrecoverable debt.)

### 5. Map to Drewgent hot spots
For each algorithm/feature, list Drewgent files that would benefit:
- Tool output hot spots: `tools/mcp_tool.py`, `tools/browser_tool.py`, `tools/file_tools.py`, `tools/terminal_tool.py`
- LLM call site: `run_agent.py:_interruptible_api_call()` (line ~5244)
- Existing compression: `agent/context_compressor.py` (conversation-level summary)
- Prompt caching: `agent/prompt_caching.py` (prefix alignment conflicts)

**For agent behavior rulesets only** — the integration point is NOT a code path. Map to:
- **AGENTS.md** (per-project ruleset — most portable, works with any agent reading the repo)
- **Hermes skill** (`~/.drewgent/skills/<category>/SKILL.md`) — injected per task, Drewgent-native
- **System prompt injection point** (Hermes config, model routing, skill loading) — if the ruleset needs to be always-on, not task-scoped
- **Neuron file** (`P0-brainstem/brain/rules.md` or `*.neuron`) — for immutable principles that should never be skipped

### 6. Score integration modes against Drewgent
Always evaluate 3-4 options with the same axes:
- Code change size
- Latency overhead
- Conflict with our gateway proxy structure
- Reversibility (can we roll back?)

Common modes for Drewgent:
- A. **Proxy** (zero code, runs alongside gateway) — usually conflicts with our existing gateway
- B. **SDK/Library in `_interruptible_api_call`** — surgical, best for compression libs
- C. **Wrap CLI** (`headroom wrap claude`) — conflicts with our `drewgent` wrapper
- D. **MCP server** (`gbrain serve`, `mcp install`) — **most modular**. Hermes MCP client already built-in. Add `mcpServers` entry in config.yaml, zero code change. Agent discovers tools automatically.
- E. **Ruleset-only adoption** (for agent behavior rulesets only) — copy the portable ruleset into Drewgent's AGENTS.md or a Hermes skill. Zero code change, no vendor lock-in. The plugin/commands layer is platform-specific (Claude Code vs Codex vs Cursor) and should be evaluated separately. Scoring axes differ: instead of latency/code-change, evaluate **ruleset completeness** (does it guardrail security?), **deferral hygiene** (are shortcuts tracked?), and **over-minimization risk** (what abstractions does it skip that Drewgent needs?).

### 6b. Architecture lens: two-repo vs unified vault
When evaluating an external tool, check if its architecture separates "agent behavior" from "world knowledge":

- **Two-repo** (GBrain, Garry Tan pattern): agent config in one repo, knowledge graph in another. Clean separation, but requires managing cross-repo state. Best for multi-agent deployments where different agent types share the same brain.
- **Unified vault** (Drewgent's `.drewgent/P0-P6`): agent architecture + knowledge in one tree with wikilinks between policy, experience, and memory. Simpler, no cross-repo sync, but harder to swap agent frameworks.

**Decision heuristic**: If the tool is primarily a *search/retrieval engine* (embedding, vector DB, knowledge graph), **MCP integration** is cleaner than repo restructuring — Drewgent keeps its unified vault, the tool serves as an additional retrieval layer.

### 7. Recommend with POC-first framing
Per memory: "옵션 (H1~H4) + '내 추천' + 'over-engineering 위험' 또는 '0 risk vs 작업 시간' 가성비 분석."

Default recommendation: POC first (30 min) before integration. Verify with dry-run or dry-mode audit before wiring into critical path.

## Output template (terminal-friendly, no markdown headers per SOUL)

```
[Tool] 한 줄 요약
[maturity] stars, last commit
[algorithms] 4-6 bullets
[benchmarks] % savings on real workloads + accuracy
[integration modes] 4-way score table
[hot spot mapping] our files × their algorithms
[risks] 3-4 bullets
[POC] 1-step 30min experiment
[options] H1 POC / H2 surgical / H3 full integration — with "내 추천" framing
```

## Pitfalls

- **GitHub UI snapshot is mostly chrome** — `browser_navigate` returns nav menus, header, sidebar, footer with ref IDs. The actual README content gets truncated at 8000 chars. Use raw curl.
- **`docs/` is often a Next.js site** — `docs/package.json`, `docs/next.config.mjs`, `docs/components/` are signs. Look for `docs/spec/`, `docs/content/`, or skip straight to `crates/`, `src/`, `headroom/`, etc.
- **Stars and recency lie** — 4.3k stars + commit 3h ago can still be a side project. Check contributor count and whether the most active branch is the default.
- **Don't propose proxy mode by default** — Drewgent's gateway is already a proxy. Adding another proxy layer creates debugging hell. Library/SDK in our existing call site is almost always better.
- **Benchmarks are on the tool's own workloads** — 92% savings on "code search" may not translate to Drewgent's pattern. Always map to our actual hot spots.
- **Compression + caching conflict** — if the tool reorders prefixes or rewrites system prompt, prompt_caching.py's KV cache hit rate can drop to 0. Verify CacheAligner / prefix-stability behavior before integration.
- **SaaS vs Self-Host TCO** — When a tool offers both cloud and self-host, evaluate REAL resource requirements against host capacity. Official minimum specs are often dev-mode figures, not production with all services. A Docker stack (DB + search + queue + app servers) can consume 4-8GB RAM before adding data. Decision heuristic: if the host has under 8GB free RAM or runs other memory-heavy services (Ollama, Hermes gateway, n8n), prefer SaaS.
- **Agent behavior rulesets: separate ruleset from plugin.** The ruleset (checklist, philosophy, guardrails) is portable across agents. The plugin (commands, intensity levels, cross-platform adapters) is platform-specific. Evaluating the plugin value as if it's the ruleset overstates the tool's portability. Always default to "ruleset-only" as H1 and only consider plugin if Drewgent's stack (Hermes + opencode-go) is directly supported.
- **Over-minimization risk with rulesets.** Rulesets that aggressively minimize code ("one line or nothing") can skip needed abstractions for complex domains. Check: does the ruleset have explicit guardrails for security, validation, data-loss prevention, and explicitly requested features? The best rulesets exempt these from minimization. Without guardrails, the ruleset is too dangerous for production use.
- **Deferral hygiene is critical.** If the ruleset encourages shortcuts (e.g. `ponytail:` comments), verify there's a mechanism to track and revisit them. Without it, minimizations become permanent tech debt — the agent writes the minimal version and never comes back to harden it.

## Verification

- [ ] Raw README fetched (not browser snapshot)
- [ ] Repo health checked (stars + last_push_at)
- [ ] 2-3 architecture/spec files read for actual algorithm details
- [ ] Drewgent hot spots identified with file paths
- [ ] 3-4 integration modes scored against Drewgent's gateway constraint
- [ ] POC option offered first (30 min, 0 risk)
- [ ] Risks section includes prompt-caching conflict check
- [ ] For ruleset tools: separated ruleset value from plugin value, checked guardrails and deferral hygiene
- [ ] Reference file added (`references/`) for detailed session findings

## Related

- [[P4-cortex/growth/INTEGRATION_PROTOCOL]] — when evaluation leads to "yes, integrate," follow this protocol
- [[skills/llm-model-migration]] — sibling skill for LLM provider updates
- [[skills/gateway-module-extraction]] — sibling skill for gateway refactoring
- [[P4-cortex/knowledge/garry-tan-unified-architecture-drewgent-review]] — "fat skills, thin harness" lens for evaluating if the tool's complexity fits

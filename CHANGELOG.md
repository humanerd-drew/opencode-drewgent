---

title: Changelog
type: document
space: concept
tags: [concept]
created: 2026-05-20
updated: 2026-06-23
links: []
links:
  - "[[@memory/knowledge/NEURONFS_RULES]]"
---


# Drewgent Changelog

All notable changes to Drewgent Agent are documented here.

---

## [0.8.0] — 2026-06-22

### Architecture Compression

#### What changed
- **P-layer 7→3**: P0/P1/P5 → `@identity/`, P2/P4 → `@memory/`, P3/P6 → `@action/`. Symlinks preserve backward compatibility.
- **Agent profiles 14→6**: tester, security-reviewer, orchestrator, sre, editor, analyst, content-manager merged into 6 core profiles. designer migrated to skill.
- **Pipeline 5→3**: tester and archiver stages removed. Archiver runs as post-hook on completion.
- **MCP conditional**: lazyweb and specification-website set to `enabled: false`; activated on demand via skill().
- **Scripts cleanup**: 18 unreferenced scripts archived (25 active remain).
- **Tools cleanup**: 22 unreferenced tools archived (36 active remain).
- **Provenance cleanup**: `trigger:` and `provenance:` frontmatter lines removed from 27 SKILL.md files.
- **Wikilinks**: 28,347 stale `[[P[0-6]-` references updated to `@identity/`, `@memory/`, `@action/` paths.
- **.gitignore**: `@identity/` and `@action/` removed from gitignore (must be tracked); `@memory/` remains gitignored (runtime data).

#### Files affected
- 127 files changed, 9,574 insertions, 16,890 deletions

---

## [0.7.4] — 2026-06-01

### MiniMax M3 + Token Plan Migration

#### What changed
- Drewgent의 기본 MiniMax 모델이 **M2.7 → M3**로 자동 전환
- 컨텍스트 윈도우: 200K (204,800) → **1M (1,048,576)**
- Token Plan 신규 가격 정책 적용
- 영향 파일 14개: production code 5 + docs 5 + comments 2 + 신규 Token Plan 참고 문서 1 + CHANGELOG 1
  - `source/_agent/orchestrator/bot.py` (follow-up, 2026-06-01): `call_minimax()`의 audit_log + `client.messages.create()` 두 곳을 M3로 정정. system prompt (`AGENT_SYSTEM`, `GEEKNEWS_ANALYZER_SYSTEM`)와 max_tokens (1000/800)는 M3에서 그대로 유효 (drop-in 호환).

#### Why
- M3: 신 프론티어 코딩 모델 (1M context, 강화된 멀티모달)
- M2.7 deprecation 대비
- Token Plan 가격 정책 변경 대응

#### Migration impact
- 기존 M2.7 사용자는 자동 전환 (별도 작업 불필요)
- M2.5 명시 사용은 계속 지원 (`MiniMax-M2.5` 직접 지정)
- `minimax-cn` provider도 M3 사용 (단, Token Plan quota는 global과 별도)

#### New reference doc
- `website/docs/reference/token-plan.md` — Token Plan 가이드 (가격, quota, M3 컨텍스트 활용)

#### Catalog 일관성 + multi-source 발견 (2026-06-01)
- **Catalog 노출 일관성 보강**: 2개 source mirror (top-level `drewgent_cli/` + `source/drewgent-agent/drewgent_cli/`) 양쪽의 `models.py` + `setup.py` 4개 파일을 grep sweep해 14개 production flip와 일치 확인. 추가로 `tests/test_setup_model_selection.py` (top + source) 2개 파일을 신규 보강 — `minimax-m3`을 첫 번째 entry로 노출.
- **Multi-source sync gap 발견**: 14개 production 파일 flip 이후 `tests/test_setup_model_selection.py`가 **top + source 두 곳에 mirror돼있는데 둘 다 M2.7만 노출**된 채 방치 — production은 M3로 flip됐는데 test는 M2.7에 pin된 상태. 같은 "M3 is default" claim이 production과 test 사이에 inconsistent. 양쪽 모두 첫 entry를 `minimax-m3`로 정렬하여 동기화.
- **이 발견이 중요한 이유**: Drewgent는 `drewgent-root-consolidation-20260506` 이후 top + source 2 source 구조를 유지 중. 같은 catalog claim이 두 곳에 있으면 **mirror 누락 시 production vs test drift**가 됨. 향후 default 모델 flip 시 반드시 4 spots (top/models.py + top/setup.py + source/models.py + source/setup.py) + 2 test spots 동기화 필요. 이게 일종의 "6-spot rule" — flip 후 `git grep`로 mirror 누락 검증.

---

## [0.7.3] — 2026-05-31

### Kanban Orchestrator — Autonomous Worker System

#### What changed

Drewgent now has a full kanban-based autonomous worker system. Workers claim tasks from the kanban board, execute them via AIAgent (with terminal, web, and brain tools), and report completion — enabling multi-task parallelism and task queuing.

#### Why

The Drewgent agent needed to handle multiple tasks concurrently, queue work, and provide visibility into task state. The kanban board (SQLite-based, stored in `~/.drewgent/P2-hippocampus/kanban/state/drewgent_tasks.db`) now serves as the task queue and state store.

#### Files changed

| File | Change | Location |
|------|--------|----------|
| `scripts/run_kanban_worker.py` | **NEW** — Worker script that reads `KANBAN_TASK_ID`, fetches task from DB, spawns AIAgent subprocess with task body, sends heartbeats every 60s, reports completion/failure | `~/.drewgent/scripts/` |
| `scripts/dispatch_once_content.py` | Updated to spawn `run_kanban_worker.py` via tempfile + venv python | `~/.drewgent/scripts/` |
| `scripts/dispatch_once_default.py` | Updated to spawn `run_kanban_worker.py` via tempfile + venv python | `~/.drewgent/scripts/` |
| `drewgent_cli/providers.py` | Fixed `determine_api_mode()` — moved URL heuristic (checking for `/anthropic` in endpoint) **before** provider transport lookup, so MiniMax with `/anthropic` endpoint correctly gets `anthropic_messages` mode | `providers.py` |
| `run_agent.py` | Fixed 1) `determine_api_mode()` called early in `__init__` before provider-known check; 2) `base_url` and `api_key` resolution for known third-party providers (minimax, minimax-cn, alibaba, deepseek) in `anthropic_messages` path — `effective_key`/`_anthropic_api_key` now properly set from resolved credentials | `run_agent.py` |
| `P4-cortex/scripts/kanban_dashboard_server.py` | **NEW** — Full rewrite with SSE real-time updates, drag-and-drop between columns, mobile responsive design, board-tab layout (5 columns in one row, board filter via tabs), new SSE broadcast system for card actions | `P4-cortex/scripts/` |
| `P4-cortex/scripts/generate_kanban_html.py` | Fixed f-string brace escaping bug — titles with `{` `}` characters now render correctly in static HTML export | `P4-cortex/scripts/` |
| `skills/kanban-dashboard/SKILL.md` | Updated with new layout, SSE/real-time, drag-drop, mobile features | `skills/kanban-dashboard/` |

#### Architecture

```
kanban_create(title, body, board, priority)
    ↓
dispatch_once_content.py / dispatch_once_default.py
    → claims task → spawns worker subprocess → returns immediately
        ↓
    run_kanban_worker.py
        → reads KANBAN_TASK_ID from env
        → _load_worker_config() reads config.yaml for model/provider
        → AIAgent(model, provider="minimax", ...)
        → sends heartbeat every 60s
        → kanban_complete(task_id) or kanban_fail(task_id, error)
```

#### Kanban Dashboard UI (2026-05-31)

| Feature | Description |
|---------|-------------|
| **Board tabs** | All / default / content / integrations — tab navigation |
| **5-column layout** | To Do / Ready / In Progress / Blocked / Completed in one row |
| **SSE real-time** | `/kanban/api/stream` SSE endpoint — board actions (complete, claim, block, create, delete) trigger immediate page refresh |
| **Drag-and-drop** | Drag card to another column → calls `POST /kanban/api/update_status` |
| **Mobile responsive** | `viewport` meta, touch scrolling, narrower columns on small screens |
| **SSE status indicator** | Green dot = connected, auto-reconnect on disconnect |

#### Kanban tools (11 total + multi-action entry)

| Tool | Description |
|------|-------------|
| `kanban_list` | List tasks by board and status |
| `kanban_create` | Create new task |
| `kanban_update` | Update task fields |
| `kanban_delete` | Delete task |
| `kanban_claim` | Claim/assign task to worker |
| `kanban_complete` | Mark task completed |
| `kanban_fail` | Mark task failed |
| `kanban_reclaim_stale` | Reclaim stale in-progress tasks |
| `kanban_archive` | Archive task |
| `kanban_get` | Get single task details |
| `kanban_board_list` | List all boards |

Multi-action entry: `kanban` — dispatches to individual tools by action field.

#### Known providers (third-party Anthropic-compatible)

When `provider=minimax` (or minimax-cn, alibaba, deepseek), AIAgent now automatically resolves:
- `api_mode=anthropic_messages` (when base_url contains `/anthropic`)
- `base_url` from `PROVIDER_REGISTRY[provider].inference_base_url`
- `api_key` via `resolve_api_key_provider_credentials(provider)` → env var

#### Key fix: `determine_api_mode` URL heuristic ordering

Before: URL heuristic checked **after** provider transport lookup → MiniMax's `/anthropic/v1/messages` endpoint incorrectly classified as `openai` mode because MiniMax provider maps to OpenAI transport first.

After: URL heuristic checked **before** provider transport lookup → endpoint with `/anthropic` in path correctly gets `anthropic_messages` mode.

#### Key fix: AIAgent init for third-party providers

Before: `effective_key` and `_anthropic_api_key` were set from unresolved `api_key` before the third-party provider credential resolution block ran.

After: Credential resolution block updates `api_key` variable; then `effective_key = api_key` and `self._anthropic_api_key = effective_key` are set **after** the resolution, ensuring the resolved credential is used.

#### Test result (2026-05-30)

```
kanban_create(title='[test] Final minimax fix', body='Run: echo minimax-final')
    → {task_id: "t_279a401c9e92", status: "ready"}

dispatch_once_default.py
    → reclaimed=0, claimed=1, spawned=1
    → Worker: AIAgent(minimax-m2.7) → terminal tool → echo minimax-final
    → API call #1: 9.73s, tool output: "minimax-final"
    → API call #2: 2.04s, cache 100% hit
    → kanban_complete() → status: "completed"
```

---

## [0.7.2] — 2026-05-13

### Brain Upgrade — P0-Brainstem Enforcement Layer (Event-Driven)

#### What changed

signal_processor.py handlers implemented — P0-brainstem rules now enforced via event-driven signal flow, not just static rules.

#### Why

`_on_turn_start`, `_on_turn_end`, `_on_agent_complete` were `pass` (empty). No P0 rule tracking. Workflow incomplete detection broken by Python None attribute trap.

#### Files changed

| File | Change | Location |
|------|--------|----------|
| `agent/signal_processor.py` | 5 new handlers + state fields | lines 447-448, 1174-1265, 1416-1458, 1509-1660 |
| `P3-sensors/gateway/drewgent-architecture-dataflow.md` | NEW — 28KB end-to-end data flow document | P3-sensors/gateway |
| `P2-hippocampus/memories/insights/.archive/brain-signal-system-20260513.md` | NEW — detailed P0 enforcement docs | archive |
| `P5-ego/SELF_MODEL.md` | Added "P0-Brainstem Enforcement" section | P5-ego layer |
| `P2-hippocampus/memories/insights/2026-05.md` | Updated with 2026-05-13 work log | P2-hippocampus |

#### Event flow (new handlers)

```
turn.start
  └→ _on_turn_start() → dangerous.op → _on_dangerous_op()
        └→ _dangerous_ops_history[] + awareness.integrity (high severity)

turn.end
  └→ _on_turn_end() → rule.violation → _on_rule_violation()
        └→ _violation_history[] + awareness.integrity

agent.complete
  └→ _on_agent_complete()
        ├→ workflow.incomplete → _on_workflow_incomplete → _workflow_history archive
        └→ session.violations (by-rule summary)
```

#### Bug fixed

`wf.started_at.isoformat() if hasattr(wf, "started_at") else None` — hasattr returns True when attr exists but value is None → AttributeError → silent catch → emit skipped → workflow_history empty forever.

Fix: `wf.started_at.isoformat() if getattr(wf, "started_at", None) else None`

---

## [0.7.1] — 2026-05-12

### Brain Upgrade — Karpathy Coding Principles

#### What changed

Drewgent's brain now enforces **Andrej Karpathy's 4 coding principles** at the P0 brainstem level — the highest priority layer, overriding all other rules.

#### Why

Drewgent was repeating common LLM coding mistakes: wrong assumptions as facts, overcomplicated code, surgical violations, and no verifiable success criteria. The brain needed enforcement teeth at the P0 level to catch these before they become user-visible bugs.

#### Files changed

| File | Change | Location |
|------|--------|----------|
| `~/.drewgent/SOUL.md` | Rewritten with Karpathy 4 principles (primary identity) | Drewgent home |
| `~/.drewgent/P1-limbic/persona/SOUL.md` | Same content (P1 fallback) | P1-limbic layer |
| `~/.drewgent/AGENTS.md` | Created from writing-style-guide.md + expanded with coding guidelines | Drewgent home project context |
| `~/.drewgent/brain/Drewgent-brain/P0-brainstem/禁karpathy_coding_principles.neuron` | **NEW** — P0 brainstem enforcement rule | Brain filesystem |

#### Cross-reference chain (organic brain system)

```
SOUL.md     → links: [P0-brainstem/禁, P1-limbic/persona/writing-style-guide.md]
AGENTS.md   → links: [SOUL.md, P0-brainstem/禁]
Neuron      → P0-brainstem/禁karpathy_coding_principles.neuron (located in P0-brainstem)
System prompt layers:
  Layer 1: load_soul_md()        → SOUL.md
  Layer 3: brain_load()          → P0-brainstem neurons (including neuron above)
  Layer 7: build_context_files_prompt() → AGENTS.md

Result: SOUL.md ↔ P0-brainstem ↔ AGENTS.md — circular organic reference chain
```

#### Verification (2026-05-12)

```
Active brain: Drewgent-brain
P0-brainstem neurons: 10 (禁karpathy_coding_principles included ✅)
brain_load(): returns brain content with neuron ✅
_load_agents_md(drew_home): returns AGENTS.md with Karpathy principles ✅
load_soul_md(): returns SOUL.md with 4 principles ✅
```

#### The 4 Karpathy Principles

1. **Think Before Coding** — State assumptions explicitly. Ask when uncertain. Stop when confused.
2. **Simplicity First** — Minimum code that solves the problem. Nothing speculative.
3. **Surgical Changes** — Touch only what you must. Don't refactor adjacent code.
4. **Goal-Driven Execution** — Define success criteria. Write tests first. Loop until verified.

#### Enforcement mechanism

```
User asks "fix the bug"
    → Agent must write test that reproduces it first
    → Then make it pass

User asks "add validation"
    → Agent must write tests for invalid inputs
    → Then make them pass

Multi-step task
    → State plan: "1. [step] → verify: [check]"
    → Each step verifiable independently
```

#### Brain scan verification

```
Active brain: Drewgent-brain
P0-brainstem neurons: 10 total
  - 禁tool_integration_3file
  - 禁rm_rf_root
  - 禁blind_write
  - 禁task_qa_gate
  - 禁secrets_in_code
  - 禁auto_validate
  - 禁console_log
  - 禁karpathy_coding_principles ✨ NEW
  - 禁subagent_verify
  - 禁filesystem_truth
```

#### Related components (unchanged, verified working)

- `agent/prompt_builder.py` — SOUL.md loading (primary: ~/.drewgent/SOUL.md, fallback: P1-limbic/persona/)
- `agent/prompt_builder.py` — AGENTS.md loading via `_load_agents_md(drew_home)`
- `drewgent_cli/brain_manager.py` — scan_brain/emit_brain for neuron filesystem
- `docs/DREWGENT_ARCHITECTURE.md` — brain system documentation (Version 1.0, 2026-04-15)

---

## [0.7.0] — 2026-04-03

## [0.7.x] — 2026-06-20

### SEO Service QA Gate Guide

#### What changed
- Created `P4-cortex/growth/seo/seo-service/qa-gate.md` — project-specific QA gate guide
- Documents 禁task_qa_gate + 禁subagent_verify 적용법 for SEO Service
- 3-tier pipeline templates (Tier 1-3) matching AGENTS.md Tiered Autonomy
- Hard gate rules (6 rules), common failure modes (6 modes), phase-specific notes
- Written by documentation agent, triggered by user request

### Initial release with NeuronFS brain governance

- 7-layer subsumption (P0-P6)
- Brain filesystem with `.neuron` files
- `禁` (forbidden) micro-opcode pattern
- `vorq` (value-or-lookup) harness for unknown governance tokens
- Discord gateway integration
- Skill/agent architecture
---
title: Drewgent Self-Model
type: document
space: concept
tags: [concept]
created: 2026-05-12
updated: 2026-05-20
links:
  - "[[@identity/_agent/COLLAB/ENGINE_USAGE]]"
  - "[[@identity/brain/Drewgent-brain/P0-brainstem/禁/禁brain_obsidian_graph.neuron]]"
  - "[[@identity/brain/Drewgent-brain/P0-brainstem/禁/禁kanban_hallucination.neuron]]"
  - "[[@identity/brain/Drewgent-brain/P0-brainstem/禁/禁kanban_worker_accountability.neuron]]"
  - "[[@identity/brain/Drewgent-brain/P0-brainstem/禁/禁task_qa_gate.neuron]]"
  - "[[@identity/brain/rules]]"
  - "[[@identity/persona/SOUL]]"
  - "[[@identity/persona/writing-style-guide]]"
  - "[[@memory/memories/SCHEMA]]"
  - "[[@action/gateway/drewgent-architecture-dataflow]]"
  - "[[@action/gateway/platforms/ADDING_A_PLATFORM]]"
  - "[[@action/resolver/RESOLVER.md]]"
  - "[[@action/skills/SKILL-INDEX]]"
  - "[[@memory/growth/INTEGRATION_PROTOCOL]]"
  - "[[@memory/knowledge/NEURONFS_RULES]]"
  - "[[@memory/knowledge/garry-tan-unified-architecture-drewgent-review]]"
  - "[[@memory/knowledge/laws-of-ux-wiki/index]]"
  - "[[@memory/knowledge/obsidian-vault-site-principle]]"
  - "[[@memory/plans/gateway_decomposition_plan]]"
  - "[[@memory/plans/stabilization_report]]"
  - "[[@memory/growth/harness-autonomous-behaviors]]"
  - "[[@memory/growth/brain-signal-post-processing-20260531]]"
  - "[[@memory/memories/index]]"
  - "[[@memory/memories/MEMORY_wiki]]"
---


# Drewgent Self-Model (P5-Ego)

에이전트가 자기 자신의 구조를 인식하기 위한 지식 베이스.
이 문서는 에이전트가 외부 기능을 자기 안에 녹일 때 참조하는 내부 모델이다.

## 뇌 구조 (7-Layer Subsumption)

```
P0-brainstem   — CRITICAL: 절대적 규칙 (생존, 안전, 금지 규칙)
P1-limbic      — 가치, 성격, 톤 (persona/SOUL.md, writing-style-guide.md)
P2-hippocampus — 메모리 패턴, 문맥 경계 (session, context)
P3-sensors     — 입력 감지 (gateway, tools, skills, hooks)
P4-cortex      — 성장, 학습, 패턴 인식 (growth/, trends/)
P5-ego         — 자아: 자기 인식, 통합 의사결정 ← 이 파일
P6-prefrontal  — 전략적 사고 (planning, long-term goals)
```

## 핵심 원칙

1. **P0은Override了一切** — brainstem 규칙은 어떤 상위 레이어보다 우선
2. **정보는 아래→위** — P3가 감지한 것 → P2에 저장 → P4가 성장
3. **자아는 위→아래** — P5가 "나는 이것이다"라고 정의하면 P3/P4는 그것에 맞춰 작동
4. **통합은 3단계** — 감지(P3) → 평가(P4) → 흡수(P5+P0)

## 하네스의 자동 작용 영역 (Harness Autonomous Behaviors)

하네스가 **특정 패턴에서 스스로 판단해서 작동**하는 영역:

| 패턴 | 동작 | 구현 위치 |
|------|------|----------|
| cron tick (1분) | `dispatch_once()` 실행 → ready task spawn | scheduler.py |
| TTL 만료 | `_reclaim_stale_tasks()` → worker reclaim | drewgent_kanban_db.py |
| kanban_complete | created_cards hallucination check | task_complete() |
| task_link | cycle detection | task_link() |
| integration workflow 시작 | task 자동 생성 | signal_processor |
| cron job failure | retry → fallback delivery | self-healing protocol |
| turn.end | dangerous ops 감지 → event emit | signal_processor |
| ACP first exchange 완료 | 세션 제목 자동 생성 | acp_adapter/server.py → title_generator |

| jobs.json cron expression (SEO/Trend/kanban-maintenance/cron-output-cleanup) | load_jobs() + get_due_jobs() + due compute | 별도 process (gateway 내부?) | in-memory state 기반, patch 안 먹음 (incident 6/1) |
**주의**: 이 자동 작용들은 에이전트가 명시적으로 요청하지 않아도 event-driven으로 작동한다.
"kanban을 써야겠다"는 판단 자체는 내재화되지 않았으므로 에이전트가 스스로 판단할 수 있는건 이 자동作用域 안에 한정된다.

## 외부 기능 통합 프로토콜

외부 도구나 스킬을 추가할 때 반드시 거치는 표준 절차:

### 1단계: 파일 생성 (P3 — sensors)
```
도구 추가:
  tools/<name>_tool.py          ← 핸들러 + registry.register()
  model_tools.py (_discover_tools) ← import 추가
  toolsets.py                   ← toolset 배정

스킬 추가:
  ~/.drewgent/skills/<name>/   ← SKILL.md + references/ + scripts/
  agent/skill_commands.py       ← 로딩 로직
```

### 2단계: 의도 인식 (P4 — cortex)
```
도구를 왜 추가하는가? (문맥 분석)
스킬이 어떤 성장 패턴을 지원하는가?
integratoin 완료 후 에이전트 행동이 어떻게 달라지는가?
```

### 3단계: 흡수 (P5 — ego + P0 — brainstem)
```
P5: "이 도구/스킬은 Drewgent의 identity에 어떻게 통합되는가?"
P0: "이 통합이 안전하고 Rewgent의 operating principles에 부합하는가?"
완료 → P2에_session 기록 → P4에_pattern归档
```

## 도구 통합 상태 추적 (ArchitectureModel)

`agent/signal_processor.py`의 `ArchitectureModel`이 실시간으로 관리:

```python
TOOL_INTEGRATION_FILES = [
    "tools/",
    "model_tools.py",
    "toolsets.py",
]

SKILL_INTEGRATION_FILES = [
    "skills/",
    "agent/skill_commands.py",
]
```

## P0-Brainstem Enforcement — Event-Driven Signal Flow

`signal_processor.py`의 handlers가 event bus를 통해 P0 규칙을 enforcement함:

```
turn.start event
  └→ _on_turn_start() → dangerous.op event
        └→ _on_dangerous_op() → _dangerous_ops_history 기록
              └→ severity=high: awareness.integrity event

turn.end event
  └→ _on_turn_end() → rule.violation event
        └→ _on_rule_violation() → _violation_history 기록
              └→ awareness.integrity event

agent.complete event
  └→ _on_agent_complete()
        ├→ incomplete workflow: workflow.incomplete → _on_workflow_incomplete → _workflow_history archive
        └→ accumulated violations: session.violations event
```

**Tracking state** (in SignalProcessor):
- `_violation_history: List[dict]` — rule.violation events across session
- `_dangerous_ops_history: List[dict]` — dangerous.op events across session

**Python None trap fix** (2026-05-13):
`wf.started_at.isoformat() if hasattr(wf, "started_at") else None` → silent AttributeError
→ Fix: `wf.started_at.isoformat() if getattr(wf, "started_at", None) else None`

## Integration Workflow States

```
detected → started → [step_1, step_2, ...] → completed
           ↓
        (P4가 다음 힌트를 제공)
```

## Kanban — Drewgent's Task Queue (Brain-Integrated)

Drewgent의 kanban 시스템은 brain structure(P0~P6) 안에 완전히 녹아들어 있다.

### 상태 저장소 (P2-hippocampus)

```
~/.drewgent/P2-hippocampus/kanban/
├── state/drewgent_tasks.db   ← SQLite canonical store (tasks, task_links, task_events, task_runs, boards, kanban_notify_subs)
├── events/                    ← archived JSONL events
├── sessions/                  ← worker session logs
└── KANBAN_INDEX.md           ← this layer's index
```

### Brain Signal Events (P3 → event_bus → signal_processor → awareness)

| Event | Source | Handler |
|-------|--------|---------|
| `kanban.task.created` | `task_create()` | `_on_kanban_task_created()` → awareness.kanban |
| `kanban.task.completed` | `task_complete()` | `_on_kanban_task_completed()` → awareness.kanban |
| `kanban.task.blocked` | `task_block()` | `_on_kanban_task_blocked()` → awareness.kanban |
| `kanban.worker.reclaimed` | `_reclaim_stale_tasks()` | `_on_kanban_worker_reclaimed()` → awareness.integrity |
| `kanban.hallucination_blocked` | `task_complete()` | `_on_kanban_hallucination()` → awareness.integrity |

### P0 Brainstem Kanban Rules

- `禁kanban_hallucination` — `created_cards`의 task ID는 반드시 DB 검증 필요. 가짜 ID로 completion 시도 → 차단
- `禁kanban_worker_accountability` — worker는 TTL 내 heartbeat 필수. TTL 만료 → automatic reclaim + awareness.integrity

### Integration Workflow ↔ Kanban (Bidirectional)

```
integration workflow 시작
  → create_integration_workflow_task() ✅
  → kanban.task.created event ✅

task 완료 (kanban_complete)
  → kanban.task.completed event ✅
  → integration workflow completed 트리거 (TODO)

task 차단 (task_block)
  → kanban.task.blocked event ✅
  → integration workflow blocked 트리거 (TODO)
```

### 도구 (Tools)

10개 agent tool이 `drewgent_kanban_db.py`에 구현됨:
`kanban_create`, `kanban_complete`, `kanban_block`, `kanban_unblock`, `kanban_claim`, `kanban_heartbeat`, `kanban_list`, `kanban_get`, `kanban_link`, `kanban_add_comment`

스킬: `kanban-worker`, `kanban-orchestrator`, `kanban-dashboard`

Cron dispatcher: 3개 board-scoped dispatcher가 `jobs.json`에 등록됨 (1분마다)
- `kanban-dispatcher-default` — `~/.drewgent/scripts/dispatch_once_default.py`
- `kanban-dispatcher-content` — `~/.drewgent/scripts/dispatch_once_content.py`
- `kanban-dispatcher-integrations` — `~/.drewgent/scripts/dispatch_once_integrations.py`

각 dispatcher는 `Popen`으로 worker spawn 시 `KANBAN_WORKER_MODE=1` env flag 주입.
worker는 LLM 호출 없이 직접 sqlite3 read/write (결정론적). stdout/stderr는 `~/.drewgent/P4-cortex/scripts/kanban/logs/workers/{task_id}.log`로 redirect (pipe deadlock 회피).

**Board scope (2026-06-01 추가, v0.8.5)**: 각 dispatcher는 **자기 board의 in_progress만** 본다 (Phase 0/1 SQL에 `AND board = "self_board"`). cross-board race 차단 — 한 dispatcher가 다른 board의 dead worker를 reclaim해버리는 사고 방지. content는 legacy 호환: `board = "content" OR board = "" OR board IS NULL`.

**Worker → DB handoff**:
- heartbeat: dispatcher가 매 tick마다 `_reclaim_stale_tasks()`로 TTL 만료 task reclaim
- watchdog (2026-06-01 추가): Phase 0에서 `os.kill(pid, 0)`으로 worker 생존 확인, dead worker 즉시 reclaim

### P-Layer Integration Status

| Layer | Status |
|-------|--------|
| P0-brainstem | ✅ 禁kanban_hallucination, 禁kanban_worker_accountability |
| P1-limbic | TODO — kanban task description writing style |
| P2-hippocampus | ✅ state/events/sessions directory structure |
| P3-sensors | ✅ tools + skills + cron + brain signals |
| P4-cortex | Partial — implementation plan exists, patterns not archived |
| P5-ego | ✅ SELF_MODEL integration (this section) |
| P6-prefrontal | TODO — plans/incidents templates |

## 절대 규칙 (P0 brainstem)

- `禁rm_rf_root` — rootdir 삭제 금지
- `禁blind_write` — 파일 읽기 없이 쓰기 금지
- `禁task_qa_gate` — 작업 완료 시 QA 검증 필수
- `禁secrets_in_code` — API 키/토큰을 코드에 하드코딩 금지
- `禁auto_validate` — 위험한 명령 자동 검증 금지
- `禁console_log` — production에서 console.log 사용 금지
- `禁subagent_verify` — subagent 출력 검증 없이 수락 금지
- `禁filesystem_truth` — 외부 도구 대신 직접 파일 읽기 우선
- `禁kanban_hallucination` — 가짜 task ID로 kanban_complete 차단 (P0-brainstem/禁/禁kanban_hallucination.neuron)
- `禁kanban_worker_accountability` — worker TTL/heartbeat enforcement (P0-brainstem/禁/禁kanban_worker_accountability.neuron)

## Related Documentation

### Core Identity
- [[@identity/persona/SOUL]] — P1-Limbic identity and voice (who Drewgent is)
- [[@identity/persona/writing-style-guide]] — Korean writing style guide for blog content (Drewgent P1-limbic tone)

### Architecture & Data Flow
- [[@action/gateway/drewgent-architecture-dataflow]] — **End-to-end data flow**: full message lifecycle (Platform → Gateway → AIAgent → Platform), session/memory flow, file reference table with line numbers
- [[@action/skills/SKILL-INDEX]] — Skill category index with 28 DESCRIPTION.md references
- [[@action/resolver/RESOLVER.md]] — Context routing table (on-demand document loading)

### Brain & Governance
- [[@identity/brain/rules]] — P0 Brainstem absolute rules (禁 rules, Karpathy principles)
- [[@memory/knowledge/NEURONFS_RULES]] — NeuronFS file system architecture rules

### Growth & Integration
- [[@memory/growth/INTEGRATION_PROTOCOL]] — Tool/Skill absorption protocol (P5-Ego integration procedure)
- [[@memory/plans/gateway_decomposition_plan]] — GatewayRunner decomposition into isolated components
- [[@memory/plans/stabilization_report]] — Drewgent runtime stabilization report (P0-brainstem import fix, launchd label fix)

### Content & Automation
- [[@memory/knowledge/laws-of-ux-wiki/index]] — Laws of UX knowledge wiki (external-link content, graph excluded)

### Planning & Memory
- [[@action/plans/growth-2026]] — Drewgent growth plan 2026 (skills, memory, automation goals)
- [[@action/migrations/drewgent-root-consolidation-20260506]] — 2026-05-06 root consolidation migration (canonical runtime, quarantine)
- [[@memory/memories/SCHEMA]] — Wiki schema conventions (tags, wikilinks, entity/concept/insight structure)
- [[memories/SCHEMA]] — memories/ schema (mirrors P2-hippocampus/memories/SCHEMA)

## 자기 인식 체크리스트 (새 통합 시)

에이전트가 도구/스킬을 추가할 때 스스로에게 물어볼 것:

1. 이 도구/스킬이 P0 brainstem 규칙을 위반하는가?
2. 3개 파일 모두 수정했는가? (도구의 경우)
3. registry.register() 패턴을 따랐는가?
4. toolset이 적절하게 배정되었는가?
5. IntegrationWorkflow가 추적하고 있는가?
6. P4-cortex growth에 패턴이归档되었는가?
7. QA 검증이 완료되었는가?

## Related
- [[@identity/_agent/COLLAB/ENGINE_USAGE]]
- [[@action/gateway/platforms/ADDING_A_PLATFORM]]
- [[@memory/knowledge/obsidian-vault-site-principle]]
- [[@memory/knowledge/garry-tan-unified-architecture-drewgent-review]]

## Links
- [[@identity/brain/Drewgent-brain/P0-brainstem/禁/禁brain_obsidian_graph.neuron]]
- [[@identity/brain/Drewgent-brain/P0-brainstem/禁/禁kanban_hallucination.neuron]]
- [[@identity/brain/Drewgent-brain/P0-brainstem/禁/禁kanban_worker_accountability.neuron]]
- [[@identity/brain/Drewgent-brain/P0-brainstem/禁/禁task_qa_gate.neuron]]
- [[@memory/growth/harness-autonomous-behaviors]]
- [[@memory/growth/brain-signal-post-processing-20260531]]

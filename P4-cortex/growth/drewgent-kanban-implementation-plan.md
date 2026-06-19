---
title: Drewgent Kanban Implementation Plan
type: document
space: growth
tags: [growth, projects]
created: 2026-05-18
updated: 2026-05-20
aliases:
  - /projects/drewgent-kanban
links:
  - "[[P0-brainstem/brain/rules]]"
  - "[[P3-sensors/gateway/drewgent-architecture-dataflow]]"
  - "[[P4-cortex/growth/INTEGRATION_PROTOCOL]]"
  - "[[P4-cortex/growth/KANBAN-USER-GUIDE]]"
  - "[[P5-ego/SELF_MODEL]]"
---


# Drewgent Kanban Implementation Plan

Hermes Agent kanban 분석 (2026-05-18) 결과 기반.
Drewgent의 existing infrastructure를 최대한 활용하여 kanban functionality를 layer.

## 목표

Drewgent에 persistent task queue + dependency tracking + hallucination detection 추가.
Hermes kanban의 핵심价值 proposition을 Drewgent 아키텍처에 맞게 포팅.

---

## Phase 1 — Core Task Store (MVP)

**목표**: Drewgent에 SQLite-backed persistent task store + agent task tools

### 1.1 DrewgentTaskStore (`~/.drewgent/state/drewgent_tasks.db`)

Drewgent의 existing session store 패턴 (`~/.drewgent/sessions/*.db`)을 따라감.
단일 `drewgent_tasks.db`로 시작 (multi-board는 Phase 2).

```
~/.drewgent/state/drewgent_tasks.db

tasks table:
  id, title, body, assignee, status, priority,
  created_by, created_at, started_at, completed_at,
  workspace_kind, workspace_path, claim_lock, claim_expires,
  result, consecutive_failures, last_failure_error,
  worker_pid, max_runtime_seconds, last_heartbeat_at,
  idempotency_key, skills, max_retries, tenant

task_links: parent_id, child_id (PRIMARY KEY)

task_events: task_id, run_id, kind, payload, created_at

task_comments: task_id, author, body, created_at

task_runs: task_id, profile, status, claim_lock, claim_expires,
           worker_pid, started_at, ended_at, outcome, summary, metadata, error
```

**Drewgent specific extensions**:
- `integration_workflow_id` (TEXT): 이 task가 속한 integration workflow 추적
- `trigger_source` (TEXT): 'activity_logger' | 'cron' | 'manual' | 'subagent'
- `parent_session_id` (TEXT): 이 task를 생성한 Drewgent session

### 1.2 Task Tools (agent skill)

`kanban` toolset을 Drewgent agent에 추가:

```
kanban_create(title, body?, assignee?, workspace_kind?,
              priority?, parents?, idempotency_key?, skills?,
              max_runtime_seconds?, trigger_source?)
  → task_id (status = ready if no undone parents, else todo)

kanban_complete(task_id, result?, summary?, metadata?,
               created_cards?, expected_run_id?)
  → bool (+ hallucination detection)

kanban_block(task_id, reason?)
kanban_unblock(task_id)
kanban_claim(task_id, ttl_seconds?)
kanban_heartbeat(task_id, note?)
kanban_list(status?, assignee?)
kanban_get(task_id)
kanban_link(parent_id, child_id)
kanban_add_comment(task_id, author, body)
```

**Worker ownership enforcement**: worker env (`KANBAN_TASK_ID`)이 없으면 task를 mutate할 수 없음.

### 1.3 Integration Workflow → Task Store Hook

기존 `integration_workflow.py`의 workflow state를 task store로 연결:

```python
# Integration workflow가 task를 생성할 때:
task_id = kanban_create(
    title=f"[{wf.name}] {step.description}",
    body=step.spec,
    assignee=wf.config.get("default_assignee"),
    parents=[parent_task_ids],
    trigger_source="subagent",
    integration_workflow_id=wf.id,
)

# Workflow 완료 시:
kanban_complete(task_id, result=result, summary=summary,
                metadata={"changed_files": [...], "workflow_id": wf.id})
```

### 1.4 Dispatcher Cron Job (60초 tick)

`hermes kanban daemon`과 달리 Drewgent는 gateway가 아니라 cron-based.
Drewgent cron에 kanban dispatcher job 추가:

```
~/.drewgent/cron/jobs.py
  - name: kanban-dispatcher
    schedule: "*/1 * * * *"  # 1분마다
    enabled: true
    board: default
    max_spawn: 3  # Drewgent는 gateway가 아니라서 concurrency 낮게
    failure_limit: 3
```

**DrewgentTaskStore와 다른 점**: Gateway embedded dispatcher가 아니라 cron-based.
Drewgent의 gateway는 Discord/Telegram messaging hub이지 kanban dispatcher가 아님.
그래서 cron job으로 별도 실행.

---

## Phase 2 — Dependency + Hallucination + Multi-board

### 2.1 Hallucination Detection (Hermes kanban 핵심 기능)

Hermes의 `created_cards` verification을 Drewgent에 포팅:

```
kanban_complete(task_id, created_cards=["t_abc123", "t_def456"])

→ 각 id가 DB에 존재하는지 검증
→ 각 id의 created_by가 호출자의 profile인지 검증
→ 가짜 id면 completion_blocked_hallucination event 발생 + 예외
→ prose scan: summary/result에서 t_<hex> 패턴 추출 → 미해결 ref 기록
```

**Drewgent 특화**: created_by를 Drewgent session_id 또는 profile로 매핑.

### 2.2 Parent-Child Dependency + Promotion

Hermes의 `link_tasks` + `recompute_ready` 포팅:

```
kanban_link(parent_id, child_id)
  → cycle detection (DFS)
  → child가 ready인데 parent가 done이 아니면 child: ready → todo
  → recompute_ready()가 다음 dispatcher tick에서 promotion

Task dependencies expose to upstream:
  parent_results(task_id) → [(parent_id, result), ...]
  Worker가 다음 단계 parent 결과를 읽어서 handoff
```

### 2.3 Multi-board Support

Hermes의 board slug 패턴 도입:

```
~/.drewgent/kanban/
  boards/
    default/      # 기본 보드 (tasks.db)
    content/      # Content pipeline 전용 보드
    integrations/ # Integration workflow 보드
  current         # 현재 선택된 보드
```

Activity Logger → content board에 card 생성.
Integration workflow tracker → integrations board에 card 생성.

### 2.4 Activity Logger → Kanban Card Creation

```
# Activity Logger가 Discord conversation 분석 후:

# 기존 (단순 draft 생성):
draft = create_draft(title, content, channel_id)

# 개선 (kanban card + draft):
task_id = kanban_create(
    title=f"[draft] {title}",
    body=content,
    assignee="drewgent",  # Drewgent agent가 처리
    trigger_source="activity_logger",
    idempotency_key=f"activity:{message_id}",
    parent=parent_task_id  # conversation thread linking
)

# Board notification:
# 사용자가 @Drewgent approve 하면 → kanban_complete(task_id)
# 사용자가 @Drewgent revise 하면 → kanban_block(task_id, reason)
```

---

## Phase 3 — Dashboard + Notifications

### 3.1 FastAPI Dashboard (optional)

Hermes dashboard (`/api/plugins/kanban/`)는 있지만, Drewgent는 n8n이 이미 있음.
n8n workflow로 kanban board 렌더링:

```
kanban-dashboard workflow:
  - Trigger: DrewgentTasks DB poll (30초마다)
  - Node: kanban_board_UI (HTML generation)
  - Delivery: Discord embed with reaction buttons
    - ✅ → kanban_complete
    - 🔄 → kanban_unblock
    - ❌ → kanban_block
```

### 3.2 Gateway Notifier (Hermes kanban_notify_subs 포팅)

Hermes의 `kanban_notify_subs` table을 Drewgent gateway에 포팅:
completed/blocked/crashed events → original Discord/Telegram subscriber에게 push.

```
Drewgent Gateway already has platform adapters:
  - Discord: send message to original channel
  - Telegram: send message to original chat_id
  - Slack: webhook delivery

→ task_events table의 completed event tail
→ subscription: task_id + platform + chat_id + thread_id
```

---

## Implementation Status (2026-05-19)

### Completed

| Item | Status | Notes |
|------|--------|-------|
| drewgent_kanban_db.py | ✅ Done | SQLite store, all core functions |
| kanban_tools.py | ✅ Done | 457 lines, spawn_worker, 10 tools |
| kanban-worker skill | ✅ Done | SKILL.md + references/ |
| cron dispatcher job | ✅ Done | `*/1 * * * *`, d1ef68ced116, 858 runs |
| Hallucination detection | ✅ Done | created_cards DB verify + prose scan |
| Parent-child promotion | ✅ Done | _recompute_ready_for_children() |
| task_link demotion | ✅ Done | Bug fix: child demoted to 'todo' if parent not done |
| task_unblock → ready | ✅ Done | Bug fix: blocked → unblock → 'ready' (not 'todo') |
| kanban-orchestrator skill | ✅ Done | Phase 2 skill, decompose + link |
| kanban-dashboard skill | ✅ Done | SKILL.md with board embed format + reaction workflow |
| kanban-notify hook | ✅ Done | hooks/kanban-notify/ + gateway startup adapter delivery |
| gateway:startup adapters+loop | ✅ Done | gateway/run.py passes adapters+loop to hook context |

### REMOVED (2026-05-20 — Linear 의존성 제거)

| Item | Status | Notes |
|------|--------|-------|
| linear_kanban_tools.py | ❌ Removed | 698 lines, Linear bridge (불필요) |
| linear-activity-logger cron | ❌ Paused | 5분마다 Discord→Linear sync (사용 안함) |
| linear-activity-logger skill | ❌ Removed | skills/linear-activity-logger/ 디렉토리 삭제 |
| drewgent-content-pipeline-v1.md | ❌ Removed | Linear content pipeline 문서 삭제 |
| Gateway Linear webhook | ⚪ Disabled | Linear webhook route in gateway (future use) |

### Phase 2 Completed

| Item | Status | Notes |
|------|--------|-------|
| Multi-board support | ✅ Done | board column + boards table + task_list(board=) filtering |
| Integration workflow hook | ✅ Done | create_integration_workflow_task() + complete_integration_workflow_task() already wired to signal_processor |
| Cycle detection in task_link | ✅ Done | DFS cycle detection in task_link() |

### Phase 3 — Dashboard + Notifications (Completed)

| Item | Status | Notes |
|------|--------|-------|
| n8n dashboard workflow | ✅ Done | SKILL.md + references/n8n-protocol.md created |
| kanban-dashboard skill | ✅ Done | SKILL.md with board embed format + reaction workflow |
| Gateway notifier | ✅ Done | kanban_notify_subs table + notify_*() functions + notify_task_event() in task_block/unblock/complete |
| FastAPI dashboard | ❌ TODO | Optional alternative to n8n |

---

## File Structure (Updated 2026-05-19)

```
~/.drewgent/
  state/
    drewgent_tasks.db      # SQLite task store (Phase 1)
  skills/
    kanban-worker/         # Worker skill (Phase 1) ✅
      SKILL.md
      references/
        protocol.md
    kanban-orchestrator/   # Orchestrator skill (Phase 2) ✅
      SKILL.md
      references/
        protocol.md
    kanban-dashboard/      # Dashboard skill (Phase 3) ✅
      SKILL.md
      references/
        n8n-protocol.md
  cron/
    jobs.json             # kanban-dispatcher job ✅
  tools/
    kanban_tools.py        # Tool wrappers (Phase 1) ✅
    drewgent_kanban_db.py  # Core DB (Phase 1) ✅
  source/drewgent-agent/
    tools/
      model_tools.py       # kanban_tools imported ✅
      toolsets.py           # "kanban" toolset registered ✅
```

---

## 우선순위 Implementation Order (Updated 2026-05-19)

### Completed ✅

- Week 1 items 1-3: Phase 1 core ✅
- Week 2 item 4-5: dispatcher + integration hook planning ✅
- Week 3-4 items 6-7: Hallucination detection + parent-child promotion ✅

### In Progress ⏳

- Multi-board support
- Activity Logger → Kanban integration
- Integration workflow → task store hook

### Remaining ❌

- Cycle detection in task_link
- n8n dashboard workflow
- kanban-dashboard skill
- Gateway notifier
- FastAPI dashboard (optional)

---

## Related

- [[P3-sensors/gateway/drewgent-architecture-dataflow]]
- [[P4-cortex/growth/INTEGRATION_PROTOCOL]]
- [[P5-ego/SELF_MODEL]]

## Links
- [[P0-brainstem/brain/rules]]
- [[P4-cortex/growth/KANBAN-USER-GUIDE]]

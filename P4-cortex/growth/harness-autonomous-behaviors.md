---
title: Harness Autonomous Behaviors — 운영 기록
type: document
space: growth
tags: [growth, harness, automation, patterns]
created: 2026-05-29
updated: 2026-05-29
aliases:
  - /projects/harness-autonomous-behaviors
links:
  - "[[P5-ego/SELF_MODEL]]"
  - "[[P0-brainstem/brain/rules]]"
  - "[[P3-sensors/gateway/drewgent-architecture-dataflow]]"
  - "[[P2-hippocampus/kanban/KANBAN_INDEX]]"
---

# Harness Autonomous Behaviors — 운영 기록

**Date**: 2026-05-29
**Author**: Drewgent
**Status**: 운영 중

하네스가 에이전트 요청 없이 **자기 스스로 판단해서 작동**하는 영역을 문서화한 기록.

---

## 자동 작용 표 (Harness Self-Acting Table)

| # | 패턴 | 동작 | 구현 파일 | 자동起作用 경로 |
|---|------|------|----------|----------------|
| 1 | cron tick (1분) | `dispatch_once()` → ready task spawned | `scheduler.py` | cron → scheduler.py → drewgent_kanban_db.py |
| 2 | TTL 만료 | `_reclaim_stale_tasks()` → worker reclaim | `drewgent_kanban_db.py:760` | dispatcher tick → reclaim → status='todo' |
| 3 | kanban_complete | created_cards hallucination check | `drewgent_kanban_db.py:task_complete()` | tool call → DB verify → completion_blocked event |
| 4 | task_link | DFS cycle detection | `drewgent_kanban_db.py:task_link()` | tool call → graph check → cycle이면 예외 |
| 5 | integration workflow 시작 | task 자동 생성 | `signal_processor.py` | event: integration.start → create_integration_workflow_task() |
| 6 | cron job failure | retry → fallback delivery | `cron-self-healing-protocol.md` | job fail → retry (1회) → fallback → partial status |
| 7 | turn.end | dangerous ops 감지 → event emit | `signal_processor.py:_on_turn_end()` | event: turn.end → _on_turn_end() → rule.violation |
| 8 | kanban.task.created/completed | brain signal awareness event | `signal_processor.py:_on_kanban_task_created()` | DB event → awareness.kanban |

---

## 자동起作用 경계 (What the Harness CANNOT Do Alone)

하네스가 **스스로 판단하지 못하는 것**:

| 패턴 | 현재 상태 | 설명 |
|------|----------|------|
| "kanban을 써야겠다" 판단 | 에이전트頼み | tool 호출은 에이전트가 명시적으로 요청해야 함 |
| 새 스킬/도구 통합 | 에이전트頼み | INTEGRATION_PROTOCOL 3단계는 에이전트가 실행 |
| QA gate 결정 | 에이전트頼み | latent task detection은 있지만 gate 통과 여부는 agent가 결정 |
| cron job 생성/삭제 | 에이전트頼み | jobs.json 수정은 에이전트/사람이 명시적으로 |

---

## Pattern 상세

### 1. dispatcher tick → dispatch_once

```
cron (1분마다)
  → scheduler.py가 dispatch_once() 호출
  → ready task 중 claiming 가능한 첫 번째 task 선택
  → _spawn_worker_for_task() → ACP subprocess spawn
  → task status: todo → in_progress
```

### 2. TTL 만료 → reclaim

```
worker가 heartbeat 없음 (TTL 기본 1시간)
  → dispatch_once() 매번 _reclaim_stale_tasks() 호출
  → claim_expires < now 인 task 발견
  → status = 'todo', worker_pid = NULL
  → kanban.worker.reclaimed event → awareness.integrity
```

### 3. kanban_complete hallucination check

```
agent가 kanban_complete(task_id, created_cards=[...])
  → task_complete()에서 각 ID가 drewgent_tasks.db에 존재하는지 검증
  → 존재하지 않으면: completion_blocked_hallucination event + ValueError
  → task 완료되지 않음 (차단)
```

### 4. task_link cycle detection

```
agent가 kanban_link(parent_id, child_id)
  → DFS로 순환 의존성 탐지
  → t_a → t_b → t_c → t_a 같은 cycle 발견
  → ValueError: cyclic dependency detected
  → linking되지 않음
```

### 5. integration workflow → task creation

```
signal_processor가 integration_workflow_started event 감지
  → create_integration_workflow_task() 호출
  → kanban_create(title=f"[{wf.name}].step 1", trigger_source='subagent')
  → kanban.task.created event → awareness.kanban
```

### 6. cron job failure → self-healing

```
cron job script 실행 failure (non-zero exit)
  → fallback command 1회 재시도
  → 다시 failure → partial status라도 Discord/Telegram delivery
  → 절대 침묵 금지 (no silent failure)
```

---

## Health Monitoring (실시간 모니터링)

각 자동 작용이 제대로 작동 중인지 확인하는 방법:

| 패턴 | 확인 방법 | 정상 신호 | 이상 신호 |
|------|----------|----------|-----------|
| #1 dispatcher | cron output 디렉토리 | 1분마다 새 파일 | tick 누락, double-run |
| #2 TTL reclaim | `task_list(status='in_progress')` | worker_pid ≠ NULL | orphan in_progress (worker_pid NULL, reclaimed_at NULL) |
| #3 hallucination check | gateway.log | completion_blocked event 없음 | KeyError나 validation error |
| #4 cycle detection | task_link() 호출 후 | linking 성공 | cyclic dependency error |
| #5 workflow→task | `task_list(trigger_source='subagent')` | workflow task 존재 | task 누락 |
| #6 self-healing | cron output + delivery | fallback delivery 성공 | silent failure |
| #7 dangerous ops | gateway.log `dangerous.op` | 없음 (정상) | turn.start 후 dangerous.op fire |
| #8 kanban events | brain signal log | task.created/completed event | event 누락 |

### 검증 명령

```bash
# 1. dispatcher tick 확인
ls -lt ~/.drewgent/cron/output/*/ | head -5

# 2. orphan in_progress tasks (reclaim 필요)
python3 -c "
import sys; sys.path.insert(0, 'source/claude-code')
from tools.drewgent_kanban_db import task_list
orphans = [t for t in task_list(status='in_progress') if not t.get('worker_pid')]
print(f'orphan tasks: {len(orphans)}')
for t in orphans[:5]:
    print(f'  {t[\"id\"]} - {t[\"title\"]}')
"

# 3. cron job recent failures
grep -l "failed" ~/.drewgent/cron/output/*/*.log 2>/dev/null | tail -5

# 4. kanban task throughput (오늘)
python3 -c "
import sys; sys.path.insert(0, 'source/claude-code')
from tools.drewgent_kanban_db import task_list
from datetime import date, timedelta
today = date.today()
completed = [t for t in task_list(status='completed') if t.get('completed_at', '').startswith(str(today))]
print(f'completed today: {len(completed)}')
"

# 5. brain signal health (마지막 session)
python3 -c "
import sys; sys.path.insert(0, 'source/claude-code')
from agent.signal_processor import get_signal_processor
sp = get_signal_processor()
print(f'violation_history: {len(sp._violation_history)}')
print(f'dangerous_ops_history: {len(sp._dangerous_ops_history)}')
print(f'workflow_history: {len(sp._workflow_history)}')
"
```

### 이상 감지 시 대응

| 증상 | 즉시 조치 |
|------|----------|
| orphan in_progress > 0 | `kanban_unblock(id)` 또는 `kanban_complete(id, result='reclaimed')` |
| dispatcher tick 누락 | `launchctl start ai.drewgent.gateway` (gateway restart) |
| cron job silent failure | jobs.json에서 job 확인, script 직접 실행해서 디버그 |
| violation_history 증가 | gateway.log에서 해당 rule violation 확인 |

---

## Links 업데이트 (2026-05-29)

SELF_MODEL.md 하네스 자동 작용 section과 bidirectional link:

- [[P5-ego/SELF_MODEL]] — 하네스 autonomous behaviors 원본 (P5-Ego)
- [[P0-brainstem/brain/rules]] — P0 brainstem (자동 작용 중 turn.end dangerous ops enforcement 포함)
- [[P2-hippocampus/kanban/KANBAN_INDEX]] — kanban store (자동작용#1~4의 실행 환경)
- [[P3-sensors/gateway/drewgent-architecture-dataflow]] — gateway architecture (하네스가 embedded된运行环境)
- [[P5-ego/SELF_MODEL]] — 하네스 autonomous behaviors 원본 (P5-Ego bidirectional)

---

*Generated by Drewgent — 2026-05-29*

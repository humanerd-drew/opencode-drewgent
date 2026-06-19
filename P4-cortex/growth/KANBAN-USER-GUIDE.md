---

title: Kanban User Guide
type: guide
space: growth
tags: [growth, projects, kanban]
created: 2026-05-20
updated: 2026-05-20
aliases:
  - /projects/kanban-user-guide
links:
  - "[[P5-ego/SELF_MODEL]]"
---


# Drewgent Kanban — 사용자 가이드

생성일: 2026-05-19
상태: 완전 구현 완료
Updated: 2026-05-20 — Linear 의존성 제거 (Linear workflow 완전 제거)

---

## 2개 인터페이스

| 인터페이스 | 용도 | 자동화 |
|-----------|------|--------|
| **Discord** |日常工作 — task 조회, 완료, reaction | n8n board + reaction actions |
| **터미널** | 직접 조작 — 모든 기능 | Drewgent agent tool 직접 호출 |

---

## 1. Discord에서 사용하기

### 1-1. Kanban Board 확인

n8n workflow가 주기적으로 board를 Discord 채널에 게시합니다:

```
=== Drewgent Kanban Board ===
Board: default | Updated: 2026-05-20 10:30 KST

[todo] 3 tasks
  🟡 t_abc123 — Implement SEO article harvester

[ready] 2 tasks
  ⚪ t_def456 — Deploy n8n workflow

[in_progress] 1 task
  🔵 t_ghi789 — kanban-orchestrator skill (worker: pid 12345)

[blocked] 1 task
  🔴 t_jkl012 — gateway notifier (failures: 3)

[completed] 7 tasks (today: 2)
  ✅ t_mno345 — multi-board support

React to manage:
  ✅ = complete | 🔄 = unblock | ❌ = block
```

### 1-2. Reaction으로 Task 조작

Board message에 emoji reaction하면 해당 동작이 실행됩니다:

| Emoji | 동작 | 설명 |
|-------|------|------|
| ✅ | Complete | task 완료 처리 |
| 🔄 | Unblock | blocked → ready로 변경 |
| ❌ | Block | task를 blocked 상태로 변경 |
| 🔁 | Claim | task를 내가 작업 중인 것으로 표시 |

### 1-3. @Drewgent 명령어로 Task 생성

Discord에서 Drewgent에게 직접 말하기:

```
@Drewgent 새 테스크 만들어줘: SEO article harvester 개선
@Drewgent 테스크 완료: t_abc123 결과=설정 파일 업데이트함
@Drewgent 테스크 목록 보여줘
@Drewgent 테스크的状态: t_abc123
```

---

## 2. 터미널에서 사용하기

### 2-1. Task 생성

```python
# Drewgent agent에서
kanban_create(
    title="SEO article 개선",
    body="설명...",
    assignee="drewgent",
    trigger_source="manual",  # 'manual' | 'cron' | 'subagent'
    priority=1,
    parent_task_ids=["t_abc123"],  # 의존성
    board="default",  # 'default' | 'content' | 'integrations'
)
```

### 2-2. Task 조회

```python
# 전체 목록
kanban_list()

# 상태별 필터
kanban_list(status="ready")
kanban_list(status="in_progress")

# 특정 board
kanban_list(board="content")

# 특정 담당자
kanban_list(assignee="drewgent")
```

### 2-3. Task 작업 (Worker)

```python
# Task 가져오기
kanban_list(status="ready")
task_id = "t_abc123"

# Claim (작업 시작)
kanban_claim(task_id, ttl_seconds=3600)

# 작업 중 heartbeat (지속不被 reclaim)
kanban_heartbeat(task_id, note="Step 2/5: running tests")

# 완료
kanban_complete(
    task_id,
    result="SEO article harvester 개선 완료",
    summary="설정 파일 업데이트 + rate limit 추가",
    metadata={"changed_files": ["harvester.py", "config.yaml"]},
    created_cards=["t_def456"],  # 생성한 sub-task (hallucination check)
)
```

### 2-4. 의존성 (Parent-Child)

```python
# A가 완료되어야 B를 시작할 수 있음
kanban_link(parent_id="t_abc123", child_id="t_def456")

# 순환 의존성 방지 (DFS cycle detection)
# t_abc → t_def → t_ghi → t_abc (에러 반환)
```

### 2-5. Block/Unblock

```python
# 외부 의존성으로 작업 불가
kanban_block(task_id, reason="API credentials 필요")

# 준비 완료
kanban_unblock(task_id)  # → ready 상태로 변경
```

### 2-6. Hallucination Detection

`created_cards`에 넣은 task ID가 DB에 실제로 존재하는지 자동 검증:

```python
# 가짜 ID 넣으면 예외 발생
kanban_complete(task_id, created_cards=["t_fake123"])
# → completion_blocked_hallucination event
```

### 2-7. Integration Workflow 추적

도구/스킬 통합 시 자동 task 생성:

```python
# signal_processor가 자동 호출
# integration 시작 → task_create(trigger_source="subagent", integration_workflow_id=xxx)
# integration 완료 → task_complete(workflow_id로 찾아서 완료)
```

### 2-8. Dispatcher (60초마다 자동 실행)

```bash
# cron job으로 자동 실행 (jobs.json에 등록済み)
# 수동 테스트
cd ~/.drewgent
python3 -c "
import sys; sys.path.insert(0, 'source/drewgent-agent')
from tools.drewgent_kanban_db import dispatch_once
result = dispatch_once(max_spawn=1, failure_limit=3)
print(result)
"
```

---

## 3. Cron Schedule

| Job | 주기 | 동작 |
|-----|------|------|
| kanban-dispatcher | 1분마다 | ready tasks → worker spawn |
| kanban-notify | gateway lifecycle | Discord notification (task 완료/차단 시) |

---

## 4. DB 위치

```
~/.drewgent/state/drewgent_tasks.db

Tables:
  tasks              — task 본체
  task_links         — parent-child 의존성
  task_events        — event log
  task_comments      — 코멘트
  task_runs          — worker 실행 이력
  kanban_notify_subs — subscriber (notification용)
  boards             — board 정의 (multi-board 지원)
```

---

## 5. Quick Reference

| 하고 싶은 일 | 방법 |
|-------------|------|
| 지금 할 일 확인 | Discord board message 확인 |
| 새 작업 추가 | `@Drewgent 새 테스크...` |
| 작업 완료 처리 | ✅ reaction on board |
| 복잡한 작업 분해 | `/kanban-orchestrator` skill |
| worker로 자동 실행 | kanban-dispatcher가 1분마다 spawn |
| 상태 확인 | `kanban_list(status="in_progress")` |
| 의존성 설정 | `kanban_link(parent, child)` |
| 무응답 worker reclaim | dispatcher가 자동 처리 (TTL 1시간) |

## Links
- [[P5-ego/SELF_MODEL]]

---
name: kanban-dispatcher-hardening
title: kanban-dispatcher-hardening
description: Drewgent kanban dispatcher의 logfile redirect + dead worker watchdog 적용 skill. PIPE deadlock 회피, dead worker 즉시 reclaim.
type: skill
space: knowledge
tags: [P3, sensors, kanban, dispatcher, watchdog, logfile, operational]
created: 2026-06-01
updated: 2026-06-01
links:
  - "[[P0-brainstem/brain/Drewgent-brain/P0-brainstem/禁/禁kanban_worker_accountability.neuron]]"
  - "[[P2-hippocampus/kanban/KANBAN_INDEX]]"
  - "[[P4-cortex/growth/KANBAN-USER-GUIDE]]"
  - "[[P0-brainstem/brain/rules]]"---

# kanban-dispatcher-hardening

Drewgent kanban dispatcher의 두 가지 운영 hardening 적용 skill.

**적용 대상**:
- `~/.drewgent/scripts/dispatch_once_default.py`
- `~/.drewgent/scripts/dispatch_once_content.py`
- `~/.drewgent/scripts/dispatch_once_integrations.py`

3개 파일 모두 동일 패턴으로 적용.

## 1. logfile redirect (PIPE → FILE)

### 문제
기존 dispatcher는 `subprocess.PIPE`로 worker stdout을 받아 처리하려 했음:
- Worker가 대량 출력 시 PIPE buffer (~64KB) 채워서 **deadlock**
- Worker가 완료 전까지 부모 dispatcher가 block 가능
- dispatcher 1분 tick 지연 → 다음 ready task 못 받음

### 해결
Worker stdout/stderr를 **logfile**로 redirect, dispatcher는 Popen 후 즉시 return.

```python
log_dir = DREW_HOME / 'P4-cortex' / 'scripts' / 'kanban' / 'logs' / 'workers'
log_dir.mkdir(parents=True, exist_ok=True)
log_path = log_dir / f'{task_id}.log'
logf = open(log_path, 'ab')
proc = subprocess.Popen(
    [venv_python, worker_script],
    stdout=logf, stderr=subprocess.STDOUT,
    env=env, cwd=ws_dir, start_new_session=True
)
logf.close()  # Popen이 fd 상속 — parent close 안전
```

### 디버깅
```bash
# worker output 실시간 확인
tail -f ~/.drewgent/P4-cortex/scripts/kanban/logs/workers/<task_id>.log
```

---

## 2. worker watchdog (Phase 0 — dead worker 즉시 reclaim)

### 문제
기존 dispatcher는 TTL 만료(claim_expires < now)시에만 in_progress task를 reclaim. 그런데 worker process가 비정상 종료 (segfault, OOM kill, parent kill)되면 **claim_expires가 만료될 때까지 1시간 동안 queue stuck**.

### 해결
Phase 0 추가: `os.kill(pid, 0)`로 worker 생존 확인, dead면 즉시 reclaim.

**Board 필터 적용 (cross-board race 차단)**:
각 dispatcher는 자기 board의 in_progress만 본다. `default`/`content`/`integrations` 3개 dispatcher가 동시에 돌 때, 한 dispatcher가 다른 board의 dead worker를 reclaim해버리는 race를 차단.

```python
# Phase 0: watchdog (board-scoped)
in_progress = conn.execute('''
    SELECT id, title, worker_pid FROM tasks
    WHERE status = "in_progress" AND worker_pid IS NOT NULL AND board = "self_board"
''').fetchall()
```

content는 legacy 호환:
```python
WHERE status = "in_progress" AND worker_pid IS NOT NULL AND (board = "content" OR board = "" OR board IS NULL)
```

Phase 1 (TTL reclaim)도 동일하게 board 필터:
```python
stale = conn.execute('''
    SELECT id, title, worker_pid, claim_expires FROM tasks
    WHERE status = "in_progress"
      AND claim_expires IS NOT NULL
      AND claim_expires < ?
      AND board = "self_board"
    ORDER BY claim_expires ASC
''', (now_ts,)).fetchall()
```

```python
# Phase 0: watchdog
in_progress = conn.execute('''
    SELECT id, title, worker_pid FROM tasks
    WHERE status = "in_progress" AND worker_pid IS NOT NULL
''').fetchall()

for task_id, title, wpid in in_progress:
    try:
        os.kill(int(wpid), 0)  # signal 0 = existence check (no actual signal)
    except (ProcessLookupError, OSError):
        # Worker dead — 즉시 reclaim
        conn.execute('UPDATE tasks SET status="ready", worker_pid=NULL, claim_expires=NULL WHERE id=?', (task_id,))
        result['watchdog_reclaimed'] += 1
```

### 출력 형식
```
watchdog_reclaimed=N | ttl_reclaimed=M | claimed=K | spawned=L
```

- `watchdog_reclaimed`: Phase 0가 dead worker로 reclaim한 수
- `ttl_reclaimed`: Phase 1가 TTL 만료로 reclaim한 수 (기존)
- `claimed`: Phase 2가 ready task를 claim한 수
- `spawned`: Phase 3가 worker를 spawn한 수

---

## 적용 시 체크리스트

3개 dispatcher 파일 각각에 대해:

- [ ] Phase 0 (watchdog) 코드 추가 — `os.kill(pid, 0)` 패턴
- [ ] `result` dict에 `watchdog_reclaimed: 0` 추가
- [ ] `watchdog_details = []` 리스트 추가
- [ ] `if result['watchdog_reclaimed'] > 0: conn.commit()` (TTL phase 전 commit)
- [ ] Output 라인에 `watchdog_reclaimed=N | ttl_reclaimed=M` 형식
- [ ] logfile redirect 적용 (stdout=logf, stderr=STDOUT)
- [ ] chmod +x (Unix 실행 권한)

---

## 검증 절차

### 1. AST 검증
```bash
for f in dispatch_once_default dispatch_once_content dispatch_once_integrations; do
  python3 -c "import ast; ast.parse(open('/Users/drew/.drewgent/scripts/${f}.py').read()); print('${f}: AST OK')"
done
```

### 2. Fake dead worker test
```python
import sqlite3, subprocess
from pathlib import Path
from datetime import datetime, timezone, timedelta

DB = Path.home() / '.drewgent' / 'P2-hippocampus' / 'kanban' / 'state' / 'drewgent_tasks.db'
DREW_HOME = Path.home() / '.drewgent'

# Fake dead worker: in_progress + worker_pid=99999 (절대 안 쓰는 PID)
fake_pid = 99999
conn = sqlite3.connect(str(DB))
tid = f't_fake_solo_{int(datetime.now().timestamp())}'
now = datetime.now(timezone.utc).isoformat()
expires = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
conn.execute('''
    INSERT INTO tasks (id, title, body, status, board, priority, worker_pid, claim_expires, created_at, last_heartbeat_at)
    VALUES (?, 'FAKE DEAD WORKER', 'test', 'in_progress', 'default', 1, ?, ?, ?, ?)
''', (tid, fake_pid, expires, now, now))
conn.commit()
conn.close()

# 단일 dispatcher 실행
result = subprocess.run(
    ['python3', str(DREW_HOME / 'scripts' / 'dispatch_once_default.py')],
    capture_output=True, text=True
)
print(result.stdout)
# Expected: "watchdog_reclaimed=1 | ttl_reclaimed=0 | claimed=1 | spawned=1"
# "DEAD | FAKE DEAD WORKER" 라인 출력
```

### 3. Cleanup
```python
conn.execute('DELETE FROM tasks WHERE id=?', (tid,))
conn.commit()
```

---

## 3. Sequential tick blocking (T4 root cause, 2026-06-10)

### 문제

`scheduler.py:tick()`가 `for job in due_jobs:`에서 **순차 실행**. LLM 기반 cron job (kanban-dispatcher, `d1ef68ced116`) 이 먼저 실행되면 script 기반 dispatcher (`drewgent-cron-runner-001`)가 그 뒤에서 **block**됨. LLM job이 `task_qa_gate` neuron contract phase에서 hang → 전체 tick stall, 15-26분간 dispatcher 0 fire.

### 발견된 패턴

1. `d1ef68ced116` (kanban-dispatcher, LLM agent job)가 `tick()` loop에서 먼저 실행
2. `run_job()`이 AIAgent 호출 → `task_qa_gate` neuron `contract.json` 없음 → **QA gate FAILED** (non-blocking이지만 agent가 추가 LLM 호출 중 hang)
3. `drewgent-cron-runner-001` (script-based)이 뒤에서 실행 불가
4. 다음 tick (60s 후)에서도 LLM job이 여전히 실행 중 → dispatcher fire 0 지속

### 해결

**1차 (disable redundant LLM job)**: `d1ef68ced116`을 `enabled: false`로. `cron_runner.py`가 이미 3개 board(default/content/integrations)를 script subprocess로 처리 — LLM job과 완전 중복이었음.

**2차 (systemic fix)**: `cron/scheduler.py:tick()`에서 due_jobs 정렬:

```python
# Process script-based jobs (dispatchers) FIRST so they never get
# blocked behind slow LLM agent jobs. LLM jobs run after.
_script_jobs = [j for j in due_jobs if j.get("script")]
_llm_jobs = [j for j in due_jobs if not j.get("script")]
for job in _script_jobs + _llm_jobs:
    # ... existing loop body
```

### 방어 계층 (T4.x)

| 계층 | 위치 | 역할 |
|---|---|---|
| A.2 | `gateway/run.py:3260-3290` | housekeeping try/except 분해 — exception 누수 방지 |
| T4.3 | `gateway/run.py:3236` | tick watchdog (`tick_elapsed > 5×interval` → warning) |
| T4.4 | `drewgent_harmony_check.sh` | Layer 3.5b — cron-runner fire frequency 검출 |
| T4.6 | `drewgent_cron_watchdog.sh` | 0 fires in 5min → auto kickstart |

### Pitfall

**모든 LLM cron job이 동일한 위험**: SEO Article Harvester, Trend Harvester 등도 sequential tick에서 diabled된 kanban-dispatcher와 같은 패턴으로 block 가능. 해결은 동일 — script-first sort가 script job을 보호. LLM job들 사이에서는 여전히 sequential 실행되나, dispatcher가 blocking되지 않으므로 watchdog이 5분 내 kickstart.

---

## Pitfall

**같은 tick에서 watchdog reclaim → Phase 2 re-claim**:
Phase 0가 task를 ready로 만들면, 같은 dispatcher cycle의 Phase 2가 그 task를 다시 claim할 수 있음. 이는 expected — 다음 tick (1분 후)에는 다른 ready task를 받음. 검증 시 SELECT 시점이 Phase 2 후면 status='in_progress'로 보일 수 있음. **검증은 stdout의 `watchdog_reclaimed=1` 카운터로** 확인할 것.

**logfile 무한 누적**:
`P4-cortex/scripts/kanban/logs/workers/{task_id}.log`가 task 완료 후에도 남음. 정리 cron 필요 (kanban-maintenance-guide.md의 cron-output-cleanup 패턴 참고).

**content board legacy 호환**:
content dispatcher는 `board = "" OR board IS NULL`도 받음 — `kanban_create()` 호출 시 board 미지정으로 생긴 legacy task 호환. 새 task는 반드시 board 명시 권장.

---

## Related
- [[P0-brainstem/brain/Drewgent-brain/P0-brainstem/禁/禁kanban_worker_accountability.neuron]] — TTL/heartbeat enforcement
- [[P2-hippocampus/kanban/KANBAN_INDEX]] — kanban brain integration
- `~/.drewgent/scripts/dispatch_once_default.py`
- `~/.drewgent/scripts/dispatch_once_content.py`
- `~/.drewgent/scripts/dispatch_once_integrations.py`

---

*Generated by Drewgent — 2026-06-01*
*Source: agent design session for dispatcher hardening (Phase 1)*

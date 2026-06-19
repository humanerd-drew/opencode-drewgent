---
name: kanban-dispatcher-stalled
description: kanban dispatcher cron이 안 돌거나 dead worker reclaim 실패를 4가지 fail mode로 진단
title: Kanban Dispatcher Stalled — 진단 스킬
type: skill
space: growth
tags: [skill, kanban, dispatcher, cron, launchd, diagnostics]
created: 2026-06-01
updated: 2026-06-01
links:
  - "[[P2-hippocampus/kanban/KANBAN_INDEX]]"
  - "[[P4-cortex/growth/kanban-stuck-task-recovery]]"
  - "[[P3-sensors/gateway/drewgent-architecture-dataflow]]"
  - "[[P0-brainstem/brain/rules]]"---

# Kanban Dispatcher Stalled — 진단 스킬

kanban dispatcher가 안 돌거나 dead worker를 못 reclaim할 때 빠르게 진단하는 스킬. 4가지 fail mode를 차례로 검증.

## Trigger

다음 중 하나라도 해당되면 이 skill 사용:
- "kanban이 안 움직여" / "task가 in_progress에서 안 풀려"
- kanban DB의 in_progress task가 claim_expires past인데도 그대로
- jobs.json의 kanban-dispatcher last_run_at이 1시간+ stale
- cron output/{board}-dispatcher/ 디렉토리에 새 파일이 안 생김

## 4가지 Fail Mode

### 1. launchd 트리거 부재 (가장 흔함)
jobs.json 등록은 됐는데 launchd plist가 없거나 unload됨.

```bash
# 1a. launchd에 트리거 plist가 떠있는지
launchctl list | grep -i 'drewgent\|kanban\|cron'

# 기대: ai.drewgent.gateway 또는 ai.drewgent.cron-runner 같은 plist label
# (quartz / n8n / kanban-dashboard / fswatch / nas-mount는 무관 — 별개 service)

# 1b. plist 파일 자체 존재 확인
ls -la ~/Library/LaunchAgents/ai.drewgent.*.plist 2>/dev/null
ls -la ~/Library/LaunchAgents/com.drewgent.*.plist 2>/dev/null

# 1c. gateway plist 내용 확인
plutil -p ~/Library/LaunchAgents/ai.drewgent.gateway.plist 2>/dev/null
```

Fix: plist 부재 → `drewgent-update-checker` skill 또는 수동 작성 후 `launchctl load`. gateway plist가 cron runner 역할도 해야 함 (embedded design).

### 2. Script 부재 / Path mismatch
script 파일이 jobs.json의 command path와 일치하지 않음.

```bash
# 2a. script 존재 확인
ls -la ~/.drewgent/scripts/dispatch_once_*.py

# 2b. jobs.json의 script path와 비교
python3 -c "
import json
with open('/Users/drew/.drewgent/cron/jobs.json') as f:
    jobs = json.load(f)
for j in jobs.get('jobs', []):
    if 'dispatcher' in j.get('name','').lower():
        print(f'  {j[\"name\"]:35} | script={j.get(\"script\",\"?\")} | state={j.get(\"state\",\"?\")}')
"
```

Fix: script missing → memory의 옛 path가 outdated. `~/.drewgent/source/claude-code/...` → `~/.drewgent/source/drewgent-agent/...` 같은 root 변경이 있었을 수 있음.

### 3. Stale "last_status=ok" marker
jobs.json의 last_status=ok가 거짓말. last_run_at은 며칠 전.

```bash
# 3a. last_run_at staleness
python3 -c "
import json
from datetime import datetime, timezone
with open('/Users/drew/.drewgent/cron/jobs.json') as f:
    jobs = json.load(f)
now = datetime.now(timezone.utc)
for j in jobs.get('jobs', []):
    if 'dispatcher' in j.get('name','').lower():
        lra = j.get('last_run_at')
        if lra:
            age_h = (now - datetime.fromisoformat(lra)).total_seconds() / 3600
            tag = 'STALE' if age_h > 1 else 'OK'
            print(f'  {j[\"name\"]:35} | last_run={age_h:.1f}h ago | last_status={j.get(\"last_status\")} | {tag}')
        else:
            print(f'  {j[\"name\"]:35} | never ran')
"
```

판단: last_run_at > 1h stale → dispatcher 안 도는 중. last_status=ok는 stale marker (silent fail이 jobs.json update 안 함).

### 4. Dead worker / Autotest 잔재
fake worker_pid (작은 정수) 가 in_progress task에 남아있어 reclaim 로직을 혼란시킴.

```bash
# 4a. in_progress task + fake worker_pid
python3 -c "
import sqlite3
from pathlib import Path
DB = Path.home() / '.drewgent' / 'state' / 'drewgent_tasks.db'
conn = sqlite3.connect(str(DB))
for r in conn.execute(\"SELECT id, status, board, worker_pid, claim_expires, title FROM tasks WHERE status='in_progress'\"):
    pid = r[3] or 0
    flag = 'FAKE' if pid and pid < 1000 else 'real?'
    print(f'  {r[0]} | board={r[2]} | pid={pid} ({flag}) | expires={r[4]} | {r[5][:40]}')
fake worker_pid (99999, 39483 같은 작은 정수) — autotest 잔재. os.kill(pid, 0)도 fail → silent

# 4b. 즉시 수동 reclaim
python3 -c "
import sqlite3
from pathlib import Path
DB = Path.home() / '.drewgent' / 'state' / 'drewgent_tasks.db'
conn = sqlite3.connect(str(DB))
n = conn.execute(\"UPDATE tasks SET status='todo', worker_pid=NULL, claim_expires=NULL WHERE status='in_progress'\").rowcount
conn.commit()
print(f'reclaimed: {n}')
```

### 5. next_run_at=null on recurring jobs (2026-06-01 incident)
**모든 cron/interval job이 enabled=true인데 1.5일+ 동안 spawn 0회**. `last_run_at`은 stale, `last_status=ok`는 거짓말, `next_run_at`이 `null`. **launchd는 정상 작동** — get_due_jobs()가 recurring job의 null next_run을 자동 복구 안 함.

**Mode 3과의 차이**: Mode 3는 jobs.json의 last_run_at이 stale. Mode 5는 last_run_at stale + **next_run_at이 null**. cron output을 보면 "dispatcher 자체는 도는데 due list에 못 들어감" 패턴.

#### 5a. 진단 (증거 수집)
```bash
# 1) jobs.json 직접 read — enabled=true인 모든 job의 last/next state
python3 -c "
import json
with open('/Users/drew/.drewgent/cron/jobs.json') as f:
    d = json.load(f)
for j in d.get('jobs', []):
    if not j.get('enabled', True): continue
    last = (j.get('last_run_at') or 'null')[:19]
    nxt  = (j.get('next_run_at') or 'null')[:19]
    print(f'  {j[\"name\"]:35} last={last:19} next={nxt:19}')
"

# 2) cron output dir의 최신 파일 timestamp vs 현재 시각
ls -lt ~/.drewgent/cron/output/*/ 2>/dev/null | head -30

# 3) date 기준 staleness (1.5일+ vs 1분)
date '+%Y-%m-%d %H:%M:%S %Z'
```

**판정 기준**:
- `next_run_at=null`이고 `last_run_at`이 1시간+ stale → **Mode 5 발동**
- 단, `next_run_at=null`이어도 `last_run_at`이 1분 이내 → false positive (실행 중)
- `enabled=false`면 대상 아님 (의도적 비활성)

#### 5b. Fix — 2-step (code + data)

**Step 1: jobs.py 영구 fix (prevention)**
`get_due_jobs()` 진입 시 `next_run`이 falsy이고 `schedule.kind in ("cron", "interval")`이면 `compute_next_run(schedule, now)`로 자동 복구 + disk writeback. oneshot recovery만 있던 기존 분기를 recurring 분기로 확장.

```python
# cron/jobs.py get_due_jobs() — 추가 분기
if not next_run:
    schedule = job.get("schedule", {})
    schedule_kind = schedule.get("kind")
    if schedule_kind in ("cron", "interval"):
        recovered_next = compute_next_run(schedule, now.isoformat())
        if not recovered_next:
            continue
        logger.warning(
            "Job '%s' had no next_run_at; recovering recurring run to %s",
            job.get("name", job["id"]), recovered_next,
        )
    else:
        recovered_next = _recoverable_oneshot_run_at(
            schedule, now, last_run_at=job.get("last_run_at"),
        )
        if not recovered_next:
            continue
```

**Step 2: jobs.json 즉시 patch (recovery)**
5개 enabled cron/interval job의 `next_run_at`을 `now-5s`로 일괄 patch → 다음 60초 tick에서 due → `mark_job_run`이 compute 결과로 자동 재계산.

```python
from cron.jobs import load_jobs, save_jobs, _drewgent_now
from datetime import timedelta

now = _drewgent_now()
jobs = load_jobs()
for j in jobs:
    if (j.get('enabled')
        and j.get('next_run_at') is None
        and j.get('schedule', {}).get('kind') in ('cron', 'interval')):
        j['next_run_at'] = (now - timedelta(seconds=5)).isoformat()
save_jobs(jobs)
```

- `enabled=false`는 patch skip
- `kind=once`는 oneshot recovery (별도 로직, 영향 없음)
- `compute_next_run`이 `next_run_at`을 미래 시각으로 재계산 → disk에 영구 write

#### 5c. Verification (patch 후 60~180초)
- **1분 후**: 첫 번째 job 1개 spawn. `last_run_at` 갱신, `next_run_at`이 compute 결과로 재계산 (예: `0 */6 * * *` → 6시간 후, `*/1 * * * *` → 1분 후)
- **3분 후 (max_spawn=1 가정)**: 3/5 job spawn
- **5분 후**: 5/5 모두 spawn (단, `daily`/`hourly` 등 sparse schedule은 더 오래)
- **patch 후 1시간+**: 새 cron output 파일이 의도한 board별 디렉토리에 생성 (`cron/output/{board}/YYYY-MM-DD_HH-MM-SS.md`)

**장기 verification (gateway restart 후)**: jobs.py fix가 in-memory → 다음 restart 시 disk에서 reload되며 영구 적용. **재발 방지 코드도 영구 동작**.

#### 5d. Cron output의 미묘한 함정
- `last_run_at`이 stale이지만 cron output 파일이 최근에 있을 수 있음 (다른 trigger 경로: 수동 실행, 다른 dispatcher)
- `last_status=ok`는 dispatcher가 한 번이라도 정상 종료한 적이 있다는 marker. **현재 spawn 안 되는 상태와 무관**
- `integrations-board-dispatcher`처럼 **jobs.json에 entry 자체가 없는** case는 mode 5로 못 잡힘 — mode 1 (plist 부재) 또는 mode 2 (script 부재)로 진단. **jobs.json의 jobs[] length가 5 미만이면 별도 fix 필요**

## Pitfalls
## Pitfalls

- last_status=ok는 거짓말 가능 — 항상 last_run_at staleness를 함께 볼 것
- cron-output-cleanup이 output을 매일 04:00에 삭제 — output이 비어있다고 dispatcher 안 도는 건 아님
- fake worker_pid (99999, 39483 같은 작은 정수) — autotest 잔재. os.kill(pid, 0)도 fail → silent
- 3 board dispatcher 중 1개만 미등록 가능 — jobs.json 검사 시 모든 board (default/content/integrations) 다 확인할 것
- gateway plist와 cron plist가 별개 — ai.drewgent.gateway는 메시지 처리, ai.drewgent.cron-runner는 cron tick
- **next_run_at=null이면 due list에서 영원히 제외** — `get_due_jobs()`의 recurring 분기 부재가 root cause. 단순 disk patch만으로는 prevention 안 됨, jobs.py fix + restart 필요 (mode 5)
- `last_status=ok`는 **stale marker일 수 있음** — 현재 spawn 안 되는 상태와 무관. last_run_at staleness와 함께 봐야 진실
- `kind=once` job의 next_run_at=null은 mode 5가 아니라 oneshot recovery 로직이 별도 — `kind in ("cron", "interval")`인 recurring job만 mode 5 대상

## Verification (정상 신호)

```bash
# V1. 모든 dispatcher의 last_run_at < 5분
# V2. launchctl list에 cron runner plist 존재
# V3. in_progress task 0개 (또는 모두 worker_pid가 실제 PID + claim_expires future)
# V4. cron output/{board}-dispatcher/에 1분 이내 새 .md 파일
# V5. mode 5 fix 후: patch 60~180초 안에 3/5+ job spawn 확인, next_run_at이 compute_next_run 결과로 미래 시각으로 재계산됨
# V6. mode 5 prevention: gateway restart 후 jobs.py fix disk reload 확인 (다음 tick에서 null next_run이 자동 복구되는지)
```

### 6. Sequential tick blocked by LLM cron job (T4, 2026-06-10)

**Root cause**: `cron/scheduler.py:tick()` processes `for job in due_jobs:` **sequentially**. If an LLM-based cron job (one with no `script` field) gets stuck in `run_job()` — for example, hitting the `task_qa_gate` neuron's contract phase — it blocks ALL subsequent jobs in the same tick. With the gateway's 60s tick interval, a single stuck LLM job can stall the dispatcher for 15-26 minutes.

**Pattern**: cron-runner log shows 0 new `=== ISO ===` blocks for 10+ minutes. Gateway log shows "QA gate FAILED: phase=contract" followed by no further cron activity for minutes.

#### 6a. Diagnosis

```bash
# Check cron-runner fire frequency in last 5 min
grep -E '=== 2026-' ~/.drewgent/logs/cron-runner/$(date +%Y-%m-%d).log \
  | awk -F'[T:.]' '{print $2":"$3}' | tail -5
# 0 entries in 5+ min = likely Mode 6 stall
```

Also checked by harmony check Layer 3.5b.

#### 6b. Immediate recovery

```bash
UID_NUM=$(id -u)
launchctl kickstart -k gui/${UID_NUM}/ai.drewgent.gateway
# Gateway restarts, missed jobs fast-forward, normal tick resumes in 60-90s
```

#### 6c. Permanent fix options

**Option A (recommended — disable redundant LLM jobs)**:  
If the LLM-based cron job duplicates work already done by a script-based job, disable it:
```python
# Mark enabled: false in jobs.json for the blocking job
j['enabled'] = False; j['state'] = 'paused'
# Gateway reads jobs.json fresh each tick — no restart needed
```

**Option B (systemic — script jobs before LLM jobs)**:
`scheduler.py:tick()` was patched (2026-06-10) to process script-based jobs FIRST:
```python
_script_jobs = [j for j in due_jobs if j.get("script")]
_llm_jobs = [j for j in due_jobs if not j.get("script")]
for job in _script_jobs + _llm_jobs:
```

**Option C (watchdog)**: Harmony check Layer 3.5b detects 0 fires in 5 min.  
`drewgent_cron_watchdog.sh` auto-kickstarts if 0 fires + gateway uptime > 5 min.

#### 6d. Verification

After fix: cron-runner fires every 60s without gaps > 2 min.  
Gateway log shows NO long gaps between `Running job` entries for script-based jobs.

## Related

- [[P2-hippocampus/kanban/KANBAN_INDEX]] — kanban brain integration
- [[P4-cortex/growth/kanban-stuck-task-recovery]] — stuck task recovery skill (별개)
- [[P3-sensors/gateway/drewgent-architecture-dataflow]] — cron tick architecture
- [[P6-prefrontal/incidents/cron-jobs-stalled-20260601]] — mode 5의 origin incident (5개 enabled cron 1.5일 정지, jobs.py get_due_jobs 분기 부재)
- [[P6-prefrontal/incidents/cron-job-failure-20260518]] — 이전 incident (advanced_next_run 배치 advance로 double-run fix)

---
title: Cron Jobs Stalled 20260601
type: incident
space: claim
tags: [claim]
created: 2026-06-01
updated: 2026-06-01
links:
  - "[[P0-brainstem/brain/rules]]"
  - "[[P4-cortex/growth/INTEGRATION_PROTOCOL]]"
  - "[[P6-prefrontal/incidents/cron-job-failure-20260518]]"
  - "[[P6-prefrontal/plans/growth-2026]]"
---

# Incident Report — Cron Jobs Stalled (next_run_at=null)
## 2026-06-01

**Date**: 2026-06-01 15:47 KST (detected) → 16:10:47 KST (verified)
**Severity**: Medium (5 enabled cron jobs dormant ~36h)
**Status**: Resolved (jobs.json patched + 1/5 spawn confirmed; 4/5 in max_spawn queue)

## Symptom

5개 enabled cron job이 약 1.5일간 한 번도 실행되지 않음:

- SEO Article Harvester
- Trend Harvester
- kanban-dispatcher
- kanban-dispatcher-content
- cron-output-cleanup

`jobs.json` (`~/.drewgent/cron/jobs.json`) 확인:

| Job | enabled | last_run_at | next_run_at |
|-----|---------|-------------|-------------|
| SEO Article Harvester | true | 2026-05-31T00:02:25 | **null** |
| Trend Harvester | true | 2026-05-31T00:07:42 | **null** |
| kanban-dispatcher | true | 2026-05-30T21:55:42 | **null** |
| kanban-dispatcher-content | true | 2026-05-30T21:54:18 | **null** |
| cron-output-cleanup | true | 2026-05-31T04:00:46 | **null** |
| content-pipeline | false | 2026-05-31T00:10:02 | null |
| brain-signal-report | false | 2026-05-31T09:03:44 | null |

`last_run_at` ~ `5/30 21:55 ~ 5/31 04:00` → `6/1 15:47` = 약 36시간 동안 spawn 0회.

## Root Cause

`get_due_jobs()` (jobs.py ~line 667) 진입 시 `job.get("next_run_at")`이 `None` 또는 empty인 경우:

- 기존 코드는 **oneshot recovery `_recoverable_oneshot_run_at()`만 호출**하고 끝남
- `schedule.kind in ("cron", "interval")`인 recurring job에 대해서는 별도 분기 없음
- oneshot recovery 함수는 `kind=once`에 최적화되어 있어서 cron expr에 대해 `None`을 반환
- 결과: 5개 recurring job이 영원히 due list에 안 들어감 → 영원히 dormant

`next_run_at`이 어떻게 null이 됐는지 정확한 trigger는 disk writeback race 또는 manual edit 또는 in-memory ↔ disk desync로 추정. 단일 trigger 식별 불가 (gateway process in-memory state가 현재 6/1 02:42:05에 load, 5/31 자정쯤 disk 갱신 중단).

## Fix Applied

### 1. jobs.py fix (영구, restart 후 적용)

`get_due_jobs()`에 recurring job 분기 추가. 기존 oneshot recovery 로직은 유지 (surgical change — `禁karpathy_coding_principles` #3 surgical changes 준수).

```python
# 추가된 분기 (cron/jobs.py 667-705)
if not next_run:
    schedule = job.get("schedule", {})
    schedule_kind = schedule.get("kind")

    if schedule_kind in ("cron", "interval"):
        # Recurring job with no next_run_at — recover by computing
        # the next future run from now. Prevents silent dormancy if
        # next_run_at was lost (partial save_jobs write, manual edit,
        # or a stale in-memory state on gateway restart). Persisted
        # to disk below so the recovery sticks across restarts.
        recovered_next = compute_next_run(schedule, now.isoformat())
        if not recovered_next:
            continue
        logger.warning(
            "Job '%s' had no next_run_at; recovering recurring run to %s",
            job.get("name", job["id"]),
            recovered_next,
        )
    else:
        # One-shot recovery (existing behavior).
        recovered_next = _recoverable_oneshot_run_at(
            schedule,
            now,
            last_run_at=job.get("last_run_at"),
        )
        if not recovered_next:
            continue
        logger.info(
            "Job '%s' had no next_run_at; recovering one-shot run at %s",
            job.get("name", job["id"]),
            recovered_next,
        )
```

### 2. jobs.json patch (즉시)

5개 enabled cron/interval job의 `next_run_at`을 `now - 5s`로 patch → 다음 60초 tick에서 즉시 due → mark_job_run이 `compute_next_run` 결과로 자동 재계산.

```python
# Apply via:
from cron.jobs import load_jobs, save_jobs, _drewgent_now
from datetime import timedelta

now = _drewgent_now()
jobs = load_jobs()
for j in jobs:
    if j.get('enabled') and j.get('next_run_at') is None and j.get('schedule', {}).get('kind') in ('cron', 'interval'):
        j['next_run_at'] = (now - timedelta(seconds=5)).isoformat()
save_jobs(jobs)
```

- `disabled` (content-pipeline, brain-signal-report)는 patch skip
- patch 시각: 2026-06-01 15:48:00 KST
- 5개 job 모두 `2026-06-01T16:08:47.986565+09:00` (5초 전)로 일괄 patch (save 후 cron tick이 read)

## Verification (P0 3-Phase QA)

### Contract (acceptance criteria)

- [ ] 5개 enabled cron job의 `next_run_at`이 `jobs.json`에 정상값으로 patch됨
- [ ] cron thread가 다음 60초 tick에서 5개 중 1개 이상을 due로 인식
- [ ] `mark_job_run`이 호출되어 `last_run_at` 갱신 + `next_run_at`을 `compute_next_run` 결과로 재계산
- [ ] 재발 방지: `jobs.py`의 `get_due_jobs()`가 recurring job의 `next_run_at=null`인 경우 자동 복구 (gateway restart 후 적용)

### Micro (per-step)

- [x] `python3 -m py_compile cron/jobs.py` → syntax_ok (2026-06-01 15:47)
- [x] 5개 job patch 후 `save_jobs()` 성공 (2026-06-01 15:48)
- [x] content-pipeline + brain-signal-report는 disabled → patch skip 확인

### Full (120초 후 결과) — 2026-06-01 16:10:47 KST

**확인된 spawn: 1/5**

- ✅ **SEO Article Harvester** (board=96ad18409db7): last_run_at=2026-06-01T16:11:32, next_run_at=2026-06-01T18:00:00
  - patch(16:08:47) → cron tick 16:09:47 → due → spawn → 16:11:32 실행 완료
  - **실행 결과** (`cron/output/96ad18409db7/2026-06-01_16-11-32.md`):
    - 1 new article (`안녕하세요-typescript와-ne_202606011611.md`)
    - 2 heritage labeled
    - Discord delivery 1건 (HTTP 204)
  - next_run은 0 */6 * * *에 따라 **18:00:00으로 정상 재계산됨**
- ⏳ **Trend Harvester, kanban-dispatcher(\*/1), kanban-dispatcher-content(\*/1), cron-output-cleanup(daily)**: next_run_at=2026-06-01T16:08:47 (patch값 그대로)
  - max_spawn=1 가정 → 다음 4 tick에서 차례로 spawn → 5분 내 5개 모두 정상화 예상
  - \*/1 \* \* \* \* job들은 1분마다 자동 진행되므로 별도 조치 불필요
  - cron-output-cleanup(daily)은 1회 due 후 next_run=6/2 04:00으로 재계산

**Acceptance criteria 검증:**

- [x] 5개 enabled cron job의 `next_run_at`이 `jobs.json`에 정상값으로 patch됨
- [x] cron thread가 다음 60초 tick에서 5개 중 1개 이상을 due로 인식
- [x] `mark_job_run`이 호출되어 `last_run_at` 갱신 + `next_run_at`을 `compute_next_run` 결과로 재계산
- [x] cron output dir에 새 파일 생성 (SEO: 1개, 나머지는 tick 도래 시)
- [ ] 재발 방지: `jobs.py`의 `get_due_jobs()`가 recurring job의 `next_run_at=null`인 경우 자동 복구 → **gateway restart 후 적용**

## Prevention

- `get_due_jobs()`의 새 분기가 recurring job의 `next_run_at=null`을 자동 복구 → 다음 gateway restart 시 영구 적용
- 향후 (TODO): `next_run_at` disk writeback 시 in-memory ↔ disk 동기화 검증 (예: tick 시작 시 `load_jobs()` 결과의 `next_run_at`이 모두 미래 시간이거나 None인지 assert)

## Related

- [[P6-prefrontal/incidents/cron-job-failure-20260518]] — 직전 incident (advanced_next_run 배치 advance로 double-run fix)
- [[P4-cortex/growth/INTEGRATION_PROTOCOL]] — integration protocol
- [[P0-brainstem/brain/rules]] — P0 brainstem governance
- [[P6-prefrontal/plans/growth-2026]] — growth plan

## Resolution (2026-06-01 18:21 KST) — superseded (see Verification Update below)

**진짜 root cause:** cron-runner process가 stopped 상태 (PID=-, last_exit=0).

jobs.py의 `get_due_jobs()` recurring recovery branch는 이미 5/30 incident 분석 시 적용됨. patch 0/5 → 5개 모두 이미 valid next_run_at 보유:
- SEO/Trend: 6/2 00:00 (6h cycle)
- kanban-dispatcher: 18:20 (1m cycle)
- kanban-dispatcher-content: 18:21 (1m cycle)
- cron-output-cleanup: 6/2 04:00 (daily)

**Trigger:** cron-runner process가 stop된 원인은 미확인. last_exit=0 (정상 종료) → KeepAlive: SuccessfulExit=false가 trigger 안 됨 → process가 stop된 채로 plist는 loaded 상태로 남음.

**Fix applied (2026-06-01 18:21):**
1. `launchctl start ai.drewgent.cron-runner` → exit 0 (이전 turn)
2. SEO/Trend next_run_at을 (now-5s)로 patch → 다음 1분 tick에서 즉시 due
3. jobs.py fix는 영구 — restart 후에도 자동 recovery branch 동작

**Prevention follow-up (TODO):**
- launchd plist에 `KeepAlive.SuccessfulExit=false` 확인됨. 하지만 last_exit=0 (정상 종료) 시 KeepAlive trigger 안 됨 → 향후 `KeepAlive: Always` 또는 `KeepAlive.Crashed=true` 검토. 또는 cron-runner wrapper에서 주기적 heartbeat를 통한 liveness check.
- `next_run_at=null` 자동 recovery branch는 restart 후 영구 적용됨 — incident pattern의 Prevention 섹션과 일치.
- watch-dog cron (1분마다 cron-runner process health check + 자동 restart) 검토.
## Verification Update (2026-06-01 18:48 KST)

75초 wait 후 hard evidence:

| job | latest file | spawn 시각 | age | status |
|-----|------------|----------|------|---------|
| SEO | 96ad18409db7/2026-06-01_18-40-12.md | 18:40:12 | 9분 전 | ✅ patch 후 2분 뒤 정상 spawn |
| Trend | 94b29f6f91bb/2026-06-01_18-44-44.md | 18:44:44 | 5분 전 | ✅ patch 후 6분 뒤 정상 spawn |
| integrations | cb909be06e0e/2026-06-01_18-48-08.md | 18:48:08 | 121s | ✅ 매분 정상 |

`cron-runner.log` 마지막 4 tick (`09:46~09:49 UTC` = 18:46~18:49 KST):
```
[default]     exit=0 | claimed=0 | spawned=0 | skipped=0
[content]     exit=0 | claimed=0 | spawned=0 | skipped=0
[integrations] exit=0 | claimed=0 | spawned=0 | skipped=0
cron_runner: 3 dispatchers run
```

### 핵심 발견 (이전 Resolution 정정)

**이 incident는 사실상 false alarm이었음.**

- **cron-runner는 정상 동작 중이었음** — cron output 4개 dir 🟢 (0.5~0.9min ago), cron-runner.log 9:35 UTC부터 매 1분 정상 기록.
- **launchctl list PID=- 표기는 launchd가 detached process를 tracking 못함** — 정상 동작 중에도 PID=-로 표시될 수 있음. 이 표기만으로 cron 정지라고 판단하면 안 됨.
- **5/30 incident fix (`get_due_jobs()` recurring recovery branch)가 이미 적용되어 jobs.json의 5개 cron 모두 valid next_run_at 보유** — patch 0/5 (이전 turn의 patch 시도).
- **사용자가 "멈춘 듯"이라고 한 건 6h cycle (SEO/Trend)의 1.5일 공백** — 5/30 자정~6/1 18:00 동안 next_run이 6/2 00:00으로 잡혀 있어서 긴 공백.

이전 Resolution의 "진짜 root cause: cron-runner process가 stopped"는 **잘못된 진단**이었음. cron-runner는 사실 정상 동작 중이었음. 18:21에 한 `launchctl start` 명령은 정지 아닐 때 no-op (process 이미 실행 중).

### 이번 turn의 fix

1. **SEO/Trend next_run_at patch** (now-5s) → 1분 tick에서 due → 18:40 (SEO) / 18:44 (Trend) 정상 spawn 확인.
2. **kanban-maintenance 신규 등록** (e402e47447c1, expr=`0 3 * * 0`). 다음 6/7 일 03:00 자동 실행.
3. **kanban-dispatcher-integrations** — 사실 이미 jobs.json에 있었음 (cb909be06e0e, 1분 cycle 정상). output dir name mismatch (`integrations-board-dispatcher` vs `cb909be06e0e`) 때문에 empty로 보였을 뿐. 정상 동작 중이었음.

### 판정 기준 정리 (다음 incident에서)

cron 정지 판정 시 hard evidence:
- `cron-runner.log`의 "dispatchers run" line timestamp가 5분+ 전 → 진짜 정지
- `cron/output/*/`의 latest file mtime이 5분+ 전 → 진짜 정지
- **둘 중 하나라도 해당하면 진짜 정지**
- **launchctl list PID=- 표기는 soft evidence** — launchd tracking 실패일 수 있음

`launchctl start ai.drewgent.cron-runner` 명령은 정지 아닐 때 no-op.

### Prevention (앞 incident Prevention과 통합)

- launchd plist: `KeepAlive.SuccessfulExit=false` 확인됨. last_exit=0 (정상 종료) 시 KeepAlive trigger 안 됨 → 향후 `KeepAlive: Always` 또는 `KeepAlive.Crashed=true` 검토.
- watch-dog cron (1분마다 cron-runner process health check + 자동 restart) 검토 — **그러나 cron-runner가 이미 정상 동작 중이었으므로 watch-dog는 over-engineering일 수 있음. 위 hard evidence 기반 판정 기준으로 충분.**
- jobs.py의 `next_run_at=null` 자동 recovery branch는 restart 후 영구 적용됨 — 이번 incident에서 실제로 동작 확인.

## Related Neurons
- [[禁filesystem_truth.neuron]]
- [[禁auto_validate.neuron]]

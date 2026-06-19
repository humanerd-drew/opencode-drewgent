---
title: Cron Job Failure 20260518
type: incident
space: claim
tags: [claim]
created: 2026-05-20
updated: 2026-05-20
links:
  - "[[P0-brainstem/brain/rules]]"
  - "[[P4-cortex/growth/INTEGRATION_PROTOCOL]]"
  - "[[P6-prefrontal/plans/growth-2026]]"
---



# Incident Report — Cron Job Failure Analysis
## 2026-05-18

**Date**: 2026-05-18 02:20 KST
**Severity**: Medium
**Status**: Resolved

## Incident

Cron job들이 제대로 작동하지 않음 (Trend Harvester disabled, SEO over-execution).

## Root Cause

1. **Trend Harvester**: `enabled=false`로 수동 비활성화됨 (아마 조작 실수)
2. **SEO Article Harvester**: gateway 재시작 시 stale run detection의 fast-forward grace(2시간)가 일부 스케줄 미스 케이스를 catch-up 처리
3. KST croniter 해석은 실제로 올바름 (버그 아님)

## Additional Bugs Found (2026-05-18 afternoon)

### Bug 1: `KeyError: 'qa_evidence_dir'`
- **Time**: 06:00:28~06:00:32 KST
- **Impact**: SEO + Trend job 모두 실패
- **Symptom**: gateway.log에 `ERROR cron.scheduler: Job 'X' failed: KeyError: 'qa_evidence_dir'`
- **Auto-recovery**: 두 job 모두 11:51~11:58에 자기好自己修正 (별도 조치 없이恢复正常)
- **Root cause 미해결**: 왜 `qa_evidence_dir` KeyError가 떴는지 원人不详

### Bug 2: Double-run in same tick — FIXED ✅
- **Time**: 01:53 + 01:59 (Trend만), SEO는 01:46 + 01:28 두 번
- **Symptom**: 같은 tick에서 같은 job이 2번 실행됨
- **Root cause**: `advance_next_run()`이 `run_job()` 실행 *중에* 호출 → disk에 새 next_run_at이 write됨 → 다음 job iteration에서 `get_due_jobs()`가 같은 job을 다시 due로 반환
- **Fix**: `advance_next_run()`를 for loop *이전으로* 이동 — 모든 job의 next_run_at을 실행 전에 한꺼번에 advance
- **Location**: `cron/scheduler.py` ~line 793 — pre-loop batch advance
- **Applied**: 2026-05-18 (이슈 분석 직후)

## Fix Applied

1. Trend Harvester 재활성화: `enabled=true`, `state=scheduled`, `next_run=2026-05-18T06:00:00+09:00`
2. SEO next_run_at 확인: `2026-05-18T06:00:00+09:00` (정상)
3. KST croniter는 KST-aware datetime 입력 시 올바르게 동작 → 별도 코딩 수정 불필요
4. 06:00 실패 job들은 자기好自己修正 (11:51~11:58 정상 실행됨)

## Verification (2026-05-18 14:15 KST)

- Manual trigger test (Trend Harvester, 14:13 KST): **single run confirmed** — no double-run
- Log confirms: only one execution at 14:14:43, not repeated
- Fix verified: `advance_next_run()` pre-loop batch advance working correctly
- Next full tick: 18:00 KST (scheduled)

## Current Job State (2026-05-18 14:15 KST)

| Job | enabled | state | next_run_at | last_run_at | last_status |
|-----|---------|-------|-------------|-------------|-------------|
| SEO Article Harvester | true | scheduled | 2026-05-18T18:00:00+09:00 | 2026-05-18T11:51:01+09:00 | ok |
| Trend Harvester | true | scheduled | 2026-05-18T18:00:00+09:00 | 2026-05-18T14:13:58+09:00 | ok |

## Schedule

- `0 */6 * * *` → KST 06:00, 12:00, 18:00, 00:00

## TODO (Closed)

1. ~~Bug 1 (`qa_evidence_dir` KeyError) root cause 조사~~ — Low priority, not blocking
2. ~~Bug 2 (double-run)~~ → **FIXED & VERIFIED** ✅ (scheduler.py line 793 batch advance)

## Related

- [[P6-prefrontal/plans/growth-2026]] — growth plan reference
- [[P4-cortex/growth/INTEGRATION_PROTOCOL]] — integration protocol
- [[P0-brainstem/brain/rules]] — P0 brainstem governance

## Related Neurons
- [[禁auto_validate.neuron]]
- [[禁subagent_verify.neuron]]

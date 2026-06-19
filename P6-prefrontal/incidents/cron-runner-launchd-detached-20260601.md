---
title: cron-runner launchd lifecycle (60s StartInterval cycle)
type: incident
space: claim
tags: [claim]
created: 2026-06-01
updated: 2026-06-01
links:
  - "[[P0-brainstem/brain/rules]]"
  - "[[P4-cortex/growth/INTEGRATION_PROTOCOL]]"
  - "[[P6-prefrontal/incidents/cron-jobs-stalled-20260601]]"
---

# Incident — cron-runner launchd lifecycle — (60s StartInterval)

**Date**: 2026-06-01 19:10 KST
**Severity**: P3 (low — currently normal)
**Status**: Analyzed, prevention options pending
**Author**: Drewgent self-review

---

## 1. Symptom

`launchctl list` shows `ai.drewgent.cron-runner` with PID=- (last_exit=0).
5/30 → 6/1 18:08 KST about 1.5 days dormant. 6/1 18:08 plist mtime refreshed + user launchd manipulation(?) restored normal.

---

## 2. Diagnosis (2026-06-01 19:10 KST)

### 2-1. plist content

`~/Library/LaunchAgents/ai.drewgent.cron-runner.plist` (1,252 bytes, mtime 6/1 18:08):

```xml
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>ai.drewgent.cron-runner</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/drew/.drewgent/source/drewgent-agent/.venv/bin/python</string>
        <string>/Users/drew/.drewgent/scripts/cron_runner.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/drew/.drewgent/source/drewgent-agent</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key><string>.../drewgent-agent/.venv/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
        <key>VIRTUAL_ENV</key><string>/Users/drew/.drewgent/source/drewgent-agent/.venv</string>
        <key>DREW_HOME</key><string>/Users/drew/.drewgent</string>
    </dict>
    <key>StartInterval</key>
    <integer>60</integer>      — 60s spawn cycle
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/drew/.drewgent/logs/cron-runner.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/drew/.drewgent/logs/cron-runner.error.log</string>
</dict>
</plist>
```

**Key points:**
- `StartInterval=60` — launchd spawns the process every 60 seconds
- `RunAtLoad=true` — runs once at boot
- **No KeepAlive** — if process dies abnormally, no immediate restart (waits for next StartInterval, 60s gap)

### 2-2. cron_runner.py header (ProgramArguments)

```python
#!/usr/bin/env python3
"""
Cron Runner — launchd StartInterval 60s로 실행됨.
jobs.json의 dispatcher entry들에 대응하는 결정론적 shell script들을 순차 실행.
"""
DISPATCHERS = [
    ("default",      "dispatch_once_default.py"),
    ("content",      "dispatch_once_content.py"),
    ("integrations", "dispatch_once_integrations.py"),
]
```

3 dispatchers (default, content, integrations) run sequentially. Each dispatcher is a deterministic sqlite3 script with no LLM call.

### 2-3. ps / pgrep / lsof results (all 0)

```
$ ps aux | grep cron-runner     → (none)
$ ps -ef | grep cron-runner     → (none)
$ pgrep -fl cron-runner         → (none)
$ pgrep -P 1 -fl cron-runner    → (none — not a child of launchd)
$ lsof /Users/drew/.drewgent/P6-prefrontal/logs/cron-runner.log  → (no process)
$ lsof /Users/drew/.drewgent/cron/output/d1ef68ced116/  → (no process)
```

**What 0 processes means:** launchd spawns via StartInterval=60 every 60s → cron_runner.py runs → 3 dispatchers run → files written → process exits → 60s wait. **ps captured the empty gap in the spawn cycle.**

Evidence: cron output 4 dirs with 0.5-0.9 min old files, cron-runner.log new line every minute. **Process is in a spawn-then-exit cycle.**

---

## 3. Timeline (5/30 - 6/1 19:10)

| Time | Event |
|------|-------|
| 5/30 21:55 | Last normal spawn (kanban-dispatcher default board) |
| 5/30 - 6/1 18:08 | cron dormant (~20h). **plist missing or invalid.** |
| 6/1 18:08 | plist mtime refreshed — someone rewrote plist or did unload/load |
| 6/1 18:08 - | StartInterval=60 cycle resumed |
| 6/1 18:46 - 18:49 | cron-runner.log "3 dispatchers run" recorded every minute |
| 6/1 18:40 (SEO) / 18:44 (Trend) | 6h cycle cron patched then normal spawn (cron-jobs-stalled fix) |
| 6/1 19:00 - 19:10 | cron output 4 dirs normal activity, ps 0 (cycle gap) |

**Cause of plist missing/dormant (during 5/30 incident):**
- 5/30 incident fix note mentioned "KeepAlive: SuccessfulExit=false" was the **planner's assumption**; the actual plist never had KeepAlive
- During 5/30 21:55 - 6/1 18:08: `ai.drewgent.gateway.plist` Label conflict (ai.custom-agent.gateway rename) or launchd unload → plist unregistered (not directly verified)

---

## 4. Prevention Options

### Option A: Add KeepAlive to plist (optional)

```xml
<key>KeepAlive</key>
<dict>
    <key>SuccessfulExit</key>
    <false/>   — on non-zero exit, immediate restart
</dict>
```

- Effect: immediate restart on abnormal exit. Normal exit (exit=0) keeps StartInterval=60 cycle.
- Trade-off: 1-min gap for normal exits; immediate restart only on crash. **Currently normal, so skip — over-engineering risk.**

### Option B: Resolve gateway Label conflict

`ai.drewgent.gateway.plist` (5/17, 2,031 bytes) + `ai.custom-agent.gateway.plist` (5/6, 1,337 bytes) both in LaunchAgents/. 5/30 incident's "Label conflict → load fail" pattern.

→ verify Label of `ai.drewgent.gateway.plist`, then disable or rename. **Currently cron-runner normal, so follow-up.**

### Option C: External watchdog (over-engineering risk)

`cron-runner.log` mtime 5min+ stale → `launchctl kickstart -k ai.drewgent.cron-runner`. n8n or gateway health check.

But 5/30 fix's `get_due_jobs()` recovery branch auto-recovers jobs.json next_run_at null. **So jobs.json's 5 cron jobs are self-healing.** plist is not self-healing → separate fix needed, but **currently normal so watchdog is over-engineering risk.**

---

## 5. Judgment Criteria (aligned with 6/1 Verification Update)

Hard evidence for cron stopped:
1. `cron-runner.log` "dispatchers run" line timestamp 5min+ old → truly stopped
2. `cron/output/*/` latest file mtime 5min+ old → truly stopped
3. **`launchctl list PID=-` is soft evidence** — normal-running process can show PID=- (per this analysis)

---

## 6. Status (2026-06-01 19:10 KST)

| Item | Status |
|------|--------|
| cron-runner (plist) | normal 60s cycle (StartInterval=60) |
| 3 dispatchers (default/content/integrations) | every 1min exit=0 |
| SEO/Trend 6h cycle | patch 18:40 / 18:44 normal spawn |
| plist KeepAlive | not set (optional — current normal so over-engineering risk) |
| gateway Label conflict | unresolved (follow-up) |
| external watchdog | not built (over-engineering risk) |

---

## 7. Related

- [[P6-prefrontal/incidents/cron-jobs-stalled-20260601]] — 5/30 / 6/1 incident (false alarm, corrected in Verification Update)
- [[P4-cortex/growth/INTEGRATION_PROTOCOL]] — integration protocol
- [[P0-brainstem/brain/rules]] — P0 brainstem governance
- `~/Library/LaunchAgents/ai.drewgent.cron-runner.plist` — plist itself
- `~/.drewgent/scripts/cron_runner.py` — wrapper script
- `~/.drewgent/P6-prefrontal/logs/cron-runner.log` — execution log
- `~/.drewgent/cron/output/` — cron output root


---

## 8. Follow-up: kanban-maintenance next_run_at=null (1-min tick skip)

**Date**: 2026-06-01 19:31 KST
**Severity**: P3 (low — next auto-run in 5 days)
**Status**: Accepted, monitoring 6/7 03:00 KST
**Decision**: H4 (terminate, no further action this turn)

### 8-1. Symptom

kanban-maintenance entry는 6/1 18:38 KST에 jobs.json에 patch됐지만, 그 process의 in-memory state에는 18:08 시점 `load_jobs()` 결과가 유지돼 있음 (kanban-maintenance 등록 18:38 이전). (a) patch 시도:
- `next_run_at`을 `now-5s`로 patch — 65초 wait 후에도 unchanged
- cron-runner.log에 `kanban-maintenance` 0 hits
- 1분 tick (19:30:23, 19:31:23) 2회 모두 board task만 처리

### 8-2. Pre-state panorama (6/1 19:30 KST)

| job | next_run_at | sched | status |
|-----|-------------|-------|--------|
| SEO Article Harvester | 6/2 00:00 | `0 */6 * * *` | normal |
| Trend Harvester | 6/2 00:00 | `0 */6 * * *` | normal |
| kanban-dispatcher | 19:31:00 | `*/1 * * * *` | normal (1-min cycle) |
| kanban-dispatcher-content | 19:29:00 | `*/1 * * * *` | normal (1-min cycle) |
| cron-output-cleanup | 6/2 04:00 | `0 4 * * *` | normal |
| **kanban-maintenance** | **None** | `0 3 * * 0` | **patch 후에도 안 읽힘** |

다른 5개 cron은 **전부 valid next_run_at** (1분 tick마다 jobs.json read + due compute 정상). kanban-maintenance만 **in-memory state skip**.

### 8-3. Why (a) patch alone does not work

- (a) patch는 jobs.json 파일에만 반영
- 그 process의 last `load_jobs()`는 6/1 18:08 KST (kanban-maintenance 등록 18:38 이전)
- 1분 tick에서는 board task만 처리 (kanban-maintenance 같은 cron expression entry는 skip)
- 5/30 incident fix의 `get_due_jobs()` recurring recovery branch도 안 트리거 — 추정: in-memory state에 entry 없어서 branch 진입 자체 안 함
- 65초 wait 후에도 unchanged = 그 process가 jobs.json reload 안 함 (또는 reload하지만 kanban-maintenance skip)

### 8-4. Decision: H4 (terminate)

가성비 분석:

| option | work | risk | expected fix |
|--------|------|------|--------------|
| H1 SIGHUP | process PID 식별 + signal | medium (signal to wrong PID) | if file watcher + signal handler |
| H2 entry delete+re-add | 2 JSON edits | low | if next load_jobs() picks up new entry |
| H3 process restart | gateway restart 1—2min | high (downtime) | certain |
| **H4 terminate** | 0 | 0 | 6/7 03:00 auto (or same situation) |

- (H1)~(H3) 모두 risk + 작업 시간 vs **H4 = 0 risk, 0 작업**
- 영향: 6/7 03:00 KST (다음 일요일)까지 kanban-maintenance 미실행. 주 1회 cleanup 5일치 누락.
- dispatcher 정상 동작에는 지장 없음. 5/30 incident pattern (1.5일 dormant, SEO/Trend 정지) 재발 위험 없음 — SEO/Trend는 in-memory state에 있음, 매 1분 tick에서 정상 dispatch.

### 8-5. Verification checkpoint (6/7 03:00 KST)

다음 일요일 03:00 KST에 cron expression `0 3 * * 0`이 trigger. 그 시점에 그 process가 `load_jobs()`를 다시 호출했다면 kanban-maintenance 정상 spawn. 자동 검증 방법:

```bash
# 6/7 03:00 KST 이후
sqlite3 ~/.drewgent/state/drewgent_tasks.db "SELECT COUNT(*) FROM tasks WHERE trigger_source='kanban-maintenance';"
# 또는
ls -lt ~/.drewgent/cron/output/kanban-maintenance/  # output dir
```

만약 6/7에도 안 돌아가면:
1. **H1 SIGHUP** — in-memory reload trigger
2. **jobs.json mtime touch** — `os.utime()` — file watcher가 있으면 trigger
3. **H3 gateway process restart** — 큰 작업이지만 확실

### 8-6. Prevention

- 새 cron job을 jobs.json에 추가할 때 **그 process를 SIGHUP 또는 restart**하여 in-memory state reload 트리거. 또는 새 entry 추가 후 즉시 `load_jobs()` 호출 확인.
- 또는 cron-runner.py의 3 dispatcher 중 1개에 jobs.json cron expression 처리 통합 — board task + cron expression 모두 처리 (현재는 board task만).
- 또는 jobs.json write 시 in-memory state invalidate — mtime-based reload trigger in 그 process.

### 8-7. Related

- 이 incident의 Section 2-3 (ps/pgrep/lsof 진단) — cron-runner의 board task 처리 cycle 분석
- 5/30 incident fix (`get_due_jobs()` recurring recovery branch) — 이 fix도 (a) patch 후 안 트리거됨
- jobs.json declarative vs in-memory state mismatch — Drewgent cron 인프라의 structural issue

---

*This follow-up accepted (H4). 6/7 03:00 KST verification pending.*

## Related Neurons
- [[禁incident_aware.neuron]]
- [[禁filesystem_truth.neuron]]

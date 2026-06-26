---
name: drewgent-runtime-checkup
title: Drewgent Runtime Checkup
description: Drewgent 코어 시스템 (AIAgent, signal, kanban, dispatcher, worker) 의 기본기를 점검하는 6-Phase 절차. docs와 reality mismatch 발견 시 methodology.
type: skill
space: growth
tags: [skill, checkup, runtime, verification]
created: 2026-06-01
updated: 2026-06-11
links:
  - "[[@action/gateway/drewgent-architecture-dataflow]]"
  - "[[@memory/kanban/KANBAN_INDEX]]"
  - "[[@identity/brain/Drewgent-brain/P0-brainstem/禁/禁filesystem_truth.neuron]]"
  - "[[@identity/brain/rules]]"
---

# Drewgent Runtime Checkup

Drewgent 코어 시스템의 "기본기"를 점검할 때 사용하는 표준 절차. 핵심 철학: **"docs에서 Done이라고 한 것 ≠ 실제 구현"**. 항상 filesystem ground truth 로 verify.

## When to Use

- "기본기 점검해줘", "코어 시스템 확인", "이거 진짜 작동해?" 류 요청
- P0/P1 review 문서가 "✅ Done"이라 한 항목 의심될 때
- Cron job / dispatcher / worker 가 silent failure 중인지 확인할 때
- Major refactor 후 회귀 점검
- 새 모델 / 새 환경에서 Drewgent 설치 직후 sanity check

## 6-Phase Checkup (in order)

### Workdir 주의
터미널 workdir 는 turn 사이에서 휘발됨. 모든 명령은 `cd ~/.drewgent/source/drewgent-agent &&` prefix 필수. 절대 workdir 에 의존하지 말 것.

### Phase 1 — Core Imports (1분)
AIAgent, signal_processor, context_compressor, brain_signals, event_bus 모두 import. **import 실패 = P0 즉시 보고**.

```bash
cd ~/.drewgent/source/drewgent-agent && source .venv/bin/activate
python3 -c "
from run_agent import AIAgent
from agent.signal_processor import get_signal_processor
from agent.context_compressor import ContextCompressor
from agent.brain_signals import get_signal_emitter
print('OK')
"
```

### Phase 2 — Persistent State Health (1분)
SQLite DB 무결성. FK ON. Status 분포.

```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('P2-hippocampus/kanban/state/drewgent_tasks.db')
conn.execute('PRAGMA foreign_keys = ON')
for r in conn.execute('SELECT status, COUNT(*) FROM tasks GROUP BY status'):
    print(r)
print('integrity:', conn.execute('PRAGMA integrity_check').fetchone())
"
```

기대값: FK violations 0, status 7종 (todo/ready/in_progress/blocked/completed/cancelled).

### Phase 3 — Brain Signal Accumulation (1분)
`signal_processor` 인스턴스 state 확인.

```bash
python3 -c "
from agent.signal_processor import get_signal_processor
sp = get_signal_processor()
print('violations:', len(sp._violation_history))
print('dangerous_ops:', len(sp._dangerous_ops_history))
print('workflows:', len(sp._workflow_history))
"
```

기대값: violation ≥ 1, dangerous_ops ≥ 0 (사용 패턴에 따라 다름). 0/0/0이면 signal event bus wiring 끊긴 것.

### Phase 4 — Dispatcher End-to-End (1분)
Cron이 1분마다 도는 dispatcher 직접 실행. ready task 없으면 0/0/0/0 정상.

```bash
python3 ~/.drewgent/scripts/dispatch_once_default.py
# 기대: "reclaimed=0 | claimed=0 | spawned=0 | skipped=0"
```

### Phase 5 — Tool Surface Verification (1분)
`toolsets.py`에 등록된 toolset과 실제 handler 연결.

```bash
python3 -c "
import toolsets
all_toolsets = toolsets.get_all_toolsets()
print('toolsets:', list(all_toolsets.keys()))
print('kanban tools:', all_toolsets.get('kanban', {}).get('tools', []))
"
```

기대값: kanban toolset 안에 13개 function (create/complete/block/unblock/claim/heartbeat/list/get/link/add_comment/get_events 등).

### Phase 5b — Token Estimation Spot-Check (1분, 필요시)
ContextCompressor / chunker 가 silent off-by-N 버그 만들기 쉬운 영역. 변경 후 반드시:

```bash
# 1. Token estimation 정확도 — dict/list 직렬화 + 빈 청크도 인덱싱
python3 -m pytest tests/test_context_compressor.py::TestTokenEstimation -v --no-header
# 기대: 4/4 pass. dict → json.dumps, list → len+str, str → len/4
# 0 pass면: source/drewgent-agent/agent/context_compressor.py 의 _estimate_tokens() 확인

# 2. Compression chunking — 1k 윈도우 세션 + DM topic 전환
python3 -m pytest tests/test_context_compressor.py -k "chunk or topic or window" -v --no-header
# 기대: 4/4 pass. CharacterTextSplitter 의 empty chunk 가 인덱싱되는지 확인

# 3. 주변 test file 도 함께 — fixture gap 발견용
python3 -m pytest tests/gateway/test_session_hygiene.py --no-header -q
# 한두 개 fail 이어도 AttributeError 면 fixture 문제 (다음 항목 참고), 진짜 버그 아님
```

**3-tier chunking 버그 이력** (2026-06-01):
- dict 를 str(dict) 로 estimate → 1000x overcount
- list 를 str(list) 로 estimate → 같은 문제
- CharacterTextSplitter 가 빈 청크를 skip → 인덱싱 누락

수정 패턴:
```python
def _estimate_tokens(text: str) -> int:
    if isinstance(text, dict): return _estimate_tokens(json.dumps(text))
    if isinstance(text, list): return sum(_estimate_tokens(t) for t in text) if text else 0
    return len(text) // 4
```

## CRITICAL DIAGNOSTIC — AttributeError in GatewayRunner

`object.__new__(GatewayRunner)` 기반 mock runner 테스트에서 자주 등장:

```python
AttributeError: 'GatewayRunner' object has no attribute '_session_manager'
AttributeError: 'GatewayRunner' object has no attribute '_dispatcher'
AttributeError: 'GatewayRunner' object has no attribute '_sentinel_guard'
```

**테스트에서 발생 = fixture 갭** (defer). GatewayRunner 가 decomp 됨에 따라 mock 이 새 속성을 모름.

**프로덕션 로그(gateway.log/errors.log)에서 발생 = 진짜 버그** — method extraction gap. 조사 필요.

### Production AttributeError 진단 흐름

1. `grep "def _Y\|async def _Y" gateway/run.py gateway/agent_cache.py` — 메서드가 어디로 갔는지 확인
2. `cd ~/.drewgent/source/drewgent-agent && git diff HEAD -- gateway/run.py | grep "^-.*def "` — 클래스에서 제거된 메서드 목록
3. 제거된 메서드가 다른 모듈에 standalone 함수로 존재하는지 확인
4. 존재하면 → **method extraction gap**: `self.method()` → `function(self, ...)` 변환 필요
5. `references/gateway-method-extraction-gap.md` 참조

### Fixture gap vs Real bug 구분

| 증상 | 컨텍스트 | 진단 |
|------|----------|------|
| `AttributeError: 'X' object has no attribute '_Y'` | test (pytest) | fixture 갭 (defer) |
| `AttributeError: 'X' object has no attribute '_Y'` | production log | **진짜 버그** — 조사 필요 |
| `assert X == Y` 실패 | test | 진짜 버그 (조사 필요) |
| `KeyError: 'Z'` | any | 진짜 버그 (DB/mapping 문제) |
| `TypeError: ... argument ...` | any | 진짜 버그 (signature mismatch) |
| Timeout / hang | any | 환경/순환 문제 (별도) |

### Phase 4b — Cron-Runner Wrapper Registration (필요시)

**Symptoms (문서엔 Done, 실제로는 silent)**:
- `jobs.json`에 cron job entry가 없는데 script는 `~/.drewgent/scripts/`에 존재
- `last_run_at`이 며칠 전에서 멈춤
- `launchctl list | grep drewgent` → ai.drewgent.gateway 또는 ai.drewgent.cron-runner plist 없음
- 3개 board dispatcher (default/content/integrations) 중 일부만 jobs.json에 등록됨

**원인**: jobs.json은 declarative한 record 일 뿐, 실제 실행은 **launchd plist + Python wrapper** 가 담당. jobs.json에 등록 안 된 script는 절대 자동 실행 안 됨.

**또는 반대 패턴 — LLM-based dispatcher가 script-based dispatcher blocking**:
`cron/scheduler.py:tick()`은 sequential `for job in due_jobs:` loop. LLM agent job
(d1ef68ced116, kanban-dispatcher)이 먼저 실행되면 API 시간 동안 tick loop block →
뒤 script job (drewgent-cron-runner-001)이 fire 못 함. 최대 26분 stall 검증됨.

**진단**: gateway log에서 "Running job" 순서 확인:
```bash
grep "Running job" ~/.drewgent/P6-prefrontal/logs/gateway.log | tail -20
# d1ef68ced116만 있고 drewgent-cron-runner-001 없으면 = tick loop block
```

**해결 (3단계)**:

1. **즉시 조치**: LLM-based job disable (중복일 경우). `cron_runner.py`가 모든 board를
   처리한다면 `d1ef68ced116`를 `enabled: false`.
2. **Systemic fix** (권장): `cron/scheduler.py:tick()`에서 **script jobs를 LLM jobs보다
   먼저 실행**. 예방적 fix로 이후 ALL LLM job이 dispatcher blocking 불가:
   ```python
   _script_jobs = [j for j in due_jobs if j.get("script")]
   _llm_jobs = [j for j in due_jobs if not j.get("script")]
   for job in _script_jobs + _llm_jobs:
       # ... existing loop body
   ```
3. **Cron-runner fire frequency 모니터링**: harmony check Layer 3.5b가 5분마다
   0 fire (= stall) 또는 ≥12 fire (= abnormal) 감지. Layer 3.5b 결과에 따라
   `drewgent_cron_watchdog.sh`가 자동 kickstart.

**Tick watchdog** (T4.3): `gateway/run.py:_start_cron_ticker`에서 각 tick의
elapsed time 측정, `tick_elapsed > 5 × interval` → warning log.
Outer try/except도 `logger.debug`→`logger.warning`으로 강화.

**참조**: `references/gateway-cron-ticker-diagnosis.md` — 3가지 failure mode 별 root cause (housekeeping try/except, sequential tick block, stale lock) + tick watchdog + fire-frequency detection + auto-kickstart.

**참조**: `references/gateway-platform-connection-diagnosis.md` — Gateway 프로세스는 실행 중이지만 플랫폼 연결 안 됨 (orphaned extracted method). `AdapterLoader.connect_all()` 무호출 진단 및 수정.

**참조**: `references/gateway-method-extraction-gap.md` — GatewayRunner 메서드가 standalone 함수로 추출되었지만 `self.method()` 호출이 업데이트 안 됨 (e.g. `_run_agent`). Production AttributeError 진단 및 수정.

---

### Phase 4c — Dead Worker Board 격리 (필요시)

**진단**:
```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('~/.drewgent/P2-hippocampus/kanban/state/drewgent_tasks.db')
for r in conn.execute('SELECT id, title, board, worker_pid FROM tasks WHERE status=\"in_progress\"'):
    print(r)
"
```

**판단 기준**:
- worker_pid != NULL + ETIME < 30s → 정상 (worker 처리 중)
- worker_pid != NULL + ETIME > 1h + ps에서 PID 없음 → DEAD, reclaim 필요
- board = "test" 또는 board = "default"이고 title = "Test ..." → **false alarm**: 격리된 test board, dispatcher 무관

**False positive 회피**:
- test/* board에 dead worker 격리돼 있으면 default dispatcher가 안 보는 게 정상
- board scope hardening v0.8.5 적용 후 cross-board reclaim 시도 없음
- 진짜 bug: production task (board=default/content/integrations) + real worker_pid + TTL expired

### Phase 6 — Integration Path Spot-Check (1분)

---

### Phase 7 — Vault Graph Health (1분, 필요시)

Obsidian vault `.drewgent/`의 wikilink graph 무결성 점검. **vault = agent의 장기 기억**. 링크가 끊어지면 agent가 관련 문서를 찾지 못함.

**진단**: `~/.hermes/scripts/drewgent_graph_gap_analysis.sh` 실행:
```bash
bash ~/.hermes/scripts/drewgent_graph_gap_analysis.sh
# 기대: "✓ all wikilinks resolve"
# ⚠ dangling: N → broken link 존재. 아래 복구 절차.
```

**복구 패턴**:
- **`.neuron` → `.md` 미인식**: Obsidian이 `.neuron` 파일을 markdown으로 인식 못 함
  → `~/.drewgent/.obsidian/app.json`에 `"extensionOverrides": [".neuron"]` 추가 (파일 rename 불필요)
- **frontmatter `links:` → body wikilinks 누락**: Obsidian Graph View가 frontmatter 링크를
  약하게 인식. `write_file` 또는 `patch`로 본문 하단에 `## Links\n- [[target]]` 추가.
- **bidirectional 부재**: incident doc → neuron 링크만 있고 역방향(neuron → incident) 없음.
  양방향 추가 시 Obsidian Local Graph에 양쪽 노드 모두 표시.
- **Monitor/ brain signal orphan**: `~/.drewgent/monitor/brain_signals_*.md` 파일들 (수천 개)
  → `brain_monitor.py:_deliver()`의 `_deliver_fallback()` 호출 제거 (생성 중단) +
    기존 파일 일괄 삭제 (`rm monitor/brain_signals_*.md`). **정보 손실 0** — gateway.log에 동일 데이터.

**검증**:
```bash
bash ~/.hermes/scripts/drewgent_graph_gap_analysis.sh --dangling-only
# ✓ all wikilinks resolve
```
**"✅ Done이라 doc에 적혀 있지만 진짜?"** — 이 phase가 가장 자주 함정 있음.

```bash
# 1. dispatcher가 spawn할 때 어떤 env를 worker에 넘기는지
grep -A 10 "subprocess.Popen" ~/.drewgent/scripts/dispatch_once_default.py
# 2. worker가 그 env를 어떻게 read하는지
grep -E "os\\.environ\\[" ~/.drewgent/scripts/run_kanban_worker.py
# 3. Python tool 코드에서 그 env를 참조하는지
grep -rln "KANBAN_WORKER_MODE" ~/.drewgent/source/drewgent-agent --include="*.py"
```

## CRITICAL PITFALL — Shell Env Var Pattern

Drewgent는 자주 **shell env로 subprocess에 mode를 전달**한다. Python 코드에 그 env var가 안 보일 수 있다. 이게 **"미구현"이 아니라 "정상 구현"** 인 경우:

| Env var | Where set | Where read | Why |
|---------|-----------|------------|-----|
| `KANBAN_TASK_ID` | `dispatch_once_default.py` (subprocess.Popen env=) | `run_kanban_worker.py` (os.environ) | dispatcher가 어떤 task 줄지 worker에게 알림 |
| `KANBAN_WORKER_MODE=1` | `dispatch_once_default.py` | `run_kanban_worker.py` | worker가 mode=1 감지하면 LLM bypass, 직접 sqlite3 |
| `KANBAN_BOARD` | dispatcher | worker | multi-board 라우팅 |
| `DREW_HOME` | parent process | worker | 경로 override |
| `KANBAN_WORKER_PID` | dispatcher | worker | spawn tracker |

**Rule of thumb**: "Python code에 안 보임" → "Not implemented" 결론 **금지**. 항상:
1. `~/.drewgent/scripts/*.py` 확인 (dispatcher / worker script는 `source/drewgent-agent` 밖)
2. `subprocess.Popen(env=...)` 의 `env.update({...})` dict 확인
3. `os.environ.get("VAR")` 호출 위치 확인
4. 그래도 0건이면 그때 "미구현" 결론

## Verification Examples

### Good (실제 구현 검증)
- dispatch_once_default.py: `env.update({'KANBAN_TASK_ID': task_id, 'KANBAN_WORKER_MODE': '1', ...})` ✓
- run_kanban_worker.py: `task_id = os.environ.get("KANBAN_TASK_ID")` ✓
- → 두 파일이 shell env로 연결됨. **정상 동작**

### Bad (false negative)
- Python 코드에 `KANBAN_WORKER_MODE` 없음 → "구현 안 됨" 보고
- (실제로는 shell env로 전달 중)
- → **잘못된 진단**

## False-Alarm Verification Methodology (user preference, 2026-06-10)

When a checkup reveals a "broken" thing, **the next move is verify-before-patch**. The user's preference expressed in the 6/10 session: don't accumulate follow-ups for false alarms, don't spend time fixing what's already fixed.

**Rule**: For every checkup finding, classify it before acting:

1. **Re-verify the symptom first** with a *counting* tool — `grep -c`, `lsof -i`, `ps aux`, `stat -f %z` for file sizes. The goal is to distinguish "the symptom is real" from "I read something in a log dump that looked like a symptom."

2. **Confirm with the actual port / path / PID**, not with a remembered or assumed one. `lsof -i :<port>` is the source of truth for which port a service binds.

3. **Drop findings that don't reproduce**. Mark them as "False alarm" in the report with the *specific verification* that disproved the symptom. Future agents reading the report know not to re-investigate the same false alarm.

4. **Example 6/10 F2**: "kanban-dashboard port 5555 HTTP 000" → re-verified: actual port is 8765, `curl http://localhost:8765/kanban` returns 200. No fix needed. Reported as "False alarm: wrong port number in checkup."

5. **Example 6/10 F3**: "run_agent.py line 6790 `NameError: api_start_time` recurring" → re-verified: `grep -c 'api_start_time is not defined' gateway.error.log` returns 0. The visual scan of a 9.6M-line log was an artifact, not a real signal. No fix needed. Reported as "False alarm: 0 occurrences in log."

6. **When to actually patch**: only after re-verification shows the symptom is real AND the root cause is in our code. Anything else is scope creep.

This is a quality bar, not an extra step. The 5 minutes of `grep -c` is cheaper than the hours of "fixing" a phantom bug.

## Internal-Tool Consolidation (user preference, 2026-06-10)

When a checkup produces follow-up work, ask: **"can any of these be handled by an existing internal tool?"** The user's framing on 6/10:

> "보류된 follow-up은 내부 기능으로 대체 가능한 건 그렇게 하고 정리하면 되지 않을까. 어떠니."

**Decision flow for each follow-up item:**

1. **Can an existing cron, watchdog, or skill handle this automatically?**
   - YES → wire it up now, mark follow-up as resolved
   - NO → continue to step 2

2. **Does the symptom actually reproduce on re-verification?** (See "False-Alarm Verification Methodology" above.)
   - NO (false alarm) → drop the follow-up entirely
   - YES → continue to step 3

3. **Is this a real reliability fix, or scope creep?**
   - Reliability fix → keep in incident doc section 6.5 "Open (deferred)"
   - Scope creep → drop it

**Concrete 6/10 examples:**
- F1 (n8n plist missing) → step 1 YES (memory had 6/1 plist template). Consolidated: rewrote + bootstrap. Done.
- F2 (port 5555) → step 2 NO. False alarm. Dropped.
- F3 (api_start_time) → step 2 NO. False alarm. Dropped.
- "log rotation" (NEW follow-up surfaced during F1-F3) → step 1 NO (no existing tool), step 3 real reliability → step 1: write the tool. Consolidated: `drewgent_log_rotate.sh` + cron registration. Done.

**Why this matters**: a long follow-up list signals "we're not done, we're not sure if we're done, please come back later." Consolidating follow-ups into the existing system — or proving they're false alarms — makes the incident closure real and the run history clean.

## Honest Assessment Over Optimism (user preference, 2026-06-10)

When asked "is X working?" or "is this fully integrated?", the user prefers an **honest partial-credit answer** over a reassuring "yes, all good." The 6/10 follow-up session surfaced 5 architectural drift points between Drewgent and Hermes; the user asked directly whether "내부 아키텍처랑 공유도 되는거지?" (does the internal architecture share with hermes?). The right answer was:

> "기능 사용: yes. 내부 아키텍처 작동: yes. 깊은 공유: 부분적 — 5개 균열이 남았습니다. 그중 2개는 harmony check + neuron으로 자동화 가능, 3개는 architecture fix 영역입니다."

**Bad answer** (do not give): "네, 모두 잘 작동합니다." — overstates state, hides unresolved work, sets up future discovery of the same drift.

**Good answer** (use this template): "X works at [layer]. Y is partial because [specific drift]. Z is out of scope because [reason]." Then list 3-5 specific follow-ups with one-line classification each (resolved / false alarm / architecture fix / user decision needed).

**Why this matters**: the user asks "정직하게" / "솔직하게" expecting partial-credit truth. Optimism is treated as missing the question, not as courtesy. The cost of admitting "이건 architecture fix" is one user clarification; the cost of pretending "다 잘 됩니다" is the user discovering it later and losing trust.

**Rule**: never claim "완전히 통합" or "문제 없이" unless you have *all* layers verified in the current session. "표면적으로 작동 + N개 미해결" is the honest baseline.

## Daejeon-Je Based Autonomous Judgement (user preference, 2026-06-10)

When the user states a **대전제** (high-level premise) and asks for a plan, do NOT ask clarification questions for things the premise already answers. Decide and document the choice, even if it's a one-way door.

**User phrasing that signals this preference**:
- "내가 주는 대전제에 기반해 알아서 판단해"
- "설명이 부족한데, [대전제] ... 어떠니."
- "어떻게 생각하니" (after stating context)

**Anti-pattern** (do NOT do this):
> "다음 4가지 결정이 필요합니다: 1) D1 label 2) D3 memory 3) D5 scheduler 4) scope. 결정해 주세요."

**Right pattern**:
> "대전제: .drewgent 구조 유지 + hermes는 *내* 맥락에 맞춤. 적용:
> - D1 hermes → customize layer (PYTHONPATH hijack), upstream PR 안 함
> - D3 memory → .drewgent canonical, codex 무시 (policy)
> - D5 scheduler → unify (cron-runner plist bootout)
> - Scope → Phase 1+2+3 (5/13 + F1-F3 follow-up), 단 F2/F3는 false alarm verify 후 drop
>
> 이 결정으로 진행. 단, *유일한* 1-way door (memory single source)는 user 사전 confirm."

**What to defer to user**:
- 1-way door decisions (e.g. memory single source — once committed, hard to reverse)
- Decisions that destroy features per `禁/禁task_qa_gate.neuron` "Fixes that destroy the feature they secure"
- Decisions where the user's specific intent is genuinely unknowable (rare)

**What to decide autonomously**:
- Implementation details (e.g. "use `importlib.util` proxy" vs "monkey-patch directly")
- Order of operations within a phase
- "Drop the follow-up" calls (false alarm)
- "This is a follow-up, but it's scope creep → drop" calls

The user's expectation is: *I gave you the premise, you decided. Show me your work so I can audit, not so I can re-decide.* This is the difference between "여러분의 대리인" and "여러분의 mirror."

## "No Residue Left Behind" — Cleanup as Part of Execution (user preference, 2026-06-10)

When the user says "꼼꼼하게" or "찌꺼기 남기지 않게" (e.g. "꼼꼼하게. 찌꺼기 남기지 않게."), every step is:
- (a) **action** — make the change
- (b) **cleanup** — remove intermediate files, unused wrappers, dead code
- (c) **verify** — confirm no residue

**Residue patterns to clean**:
- Wrapper scripts that were useful for a brief moment but became redundant after the real fix
- `.pyc` files in `__pycache__/` (auto-regenerated, but listing them in commit output is noise)
- `.bak` files (keep at most one canonical `.bak` for the most-recent rollback target; remove earlier ones)
- Temp files in `/tmp/` from intermediate script invocations
- Imports/lines that the real fix made unreachable

**Verification commands**:
```bash
# After a multi-step task, run:
ls -la ~/.hermes/scripts/        # check for unused wrappers
find ~/.drewgent/customize -name '__pycache__' -type d  # check for python cache
find /tmp -name 'drewgent_*' 2>/dev/null  # check for temp residue
grep -cE 'set -u' ~/.hermes/scripts/*.sh   # check for bash 3.2 compat violations
```

**Honest cleanup log**: at the end of a multi-step task, the report should explicitly mention:
- "Removed: `drewgent-hermes` wrapper (redundant after `~/.local/bin/hermes` patch)"
- "Kept: `hermes.bak` (rollback target for one risk-bearing patch)"
- "Cache: `__pycache__/` left in place (auto-regenerated, removal = noise)"

**Why this matters**: a clean run history makes future agents' work easier. They can read the 6/10 incident doc and see "the fix left these artifacts, here's why" — vs. a polluted history where they have to guess "is this `__pycache__` from today's fix or yesterday's?"

## When You Find a Memory/Reality Gap — Write the Incident Doc IMMEDIATELY

A checkup finding that contradicts a memory entry is the highest-value signal in this whole skill. The 2026-06-10 checkup discovered that the 6/1 incident was recorded in memory as "복구 완료" but the actual system had been dead for 6+ days at that point. The earlier incident doc (5/30~6/2) was incomplete: it described the recovery as successful, but didn't track whether the recovery *stayed* successful.

**Required behavior when a checkup reveals gap between memory/incident-doc claims and reality:**

1. **Do NOT silently update memory to "still broken" or "no longer fixed"** — the gap is itself the data
2. **Write or update an incident doc under `P6-prefrontal/incidents/`** with the structure:
   - **What was claimed in memory/incident-doc** (cite the exact text + date)
   - **What the checkup actually found** (filesystem ground truth, hard evidence)
   - **When did the gap open** (best estimate from log mtimes, sessions, last_run_at)
   - **Why wasn't it caught** (which watchdog/alert path was missing)
   - **What changes prevent recurrence** (concrete list of plist edits, watchdogs, doc updates)
3. **Update memory** with both: (a) the original "incident fixed" claim, annotated with "see incident doc for actual follow-through" and (b) the new finding
4. **Tag the checkup session for `filesystem-truth-audit`** — the audit skill is the right tool to verify the original incident doc's filesystem claims were true at the time, vs. when they started becoming stale

**Why this matters:** A future agent reading memory sees "5/30 incident fixed" and skips the diagnostic. A future agent reading "5/30 incident fixed; see P6-prefrontal/incidents/cron-jobs-stalled-20260601.md section 8 for follow-through — actual recurrence observed on 6/10, see incident-cron-runner-gap-20260610.md" gets the full context. The second memory is harder to write but more honest.

**Three of the worst memory anti-patterns to avoid:**
- "복구됨" / "fixed" / "resolved" without a verification date and the file/last_run_at/etc. that confirms it
- "Should now work" — verify the change actually took effect (config.yaml committed, in-memory state reloaded, etc.)
- "Done per [incident doc]" without a wikilink to the doc

## Output Format

점검 끝나면 다음 형식으로 보고:

```
[P0] Core imports: OK
[P0] DB health: FK ok, status 분포 정상 (7종)
[P0] Brain signal: violations=N, dangerous_ops=M
[P0] Dispatcher: claimed=0 spawned=0 (정상, ready task 없음)
[P0] Tool surface: kanban toolset 13개 등록됨
[P1] X 발견: stdout=PIPE pipe full 위험
[P1] Y 발견: watchdog 부재 (TTL=1h lag)
[P2] Z 권장: docs 표현 정정
```

P0는 critical (한 줄로 fix 필요), P1은 단기 개선, P2는 장기 검토.

## Files Likely Worth Touching

점검 후 발견되는 P1 issue는 보통:
- `~/.drewgent/scripts/dispatch_once_*.py` (3개 board) — stdout=PIPE → DEVNULL 변경
- `~/.drewgent/scripts/run_kanban_worker.py` — watchdog 추가
- `P4-cortex/growth/KANBAN-REVIEW-20260520.md` — docs 표현 정정 ("Python mode 분기" → "shell env flag")

## Related

- [[@action/gateway/drewgent-architecture-dataflow]] — 전체 데이터 흐름
- [[@memory/kanban/KANBAN_INDEX]] — kanban 시스템 개요
- [[@identity/brain/Drewgent-brain/P0-brainstem/禁/禁filesystem_truth.neuron]] — "files are truth" 원칙
- `launchd-process-health-check` — **the skill that pairs with this one for infra-level findings**. Sub-pattern 6 in that skill (jobs.json patch has zero effect on a dead scheduler) is the meta-pattern for Pattern E in `cron-jobs-stalled`. The 6/10 incident response ran these two skills together.
- `cron-jobs-stalled` — for cron-stall-specific findings. Pattern E (silent scheduler death) added 2026-06-10.
- `~/.drewgent/P0-brainstem/brain/Drewgent-brain/P0-brainstem/禁incident_aware.neuron` (P0 policy) — auto-loads this skill + the 6/10 incident doc when watchdog fires or user requests "에이전트 상태 점검". Trip-wires the cross-layer diff path so the agent doesn't re-discover the 6 root causes from scratch.
- `references/2026-06-10-harmony-check-recipe.md` (under `launchd-process-health-check`) — the 4-layer cross-diff tool. Run after Pattern E recovery to verify the fix, or daily at 09:00 KST via cron. Includes the bash 3.2 pitfalls hit during 6/10 development.

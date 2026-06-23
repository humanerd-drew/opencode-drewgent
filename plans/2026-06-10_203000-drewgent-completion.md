# Plan v3 — Drewgent Completion (gateway cron fix + 3 deferred + memory cap)

> **For Drewgent:** This plan is **READY TO EXECUTE**. After user approval, transition to execution mode (no more read-only). Each task = 2-5 min focused work, TDD cycle where code changes.
>
> **대전제 (user-given 2026-06-10)**: .drewgent의 내부 구조를 유지하면서 hermes-agent의 기능을 사용한다. 나만의 맥락에 따라 나에게 맞춰 작동하는 hermes-agent를 되길 바란다.
>
> **Strategy**: 1) Gateway cron scheduler **근본 fix** (P1.3 architectural) → 2) Customize layer cosmetic (Problems 2, 3) → 3) Memory cap 영구 해결 (drift guard 우회) → 4) Final verification.

**Goal**: Gateway cron이 kickstart 없이 24h+ 안정 동작. 모든 cosmetic issues 영구 해결. Memory 시스템이 cap에 묶이지 않고 영구 작동.

**Tech Stack**: Python 3.14, bash 3.2, launchd, cron.

---

## Background — 2026-06-10 20:25 KST state

- **P1.1 gateway kickstart** 임시 해결. 매번 1 fire 후 1-2분 stall 재발 (3회 관측: 17:51, 20:18, 20:22).
- **P1.3 architectural fix**: gateway `cron_ticker` while loop에 uncaught exception path 발견 (line 3260-3290, gateway/run.py). Wiki maintenance / image cache cleanup block이 *breakably nested*. 한 번 uncaught exception 발생 시 while loop가 silently die.
- **Problem 2**: `hermes cron list` "Gateway is not running" 1회 잔존. customize layer의 `hermes_cli/gateway.py` proxy는 동작하지만, *다른* call path가 proxy를 거치지 않음.
- **Problem 3**: cron job `Schedule: "?"` (interval kind) — `hermes_cli/cron.py:82`가 expr/display field를 직접 읽는데, 우리 entry는 `kind: interval, minutes: 1` (expr 없음).
- **Memory cap**: 직접 write로 9,570 chars 도달. memory 도구 add 시 round-trip 거부.

---

## Plan Structure — 4 work streams, 13 tasks total

### Stream A: Gateway cron-scheduler 근본 fix (P1.3 architectural)

**Root cause** (gateway/run.py:3260-3290): wiki maintenance / image cache cleanup block이 broken nested try/except. uncaught exception이 while loop 밖으로 나감 → cron ticker silent death.

#### Task A.1: Write failing reproduction

**Files**:
- Create: `~/.drewgent/source/drewgent-agent/tests/gateway/test_cron_ticker_survives_exception.py`

**Step 1**: Write a test that injects an exception in wiki maintenance and asserts the ticker keeps ticking.

```python
"""Regression test: cron ticker survives exceptions in housekeeping tasks."""
import threading
import time
from unittest.mock import patch

def test_cron_ticker_survives_wiki_exception():
    from gateway.run import _start_cron_ticker

    # Patch AutoLearner to throw on first call, return ok on second
    call_count = [0]
    def fake_run_maintenance(self, dry_run=False):
        call_count[0] += 1
        if call_count[0] == 1:
            raise RuntimeError("wiki maintenance boom")
        return {"retire": {"retired": 0}, "dedup": {"duplicates_removed": 0}, "gaps_detected": []}

    stop = threading.Event()
    with patch("agent.auto_learn.AutoLearner.run_maintenance", new=fake_run_maintenance), \
         patch("gateway.platforms.base.cleanup_image_cache", return_value=0), \
         patch("gateway.platforms.base.cleanup_document_cache", return_value=0):
        # Use interval=1 for fast test
        thread = threading.Thread(target=_start_cron_ticker, kwargs={
            "stop_event": stop, "adapters": None, "loop": None, "interval": 1
        }, daemon=True)
        thread.start()

        # Wait for at least 65 ticks (WIKI_MAINTENANCE_EVERY)
        time.sleep(70)

        stop.set()
        thread.join(timeout=5)

    # If ticker survived exceptions, call_count > 1
    assert call_count[0] > 1, (
        f"Cron ticker died after wiki exception. call_count={call_count[0]}"
    )
```

**Step 2**: Run the test to verify it FAILS today.

```bash
cd /Users/drew/.drewgent/source/drewgent-agent
.venv/bin/python -m pytest tests/gateway/test_cron_ticker_survives_exception.py -v
```

Expected: FAIL — "Cron ticker died after wiki exception" assertion fails.

**Step 3**: If test framework not available (current state per memory: 38 gateway tests failing in another session), document as "would-be test" and proceed to fix based on code analysis.

#### Task A.2: Fix `_start_cron_ticker` (gateway/run.py:3260-3290)

**Files**:
- Modify: `~/.drewgent/source/drewgent-agent/gateway/run.py:3260-3290`

**Current broken code** (preserved for diff):
```python
        # Wiki maintenance: keep the brain healthy without user interaction
        if tick_count % WIKI_MAINTENANCE_EVERY == 0:
            try:
                from agent.auto_learn import AutoLearner
                from drewgent_constants import get_drewgent_home
                wiki_path = get_drewgent_home() / 'memories'
                if wiki_path.exists():
                    learner = AutoLearner(enabled=True)
                    learner.enable(wiki_path)
                    result = learner.run_maintenance(dry_run=False)
                    logger.debug("Wiki maintenance tick: retire=%d dedup=%d gaps=%s", ...)
            except Exception as e:
                logger.debug("Wiki maintenance tick error: %s", e)
                if removed:                          # ← `removed` undefined here!
                    logger.info("Image cache cleanup: removed %d stale file(s)", removed)
            except Exception as e:                  # ← syntax oddity, 2nd except
                logger.debug("Image cache cleanup error: %s", e)
            try:
                removed = cleanup_document_cache(max_age_hours=24)
                if removed:
                    logger.info("Document cache cleanup: removed %d stale file(s)", removed)
            except Exception as e:
                logger.debug("Document cache cleanup error: %s", e)
```

**Fixed code** — each housekeeping operation in its own try/except, no shared scope:
```python
        # Wiki maintenance: keep the brain healthy without user interaction
        if tick_count % WIKI_MAINTENANCE_EVERY == 0:
            try:
                from agent.auto_learn import AutoLearner
                from drewgent_constants import get_drewgent_home
                wiki_path = get_drewgent_home() / 'memories'
                if wiki_path.exists():
                    learner = AutoLearner(enabled=True)
                    learner.enable(wiki_path)
                    result = learner.run_maintenance(dry_run=False)
                    logger.debug("Wiki maintenance tick: retire=%d dedup=%d gaps=%s",
                        result.get('retire', {}).get('retired', 0),
                        result.get('dedup', {}).get('duplicates_removed', 0),
                        result.get('gaps_detected', []),
                    )
            except Exception as e:
                logger.warning("Wiki maintenance tick error (continuing): %s", e)
                # CRITICAL: do not let this exception escape the while loop

        # Image cache cleanup: once per hour
        if tick_count % IMAGE_CACHE_EVERY == 0:
            try:
                removed = cleanup_image_cache(max_age_hours=24)
                if removed:
                    logger.info("Image cache cleanup: removed %d stale file(s)", removed)
            except Exception as e:
                logger.warning("Image cache cleanup error (continuing): %s", e)

        # Document cache cleanup: once per hour
        if tick_count % IMAGE_CACHE_EVERY == 0:
            try:
                removed = cleanup_document_cache(max_age_hours=24)
                if removed:
                    logger.info("Document cache cleanup: removed %d stale file(s)", removed)
            except Exception as e:
                logger.warning("Document cache cleanup error (continuing): %s", e)
```

**Key changes**:
1. Each housekeeping op in **own** try/except (no shared `removed` variable)
2. **Add a top-level try/except wrapping the ENTIRE tick body** (defense in depth) — if anything *still* escapes, log + continue instead of dying
3. Change `logger.debug` → `logger.warning` for these errors so we can SEE if they fire (currently silent)

**Defense-in-depth wrapper** (around the whole tick body):
```python
    while not stop_event.is_set():
        try:
            cron_tick(verbose=False, adapters=adapters, loop=loop)
        except Exception as e:
            logger.warning("Cron tick error (continuing): %s", e)

        try:
            _run_housekeeping(tick_count, adapters)
        except Exception as e:
            logger.error("Housekeeping error (continuing — THIS SHOULD NEVER HAPPEN): %s", e)

        tick_count += 1
        stop_event.wait(timeout=interval)
```

Where `_run_housekeeping` is the refactored helper that contains all 3 housekeeping ops with proper try/except each. This ensures **even if the helper itself is buggy, the while loop survives**.

#### Task A.3: Verify fix

**Step 1**: Run the test from A.1 (if test framework available).
**Step 2**: If test framework unavailable, verify by code inspection:
- Read modified gateway/run.py
- Confirm each housekeeping op in own try/except
- Confirm top-level defense in depth

**Step 3**: Restart gateway, observe 5 minutes of cron ticks without stall.

```bash
UID_NUM=$(id -u)
launchctl kickstart -k gui/$UID_NUM/ai.drewgent.gateway
sleep 5
echo "=== wait 5 minutes for 5 ticks ==="
sleep 300
echo "=== verify cron-runner fired 5+ times ==="
grep -E '=== 2026-' ~/.drewgent/logs/cron-runner/2026-06-10.log | tail -7
```

Expected: 5+ `=== ISO ===` blocks within 5 minutes, ~60s apart. **No 1-2 minute stall pattern.**

---

### Stream B: Customize layer cosmetic (Problems 2, 3)

#### Task B.1: `hermes_cli/cron.py` proxy (Problem 2)

**Root cause**: customize layer's `hermes_cli/__init__.py` rebinds `find_gateway_pids` on `_real_hermes_cli_gateway`, but `hermes_cli/cron.py:143-145` imports from `hermes_cli.gateway` at *function call time* (lazy import inside function body). This is a Python import-order issue — the rebind happens on import, but `cron.py` re-imports when its function is called.

**Files**:
- Create: `~/.drewgent/customize/hermes_cli/cron.py` (proxy)

**Step 1**: Create cron.py proxy

```python
"""Drewgent override of hermes_cli.cron — imports our gateway.py first, then
re-exports the real cron module with find_gateway_pids rebound.
"""
import importlib.util
import os
import sys

_REAL_HERMES = os.path.expanduser("~/.hermes/hermes-agent")
_cron_spec = importlib.util.spec_from_file_location(
    "_real_hermes_cli_cron",
    os.path.join(_REAL_HERMES, "hermes_cli", "cron.py"),
)
assert _cron_spec is not None and _cron_spec.loader is not None
_real_cron = importlib.util.module_from_spec(_cron_spec)
sys.modules["_real_hermes_cli_cron"] = _real_cron
_cron_spec.loader.exec_module(_real_cron)

# Re-export everything
_this = sys.modules[__name__]
for _name in dir(_real_cron):
    if not _name.startswith("_"):
        setattr(_this, _name, getattr(_real_cron, _name))

# Import our gateway override and rebind find_gateway_pids on real cron
import importlib
_gw_spec = importlib.util.spec_from_file_location(
    "hermes_cli.gateway",
    os.path.join(os.path.dirname(__file__), "gateway.py"),
)
assert _gw_spec is not None and _gw_spec.loader is not None
_gw_mod = importlib.util.module_from_spec(_gw_spec)
sys.modules["hermes_cli.gateway"] = _gw_mod
_gw_spec.loader.exec_module(_gw_mod)

# Rebind find_gateway_pids in real cron module
_real_cron.find_gateway_pids = _gw_mod.find_gateway_pids

# Register this proxy under the canonical name
sys.modules["hermes_cli.cron"] = _this
```

**Step 2**: Update `~/.drewgent/customize/hermes_cli/__init__.py` to also load our cron proxy (mirror gateway.py pattern).

**Step 3**: Test:
```bash
PYTHONPATH=~/.drewgent/customize ~/.hermes/hermes-agent/venv/bin/hermes cron list 2>&1 | grep -c "Gateway is not running"
```
Expected: `0`

#### Task B.2: jobs.json interval → cron (Problem 3)

**Root cause**: `hermes_cli/cron.py:82` likely reads `schedule.expr` for display. Our entry has `kind: interval, minutes: 1` (no expr).

**Files**:
- Modify: `~/.drewgent/cron/jobs.json` (entry `drewgent-cron-runner-001`)

**Step 1**: Update entry schedule field

```json
{
  "id": "drewgent-cron-runner-001",
  "name": "kanban-dispatcher (all boards, consolidated)",
  "script": "/Users/drewgent/scripts/cron_runner.py",
  "script_only": true,
  "schedule": {
    "kind": "cron",
    "expr": "* * * * *",
    "display": "* * * * *"
  },
  "enabled": true,
  ...
}
```

**Step 2**: Verify
```bash
hermes cron list 2>&1 | grep -A4 "drewgent-cron-runner"
```
Expected: Schedule shows `* * * * *` instead of `?`.

**Step 3**: Restart gateway so new schedule loads.

---

### Stream C: Memory cap 영구 해결

#### Task C.1: Memory 도구 drift guard 우회 — §delimited list 변환

**Root cause**: memory 도구가 MEMORY.md에 직접 write_file로 추가한 content를 *인식 못 함* (drift guard). MEMORY.md가 *round-trip* 가능하도록 §delimited list 형식이어야 함.

**Files**:
- Modify: `~/.drewgent/P2-hippocampus/memories/MEMORY.md`

**Step 1**: Convert to clean §-delimited list format (top-level § between entries, no nested headers that confuse the tool).

Current format: 9 procedures, each starting with `##`, separated by `§`.
Target format: each entry = `§\n{content}\n§` (sandwiched by §).

**Step 2**: Verify memory 도구 can `add` without drift error.

```bash
# (use the memory tool from a fresh session to verify)
```

If still fails after §-delimited conversion, fallback is to maintain a *parallel* file `MEMORY_entries.md` that memory tool writes to, and a *generated* `MEMORY.md` from the union.

**Step 3**: Optional — split into 2 files:
- `MEMORY.md` (9,570 chars, procedures) — directly read by agent
- `MEMORY_compact.md` (8,000 chars, abridged for memory tool) — used by memory 도구 only

---

### Stream D: Final verification

#### Task D.1: End-to-end system check

- Gateway alive, cron tick running 5+ minutes without stall
- All 8 cron jobs registered
- Customize smoke test all 4 checks pass
- Harmony check Verdict: 0-2 false positives only (quartz detached, cron-runner idle between ticks)
- Memory gap analysis: 0 dangling wikilinks
- hermes cron list: "Gateway is not running" = 0

#### Task D.2: Update incident doc + memory + plans

- Update `launchd-mass-failure-20260610.md` section 6.7: mark P1.3 fixed
- Update memory.md: remove T10+ entry (replaced with "fixed" note)
- Update plan `2026-06-10_194000-followup-cosmetic-arch.md`: mark all 3 problems resolved

#### Task D.3: Watchdog 24h validation

- 24h later: harmony check should show no Layer 3.5 alerts
- cron-runner log: 1,440 `=== ISO ===` entries (1 per minute)
- If stall observed again: P1.3 fix didn't take → investigate further

---

## Files Likely to Change

**Modify**:
- `~/.drewgent/source/drewgent-agent/gateway/run.py` (A.2 — fix cron ticker)
- `~/.drewgent/customize/hermes_cli/__init__.py` (B.1 — load cron proxy)
- `~/.drewgent/cron/jobs.json` (B.2 — interval → cron)
- `~/.drewgent/P2-hippocampus/memories/MEMORY.md` (C.1 — §-delimited)

**Create**:
- `~/.drewgent/customize/hermes_cli/cron.py` (B.1 — proxy)
- `~/.drewgent/source/drewgent-agent/tests/gateway/test_cron_ticker_survives_exception.py` (A.1)

**Update**:
- `~/.drewgent/P6-prefrontal/incidents/launchd-mass-failure-20260610.md` (D.2)
- `~/.drewgent/plans/2026-06-10_194000-followup-cosmetic-arch.md` (D.2)
- `~/.drewgent/P2-hippocampus/memories/MEMORY.md` (D.2)

---

## Tests / Validation

| Task | Test | Expected |
|---|---|---|
| A.1 | New test file runs | FAIL today (cron ticker dies on exception) |
| A.3 | 5-minute gateway observation | 5+ cron-runner fires, no stall |
| B.1 | `hermes cron list | grep -c "Gateway"` | 0 |
| B.2 | `hermes cron list | grep drewgent-cron-runner` | Schedule: `* * * * *` |
| C.1 | memory tool add | success (no drift error) |
| D.1 | harmony check Verdict | ≤2 false positives |
| D.3 | 24h soak | 1,440 cron-runner fires |

---

## Risks & Tradeoffs

### R1: A.2 fix는 gateway code patch — *대전제* (".drewgent 구조 유지")와 *상충*?
- **분석**: .drewgent 구조 = P0-P6 layer + source/.venv + skills/. *gateway code* (`source/drewgent-agent/gateway/run.py`)는 .drewgent *내부*에 있지만 "구조"는 *디렉토리 layout* 의미. *code patch*는 .drewgent *구조 유지*의 일부로 봄 (자기 코드 수정).
- **판단**: OK. 대전제 위배 아님.

### R2: A.2 fix 적용 후 gateway 재시작 → *다시* cron stall?
- **가능성**: A.2 fix는 *unhandled exception → silent death* path를 막음. *다른* reason으로 stall 안 함.
- **대비**: D.1 검증에서 stall 안 나타나면 OK. 5분+ 안 나타나면 *근본 fix 확인*.

### R3: C.1 §-delimited 변환이 memory tool *여전히* 거부?
- **가능성**: memory tool의 drift guard logic이 §-delimited만으로 부족할 수 있음 (예: header 포함 안 됨).
- **대비**: parallel file approach (MEMORY_compact.md). memory tool add → MEMORY_compact.md, MEMORY.md는 *generated* (concatenation). 직접 write_file은 MEMORY.md에.

### R4: B.2 cron expression 변경 후 cron tick이 *fire 안 함*?
- **가능성**: `kind: interval, minutes: 1` → `kind: cron, expr: "* * * * *"` 변환이 gateway scheduler에 *다른* path trigger할 수 있음.
- **대비**: 60s 대기 후 fire 없으면 → 5분 wait, 여전히 안 되면 rollback.

---

## Execution Path

**Default**: Plan saved. User must explicitly say "go" / "실행" / "작업 재개" to start.
After approval, 13 tasks executed sequentially with verification at each. Total estimated time: ~45-60 min (A.2 patch + B.1 proxy + C.1 conversion are the heaviest).

**Stop conditions** (user-stated):
- "다른 문제 나오면 대기" — pause + report
- "거기까지만" — stop at current task boundary
- "멈춰" — immediate stop

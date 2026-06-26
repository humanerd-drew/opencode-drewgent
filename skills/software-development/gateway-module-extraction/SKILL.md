---
name: gateway-module-extraction
description: Extract modules from gateway/run.py (9,876 lines) into isolated files under gateway/. Covers stdlib name collision, runner circular reference, mock fixture sync order, and honest multi-session QA verdicts.
type: skill
space: outcome
tags: [skill, software-development, refactoring, drewgent-gateway]
created: 2026-06-01
updated: 2026-06-12
links:
  - "[[@identity/brain/rules]]"
  - "[[@memory/plans/gateway_decomposition_plan]]"
  - "[[software-development/python-large-file-patch-drewgent]]"
  - "[[software-development/codebase-refactoring]]"
  - "[[software-development/incremental-refactoring]]"
  - "[[software-development/codebase-structure-audit]]"
  - "[[software-development/requesting-code-review]]"
  - "[[@action/skills/SKILL-INDEX]]"
---

# Skill: Extracting Modules from gateway/run.py

## When to Use
When splitting GatewayRunner methods into separate modules under `gateway/` and the extracted class needs to read/write the runner's many attributes (adapters, session_store, hooks, task_manager, _running_agents, etc.).

## Three Things That Bite

### 1. stdlib name collision
`Dispatcher` clashes with `asyncio.Dispatcher` (or any stdlib symbol you forgot). Symptom: mysterious AttributeError or TypeError at import time, not at use time. Fix: prefix with the domain — `MessageDispatcher`, `SessionLifecycle`, `CronRunner`. Always grep stdlib before naming:

```bash
python3 -c "import asyncio; print(hasattr(asyncio, 'Dispatcher'))"
```

### 2. circular reference via runner
Extracted class needs `self.adapters`, `self._running_agents_ts`, etc. Two ways to give it access:

a) Pass runner in `__init__` and store as `self.runner`:
```python
class SentinelGuard:
    def __init__(self, runner):
        self.runner = runner  # NOT self.run_agent
    def is_sentinel(self, session_key):
        return self.runner._running_agents.get(session_key) is _SENTINEL
```

b) Pass the specific attributes the class needs (cleaner but verbose).

For Drewgent gateway, use (a) — 51 attribute references would make (b) painful.

### 3. Mock fixture sync order
After extracting modules, tests fail because `mock_gateway_runner` (built via `object.__new__(GatewayRunner)`) doesn't have the new attributes. **Order matters**:

1. First: replace the original method body with `self._new_module.method()` delegate
2. Then: update mock fixture to set the new attributes
3. Then: run tests

Doing fixture first leaves the real runner working but the mock broken. Doing tests first leaves everything broken. Delegate-first means the wiring is provably correct before any test changes.

- **`references/pyc-staleness-pitfall.md`** — `.pyc` staleness masking extraction errors (stale bytecode loads instead of modified source). Always clear `__pycache__` after modifying multiple Python files during extraction.

## Step-by-Step Procedure

1. **Pick the next extraction** by LOC + import surface. SentinelGuard (200 LOC, 3 attrs) before MessageDispatcher (580 LOC, 30+ attrs).
2. **Create skeleton module** with the class signature, leaving methods as `pass` or `raise NotImplementedError`.
3. **Copy method body verbatim** from run.py into the new module. Replace `self.foo` with `self.runner.foo`.
4. **Re-export at run.py module level** for backward compat if any test imports the old name:
   ```python
   # run.py
   from gateway.sentinel_guard import SentinelGuard  # noqa: F401
   ```
5. **Wire in `__init__`**: `self._sentinel_guard = SentinelGuard(self)` after the attrs it touches are set.
6. **AST parse check**:
   ```python
   import ast, glob
   for p in glob.glob('gateway/*.py'):
       try:
           ast.parse(open(p).read())
           print(f'OK  {p}')
       except SyntaxError as e:
           print(f'FAIL {p}: {e}')
   ```
7. **DO NOT replace the call site yet** — keep both the inline method and the new module working in parallel. This is a feature flag without the flag.
8. **Update plan doc** with what was extracted, what remains, exact LOC counts.

## Order of Extraction (Recommended)

| Priority | Module | LOC | Difficulty | Why first/later |
|----------|--------|-----|------------|-----------------|
| 1 | sentinel_guard | ~200 | LOW | Small, isolated, has its own tests |
| 2 | adapters | ~400 | LOW | Mostly config loading |
| 3 | stream_consumer | ~300 | LOW | Self-contained async iterator |
| 4 | session + session_manager | ~900 | MEDIUM | Many attrs touched |
| 5 | hooks | ~300 | LOW | Already a self-contained class |
| 6 | delivery | ~300 | LOW | Single-method router |
| 7 | task_manager | ~200 | LOW | Background task tracking |
| 8 | pairing | ~400 | MEDIUM | Touches session_store |
| 9 | channel_directory | ~300 | LOW | Read-mostly |
| 10 | cron_runner | ~400 | MEDIUM | Lifecycle + retry |
| 11 | **MessageDispatcher (was Dispatcher)** | ~580 | HIGH | Last — biggest, touches everything |

Save MessageDispatcher for last. It needs all the other modules in place to delegate to.

## Status (2026-06-11)

All modules listed above have been extracted. The extraction was completed incrementally over several sessions. The final completion pass (2026-06-11) fixed the following issues that had accumulated from incomplete extraction commits:

- **`GatewayRunner.start()`** — was reduced to `self._running = True`. Fixed by calling `self._adapter_loader.connect_all()`. Without this, platforms never connect after restart.
- **29 `_handle_*` handlers** — extracted to `session.py` and `voice.py` but never re-registered on `GatewayRunner`. Every slash command would `AttributeError`. Fixed by registering as class attributes after class definition.
- **`_run_agent`** — extracted to `agent_cache.py` but call sites still used `self._run_agent()`. Recursive call within the function itself also missed. Fixed by updating both call sites.
- **Missing lazy imports** — `import asyncio`, `_load_gateway_config`, `_platform_config_key`. Caused `NameError` on first user message. Fixed by adding module-level `import asyncio` and lazy imports inside function bodies.
- **`self`/`gw` parameter mismatch** — 29 functions had `self` in signature but `gw.xxx` in body. Fixed by renaming parameter to `gw`.
- **Circular import** — `session.py` importing `MessageEvent` from `platforms.base` which imports from `session.py`. Fixed with `from __future__ import annotations`.
- **Stale debris** — orphaned `@staticmethod` code left at end of `run.py`. Removed.
- **6 untracked files** — `adapters.py`, `agent_cache.py`, `config_loader.py`, `dispatcher.py`, `sentinel_guard.py`, `voice.py` — committed to git.

Refer to this skill's pitfalls if a future session needs to diagnose silent platform failures, broken slash commands, or import crashes after similar refactoring work.

## Verification After Each Extraction

```bash
# 0. ⚠️ CRITICAL: Clear stale bytecode BEFORE testing
# Stale .pyc files mask extraction errors — the old compiled code
# runs instead of your modified source. Always clear first.
find gateway/__pycache__/ -name "*.pyc" -delete
find gateway/__pycache__/ -empty -delete

# 1. AST parse all touched files
python3 -c "
import ast, glob
for p in glob.glob('gateway/*.py'):
    try:
        ast.parse(open(p).read())
        print(f'OK  {p}')
    except SyntaxError as e:
        print(f'FAIL {p}: {e}')
"

# 2. Import check
cd /Users/drew/.drewgent/source/drewgent-agent
python3 -c "from gateway.sentinel_guard import SentinelGuard; print('SentinelGuard importable')"

# 3. Check for orphaned extracted methods (defined but never called or registered)
echo "=== Orphaned startup methods ==="
grep -rn "connect_all\|\.start(" gateway/ --include="*.py" | grep -v __pycache__ | grep -v test_
echo "=== Expected: at least one call site in run.py ==="

echo "=== Orphaned handler methods ==="
grep -oP 'self\.(_handle_\w+)\(event\)' gateway/run.py | sort -u > /tmp/callsites
grep -oP 'GatewayRunner\.(_handle_\w+)' gateway/run.py | sort -u > /tmp/registered
echo "Missing registrations (should be empty):"
diff /tmp/callsites /tmp/registered || true

echo "=== Orphaned _run_agent call sites ==="
grep -n "_run_agent" gateway/run.py gateway/agent_cache.py | grep -v "import\|__pycache__"

# 4. Existing gateway smoke test: check platforms connect
# Restart gateway via launchd, then check logs
launchctl kickstart gui/$(id -u)/ai.drewgent.gateway 2>/dev/null || \\
    launchctl start ai.drewgent.gateway
sleep 6
grep -E "Connecting|connected" ~/.drewgent/logs/gateway.log | tail -5

# 5. Existing tests still pass (regression)
pytest tests/gateway/ -x -q 2>&1 | tail -20
```

## After Each Extraction — Git Workflow

```bash
# Add new files and commit
git add gateway/new_module.py gateway/run.py  # + other changed files
git commit -m "feat(gateway): extract $MODULE_NAME from GatewayRunner

- Extracted $MODULE_NAME ($LOC LOC) into gateway/$FILENAME
- Wired into GatewayRunner.__init__
- Updated mock fixtures in test_*.py
- Smoke tested: platforms connect, commands work"
```

Don't accumulate untracked extraction files. Each extraction should be committed immediately so the next extraction starts from a clean base.

## QA Evidence: Honest Verdict

When the work spans multiple sessions and you can't finish C3-C7 in one go, **write full-qa.json with `all_criteria_met: false`** and explain which criteria are deferred. Don't lie to pass the gate. `禁task_qa_gate` blocks delivery on false verdicts, but the alternative is shipping a partial refactor that looks complete in evidence.

Structure:
```json
{
  "criteria": [
    {"id": "C1", "met": true, "evidence": "..."},
    {"id": "C3", "met": false, "evidence": "Deferred to next session because..."}
  ],
  "met_count": 2,
  "total_criteria": 7,
  "verdict": "PARTIAL — X/Y met. Z blocked on ...",
  "blockers_for_delivery": ["C3 must complete before..."],
  "next_session_first_action": "Read gateway/run.py lines 1868-2447, copy verbatim into dispatcher.py..."
}
```

## Anti-Patterns

- Naming a class `Dispatcher`, `Loader`, `Manager`, `Handler` without checking stdlib
- Adding `from gateway.X import Y` at the top of run.py before the class is defined (circular import)
- Replacing the call site before the new module is wired in `__init__` (AttributeError at first request)
- Writing `all_criteria_met: true` when 5/7 criteria are deferred (the QA gate will catch it, but writing it dishonestly is worse)
- Using `mcp_patch` for ~580 LOC body replacement — even with `1` limit, the diff is too large. Use `read_file` + `write_file` for the whole method, or do it in chunks of ~50 LOC per patch

## Pitfall: Orphaned Internal Call Sites After Extraction

**Symptom**: Gateway starts, platforms connect, but the first user message triggers `AttributeError: 'GatewayRunner' object has no attribute '_run_agent'`.

**Root cause**: A method (`_run_agent`) was extracted from `GatewayRunner` into `agent_cache.py` as a standalone `async def _run_agent(gw, ...)`, but:
- The call site in `run.py` still said `await self._run_agent(...)` instead of `await _run_agent(self, ...)`
- A recursive call within the extracted function itself still said `await gw._run_agent(...)` instead of `await _run_agent(gw, ...)`

**Prevention — after extraction, grep ALL call sites**:

```bash
# Find EVERY reference to the extracted method name
grep -rn "_run_agent" gateway/ --include="*.py" | grep -v __pycache__ | grep -v test_

# Three categories to check:
# 1. External call sites (in run.py or other modules): must use new function call
# 2. Internal/recursive call sites (within the extracted function itself): also must use new function call
# 3. Comments mentioning the old name: cosmetic, safe to leave
```

### Pitfall: Method-called-as-standalone (self/gw parameter mismatch)

**Symptom**: Extracted function signature uses `self` as first parameter, but function body references `gw.xxx`. The original was a class method (`def _handle_X(self, event)`) that was copied verbatim, and a find-replaced `self.` → `gw.` was applied to the body but NOT to the parameter.

**Detection**: After extraction, check parameter name vs body references:

```bash
# Find functions where param is 'self' but body uses 'gw.'
grep -n "^async def.*self" gateway/session.py gateway/voice.py | head -20
grep -n "gw\." gateway/session.py gateway/voice.py | head -5
```

**Fix**: Rename the parameter from `self` to `gw`:

```python
# BEFORE:
async def _handle_reset_command(self, event: MessageEvent) -> str:
    session_key = gw._session_key_for_source(source)  # NameError: gw not defined

# AFTER:
async def _handle_reset_command(gw, event: MessageEvent) -> str:
    session_key = gw._session_key_for_source(source)  # OK
```

**Why this happens**: During extraction, the author used IDE find-replace to change `self.xxx` → `gw.xxx` in the body, but didn't rename the first parameter. Python then sees `self` (the GatewayRunner instance) bound to `self`, and `gw` is an undefined local → `NameError` at runtime.

**Rule of thumb**: After copy-pasting a method body out of a class, ALWAYS rename the first parameter from `self` to something domain-meaningful (typically `gw` for GatewayRunner, or the class name in lowercase). Body find-replace is not enough.

### Pitfall: Extracted handlers not re-registered on class (orphaned after extraction)

**Symptom**: Gateway starts, platforms connect, but slash commands (`/reset`, `/status`, `/help`) cause `AttributeError: 'GatewayRunner' object has no attribute '_handle_reset_command'`.

**Root cause**: A `_handle_*` method was removed from `GatewayRunner` and placed in a standalone module (`session.py` or `voice.py`), but the call sites in `run.py` still use `self._handle_reset_command(event)`. The extracted function exists as a module-level function but is not attached to the class.

**Fix — register as class attributes after class definition**:

In `run.py`, after the `GatewayRunner` class body ends, assign the functions as class attributes so Python's descriptor protocol treats them as bound methods:

```python
# At module level, after GatewayRunner class definition:
from gateway.session import _handle_reset_command, _handle_status_command, ...
from gateway.voice import _handle_approve_command, _handle_background_command, ...

GatewayRunner._handle_reset_command = _handle_reset_command
GatewayRunner._handle_status_command = _handle_status_command
GatewayRunner._handle_approve_command = _handle_approve_command
# ... all 29 extracted handlers
```

This works because regular Python functions are descriptors — accessing them via `instance.method` automatically binds the instance as the first argument (`gw`).

**Alternative — direct call style**: Instead of registering on the class, change all call sites from `self._handle_X(event)` to `_handle_X(self, event)`. This avoids monkey-patching but requires ~30 call site edits in run.py.

**Verification**:
```bash
# Check that all call sites found in run.py have a matching registration
grep -oP 'self\.(_handle_\w+)\(event\)' gateway/run.py | sort -u > /tmp/callsites
# vs registered methods:
grep -oP 'GatewayRunner\.(_handle_\w+)' gateway/run.py | sort -u > /tmp/registered
diff /tmp/callsites /tmp/registered  # should be empty: every call site has a registration
```

**The specific 6/11 failure chain**:
1. `_run_agent` method (7163 in old run.py) was extracted to `gateway/agent_cache.py` as `async def _run_agent(gw, ...)`
2. The primary call site in `_handle_message_inner` was missed: `await self._run_agent(...)` → `await _run_agent(self, ...)`
3. The recursive re-entry call inside `_run_agent` itself was also missed: `await gw._run_agent(...)` → `await _run_agent(gw, ...)`
4. → Gateway connected Discord fine, but crashed on first user message

## Pitfall: Missing Lazy Imports for Cross-Module References

**Symptom**: After extracting a function to a new module, the first invocation gives `NameError: name '_load_gateway_config' is not defined`.

**Root cause**: The extracted function referenced a module-level function (`_load_gateway_config`) that lives in the original `run.py`. Adding a top-level `from gateway.run import _load_gateway_config` in the new module creates a **circular import** because `run.py` already imports from the new module at its top level (line 36). When Python processes `run.py`, it pauses at the import of the new module, which then tries to import from `run.py` — but `_load_gateway_config` is defined later at line 388 and hasn't been defined yet.

**Fix — use lazy imports inside the function body**:

```python
# agent_cache.py — WRONG (circular import at module level):
from gateway.run import _load_gateway_config  # BOOM: NameError at import time

# agent_cache.py — CORRECT (lazy import inside function):
async def _run_agent(gw, ...):
    from run_agent import AIAgent
    import queue

    # Lazy import avoids circular dep with gateway.run
    from gateway.run import _load_gateway_config, _platform_config_key

    user_config = _load_gateway_config()
    ...
```

**Detection rule**: After extracting any function to a new module, check every name it uses:
1. Is the name defined in the new module? → OK
2. Is the name imported at the top of the new module? → Check for circular import
3. Is the name from the original module AND the original module imports from this new module? → **Must use lazy import inside the function body** (or `from __future__ import annotations` for type-only references)

**Fix options**:

**Option A — Lazy import inside function body** (for runtime references):
```python
async def _run_agent(gw, ...):
    # Lazy import avoids circular dep with gateway.run
    from gateway.run import _load_gateway_config, _platform_config_key
    user_config = _load_gateway_config()
```

**Option B — `from __future__ import annotations`** (for type annotations only):
```python
from __future__ import annotations  # makes ALL annotations lazy strings

# Now this works even if MessageEvent is imported in a circular chain:
async def _handle_reset_command(gw, event: MessageEvent) -> str:
    # MessageEvent annotation is never evaluated at import time
```

Use Option A for runtime values (functions, objects), Option B when the only cross-module reference is in type annotations. Option B is preferred for annotations because it's a single line and doesn't clutter function bodies.

### Pitfall: Method → standalone function (gw._xxx → xxx(gw,) mismatch)

**Symptom**: Extracted function was called as `gw._format_session_info()` in the body of another extracted function. But `_format_session_info` was also extracted — it's now a standalone `def format_session_info(gw)` in the same file. The call `gw._format_session_info()` tries to call it as a GatewayRunner method, which doesn't exist → `AttributeError`.

**Root cause**: During extraction, functions that used to be class methods calling OTHER class methods get copied verbatim. The `self._xxx()` calls become `gw._xxx()` after find-replace — but if `_xxx` was ALSO extracted, it's no longer a method on GatewayRunner. It's a standalone function now.

**Prevention — after each extraction, scan for misdirected gw.xxx() calls**:

```bash
# 1. Get all GatewayRunner methods
grep -P '^    (?:async )?def \w+\(self' gateway/run.py | grep -oP 'def \K\w+' | sort > /tmp/gw_methods

# 2. Get all standalone functions in extracted files
for f in gateway/agent_cache.py gateway/session.py gateway/voice.py; do
    grep -P '^(?:async )?def \w+\(' "$f" | grep -oP 'def \K\w+' >> /tmp/standalone
done
sort -u /tmp/standalone > /tmp/standalone_sorted

# 3. Find gw._xxx() calls where xxx is a standalone, not a method
grep -oP 'gw\.\K\w+(?=\()' gateway/agent_cache.py gateway/session.py gateway/voice.py | sort -u > /tmp/gw_calls
comm -12 /tmp/gw_calls /tmp/standalone_sorted > /tmp/misdirected
echo "=== Misdirected calls (should be empty) ==="
cat /tmp/misdirected
```

**Fix**: Change from method-style to function-style:
```python
# BEFORE (method-style, breaks because _format_session_info is standalone now):
session_info = gw._format_session_info()

# AFTER (function-style, calls standalone function correctly):
session_info = format_session_info(gw)
```

**Why the distinction matters**:
- `gw._xxx()` — use when `_xxx` is a REAL GatewayRunner method (defined with `def _xxx(self, ...)` inside the class body)
- `xxx(gw,)` — use when `xxx` is a standalone function (defined at module level) that takes `gw` as its first parameter

After extraction, many former methods become standalone — ALL their call sites need updating, not just the primary one.

## Systematic Post-Extraction Scan (do this ONCE after all extractions, not after each)

**Why this matters — user feedback from 2026-06-11**: During the final completion pass, fixing errors one-by-one as the user hit them resulted in 11 rounds of "fix one error → user hits next → fix next" over 10 hours. The user explicitly corrected the approach: *"하나씩 문제가 달라지는데, 전수조사 좀 해봐라"* (problems keep changing, do a thorough investigation). 

**Lesson**: After any multi-file refactoring, run a comprehensive scan BEFORE the user tests. Don't iterate on runtime errors. The scan below catches all the common extraction issues in one pass.

Run this ONCE after the extraction pass is complete. It catches all the issues before the user ever hits them.

Instead of fixing errors one-by-one as the user hits them ("하나씩 문제가 달라지는데"), run a comprehensive scan:

```bash
cd /path/to/project

echo "=== 1. Missing import: functions referenced but not imported ==="
for f in gateway/agent_cache.py gateway/session.py gateway/voice.py gateway/dispatcher.py; do
    echo "--- $f ---"
    grep -oP '\b[a-z_]+\(\)' "$f" | sort -u | while read -r call; do
        func="${call%()}"
        # Check if it's a known GatewayRunner standalone or internal function
        if grep -q "^def $func\|^async def $func" gateway/run.py; then
            # Check if it's imported from gateway.run
            if ! grep -q "from gateway.run import.*\b$func\b" "$f" && ! grep -q "from gateway.run import.*\b$func\b" <(grep -B5 "$func" "$f"); then
                echo "  ⚠ $call referenced in $f but NOT imported from gateway.run (may need lazy import)"
            fi
        fi
    done
done

echo "=== 2. Orphaned _handle_* registrations ==="
grep -oP 'self\.(_handle_\w+)\(event\)' gateway/run.py | sort -u > /tmp/callsites
grep -oP 'GatewayRunner\.(_handle_\w+)' gateway/run.py | sort -u > /tmp/registered
echo "Missing registrations:"
diff /tmp/callsites /tmp/registered || true

echo "=== 3. gw.xxx() calls where xxx is standalone ==="
grep -P '^    (?:async )?def \w+\(self' gateway/run.py | grep -oP 'def \K\w+' | sort > /tmp/gw_methods
for f in gateway/agent_cache.py gateway/session.py gateway/voice.py; do
    grep -P '^(?:async )?def \w+\(' "$f" | grep -oP 'def \K\w+' >> /tmp/standalone
done
sort -u /tmp/standalone > /tmp/standalone_sorted
grep -oP 'gw\.\K\w+(?=\()' gateway/agent_cache.py gateway/session.py gateway/voice.py | sort -u > /tmp/gw_calls
echo "Misdirected gw.xxx() calls (should be empty):"
comm -12 /tmp/gw_calls /tmp/standalone_sorted

echo "=== 4. Stale bytecode check ==="
for f in gateway/*.py; do
    pyc="gateway/__pycache__/$(basename "$f" .py).cpython-*.pyc"
    if ls $pyc 2>/dev/null; then
        for p in $pyc; do
            if [ "$(stat -f %m "$f")" -le "$(stat -f %m "$p")" ]; then
                echo "  ⚠ $(basename "$f"): .pyc NEWER than .py — will use stale bytecache!"
            fi
        done
    fi
done

echo "=== 5. Syntax check ==="
python3 -c "
import ast, glob
for p in sorted(glob.glob('gateway/*.py')):
    try:
        ast.parse(open(p).read())
        print(f'OK  {p}')
    except SyntaxError as e:
        print(f'FAIL {p}: {e}')
"
```

Run this ONCE after the extraction pass is complete. It catches all the issues before the user ever hits them.

### Pitfall: OpenCode provider prefix not stripped in gateway model path

**Symptom**: Gateway starts, Discord connects, but every user message triggers `HTTP 400: opencode-go/deepseek-v4-flash is not a valid model ID`. The same model works fine in CLI mode.

**Root cause**: CLI path normalizes model IDs via `normalize_opencode_model_id()` which strips the provider prefix (`opencode-go/deepseek-v4-flash` → `deepseek-v4-flash`). The gateway path calls `_resolve_gateway_model()` which returned the raw config string (`opencode-go/deepseek-v4-flash`) — sending the prefixed ID to the API causes HTTP 400.

**Fix**: Strip the provider prefix in `_resolve_gateway_model()`:

```python
# gateway/run.py
def _resolve_gateway_model(config: dict | None = None) -> str:
    ...
    # Strip provider prefix for opencode providers (opencode-go/X → X)
    for prefix in ("opencode-go/", "opencode-zen/"):
        if model.lower().startswith(prefix):
            return model[len(prefix):]
    return model
```

**Detection**: Check the model string passed to the API:
1. Match CLI behavior: `grep -n "normalize_opencode_model_id" cli.py` — the CLI normalizes at line ~1414
2. Check gateway equivalent: `grep -n "_resolve_gateway_model" gateway/run.py` — if it doesn't strip prefixes, it's missing the normalization step

**Prevention**: After any extraction that copies model-resolution logic, verify that provider-specific normalization (like OpenCode's prefix stripping) is also replicated. The extraction often copies the "what" (which config key to read) but not the "how" (which normalization to apply before returning).

#### Pitfall: Optional attribute accessed as `self.xxx` — use `getattr` with fallback

**Symptom**: After extraction, `AttributeError: 'GatewayRunner' object has no attribute 'session_id'`. The extracted code references `self.session_id` (or `gw.session_id`) which was never initialized in `__init__`.

**Root cause**: During extraction, a method that used `self.session_id` was copied verbatim from GatewayRunner. But `session_id` was never set as an instance attribute — it was probably intended to be passed as a method parameter or set per-message. The original code may have never exercised this path (e.g., a SessionRouter caching path that only activates after N messages).

**Fix**: Use `getattr` with a safe fallback string:

```python
# BEFORE (AttributeError if session_id not set):
route = router.route(self.session_id, user_message)

# AFTER (None-safe, uses fallback string for logging):
_sid = getattr(self, "session_id", None) or "unknown"
route = router.route(_sid, user_message)
```

**Prevention — after extraction, check all `self.xxx` attribute reads**:

```python
# 1. List ALL `self.xxx` accesses in the original class __init__
# 2. List ALL `self.xxx` reads in extracted methods
# 3. Any read-only access without a matching set → potential AttributeError at runtime

# Quick bash check:
cd /path/to/gateway
echo "=== self.xxx reads in extracted files (potential AttributeError) ==="
for f in agent_cache.py session.py voice.py; do
    grep -oP 'gw\.\K\w+(?=\()' "$f" | sort -u | while read attr; do
        # Check if it's set in GatewayRunner.__init__
        if ! grep -q "self\.$attr\s*=" ../run.py; then
            echo "  ⚠ gw.$attr() — NOT set in GatewayRunner.__init__ (may need getattr)"
        fi
    done
done
```

**The specific 6/12 failure chain**:
1. `_resolve_turn_agent_config()` referenced `self.session_id` which was never set in `GatewayRunner.__init__`
2. → `AttributeError: 'GatewayRunner' object has no attribute 'session_id'`
3. Fixed with `getattr(self, "session_id", None) or "unknown"`

### Pitfall: Provider resolved via stale env var instead of model config

**Symptom**: Gateway starts, model ID is correct, but every user message fails with `HTTP 402: out of credits` or connects to the wrong provider (e.g., OpenRouter instead of opencode-go).

**Root cause**: `_resolve_runtime_agent_kwargs()` called `resolve_runtime_provider(requested=os.getenv("HERMES_INFERENCE_PROVIDER"))`. This env var was never set in the gateway context, so `resolve_requested_provider()` fell through from `None` → config provider → `HERMES_INFERENCE_PROVIDER` → `"auto"` → OpenRouter (the default). The gateway silently used a different provider than the CLI.

The CLI works because it parses the model string `opencode-go/deepseek-v4-flash` in `cli.py:1414` and extracts the provider prefix (`opencode-go`) explicitly.

**Fix**: Parse the provider from the model config instead of relying on a likely-unset env var:

```python
def _resolve_runtime_agent_kwargs() -> dict:
    # Extract provider hint from model config
    # e.g. "opencode-go" from "opencode-go/deepseek-v4-flash"
    _cfg = _load_gateway_config()
    _raw_model = _cfg.get("model", {})
    if isinstance(_raw_model, str) and "/" in _raw_model:
        _provider_hint = _raw_model.split("/", 1)[0]
    else:
        _provider_hint = os.getenv("HERMES_INFERENCE_PROVIDER")

    runtime = resolve_runtime_provider(requested=_provider_hint)
    ...
```

**Detection**: Check what provider the gateway is actually using vs the CLI:

```bash
# Check CLI provider
grep "^model:" ~/.drewgent/config.yaml  # e.g. "opencode-go/deepseek-v4-flash"

# Check which provider the gateway resolves
grep "runtime.*provider" gateway/run.py  # look for resolve_runtime_provider call

# If it uses os.getenv("HERMES_INFERENCE_PROVIDER") without a config-based fallback,
# it will silently use "auto" → OpenRouter instead of the configured provider.
```

**Prevention rule**: After extracting credential resolution logic, verify the gateway path uses the SAME provider detection logic as the CLI. The common mistake is: CLI reads provider from the model string prefix → OK; gateway reads from an env var that nobody set → silently falls through to a different default.

## Pitfall: Orphaned Extracted Method (gateway platforms dead after restart — 2026-06-11)

**Symptom (silent)**: Gateway process is running (visible via `ps`), cron jobs fire normally, but no platform adapter connects. Log shows zero `"Connecting to"` / `"✓ connected"` messages after the last restart.

**Root cause**: Module extraction created `gateway/adapters.py` with `AdapterLoader.connect_all()` but **never called it from the startup flow**. The original `GatewayRunner.start()` method (which iterated platforms and connected each adapter) was replaced with a stub (`self._running = True`) during extraction. The extracted `connect_all()` method existed in the new module but had no call site in `run.py`.

**Prevention rule**: After extracting any method that was called during startup/shutdown lifecycle:

```bash
# 1. Find the original call site BEFORE extracting (grep the old code)
grep -n "\.start()\|connect_all\|\.connect()" gateway/run.py

# 2. After extraction, verify the new method is actually invoked:
grep -rn "connect_all\|\.start(" gateway/ --include="*.py" | grep -v __pycache__ | grep -v test_

# 3. Expected: at least one call site in run.py (the main runner) OR
#    in start_gateway() (the top-level entry point)
#    If zero call sites appear = orphaned method = gateway connects nothing
```

**The specific 6/11 failure chain**:
1. `GatewayRunner.start()` body was moved to `gateway/config_loader.py` as a standalone `async def start(self)` function (never wired)
2. `AdapterLoader.connect_all()` was added to `gateway/adapters.py` (complete and correct, also never wired)
3. `GatewayRunner.start()` in `run.py` was reduced to `self._running = True; return True`
4. → Gateway starts, cron runs, but no platforms ever connect

**Fix pattern**: Add the call site in `GatewayRunner.start()`:

```python
async def start(self) -> bool:
    self._running = True
    connected, enabled, nonretryable, retryable = (
        await self._adapter_loader.connect_all()
    )
    # log results
    return True
```

**Verification**: After fixing, restart gateway and check logs:
```bash
grep -E "Connecting|connected" ~/.drewgent/logs/gateway.log | tail -10
# Expected:
# Connecting to discord...
# ✓ discord connected
# Connecting to api_server...
# ✓ api_server connected
# Connected 3/3 platform(s)
```

**Related**: `drewgent-runtime-checkup` skill's `references/gateway-platform-connection-diagnosis.md` for the broader diagnostic pattern.

**See also**: `references/gateway-delegate-pattern.md` — lightweight subagent with focused toolset to avoid 151-tool context blowup.

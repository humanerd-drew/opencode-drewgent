# GatewayRunner Method Extraction Gap (2026-06-11)

Diagnostic pattern for when a method is extracted from `GatewayRunner` into a standalone function, but call sites aren't updated from `self.method()` to `function(self, ...)`.

## Relationship to Platform Connection Diagnosis

This is the **same class of bug** as the orphaned `connect_all` in `gateway-platform-connection-diagnosis.md`, but with a different symptom and fix surface. Both are incomplete module extractions from `GatewayRunner` during refactoring.

## Symptom

- Gateway starts and connects platforms fine
- First user message causes `AttributeError: 'GatewayRunner' object has no attribute '_run_agent'`
- The gateway log shows the error right after the agent tries to respond
- Discord bot appears online but doesn't respond to messages

## Root Cause

The old `GatewayRunner` had `_run_agent` as a method (line 7163 in the committed version). During refactoring, it was extracted to `gateway/agent_cache.py` as a standalone `async def _run_agent(gw, ...)` function. But:

1. **Call site in `run.py`** still uses `self._run_agent(...)` instead of `_run_agent(self, ...)`
2. **Recursive call inside `agent_cache.py`** still uses `gw._run_agent(...)` instead of `_run_agent(gw, ...)`

Both are the same mistake: the function changed shape (from method to standalone) but the callers weren't updated.

## Diagnosis

```bash
# Check if GatewayRunner is missing the method
grep "def _run_agent" gateway/run.py
# Expected: empty (method was extracted)
# If empty, confirm it exists in agent_cache.py:
grep "async def _run_agent" gateway/agent_cache.py
# Expected: shows the function definition

# Find all stale self-call sites
grep -n "self\._run_agent" gateway/run.py gateway/agent_cache.py
# Each hit needs to be converted from self.method() to function(self, ...)

# Also check for other extracted methods with same pattern — 
# compare current GatewayRunner methods against committed version:
cd ~/.drewgent/source/drewgent-agent
git diff HEAD -- gateway/run.py | grep "^[-].*def " | grep -v "^---"
# Shows methods that were removed from the class (likely extracted)
```

## Fix

### Step 1: Add import
```python
# in gateway/run.py imports section
from gateway.agent_cache import (
    ...
    _run_agent,   # ADD THIS
)
```

### Step 2: Fix call site in run.py
```python
# OLD (broken):
agent_result = await self._run_agent(
    message=message_text,
    ...

# NEW (fixed):
agent_result = await _run_agent(self,
    message=message_text,
    ...
```

### Step 3: Fix recursive call in agent_cache.py
```python
# OLD (broken):
return await gw._run_agent(
    message=pending,
    ...

# NEW (fixed):
return await _run_agent(
    gw,
    message=pending,
    ...
```

### Step 4: Restart and verify
```bash
kill -TERM $(pgrep -f "drewgent_cli.main gateway")
launchctl start ai.drewgent.gateway
sleep 5
# Send a test message on Discord — should respond now
```

## Distinguishing from Mock Fixture Gap

The existing CRITICAL DIAGNOSTIC section in SKILL.md covers `AttributeError` from **test mocks**. This is different:

| Context | Real Bug or Fixture Gap? |
|---------|--------------------------|
| `AttributeError` in **test** (pytest output) | Fixture gap — defer |
| `AttributeError` in **production** (gateway.log/errors.log) | Real bug — fix now |
| Error mentions `GatewayRunner` + a method that was in the old class | Extraction gap — likely real |
| Error mentions `MagicMock` or `AsyncMock` | Fixture gap — defer |

## Prevention

After any extraction from `GatewayRunner`:
1. `git diff HEAD -- gateway/run.py | grep "^[-].*def "` — list removed methods
2. For each removed method, check if it exists elsewhere as a standalone function
3. `git grep "self\.<method_name>"` — find all call sites that need updating
4. If the standalone function lives in a different module, update all imports too

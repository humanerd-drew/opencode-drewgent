# .pyc Staleness — Masked Extraction Errors After Refactoring

## Symptom

Gateway starts without errors, platforms connect, but user messages trigger `NameError`/`ImportError` for symbols that clearly exist in the source files. You add the missing import, restart, and the **same error persists**.

## Root Cause

Python caches bytecode in `__pycache__/*.pyc`. When a `.py` file is modified, Python recompiles only if the `.pyc` is **older** than the `.py`. If the `.pyc` was compiled during the extraction (when the file had different content) and the `.py` was later modified in ways that don't change the mtime enough, **the old `.pyc` is loaded instead of the new `.py`**.

This is especially dangerous during refactoring because:

1. You extract a method from `run.py` into `session.py` (both files modified)
2. The `.pyc` files are compiled from the **pre-extraction** versions (which had the methods inline)
3. On restart, Python loads the stale `.pyc` for `session.py` — which doesn't have the new `_handle_*` functions
4. But `run.py`'s `.pyc` also lacks the imports that wire them
5. The runtime error looks like "the fix didn't work" when the real problem is "the old compiled code is running"

## Detection

```bash
# Compare .py and .pyc modification times
stat -f "%Sm %N" gateway/__pycache__/session.cpython-*.pyc gateway/session.py
# If .pyc is NEWER than .py, stale cache is active
```

## Fix

```bash
# Clear ALL pycache for the modified files
find gateway/__pycache__/ -name "*.pyc" -delete

# Or touch the .py files to make them newer
touch gateway/session.py gateway/run.py

# Restart gateway
launchctl kickstart -k gui/$(id -u)/ai.drewgent.gateway
```

## Prevention

**After any extraction or refactoring that modifies multiple files, ALWAYS clear pycache before testing:**

```bash
# In the extraction verification checklist
find gateway/__pycache__/ -name "*.pyc" -delete
find gateway/__pycache__/ -empty -delete  # clean up empty dirs
```

Add this as the first step in the restart sequence after any Python source modification in the gateway directory.

## Why It Matters for Extraction

During the 2026-06-11 final completion pass, `session.py` had been modified ~7 days earlier (Jun 10 00:24) but the `.pyc` was compiled the same day. Later edits to `session.py` (adding imports, fixing signatures) were masked because the `.pyc` timestamp (Jun 10 00:24:36) was still **newer** than the modified `.py` (Jun 10 00:24:35). The `.pyc` had a 1-second advantage that lasted for days.

This is a **silent trap**: every test pass appears to fail with `NameError: name 'MessageEvent' is not defined` even after adding the import, because the old bytecode is being executed. The fix that "doesn't work" actually works — it's just not being loaded.

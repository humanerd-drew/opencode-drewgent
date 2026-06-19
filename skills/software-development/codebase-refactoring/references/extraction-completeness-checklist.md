# Method-to-Function Extraction: Completeness Checklist

When methods are extracted from a class to standalone functions in a separate module, these are the things that ALWAYS need to be checked — because they're what ALWAYS get missed.

## Important: scan FIRST, fix after

DO NOT fix extraction errors one at a time as they surface at runtime. The user experience is terrible ("하나씩 문제가 달라지는데" — problems keep changing one by one). Instead:

1. **Run the comprehensive scans** (sections 8-14 below) FIRST
2. **Collect ALL missing imports, wrong call sites, and parameter mismatches** into one list
3. **Fix everything at once** using batch scripts (execute_code with string replacement loops)
4. **Clear `.pyc` caches and restart** — one restart, not N restarts
5. **Only then test** — if a new error surfaces, it's a genuinely new issue, not one you should have caught in the scan

This approach turns a frustrating "whack-a-mole" debugging session into a single clean fix rollout.

## Checklist (apply to every extraction)

### 1. Imports in the NEW file
- [ ] All stdlib modules used in function bodies are imported (`asyncio`, `threading`, etc.)
- [ ] All type annotations used in signatures are imported (`MessageEvent`, `SessionSource`, `Platform`, etc.)
- [ ] All symbols from the ORIGINAL module that are still needed are imported (use lazy imports inside the function body if there's a circular import risk)

### 2. Imports in the ORIGINAL file
- [ ] The new module is imported so the functions are available at runtime
- [ ] No circular import created (A→B→A): use lazy imports (inside function bodies) to break the cycle
- [ ] For type annotations that would create a circular import, use `from __future__ import annotations` at the top of the file (PEP 563 — makes all annotations lazy strings)

### 3. Call sites
- [ ] `self.method_name(args)` → needs to become a callable on the class
- [ ] If the function is imported and assigned to the class, Python's descriptor protocol binds it automatically — `setattr(ClassName, name, func)` works
- [ ] If the function takes the instance as first param, the parameter should be named to match what the body uses (e.g. `gw` not `self` if body uses `gw.xxx`)

### 4. Parameter naming
- [ ] The first parameter of the extracted function receives the class instance
- [ ] If the body uses `self.xxx`, keep the param as `self`
- [ ] If the body was renamed to `gw.xxx`, rename the param to `gw` too
- [ ] If both `self` and `gw` appear, the extraction was inconsistent — pick one
- [ ] If the body uses NEITHER `self.` NOR `gw.` (only works with `event`, `adapter`, response params), rename `self` → `gw` for consistency (or `_` to mark unused). The instance is passed but ignored — make the signature consistent with other extracted functions.

### 5. Leftover code fragments
- [ ] After removing a method from a class, check the end of the file for orphaned indented blocks (partial extraction artifacts)
- [ ] These often look like `@staticmethod` or `def method_name(...):` that were only partially pulled out
- [ ] Always check `tail -30 file.py` for leftover debris

### 6. Registration on the class
- [ ] If the original code called `self.handle_command(event)`, the function must be attached to the class
- [ ] `setattr(ClassName, "handle_command", handle_command_function)` — do this AFTER the class is defined, at module level
- [ ] For 20+ handlers, use a dict loop or direct attribute assignment
- [ ] Place the registration block right after the class definition, not in a wrapper function
- [ ] Every function registered must ALSO be imported (`from extracted_module import function_name`) — otherwise the registration line itself raises NameError

### 7. Cached .pyc files
- [ ] Old `.pyc` files can mask import errors at module load time — delete them after changes
- [ ] If the gateway/process keeps running but imports fail, clear `__pycache__` directories
- [ ] `find path/to/__pycache__/ -name "*.pyc" -delete`

### 8. Cascading extraction: extracted files calling each other

When multiple methods are extracted from the SAME class to DIFFERENT files, extracted functions may call each other as `gw.method()`. These need to be checked:

- [ ] For every extracted file, scan `gw.xxx()` calls and verify `xxx` is either a real class method or a registered extracted function
- [ ] If `xxx` is defined in ANOTHER extracted file, add it to the class registration block too
- [ ] If `xxx` is defined in the SAME extracted file as a standalone function, change `gw.xxx(args)` → `xxx(gw, args)` (direct call, not method call)

```python
"""Detect cascading extraction issues: gw.xxx() calls where xxx is a standalone function."""
import re
from pathlib import Path

base = Path("/path/to/codebase")
extracted_files = ["file1.py", "file2.py", ...]

# All functions defined in extracted files as standalone (not class methods)
standalone_funcs = {}
for fname in extracted_files:
    content = (base / fname).read_text()
    for m in re.finditer(r'^(?:async )?def (\w+)\(', content, re.MULTILINE):
        standalone_funcs[m.group(1)] = fname

# Check all gw.xxx() calls in extracted files
issues = []
for fname in extracted_files:
    content = (base / fname).read_text()
    for m in re.finditer(r'gw\.(\w+)\(', content):
        call = m.group(1)
        line_num = content[:m.start()].count('\n') + 1
        if call in standalone_funcs:
            print(f"⚠ {fname}:{line_num} — gw.{call}() should be {call}(gw,) (defined in {standalone_funcs[call]})")
```

### 9. Function-name method calls (`gw._load_xxx()` → `load_xxx()`)

When extraction creates a standalone function but the old code calls it as `gw._function()`, the extracted function was never made into a real method:

- [ ] Check for `gw._load_xxx()` calls — if `_load_xxx` was a module-level function (not a class method), call it directly
- [ ] Common pattern: `gw._load_reasoning_config()` → `load_reasoning_config()` (standalone in config_loader.py)
- [ ] Common pattern: `gw._load_background_notifications_mode()` → `load_background_notifications_mode()` (standalone in config_loader.py)
- [ ] Common pattern: `gw._format_session_info()` → `format_session_info(gw)` (standalone in session.py)
- [ ] Common pattern: `gw._agent_config_signature(...)` → `agent_config_signature(...)` (standalone in same file)
- [ ] Common pattern: `gw._cleanup_session_checkpoint()` → `cleanup_session_checkpoint(gw)` (standalone in same file)
- [ ] Common pattern: `gw._evict_cached_agent(key)` → `evict_cached_agent(gw, key)` (standalone function)

### 10. Recursive call in extracted function

When the extracted function calls itself recursively:

- [ ] `gw._run_agent(args)` inside `_run_agent` → `_run_agent(gw, args)` (self-call, not class method call)
- [ ] The recursive call signature must match the standalone function's signature (first param is `gw`, not `self`)

### 11. Verify with a full import test

Clear all cached bytecode and test imports:

```bash
find path/to/__pycache__/ -name "*.pyc" -delete
python3 -c "from extracted_module import extracted_function"
python3 -c "from original_module import OriginalClass"
```

If any ImportError or NameError surfaces, fix it before proceeding.

### 12. Full static analysis scan

Before declaring the extraction complete, run a comprehensive scan for all remaining references.

**Scan 1: Original-module functions referenced but not imported in extracted files**

```python
"""Find all functions from the ORIGINAL module that are referenced but not imported in EXTRACTED files."""
import re
from pathlib import Path

base = Path("/path/to/codebase")
original_file = base / "original_module.py"
extracted_files = ["extracted1.py", "extracted2.py", ...]

# Collect all functions defined in the original module
original_funcs = {}
with open(original_file) as f:
    for i, line in enumerate(f, 1):
        m = re.match(r'^def (_?\w+)\(', line) or re.match(r'^async def (_?\w+)\(', line)
        if m:
            original_funcs[m.group(1)] = i

# For each extracted file, check which functions are used but not imported
for fname in extracted_files:
    fpath = base / fname
    if not fpath.exists():
        continue
    content = fpath.read_text()
    missing = []
    for func in original_funcs:
        if func not in content:
            continue
        # Check if imported from the original module
        pattern = rf'from original_module import[^)]*{re.escape(func)}'
        if not re.search(pattern, content):
            missing.append(func)
    
    if missing:
        print(f"  {fname}:")
        for func in sorted(missing):
            print(f"    ⚠ {func} ({content.count(func)}x references)")
```

Then for each missing function found:
- Add a lazy import inside the relevant function body (avoids circular deps)
- Verify by doing `python3 -c "import extracted_file"` — no ImportError = success

**Scan 2: ALL self._xxx() calls must resolve to class methods**

Run this AFTER the class is defined AND all registrations are in place:

```python
"""Find all self._xxx() calls and verify each resolves to a class method or registered function."""
import re
from pathlib import Path

content = Path("original_module.py").read_text()

# Collect ALL registered methods — both class-body definitions AND setattr registrations
gw_methods = set()
for line in content.split('\n'):
    m = re.match(r'    (?:async )?def (\w+)\(', line)  # class methods (with 4-space indent)
    if m:
        gw_methods.add(m.group(1))
    m = re.match(r'ClassName\.(\w+) = ', line)  # setattr registrations
    if m:
        gw_methods.add(m.group(1))

# Also catch @staticmethod definitions (no 'self' param)
for line in content.split('\n'):
    if '@staticmethod' in line:
        continue

# Find ALL self._xxx() calls — these must ALL resolve
called = set()
for m in re.finditer(r'self\.(\w+)\(', content):
    name = m.group(1)
    if name.startswith('_') and not name.startswith('__'):
        called.add(name)

missing = called - gw_methods - {'logger', 'config'}  # exclude attr lookups, not method calls
if missing:
    print(f"❌ {len(missing)} self._xxx() calls with no method:")
    for m in sorted(missing):
        print(f"  self.{m}()")
```

### 13. Check for uninitialized `self.xxx` attributes

When the extracted function accesses `self.some_attribute` (or `gw.some_attribute` after renaming), verify that the attribute is actually initialized in the class `__init__`:

```python
"""Find all self.xxx used in methods but not set in __init__."""
import re
from pathlib import Path

content = Path("original_file.py").read_text()

# Collect attrs set in __init__
init_attrs = set()
in_init = False
for line in content.split('\n'):
    if 'def __init__' in line:
        in_init = True
        continue
    if in_init and line.strip().startswith('def '):
        in_init = False
        continue
    if in_init:
        m = re.search(r'self\.(\w+)\s*=', line)
        if m:
            init_attrs.add(m.group(1))

# Collect attrs set via setattr registrations
for line in content.split('\n'):
    m = re.match(r'ClassName\.(\w+)\s*=', line)
    if m:
        init_attrs.add(m.group(1))

# Find self.xxx references (exclude private attrs)
all_refs = set()
for m in re.finditer(r'self\.(\w+)', content):
    name = m.group(1)
    if not name.startswith('_'):
        all_refs.add(name)

missing = all_refs - init_attrs
if missing:
    print(f"Attrs used but never init'd: {missing}")
    # Fix: either add to __init__ or use getattr() with fallback
```

**⚠ CRITICAL: The `None` → string slice trap.** When fixing uninitialized attributes with `getattr(self, "attr", None)`, any downstream code that does `attr[:8]` (string slicing) crashes with `TypeError: 'NoneType' object is not subscriptable`. Always pass a STRING fallback when the attribute is used in string operations:

```python
# WRONG: None crashes on string slice
_sid = getattr(self, "session_id", None)     # ❌ TypeError when downstream does _sid[:8]

# RIGHT: string fallback
_sid = getattr(self, "session_id", None) or "unknown"  # ✅ safe for string ops
```

**Common pitfalls:**
- `self.session_id` — never initialized on GatewayRunner, used in `_resolve_turn_agent_config()` for SessionRouter caching. Fix: `getattr(self, "session_id", None) or "unknown"` — SessionRouter uses it only as a cache key and for logging (`session_id[:8]`), so a string fallback is safe.
- `self._load_reasoning_config` — was called as method but was actually a module-level function `load_reasoning_config()`. The extraction created `gw._load_reasoning_config()` which doesn't exist. Fix: call the standalone function directly.
- `self._load_background_notifications_mode` — same pattern, module-level function called as method.

### 14. Self/gw parameter naming completeness scan

Run this to catch ALL functions where the body references `gw.xxx` but the parameter is `self` (or vice versa):

```python
"""Find functions where body uses 'gw.' but parameter is 'self' (or vice versa)."""
import re
from pathlib import Path

base = Path("/path/to/codebase")
extracted_files = ["file1.py", "file2.py"]

for fname in extracted_files:
    content = (base / fname).read_text()
    for m in re.finditer(r'^(?:async )?def (\w+)\((\w+)', content, re.MULTILINE):
        func_name = m.group(1)
        first_param = m.group(2)
        func_start = m.start()
        body_end = content.find('\n\n', func_start)
        body = content[func_start:body_end] if body_end > 0 else content[func_start:func_start + 500]
        uses_gw = 'gw.' in body
        uses_self = 'self.' in body
        neither = not uses_gw and not uses_self
        if uses_gw and first_param != 'gw':
            print(f"⚠ {fname}:{func_name} — body uses 'gw.' but param is '{first_param}'")
        if uses_self and first_param != 'self':
            print(f"⚠ {fname}:{func_name} — body uses 'self.' but param is '{first_param}'")
        if neither and first_param == 'self':
            print(f"⚠ {fname}:{func_name} — param is 'self' but body uses neither self nor gw (should be '_' or 'gw')")
```

**Important: This scan catches ALL functions**, not just `_handle_*` ones. Non-`_handle_*` extracted functions (`_send_voice_reply`, `should_send_voice_reply`, `_deliver_media_from_response`, `_handle_voice_channel_input`) are EASILY MISSED by regex patterns that only match `_handle_\w+`.

## 16. Post-extraction provider/model resolution divergence

After all extraction bugs are fixed, the gateway may use a DIFFERENT provider than the CLI even though both read the same config. This happens when:

- **CLI path** goes through `cli.py` → `normalize_opencode_model_id()` (strips `opencode-go/` prefix) → resolves provider from model string → uses `opencode-go` provider
- **Gateway path** goes through `_resolve_runtime_agent_kwargs()` → reads `HERMES_INFERENCE_PROVIDER` env var (unset = `None`) → `resolve_requested_provider(None)` → config `model.provider` (not set) → env `HERMES_INFERENCE_PROVIDER` (not set) → **returns `"auto"`** → resolves to **openrouter** (default)

The gateway silently uses OpenRouter while CLI uses opencode-go, causing:
- Different API consumption (different billing, different rate limits)
- Different model availability
- HTTP 402 (insufficient credits) on one path but not the other

### Detection

Compare the resolved provider between CLI and gateway:

```bash
# CLI: what provider does the CLI resolve?
grep "^model:" ~/.drewgent/config.yaml
# → "opencode-go/deepseek-v4-flash"  → provider = "opencode-go"

# Gateway: what does _resolve_runtime_agent_kwargs return?
grep "HERMES_INFERENCE_PROVIDER" gateway/run.py
# → os.getenv("HERMES_INFERENCE_PROVIDER") — NOT the config model!
```

### Fix: extract provider from model config, not env var

```python
# Before (wrong — reads env var, not config):
def _resolve_runtime_agent_kwargs():
    runtime = resolve_runtime_provider(
        requested=os.getenv("HERMES_INFERENCE_PROVIDER"),  # unset → "auto" → openrouter
    )

# After (correct — parses model config):
def _resolve_runtime_agent_kwargs():
    _cfg = _load_gateway_config()
    _raw_model = _cfg.get("model", {})
    if isinstance(_raw_model, str) and "/" in _raw_model:
        _provider_hint = _raw_model.split("/", 1)[0]  # "opencode-go/deepseek-v4-flash" → "opencode-go"
    else:
        _provider_hint = os.getenv("HERMES_INFERENCE_PROVIDER")
    runtime = resolve_runtime_provider(requested=_provider_hint)
```

### Also fix: strip provider prefix from model ID for opencode providers

```python
# Before:
def _resolve_gateway_model(config):
    model_cfg = cfg.get("model", {})
    if isinstance(model_cfg, str):
        return model_cfg  # "opencode-go/deepseek-v4-flash" — API rejects this

# After: 
    if isinstance(model_cfg, str):
        model = model_cfg
        # Strip provider prefix for opencode providers
        for prefix in ("opencode-go/", "opencode-zen/"):
            if model.lower().startswith(prefix):
                return model[len(prefix):]  # "deepseek-v4-flash" — API accepts this
        return model
```

### Root cause pattern

The provider resolution divergence is NOT an extraction bug — it's a **dual-codebase-path divergence**. The CLI and gateway were developed independently and each chose a different method to determine the provider:

| Resolution step | CLI (`cli.py`) | Gateway (`gateway/run.py`) |
|----------------|---------------|--------------------------|
| Read model | `opencode-go/deepseek-v4-flash` | `opencode-go/deepseek-v4-flash` |
| Strip prefix | ✅ `normalize_opencode_model_id` | ❌ missing |
| Provider source | Extracted from model string | `HERMES_INFERENCE_PROVIDER` env var |
| Fallback | config model → env | env → `"auto"` → openrouter |

The fix must be applied to BOTH the model string (`_resolve_gateway_model`) AND the provider resolution (`_resolve_runtime_agent_kwargs`) because they are independent code paths that both need to match the CLI behavior.

## 17. Post-extraction config/routing issues

After all extraction bugs are fixed, test the FULL code path — not just import and instantiation. Extraction errors can MASK pre-existing config bugs that only surface when the code path is exercised for the first time:

- **Model ID format mismatch:** If the extraction re-exposed a SessionRouter or model-routing codepath, the model ID format (`provider/model`) might be wrong for the downstream API. The extraction code is correct; the model configuration was always wrong but masked by the extraction bug.
- **Fallback chain:** If one model fails (HTTP 400), the agent tries fallbacks. Test that the fallback chain works end-to-end. 
- **SessionRouter worker route:** If the SessionRouter routes to a worker with a hardcoded model, that model MUST be in the provider's accepted model list. Hardcoded models (`deepseek-v4-flash`) that aren't in the provider's model catalog (`opencode-go` list) produce HTTP 400 errors.

**Fix strategy (not an extraction bug but surfaced by it):** If the worker route model isn't accepted by the API, disable the SessionRouter (`self._session_router = None`) to fall through to the working main model routing. Fix the worker model configuration as a separate task.

## Circular Import Resolution Patterns

### Pattern 1: Lazy imports (inside functions)

```python
# Instead of module-level:
from gateway.run import some_function  # may create circular import

# Use function-level lazy import:
async def my_function():
    from gateway.run import some_function  # resolved at call time
    result = some_function()
```

### Pattern 2: `from __future__ import annotations`

When type annotations reference a type that would create a circular import:

```python
# At the top of the file:
from __future__ import annotations

# Now all annotations are lazy strings — evaluated only when accessed
# This allows using MessageEvent, SessionSource, etc. in signatures
# without importing them at module level
async def handle_command(gw, event: MessageEvent) -> str:
    ...
```

This works because PEP 563 defers annotation evaluation. The annotation is only resolved when `typing.get_type_hints()` is called, or when runtime inspection happens.

### Pattern 3: Lazy import in register function

When the extracted functions need to be registered as methods on the class, but the class is defined in the original module:

```python
# At the end of the original module, AFTER the class definition:
def _register_handlers():
    from extracted_module import handler_func1, handler_func2
    OriginalClass.handler_func1 = handler_func1
    OriginalClass.handler_func2 = handler_func2

_register_handlers()
```

## Detection commands

```bash
# Find what changed
git diff --name-only

# Check for missing module-level imports in a file
grep -n "import " file.py | head -20

# Check for names used in type annotations that aren't imported
grep -n "MessageEvent\|SessionSource\|MessageType" file.py | grep -v "import\|from.*import"

# Check for leftover indented code at file end
tail -30 file.py

# Check for parameter naming inconsistency
grep -n "gw\.\|self\." file.py | head -20

# Find all functions removed from a class (compare committed vs current)
git diff HEAD -- original_file.py | grep "^-.*def _handle" | head -30

# Check if a file needs to be imported in a consuming module
grep -rn "import extracted_file\|from extracted_file" consuming_modules*.py

# Find uninitialized self.xxx attributes used in methods
python3 -c "
import re
c = open('file.py').read()
in_class = False
init_attrs = set()
for line in c.split(chr(10)):
    if 'class ' in line and ':' in line: in_class = True
    if in_class and 'def __init__' in line: in_init = True
    if in_init and line.strip().startswith('def '): in_init = False
    if in_init:
        m = re.search(r'self\.(\w+)=', line.replace(' ', ''))
        if m: init_attrs.add(m.group(1))
refs = {m.group(1) for m in re.finditer(r'self\.(\w+)', c) if not m.group(1).startswith('_')}
missing = refs - init_attrs - {'logger','config','adapters'}
if missing: print('Missing:', missing)
"
```

## Real example (Drewgent Gateway, 2026-06-11~12)

The `GatewayRunner` class had 30+ `_handle_*` methods and the `_run_agent` method extracted to separate files. The extraction left behind ALL of the following issues, which were found and fixed over ~10 hours of iterative debugging:

### Issues found (in order of discovery)

| # | Error | Root cause | Fix |
|---|-------|-----------|-----|
| 1 | No platforms connected | `connect_all()` never called from `GatewayRunner.start()` | Add `await self._adapter_loader.connect_all()` to `start()` |
| 2 | `_run_agent` not defined | Extracted to `agent_cache.py` but `run.py` still called `self._run_agent()` | Import + change to `_run_agent(self,)` |
| 3 | `asyncio` not defined | `agent_cache.py` lacked `import asyncio` | Add `import asyncio` |
| 4 | `_load_gateway_config` not defined | `agent_cache.py` referenced it without import | Lazy import inside function (avoids circular dep) |
| 5 | `_handle_reset_command` not found | 13 `_handle_*` functions extracted to `session.py` but not registered on `GatewayRunner` | Import + register all 29 handlers |
| 6 | `_resolve_gateway_model` not defined | Referenced in 3 extracted files without import | Add lazy imports |
| 7 | `gw` not defined in `should_send_voice_reply` | Parameter named `self` but body used `gw.xxx` | Rename `self` → `gw` in signature |
| 8 | `self.session_id` AttributeError | `_resolve_turn_agent_config()` accessed `self.session_id` which was never set | `getattr(self, "session_id", None) or "unknown"` |
| 9 | `NoneType` not subscriptable (`session_id[:8]`) | `None` passed to string slice in logging | Used `"unknown"` fallback (not `None`) |
| 10 | HTTP 400 model ID error | SessionRouter worker route model not in opencode-go model list | Disabled SessionRouter (`_session_router = None`) |

### Key lessons

1. **Switch to comprehensive audit at error #2.** After fixing error A (`connect_all`), error B (`_run_agent`) appeared. That was THE signal to stop and scan all files, not to keep fixing one-by-one. The cascade went to 10 distinct errors over 10 hours. A pre-audit would have caught all 10 in one pass.

2. **Non-`_handle_*` extracted functions are easy to miss.** The `should_send_voice_reply`, `_send_voice_reply`, `_deliver_media_from_response`, `_handle_voice_channel_input` functions have different naming patterns and are skipped by regex that only matches `_handle_\w+`. Use the parameter-naming scan (section 14) which catches ALL functions.

3. **Registration is NOT the same as import.** A function can be registered on the class (`GatewayRunner.func = func`) but NOT imported (`from module import func`), producing a `NameError` when the registration line executes. Always verify BOTH.

4. **The `None` → string slice trap is insidious.** `getattr(self, "attr", None)` seems safe but crashes on downstream `attr[:8]`. Always provide a string fallback for attributes used in string operations.

5. **Post-extraction bugs can mask pre-existing config issues.** The SessionRouter worker model was ALWAYS broken — it just never ran because `self.session_id` crashed first. After fixing the extraction bugs, the model error surfaced. This is not an extraction bug — it's a pre-existing config bug revealed by the fix.

## Cascade trap: when to switch to comprehensive mode

**Switch signal:** When the SECOND distinct error appears after the FIRST fix, do NOT fix error B. Instead, IMMEDIATELY switch to comprehensive cross-file audit.

```
Good (normal debugging):  Fix error A → test → PASS ✅
Bad (cascade trap):       Fix error A → Error B appears → Fix B → Error C → Fix C → ...
Correct (escape):         Fix error A → Error B appears → STOP → run complete audit → fix ALL at once → test → PASS ✅
```

The critical moment is the TRANSITION: the moment error B appears is the moment to stop fixing and start scanning. Don't wait for error C, D, or E. Don't justify "just one more fix." Error B IS the signal.

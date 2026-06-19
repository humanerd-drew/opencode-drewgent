# Customize Layer for Drewgent + Hermes (verified 2026-06-10 17:30)

When you need to make `hermes-cli` work *for Drewgent's environment* (not the
upstream generic hermes) — e.g. override a hardcoded label, patch a parser
that breaks on macOS Sonoma+ — use this customize layer pattern. **Do not
edit `~/.hermes/hermes-agent/` files directly.** Upstream reinstalls will
overwrite your changes silently.

## Directory Layout

```
~/.drewgent/customize/
├── README.md                    # Purpose + activation paths
├── sitecustomize.py             # Python startup hook (auto-load)
├── __init__.py                  # Package marker
└── hermes_cli/                  # Proxy package (mirrors real hermes_cli)
    ├── __init__.py              # Re-exports real hermes_cli, then
    │                            #   registers our gateway.py override
    └── gateway.py               # The actual override module
```

## The 3-Path Activation Problem (most common failure mode)

A customize layer is useless unless **all three** activation paths are
configured. Missing any one and the layer is silently invisible.

| Path | Where | What to set |
|---|---|---|
| **Gateway plist** | `~/Library/LaunchAgents/ai.drewgent.gateway.plist` | `<key>PYTHONPATH</key><string>/Users/drew/.drewgent/customize</string>` in `EnvironmentVariables` dict |
| **Shell env** (for `hermes cron list` from terminal) | `~/.zshrc` | `export PYTHONPATH="$HOME/.drewgent/customize:${PYTHONPATH:-}"` |
| **The `hermes` bash wrapper** | `~/.local/bin/hermes` | **Remove the `unset PYTHONPATH` line.** Original kept as `hermes.bak`. |

### Why the wrapper matters (verified 2026-06-10 17:30)

`~/.local/bin/hermes` is a 4-line bash script:

```bash
#!/usr/bin/env bash
unset PYTHONPATH          # ← THIS line defeats the customize layer
unset PYTHONHOME
exec "/Users/drew/.hermes/hermes-agent/venv/bin/hermes" "$@"
```

The `unset PYTHONPATH` is **deliberate** — hermes wants the venv hermes to
control its own environment, not have callers inject one. So setting
PYTHONPATH in `.zshrc` is **NOT enough**. The wrapper must be patched.

**Fix** (verified recipe):

```bash
# Back up original
cp ~/.local/bin/hermes ~/.local/bin/hermes.bak

# Replace with the customize-friendly version
cat > ~/.local/bin/hermes <<'EOF'
#!/usr/bin/env bash
# Drewgent-customized hermes wrapper — preserves PYTHONPATH so the
# customize layer takes effect. Original wrapper (saved as hermes.bak)
# explicitly unset PYTHONPATH, which broke our customize layer.
unset PYTHONHOME
exec "/Users/drew/.hermes/hermes-agent/venv/bin/hermes" "$@"
EOF
chmod +x ~/.local/bin/hermes
```

**Upgrade hazard**: any `pip install -U hermes-cli` or upgrade script that
re-installs the bash wrapper will silently re-introduce `unset PYTHONPATH`.
Add a smoke test (cron weekly) that greps the wrapper and alerts if the
line returns. See **Smoke Test Recipe** below.

## sitecustomize.py

```python
"""Drewgent sitecustomize — auto-load customize layer at Python startup.

Insert ~/.drewgent/customize/ at sys.path[0] so 'from hermes_cli.gateway'
loads OUR gateway.py first.
"""
import os
import sys
from pathlib import Path

CUSTOMIZE = Path.home() / ".drewgent" / "customize"
if CUSTOMIZE.exists() and str(CUSTOMIZE) not in sys.path:
    sys.path.insert(0, str(CUSTOMIZE))
```

**Test**:
```bash
PYTHONPATH=~/.drewgent/customize python3 -c "
import sys
from pathlib import Path
expected = str(Path.home() / '.drewgent' / 'customize')
assert expected in sys.path
print('OK: position', sys.path.index(expected))
"
```

## hermes_cli/__init__.py — The Proxy That Re-exports The Real Package

This is the **trickiest** part. Naive `from hermes_cli import *` in the
override package breaks because the real `hermes_cli/__init__.py` defines
`__version__` and `__release_date__` — if you shadow them, every
`from hermes_cli import X` fails with `ImportError: cannot import name
'__version__'`.

The right approach: **load the real package as a separate module, then
register the override submodules explicitly**.

```python
"""Drewgent customization of hermes_cli package.

The real hermes_cli/__init__.py defines __version__ and __release_date__.
We proxy that file, then explicitly register our overrides for hermes_cli.gateway
so that downstream `from hermes_cli.gateway import X` resolves to our customized
version.
"""
import importlib.util
import os
import sys

_REAL_HERMES = os.path.expanduser("~/.hermes/hermes-agent")
_init_spec = importlib.util.spec_from_file_location(
    "_real_hermes_cli",
    os.path.join(_REAL_HERMES, "hermes_cli", "__init__.py"),
)
assert _init_spec is not None and _init_spec.loader is not None
_real_init = importlib.util.module_from_spec(_init_spec)
sys.modules["_real_hermes_cli"] = _real_init
_init_spec.loader.exec_module(_real_init)

# Re-export everything from the real __init__ at package level
for _name in dir(_real_init):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_real_init, _name)

# Register the real hermes_cli package under the canonical name
sys.modules["hermes_cli"] = _real_init

# Now load our hermes_cli.gateway override and register it under
# hermes_cli.gateway (so the real hermes_cli package sees our override
# when its internal code does `from hermes_cli.gateway import find_gateway_pids`).
_gw_spec = importlib.util.spec_from_file_location(
    "hermes_cli.gateway",
    os.path.join(os.path.dirname(__file__), "gateway.py"),
)
assert _gw_spec is not None and _gw_spec.loader is not None
_gw_mod = importlib.util.module_from_spec(_gw_spec)
sys.modules["hermes_cli.gateway"] = _gw_mod
_gw_spec.loader.exec_module(_gw_mod)
```

## hermes_cli/gateway.py — The Override Module

Use `importlib.util` to load the real gateway as a *separate* module,
then mirror its attributes into this proxy. Patch the symbols you care
about. **Re-bind on the real module too** so internal references
(e.g. `hermes_cli.cron`) that imported the symbol before your override
was registered get your version.

```python
import importlib.util
import os
import sys
import re
import subprocess

_REAL_HERMES_PKG = os.path.expanduser("~/.hermes/hermes-agent")
_spec = importlib.util.spec_from_file_location(
    "_real_hermes_cli_gateway",
    os.path.join(_REAL_HERMES_PKG, "hermes_cli", "gateway.py"),
)
assert _spec is not None and _spec.loader is not None
_real = importlib.util.module_from_spec(_spec)
sys.modules["_real_hermes_cli_gateway"] = _real
_spec.loader.exec_module(_real)

# Make this proxy module expose everything from _real
_this = sys.modules[__name__]
for _name in dir(_real):
    if not _name.startswith("_"):
        setattr(_this, _name, getattr(_real, _name))

# --- Override get_launchd_label ---
def get_launchd_label() -> str:
    """Drewgent uses ai.drewgent.gateway (not ai.hermes.gateway)."""
    return "ai.drewgent.gateway"

# --- Override find_gateway_pids (Drewgent version) ---
# Why: hermes's _get_service_pids() parses `launchctl list <label>` as
# tab-separated text, but macOS Sonoma+ returns plist-format JSON.
# We re-implement to handle both formats AND to look up our label.
def find_gateway_pids(exclude_pids=None, all_profiles=False) -> list:
    excluded = set(exclude_pids or set())
    pids: list = []
    for label in ("ai.drewgent.gateway", "ai.hermes.gateway"):
        try:
            result = subprocess.run(
                ["launchctl", "list", label],
                capture_output=True, text=True, timeout=5,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
        if result.returncode != 0:
            continue
        out = result.stdout
        matched_text = False
        for line in out.strip().splitlines():
            parts = line.split("\t") if "\t" in line else line.split()
            if len(parts) >= 3 and parts[2].strip() == label:
                try:
                    pid = int(parts[0])
                    if pid > 0 and pid not in excluded:
                        pids.append(pid)
                except ValueError:
                    pass
                matched_text = True
                break
        if matched_text:
            continue
        # Plist format: look for "PID" = NNN;
        m = re.search(r'"PID"\s*=\s*(\d+)\s*;', out)
        if m:
            try:
                pid = int(m.group(1))
                if pid > 0 and pid not in excluded:
                    pids.append(pid)
            except ValueError:
                pass
    return pids

# Re-bind on _real so hermes's internal references resolve to our versions
_real.get_launchd_label = get_launchd_label
_real.find_gateway_pids = find_gateway_pids

# Re-bind on this module so direct imports get the overrides
setattr(_this, "get_launchd_label", get_launchd_label)
setattr(_this, "find_gateway_pids", find_gateway_pids)

# Register this proxy under the canonical name
sys.modules["hermes_cli.gateway"] = _this
```

## macOS Sonoma+ `launchctl list <label>` Format Change

**Symptom**: hermes's `_get_service_pids()` parses launchctl output as
tab-separated text but the actual output is plist-format JSON:

```
$ launchctl list ai.drewgent.gateway
{
    "StandardOutPath" = "/Users/drew/.drewgent/logs/gateway.log";
    ...
    "PID" = 91604;
    "Program" = "...";
};
```

**Hermes's parser fails silently**: `find_gateway_pids()` returns `[]`
even when the gateway is alive. The `hermes cron list` "Gateway is not
running" warning is *always* wrong on macOS Sonoma+ when the label
mismatches.

**Fix**: in your `find_gateway_pids` override, handle BOTH formats (see
code above). Use regex `'\"PID\"\s*=\s*(\d+)\s*;'` for the plist format.

## Verification

```bash
# 1. Verify the override is reachable
PYTHONPATH=~/.drewgent/customize python3 -c "
from hermes_cli.gateway import find_gateway_pids, get_launchd_label
print('label:', get_launchd_label())             # → ai.drewgent.gateway
print('pids:', find_gateway_pids())               # → [91604] (or empty if not running)
"

# 2. Verify hermes cron list no longer warns
hermes cron list 2>&1 | grep -c "Gateway is not running"   # → 0

# 3. Verify the venv hermes also sees the override (gateway uses this path)
PYTHONPATH=~/.drewgent/customize ~/.hermes/hermes-agent/venv/bin/hermes cron list 2>&1 | tail -3
```

## Smoke Test Recipe (recommended weekly cron)

Add to a no_agent cron job:

```bash
#!/bin/bash
# Test 1: hermes wrapper doesn't unset PYTHONPATH
if grep -q "unset PYTHONPATH" ~/.local/bin/hermes 2>/dev/null; then
  echo "ALERT: ~/.local/bin/hermes contains 'unset PYTHONPATH' — customize layer broken"
  exit 1
fi

# Test 2: customize layer's gateway override is reachable
if ! PYTHONPATH=~/.drewgent/customize python3 -c "
from hermes_cli.gateway import get_launchd_label
assert get_launchd_label() == 'ai.drewgent.gateway', get_launchd_label()
" 2>/dev/null; then
  echo "ALERT: customize layer override not reachable"
  exit 1
fi

# Test 3: gateway plist has PYTHONPATH
if ! grep -q "PYTHONPATH" ~/Library/LaunchAgents/ai.drewgent.gateway.plist 2>/dev/null; then
  echo "ALERT: gateway plist missing PYTHONPATH"
  exit 1
fi

# All checks passed
exit 0
```

Register with `cronjob(action="create", no_agent=True, schedule="0 9 * * 0", script="drewgent_customize_smoke_test.sh")` (weekly Sunday 09:00).

## Pitfalls (verified 2026-06-10)

1. **Forgetting any of the 3 activation paths** → silent break. Most common
   cause: developer sets `PYTHONPATH` in shell, sees it work in dev, then
   the gateway plist and `~/.local/bin/hermes` are still unchanged and
   the customize layer never reaches the running gateway.
2. **Shadowing `hermes_cli/__init__.py` directly with an empty file** →
   `ImportError: cannot import name '__version__'`. Always use the proxy
   pattern (load real package separately, re-export).
3. **Patching only the proxy module, not the real module** → `hermes_cli.cron`
   that did `from hermes_cli.gateway import find_gateway_pids` *before*
   your override was registered gets the original (unpatched) symbol. The
   fix: re-bind on the real module after exec.
4. **Bare `declare -A` in bash 3.2** (macOS default) → `declare: -A: invalid option`.
   Use parallel indexed arrays indexed by position instead.
5. **Set -u + dotted array keys** → `syntax error: invalid arithmetic operator (error token is ".drewgent.cron-runner")`. Use
   underscored keys (`"ai_drewgent_cron-runner"`) or drop `set -u`.
6. **LSP errors about `cannot assign to attribute` are type-check warnings only** —
   runtime works fine. Don't try to fix them; ignore.
7. **Customize layer fragility to upstream renames**: if hermes renames
   `get_launchd_label` or `find_gateway_pids`, your override fails silently
   (the real symbol just runs). The smoke test catches this.
8. **Patching `~/.local/bin/hermes` is risky**: if you break it, `hermes`
   CLI is dead. Always back up as `hermes.bak` first. The recipe in this
   doc preserves `unset PYTHONHOME` (necessary for venv detection) and
   only removes the PYTHONPATH line.

## Files Created by This Pattern (verified 2026-06-10)

```
~/.drewgent/customize/README.md
~/.drewgent/customize/__init__.py                (empty marker)
~/.drewgent/customize/sitecustomize.py
~/.drewgent/customize/hermes_cli/__init__.py    (proxy)
~/.drewgent/customize/hermes_cli/gateway.py     (override)
```

Plus edits to:

```
~/.zshrc                                                        (PYTHONPATH export)
~/Library/LaunchAgents/ai.drewgent.gateway.plist               (PYTHONPATH env var)
~/.local/bin/hermes                                             (unset PYTHONPATH removed)
~/.local/bin/hermes.bak                                         (original preserved)
```

No edits to `~/.hermes/hermes-agent/`. The venv hermes is untouched.

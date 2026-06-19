# PYTHONPATH Trailing Colon — sys.path Leak

## The Pattern That Breaks

```bash
# .zshrc — WRONG: trailing colon leaks CWD into sys.path
export PYTHONPATH="$HOME/.drewgent/customize:${PYTHONPATH:-}"
```

Python's `site` module splits `PYTHONPATH` on `:`. A trailing colon produces an empty-string entry, which Python resolves to the **current working directory** at startup time. If the CWD happens to be `~/.drewgent/` (or any dir with overlapping module names), Hermes modules like `utils`, `tools.registry` get shadowed by Drewgent-local files.

## The Fix

```bash
# .zshrc — CORRECT: no trailing colon when PYTHONPATH is empty
export PYTHONPATH="$HOME/.drewgent/customize${PYTHONPATH:+:$PYTHONPATH}"
```

`${PYTHONPATH:+:$PYTHONPATH}` expands to `:$PYTHONPATH` only when `PYTHONPATH` is set AND non-empty. When unset, only `customize` is added — no empty entry.

## Symptoms

- `hermes kanban diagnostics` → `ImportError: cannot import name 'atomic_replace' from 'utils'`
- `hermes kanban dispatch` → `ImportError: cannot import name 'tool_error' from 'tools.registry'`
- Any Hermes CLI command that imports from `utils` or `tools` when CWD overlaps Drewgent paths
- The shadow manifests only when CWD is `~/.drewgent/` — can be intermittent (some terminals start there, some don't)

## Verification

```bash
# Check if the leak is active
echo "PYTHONPATH=$PYTHONPATH"          # trailing colon? → leak
python3 -c "import sys; print([p for i,p in enumerate(sys.path) if 'drewgent' in p.lower() and 'customize' not in p])"
# If non-empty, CWD is leaking through PYTHONPATH
```

## Subprocess Protection (cron / background)

Even with the `.zshrc` fix, cron jobs and subprocesses can inherit the old PYTHONPATH from the launchd/docker environment. Always **explicitly set PYTHONPATH** in subprocess env:

```python
import subprocess
r = subprocess.run(
    ["hermes", "kanban", "dispatch"],
    env={
        **os.environ,
        "PYTHONPATH": "/Users/drew/.drewgent/customize",  # explicit, no trailing colon
        "HERMES_HOME": str(Path.home() / ".drewgent"),
    },
)
```

## Provenance

- **Found**: 2026-06-14 kanban-linear sync + kanban dispatch investigation
- **Root cause**: `.zshrc` trailing colon made `~/.drewgent/` resolve into `sys.path` via PYTHONPATH's empty entry
- **Leverage score**: 4 — fixed multiple ImportError symptoms across kanban diagnostics, dispatch, and linear sync in one shot

---
title: Shell Init Side-Effect Gating
name: shell-init-side-effect-gating
description: "Audit and fix shell init files (zsh/bash) where a side effect (bg fetch, daemon, cache) runs in a context where its consumer (RPROMPT, prompt, key binding) is gated OFF. Trigger when user shows [N] PID job notification on shell login, asks to silence one, or asks to modify .zshrc/.zshenv/.zprofile/.zlogin/.bashrc. Fix pattern - move side effect to consumer's wrapper function, or apply the same gate, or silence with `&!` only after diagnosis."
domain: software-development
created: 2026-06-03
updated: 2026-06-14
links:
  - "[[P4-cortex/growth/patterns/shell-init-side-effect-gating]]"
  - "[[P0-brainstem/brain/rules]]"
---

# Skill: Shell Init Side-Effect Gating

## When to load

Trigger when:
- User asks to add or modify `.zshrc` / `.zshenv` / `.zprofile` / `.zlogin` / `.bashrc` / `.bash_profile`
- User shows a `[N] PID` job notification or other unexpected background process on shell login
- User asks to silence a `[N] PID` notification (audit first, don't just slap `&!` on it)
- Reviewing existing shell init for cleanup or refactor

## Steps

1. **Find all `&` in shell init**:
   ```bash
   grep -nE '&\s*$' ~/.zshenv ~/.zshrc ~/.zprofile ~/.zlogin 2>/dev/null
   ```

2. **For each backgrounded process, identify its consumer** (RPROMPT, prompt segment, alias, key binding, function called from elsewhere).

3. **Check the consumer's gate** — is it conditional on a marker file, TTY, `$DISPLAY`, `uname`, etc.?

4. **Compare gates**:
   - Consumer gated, side effect not → **leak**
   - Both gated the same way → fine
   - Both ungated → fine
   - Side effect gated, consumer not → consumer might be missing optimization

5. **Decide on fix** (in this priority order):
   - **A. Move side effect to consumer's entry point** (e.g., wrapper function) — preferred
   - **B. Apply same gate to side effect** — if gate is static at source time
   - **C. Silence with `&!`** — only if leak is acceptable and noise is the only complaint
   - **D. Make consumer unconditional** — only if re-evaluating design intent confirms broad usefulness

6. **Verify**:
   ```bash
   zsh -c 'source /Users/drew/.drewgent/.zshrc_aliases; sleep 0.3; jobs -l' 2>&1
   ```
   Should report no jobs (or only the ones you intended).

7. **Document** the change in `P4-cortex/growth/patterns/shell-init-side-effect-gating.md`.

## Anti-patterns

- ❌ Adding `&` "for performance" without checking the consumer's gate
- ❌ Slapping `&!` on every `&` to silence notifications
- ❌ Treating `[N] PID` as "noise to silence" — it's a symptom pointing at a real issue
- ❌ Moving the side effect to a wrapper without checking that the wrapper actually gates the consumer

## Pitfalls

- **Marker timing**: marker files are often created by wrappers AFTER .zshrc source. So you can't gate bg-init by `[[ -f $marker ]]` at source time — marker doesn't exist yet. Fix: move side effect to the wrapper itself.

- **Subshell evaluation**: `eval "$(brew shellenv)"` and similar `eval` of generated shell code can hide `&` if upstream changes. Re-check after `brew upgrade`.

- **System /etc files**: macOS `/etc/zprofile` (path_helper) and `/etc/zshrc` (sources `/etc/zshrc_$TERM_PROGRAM`) should be checked, not just user files.

- **Multiple `&` mystery**: if `[N] PID` shows N=3 but only one `&` in user files, the others come from system /etc files, login hooks, or subshell evals. Audit those too.

## PYTHONPATH Trailing Colon

A closely related class of shell-init side effect: `PYTHONPATH` entries with a trailing separator leak the CWD into `sys.path`, shadowing modules. See `references/pypath-trailing-colon.md`.

### Detection

```bash
# Check current PYTHONPATH for trailing separator
echo "PYTHONPATH=$PYTHONPATH" | grep -E '[:;]$'
# Check if CWD leaked into sys.path
python3 -c "import sys; print([p for i,p in enumerate(sys.path) if 'drewgent' in p.lower() and 'customize' not in p])"
```

### Fix

```bash
# WRONG — trailing colon leaks CWD when PYTHONPATH is empty
export PYTHONPATH="$HOME/.drewgent/customize:${PYTHONPATH:-}"

# CORRECT — no leak
export PYTHONPATH="$HOME/.drewgent/customize${PYTHONPATH:+:$PYTHONPATH}"
```

## Subprocess Protection

When spawning Hermes CLI from cron/background runners, explicitly set `PYTHONPATH` in the child process env to prevent inherited PYTHONPATH leaks:

```python
import subprocess
subprocess.run(
    ["hermes", "kanban", "dispatch"],
    env={**os.environ, "PYTHONPATH": "/Users/drew/.drewgent/customize"},
)
```

## Reference

See `P4-cortex/growth/patterns/shell-init-side-effect-gating.md` for:
- Full case study (2026-06-03 .zshrc_aliases leak)
- Generalization beyond shell init
- Verification recipe

### Linked References

- `references/pypath-trailing-colon.md` — PYTHONPATH trailing colon pitfall with full diagnostics, fix pattern, and provenance.

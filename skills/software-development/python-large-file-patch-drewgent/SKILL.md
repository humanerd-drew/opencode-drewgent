---
title: python-large-file-patch-drewgent
name: python-large-file-patch-drewgent
type: skill
space: growth
description: How to patch large Python files in the Drewgent codebase. Covers the dual-file layout (runtime ~/.drewgent/agent/ vs source ~/.drewgent/source/drewgent-agent/), diagnose-fallback when direct patch fails, and the copy-sync protocol to keep both copies aligned.
tags: [skill, software-development, patching, python]
created: 2026-06-01
updated: 2026-06-11
links:
  - "[[@identity/brain/rules]]"
  - "[[@action/skills/SKILL-INDEX]]"
  - "[[software-development/gateway-module-extraction]]"
  - "[[software-development/codebase-refactoring]]"
  - "[[software-development/incremental-refactoring]]"
  - "[[software-development/python-nested-import-nameerror]]"
  - "[[software-development/yaml-config-patch-drewgent]]"
  - "[[software-development/llm-model-migration]]"
  - "[[software-development/shell-init-side-effect-gating]]"
---

# Skill: Patching Large Python Files in Drewgent

## When to Use
When you need to edit a specific function or code block inside a large Python file (500+ lines) in the Drewgent codebase (signal_processor.py, run_agent.py, gateway/run.py, etc.), and direct `patch` fails due to text pattern mismatch.

## The Problem
`patch` relies on exact string matching. Large files with complex docstrings (especially with newlines and special characters) often don't match what you expect from reading partial snippets. You get "old_string not found" even when the function exists.

## CRITICAL: Dual-File Layout (Runtime vs Source)

Drewgent has **two copies** of the agent code:

| Copy | Path | Purpose |
|------|------|---------|
| **Runtime** | `~/.drewgent/agent/` | What Python actually imports at runtime |
| **Source** | `~/.drewgent/source/drewgent-agent/agent/` | Git-tracked development copy |

When you patched a file in the `source/` copy but nothing changed, it's because Python loaded from `~/.drewgent/agent/` instead. The two copies can and do diverge.

### Patching Protocol

1. **Identify which copy is live** before editing:
   ```python
   python3 -c "import module_name; print(module_name.__file__)"
   ```

2. **Patch the runtime copy first** (`~/.drewgent/agent/...`) — that's where the effect is immediate.

3. **Sync the source copy** after the fix to keep them aligned:
   ```bash
   cp ~/.drewgent/agent/patched_file.py ~/.drewgent/source/drewgent-agent/agent/patched_file.py
   ```

4. **Verify** with an import and test call before declaring done.

## Solution: Python Patch Script with Diagnostic Output

When `patch` fails, use `execute_code` to:
1. First read the file and locate the exact text with `in` operator
2. Print diagnostics so you know exactly what to match
3. Apply with `content.replace(old, new, 1)` — the `1` limit prevents accidental multi-match
4. Write back and verify

```python
with open('/path/to/file.py') as f:
    content = f.read()

old1 = '''    def _on_dangerous_op(self, event: BrainEvent) -> None:
        """Handle dangerous.op'''

if old1 not in content:
    import re
    match = re.search(r'def _on_dangerous_op.*?(?=\n    def )', content, re.DOTALL)
    if match:
        print("FOUND at char", match.start())
        print("Actual text:", repr(match.group()[:200]))
    else:
        print("ERROR: pattern not found")
else:
    content = content.replace(old1, new1, 1)
    print("Patch OK")

with open('/path/to/file.py', 'w') as f:
    f.write(content)
```

## Key Rules

1. **Always use `1` in `replace(old, new, 1)`** — prevents replacing the same pattern multiple times accidentally
2. **Search before patching** — use `in` operator to confirm exact text exists before replacing
3. **Use `re.DOTALL` for multi-line matches** — docstrings and indented blocks span lines
4. **Print `repr()` of found text** — reveals hidden characters (`\n`, `\r`, trailing spaces) that break exact matching
5. **Match from unique anchor to unique anchor** — not just the function header alone; include enough context to be unique
6. **Patch both copies** — runtime first, then sync source. Patching only the source has no effect.

## Drewgent File Paths (both copies)

**Runtime (active)** — `~/.drewgent/`:
- `agent/auxiliary_client.py` (~2127 lines)
- `agent/title_generator.py`
- `agent/signal_processor.py`
- `gateway/run.py` (~8700 lines)
- `run_agent.py`
- `drewgent_cli/auth.py`

**Source (git-versioned)** — `~/.drewgent/source/drewgent-agent/`:
- `agent/auxiliary_client.py`
- `agent/signal_processor.py`
- `agent/prompt_builder.py`
- `run_agent.py`
- `gateway/run.py`

## Anti-Patterns
- Don't use `cat` or `head` to read files before patching — use `read_file` with offset/limit
- Don't patch only the source copy and expect the runtime to change — patch both
- Don't try to match just `"""docstring"""` alone — docstrings often have newlines and vary in wording
- Don't use `replace_all=True` unless you intentionally want to replace every occurrence

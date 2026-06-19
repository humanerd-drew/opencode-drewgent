---
name: ponytail
title: Ponytail — Lazy Senior Dev Mode
description: Forces AI agents through a minimization checklist before writing code. 80-94% less code, 3-6x faster. Adapted from DietrichGebert/ponytail.
trigger: "User shared github.com/DietrichGebert/ponytail for review and adoption discussion. Evaluated via external-tool-evaluation skill → H1 (ruleset-only) accepted."
domain: software-development
space: outcome
type: workflow
provenance:
  session: "2026-06-15 ponytail-adoption"
  decision: "Import the portable ruleset as a Hermes skill + AGENTS.md section, skip plugin infrastructure (Claude Code/Codex-specific). Ruleset-only H1 minimizes vendor lock-in; plugin layer evaluated separately if stable after 1-2 weeks."
tags: [yagni, senior-dev, lazy, code-minimization, efficiency, coding-discipline]
created: 2026-06-15
updated: 2026-06-15
links:
  - "https://github.com/DietrichGebert/ponytail"
  - "[[P0-brainstem/brain/rules/pre-coding-ritual]]"
  - "[[skills/simplify-code]]"
  - "[[skills/test-driven-development]]"
  - "[[skills/systematic-debugging]]"
  - "[[skills/external-tool-evaluation]]"
---

# Ponytail — Lazy Senior Dev Mode

You are a lazy senior developer. Lazy means efficient, not careless. The best code is the code never written.

This skill is auto-loaded during coding tasks. Internalize the checklist below.

## Core Checklist (before ANY code)

Stop at the first rung that holds:

1. **Does this need to be built at all?** (YAGNI) → no: skip it entirely
2. **Does the standard library already do this?** → use it
3. **Does a native platform feature cover it?** → use it (browser APIs, macOS/iOS APIs, shell builtins, HTML elements)
4. **Does an already-installed dependency solve it?** → use it (don't add new deps)
5. **Can this be one line?** → make it one line
6. **Only then:** write the minimum code that works

## Rules

- No abstractions that weren't explicitly requested
- No new dependency if it can be avoided
- No boilerplate nobody asked for
- Deletion over addition. Boring over clever. Fewest files possible
- Question complex requests: "Do you actually need X, or does Y cover it?"
- Pick the edge-case-correct option when two stdlib approaches are the same size — lazy means less code, not the flimsier algorithm
- Mark intentional simplifications with a `ponytail:` comment. If the shortcut has a known ceiling (global lock, O(n²) scan, naive heuristic), the comment names the ceiling and the upgrade path

## NOT Lazy About (Guardrails)

These are never on the chopping block:
- Input validation at trust boundaries
- Error handling that prevents data loss
- Security (auth, encryption, injection prevention)
- Accessibility (a11y)
- Hardware calibration (platform is never the spec ideal — a clock drifts, a sensor reads off)
- Anything explicitly requested by the user

## Verification Requirement

Non-trivial logic leaves ONE runnable check behind: the smallest thing that fails if the logic breaks (an assert-based demo/self-check or one small test file; no frameworks, no fixtures). Trivial one-liners need no test.

## Application to Drewgent Coding Tasks

When writing code in this workspace (Python, TypeScript/JS, Shell, config):

### Python
```python
# ❌ Don't: pip install pandas, write a DataFrame, import numpy
# ✅ Do: stdlib csv module, simple list comprehension

# ponytail: stdlib handles this — use csv.DictReader
import csv
with open('data.csv') as f:
    for row in csv.DictReader(f):
        print(row['name'])
```

### Shell
```bash
# ❌ Don't: write a Python/Ruby script to rename files
# ✅ Do: shell one-liner
for f in *.txt; do mv "$f" "${f%.txt}.md"; done
```

### Config/YAML
```yaml
# ❌ Don't: build a config validator, schema system, or custom loader
# ✅ Do: use what's already in the tooling
```

### HTML/UI
```html
<!-- ❌ Don't: install flatpickr, build a React wrapper, CSS import -->
<!-- ✅ Do: native -->
<input type="date">
```

## Trigger Conditions

This skill is loaded automatically when the task involves:
- Writing new code
- Refactoring existing code
- Code review
- Adding features
- Fixing bugs (check if the fix is minimal)
- Dependency management

## Related Drewgent Skills & Rules

- **TDD skill** — ponytail reduces code, TDD ensures correctness. Complementary.
- **Simplify code skill** — ponytail prevents bloat in the first place, simplify-code cleans existing bloat.
- **Pre-coding ritual neuron** — read `禁karpathy_coding_principles.neuron` first for TDD/DRY/YAGNI foundation.
- **Systematic debugging** — ponytail applies AFTER debugging is done; don't skip isolation steps for speed.

## Pitfalls

- **Not for debugging sessions** — during root cause analysis, write more exploration code, not less. Apply ponytail when writing the *fix*, not during investigation.
- **Not for exploration/spikes** — throwaway prototype code should err on the side of working fast, not minimal. The `spike` skill handles this.
- **Ponytail vs over-engineering** — the goal is not "as few characters as possible." It's "no unnecessary complexity." A well-named helper function is better than a dense one-liner.
- **Ponytail comments are debt, not permanent** — `ponytail:` comments flag shortcuts. When requirements change, upgrade the shortcut, don't pile on.

## "Is ponytail running right now?" — the honest answer pattern

When the user asks whether ponytail is active during a debugging/automation session, the truthful answer is **"no, and that's by design."** A debugging session is explicitly exempt from the minimization checklist. Don't fabricate minimization behavior just because the user asked — that would be theatre. Instead, name the active guardrail (e.g. `systematic-debugging`, `cloudflare-workers-local-dev`, `ponytail`'s opposite: the "exploration" pattern) and explain why the session deliberately does *more* probe code than the fix would.

Pattern:
- User: "너 작업 중에 포니테일 작동 하고 있어?"
- Wrong: "네, 잘 작동하고 있습니다" (false — debugging session)
- Wrong: "아뇨, 비효율적으로 일하고 있습니다" (false self-flagellation)
- Right: "아니, debugging session이라 ponytail 발동 안 됨 (스킬 pitfall에 명시). 대신 [systematic-debugging] / [cloudflare-workers-local-dev] / exploration mode가 켜져 있습니다. 작업 마무리 후 fix 작성 시 ponytail 적용."

## Expect/automated shell script style — from user correction 2026-06-15

When the user pastes output that has **leading whitespace on every line** (a quoted code block from a chat, an indented here-doc), they often meant the lines to be raw. When the user pastes a request like "네가 코드 라인을 줄때 앞에 공백 없이 주면 안되냐?" (literal: "if you give me code lines, can you not put a leading space?"), the agent is being asked to **drop the indentation that auto-formatting / chat copy-paste adds**. Specifically:

- When pasting a here-doc body or shell snippet, do **not** indent the inner lines. The shell's `<<'EOF' ... EOF` block is whitespace-significant in some contexts (e.g. `cat > file <<EOF` doesn't care, but `<<-EOF` strips leading tabs only — leading SPACES would be preserved and break Python).
- Use the no-indent form: `cat > file <<'EOF'\nHULY_VERSION=v1\nSECRET=***\nEOF` — every inner line starts at column 0.
- When writing expect scripts, the `send "..."` payload should also be a single string literal that the shell will receive, with newlines as `\n` and no extra indentation inserted by the agent's text formatting.

The user caught a case where I pasted a multi-line shell block with leading spaces, and Synology DSM's `set -e` plus NAS-specific bash behaviors caused the indent to matter. Fix: always emit shell blocks at column 0 unless the user explicitly asks for indentation.

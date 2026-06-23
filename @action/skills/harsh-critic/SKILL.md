---
title: Harsh Critic — Completion Bias Defense
type: skill
space: outcome
tags: [outcome]
created: 2026-05-20
updated: 2026-05-20
links:
  - "[[@action/skills/SKILL-INDEX]]"
---

space: outcome
type: document
links: [[@action/skills/SKILL-INDEX]]]


# Harsh Critic — Completion Bias Defense

## Purpose

Before Drewgent declares "done", Harsh Critic asks:
**"If the user saw this right now, what would they say?"**

This defends against the 5 structural LLM completion biases:
1. **Completion Bias** — "let's call it done"
2. **Error Loop Escape** — delete the feature instead of fixing it
3. **QA Skipping** — "build passed" = "verified"
4. **Silent Standard Lowering** — "good enough for now"
5. **Delegation to User** — "please check this manually"

---

## 3-Tier Classification

### EXTREME — HARD Block (exit 2)

These patterns mean the task is NOT done. Block immediately.

| Pattern | Detection | Example |
|---------|-----------|---------|
| Exception Violation | User said "don't X" but X happened | "I said don't push and you pushed" |
| QA Without Evidence | "PASS" claimed but no `.qa-evidence.json` | "QA passed" without any test run |
| Same Mistake Repeat | Same issue from last session detected again | "This is the 3rd time you..."
| Fake Completion | "Done" declared but build/test still failing | "Completed!" with unfixed errors |

### HIGH — FAIL + Mandatory Fix

These patterns need correction before proceeding.

| Pattern | Detection | Example |
|---------|-----------|---------|
| Delegation to User | "please check", "verify yourself", "確認してください" | Shifting verification burden |
| Scope Expansion | One-time instruction applied globally | User said once → permanent rule created |
| Unverified Claim | Statement without supporting evidence | "This is the pattern" with no diff/URL |
| Design Regression | Visual quality dropped without acknowledgment | "It works" but design is broken |

### MEDIUM — Warning

These are suboptimal but not blocking.

| Pattern | Detection |
|---------|-----------|
| Premature Completion | Declaring done before all scenarios tested |
| Format Over Substance | Clean formatting but missing critical content |
| Apology Without Fix | "Sorry about that" without behavior change |
| Vague Plan | "We'll improve this later" without specifics |

---

## Detection Patterns (regex)

```python
# EXTREME patterns
EXTREME_PATTERNS = [
    r"push\s*하지\s*말라",       # "don't push"
    r"test.*없이.*완료",          # "completed without test"
    r"또\s*같다",                 # "same thing again"
    r"이미\s*말했",               # "I already said"
]

# HIGH patterns
HIGH_PATTERNS = [
    r"확인해보세요",              # "please check"
    r"검증\s*해주세요",           # "please verify"
    r"확인\s*필요",              # "needs verification"
    r"개별적으로\s*확인",         # "check individually"
    r"尼古拉斯",                  # "I don't know"
]

# MEDIUM patterns
MEDIUM_PATTERNS = [
    r"나중에\s*改善",             # "improve later"
    r"일단\s*완료",               # "let's call it done for now"
    r"괜찮지\s*않을까",          # "probably fine"
]
```

---

## Usage Modes

### Mode 1: Pre-Commit Check

Run before `git commit` / task completion:

```bash
/harsh-critic before_commit
```

This checks:
1. All [MUST] items in `.requirements-lock.md` are checked
2. QA evidence file exists
3. No feature deletion patterns in staged changes
4. No EXTREME patterns in recent tool outputs

### Mode 2: Auto-Run (post_tool_call hook)

Automatically runs after every tool call when plugin is active.
Does NOT block — only warns (EXTREME patterns raise HARD block via plugin).

### Mode 3: On-Demand Review

```bash
/harsh-critic review
```

Review last N tool calls for completion bias patterns.

---

## Integration with HARD Gates

Harsh Critic integrates with `loopy-era-harness` plugin:

```
post_tool_call hook
    ↓
harsh_critic_check() in __init__.py
    ↓
EXTREME pattern found?
    → YES: hard_block() → SystemExit(2)
    → NO: HIGH/MEDIUM → soft_warn()
```

---

## Phase 1 — Scan Output

### 1.1 Collect recent outputs

Get last N tool results. Focus on:
- Bash/terminal outputs (where completion is declared)
- Write/edit confirmations
- Any message containing completion phrases

### 1.2 Run pattern matching

For each EXTREME pattern:
- If found → immediate HARD block
- Log to `harsh_critic_log.jsonl`

For each HIGH pattern:
- Flag for correction
- Log to `harsh_critic_log.jsonl`

For each MEDIUM pattern:
- Warn but continue
- Log to `harsh_critic_log.jsonl`

---

## Phase 2 — Context Check

### 2.1 Check requirement lock

```bash
cat .requirements-lock.md
```

If unchecked [MUST] items exist → EXTREME (not done)

### 2.2 Check QA evidence

```bash
cat .qa-evidence.json 2>/dev/null || echo "MISSING"
```

If missing → EXTREME (not verified)

### 2.3 Check staged diff

```bash
git diff --cached
```

If deletion patterns found → EXTREME (feature removed)

---

## Phase 3 — Response

### 3.1 If EXTREME

```
[HARD BLOCK] Harsh Critic — EXTREME violation detected

Pattern: {pattern_name}
Evidence: {matching text}

The task is NOT complete.
Fix the issue before proceeding.
```

Raise `SystemExit(2)` via `hard_block()`.

### 3.2 If HIGH

```
[HIGH] Harsh Critic — correction required

Pattern: {pattern_name}
Issue: {what's wrong}
Required: {what needs to happen}

Fix this now. Do not continue until addressed.
```

Do not proceed. Require fix.

### 3.3 If MEDIUM

```
[MEDIUM] Harsh Critic — warning

Pattern: {pattern_name}
Suggestion: {what to consider}

This is not blocking, but address if time permits.
```

Continue, but note the warning.

---

## Logging

All checks logged to `~/.drewgent/harsh_critic_log.jsonl`:

```json
{"timestamp": "...", "tier": "EXTREME", "pattern": "...", "text": "..."}
```

This log feeds `/self-improve` for pattern analysis.

---

## File Locations

| Purpose | Path |
|---------|------|
| Plugin | `~/.drewgent/plugins/loopy-era-harness/` |
| Hard gates | `~/.drewgent/plugins/loopy-era-harness/__init__.py` |
| Log | `~/.drewgent/harsh_critic_log.jsonl` |
| Rules | `~/.drewgent/rules/` |

---

## Key Principle

> "The user doesn't see your reasoning — they only see the result.
> If the result looks like 'done' but isn't actually done, you failed."

---

## Related Skills

- `/loopy-era-self-improve` — analyze harsh critic logs for rule extraction
- `/loopy-era-qa-cycle` — proper QA with evidence
- `/loopy-era-eval` — measure harness completeness

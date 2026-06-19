---
title: Subagent Driven Development
name: subagent-driven-development
description: "Dispatch parallel subagents for implementation and refactoring — two-stage review, wave-based batch delegation, and mechanical split patterns"
type: document
space: concept
tags: [concept]
created: 2026-05-20
updated: 2026-06-15
links:
  - "[[P3-sensors/skills/SKILL-INDEX]]"
  - "[[autonomous-ai-agents/delegate-task-tool]]"
  - "[[autonomous-ai-agents/opencode]]"
  - "[[software-development/writing-plans]]"
  - "[[P0-brainstem/brain/rules]]"
---

# Subagent-Driven Development

## Overview

Execute implementation plans by dispatching fresh subagents per task with systematic two-stage review.

**Core principle:** Fresh subagent per task + two-stage review (spec then quality) = high quality, fast iteration.

## When to Use

Use this skill when:
- You have an implementation plan (from writing-plans skill or user requirements)
- Tasks are mostly independent
- Quality and spec compliance are important
- You want automated review between tasks

**vs. manual execution:**
- Fresh context per task (no confusion from accumulated state)
- Automated review process catches issues early
- Consistent quality checks across all tasks
- Subagents can ask questions before starting work

## The Process

### 1. Read and Parse Plan

Read the plan file. Extract ALL tasks with their full text and context upfront. Create a todo list.

**Key:** Read the plan ONCE. Extract everything. Don't make subagents read the plan file — provide the full task text directly in context.

### 2. Per-Task Workflow

For EACH task in the plan:

#### Step 1: Dispatch Implementer Subagent

Use `delegate_task` with complete context including: task spec, file paths to modify, TDD instructions, project context, toolsets.

#### Step 2: Dispatch Spec Compliance Reviewer

Verify implementation matches original spec:
- All requirements from spec implemented?
- File paths match spec?
- Function signatures match spec?
- Nothing extra added (no scope creep)?

#### Step 3: Dispatch Code Quality Reviewer

After spec compliance passes: check conventions, error handling, naming, test coverage, security issues.

#### Step 4: Mark Complete

### 3. Final Review

After ALL tasks are complete, dispatch a final integration reviewer.

### 4. Verify and Commit

## Task Granularity

**Each task = 2-5 minutes of focused work.** Not "Implement authentication system" — instead: "Create User model", "Add password hashing function", "Create login endpoint".

## Red Flags

- Skip reviews (spec compliance OR code quality)
- Proceed with unfixed critical/important issues
- Dispatch multiple implementation subagents for tasks that touch the same files
- Start code quality review before spec compliance is PASS
- Skip review loops (reviewer found issues → implementer fixes → review again)

## Handling Issues

- If subagent asks questions: answer clearly and completely
- If reviewer finds issues: implementer fixes, reviewer re-reviews
- If subagent fails a task: dispatch a new fix subagent with specific instructions

## Efficiency Notes

**Why fresh subagent per task:** Prevents context pollution from accumulated state. Each subagent gets clean, focused context.

**Why two-stage review:** Spec review catches under/over-building early. Quality review ensures well-built code. Catches issues before they compound.

## Wave-Based Batch Delegation

For parallel multi-task execution, use `delegate_task(tasks=[...])`. Sends up to 3 independent tasks simultaneously — all results return together.

### When to Use Parallel Waves

**Parallel-safe tasks:** Files that share ZERO imports or dependencies. E.g. splitting `saju-controller.ts`, `auth-controller.ts`, and `db/queries.ts` simultaneously — they don't import from each other.

**Sequential-dependent tasks:** Tasks that need a shared utility module created first. E.g. creating `utils/report-format.ts` before splitting report controllers that should import from it.

### Detailed-Instruction Pattern (Eliminates Spec Review for Mechanical Work)

When delegating mechanical code refactoring (splitting, moving, consolidating), provide exhaustive instructions so the subagent produces correct output on the first attempt:

```
CONTEXT FOR EACH SPLIT TASK:
├── Exact file path to read
├── Target file list with:
│   ├── File name
│   ├── Which functions go there (by original export name)
│   └── What imports to keep/change
├── Shared modules already available (provide paths + export signatures)
├── Barrel re-export instruction (keep original file, make it barrel)
├── Verification command (npx tsc --noEmit)
└── "Do NOT change any function bodies"
```

**When detailed instructions suffice:** Mechanical refactoring (splitting, renaming, moving code), straightforward extraction with known target layout.

**When spec review IS still needed:** Complex logic with edge cases, when user intent needs interpretation, when multiple valid approaches exist.

### Pattern: Consolidate First, Then Split

For projects with heavy code duplication (3+ copies of the same utility):

1. **Wave 1 (independent):** Split files that don't share duplicated code
2. **Direct work:** Create shared utility modules from the duplicated code
3. **Wave 2 (after consolidation):** Split the remaining files, instructing to import from new shared utils

This prevents split propagation of duplicated code.

### Real Example — m-log-v2 Controller Splitting (2026-06-15)

```
Wave 1 (3 parallel): saju split | auth split | db split
[Direct: create utils/report-format.ts + utils/llm-report.ts]
Wave 2 (3 parallel): dating split | report+comprehensive split | payment split

Result: 7 monolithic files → 20+ domain files
        6 duplicated functions eliminated, 0 broken imports, ~7 min wall-clock
```

## 🛑 Critical Pitfall: Subagents Silently Change Behavior During Mechanical Splits

**This is the most dangerous subagent failure mode discovered to date.**

Even with detailed instructions saying "Do NOT change any function bodies or logic", a subagent CAN change the call path of a function, altering runtime behavior, token counts, environment variable lookup order, and error handling — all while passing TypeScript compilation and appearing correct.

### Real Incident — m-log-v2 Free Report Bypass (2026-06-15)

**Task:** Split `report-controller.ts` into `generate-free-report.ts` + `generate-paid-report.ts` + prompts.
**Instructions:** Explicit "Do NOT change any function bodies or logic."
**What the agent did:** Changed `handleGenerateFreeLogReport` to call `callLLMJson()` directly instead of the original `generateAIReportContent()`. Result:
- Output token budget: **1500 → 3000** (2x cost increase, unnoticed by the agent)
- NVIDIA key fallback list: **4 keys → 3 keys** (dropped legacy safety-net `NVIDIA_API_KEY`)
- Both behaviors compiled fine and returned the same shape — the bug was invisible unless you traced the exact API call paths

**Root cause:** The agent saw `generateAIReportContent()` as an unnecessary wrapper and "optimized" it away, replacing it with a direct call to the underlying `callLLMJson()`. The agent didn't realize the wrapper had different default parameters.

### Detection Methods

**Method 1 — Path trace audit (most reliable):**
After receiving all subagent results, trace ONE complete request path through the critical handler. Don't just check that TypeScript compiles — verify that the call chain reaches the same leaf functions with the same parameters.

```typescript
// BEFORE (original): handleGenerateFreeLogReport → generateAIReportContent → callDeepSeek / callNvidiaWithFallback
// AFTER (agent changed): handleGenerateFreeLogReport → callLLMJson → callDeepSeek / callNvidiaWithFallback
//                      ↳ bypassed generateAIReportContent entirely!
```

**Method 2 — grep for "bypass" patterns:**
```bash
# Check if the same function is imported but not used in the critical path
grep -n "callLLMJson\|callReportLLM\|generateAIReportContent" src/report/generate-free-report.ts
# If callLLMJson is imported but generateAIReportContent is also defined in the file,
# which one does the handler actually call? Trace to find out.
```

**Method 3 — Parameter value audit:**
Check that token counts, timeouts, and fallback key lists match the original:
```bash
# Dump all LLM caller invocations with their parameters
grep -A 5 "await callLLMJson\|await callReportLLM\|await generateAIReportContent" src/report/*.ts
```

**Method 4 — Original ↔ Split comparison:**
For critical files, do a semantic diff. The total line count should be approximately the same (plus barrel lines, minus duplicated imports). A significant discrepancy in total size indicates missing or changed logic.

```bash
# Before refactoring (save this before delegating)
wc -l src/report/dating-controller.ts src/report/report-controller.ts
# After refactoring
# Total of new files should ≈ old total + barrel lines
```

### Prevention in Task Instructions

Add this explicit instruction to every split task:

> "After splitting, verify that the main exported handler calls the SAME internal functions as before. If the original handler called `generateAIReportContent()`, the new handler MUST also call `generateAIReportContent()` — not `callLLMJson()` directly, not any other function. The intermediate wrapper exists for a reason (different token budget, different fallback logic)."

Also add:

> "Import ALL functions that the original file imported, even if they seem unused in the new file. Removing an import because 'it's not used here' is a red flag — check if the original used it on a different call path."

### Recovery Pattern (when discovered after delegation)

```typescript
// 1. Identify what the agent changed
// 2. Find the ORIGINAL code (from session memory, another split file, or the barrel)
// 3. Restore the original call path
// 4. Verify with npx tsc --noEmit AND behavioral trace
```

### Why Standard Code Review Misses This

- ✅ TypeScript compiles (callLLMJson and generateAIReportContent have compatible return types)
- ✅ All exports preserved (barrel re-exports are correct)
- ✅ Function signatures unchanged
- ❌ **Call graph changed** — the handler now invokes a different function with different parameters
- ❌ **Default parameters changed** — maxTokens defaulted differently (1500 vs 3000)
- ❌ **Side effects changed** — different API keys tried in different order

**Lesson:** For mechanical splits, TypeScript compilation is NOT enough verification. You MUST trace at least one critical call path to confirm behavioral equivalence.

## Related
- [[P3-sensors/skills/SKILL-INDEX]]
- [[autonomous-ai-agents/delegate-task-tool]]
- [[autonomous-ai-agents/opencode]]
- [[software-development/writing-plans]]
- [[software-development/project-restructure]]
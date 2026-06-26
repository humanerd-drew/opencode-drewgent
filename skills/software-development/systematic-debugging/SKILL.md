---
name: systematic-debugging
title: Systematic Debugging Skill
type: skill
space: outcome
description: Multi-phase debugging protocol — find root cause before fixing. Covers the 4-phase process, Drewgent stack debugging, and T4-style stall investigation.
tags: [outcome, debugging, root-cause]
created: 2026-06-11
updated: 2026-06-13
  session: "2026-06-13 opencode-go model-routing architecture-verification"
  decision: "Added Phase 0: Architecture Investigation — verify provider wiring before answering. Prevents confident wrong answers based on naming conventions (e.g. assuming opencode-go/deepseek-v4-flash routes through OpenRouter). Covers provider registration check, naming convention pitfall, auto-resolution chain, and recovery protocol."
  previous:
  previous:
    session: "2026-06-12 m-log dating report debugging"
    decision: "Added destructured-variable-missing pattern to Frontend SPA Debugging — common bug when adding new state properties to Component views"
links:
  - "[[@action/skills/SKILL-INDEX]]"
  - "[[software-development/python-debugpy]]"
  - "[[software-development/node-inspect-debugger]]"
  - "[[software-development/test-driven-development]]"
  - "[[@identity/brain/rules]]"
---




# Systematic Debugging

## Overview

**Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.

**Preceding principle — Phase 0: NEVER assume system architecture from naming conventions.** Verify the actual wiring (base URL, provider registration, API key env vars) before making claims about how a provider/model/service routes. See the Phase 0 section below.

**Violating the letter of this process is violating the spirit of debugging.**

## The Iron Law

```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```

If you haven't completed Phase 1, you cannot propose fixes.

## When to Use

Use for ANY technical issue:
- Test failures
- Bugs in production
- Unexpected behavior
- Performance problems
- Build failures
- Integration issues

**Use this ESPECIALLY when:**
- Under time pressure (emergencies make guessing tempting)
- "Just one quick fix" seems obvious
- You've already tried multiple fixes
- Previous fix didn't work
- You don't fully understand the issue

**Don't skip when:**
- Issue seems simple (simple bugs have root causes too)
- You're in a hurry (rushing guarantees rework)
- Someone wants it fixed NOW (systematic is faster than thrashing)

## First-Fix Rule: Cross-File Audit Before Any Fix

**WHEN you encounter ANY error in a recently-refactored or extracted codebase:**

1. **Do NOT attempt a single fix.**
2. Immediately run a **comprehensive cross-file audit** to find ALL broken references.
3. Fix them ALL in one batch.

**Why:** Refactoring extractions ALWAYS leave multiple dangling references across multiple files. Each "fix one → discover next" cycle wastes turns and frustrates the user.

**User signal to trigger this:** If the user says anything like "하나씩 문제가 달라지는데, 전수조사 좀 해봐라" (problems keep changing one at a time, do a thorough investigation) — or even BEFORE they say it, the FIRST time a second distinct error appears after a fix — switch to comprehensive audit mode IMMEDIATELY.

**The audit must cover:**
1. All files modified in the extraction (`git diff --name-only`)
2. All functions from the original module referenced in extracted files
3. All lazy imports needed (circular dependency check)
4. All call sites that need updating (`self.method()` → `function(self, ...)`)
5. All registration points (class attribute assignment)
6. All leftover debris at file ends
7. All cached `.pyc` files that mask errors

Use the `extraction-completeness-checklist.md` reference under `codebase-refactoring` for the detailed procedure.

---

## The Four Phases

You MUST complete each phase before proceeding to the next.

---

## Phase 0: Architecture Investigation (Verify Before Answering)

**When you're asked how a provider/model/service/system is wired up, do NOT infer architecture from naming conventions.** Verify the actual registration points before making claims.

### When to use

- User asks how a model/provider/service routes or connects
- You see a naming convention (e.g. `provider/model`) and are about to infer routing paths
- You're about to explain how something is wired without checking the actual registration

### Investigation protocol

#### 1. Check the actual provider registration

For Hermes providers, the three things that tell you how it actually works:

```bash
# 1a) What is the base URL?
grep -A5 '"opencode-go"' ~/.hermes/hermes-agent/hermes_cli/auth.py
```

**Base URL determines where requests actually go** — not the model name prefix.

```bash
# 1b) What API key env var does it read?
# Each provider has api_key_env_vars tuple. That's your credential source.
```

**The API key env var tells you which key credential is actually required** — not what's convenient or what you assume.

#### 2. Don't infer from the `provider/model` naming format

The `opencode-go/deepseek-v4-flash` format does NOT mean "goes through OpenRouter."

| Wrong inference | What actually happens |
|---|---|---|
| `opencode-go/deepseek-v4-flash` → OpenRouter involved | ❌ `opencode-go` is a standalone provider with `https://opencode.ai/zen/go/v1` |
| `qwen3.7-max` when provider=opencode-go → goes through opencode-go | ✅ Correct — model name is looked up in the provider's own catalog |

The model prefix only tells you **who hosts the model on the current provider.** It does NOT tell you what provider/infrastructure handles the request.

#### 3. Trace the auto-resolution chain

When `provider: "auto"`, the chain (from `auth.py:resolve_provider()`):

```
① Active OAuth provider in auth store → returns that
② OPENAI_API_KEY / OPENROUTER_API_KEY env var → returns "openrouter"
③ Iterate PROVIDER_REGISTRY for first API key found → returns that provider
   (minimax → deepseek → nvidia → opencode-zen → opencode-go ... order matters!)
④ AWS Bedrock credential detection
⑤ Error: no provider configured
```

**The FIRST matching API key wins** — PROVIDER_REGISTRY dict order determines priority.

#### 4. State verified facts before analysis

After verifying the actual wiring:
1. State the factual finding first: "Base URL = X, provider = Y, auth = Z"
2. THEN answer the user's question based on verified facts
3. If your initial assumption was wrong, acknowledge clearly and move on — don't explain why you were wrong

### Common pitfalls

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| Confident wrong answer | Long explanation based on naming assumption | Verify registration before typing |
| Auto-resolution misunderstanding | "I have MiniMax key but it's not being used" | Check PROVIDER_REGISTRY order — another provider matched first |
| OpenRouter confusion | Treating all `provider/model` as OpenRouter | Check if the provider segment is a standalone entry with its own base URL |

### Recovery when caught in a wrong assumption

1. Acknowledge the error immediately and clearly — one sentence
2. Do the actual investigation silently (don't narrate the "why you were wrong")
3. Report the real finding
4. Then answer the question correctly

The user prefers a quick correction over a lengthy retraction.

---

## Phase 1: Root Cause Investigation

**BEFORE attempting ANY fix:**

### 1. Read Error Messages Carefully

- Don't skip past errors or warnings
- They often contain the exact solution
- Read stack traces completely
- Note line numbers, file paths, error codes

**Action:** Use `read_file` on the relevant source files. Use `search_files` to find the error string in the codebase.

### 2. Reproduce Consistently

- Can you trigger it reliably?
- What are the exact steps?
- Does it happen every time?
- If not reproducible → gather more data, don't guess

**Action:** Use the `terminal` tool to run the failing test or trigger the bug:

```bash
# Run specific failing test
pytest tests/test_module.py::test_name -v

# Run with verbose output
pytest tests/test_module.py -v --tb=long
```

### 3. Check Recent Changes

- What changed that could cause this?
- Git diff, recent commits
- New dependencies, config changes

**Action:**

```bash
# Recent commits
git log --oneline -10

# Uncommitted changes
git diff

# Changes in specific file
git log -p --follow src/problematic_file.py | head -100
```

### 4. Gather Evidence in Multi-Component Systems

**WHEN system has multiple components (API → service → database, CI → build → deploy):**

**BEFORE proposing fixes, add diagnostic instrumentation:**

For EACH component boundary:
- Log what data enters the component
- Log what data exits the component
- Verify environment/config propagation
- Check state at each layer

Run once to gather evidence showing WHERE it breaks.
THEN analyze evidence to identify the failing component.
THEN investigate that specific component.

### 5. Trace Data Flow

**WHEN error is deep in the call stack:**

- Where does the bad value originate?
- What called this function with the bad value?
- Keep tracing upstream until you find the source
- Fix at the source, not at the symptom

### 6. Check Local vs Deployed / Production vs Dev

**WHEN the user reports "it works locally" or "it works on dev":**

- **Believe them.** Treat "works locally" as a confirmed data point, not an anecdote.
- **Test from the SAME environment they tested from** before declaring a root cause.
  - If they used `npm run dev` / `wrangler dev`, the fetch goes from their local IP — not from Cloudflare's network.
  - A curl test from your terminal is the same environment as `wrangler dev`. A deployed Worker is NOT.
- **Common causes for local-ok/deployed-fail:**
  - Environment variables / secrets not synced (`.dev.vars` ≠ Cloudflare secrets)
  - API key scoping / IP allowlist (NVIDIA, OpenAI etc. may behave differently by source IP)
  - Network connectivity (Cloudflare Workers use shared egress IPs)
  - Timeout / CPU limits (Cloudflare Workers free tier: 30s total; paid: 30s per fetch)
  - DNS resolution differences (Cloudflare's resolver may route differently)
- **Verification protocol:**
  1. Get the EXACT error from the deployed environment — don't guess (use `wrangler tail`, platform logs, or curl the failing endpoint)
  2. Test the same API call from your local machine with the SAME credentials
  3. If local works, test from the deployed Worker specifically (not from your machine)
  4. Only then form a hypothesis

**⚠️ Tool-output masking pitfall:**

When testing API keys or secrets from the terminal, the tool may mask sensitive values in its **displayed output** by replacing them with `***`. This is a display-only safety feature — the actual command sent had the real value.

**Never** copy a `***`-masked value back into a subsequent command. If you see:
```
$ curl -H "Authorization: Bearer ***"
```
the `***` was only in what you saw. The real key was sent. If you copy that `***` into a Python script or another curl as a literal string, you will send an invalid key and get a 401/403, falsely concluding the key doesn't work.

**How to safely verify a key:**
```bash
# 1. Use the value directly from the source file, not from terminal output
grep "^SECRET=" .env | cut -d= -f2   # read from file

# 2. Use Python to read the file and make the request in one step (avoids shell echo issues):
python3 -c "
import urllib.request, json
with open('.env') as f:
    for line in f:
        if line.startswith('SECRET='):
            key = line.split('=',1)[1].strip()
res = urllib.request.urlopen(urllib.request.Request(url, headers={'Authorization': f'Bearer {key}'}))
print(res.status)
"

# 3. Verify length/prefix before sending:
echo "Key length: ${#KEY}, prefix: ${KEY:0:8}"
```

**When a curl command returns 403, and the user insists the key works:**
- You likely tested with a masked/truncated key
- Read the key fresh from the source file, not from the terminal display
- Retest with Python or a heredoc that reads the file directly

**Action:** Use `search_files` to trace references:

```python
# Find where the function is called
search_files("function_name(", path="src/", file_glob="*.py")

# Find where the variable is set
search_files("variable_name\\s*=", path="src/", file_glob="*.py")
```

### Phase 1 Completion Checklist

- [ ] Error messages fully read and understood
- [ ] Issue reproduced consistently
- [ ] Recent changes identified and reviewed
- [ ] Evidence gathered (logs, state, data flow)
- [ ] Problem isolated to specific component/code
- [ ] Root cause hypothesis formed

**STOP:** Do not proceed to Phase 2 until you understand WHY it's happening.

---

## Phase 2: Pattern Analysis

**Find the pattern before fixing:**

### 1. Find Working Examples

- Locate similar working code in the same codebase
- What works that's similar to what's broken?

**Action:** Use `search_files` to find comparable patterns:

```python
search_files("similar_pattern", path="src/", file_glob="*.py")
```

### 2. Compare Against References

- If implementing a pattern, read the reference implementation COMPLETELY
- Don't skim — read every line
- Understand the pattern fully before applying

### 3. Identify Differences

- What's different between working and broken?
- List every difference, however small
- Don't assume "that can't matter"

### 4. Understand Dependencies

- What other components does this need?
- What settings, config, environment?
- What assumptions does it make?

---

## Phase 3: Hypothesis and Testing

**Scientific method:**

### 1. Form a Single Hypothesis

- State clearly: "I think X is the root cause because Y"
- Write it down
- Be specific, not vague

### 2. Test Minimally

- Make the SMALLEST possible change to test the hypothesis
- One variable at a time
- Don't fix multiple things at once

### 3. Verify Before Continuing

- Did it work? → Phase 4
- Didn't work? → Form NEW hypothesis
- DON'T add more fixes on top

### 4. When You Don't Know

- Say "I don't understand X"
- Don't pretend to know
- Ask the user for help
- Research more

---

## Phase 4: Implementation

**Fix the root cause, not the symptom:**

### 1. Create Failing Test Case

- Simplest possible reproduction
- Automated test if possible
- MUST have before fixing
- Use the `test-driven-development` skill

### 2. Implement Single Fix

- Address the root cause identified
- ONE change at a time
- No "while I'm here" improvements
- No bundled refactoring

### 3. Verify Fix

```bash
# Run the specific regression test
pytest tests/test_module.py::test_regression -v

# Run full suite — no regressions
pytest tests/ -q
```

### 4. If Fix Doesn't Work — The Rule of Three

- **STOP.**
- Count: How many fixes have you tried?
- If < 3: Return to Phase 1, re-analyze with new information
- **If ≥ 3: STOP and question the architecture (step 5 below)**
- DON'T attempt Fix #4 without architectural discussion

### 5. If 3+ Fixes Failed: Question Architecture

**Pattern indicating an architectural problem:**
- Each fix reveals new shared state/coupling in a different place
- Fixes require "massive refactoring" to implement
- Each fix creates new symptoms elsewhere

**STOP and question fundamentals:**
- Is this pattern fundamentally sound?
- Are we "sticking with it through sheer inertia"?
- Should we refactor the architecture vs. continue fixing symptoms?

**Discuss with the user before attempting more fixes.**

This is NOT a failed hypothesis — this is a wrong architecture.

---

## Completeness Verification — Trusted vs Superficial Checks

**Critical rule: NEVER do a file-existence-only check or a regex-scan when the user asks you to verify completeness.** The user WILL notice and WILL lose trust.

Session 2026-06-13 m-log-v2 restructuring produced these specific failures:

| What I did | User reaction |
|---|---|
| 39-second audit checking only file existence | "39초만에 대조했으리라 생각되지 않는다. 이 답변을 신뢰할 수없음" |
| Regex matching keywords instead of reading actual logic | Missed multiple functional gaps |
| Assuming copied files = ported functionality | Dashboard/Input feature mismatches missed |
| Not reading the original planning docs first | "기획된 문서를 보고도 그런 말이 나온다니" |

### The 3-Layer Verification Protocol

When asked to "check if X is complete" or "compare original vs new":

**Layer 1: Structural (30 seconds — NEVER stop here alone)**
- Files exist at expected paths?
- Build passes?
- HTTP endpoints return 200?

**Layer 2: Functional (2–10 minutes — MINIMUM)**
- For EACH feature in the original:
  1. Read the actual original code (not just grep it)
  2. Read the new implementation  
  3. List actual exported functions, HTML structure, CSS classes, data flows
  4. Mark each as: ✅ ported, ⚠️ different, ❌ missing
- Use `read_file` with line ranges, not `search_files` alone
- Build a structured comparison table with concrete findings

**Layer 3: Behavioral (when user is demanding or previous check failed)**
- Rebuild and test with actual HTTP requests
- Compare visual output if frontend
- Compare API responses if backend
- Show the user your evidence chain, not just conclusions

### When to escalate to Layer 3 immediately
- User says "분석 결과물을 신뢰할 수없음" (can't trust the analysis)
- User says "39초" (they timed you)
- User says "내용 기반 대조" (content-based comparison)
- Previous check was wrong (caught by user or by subsequent testing)

### Trust Recovery Protocol
When a user has already caught you providing a superficial check:
1. ADMIT it immediately — no excuses about tool limitations
2. State what the correct approach would have been
3. Offer to redo the check properly with content-based comparison
4. DO NOT list reasons why the superficial check seemed reasonable
5. Present thorough results as a structured diff/table

### Integration with Ported Code Pattern
When migrating code (Vanilla JS → Svelte, etc.):
1. Read the original planning docs FIRST (DESIGN_REFERENCE.md, ARCHITECTURE.md)
2. Catalog every function and feature from the original
3. Check the ported version against each — not just "does a file exist"
4. Test each feature path (happy path + error path)
5. Compare visual output — HTML structure and CSS class names

## Multi-Task Orientation: Full Inventory Before Any Change

**When the user gives you a SET of related tasks** (e.g., "fix these 4 report navigations"), follow this protocol:

1. **Inventory first** — List EVERYTHING that needs changing. Read the relevant files. Map existing state.
2. **Report findings** — Show the user what you found: what exists, what's missing, what's broken.
3. **Get guidance** — Let the user steer the approach before you start coding. They may have priorities or constraints you can't infer.
4. **Implement per guidance** — One item at a time, but with the full map in mind.

**Why:** The user has context you don't. If you dive into the first fix without showing the full picture, you'll waste turns going back and forth. The user's guidance in step 3 is what makes the implementation efficient.

**User signal:** When the user says "하나씩 확인하자" (let's check one by one) or gives you a list of items to handle, switch to inventory-first mode before touching any code.

## Cascade Error Pattern — When Fixing Error A Reveals Error B

**Critical workflow rule:** When you fix ONE error and the NEXT error is a different one (not the same error recurring), you are in a cascade. STOP fixing one-at-a-time and do a COMPREHENSIVE CROSS-FILE AUDIT.

### The Cascade Trap

```
Fix error A → discover error B → fix error B → discover error C → fix error C → ...
```

This pattern means the root problem is not individual bugs — it's an **incomplete change** (refactoring, extraction, migration) that left multiple broken references across multiple files. Each fix only reveals the next victim.

### When to switch to comprehensive mode

**The critical signal is the TRANSITION: the moment error B appears after fixing error A.**

Not after accumulating 3, 5, or 10 errors — the VERY FIRST time a new error surfaces that is different from the one you just fixed. At that point:
1. STOP all fixing
2. Announce: "We're in a cascade — switching to comprehensive audit"
3. Run the extraction-completeness-checklist (see codebase-refactoring/references/)
4. Fix everything in one batch
5. Restart and test once

**Don't:** "just one more fix" — error B is never the last one in a cascade.
**Don't:** wait for error C or D — every fix in a cascade is wasted work.
**Don't:** assume each error is independent — cascades share a single root cause (incomplete extraction).

### How to Escape

**When you fix one error and a different error immediately follows, do NOT fix error B directly. Instead:**

1. **Identify the incomplete change.** Use `git diff` or `git log` to find what was recently modified. Look for:
   - Methods extracted from one class to another file
   - Functions moved between modules
   - Configuration keys renamed/migrated
   - Import paths restructured

2. **Audit ALL touched files for missing references.** For each file in the diff:
   - ✅ Module-level imports present (nothing used but not imported)
   - ✅ Type annotations resolve (classes/types used in signatures are imported)
   - ✅ Call sites updated (method→function call syntax)
   - ✅ Circular import avoided (A imports B, B imports A)
   - ✅ Parameter names match body references (no `self` vs `gw` mismatch)
   - ✅ No leftover code fragments (orphaned indented blocks at file end)

3. **Use static analysis to verify.** For Python:
   ```python
   import ast
   tree = ast.parse(content)
   # Collect module-level imports, check every Name node
   ```
   Or simpler: try to import the module standalone to catch missing names.

4. **Check cross-file wiring.** Extracted functions need:
   - Import in the consuming module
   - Registration (if called as `self.method()`, the function must be attached to the class)
   - Parameter signature matching the call pattern

5. **Clean up extraction debris.** Check for:
   - Orphaned method definitions that were removed from the class but not re-attached
   - Leftover code at end of files (partial extraction artifacts)
   - `@staticmethod` / classmethod decorators left dangling after extraction

### User Signal

If the user says something like "하나씩 문제가 달라지는데, 전수조사 좀 해봐라" (problems keep changing, do a thorough investigation), this IS the signal to stop the serial fix loop and switch to comprehensive audit mode immediately.

### Prompt Quality Debugging

**Symptom:** LLM output is rigid, repetitive, or misses nuance. User says "문장이 딱딱한데" (stiff), "자연스럽지 않은데" (unnatural), or keeps asking for one-off rule patches.

**Pattern:** After several individual rule patches, the prompt becomes a collection of exceptions rather than a coherent instruction set. Each new rule tries to fix the output of the previous rules.

**Diagnosis protocol:**

1. **Count patches.** How many individual rules/patterns have been added since the last structural review?
   - 3+ patches = time for structural review
   - Don't add patch #4 without restructuring

2. **Identify redundancy.** Does the same concept appear in multiple sections? E.g. "라벨 문단 구조" explained in both "출력 구조" and "분석 필수 규칙" and "어투" — consolidate to one.

3. **Check section boundaries.** Does each section have a single, clear responsibility?
   - If "표현 규칙" contains output format instructions → move to "출력 형식"
   - If "품질 기준" contains tone instructions → move to "어투"

4. **Verify rule consistency.** Do any rules contradict each other?
   - "변경률 30% 초과 금지" (prompt) vs "70% 이상 길이 유지" (code validation) = redundant but consistent
   - But if prompt says "간결하게" and validation requires "70% 길이 유지" = contradictory

5. **Remove irrelevant context.** Does every word in the prompt serve the task?
   - Personality ontology in a fortune-telling prompt → remove
   - Relationship psychology in a career analysis → remove

6. **Apply the 7 Principles** (from m-log-development-patterns):
   - One section = one responsibility
   - No duplication
   - One concrete example only
   - Positive commands preferred
   - Output format defined first, reinforced last
   - Remove irrelevant context
   - One instruction per bullet

**User signal to trigger structural review:** When user says "지금처럼 하나하나 예외가 있는 거 말고 구조적으로 안정적인 프롬프트를 구성해" (don't patch individual exceptions, build a structurally stable prompt instead) — STOP patching and restructure.

## Red Flags — STOP and Follow Process

If you catch yourself thinking:
- "Quick fix for now, investigate later"
- "Just try changing X and see if it works"
- "Add multiple changes, run tests"
- "Skip the test, I'll manually verify"
- "It's probably X, let me fix that"
- "I don't fully understand but this might work"
- "Pattern says X but I'll adapt it differently"
- "Here are the main problems: [lists fixes without investigation]"
- Proposing solutions before tracing data flow
- **"One more fix attempt" (when already tried 2+)**
- **Each fix reveals a new problem in a different place**

**ALL of these mean: STOP. Return to Phase 1.**

**If 3+ fixes failed:** Question the architecture (Phase 4 step 5).

## Background process notification lag (Hermes)

When you start a long-running process with `terminal(background=True, notify_on_complete=True)`, the completion notification can arrive **many turns late** — sometimes 3-4 turns after the process actually finished. By the time you see the `IMPORTANT: Background process <id> completed` block in the user's message, you may have already spawned a second attempt or moved on to a different state.

**Symptoms:**
- You see "exit code 137" or similar for a process you already abandoned
- A "DEAD" poll contradicts a "still listening" lsof — usually the poll happens *before* the process truly exits
- You start a second background job, then the first one's notification arrives and you don't know which one is canonical

**Rules:**
1. **Before starting a second background job**, poll or check status of the existing one. If it's still running, wait or kill it. Don't race.
2. **Trust the most recent state check** (lsof, ps, curl), not stale "DEAD" reports from earlier turns.
3. **On late notification:** if the late notification is for a process you've already replaced, treat it as informational only. Don't act on it as if the new state is wrong — verify the new state with a fresh check first.
4. **When a "second attempt" was started out of caution,** don't immediately kill it on seeing the first's late completion. The second attempt may be the one that actually fixed the issue. Verify with health checks (HTTP 200, port listening) before deciding.

**Anti-pattern:** Seeing exit code 137 and immediately killing the second attempt, only to find the second attempt was the one that actually unblocked the user.

## External System Debugging — Read-Only First, Propose Destructive Second

When debugging systems outside the agent's sandbox (NAS, remote server, production cluster, user-owned infrastructure), the 4-phase process still applies BUT Phase 4 has a critical gate the user must explicitly pass.

### Why the standard flow doesn't work for external systems

The 4-phase flow assumes the agent can execute fixes freely. For external systems:
- The user owns the system and bears the risk
- Destructive operations (`rm -rf`, `docker compose down`, `drop database`, `kubectl delete`) can cause data loss, service outage, or cascade failures the agent cannot recover from
- The agent does not have the user's full context (backup state, runbooks, other users depending on the service)

### The protocol

1. **Phase 1–3 (root cause investigation): use read-only commands only.** On a NAS or remote host, this means:
   - `cat`, `grep`, `find`, `ls`, `ps`, `lsof`, `docker inspect`, `docker logs`, `docker ps`
   - Avoid: `rm`, `mv`, `chmod` on host data, `docker compose down`, `docker exec ... restart`, anything that mutates state
   - If a read-only command would be more useful as a state-changing one (e.g. restarting a service to read fresh logs), **propose the destructive version instead of executing it.** Show the user exactly what you would run.

2. **Phase 4 (Implementation): present the destructive plan as a written proposal.** Format:
   ```
   To fix this, the following destructive actions are needed:
   1. <exact command> — <what it does, what it could lose>
   2. <exact command> — <what it does, what it could lose>
   
   Confirm "go" or adjust before I run.
   ```
   - Never bundle destructive + read-only in one command sequence.
   - If a fix is non-destructive (e.g. editing a config file the user has shared), normal Phase 4 applies.

3. **If the user approves, execute ONE destructive command at a time and verify state between each.** This is the "Rule of Three" applied to destructive operations: don't batch 3 destructive commands and hope.

4. **If the user denies or interrupts ("Do NOT retry", "stop"), STOP immediately.** Do not rephrase the same operation through a different command path. Do not proceed with sub-steps that depend on the denied step. Switch to a different angle or ask the user what they want to do.

### The "Do NOT retry" signal is a hard stop

If the security system (or the user) blocks a command with a message like "Do NOT retry this command, do NOT rephrase it, and do NOT attempt the same outcome via a different command":

- That is an explicit refusal. Stop the workflow.
- Do not attempt to bypass via a different command that achieves the same effect.
- Do not continue with adjacent steps that depended on the blocked one.
- Report the blocked state to the user, present alternative paths if any, and wait for explicit direction.

### Common mistakes

| Mistake | Why it's wrong |
|---------|----------------|
| Auto-running `rm -rf` / `docker compose down` after read-only diagnosis completed | The user may have plans for the existing data state, or the operation may affect other services. Destructive on external systems always needs explicit user approval. |
| Treating a blocked command as "the security system being conservative" and trying a different formulation | The block is a hard signal. The user (or their guardrails) decided the action is unsafe in this context. Move on. |
| Running multiple destructive commands in one expect/bash session | If one fails mid-sequence, the system is in an unknown state. Always check between commands. |
| Restarting a service to read fresh state instead of using logs | Use `docker logs --tail N` or `journalctl` to read state without mutating. |

### What this looks like in practice

When the agent has determined that fixing the issue requires touching a remote host:

1. Run all read-only commands first to fully understand state.
2. Write up the proposed destructive steps with clear before/after.
3. Wait for user "go" (or, on a hostile CI/automation context, wait for an explicit unblock).
4. Execute one step, verify, then the next.

If the user says "이어서 해줘" (just go ahead), treat that as a single explicit approval for the proposed plan — not a blanket license for all future destructive operations on that system.

## Common Rationalizations

| Excuse | Reality |
|--------|---------|
| "Issue is simple, don't need process" | Simple issues have root causes too. Process is fast for simple bugs. |
| "Emergency, no time for process" | Systematic debugging is FASTER than guess-and-check thrashing. |
| "Just try this first, then investigate" | First fix sets the pattern. Do it right from the start. |
| "I'll write test after confirming fix works" | Untested fixes don't stick. Test first proves it. |
| "Multiple fixes at once saves time" | Can't isolate what worked. Causes new bugs. |
| "Reference too long, I'll adapt the pattern" | Partial understanding guarantees bugs. Read it completely. |
| "I see the problem, let me fix it" | Seeing symptoms ≠ understanding root cause. |
| "Model returns 403 from my test" | User says it works locally. Test from the SAME context (local IP, same key) before declaring root cause. |
| "One more fix attempt" (after 2+ failures) | 3+ failures = architectural problem. Question the pattern, don't fix again. |

## Quick Reference

| Phase | Key Activities | Success Criteria |
|-------|---------------|------------------|
| **1. Root Cause** | Read errors, reproduce, check changes, gather evidence, trace data flow | Understand WHAT and WHY |
| **2. Pattern** | Find working examples, compare, identify differences | Know what's different |
| **3. Hypothesis** | Form theory, test minimally, one variable at a time | Confirmed or new hypothesis |
| **4. Implementation** | Create regression test, fix root cause, verify | Bug resolved, all tests pass |

---

## Frontend SPA Debugging (Vanilla JS / Cloudflare Workers)

### Component Lifecycle Infinite-Call Debugging

**Symptom:** A component-based SPA keeps calling the same API endpoint repeatedly — either once per navigation/refresh or in an endless loop. Common pattern in M-LOG's `ReportComprehensiveView` where `mounted()` auto-submits the report generation API.

**Multi-Layer Diagnosis Protocol:**

#### Layer 1: Guard Flag Reset on View Recreation

In a Router-based SPA, each `handleRoute()` call DESTROYS the current Component instance and creates a NEW one:

```javascript
// Router.js — handleRoute():
if (this.currentView) {
    if (typeof this.currentView.destroy === 'function') this.currentView.destroy();
    this.currentView = null;
}
this.container.innerHTML = '';
this.currentView = new ViewClass(viewWrapper);
```

This means any **instance-level guard flags** (`_autoSubmitted`, `_alreadyFetched`, `_initComplete`) are reset to `undefined` on every navigation, even if the user navigates to the SAME route they're already on.

**Investigation steps:**
```javascript
// 1. Identify the guard flag in the View's mounted() or init()
// Look for: _autoSubmitted, _alreadyFetched, _fetchStarted, _loading
search_files("_autoSubmitted", path="frontend/app/js/views/")
search_files("_loaded\|_fetched\|_started", path="frontend/app/js/views/")

// 2. Check if the guard is a class property (NOT state)
// Class properties like `this._autoSubmitted = true` survive setState() → render() → mounted()
// But DO NOT survive Router.destroy() → new ViewClass()

// 3. Trace every path that could call handleRoute() during the View's lifecycle:
search_files("handleRoute", path="frontend/app/js/")
search_files("renderData", path="frontend/app/js/")
```

**Root cause candidates:**
- `App.renderData()` → calls `router.handleRoute()` → recreates ALL views
- `AppShell` Store subscriber (e.g., on `user` prop change) → calls `router.handleRoute()`
- History sidebar load/delete → calls `router.handleRoute()`
- Any hash change while already on the target route (same-hash bug) → NO hashchange event, but if query params are added → view recreates

**Fix options:**
1. **sessionStorage flag** — survives page refresh and view recreation:
   ```javascript
   mounted() {
       if (isPaid && !sessionStorage.getItem('__RPT_AUTO_SUBMITTED__')) {
           sessionStorage.setItem('__RPT_AUTO_SUBMITTED__', '1');
           this.autoSubmit();
       }
   }
   ```
2. **Static class flag** — shared across all instances:
   ```javascript
   static autoSubmitted = false;
   mounted() {
       if (!ReportComprehensiveView.autoSubmitted) {
           ReportComprehensiveView.autoSubmitted = true;
           this.autoSubmit();
       }
   }
   ```
3. **Remove auto-submit entirely** — Show the form and let the user click Submit. Simplest and safest.

#### Layer 2: Component State Cascade (setState → render → mounted → ??)

```javascript
// Component.js — the chain:
setState(newState) {
    this.state = { ...this.state, ...newState };
    this.update();
}
update() { this.render(); }
render() {
    this.container.innerHTML = this.template();
    this.mounted();           // ← Re-enters here!
    this._bindEventsInternal();
}
```

Every `setState()` call re-enters `mounted()`. If `mounted()` has conditional logic that triggers another `setState()` → `mounted()` → ... it's an infinite loop.

**Safeguard pattern (proper):**
```javascript
mounted() {
    // FIRST: set guard flag BEFORE any async operation
    if (condition && !this._guard) {
        this._guard = true;        // ← Synchronous, persists through setState cycles
        this.startAsyncOp();
        // do NOT await here — return immediately
        return;
    }
    // Handle non-guarded state changes
    if (this.state.reportData && !this._historySaved) {
        this._historySaved = true;
        this.saveHistory();
    }
}
```

**Pitfall — guard flag set AFTER the first setState call:**
```javascript
// ❌ Wrong: The guard is in a different setState call
mounted() {
    if (condition) {
        this.setState({ loading: true });  // → render() → mounted() AGAIN
        this._guard = true;  // ← Too late! The second mounted() enters before this
    }
}

// ✅ Correct: Guard is set BEFORE any setState/async call
mounted() {
    if (condition && !this._guard) {
        this._guard = true;
        this.setState({ loading: true });  // → render() → mounted()
        // Second mounted() sees this._guard === true → returns early
    }
}
```

#### Layer 3: Timer/Interval Cleanup

If `startLoadingSimulation()` creates a `setInterval`, and `stopLoadingSimulation()` is only called on SUCCESS (not on error), the interval continues forever, calling `setState()` every N seconds.

```javascript
// Investigate:
search_files("setInterval", path="frontend/app/js/views/")
search_files("setTimeout", path="frontend/app/js/views/")
```

**Required cleanup paths:**
```javascript
destroy() {  // Called by Router when view is destroyed
    this.stopLoadingSimulation();  // clearInterval
}

stopLoadingSimulation() {
    if (this.loadingInterval) {
        clearInterval(this.loadingInterval);
        this.loadingInterval = null;
    }
}
```

#### Layer 4: Deployed vs Development Version Comparison

When the SPA has two parallel directories (`public/` deployed vs `frontend/` dev), they can diverge:

```bash
diff public/app/js/views/ReportXView.js frontend/app/js/views/ReportXView.js
```

**Key areas to diff:**
- `init()` — default state values (especially `isSimulatingAnalysis`, `isPaid`)
- `mounted()` — auto-submit logic presence and guard flags
- `handleSubmit()` — whether it calls the API directly or redirects first
- Event guard flags (`_autoSubmitted`, `_historySaved`, `_eventsBound`)

The deployed version (in `public/` for Cloudflare Workers) is the one users actually see. If it has auto-submit logic but the dev version doesn't, that's a bug in the deployed version.

#### Layer 5: Auth Inconsistency Between Payment and Report Generation

Payment flow may allow anonymous checkout (via `anonymousId`), but the report generation endpoint requires a session cookie. This creates a hidden loop pattern:

1. User pays (anonymous, no session) → stored in `__PURCHASED_REPORTS__` (localStorage)
2. Redirect to report page → View mounts → `isPaid=true` → auto-submit fires
3. API returns 401 (no session) → frontend shows error → `isSimulatingAnalysis=false`
4. User refreshes → View recreates → auto-submit fires again → 401 again
5. User is stuck in a refresh → retry → fail → refresh cycle

**Investigation:**
```javascript
// Check if the API requires auth while payment allows anonymous
search_files("getSessionPayload", path="src/controllers/")
search_files("anonymousId", path="src/controllers/") 
search_files("m_log_session", path="src/utils/")
```

**Fix:** Either (a) make the report endpoint work with `anonymousId`, or (b) require login before payment.

### Multi-Layer Frontend Audit Protocol (Legacy)

When a component-based SPA (Router + Views) shows a blank screen, broken layout, or 404s on hash routes:

**Audit layers in this order:**

#### Layer 1: HTML Shell
```javascript
// Check if the app mount point exists
console.log('app div:', document.getElementById('app'));
console.log('contentView div:', document.getElementById('contentView'));
```
- If `#app` missing → index.html is wrong (verify `id="app"` exists)
- If `#contentView` missing → AppShell template didn't render (check for template syntax errors)

**Common causes of blank screen in component-based SPA:**

1. **Escaped backticks from patch tool** (`\`` instead of `` ` ``):
   - Fix: `node --check path/to/file.js`
   - Always verify after patching template strings

2. **Stray trailing backtick in template literal** — an extra `` ` `` at end of a line inside a template string prematurely closes it:
   ```js
   // ❌ The trailing backtick closes the template literal here
   <div class="container" style="display:${isActive ? 'block' : 'none'}">`
       <div class="inner">...</div>   // ← parsed as JS, causes cascade error
   ```
   - Browser error: `Uncaught SyntaxError: missing } in template string` — misleadingly points to a line **after** the stray backtick because the parser cascades
   - Detection: `node --input-type=module -e "try { await import('./View.js'); } catch(e) { console.log(e.message); }"`
   - The error message targets the wrong line; always search backward for stray backticks when you see "missing }" in a template-heavy file

3. **Module import failure** — If ANY import in a `<script type="module">` chain fails (404), the entire script fails silently (no console error visible in DevTools).

6. **Destructured state variable missing from template** — Adding a new field to `this.state` without adding it to the destructuring in `template()` causes a `ReferenceError` that silently breaks the entire view:

   ```js
   // ❌ Bug: isSimulatingAnalysis added to state but not destructured
   this.state = { ... reportData: null, isSimulatingAnalysis: false };
   
   template() {
       const { reportData } = this.state;  // isSimulatingAnalysis NOT destructured
       if (isSimulatingAnalysis || loading) { ... }  // ReferenceError!
   }
   ```

   **Detection:** The browser console shows `Uncaught ReferenceError: X is not defined` but the SPA may render a blank/white page. In headless testing:
   ```javascript
   page.on('pageerror', err => console.log('PAGE ERROR:', err.message));
   ```
   
   **Fix:** Every field referenced inside `template()` must be destructured from `this.state` at the top. This is the most common mistake when adding new UI state properties to a Component-based view.

**Universal fix for all three:** Import the file as an ES module in Node to catch the real SyntaxError (command above).

#### Layer 2: CSS & Layer System
### CSS Layer Audit

#### The Canonical Layer System
All z-index values should use CSS custom properties from `variables.css`:
```css
--z-base: 1
--z-sticky: 100
--z-header: 500
--z-dropdown: 1000
--z-overlay: 2000
--z-drawer: 3000
--z-backdrop: 4000
--z-modal: 5000
--z-popover: 6000
--z-tooltip: 7000
--z-toast: 9000
--z-max: 10000
```

**Hardcoded z-index values** are the most common source of visual chaos:
```bash
# Find them in CSS files
grep -rn "z-index:" public/app/css/ --include='*.css' | grep -v "var(--z"
# Find them in JS/HTML inline styles
grep -rn "z-index:" public/app/js/ --include='*.js' | grep -v "var(--z"
```

#### ⚠️ CSS `transform` Containing Block Trap

**Symptom:** A `position: fixed` element (modal, overlay, toast) appears in the wrong position — constrained to a sidebar, off-screen, or covering only part of the viewport.

**Root cause:** Any ancestor with a `transform` property (even `translateX(-100%)` for slide-in drawers) creates a new containing block. `position: fixed` elements inside that ancestor are relative to that element, NOT the viewport.

```css
/* ❌ This breaks position: fixed children */
.menu-sidebar {
    position: fixed;
    transform: translateX(-100%);  /* ← creates new containing block */
}

/* A modal inside this sidebar would be constrained to it, not the viewport */
```

**Same applies to:**
- `will-change: transform` (future transform hint)
- `filter: blur(...)` / `backdrop-filter: blur(...)`
- `perspective`
- `contain: layout|paint|strict`

**Detection:**
```javascript
// In browser console — check modal's positioning context
const modal = document.getElementById('loginModal');
let el = modal.parentElement;
while (el) {
    const style = getComputedStyle(el);
    if (style.transform !== 'none' || style.willChange === 'transform') {
        console.log('⚠️ Containing block ancestor:', el, style.transform);
    }
    el = el.parentElement;
}
```

**Fix:** Append `position: fixed` elements (modals, toasts, overlays) directly to `document.body`:
```javascript
// DON'T put modal HTML inside a component template
// DO append to body in mounted():
const container = document.createElement('div');
container.innerHTML = this.renderModalHtml();
document.body.appendChild(container.firstElementChild);
```

| Element | CSS Variable |
|---------|-------------|
| Page overlay/dim | `var(--z-overlay, 2000)` |
| Drawer/sidebar | `var(--z-drawer, 3000)` |
| Modal backdrop | `var(--z-backdrop, 4000)` |
| Modal dialog | `var(--z-modal, 5000)` |
| Loading full-screen | `var(--z-max, 10000)` |
| Tooltip | `var(--z-tooltip, 7000)` |
| Toast notification | `var(--z-toast, 9000)` |

4. **Verify no conflict** — scan for any values between 500-7000 that don't use `var(--z-*)`.

#### Layer 3: JavaScript Imports & Router
```bash
# Check all JS modules load (SPA will fail silently if one import fails)
for url in "/app/js/app.js" "/app/js/core/Router.js" "/app/js/core/Component.js" "/app/shared/core/store.js"; do
  curl -s -o /dev/null -w "%{http_code} $url\\n" "http://localhost:8787$url"
done
```
- If any file returns 404 → missing file or wrong import path
- If all files return 200 but app is blank → JS runtime error (check browser console)

#### Layer 4: Data Persistence (localStorage vs sessionStorage)
When migrating a frontend, pay attention to persistence keys:

```bash
grep -rn "localStorage.getItem\|sessionStorage.getItem" public/app/js/ --include='*.js'
```

**Common migration pitfall:** If the backend was changed to use `sessionStorage` (for security), but the new frontend uses `localStorage`, all views will find empty data and render blank/empty states.

**Fix for this pattern:**
- If the app doesn't need persistent data across tabs → change ALL to `sessionStorage`
- If data must survive tab close → keep `localStorage`
- Check BOTH `getItem()` and `setItem()` calls — they must use the same storage

#### Layer 5: Mobile vs Desktop Layout
Component-based SPAs often use CSS classes like `.is-desktop` or `.is-mobile` added by JavaScript:

```javascript
// Check device detection
document.body.classList.contains('is-desktop');
document.body.classList.contains('is-mobile');
```
- If neither class is present → device detection code isn't running
- The layout CSS may rely on these classes for responsive design

**Fix:** Add device detection in the App init:
```javascript
detectDevice() {
    const isDesktop = window.innerWidth >= 1024;
    document.body.classList.toggle('is-desktop', isDesktop);
    document.body.classList.toggle('is-mobile', !isDesktop);
}
```

#### ⚠️ Event Delegation Scope for Off-Container Elements

**Symptom:** UI elements render on screen (modal, toast, overlay) but clicking buttons inside them does nothing — no event handler fires.

**Root cause:** The component uses event delegation (`this.container.addEventListener(eventType, handler)`) but the element was appended OUTSIDE `this.container` (e.g., to `document.body` to avoid the CSS `transform` containing block trap). Delegated events attached to the container can't catch clicks on elements outside it.

**Detection:**
```javascript
// In browser console — check which container the handler is delegated from
// The AppShell component uses this.container (usually #app)
// If the login modal is appended to document.body, clicks inside it
// won't bubble to #app
console.log('Modal parent:', document.getElementById('loginModal')?.parentElement);
console.log('AppShell container:', document.querySelector('#app'));
```

**Fix options:**
1. **Direct binding** — Add `addEventListener` directly to the off-container elements after creation:
```javascript
document.getElementById('modalBtn')?.addEventListener('click', () => this.handleAction());
```
2. **Delegate from document** — If using a component framework that supports document-level delegation, bind to `document` instead of `this.container` for specific off-container elements.
3. **Keep inside container** — Restructure the template so the element stays inside the container, but fix the CSS `transform` issue differently.

**Best practice for modals/overlays in component-based SPA:**
- Render the modal template in the component's `template()` or `render()` method
- In `mounted()`, move it to `document.body` to avoid CSS containing-block issues
- Immediately attach direct event listeners to the moved elements
- Keep dismiss/backdrop-click handlers simple (not dependent on component state)

### Component-Based SPA Data Flow Tracing

When data doesn't appear after navigation:

1. **Router → View creation** — Router creates `new ViewClass(viewWrapper)`. If the constructor fails, no error is shown.
2. **View.init() → data fetch** — View reads from `localStorage/sessionStorage` or `Store.state`
3. **View.render() → template** — Uses `this.state` data to generate HTML
4. **Store persistence** — `Store.setActiveSaju(data)` must be called before navigating

**Debugging flow:**
```javascript
// In browser console:
console.log(Store.state);            // Check Store has data
console.log(localStorage.__SAJU_DATA__); // Check localStorage
console.log(sessionStorage.__SAJU_DATA__); // Check sessionStorage
```

### Common SPA Migration Issues

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Blank screen, all JS 200 | Template syntax error (escaped backtick) | `node --check` all view files |
| Cards visible but no data | Wrong storage (local vs session) | Align `getItem`/`setItem` calls |
| Z-index chaos | Hardcoded z-index values | Replace with `var(--z-*)` |
| 404 on hash routes | Route not registered in Router | Check `new Router('#cv', {'/path': View})` |
| Layout broken on one breakpoint | Missing `.is-desktop`/`.is-mobile` class | Add device detection in init |
| Navigating back clears data | View recreation destroys state | Store data in persistent Store, not component state |
| Clicking history item does nothing | Same-hash navigation: `window.location.hash` set to current hash | Add `?t=timestamp` to force hash change: `#/route?t=' + Date.now()` |

### Hash-Routing Same-Hash Bug

**Symptom:** User clicks a history item (or any navigation element), nothing happens. No error in console, no route change, no view update.

**Root cause:** When the current URL hash matches the target hash, `window.location.hash = hash` doesn't fire a `hashchange` event. The Router stays idle, and the new view is never created.

```javascript
// ❌ Bug: if already on #/report-dating, this does NOTHING
window.location.hash = '#/report-dating';

// ✅ Fix: append a unique query parameter to force hash change
window.location.hash = '#/report-dating?t=' + Date.now();
```

The Router should strip query params when matching routes:
```javascript
let path = hash.replace(/^#/, '').split('?')[0];
```

**Affected flows:**
- History sidebar → restore report (always navigates to a report page; if already on that page, the hash is the same)
- Dashboard → report card navigation (only affected if user navigates to the same report they're already viewing)
- Tab switches within a report view (these use component state via `setState`, not hash navigation — unaffected)

**Detection:**
```javascript
// In browser console — check if hashchange fires
window.addEventListener('hashchange', () => console.log('hash changed:', location.hash));
window.location.hash = '#/report-dating';  // If already there → no log
window.location.hash = '#/report-dating?t=1';  // Always fires
```

**Fix pattern applied to history restore flow:**
```javascript
// Before:
const hash = '#/report-dating';
window.location.hash = hash;

// After:
window.location.hash = '#/report-dating?t=' + Date.now();
```

This pattern should be applied to ALL report-type history restore navigation in AppShell.js, not just the one that was reported as broken.

## Drewgent Stack Debugging

Drewgent's cron/gateway stack has a specific multi-layer architecture requiring a **process → log → scheduler → code → hypothesis** elimination chain.

### Layer Map for Drewgent

```
launchctl list | ps -A     →    launchd process manager
       │
       ▼
gateway log                →    P6-prefrontal/logs/gateway.log
       │
       ▼
cron ticker thread         →    gateway/run.py:_start_cron_ticker
       │
       ▼
tick() scheduler           →    cron/scheduler.py:tick
       │
       ▼
run_job()                  →    cron/scheduler.py:run_job
       │
       ▼
cron-runner subprocess     →    logs/cron-runner/YYYY-MM-DD.log
```

### T4-Style Stall Debugging (0 cron fires + sequential block)

**Pattern**: cron-runner log has 0 fires in 5+ minutes but gateway process appears alive.

**Investigation chain**:

1. **Is the gateway process alive?**
   ```bash
   launchctl list | grep ai.drewgent.gateway
   launchctl print gui/$(id -u)/ai.drewgent.gateway | grep pid
   ```
   PID present = process alive. PID absent = crash.

2. **Cron-runner log fresh?**
   ```bash
   ls -lt ~/.drewgent/logs/cron-runner/*.log
   grep -E '=== 2026-' ~/.drewgent/logs/cron-runner/YYYY-MM-DD.log | tail -3
   ```
   If mtime > 5 min old + no recent `=== ISO ===` blocks → stall.

3. **Sequential block (most common root cause)**
   ```bash
   grep "Running job" ~/.drewgent/P6-prefrontal/logs/gateway.log | tail -10
   ```
   Is an LLM-based job (no `script` field) running before a script-based job (has `script` field)? The LLM job blocks the entire tick.

4. **Check redundancy** (`~/.drewgent/cron/jobs.json`):
   Look for duplicate job entries — same function, one script-based, one LLM-based. The LLM one blocks the tick loop.

**Immediate fix** when sequential block is confirmed:
- Disable the redundant LLM job (`enabled: false`)
- Ensure script jobs run first in `scheduler.py:tick()`:
  ```python
  _script_jobs = [j for j in due_jobs if j.get("script")]
  _llm_jobs = [j for j in due_jobs if not j.get("script")]
  for job in _script_jobs + _llm_jobs:
  ```

**Kickstart to reset**:
```bash
launchctl kickstart -k gui/$(id -u)/ai.drewgent.gateway
```

**Check file lock** (stale lock blocks ticks):
```bash
rm -v ~/.drewgent/cron/.tick.lock
```

**Auto-watchdog**:
```bash
bash ~/.hermes/scripts/drewgent_cron_watchdog.sh
```

## Drewgent Agent Integration

### Investigation Tools

Use these tools during Phase 1:

- **`search_files`** — Find error strings, trace function calls, locate patterns
- **`read_file`** — Read source code with line numbers for precise analysis
- **`terminal`** — Run tests, check git history, reproduce bugs
- **`web_search`/`web_extract`** — Research error messages, library docs. If unavailable, use `terminal` + `curl`/`wget` instead — never claim search is impossible.. If unavailable, use `terminal` + `curl`/`wget` instead — never claim search is impossible.

### With delegate_task

For complex multi-component debugging:

```python
delegate_task(
    goal="Investigate why [specific test/behavior] fails",
    context="""
    Follow systematic-debugging skill:
    1. Read the error message carefully
    2. Reproduce the issue
    3. Trace the data flow to find root cause
    4. Report findings — do NOT fix yet

    Error: [paste full error]
    File: [path to failing code]
    Test command: [exact command]
    """,
    toolsets=['terminal', 'file']
)
```

### With test-driven-development

1. Write a test that reproduces the bug (RED)
2. Debug systematically to find root cause
3. Fix the root cause (GREEN)

## Real-World Impact

From debugging sessions:
- Systematic approach: 15-30 minutes to fix
- Random fixes approach: 2-3 hours of thrashing
- First-time fix rate: 95% vs 40%
- New bugs introduced: Near zero vs common

**No shortcuts. No guessing. Systematic always wins.**

## Related
## Related
- [[@action/skills/SKILL-INDEX]]
- `references/css-layer-debug.md` — CSS z-index conflict patterns, backdrop-filter WebKit bug, dual CSS variable system diagnosis, NAS canonical source check protocol
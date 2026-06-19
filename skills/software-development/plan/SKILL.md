---
name: plan
title: Plan Mode
description: Use this skill when the user wants a plan instead of execution.
type: skill
tags: [outcome]
links:
  - "[[P3-sensors/skills/SKILL-INDEX]]"
  - "[[software-development/writing-plans]]"
  - "[[software-development/test-driven-development]]"
  - "[[software-development/spike]]"
  - "[[software-development/requesting-code-review]]"
  - "[[P0-brainstem/brain/rules]]"
---

# Plan Mode

Use this skill when the user wants a plan instead of execution.

## Core behavior

For this turn, you are planning only.

- Do not implement code.
- Do not edit project files except the plan markdown file.
- Do not run mutating terminal commands, commit, push, or perform external actions.
- You may inspect the repo or other context with read-only commands/tools when needed.
- Your deliverable is a markdown plan saved inside the active workspace under `.drewgent/plans/`.

## Output requirements

Write a markdown plan that is concrete and actionable.

Include, when relevant:
- Goal
- Current context / assumptions
- Proposed approach
- Step-by-step plan
- Files likely to change
- Tests / validation
- Risks, tradeoffs, and open questions

If the task is code-related, include exact file paths, likely test targets, and verification steps.

## Save location

Save the plan with `write_file` under:
- `.drewgent/plans/YYYY-MM-DD_HHMMSS-<slug>.md`

Treat that as relative to the active working directory / backend workspace. Drewgent file tools are backend-aware, so using this relative path keeps the plan with the workspace on local, docker, ssh, modal, and daytona backends.

If the runtime provides a specific target path, use that exact path.
If not, create a sensible timestamped filename yourself under `.drewgent/plans/`.

## Interaction style

- If the request is clear enough, write the plan directly.
- If no explicit instruction accompanies `/plan`, infer the task from the current conversation context.
- If it is genuinely underspecified, ask a brief clarifying question instead of guessing.
- After saving the plan, reply briefly with what you planned and the saved path.

## User's "Try First, Don't Conservative" Principle (verified 2026-06-14)

When the user proposes a major direction change (new platform, new architecture, new tool), do NOT:
- ❌ List objections or risks based on imagination
- ❌ Default to the familiar/conservative path
- ❌ Decide against the proposal without trying

Instead:
- ✅ **"Apply the direction to the current environment."** Figure out HOW, not IF.
- ✅ **"Maximum application first."** Try the proposal with existing infra before considering alternatives.
- ✅ **Evaluate after implementation.** If it actually proves inefficient after trying, THEN pivot. User will acknowledge it.
- ✅ **"상정한 방향을 현재 환경에 맞춰 최대한 적용해보고, 그럼에도 손해 또는 비효율이라 판단된다면 그 때 물러도 늦지 않다."**

Applies to: platform migrations, tooling changes, workflow restructuring, content strategy pivots.

**Pitfall:** This is NOT about skipping due diligence. If there's a concrete, verifiable blocker (API doesn't exist, binary unavailable on this platform, key not obtainable), state it factually. The principle is about avoiding *imagined* risks, not ignoring *real* ones.

## User's "Daejeon-Je" Plan Mode (verified 2026-06-10)

When the user states a **대전제** (high-level premise) upfront, the plan should:
1. Apply the premise to every decision
2. NOT ask 4-question clarification when the premise already answers
3. Make explicit per-decision choices, even 1-way doors, with rationale

**Plan structure for 대전제-driven work**:
- Header: restate the 대전제 verbatim
- Each section: "대전제 → decision" mapping
- Execution path: explicit "Path A: execute now" vs "Path B: stop here, user re-evaluates"
- Default if user is silent for 60s after plan save: Path B (user must explicitly approve to start execution)

**Anti-pattern**: saving a "discovery" plan that's mostly questions and few answers. The user gave a premise; the plan must *apply* it.

## Plan → Execution Transition (verified 2026-06-10)

When the user approves the plan with a short signal ("go", "실행", "그냥 지금 작업해버리는건?"), transition to execution mode:
- Drop the read-only constraint
- Each task = 2-5 min focused work (TDD cycle per task if code change)
- Keep the plan's task list as the todo list
- Don't dispatch subagents unless the task is *isolation-worthy* (e.g. 30+ min work that benefits from fresh context)
- For "꼼꼼하게" / "찌꺼기 없이" requests: do the work directly, verify at each step, clean residue at the end

**Plan file is the source of truth during execution**: the todo list mirrors the plan's tasks, and any deviation from the plan (e.g. "discovered this doesn't work, switching to approach B") must be documented in the plan file or a follow-up incident doc.

## Related

- [[P3-sensors/skills/SKILL-INDEX]]
- `writing-plans` — for full multi-task implementation plans (vs. this skill's "ready-to-execute single task")
- `subagent-driven-development` — when plan execution needs fresh-context subagent dispatch (not always needed; for "꼼꼼하게" requests, direct execution is preferred)

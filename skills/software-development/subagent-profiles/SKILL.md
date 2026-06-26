---
name: subagent-profiles
title: Subagent Profiles (Archived)
description: >-
  **2026-06-23: Superseded by GJC Coordinator MCP.** OMO subagent profile system
  (delegate.ts + agents/*.md) was replaced by Gajae-Code. Use `task()` for simple
  subagent work (opencode built-in) or `gjc_delegate_*` for isolated/parallel tasks.
domain: software-development
space: growth
type: mechanism
tags: [subagent, profile, delegation, model-routing, loop-engineering]
created: 2026-06-13
updated: 2026-06-23
---

# Subagent Profiles (Archived)

This skill is archived. The OMO subagent profile system (`~/.config/opencode/agents/*.md` + `delegate.ts`) has been removed.

## Current replacement

- **`task(subagent_type="<type>")** — opencode built-in. Types: explorer, implementer, tester, reviewer, reviewer-critical, security-reviewer, planner, orchestrator, designer, sre, analyst, content-manager, editor, archiver, seo-engineer.
- **`gjc_delegate_execute(goal, worktree?, acceptance?)`** — GJC worktree isolation + tmux execution.
- **`gjc_delegate_team(goals=[...])`** — GJC tmux parallel workers.

---
title: "Trend Discuss: Multi-Agent Orchestration"
date: 2026-06-29
task: trend-discuss-agent-orchestration
status: draft
tags: [trends, orchestration, multi-agent, gjc-coordinator, claude-squad, multica]
---

# Trend Discuss: Multi-Agent Orchestration

**Date:** 2026-06-29
**Question:** Should we evaluate any for specific gaps in GJC Coordinator MCP?

---

## Executive Summary

The multi-agent orchestration space has exploded — 4 distinct approaches emerged in this batch. Multica (38.4k stars) is a full managed-agents platform (assign tasks, track progress, compound skills) that overlaps significantly with Drewgent's existing kanban + GJC flow. Claude-squad (8k stars) and agent-deck (393 stars) are TUI-based session managers for running multiple coding agents in parallel worktrees — complementing GJC's programmatic orchestration with a human supervision layer. Ruflo (61.9k stars) is a sprawling meta-harness with 100+ agents, swarm coordination, and federation — more kitchen-sink than focused tool. **Recommendation:** skip Multica (too much overlap), skip Ruflo (too noisy). Evaluate Claude-squad and agent-deck for their TUI-based session management — they fill a gap GJC doesn't address: visual multi-agent supervision in the terminal.

---

## Per-Item Analysis

### claude-squad (7.32) — smtg-ai/claude-squad
**One-liner:** Go-based terminal TUI that manages multiple coding agents (Claude Code, Codex, OpenCode, etc.) in isolated tmux sessions with git worktrees.

**Key features:**
- Runs agents in parallel tmux sessions, each in its own git worktree
- TUI with session list, diff preview, and status detection (running/waiting/idle/error)
- Yolo/auto-accept mode for unattended background execution
- Profile system for named agent configurations
- `cs` binary via Homebrew or manual install (~5MB, Go single binary)
- AGPL-3.0 license, **8k stars**, 571 forks, 219 commits
- Simple mental model: tmux + worktrees + TUI = parallel agents

### multica (7.18) — multica-ai/multica
**One-liner:** Full managed-agents platform with web dashboard, Go backend, agent daemon, autonomous execution, and squad routing — "turn coding agents into real teammates."

**Key features:**
- Agents as first-class teammates: assign issues, track progress, compound reusable skills
- Squads: group agents under a leader for stable routing (`@FrontendTeam`)
- Autopilots: cron/webhook-triggered recurring work
- Web dashboard + CLI + iOS mobile client + daemon
- Works with Claude Code, Codex, Copilot CLI, OpenCode, OpenClaw, Hermes, Gemini, and 5+ more
- Go backend + Next.js 16 frontend + PostgreSQL + Agent daemon architecture
- AGPL-3.0 license, **38.4k stars**, 4.8k forks, 3,797 commits
- REQUIRES Multica Cloud or Docker self-hosting (PostgreSQL, full stack)

### orca (7.05) — stablyai/orca
**One-liner:** Desktop Electron app ("ADE") for running multiple coding agents in parallel worktrees with mobile companion, design mode, and native GitHub/Linear integration.

**Key features:**
- Desktop app (macOS/Windows/Linux) — NOT a terminal tool
- Parallel worktrees: fan one prompt across 5 agents, compare results
- Mobile companion (iOS/Android): monitor and steer agents from phone
- Design Mode: click UI elements to send HTML/CSS/screenshot into agent prompt
- GitHub & Linear native integration with PR browsing and code review
- SSH worktrees for remote agent execution
- Terminal splits with Ghostty-class WebGL rendering
- MIT license, **8.7k stars**, TypeScript + Electron
- Commercial product (YC-backed). Desktop-only, not CLI-friendly for our workflow

### ruflo (7.18) — ruvnet/ruflo (and agent-deck 7.18)
**One-liner:** Ambitious agent meta-harness with 100+ specialized agents, swarm coordination, self-learning, and federation — more kitchen-sink than focused orchestration tool.

**Key features:**
- 100+ specialized agents + 35 plugins + swarm coordination (hierarchical/mesh/adaptive)
- Self-learning via SONA neural patterns and ReasoningBank
- Agent federation: cross-machine zero-trust agent collaboration
- MCP server integration, Claude Code + Codex plugin modes
- Web UI (flo.ruv.io) + Goal Planner UI (goal.ruv.io)
- HNSW vector memory (AgentDB), security guardrails, AIDefence
- MIT license, **61.9k stars**, 7.3k forks — very active (1,548 releases)
- Massive surface area: 7,082 commits, 82% TypeScript, multi-crate Rust
- **Verdict: too much noise. Hard to evaluate what's real vs aspirational.**

### agent-deck (7.18) — asheshgoplani/agent-deck
**One-liner:** Go-based TUI command center for AI coding agents with forking, MCP manager, skills manager, conductor sessions, and Docker sandbox.

**Key features:**
- TUI for managing Claude Code, OpenCode, Codex, Pi, and other agents
- Session forking with inherited conversation context and worktree isolation
- MCP Manager: attach/detach MCP servers per session without touching config files
- Conductor: persistent agent sessions that monitor and orchestrate child sessions
- Docker sandbox: run agents in isolated containers
- Git worktrees with `.worktreeinclude` for gitignored files
- Telegram/Slack bridge for remote monitoring
- Web UI (http://127.0.0.1:8420)
- MIT license, 393 stars, 2,533 commits, Go single binary

---

## Comparison to Current GJC Coordinator Setup

| Capability | GJC Coordinator | claude-squad | agent-deck | multica | orca | ruflo |
|---|---|---|---|---|---|---|
| Terminal TUI | ❌ (CLI only) | ✅ | ✅ | ❌ (Web) | ❌ (Desktop) | Web UI |
| Worktree isolation | ✅ (gjc_delegate) | ✅ tmux | ✅ git worktrees | ❌ | ✅ | ❌ |
| Parallel agents | ✅ (gjc_delegate_team) | ✅ | ✅ | ✅ | ✅ | ✅ |
| Task tracking | ✅ kanban | ❌ | ✅ Conductor | ✅ Issues board | ❌ | ❌ |
| Human supervision TUI | ❌ | ✅ | ✅ | ✅ Web | ✅ Desktop | ✅ Web |
| Mobile monitoring | ❌ | ❌ | ✅ Telegram/Slack | ✅ iOS app | ✅ iOS/Android | ✅ Web |
| Session management | ❌ (task-based) | ✅ | ✅ | ✅ | ✅ | ❌ |
| Skill/Profile management | ✅ (profiles) | ✅ | ✅ Skills Mgr | ✅ Skills | ❌ | ✅ 35 plugins |
| MCP tool management | ❌ | ❌ | ✅ MCP Manager | ❌ | ❌ | ✅ MCP server |
| Self-hosted | ✅ | ✅ | ✅ | ❌ (Cloud) | ✅ Desktop | ✅ |
| Licensing | Open | AGPL-3.0 | MIT | AGPL-3.0 | MIT | MIT |
| Stars | Built-in | 8k | 393 | 38.4k | 8.7k | 61.9k |

**Key gap in current setup:** GJC Coordinator + kanban handles **programmatic orchestration** well (task decomposition → worktree isolation → parallel execution → merge). What's missing is a **real-time human supervision layer** — a way to visually monitor all running agent sessions, see their status at a glance, fork sessions interactively, and attach/detach MCP servers per session without editing config files. The kanban board provides task-level tracking but not session-level live visibility.

---

## Recommendation

### Evaluate: **Agent-deck as GJC companion** (Evaluate)

**Rationale:**
- Agent-deck fills the exact gap GJC doesn't address: real-time TUI supervision
- MCP Manager lets you toggle MCP servers per session — useful for testing new servers before committing them to kanban workflows
- Conductor concept (persistent agent that monitors child sessions) closely mirrors how we use orchestrator profiles
- Git worktree management with forking is complementary to GJC's worktree isolation
- Go single binary, MIT license — low integration cost
- Telegram/Slack bridge matches our existing Discord notification pattern

**Suggested POC:**
1. Install agent-deck alongside existing setup
2. Use it to visually monitor kanban-dispatched sessions
3. Test MCP Manager for toggling experimental MCP servers
4. Evaluate if the Conductor session reduces the need for manual orchestrator oversight

### Skip: **claude-squad**

Claude-squad is simpler but agent-deck has the same capabilities plus MCP Manager, Skills Manager, and Conductor — more features for the same category. If agent-deck proves too heavy, claude-squad is a lightweight alternative.

### Skip: **multica**

Multica requires a cloud service or heavy self-hosting (PostgreSQL, full Go+Next.js stack). It overlaps with our kanban (task tracking), GJC (orchestration), and Discord notifications (telegram bridge). Too much duplication for marginal gain.

### Skip: **orca**

Desktop Electron app doesn't fit our terminal-first workflow. The mobile companion is interesting but not worth the platform shift.

### Skip: **ruflo**

61.9k stars is impressive but the project is too sprawling — 35 plugins, 100+ agents, 7k commits, 1.5k releases. Hard to isolate what's production-ready vs experimental. The federation and self-learning features are visionary but irrelevant to our current needs.

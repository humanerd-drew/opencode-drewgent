# Loop Engineering — Drewgent Assessment

Source: [Loop Engineering — addyo.substack.com](https://addyo.substack.com/p/loop-engineering)
Assessed: 2026-06-13

## The Five Building Blocks + Memory

### 1. Automations (Heartbeat)

| Requirement | Drewgent Status |
|-------------|-----------------|
| Scheduled auto-discovery | `cronjob` tool — cron, intervals, ISO timestamps |
| Background triage | Kanban dispatcher + cron-runner auto-spawns tasks |
| Skill-based automation | Cron job `skills:` list loads skill context |
| Silent runs (empty = quiet) | `no_agent=True` — stdout empty = silent delivery |
| In-session recurring loop | **Missing.** No `/goal` / `/loop` in main CLI session |

**Gap**: Kanban `goal_mode` exists (goal_mode + goal_max_turns + separate
judge model), but only for background workers, not in the interactive CLI.
This is an architectural decision — kanban workers are detached and don't
block the user session.

### 2. Worktrees (Parallel Isolation)

| Requirement | Drewgent Status |
|-------------|-----------------|
| Git worktree for parallel agents | `kanban_create(workspace_kind="worktree")` |
| Config toggle | `config.yaml worktree: true/false` |
| Auto-cleanup | scratch=tmpdir, worktree=git cleanup |
| Subagent isolation | delegate_task: separate terminal session per child |

**Gap**: Worktree not enabled by default. Subagent `delegate_task` does not
get an isolated worktree — children share the parent's working directory.
Kanban tasks with `workspace_kind="worktree"` do get isolation.

### 3. Skills (Project Knowledge)

| Requirement | Drewgent Status |
|-------------|-----------------|
| SKILL.md format | ✅ 100+ skills, YAML frontmatter + markdown |
| Trigger conditions | `trigger:` frontmatter field |
| Skill auto-matching | ❌ Manual via `skill_view()`. Codex/Claude Code auto-match by description. |
| Cross-repo sharing | ✅ `skill_manage` tool, `~/.drewgent/skills/` |
| Intent capture | ✅ 禁.neuron files, P0-P6 vault incidents, provenance convention |

**Gap**: No auto-matching. The model must know to call `skill_view()`.

### 4. Plugins & Connectors (MCP)

| Requirement | Drewgent Status |
|-------------|-----------------|
| MCP protocol | ✅ Native client + mcporter CLI |
| Connectors | MCP catalog (gbrain, specification-website, etc.) |
| Plugin packaging | Plugin system (model-providers, hooks) |
| Shell hooks | `hooks:` config — pre/post tool call, LLM call |

**Gap**: MCP tools are on-demand (tool_search). No auto-discovery of
available MCP servers from inside the agent loop.

### 5. Sub-agents (Maker/Checker Split)

| Requirement | Drewgent Status |
|-------------|-----------------|
| Sub-agent spawning | ✅ `delegate_task` — single + batch (parallel) |
| Different model per subagent | ✅ `delegation.provider/model` config + `agent_profile` override |
| Agent profile files | ✅ **NEW** (2026-06-13) — `.md` files in `$HERMES_HOME/agents/` |
| Static agent definitions | ✅ `subagent-profiles` skill, `.md` files with frontmatter |
| Kanban assignee routing | ✅ Specialist profiles per kanban assignee |

**Note**: Agent profiles were built during this assessment session. See
`subagent-profiles` SKILL.md for details.

### 6. Memory (External State = Spine)

| Requirement | Drewgent Status |
|-------------|-----------------|
| Kanban board as durable state | ✅ `kanban_create/kanban_complete` lifecycle |
| Cron context chaining | ✅ `context_from: [job_id]` |
| Session persistence | ✅ `memory()` tool + `session_search()` (FTS5) |
| Vault as knowledge spine | ✅ P0-P6 Obsidian vault, wikilinks, AGENTS.md |
| State files | ✅ MEMORY.md, USER.md, P6-prefrontal/incidents/ |

**Strongest area.** The quote from the article applies directly:
> "The model forgets everything between runs so the memory has to be on disk
> and not in the context."

Drewgent's P-layer vault + kanban + memory tool implement this with three
redundant systems at different TTLs.

## Overall Score

| Building Block | Score | Key Gap |
|---------------|-------|---------|
| Automations | ★★★★ | No `/goal` in main session (kanban has it) |
| Worktrees | ★★★ | Not default; subagent isolation incomplete |
| Skills | ★★★★★ | Auto-matching weak (manual skill_view required) |
| Plugins & Connectors | ★★★★ | MCP discoverability |
| Sub-agents | ★★★★★ | **NOW CLOSED** — agent profiles + delegate_task integration |
| Memory (spine) | ★★★★★ | Robust |

## Key Insight

The article's core loop shape is already achievable with Drewgent:

> An automation runs every morning on the repo. Its prompt calls a triage skill
> that reads yesterday's CI failures, the open issues, the recent commits, and
> writes the findings into a markdown file or a Linear board. For each finding
> that is worth doing the thread opens an isolated worktree and sends a
> sub-agent to draft the fix, and a second sub-agent reviews that draft against
> the project skills and the existing tests.

This exact pipeline can be built with:
- `cronjob` + `kanban_create` for the morning automation
- `kanban_create(workspace_kind="worktree")` for isolated work
- `task(subagent_type="implementer", description="...", prompt="...")` + `task(subagent_type="reviewer", description="...", prompt="...")`
- kanban board as the "state file" spine
- (Future) Linear MCP bridge for human visibility

---
name: kanban-worker
description: Pitfalls, examples, and edge cases for Hermes Kanban workers. The lifecycle itself is auto-injected into every worker's system prompt as KANBAN_GUIDANCE (from agent/prompt_builder.py); this skill is what you load when you want deeper detail on specific scenarios.
version: 2.0.0
platforms: [linux, macos, windows]
environments: [kanban]
metadata:
  hermes:
    tags: [kanban, multi-agent, collaboration, workflow, pitfalls]
    related_skills: [kanban-orchestrator]
links:
  - "[[@identity/brain/rules]]"
links:
  - "[[@action/skills/SKILL-INDEX]]"
  - "[[@identity/brain/rules]]"
---

# Kanban Worker — Pitfalls and Examples

kanban-worker: this is the detail layer.

## Sub-steps with task()

When your task requires sub-steps (analysis → implementation → testing), use `task(subagent_type="<name>", description="summary", prompt="...")` to spawn subagents. Types: explorer, implementer, tester, reviewer. The `subagent_type` parameter is built into the `task` tool schema — discoverable without loading a skill.

For worktree-isolated or tmux-parallel work, use `gjc_delegate_execute` / `gjc_delegate_team` via GJC Coordinator MCP.

## Workspace handling

Your workspace kind determines how you should behave inside `$HERMES_KANBAN_WORKSPACE`:

| Kind | What it is | How to work |
|---|---|---|
| `scratch` | Fresh tmp dir, yours alone | Read/write freely; it gets GC'd when the task is archived. |
| `dir:<path>` | Shared persistent directory | Other runs will read what you write. Treat it like long-lived state. Path is guaranteed absolute (the kernel rejects relative paths). |
| `worktree` | Git worktree at the resolved path | If `.git` doesn't exist, run `git worktree add <path> ${HERMES_KANBAN_BRANCH:-wt/$HERMES_KANBAN_TASK}` from the main repo first, then cd and work normally. Commit work here. |

## Tenant isolation

If `$HERMES_TENANT` is set, the task belongs to a tenant namespace. When reading or writing persistent memory, prefix memory entries with the tenant so context doesn't leak across tenants:

- Good: `business-a: Acme is our biggest customer`
- Bad (leaks): `Acme is our biggest customer`

## Good summary + metadata shapes

The `kanban_complete(summary=..., metadata=...)` handoff is how downstream workers read what you did. Patterns that work:

**Coding task:**
```python
kanban_complete(
    summary="shipped rate limiter — token bucket, keys on user_id with IP fallback, 14 tests pass",
    metadata={
        "changed_files": ["rate_limiter.py", "tests/test_rate_limiter.py"],
        "tests_run": 14,
        "tests_passed": 14,
        "decisions": ["user_id primary, IP fallback for unauthenticated requests"],
    },
)
```

**Coding task that needs human review (review-required):**

For most code-changing tasks, the work isn't truly *done* until a human reviewer has eyes on it. Block instead of complete, with `reason` prefixed `review-required: ` so the dashboard surfaces the row as needing review. Drop the structured metadata (changed files, test counts, diff/PR url) into a comment first, since `kanban_block` only carries the human-readable reason — comments are the durable annotation channel. Reviewer either approves and runs `kanban_unblock(task_id=...)` (which re-spawns you with the comment thread for any follow-ups) or asks for changes via another comment.

```python
import json

kanban_comment(
    body="review-required handoff:\n" + json.dumps({
        "changed_files": ["rate_limiter.py", "tests/test_rate_limiter.py"],
        "tests_run": 14,
        "tests_passed": 14,
        "diff_path": "/path/to/worktree",  # or PR url if pushed
        "decisions": ["user_id primary, IP fallback for unauthenticated requests"],
    }, indent=2),
)
kanban_block(
    reason="review-required: rate limiter shipped, 14/14 tests pass — needs eyes on the user_id/IP fallback choice before merging",
)

**Side effect:** A `post_tool_call` hook fires after every `kanban_complete`, syncing review-required/blocked/critical tasks to a Linear issue tracker (DEPRECATED 2026-06-14 — Linear integration paused, pending Huly evaluation). The hook stub remains at `~/.drewgent/scripts/kanban_linear_sync.py`.

Use `kanban_complete` only when the task is genuinely terminal
Use `kanban_complete` only when the task is genuinely terminal — e.g. a one-line typo fix, a docs change with no functional consequences, or a research task where the artifact IS the writeup itself.

**Research task:**
```python
kanban_complete(
    summary="3 competing libraries reviewed; vLLM wins on throughput, SGLang on latency, Tensorrt-LLM on memory efficiency",
    metadata={
        "sources_read": 12,
        "recommendation": "vLLM",
        "benchmarks": {"vllm": 1.0, "sglang": 0.87, "trtllm": 0.72},
    },
)
```

**Review task:**
```python
kanban_complete(
    summary="reviewed PR #123; 2 blocking issues found (SQL injection in /search, missing CSRF on /settings)",
    metadata={
        "pr_number": 123,
        "findings": [
            {"severity": "critical", "file": "api/search.py", "line": 42, "issue": "raw SQL concat"},
            {"severity": "high", "file": "api/settings.py", "issue": "missing CSRF middleware"},
        ],
        "approved": False,
    },
)
```

Shape `metadata` so downstream parsers (reviewers, aggregators, schedulers) can use it without re-reading your prose.

## Claiming cards you actually created

If your run produced new kanban tasks (via `kanban_create`), pass the ids in `created_cards` on `kanban_complete`. The kernel verifies each id exists and was created by your profile; any phantom id blocks the completion with an error listing what went wrong, and the rejected attempt is permanently recorded on the task's event log. **Only list ids you captured from a successful `kanban_create` return value — never invent ids from prose, never paste ids from earlier runs, never claim cards another worker created.**

```python
# GOOD — capture return values, then claim them.
c1 = kanban_create(title="remediate SQL injection", assignee="security-worker")
c2 = kanban_create(title="fix CSRF middleware", assignee="web-worker")

kanban_complete(
    summary="Review done; spawned remediations for both findings.",
    metadata={"pr_number": 123, "approved": False},
    created_cards=[c1["task_id"], c2["task_id"]],
)
```

```python
# BAD — claiming ids you don't have captured return values for.
kanban_complete(
    summary="Created remediation cards t_a1b2c3d4, t_deadbeef",  # hallucinated
    created_cards=["t_a1b2c3d4", "t_deadbeef"],                   # → gate rejects
)
```

If a `kanban_create` call fails (exception, tool_error), the card was NOT created — do not include a phantom id for it. Retry the create, or omit the id and mention the failure in your summary. The prose-scan pass also catches `t_<hex>` references in your free-form summary that don't resolve; these don't block the completion but show up as advisory warnings on the task in the dashboard.

## Block reasons that get answered fast

Bad: `"stuck"` — the human has no context.

Good: one sentence naming the specific decision you need. Leave longer context as a comment instead.

```python
kanban_comment(
    task_id=os.environ["HERMES_KANBAN_TASK"],
    body="Full context: I have user IPs from Cloudflare headers but some users are behind NATs with thousands of peers. Keying on IP alone causes false positives.",
)
kanban_block(reason="Rate limit key choice: IP (simple, NAT-unsafe) or user_id (requires auth, skips anonymous endpoints)?")
```

The block message is what appears in the dashboard / gateway notifier. The comment is the deeper context a human reads when they open the task.

## Heartbeats worth sending

Good heartbeats name progress: `"epoch 12/50, loss 0.31"`, `"scanned 1.2M/2.4M rows"`, `"uploaded 47/120 videos"`.

Bad heartbeats: `"still working"`, empty notes, sub-second intervals. Every few minutes max; skip entirely for tasks under ~2 minutes.

## Retry scenarios

If you open the task and `kanban_show` returns `runs: [...]` with one or more closed runs, you're a retry. The prior runs' `outcome` / `summary` / `error` tell you what didn't work. Don't repeat that path. Typical retry diagnostics:

- `outcome: "timed_out"` — the previous attempt hit `max_runtime_seconds`. You may need to chunk the work or shorten it.
- `outcome: "crashed"` — OOM or segfault. Reduce memory footprint.
- `outcome: "spawn_failed"` + `error: "..."` — usually a profile config issue (missing credential, bad PATH). Ask the human via `kanban_block` instead of retrying blindly.
- `outcome: "reclaimed"` + `summary: "task archived..."` — operator archived the task out from under the previous run; you probably shouldn't be running at all, check status carefully.
- `outcome: "blocked"` — a previous attempt blocked; the unblock comment should be in the thread by now.

## Notification routing

You can configure the gateway to receive cross-profile Kanban task notifications by adding `notification_sources` to `~/.config/opencode/opencode.jsonc`.
- `notification_sources: ['*']` accepts subscriptions from all profiles.
- `notification_sources: ['default', 'zilor-ppt']` or `"default,zilor-ppt"` restricts subscriptions to specified profiles.
- Omitting the key keeps the default behavior (profile isolation).

## Provenance Convention (kanban task)

모든 kanban task body는 **trigger/context**를 함께 기록해야 한다. 이 결정을 내리게 된 맥락이 무엇인지 명시.

### Task 생성 시 (kanban_create)

Body에 `## Origin` 섹션 추가:

```
## Origin
- Trigger: [무슨 문제/요청에서 비롯되었는가]
- Session: [YYYY-MM-DD topic]
- Decision rationale: [왜 이렇게 하는가, 어떤 대안이 있었는가]
```

### Task 완료 시 (kanban_complete)

metadata에 provenance 및 leverage score 기록:

```python
kanban_complete(
    summary="...",
    metadata={
        "trigger": "사용자 요청: Y 문제 해결",
        "taste_decision": "왜 이 접근법이 최선이었는지",
        "leverage_score": 4,
        "problems_eliminated": ["problem A", "problem B"],
    },
)
```

---

## Leverage Score Convention

모든 kanban task는 **leverage assessment**를 포함해야 한다. 생성 시 "이 작업이 해결되면 몇 개의 다른 문제가 자동으로 사라지는가?"를 평가하고, 완료 시 실제 impact를 기록한다.

### Task 생성 시 (kanban_create)

Body에 `## Leverage Assessment` 섹션 추가:

```
## Leverage Assessment
- 이 작업 해결 시 자동 해결되는 문제:
  1. ...
  2. ...
- Leverage Score (1-5): N
- 근거: 왜 이 점수인지 간단히
```

### Task 완료 시 (kanban_complete)

metadata에 실제 impact 기록:

```python
kanban_complete(
    summary="...",
    metadata={
        "leverage_score": 4,
        "problems_eliminated": ["problem A", "problem B"],
        "taste_decision": "왜 이 접근법이 최선이었는지",
    },
)
```

### 점수 기준

| Score | 의미 | 예시 |
|-------|------|------|
| 5 | 전체 시스템의 근본 문제 해결 | 아키텍처 변경으로 클래스 전체 제거 |
| 4 | 여러 하위 문제를 한 번에 해결 | 공통 모듈 추출로 N개 중복 제거 |
| 3 | 명확한 개선 + 1-2개 부수 효과 | config 정리로 수동 스탭 제거 |
| 2 | 국소적 개선, 부수 효과 없음 | 버그 수정 |
| 1 | 표면적 변경, 영향 제한적 | 오타 수정, 문서 업데이트 |

---

## Do NOT

- Call `delegate_task` as a substitute for `kanban_create`. `delegate_task` is for short reasoning subtasks inside YOUR run; `kanban_create` is for cross-agent handoffs that outlive one API loop.
- Call `clarify` to ask the human a question. You are running headless — there is no live user to answer. The call will time out (default ~120s) and the task will sit silently in `running` with no signal that it needs input. Use `kanban_comment` (context) + `kanban_block(reason=...)` (decision needed) instead — the task surfaces on the board as blocked, the operator sees it, unblocks with their answer in a comment, and you respawn with the thread.
- Modify files outside `$HERMES_KANBAN_WORKSPACE` unless the task body says to.
- Create follow-up tasks assigned to yourself — assign to the right specialist.
- Complete a task you didn't actually finish. Block it instead.

## Board Maintenance (Periodic Cleanup)___VERIFIED___

Kanban boards accumulate stale tasks over time. Run this cleanup periodically (every 2-4 weeks or on request).

### Process

1. **Read the full board** via the dashboard API (`GET /kanban/api/board` or `kanban_list`). Group by status + board.
2. **Identify duplicates**: same topic keyword in multiple task titles. Compare body completeness, assignee, and creation date. Keep the task with: fuller body, has an assignee, more recent date.
3. **Identify stale items**: todo/ready tasks 14+ days old with no assignee — abandoned. Propose deletion.
4. **Identify completed items**: tasks whose result is just a log line (no retained data). Propose archiving (delete from board).
5. **Present a proposal** before mass deletion. Group by reason (duplicates, stale, completed). Get approval per group.
6. **Execute**: `POST /kanban/api/delete` with `task_id` form param. One task per request. Order: duplicates first, then completed, then stale.

### Duplicate detection heuristics

- Same `[draft-xxx]` prefix + matching keyword = likely duplicate
- Empty body or <100 chars = incomplete, delete candidate
- Unassigned tasks are more disposable than assigned ones
- Older tasks with no progress = stale

### What NOT to delete

- `in_progress` tasks (actively worked)
- Tasks with meaningful result data not stored elsewhere
- Tasks the user explicitly wants to keep

### Post-cleanup

```bash
curl -s http://macmini:8765/kanban/api/board | python3 -m json.tool
```

## Pitfalls

**Worker crash with "pid not alive" on spawn.** When the dispatcher reports `pid NNNNN not alive` repeatedly and the task moves to `gave_up`/blocked, the worker process died before doing any work. Causes:

1. **Python import error at startup** — worker starts but immediately crashes on an `ImportError`. Fix: check the dispatcher log (`~/.drewgent/P4-cortex/scripts/kanban/logs/dispatcher.log` or `grep -r "task_id" ~/.drewgent/P4-cortex/scripts/kanban/logs/workers/`). Common causes: missing venv, broken PYTHONPATH (customize layer), missing cloudflare workers-types, or a dependency that's only available in `node_modules` (npm context missing).
2. **Segfault in workerd/sqlite** — less common. Check system logs.
3. **Dispatcher's spawn mechanism issue on macOS** — fork-exec of `run_kanban_worker.py` may fail if the shell environment has conflicting PYTHONPATH or if the venv's python binary is missing.

**Diagnostic steps for "pid not alive":**
```bash
# 1. Try spawning the worker manually
cd ~/.drewgent
source .venv/bin/activate
python ~/.drewgent/scripts/run_kanban_worker.py --task-id <TASK_ID> 2>&1 | head -50

# 2. Check if it's an import error
python -c "from tools.kanban import kanban_show" 2>&1

# 3. Check PYTHONPATH
echo $PYTHONPATH
```

**Note:** A blocked/crashed kanban task does NOT mean the work needs recovery — the user may have completed it offline in a separate session. Always check the actual filesystem state before assuming recovery is needed (see "Kanban task may be abandoned with work already done outside the board" below).

**Task state can change between dispatch and your startup.** Between when the dispatcher claimed and when your process actually booted, the task may have been blocked, reassigned, or archived. Always `kanban_show` first. If it reports `blocked` or `archived`, stop — you shouldn't be running.

**Kanban task may be abandoned with work already done outside the board.** A blocked/crashed/ready kanban task does NOT mean the work needs recovery or execution — the user may have scrapped it mid-flight and completed the work in a separate session or directly on the filesystem. When a task looks like it stalled or never started:
1. Ask the user if the task is still relevant before assuming recovery is needed
2. **Check the actual project directory on disk** — verify what state the codebase is in
3. **Look for AGENTS.md** (the project's canonical state document) — read it to understand what work is actually done and what's still pending
4. Cross-reference documented state in AGENTS.md against the actual filesystem tree before reporting anything

This applies especially to orchestrator/fan-out tasks where the kanban card shows `status: blocked` and `children: [todo, todo, ...]` — the children may never have run because the orchestrator crashed, but the user may have manually completed the structural work in a different context.

**Workspace may have stale artifacts.** Especially `dir:` and `worktree` workspaces can have files from previous runs. Read the comment thread — it usually explains why you're running again and what state the workspace is in.

**Don't rely on the CLI when the tool is available.** The `kanban_*` tools work across all terminal backends (Docker, Modal, SSH). External CLI wrappers may not be available in containerized backends. When in doubt, use the tool.

## Stay on the original task — don't drift into side investigations

When the user's original request is **Task A**, and during execution you discover something that looks like a related mystery (a port mismatch, a different machine's IP, a process from an older project still running), it is tempting to pivot and investigate that side-quest. **Don't.**

**Why this burns turns:**
- The side investigation often has its own ambiguity (you don't know which machine, which service, which box is on which port), and answering it requires the user — who just asked you to do Task A
- Each clarifying question delays Task A's actual completion
- Even when you correctly identify the side issue, the user wanted the *original* task done, not a peripheral cleanup

**Pattern from real sessions:** User asks "fix SQLITE_BUSY so I can use Huly." You fix SQLITE_BUSY (the actual blocker). User then asks about a port number, hinting at a different machine. You start chasing the IP/port mystery. User cuts you off: *"개소리 하지말고 Huly 관련 검색 다시 해서 와라"* — meaning, stop the side-quest, return to Huly research (the actual original goal).

**Rule:**
1. Finish or block on the **original task** first
2. If a side mystery is genuinely a blocker for the original task, name it in one line and ask the user to confirm before investigating
3. If the side mystery is **not** a blocker, mention it as a footnote ("also noticed X, do you want me to look at that next?") and let the user choose — don't dive in
4. If the user re-steers, acknowledge briefly and re-orient to the original task without defending the detour

**Anti-pattern:** Spending 3+ turns investigating a side mystery that turns out to be a different machine on a different network — pure turn waste, and the user is now annoyed.

**A second pattern from 2026-06-15 Huly NAS session:** User pastes a terminal output that **looks like a context for the current task** but is actually a stack trace from a *different* process. Specifically: the user opens with "huly 계정 생성하려는데 브라우저 콘솔에 [wrangler SQLITE_BUSY output]" and assumes the wrangler error is related. **wrangler / workerd has nothing to do with Huly** (Huly is Node + Mongo/Postgres + Redis; the user's NAS port 8087 hosts Huly, not workerd). The agent's job:

1. **Do not assume pasted text is from the same context.** Look at the prompt text *and* the technical content. The user often dumps multiple terminal windows or pastes one-off outputs. Cross-check the actual environment (`lsof -i :8787` vs `lsof -i :8087`, `docker ps`, the IP they're connecting to).
2. **Disambiguate quickly with one diagnostic**, not a long investigation. A single `lsof -nP -iTCP:8087 -sTCP:LISTEN` tells you "what is on this port, on this Mac, right now" — usually enough to name the real environment.
3. **If the user's pasted error and the real environment disagree, name it in one sentence**: "The wrangler trace you pasted is from a different process (m-log-v2 dev on port 8787); your Huly session is on 192.168.1.53:8087 — that one is on a different machine (NAS). Want me to look at the NAS or fix the Mac dev?"
4. **Don't fabricate a connection between unrelated stack traces.** If the user says "이게 문제라는데" about a wrangler trace and the real blocker is on a different machine, the honest answer is: "those are different systems; the actual Huly blocker is on the NAS, not this Mac." Don't chase the wrangler trace.

**The same lesson applies in reverse**: when *you* (the agent) are chasing a fragile system (like NAS docker containers) and produce reams of guess-and-check debugging output, **stop after 2-3 attempts of the same pattern**. If the same `expect`/ssh race condition has bitten you three times in a row, the right move is to ask the user to either run the command themselves or give you a different transport. The user may be running the same fragile command in 2 minutes; you might still be debugging the race condition 30 minutes later.

**Dispatcher reads wrong DB → tasks never dispatched.** When a custom cron runner dispatches kanban tasks (e.g. `drewgent-cron-runner-001` calling `dispatch_once_*.py`), verify it reads from the **same DB** that `kanban_create`/`kanban_list` use. The native kanban is at `~/.drewgent/kanban.db`. If the dispatcher reads a separate legacy DB (`~/.drewgent/P2-hippocampus/kanban/state/drewgent_tasks.db`), tasks created via the `kanban_*` toolset will never dispatch — they exist in a different database. Fix: point the dispatcher to the native kanban DB.

**Subprocess PYTHONPATH can shadow modules.** When spawning kanban dispatch from a cron runner, explicitly set `PYTHONPATH` in the subprocess env to prevent leaked sys.path entries (e.g. from a trailing colon in `.zshrc`) from shadowing `utils`, `tools.registry`, and other modules. See `shell-init-side-effect-gating` skill for the fix pattern.

**no_agent cron jobs with `.js` scripts fail silently.** `_run_job_script()` in the Drewgent cron scheduler interprets file extension to pick the runner: `.sh`/`.bash` → bash, **everything else → `sys.executable` (Python)**. A `.js` script passed to no_agent cron will be run by the Python interpreter and fail with a syntax error about non-ASCII characters (e.g. the JS comment's em-dash `—` triggers it first). Fix: wrap Node.js scripts in a `.sh` wrapper:

```bash
#!/bin/bash
cd "$(dirname "$0")" || exit 1
HULY_KEY="$(grep '^HULY_KEY=' "$HOME/.drewgent/.env" | head -1 | cut -d= -f2-)"
export HULY_KEY
exec 2>/dev/null
exec node --no-warnings your_script.js
```

Then point the cron `script:` field to the `.sh` file, not the `.js` file. The wrapper pattern also solves credential masking issues (the system replaces `process.env.<SECRET_VAR>` patterns with `***` in file content; reading via grep in a `.sh` wrapper avoids this).

## Tool reference (no external CLI needed)

All kanban operations use the built-in tools:
- `kanban_show(task_id=...)` — show task details
- `kanban_complete(task_id=..., summary=..., metadata={...})` — mark done
- `kanban_block(task_id=..., reason="...")` — block for human input
- `kanban_create(title="...", assignee="...", parents=[...])` — create new task
- `kanban_unblock(task_id=...)` — unblock a blocked task
- etc.

Use the tools from inside an agent; they are the only supported interface.

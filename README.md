# opencode-drewgent

[🇰🇷 한국어](README.ko.md)

AI 에이전트를 처음부터 만드는 대신, 이 **시작 키트**를 복제하세요.

---

## 1. 설치 (2분)

**필요한 것:** 터미널 + GitHub 계정.

```bash
# 1. opencode 설치 (이미 설치했다면 생략)
curl -fsSL https://opencode.ai/install | sh

# 2. 이 레포를 복제
git clone git@github.com:humanerd-drew/opencode-drewgent.git ~/.youragent
cd ~/.youragent

# 3. 실행 (설치 + 실행을 한 번에)
bash scripts/setup.sh && opencode
```

`opencode`가 열리면:

```
# 4. 이름을 바꾸세요
/rename "내 에이전트"
```

이제 에이전트가 명령을 기다립니다. `"내 프로젝트에 로그인 기능을 추가해줘"` 같은 걸 말해보세요.

## 2. 이 키트가 주는 것

| 사용법 | 결과 |
|--------|------|
| `remember("portone v2로 전환")` | 결정이 영구 저장됩니다. 이후 `recall("portone")`로 언제든 검색 가능 |
| `recall("결제 오류")` | 지난 세션의 관련 내용을 찾아줍니다 |
| `graph-rca("배포 실패")` | 문제의 원인을 추적해 리포트를 만듭니다 |
| `"코드 리뷰해줘"` | 전담 리뷰어 에이전트가 검토합니다 |
| `"코드 분석해줘"` | 탐색 전담 에이전트가 아키텍처를 분석합니다 |
| `"이거 계획을 세워줘"` | 플래너 에이전트가 단계별 계획을 만듭니다 |

## 3. 시작 후 할 일

1. **이름 바꾸기** — `@identity/`와 `@action/` 폴더에 에이전트의 이름, 성격, 규칙이 있음
2. **API 키 등록** — `.env` 파일에 LLM 제공자 키를 추가
3. **맞춤 설정** — `skills/` 폴더에 새로운 능력을 추가할 수 있음

> 궁금하면 `opencode` 안에서 `"이 프로젝트 구조가 어떻게 돼?"`라고 물어보세요.

## 설계 철학 — 왜 이렇게 만들었나

각 결정 뒤에는 이유가 있습니다. 이 섹션은 그 이유를 설명합니다.

The vault is the agent's long-term memory and identity. It uses a **brain metaphor** because an agent needs the same layers a human brain has: instincts, personality, memory, senses, reasoning, self-awareness, and planning.

| Layer | Path | Purpose | Why it exists |
|-------|------|---------|---------------|
| **P0 — Brainstem** | `@identity/brain/` | Rules, constraints, 禁 (never-do) rules | Bare minimum safety. If the agent has no absolute rules, it will make the same mistakes repeatedly. These are the "don't delete files without reading them first" layer — enforced at the highest priority. |
| **P1 — Limbic** | `@identity/persona/` | Personality, voice, writing style | The agent needs a consistent character. Without this, every session feels like talking to a different person. Tone, formality, communication preferences live here. |
| **P2 — Hippocampus** | `P2-hippocampus/` | Raw archives — sessions, memories, collected knowledge | The agent's episodic memory. Every session log, every insight, every collected article goes here. It's read-only — the agent doesn't edit raw memory, it compiles from it. |
| **P3 — Sensors** | `@action/` | Tool integrations, gateway configs | Like your eyes and ears. MCP server configs, Discord bot setup, webhooks — anything that lets the agent perceive or act on the outside world. |
| **P4 — Cortex** | `skills/` | Skill definitions, growth records | Learned skills. Each skill is a specialized capability loaded on demand — like a muscle memory for coding patterns, SEO strategy, or payment integration. |
| **P5 — Ego** | `@identity/SELF_MODEL.md` | Self-awareness, compiled wiki | The agent's self-concept. "Who am I, what can I do, what are my constraints?" Also hosts compiled knowledge — weekly summaries of what the agent learned. |
| **P6 — Prefrontal** | `P6-prefrontal/` | Incidents, retrospectives, long-term plans | Executive function. When things go wrong, the post-mortem goes here. When planning next quarter's work, the plan lives here. |

**Why P0-P6 and not flat folders?** The priority numbering is intentional. P0 rules override everything. When there's a conflict between "be polite" (P1) and "never expose secrets" (P0), P0 wins without negotiation. This layered design prevents the agent from reasoning its way around safety rules.

---

## Why Subagent Profiles?

A single agent tries to be good at everything — coding, reviewing, planning, debugging, content writing. That's too much for one context window and one model. Instead:

**Each profile is a specialized expert.** The implementer uses a fast, cheap model (flash) for code generation. The reviewer-critical uses an expensive, thorough model (max) for architecture audits. The analyst is read-only and can't modify files. This separation means:

- **Cost optimization**: Cheap models for production work, expensive ones only when needed
- **Safety**: Read-only profiles can't accidentally modify production
- **Focus**: Each profile's system prompt targets exactly one job
- **Scalability**: Add a new profile without changing existing ones

```
implementer → reviewer → tester    (standard dev workflow)
explorer → planner → implementer   (complex task decomposition)
analyst → sre → architect          (incident response)
```

---

## Why Provenance Convention?

The biggest problem with AI assistants is **ephemeral context**. An agent makes a great decision mid-session, but three sessions later it has no memory of why. The provenance convention solves this by stamping every artifact with its origin story:

```yaml
trigger: "what problem or request caused this"
provenance:
  session: "YYYY-MM-DD topic"
  decision: "why this approach, what alternatives were considered"
```

This does two things: (1) the agent can later `recall("decision: ...")` and get the full context, and (2) the human can audit why something was built a certain way without reading the agent's mind. It's the minimum viable documentation for a system that outgrows one person's memory.

---

## Why Tiered Autonomy?

An agent that asks permission for everything is useless. An agent that never asks is dangerous. Tiered autonomy defines when the agent decides alone and when it must wait:

| Tier | Scope | Authority | Example |
|------|-------|-----------|---------|
| **1** | Trivial changes | **Autonomous.** Complete and report. | Fix a typo, update a comment, save a fact to memory |
| **2** | Established patterns | **Autonomous.** Include provenance. | Apply a known refactoring pattern, add a new cron job like existing ones |
| **3** | Structural changes | **Propose → wait for approval.** | Add a new MCP server, change a skill's directory structure |
| **4** | Architecture decisions | **Proposal only. Human decides.** | Switch vault structure, change delegation strategy |

**Why not just use "ask me if unsure"?** Because that puts the burden on the agent to judge uncertainty, which models are notoriously bad at. Explicit tiers remove the judgment call. If it's Tier 1-2, the agent acts. If it's Tier 3, it drafts. If it's Tier 4, it summarizes. No hesitation, no false confidence.

---

## Why a Skill System?

Skills are not configuration. They are **executable knowledge** — specialized instructions loaded on demand when a task matches their trigger.

```python
# When the user asks about payment integration:
skill("portone-payment-integration")
# → loads PortOne V2 SDK patterns, KG이니시스 setup, webhook handling
```

Each skill is a directory with a `SKILL.md` file and optionally `references/`, `scripts/`, or `templates/`. The skill system means the agent doesn't need to know everything upfront. It learns what it needs, when it needs it. Over time, you build a library of capabilities that grows with your needs.

---

## Why Delegation Patterns?

Two patterns, two trade-offs:

- **`task(subagent_type="...")`** — Same-model, same-session subtask. Fast and cheap because there's no context transfer overhead. Use this for code review after implementation, or for asking the analyst to query the kanban board.
  
- **`gjc_delegate_execute(...)`** — Isolated worktree + separate tmux session. Slower but fully isolated. Use this when you need parallel execution (refactor three modules at once) or when the subtask has side effects that shouldn't pollute the main session.

The rule of thumb: if the subtask takes <5 minutes and doesn't need isolation, use `task()`. If it's complex, long-running, or risky, use delegation.

---

## Why Cron Automation?

The cron scheduler (`scripts/drewgent_cron.py`) turns the agent from reactive (only works when you talk to it) to proactive (works on a schedule). Jobs are defined in `cron/jobs.json`:

```json
{
  "id": "health-check",
  "enabled": true,
  "schedule": { "kind": "interval", "seconds": 300 },
  "deliver": { "kind": "script", "script": "scripts/health_check.sh" }
}
```

**Why not just use system cron?** Because agent jobs need context — they may need to `opencode run` with a specific agent profile, check the kanban board, or report results to Discord. The scheduler wraps all of that.

---

## Why Kanban?

The kanban board is not project management. It's **work persistence**. When you tell the agent "implement this feature," that task goes into the kanban DB with a pipeline (explorer → implementer → reviewer). Each step spawns the right subagent. On completion, the next step triggers automatically.

Without this, an agent crash mid-task loses everything. With kanban, you can restart, inspect task status, and even see which subagent did what. The leverage score (1-5) helps prioritize: "if this task is done, how many other problems disappear?"

---

## From Symptom to Solution

Most agent setups only handle two states: "write code" and "answer questions." This template adds a third: **solve problems systematically**. The loop is simple:

```
Name it → Trace it → Match it → Decide → Fix → Archive
```

### 1. Name it

A problem you can't name is a problem you'll solve twice. Drop the symptom somewhere permanent — `P2-hippocampus/` for raw observations, or a kanban task if it needs action. The label can be ugly. It just needs to exist.

### 2. Trace it

Problems are never isolated. A cron failure connects to launchd, to Python version, to `jobs.json` format, to the last time you changed the scheduler. Use `recall()` to find related decisions. Use `trace_path` in `codebase-memory-mcp` to follow code call chains. Use `@identity/brain/rules.md` to check if you've already made a rule about this.

### 3. Match it

Open `harness/patterns/manufacturing-bridge.md`. Six quality patterns cover most agent-system failure modes:

- **Gradual braking** — warn first, tighten, then stop
- **Structurally impossible** — architecture-level block instead of a rule
- **Flaky vs systematic** — one-time glitch or recurring flaw
- **Automatic stop + human judgment** — when the guardrail trips, who decides?

If your problem doesn't fit any pattern, that's useful data. You might have found a new one.

### 4. Decide

Make a decision. Then immediately save it:

```
remember("Switched from n8n to launchd cron because ...", type="decision")
```

This single line is what separates a system that learns from one that repeats. Next session, `recall("decision: cron")` brings back the full context.

### 5. Fix

Know your autonomy tier:
- **Tier 1-2**: Fix directly, no permission needed
- **Tier 3**: Draft the fix proposal first
- **Tier 4**: Summarize and wait

For multi-step fixes, create a kanban task with a pipeline: `explorer → implementer → reviewer`. Each step spawns the right subagent.

### 6. Archive

Move the resolved incident from `P2-hippocampus/` (raw) to `P6-prefrontal/` (closed). The symptom is documented, the trace is recorded, the pattern is matched, the decision is permanent. Next time a similar problem shows up, the agent can start at step 3.

**Most agents skip steps 2-4 and wonder why they keep rediscovering the same bugs.** The template is designed to make the full loop natural, not forced. You don't have to follow it every time — but when a problem recurs, the loop is already in place.

---

## MCP Servers (Configuration)

The template comes with example MCP server configs in `opencode.jsonc`:

| Server | Type | Purpose |
|--------|------|---------|
| `codebase-memory-mcp` | local stdio | Knowledge graph for your codebase. Search functions, trace call chains, understand architecture. |
| `gajae-code` | local stdio | GJC Coordinator — isolated worktree execution and parallel delegation. Required for `gjc_delegate_*` tools. |
| `safari` | local stdio | Web browsing via Safari Technology Preview. Read pages, fill forms, take screenshots. |
| `astryx` | remote HTTP | Meta's Astryx design system (React 19 + StyleX). 150+ accessible components. |
| `discord` | local stdio | Discord integration — read messages, send responses, manage channels. |
| `wordpress` | local stdio | WordPress content management — create, edit, publish posts via wp-cli. |

**Note:** The `safari` MCP server requires Safari Technology Preview on macOS. The `discord` server needs a `DISCORD_BOT_TOKEN` in your environment.

---

## Known Pitfalls

### Python 3.14: json scope bug
Large functions using `except json.JSONDecodeError:` cause `UnboundLocalError` on `json.loads()`. Fix: `__import__('json').loads()` or extract to a wrapper function.

### macOS bash 3.2
No associative arrays. Use `date -j -f`. Avoid `set -u` with undefined variables.

### Launchd plist patterns
All services should use `KeepAlive { SuccessfulExit: false, ThrottleInterval: 10 }`. Do not use bare `<true/>` or `<false/>`.

### Token/cost data = SQLite, not stderr
opencode stderr logs show `tokens.input=0`. Real usage data is in `~/.local/share/opencode/opencode.db`.

### Rename before use
If you `git clone` this repo and run opencode without renaming `drewgent`, the agent will think its name is "Drewgent" and produce answers in that persona. Run `skill("rename-drewgent")` first.

---

## Generated Content Attribution

For public-facing content only (blog posts, tweets, demo pages):

```
Built with [opencode-drewgent](https://github.com/humanerd-drew/opencode-drewgent)
```

Don't add this to internal notes, private messages, or debug output.

---

## Credits

opencode-drewgent은 이 오픈소스 프로젝트들의 아이디어와 구조를 참고했습니다:

| Project | Author | Contribution | License |
|---------|--------|-------------|---------|
| [opencode](https://opencode.ai) | [Anomaly](https://github.com/anomalyco) | AI 코딩 에이전트 플랫폼 | MIT |
| [codebase-memory-mcp](https://github.com/anomalyco/opencode) | Anomaly | 코드베이스 지식 그래프 | MIT |
| [Gajae-Code](https://github.com/Yeachan-Heo/gajae-code) | [Yeachan-Heo](https://github.com/Yeachan-Heo) | GJC Coordinator — worktree 격리, tmux 병렬 실행 | — |
| [discord-mcp](https://github.com/anomalyco/discord-mcp) | Anomaly | Discord MCP 서버 | MIT |
| [PortOne](https://developers.portone.io) | PortOne | 한국 결제 게이트웨이 SDK | — |
| [Cloudflare Agents SDK](https://developers.cloudflare.com/agents) | Cloudflare | 상태 기반 에이전트 프레임워크 | MIT |
| [Karpathy LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) | Andrej Karpathy | 컴파일 패턴 지식베이스 개념 | — |
| [Ponytail](https://github.com/DietrichGebert/ponytail) | Dietrich Gebert | 코드 최소화 체크리스트 | — |
| [NeuronFS](https://github.com/rhino-acoustic/NeuronFS) | [rhino-acoustic](https://github.com/rhino-acoustic) | 뇌 기반 거버넌스 시스템 | — |
| [specification.website](https://specification.website) | [Joost de Valk](https://github.com/jdevalk) | 웹 스펙 체크리스트 MCP | — |
| [ARD Spec](https://agenticresourcediscovery.org) | Google/MS | Agentic Resource Discovery 표준 | — |
| [agent-wiki](https://github.com/lazymac2x/agent-wiki) | lazymac2x | 제조↔에이전트 하네스 동형성 개념 | MIT |
| [opencrab](https://github.com/opencrab/opencrab) | opencrab | AI 에이전트용 지식 그래프 시스템 | Apache 2.0 |

---

## License

MIT — replace with your own license when forking.

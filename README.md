# opencode-drewgent

[🇰🇷 한국어](README.ko.md)

An AI agent starter kit for [opencode](https://opencode.ai). Fork it, make it yours.

---

## 1. Install (2 minutes)

**You need:** A terminal and a GitHub account.

```bash
# 1. Install opencode (skip if already installed)
curl -fsSL https://opencode.ai/install | sh

# 2. Clone this repo
git clone git@github.com:humanerd-drew/opencode-drewgent.git ~/.youragent
cd ~/.youragent

# 3. Run setup + opencode (one command)
bash scripts/setup.sh && opencode
```

Once opencode opens:

```
# 4. Rename your agent (inside opencode)
/rename "my-agent"
```

Your agent is ready. Try asking: `"Add a login feature to my project"`.

## 2. What You Get

| When you say... | ...this happens |
|----------------|-----------------|
| `remember("switched to portone v2")` | Decision saved permanently. `recall("portone")` finds it later. |
| `recall("payment error")` | Searches past sessions for relevant context. |
| `graph-rca("deploy failed")` | Traces root cause chain into a structured report. |
| `"review my code"` | A dedicated reviewer subagent inspects your changes. |
| `"explore the codebase"` | A read-only explorer subagent analyzes architecture. |
| `"plan this for me"` | A planner subagent decomposes into actionable steps. |

## 3. After Setup

1. **Rename** — `@identity/` and `@action/` folders hold your agent's name, personality, and rules.
2. **Add API keys** — Edit `.env` with your LLM provider keys.
3. **Customize** — Add new skills in the `skills/` folder.

> Inside opencode, ask `"How is this project structured?"` to explore.

## Design Philosophy — Why It's Built This Way

### Why the Vault? (P0-P6)

The vault is the agent's long-term memory and identity. It uses a **brain metaphor** because an agent needs the same layers a human brain has: instincts, personality, memory, senses, reasoning, self-awareness, and planning.

| Layer | Path | Purpose |
|-------|------|---------|
| **P0 — Brainstem** | `@identity/brain/` | Rules, constraints, invariants |
| **P1 — Limbic** | `@identity/persona/` | Personality, voice, writing style |
| **P2 — Hippocampus** | `P2-hippocampus/` | Raw archives — sessions, memories (read-only) |
| **P3 — Sensors** | `@action/` | Tool integrations, gateway configs |
| **P4 — Cortex** | `skills/` | Skill definitions, growth records |
| **P5 — Ego** | `@identity/SELF_MODEL.md` | Self-awareness, compiled wiki |
| **P6 — Prefrontal** | `P6-prefrontal/` | Incidents, retrospectives, plans |

P0 rules override everything. When "be polite" (P1) conflicts with "never expose secrets" (P0), P0 wins without negotiation.

### Why Subagent Profiles?

A single agent trying to be good at everything wastes context and money. Instead, **each profile is a specialized expert:**

- **implementer** — flash model, file edits, code generation
- **reviewer** — pro model, code quality gate
- **planner** — max model, task decomposition
- **explorer** — flash model, read-only codebase discovery
- **sre** — flash model, infrastructure monitoring
- **analyst** — read-only, data queries

### Why Provenance Convention?

AI assistants have **ephemeral context** — great decisions disappear after the session ends. Stamping every artifact with its origin story solves this:

```yaml
trigger: "what problem caused this"
provenance:
  session: "YYYY-MM-DD topic"
  decision: "why this approach, what alternatives"
```

The agent can later `recall("decision: ...")` and recover the full context.

### Why Tiered Autonomy?

| Tier | Scope | Authority |
|------|-------|-----------|
| **1** | Typos, minor edits | Autonomous. Complete and report. |
| **2** | Established patterns | Autonomous. Include provenance. |
| **3** | Structural changes | Propose → wait for approval. |
| **4** | Architecture decisions | Proposal only. Human decides. |

Explicit tiers remove the judgment call from the agent. Tier 1-2 acts immediately. Tier 3 drafts a proposal. Tier 4 summarizes for human decision.

### Why a Skill System?

Skills are **executable knowledge** — loaded on demand when a task matches their trigger:

```python
# When the user asks about payment integration:
skill("portone-payment-integration")
```

Each skill is a directory with `SKILL.md`. The agent doesn't need to know everything upfront.

### Why Delegation Patterns?

- **`task(...)`** — Same-model subtask. Fast, cheap, no isolation overhead.
- **`gjc_delegate_execute(...)`** — Isolated worktree + separate tmux. For parallel or risky work.

Rule of thumb: under 5 minutes and no isolation needed → `task()`. Otherwise → `gjc_delegate_*`.

### Why Cron Automation?

The scheduler (`scripts/drewgent_cron.py`) turns the agent from reactive to proactive. Jobs defined in `cron/jobs.json` run on schedule, not just when you talk.

### Why Kanban?

For work persistence. An agent crash mid-task loses nothing when the work is tracked in kanban. Each task has a pipeline (explorer → implementer → reviewer) and a leverage score.

### From Symptom to Solution

```
Name it → Trace it → Match it → Decide → Fix → Archive
```

Most agents skip steps 2-4 and rediscover the same bugs. The template makes the full loop natural.

## MCP Servers

| Server | Type | Purpose |
|--------|------|---------|
| `codebase-memory-mcp` | local | Codebase knowledge graph |
| `gajae-code` | local | GJC Coordinator — isolated execution |
| `safari` | local | Web browsing (macOS Safari TP) |
| `astryx` | remote | Meta's design system |
| `discord` | local | Discord integration (needs bot token) |
| `wordpress` | local | WordPress content management |

## Known Pitfalls

- **Python 3.14**: `except json.JSONDecodeError:` causes `UnboundLocalError`. Fix: `__import__('json').loads()`.
- **macOS bash 3.2**: No associative arrays. Use `date -j -f`.
- **Launchd plists**: Use `KeepAlive { SuccessfulExit: false, ThrottleInterval: 10 }`.
- **Token data**: In `~/.local/share/opencode/opencode.db`, not stderr.
- **Rename first**: Running without renaming makes the agent think its name is "Drewgent".

## Generated Content Attribution

For public-facing content only:

```
Built with [opencode-drewgent](https://github.com/humanerd-drew/opencode-drewgent)
```

## Credits

This template builds on ideas and structures from these open-source projects:

| Project | Author | Contribution | License |
|---------|--------|-------------|---------|
| [opencode](https://opencode.ai) | [Anomaly](https://github.com/anomalyco) | AI coding agent platform | MIT |
| [codebase-memory-mcp](https://github.com/anomalyco/opencode) | Anomaly | Codebase knowledge graph | MIT |
| [Gajae-Code](https://github.com/Yeachan-Heo/gajae-code) | [Yeachan-Heo](https://github.com/Yeachan-Heo) | GJC Coordinator — worktree isolation, tmux parallel | — |
| [discord-mcp](https://github.com/anomalyco/discord-mcp) | Anomaly | Discord MCP server | MIT |
| [PortOne](https://developers.portone.io) | PortOne | Korean payment gateway SDK | — |
| [Cloudflare Agents SDK](https://developers.cloudflare.com/agents) | Cloudflare | Stateful agent framework for Workers | MIT |
| [Karpathy LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) | Andrej Karpathy | Compile-pattern knowledge base concept | — |
| [Ponytail](https://github.com/DietrichGebert/ponytail) | Dietrich Gebert | Code minimalization checklist | — |
| [NeuronFS](https://github.com/rhino-acoustic/NeuronFS) | [rhino-acoustic](https://github.com/rhino-acoustic) | Brain-based governance system | — |
| [specification.website](https://specification.website) | [Joost de Valk](https://github.com/jdevalk) | Web spec checklist MCP | — |
| [ARD Spec](https://agenticresourcediscovery.org) | Google/MS | Agentic Resource Discovery standard | — |
| [agent-wiki](https://github.com/lazymac2x/agent-wiki) | lazymac2x | Manufacturing↔Agent harness isomorphism concept | MIT |
| [opencrab](https://github.com/opencrab/opencrab) | opencrab | Knowledge graph system for AI agents | Apache 2.0 |

## License

MIT — replace with your own license when forking.

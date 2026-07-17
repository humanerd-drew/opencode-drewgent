---
title: Brain Rules — {{AGENT_NAME}}
type: document
space: concept
tags: [concept, rules]
created: {{DATE}}
updated: {{DATE}}
links:
  - "[[@identity/SELF_MODEL]]"
  - "[[@identity/persona/SOUL]]"
  - "[[@identity/persona/writing-style-guide]]"
---

# {{AGENT_NAME}} — Critical Rules

P0 (Brainstem) rules always override higher layers. No exceptions.

## Never-Do Rules

| Rule | Description |
|------|-------------|
| No destructive commands | `rm -rf /`, `rm -rf ~`, `rm -rf ./*` — never |
| Read before write | Never modify a file without reading it first |
| Never hardcode secrets | API keys, tokens, passwords — env vars only |
| QA gate | Never declare completion without verification |
| Subagent verify | Never accept subagent output without review |
| Filesystem is truth | Read files directly, don't trust memory |
| No big-bang refactoring | One change at a time, verify between |
| YAGNI | No speculative abstraction, minimize deps |
| Answer-first | Conclusion before process in CLI output |
| Trace before fix | Before modifying any system: map the full behavior chain, find the missing link, then fix. Never skip diagnosis. |

## 4 Karpathy Coding Principles

1. **Think Before Coding** — State assumptions. Ask when uncertain. Say "I don't know."
2. **Simplicity First** — Minimal code. If 200 lines can be 50, make it 50.
3. **Surgical Changes** — Only what's requested. Remove orphans. Leave the rest.
4. **Goal-Driven Execution** — Define success criteria. Test first. Iterate.

## Quality Architecture

### Layer 0: Structural (always ON — OS/filesystem level)
- Safety rails that cannot be bypassed by the agent
- Permission boundaries, env var isolation, file-level guards

### Layer 1: Principles (always ON — behavioral)
- Gradual braking: 4-step incident response (warn → tighten → slow → stop)
- Auto-stop + human-in-the-loop: escalate before irreversible action
- Flaky vs systematic: classify failures, prevent recurrence
- Two-eye principle: build-green ≠ live-works

### Layer 2: Process (OFF by default — explicit invocation)
- Pre-mortem for new cron/skill/RISK items
- Bridge lint for cross-reference integrity

## Related

- [[@identity/SELF_MODEL]] — Self-awareness and identity
- [[@identity/persona/SOUL]] — Personality and voice
- [[@identity/persona/writing-style-guide]] — Writing conventions

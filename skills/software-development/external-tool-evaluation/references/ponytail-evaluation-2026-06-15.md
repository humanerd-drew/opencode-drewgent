# Ponytail Evaluation — 2026-06-15

## Source
https://github.com/DietrichGebert/ponytail

## One-liner
An AI agent ruleset that enforces YAGNI -> stdlib -> native feature -> existing dep -> one line -> minimum code dependency chain.

## Why evaluated
User saw it trending (9k+ stars in 3 days) and asked to review for Drewgent adoption.

## Maturity snapshot (2026-06-15)
- Stars: 9,215 (created 3 days ago — explosive viral growth)
- Forks: 393, License: MIT
- Platform support: 11 agents (Claude Code plugin, Codex, Cursor, Windsurf, Cline, Copilot, Aider, Kiro, Gemini CLI, pi, OpenCode)
- Open issues: 2

## Tool category
**Agent behavior ruleset** — not a library, not an MCP server. A prompt-level modification that changes how the agent thinks before writing code.

## Core ruleset (portable)
1. Does this need to exist? (YAGNI)
2. Stdlib does it? Use it.
3. Native platform feature? Use it.
4. Installed dependency? Use it.
5. One line? Make it one line.
6. Only then: minimum that works.

## Guardrails (what it protects from minimization)
- Input validation at trust boundaries
- Error handling preventing data loss
- Security
- Accessibility
- Hardware calibration
- Explicitly requested features

## Deferral mechanism
Shortcuts marked with `ponytail:` comments naming the ceiling and upgrade path. Non-trivial logic leaves one runnable assert/self-check.

## Benchmarks (self-reported)
- 80-94% less code
- 47-77% less cost
- 3-6x faster
- Tested: email validator, debounce, CSV sum, countdown timer, rate limiter (5 tasks x 3 models x 10 runs)

## Plugin infrastructure (platform-specific, separate value)
- CLI commands: /ponytail [lite|full|ultra|off], /ponytail-review, /ponytail-audit, /ponytail-debt
- Claude Code plugin system (marketplace install)
- OpenCode plugin (ponytail.mjs)
- Level system (lite = mild, ultra = aggressive)

## Drewgent integration assessment

### Ruleset value
High. Drewgent already has karpathy_coding_principles.neuron with DRY/YAGNI but lacks an injected per-turn checklist. The 6-step chain is concise, language-agnostic, and aligns with existing philosophy.

### Plugin value
Low for Drewgent. Plugin assumes Claude Code / Codex ecosystem. Drewgent uses Hermes Agent + opencode-go. Commands (/ponytail-review, /ponytail-debt) could be replicated as Hermes skills if ruleset proves useful.

### Recommended approach
H1 (POC): Copy ruleset only into Drewgent AGENTS.md or a skill. Zero code change, test-driven.
H2 (skillize): If POC works, build /ponytail-review equivalent as a Drewgent skill.
H3 (plugin): Not recommended — platform mismatch and vendor lock-in risk.

### Key caution
This is a 3-day-old project. The ruleset itself is stable and proven (just prompt engineering), but the plugin infrastructure may change rapidly. Adopting the ruleset carries near-zero risk; adopting the plugin carries integration risk.

## Decision
POC proposed to user. Awaiting approval.

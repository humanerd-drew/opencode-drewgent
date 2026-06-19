---
title: Contributing
type: guide
space: concept
tags: [concept, contributing]
---

# Contributing to opencode-drewgent

Thanks for your interest. This repo is opinionated — it reflects specific architectural decisions and taste. Contributions that align with those decisions are welcome.

## What We Value

1. **Bug fixes** — crashes, incorrect behavior, data loss. Always top priority.
2. **Skill improvements** — better instructions, better examples, better handoffs.
3. **Documentation** — clearer README, better cross-references, Korean/English parity.
4. **New agent profiles** — only if they fill a genuine gap in the pipeline.
5. **New skills** — only if broadly useful. Most new skills should be narrow and deep.

## What We Don't Want

- **New dependencies** — this repo runs on opencode + Python stdlib. Avoid adding PyPI packages.
- **Speculative abstractions** — don't add a "plugin system" because "someone might need it later."
- **Framework migrations** — no, we're not switching to LangChain.
- **Cosmetic changes** — reformatting, renaming without reason, style wars.

## Before Contributing

1. Read the [README](README.md) and [AGENTS.md](AGENTS.md) to understand the architecture.
2. Check `P6-prefrontal/proposals/` for relevant design decisions.
3. Check existing skills and profiles for patterns to follow.

## Pull Request Process

1. One change per PR. Atomic > monolithic.
2. Include provenance in your change: what problem, what context, why this approach.
3. If changing skill/profile behavior, document the handoff contract implications.
4. Verify with `python3 -c "import py_compile; py_compile.compile('your_file.py')"`.
5. PRs that add dependencies will be closed without review.

## Code of Conduct

Be constructive. Assume good faith. Disagree with ideas, not people.

This is a small, focused project. If something doesn't fit, we'll say so directly.

# Taste Framework (Pratik Bhavsar) — Reference Summary

**Source**: https://pakodas.substack.com/p/how-to-be-a-30x-ai-engineer-with-a-taste
**Author**: Pratik Bhavsar
**Published**: 2026-02-19
**Tag**: #ai-engineering #taste #evaluation-framework

## Core Thesis

In the AI era (post-Nov/Dec 2025 when Opus 4.5, GPT-5.2, Gemini 3 crossed the capability line), code generation is approaching commodity. **Taste** — the quality of your internal evaluation function — is the differentiator.

## The Three Forms of Taste

| Form | Definition | Reference Example |
|------|------------|-------------------|
| **Recognition** | Evaluating finished artifacts; knowing good from bad before explaining why | Emma Tang: "It's a matter of taste as to whether a system is actually really clean, scalable, and not duplicative" |
| **Compass** | Knowing what to build next; sensing the right direction before the system exists | Boris Cherny: 20 prototypes of todo list in 2 days before landing on the right one |
| **Vision** | Knowing what will matter in 2 years; picking the right problem, not just the right solution | SQ Mah: "Humans define evolution"; Codex team prioritizing "planning with rich context" |

### Unified Definition

Taste is the **quality of your internal evaluation function**. Recognition = evaluates finished artifacts. Compass = evaluates possibilities/directions. Vision = evaluates futures/trajectories.

## The Five Zones of Value Creation

| Zone | Description | Example |
|------|-------------|---------|
| **1: Problem Selection** | Choosing what to work on — which problem, if solved, makes 5 others disappear | Peter Steinberger: spends time planning with agent, only delegates execution |
| **2: System Architecture** | How pieces fit together — longest half-life decision | Claude Code: "write as little business logic as possible, let model do the work" |
| **3: Quality Judgment** | Knowing when good enough vs needs more work | Codex: tiered code review — AI review for non-critical, human for core agent code |
| **4: User Empathy** | Understanding what the human needs | Boris: contextual loading spinner messages (nobody asked for it) |
| **5: Communication & Storytelling** | Framing what you've built | Peter Steinberger's OpenClaw narrative: "one guy building a full team's output" |

## Paired Examples (With/Without Taste)

| Situation | Without Taste | With Taste |
|-----------|---------------|------------|
| Tech stack choice | "TypeScript because popular" | Claude Code chose TS because model excels at it; Codex chose Rust for culture effects |
| AI code you didn't read | "Tests pass, ship it" | Steinberger: maintains architectural understanding + verification layer |
| Feature request | Implement as spec'd | Boris: 20 prototypes finding the inevitable design |
| Documentation | Generic README | Codex: AGENTS.md for AI agents, structured for model success |
| PR review | Old review process flooded | Emma: require prompt alongside PR; Steinberger: PRs = "prompt requests" |

## Key Quotes

> "Everybody can be a 10x engineer now, as long as you have people with good software taste." — Emma Tang

> "I've never felt this much behind as a programmer. The profession is being dramatically refactored." — Andrej Karpathy (Dec 2025, reversing his Oct 2025 "slop" stance)

> "Most code is boring data transformation. Focus energy on system design instead." — Peter Steinberger

> "The model IS the product, and everything around it should be as thin as possible." — Claude Code philosophy

## 90-Day Plan (Summary)

- **Month 1**: Recognition taste — study 10 developer tools (15-min analysis each), study 10 research papers for methodology
- **Month 2**: Compass taste — make 3 product decisions with explicit reasoning, constraint writing practice
- **Month 3**: Vision taste — write a technology roadmap, practice 2-year-out thinking

## Application Notes

When using this framework for assessment:
- **Recognition taste** correlates with: code review practices, refactoring principles, quality gates
- **Compass taste** correlates with: architecture decisions, technology choices, "what to build next" judgment
- **Vision taste** correlates with: long-term investment in infrastructure, skill library evolution, system philosophy
- The 5 zones map well to: backlog management (zone 1), codebase structure (zone 2), QA pipeline (zone 3), user experience design (zone 4), public communication (zone 5)

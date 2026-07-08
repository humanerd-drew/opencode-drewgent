---
title: Garry Tan Complexity Ratchet 2026
status: published
type: concept
space: concept
tags: [concept, insights]
created: 2026-05-20
updated: 2026-05-20
aliases:
  - /insights/garry-tan-complexity-ratchet
links:
  - "[[P0-brainstem/brain/rules]]"
  - "[[P4-cortex/growth/INTEGRATION_PROTOCOL]]"
  - "[[P4-cortex/knowledge/garry-tan-building-with-ai-series]]"
  - "[[P4-cortex/knowledge/garry-tan-unified-architecture-loragent-review]]"
---



# Garry Tan — "The AI Agent Complexity Ratchet: Why 90% Test Coverage Is Required"
# Series #7 — Building with AI

## Meta
- Author: Garry Tan (Y Combinator CEO)
- Published: May 12, 2026
- Stats: 168K views, 768 likes, 127 reposts, 1531 bookmarks
- Series: 7th in "building with AI" series (1-6 links present)

## Core Thesis
**90% test coverage is required — and AI agents made it free to get.**

50년간 소프트웨어 엔지니어링은 "에러 방지" 중심으로 운영됨.
에러 = 재앙이었음. 한 번의 실수가 프로덕션 크래시.
90% coverage이 해답: 시스템이 개선만 되고, 나빠질 수 없게 만드는 lock.

## What He Built

### Two OSS Projects
1. **GStack** — AI coding agents better (23 specialist skills, multi-host: Claude Code, Codex, Cursor, etc.)
2. **GBrain** — turns everything you read/write into searchable knowledge base for AI

### Scale
- ~970,000 lines of code
- 665 test files
- Mostly written by **Claude Code + Codex** at his direction
- 15 simultaneous Conductor sessions most of the time
- 72小时内: 14 PRs merged, ~29,000 lines new code

## The Complexity Ratchet

```
90% coverage → no bugs → safe refactoring → complexity increase possible
→ faster feature dev → more coverage → ...
```

**システムが改善만 가능, 나빠질 수 없음** = Ratchet (棘輪)

Speed vs Quality trade-off 없음. "Ship fast, break things" vs "Move slow, ship right" — **둘 다 버림**.

## Key Quotes

> "Speed and quality are supposed to trade off. Ship fast, break things. Move slow, ship right. Pick one."
> "You don't have to pick anymore. The unlock is 90% test coverage -- and AI agents made it free to get there."
> "For fifty years, that level of verification cost too much human willpower to sustain. Now the agent writes the tests alongside the code."

## Software Was Brittle (50 years)

1. **에러 = 재앙** — one edge case miss = crash in production
2. **DB migration 위험** — bad migration = lose customer data
3. **암묵적 지식 문제** — one person who understands it quits = nobody knows why it works
4. **전체 시스템이 그 사람에 의존** — tribal knowledge = architectural debt

## The Unlock: AI Made 90% Coverage Free

- Agent writes tests alongside code (not after)
- Human willpower no longer the bottleneck
- "The agent writes the tests alongside the code"
- Result: complexity ratchet — system can only get better, never worse

## Architecture Implications for Loragent (HP-3 Implementation: 2026-05-15)

1. **Test coverage as quality gate** — Loragent's 禁task_qa_gate aligns with this thesis
2. **Complexity ratchet = self-improving agent** — Trend Harvester fits here
3. **AI makes rigorous verification free** — Agent writes tests alongside code
4. **Speed + quality no longer trade-off** — parallels Loragent's TDD-PDCA loop
5. **HP-3 implemented (2026-05-15)**: 3-phase QA gate (contract/micro/full), delivery blocking, QA_GUIDANCE_TEMPLATE injected into system prompt for latent tasks

## Related
- GStack: https://github.com/garrytan/gstack (95K+ stars)
- GBrain: https://github.com/garrytan/gbrain
- Series 1-6: Not accessible (Xitter article format requires login)


- [[P4-cortex/knowledge/garry-tan-unified-architecture-loragent-review]]
- [[P4-cortex/knowledge/garry-tan-building-with-ai-series]]
- [[P0-brainstem/brain/rules]]

## Tags
#garrytan #ai-agent #test-coverage #complexity-ratchet #gstack #gbrain #building-with-ai #yc

## Links
- [[P4-cortex/growth/INTEGRATION_PROTOCOL]]

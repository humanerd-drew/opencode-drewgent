---
title: Garry Tan Building With Ai Series
status: published
type: concept
space: concept
tags: [concept, insights]
created: 2026-05-20
updated: 2026-05-20
aliases:
  - /insights/garry-tan-building-with-ai
links:
  - "[[P4-cortex/growth/INTEGRATION_PROTOCOL]]"
  - "[[P4-cortex/knowledge/NEURONFS_RULES]]"
  - "[[P4-cortex/knowledge/garry-tan-complexity-ratchet-2026]]"
  - "[[P4-cortex/knowledge/garry-tan-unified-architecture-drewgent-review]]"
---



# Garry Tan — "Building with AI" 시리즈 전체 정리

## 개요
- Author: Garry Tan (Y Combinator CEO)
- 시리즈: 7개 기사 (2026년 4월~5월)
- 주제: AI 에이전트로 소프트웨어 개발하는 방법론

---

# Article 1: "Thin Harness, Fat Skills"
## How to Make AI Agents Actually Understand Your Data

**Stats**: 153만 조회, 4133 likes, 609 reposts, 11482 bookmarks
**Date**: 2026년 4월 11일
**Link**: https://x.com/garrytan/status/2042925773300908103

### Steve Yegge 인용
> "People using AI coding agents are 10x to 100x as productive as engineers using Cursor and chat today, and roughly 1000x as productive as Googlers were back in 2005."

**핵심**: 2x的人和 100x的人는 같은 모델을 씁니다. 차이는 지능이 아니라 **아키텍처** — five concepts that fit on an index card.

### The Harness is the Secret Sauce

Anthropic이 2026년 3월 31일 Claude Code 전체 소스 코드(512,000 줄)를 npm registry에 실수로 게시함. 이를 읽고 확인한 것: 

- Live repo context
- Prompt caching
- Purpose-built tools
- Context bloat minimization
- Structured session memory
- Parallel sub-agents

**이것들이 모델을 더 똑똑하게 만드는 게 아님. 올바른 맥락을, 올바른 타이밍에, 노이즈 없이 模型에게 주는 것.**

### Five Definitions

#### Definition 1: Skill File

스킬 파일 = 재사용 가능한 markdown 절차. **무엇을(WHAT)** 하지 않고 **어떻게(HOW)** 할지 가르침.

**핵심 인사이트**: 스킬 파일은 메서드 콜처럼 작동함. 파라미터를 받음. 다른 인자로 호출. Same procedure, radically different capability.

예: `/investigate` 스킬 — 7단계:
1. scope the dataset
2. build a timeline
3. diarize every document
4. synthesize
5. argue both sides
6. cite sources

파라미터: TARGET, QUESTION, DATASET

- Dr. Sarah Chen + 2.1M discovery emails → 의료 연구 분석가 (whistleblower silencing 분석)
- Pacific Corporate Services + FEC filings → 포렌식 수사관 (shell company 캠페인 기부 추적)

**이것은 prompt engineering이 아님. 소프트웨어 디자인. Markdown을 프로그래밍 언어로, human judgment를 runtime으로 사용.**

#### Definition 2: Harness

Harness = LLM을 실행하는 프로그램. 4가지만 함: 
1. 모델을 루프로 실행
2. 파일 읽고 쓰기
3. 컨텍스트 관리
4. 안전 강제

**Anti-pattern**: fat harness + thin skills
- 40+ tool definitions가 context window의 절반을 먹음
- God tools (2~5초 MCP round-trips)
- REST API wrappers
- 3x tokens, 3x latency, 3x failure rate

**대안**: Playwright CLI — 각 브라우저操作 100ms. Chrome MCP는 screenshot+find+click+wait+read에 15초. Playwright CLI는 200ms. **75x faster.**

#### Definition 3: Resolver

Resolver = 맥락의 라우팅 테이블. **"task type X가 나타나면 document Y를 먼저 로드"**

- Skills say HOW
- Resolvers say WHAT to load WHEN

예: 개발자가 프롬프트를 변경. Resolver 없으면 shipping. Resolver 있으면:
1. 모델이 `docs/EVALS.md`를 먼저 읽음
2. "run the eval suite, compare scores, if accuracy drops > 2%, revert and investigate"
3. 개발자는 eval suite가 있다는 걸 몰랐음 — resolver가 올바른 맥락을 올바른 순간에 로드함

**Claude Code의 built-in resolver**: 모든 스킬의 description 필드 → 모델이 user intent를 skill descriptions에 자동 매칭.

**Garry의 confession**: CLAUDE.md가 20,000줄. 모든 quirk, 모든 pattern, 모든 lesson. 완전히 불합리. 모델의 attention이 저하됨. Claude Code가 literally 줄이라고 말함.

**수정 후**: 약 200줄. 문서에 대한 포인터만. Resolver가 필요한 순간에 올바른 것을 로드.

#### Definition 4: Latent vs. Deterministic

모든 단계는 둘 중 하나: 
- **Latent space**: 지능이 있는 곳. 모델이 읽고, 해석하고, 결정. Judgment. Synthesis. Pattern recognition.
- **Deterministic**: 신뢰가 있는 곳. Same input, same output. SQL. Code. Numbers.

**LLM은 8명을 dinner table에 앉힐 수 있음. 800명에게 물으면 환각 seating chart 생성** (看起来 plausible but completely wrong). That's a deterministic problem forced into latent space.

#### Definition 5: Diarization

모델이 주제에 대한 모든 것을 읽고 구조화된 프로필을 작성: **50개 문서 읽고 → 1 page의 judgment 출력**.

No SQL query produces this. No RAG pipeline produces this.

### The Architecture

Three layers: 

```
[Fat Skills]     ← Markdown procedures encoding judgment/process/domain knowledge (90% of value)
[Thin CLI Harness] ← ~200 lines. JSON in, text out. Read-only by default.
[Your App]       ← QueryDB. ReadDoc. Search. Timeline. The deterministic foundation.
```

**원칙**: Push intelligence UP into skills. Push execution DOWN into deterministic tooling. Keep the harness THIN.

---

## Related
- [[P4-cortex/knowledge/garry-tan-unified-architecture-drewgent-review]]
- [[P4-cortex/knowledge/garry-tan-complexity-ratchet-2026]]
- [[P4-cortex/knowledge/NEURONFS_RULES]]

## Links
- [[P4-cortex/growth/INTEGRATION_PROTOCOL]]

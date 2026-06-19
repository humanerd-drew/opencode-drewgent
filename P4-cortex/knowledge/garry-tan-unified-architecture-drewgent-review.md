---
title: Garry Tan Unified Architecture Drewgent Review
status: published
type: concept
space: concept
tags: [concept, insights]
created: 2026-05-20
updated: 2026-05-20
aliases:
  - /insights/garry-tan-architecture
links:
  - "[[P0-brainstem/brain/Drewgent-brain/P0-brainstem/禁/禁task_qa_gate.neuron]]"
  - "[[P0-brainstem/brain/rules]]"
  - "[[P3-sensors/resolver/RESOLVER.md]]"
  - "[[P4-cortex/growth/INTEGRATION_PROTOCOL]]"
  - "[[P4-cortex/knowledge/garry-tan-building-with-ai-series]]"
  - "[[P4-cortex/knowledge/garry-tan-complexity-ratchet-2026]]"
  - "[[P4-cortex/knowledge/garry-tan-complexity-ratchet-2026.md]]"
  - "[[P5-ego/SELF_MODEL]]"
---



# Garry Tan — "Building with AI" 통합 아키텍처
## 7개 시리즈 종합 분석 + Drewgent 보완 제안

**Author**: Garry Tan (Y Combinator CEO)
**Series**: 7개 기사 (2026년 4월~5월)
**Target**: Drewgent Architecture Review
**Status**: HP-2/HP-3 구현 완료 (2026-05-15)

---

## 시리즈 요약

| # | 제목 | 날짜 | 조회 | 핵심 주장 |
|---|------|------|------|----------|
| 1 | Thin Harness, Fat Skills | Apr 11 | 153만 | 5개 정의 소개 |
| 2 | Resolvers: The Routing Table | Apr 16 | 32만 | Context routing |
| 3 | On the LOC Controversy | Apr 18 | 13만 | AI 생산성 측정 |
| 4 | Naked Models Are Stupider | Apr 19 | 15만 | 모델=엔진,≠자동차 |
| 5 | The Skillify Manifesto | Apr 22 | ? | LangChain 비판 |
| 6 | Meta-Meta-Prompting | May 5 | **140만** | Personal AI OS |
| 7 | The Complexity Ratchet | May 12 | 16만 | 90% 테스트 커버리지 |

---

## Garry Architecture 핵심 정리

### 5개 정의 (Article 1)

**Definition 1: Skill File**
Markdown 절차 — WHAT이 아닌 HOW를 가르침. 파라미터로 호출.

**Definition 2: Harness**
LLM 실행 프로그램 — 4가지만 함: 모델 루프, 파일读写, 컨텍스트 관리, 안전 강제.
Anti-pattern: fat harness (40+ tools) + thin skills.

**Definition 3: Resolver**
"task type X → document Y" 매핑 테이블. on-demand doc load.

**Definition 4: Latent vs. Deterministic**
Latent: 모델 판단/합성. Deterministic: Same input → Same output.

**Definition 5: Diarization**
50개 문서 → 1 page judgment 출력. RAG/SQL 불가.

### The Complexity Ratchet (Article 7)

```
90% coverage → no bugs → safe refactoring → faster feature dev → more coverage
→ 시스템 개선만 가능, 나빠질 수 없음 (棘輪)
```

~970,000 lines, 665 test files, 72小时内 14 PRs merged.

---

## Drewgent 매핑

| 항목 | Garry Architecture | Drewgent 현재 | 상태 |
|------|-------------------|--------------|------|
| Fat Skills | markdown procedures | `~/.drewgent/skills/*.md` | ✅ 완료 |
| Thin Harness | ~200 lines CLI | `run_agent.py` (8.7K줄) | ⚠️ 분해 필요 |
| HP-2: Latent Detection | Latent vs Deterministic 구분 | `_is_latent_task()` 추가 | ✅ 완료 |
| HP-3: Complexity Ratchet | 90% test coverage | 3-phase QA gate + delivery blocking | ✅ 완료 |
| Context Resolver | on-demand doc load | `RESOLVER.md` 생성 완료 | ✅ 완료 |

---

## HP-3 3-Phase QA Gate 구현 (2026-05-15)

### Flow

```
Latent task 감지 (implement/build/create 등)
  → _is_latent_task() = True
  → emit_qa_gate("contract") + self._qa_task_id set
  → QA_GUIDANCE_TEMPLATE injected into system prompt
      ↓
[Turn 1] contract.json 작성 (criteria)
  → emit_turn_end() → micro emitted
      ↓
[Each turn] micro-qa.json累积
      ↓
[agent-complete] emit_qa_gate("full")
  → full-qa.json must have all_criteria_met=true
      ↓
gateway: qa_gate_status check
  ├── True → delivery 통과
  └── False → ⚠️ blocked
```

### Evidence Files (P2-hippocampus/qa-evidence/{task_id}/)

- `contract.json` — acceptance criteria (written by agent before coding)
- `micro-qa.json` — per-step verification (accumulated across turns)
- `full-qa.json` — final verification (all_criteria_met required for unblock)

### Files Modified

| File | Lines | Change |
|------|-------|--------|
| run_agent.py | +65 | helpers, contract/micro/full emit, qa_gate_status in result |
| agent/prompt_builder.py | +18 | QA_GUIDANCE_TEMPLATE constant |
| gateway/run.py | +17 | delivery blocking check |
| agent/signal_processor.py | ~90 | _on_qa_gate() skeleton auto-generation |
| 禁task_qa_gate.neuron | full rewrite | HP-3 implementation documented |
| RESOLVER.md | updated | HP-2 latent keywords + flow |
| garry-tan-complexity-ratchet-2026.md | updated | HP-3 implementation note |

---

## Related

- [[P3-sensors/resolver/RESOLVER.md]] — Context routing table
- [[P0-brainstem/brain/Drewgent-brain/P0-brainstem/禁/禁task_qa_gate.neuron]] — P0 brain rule
- [[P4-cortex/knowledge/garry-tan-complexity-ratchet-2026.md]] — Article 7 detail
- [[P0-brainstem/brain/rules]] — Karpathy coding principles
- [[P4-cortex/knowledge/garry-tan-building-with-ai-series]]
- [[P4-cortex/knowledge/garry-tan-complexity-ratchet-2026]]
- [[P5-ego/SELF_MODEL]]

## Links
- [[P4-cortex/growth/INTEGRATION_PROTOCOL]]

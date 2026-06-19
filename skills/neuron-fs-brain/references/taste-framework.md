---
title: Taste Framework for AI Engineers
trigger: "Pratik Bhavsar 'How to Be a 30x AI Engineer with a Taste' (Feb 2026)"
provenance:
  session: "2026-06-14 taste-discussion"
  decision: "Taste 개념을 agent 아키텍처 평가 프레임워크로 도입 — AGENTS.md, kanban-worker, neuron-fs-brain에 반영"
---

# Taste Framework — Reference Summary

> Source: [How to Be a 30x AI Engineer with a Taste](https://pakodas.substack.com/p/how-to-be-a-30x-ai-engineer-with-a-taste) by Pratik Bhavsar, Feb 2026
> Core thesis: AI가 코드 생성의 commodity가 된 시대에 엔지니어의 가치를 가르는 핵심 역량은 **taste** (내부 평가 함수의 품질).

---

## Three Forms of Taste

| Form | 정의 | 예시 |
|------|------|------|
| **Recognition** | 완성된 artifact 보고 quality 판단 | "이 시스템이 깔끔한가, 중복이 없는가, 단순한가" |
| **Compass** | 존재하지 않는 시스템의 방향 감지 | "어떤 feature를 만들어야 하는가" — Boris Cherny의 20번 todo prototype |
| **Vision** | 2년 후에 무엇이 중요해질지 예측 | "사업 목표, 시장 동향, 팀 우선순위 이해가 필요해질 것" |

**통합 정의:** Taste는 내부 evaluation function의 품질이다. Recognition = 완성된 artifact 평가. Compass = 방향성/가능성 평가. Vision = 미래 평가.

---

## Five Zones of Value Creation

| Zone | 무엇 | Taste가 중요한 이유 |
|------|------|---------------------|
| 1. **Problem Selection** | 무엇을 작업할지 선택 | "이 문제가 해결되면 5개의 다른 문제가 사라지는가?" |
| 2. **System Architecture** | 조각을 어떻게 맞출지 | 좋은 아키텍처 결정은 2년 후에도 가치가 있음 |
| 3. **Quality Judgment** | 언제 배송할지, 언제 더 다듬을지 | AI는 "good enough"가 무엇인지 모름 |
| 4. **User Empathy** | 사용자가 실제로 무엇을 필요로 하는지 | AI가 가장 못하는 영역 |
| 5. **Communication** | 만든 것을 어떻게 전달할지 | 시장에서 일관되게 저평가되고 보상되는 영역 |

---

## Taste Signals in Practice

### Good taste examples from the article

| 결정 | Taste 있음 | Taste 없음 |
|------|-----------|-----------|
| Tech stack 선택 | Rust → engineering culture shaping; TypeScript → model strength matching | "유명하니까" |
| 모르는 코드 처리 | 아키텍처 이해는 유지, 모델이 생성한 코드는 CI로 검증 | "테스트 통과했으니 OK" |
| Feature 대응 | 20개 prototype으로 방향 탐색 | ticket 구현 → ship |
| 문서화 | AGENTS.md — agent가 성공할 수밖에 없는 환경 설계 | README (설치법 + API endpoint 목록) |
| PR 리뷰 | prompt 리뷰가 코드 리뷰보다 중요 | 기존 리뷰 프로세스 유지 |

### Key quotes

> "Every time there's a new model release, we delete a bunch of code." — Boris Cherny, Claude Code

> "Most code is boring data transformation. Focus energy on system design instead." — Peter Steinberger, OpenClaw

> "A single good architecture decision saves the team months of work over the next year." — Pratik Bhavsar

---

## Application to Drewgent

Drewgent에서 taste를 어떻게 측정하고 개선할지:

1. **Kanban Leverage Score** (1-5): 이 작업이 몇 개의 문제를 해결하는가?
2. **Provenance Tracking**: 모든 결정에 trigger/context 기록 → taste decision의 궤적을 추적 가능
3. **AGENTS.md**: agent-first documentation — agent가 성공할 수밖에 없는 환경 설계
4. **90-Day Plan**: recognition → compass → vision 순서로 taste 개발

### 관련 문서

- `AGENTS.md` — Provenance convention + leverage score convention
- `devops/kanban-worker/SKILL.md` — Leverage score convention
- `neuron-fs-brain/SKILL.md` — Brain governance + taste integration

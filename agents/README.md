---
title: Agent Profiles
description: "Profile definitions for subagent roles — model, provider, instructions, and toolset constraints per role."
created: 2026-06-13
updated: 2026-06-18
---

# Agent Profiles

각 프로필은 하나의 Markdown 파일로 정의됩니다. YAML frontmatter에 모델/프로바이더/도구세트를, 본문에 역할 지침(instructions)을 작성합니다.

## 사용 방식

```
delegate_task(agent_profile="reviewer", goal="...")
# → ~/.drewgent/agents/reviewer.md 로드
# → model/provider/instructions/toolsets 적용
```

## Cost Tier

| Tier | 모델 | 프로필 | 비용 |
|------|------|--------|------|
| **Flash** | deepseek-v4-flash | explorer, implementer, tester, archiver, designer, sre, analyst | OpenCode Go 구독에 포함, 추가 비용 $0 |
| **Pro** | deepseek-v4-pro | reviewer, editor | 구독 포함, 약간 더 느림 |
| **Max** | qwen3.7-max | planner, reviewer-critical, security-reviewer, orchestrator | 구독 포함, 가장 느리지만 추론 품질 최상 |

## Pipeline

```
Tier 1 (단순):
  Implementer(flash) → [optional: Tester(flash)] → Archiver(flash)

Tier 2 (보통):
  Explorer(flash) → Implementer(flash) ↔ Tester(flash) [≤2회 loop]
  → Reviewer(pro) → Archiver(flash)

Tier 3 (복잡):
  Planner(max) → Explorer(flash) → Implementer(flash) ↔ Tester(flash) [≤3회 loop]
  → Reviewer(pro)
  → [보안 관련?] → Security-reviewer(max)
  → [매우 중요?] → Reviewer-critical(max)
  → Archiver(flash)

Content Pipeline:
  Content Manager(pro) → Editor(pro) → Archiver(flash)

Design Pipeline:
  Explorer(flash) [Lazyweb refs] → Designer(flash) → [Implementer(flash)]
  → Reviewer(pro) → Archiver(flash)

Incident Pipeline:
  SRE(flash) → [ESCALATE? → Orchestrator(max)] → Archiver(flash)

Data Request:
  Analyst(flash) → [ESCALATE? → Orchestrator(max)] → Report
```

## 프로필 목록

| 파일 | 역할 | 모델 | Pipeline 위치 |
|------|------|------|-------------|
| `explorer.md` | 탐색/분석 (읽기 전용) | flash | 첫 단계 |
| `planner.md` | 태스크 분해/계획 | max | 복잡한 작업 첫 단계 |
| `orchestrator.md` | 작업 배정/파이프라인 관리 | max | 전체 pipeline 조정 |
| `designer.md` | UI/UX 디자인, 시각 자료 | flash | 설계 단계 |
| `implementer.md` | 구현 | flash | 구현 |
| `tester.md` | 테스트 작성/실행 | flash | 구현 ↔ 테스트 loop |
| `reviewer.md` | 일반 코드 리뷰 | pro | 리뷰 단계 |
| `reviewer-critical.md` | 중요 변경 심층 리뷰 | max | 중요 변경 한정 |
| `security-reviewer.md` | 보안 감사 | max | 보안 관련 변경 한정 |
| `sre.md` | 인프라/배포/인시던트 대응 | flash | 운영 |
| `analyst.md` | 데이터 분석/인사이트 | flash | 분석 |
| `content-manager.md` | 콘텐츠 생성 (CMO) | pro | 콘텐츠 파이프라인 |
| `editor.md` | 콘텐츠 검수/한국어 인퓨전 | pro | 퍼블리시 전 최종 게이트 |
| `archiver.md` | 문서화/기록 | flash | 마무리 |

## Escalation

Explorer, Implementer, Tester, Designer, SRE, Analyst는 `ESCALATE: <reason>` 신호를 보낼 수 있음.
상위 호출자가 감지 → Orchestrator(max)가接手하거나 더 강한 모델로 재시도.

## Agent Office 구조 (14개 프로필)

```
                     ┌─────────────┐
                     │ Orchestrator │  (max) — 전체 pipeline 조정
                     └──────┬──────┘
          ┌─────────────────┼─────────────────┐
          ▼                 ▼                  ▼
   ┌────────────┐   ┌──────────────┐   ┌────────────┐
   │  Planner   │   │ Content Mgr  │   │    SRE     │  (운영)
   │  (max)     │   │  (pro)       │   │  (flash)   │
   └─────┬──────┘   └──────┬───────┘   └──────┬─────┘
         ▼                 ▼                   ▼
   ┌────────────┐   ┌──────────────┐   ┌──────────────┐
   │  Explorer  │   │   Editor     │   │   Analyst    │
   │  (flash)   │   │   (pro)      │   │  (flash)     │
   └─────┬──────┘   └──────────────┘   └──────────────┘
         ▼
   ┌────────────┐
   │  Designer  │
   │  (flash)   │
   └─────┬──────┘
         ▼
   ┌──────────────┐
   │ Implementer  │ ←→ │  Tester  │  (flash, ≤3 cycles)
   └──────┬───────┘    └──────────┘
          ▼
   ┌──────────────┐
   │   Reviewer   │  (pro)
   └──────┬───────┘
          ▼
   ┌──────────────────┐
   │ Security-Reviewer │  (max, conditional)
   │ Reviewer-Critical │  (max, conditional)
   └──────────────────┘
          ▼
   ┌──────────────┐
   │   Archiver   │  (flash)
   └──────────────┘
```

---
title: Agent Profiles
description: "Profile definitions for subagent roles — model, provider, instructions, and toolset constraints per role."
created: 2026-06-13
updated: 2026-06-20
---

# Agent Profiles

각 프로필은 하나의 Markdown 파일로 정의됩니다. YAML frontmatter에 모델/프로바이더/도구세트를, 본문에 역할 지침(instructions)을 작성합니다.

## 사용 방식

**2계층 호출:**

```
# 같은 세션 (빠름) — 부모 모델 상속, profile의 프롬프트/권한만 적용
task(
    subagent_type="reviewer",
    description="Review PR changes",
    prompt="Review this PR for logic errors, edge cases, and style issues."
)

# 다른 모델 (정확) — profile의 모델로 새 세션 실행
delegate(
    name="implementer",
    prompt="Implement login validation. Files: src/auth/login.ts..."
)
# → ~/.config/opencode/tools/delegate.ts 커스텀 툴
# → opencode run --agent <name> --model <model> --attach :8642 실행
# → 프로필 고유 모델 적용됨 (kimi-k2.7-code, qwen3.7-plus 등)
```

## Cost Tier

| Tier | 모델 | 프로필 | 비용 |
|------|------|--------|------|
| **Flash** | deepseek-v4-flash, kimi-k2.7-code | explorer, implementer(kimi), archiver | OpenCode Go 구독에 포함 |
| **Pro** | deepseek-v4-pro, glm-5.2, minimax-m3 | reviewer, editor(glm), security-reviewer(minimax) | 구독 포함 |
| **Max** | qwen3.7-max, qwen3.7-plus | planner, orchestrator, reviewer-critical(plus) | 구독 포함 |

## Pipeline (Calling Convention)

- `task(subagent_type="...")` — 같은 모델일 때 (부모 모델 상속, 가볍고 빠름)
- `delegate(name="...", prompt="...")` — 다른 모델이 필요할 때 (프로필 모델 적용)

```
Tier 1 (단순, 전부 flash):
  task(implementer) → [optional: task(tester)] → task(archiver)

Tier 2 (보통, implementer는 kimi):
  task(explorer, flash)
  → delegate(implementer, kimi-k2.7-code) ↔ task(tester, flash) [≤2회 loop]
  → task(reviewer, pro) → task(archiver, flash)

Tier 3 (복잡, 3개 계열 모델):
  delegate(planner, qwen3.7-max)       # 계획 수립
  → task(explorer, flash)              # 분석
  → delegate(implementer, kimi-k2.7)   # 코드 생성 (kimi 특화)
  ↔ task(tester, flash) [≤3회 loop]
  → task(reviewer, pro)                # 일반 리뷰
  → delegate(security-reviewer, minimax-m3)     # 보안 감사 (다른 계열)
  → delegate(reviewer-critical, qwen3.7-plus)   # 최종 심층 리뷰 (최상급)
  → task(archiver, flash)              # 문서화

Content Pipeline:
  delegate(content-manager, pro) → delegate(editor, glm-5.2) → task(archiver)

Design Pipeline:
  task(explorer) [Lazyweb refs] → task(designer) → [delegate(implementer)]
  → task(reviewer) → task(archiver)

Incident Pipeline:
  task(sre) → [ESCALATE? → delegate(orchestrator, max)] → task(archiver)

Data Request:
  task(analyst) → [ESCALATE? → delegate(orchestrator, max)] → Report
```

## 프로필 목록

| 파일 | 역할 | 모델 | Pipeline 위치 |
|------|------|------|-------------|
| `explorer.md` | 탐색/분석 (읽기 전용) | flash (deepseek-v4) | 첫 단계 |
| `planner.md` | 태스크 분해/계획 | max (qwen3.7-max) | 복잡한 작업 첫 단계 |
| `orchestrator.md` | 작업 배정/파이프라인 관리 | max (qwen3.7-max) | 전체 pipeline 조정 |
| `designer.md` | UI/UX 디자인, 시각 자료 | flash (deepseek-v4) | 설계 단계 |
| `implementer.md` | 구현 — 코드 생성 특화 | flash (kimi-k2.7-code) | 구현 |
| `tester.md` | 테스트 작성/실행 | flash (deepseek-v4) | 구현 ↔ 테스트 loop |
| `reviewer.md` | 일반 코드 리뷰 | pro (deepseek-v4-pro) | 리뷰 단계 |
| `reviewer-critical.md` | 중요 변경 심층 리뷰 — 최상급 추론 | max (qwen3.7-plus) | 중요 변경 한정 |
| `security-reviewer.md` | 보안 감사 — 다른 계열 시각 | pro (minimax-m3) | 보안 관련 변경 한정 |
| `sre.md` | 인프라/배포/인시던트 대응 | flash (deepseek-v4) | 운영 |
| `analyst.md` | 데이터 분석/인사이트 | flash (deepseek-v4) | 분석 |
| `content-manager.md` | 콘텐츠 생성 (CMO) | pro (deepseek-v4-pro) | 콘텐츠 파이프라인 |
| `editor.md` | 콘텐츠 검수/한국어 인퓨전 | pro (glm-5.2) | 퍼블리시 전 최종 게이트 |
| `archiver.md` | 문서화/기록 | flash (deepseek-v4) | 마무리 |

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

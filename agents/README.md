---
title: Agent Profiles
description: "Profile definitions for subagent roles — model, provider, instructions, and toolset constraints per role."
created: 2026-06-13
updated: 2026-06-23
---

# Agent Profiles

Each profile is a single Markdown file. YAML frontmatter defines model/provider/toolset; the body contains role instructions.

## Usage

**Two invocation paths:**

```
# Same session (fast) — inherits parent model, applies profile prompt/permissions
task(
    subagent_type="reviewer",
    description="Review PR changes",
    prompt="Review this PR for logic errors, edge cases, and style issues."
)

# Different model / isolated execution — uses the profile's model in a fresh session
delegate(
    name="implementer",
    prompt="Implement login validation. Files: src/auth/login.ts..."
)
# → GJC Coordinator MCP (gjc_delegate_execute / gjc_delegate_team)
# → worktree isolation, tmux parallel execution
# → profile model is applied (kimi-k2.7-code, qwen3.7-max, etc.)
```

> **Note:** The legacy OmO delegate tool has been replaced by the GJC Coordinator MCP. Use `task()` for lightweight same-model work or `gjc_delegate_*` for isolated/parallel execution.

## Cost Tier

| Tier | 모델 | 프로필 | 비용 |
|------|------|--------|------|
| **Flash** | deepseek-v4-flash, kimi-k2.7-code | explorer, archiver, implementer(kimi) | OpenCode Go 구독에 포함 |
| **Pro** | deepseek-v4-pro | reviewer | 구독 포함 |
| **Max** | qwen3.7-max, qwen3.7-plus | planner, reviewer-critical(plus) | 구독 포함 |

## Pipeline (Calling Convention)

- `task(subagent_type="...")` — same model, fast in-session delegation
- `gjc_delegate_execute(goal="...", model="...")` / `gjc_delegate_team(goals=[...])` — isolated worktree/tmux execution with profile-specific models

```
Tier 1 (simple, all flash):
  task(implementer) → task(archiver)

Tier 2 (moderate, implementer uses kimi):
  task(explorer, flash)
  → delegate(implementer, kimi-k2.7-code) [test inside implementer]
  → task(reviewer, pro) → task(archiver, flash)

Tier 3 (complex, multi-tier models):
  delegate(planner, qwen3.7-max)         # planning
  → task(explorer, flash)                # analysis
  → delegate(implementer, kimi-k2.7)     # code generation
  → task(reviewer, pro)                  # general review
  → delegate(reviewer-critical, qwen3.7-plus)  # deep final review
  → task(archiver, flash)                # documentation

Content Pipeline:
  task(archiver, pro-level content work) → task(reviewer, editorial) → task(archiver)

Incident Pipeline:
  task(planner/SRE role) → [ESCALATE?] → task(archiver)
```

## Profile List (6 Active)

| 파일 | 역할 | 모델 | Pipeline 위치 |
|------|------|------|-------------|
| `explorer.md` | 탐색/분석/데이터 분석 (읽기 전용) | flash (deepseek-v4-flash) | 첫 단계 |
| `planner.md` | 태스크 분해/오케스트레이션/SRE 계획 | max (qwen3.7-max) | 복잡한 작업 첫 단계 |
| `implementer.md` | 구현 및 테스트 — 코드 생성 특화 | flash (kimi-k2.7-code) | 구현 |
| `reviewer.md` | 코드 및 콘텐츠 리뷰/편집 | pro (deepseek-v4-pro) | 리뷰/퍼블리시 전 게이트 |
| `reviewer-critical.md` | 중요 변경 심층 리뷰 + 보안 감사 | max (qwen3.7-max) | 중요/대규모/보안 변경 한정 |
| `archiver.md` | 문서화/기록/콘텐츠 큐레이션 | flash (deepseek-v4-flash) | 마무리 |

## Consolidation (v0.8)

v0.8 merged 14 profiles into 6. Removed profiles and their successors:

| 삭제된 프로필 | 병합 대상 | 이유 |
|--------------|----------|------|
| `analyst.md` | `explorer.md` | 데이터 분석 역할을 explorer에 통합 |
| `content-manager.md` | `archiver.md` | 콘텐츠 큐레이션/CMO 역할을 archiver에 통합 |
| `editor.md` | `reviewer.md` | 콘텐츠 검수/한국어 인퓨전을 reviewer에 통합 |
| `security-reviewer.md` | `reviewer-critical.md` | 보안 감사를 reviewer-critical에 통합 |
| `orchestrator.md` | `planner.md` | 파이프라인 오케스트레이션을 planner에 통합 |
| `sre.md` | `planner.md` | 인프라/인시던트 대응 계획을 planner에 통합 |
| `tester.md` | `implementer.md` | 테스트 작성/실행을 implementer에 통합 |
| `designer.md` | `skills/ui/designer/SKILL.md` | UI/UX 디자인 역할은 skill로 이관 |

Also removed:
- `agent-office.html` — personal artifact, not a profile
- `seo-engineer.md` — old unnecessary profile

## Escalation

Explorer, Implementer, and Planner can emit an `ESCALATE: <reason>` signal when a task exceeds their reasoning capability. The caller routes the task to a stronger model (e.g., planner → reviewer-critical, or human review).

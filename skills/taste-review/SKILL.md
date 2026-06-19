---
title: Taste Review
name: taste-review
type: document
space: concept
description: "Trend Harvester keep 리스트에서 고품질 툴을 1개 선정하여 심층 분석, taste 결정을 추출, vault에 기록"
tags: [taste, review, learning, growth]
trigger: "Taste Exposure Loop — Month 1 of '30x AI Engineer' 90-day plan"
provenance:
  session: "2026-06-14 taste-discussion"
  decision: "Trend Harvester keep 리스트 활용, 주 2회 심층 분석 루틴 — kanban delegation 패턴으로 cron timeout 회피"
created: 2026-06-14
updated: 2026-06-14
links:
  - "[[P3-sensors/skills/SKILL-INDEX]]"
  - "[[P0-brainstem/brain/rules]]"
  - "[[P3-sensors/skills/trend-harvester]]"
---

# Taste Review Skill

Trend Harvester가 수집+분석한 keep 리스트에서 1개를 골라 **심층 분석**하고,
그 툴에서 배울 수 있는 **taste 결정**을 추출하여 vault에 기록한다.

## Execution Model — Kanban Delegation

Taste Review는 **더 이상 직접 cron job에서 실행되지 않는다**. 다음 플로우로 동작:

```
cron: taste-review-trigger (fast LLM, 화/금 10:00)
  → kanban_create(title="taste-review: YYYY-MM-DD", assignee="default")
    → kanban worker (본 분석 실행)
```

- **Trigger cron** (`taste-review-trigger`, `66d907f7bce4`): 빠른 모델(`opencode-go/deepseek-v4-flash`)로 keep 리스트 확인 → 새 항목 있으면 kanban task 생성 → 종료 (수초)
- **Kanban worker**: 실제 분석 실행 (web_search + file write + LLM reasoning) — cron idle timeout(600s)과 무관

## Phase 1 — Pick & Research

### 항목 선택

1. `analyzed/keep/` 디렉토리에서 **아직 evaluated/에 없는** 항목 1개 선택
2. 이미 `applied/` 또는 `evaluated/`에 있는 항목은 스킵

### 웹 리서치

3. `web_search` 또는 직접 URL로 해당 툴의 README와 문서 탐색
4. 다음에 집중:
   - **아키텍처 결정**: 왜 이렇게 만들었을까? (언어, 패턴, 구조)
   - **사용자 경험 결정**: 어떤 trade-off를 했을까?
   - **독특한 접근법**: 다른 툴과 다른 점은?

## Phase 2 — Analyze & Write

### 분석 프레임워크

다섯 가지 질문에 답변:

1. **One-Liner**: 이 툴을 한 문장으로 설명하면?
2. **훔칠 Taste 결정 (1-3개)**: 이 툴의 제작자가 내린 결정 중, Drewgent에 적용할 가치가 있는 것은?
3. **아키텍처 인사이트**: 구조적으로 배울 점은?
4. **Drewgent 적용 가능성**: 이 아이디어를 Drewgent에 적용할 수 있는가? 어떻게?
5. **Leverage Score (1-5)**: 이 인사이트가 Drewgent에 미칠 영향은?

### Vault 저장

```
Path: P4-cortex/taste-reviews/YYYY-MM-DD-tool-slug.md
```

**Frontmatter:**
```yaml
---
title: "Taste Review: Tool Name"
type: taste-review
tags: [taste-review, YYYY-MM]
created: YYYY-MM-DD
links:
  - "[[trend-harvester]]"
  - "[[P4-cortex/growth/trend-harvester/analyzed/keep/xxxx.json]]"
  - "[[P0-brainstem/brain/rules]]"
provenance:
  session: "YYYY-MM-DD taste-review"
  trigger: "scheduled taste review"
---
```

**Body:**
```
# Taste Review: Tool Name

분석일: YYYY-MM-DD | 링크: [GitHub](url)

## One-Liner
...

## 훔칠 Taste 결정
### 1. [결정 제목]
- **무슨 결정인가:** ...
- **왜 taste가 필요한 결정인가:** ...
- **Drewgent에 적용:** ...

### 2. ...

## 아키텍처 인사이트
...

## Drewgent 적용 가능성
[Yes/No + 구체적 방법]

## Leverage Score: N/5
```

## Phase 3 — Deliver & Sync

### Discord 메시지 포맷 (growth 채널)

```
🔍 **Taste Review: [Tool Name]**

[One-Liner]

**훔칠 Taste 결정**
1. [결정] — [간단히]
...

**Leverage Score: N/5**
[1-2 sentence why]

자세한 분석: vault P4-cortex/taste-reviews/YYYY-MM-DD-tool-slug.md
```

### 항목 이동

분석 완료 후, 해당 keep JSON 파일을 `evaluated/`로 복사 (평가 완료 마킹):

```
cp keep/xxxx.json ../../evaluated/YYYY-MM-DD-taste-{name}.json
```

(`applied/` 이동은 추후 evaluation pipeline에서 별도 처리. Taste Review는 "분석"만 하고
"적용 결정"은 standard evaluation pipeline에 맡긴다.)

## 주의사항

- **너무 길게 분석하지 말 것.** 핵심 taste 결정 1-3개에 집중.
- GitHub README만 보고 판단하지 말 것. 가능하면 아키텍처 문서, 블로그 포스트, 이슈까지 확인.
- "이미 알고 있는 내용"을 반복하지 말 것. **새로운 인사이트**에 집중.
- 분석 결과는 **반드시 한국어**로 작성 (사용자 언어).
- 모든 keep 항목이 이미 `evaluated/`에 있으면 완료 메시지 출력 후 종료.
- **Taste Review는 추천 단계** — 실제 적용은 evaluation pipeline에서 판단.

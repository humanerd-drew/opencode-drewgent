---
title: Manyfast — Product Planning Architecture Study
type: document
space: concept
tags: [concept]
created: 2026-05-21
updated: 2026-05-20
links:
  - "[[@memory/kanban/KANBAN_INDEX]]"
  - "[[@action/skills/SKILL-INDEX]]"
  - "[[@memory/growth/INTEGRATION_PROTOCOL]]"
  - "[[@memory/knowledge/prd-template]]"
  - "[[memories/concepts/prd-schema]]"
  - "[[@identity/brain/rules]]"---


# Manyfast 아키텍처 분석 — Drewgent 내재화

## Manyfast 핵심 분석

Manyfast는 **제품 기획 협업 SaaS**. 아래 구조를 가진다:

### 1. PRD 구성 (프로덕트 요구사항)

```
PRD
├── 개요        — 제품 목표, 비즈니스 배경 (한 줄 정의)
├── 핵심 가치    — 문제 정의 + 해결 방식 + 차별점
├── 타겟/시나리오 — 사용자 그룹 + 사용 스토리
├── 성공 지표    — KPI + 리스크 + 오픈 이슈
└── 속성 설정   — 카테고리, 사용자 역할, 서비스 환경
```

**Drewgent 적용 시**: `memories/concepts/` 또는 `P4-cortex/knowledge/`에 PRD 스키마 정의. Drewgent kanban task의 metadata로 PRD 필드 표현 가능.

### 2. Features 3-tier Hierarchy (핵심)

```
Requirement (요구사항)
├── Feature (기능)
│   ├── Specification (상세 기능)
│   └── Specification
├── Feature
│   └── Specification
└── Feature
    └── Specification
```

**각 단계 속성**:
| 단계 | 설명 | 속성 |
|------|------|------|
| Requirement | 프로젝트 최상위 목표 | 설명 + Acceptance Criteria(체크리스트) |
| Feature | 논리적 기능 단위 | 설명 + 사용자 역할(PRD 역할 매핑) |
| Specification | 세부 동작/비즈니스 정책 | 설명 (개발/디자인 기준) |

**중요도**: 낮음/중간/높음
**상태**: 시작 전/진행중/완료/중단

**Drewgent 적용 시** — Drewgent kanban task tree로 동일 구조 구현:
```
parent task (Requirement)
  child task (Feature)
    grandchild task (Specification)
```
- `metadata["requirement"]` → parent task title
- `metadata["feature"]` → child task title
- `metadata["specification"]` → grandchild task title
- `metadata["acceptance_criteria"]` → QA gate criteria로 연동

### 3. AI 에이전트 Dual-Mode

Manyfast AI는 두 가지 모드:

```
설계 모드 (Design Mode)
  — AI와 함께 계획을 구체화, 합의점 먼저 찾음
  — 빠른 실행 대신 탐색/토의에 집중

실행 모드 (Execution Mode)
  — 지시 즉시 실행, 기획 도구로 데이터 직접 수정
  — 빠른 결과물 생성
```

**Drewgent 적용 시**:
- Drewgent kanban에 `design_mode` 플래그 추가
- design mode: task를 분해만 하고 실행은 보류
- execution mode: task 분해 후 바로 kanban-dispatcher로 실행 전달
- `kanban_create(mode="design"|"execution")` 파라미터로 구분

### 4. AI 수정 검토 workflow (핵심 패턴)

```
AI가 수정 제안
    ↓
사용자가 검토 (파란 화살표로 표시)
    ↓
개별 승인/거절 또는 일괄 승인/거절
    ↓
최종 반영
```

**Drewgent 적용 시** — Drewgent의 QA gate와 유사:
- Agent가 task 결과를 제안
- QA gate에서 `all_criteria_met` 확인
- 사용자가 승인/거절 (Telegram/Discord reaction 또는明确的承認)

### 5. MCP Integration (외부 AI 연동)

Manyfast MCP는:
```
매니패스트 기획 데이터 → AI coding agent (Cursor, Claude Code 등)
                      → 코딩 결과 → 매니패스트에 반영
```

**Drewgent의 현재 상태**:
- Drewgent kanban이 자체 task queue를 관리
- MCP client (`tools/mcp_tool.py`)로 외부 MCP 서버에 연결 가능
- Manyfast MCP 대신 **직접 구현**이 목표

### 6. 실시간 동기화 + Credit 추적

- Manyfast: 프로젝트 변동사항 → 연결된 AI agent에 실시간 전파
- AI Credit: Claude(10-50 credit/대화), Gemini(5-10 credit/대화)

**Drewgent 적용 시**:
- Drewgent kanban event → Discord/Telegram notification (이미 구현됨)
- kanban task 완료 → Manyfast에 웹훅으로 피드백 (선택적)

---

## Drewgent 내재화 — 구현 해야 할 것

### Phase 1: PRD Structure in Drewgent

```
memories/concepts/prd-schema.md
P4-cortex/knowledge/prd-template.md
```

**PRD metadata in kanban task**:
```json
{
  "title": "[프로젝트] 회원 관리",
  "board": "content",
  "metadata": {
    "type": "requirement",
    "project_goal": "한 줄 정의",
    "core_value": "문제 + 해결 + 차별점",
    "target_users": "사용자 그룹",
    "success_kpi": "KPI",
    "acceptance_criteria": ["기준1", "기준2"]
  }
}
```

### Phase 2: 3-tier Task Decomposition

Drewgent kanban-orchestrator skill이 이미 parent-child link를 지원:
- Requirement → parent task
- Feature → child task  
- Specification → grandchild task

**task title 규칙**:
```
[{project}] {requirement}
[{project}] {requirement}/{feature}
[{project}] {requirement}/{feature}/{specification}
```

### Phase 3: Design/Execution Mode Split

```
kanban_create(..., mode="design")
  → task status='todo', metadata["mode"]="design"
  → AI가 분해만 하고 대기

kanban_create(..., mode="execution")  
  → task status='in_progress'
  → kanban-dispatcher가 즉시 실행
```

### Phase 4: AI Review Workflow

Manyfast의 "AI 수정 → 사용자 승인" 패턴을 Drewgent에 구현:

```
Agent가 작업 결과 제안
    ↓
QA gate 검증 (contract.json criteria check)
    ↓
사용자에게 승인 요청 (Discord/Telegram message)
    ↓
✅ 승인 → task_complete()
❌ 거절 → task_block() + 수정 요청
```

---

## Manyfast Docs Query (Drewgent 자체적으로 가능)

Manyfast docs는 `?ask=` 쿼리 파라미터로 RAG처럼 동작:
```
GET https://docs.manyfast.io/{page}.md?ask={question}
```

Drewgent는 자체 `memories/concepts/` + `P4-cortex/knowledge/`를 검색 인프라로 활용.
외부 문서 대신 **자기 vault 안에서** 같은 패턴 구현.

---

## Manyfast 아키텍처 핵심 인사이트

### 1. Tree View ↔ Directory View 분리

Manyfast는 같은 데이터를 두 가지 뷰로 제공:
- **Tree View**: 전체 구조一目了然
- **Directory View**: 세부 내용 편집

**Drewgent 적용**: Drewgent kanban HTML dashboard가 이미 비슷함. 추가로:
- Tree view: kanban 전체 dependency graph
- Detail view: 특정 task의 metadata 편집

### 2. AI First Editing

모든 편집에 AI 제안 + approve/reject 흐름:
- 텍스트 선택 → AI 수정 요청 → 검토 → 승인/거절
- 문서 전체 → AI 최적화 요청 → 검토 → 승인/거절

**Drewgent 적용**: Drewgent의 QA gate가 이미 similar. `contract.json` criteria를 AI가 제안하고 사용자가 승인하는 구조로 발전 가능.

### 3. 역할 기반 Access

PRD에서 정의한 역할을 Features에 매핑:
- 역할: 관리자, 고객, 기획자
- Feature마다 수행 주체(역할) 지정

**Drewgent 적용**: kanban task의 `assignee`를 역할 단위로 관리:
- `assignee="admin"`, `assignee="customer"`, `assignee="planner"`
- kanban-dispatcher가 역할 기반으로 worker 배정

### 4. Credit-based AI Usage

AI 사용량 추적:
- 모델별 credit 소모량 상이
- 작업 복잡도에 따라 credit 차등 부과

**Drewgent 적용**: Drewgent가 사용하는 AI provider별 cost tracking:
- Anthropic API: cost per token 추적
- OpenAI API: cost per token 추적
- kanban task 완료 시 cost 기록 (`task_runs.cost`)

---

## 정리: Manyfast의 것을 Drewgent에 내재화

| Manyfast 기능 | Drewgent 구현 | 상태 |
|---------------|--------------|------|
| PRD structure | memories/concepts/prd-schema.md | TODO |
| 3-tier Features | kanban task tree (parent-child) | ✅ Done |
| AI Design/Execution mode | kanban_create(mode=) | TODO |
| AI Review workflow | QA gate + user approval | ✅ Done |
| MCP integration | Drewgent MCP client | ✅ Done |
| Tree/Directory view | kanban HTML dashboard | ✅ Done |
| Credit tracking | task_runs cost tracking | TODO |
| Real-time sync | Discord/Telegram webhook | ✅ Done |

---

## Files to Create

```
~/.drewgent/memories/concepts/prd-schema.md      — PRD 스키마 정의
~/.drewgent/P4-cortex/knowledge/prd-template.md — PRD 작성 템플릿
~/.drewgent/P4-cortex/growth/manyfast-study.md  — 이 문서 (아키텍처 분석 결과)
---

## Files Created

| File | Description |
|------|-------------|
| `memories/concepts/prd-schema.md` | PRD 스키마 정의 |
| `P4-cortex/knowledge/prd-template.md` | PRD 작성 템플릿 |
| `P4-cortex/growth/manyfast-study.md` | Manyfast 아키텍처 분석 문서 |

## Related

- Manyfast Docs: https://docs.manyfast.io
- PRD: https://docs.manyfast.io/plan/prd.md
- Features: https://docs.manyfast.io/plan/features.md
- Drewgent kanban: [[@memory/kanban/KANBAN_INDEX]]
- PRD Schema: [[memories/concepts/prd-schema]]
- PRD Template: [[@memory/knowledge/prd-template]]

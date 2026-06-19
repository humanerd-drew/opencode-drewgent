---
title: "Parent Context Injection — pipeline 단계 간 맥락 자동 전달"
type: proposal
status: implemented
created: 2026-06-19
implemented: 2026-06-19
tier: 3
tags: [kanban, pipeline, context, handoff]
leverage_score: 4
---

# Parent Context Injection

## Problem

`kanban_create(pipeline=["explorer","implementer","tester"])`로 자동 분해된 파이프라인에서, **각 단계는 이전 단계의 출력을 알지 못한 채 시작한다.**

`parents=[t1]`은 순서 제어만 할 뿐, t1의 `kanban_complete(result=...)`가 t2의 context에 포함되지 않는다.

## Solution

Worker-side structured handoff resolution. Worker가 시작 시 부모의 `tasks.result`를 읽어 JSON 파싱 → `findings`/`risks`/`next`를 markdown으로 변환 → 현재 prompt 앞에 주입.

### Schema (3 fields)

```python
kanban_complete(
    task_id="t_xxx",
    summary="Human-readable completion report",
    result=json.dumps({
        "findings": ["What was discovered or produced"],
        "risks": ["Concerns for next stage"],
        "next": ["Recommended next actions"],
    }),
)
```

## Implementation

### `run_kanban_worker.py` — `_resolve_parent_context()`

Worker-side assembly. Reads `task_links` → parent `tasks.result` → JSON parse → structured markdown.

```python
def _resolve_parent_context(task_id: str) -> str:
    parents = conn.execute(
        """SELECT p.id, p.title, p.result, p.skills
        FROM task_links tl JOIN tasks p ON p.id = tl.parent_id
        WHERE tl.child_id = ? ORDER BY p.completed_at""",
        (task_id,),
    ).fetchall()

    for pid, title, result, skills in parents:
        try:
            data = json.loads(result)
            # parse findings/risks/next → markdown
        except (json.JSONDecodeError, TypeError):
            # log warning + task_events record + visual indicator in context
```

Key behaviors:
- `result`가 valid JSON with dict → sections별 markdown 분할
- dict가 아니거나 JSON parse 실패 → fallback. stdout 경고 + `handoff_failed` event 기록 + context에 `⚠` 표시
- `skills`를 event payload에 저장 → profile별 실패 집계 가능
- `result`가 없거나 빈 값 → skip

### Agent Profiles — Handoff Contract

10개 profile에 `## Handoff Contract` 섹션 추가:

| Profile | findings | risks | next |
|---------|----------|-------|------|
| explorer | Discoveries with file paths | Concerns for implementer | Recommended actions |
| implementer | What was implemented, files changed | Known issues, edge cases | Tester focus areas |
| tester | Test results, bugs found | Flaky tests, untested paths | Reviewer attention points |
| planner | Key findings, plan rationale | Complexity concerns | Execution order |
| reviewer | Issues with severity/path | Blocking issues | APPROVE/CHANGES_REQUESTED |
| reviewer-critical | Architecture concerns | Migration risks | Recommended changes |
| security-reviewer | Vulnerabilities (CWE, path) | CRITICAL/HIGH issues | Required fixes |
| archiver | Docs produced, files updated | Coverage gaps | Future doc needs |
| designer | Design decisions, assets | Usability concerns | Dev handoff details |
| editor | Edits made, quality assessment | Remaining concerns | ACCEPT/REJECT verdict |
| content-manager | Content produced, arc update | Timing/quality concerns | Editor focus areas |

### Failure Handling

JSON parsing 실패 시 3-layer 대응:

| Layer | Action | 식별 방법 |
|-------|--------|-----------|
| **Log** | `[handoff] WARN parent t_xxx: result is not valid JSON (len=N, preview="...")` | worker stdout |
| **Event** | `kind="handoff_failed"` + payload `{child_id, preview, skills}` | `kanban_get_events(parent)` |
| **Context** | `⚠ Handoff format not recognized — raw output below` | agent가 받는 prompt에 표시 |

## Files Changed

| File | Change | Lines |
|------|--------|-------|
| `scripts/run_kanban_worker.py` | `_resolve_parent_context()` 추가 + `run_worker()` 호출 | +55 |
| `agents/explorer.md` | Handoff Contract 섹션 | +9 |
| `agents/implementer.md` | Handoff Contract 섹션 | +9 |
| `agents/tester.md` | Handoff Contract 섹션 | +9 |
| `agents/planner.md` | Handoff Contract 섹션 | +9 |
| `agents/reviewer.md` | Handoff Contract 섹션 | +9 |
| `agents/reviewer-critical.md` | Handoff Contract 섹션 | +9 |
| `agents/security-reviewer.md` | Handoff Contract 섹션 | +9 |
| `agents/archiver.md` | Handoff Contract 섹션 | +9 |
| `agents/designer.md` | Handoff Contract 섹션 | +9 |
| `agents/editor.md` | Handoff Contract 섹션 | +9 |
| `agents/content-manager.md` | Handoff Contract in step 6 | +7 |
| `P6-prefrontal/proposals/...` | 문서 업데이트 | — |

## Design Decisions

| 결정 | 선택 | 이유 |
|------|------|-------|
| Handoff 저장 위치 | `tasks.result` (JSON) | 이미 존재하는 필드. 새 스키마 불필요 |
| Transport 시점 | Worker-side (runtime) | Idempotent. Promotion-time은 중복 위험 |
| Handoff depth | 1 level (direct parents only) | 부모가 필요한 조상 맥락을 forward |
| Schema 강제 | Soft (JSON 실패 → log + event + context 표시) | 장애 투명하지 않게 넘기지 않음 |
| 실패 시 동작 | 조용히 넘기지 않음 | stdout 경고 + DB event + agent prompt에 표시 |
| Field 개수 | 3개 (findings, risks, next) | 최소. `files_touched` 등은 noise |
| Profile 추적 | `skills`를 event payload에 포함 | profile별 패턴 발견 가능 |
| `summary` 역할 | Human-readable 완료 보고 | `result`와 책임 분리 |

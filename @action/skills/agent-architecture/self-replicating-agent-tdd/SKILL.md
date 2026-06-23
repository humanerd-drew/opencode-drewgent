---
name: self-replicating-agent-tdd
description: TDD-PDCA plan for building a self-replicating branching agent in Drewgent. 단일 에이전트가 스스로 서브에이전트를 분기하고, 결과를 수렴시키는 구조.
triggers:
  - "자가 증식 에이전트"
  - "branching agent"
  - "self-replicating"
  - "subagent autonomous branching"
space: outcome
type: document
tags: [architecture, branching, self-replicating, tdd, pdca]
links:
  - "[[@action/skills/agent-architecture/DESCRIPTION]]"
  - "[[@action/skills/SKILL-INDEX]]"
created: 2026-05-10
---

# TDD-PDCA: Self-Replicating Branching Agent for Drewgent

## Goal
Drewgent (단일 에이전트)이 복잡한 문제를 감지 → 스스로 서브에이전트를 분기 (branch) → 병렬 추론 → 결과를 부모가 수렴 → 최종 응답 형성.

---

## 현재 상태 (Baseline) — Updated 2026-05-10

Phase 1 (COMPLETE): SelfBranchDecider class with 17 passing tests.
Phase 2 (COMPLETE): Integrated into run_agent.py loop.
Phase 3 (COMPLETE): Structural bugs fixed + integration tests written. 23 tests passing.

### PDCA Progress

| Phase | Goal | Status |
|---|---|---|
| Phase 1 | score_complexity + should_branch + plan_branches + integrate_results | COMPLETE |
| Phase 2 | Hook into run_agent.py _execute_tool_calls_concurrent at api_call_count==1 | COMPLETE |
| Phase 3 | Fix structural bugs (tool_name, _already_branching, decider caching) + integration tests | COMPLETE |
| Phase 4 | End-to-end test + CLI indicator + child agent propagation | COMPLETE |

### Phase 3 — Bug Fixes (COMPLETE)

| # | Bug | Location | Fix |
|---|---|---|---|
| 1 | `tool_name` missing from tool result messages (sequential) | `run_agent.py:7719` | Added `tool_name` to `tool_msg` dict |
| 2 | `tool_name` missing from concurrent path interrupt skip | `run_agent.py:7003` | Added `tool_name` to interrupt skip_msg |
| 3 | `_already_branching` check-only (never set) | `run_agent.py:7289` | Added `self._already_branching = True` before execute |
| 4 | `SelfBranchDecider` recreated every call | `run_agent.py:7839` | Cached as `self._branch_decider` |
| 5 | `original_user_message` not passed in concurrent path | `run_agent.py:6877` | Added to `_execute_tool_calls()` signature and all call sites |

### Phase 4 — Integration (COMPLETE)

| # | Item | Location |
|---|---|---|
| A | CLI visual indicator on branching | `run_agent.py:7291-7293` — `⚡ Self-branch triggered` message |
| B | `_already_branching` propagates to child agents | `delegate_tool.py:322` — `child._already_branching = getattr(parent_agent, '_already_branching', False)` |

**Integration Tests (9 in `TestSelfBranchIntegration`):**
- `test_execute_tool_calls_sets_tool_name_in_result_messages` — sequential path tool_msg includes tool_name
- `test_should_self_branch_false_on_no_conjunction` — conjunction gate blocks simple messages
- `test_should_self_branch_false_on_simple_message` — no conjunction → no branch
- `test_should_self_branch_true_with_conjunction_and_complex_messages` — passes when both conditions met
- `test_should_self_branch_false_when_already_branching` — `_already_branching` flag blocks re-entry
- `test_should_self_branch_false_on_child_agent` — `_delegate_depth > 0` blocks branching in children
- `test_execute_self_branch_calls_decider_execute_branching` — cached decider receives correct args
- `test_decider_cached_on_agent_instance` — conjunction pass → cache set
- `test_branch_response_returned_with_branched_flag` — branching result string returned

**Test Results**: 236 passed, 7 failed (pre-existing, all Azure/max_tokens related)

### Phase 1 — Test Results (17 PASS)
- test_score_returns_float_between_0_and_1
- test_simple_question_low_score
- test_complex_debugging_high_score
- test_tool_diversity_increases_score
- test_should_branch_fires_on_complex_task
- test_should_branch_false_on_simple_task
- test_child_agent_never_branches
- test_double_branch_prevented
- test_debug_score_shows_breakdown
- test_plan_branches_returns_list
- test_plan_branches_single_task
- test_plan_branches_max_concurrent
- test_plan_branches_includes_context
- test_integrate_results_returns_string
- test_integrate_results_contains_summaries
- test_integrate_results_failed_branch_warning
- test_integrate_results_all_failed_returns_error

### Phase 2 — Changes to run_agent.py

1. `_execute_tool_calls_concurrent()` signature: added `original_user_message=""` parameter
2. Self-branch check after tool execution (line ~7276): `if api_call_count == 1 and self._should_self_branch(messages, original_user_message)`
3. New methods on AIAgent (line ~7796): `_should_self_branch()`, `_execute_self_branch()`

### Key Design Decisions

**Conjunction Gate**: Only branch when goal contains natural conjunction (" and ", " and also ", " + ", "그리고", " 또한 ", "且", "並且", "同时"). Prevents branching on every complex single task.

**Complexity Score Components (0.0 to 1.0)**:
| Component | Weight | Notes |
|---|---|---|
| tool_diversity | 0.30 | unique tools / total calls |
| tool_call_count | 0.30 | calls / 15 |
| turn_count | 0.20 | assistant turns / 8 |
| reasoning_ratio | 0.10 | thinking blocks present |
| context_compression | 0.10 | bonus if > 30 messages |

Threshold: 0.30

**Tool Name Extraction — CRITICAL FIX**: Must extract from BOTH `assistant.tool_calls[].function.name` (OpenAI format) AND `tool` role messages with `tool_name` field (Drewgent format).

**Trigger**: api_call_count == 1 — after FIRST tool-call turn completes.

### Pitfalls Found and Fixed

1. tool_names NOT extracted from tool role messages (Drewgent uses `{"role": "tool", "tool_name": "..."}`)
2. COMPLEXITY_THRESHOLD was 0.45 — complex debugging only scored 0.36. Lowered to 0.30.
3. Duplicate function definition left by patch tool — removed stale first def.
4. original_user_message not available in concurrent execution path — added as parameter.

### Files Created/Modified

- CREATED: `agent/self_brancher.py` — SelfBranchDecider class
- CREATED: `tests/agent/test_self_brancher.py` — 17 tests
- MODIFIED: `run_agent.py` — integration hooks + new methods

### 이미 존재하는 것
- `delegate_task` (tools/delegate_tool.py) — 병렬 서브에이전트 spawn (MAX_CONCURRENT=3, MAX_DEPTH=2)
- `_active_children` interrupt 전파 (run_agent.py)
- `MemoryManager.on_delegation()` — 자식 완료 후 메모리 동기화 hook
- `SessionDB` parent_session_id 체인 추적
- `ContextCompressor` — iterative summarization
- `_budget_caution_threshold=0.7`, `_budget_warning_threshold=0.9` — pressure injection
- `smart_model_routing` — cheap/strong model routing
- `credential_pool` — same-provider credential sharing

### 부족한 것 (Gap Analysis)
1. **Branching trigger** — 복잡한 문제 감지 → 모델이 명시적으로 delegate_task 호출해야 분기 (자율적 아님)
2. **Shared context** — 자식들 `skip_memory=True`, 고립된 메모리, 결과는 `summary` 문자열만 반환
3. **Streaming aggregation** — 자식 완료까지 부모 블로킹, 실시간 수렴 없음
4. **Recursive branching** — MAX_DEPTH=2 제한, 자식은 delegate_task 사용 불가

---

## 논리적 진행 순서 (의존성 기반)

### Phase 1: T+D — 복잡도 감지 +自愿적 Branching
**왜 이것부터?** Branching decision이 없으면 뒤의 모든 단계가 무의미.

| Step | 내용 |
|---|---|
| **T (Test)** | "복잡한 문제"를 정량화 — iteration count, tool diversity score, reasoning token ratio, message depth |
| **T (Test)** | Branching trigger 조건 정의 — threshold 조합 테스트 |
| **D (Driver)** | AIAgent에 complexity scorer組み込み — `_should_branch()` method |
| **D (Driver)** | Branching decision을 autonomous하게 내리는 시스템 — 모델 요청이 아니라 에이전트 자체 판단 |
| **C (Check)** | 실제 복잡한 문제에서 branching이 트리거되는지 검증 |

### Phase 2: D+C — Shared Brain + Branch Exec
**왜 이것부터?** Branch 결과를 공유하지 못하면 병렬 분기의 가치가 떨어짐.

| Step | 내용 |
|---|---|
| **D (Driver)** | Wiki-based shared brain 활용 — 자식들이 중간 결과를 wiki에 write, 부모가 read |
| **D (Driver)** | Branch별 결과 aggregation 메서드 — parent가 wiki에서 branch 결과 수집 |
| **C (Check)** | 자식 완료 후 wiki에 기록되는 결과의 정확성 검증 |
| **A (Adjust)** | Wiki write batching 빈도 조정, aggregation 로직 튜닝 |

### Phase 3: Bug Fix + Integration (2026-05-10)

**Bug Fixes:**

1. **`tool_name` missing from run_agent.py tool result messages** (line ~7249)
   - SelfBranchDecider extracts tool names from `{"role": "tool", "tool_name": "..."}` messages
   - run_agent.py was only setting `role`, `content`, `tool_call_id` — not `tool_name`
   - Fixed: added `"tool_name": name` to the tool result message dict

2. **`_already_branching` flag never set** (line ~7284)
   - Phase 2 checked the flag but never set it → double-branch guard was no-op
   - Fixed: set `self._already_branching = True` before calling `_execute_self_branch()`
   - Unset it if branching fails so normal flow continues

3. **`SelfBranchDecider recreated each call** (lines ~7817–7829)
   - `_should_self_branch()` created fresh `SelfBranchDecider()` on every call
   - Reset `_branching_happened = False` each time → double-branch guard broken
   - Fixed: cache as `self._branch_decider`, reuse across calls

**Integration Tests Added** (`tests/agent/test_self_brancher.py` — `TestSelfBranchIntegration`):
- 6 new tests: tool_name field, already_branching guard, decider caching, execute_branching flag, conjunction gate, child depth guard
- All 23 tests passing (17 original + 6 new)

**Key Behavioral Insights (from tests):**
- `should_branch()` does NOT set `_branching_happened` — only `execute_branching()` does
- Repeated `should_branch()` calls without `execute_branching()` keep returning True
- Real double-branch protection: (1) AIAgent `_already_branching` flag, (2) `_delegate_depth > 0`
- `SelfBranchDecider.should_branch()` is agnostic to `_already_branching` — that check lives in AIAgent layer above it

**Phase 4 — TODO:**
- End-to-end test: trigger self-branch in actual run_agent loop
- Visual indicator in CLI when branching occurs
- `_already_branching` should propagate to child agents via delegate_task context

---

## Phase 1 상세 설계

### T (Test) — 복잡도 측정 기준

```python
# complexity_score 계산 요소
- tool_call_count: 10회 이상 → +1
- unique_tool_types: 4가지 이상 → +1  
- reasoning_tokens / total_tokens: 0.3 이상 → +1
- message_turn_count: 8회 이상 → +1
- nested_delegate (subagent 호출): +2
- context compression 발생: +1

threshold: score >= 3 → branching 고려
```

### D (Driver) — 구현 위치

**파일:** `agent/self_brancher.py` (신규)

```python
class SelfBranchDecider:
    """Parent agent가 autonomous하게 branch를 결정하게 하는 모듈."""
    
    def __init__(self, agent):
        self.agent = agent
    
    def score_complexity(self, messages) -> float:
        """0.0~1.0 complexity score."""
    
    def should_branch(self, messages) -> bool:
        """score > threshold AND not already branching."""
    
    def plan_branches(self, goal: str, context: str) -> list[BranchTask]:
        """goal을 branch로 분할."""
    
    def integrate_results(self, branch_results: list) -> str:
        """branch 결과들을 통합."""
```

### C (Check) — 검증 방법

```bash
# 테스트 시나리오
# 1. 복잡한 디버깅 문제 → branch 발생 확인
# 2. 단순한 질문 → branch 없음 확인  
# 3. branch 후 wiki에 결과 기록 확인
# 4. parent가 결과를 수렴해서 최종 응답 형성 확인
```

---

## 기술적 고려사항

### Branching Trigger Mechanism
현재: 모델이 `delegate_task` tool을 명시적으로 호출해야 함
→ 원하는: iteration pressure, complexity score 등 내부 신호로 에이전트가 스스로 분기

**구현 옵션:**
1. `_should_branch()` hook을 agent loop에組み込み — 매 turn마다 complexity check
2. Budget pressure가 70% 도달하면 → autonomous branching suggestion을 system prompt에 injection
3. Model이 `delegate_task` 호출하도록 유도하는 system prompt 전략

### Shared Brain Implementation
**옵션 A: Wiki (Obsidian) — 기존 infrastructure 활용**
- 자식들: `brain_record` tool로 wiki에 write
- 부모: `brain_query`로 wiki에서 branch 결과 read
-优点: 이미 구현되어 있음, persistent
- 단점: 비동기, 실시간 아님

**옵션 B: In-memory shared state (새로 구현)**
- Shared dict/channel for real-time progress
-优点: 실시간, low latency
- 단点: 상태 유실 위험

### Streaming Result Channel
`delegate_task`의 현재 limitation: 자식이 완료될 때까지 부모 block

**개선 방향:**
1. `tool_progress_callback` 활용 — 자식이 중간 결과를 parent에게 push
2. ThreadPoolExecutor에서 future.result() 대신 polling 방식으로 변경
3. Parent가 branch 결과를 실시간으로 소비하며 aggregator에게 전달

---

## 의존성 정리

```
Phase 1 (T+D) ← 가장 먼저: branching decision 없으면 의미 없음
    ↓
Phase 2 (D+C) ← Phase 1 완료 후: branch 결과를 공유해야 수렴 가능
    ↓
Phase 3 (C+A) ← 마지막: 실시간 streaming + autonomous refinement
```

---

## 각 Phase별验收 기준 (Definition of Done)

### Phase 1 Done
- [ ] 복잡도 score가 0.0~1.0로 정확히 계산됨
- [ ] threshold 초과 시 autonomous branching 발생
- [ ] branching 안 한 단순 질문에는 branch 없음
- [ ] branch 결과가 summary로 부모에게 반환됨

### Phase 2 Done
- [ ] 자식들이 wiki에 중간 결과를 write
- [ ] 부모가 branch 완료 후 wiki에서 결과 수집
- [ ] aggregation이 정확함 (정보 손실 없음)
- [ ] wiki write overhead가 performance에 미치는 영향 측정

### Phase 3 Done
- [ ] 자식들이 완료 전에 중간 결과를 부모에게 push
- [ ] 부모가 실시간으로 branch 진척상황 모니터링
- [ ] further branching decision이 autonomous하게 발생
- [ ] recursive branching이 안정적으로 작동 (MAX_DEPTH 정책 재정립)

## Related
- [[@action/skills/SKILL-INDEX]]
- [[@action/skills/agent-architecture/DESCRIPTION]]

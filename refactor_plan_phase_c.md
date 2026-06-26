---

title: Refactor Plan Phase C
type: plan
space: concept
tags: [concept]
created: 2026-05-20
updated: 2026-05-20
links: []
links:
  - "[[@action/plans/growth-2026]]"
---


# Phase C 작업 계획서 — `run_conversation()` 분해

## ⚠️ 고위험 단계 — Phase A+B 완료 + 테스트 전체 통과 후 진행

```bash
cd /Users/drew/.drewgent/source/drewgent-agent
source .venv/bin/activate
git checkout -b refactor/phase-c-loop-decomposition
python -m pytest tests/test_run_agent.py tests/test_streaming.py -n0 -q --tb=short 2>&1 | tee /tmp/phase_c_baseline.txt
```

---

## 핵심 설계: `TurnState` dataclass

`run_conversation` 루프 안의 공유 지역변수들을 하나의 객체로 묶음.
이것 없이는 수많은 상태 변수들(`api_call_count`, `interrupted`, `final_response` 등)을 여러 헬퍼 메서드로 전달하고 업데이트하기 매우 어려움.

### 새 파일: `agent/turn_state.py`

```python
"""Per-turn mutable state shared across run_conversation sub-methods."""
from dataclasses import dataclass, field
from typing import Any, Optional

@dataclass
class TurnState:
    api_call_count: int = 0
    tool_call_count: int = 0
    interrupted: bool = False
    final_response: Optional[str] = None
    final_reasoning: Optional[str] = None
    messages: list = field(default_factory=list)
    # budget pressure
    pressure_injected: bool = False
    # streaming
    last_stream_chunk: Any = None
    # empty response retry
    empty_response_retries: int = 0
    # tool results for current turn
    current_tool_results: list = field(default_factory=list)
```

---

## Task C-1: `TurnState` 도입 + `_preflight_turn` 추출

### 대상
`run_conversation` 초반부:
- `user_message` surrogate sanitize
- `IterationBudget` 체크 및 refund 준비
- `TurnState` 초기화
- `messages` 배열 생성 (기존 history 복사 포함)

### 시그니처
```python
def _preflight_turn(self, user_message: str, conversation_history: list) -> TurnState:
    """Initialize state for a new conversation turn."""
```

### 검증
```bash
python -m pytest tests/test_surrogate_sanitization.py tests/test_run_agent.py -k "budget" -n0 -v --tb=short
git commit -am "refactor: introduce TurnState + extract _preflight_turn"
```

---

## Task C-2: `_build_turn_messages` 추출

### 대상
API 호출 직전 메시지 구성 로직:
- `_build_system_prompt()` 호출 및 메시지 리스트 삽입
- 컨텍스트 파일(`context_files`) 추가
- Brain decision hint 주입
- Integration workflow progress hint 주입

### 시그니처
```python
def _build_turn_messages(self, state: TurnState, user_message: str) -> None:
    """Build full message list including system prompt and dynamic hints."""
```
*(수정된 `messages`는 `state.messages`에 저장됨)*

### 검증
```bash
python -m pytest tests/test_run_agent.py -k "system_prompt" -n0 -v --tb=short
git commit -am "refactor: extract _build_turn_messages"
```

---

## Task C-3: `_execute_api_call` 추출

### 대상
메인 while 루프 내부의 모델 호출부 (~500줄):
- 스트리밍 / 비스트리밍 분기
- `_interruptible_streaming_api_call` / `_interruptible_api_call`
- 빈 응답 재시도 로직
- API 호출 카운트 증가

### 시그니처
```python
def _execute_api_call(self, state: TurnState, tool_schemas: list) -> Any:
    """Execute LLM call, handle retries, and return the raw response object."""
```

### 주의사항
`_set_interrupt` 패치 테스트들이 이 경로를 집중적으로 검증함. 예외 처리 로직(`except Exception as e`)이 정확히 복사되었는지 확인.

### 검증
```bash
python -m pytest tests/test_streaming.py tests/test_run_agent.py -k "interrupt" -n0 -v --tb=short
git commit -am "refactor: extract _execute_api_call"
```

---

## Task C-4: `_handle_tool_batch` 추출

### 대상
API 응답에 툴콜이 있을 때 처리하는 로직 (~300줄):
- 툴콜 파싱 및 유효성 검사
- `_should_parallelize_tool_batch` 체크
- `ThreadPoolExecutor`를 통한 병렬 실행 또는 순차 실행
- `handle_function_call` 호출
- `state.current_tool_results` 업데이트

### 시그니처
```python
def _handle_tool_batch(self, state: TurnState, tool_calls: list) -> None:
    """Execute parsed tool calls and append results to state."""
```

### 검증
```bash
python -m pytest tests/test_agent_loop_tool_calling.py -n0 -q --tb=short
git commit -am "refactor: extract _handle_tool_batch"
```

---

## Task C-5: `_postprocess_turn` 추출

### 대상
루프 정상 종료 후 또는 예외 발생 시 정리 작업 (~200줄):
- `checkpoint_manager`에 저장
- `sessionDB` 업데이트
- `AutoLearner` 메모리 리뷰 트리거
- `save_trajectory` 호출

### 시그니처
```python
def _postprocess_turn(self, state: TurnState) -> dict:
    """Persist turn data and return the final API response dictionary."""
```

### 검증
```bash
python -m pytest tests/test_run_agent.py tests/test_compression_persistence.py -n0 -q --tb=short
git commit -am "refactor: extract _postprocess_turn"
```

---

## Phase C 완료 검증

```bash
# 전체 테스트 실행
python -m pytest tests/ -n0 -q --tb=short 2>&1 | tee /tmp/phase_c_result.txt

# 베이스라인 비교
diff /tmp/phase_c_baseline.txt /tmp/phase_c_result.txt

# run_conversation 메서드 길이 확인 (200줄 이내가 목표)
python -c "
import inspect, run_agent
src = inspect.getsource(run_agent.AIAgent.run_conversation)
print(f'run_conversation lines: {len(src.splitlines())}')
"

# 전체 파일 라인 수 확인 (초기 11,810줄에서 3,000줄 이상 감소 기대)
wc -l run_agent.py

git push origin refactor/phase-c-loop-decomposition
```

---

## Phase C 예상 결과

| 항목 | 변화 |
|------|------|
| `run_conversation` | 3,114줄 → ~200줄 (루프 오케스트레이션만 담당) |
| 신규 헬퍼 메서드 | `_preflight_turn`, `_build_turn_messages`, `_execute_api_call`, `_handle_tool_batch`, `_postprocess_turn` |
| `agent/turn_state.py` | 신규 ~40줄 |
| `run_agent.py` 전체 | 수천 줄이 분리되어 응집도 향상 및 복잡도 대폭 감소 |

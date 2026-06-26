---

title: Refactor Plan Phase B
type: plan
space: concept
tags: [concept]
created: 2026-05-20
updated: 2026-05-20
links: []
links:
  - "[[@action/plans/growth-2026]]"
---


# Phase B 작업 계획서 — `AIAgent.__init__()` 분해

## 전제조건
Phase A 완료 + 모든 테스트 통과 확인.

```bash
cd /Users/drew/.drewgent/source/drewgent-agent
source .venv/bin/activate
git checkout -b refactor/phase-b-init-decomposition
python -m pytest tests/test_run_agent.py -n0 -q --tb=short 2>&1 | tee /tmp/phase_b_baseline.txt
```

---

## 작업 개요

`AIAgent.__init__()` (약 L721~L1669, **950줄**)을 아래 구조로 분해.
파일 크기는 동일하지만 각 초기화 단계가 명확히 분리됨.

```python
def __init__(self, ...):          # ~50줄 (호출만)
    self._init_params(...)        # Step 1: 인수 저장
    self._init_api_client()       # Step 2: OpenAI 클라이언트
    self._init_context_limits()   # Step 3: 컨텍스트 길이 로드
    self._init_toolset()          # Step 4: 툴셋 구성
    self._init_memory()           # Step 5: 메모리/위키
    self._init_prompt_caching()   # Step 6: Anthropic 캐싱
    self._init_brain_signals()    # Step 7: Brain Signal
    self._init_checkpoints()      # Step 8: 체크포인트
    self._init_callbacks()        # Step 9: 콜백 등록
    self._init_smart_routing()    # Step 10: Smart routing
    self._init_fallback()         # Step 11: Fallback model
```

> [!IMPORTANT]
> 각 `_init_*` 메서드는 `__init__` 내 코드를 **이동**하는 것이지 복사가 아님.
> 메서드 순서가 의존성 순서이므로 반드시 위의 순서 유지.

---

## Task B-1: `_init_params` 추출

### 대상
`__init__` 시작부터 인수를 `self.*`에 저장하는 블록 전체.
`self.model = model`, `self.max_iterations = max_iterations` 등의 단순 대입 코드.

### 방법
1. 해당 블록 전체를 `def _init_params(self, model, max_iterations, ...):`로 이동
2. `__init__` 시그니처는 그대로 유지
3. `__init__` 본문 첫 줄에 `self._init_params(model, max_iterations, ...)` 추가

### 검증
```bash
python -c "
from unittest.mock import patch, MagicMock
with patch('run_agent.get_tool_definitions', return_value=[]), \
     patch('run_agent.check_toolset_requirements', return_value={}), \
     patch('run_agent.OpenAI'):
    from run_agent import AIAgent
    a = AIAgent(model='test', api_key='test', quiet_mode=True, skip_memory=True)
    assert a.model == 'test', f'Expected test, got {a.model}'
    print('OK')
"
git commit -am "refactor: extract _init_params from AIAgent.__init__"
```

---

## Task B-2: `_init_api_client` 추출

### 대상
`self.client = OpenAI(...)` 포함 구간.
API 클라이언트 생성, `base_url` 설정, provider 분기 로직.

### 주의사항
- `self.model`, `self.api_key`, `self.base_url` 등이 `_init_params` 이후 설정된 상태여야 함
- `patch("run_agent.OpenAI")` 테스트들이 이 경로를 통과함

### 검증
```bash
python -m pytest tests/test_openai_client_lifecycle.py tests/test_primary_runtime_restore.py -n0 -q --tb=short
git commit -am "refactor: extract _init_api_client"
```

---

## Task B-3: `_init_context_limits` 추출

### 대상
컨텍스트 길이 로드 블록.
`fetch_model_metadata`, `save_context_length`, `self.context_limit` 설정.

### 검증
```bash
python -m pytest tests/test_model_metadata_local_ctx.py -n0 -q --tb=short
git commit -am "refactor: extract _init_context_limits"
```

---

## Task B-4: `_init_toolset` 추출

### 대상
`get_tool_definitions`, `check_toolset_requirements` 호출 블록.
`self.tool_schemas`, `self.enabled_toolsets`, `self.disabled_toolsets` 설정.

### 주의사항
`patch("run_agent.get_tool_definitions")` 및 `patch("run_agent.check_toolset_requirements")` 패치 테스트들이 이 경로를 통과함.
추출 후 `run_agent` 네임스페이스 유지 필요 (코드가 `run_agent.get_tool_definitions`를 호출하므로).

### 검증
```bash
python -m pytest tests/test_toolsets.py tests/test_model_tools.py -n0 -q --tb=short
git commit -am "refactor: extract _init_toolset"
```

---

## Task B-5: `_init_memory` 추출

### 대상
메모리/위키 초기화 블록.
`AutoLearner`, `build_memory_context_block`, `self.memory_context` 설정.
`skip_memory` 분기 포함.

### 주의사항
테스트에서 `skip_memory=True`로 AIAgent를 생성하는 경우 대부분 이 블록을 건너뜀.
`_init_memory` 내부에서 `self.skip_memory` 체크.

### 검증
```bash
python -m pytest tests/test_insights.py tests/test_run_agent.py -k "memory" -n0 -q --tb=short
git commit -am "refactor: extract _init_memory"
```

---

## Task B-6: `_init_prompt_caching` 추출

### 대상
Anthropic 프롬프트 캐싱 설정 블록.
`apply_anthropic_cache_control` 관련 코드, `self.prompt_caching_enabled` 설정.

### 검증
```bash
python -m pytest tests/test_anthropic_adapter.py -n0 -q --tb=short -x
git commit -am "refactor: extract _init_prompt_caching"
```

---

## Task B-7: `_init_brain_signals` 추출

### 대상
Brain Signal 초기화 블록.
`get_signal_emitter`, `get_signal_processor`, `get_awareness_reporter` 호출.
`restore_workflows` 포함.

### 검증
```bash
python -m pytest tests/test_brain_signals_integration.py -n0 -v --tb=short
git commit -am "refactor: extract _init_brain_signals"
```

---

## Task B-8: `_init_checkpoints` 추출

### 대상
체크포인트 매니저 초기화 블록.

### 검증
```bash
python -m pytest tests/test_run_agent.py -k "checkpoint" -n0 -q --tb=short
git commit -am "refactor: extract _init_checkpoints"
```

---

## Task B-9: `_init_callbacks` 추출

### 대상
콜백 등록 블록.
`self.clarify_callback`, `self.sudo_callback`, `self.approval_callback` 등.

### 검증
```bash
python -m pytest tests/test_run_agent.py -k "callback" -n0 -q --tb=short
git commit -am "refactor: extract _init_callbacks"
```

---

## Task B-10: `_init_smart_routing` + `_init_fallback` 추출

### 대상
Smart model routing (~80줄) + Fallback model 초기화 (~60줄).
`self.primary_runtime`, `self.fallback_runtime` 설정.

### 검증
```bash
python -m pytest tests/test_fallback_model.py tests/test_primary_runtime_restore.py -n0 -q --tb=short
git commit -am "refactor: extract _init_smart_routing and _init_fallback"
```

---

## Phase B 완료 검증

```bash
python -m pytest tests/test_run_agent.py -n0 -q --tb=short 2>&1 | tee /tmp/phase_b_result.txt
diff /tmp/phase_b_baseline.txt /tmp/phase_b_result.txt

# __init__ 메서드 길이 확인 (50줄 이내여야 함)
python -c "
import inspect, run_agent
src = inspect.getsource(run_agent.AIAgent.__init__)
print(f'__init__ lines: {len(src.splitlines())}')
# 각 _init_* 메서드 목록 확인
methods = [m for m in dir(run_agent.AIAgent) if m.startswith('_init_')]
print('init methods:', methods)
"

git push origin refactor/phase-b-init-decomposition
```

---

## Phase B 예상 결과

| 항목 | 변화 |
|------|------|
| `AIAgent.__init__` | 950줄 → ~50줄 |
| 신규 `_init_*` 메서드 | 11개, 각 50~120줄 |
| `run_agent.py` 총 라인 | **변화 없음** (코드 이동만) |
| 테스트 결과 | 베이스라인과 **동일** |

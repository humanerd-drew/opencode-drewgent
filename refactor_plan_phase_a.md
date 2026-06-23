---

title: Refactor Plan Phase A
type: plan
space: concept
tags: [concept]
created: 2026-05-20
updated: 2026-05-20
links: []
links:
  - "[[P6-prefrontal/plans/growth-2026]]"
---


# Phase A 작업 계획서 — 모듈-레벨 헬퍼 추출

## 사전 준비

```bash
cd /Users/drew/.drewgent/source/drewgent-agent
source .venv/bin/activate
git checkout -b refactor/phase-a-module-extraction
# 베이스라인 테스트 실행 (결과 기록)
python -m pytest tests/test_surrogate_sanitization.py tests/test_run_agent.py -n0 -q --tb=short 2>&1 | tee /tmp/baseline.txt
```

---

## Task A-1: `agent/safe_io.py` 생성

### 새 파일 생성: `agent/safe_io.py`
내용: `run_agent.py` **L238~L292** 전체 복사.
파일 상단에 추가:
```python
"""Safe stdio wrappers for agent processes."""
import sys
```

### `run_agent.py` 수정
L238~L292 (`class _SafeWriter` + `def _install_safe_stdio`) 삭제 후
L237(빈 줄) 위치에 추가:
```python
from agent.safe_io import _SafeWriter, _install_safe_stdio
```

### 검증
```bash
python -c "from run_agent import AIAgent; print('OK')"
python -c "from agent.safe_io import _SafeWriter, _install_safe_stdio; print('OK')"
git commit -am "refactor: extract _SafeWriter to agent/safe_io.py"
```

---

## Task A-2: `agent/budget.py` 생성

### 새 파일 생성: `agent/budget.py`
내용: `run_agent.py` **L295~L337** 전체 복사.
파일 상단에 추가:
```python
"""Thread-safe iteration budget for agent loops."""
import threading
```

### `run_agent.py` 수정
L295~L337 삭제 후 해당 위치에 추가:
```python
from agent.budget import IterationBudget
```

### 검증
```bash
python -c "from run_agent import IterationBudget; b = IterationBudget(5); print(b.remaining)"
python -m pytest tests/test_run_agent.py -k "budget" -n0 -q --tb=short
git commit -am "refactor: extract IterationBudget to agent/budget.py"
```

---

## Task A-3: `agent/parallel_tools.py` 생성

### 새 파일 생성: `agent/parallel_tools.py`
내용: `run_agent.py` **L339~L437** 전체 복사.
파일 상단에 추가:
```python
"""Parallel tool execution helpers."""
import json
import logging
import os
import re
from pathlib import Path
```

### `run_agent.py` 수정
L339~L437 삭제 후 해당 위치에 추가:
```python
from agent.parallel_tools import (
    _NEVER_PARALLEL_TOOLS,
    _PARALLEL_SAFE_TOOLS,
    _PATH_SCOPED_TOOLS,
    _MAX_TOOL_WORKERS,
    _DESTRUCTIVE_PATTERNS,
    _REDIRECT_OVERWRITE,
    _is_destructive_command,
    _should_parallelize_tool_batch,
    _extract_parallel_scope_path,
    _paths_overlap,
)
```

### 검증
```bash
python -c "from run_agent import _is_destructive_command; print(_is_destructive_command('rm -rf /'))"
python -m pytest tests/test_run_agent.py -n0 -q --tb=short -x
git commit -am "refactor: extract parallel tool helpers to agent/parallel_tools.py"
```

---

## Task A-4: `agent/brain_file_signals.py` 생성

### 새 파일 생성: `agent/brain_file_signals.py`
내용: `run_agent.py` **L468~L560** 전체 복사.
파일 상단에 추가:
```python
"""File-path extraction helpers for brain signal tracking."""
import json
import re
from typing import Optional
```

### `run_agent.py` 수정
L468~L560 삭제 후 해당 위치에 추가:
```python
from agent.brain_file_signals import (
    _FILE_PATH_KEYS,
    _FILE_PATH_PATTERNS,
    _TERMINAL_FILE_PATTERNS,
    _extract_file_path_from_tool_args,
    _extract_file_path_from_result,
    _looks_like_path,
)
```

### 검증
```bash
python -c "from run_agent import _looks_like_path; print(_looks_like_path('/tmp/foo'))"
python -m pytest tests/test_run_agent.py -n0 -q --tb=short -x
git commit -am "refactor: extract brain file-path signals to agent/brain_file_signals.py"
```

---

## Task A-5: `agent/message_sanitizers.py` 생성

### 새 파일 생성: `agent/message_sanitizers.py`
내용: `run_agent.py` **L563~L640** 전체 복사.
파일 상단에 추가:
```python
"""Message content sanitizers (surrogates, budget warnings)."""
import json
import re
```

### `run_agent.py` 수정
L563~L640 삭제 후 해당 위치에 추가:
```python
from agent.message_sanitizers import (
    _SURROGATE_RE,
    _BUDGET_WARNING_RE,
    _sanitize_surrogates,
    _sanitize_messages_surrogates,
    _strip_budget_warnings_from_history,
)
```

### 검증 (가장 중요 — `cli.py:6486`이 직접 import함)
```bash
python -c "from run_agent import _sanitize_surrogates, _SURROGATE_RE; print('OK')"
python -c "from cli import DrewgentCLI; print('OK')"
python -m pytest tests/test_surrogate_sanitization.py -n0 -v --tb=short
git commit -am "refactor: extract message sanitizers to agent/message_sanitizers.py"
```

---

## Task A-6: `agent/tool_result_handler.py` 생성

### 새 파일 생성: `agent/tool_result_handler.py`
내용: `run_agent.py` **L642~L702** 전체 복사.
파일 상단에 추가:
```python
"""Large tool result handler — saves oversized output to file."""
import logging
import os
import re
from datetime import datetime
from drewgent_constants import get_drewgent_home

logger = logging.getLogger(__name__)
```

### `run_agent.py` 수정
L642~L702 삭제 후 해당 위치에 추가:
```python
from agent.tool_result_handler import (
    _LARGE_RESULT_CHARS,
    _LARGE_RESULT_PREVIEW_CHARS,
    _save_oversized_tool_result,
)
```

### 검증
```bash
python -m pytest tests/test_large_tool_result.py -n0 -v --tb=short
git commit -am "refactor: extract tool result handler to agent/tool_result_handler.py"
```

---

## Task A-7: hint 빌더를 `agent/prompt_builder.py`로 이동

### `agent/prompt_builder.py` 맨 아래에 추가
`run_agent.py` **L141~L235** (`_build_self_model_hint`, `_build_prefrontal_hint`) 복사.
`agent/prompt_builder.py` 상단 import에 없으면 추가:
```python
from drewgent_constants import get_drewgent_home
```

### `run_agent.py` 수정
L141~L235 삭제 후 기존 `agent.prompt_builder` import 블록(L84~L114)에 두 이름 추가:
```python
from agent.prompt_builder import (
    # ...기존 항목 유지...
    _build_self_model_hint,
    _build_prefrontal_hint,
)
```

### 검증
```bash
python -c "from run_agent import _build_self_model_hint; print('OK')"
python -m pytest tests/test_run_agent.py -n0 -q --tb=short -x
git commit -am "refactor: move hint builders to agent/prompt_builder.py"
```

---

## Phase A 완료 검증

```bash
# 전체 핵심 테스트
python -m pytest \
  tests/test_surrogate_sanitization.py \
  tests/test_large_tool_result.py \
  tests/test_run_agent.py \
  -n0 -q --tb=short 2>&1 | tee /tmp/phase_a_result.txt

# 베이스라인과 비교 (차이 없어야 함)
diff /tmp/baseline.txt /tmp/phase_a_result.txt

# 라인 수 확인 (약 660줄 감소 기대)
wc -l run_agent.py

git push origin refactor/phase-a-module-extraction
```

---

## Phase A 예상 결과

| 파일 | 변화 |
|------|------|
| `run_agent.py` | ~11,810줄 → ~11,150줄 (-660줄) |
| `agent/safe_io.py` | 신규 ~58줄 |
| `agent/budget.py` | 신규 ~48줄 |
| `agent/parallel_tools.py` | 신규 ~105줄 |
| `agent/brain_file_signals.py` | 신규 ~100줄 |
| `agent/message_sanitizers.py` | 신규 ~82줄 |
| `agent/tool_result_handler.py` | 신규 ~65줄 |

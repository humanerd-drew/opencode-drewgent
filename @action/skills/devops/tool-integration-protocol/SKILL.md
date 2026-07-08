---
title: Tool Integration Protocol
type: skill
space: outcome
tags: [outcome]
created: 2026-05-20
updated: 2026-05-20
links:
  - "[[@action/skills/SKILL-INDEX]]"
  - "[[@action/skills/devops/DESCRIPTION]]"
---


space: outcome
type: document
links:
  - "[[@action/skills/devops/DESCRIPTION]]"
  - "[[@action/skills/SKILL-INDEX]]"


# Tool Integration Protocol

Drewgent에 새로운 도구를 추가할 때 사용하는 표준 절차.

## 3단계 통합 패턴

### Step 1: 도구 핸들러 파일

파일: `tools/<name>_tool.py`

```python
import json, os
from tools.registry import registry

def check_requirements() -> bool:
    return bool(os.getenv("YOUR_API_KEY"))  #또는 True

def your_tool(param: str, task_id: str = None) -> str:
    return json.dumps({"success": True, "data": "..."})

registry.register(
    name="your_tool",
    toolset="your_toolset",
    schema={
        "name": "your_tool",
        "description": "...",
        "parameters": {
            "type": "object",
            "properties": {
                "param": {"type": "string", "description": "..."}
            },
            "required": ["param"]
        }
    },
    handler=lambda args, **kw: your_tool(
        param=args.get("param", ""),
        task_id=kw.get("task_id")
    ),
    check_fn=check_requirements,
    requires_env=["YOUR_API_KEY"],  #또는 []
)
```

### Step 2: model_tools.py import 추가

파일: `model_tools.py`, `_discover_tools()` 함수의 `_modules` 리스트

```python
"tools.your_tool",  # 알파벳 순서로 추가
```

### Step 3: toolsets.py에 toolset 배정

파일: `toolsets.py`

_HERMES_CORE_TOOLS에 추가:
```python
"your_tool",
```

## 필수 검증 체크리스트

- [ ] `registry.register()` 호출됨
- [ ] `schema["parameters"]["type"] = "object"` 확인
- [ ] `model_tools.py` import 추가됨
- [ ] `toolsets.py` toolset 배정됨
- [ ] P0 `禁tool_integration_3file` 위반 없음

## Workflow 추적

IntegrationWorkflow가 signal_processor에서 자동 추적됨.
완료 시 `brain.awareness.integration_complete` 시그널 발생.

## Pitfalls

1. **import 안 함** → 도구 레지스트리에 안 올라감
2. **toolset 안 배정** → tool_schemas에 안 포함됨
3. **check_fn이 False** → availability check 실패
4. **handler가 JSON string 안 반환** → tool result 파싱 에러
5. **requires_env 빈 배열** → API 키 없어도 등록됨 (의도한 경우 제외)

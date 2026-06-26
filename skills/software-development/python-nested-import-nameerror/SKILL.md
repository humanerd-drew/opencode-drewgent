---
title: __import__ in Nested Scope Bug Pattern
name: python-nested-import-nameerror
description: Python nested function에서 __import__('json') 사용 시 UnboundLocalError 발생 원인 + 방지 규칙
type: skill
space: outcome
tags: [bug-pattern, python, debugging]
created: 2026-05-29
updated: 2026-05-30
links:
  - "[[@action/skills/SKILL-INDEX]]"
  - "[[@identity/brain/rules]]"
---

# Python Nested Import NameError Bug Pattern

Python 함수 내부에서 `import json` 또는 `import json as X`를 실행하면, 같은 함수 내 모든 `json` 참조가 local variable가 됨.
선언보다 앞에서 `json.dumps()` 등을 호출하면 → `UnboundLocalError`.

## Root Cause — Python Lexical Scoping

Python 컴파일러가 함수 전체를 훑는다. 함수 어딘가에서 `import json as X`를 보면, 해당 함수 스코프의 `json` 이름을 **local variable**로 등록한다.
이후 `json.dumps()`가 호출되더라도, local `json`은 아직 값이 할당되지 않았으므로 → `UnboundLocalError`.

```python
def run_conversation(self):
    # ...
    if isinstance(raw, dict):
        assistant_message.content = (
            raw.get("text", "")
            or raw.get("content", "")
            or json.dumps(raw)   # ❌ line 10646 — local `json` 아직 없음
        )
    # ...
    def inner():
        import json as _json_mod  # line 10929 — 이 한 줄이
        _json_mod.dumps(...)       # `json` 이름을 local로 만듦

# Error: cannot access local variable 'json' where it is not associated with a value
```

## The Fix — module-level import 우선

```python
import json  # file top — module-level (line 29)

def run_conversation(self):
    json.dumps(raw)  # ✅ module-level `json` 사용
```

## Applied Fixes in run_agent.py

**2026-05-30 fix** — `run_conversation()` 내부 4곳 수정:

| 줄 | 수정 전 | 수정 후 | 이유 |
|----|---------|---------|------|
| 10929 | `import json as _json_mod` | `# json is module-level (line 29)` 주석 처리 | nested import 제거 — `json` 이름 local로 shadowing됨 |
| 10934 | `_json_mod.dumps(args)` | `json.dumps(args)` | module-level `json` 직접 사용 |
| 10944 | `_json_mod.loads(args)` | `json.loads(args)` | module-level `json` 직접 사용 |
| 11548 | `import os, json` | `# os, json are module-level` 주석 처리 | nested import 제거 |

**주의**: 이전 수정(2026-05-29)에서 `import json as _json_mod`를 주석 처리하고 `json.dumps()` 사용으로 바꿨지만, 같은 함수 스코프 내의 `json.loads()` 호출은 여전히 `_json_mod.loads()`로 남아있음 → `NameError: name '_json_mod' is not defined` 발생

**정답**: 모든 nested `import json` 제거 → module-level `import json` (line 29) 하나만 사용

## Detection Commands

```bash
# nested import json 패턴 찾기
grep -n "import json\|import os, json" /Users/drew/.drewgent/source/drewgent-agent/run_agent.py

# 함수 내부 import json AST로 정확히 찾기
python3 -c "
import ast, sys
with open(sys.argv[1]) as f:
    tree = ast.parse(f.read())
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef):
        local = [n for n in ast.walk(node) if isinstance(n, (ast.Import, ast.ImportFrom)) and any(a.name == 'json' for a in n.names)]
        if local:
            print(f'{node.name}: line {local[0].lineno} — {ast.unparse(local[0])}')
" /Users/drew/.drewgent/source/drewgent-agent/run_agent.py

# _json_mod 잔여 확인
grep -n "_json_mod" /Users/drew/.drewgent/source/drewgent-agent/run_agent.py
```

## Discovery Timeline

- **2026-05-29 03:14 KST**: SEO + Trend cron jobs both failed with `Error during OpenAI-compatible API call #89: cannot access local variable 'json' where it is not associated with a value`
- **Root cause**: `run_agent.py` line 10929: `import json as _json_mod` inside `run_conversation()` → `json` becomes local variable in function scope
- **Trigger**: API call #89에서 `json.loads(args)` 실행 시도시 → local `json`은 아직 값 없음 → `UnboundLocalError`
- **2026-05-29 fix**: line 10929 주석 처리, `json.dumps()` 사용으로 변경 — 하지만 `_json_mod.loads()` 미수정
- **2026-05-30 14:05 KST**: manual trigger에서 `_json_mod is not defined` NameError 여전히 발생 — log에서 확인
- **2026-05-30 14:07 KST**: line 10944 `_json_mod.loads(args)` → `json.loads(args)` 수정 — 2차 fix
- **2026-05-30 14:09 KST**: SEO Article Harvester **성공** (35개 기사 수집, heritage labeling 완료)
- **2026-05-30 14:15 KST**: Trend Harvester **성공** (175 트렌드 수집, memory sync 완료)
- **Gateway log**: `CRITICAL json NameError` 0건確認 — 완전히 제거됨

## Prevention Rule

**禁karpathy_coding_principles** 적용 — "Think Before Coding":
> IF YOU DON'T KNOW how Python scoping works in a nested function, ASK. Don't guess.

함수 내부에서 `import json`을 쓸 때는:
1. module-level `import json`이 이미 있는지 확인 (run_agent.py line 29)
2. 이미 있으면 함수 내부 import 불필요 → module-level 직접 사용
3. 불가피 시 `import json as _json_mod` 후 `_json_mod.dumps()` — but NEVER `import json` without alias
4. 수정 후 반드시 `grep -n "_json_mod" run_agent.py` 로 잔여 확인

---
*Generated: 2026-05-30 — root cause verified after 2nd fix*
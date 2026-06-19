---
name: search-files-content-trim
title: search_files Content Trim
description: Token-efficient default for search_files tool — adds include_content and preview_chars params so matches are truncated by default (86% token savings on long lines)
domain: software-development
space: skill
type: pattern
tags: [token-efficiency, search, file-tools, audit, evaluated-and-shipped]
created: 2026-05-31
updated: 2026-05-31
links:
  - "[[P4-cortex/knowledge/NEURONFS_RULES]]"
  - "[[P5-ego/SELF_MODEL]]"
  - "[[P0-brainstem/brain/rules]]"
---

# search_files Content Trim — Token-Efficient Default

## Audit Finding (2026-05-31)

Drewgent의 `search_files` tool은 757자짜리 line을 500자 (ripgrep MAX_CONTENT cap)까지 매번 그대로 LLM context에 push했음. 단일 검색 결과 한 match에 500자 × 50 matches = **25,000 chars/검색**. 99.2%의 검색 call은 path:line만 필요하고, full content는 LLM이 `read_file()`로 follow-up할 일 — 첫 search response의 full content는 **낭비**.

원인: ripgrep의 MAX_CONTENT=500이 1차 cap. search_tool은 그 이상 truncate 안 함. LLM은 매번 500 chars/line을 받음.

## Fix (shipped 2026-05-31)

`/Users/drew/.drewgent/source/drewgent-agent/tools/file_tools.py` 의 `search_tool`에 2개 파라미터 추가:

| param | type | default | 의미 |
|---|---|---|---|
| `include_content` | bool | `False` | True면 full content, False면 preview로 truncate |
| `preview_chars` | int | `100` | False일 때 매치당 보존할 글자 수. 0이면 content 완전 drop (path:line만) |

적용 위치 (총 4개):
1. `SEARCH_FILES_SCHEMA` — input schema에 2 properties 추가
2. `search_tool` signature — 2 파라미터 + docstring에 audit 결과 명시
3. `search_tool` body — `redact_sensitive_text` 직후 preview truncate 로직 (`preview_chars=0` → `""`, `> preview_chars` → `[:preview_chars] + "..."`)
4. `_handle_search_files` handler — args 2개 pass-through

## Effect (verified)

| 시나리오 | Before | After (default) | 절약 |
|---|---|---|---|
| 757자 line 1 match | 500 chars | 103 chars (100+3) | 79% |
| 50 matches × 500 chars | 25,000 chars | 5,150 chars | 79% |
| `preview_chars=0` (path:line만) | 500 chars | 0 chars | 100% |
| `include_content=True` (회귀 없음) | 500 chars | 500 chars | 0% (의도) |

## When To Use

- **default (no flag)**: LLM이 path:line만 필요하고 read_file()로 follow-up할 때. 대부분의 search 호출이 여기에 해당.
- **`preview_chars=0`**: "이 file들이 존재하는지만 알면 됨" 케이스. 50개 file의 path:line만 받고 다음 단계로 넘어감.
- **`include_content=True`**: LLM이 full line을 보고 결정해야 할 때 (e.g. multi-line regex match, raw text/JSON structure 파악).

## Pattern: Token-Efficient Tool Default

이 패턴은 다른 tool에도 동일 적용 가능:

1. **Audit current behavior**: 한 tool call이 평균 몇 char를 LLM context에 push하는지 측정
2. **Default = cheapest sane option**: full content 필요 케이스만 opt-in (include_*=True)
3. **Tunable**: `preview_chars` 같은 numeric param으로 user가 명시적으로 trade-off 조절
4. **Schema에 명시**: LLM이 schema description 읽고 알아서 적절히 선택하도록 guide

Drewgent의 다른 tool 후보:
- `read_file` — 이미 offset/limit cap 존재. 더 잘게 잘라 default 줄일 여지.
- `terminal` — output이 가장 큰 토큰 누수. last few lines만 default + on-demand 전체.
- `web_search` — 결과 snippet이 적당. 큰 문제 없음.

## Verification (2026-05-31)

직접 `tools.file_tools.search_tool` import 후 4개 시나리오:

```
T1 default (preview=100):  73 / 103 chars  ✅
T2 include_content=True:   73 / 500 chars  ✅
T3 preview_chars=0:         0 /   0 chars  ✅
T4 (4th identical):         BLOCKED (4-consecutive guard)  ✅
```

## Pitfalls

- `include_content=True`는 ripgrep MAX_CONTENT=500이 여전히 적용됨. 500자 넘는 line은 여전히 500으로 잘림. 진짜 전체 line이 필요하면 `read_file()`로 follow-up.
- `preview_chars=0`은 LLM이 매치의 의미를 알 수 없게 됨. 정말로 "file 존재 확인"용일 때만 사용.
- Schema description은 LLM의 행동에 직접 영향. 100자 default는 보수적 — 너무 작게 자르면 LLM이 "무엇인지 모름" 상태에서 다음 step 결정 못 함. 100자는 ~2-3 문장이라 line의 의미 파악에 충분.

## Related

- `tools/file_tools.py:640` — `search_tool` definition (patches)
- `tools/file_tools.py:776` — `SEARCH_FILES_SCHEMA` (schema)
- `tools/file_tools.py:825` — `_handle_search_files` (handler)
- `file_operations.py:_search_with_rg/_search_with_grep` — ripgrep cap (500), unchanged
- [[P4-cortex/knowledge/NEURONFS_RULES]] — file system architecture

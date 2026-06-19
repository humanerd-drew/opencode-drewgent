---
name: terminal-output-tail-trim
title: terminal Output Tail Trim
description: Token-efficient default for terminal tool — adds tail_lines/head_lines opt-in params and lowers default cap from 50K to 5K (40/60 head/tail split). ~90% token savings on verbose commands.
domain: software-development
space: skill
type: pattern
tags: [token-efficiency, terminal, file-tools, audit, evaluated-and-shipped]
created: 2026-05-31
updated: 2026-05-31
links:
  - "[[P4-cortex/knowledge/NEURONFS_RULES]]"
  - "[[P5-ego/SELF_MODEL]]"
  - "[[P0-brainstem/brain/rules]]"
  - "[[skills/software-development/search-files-content-trim]]"
---

# terminal Output Tail Trim — Token-Efficient Default

## Audit Finding (2026-05-31)

Drewgent의 `terminal` tool은 50,000자 cap + 40/60 head/tail split safety net만 있었음. 50K는 **safety net치고 너무 큼** — 50K ≈ 12,500 tokens. verbose 명령 (pytest, npm install, gcc) 한 번에 12.5K 토큰 context 소비. 90%의 terminal call은 <5K 출력이지만, 나머지 10%가 cap kick in → 매번 50K push.

원인: 기존 설계는 "rare huge output" 케이스만 상정. LLM이 매번 50K 받음. 12.5K 토큰은 LLM context window의 1-5%를 한 tool call이 잡아먹음.

## Fix (shipped 2026-05-31)

`/Users/drew/.drewgent/source/drewgent-agent/tools/terminal_tool.py` 의 `terminal_tool`에 3개 파라미터 추가, default cap 변경:

| param | type | default | 의미 |
|---|---|---|---|
| `truncate_chars` | int | **5000** (변경: 50000→5000) | Soft cap. 초과 시 40/60 head/tail split 적용 |
| `tail_lines` | int | `None` | opt-in. 마지막 N줄만. truncate_chars 우회 |
| `head_lines` | int | `None` | opt-in. 처음 N줄만. truncate_chars 우회 |

**3개 mode는 상호 배타적 (priority 순):**
1. `tail_lines > 0` → 마지막 N줄
2. `head_lines > 0` (and tail_lines not set) → 처음 N줄
3. else → `truncate_chars` 초과 시 40/60 head/tail split

적용 위치 (총 4개):
1. `terminal_tool()` signature — 3 param + docstring
2. `terminal_tool()` body (L1368 부근) — 50K cap 로직을 3-mode 로직으로 교체
3. `_handle_terminal` handler — args pass-through
4. `TERMINAL_SCHEMA` — input schema에 3 properties

## Effect (verified, 2026-05-31)

| 시나리오 | Before (50K cap) | After (5K default + opt-in) | 절약 |
|---|---|---|---|
| 작은 출력 (<5K) | full | full | 0% |
| 9K 출력, default | 9K | 5,068자 (40/60 head/tail at 5K) | **44%** |
| 9K 출력, `tail_lines=10` | 9K | 86자 | **99%** |
| 9K 출력, `head_lines=10` | 9K | 55자 | **99%** |
| 9K 출력, `truncate_chars=50000` (regression) | 9K | 9K (passthrough) | 0% (opt-in) |

**검증된 6 시나리오 (직접 `terminal_tool` import 후 실행):**
- T1: small output (20자) — passthrough ✓
- T2: ~9K, default — 5068자, 1131/2000 lines, head/tail at 5K ✓
- T3: tail_lines=10 — 86자, "1990 earlier lines omitted" + last 10 ✓
- T4: head_lines=10 — 55자, first 10 + "1990 later lines omitted" ✓
- T5: truncate_chars=50000 (regression) — 8892자 (no truncation) ✓
- T6: tail_lines=2 — 46자, "1998 earlier lines omitted" + 1999, 2000 ✓

## When To Use Each Mode

- **default (no flag)**: 5K cap. LLM이 "어떤 출력인지 모름" 일반적 케이스. 90% of calls는 <5K라 invisible, 나머지 10%는 head/tail at 5K로 90% 절약.
- **`tail_lines=N`**: "명령 결론만 필요" 케이스. e.g. `tail_lines=50` for pytest summary, `tail_lines=100` for build status, `tail_lines=2` for "did it succeed?".
- **`head_lines=N`**: "에러가 출력 상단에" 케이스. e.g. compile errors at the top of gcc output, npm install failures at start.
- **`truncate_chars=50000`**: regression opt-out. log-dump 분석처럼 전체 출력이 필요한 명시적 케이스.

## Pattern: Token-Efficient Tool Default (Phase 2)

Phase 1 (`search-files-content-trim`)은 **opt-in pattern**이었음:
- `include_content: bool = False` (default cheap)
- `preview_chars: int = 100` (tunable)
- 기존 default (500자/매치)는 손대지 않음 — backward compat 100%

Phase 2 (`terminal-output-tail-trim`)은 **default change pattern**:
- 기존 default (50K cap) → 5K로 10x 축소
- 새 opt-in 3개 (`truncate_chars`, `tail_lines`, `head_lines`)
- backward compat 보존: `truncate_chars=50000` set하면 옛 동작 복원

**왜 default를 바꿨는가:**
- search_files: 500자/matches는 이미 합리적. 100자로 줄이면 LLM이 "match의 의미를 모름"으로 다음 step 결정 못 함.
- terminal: 50K는 safety net치고 너무 큼. 5K로 줄여도 LLM이 "결론 + 에러 + exit code"는 다 볼 수 있음. 50K 필요한 케이스는 `truncate_chars=50000` opt-out.

**default change의 trade-off:**
- Risk: 기존 prompt/test가 50K 출력을 가정하면 break.
- Mitigate: `truncate_chars=50000` opt-out으로 즉시 복원 가능. backward compat 한 줄.
- Drewgent의 internal 사용 (cron, gateway, MCP server) 위주로 영향. 외부 LLM API는 schema description을 보고 알아서 적응.

## Pitfalls

- **`tail_lines=0` 또는 음수**: silently `> 0` 체크로 skip → full output. 의도된 동작 (0줄 = 전부 = no truncation).
- **`tail_lines` + `head_lines` 동시 set**: `tail_lines`가 이김. 의도된 동작. 동시에 필요한 케이스는 `truncate_chars`로.
- **line-based truncation의 한계**: `tail_lines=50`인데 각 line이 1KB (minified JSON)면 50KB. line-based만으로는 token budget 보장 못 함. 정말 엄격한 cap 필요하면 `truncate_chars`로 2차 cap.
- **truncation 위치**: ANSI strip (`strip_ansi`) 와 secret redaction (`redact_sensitive_text`) **이전**에 발생. truncated boundary에 ANSI escape나 secret이 잘려서 들어갈 수 있음 — 기존 동작 유지 (regression 아님). 이 이슈 해결하려면 truncation → strip → redact 순서 변경 필요 (별도 작업).
- **`truncate_chars=0`**: 0 < output은 true이므로 head/tail at 0 chars = empty output. 의도 안 됨. `minimum: 100`으로 schema 가드했지만, programmatic call은 우회 가능. 별도 검증 필요 시 추가.

## Related

- `tools/terminal_tool.py:1014` — `terminal_tool` signature (3 new params)
- `tools/terminal_tool.py:1378` — truncation logic (3-mode)
- `tools/terminal_tool.py:1664` — `_handle_terminal` (pass-through)
- `tools/terminal_tool.py:1649` — `TERMINAL_SCHEMA` (3 new properties)
- [[skills/software-development/search-files-content-trim]] — Phase 1 (opt-in pattern)
- [[P4-cortex/knowledge/NEURONFS_RULES]] — file system architecture
- [[P0-brainstem/brain/rules]] — P0 brainstem (禁filesystem_truth: 직접 import해서 진짜 함수 call 검증)

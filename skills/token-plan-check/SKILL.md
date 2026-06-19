---
name: token-plan-check
description: "MiniMax Token Plan 사용량/리셋을 터미널에서 즉시 확인하거나, zsh RPROMPT statusline으로 영구 통합하는 절차. 사용자가 토큰 얼마나 남았는지, 리셋까지 얼마인지, 주간 한도 현황을 물을 때 사용. API endpoint: GET https://api.minimax.io/v1/api/openplatform/coding_plan/remains. 기존 script 위치: ~/.drewgent/scripts/minimax_usage.py. Statusline 파일: ~/.drewgent/.zshrc_aliases."
title: Token Plan Check — Terminal Usage & Statusline
domain: brain
space: growth
type: workflow
tags: [token-plan, minimax, statusline, rprompt, zsh, terminal, drewgent]
created: 2026-06-02
updated: 2026-06-02
links:
  - "[[P4-cortex/growth/INTEGRATION_PROTOCOL]]"
  - "[[P0-brainstem/brain/Drewgent-brain/P0-brainstem/禁/禁secrets_in_code.neuron]]"
  - "[[P0-brainstem/brain/Drewgent-brain/P0-brainstem/禁/禁filesystem_truth.neuron]]"
  - "[[P0-brainstem/brain/rules]]"---

# Token Plan Check — Terminal Usage & Statusline Integration

MiniMax Token Plan (coding_plan) 사용량을 터미널/RPROMPT에서 확인하는 표준 절차.

## 트리거 조건

다음 중 하나라도 해당되면 이 스킬을 로드:
- "내 토큰 사용량 좀 보여줘" 류 task
- "리셋까지 남은 시간" 류 task
- "주간 한도 / 이번 주 사용량" 류 task
- "Token Plan statusline / RPROMPT 영구 표시" 류 통합 task
- "platform.minimax.io/console 안 가고 보고 싶어" 류 자동화 task

## 1단계: 기존 자산 확인

**이미 구현된 것** (2026-06-02 작업):

| 자산 | 경로 | 용도 |
|---|---|---|
| 메인 스크립트 | `~/.drewgent/scripts/minimax_usage.py` | 한 번 조회 / watch / json / cache write / RPROMPT |
| zsh 통합 파일 | `~/.drewgent/.zshrc_aliases` | aliases + RPROMPT 함수 |
| 캐시 | `~/.drewgent/cache/minimax_usage.json` | API 응답 (60s TTL) |
| 잠금 | `~/.drewgent/cache/minimax_usage.json.lock` | bg refresh 중복 spawn 방지 (PID) |

**메인 스크립트 모드:**

```
minimax_usage.py                  # 컬러 pretty 출력
minimax_usage.py --json           # raw API JSON
minimax_usage.py --watch 30       # 30초마다 refresh, Ctrl-C로 종료
minimax_usage.py --write-cache P  # fetch + atomic write, silent
minimax_usage.py --rprompt        # RPROMPT 한 줄 문자열 (cache-first)
minimax_usage.py --maybe-refresh  # cache stale일 때만 bg refresh spawn
```

`.env`의 `MINIMAX_API_KEY` 자동 로드. 키 없으면 명확한 에러.

## 2단계: API 직접 호출 (스크립트 우회)

스크립트 거치지 않고 빠르게 확인:

```bash
API_KEY=$(grep "^MINIMAX_API_KEY=" ~/.drewgent/.env | cut -d= -f2-)
curl -sS "https://api.minimax.io/v1/api/openplatform/coding_plan/remains" \
  -H "Authorization: Bearer $API_KEY" | python3 -m json.tool
```

**응답 필드** (`model_remains[].<model_name="general">`):

| 필드 | 의미 |
|---|---|
| `current_interval_remaining_percent` | 5h 윈도우 남은 % (100 - used) |
| `current_weekly_remaining_percent` | 주간 윈도우 남은 % |
| `remains_time` (ms) | 5h 윈도우 리셋까지 ms |
| `weekly_remains_time` (ms) | 주간 리셋까지 ms |
| `start_time` / `end_time` (ms epoch) | 5h 윈도우 경계 |
| `weekly_start_time` / `weekly_end_time` | 주간 경계 |
| `current_interval_status` / `current_weekly_status` | 0=inactive, 1=active, 2=exhausted, 3=unlimited |

⚠️ **알려진 한계**: `current_interval_total_count` / `current_interval_usage_count` 같은 토큰 절대량 필드는 응답에 존재하지만 항상 0으로 옵니다. MiniMax가 이 엔드포인트로는 %만 노출. 절대량 필요 시 결제 대시보드 사용.

## 3단계: Statusline / RPROMPT 통합

**이미 한 번 통합된 상태** (2026-06-02). 사용자가 해야 할 일:

1. `~/.zshrc`에 한 줄 추가:
   ```bash
   source ~/.drewgent/.zshrc_aliases
   ```
2. `source ~/.zshrc` 또는 새 터미널 열기

그러면:
- 모든 prompt 우측에 `Token Plan  5h:53% 2h35m  ·  wk:52% 5d16h` 표시
- 색상: < 50% 사용 = green, 50-80% = yellow, > 80% = red
- 60초마다 백그라운드 자동 refresh (PID lock으로 중복 spawn 방지)
- cache miss 시 "Token Plan  refreshing…" → 1-2초 후 fresh data

**RPROMPT format** (compact, ~30 chars + ANSI):
```
Token Plan  5h:53% 2h35m  ·  wk:52% 5d16h
```

stale 시 prefix `⏳` (dim).

**Aliases 자동 사용 가능**:
- `mm-usage` — 한 번 조회
- `mm-usage-watch` — 30초 watch
- `mm-usage-json` — raw JSON
- `mm-usage-refresh` — cache 즉시 갱신

tmux/ssh 세션도 동일: `source ~/.zshrc`가 자동 실행되므로 RPROMPT 동일하게 적용.

## 4단계: Drewgent에서 활용

에이전트가 "내 토큰 상황 알려줘" 또는 "리셋까지 몇 분?" 류 task 받으면:

```bash
# Option A: RPROMPT 모드 호출 (cache-first, 1-2초 응답)
python3 ~/.drewgent/scripts/minimax_usage.py --rprompt

# Option B: 즉시 fresh 데이터 (API 직접, ~500ms)
python3 ~/.drewgent/scripts/minimax_usage.py

# Option C: JSON 파싱해서 structured 답변
python3 ~/.drewgent/scripts/minimax_usage.py --json | jq '.model_remains[] | select(.model_name=="general") | {interval_used: (100 - .current_interval_remaining_percent), weekly_used: (100 - .current_weekly_remaining_percent), reset_in_h: (.remains_time / 3600000)}'
```

에이전트는 pretty 출력 또는 JSON 중 응답 형태에 따라 선택. RPROMPT 모드는 사용자에게 보여줄 때 적합, JSON은 다른 도구와 연동할 때 적합.

## 5단계: 검증 체크리스트

스크립트 / 통합 변경 후:

```bash
# 1. syntax check
python3 -c "import ast; ast.parse(open('~/.drewgent/scripts/minimax_usage.py').read())"

# 2. 직접 호출 — 200 OK
~/.drewgent/scripts/minimax_usage.py
# → "Token Plan usage" 헤더 + general/video 섹션

# 3. RPROMPT 모드 — 1줄 출력
~/.drewgent/scripts/minimax_usage.py --rprompt
# → "Token Plan  5h:N% XhYm  ·  wk:N% XdYh"

# 4. zsh 통합 — source 후 RPROMPT 설정 확인
zsh -c 'source ~/.drewgent/.zshrc_aliases; echo "RPROMPT=$RPROMPT"'
# → "RPROMPT=$(_mm_rprompt)"

# 5. cache lock cleanup
ls ~/.drewgent/cache/minimax_usage.json.lock 2>/dev/null
# → 안 떠야 정상 (refresh 완료 후 정리)
```

## Pitfalls (실제 겪은 함정)

### P1: spawn_background_refresh return False → "n/a" 표시 버그
**증상**: cache 없을 때 동시 5번 호출 → 첫 1개 "refreshing…", 나머지 4개 "n/a"
**원인**: `if load_api_key() and spawn_background_refresh(...)` — lock held로 spawn이 False 반환하면 "n/a"로 fallback
**수정**: lock held는 "다른 refresh가 이미 진행 중" 의미 → "refreshing…"으로 동일하게 표시. "n/a"는 API key가 정말 없을 때만.
**교훈**: spawn return value에 "성공/실패"만 보지 말고, "다른 누군가가 하고 있다"는 상태도 정상으로 처리.

### P2: prompt render 시 API 직접 호출
**증상**: RPROMPT 함수에서 매번 API hit → terminal lag + rate limit 위험
**원인**: stale-while-revalidate 패턴 부재
**수정**: cache-first (RPROMPT는 cache만 읽음, stale 시 background spawn만)
**교훈**: prompt frequency × API cost 계산. 매번 호출 = 좋지 않은 디자인. Stale-while-revalidate가 정답.

### P3: 중복 bg spawn
**증상**: 5번 빠른 prompt → 5개 refresh 동시 spawn → API rate limit
**원인**: spawn check 부재
**수정**: PID lock file (`.lock` 확장자, PID 저장). 다음 spawn 전에 lock 확인 + `os.kill(pid, 0)`로 alive check. Lock held by alive process → skip.
**교훈**: fire-and-forget도 동시성 제어 필요. PID lock이 단순하고 견고.

### P4: API 응답에 `current_interval_usage_count: 0`
**증상**: 토큰 절대량 보고 싶지만 항상 0
**원인**: MiniMax API 디자인 — 이 엔드포인트는 % 만 노출, 절대량은 미노출
**대응**: 사용자에게 %로만 표시. 절대량 필요 시 결제 대시보드 안내. 이건 사용자/시스템 한계로 명시.
**교훈**: API 문서 없으면 trial-and-error. 응답 보고 디자인 제약 파악. user에게 "이건 안 돼" 솔직히 말하기.

### P5: atomic write 안 함
**증상**: refresh 도중 RPROMPT read → partial JSON → crash
**원인**: write_file로 덮어쓰기 + read가 중간에 끼어들 수 있음
**수정**: `tmp = cache.with_suffix(".tmp")` → `tmp.write_text(...)` → `tmp.replace(cache)`. POSIX rename은 atomic.
**교훈**: cache file은 항상 atomic. 동일 패턴 권장.

### P6: statusline (RPROMPT) 색상 / 비-TTY
**증상**: pipe/capture로 RPROMPT 호출 시 ANSI 코드 그대로 노출
**원인**: `USE_COLOR = sys.stdout.isatty()` 체크로 stdout이 TTY 아니면 색상 OFF. 단, RPROMPT는 terminal에서 호출되지만 일부 capture는 비-TTY.
**대응**: 현재 RPROMPT은 색상 OFF일 때 plain text로 fallback. 사용자 보고가 색 빠진 형태로 보이게 됨. (Acceptable)
**교훈**: TTY 감지 정확히. RPROMPT는 interactive context라 거의 항상 TTY, 그래서 색상 OK.

### P7: 첫 실행 시 cache 없음
**증상**: 새 터미널 켜자마자 prompt → "Token Plan  refreshing…" 잠깐 → 1-2초 후 fresh
**원인**: cache는 60s TTL, 새 shell은 그 전 cache 없음
**대응**: 
1. `~/.zshrc_aliases` 하단에 `python3 minimax_usage.py --maybe-refresh &` 1회 즉시 spawn
2. user는 "refreshing…" 봤다가 1-2초 후 fresh
**교훈**: 첫 진입 latency는 허용, 단 명확한 placeholder ("refreshing…")로 user confusion 방지.

### P8: RPROMPT에 literal `$(_mm_rprompt)` 출력 (가장 자주 발생하는 함정)
**증상**: prompt 우측에 `$(_mm_rprompt)` 같은 **리터럴 텍스트**가 그대로 나옴. evaluate 안 됨.
**원인**: zsh는 기본적으로 RPROMPT 안의 command substitution을 **evaluation하지 않음**. `RPROMPT='$(_mm_rprompt)'` 라고 적어도 prompt 자체는 매번 새로 평가되는데, 그 평가 시점에 `$()` 가 그대로 literal 로 남음.
**조건**: `setopt prompt_subst` 가 켜져 있어야만 RPROMPT 안의 `$()`, `${var}`, `$(())` 가 매 prompt마다 evaluation됨.
**수정**: `~/.drewgent/.zshrc_aliases` 에 `setopt prompt_subst 2>/dev/null` 한 줄 추가.
**검증**:
```bash
zsh -c 'source ~/.drewgent/.zshrc_aliases
        print "prompt_subst: ${options[prompt_subst]:-off}"
        print "RPROMPT expansion: ${(e)RPROMPT}"'
# → "prompt_subst: on"
# → "RPROMPT expansion: Token Plan  5h:60% 2h 4m  ·  wk:53% 5d 16h" (literal 아닌 실제 데이터)
```
**테스트 시 함정**: `print -P "..."` 로 검증하면 `%` 가 prompt escape 로 해석돼서 출력에서 사라짐. `print` 또는 `${(e)RPROMPT}` 로 검증할 것.
**교훈**:
- RPROMPT / PROMPT / PS1 안에 dynamic content (function call, var, command) 넣을 때는 **반드시 `setopt prompt_subst`** 동반.
- zsh 기본은 `prompt_subst: off`. bash와 다른 부분.
- 사용자에게 "literal 텍스트가 보인다"는 feedback 받으면 가장 먼저 확인.

### P9: "Drewgent이 동작 안 한 터미널에도 RPROMPT 나옴" (scope 오해)
**증상**: 사용자가 평소 쓰는 zsh 터미널 (drewgent 실행 안 함) 에도 Token Plan RPROMPT 표시됨. "drewgent 터미널에서만 나올 줄 알았는데 왜 로컬에도 따라다니지?" 라는 feedback.
**원인**: RPROMPT는 zsh 전역 기능. source .zshrc_aliases 만 하면 모든 zsh shell (iTerm, Terminal.app, tmux, ssh, vscode integrated terminal) 에 적용. "Drewgent" 래 wrapping이 아니라 zsh 레벨.
**오해 패턴**: agent가 "tmux/ssh 공통" 이라고 디자인한 의도를 사용자는 "drewgent 만" 으로 해석. **양방향 모두 가능성 있음** — 사용자가 명확히 의도 말하지 않으면 추측하면 안 됨.
**수정**: tty 기반 marker file 로 scope 한정.
- Drewgent wrapper 함수: launch 시 `touch /tmp/drewgent-rprompt-${tty##*/}`, exit 시 `rm`.
- `_mm_rprompt()`: marker 없으면 즉시 return (RPROMPT 비움).
- 결과: drewgent 실행 중인 tty만 RPROMPT 켜짐. 다른 터미널 / tmux pane / ssh 세션은 자동으로 꺼짐.

**zsh function 정의 함정**: `drewgent` 가 alias로 이미 정의돼있으면 `drewgent() { ... }` 가 parse error (`defining function based on alias`).
- 해결: `unalias drewgent 2>/dev/null` 먼저 호출 후 function 정의.
- zsh 동작: function > alias 이므로 unalias 하면 function 이 우선.

**검증 시나리오**:
| 상태 | tty1 (drewgent) | tty2 (idle) |
|---|---|---|
| 둘 다 fresh | (empty) | (empty) |
| tty1에서 drewgent 실행 | on | (empty) |
| tty1 drewgent 종료 | (empty) | (empty) |
| tmux pane1=drewgent, pane2=idle | on | (empty) |

**교훈**:
- "전역/특정 컨텍스트" 디자인은 사용자에게 명시적으로 확인. 추측으로 디자인하면 양쪽 다 어긋남.
- "Universal tmux/ssh"와 "drewgent only"는 **mutually exclusive design choices**. 사용자 의도가 모호하면 둘 중 하나 정해달고 묻기.
- Scope 한정이 필요할 때의 정석: marker file (per-tty) 또는 env var. PID 검사 (parent process) 는 fragile.

### P10: "drewgent이 안 켜져요" — Incomplete class rename from upstream fork
**증상**: `drewgent` 또는 `drewgent acp --stdio` 실행 시:
```
2026-06-02 17:17:09 [INFO] acp_adapter.entry: Loaded env from /Users/drew/.drewgent/.env
2026-06-02 17:17:09 [INFO] acp_adapter.entry: Starting drewgent-agent ACP adapter
ACP dependencies not installed.
Install them with:  pip install -e '.[acp]'
```
**진짜 에러**: `drewgent_cli/main.py`의 `cmd_acp()` 가 `try/except ImportError` 로 `acp_main()` 호출. 실제 ImportError 메시지가 catch되어 "ACP dependencies not installed" 로 출력. **사용자에게는 가짜 메시지**가 보임.

**진단 단계**:
1. `pip install -e '.[acp]'` 시도 → 그래도 실패 (venv의 pip shebang 깨졌을 수 있음 — `/Users/drew/drewgent_workspace/...` 옛 path 가리킴)
2. `python -m pip install -e .` 로 editable install → 일단 됨
3. `drewgent acp --stdio` 재시도 → 여전히 같은 에러
4. 직접 `python -c "from acp_adapter.entry import main"` → **잘 import 됨**
5. `python -c "from acp_adapter.entry import main; main()"` 실행 → 진짜 에러 보임:
   ```
   ImportError: cannot import name 'DrewgentACPAgent' from 'acp_adapter.server'
   ```

**진짜 root cause**: 2026-04-08 initial fork commit (`6409efb72 Initial fork: hermes-agent → Drewgent Agent`) 에서 Hermes → Drewgent rebrand 시 `acp_adapter/entry.py`만 `DrewgentACPAgent`로 import 하도록 변경, `acp_adapter/server.py`의 class 정의는 `HermesACPAgent` 그대로 남음. **불완전한 rename**.

**수정 (surgical 1-line + docstring)**:
```python
# acp_adapter/server.py:430
-class HermesACPAgent(acp.Agent):
-    """ACP Agent implementation wrapping Hermes AIAgent."""
+class DrewgentACPAgent(acp.Agent):
+    """ACP Agent implementation wrapping the AIAgent core."""
```

**검증**:
- `python -c "from acp_adapter.entry import main"` → OK
- `drewgent acp --stdio` 실행 → ACP 부팅 → JSON-RPC `initialize` 응답:
  ```json
  {"jsonrpc":"2.0","id":1,"result":{"agentInfo":{"name":"drewgent-agent","version":"0.7.1"},...}}
  ```
- `rm -rf acp_adapter/__pycache__` 필수 (stale .pyc가 rename 무시)

**교훈**:
- **`except ImportError: print("ACP dependencies not installed")` 같은 광범위한 catch-all 에러 메시지는 거짓말**일 가능성 높음. 실제 ImportError는 별도 출력 안 함 → 사용자/agent 둘 다 misleading.
- fork/rename 검증 패턴: rename 후 `grep -rn "OldName" --include="*.py"` 0건이어야 함. 1건이라도 있으면 incomplete.
- `try: import X; X() / except: print("X missing")` 패턴은 debug 어렵게 만듦. **traceback 출력**하거나 **ImportError 그대로 propagate**하는 게 정답.
- `pip install -e '.[extra]'` 가 venv에서 안 될 때는 `python -m pip install ...` 우회.
- venv의 pip shebang가 옛 path 가리키면 깨진 상태. 새 venv 만들거나 pip 직접 호출.

**연쇄 진단 단계 (이 incident 전체)**:
1. 사용자: "drewgent 안 켜져" → 1차 가설: wrapper 문제
2. binary 직접 실행 → "ACP dependencies not installed" → 가짜 에러 메시지
3. `acp` 패키지 import 가능한지 → 가능 (dist-info만 보고 오판했음)
4. `agent_client_protocol` 직접 import → 실패 (오해, PyPI 이름 ≠ 모듈 이름)
5. `python -c "from acp_adapter.entry import main; main()"` → 진짜 ImportError 보임
6. `grep`으로 rename 누락 발견 → 1-line fix → ACP 정상 부팅

가장 시간이 많이 든 단계는 #2 (가짜 에러 메시지에 낚임). **catch-all 에러 메시지 항상 의심**이 1순위 교훈.

### P11: ACP vs chat subcommand (plain terminal에서 hang 함정)
**증상**: `drewgent` 또는 `drewgent acp --stdio` 실행 시:
```
[INFO] acp_adapter.entry: Loaded env from /Users/drew/.drewgent/.env
[INFO] acp_adapter.entry: Starting drewgent-agent ACP adapter
[INFO] acp_adapter.server: ACP client connected
... (hang) ...
```
**진짜 원인**: ACP는 **Agent Client Protocol** (JSON-RPC 기반). stdin/stdout 이 ACP transport 로 잡혀서 동작. plain terminal 에서 실행하면 ACP server 가 stdin 에서 JSON-RPC 메시지를 기다리며 **무한 hang**.
- "ACP client connected" 메시지는 자기 자신 (stdin/stdout) 이 transport 로 연결됐다는 뜻. **정작 JSON-RPC 보낼 client 는 없음**.
- ACP 사용 사례: **VS Code / Zed / JetBrains 같은 IDE가 client driver** 역할. plain terminal 은 client 가 아니라 단순 stdin.
- 그러므로 plain terminal UX는 `drewgent chat` 이 정답.

**해결**:
- wrapper 함수가 `command "$DREW_BIN" acp --stdio "$@"` 호출 → `command "$DREW_BIN" chat "$@"` 로 변경.
- `drewgent chat` 은 prompt_toolkit 기반 TUI 채팅. user 가 stdin 으로 직접 메시지 입력, agent 가 stdout 으로 응답.

**사용자 의도와 subcommand 분리**:
- 5/27 memory: 사용자가 명시적으로 `acp --stdio` 선택. 이유: "각 터미널이 독립 Python 프로세스" (격리).
- **이 격리는 wrapper 자체의 `exec python -m ...` 구조가 보장**. subcommand 와 무관.
- 따라서 `chat` 도 동일한 격리 제공 + plain terminal UX.

**`drewgent chat --help` 핵심 옵션**:
- `-q QUERY` — single query (non-interactive)
- `-m MODEL` — e.g. `anthropic/claude-sonnet-4`, `MiniMax-M3`
- `--provider` — `auto`, `minimax`, `minimax-cn`, `anthropic`, ...
- `--resume SESSION_ID` — 기존 세션 이어가기
- `-v` — verbose
- `--yolo` — 위험한 명령 자동 승인

**검증**:
```bash
# ACP (hang) vs chat (실행) 비교
timeout 1 /Users/drew/.local/bin/drewgent acp --stdio </dev/null
# → "ACP client connected" 후 hang (timeout kill)

timeout 1 /Users/drew/.local/bin/drewgent chat </dev/null
# → bash tcsetattr warning (TTY mode 설정 시도) 후 timeout kill
# → hang 아님, TUI 초기화 후 user input 대기
```

**교훈**:
- ACP 와 chat 은 subcommand 가 다르고 **transport model 자체가 다름**. ACP=client/server, chat=direct TUI.
- wrapper 디자인 시 사용자가 어디서 invoke 할지 plain terminal 인지 IDE 인지 **명시적으로 확인** 필수. 5/27 memory 는 "isolation" 이유만 적혀있고 UX 단서 없음 — agent가 추측하면 안 됨.
- "ACP client connected" 같은 메시지는 **자기 자신이 transport 로 잡혔다는 confirmation** 일 뿐, 정작 user 가 client 역할을 할 수 있다는 의미 아님. plain terminal 에선 false positive.

## Related

- [[P4-cortex/growth/INTEGRATION_PROTOCOL]] — tool/skill 통합 절차
- [[P0-brainstem/brain/Drewgent-brain/P0-brainstem/禁/禁secrets_in_code.neuron]] — API key는 .env, 절대 코드에 금지
- [[P0-brainstem/brain/Drewgent-brain/P0-brainstem/禁/禁filesystem_truth.neuron]] — 캐시 = truth, stale이면 표시
- `~/.drewgent/scripts/minimax_usage.py` — 메인 스크립트
- `~/.drewgent/.zshrc_aliases` — zsh 통합 파일
- `~/.drewgent/cache/minimax_usage.json` — 캐시

### P12: Drewgent chat TUI status bar에 Token Plan 통합
**배경**: 기존 status bar는 모델, context, %, session duration을 표시. Token Plan (5h interval + weekly)도 같은 줄에 통합하면 user가 한 번에 모든 사용량 확인 가능.

**구현 위치**: `cli.py:DrewgentCLI` (Drewgent chat TUI)
- `_get_status_bar_snapshot()` — snapshot dict 에 `plan: Optional[Dict]` 필드 추가
- `_get_plan_snapshot()` — cache read helper (synchronous, ~5ms)
- `_format_reset_compact(ms)` — `2h` / `1h23m` / `5d16h` compact format
- `_build_status_bar_text()` (width tier) 와 `_get_status_bar_fragments()` (color) 두 곳에 TP segment 추가

**Snapshot 필드 (plan dict)**:
```python
{
    "interval_used": 50,                # 100 - current_interval_remaining_percent
    "interval_resets_ms": 10007103,     # API field "remains_time"
    "weekly_used": 53,
    "weekly_resets_ms": 492407103,      # API field "weekly_remains_time"
}
```

**Width tier (TP 포함)**:
| width | parts | format 예시 |
|---|---|---|
| < 52 | 2 | `⚕ {model} · {duration}` |
| 52-75 | 3 | `⚕ {model} · {pct} · {duration}` |
| 76-99 | 4 | `⚕ {model} │ {ctx}/{total} │ {pct} │ {duration}` |
| **≥ 100** | **6** | `⚕ {model} │ {ctx}/{total} │ {pct} │ {duration} │ 5h:{N}%/{reset} │ wk:{N}%/{reset}` |

**Threshold 100** 선택 이유: 기존 4-part가 ~60 chars → TP 2 parts 추가에 ~25 chars 필요. 100 cols 미만이면 TP 안 보이게.

**Color (fragments only)**:
- `5h:55%` / `wk:53%` 부분: `_status_bar_context_style(percent)` 가 적용 (green < 50, yellow 50-80, red > 80, critical 95+)
- `/2h` / `/5d16h` 부분: `class:status-bar-dim`
- separator ` │ `: `class:status-bar-dim`

**Cache read 동작**:
- `~/.drewgent/cache/minimax_usage.json` read (synchronous, ~5ms)
- 파일 없거나 malformed면 `None` 반환 → TP segment 숨김 (graceful degradation)
- Cache miss 시 user가 `mm-usage` 한 번 실행하면 다음 status bar refresh 부터 TP 표시

**Refresh 전략**:
- Status bar 자체는 cache만 읽음 (no API call). Prompt 마다 render되므로 매번 read는 비효율처럼 보이지만 < 5ms 라 acceptable.
- Cache 자체의 refresh는 `minimax_usage.py` 모드들이 담당:
  - 터미널 init 시 `_mm_maybe_refresh` 가 1회 spawn
  - `mm-usage` 직접 실행 시 즉시 write
  - `mm-usage-watch N` 실행 시 매 N초 마다 write
  - cron `mm-usage-refresh` job 등록 시 주기적 write

**Cache miss / fresh 표시**:
- Stale 표시 (예: `⏳`) 추가 안 함. status bar 가 항상 fresh 라고 가정. Stale 데이터는 user 가 `mm-usage` 직접 실행으로 갱신.
- 만약 stale 표시 원하면: snapshot 의 `fetched_at` 읽어서 age > 2*TTL 일 때 `⏳` prefix 추가. 현재는 simple 모드.

**Format 결정 — 왜 `5h:55%/2h` 인가**:
- `5h` / `wk` label: 사용자가 "5h interval", "weekly" 구분 가능
- `{N}%` : 사용량 (colored)
- `/2h` : reset까지 남은 시간 (dim)
- 4 chars (`5h:`) + 3 chars (`55%`) + 1 char (`/`) + ~5 chars (`2h`) = ~13 chars/segment
- separator ` │ ` 포함 ~16 chars/segment
- 2 segments = ~30 chars 추가

**대안 (사용자가 다른 format 원하면)**:
- `5h 55% (2h)` — 공백 구분, 더 가독성
- `5h:55% 2h left` — explicit "left"
- `TP 5h:55%/2h wk:53%/5d16h` — single segment (separator 없이)

현재 구현은 compact 모드. 변경 시 `_build_status_bar_text` / `_get_status_bar_fragments` 의 TP format string 만 수정.

**Trade-off 노트**:
- Status bar render frequency: 매 prompt input 마다 (~ 수십 회 / 세션). cache read 5ms × 50 = 250ms / 세션. Acceptable.
- 만약 session 길어져서 부담되면: `@lru_cache(maxsize=1)` + 1초 TTL 로 cache. 현재는 YAGNI.
- Plan data 가 None 일 때 (cache missing) graceful fall back: 그냥 TP segment 안 보임. user 가 `mm-usage` 실행하면 보임. 에러 메시지 없음 — 이게 더 친절.

**교훈**:
- 기존 status bar 가 이미 model/ctx/duration 같은 운영 metrics 통합 중 → 새 metric (Token Plan) 추가 자리 있음.
- Threshold (width) 기반 graceful degradation: 좁은 터미널에서는 metric 자동 숨김, 넓을 때 추가. User 수동 토글 불필요.
- Cache-first + API-no-call: status bar 는 절대 API 직접 호출 X. 다른 도구가 cache 관리, status bar 는 read-only.
- Color coding 일관성: 기존 `context_percent` 가 쓰는 color class (good/warn/bad/critical) 재사용. 새 color 정의 안 함.

**관련 파일**:
- `cli.py` line 1484-1544 (helper methods)
- `cli.py` line 1604 (snapshot `plan` field)
- `cli.py` line 1607 (snapshot populate)
- `cli.py` line 1678-1696 (`_build_status_bar_text` TP)
- `cli.py` line 1762-1793 (`_get_status_bar_fragments` TP)

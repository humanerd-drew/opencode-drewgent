---
title: - skills/project/kis-autonomous-bot-debug/SKILL
type: skill
space: outcome
tags: [outcome]
created: 2026-05-20
updated: 2026-05-20
links:
  - "[[@action/skills/SKILL-INDEX]]"
  - "[[projects/X]]"
  - "[[projects/uncategorized]]"
  - "[[sessions/YYYY-MM-DD_title]]"
  - "[[sessions/prior-session]]"
  - "[[skills/Y]]"
---



# Session Pattern Archiver

Discord thread/대화가 종료되면 → Obsidian 판단 패턴 세션 노트로 자동 기록.

## 트리거

|| 유형 | 조건 | 우선순위 |
||------|------|----------|
|| **Auto (thread_close)** | Discord thread archived/locked → gateway event hook | highest |
|| **Auto (thread_delete)** | Discord thread deleted → gateway event hook | highest |
|| **Auto (inactivity)** | thread 2시간 미활동 → cron (c7041bc0a7b9) | 높음 |
|| **Manual** | `/sync-obsidian` 명령 | 항상 가능 |

## 출력 노트 형식

생성 위치: `MEMORY/sessions/YYYY-MM/YYYY-MM-DD_project-title.md`

```markdown
# Session: [Thread Title]
**Date**: YYYY-MM-DD
**Trigger**: thread_close | thread_delete | inactivity | manual
**Participants**: @user1, @user2

## 🎯 의도 (Humanerd's Intent)
[이 작업을 왜 시작했는가 — Humanerd의 목적]

## 🧠 사고방식 (Reasoning Pattern)
[문제를 어떻게 풀어가려 했는가]
[왜 이 방법을 선택했는가]

## ⚖️ 가치 판단 (Value Judgments)
[이 상황에서 무엇을 우선시했는가]
[이것은重要하고 저것은 덜 중요하다 — 왜?]

## 👁️ 맹점 (Blind Spots)
[Humanerd가 자주 놓치는 것]
[에이전트가 대신 확인해줘야 할 것]
[과거 이 종류의 실수 기록]

## ✅ 결정 & 액션 (Decisions)
- **결정/액션 A** → 이유: ..., 다음: ...

## 🔗 관련 노트
`[[projects/X]]`, `[[skills/Y]]`, `[[sessions/prior-session]]`

## 📋 Follow-ups
- [ ] [todo by when - who]

## Meta
**Archived**: YYYY-MM-DD HH:MM
**Pattern completeness**: full | partial | inferred
```

## Clarify 질문 (비동기, Discord DM)

**inactivity / manual 트리거** → Clarify 전송 (이전 버전)
**2026-04-13 이후**: 모든 트리거에서 Clarify DM 비활성화 — "세션패턴 정리는 나에게 묻지 말고 알아서 하기" 지시 반영. 모든 archive는 즉시 Obsidian 노트 생성만 수행.
```
📝 세션 패턴 정리해드릴게요 — 30초만 답변주세요:

🎯 **의도**: 이 작업의目的是?
⚖️ **가치**: 무엇을優先했나요?
👁️ **맹점**: 놓치기 쉬운 것은?
```

24시간 무응답 → 부분 정보로 노트 생성 (completeness=inferred)

**thread_close / thread_delete 이벤트**에서는 Clarify 생략 — 즉시 아카이브 (humanerd 지시: "세션패턴 정리는 나에게 묻지 말고 알아서 하기")

## Backlink 규칙

생성 후 projects/ 노트 업데이트:
- thread topic과 관련된 `[[projects/X]]` 검색
- 해당 프로젝트 노트 하단에 `## Sessions\n- [[sessions/YYYY-MM-DD_title]]` 추가
- 없으면 `[[projects/uncategorized]]`에 추가

## 사용법

```
/sync-obsidian                    # 현재 thread 수동 동기화
/sync-obsidian [thread_id]        # 특정 thread 동기화
/sync-obsidian --project=X        # 프로젝트별 세션 모두 동기화
```

## 파일 구조

```
MEMORY/
└── sessions/
    └── YYYY-MM/
        ├── YYYY-MM-DD_project-alpha.md   # 판단 패턴 노트
        └── YYYY-MM-DD_project-beta.md
```

## Phase 1: ✅ 완료
- `archiver.py` core engine (LLM pattern inference, note generation, project linker)
- `MEMORY/sessions/YYYY-MM/` 자동 생성
- Cron job: every 2h (job_id: c7041bc0a7b9)

## Phase 2: ✅ 완료
- Discord webhook 전송 (User-Agent 헤더로 Cloudflare 우회)
- Clarify embed 자동 발송
- Thread state tracker (`discord_threads.json`)
- `python3 archiver.py clarify` CLI
- `python3 archiver.py archive` with webhook support

## Phase 3: ✅ 완료
- Discord thread close/delete event hook → `gateway/platforms/discord.py` on_thread_update / on_thread_delete에서 archiver subprocess 호출
- `archiver.py archive-thread-event` subcommand (ask_clarify=False, auto-archive)
- Thread 메시지 Discord API 직접 fetch (`_fetch_thread_messages`)
- projects/ backlink 자동 업데이트 (sessions/index.md 연동)

## Phase 4: ✅ 완료 — 증분 아카이빙 (Incremental Archiver)

### 문제
이전 방식: 스레드 종료 시 **一次性** (one-shot) 전체 메시지 fetch + Abstract 생성.
문제: 스레드 종료 시 fetch가 수십 개의 메시지를 한꺼번에 처리하면서 사용자에게 메시지 수십 개를 보냄.

### 해결: 증분 아카이빙
| 시점 | 동작 | 설명 |
|------|------|------|
| Thread 생성 | `ensure-note` | 빈 스kelaton 노트 skeleton note 생성 |
| 메시지 수신 (on_message) | 버퍼링 (5초 debounce) | 메시지를 버퍼에 쌓고 5초간 flush 지연 |
| 버퍼 flush | `append-batch` | 버퍼를 batch 단위로 노트에 추가 |
| Thread 종료 | `finalize` | Abstract 생성 후 노트 마무리 |

**핵심 개선**: `finalize`는 기존에 쌓인 batch를 재사용하므로, thread 종료 시 **남은 unflushed 메시지만** fetch하면 됨. 큰 스레드도 메시지를 수십 개씩 나누어 처리 → 사용자에게도 하나씩.

### 새 CLI 명령
```bash
archiver.py ensure-note    --thread-id X --channel-id X --title X [--participants @user]
archiver.py append-batch   --thread-id X --batch-num N --messages [msg1 msg2 ...]
archiver.py finalize       --thread-id X
```

### discord.py 변경
- `DiscordAdapter.__init__`: `_msg_batch_buf`, `_msg_batch_count`, `_msg_batch_timer` 추가
- `on_message`: allowed-user 메시지를 버퍼링 (비동기, 5초 debounce flush)
- `on_thread_create`: 새 스레드 → `ensure-note` 호출
- `on_thread_delete/update`: `finalize` 호출 (더 이상 `archive-thread-event` 아님)
- `disconnect()`: shutdown 시 batch timer 정리

### 데이터 흐름
```
on_message → _queue_message_to_buffer()
                    ↓ 5초 debounce
              _flush_message_batch() → archiver.py append-batch
                    ↓ 각 batch마다 (노트에 실시간 기록)
on_thread_close → finalize() → Abstract + 마무리
```

###discord_threads.json 필드 (Phase 4)
```json
{
  "thread_id_123": {
    "session_file": "sessions/2026-04/Session Title",
    "batch_count": 5,
    "last_batch_at": "2026-04-13T15:32:00",
    "status": "active",
    "created_at": "2026-04-13T10:00:00",
    "last_activity": "2026-04-13T15:32:00"
  }
}
```

**batch_count=0은 finalize 직전 batch 번호가 아님** — `_msg_batch_count`는 파이썬 인스턴스 변수이므로 gateway 재시작 시 초기화. 재시작 후 첫 finalize에서 누락 batch는 Discord API로 보충 fetch.

## Related
- [[@action/skills/SKILL-INDEX]]

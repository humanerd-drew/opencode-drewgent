---
title: Kanban Dashboard
name: kanban-dashboard
type: skill
description: Drewgent kanban board UI — Flask dashboard server for visual task management
space: outcome
tags: [outcome]
created: 2026-05-20
updated: 2026-06-15
links:
  - "[[@memory/kanban/KANBAN_INDEX]]"
  - "[[skills/automation/DESCRIPTION]]"
  - "[[@identity/brain/rules]]"
---

# Kanban Dashboard Skill

# Kanban Dashboard — Flask Server (Primary)

Flask server가 kanban board를 렌더링. SSE 실시간 업데이트 + 드래그드롭 + 모바일 대응.

**URL**: `http://macmini:8765/kanban`

## 레이아웃

- **보드 탭**: All / default / content / integrations — 탭 클릭으로 보드 필터
- **컬럼**: To Do | Ready | In Progress | Blocked | Completed — 상태별 한 줄
- **카드 표시** (3줄):
  - **Title**: 제목 (60자 truncation, hover 시 전체 표시)
  - **Summary**: body에서 `## Topic` 첫 문단 추출한 1줄 요약 (`.card-summary`, 2줄 clamp)
  - **Meta row 1**: Priority badge + Category badge (컬러 + 이모지: draft-trend=📈#5bc0eb, draft-conversation=💬#aa66ff, draft-seo=🔍#00c853 등) + Board + Worker + Created + Assignee
  - **Meta row 3** (if draft path exists): Draft file link (📄, 보라색 `obsidian://open` 링크) — `_extract_draft_path()`로 body `## Draft 파일 위치` 파싱, `_obsidian_url()`로 URL 변환
- **카드 상세 모달**: 카드 클릭 시 모달 오픈. 5개 탭:
  - **Description** (기본): task body (내용/설명) 표시 + 📄 Open in Obsidian 버튼 (body에 `## Draft 파일 위치` 경로가 있으면 렌더링) + ✏️ Edit 버튼
  - **Events**: 생성, 완료, 블록, 클레임 등 이벤트 히스토리
  - **Result**: task result 필드 (작업 결과물)
  - **Info**: 모든 메타 필드 (trigger_source, tenant, claim_lock, worker_pid, heartbeat 등)
  - Escape 키 또는 overlay 클릭으로 닫기
  - 데이터 출처: `GET /kanban/api/task/<id>`
- **Body 에디터**: Description 탭에서 Edit 버튼 → title input + body textarea + Save/Cancel 버튼으로 전환. 저장 시 `POST /kanban/api/edit` 호출. 저장 후 SSE 브로드캐스트로 보드 새로고침.
- **실시간**: SSE 스트림 연결 → 카드 액션 시 즉시 화면 반영 (초록 점으로 연결 상태 표시)
- **드래그드롭**: 카드를 다른 컬럼으로 드래그하면 상태 자동 변경
- **모바일**: 터치 스크롤, 작은 화면에서 컬럼 너비 축소

## LaunchAgent (Self-Healing, Auto-Restart)

```
/Users/drew/Library/LaunchAgents/ai.drewgent.kanban-dashboard.plist
```

- `KeepAlive: SuccessfulExit=false` → 프로세스 죽으면 자동 재시작
- MacMini 재부팅해도 자동 실행
- 로그: `/Users/drew/.drewgent/P6-prefrontal/logs/kanban-server.log`

## 관리 명령

```bash
# 상태 확인
launchctl list | grep kanban

# 수동 시작/정지
launchctl start ai.drewgent.kanban-dashboard
launchctl stop ai.drewgent.kanban-dashboard

# 로그 확인
tail -f /Users/drew/.drewgent/P6-prefrontal/logs/kanban-server.log
```

## 엔드포인트

| Method | Path | Description |
|--------|------|-------------|
| GET | `/kanban` | Kanban board HTML (SSE 실시간 업데이트) |
| GET | `/kanban/api/board` | JSON board state (tasks grouped by status) |
| GET | `/kanban/api/task/<task_id>` | Full task detail (body + events) — 모달 데이터 소스 |
| GET | `/kanban/api/events` | Recent events (minutes query param) |
| GET | `/kanban/api/stream` | SSE 실시간 스트림 |
| POST | `/kanban/api/complete` | task complete |
| POST | `/kanban/api/claim` | task claim |
| POST | `/kanban/api/block` | task block |
| POST | `/kanban/api/unblock` | task unblock |
| POST | `/kanban/api/create` | task create |
| POST | `/kanban/api/delete` | task delete |
| POST | `/kanban/api/dispatch` | task dispatch (spawn worker) |
| POST | `/kanban/api/update_status` | task status 변경 (드래그드롭) |
| POST | `/kanban/api/edit` | task title/body 수정 (form: task_id, title, body) |

## Body Parser Helpers (server-side)

`kanban_dashboard_server.py`에 내장된 body 파싱 함수들:

| 함수 | 용도 |
|------|------|
| `_extract_summary(body)` | `## Topic` 첫 문단 추출, bold/newline 제거, 180자 truncation |
| `_extract_source(body)` | `## Content Source` 섹션에서 source + score 파싱 |
| `_categorize(title)` | 제목 `[tag]` prefix 추출 (예: `draft-trend`, `draft-conversation`) |
| `_cat_color(cat)` | 카테고리 → 컬러 매핑 (trend=#5bc0eb, conversation=#aa66ff, seo=#00c853) |
| `_cat_emoji(cat)` | 카테고리 → 이모지 매핑 (trend=📈, conversation=💬, seo=🔍) |
| `_extract_draft_path(body)` | `## Draft 파일 위치` 섹션에서 vault draft 절대경로 추출 |
| `_obsidian_url(vault_path)` | 절대경로 → `obsidian://open?vault=Drewgent&file=...` URL 변환 (`urllib.parse.quote`로 인코딩) |

## Obsidian Vault Integration

칸반 task body에 `## Draft 파일 위치` 섹션으로 vault 경로가 기록된 경우, 대시보드에서 직접 Obsidian으로 이동 가능:

### Card-level
- `.card-draft-link`: `<a>` 태그로 vault 파일명 표시, 클릭 시 `obsidian://open` URL 실행
- `.card-draft`: 경로는 있으나 URL 변환 실패 시 텍스트로만 표시
- CSS: 보라색(#8b5cf6) dotted underline, hover 시 solid로 변경, `event.stopPropagation()`으로 카드 클릭 이벤트 충돌 방지

### Modal-level
- Description 탭 하단에 📄 Open in Obsidian 버튼 (JS로 body에서 `## Draft 파일 위치` regex 매칭 후 동적 생성)
- 버튼: `background:#8b5cf6`, 흰색 텍스트, 6px radius
- URI scheme: `obsidian://open?vault=Drewgent&file={encodeURIComponent(relative_path)}`
- draft 경로가 없으면 버튼 미표시

### File path convention
- 절대경로: `/Users/drew/.drewgent/P2-hippocampus/memories/insights/YYYY-MM-slug.md`
- 상대경로 (URL용): `P2-hippocampus/memories/insights/YYYY-MM-slug.md`
- vault name: `Drewgent` (고정 — `~/.drewgent` 디렉토리명)
- Obsidian URL 동작 조건: macOS에서 Obsidian이 설치되어 있어야 함. Safari/Chrome/Firefox에서 `obsidian://` scheme 핸들러 등록 필요.

## Board Maintenance

Kanban 보드 정리 프로토콜 — content pipeline에서 생성된 draft-trend task가 쌓이면:

1. **중복 확인**: 같은 주제의 task가 여러 개면 body가 더 완성된 쪽 유지, 나머지 삭제
2. **Completed 정리**: 완료된 task는 `POST /kanban/api/delete`로 제거 (board clutter 방지)
3. **Stale todo 정리**: assignee 없고 2주 이상 방치된 todo는 삭제 또는 재할당
4. **최종 검증**: `GET /kanban/api/board`로 최종 상태 확인

정리 기준: `[draft-trend]` task는 같은 GitHub repo/주제명이면 중복으로 간주. `assignee=None` + created_at 14일 이상이면 stale.

## 파일

- Server script: `/Users/drew/.drewgent/P4-cortex/scripts/kanban_dashboard_server.py`
- LaunchAgent plist: `/Users/drew/Library/LaunchAgents/ai.drewgent.kanban-dashboard.plist`

## Pitfalls

- `get_tasks()` in server uses its own `init_db()` — task table schema must match `drewgent_tasks.db` (both use same board column). If schema mismatches, board returns empty.
- Access from outside: `http://macmini:8765/kanban` (same network). MacMini hostname or IP 사용.
- **f-string escape bug**: Python f-string에서 `{{var}}` → literal `{var}` 출력. Python 변수 사용은 `{var}` (single brace).
- **Server restart required**: Changing `kanban_dashboard_server.py` doesn't auto-reload. Must run `launchctl stop ai.drewgent.kanban-dashboard && launchctl start ai.drewgent.kanban-dashboard` to apply changes.
- **Python 3.14 compat**: Server runs under Python 3.14.4 (from `.venv`). Syntax is OK but test in the actual venv, not system python3.
- **Modal JavaScript missing**: The server generates HTML with `onclick="openModal('tid')"` on each card, but `openModal(taskId)`, `switchTab(tab)`, and `closeModal()` must be defined in the inline `<script>` block. If these JS functions are missing (e.g. after editing the template f-strings), clicking cards silently does nothing. Verify their presence after any edit to the HTML template section. The modal also needs `escapeHtml()` for safe body rendering and event listeners for Escape/overlay-close.
- **Card title truncation**: Card titles are truncated to 60 chars on the board. Full title visible in modal header or card `title` attribute (hover).
- **Body parser regex**: `_extract_summary()` uses regex `## Topic\s*\n+(.*?)(?:\n\n|\n##)` which assumes the body has a `## Topic` heading followed by the summary paragraph. If the body format changes (e.g. no `## Topic`), falls back to first non-empty non-heading line.
- **Edit API idempotency**: `POST /kanban/api/edit` always updates body (even empty string) but only updates title if non-empty. To clear body, send `body=` (empty). The edit event is logged in `task_events` with kind='edited'.
- **JS modal functions are in f-string**: `openModal()`, `switchTab()`, `editBody()`, `saveBody()`, `cancelEdit()`, `escapeHtml()` are all embedded in the Python f-string HTML template. Any syntax error in these JS functions breaks the entire modal. After editing, verify with `curl -s http://macmini:8765/kanban | grep -c 'function openModal'` (>0 means present).
- **Card enrichment on page load**: `_extract_summary()` and `_extract_source()` run at page render time — they add server-side compute per card. For boards with 50+ cards, consider caching or moving extraction to JS. Currently fine for <30 cards.
- **Obsidian URL dependency**: `obsidian://open` requires (1) Obsidian.app installed on macOS, (2) browser-registered URL scheme handler. Links silently fail on non-macOS or without Obsidian. The `_obsidian_url()` function only generates URLs for paths under `/Users/drew/.drewgent/` — other paths render as plain text.
- **Draft path format sensitivity**: `_extract_draft_path()` relies on the exact section header `## Draft 파일 위치` in the body. If the content-pipeline changes this header (e.g. to `## Draft Location`), draft links stop rendering silently. The regex also expects the path on the immediately following line.
- **Modal draft link via JS regex**: The Obsidian button in the modal Description tab is generated client-side by a regex against `task.body`. This means if the body is edited via the dashboard (Edit button), the Obsidian link updates automatically on next modal open — no page reload needed. But if the body is edited externally (DB direct, API), the modal shows stale links until reload.

## Board UI Workflow (n8n)

### Trigger
- **Cron**: Every 5 minutes (`*/5 * * * *`)

### Nodes

```
1. Cron Trigger (every 5min)
   ↓
2. SQLite Node — Query drewgent_tasks.db
   SQL: |
     SELECT id, title, status, assignee, created_at,
            last_heartbeat_at, consecutive_failures
     FROM tasks
     WHERE board = 'default'
     ORDER BY priority ASC NULLS LAST, created_at DESC
     LIMIT 50
   ↓
3. Discord Bot Token (from .env: DISCORD_BOT_TOKEN)
   ↓
4. Discord Embed Builder (per status group)
   ↓
5. Edit Message — post board to designated Discord channel
```

### Board Embed Format

```
=== Drewgent Kanban Board ===
Board: default | Updated: 2026-05-19 10:30 KST

[todo] 3 tasks
  🟡 t_abc123 — Implement kanban-dashboard skill
  🟡 t_def456 — Fix cycle detection bug

[ready] 2 tasks
  ⚪ t_ghi789 — Deploy n8n workflow

[in_progress] 1 task
  🔵 t_jkl012 — kanban-orchestrator skill (worker: pid 12345)

[blocked] 1 task
  🔴 t_mno345 — gateway notifier (failures: 3)

[completed] 7 tasks (today: 2)
  ✅ t_pqr678 — multi-board support
  ✅ t_stu901 — activity logger integration

React to manage:
  ✅ = complete | 🔄 = unblock | ❌ = block
```

### Task Groups (by status)

| Status | Color | Emoji | Meaning |
|--------|-------|-------|---------|
| todo | 🟡 | YELLOW | Not yet ready |
| ready | ⚪ | WHITE | Claimable |
| in_progress | 🔵 | BLUE | Worker active |
| blocked | 🔴 | RED | Waiting / failed |
| completed | ✅ | GREEN | Done |

## Reaction → Action Workflow

When user reacts to the board message, n8n captures the reaction event:

```
1. Discord Reaction Event (add)
   ↓
2. Extract: message_id, emoji, user_id
   ↓
3. SQLite — find task by id (from message content parsing)
   ↓
4. Switch on emoji:
   - ✅ → kanban_complete(task_id, result="manual")
   - 🔄 → kanban_unblock(task_id)
   - ❌ → kanban_block(task_id, reason="manual")
   - 🔁 → kanban_claim(task_id, ttl_seconds=3600)
   ↓
5. Edit board message (refresh status)
```

### Emoji Mapping

| Emoji | Action | Tool |
|-------|--------|------|
| ✅ | Complete task | `kanban_complete` |
| 🔄 | Unblock task | `kanban_unblock` |
| ❌ | Block task | `kanban_block` |
| 🔁 | Claim task | `kanban_claim` |

## Gateway Notifier (Phase 2)

Push task events to Discord subscribers.

### SQLite Schema Addition

```sql
CREATE TABLE IF NOT EXISTS kanban_notify_subs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id     TEXT NOT NULL,
    platform    TEXT NOT NULL,  -- 'discord', 'telegram', etc.
    chat_id     TEXT NOT NULL,
    thread_id   TEXT,
    subscriber  TEXT NOT NULL,  -- user_id or channel_id
    created_at   TEXT NOT NULL,
    UNIQUE(task_id, platform, chat_id, subscriber)
);

CREATE INDEX IF NOT EXISTS idx_notify_task ON kanban_notify_subs(task_id);
```

### Notifier Workflow

```
Task event fires (completed/blocked/crashed)
  ↓
1. Event Listener (from DrewgentTaskStore.task_events table)
   ↓
2. Lookup subscribers for this task_id
   ↓
3. Per subscriber:
   - Build Discord embed with event details
   - Send via Discord webhook / bot
   - Include: task title, status change, result summary
   ↓
4. Log notification in task_events
```

### Notification Embed Format

```
🎉 Task Completed
  [content] multi-board support
  Result: boards table + board-aware dispatch_once
  Time: 2026-05-19 10:35 KST
  Trigger: integration_workflow
```

## n8n Workflow JSON (board poll)

```json
{
  "name": "Drewgent Kanban Board",
  "nodes": [
    {
      "name": "Cron Trigger",
      "type": "n8n-nodes-base.cron",
      "parameters": {
        "rule": {"interval": [{"field": "minutes", "minutes": 5}]}
      }
    },
    {
      "name": "Query Tasks",
      "type": "n8n-nodes-base.sql",
      "parameters": {
        "operation": "executeQuery",
        "dataMode": "resolve",
        "query": "SELECT id, title, status, assignee, created_at FROM tasks WHERE board = 'default' ORDER BY created_at DESC LIMIT 50"
      }
    },
    {
      "name": "Build Embed",
      "type": "n8n-nodes-base.code",
      "parameters": {
        "jsCode": "// Group by status, build Discord embed JSON"
      }
    },
    {
      "name": "Post to Discord",
      "type": "n8n-nodes-discord.api",
      "parameters": {
        "webhook": "{{$env.DISCORD_WEBHOOK_KANBAN}}"
      }
    }
  ]
}
```

## Discord Channel Setup

Board message posted to: `1492883985473208522` (content-notify-channel)
Reaction events captured via Discord bot intents: `GUILD_MESSAGES`, `MESSAGE_REACTION_ADD`

## Verification

1. n8n workflow active and running
2. Board embed posted to Discord channel
3. Reaction → task action confirmed
4. Subscriber notifications delivered on task completion

## Pitfalls (n8n/Discord)

- **Poll frequency**: 5min is default, too frequent (1min) may hit rate limits
- **Message vs thread**: Board message in channel, reactions on that message
- **Emoji uniqueness**: Multiple reactions from same user → deduplicate by user_id + emoji
- **Board refresh**: After reaction action, edit the board message (not new message) to keep context

## References

- `references/n8n-protocol.md` — n8n webhook protocol
- `references/kanban-modal-fix-20260615.md` — Modal openModal/switchTab implementation details
- `references/kanban-card-enrichment-20260615.md` — Card enrichment (body summary, category badge, source) + edit API + board cleanup protocol

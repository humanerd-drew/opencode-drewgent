---
name: minimax-usage
description: Check MiniMax Token Plan usage, current 5h interval, and weekly remaining — terminal-friendly output (no browser/console). Use when the user asks about "Token Plan 남은거", "minimax 사용량", "리셋까지 얼마", "주간 한도", or wants a quick status check without opening platform.minimax.io/console.
title: MiniMax Token Plan — Terminal Usage Check
domain: devops
space: growth
type: workflow
tags: [minimax, token-plan, api, usage, drewgent]
created: 2026-06-02
updated: 2026-06-02
links:
  - "[[P4-cortex/growth/INTEGRATION_PROTOCOL]]"
  - "[[P5-ego/SELF_MODEL]]"
  - "[[P0-brainstem/brain/rules]]"---

# MiniMax Token Plan — Terminal Usage Check

Skip platform.minimax.io/console — query the Token Plan API directly from the terminal.

## 1. API Endpoint (discovered 2026-06-02)

```
GET https://api.minimax.io/v1/api/openplatform/coding_plan/remains
Authorization: Bearer ${MINIMAX_API_KEY}
```

**Why GET, not POST**: trial showed POST returns `404 page not found`. GET returns JSON.

**Auth source**: `MINIMAX_API_KEY` from `~/.drewgent/.env` (also exported in `~/.zshrc`).

## 2. Response Schema (important: percentages, not absolute counts)

```json
{
  "model_remains": [
    {
      "model_name": "general",                       // "general" = text models (M3, etc.), "video" = video gen
      "start_time": 1780376400000,                   // interval start (ms epoch)
      "end_time": 1780394400000,                     // interval end
      "remains_time": 9819982,                       // ms until interval reset
      "current_interval_remaining_percent": 49,      // 0~100, percent REMAINING
      "current_interval_status": 1,                  // 0=inactive, 1=active, 2=exhausted, 3=unlimited
      "weekly_start_time": 1780272000000,
      "weekly_end_time": 1780876800000,              // weekly window = 7 days
      "weekly_remains_time": 492219982,              // ms until weekly reset
      "current_weekly_remaining_percent": 48,
      "current_weekly_status": 1,
      "current_interval_total_count": 0,             // ⚠ always 0 — see Pitfall P1
      "current_interval_usage_count": 0              // ⚠ always 0
    },
    // {model_name: "video", ...} typically reports unlimited (status 3, percent 100)
  ],
  "base_resp": { "status_code": 0, "status_msg": "success" }
}
```

Window math: 5h interval = `(end_time - start_time) / 1000 / 3600 = 5`. Weekly = 7 days. Timestamps are in user's local TZ (already in KST when shown via `datetime.fromtimestamp().astimezone()`).

## 3. Ready-Made Script (created 2026-06-02)

`~/.drewgent/scripts/minimax_usage.py` (7.1KB, no external deps, stdlib only)

```bash
python3 ~/.drewgent/scripts/minimax_usage.py            # colored table + progress bars
python3 ~/.drewgent/scripts/minimax_usage.py --json     # raw JSON for monitoring
python3 ~/.drewgent/scripts/minimax_usage.py --watch 30 # 30s refresh, Ctrl-C 종료
```

Output format:
```
Token Plan usage
fetched 2026-06-02 16:15:24

● general
  5h interval
    used:      ████████████░░░░░░░░░░░░░░░░░░   51.0%   (active)
    resets in: 2h 44m  (at 2026-06-02 19:00 KST)
  weekly
    used:      ████████████░░░░░░░░░░░░░░░░░░   52.0%   (active)
    resets in: 5d 16h  (at 2026-06-08 09:00 KST)
```

## 4. Shell alias (user must add manually)

`~/.zshrc` is write-protected from `mcp_patch`. User adds these 2 lines themselves:

```bash
alias mm-usage='python3 /Users/drew/.drewgent/scripts/minimax_usage.py'
alias mm-usage-watch='python3 /Users/drew/.drewgent/scripts/minimax_usage.py --watch 30'
```

## 5. Pitfalls

### P1: Absolute token counts not exposed
The fields `current_interval_usage_count` / `current_weekly_usage_count` are always 0 in the response. MiniMax exposes only **percentages** of the window remaining, not absolute token consumption. For absolute counts, the user has to go to platform.minimax.io/console — there's no programmatic alternative for this endpoint. Don't promise the user token counts if they ask.

### P2: POST returns 404, use GET
First instinct for `/coding_plan/remains` is to POST (since it's an action-like endpoint name). The endpoint is actually GET-only. Trial found this in 1 attempt.

### P3: `~/.zshrc` is write-protected
`mcp_patch` on `/Users/drew/.zshrc` returns `Write denied: ... is a protected system/credential file`. Don't try to add aliases via patch — instruct the user to add them in their next shell session. The `.env` API key is fine to read from the script, but adding shell config requires user action.

### P4: `tcsetattr: Inappropriate ioctl for device` warning
Bash warning when piping `minimax_usage.py --watch` through `timeout`/non-TTY. Comes from Python's TTY detection in the watch loop. Harmless in real terminal use. The `--watch` mode also clears the screen on each refresh, which can be janky in non-TTY contexts.

### P5: Video bucket reports "unlimited"
The `model_name: "video"` entry typically shows `current_interval_status: 3` (unlimited) and `current_weekly_status: 3`. The user's main concern is `general` (text models). Don't get confused by video bucket's 100% remaining — it's not a separate quota, just labeled as unlimited for billing purposes.

### P6: Window times are local TZ
`start_time` / `end_time` are ms-epoch UTC, but `datetime.fromtimestamp(...).astimezone()` renders them in the user's local TZ (KST in Drewgent's case). Don't double-convert or you'll show wrong times.

## 6. Future Extensions (suggested, not implemented)

- **Statusline integration**: `mm: 51% | 5d16h` next to the prompt. Touches Drewgent identity layer → confirm with user before implementing.
- **Cron alert**: When `current_interval_remaining_percent < 20`, send Discord notification. Add as separate cron job + skill.
- **Multi-account support**: If user has multiple MiniMax keys, allow `mm-usage --key <name>` to switch. Currently the script reads only one fixed path.

## 7. Related

- [[P4-cortex/growth/INTEGRATION_PROTOCOL]] — Drewgent 3-file integration protocol
- [[P5-ego/SELF_MODEL]] — Drewgent identity (for statusline extension)
- `~/.drewgent/scripts/minimax_usage.py` — the implementation
- `~/.drewgent/.env` — API key source
- MiniMax console: https://platform.minimax.io/console (for absolute counts, fallback only)

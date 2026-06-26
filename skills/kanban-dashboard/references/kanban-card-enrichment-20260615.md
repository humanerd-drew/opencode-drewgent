# Kanban Card Enrichment & Edit — 2026-06-15

## Trigger

User complained that kanban dashboard shows items but "내용을 볼 수 없어 불편하다" — cards only showed truncated title, no body, no distinction between tasks. Also wanted to edit task content from the dashboard.

## Changes Made

### 1. Card Display Enrichment

**Problem**: Cards only showed title (60 chars) + board name + assignee. All `[draft-trend]` tasks looked identical.

**Solution**: Added 3 new visual elements per card:
- **Category badge** (`card-cat`): Extracts `[tag]` prefix from title, color-coded per category (draft-trend=blue, draft-conversation=purple, draft-seo=green)
- **Body summary** (`card-summary`): Extracts first paragraph after `## Topic` heading, 180-char max, 2-line CSS clamp
- **Source info** (`card-source`): Parses `## Content Source` section for source name/score

**Server-side helpers** (in `kanban_dashboard_server.py`):
- `_extract_summary(body)` — regex `## Topic\s*\n+(.*?)(?:\n\n|\n##)`
- `_extract_source(body)` — regex `## Content Source.*?\n- source:\s*(.*?)\n`
- `_categorize(title)` — regex `\[([^\]]+)\]`
- `_cat_color(cat)` / `_cat_emoji(cat)` — dict lookups

**CSS additions**:
```css
.card-summary { font-size: 12px; color: #999; line-height: 1.4; margin: 4px 0 6px 0;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.card-source { color: #666; font-size: 10px; }
```

### 2. Task Body Editing

**Problem**: No way to edit task body/description from the dashboard. User had to use CLI or direct DB.

**Solution**: Added `POST /kanban/api/edit` endpoint + modal Edit/Save UI.

**API endpoint**:
- Route: `POST /kanban/api/edit`
- Form params: `task_id` (required), `title` (optional, empty = no change), `body` (always updated)
- Logs event: `kind='edited'` with payload `{title: "...", body_len: N}`
- Returns: `{ok: true, task_id: "..."}`
- SSE broadcasts `{action: "edit", task_id: "..."}`

**JS functions** (in inline `<script>`):
- `editBody()` — switches Description tab from read-only to edit mode (title input + body textarea + Save/Cancel)
- `saveBody()` — POSTs to `/kanban/api/edit`, updates window._editBody/_editTitle on success
- `cancelEdit()` — restores read-only view from stored window._editBody

### 4. Obsidian Vault Draft Link

**Problem**: Kanban cards showed briefs (367-878 chars) but real draft content lived in vault (`P2-hippocampus/memories/insights/`). User had to manually find files. Workflow: "칸반 보고 옵시디언으로 이동해서 작업하라는거야?"

**Solution**: Added `_extract_draft_path()` and `_obsidian_url()` server-side helpers to extract the vault path from the body `## Draft 파일 위치` section and convert it to an `obsidian://open` URL.

**Card-level** (server-rendered at page load):
- New row: `📄 2026-05-cc-switch-...` (clickable, opens in Obsidian)
- CSS: `.card-draft-link` (보라색 dotted underline, `event.stopPropagation()`)
- Only renders if body contains `## Draft 파일 위치` path

**Modal-level** (JS-injected on openModal):
- Description tab bottom: purple "📄 Open in Obsidian" button
- JS regex: `Draft\s*파일\s*위치\s*\n\s*(\/[^\n]+)`
- URI: `obsidian://open?vault=Drewgent&file=...`
- Fallback: if path doesn't match `/Users/drew/.drewgent/` prefix, show as text only

**Server-side helpers**:
- `_extract_draft_path(body)` — regex `## Draft 파일 위치\s*\n\s*(/[^\n]+)`
- `_obsidian_url(vault_path)` — strips `/Users/drew/.drewgent/` prefix, URL-encodes with `urllib.parse.quote`

**Verification**:
```bash
# Card-level link
curl -s http://macmini:8765/kanban | grep 'card-draft-link' | head -3
# Modal link (JS template)
curl -s http://macmini:8765/kanban | grep 'obsidian://open' | head -5
```

**Problem**: 30 tasks accumulated (29 content + 1 integrations). 18 todo, 11 completed. Many duplicates and stale.

**Cleanup actions**:
1. Duplicate detection: same topic (cc-switch, superpowers-zh, CodeGraph) → keep best body, delete rest (3 deleted)
2. Completed purge: 11 completed content tasks deleted (results were already logged)
3. Stale todo: 9 unassigned tasks older than 14 days deleted
4. Final state: 6 tasks, all drewgent-assigned

### Verification

```bash
# Check card enrichment renders
curl -s http://macmini:8765/kanban | grep -o 'card-summary">[^<]*'
curl -s http://macmini:8765/kanban | grep -o 'card-cat[^>]*>[^<]*'

# Test edit API
curl -s -X POST -d 'task_id=t_xxx&title=new title&body=new body' http://macmini:8765/kanban/api/edit

# Verify API
curl -s http://macmini:8765/kanban/api/task/t_xxx | python3 -c "import sys,json; print(json.load(sys.stdin)['task']['body'][:100])"
```

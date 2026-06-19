# Kanban Modal Fix — 2026-06-15

## Problem

Kanban dashboard at `http://macmini:8765/kanban` showed task cards correctly but clicking
any card did nothing. The HTML had `onclick="openModal('{{tid}}')"` on every card and a
modal `<div>` with 3 empty tabs (Events, Result, Info), but the JavaScript functions
`openModal()`, `switchTab()`, and `closeModal()` were **never defined** in the inline
`<script>` block.

## Root Cause

The server script (`kanban_dashboard_server.py`) generates the full HTML page as Python
f-strings inside the `kanban_board()` Flask route function. Modal tabs (Events, Result,
Info) and the card `onclick` handler were added to the HTML template early on, but the
accompanying JavaScript to fetch task data and populate the modal was never written.
The modal remained a dead UI shell.

## Fix

Added ~120 lines of JavaScript to the inline `<script>` block, implementing:

### Functions

- **`openModal(taskId)`**: Fetches `GET /kanban/api/task/<taskId>`, populates:
  - Modal header: task title
  - Meta bar: id, board, status, assignee, priority, created_at
  - **Description tab** (new, default-active): task `body` field, escaped via
    `escapeHtml()`. Shows "(No description)" if empty.
  - **Events tab**: task_events rows as timeline cards with kind label + payload
    details. Shows "No events" if empty.
  - **Result tab**: task `result` field in a scrollable block. Shows "(No result yet)"
    if empty.
  - **Info tab**: all non-null metadata fields in label:value list
    (trigger_source, workspace_kind, tenant, claim_lock, worker_pid,
    consecutive_failures, started_at, completed_at, created_by, etc.)
- **`switchTab(tab)`**: Toggles `.active` class between tab buttons and content divs
- **`closeModal()`**: Removes `.open` class from `.modal-overlay`
- **`escapeHtml(str)``: DOM-based XSS-safe text rendering

### Event Handlers

- Overlay click → `closeModal()`
- Escape keydown → `closeModal()`

### Tab Order

1. Description (default active) — was missing entirely
2. Events — existed as placeholder
3. Result — existed as placeholder
4. Info — existed as placeholder

## Key Details

- The API endpoint `GET /kanban/api/task/<task_id>` was already implemented and returned
  full task rows (`SELECT * FROM tasks`) plus events. It just wasn't being called.
- Card titles are truncated to 60 chars on the board; full title visible in modal.
- Body content is rendered as pre-wrapped text in a `.result-block` div (not markdown).
- The modal size is 600px max-width, 85vh max-height with scrollable body.

## File Changed

- `/Users/drew/.drewgent/P4-cortex/scripts/kanban_dashboard_server.py`
  - Modal HTML: added Description tab button + `content-body` div
  - JavaScript: ~120 lines of new functions between SSE and drag-drop code

## Restart Required

After editing `kanban_dashboard_server.py`:
```bash
launchctl stop ai.drewgent.kanban-dashboard
sleep 2
launchctl start ai.drewgent.kanban-dashboard
```

The server has no auto-reload. Verify:
```bash
curl -s http://macmini:8765/kanban | grep -c 'function openModal'
# Expected: 1
```

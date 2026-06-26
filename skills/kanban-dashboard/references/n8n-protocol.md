---

title: N8N Protocol
type: resource
space: outcome
tags: [outcome]
created: 2026-05-20
updated: 2026-05-20
links: []
links:
  - "[[@action/skills/SKILL-INDEX]]"
---




# Kanban Dashboard — n8n Protocol

## n8n Workflow Structure

### Trigger: Cron (every 5 minutes)

```
Node: n8n-nodes-base.cron
Schedule: */5 * * * *
```

### Node 1: SQLite Query

```
Node name: Query Tasks
Operation: executeQuery
Database path: ~/.drewgent/state/drewgent_tasks.db

Query:
SELECT
  id,
  title,
  status,
  assignee,
  created_at,
  last_heartbeat_at,
  consecutive_failures,
  last_failure_error
FROM tasks
WHERE board = 'default'
ORDER BY
  CASE status
    WHEN 'todo' THEN 1
    WHEN 'ready' THEN 2
    WHEN 'in_progress' THEN 3
    WHEN 'blocked' THEN 4
    WHEN 'completed' THEN 5
  END,
  priority ASC NULLS LAST,
  created_at DESC
LIMIT 50
```

### Node 2: Code (Build Discord Embed)

```javascript
// Group tasks by status
const groups = {
  todo: [],
  ready: [],
  in_progress: [],
  blocked: [],
  completed: []
};

for (const task of $input.all()) {
  const row = task.json;
  if (groups[row.status]) {
    groups[row.status].push(row);
  }
}

const statusEmoji = {
  todo: '🟡',
  ready: '⚪',
  in_progress: '🔵',
  blocked: '🔴',
  completed: '✅'
};

const statusColor = {
  todo: 16776960,     // YELLOW
  ready: 10000000,    // WHITE/DIM
  in_progress: 3447003,  // BLUE
  blocked: 15105570,  // RED
  completed: 3066993   // GREEN
};

let description = '';
for (const [status, tasks] of Object.entries(groups)) {
  if (tasks.length === 0) continue;
  description += `**${statusEmoji[status]} [${status}]** ${tasks.length} tasks\n`;
  for (const t of tasks) {
    const heartbeat = t.last_heartbeat_at
      ? `\n    └ 💓 ${t.last_heartbeat_at.slice(11, 16)}`
      : '';
    description += `  \`${t.id.slice(-8)}\` — ${t.title.slice(0, 60)}${heartbeat}\n`;
  }
  description += '\n';
}

const embed = {
  title: '📋 Drewgent Kanban Board',
  description,
  color: 3447003,
  footer: {
    text: 'React: ✅ complete | 🔄 unblock | ❌ block | 🔁 claim'
  },
  timestamp: new Date().toISOString()
};

return [{ json: embed }];
```

### Node 3: Discord Post/Edit Message

```
Node: Discord API v2
Operation: editMessage (by message_id)

Channel: 1492883985473208522
Message ID: (from previous board message ID stored in n8n variable)

Body: {{ $json }}
```

### Node 4: Store Message ID (for next poll)

```
Node: n8n-nodes-base.set
Set: kanban_board_message_id = {{ $response.id }}
```

---

## Reaction → Action Workflow

### Trigger: Discord Reaction Add

```
Intents: GUILD_MESSAGES, MESSAGE_REACTION_ADD
Event: message_id matches board message ID
```

### Node 1: Discord Reaction Event

```json
{
  "emoji": "{{ $Trigger.event.emoji.name }}",
  "user_id": "{{ $Trigger.event.user_id }}",
  "message_id": "{{ $Trigger.event.message_id }}",
  "channel_id": "{{ $Trigger.event.channel_id }}"
}
```

### Node 2: Extract Task ID (parse board message)

```
Node: Code
Parse the board message content to extract task IDs from code blocks (t_abc123)

const messageText = $input.first().json.content;
// Find all t_<hex> patterns
const taskIds = messageText.match(/t_[0-9a-f]{8}/g);
return taskIds.map(id => ({ json: { task_id: id } }));
```

### Node 3: Switch (Emoji → Action)

| Emoji | Action | SQL Operation |
|--------|--------|---------------|
| ✅ | kanban_complete | UPDATE tasks SET status='completed' WHERE id=? |
| 🔄 | kanban_unblock | UPDATE tasks SET status='ready' WHERE id=? AND status='blocked' |
| ❌ | kanban_block | UPDATE tasks SET status='blocked' WHERE id=? |
| 🔁 | kanban_claim | UPDATE tasks SET status='in_progress' WHERE id=? |

### Node 4: Log event

```sql
INSERT INTO task_events (task_id, kind, payload, created_at)
VALUES (?, 'notification', '{"action": "discord_reaction", "emoji": "✅"}', datetime('now'))
```

---

## DrewgentTasks DB Path

```
~/.drewgent/state/drewgent_tasks.db
```

Absolute path (for n8n SQLite node):
```
/Users/drew/.drewgent/state/drewgent_tasks.db
```

---

## Environment Variables (.env)

```bash
# Drewgent
DREWAGENT_HOME=/Users/drew/.drewgent
DREWAGENT_DB=/Users/drew/.drewgent/state/drewgent_tasks.db

# Discord
DISCORD_BOT_TOKEN=your_bot_token_here
DISCORD_WEBHOOK_KANBAN=https://discord.com/api/webhooks/...
DISCORD_CHANNEL_KANBAN=1492883985473208522

# Optional
KANBAN_BOARD_MESSAGE_ID=  (set by n8n after first post)
```

---

## kanban_notify_subs Schema

```sql
CREATE TABLE IF NOT EXISTS kanban_notify_subs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id     TEXT NOT NULL,
    platform    TEXT NOT NULL,  -- 'discord', 'telegram'
    chat_id     TEXT NOT NULL,
    thread_id   TEXT,
    subscriber  TEXT NOT NULL,  -- user_id or channel_id
    created_at  TEXT NOT NULL,
    UNIQUE(task_id, platform, chat_id, subscriber)
);

CREATE INDEX IF NOT EXISTS idx_notify_task ON kanban_notify_subs(task_id);
```

### Subscribe via Discord reaction

When user reacts 🔔 to a task completion notification, insert:

```sql
INSERT INTO kanban_notify_subs (task_id, platform, chat_id, subscriber, created_at)
VALUES ('t_abc123', 'discord', '1492883985473208522', 'user_123', datetime('now'))
```

---

## Error Handling

1. **SQLite connection fail**: Retry 3x with exponential backoff, then alert via Discord
2. **Discord API rate limit**: Respect 429 responses, backoff 5 min
3. **Invalid task_id from reaction**: Log warning, skip action, do not crash workflow
4. **Missing kanban_board_message_id**: Post new message instead of edit

---

## Testing the Workflow

```bash
# Manual trigger via n8n test panel
# 1. Set cron to fire immediately
# 2. Check Discord channel for board embed
# 3. React with ✅ to a task
# 4. Verify task status changes in DB

# Query DB to verify
sqlite3 ~/.drewgent/state/drewgent_tasks.db "
SELECT id, status, last_failure_error
FROM tasks
WHERE board='default'
ORDER BY created_at DESC LIMIT 5;"
```
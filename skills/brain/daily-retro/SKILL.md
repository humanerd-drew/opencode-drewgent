---
title: Daily Retro
name: daily-retro
type: document
space: concept
description: "매일 Discord로 작업 요약 + 회고 질문 발신, 사용자 답변을 vault에 구조화하여 저장. 30/70 rule 적용."
tags: [retro, human-zone, taste, reflection, vault]
  session: "2026-06-14 taste-discussion"
  decision: "Pratik '30x Engineer' 30/70 rule 적용 — 인간이 직접 회고, agent가 정리/저장"
created: 2026-06-14
---

# Daily Retro — 30% Human Zone

## Concept

From the "How to Be a 30x AI Engineer with a Taste" framework: the 30% of work that humans should do directly is the part where **quality judgment matters most**. The daily retro is that 30% applied to reflection and direction-setting.

The agent handles the mechanical part (summarizing the day, sending prompts, storing results). The human handles the judgment part (evaluating decisions, setting direction, identifying what matters).

## Architecture

```
cron job (daily at scheduled time)
  ↓
Phase 1: Agent gathers today's work summary from kanban + recent sessions
  ↓ Discord deliver
User reads summary + answers 3 reflection questions in Discord
  ↓ Discord reply
Phase 2: Agent structures answers into vault, links to related tasks
  ↓
P2-hippocampus/retro/YYYY-MM-DD.md (wikilink chain)
```

## Phase 1 — Daily Cron Job

### Channel

- **Discord channel**: `#growth` (ID: `1492431680269713558`)
- 설정: `deliver="discord:1492431680269713558"`

### Setup

```python
cronjob(
    action="create",
    name="daily-retro",
    schedule="0 20 * * *",  # daily at 20:00 KST
    prompt="""Run the daily retro workflow:
1. Query kanban for tasks completed today (status='done')
2. Check recent session activity
3. Format a concise work summary
4. Send the retro prompt with 3 questions to the user""",
    skills=["daily-retro"],
    deliver="discord:<channel-id>",
)
```

### What the message includes

```
━━━ 오늘 작업 요약 ━━━
• [task 1] — completed
• [task 2] — completed
• [key decision] — made

━━━ 오늘의 회고 ━━━
1. 오늘 가장 taste가 필요했던 결정은?
2. 내가(agent) 개선할 점이나 다르게 했으면 하는 것은?
3. 내일 집중할 한 가지는?
```

### 3 default questions

1. **Taste decision**: "오늘 가장 taste가 필요했던 결정은?"
2. **Agent improvement**: "내가(agent) 개선할 점이나 다르게 했으면 하는 것은?"
3. **Focus**: "내일 집중할 한 가지는?"

These can be customized per user preference. Store custom questions in memory.

## Phase 2 — Processing the Reply

When the user replies in Discord, the agent receives it in a normal session and must:

1. **Acknowledge receipt** briefly
2. **Structure the response** into vault format
3. **Store in vault** with cluster conventions

### Vault File Format

**Path:** `P2-hippocampus/retro/YYYY-MM-DD.md`

```markdown
---
title: "Daily Retro YYYY-MM-DD"
type: retro
tags: [retro, YYYY-MM]
created: YYYY-MM-DD
links:
  - "[[retro/YYYY-MM-DD-before]]"
  - "[[retro/YYYY-MM-DD-after]]"
  - "[[@identity/brain/rules]]"provenance:
  session: "YYYY-MM-DD daily retro"
  trigger: "scheduled daily retro"
---

# Daily Retro — YYYY-MM-DD

## Today's Work
- [summary from cron job]

## Reflection

### 가장 taste가 필요했던 결정
[user's answer]

### Agent 개선점
[user's answer]

### 내일 집중할 한 가지
[user's answer]

## Related Tasks
- [[kanban-task-id]]
```

### Cluster Convention

- **Directory**: `P2-hippocampus/retro/`
- **Wikilink chain**: each retro links to the previous and next day
- **Tags**: `#retro` + `#YYYY-MM` for monthly grouping
- **INDEX.md**: `P2-hippocampus/retro/INDEX.md` lists all retros with tags for Obsidian graph discovery

### INDEX.md format

```markdown
---
title: "Retro Index"
type: index
tags: [retro, index]
---

# Daily Retro Archive

| Date | Summary |
|------|---------|
| [[retro/YYYY-MM-DD]] | Brief highlight |
```

## Pitfalls

**Cron job has no context of today's conversations.** It only has access to kanban board, session search (historical), and filesystem. It cannot know what was discussed in current sessions. Work summary will be kanban-based only.

**Two-phase handoff is async.** The cron job sends the message and exits. The user may reply hours later or in a different session. The agent processing the reply may not have the cron job's context. The retro skill + vault convention is the bridge.

**User may skip a day.** Don't nag. If no reply arrives by next day's cron, the new message replaces the old one. The skipped day gets no retro file.

**Timezone matters.** The cron schedule is in the user's local timezone (KST UTC+9). All timestamps in the vault file should be KST.

**Discord channel must allow agent messages.** The cron job's `deliver` field needs a channel where the agent's bot has write permission. `free_response_channels` config may be needed if the channel doesn't use @mention.

## Related

- [[@action/]] — incidents and long-term reflection
- [[@memory/]] — memory storage layer
- [[kanban-orchestrator]] — provenance + leverage score conventions for task creation
- AGENTS.md — tiered autonomy framework

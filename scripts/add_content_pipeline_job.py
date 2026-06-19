#!/usr/bin/env python3
import json

with open('/Users/drew/.drewgent/cron/jobs.json') as f:
    data = json.load(f)

prompt_text = """Content Pipeline — gather content from Activity Logger, Trend Harvester, and SEO results; create content board kanban tasks for draft writing.

Steps:
1. Check recent Activity Logger outputs (~last 3h sessions)
2. Check Trend Harvester results: ls -t ~/.drewgent/P4-cortex/growth/trend-harvester/analyzed/keep/ | head -3
3. Check SEO Harvester report: cat ~/.drewgent/P2-hippocampus/knowledge/seo-articles/report.json 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); [print(f'- {i[\"title\"]} ({i[\"keyword\"]}) score={i.get(\"score\",0):.2f}') for i in d.get('articles',[])]"
4. Select up to 3 topics (1 from each source if available)
5. For each topic: kanban_create(title=f"[draft-{type}] {topic_title}", body=context, board="content", trigger_source="content_pipeline", priority=1, idempotency_key=f"{YYYY-MM-DD}-{slug}")
6. Report: topics_selected=N tasks_created=N

If no topics found: respond with [SILENT]

If topics found: output this delivery format:
## Content Pipeline — YYYY-MM-DD HH:MM KST

Topics selected: N (task created)

| # | Source | Topic | Task ID | Draft File |
|---|--------|-------|---------|------------|
| 1 | trend | {title} | {id} | pending |
| 2 | seo | {title} | {id} | pending |
| 3 | conversation | {title} | {id} | pending |

Draft files are written to: ~/.drewgent/P2-hippocampus/memories/insights/
Worker will deliver the file path via kanban_complete result when draft is ready.

---

Phase 5: Periodic Delivery (completed drafts in last 72h)

import sqlite3, os, re
DB = os.path.expanduser("~/.drewgent/P2-hippocampus/kanban/state/drewgent_tasks.db")
conn = sqlite3.connect(DB)
rows = conn.execute("""
SELECT id, title, result, completed_at
FROM tasks
WHERE trigger_source = 'content_pipeline'
AND board = 'content'
AND status = 'completed'
AND completed_at > datetime('now', '-72 hours')
ORDER BY completed_at DESC
""").fetchall()
conn.close()

drafts = []
for task_id, title, result, completed_at in rows:
    match = re.search(r'memories/insights/(20\d{2}-\d{2}-[^.]+\.md)', result or '')
    if match:
        draft_path = os.path.expanduser(f"~/.drewgent/P2-hippocampus/memories/insights/{match.group(1)}")
        drafts.append((title, task_id, draft_path))

if drafts:
    print("Draft files ready for review:")
    for i, (title, tid, path) in enumerate(drafts, 1):
        print(f"  {i}. {title} | {tid} | {path}")

else:
    print("No completed drafts in last 72h.")


---

Final delivery format:
## Content Pipeline — YYYY-MM-DD HH:MM KST

Draft files ready for review:

| # | Topic | Task ID | Draft File |
|---|-------|---------|------------|
| 1 | {title} | {id} | ~/.drewgent/P2-hippocampus/memories/insights/{filename}.md |

Review at: Obsidian -> P2-hippocampus/memories/insights/

If no completed drafts: [SILENT]"""

job = {
    "id": "content-pipeline-run",
    "name": "content-pipeline",
    "prompt": prompt_text,
    "skills": ["content-pipeline"],
    "skill": None,
    "schedule": {"kind": "cron", "expr": "0 */3 * * *"},
    "enabled": True,
    "state": "scheduled",
    "timeout_seconds": 1800,
    "deliver": "local",
    "retry_on_failure": True,
    "fallback_delivery": True,
    "failure_count": 0
}

data['jobs'].append(job)

with open('/Users/drew/.drewgent/cron/jobs.json', 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

# Verify
with open('/Users/drew/.drewgent/cron/jobs.json') as f:
    d2 = json.load(f)
job2 = next(j for j in d2['jobs'] if j['name'] == 'content-pipeline')
print("SUCCESS! deliver:", job2['deliver'])
print("skills:", job2['skills'])
print("schedule:", job2['schedule'])
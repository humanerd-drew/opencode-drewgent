import json
import os
from pathlib import Path

DREW_HOME = Path(os.environ.get("DREW_HOME", Path.home() / ".drewgent"))
jobs_path = DREW_HOME / "cron" / "jobs.json"

with jobs_path.open() as f:
    data = json.load(f)

job = next(j for j in data['jobs'] if j['name'] == 'content-pipeline')

new_prompt = r'''Content Pipeline — gather content from Activity Logger, Trend Harvester, and SEO results; create content board kanban tasks for draft writing.

Editorial North Star:
humanerd.kr is not an automated news blog. It is Drew's public workshop for showing how he thinks and builds through AI, tools, code, writing, and systems.

Only create a content task when the topic satisfies:
public-worthy content = 기록 + 해석 + 재사용 가능한 통찰

Default outcome is 0 topics. If candidates are weak, respond with [SILENT].

Steps:
1. Check Trend Harvester: ls -t ~/.drewgent/P4-cortex/growth/trend-harvester/analyzed/keep/*.json | head -10
   Parse JSON: item{name,description,url,source}, total_score, decision
   Filter: decision == "keep", scored_at 최근 48시간, 상위 5개

2. Check SEO Harvester: cat ~/.drewgent/P2-hippocampus/knowledge/seo-articles/report.json
   Filter: score >= 0.7, keyword 명확한 것 상위 3개

3. Check Activity Logger (kanban): query drewgent_tasks.db
   SELECT title, body FROM tasks WHERE trigger_source='activity_logger' AND status='completed' AND created_at > datetime('now','-24 hours') ORDER BY created_at DESC LIMIT 10

4. Select up to 3 topics (1 from each source if available)
   Prefix rules: [draft-trend], [draft-seo], [draft-conversation]

   Editorial Gate: score every candidate 0-10. Create a task only if score >= 7.
   Criteria, 0-2 each:
   - Drew-angle: connected to Drew's work, tools, judgment, or portfolio
   - Insight: offers a reusable principle, not just a summary
   - Evidence: has source plus concrete context or artifact
   - Portfolio value: still meaningful in 6 months
   - Specificity: includes a concrete case, decision, failure, system, or tool

   Auto-reject:
   - simple product/tool launch summaries
   - outside trends Drew has not used or interpreted
   - SEO-only topics with no point of view
   - duplicated claims from the last 30 days
   - generic "AI is powerful/risky" commentary

   Priority: conversation insight > Drewgent/humanerd-related trend > evergreen SEO.

5. For each topic: kanban_create(
   title=f"[draft-{type}] {topic_title}",
   body="""## Topic
{topic_description}

## Editorial Decision
- score: {score}/10
- publish_intent: blog | insight | portfolio | archive
- Drew-angle: {why_this_matters_to_drew}
- reusable_insight: {one_sentence_reader_value}
- reject_if_missing: if this cannot show Drew's judgment, archive instead of drafting

## Content Source
- source: {source_name}
- collected_at: {YYYY-MM-DD HH:MM}

## 글쓰기 방향
- 톤: writing-style-guide.md hybrid approach
  - 톤: 휴머너드 말투 (긴 플로우, Bold 강조, "당신" 직접호칭, 1인칭 "저"/"나")
  - SEO: aliases, 해시태그, SEO 키워드 섹션
- 제목: 질문 또는 provocative statement
- 도입: Bold 훅 한 문장 -> 10~20문장 플로우

## Frontmatter
title: {title}
type: document
space: concept
tags: [blog, {category}]
aliases: ['/blog/{slug}']
created: {YYYY-MM-DD}
status: draft

## 작성 시 반드시 확인할 것
1. forbidden.patterns grep -> 0건
2. Bold 섹션 강조 2~4개 존재
3. "당신" 직접호칭 + 1인칭 "저"/"나" 포함
4. 본문 날짜 (X월 X일) 없음
5. SEO 키워드 3~7개, 해시태그 8~14개
6. aliases in frontmatter
7. 기록 + 해석 + 재사용 가능한 통찰이 모두 있음

## Draft 파일 위치
memories/insights/YYYY-MM-{slug}.md
예: memories/insights/2026-05-{slug}.md
   """,
   board="content",
   trigger_source="content_pipeline",
   priority=1,
   idempotency_key=f"{YYYY-MM-DD}-{slug}"
)

If no topics found: respond with [SILENT]

---

Phase 3 Delivery Format (task created):

## Content Pipeline — YYYY-MM-DD HH:MM KST

Topics selected: N (task created)

| # | Source | Topic | Task ID | Draft File |
|---|--------|-------|---------|------------|
| 1 | trend | {title} | {id} | /Users/drew/.drewgent/P2-hippocampus/memories/insights/{YYYY-MM}-{slug}.md |
| 2 | seo | {title} | {id} | /Users/drew/.drewgent/P2-hippocampus/memories/insights/{YYYY-MM}-{slug}.md |
| 3 | conversation | {title} | {id} | — (in progress) |

Worker 배분: kanban-dispatcher-content가 5분마다 ready task를 worker에 배분
Review at: Obsidian -> P2-hippocampus -> memories -> insights

Topics selected=0이면 [SILENT].

---

Periodic Delivery — completed drafts in last 72h:

python3 -c "
import sqlite3, os, re, glob

DB = os.path.expanduser('~/.drewgent/P2-hippocampus/kanban/state/drewgent_tasks.db')
INSIGHTS = os.path.expanduser('~/.drewgent/P2-hippocampus/memories/insights/')
conn = sqlite3.connect(DB)
rows = conn.execute("""
    SELECT id, title, body, completed_at
    FROM tasks
    WHERE trigger_source = \"content_pipeline\"
      AND board = \"content\"
      AND status = \"completed\"
      AND completed_at > datetime(\"now\", \"-72 hours\")
    ORDER BY completed_at DESC
""").fetchall()
conn.close()

drafts = []
for task_id, title, body, completed_at in rows:
    draft_path = '— (path not recorded)'
    if body:
        m = re.search(r'P2-hippocampus/memories/insights/(\d{4}-\d{2}-[^/]+\\.md)', body)
        if m:
            draft_path = os.path.join(INSIGHTS, m.group(1))
            if not os.path.exists(draft_path):
                date_prefix = m.group(1)[:7]
                matches = glob.glob(os.path.join(INSIGHTS, f'{date_prefix}-*.md'))
                draft_path = max(matches, key=os.path.getmtime) if matches else f'~/.drewgent/P2-hippocampus/memories/insights/{m.group(1)}'
    drafts.append((title, task_id, draft_path))

if drafts:
    print('Draft files ready for review:')
    for i, (title, tid, path) in enumerate(drafts, 1):
        print(f'  {i}. {title} | {tid} | {path}')
else:
    print('No completed drafts in last 72h.')
"

---

Final delivery format:

## Content Pipeline Update — YYYY-MM-DD HH:MM KST

Draft files ready for review:

| # | Topic | Task ID | Draft File |
|---|-------|---------|------------|
| 1 | {title} | {id} | /Users/drew/.drewgent/P2-hippocampus/memories/insights/{filename}.md |

Review at: Obsidian -> P2-hippocampus -> memories -> insights

If no completed drafts: [SILENT]
'''

job['prompt'] = new_prompt

with jobs_path.open('w') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

# Verify
with jobs_path.open() as f:
    data2 = json.load(f)
job2 = next(j for j in data2['jobs'] if j['name'] == 'content-pipeline')
print("Updated prompt length:", len(job2['prompt']))
print("Phase 3 delivery format present:", "— (in progress)" in job2['prompt'])
print("Absolute path present:", "/Users/drew/.drewgent/P2-hippocampus/memories/insights/" in job2['prompt'])
print("body-based regex present:", "P2-hippocampus/memories/insights/" in job2['prompt'])
print("Review at format present:", "Obsidian -> P2-hippocampus -> memories -> insights" in job2['prompt'])

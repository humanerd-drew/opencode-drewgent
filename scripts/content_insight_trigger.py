"""
content-insight-trigger: 누적 데이터에서 인사이트 발굴 → kanban content task
Mon/Thu 10:00 KST. Reads evaluated/applied items, finds cross-cutting themes.
"""
import json, os, time, sqlite3, uuid
from datetime import datetime
from collections import Counter

HOME = os.environ.get('HOME', '/Users/drew')
KANBAN_DB = os.path.join(HOME, '.drewgent/kanban.db')
KEEP_DIR = os.path.join(HOME, '.drewgent/@memory/growth/trend-harvester/analyzed/keep')
EVAL_DIR = os.path.join(HOME, '.drewgent/@memory/growth/trend-harvester/evaluated')
NOW = int(time.time())
TODAY = datetime.now().strftime('%Y-%m-%d')

WRITING_GUIDE = """## Writing Format (Critical)
- Gutenberg HTML blocks only
- Korean, 반말+1인칭. Hook-first opening
- Structure: Pattern → Insight → Application
- Bold for key sentences. Mermaid diagrams for architecture/flow
- SVG cover: 1200x630, dark theme
- NO raw Markdown, NO YAML frontmatter
- WordPress MCP: create_post(status=publish), category="AI & Tools" or "Systems"
- After publish: update narrative_arc.md + content-inventory.md
- This is an ANALYSIS post — connect dots across multiple tools/patterns"""


def kanban_insert(title, body_lines):
    body = '\n'.join(body_lines)
    tid = str(uuid.uuid4()).upper()
    try:
        conn = sqlite3.connect(KANBAN_DB)
        conn.execute('INSERT INTO tasks (id, title, body, status, priority, created_at) VALUES (?,?,?,?,?,?)',
                     (tid, title, body, 'todo', 2, NOW))
        conn.commit()
        conn.close()
        print(f'created:{tid}')
        return True
    except Exception as e:
        print(f'error:{e}')
        return False


def check_dir(path):
    try:
        return sorted(os.listdir(path), key=lambda f: os.path.getmtime(os.path.join(path, f)), reverse=True)
    except Exception:
        return []


def read_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def extract_tags(d):
    details = d.get('details')
    if isinstance(details, dict):
        return details.get('tags', details.get('categories', []))
    if isinstance(details, list):
        return details
    return []


# Read evaluated + keep items, find patterns
all_items = []
names_seen = set()

for fn in check_dir(EVAL_DIR)[:20]:
    d = read_json(os.path.join(EVAL_DIR, fn))
    if not d:
        continue
    item = d.get('item', {})
    name = item.get('name', '') if isinstance(item, dict) else str(item)
    if name in names_seen:
        continue
    names_seen.add(name)
    all_items.append({
        'name': name,
        'tags': extract_tags(d),
        'score': d.get('total_score', 0),
        'decision': d.get('decision', ''),
    })

# Also check keep items for high-scorers not yet evaluated
for fn in check_dir(KEEP_DIR)[:30]:
    d = read_json(os.path.join(KEEP_DIR, fn))
    if not d:
        continue
    item = d.get('item', {})
    name = item.get('name', '') if isinstance(item, dict) else str(item)
    if name in names_seen:
        continue
    names_seen.add(name)
    score = d.get('total_score', 0)
    if score >= 6.5:
        all_items.append({
            'name': name,
            'tags': extract_tags(d),
            'score': score,
            'decision': 'pending-evaluation',
        })

if len(all_items) < 3:
    print('silent')
else:
    # Tag frequency for pattern detection
    all_tags = []
    for it in all_items:
        all_tags.extend(it['tags'])
    tag_freq = Counter(all_tags)
    top_tags = [t for t, c in tag_freq.most_common(5) if c >= 2]

    title = f'content-insight: {TODAY}'
    body = [
        f'# Content Task: Insight Pipeline — {TODAY}',
        '',
    ]

    if top_tags:
        body += [
            f'**Emerging patterns**: {", ".join(top_tags)}',
            '',
        ]

    body += [
        f'**Items in scope**: {len(all_items)}',
        '',
        '## Brief',
        'Read through the items below and find a cross-cutting theme. Write an analytical blog post that connects 3-5 items into a coherent insight about AI tooling, agent architecture, or engineering taste. This is not a summary of each tool — it\'s a synthesis. What pattern emerges when you look at all of them together?',
        '',
        '## Candidate Items',
        '',
    ]

    for it in all_items[:10]:
        body.append(f"- **{it['name']}** (score: {it['score']}, {it['decision']})")
        if it['tags']:
            body.append(f"  tags: {', '.join(it['tags'][:3])}")

    body += ['', WRITING_GUIDE]
    kanban_insert(title, body)

"""
content-news-trigger: 최신 트렌드/뉴스 → kanban content task
Daily 08:00 KST. Checks latest trend keep + SEO articles for fresh material.
"""
import json, os, time, sqlite3, uuid
from datetime import datetime, timedelta

HOME = os.environ.get('HOME', '/Users/drew')
KANBAN_DB = os.path.join(HOME, '.drewgent/kanban.db')
KEEP_DIR = os.path.join(HOME, '.drewgent/@memory/growth/trend-harvester/analyzed/keep')
NOW = int(time.time())
TODAY = datetime.now().strftime('%Y-%m-%d')
YESTERDAY = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
CUTOFF_TS = NOW - 86400  # 24h

WRITING_GUIDE = """## Writing Format (Critical)
- Gutenberg HTML blocks only (`<!-- wp:paragraph -->...<!-- /wp:paragraph -->`)
- Korean, 반말+1인칭 ("나", "저"). 독자에게 "당원"으로 직접 말함
- Hook-first opening: 짧고 강한 문장으로 시작
- Structure: Problem → Decision → Build Path
- Bold (<strong>) for key sentences
- SVG cover: 1200x630, dark theme (#0d0d1a → #1a1a30 gradient), amber/blue/teal accent
- NO raw Markdown, NO YAML frontmatter
- WordPress MCP: create_post(status=publish), category="AI & Tools"
- After publish: update narrative_arc.md + content-inventory.md"""


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


# Get recent keep items (last 24h)
keep_files = check_dir(KEEP_DIR)
news_items = []
for fn in keep_files[:20]:
    fp = os.path.join(KEEP_DIR, fn)
    if os.path.getmtime(fp) < CUTOFF_TS:
        break
    d = read_json(fp)
    if d and d.get('total_score', 0) >= 5.0:
        item = d.get('item', {})
        if isinstance(item, dict):
            name = item.get('name', item.get('title', fn))
            desc = item.get('description', '')
            url = item.get('url', item.get('html_url', ''))
        else:
            name = str(item)
            desc = d.get('description', '')
            url = d.get('url', '')
        news_items.append({
            'name': name, 'desc': desc, 'url': url,
            'score': d.get('total_score', 0),
            'tags': d.get('details', {}).get('tags', []) if isinstance(d.get('details'), dict) else [],
        })

if not news_items:
    print('silent')
else:
    detail_lines = []
    for it in news_items[:3]:
        detail_lines.append(f"- **{it['name']}** (score: {it['score']})")
        if it['desc']:
            detail_lines.append(f"  {it['desc'][:200]}")

    title = f'content-news: {TODAY}'
    body = [
        f'# Content Task: News Pipeline — {TODAY}',
        '',
        f'**Source**: Trend Harvester keep items (last 24h)',
        f'**Count**: {len(news_items)} fresh items found',
        '',
        '## Brief',
        'Pick the most newsworthy item(s) above. Write a short, timely blog post that connects the tool/topic to how I think about AI engineering. Think "X thread that became a blog post" — fast, opinionated, personal.',
        '',
        '## Candidate Items',
        '',
    ] + detail_lines + ['', WRITING_GUIDE]

    kanban_insert(title, body)

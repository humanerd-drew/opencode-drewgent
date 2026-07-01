"""
content-series-trigger: 시리즈 기획 → kanban content task
Weekly Mon 09:00 KST. Reads narrative_arc.md, plans next episode.
"""
import json, os, time, re, sqlite3, uuid
from datetime import datetime

HOME = os.environ.get('HOME', '/Users/drew')
KANBAN_DB = os.path.join(HOME, '.drewgent/kanban.db')
NARRATIVE_FILE = os.path.join(HOME, '.drewgent/P4-cortex/content/narrative_arc.md')
INVENTORY_FILE = os.path.join(HOME, '.drewgent/P4-cortex/content/content-inventory.md')
NOW = int(time.time())
TODAY = datetime.now().strftime('%Y-%m-%d')

WRITING_GUIDE = """## Writing Format (Critical)
- Gutenberg HTML blocks only
- Korean, 반말+1인칭. Hook-first opening
- Structure: Context → Problem → Decision → Build → Reflection
- Bold for key sentences. Mermaid + SVG architecture diagrams
- SVG cover: 1200x630, dark theme
- NO raw Markdown, NO YAML frontmatter
- WordPress MCP: create_post(status=publish), category per episode theme
- MUST update narrative_arc.md with new episode entry after publish
- MUST update content-inventory.md
- This is a SERIES episode — link to previous episodes in the chain"""


def kanban_insert(title, body_lines):
    body = '\n'.join(body_lines)
    tid = str(uuid.uuid4()).upper()
    try:
        conn = sqlite3.connect(KANBAN_DB)
        conn.execute('INSERT INTO tasks (id, title, body, status, priority, created_at) VALUES (?,?,?,?,?,?)',
                     (tid, title, body, 'todo', 3, NOW))
        conn.commit()
        conn.close()
        print(f'created:{tid}')
        return True
    except Exception as e:
        print(f'error:{e}')
        return False


# Read narrative_arc.md
narrative = ""
try:
    with open(NARRATIVE_FILE) as f:
        narrative = f.read()
except Exception:
    pass

# Read content-inventory for recent posts
inventory = ""
try:
    with open(INVENTORY_FILE) as f:
        inventory = f.read()
except Exception:
    pass

if not narrative:
    print('silent')
else:
    # Extract current season and recent episodes
    seasons = re.findall(r'## Season \d+.*?(?=## Season|\Z)', narrative, re.DOTALL)
    current_season = seasons[-1] if seasons else narrative

    # Find planned but unwritten episodes
    planned = re.findall(r'- \[ \] .+', current_season)
    written = re.findall(r'- \[x\] .+', current_season)

    title = f'content-series: {TODAY}'
    body = [
        f'# Content Task: Series Pipeline — {TODAY}',
        '',
        '## Narrative Arc Context',
        f'```\n{narrative[:2000]}\n```',
        '',
    ]

    if planned:
        body += [
            '## Planned Episodes (Unwritten)',
            '',
        ] + [f'- {ep}' for ep in planned[:5]] + ['']

    if written:
        body += [
            '## Published Episodes',
            '',
        ] + [f'- {ep}' for ep in written[-5:]] + ['']

    body += [
        '## Brief',
        'Read the narrative arc context above. Identify the next episode to write — either a planned but unwritten episode, or a new episode that fills a gap in the current season.',
        '',
        'Write ONE series episode that advances the narrative arc. Each episode should:',
        '- Stand alone (new readers can start here)',
        '- Link to previous episodes',
        '- Advance the season\'s theme',
        '- End with a teaser for the next episode',
        '',
        'After writing:',
        '1. Mark episode as [x] in narrative_arc.md',
        '2. Add new episode entry',
        '3. Update content-inventory.md',
        '',
        WRITING_GUIDE,
    ]

    kanban_insert(title, body)

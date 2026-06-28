import json, os, time, sqlite3, uuid

HOME = os.environ.get('HOME', '/Users/drew')
TRIGGER = os.environ.get('N8N_TRIGGER_TYPE', '')
KANBAN_DB = os.path.join(HOME, '.drewgent/kanban.db')
TODAY = time.strftime('%Y-%m-%d')
NOW_TS = int(time.time())


def kanban_insert(title, body_lines):
    body = '\n'.join(body_lines) if body_lines else ''
    tid = str(uuid.uuid4()).upper()
    try:
        conn = sqlite3.connect(KANBAN_DB)
        conn.execute(
            'INSERT INTO tasks (id, title, body, status, priority, created_at) VALUES (?, ?, ?, ?, ?, ?)',
            (tid, title, body, 'todo', 1, NOW_TS)
        )
        conn.commit()
        conn.close()
        print(f'created:{tid}')
        return True
    except Exception as e:
        print(f'error:{e}')
        return False


def check_dir(path):
    try:
        return [f for f in os.listdir(path) if f.endswith('.json')]
    except Exception:
        return []


def check_dir_files(path):
    try:
        return os.listdir(path)
    except Exception:
        return []


if TRIGGER == 'trend-evaluate':
    keep_dir = os.path.join(HOME, '.drewgent/@memory/growth/trend-harvester/analyzed/keep')
    ev_dir = os.path.join(HOME, '.drewgent/@memory/growth/trend-harvester/evaluated')
    keep = check_dir(keep_dir)
    ev = check_dir(ev_dir)
    new_items = [f for f in keep if f not in set(ev)]
    if new_items:
        preview = []
        for fn in new_items[:3]:
            fp = os.path.join(keep_dir, fn)
            try:
                with open(fp) as f:
                    d = json.load(f)
                item = d.get('item', {})
                if isinstance(item, dict):
                    name = item.get('name', item.get('title', fn))
                else:
                    name = str(item)
                preview.append(f"- {name} (score: {d.get('total_score', '?')})")
            except Exception:
                preview.append(f"- {fn}")
        title = f'trend-evaluate: {TODAY}'
        body = [f'Keep items to evaluate: {len(new_items)} new', ''] + preview
        kanban_insert(title, body)
    else:
        print('silent')

elif TRIGGER == 'trend-retire':
    rpt_path = os.path.join(HOME, '.drewgent/@memory/growth/trend-harvester/.usage_report.json')
    try:
        with open(rpt_path) as f:
            rpt = json.load(f)
        stale = rpt.get('stale_items', rpt.get('stale_count', 0))
        if stale:
            items = rpt.get('items', [])
            stale_list = [i for i in items if i.get('status') == 'stale']
            title = f'trend-retire: {TODAY}'
            body = [f'Stale items to retire: {len(stale_list)}', '']
            for it in stale_list[:5]:
                body.append(f"- {it.get('name', '?')}")
            kanban_insert(title, body)
        else:
            print('silent')
    except Exception:
        print('silent')

elif TRIGGER == 'taste-review':
    keep_dir = os.path.join(HOME, '.drewgent/@memory/growth/trend-harvester/analyzed/keep')
    ap_dir = os.path.join(HOME, '.drewgent/@memory/growth/trend-harvester/applied')
    keep = check_dir(keep_dir)
    ap = check_dir(ap_dir)
    new_items = [f for f in keep if f not in set(ap)]
    if new_items:
        fn = new_items[0]
        fp = os.path.join(keep_dir, fn)
        try:
            with open(fp) as f:
                d = json.load(f)
            item = d.get('item', {})
            if isinstance(item, dict):
                name = item.get('name', item.get('title', fn))
                desc = item.get('description', '')
                url = item.get('url', item.get('html_url', ''))
            else:
                name = str(item)
                desc = d.get('description', '')
                url = d.get('url', '')
            title = f'taste-review: {TODAY}'
            body = [
                f'Taste review for: {name}',
                f'Description: {desc}',
                f'URL: {url}',
                '',
                'Use the 5-question taste-review framework:',
                '1. One-Liner',
                '2. Taste decision to steal',
                '3. Architecture insight',
                '4. Drewgent applicability',
                '5. Leverage score (1-5)',
            ]
            kanban_insert(title, body)
        except Exception as e:
            print(f'error:{e}')
    else:
        print('silent')

elif TRIGGER == 'seo-analyze':
    print('noop-handled-by-analyzer-py')

elif TRIGGER == 'seo-trend':
    d = os.path.join(HOME, '.drewgent/P4-cortex/growth/seo/analyzed')
    files = check_dir_files(d)
    if files:
        title = f'seo-trend-report: {TODAY}'
        body = [f'SEO analyzed articles: {len(files)}', '']
        for fn in files[:5]:
            fp = os.path.join(d, fn)
            try:
                with open(fp) as f:
                    data = json.load(f)
                body.append(f"- {data.get('title', fn)}")
            except Exception:
                body.append(f"- {fn}")
        kanban_insert(title, body)
    else:
        print('silent')

elif TRIGGER == 'test':
    print('ok')

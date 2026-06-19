
import json, os, time

HOME = os.environ.get('HOME','/Users/drew')
TRIGGER = os.environ.get('N8N_TRIGGER_TYPE','')
TODAY = time.strftime('%Y-%m-%d')

def check_dir(path):
    try: return [f for f in os.listdir(path) if f.endswith('.json')]
    except: return []

def check_dir_files(path):
    try: return os.listdir(path)
    except: return []

if TRIGGER == 'trend-evaluate':
    keep = check_dir(os.path.join(HOME, '.drewgent/P4-cortex/growth/trend-harvester/analyzed/keep'))
    ev = check_dir(os.path.join(HOME, '.drewgent/P4-cortex/growth/trend-harvester/evaluated'))
    ni = [f for f in keep if f not in set(ev)]
    print(f'{len(ni)}' if ni else 'silent')

elif TRIGGER == 'trend-retire':
    try:
        rpt = json.load(open(os.path.join(HOME, '.drewgent/P4-cortex/growth/trend-harvester/.usage_report.json')))
        stale = rpt.get('stale_items', rpt.get('stale_count', 0))
        print(f'{stale}' if stale else 'silent')
    except: print('silent')

elif TRIGGER == 'taste-review':
    keep = check_dir(os.path.join(HOME, '.drewgent/P4-cortex/growth/trend-harvester/analyzed/keep'))
    ap = check_dir(os.path.join(HOME, '.drewgent/P4-cortex/growth/trend-harvester/applied'))
    ni = [f for f in keep if f not in set(ap)]
    print(f'{len(ni)}' if ni else 'silent')

elif TRIGGER == 'seo-analyze':
    d = os.path.join(HOME, '.drewgent/P2-hippocampus/knowledge/seo-articles')
    files = [f for f in check_dir_files(d) if f >= TODAY] if os.path.isdir(d) else []
    count = sum(len(check_dir_files(os.path.join(d, f))) for f in files) if files else 0
    print(f'{count}' if count else 'silent')

elif TRIGGER == 'seo-trend':
    d = os.path.join(HOME, '.drewgent/P4-cortex/growth/seo/analyzed')
    files = check_dir_files(d)
    print(f'{len(files)}' if files else 'silent')

elif TRIGGER == 'test':
    print('ok')

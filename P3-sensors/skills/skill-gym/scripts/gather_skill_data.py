#!/usr/bin/env python3
"""
skill-gym data gatherer
=======================
state.db + Drewgent vault에서 스킬 활용 데이터를 추출하고,
JSON으로规范化하여 stdout으로 출력합니다.

Usage:
    python3 gather_skill_data.py [--since-days N]
"""

import json
import re
import sqlite3
import sys
import random
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
DREWENT_HOME = Path.home() / ".drewgent"
SKILLS_DIR   = DREWENT_HOME / "skills"
MEMORIES_DIR = DREWENT_HOME / "memories"
STATE_DB     = DREWENT_HOME / "state.db"
MEMORY_MD    = DREWENT_HOME / "memories" / "MEMORY.md"
INDEX_MD     = DREWENT_HOME / "memories" / "index.md"

# ── Stopwords ─────────────────────────────────────────────────────────────────
STOPWORDS = {
    # Standard English
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of',
    'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
    'may', 'might', 'must', 'shall', 'can', 'this', 'that', 'these', 'those',
    'i', 'you', 'he', 'she', 'it', 'we', 'they', 'what', 'which', 'who', 'when',
    'where', 'why', 'how', 'not', 'no', 'so', 'if', 'then', 'than', 'also',
    'very', 'just', 'only', 'about', 'into', 'through', 'after', 'before',
    'between', 'under', 'over', 'again', 'more', 'most', 'some', 'any', 'all',
    'each', 'every', 'both', 'few', 'many', 'much', 'such', 'other', 'another',
    'own', 'new', 'now', 'here', 'there', 'up', 'down', 'out', 'off', 'back',
    'still', 'even', 'well', 'too', 'above', 'below', 'since', 'during',
    'while', 'until', 'because', 'without', 'against', 'per', 'among', 'within',
    'around', 'along', 'across', 'behind', 'beyond', 'toward', 'towards',
    'however', 'therefore', 'thus', 'hence', 'otherwise', 'anyway', 'besides',
    'really', 'actually', 'already', 'always', 'never', 'often',
    'sometimes', 'usually', 'probably', 'perhaps', 'maybe', 'almost', 'quite',
    'rather', 'enough', 'nearly', 'simply', 'exactly', 'especially',
    'completely', 'totally', 'absolutely', 'clearly', 'likely', 'unlikely',
    'definitely', 'certainly', 'immediately', 'finally', 'eventually',
    'currently', 'previously', 'originally', 'basically', 'generally',
    'essentially', 'directly', 'recently', 'sure', 'thing', 'things',
    'something', 'anything', 'nothing', 'everything', 'someone', 'anyone', 'everyone',
    'note', 'notes', 'folder', 'file', 'files', 'path', 'paths', 'directory',
    'year', 'month', 'day', 'week', 'today', 'yesterday', 'tomorrow', 'time',
    'name', 'names', 'type', 'case', 'use', 'used', 'using', 'make', 'made',
    'see', 'seen', 'look', 'looked', 'find', 'found', 'get', 'got',
    'give', 'given', 'take', 'taken', 'come', 'came', 'go', 'went',
    'know', 'known', 'think', 'thought', 'say', 'said', 'tell', 'told',
    'ask', 'asked', 'want', 'wanted', 'need', 'needed', 'like', 'liked',
    'try', 'tried', 'start', 'started', 'stop', 'stopped', 'call', 'called',
    'first', 'last', 'next', 'second', 'third', 'one', 'two', 'three',
    'many', 'few', 'lot', 'lots', 'bit', 'side', 'end', 'kind', 'kinds',
    'word', 'words', 'way', 'ways', 'point', 'points', 'part', 'parts',
    'well', 'work', 'works', 'working', 'worked', 'number', 'numbers',
    'work', 'works', 'workdir', 'workdirs', 'home', 'based', 'running',
    # URL / technical noise
    'https', 'http', 'com', 'org', 'net', 'io', 'dev', 'www', 'html',
    'api', 'url', 'src', 'href', 'link', 'rel', 'id', 'class', 'style',
    'div', 'span', 'body', 'head', 'title', 'meta', 'script', 'img', 'srcset',
    'cdn', 'static', 'media', 'assets', 'images', 'fonts', 'css', 'js',
    # JSON / data noise
    'null', 'none', 'true', 'false', 'string', 'boolean', 'integer',
    'array', 'object', 'key', 'value', 'default', 'required', 'optional',
    # System / logging noise
    'via', 'meas', 'measuring', 'measurement', 'output', 'outputs', 'input',
    'inputs', 'response', 'responses', 'request', 'requests', 'error', 'errors',
    'warn', 'warning', 'info', 'debug', 'trace', 'level', 'logger', 'logging',
    'final', 'tmp', 'temp', 'cache', 'cached', 'bytes', 'size', 'length',
    'count', 'total', 'sum', 'avg', 'mean', 'min', 'max', 'limit', 'offset',
    # Misc
    'friction', 'hugh-kim', 'humanerd', 'drewgent',  # too specific to user/system names
    'meas', 'conversion', 'tokens', 'token',
}

def extract_keywords(text: str, top_n: int = 30) -> list[tuple[str, int]]:
    """텍스트에서 키워드 빈도 추출"""
    words = re.findall(r'\b[a-z][a-z0-9-]{2,30}\b', text.lower())
    # 하이픈 정규화 후 stopword 체크 (hugh-kim → hughkim로 정규화해서 체크)
    filtered = []
    for w in words:
        norm = w.replace('-', '')
        if norm in STOPWORDS or w in STOPWORDS:
            continue
        if w.count('-') > 1:          # 2개 이상 하이픈: URL 패턴 등 → 제거
            continue
        filtered.append(w)
    return Counter(filtered).most_common(top_n)


def gather_project_context() -> dict:
    """Drewgent vault에서 현재 프로젝트 맥락 추출"""
    context = {
        'keywords': [],
        'sources': [],
        'sessions_summary': '',
    }

    # 1. MEMORY.md에서 키워드 추출
    if MEMORY_MD.exists():
        try:
            text = MEMORY_MD.read_text(encoding='utf-8')
            # frontmatter 제외
            text = re.sub(r'^---\n.*?\n---\n', '', text, flags=re.DOTALL)
            context['keywords'].extend(extract_keywords(text, 20))
            context['sources'].append('MEMORY.md')
        except Exception:
            pass

    # 2. index.md + insights
    insights_dir = MEMORIES_DIR / 'insights'
    if insights_dir.exists():
        for f in sorted(insights_dir.rglob('*.md'), key=lambda x: x.stat().st_mtime, reverse=True)[:5]:
            try:
                text = f.read_text(encoding='utf-8', errors='ignore')
                text = re.sub(r'^---\n.*?\n---\n', '', text, flags=re.DOTALL)
                context['keywords'].extend(extract_keywords(text, 10))
                context['sources'].append(str(f.name))
            except Exception:
                pass

    # 3. Recent session JSONL에서 최근 작업 주제 추출
    sessions_dir = DREWENT_HOME / 'sessions'
    recent_user_msgs = []
    if sessions_dir.exists():
        session_files = sorted(
            sessions_dir.glob('session_*.json'),
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )[:10]
        for sf in session_files:
            try:
                data = json.loads(sf.read_text(encoding='utf-8'))
                for msg in data.get('messages', []):
                    if msg.get('role') == 'user':
                        content = msg.get('content', '')
                        if isinstance(content, str) and len(content) > 10:
                            recent_user_msgs.append(content[:300])
            except Exception:
                pass

    # 키워드 병합
    all_kw = Counter(dict(context['keywords']))
    for msg in recent_user_msgs[:50]:
        for kw, cnt in extract_keywords(msg, 20):
            all_kw[kw] += cnt

    context['keywords'] = all_kw.most_common(40)
    context['sessions_summary'] = f"{len(recent_user_msgs)} recent user messages analyzed"
    return context


def gather_all_skills() -> dict:
    """SKILL.md 파일에서 전체 스킬 목록 + frontmatter 추출"""
    skills = {}
    skill_mds = list(SKILLS_DIR.rglob('SKILL.md'))
    
    for smd in skill_mds:
        try:
            content = smd.read_text(encoding='utf-8')
            fm_match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
            frontmatter = {}
            if fm_match:
                for line in fm_match.group(1).splitlines():
                    if ': ' in line:
                        k, v = line.split(': ', 1)
                        frontmatter[k.strip()] = v.strip()
            
            body = content[fm_match.end():] if fm_match else content
            # 첫 문단(description fallback)
            first_para = ''
            for line in body.splitlines():
                line = line.strip()
                if line and not line.startswith('#'):
                    first_para = line.strip()[:120]
                    break
            
            name = frontmatter.get('name', smd.parent.name)
            skills[name] = {
                'name': name,
                'description': frontmatter.get('description', first_para),
                'category': frontmatter.get('category', ''),
                'path': str(smd.parent.relative_to(SKILLS_DIR)),
                'tags': [t.strip() for t in frontmatter.get('tags', '').split(',') if t.strip()],
                'skill_md_size': len(content),
                'last_used': None,
                'last_used_ts': None,
                'days_ago': None,
                'call_count': 0,
            }
        except Exception as e:
            pass
    
    return skills


def get_skill_usage_from_state_db() -> dict:
    """state.db에서 skill_view/skills_list 호출 이력 추출"""
    usage = {}  # skill_name → {'ts': float, 'count': int, 'session': str}
    
    if not STATE_DB.exists():
        return usage
    
    try:
        conn = sqlite3.connect(str(STATE_DB))
        cur = conn.cursor()
        
        cur.execute("""
            SELECT session_id, timestamp, tool_calls
            FROM messages
            WHERE tool_calls IS NOT NULL
              AND tool_calls != ''
              AND tool_calls != '[]'
            ORDER BY timestamp DESC
        """)
        
        for sid, ts, tc in cur.fetchall():
            try:
                calls = json.loads(tc) if isinstance(tc, str) else tc
                for call in calls:
                    fn = call.get('function', {})
                    name = fn.get('name', '')
                    args_str = fn.get('arguments', '{}')
                    if name not in ('skill_view', 'skills_list'):
                        continue
                    try:
                        args = json.loads(args_str) if isinstance(args_str, str) else args_str
                    except Exception:
                        args = {}
                    
                    skill_name = args.get('name', '')
                    if not skill_name:
                        continue
                    
                    if skill_name not in usage:
                        usage[skill_name] = {'ts': 0.0, 'count': 0, 'session': ''}
                    usage[skill_name]['count'] += 1
                    if usage[skill_name]['ts'] < ts:
                        usage[skill_name]['ts'] = ts
                        usage[skill_name]['session'] = sid
            except Exception:
                pass
        
        conn.close()
    except Exception as e:
        print(f"Warning: state.db read failed: {e}", file=sys.stderr)
    
    return usage


def compute_relevance_score(skill: dict, project_keywords: list[tuple[str, int]]) -> float:
    """프로젝트 키워드 기반 관련성 점수 (0.0 ~ 1.0)"""
    if not project_keywords:
        return 0.5  # 맥락 없으면 중간값
    
    skill_text = ' '.join([
        skill.get('name', ''),
        skill.get('description', ''),
        skill.get('category', ''),
        ' '.join(skill.get('tags', []))
    ]).lower()
    
    total_relevance = 0.0
    total_weight = sum(c for _, c in project_keywords)
    
    if total_weight == 0:
        return 0.5
    
    for keyword, weight in project_keywords:
        if keyword in skill_text:
            total_relevance += weight / total_weight
    
    return min(1.0, total_relevance * 2)  # 정규화 (너무 낮으면 부스트)


def _get_skill_path_category(skill: dict) -> str:
    """스킬 경로에서 카테고리 추출: github/github-pr-workflow → github"""
    path = skill.get('path', '')
    return path.split('/')[0] if '/' in path else ''


def compute_surprise_score(skill: dict, recently_used_names: set[str]) -> float:
    """
    최근 미사용 카테고리 중 무작위 추출 기반 의외성 점수 (0.0 ~ 1.0)

    로직:
    - 스킬 경로에서 카테고리 추출 (path.split('/')[0])
    - 최근 14일 사용한 스킬들의 카테고리 집합 S_used 정의
    - 후보 스킬의 카테고리가 S_used에 없으면 (= 미사용 카테고리)
      → 의외성 높음: random.uniform(0.6, 1.0)
    - 후보 스킬의 카테고리가 S_used에 있으면 (= 최근 사용过的 같은 계열)
      → 의외성 낮음: random.uniform(0.1, 0.4)
    - 카테고리 정보 없으면: random.uniform(0.4, 0.9)
    """
    all_skills = skill.get('_all_skills', {})

    # 최근 사용 스킬들의 카테고리 집합 (경로 기반)
    recently_used_cats = set()
    for name in recently_used_names:
        sinfo = all_skills.get(name, {})
        cat = sinfo.get('category', '')
        if cat:
            recently_used_cats.update(c.strip() for c in cat.split(',') if c.strip())
        # frontmatter category가 없으면 path category fallback
        else:
            path_cat = _get_skill_path_category(sinfo)
            if path_cat:
                recently_used_cats.add(path_cat)

    # 후보 스킬의 카테고리 (frontmatter 우선, path fallback)
    skill_cat_fm = skill.get('category', '')
    skill_cat_path = _get_skill_path_category(skill)
    skill_cats = set(c.strip() for c in skill_cat_fm.split(',') if c.strip())
    if not skill_cats and skill_cat_path:
        skill_cats.add(skill_cat_path)

    if not recently_used_cats:
        # 기준이 없으면 일단 랜덤
        return random.uniform(0.4, 0.9)

    if not skill_cats:
        # 카테고리 정보 전혀 없으면 중간 랜덤
        return random.uniform(0.4, 0.9)

    # 미사용 카테고리 → 의외성 높음, 사용过的 카테고리 → 의외성 낮음
    overlap = len(skill_cats & recently_used_cats)
    if overlap > 0:
        return random.uniform(0.1, 0.4)   # 최근 같은 계열 — 낮음
    else:
        return random.uniform(0.6, 1.0)   # 미사용 카테고리 — 높음


def generate_usage_scenario(skill: dict) -> str:
    """스킬 활용 가능 시나리오 자동 생성"""
    name = skill.get('name', '')
    desc = skill.get('description', '')
    category = skill.get('category', '')
    path = skill.get('path', '')
    
    # 경로에서 카테고리 추출 (e.g. "github/github-pr-workflow" → "github")
    path_category = path.split('/')[0] if '/' in path else ''
    
    # 도메인 키워드 → 시나리오 매핑
    domain_keywords = {
        'github': ('GitHub', "GitHub 작업이 최근 없다면 이 스킬로 코드 리뷰나 PR 워크플로우를 점검할 수 있습니다."),
        'linear': ('Linear', "Linear 활동 로깅이나 이슈 관리를 자동화하는 데 이 스킬이 도움이 될 수 있습니다."),
        'ghost': ('Ghost 블로그', "Ghost 블로그 콘텐츠 파이프라인 운영 중이라면 이 스킬로 발행 워크플로우를 개선할 수 있습니다."),
        'obsidian': ('Obsidian', "Obsidian 노트 정리나 벡터 검색 관련 작업에 이 스킬을 활용할 수 있습니다."),
        'discord': ('Discord', "Discord 채널 모니터링이나 자동 알림 작업에 이 스킬을 사용할 수 있습니다."),
        'apple': ('Apple/macOS', "Apple 플랫폼(iMessage, Reminders 등) 자동화에 이 스킬을 활용할 수 있습니다."),
        'n8n': ('N8N 워크플로우', "N8N 워크플로우 관리나 자동화 파이프라인에서 이 스킬을 활용할 수 있습니다."),
        'brain': ('Drewgent Brain/治理', "현재 Drewgent Brain/治理 체계 작업 중이라면 이 스킬로治理 규칙을 점검할 수 있습니다."),
        'mlops': ('MLOps', "머신러닝 운용 파이프라인 관련 작업에서 이 스킬을 활용할 수 있습니다."),
        'software-development': ('소프트웨어 개발', "소프트웨어 개발 워크플로우에서 이 스킬을 활용할 수 있습니다."),
        'creative': ('크리에이티브', "크리에이티브 콘텐츠 제작에 이 스킬을 활용할 수 있습니다."),
        'media': ('미디어', "유튜브 등 미디어 콘텐츠 처리 작업에 이 스킬을 활용할 수 있습니다."),
        'social-media': ('소셜 미디어', "X(Twitter) 등 소셜 미디어 운영에 이 스킬을 활용할 수 있습니다."),
        'devops': ('DevOps', "DevOps/CD 파이프라인 작업에 이 스킬을 활용할 수 있습니다."),
        'research': ('리서치', "리서치나 분석 작업에 이 스킬을 활용할 수 있습니다."),
    }
    
    # description 기반 매칭
    desc_lower = desc.lower()
    matched = None
    for kw, (domain, _) in domain_keywords.items():
        if kw in desc_lower or kw in path_category.lower():
            matched = (domain, kw)
            break
    
    if matched:
        domain, _ = matched
        scenario = f"**{domain}** 영역의 **{name}** 스킬을 아직 사용하지 않으셨네요. 스킬 설명: {desc[:80]}"
    else:
        # 카테고리명 → 한글 라벨
        cat_labels = {
            'drewgent': 'Drewgent 내부 기능',
            'agent': '에이전트 관리',
            'productivity': '생산성',
            'automation': '자동화',
            'growth-engine': '성장 엔진',
            'social-media': '소셜 미디어',
            'smart-home': '스마트홈',
        }
        cat_label = cat_labels.get(path_category, path_category.replace('-', ' ').title() if path_category else '범용')

        if desc:
            scenario = f"현재 프로젝트에서 **{name}** 스킬({cat_label})을 활용할 수 있는 포인트가 있을 수 있습니다. 설명: {desc[:80]}"
        else:
            scenario = f"현재 프로젝트에서 **{name}** 스킬({cat_label})을 활용할 수 있을지 점검해볼 만합니다."
    # Discord markdown 정리 (bold 제거)
    scenario = scenario.replace('**', '').strip()
    return scenario


def run(since_days: int = 30) -> dict:
    """메인 실행: 전체 데이터 수집 및 분석"""
    now_ts = datetime.now().timestamp()
    
    # 1. 프로젝트 맥락 수집
    project_context = gather_project_context()
    project_keywords = project_context['keywords']
    
    # 2. 전체 스킬 목록
    skills = gather_all_skills()
    
    # 3. state.db에서 사용 이력
    usage = get_skill_usage_from_state_db()
    
    # 4. 사용 이력 머지 + 파일 크기 계산
    for name, sinfo in skills.items():
        u = usage.get(name, {'ts': 0.0, 'count': 0, 'session': ''})
        sinfo['call_count'] = u['count']
        if u['ts'] > 0:
            sinfo['last_used_ts'] = u['ts']
            sinfo['last_used'] = datetime.fromtimestamp(u['ts']).strftime('%Y-%m-%d %H:%M')
            sinfo['days_ago'] = round((now_ts - u['ts']) / 86400, 1)
        # skill_md_size KB 단위로 변환
        sinfo['skill_md_size_kb'] = round(sinfo.get('skill_md_size', 0) / 1024, 1)
    
    # recently used set (관련성/의외성 계산용)
    recently_used = {name for name, s in skills.items() if s.get('days_ago') is not None and s['days_ago'] <= 14}
    
    # _all_skills 참조를 위해 자기 자신 저장
    for name, sinfo in skills.items():
        sinfo['_all_skills'] = skills
    
    # 5. 분류
    never_used = [s for s in skills.values() if s['last_used'] is None]
    used_recently = [s for s in skills.values() if s.get('days_ago') is not None and s['days_ago'] <= 7]
    used_old = [s for s in skills.values() if s.get('days_ago') is not None and s['days_ago'] > 7]
    
    # 6. 점수 계산 (candidate pool: never_used + used_old)
    candidate_pool = never_used + used_old
    
    for skill in candidate_pool:
        skill['_relevance'] = compute_relevance_score(skill, project_keywords)
        skill['_surprise'] = compute_surprise_score(skill, recently_used)
        skill['_combined'] = skill['_relevance'] * 0.6 + skill['_surprise'] * 0.4
        skill['_scenario'] = generate_usage_scenario(skill)
    
    # 7. 정렬
    candidate_pool.sort(key=lambda s: s['_combined'], reverse=True)
    
    # 8. 출력 포맷
    result = {
        'generated_at': datetime.now().isoformat(),
        'since_days': since_days,
        'project_context': {
            'keywords': project_keywords[:20],
            'sources': project_context['sources'],
            'sessions_summary': project_context['sessions_summary'],
        },
        'summary': {
            'total_skills': len(skills),
            'never_used': len(never_used),
            'used_recently': len(used_recently),
            'used_old': len(used_old),
            'candidate_pool': len(candidate_pool),
        },
        'recommendations': [
            {
                'name': s['name'],
                'category': s['category'],
                'description': s['description'],
                'path': s['path'],
                'last_used': s['last_used'],
                'days_ago': s['days_ago'],
                'call_count': s['call_count'],
                'relevance_score': round(s['_relevance'], 3),
                'surprise_score': round(s['_surprise'], 3),
                'combined_score': round(s['_combined'], 3),
                'scenario': s['_scenario'],
            }
            for s in candidate_pool[:12]  # Top 12
        ],
        # Monthly deletion candidates
        'deletion_candidates': [
            {
                'name': s['name'],
                'category': s['category'],
                'description': s['description'],
                'path': s['path'],
                'last_used': s['last_used'],
                'days_ago': s['days_ago'],
                'call_count': s['call_count'],
                'size_kb': s.get('skill_md_size_kb', 0),
            }
            for s in sorted(never_used, key=lambda x: x.get('skill_md_size', 0), reverse=True)[:8]
        ],
    }
    
    # 메모리 저장 (phase tracking)
    meta_path = DREWENT_HOME / '.skill-gym-meta.json'
    try:
        meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    except Exception:
        meta = {}
    
    meta['last_run'] = datetime.now().isoformat()
    meta['last_recommendation_count'] = len(result['recommendations'])
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    
    return result


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--since-days', type=int, default=30)
    args = parser.parse_args()
    
    result = run(since_days=args.since_days)
    print(json.dumps(result, indent=2, ensure_ascii=False))

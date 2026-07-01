#!/usr/bin/env python3
"""
content_curator.py — Content curation hub. Replaces 6 legacy jobs.

Reads all data sources → heuristic dedup + scoring → kanban INSERT.
$0 per run (no LLM calls). Runs at 08:00, 15:00 daily.

Replaces:
  - content-manager-periodic (agent, hourly)  → 제거
  - content-news-trigger (script)              → 병합
  - content-insight-trigger (script)           → 병합
  - content-series-trigger (script)            → 병합
  - content-planner (agent, 15:30)             → 제거
  - trend-evaluate-trigger (script, 10:00)     → 병합 (trend_evaluate.py 대체)

Output (kanban INSERT):
  - content-write: {topic} — BUILD LOG / AI & TOOLS / SYSTEMS (publish)
  - trend-review: {tool}   — 외부 도구 평가 (discuss → apply/discard)
  - creative-write: {topic} — CREATIVE pillar (draft only)
"""
import json, os, subprocess, sys, time, sqlite3, uuid
from pathlib import Path
from datetime import datetime, timedelta

HOME = Path.home()
DREWGENT = HOME / ".drewgent"
NOW_TS = int(time.time())
TODAY = datetime.now().strftime("%Y-%m-%d")

# Paths
KEEP_DIR = DREWGENT / "@memory" / "growth" / "trend-harvester" / "analyzed" / "keep"
EVALUATED_DIR = DREWGENT / "@memory" / "growth" / "trend-harvester" / "evaluated"
CONTENT_DIR = DREWGENT / "@memory" / "growth" / "content" / "curated"
SEO_DIR = DREWGENT / "P2-hippocampus" / "knowledge" / "seo-articles"
NARRATIVE_ARC = DREWGENT / "P4-cortex" / "content" / "narrative_arc.md"
CONTENT_INVENTORY = DREWGENT / "P4-cortex" / "content" / "content-inventory.md"
CREATIVE_BACKLOG = DREWGENT / "P4-cortex" / "content" / "creative-backlog.md"
KANBAN_DB = DREWGENT / "kanban.db"

CURATE_HOME = DREWGENT / "@memory" / "growth" / "content"
CONTENT_EVALUATED = CURATE_HOME / "curated"

THRESHOLD_WRITE = 0.68  # content-write 최소 composite score
THRESHOLD_REVIEW = 0.62  # trend-review 최소
CONTENT_LIMIT = 3         # 회당 최대 content-write 생성 수
REVIEW_LIMIT = 3          # 회당 최대 trend-review 생성 수

DRY_RUN = "--dry-run" in sys.argv


def log(msg):
    prefix = "[DRY]" if DRY_RUN else "[curator]"
    print(f"{prefix} {msg}")


# ── Helpers ───────────────────────────────────

def composite_score(scores: dict) -> float:
    axes = [scores.get(k, 0) for k in ("relevance", "direct_impact", "actionability", "novelty", "credibility")]
    return sum(axes) / max(len(axes), 1)


def read_json(path):
    try:
        return json.loads(Path(path).read_text())
    except Exception:
        return None


def git_log_since(days=7, path=None):
    cmd = ["git", "log", "--oneline", f"--since={days} days ago"]
    if path:
        cmd += ["-C", str(path)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return r.stdout.strip()
    except Exception:
        return ""


def get_evaluated_keep_set():
    """이미 평가된 keep 항목 hash set (trend-review용)."""
    s = set()
    if EVALUATED_DIR.exists():
        for f in os.listdir(str(EVALUATED_DIR)):
            parts = f.replace(".json", "").split("-")
            if parts:
                s.add(parts[-1])
    return s


def get_curated_content_set():
    """이미 content-write로 처리된 항목 tracking."""
    s = set()
    if CONTENT_EVALUATED.exists():
        for f in os.listdir(str(CONTENT_EVALUATED)):
            if f.endswith(".json"):
                try:
                    d = json.loads((CONTENT_EVALUATED / f).read_text())
                    src = d.get("source", d.get("keep_hash", ""))
                    if src:
                        s.add(src)
                except Exception:
                    pass
    return s


def get_recent_post_titles(days=3):
    """최근 발행된 포스트 제목 목록 (중복 방지)."""
    try:
        r = subprocess.run(
            ["docker", "exec", "humanerd-wp", "wp", "--allow-root", "post", "list",
             "--post_type=post", "--post_status=publish", f"--posts_per_page=50",
             "--fields=post_title", "--format=csv"],
            capture_output=True, text=True, timeout=15,
        )
        titles = []
        for line in r.stdout.strip().split("\n")[1:]:
            t = line.strip().strip('"')
            if t:
                titles.append(t.lower())
        return titles
    except Exception:
        return []


def get_pending_kanban_titles():
    """현재 pending 상태인 kanban task title 목록 (중복 방지)."""
    try:
        conn = sqlite3.connect(str(KANBAN_DB))
        cur = conn.execute("SELECT title FROM tasks WHERE status IN ('pending','todo')")
        titles = [row[0].lower() for row in cur.fetchall()]
        conn.close()
        return titles
    except Exception:
        return []


def is_duplicate(title, recent_posts, pending_tasks):
    tl = title.lower()
    for r in recent_posts:
        if len(tl) > 10 and (tl in r or r in tl):
            return True
    for p in pending_tasks:
        if tl in p or p in tl:
            return True
    return False


def mark_curated(source_key, title, task_id, kind):
    """처리 완료 마커 기록. DRY_RUN 시 skip."""
    if DRY_RUN:
        return
    marker = CONTENT_EVALUATED / f"{TODAY}-{kind}-{source_key}.json"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(json.dumps({
        "source": source_key,
        "title": title,
        "kanban_id": task_id,
        "kind": kind,
        "created_at": TODAY,
    }, ensure_ascii=False, indent=2))


def kanban_insert(title, body, priority=1, skills=None):
    """kanban DB에 task 삽입. DRY_RUN 시 None 반환."""
    if DRY_RUN:
        return None
    tid = str(uuid.uuid4()).upper()
    skills_json = json.dumps(skills or ["kanban-orchestrator"])
    try:
        conn = sqlite3.connect(str(KANBAN_DB))
        conn.execute(
            "INSERT OR IGNORE INTO tasks (id, title, body, status, priority, created_at, skills) "
            "VALUES (?, ?, ?, 'pending', ?, ?, ?)",
            (tid, title, body, priority, NOW_TS, skills_json),
        )
        conn.commit()
        conn.close()
        return tid
    except Exception as e:
        log(f"  DB error: {e}")
        return None


# ── Source Readers ────────────────────────────

def scan_trend_keep(recent_posts, pending_tasks):
    """trend keep에서 content-write / trend-review 후보 발굴."""
    if not KEEP_DIR.exists():
        return [], []

    evaluated = get_evaluated_keep_set()
    curated = get_curated_content_set()
    write_candidates = []
    review_candidates = []

    files = sorted(os.listdir(str(KEEP_DIR)), reverse=True)[:60]  # 최신 60개만
    for fname in files:
        if not fname.endswith(".json"):
            continue
        base = fname.replace(".json", "")
        if base in curated:
            continue
        d = read_json(KEEP_DIR / fname)
        if not d:
            continue
        item = d.get("item", {})
        scores = d.get("scores", {})
        comp = composite_score(scores)
        name = item.get("name", base)[:60]
        url = item.get("url", "")
        desc = (item.get("description", "") or "")[:200]
        source = item.get("source", "github")

        # content-write 후보 (고점수, Drewgent 관련)
        if comp >= THRESHOLD_WRITE and not is_duplicate(name, recent_posts, pending_tasks):
            write_candidates.append((comp, name, url, desc, base, fname, scores))

        # trend-review 후보 (중간 점수, 아직 evaluate 안 됨)
        if comp >= THRESHOLD_REVIEW and base not in evaluated:
            review_candidates.append((comp, name, url, desc, base, fname))

    write_candidates.sort(key=lambda x: -x[0])
    review_candidates.sort(key=lambda x: -x[0])
    return write_candidates, review_candidates


def scan_seo_articles(recent_posts, pending_tasks):
    """SEO article harvester 출력에서 content-write 후보 발굴."""
    if not SEO_DIR.exists():
        return []
    candidates = []
    for root, dirs, files in os.walk(str(SEO_DIR)):
        for f in files:
            if not f.endswith(".json"):
                continue
            d = read_json(os.path.join(root, f))
            if not d or not isinstance(d, dict):
                continue
            title = d.get("title", d.get("name", f))[:60]
            desc = (d.get("description", d.get("summary", "")) or "")[:200]
            url = d.get("url", "")
            if title and not is_duplicate(title, recent_posts, pending_tasks):
                # heuristic SEO content score: base 0.5 + topic relevance
                score = 0.55
                keywords = ["agent", "ai", "mcp", "llm", "model", "automation", "workflow",
                            "search", "seo", "ge", "open source", "tool", "pipeline"]
                for kw in keywords:
                    if kw in (title + desc).lower():
                        score += 0.05
                score = min(score, 0.85)
                candidates.append((score, title, url, desc, f))
    candidates.sort(key=lambda x: -x[0])
    return candidates


def scan_git_activity(recent_posts, pending_tasks):
    """최근 git commit에서 content-write 후보 발굴."""
    git_out = git_log_since(days=7, path=str(DREWGENT))
    if not git_out:
        return []
    lines = git_out.split("\n")
    candidates = []
    for line in lines[:20]:
        parts = line.split(" ", 1)
        if len(parts) < 2:
            continue
        msg = parts[1].strip()
        if len(msg) < 10:
            continue
        if is_duplicate(msg, recent_posts, pending_tasks):
            continue
        # score based on change type
        score = 0.50
        if any(k in msg.lower() for k in ["feat", "add", "new", "refactor", "redesign", "v0.", "architecture"]):
            score += 0.15
        if any(k in msg.lower() for k in ["fix", "bug", "patch"]):
            score -= 0.10
        if any(k in msg.lower() for k in ["content", "blog", "post", "doc"]):
            score -= 0.10
        candidates.append((min(score, 0.75), msg, "", "", parts[0]))
    candidates.sort(key=lambda x: -x[0])
    return candidates


def scan_creative_backlog(recent_posts, pending_tasks):
    """Creative backlog에서 content-write 후보."""
    if not CREATIVE_BACKLOG.exists():
        return []
    text = CREATIVE_BACKLOG.read_text()
    candidates = []
    in_backlog = False
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("## 대기 주제") or line.startswith("## Pending"):
            in_backlog = True
            continue
        if line.startswith("## 발행 완료") or line.startswith("## Completed"):
            in_backlog = False
            continue
        if in_backlog and line.startswith("- [ ]"):
            title = line.replace("- [ ]", "").strip().split("/")[0].strip()
            if title and not is_duplicate(title, recent_posts, pending_tasks):
                candidates.append((0.60, title, "", f"Creative backlog: {line[:100]}", ""))
    return candidates


# ── Main ──────────────────────────────────────

def main():
    CURATE_HOME.mkdir(parents=True, exist_ok=True)

    recent_titles = get_recent_post_titles()
    pending_titles = get_pending_kanban_titles()
    log(f"recent posts: {len(recent_titles)}, pending tasks: {len(pending_titles)}")

    created = 0

    # ── 1. Trend keep → content-write + trend-review ──
    write_cands, review_cands = scan_trend_keep(recent_titles, pending_titles)
    log(f"trend keep: {len(write_cands)} write candidates, {len(review_cands)} review candidates")

    for comp, name, url, desc, base, fname, scores in write_cands[:CONTENT_LIMIT]:
        title = f"content-write: {name}"
        body = f"""## Curation: {name}

**Source**: {url}
**Composite score**: {comp:.2f}
**Context**: Trend keep ({fname})

### Writing Brief
- Topic: {name}
- Category: auto-detect (BUILD LOG / AI & TOOLS / SYSTEMS)
- Style: ReefWatch template, Korean 반말
- SVG cover required
- Author: 1 (humanerd)
- Status: publish (after editor QA)

### Score Breakdown
- relevance={scores.get('relevance',0):.1f} direct_impact={scores.get('direct_impact',0):.1f}
- actionability={scores.get('actionability',0):.1f} novelty={scores.get('novelty',0):.1f}
- credibility={scores.get('credibility',0):.1f}
"""
        tid = kanban_insert(title, body, priority=1, skills=["kanban-orchestrator"])
        if tid:
            mark_curated(base, name, tid, "content-write")
            log(f"  → content-write: {name} (score={comp:.2f})")
            created += 1

    for comp, name, url, desc, base, fname in review_cands[:REVIEW_LIMIT]:
        title = f"trend-review: {name}"
        body = f"""## Trend Review: {name}

**Source**: {url}
**Score**: {comp:.2f}
**Description**: {desc}

### Task
1. Review this tool/project
2. Determine relevance to Drewgent
3. If applicable → create implementation plan
4. If not applicable → mark as discarded
"""
        tid = kanban_insert(title, body, priority=1, skills=["kanban-orchestrator"])
        if tid:
            mark_curated(base, name, tid, "trend-review")
            log(f"  → trend-review: {name} (score={comp:.2f})")
            # Also mark as evaluated for the legacy evaluated/ dir
            marker = EVALUATED_DIR / f"{TODAY}-queue-{base}.json"
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.write_text(json.dumps({"keep_file": fname, "name": name, "score": comp, "kanban_id": tid, "created_at": TODAY}))
            created += 1

    # ── 2. SEO articles → content-write ──
    seo_cands = scan_seo_articles(recent_titles, pending_titles)
    log(f"SEO articles: {len(seo_cands)} candidates")
    for score, title, url, desc, fname in seo_cands[:2]:
        if created >= CONTENT_LIMIT + REVIEW_LIMIT:
            break
        task_title = f"content-write: {title}"
        body = f"""## Curation: {title}

**Source**: SEO article ({fname})
**Score**: {score:.2f}

### Writing Brief
- Context: external news/article
- Style: Opinion/analysis angle
- Category: AI & Tools (default for news)
"""
        tid = kanban_insert(task_title, body, priority=2)
        if tid:
            log(f"  → content-write (SEO): {title}")
            created += 1

    # ── 3. Git activity → content-write ──
    git_cands = scan_git_activity(recent_titles, pending_titles)
    log(f"git activity: {len(git_cands)} candidates")
    for score, msg, _, _, sha in git_cands[:1]:
        if created >= CONTENT_LIMIT + REVIEW_LIMIT + 2:
            break
        task_title = f"content-write: {msg[:50]}"
        body = f"""## Curation: {msg[:80]}

**Source**: git commit {sha}
**Score**: {score:.2f}

### Writing Brief
- Recent work: {msg}
- Category: BUILD LOG (default for build activity)
"""
        tid = kanban_insert(task_title, body, priority=2)
        if tid:
            log(f"  → content-write (git): {msg[:40]}")
            created += 1

    # ── 4. Creative backlog → creative-write (draft only) ──
    creative_cands = scan_creative_backlog(recent_titles, pending_titles)
    log(f"creative backlog: {len(creative_cands)} candidates")
    for score, title, _, desc, _ in creative_cands[:1]:
        task_title = f"creative-write: {title}"
        body = f"""## Creative: {title}

**Source**: creative-backlog.md
**Score**: {score:.2f}

### Rules
- **Draft only** — do NOT publish
- Category: Creative
- User must approve before publish
"""
        tid = kanban_insert(task_title, body, priority=3)
        if tid:
            log(f"  → creative-write (draft): {title}")
            created += 1

    # ── Result ──
    if created == 0:
        print("silent")
    else:
        print(f"{created}")
        log(f"total kanban tasks created: {created}")


if __name__ == "__main__":
    main()

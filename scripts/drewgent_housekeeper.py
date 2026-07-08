#!/usr/bin/env python3
"""Drewgent system housekeeper — monitors, diagnoses, cleans.

Cron schedule:
  *:00  — Light check (every hour)
  04:00 — Deep clean (daily)

Reports to Discord channel #status-monitoring → 하우스키핑 thread.
"""
import json, os, shutil, sqlite3, subprocess, sys, time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

DREW_HOME = Path(os.environ.get("DREW_HOME", str(Path.home() / ".drewgent")))
SCRIPTS = DREW_HOME / "scripts"
CRON_DIR = DREW_HOME / "cron"
LOGS = DREW_HOME / "logs"
CACHE = DREW_HOME / "logs" / "housekeeper_state.json"
DISCORD_CHANNEL = "1493982427708915713"
DISCORD_THREAD_NAME = "하우스키핑"
BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")

# ── Discord ──────────────────────────────────────────────────────

def _discord_api(method, path, data=None):
    if not BOT_TOKEN:
        return None
    url = f"https://discord.com/api/v10/{path}"
    headers = {"Authorization": f"Bot {BOT_TOKEN}", "Content-Type": "application/json"}
    r = subprocess.run(
        ["curl", "-s", "-X", method, url,
         "-H", f"Authorization: Bot {BOT_TOKEN}",
         "-H", "Content-Type: application/json",
         *(["-d", json.dumps(data)] if data else [])],
        capture_output=True, text=True, timeout=15
    )
    return json.loads(r.stdout) if r.stdout.strip() else None

def _get_thread_id():
    """Return 하우스키핑 thread ID. Cached; falls back to active-thread search then creation."""
    state = {}
    if CACHE.exists():
        try: state = json.loads(CACHE.read_text())
        except: pass
    tid = state.get("thread_id")
    if tid:
        ch = _discord_api("GET", f"channels/{tid}")
        if ch and ch.get("type") in (11, 12):
            return tid
    r = _discord_api("GET", f"channels/{DISCORD_CHANNEL}/threads/active")
    if r:
        for t in r.get("threads", []):
            if t.get("name") == DISCORD_THREAD_NAME:
                _cache_thread_id(t["id"])
                return t["id"]
    anchor = _discord_api("POST", f"channels/{DISCORD_CHANNEL}/messages",
                          {"content": f"🧹 **하우스키핑** — {datetime.now().strftime('%Y-%m-%d')}"})
    if not anchor or "id" not in anchor:
        return None
    thread = _discord_api("POST", f"channels/{DISCORD_CHANNEL}/messages/{anchor['id']}/threads",
                          {"name": DISCORD_THREAD_NAME})
    if thread and "id" in thread:
        _cache_thread_id(thread["id"])
        return thread["id"]
    return None

def _cache_thread_id(tid):
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps({"thread_id": tid}))

def discord_send(content, thread_id=None):
    """Send message to 하우스키핑 thread."""
    tid = thread_id or _get_thread_id()
    if not tid:
        return
    for chunk in [content[i:i+1900] for i in range(0, len(content), 1900)]:
        _discord_api("POST", f"channels/{tid}/messages", {"content": chunk})

# ── System checks ────────────────────────────────────────────────

def check_tmux():
    """Kill dead tmux sessions. Return killed count."""
    r = subprocess.run(["tmux", "ls"], capture_output=True, text=True, timeout=5)
    if r.returncode != 0:
        return 0
    killed = 0
    for line in r.stdout.strip().split("\n"):
        if not line.strip():
            continue
        name = line.split(":")[0].strip()
        if "(dead)" in line:
            subprocess.run(["tmux", "kill-session", "-t", name],
                           capture_output=True, timeout=3)
            killed += 1
    return killed

def check_launchd():
    """Check core services."""
    r = subprocess.run(["launchctl", "list"], capture_output=True, text=True, timeout=5)
    services = {"ai.drewgent.opencode", "ai.drewgent.discord-bot",
                "ai.drewgent.cron", "ai.drewgent.cloudflared-wp"}
    running = set()
    dead = []
    for line in r.stdout.strip().split("\n"):
        parts = line.split("\t")
        if len(parts) == 3:
            pid, last_exit, label = parts
            if label in services:
                running.add(label)
                if last_exit not in ("0", "") and pid == "-":
                    dead.append(f"{label} (exit={last_exit})")
    missing = services - running
    return missing, dead

def check_knowledge_db():
    """Check knowledge.db health."""
    db_path = DREW_HOME / "knowledge.db"
    if not db_path.exists():
        return -1
    try:
        db = sqlite3.connect(str(db_path))
        cnt = db.execute("SELECT count(*) FROM embeddings").fetchone()[0]
        db.close()
        return cnt
    except:
        return -1

def check_kanban_stale():
    """Reclaim stale in-progress tasks (24h+ since last heartbeat)."""
    db_path = DREW_HOME / "kanban.db"
    if not db_path.exists():
        return 0
    try:
        db = sqlite3.connect(str(db_path))
        cut = int(time.time()) - 86400
        cur = db.execute(
            "SELECT id, title FROM tasks WHERE status='in_progress' AND "
            "(last_heartbeat_at IS NULL OR last_heartbeat_at < ?) AND "
            "started_at < ?",
            (cut, cut * 1000)
        )
        stale = cur.fetchall()
        for tid, title in stale:
            db.execute("UPDATE tasks SET status='pending', claim_lock=NULL, "
                       "claim_expires=NULL, worker_pid=NULL WHERE id=?",
                       (tid,))
        db.commit()
        db.close()
        return len(stale)
    except:
        return -1

def check_cron_jobs():
    """Count dead/paused cron jobs."""
    try:
        data = json.loads((CRON_DIR / "jobs.json").read_text())
    except:
        return -1
    jobs = data.get("jobs", [])
    stopped = [j for j in jobs if j.get("state") in ("dead", "paused")
               or j.get("enabled") is False]
    return len(stopped)

def check_disk():
    """Return (used_pct, used_gb, total_gb)."""
    r = subprocess.run(["df", "-h", "/"], capture_output=True, text=True, timeout=5)
    lines = r.stdout.strip().split("\n")
    if len(lines) < 2:
        return None
    parts = lines[1].split()
    if len(parts) >= 5:
        pct = parts[4].replace("%", "")
        return int(pct)
    return None

# ── Bridge lint ──────────────────────────────────────────────────

def check_bridge_lint():
    """Run manufacturing-bridge tag lint. Returns (ok: bool, summary: str)."""
    script = SCRIPTS / "bridge-lint.sh"
    if not script.exists():
        return False, "bridge-lint.sh 없음"
    r = subprocess.run(["bash", str(script)], capture_output=True, text=True, timeout=30)
    out = r.stdout.strip()
    if r.returncode == 0:
        return True, out.split("\n")[-1] if out else "pass"
    return False, out.split("\n")[-1] if out else "fail"

# ── Deep clean extras ────────────────────────────────────────────

def rotate_logs():
    """Remove logs older than 30 days."""
    count = 0
    cut = time.time() - 30 * 86400
    for f in sorted(LOGS.glob("*")):
        if f.is_file() and f.stat().st_mtime < cut:
            f.unlink()
            count += 1
    return count

def clean_cron_output():
    """Remove cron output older than 7 days."""
    out_dir = CRON_DIR / "output"
    if not out_dir.exists():
        return 0
    count = 0
    cut = time.time() - 7 * 86400
    for f in out_dir.iterdir():
        if f.is_file() and f.stat().st_mtime < cut:
            f.unlink()
            count += 1
    return count

def vacuum_knowledge_db():
    """VACUUM knowledge.db for storage efficiency."""
    db_path = DREW_HOME / "knowledge.db"
    if not db_path.exists():
        return False
    try:
        db = sqlite3.connect(str(db_path))
        db.execute("VACUUM")
        db.close()
        return True
    except:
        return False

def archive_completed_kanban():
    """Archive kanban tasks completed > 7 days ago."""
    db_path = DREW_HOME / "kanban.db"
    if not db_path.exists():
        return 0
    cut = int(time.time()) - 7 * 86400
    db = sqlite3.connect(str(db_path))
    cur = db.execute(
        "UPDATE tasks SET status='archived' WHERE status='completed' AND completed_at < ?",
        (cut,)
    )
    n = cur.rowcount
    db.commit()
    db.close()
    return n


def prune_state_sessions():
    """Delete state.db sessions older than 30 days + clean orphaned FTS data."""
    db_path = DREW_HOME / "state.db"
    if not db_path.exists():
        return 0, 0
    try:
        db = sqlite3.connect(str(db_path))
        cut_ms = int(time.time() - 30 * 86400) * 1000
        cur = db.execute("DELETE FROM sessions WHERE started_at < ?", (cut_ms,))
        deleted = cur.rowcount
        # Clean orphaned messages and FTS data
        db.execute("DELETE FROM messages WHERE session_id NOT IN (SELECT id FROM sessions)")
        # Rebuild FTS indexes to purge orphaned rows
        try:
            db.execute("INSERT INTO messages_fts(messages_fts) VALUES('rebuild')")
        except Exception:
            pass
        try:
            db.execute("INSERT INTO messages_fts_trigram(messages_fts_trigram) VALUES('rebuild')")
        except Exception:
            pass
        db.execute("VACUUM")
        db.close()
        return deleted, db_path.stat().st_size
    except Exception:
        return -1, 0


def prune_memory_sessions():
    """Delete @memory/sessions/ files older than 30 days."""
    sess_dir = DREW_HOME / "@memory" / "sessions"
    if not sess_dir.exists():
        return 0, 0
    count = 0
    size = 0
    cut = time.time() - 30 * 86400
    for f in sess_dir.iterdir():
        if f.is_file() and f.stat().st_mtime < cut:
            size += f.stat().st_size
            f.unlink()
            count += 1
    return count, size


def digest_qa_evidence():
    """Digest completed QA evidence directories into wiki summary.

    Reads all non-lib task directories (any naming convention).
    Uses .qa-evidence.json manifest when available, falls back to contract.json.
    Preserves source directories — does NOT delete.
    """
    qa_dir = DREW_HOME / "P2-hippocampus" / "qa-evidence"
    if not qa_dir.exists():
        return 0, 0

    task_dirs = sorted([d for d in qa_dir.iterdir() if d.is_dir() and d.name != "lib"],
                       key=lambda d: d.stat().st_mtime, reverse=True)
    if not task_dirs:
        return 0, 0

    wiki_dir = DREW_HOME / "P5-ego" / "wiki"
    wiki_dir.mkdir(parents=True, exist_ok=True)
    digest_log = wiki_dir / "qa-evidence-summary.md"

    entries = []
    for d in task_dirs:
        manifest = d / ".qa-evidence.json"
        contract = d / "contract.json"
        try:
            if manifest.exists():
                data = json.loads(manifest.read_text())
                status = data.get("delivery_status", "?")
                score = data.get("full_qa_score", "?")
                phases = ", ".join(data.get("phases_completed", []))
                task_id = data.get("task_id", d.name)
            elif contract.exists():
                data = json.loads(contract.read_text())
                status = "INCOMPLETE"
                score = "?"
                phases = "contract"
                task_id = data.get("task_id", d.name)
            else:
                continue

            created = data.get("created_at", "")[:10] if manifest.exists() else ""
            entry = {
                "task_id": task_id,
                "status": status,
                "score": score,
                "phases": phases,
                "created": created,
            }
            entries.append(entry)
        except:
            continue

    body = "---\ntitle: QA Evidence Summary\ntype: index\nspace: meta\n---\n\n# QA Evidence Summary\n\n"
    body += f"Total: {len(entries)} tasks\n\n"
    body += "| Task ID | Status | Score | Phases | Created |\n"
    body += "|---------|--------|-------|--------|---------|\n"
    for e in entries[:100]:
        body += f"| {e['task_id']} | {e['status']} | {e['score']} | {e['phases']} | {e['created']} |\n"

    digest_log.write_text(body)
    return len(entries), len(task_dirs)


def ingest_wiki_to_knowledge():
    """Ingest P5-ego/wiki/ pages into knowledge.db."""
    db_path = DREW_HOME / "knowledge.db"
    wiki_dir = DREW_HOME / "P5-ego" / "wiki"
    if not wiki_dir.exists() or not db_path.exists():
        return False
    try:
        db = sqlite3.connect(str(db_path))
        for f in wiki_dir.rglob("*.md"):
            content = f.read_text(encoding="utf-8", errors="replace")
            slug = f.relative_to(DREW_HOME).as_posix()
            db.execute(
                "INSERT OR IGNORE INTO facts (slug, type, content) VALUES (?, 'wiki', ?)",
                (slug, content[:5000])
            )
        db.commit()
        db.close()
        return True
    except:
        return False


# ── Session ingest ───────────────────────────────────────────────

def ingest_sessions():
    """Ingest new P2 session logs into knowledge.db."""
    script = DREW_HOME / "scripts" / "ingest_sessions.py"
    if not script.exists():
        return -1
    r = subprocess.run(
        ["python3", str(script)],
        capture_output=True, text=True, timeout=600,
    )
    if r.returncode == 0:
        line = r.stdout.strip().split("\n")[0] if r.stdout else "ok"
        print(f"  session ingest: {line}")
        return 0
    print(f"  session ingest FAILED: {r.stderr[:200]}")
    return -1


# ── Contradiction audit ─────────────────────────────────────────

# ── Report builder ───────────────────────────────────────────────

def build_report(title, sections):
    lines = [f"🧹 **하우스키핑 — {title}**"]
    for name, items in sections:
        if not items:
            continue
        if isinstance(items, list):
            for item in items:
                lines.append(f"• {item}")
        else:
            lines.append(f"• {items}")
    if len(lines) == 1:
        lines.append("깨끗함 ✨")
    return "\n".join(lines)

# ── Main ─────────────────────────────────────────────────────────

def main():
    now = datetime.now()
    is_deep = now.hour == 4 and now.minute < 30

    tmux_killed = check_tmux()
    missing_svc, dead_svc = check_launchd()
    embedding_cnt = check_knowledge_db()
    stale = check_kanban_stale()
    stopped = check_cron_jobs()
    disk_pct = check_disk()

    sections = [
        ("🖥 프로세스", []),
        ("🧠 Knowledge DB", []),
        ("📋 Kanban", []),
        ("⏰ Cron", []),
        ("💾 디스크", []),
    ]

    procs = []
    if tmux_killed:
        procs.append(f"tmux dead 세션 {tmux_killed}개 종료")
    if missing_svc:
        procs.append(f"서비스 중단: {', '.join(missing_svc)}")
    if dead_svc:
        procs.append(f"서비스 비정상: {', '.join(dead_svc)}")
    sections[0] = ("🖥 프로세스", procs)

    sections[1] = ("🧠 Knowledge DB",
                   [f"임베딩 {embedding_cnt}개"] if embedding_cnt > 0 else
                   [f"DB 없음"] if embedding_cnt == -1 else [])

    sections[2] = ("📋 Kanban",
                   [f"stale {stale}건 회수"] if stale > 0 else
                   [f"stale 없음"] if is_deep else [])

    sections[3] = ("⏰ Cron",
                   [f"중단 job {stopped}개"] if stopped > 0 else
                   [f"모든 job 정상"] if is_deep else [])

    sections[4] = ("💾 디스크",
                   [f"{disk_pct}% 사용"] if disk_pct and disk_pct > 75 else
                   [f"{disk_pct}%"] if is_deep else [])

    title = f"{now.strftime('%Y-%m-%d %H:%M')} {'🔄 Deep Clean' if is_deep else '⚡ Pulse'}"

    if is_deep:
        logs_removed = rotate_logs()
        cron_out_removed = clean_cron_output()
        db_vacuumed = vacuum_knowledge_db()
        archived = archive_completed_kanban()
        sess_db_n, sess_db_sz = prune_state_sessions()
        sess_files_n, sess_files_sz = prune_memory_sessions()
        qa_digested, qa_total = digest_qa_evidence()
        wiki_ingested = ingest_wiki_to_knowledge()
        sess_ingested = ingest_sessions()

        digest_items = [f"로그 {logs_removed}개 삭제" if logs_removed else "로그 정상",
                        f"cron output {cron_out_removed}개 삭제" if cron_out_removed else "cron output 정상",
                        "knowledge.db VACUUM 완료" if db_vacuumed else "knowledge.db VACUUM 실패",
                        f"kanban {archived}건 아카이브" if archived else "kanban 아카이브 없음"]
        if sess_db_n > 0:
            digest_items.append(f"state.db 세션 {sess_db_n}건 정리 ({sess_db_sz / 1024 / 1024:.0f}MB)")
        if sess_files_n > 0:
            digest_items.append(f"메모리 세션 {sess_files_n}파일 정리 ({sess_files_sz / 1024 / 1024:.0f}MB)")
        if qa_digested > 0:
            digest_items.append(f"QA evidence {qa_digested}/{qa_total}건 digest")
        digest_items.append(f"wiki→knowledge.db {'✅' if wiki_ingested else '❌'}")
        bridge_ok, bridge_msg = check_bridge_lint()
        digest_items.append(f"bridge-lint {'✅' if bridge_ok else '⚠️'} — {bridge_msg}")
        digest_items.append(f"session→knowledge.db {'✅' if sess_ingested == 0 else '❌'}")
        digest_items.append(f"디스크 {disk_pct}% 사용" if disk_pct else "디스크 확인 불가")

        sections.append(("🧽 정리", digest_items))

    report = build_report(title, sections)
    discord_send(report)
    print(report)

    # Save state for next run
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    state = {"last_run": now.isoformat(), "orphans": orphans, "disk_pct": disk_pct}
    CACHE.write_text(json.dumps(state))

if __name__ == "__main__":
    main()

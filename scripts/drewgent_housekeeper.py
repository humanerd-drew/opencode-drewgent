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

def check_gbrain_orphans():
    """Return orphan page count. (Classification deferred to deep clean.)"""
    r = subprocess.run(["gbrain", "find-orphans", "--json"],
                       capture_output=True, text=True, timeout=15,
                       env={**os.environ, "PYTHONPATH": ""})
    if r.returncode != 0:
        return -1
    try:
        d = json.loads(r.stdout)
        return d.get("total_orphans", d.get("orphans", -1))
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

def purge_gbrain():
    """Purge soft-deleted gbrain pages and classify orphans."""
    r = subprocess.run(["gbrain", "purge-deleted-pages", "--older-than-hours", "72"],
                       capture_output=True, text=True, timeout=30,
                       env={**os.environ, "PYTHONPATH": ""})
    purged = r.returncode == 0
    return purged

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
    """Batch-digest completed QA evidence directories (≥48h old).

    A UUID directory is considered "digestible" when it has existed
    for ≥48 hours. Aggregate key signals to wiki page, then delete.
    """
    qa_dir = DREW_HOME / "P2-hippocampus" / "qa-evidence"
    if not qa_dir.exists():
        return 0, 0
    cut = time.time() - 48 * 86400
    uuid_dirs = [d for d in qa_dir.iterdir()
                 if d.is_dir() and len(d.name) == 36 and d.name.count("-") == 4
                 and d.stat().st_mtime < cut]
    if not uuid_dirs:
        return 0, 0

    wiki_dir = DREW_HOME / "P5-ego" / "wiki"
    wiki_dir.mkdir(parents=True, exist_ok=True)
    digested = 0
    for d in uuid_dirs:
        contract = d / "contract.json"
        if not contract.exists():
            continue
        try:
            data = json.loads(contract.read_text())
            # Append entry to digest log
            digest_log = wiki_dir / "qa-evidence-digest.md"
            title = data.get("title", data.get("task_id", d.name))
            entry = f"- `{d.name}` **{title}** — criteria: {len(data.get('criteria', []))}, digested: {datetime.now().strftime('%Y-%m-%d')}\n"
            MAX_ENTRIES = 100
            if digest_log.exists():
                old = digest_log.read_text()
                if entry not in old:
                    # Keep header/frontmatter + last MAX_ENTRIES entries
                    lines = old.splitlines()
                    header_end = 0
                    for i, l in enumerate(lines):
                        if l.startswith("Auto-digested"):
                            header_end = i + 2
                            break
                    entries = [l for l in lines[header_end:] if l.startswith("- `")]
                    recent = entries[-(MAX_ENTRIES - 1):]
                    body = "\n".join(lines[:header_end]) + "\n" + "\n".join(recent) + "\n" + entry
                    digest_log.write_text(body)
            else:
                header = "---\ntitle: QA Evidence Digest\ntype: index\nspace: meta\n---\n\n# QA Evidence Digest\n\nAuto-digested from raw evidence directories (48h TTL).\n\n"
                digest_log.write_text(header + entry)
            shutil.rmtree(d)
            digested += 1
        except:
            continue
    return digested, len(uuid_dirs)


def sync_wiki_to_gbrain():
    """Import P5-ego/wiki/ pages to gbrain."""
    wiki_dir = DREW_HOME / "P5-ego" / "wiki"
    if not wiki_dir.exists():
        return False
    r = subprocess.run(
        ["gbrain", "import", str(wiki_dir), "--no-embed"],
        capture_output=True, text=True, timeout=120,
        env={**os.environ, "PYTHONPATH": ""}
    )
    ok = r.returncode == 0
    if not ok:
        print(f"gbrain import stderr: {r.stderr[:500]}")
    return ok


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
    orphans = check_gbrain_orphans()
    stale = check_kanban_stale()
    stopped = check_cron_jobs()
    disk_pct = check_disk()

    sections = [
        ("🖥 프로세스", []),
        ("🧠 GBrain", []),
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

    sections[1] = ("🧠 GBrain",
                   [f"고아 페이지 {orphans}개"] if orphans > 0 else [])

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
        gbrain_purged = purge_gbrain()
        archived = archive_completed_kanban()
        sess_db_n, sess_db_sz = prune_state_sessions()
        sess_files_n, sess_files_sz = prune_memory_sessions()
        qa_digested, qa_total = digest_qa_evidence()
        wiki_synced = sync_wiki_to_gbrain()

        digest_items = [f"로그 {logs_removed}개 삭제" if logs_removed else "로그 정상",
                        f"cron output {cron_out_removed}개 삭제" if cron_out_removed else "cron output 정상",
                        "gbrain purge 완료" if gbrain_purged else "gbrain purge 실패",
                        f"kanban {archived}건 아카이브" if archived else "kanban 아카이브 없음"]
        if sess_db_n > 0:
            digest_items.append(f"state.db 세션 {sess_db_n}건 정리 ({sess_db_sz / 1024 / 1024:.0f}MB)")
        if sess_files_n > 0:
            digest_items.append(f"메모리 세션 {sess_files_n}파일 정리 ({sess_files_sz / 1024 / 1024:.0f}MB)")
        if qa_digested > 0:
            digest_items.append(f"QA evidence {qa_digested}/{qa_total}건 digest")
        digest_items.append(f"wiki→gbrain {'✅' if wiki_synced else '❌'}")
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

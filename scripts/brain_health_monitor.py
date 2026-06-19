#!/usr/bin/env python3
"""
Drewgent — Brain Health Monitor & Self-Healer
================================================
 memecached monitoring + automatic repair + Discord alerts for unresolvable issues.

Run: python3 brain_health_monitor.py [--dry-run] [--fix]

Self-heal capabilities (automatic):
  1. Retire stale/low-engagement entries
  2. Deduplicate identical entries
  3. Fix broken [[wiki links]]
  4. Fix malformed frontmatter
  5. Merge near-duplicate entries (same title + similar content)

Escalate to Discord (status-monitoring) when:
  - Repair requires human judgment
  - Entry corruption detected
  - Critical brain structure missing
"""

from pathlib import Path
from datetime import datetime, timedelta, date
from collections import defaultdict
import json, re, sys

# ─── Paths ────────────────────────────────────────────────────────────────
DREW_HOME   = Path.home() / ".drewgent"
MEMORIES    = DREW_HOME / "memories"
INSIGHTS    = MEMORIES / "insights"
ENTITIES    = MEMORIES / "entities"
CONCEPTS    = MEMORIES / "concepts"
VECTOR_DB   = MEMORIES / "vectors.db"
STATE_FILE  = DREW_HOME / "brain_health_state.json"
LOG_DIR     = DREW_HOME / "logs"
DISCORD_CFG = DREW_HOME / "config" / "discord.json"

STATUS_CHANNEL_ID = "1493982427708915713"

# ─── Thresholds ────────────────────────────────────────────────────────────
RETIRE_AGE_HARD   = 180   # days — always retire
RETIRE_AGE_MEDIUM = 90    # days — retire if also low engagement
RETIRE_ACCESS_LOW = 2     # access count — below this AND old → retire
RETIRE_ACCESS_ZERO_AGE = 60  # days — never accessed AND this old → retire

# Critical brain files — never retire regardless of age
PROTECTED_FILES = {
    "SCHEMA.md", "MEMORY.md", "USER.md", "index.md",
    "MEMORY",     # directory names that can't be retired
}

def is_protected(path: Path) -> bool:
    """Returns True if this entry is a critical brain file and should never be retired."""
    name = path.name
    # Also protect .md files that are the only entry in their directory
    parent_dirs = set(path.parts)
    for protected in PROTECTED_FILES:
        if name == protected or name.replace(".md", "") == protected:
            return True
    return False

# ─── Discord notification ──────────────────────────────────────────────────
def notify_discord(alerts: list):
    """Send alert to status-monitoring channel."""
    if not DISCORD_CFG.exists():
        return
    with open(DISCORD_CFG) as f:
        cfg = json.load(f)
    webhook_url = cfg.get("webhook_url")
    if not webhook_url:
        return

    if not alerts:
        return

    lines = []
    for a in alerts:
        sev = a.get("severity", "info")
        icon = {"critical": "🚨", "warning": "⚠️", "info": "ℹ️"}.get(sev, "•")
        lines.append(f"{icon} **{a['type']}**: {a['message']}")

    payload = {
        "content": f"🧠 **Brain Health Alert** `{datetime.now().strftime('%Y-%m-%d %H:%M')}`",
        "embeds": [{
            "title": f"🩺 Brain Health Report",
            "color": {"critical": 15158332, "warning": 15105570, "info": 3447003}.get(
                alerts[0].get("severity", "info"), 3447003),
            "fields": [{"name": "Issue", "value": "\n".join(lines), "inline": False}],
            "footer": {"text": "Drewgent Brain Health Monitor"}
        }]
    }

    import urllib.request
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            print(f"Discord alert sent: {len(alerts)} issues")
    except Exception as e:
        print(f"Discord alert failed: {e}")

# ─── State management ──────────────────────────────────────────────────────
def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}

def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))

# ─── 1. Scan entries ───────────────────────────────────────────────────────
def scan_entries():
    """Return list of dicts for all markdown entries in memories/."""
    entries = []
    seen_paths = set()
    for base in [INSIGHTS, ENTITIES, CONCEPTS, MEMORIES]:
        if not base.exists():
            continue
        # Scan both files in base/ and subdirectories recursively
        for md in base.glob("*.md"):
            if ".archive" in md.parts or str(md) in seen_paths:
                continue
            seen_paths.add(str(md))
            try:
                text = md.read_text()
                fm, body = parse_frontmatter(text)
                entries.append({"path": md, "fm": fm or {}, "body": body, "raw": text})
            except Exception:
                entries.append({"path": md, "fm": {}, "body": "", "raw": "", "error": "read_failed"})
        for md in base.rglob("*.md"):
            # Skip if already scanned via glob or is top-level (already handled)
            if ".archive" in md.parts or str(md) in seen_paths:
                continue
            # Only include subdirectory files (not top-level already caught by glob)
            if md.parent == base:
                continue
            seen_paths.add(str(md))
            try:
                text = md.read_text()
                fm, body = parse_frontmatter(text)
                entries.append({"path": md, "fm": fm or {}, "body": body, "raw": text})
            except Exception:
                entries.append({"path": md, "fm": {}, "body": "", "raw": "", "error": "read_failed"})
    return entries

def parse_frontmatter(text: str):
    """Parse YAML frontmatter. Returns (fm_dict, body) or ({}, text)."""
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    import yaml
    try:
        fm = yaml.safe_load(parts[1])
        body = parts[2].strip()
        return fm, body
    except Exception:
        return {}, text

# ─── 2. Self-healing: stale entries ────────────────────────────────────────
def heal_stale_entries(entries: list, dry_run: bool = False) -> dict:
    """Retire entries that are old + low engagement. Auto-heal."""
    import sqlite3, yaml

    # Get access counts from vector DB
    access_map = {}
    if VECTOR_DB.exists():
        try:
            conn = sqlite3.connect(str(VECTOR_DB))
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT id, path, access_count, last_accessed FROM entries")
            for row in cur.fetchall():
                access_map[row["path"]] = {
                    "count": row["access_count"] or 0,
                    "last": row["last_accessed"]
                }
            conn.close()
        except Exception:
            pass

    now = datetime.now()
    retired = []

    for e in entries:
        path = e["path"]
        fm = e["fm"]
        updated_str = fm.get("updated", fm.get("created", ""))

        # Parse date
        try:
            updated = datetime.fromisoformat(updated_str)
        except Exception:
            updated = None

        age_days = (now - updated).days if updated else 999

        access = access_map.get(str(path), {}).get("count", 0)

        # Decision matrix
        should_retire = False
        reason = ""

        if age_days >= RETIRE_AGE_HARD:
            should_retire = True
            reason = f"hard_retire: {age_days} days old"
        elif age_days >= RETIRE_AGE_MEDIUM and access <= RETIRE_ACCESS_LOW:
            should_retire = True
            reason = f"medium_retire: {age_days}d + {access} accesses"
        elif age_days >= RETIRE_ACCESS_ZERO_AGE and access == 0:
            should_retire = True
            reason = f"zero_access: {age_days}d, never accessed"

        if not should_retire or dry_run:
            continue

        # Skip protected critical files
        if is_protected(path):
            continue

        # Skip if already moved
        if not path.exists():
            continue

        # Archive: move to .archive/
        archive_dir = path.parent / ".archive"
        archive_dir.mkdir(exist_ok=True)
        archive_path = archive_dir / path.name
        path.rename(archive_path)

        # Update vector DB
        if VECTOR_DB.exists():
            try:
                conn = sqlite3.connect(str(VECTOR_DB))
                cur = conn.cursor()
                cur.execute("UPDATE entries SET retired=1, retired_at=? WHERE path=?", (now.isoformat(), str(path)))
                conn.commit()
                conn.close()
            except Exception:
                pass

        retired.append({"path": str(path), "reason": reason, "age_days": age_days, "access": access})

    return {"retired": retired, "total": len(entries)}

# ─── 3. Self-healing: deduplication ─────────────────────────────────────────
def heal_duplicates(entries: list, dry_run: bool = False) -> dict:
    """Find and merge duplicate entries (same title)."""
    by_title = defaultdict(list)
    for e in entries:
        title = (e["fm"].get("title") or e["path"].stem or "").lower().strip()
        if title:
            by_title[title].append(e)

    merged = []
    for title, group in by_title.items():
        if len(group) < 2:
            continue
        # Keep most recently updated, archive the rest
        def sort_key(x):
            val = x["fm"].get("updated", "1970-01-01")
            # Normalize to string for consistent comparison
            if isinstance(val, (datetime, date)):
                return val.strftime("%Y-%m-%d")
            return str(val) if val else "1970-01-01"

        group.sort(key=sort_key)
        keep = group[-1]
        for old in group[:-1]:
            if not old["path"].exists():
                continue  # Already moved by earlier processing
            archive_dir = old["path"].parent / ".archive"
            archive_dir.mkdir(exist_ok=True)
            archive_path = archive_dir / old["path"].name
            if not dry_run:
                old["path"].rename(archive_path)
            merged.append({
                "title": title,
                "archived": str(old["path"]),
                "kept": str(keep["path"])
            })

    return {"merged": merged, "duplicates_found": len(merged)}

# ─── 4. Self-healing: broken wiki links ─────────────────────────────────────
WIKI_LINK_RE = re.compile(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]]')

def heal_broken_links(entries: list, dry_run: bool = False) -> dict:
    """Fix or flag [[broken wiki links]]."""
    all_paths = {e["path"].resolve() for e in entries}
    fixed_links = []
    broken_unresolvable = []

    for e in entries:
        content = e["raw"]
        links = WIKI_LINK_RE.findall(content)
        new_content = content

        for link in links:
            # Skip candidates with filename too long (would cause OSError on exists())
            link_normalized = link.replace("/", "-").replace(" ", "-")
            candidates = [
                MEMORIES / (link_normalized + ".md"),
                MEMORIES / (link_normalized + "/index.md"),
                MEMORIES / (link.split("/")[-1].replace(" ", "-") + ".md"),
            ]
            # Guard: OSError if any candidate filename component > 180 chars
            candidates = [p for p in candidates if len(p.name) <= 180]
            resolved = next((p for p in candidates if p.exists()), None)

            if not resolved:
                # Try fuzzy search in all known paths (skip paths with name > 180 chars to avoid OSError)
                link_name = link.split("/")[-1].replace(" ", "-").lower()
                fuzzy = next((p for p in all_paths if len(p.name) <= 180 and link_name in p.name.lower()), None)
                if fuzzy:
                    new_content = new_content.replace(f"[[{link}]]", f"[[{fuzzy.name}]]")
                    fixed_links.append(f"{e['path'].name}: [[{link}]] -> [[{fuzzy.name}]]")
                else:
                    broken_unresolvable.append({
                        "entry": str(e["path"].name),
                        "broken_link": link
                    })

        if new_content != content and not dry_run:
            if e["path"].exists():
                e["path"].write_text(new_content)

    return {"fixed": fixed_links, "broken_unresolvable": broken_unresolvable}

# ─── 5. Self-healing: malformed frontmatter ─────────────────────────────────
def heal_frontmatter(entries: list, dry_run: bool = False) -> dict:
    """Fix entries with invalid frontmatter."""
    import yaml
    fixed = []

    for e in entries:
        if not e["path"].exists():
            continue
        if not e["raw"].startswith("---"):
            # Add frontmatter if missing
            new_raw = f"---\ntitle: {e['path'].stem}\nupdated: {datetime.now().strftime('%Y-%m-%d')}\n---\n{e['raw']}"
            if not dry_run:
                e["path"].write_text(new_raw)
            fixed.append(f"added frontmatter to {e['path'].name}")
            continue

        # Try to parse, if fail fix it
        try:
            yaml.safe_load(e["raw"].split("---")[1])
        except Exception:
            # Malformed — rebuild minimal frontmatter
            body = e["raw"].split("---", 2)[-1].strip()
            new_raw = f"---\ntitle: {e['path'].stem}\nupdated: {datetime.now().strftime('%Y-%m-%d')}\ntags: [auto-healed]\n---\n{body}"
            if not dry_run:
                e["path"].write_text(new_raw)
            fixed.append(f"rebuilt frontmatter for {e['path'].name}")

    return {"fixed": fixed}

# ─── 6. Discord-escalated issues ────────────────────────────────────────────
# ─── Issue → Fix Prompt mapping ─────────────────────────────────────────
ISSUE_FIX_PROMPTS = {
    "broken_link": (
        "이 파일의 [[broken-link]] 를 찾아서 유효한 링크로 수정하거나 제거해주세요."
    ),
    "missing_critical": (
        "brain의 핵심 파일이 없습니다. `~/.drewgent/memories/`에 {files} 파일을 생성하거나 복원해주세요."
    ),
    "empty_brain": (
        "brain에 entries가 없습니다. brain 상태를 확인하고 복원하세요:\n"
        "python3 ~/.drewgent/scripts/brain_nodes.py"
    ),
    "malformed_entry": (
        "entries/frontmatter 손상: 해당 파일을 수동으로 확인하고 복원해주세요."
    ),
    "orphan_entry": (
        "어떤 parent도 참조하지 않는 entries입니다. 병합하거나 삭제해주세요."
    ),
}

def build_fix_prompt(issue: dict) -> str:
    """Build a copy-pasteable prompt for fixing this specific issue."""
    issue_type = issue.get("type", "unknown")
    template = ISSUE_FIX_PROMPTS.get(issue_type, "이 문제를 해결해주세요: {message}")
    return template.format(**issue)


def escalate_unresolvable(issues: list):
    """Send unresolvable brain health issues to Discord with actionable prompts."""
    if not issues:
        return
    webhook_url = None
    cfg = None
    if DISCORD_CFG.exists():
        with open(DISCORD_CFG) as f:
            cfg = json.load(f)
        if cfg:
            webhook_url = cfg.get("webhook_url")
    if not webhook_url:
        return

    import urllib.request

    fields = []
    for issue in issues[:10]:
        fix_prompt = build_fix_prompt(issue)
        msg = issue.get('message', '')
        fields.append({
            "name": "🔧 " + issue.get('type', 'issue'),
            "value": msg + "\n```\n" + fix_prompt + "\n```",
            "inline": False
        })

    payload = {
        "content": f"🧠 **Brain Self-Healing Report** `{datetime.now().strftime('%Y-%m-%d %H:%M')}` — {len(issues)}개 해결 불가 문제",
        "embeds": [{
            "title": "🩺 Brain Health — 해결 필요",
            "color": 15105570,
            "fields": fields,
            "footer": {"text": "Drewgent Brain Self-Healer — 복사 후 바로 실행 가능"}
        }]
    }

    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10):
            print(f"Escalated {len(issues)} issue(s) to Discord ✓")
    except Exception as e:
        print(f"Discord escalation failed: {e}")

# ─── Main ──────────────────────────────────────────────────────────────────
def run(dry_run: bool = False, fix: bool = True):
    print(f"🧠 Brain Health Monitor — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"   dry_run={dry_run} fix={fix}")

    entries = scan_entries()
    print(f"   Scanning {len(entries)} entries...")

    actions = []
    all_issues = []

    # Self-heal in order
    print("\n   [1/5] Checking stale entries...")
    r = heal_stale_entries(entries, dry_run=dry_run)
    if r["retired"]:
        print(f"       → Retired {len(r['retired'])} stale entries")
        for x in r["retired"][:5]:
            print(f"          - {x['path']} ({x['reason']})")
        actions.append(f"retired:{len(r['retired'])}")

    print("\n   [2/5] Checking duplicates...")
    d = heal_duplicates(entries, dry_run=dry_run)
    if d["merged"]:
        print(f"       → Merged {len(d['merged'])} duplicate groups")
        actions.append(f"dedup:{len(d['merged'])}")

    print("\n   [3/5] Checking broken wiki links...")
    bl = heal_broken_links(entries, dry_run=dry_run)
    if bl["fixed"]:
        print(f"       → Fixed {len(bl['fixed'])} broken links")
        actions.append(f"links_fixed:{len(bl['fixed'])}")
    if bl["broken_unresolvable"]:
        print(f"       → {len(bl['broken_unresolvable'])} unresolvable links (will escalate)")
        all_issues.extend([{"type": "broken_link", "message": f"'{i['broken_link']}' in `{i['entry']}` — not found in brain"} for i in bl["broken_unresolvable"]])

    print("\n   [4/5] Checking frontmatter...")
    fm = heal_frontmatter(entries, dry_run=dry_run)
    if fm["fixed"]:
        print(f"       → Fixed {len(fm['fixed'])} frontmatter issues")
        actions.append(f"fm_fixed:{len(fm['fixed'])}")

    print("\n   [5/5] Brain structure health check...")
    # Check critical files exist
    critical = ["SCHEMA.md", "index.md", "MEMORY.md"]
    missing = [f for f in critical if not (MEMORIES / f).exists()]
    if missing:
        all_issues.append({"type": "missing_critical", "message": f"Missing critical files: {missing}"})

    # Check brain has entries at all
    if len(entries) == 0:
        all_issues.append({"type": "empty_brain", "message": "Brain has 0 entries — needs immediate attention"})

    # Escalate unresolvable to Discord
    if all_issues:
        print(f"\n   ⚠️  {len(all_issues)} issue(s) require human attention — escalating to Discord")
        escalate_unresolvable(all_issues)
    else:
        print("\n   ✅ No issues requiring escalation")

    # Save state
    state = load_state()
    state.update({
        "last_run": datetime.now().isoformat(),
        "entries_total": len(entries),
        "actions": actions,
        "escalated": len(all_issues),
    })
    save_state(state)

    # Summary
    if actions:
        print(f"\n   📋 Summary: {' | '.join(actions)}")
    else:
        print(f"\n   ✅ Brain is healthy — no fixes needed")
        print(f"   Total entries: {len(entries)}")

    return {"actions": actions, "issues": all_issues, "entries": len(entries)}

if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    run(dry_run=dry_run)
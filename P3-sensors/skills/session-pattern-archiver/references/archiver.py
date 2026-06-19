#!/usr/bin/env python3
"""
Session Pattern Archiver — Phase 3
Enhanced: Discord webhook + thread tracking + vault backlink integration

cron: every 2h
webhook: sessions→Discord DM/channel
backlink: auto-links to brain/, entities/, insights/, PROJECTS/, recent sessions
"""
import argparse, json, os, re, sys, time, urllib.request, urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

# ── Config ──────────────────────────────────────────────────────────────────
VAULT         = Path("/Volumes/drewgent_storage/_agent/MEMORY")
SESSIONS_DIR  = VAULT / "sessions"
PROJECTS_DIR  = VAULT / "wiki" / "projects"
ARCHIVE_DIR   = VAULT / "wiki" / "archive"

# ── Priority scan dirs for find_related_notes() ─────────────────────────────
SCAN_DIRS = [
    ("brain/",          3.0),   # highest: Drewgent brain rules
    ("entities/",       2.5),   # user preferences, communication style
    ("insights/",       2.0),   # prior insights
    ("PROJECTS/",       2.0),   # explicit projects
    ("compiled/",       1.5),   # summaries, approved insights
    ("knowledge_base/", 1.0),   # general KB
    ("wiki/",           0.8),   # wiki pages
]

# ── Session link cache (in-memory, rebuilt each run) ────────────────────────
_session_link_cache: list[dict] = []

def _env(key: str, fallback="") -> str:
    p = Path.home() / ".drewgent" / ".env"
    if p.exists():
        for line in p.read_text().splitlines():
            if line.startswith(key + "="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return os.environ.get(key, fallback)

DISCORD_WEBHOOK   = _env("DISCORD_WEBHOOK_URL", "")
AGENT_WEBHOOK     = "https://discord.com/api/webhooks/1489601604893282424/jJXSIb7YaQqjEAyUG3Tfik8XLQ36-yo2BWGMW1KpjCxmKUzsR15M9BNlE3X-cVM3fF0Q"
BOT_TOKEN         = _env("DISCORD_BOT_TOKEN", "")
CHANNEL_DIR       = Path.home() / ".drewgent" / "channel_directory.json"
THREAD_STATE_FILE = Path.home() / ".drewgent" / "discord_threads.json"
MINIMAX_KEY       = _env("MINIMAX_API_KEY", "")

TIMESTAMP   = datetime.utcnow()
TODAY       = TIMESTAMP.strftime("%Y-%m-%d")
YEAR_MONTH  = TIMESTAMP.strftime("%Y-%m")
INACTIVE_Hours = 2
BATCH_SIZE = 5  # messages per batch

# ── Phase 4: Incremental Session Note Templates ────────────────────────────

_SKELETON_TEMPLATE = """# Session: {title}
**Date**: {date}
**Participants**: {participants}

## 🎯 의도
## 🧠 사고방식
## ⚖️ 가치 판단
## 👁️ 맹점
## ✅ 결정 & 액션
## 🔗 관련 노트
## 📋 Follow-ups

---

<!-- 원본 대화 내용 -->
"""

_BATCH_MARKER = "<!-- Batch {n} @ {ts} -->"


def ensure_note(thread_id: str, title: str, channel_id: str,
                participants: str = "@humanerd") -> tuple[Path, str]:
    """
    Phase 4: Create an empty session note skeleton when a thread is created.
    Returns (filepath, vault_rel) for subsequent append_batch() calls.
    """
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    session_path = SESSIONS_DIR / YEAR_MONTH
    session_path.mkdir(parents=True, exist_ok=True)

    safe = re.sub(r'[^\w가-힣-]', '_', title)[:60]
    filename = f"{TODAY}_{safe}.md"
    filepath = session_path / filename

    if filepath.exists():
        filename = f"{TODAY}_{safe}_{TIMESTAMP.strftime('%H%M%S')}.md"
        filepath = session_path / filename

    vault_rel = f"sessions/{YEAR_MONTH}/{filepath.stem}"

    note = _SKELETON_TEMPLATE.format(
        title=title,
        date=TODAY,
        participants=participants,
    )
    filepath.write_text(note, encoding="utf-8")
    print(f"📝 Skeleton created: {vault_rel}")

    # Register in thread state
    state = load_thread_state()
    state[thread_id] = {
        "channel_id": channel_id,
        "title": title,
        "session_file": vault_rel,
        "batch_count": 0,
        "last_batch_at": None,
        "status": "active",
        "created_at": TIMESTAMP.isoformat(),
        "last_activity": TIMESTAMP.isoformat(),
    }
    save_thread_state(state)

    return filepath, vault_rel


def append_batch(thread_id: str, messages: list[str],
                 batch_num: int, ts: str) -> dict:
    """
    Phase 4: Append a batch of messages to the session note.
    Called every BATCH_SIZE messages or on inactivity.
    Updates incremental sections + logs raw messages at the bottom.
    """
    state = load_thread_state()
    if thread_id not in state:
        return {"success": False, "reason": "thread_not_tracked"}

    info = state[thread_id]
    session_file = info.get("session_file", "")
    if not session_file:
        return {"success": False, "reason": "no_session_file"}

    filepath = VAULT / session_file
    if not filepath.exists():
        return {"success": False, "reason": "file_not_found"}

    # ── LLM inference on this batch ─────────────────────────────────────────
    batch_text = "\n\n---\n\n".join(messages)
    patterns = infer_patterns(info.get("title", ""), messages)

    # ── Build incremental section entries ───────────────────────────────────
    def _sec(header: str, content: str) -> str:
        c = content.strip()
        if not c:
            return ""
        return f"- **[Batch {batch_num}]** {c}"

    entries = {
        "intent":     _sec("🎯 의도",      patterns.get("intent",     "")),
        "reasoning":  _sec("🧠 사고방식",  patterns.get("reasoning",  "")),
        "values":     _sec("⚖️ 가치 판단", patterns.get("values",     "")),
        "blindspots": _sec("👁️ 맹점",     patterns.get("blindspots", "")),
        "decisions":  _sec("✅ 결정 & 액션", patterns.get("decisions", "")),
    }

    # ── Load existing note, update sections ─────────────────────────────────
    note_lines = filepath.read_text(encoding="utf-8").splitlines(keepends=True)

    def _inject_after_header(lines: list[str], header: str,
                             entry: str) -> list[str]:
        """Find '## {header}' and append entry after its content block."""
        found = -1
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped == f"## {header}" or stripped == f"## {header} (Humanerd's Intent)" or stripped == f"## {header} (Reasoning Pattern)":
                found = i
                break
        if found < 0:
            return lines  # header not found, skip

        # Find end of this section (next ## heading or --- divider)
        end = len(lines)
        for j in range(found + 1, len(lines)):
            if lines[j].startswith("## "):
                end = j
                break
            if lines[j].startswith("---"):
                end = j
                break

        result = lines[:end] + [entry + "\n"] + lines[end:]
        return result

    SECTION_HEADERS = {
        "intent":     "🎯 의도",
        "reasoning":  "🧠 사고방식",
        "values":     "⚖️ 가치 판단",
        "blindspots": "👁️ 맹점",
        "decisions":  "✅ 결정 & 액션",
    }

    for key, entry in entries.items():
        if entry:
            note_lines = _inject_after_header(
                note_lines, SECTION_HEADERS[key], entry)

    # ── Append raw messages at the bottom ──────────────────────────────────
    marker = _BATCH_MARKER.format(n=batch_num, ts=ts)
    msg_block = f"\n{marker}\n"
    for m in messages:
        msg_block += f"{m}\n"

    # Insert before the last '---' divider if present
    for i in range(len(note_lines) - 1, -1, -1):
        if note_lines[i].startswith("---"):
            note_lines = note_lines[:i] + [msg_block + "\n"] + note_lines[i:]
            break
    else:
        note_lines.append(msg_block + "\n")

    filepath.write_text("".join(note_lines), encoding="utf-8")

    # Update batch counter
    state[thread_id]["batch_count"] = state[thread_id].get("batch_count", 0) + 1
    state[thread_id]["last_batch_at"] = TIMESTAMP.isoformat()
    state[thread_id]["last_activity"] = TIMESTAMP.isoformat()
    save_thread_state(state)

    print(f"  → Batch {batch_num} appended ({len(messages)} msgs)")

    return {
        "success": True,
        "batch_num": batch_num,
        "batch_count": state[thread_id]["batch_count"],
        "note": str(filepath.relative_to(VAULT)),
    }


def finalize_with_abstract(thread_id: str) -> dict:
    """
    Phase 4: Called on thread close/delete.
    Fetches ALL messages, LLM-infers abstract (using header structure),
    and inserts it after the metadata block.
    """
    state = load_thread_state()
    if thread_id not in state:
        return {"success": False, "reason": "thread_not_tracked"}

    info = state[thread_id]
    session_file = info.get("session_file", "")
    channel_id = info.get("channel_id", "")

    if not session_file:
        return {"success": False, "reason": "no_session_file"}

    filepath = VAULT / session_file
    if not filepath.exists():
        return {"success": False, "reason": "file_not_found"}

    # Fetch all messages
    all_messages = _fetch_thread_messages(thread_id, channel_id)
    if not all_messages:
        # Fallback: read what's already in the note
        note_text = filepath.read_text(encoding="utf-8")
        all_messages = ["[기록된 내용이 없습니다]"]

    # ── LLM Abstract (based on header structure) ─────────────────────────────
    SYSTEM_ABSTRACT = """당신은 분석가입니다. 아래 대화를 분석하여 Abstract를 작성하세요.

출력 형식 (항상 한국어로, 아래 헤더 구조를 그대로 따르세요):

## Abstract
- 🎯 **의도**: [1-2문장]
- 🧠 **사고방식**: [2-3문장]
- ⚖️ **가치 판단**: [2-3개 우선순위]
- 👁️ **맹점**: [1-2개]
- ✅ **결정 & 액션**: [핵심 결정 1-3개]

규칙: 추론이 불가능하면 해당 항목은 "[추론 불가]" 표시."""
    body = "\n\n---\n\n".join(all_messages[-30:])  # last 30 messages for abstract
    abstract_text = llm(SYSTEM_ABSTRACT, body, max_tokens=800)

    # Also scan related notes
    related_notes = find_related_notes(info.get("title", ""), " ".join(all_messages[-5:]))
    backlinks_block = _build_backlinks_block(related_notes)

    # ── Update the note ───────────────────────────────────────────────────────
    note_lines = filepath.read_text(encoding="utf-8").splitlines(keepends=True)

    # Find the position after the metadata block (first ## heading)
    insert_pos = 0
    for i, line in enumerate(note_lines):
        if line.startswith("## "):
            insert_pos = i
            break

    abstract_block = f"\n{abstract_text}\n\n---\n\n"

    # Inject after metadata, before first ## heading
    result = note_lines[:insert_pos] + [abstract_block] + note_lines[insert_pos:]

    # Update ## 🔗 관련 노트 section
    if backlinks_block:
        for i, line in enumerate(result):
            stripped = line.strip()
            if stripped == "## 🔗 관련 노트":
                # Find end of this section
                end = len(result)
                for j in range(i + 1, len(result)):
                    if result[j].startswith("## ") or result[j].startswith("---"):
                        end = j
                        break
                # Replace the empty section content
                if i + 1 < len(result) and result[i + 1].strip() == "":
                    result = result[:i + 1] + [backlinks_block + "\n"] + result[end:]
                break

    # Update last activity
    state[thread_id]["status"] = "archived"
    state[thread_id]["archived_at"] = TIMESTAMP.isoformat()
    save_thread_state(state)

    filepath.write_text("".join(result), encoding="utf-8")
    print(f"✅ Finalized: {filepath.relative_to(VAULT)}")

    # Update sessions index
    ensure_sessions_index()

    return {
        "success": True,
        "filepath": str(filepath.relative_to(VAULT)),
        "abstract": abstract_text[:200],
    }


def _build_backlinks_block(related_notes: dict) -> str:
    """Build a backlinks block from find_related_notes() output."""
    blocks = []
    for key, label in [
        ("brain",         "🧠 Brain"),
        ("entities",      "👤 Entities"),
        ("insights",      "💡 Insights"),
        ("projects",      "📁 Projects"),
        ("recent_sessions", "📋 Recent Sessions"),
    ]:
        notes = related_notes.get(key, [])
        if not notes:
            continue
        lines = "\n".join(f"- {n}" for n in notes[:3])
        blocks.append(f"**{label}**:\n{lines}")
    if not blocks:
        return ""
    return "\n".join(blocks)

# ── Discord Helpers ──────────────────────────────────────────────────────────
def discord_request(method: str, endpoint: str, data=None, token=BOT_TOKEN) -> dict:
    """Generic Discord API request"""
    url = f"https://discord.com/api/v10{endpoint}"
    headers = {"Authorization": f"Bot {token}", "Content-Type": "application/json"}
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, method=method, data=body, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"error": str(e)}

def get_channel_threads(channel_id: str) -> list[dict]:
    """Get archived + active threads in a channel"""
    threads = discord_request("GET", f"/channels/{channel_id}/threads/archived/public")
    if isinstance(threads, dict) and "error" in threads:
        return []
    active = discord_request("GET", f"/channels/{channel_id}/threads/archived/public")
    all_threads = threads if isinstance(threads, list) else []
    # Also fetch public archived
    pub_archived = discord_request("GET", f"/channels/{channel_id}/threads/archived/public")
    if isinstance(pub_archived, list):
        all_threads.extend(pub_archived)
    return all_threads

def load_thread_state() -> dict:
    if THREAD_STATE_FILE.exists():
        try:
            data = json.loads(THREAD_STATE_FILE.read_text())
            # Support legacy list format (array of thread IDs) and dict format
            if isinstance(data, list):
                return {tid: {} for tid in data}
            if isinstance(data, dict):
                return data
        except:
            pass
    return {}

def save_thread_state(state: dict):
    THREAD_STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))

def load_channel_dir() -> dict:
    if CHANNEL_DIR.exists():
        try:
            return json.loads(CHANNEL_DIR.read_text())
        except:
            pass
    return {}

def send_discord_embed(webhook_url: str, embed: dict,
                        add_reactions: bool = False,
                        channel_id: str = "") -> dict:
    """Send embed via Discord webhook. Returns dict with success + message_id."""
    payload = json.dumps({"embeds": [embed]}).encode()
    # Append ?wait=true to get message ID back
    url = webhook_url if "?" not in webhook_url else webhook_url.split("?")[0]
    url += "?wait=true"
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            body = json.loads(r.read())
            msg_id = body.get("id", "")
            if add_reactions and msg_id and channel_id and BOT_TOKEN:
                _add_reactions(channel_id, msg_id)
            return {"success": True, "message_id": msg_id}
    except Exception as e:
        print(f"  [Webhook error] {e}")
        return {"success": False, "message_id": ""}


def _add_reactions(channel_id: str, message_id: str):
    """Add approve/reject reactions to a message using bot token."""
    for emoji in ["👍", "👎"]:
        # URL-encode the emoji for Discord API
        encoded = urllib.parse.quote(emoji)
        discord_request(
            "PUT",
            f"/channels/{channel_id}/messages/{message_id}/reactions/{encoded}/%40me",
            token=BOT_TOKEN
        )

def send_dm(user_id: str, content: str) -> bool:
    """Send DM to user via Discord Bot API"""
    # Create DM channel first
    resp = discord_request("POST", "/users/@me/channels", {"recipient_id": user_id})
    if "id" not in resp:
        print(f"  [DM failed] {resp}")
        return False
    channel_id = resp["id"]
    # Send message
    msg_resp = discord_request("POST", f"/channels/{channel_id}/messages", {"content": content})
    return "id" in msg_resp

# ── LLM ─────────────────────────────────────────────────────────────────────
def llm(system: str, user: str, max_tokens: int = 1500) -> str:
    if not MINIMAX_KEY:
        return "[LLM_UNAVAILABLE]"
    try:
        payload = {
            "model": "MiniMax-M2",
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
        }
        req = urllib.request.Request(
            "https://api.minimax.io/v1/chat/completions",
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {MINIMAX_KEY}",
                "Content-Type": "application/json",
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            result = json.loads(resp.read())
        return result["choices"][0]["message"]["content"] or ""
    except Exception as e:
        return f"[LLM_ERROR: {e}]"

# ── Pattern Inference ────────────────────────────────────────────────────────
SYSTEM_PATTERNS = """당신은 분석가입니다. 주어진 대화를 분석하여 판단 패턴을 추출하세요.

출력 형식 (항상 한국어로):
## 🎯 의도
[1-3문장: 이 작업/대화의目的是 무엇이었나]

## 🧠 사고방식
[2-4문장: 문제를 어떻게 풀어가려 했나, 왜 이 방법을 선택했나]

## ⚖️ 가치 판단
[핵심优先순위 2-3개: 무엇을 더 중요하게 여겼고, 무엇을权衡했다가牺牲했나]

## 👁️ 맹점
[2-3개: 자주 놓치는 것, 에이전트가 대신 확인해줘야 할 것]

## ✅ 결정 & 액션
[구체적 결정/액션 1-5개: "- [결정/액션 내용] → 이유: ..., 다음: ..."]

## 📋 Follow-ups
[명시적 다음 단계 1-3개: "- [ ] [who does what by when]"]

규칙: 추론이 불가능하면 "[추론 불가]" 표시. 절대 만들어내지 마라."""

KEY_MAP = {
    "intent": "🎯 의도",
    "reasoning": "🧠 사고방식",
    "values": "⚖️ 가치 판단",
    "blindspots": "👁️ 맹점",
    "decisions": "✅ 결정 & 액션",
    "followups": "📋 Follow-ups",
}

def infer_patterns(thread_title: str, messages: list[str]) -> dict:
    body = f"## Thread Title: {thread_title}\n\n" + "\n\n---\n\n".join(messages[-20:])
    result = llm(SYSTEM_PATTERNS, body, max_tokens=1200)

    sections = {}
    current_key = None
    for line in result.split("\n"):
        if line.startswith("## "):
            current_key = line.strip("# ").strip()
            sections[current_key] = []
        elif current_key:
            sections[current_key].append(line)

    normalized = {}
    for norm_key, llm_key in KEY_MAP.items():
        normalized[norm_key] = "\n".join(sections.get(llm_key, []))
    for k, v in sections.items():
        if k not in KEY_MAP.values():
            normalized[k] = "\n".join(v)
    return normalized

# ── Session Note Generator ──────────────────────────────────────────────────
SESSION_TEMPLATE = """# Session: {title}
**Date**: {date}
**Trigger**: {trigger}
**Participants**: {participants}

## 🎯 의도 (Humanerd's Intent)
{intent}

## 🧠 사고방식 (Reasoning Pattern)
{reasoning}

## ⚖️ 가치 판단 (Value Judgments)
{values}

## 👁️ 맹점 (Blind Spots)
{blindspots}

## ✅ 결정 & 액션 (Decisions & Actions)
{decisions}

## 🔗 관련 노트 (Vault Backlinks)
{backlinks_block}

## 📋 Follow-ups
{followups}

## Meta
**Archived**: {archived_ts}
**Pattern completeness**: {completeness}
**Source thread**: {thread_url}
"""

def make_session_note(title, trigger, participants, patterns,
                      backlinks_block, followups, thread_url, completeness):
    defaults = {s: "[아직 기록되지 않음 — /sync-obsidian로 보완 가능]"
               for s in ["intent", "reasoning", "values", "blindspots", "decisions"]}
    defaults.update({k: v for k, v in patterns.items() if k in defaults})
    return SESSION_TEMPLATE.format(
        title=title, date=TODAY, trigger=trigger, participants=participants,
        intent=defaults["intent"],
        reasoning=defaults["reasoning"],
        values=defaults["values"],
        blindspots=defaults["blindspots"],
        decisions=defaults["decisions"],
        backlinks_block=backlinks_block,
        followups=followups,
        archived_ts=TIMESTAMP.strftime("%Y-%m-%d %H:%M"),
        completeness=completeness,
        thread_url=thread_url,
    )

# ── Project Linker ────────────────────────────────────────────────────────────
def find_related_project(title: str, body: str = "") -> list[Path]:
    if not PROJECTS_DIR.exists():
        return []
    combined = (title + " " + body).lower()
    candidates = []
    for p in PROJECTS_DIR.rglob("*.md"):
        name = p.stem.lower().replace("_", " ").replace("-", " ")
        if any(word in combined for word in name.split() if len(word) > 3):
            candidates.append(p)
    return candidates[:3]

def add_session_link(project_path: Path, session_link: str):
    try:
        content = project_path.read_text(encoding="utf-8")
        marker = "\n## Sessions\n"
        if marker not in content:
            content += f"\n{marker}"
        entry = f"- [[{session_link}]]\n"
        if entry.strip() in content:
            return
        parts = content.rsplit("\n## ", 1)
        if len(parts) == 2:
            content = parts[0] + f"\n{marker}" + entry + "\n## " + parts[1]
        else:
            content += entry
        project_path.write_text(content, encoding="utf-8")
        print(f"  → Linked to {project_path.name}")
    except Exception as e:
        print(f"  → Link failed: {e}")


# ── Vault-wide Related Notes Finder ─────────────────────────────────────────
import unicodedata

def _normalize(text: str) -> str:
    """Korean-friendly text normalization for keyword matching."""
    return (
        unicodedata.normalize("NFC", text)
        .lower()
        .replace("_", " ")
        .replace("-", " ")
    )

def _extract_keywords(title: str, body: str = "") -> list[str]:
    """Extract meaningful keywords from title + optional body text."""
    combined = _normalize(title + " " + body)
    # Strip wiki-links, URLs, code fences, frontmatter
    combined = re.sub(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", combined)
    combined = re.sub(r"https?://\S+", "", combined)
    combined = re.sub(r"```[\s\S]*?```", "", combined)
    combined = re.sub(r"---\n[\s\S]*?---", "", combined)
    # Keep only meaningful tokens: Korean (2+ chars), English (3+ chars)
    tokens = re.findall(r"[가-힣]{2,}|[a-zA-Z]{3,}", combined)
    # Filter stopwords (very common terms that add no signal)
    stopwords = {"the", "and", "for", "was", "this", "that", "with", "have", "from",
                 "which", "when", "then", "there", "their", "also", "were", "all",
                 "not", "are", "but", "they", "you", "our", "has", "been", "would",
                 "could", "should", "what", "how", "why", "who", "where", "your"}
    return [t for t in tokens if t.lower() not in stopwords]

def find_related_notes(title: str, body: str = "", limit: int = 8) -> dict[str, list]:
    """
    Scan entire vault for notes related to this session.
    Returns dict with keys: brain, entities, insights, projects, recent_sessions
    Each value is a list of (score, path, rel_path) tuples.
    """
    global _session_link_cache

    # Rebuild session cache once per run
    if not _session_link_cache:
        _session_link_cache = []
        if SESSIONS_DIR.exists():
            for fp in sorted(SESSIONS_DIR.rglob("*.md"), reverse=True):
                # Exclude index files
                if fp.stem.lower() == "index":
                    continue
                vault_rel = str(fp.relative_to(VAULT)).replace(".md", "")  # "sessions/2026-04/file"
                _session_link_cache.append({
                    "path": fp,
                    "rel": vault_rel,     # vault-relative: "sessions/2026-04/file"
                    "stem": fp.stem,
                    "mtime": fp.stat().st_mtime,
                })

    keywords = _extract_keywords(title, body)
    if not keywords:
        return {"brain": [], "entities": [], "insights": [], "projects": [], "recent_sessions": []}

    scored: dict[str, list] = {k: [] for k in ["brain", "entities", "insights", "projects", "recent_sessions"]}

    for subdir, priority in SCAN_DIRS:
        target_key = subdir.rstrip("/").split("/")[-1]  # "brain", "entities"...
        if target_key == "wiki":
            continue  # handled separately via wiki/index.md
        dir_path = VAULT / subdir
        if not dir_path.exists():
            continue
        for fp in dir_path.rglob("*.md"):
            if fp.stem.lower() == "index" or fp.stem.lower().startswith("folder_readme"):
                continue
            norm_name = _normalize(fp.stem)
            # Score by keyword overlap in filename
            score = sum(1 for kw in keywords
                        if kw.lower() in norm_name or norm_name in kw.lower())
            if score > 0:
                rel = str(fp.relative_to(VAULT))
                scored.get(target_key, scored["projects"]).append(
                    (score * priority, fp, rel.replace(".md", ""))
                )

    # Always include recent sessions (top 5 by mtime, excluding self)
    recent = sorted(_session_link_cache, key=lambda x: x["mtime"], reverse=True)[:5]
    scored["recent_sessions"] = [(1.0, s["path"], s["rel"]) for s in recent]

    # Finalize: sort each list, cap at limit — return flat list of wiki-links
    result = {}
    for key, items in scored.items():
        items.sort(reverse=True, key=lambda x: x[0])
        result[key] = [wiki_link for _, fp, rel in items[:limit]
                       if (wiki_link := _to_wiki_link(rel))]
    return result

def _to_wiki_link(rel_path: str) -> str:
    """Convert vault-relative path to Obsidian wiki-link format."""
    # sessions/2026-04/file → [[sessions/2026-04/file]]
    # brain/P0_brainstem/rule → [[brain/P0_brainstem/rule]]
    return "[[" + rel_path + "]]"

def _format_related_block(notes: list[str], label: str) -> str:
    if not notes:
        return f"**{label}**: —\n"
    lines = "\n".join(f"- {n}" for n in notes)
    return f"**{label}**:\n{lines}\n"

# ── Sessions Index Manager ───────────────────────────────────────────────────
def ensure_sessions_index(new_session_rel: str = ""):
    """
    Create / update sessions/index.md.
    Lists all months and recent sessions for quick nav.
    """
    INDEX_FILE = SESSIONS_DIR / "index.md"
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

    # Gather all months
    months: dict[str, list] = {}
    if SESSIONS_DIR.exists():
        for fp in SESSIONS_DIR.rglob("*.md"):
            if fp.stem.lower() == "index":
                continue
            # Path like sessions/2026-04/file.md
            parts = fp.relative_to(SESSIONS_DIR).parts
            if len(parts) >= 2 and parts[0].startswith("20"):
                month = parts[0]
                if month not in months:
                    months[month] = []
                rel = str(fp.relative_to(SESSIONS_DIR)).replace(".md", "")
                vault_rel = str(fp.relative_to(VAULT)).replace(".md", "")  # includes "sessions/" prefix
                title = _session_title_from_path(fp)
                months[month].append((fp.stem, title, rel, vault_rel))

    # Build month sections sorted newest first
    month_sections = []
    for month in sorted(months.keys(), reverse=True):
        entries = sorted(months[month], key=lambda x: x[0], reverse=True)
        lines = [f"### {month}"]
        for stem, title, rel, vault_rel in entries[:10]:  # cap at 10 per month in index
            wl = _to_wiki_link(vault_rel)  # vault_rel already includes "sessions/" prefix
            lines.append(f"- {wl}  \n  *{title[:60]}*")
        month_sections.append("\n".join(lines))

    divider = "\n\n---\n\n".join(month_sections)
    content = f"""# Sessions Index

**Auto-generated by Drewgent Session Archiver**  
**Last updated**: {TIMESTAMP.strftime("%Y-%m-%d %H:%M")}

## Overview
- **Total sessions**: {sum(len(v) for v in months.values())}
- **Months tracked**: {len(months)}

---

## Sessions by Month

{divider}
"""
    INDEX_FILE.write_text(content, encoding="utf-8")
    print(f"  → Updated sessions/index.md ({sum(len(v) for v in months.values())} sessions)")


def _session_title_from_path(fp: Path) -> str:
    """Extract readable title from session filename."""
    name = fp.stem
    # Format: 2026-04-12_dev-humanerd____agent-chat___topic-name____topic_123456
    parts = name.split("_")
    if len(parts) >= 4:
        # Try to find a meaningful title segment
        for part in parts[3:]:
            cleaned = re.sub(r"^[0-9]+$", "", part).strip()
            if len(cleaned) > 5:
                return cleaned.replace("-", " ").replace("__", " / ")
    return fp.stem.replace("_", " ").replace("-", " ")

# ── Clarify Message Builder ──────────────────────────────────────────────────
def build_clarify_embed(thread_title: str) -> dict:
    return {
        "title": f"📝 세션 패턴 정리 — {thread_title}",
        "color": 0x7C3AED,
        "description": "이 대화의 판단 패턴을 파악하면, 에이전트가 더 잘 작동해요.\n\n**아래 3가지에 대해 답해주세요:**",
        "fields": [
            {
                "name": "🎯 의도",
                "value": "이 대화에서 실제로 무엇을 판단/결정했나요?\n"
                         "에이전트가 기억해야 할 핵심 판단은 뭔가요?",
                "inline": False,
            },
            {
                "name": "⚖️ 가치",
                "value": "이 대화에서 만들어진 가치는 무엇인가요?\n"
                         "무엇을優先시했고, 무엇을权衡했나요?",
                "inline": False,
            },
            {
                "name": "👁️ 맹점",
                "value": "놓치기 쉬운 것은?\n"
                         "에이전트가 대신 확인해야 할 것은 무엇인가요?",
                "inline": False,
            },
        ],
        "footer": {"text": "👍 승인 → 아카이브  |  👎 거절 → 삭제"},
        "timestamp": TIMESTAMP.isoformat(),
    }

# ── Clarify Reaction Checker ──────────────────────────────────────────────────
def check_clarify_reactions() -> dict:
    """Check pending clarify messages for 👍/👎 reactions, then archive or delete."""
    state = load_thread_state()
    results = []
    for tid, info in list(state.items()):
        msg_id = info.get("clarify_msg_id", "")
        channel_id = info.get("channel_id", "")
        if not msg_id or not channel_id:
            continue
        # Fetch message reactions
        reaction_data = discord_request(
            "GET",
            f"/channels/{channel_id}/messages/{msg_id}",
            token=BOT_TOKEN
        )
        if isinstance(reaction_data, dict) and "reactions" not in reaction_data:
            # Try reactions endpoint
            reaction_data = discord_request(
                "GET",
                f"/channels/{channel_id}/messages/{msg_id}",
                token=BOT_TOKEN
            )
        # Count reactions manually from message object
        reactions = {}
        msg_reactions = reaction_data.get("reactions", []) if isinstance(reaction_data, dict) else []
        for r in msg_reactions:
            emoji = r.get("emoji", {}).get("name", "")
            count = r.get("count", 0)
            reactions[emoji] = count

        thumbs_up = reactions.get("👍", 0)
        thumbs_down = reactions.get("👎", 0)

        if thumbs_up == 0 and thumbs_down == 0:
            continue  # No decision yet

        session_file = info.get("session_file", "")
        title = info.get("title", tid)

        if thumbs_up > 0:
            # Approve → keep (update completeness to full)
            if session_file:
                path = SESSIONS_DIR / session_file
                if path.exists():
                    content = path.read_text(encoding="utf-8")
                    content = content.replace(
                        "**Pattern completeness**: partial",
                        "**Pattern completeness**: full"
                    )
                    path.write_text(content, encoding="utf-8")
                    print(f"  ✅ Approved: {session_file}")
            # Clear clarify state so it's not re-checked
            info.pop("clarify_msg_id", None)
            info.pop("session_file", None)
            info["status"] = "approved"
            results.append({"thread_id": tid, "action": "approved", "title": title})

        elif thumbs_down > 0:
            # Reject → delete session file
            if session_file:
                path = SESSIONS_DIR / session_file
                if path.exists():
                    path.unlink()
                    print(f"  🗑️ Deleted: {session_file}")
            # Move thread to deleted state
            info["status"] = "deleted"
            info.pop("clarify_msg_id", None)
            info.pop("session_file", None)
            results.append({"thread_id": tid, "action": "deleted", "title": title})

        state[tid] = info

    save_thread_state(state)
    return results


# ── Archive Session (Core) ────────────────────────────────────────────────────
def _build_backlinks_block(related_notes: dict) -> str:
    """Build the backlinks section for a session note."""
    blocks = []
    # brain rules
    if related_notes.get("brain"):
        blocks.append(_format_related_block(related_notes["brain"], "🧠 Brain Rules"))
    # entities (user preferences)
    if related_notes.get("entities"):
        blocks.append(_format_related_block(related_notes["entities"], "👤 Entities"))
    # insights
    if related_notes.get("insights"):
        blocks.append(_format_related_block(related_notes["insights"], "💡 Insights"))
    # projects
    if related_notes.get("projects"):
        blocks.append(_format_related_block(related_notes["projects"], "📁 Projects"))
    # recent sessions
    if related_notes.get("recent_sessions"):
        blocks.append(_format_related_block(related_notes["recent_sessions"], "📂 Recent Sessions"))
    if not blocks:
        return "_관련 노트를 찾을 수 없습니다. vault를 탐색해보세요._"
    return "\n".join(blocks)


def archive_session(title: str, messages: list[str],
                    participants: str, trigger: str,
                    thread_url: str = "",
                    ask_clarify: bool = True,
                    webhook_url: str = "",
                    channel_id: str = "",
                    thread_id: str = "") -> dict:

    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    safe = re.sub(r'[^\w가-힣-]', '_', title)[:60]
    filename = f"{TODAY}_{safe}.md"
    session_path = SESSIONS_DIR / YEAR_MONTH
    session_path.mkdir(parents=True, exist_ok=True)
    filepath = session_path / filename

    if filepath.exists():
        filename = f"{TODAY}_{safe}_{TIMESTAMP.strftime('%H%M%S')}.md"
        filepath = session_path / filename

    patterns = infer_patterns(title, messages)
    # Full vault scan for related notes
    related_notes = find_related_notes(title, " ".join(messages[-5:]))
    backlinks_block = _build_backlinks_block(related_notes)
    followups = patterns.get("followups", "[명시된 follow-up 없음]")

    note = make_session_note(
        title=title, trigger=trigger, participants=participants,
        patterns=patterns, backlinks_block=backlinks_block, followups=followups,
        thread_url=thread_url,
        completeness="inferred" if not ask_clarify else "partial",
    )
    filepath.write_text(note, encoding="utf-8")
    print(f"✅ Saved: {filepath.relative_to(VAULT)}")

    # Update sessions index
    ensure_sessions_index()

    # Link to related projects (legacy compat — still adds ## Sessions section)
    related_projects = find_related_project(title, " ".join(messages[-5:]))
    for proj in related_projects:
        add_session_link(proj, f"sessions/{YEAR_MONTH}/{filepath.stem}")

    # Send clarify DM/embed with reactions
    if ask_clarify and (webhook_url or AGENT_WEBHOOK):
        embed = build_clarify_embed(title)
        wh = webhook_url or AGENT_WEBHOOK
        result = send_discord_embed(wh, embed, add_reactions=True, channel_id=channel_id)
        msg_id = result.get("message_id", "")
        print(f"  → Clarify embed sent to {wh[:60]}...")
        if msg_id:
            print(f"  → 👍👎 reactions added (msg_id: {msg_id})")
            if thread_id:
                state = load_thread_state()
                if thread_id in state:
                    state[thread_id]["clarify_msg_id"] = msg_id
                    state[thread_id]["session_file"] = str(filepath.relative_to(SESSIONS_DIR))
                else:
                    state[thread_id] = {
                        "channel_id": channel_id,
                        "title": title,
                        "clarify_msg_id": msg_id,
                        "session_file": str(filepath.relative_to(SESSIONS_DIR)),
                        "status": "clarify_pending",
                    }
                save_thread_state(state)

    return {
        "filepath": str(filepath.relative_to(VAULT)),
        "related_notes": related_notes,
        "completeness": "inferred",
    }

# ── Thread Tracker ────────────────────────────────────────────────────────────
def track_thread(thread_id: str, channel_id: str, title: str,
                 last_activity: datetime, status: str = "active"):
    state = load_thread_state()
    state[thread_id] = {
        "channel_id": channel_id,
        "title": title,
        "last_activity": last_activity.isoformat(),
        "status": status,
        "archived_at": TIMESTAMP.isoformat() if status == "archived" else None,
    }
    save_thread_state(state)

def discord_snowflake_time(snowflake_id: str) -> datetime:
    """Convert Discord snowflake ID to datetime (UTC)"""
    try:
        parts = snowflake_id.split(":")
        sid = int(parts[-1])  # thread ID is last segment
        ms = (sid >> 22) + 1420070400000  # Discord epoch in ms
        return datetime.utcfromtimestamp(ms / 1000)
    except Exception:
        return TIMESTAMP  # fallback to now

def detect_inactive_threads() -> list[tuple]:
    """Find threads inactive for >2h that haven't been archived"""
    state = load_thread_state()
    inactive = []
    cutoff = TIMESTAMP - timedelta(hours=INACTIVE_Hours)

    # Handle list format (simple [thread_id] list) — convert to dict
    if isinstance(state, list):
        channel_dir = load_channel_dir()
        discord_channels = channel_dir.get("platforms", {}).get("discord", [])
        thread_map = {c.get("thread_id"): c for c in discord_channels if isinstance(c, dict)}
        for tid in state:
            tinfo = thread_map.get(tid, {})
            status = "archived" if tinfo.get("archived", False) else "active"
            # Use snowflake timestamp as last_activity
            last_ts = discord_snowflake_time(tid)
            inactive.append((tid, {
                "channel_id": tinfo.get("id", "").split(":")[0] if ":" in tinfo.get("id", "") else "",
                "title": tinfo.get("name", "Unknown"),
                "last_activity": last_ts.isoformat(),
                "status": status,
            }))
        return inactive

    # Handle dict format (thread_id -> metadata)
    if isinstance(state, dict):
        for thread_id, info in state.items():
            if info.get("status") != "active":
                continue
            try:
                last = datetime.fromisoformat(info["last_activity"])
            except Exception:
                last = discord_snowflake_time(thread_id)
            if last < cutoff:
                inactive.append((thread_id, info))
    return inactive

# ── Channel Scanner ──────────────────────────────────────────────────────────
def scan_all_channels_for_threads() -> list[dict]:
    """Scan all known channels for recent/archived threads"""
    channel_dir = load_channel_dir()
    all_threads = []

    # channel_directory.json has structure: {"updated_at": "...", "platforms": {"discord": [...], ...}}
    platforms = channel_dir.get("platforms", channel_dir)
    discord_channels = platforms if isinstance(platforms, dict) else {"discord": platforms}

    for platform, channels in discord_channels.items():
        if not isinstance(channels, list):
            continue
        for info in channels:
            if isinstance(info, dict):
                # Skip thread entries — only scan parent channels
                if info.get("type") in ("thread", "group"):
                    continue
                cid = info.get("id") or info.get("channel_id")
            else:
                continue
            if not cid:
                continue
            try:
                threads = get_channel_threads(cid)
                for t in threads:
                    t["_channel"] = info.get("name", platform)
                    t["_channel_id"] = cid
                all_threads.extend(threads)
            except Exception as e:
                print(f"  [Scan error] {info.get('name', cid)}: {e}")

    return all_threads

# ── Main Commands ─────────────────────────────────────────────────────────────
def cmd_archive(args) -> dict:
    return archive_session(
        title=args.title,
        messages=args.messages or [],
        participants=args.participants,
        trigger=args.trigger or "manual",
        thread_url=args.thread_url or "",
        ask_clarify=not args.no_clarify,
        webhook_url=args.webhook or "",
    )


def cmd_archive_thread_event(args) -> dict:
    """Archive a session triggered by a Discord thread close/delete event.
    Fetches messages from the Discord API for this thread, then archives.
    """
    # Fetch thread messages via Discord API
    thread_messages = _fetch_thread_messages(args.thread_id, args.channel_id)
    if not thread_messages:
        print(f"  [Warn] No messages fetched for thread {args.thread_id}, using placeholder")
        thread_messages = [f"[Discord thread {args.trigger_type} — messages unavailable]"]

    result = archive_session(
        title=args.title,
        messages=thread_messages,
        participants=args.participants or "Discord thread",
        trigger=args.trigger_type,  # "thread_close" or "thread_delete"
        thread_url=f"https://discord.com/channels/{args.guild_id or args.channel_id}/{args.thread_id}",
        ask_clarify=False,  # Auto-archive: no clarify
        channel_id=args.channel_id,
        thread_id=args.thread_id,
    )
    # Mark thread as archived in state
    state = load_thread_state()
    if args.thread_id in state:
        state[args.thread_id]["status"] = "archived"
        state[args.thread_id]["archived_at"] = TIMESTAMP.isoformat()
        save_thread_state(state)
    return result


def _fetch_thread_messages(thread_id: str, channel_id: str) -> list[str]:
    """Fetch recent messages from a Discord thread via API."""
    token = BOT_TOKEN
    if not token:
        return []

    url = f"https://discord.com/api/v10/channels/{thread_id}/messages"
    headers = {
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json",
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
        if not isinstance(data, list):
            return []
        messages = []
        for msg in data[-50:]:  # last 50 messages
            author = msg.get("author", {}).get("username", "unknown")
            content = msg.get("content", "")
            if content:
                ts = msg.get("timestamp", "")[:16]
                messages.append(f"[{ts}] {author}: {content}")
        return messages
    except Exception as e:
        print(f"  [Thread fetch error] {e}")
        return []

def cmd_inactivity_check() -> dict:
    """Check all tracked threads for 2h+ inactivity.
    Builds state from channel_directory.json (no bot token required for detection).
    """
    import threading

    print(f"\n=== Inactivity Check @ {TIMESTAMP.strftime('%Y-%m-%d %H:%M')} ===", flush=True)

    # Load existing tracked state FIRST — preserve archived status
    existing_state = load_thread_state()
    tracked_ids = set(existing_state) if isinstance(existing_state, list) else set(existing_state.keys())

    # Build fresh thread_map from channel_directory.json
    channel_dir = load_channel_dir()
    discord_channels = channel_dir.get("platforms", {}).get("discord", [])
    cutoff = TIMESTAMP - timedelta(hours=INACTIVE_Hours)

    # Start from existing_state to preserve archived/clarify_pending status
    new_state: dict = dict(existing_state) if isinstance(existing_state, dict) else {}

    inactive = []
    for c in discord_channels:
        if not isinstance(c, dict) or c.get("type") != "thread":
            continue
        tid = c.get("thread_id")
        if not tid:
            continue
        created = discord_snowflake_time(tid)
        channel_id = c.get("id", "").split(":")[0] if ":" in c.get("id", "") else ""

        # Only update if not already tracked (preserve existing status/archived_at)
        # Use setdefault so empty legacy entries get merged title from channel_dir
        entry = new_state.setdefault(tid, {})
        if "title" not in entry:
            entry.update({
                "channel_id": channel_id,
                "title": c.get("name", "Unknown"),
                "last_activity": created.isoformat(),
                "status": entry.get("status", "active"),
            })

        # Check for inactivity — skip already-archived threads
        if new_state[tid].get("status") == "archived":
            continue
        if tid in existing_state and existing_state.get(tid, {}).get("status") == "archived":
            continue

        try:
            last = datetime.fromisoformat(new_state[tid]["last_activity"])
            if last.tzinfo:
                last = last.replace(tzinfo=None)
        except Exception:
            last = created
        if last < cutoff:
            inactive.append((tid, new_state[tid]))

    print(f"  Found {len(inactive)} inactive threads", flush=True)

    # Save updated state (preserves archived status from existing_state)
    save_thread_state(new_state)

    results = []
    for thread_id, info in inactive:
        messages = [
            f"[Auto-archived after {INACTIVE_Hours}h inactivity]",
            f"Last active: {info.get('last_activity', 'unknown')}",
            f"Status: {info.get('status', 'active')}",
        ]

        result = None
        error_msg = None

        def make_archive_target(tid, tinfo, messages, result_holder):
            def _target():
                try:
                    result_holder[0] = archive_session(
                        title=tinfo["title"],
                        messages=messages,
                        participants="[tracked]",
                        trigger="inactivity",
                        thread_url=f"https://discord.com/channels/{tinfo.get('channel_id', '')}/{tid}",
                        ask_clarify=False,
                        channel_id=tinfo.get("channel_id", ""),
                        thread_id=tid,
                    )
                except Exception as e:
                    result_holder[1] = str(e)
            return _target

        result_holder: list = [None, None]  # [result, error_msg]
        t = threading.Thread(target=make_archive_target(thread_id, info, messages, result_holder))
        t.daemon = True
        t.start()
        t.join(timeout=20)
        result, error_msg = result_holder[0], result_holder[1]

        if error_msg:
            print(f"    [warn] Archive failed: {error_msg}", flush=True)
            results.append({"error": error_msg, "thread_id": thread_id})
            continue

        if result is None:
            print(f"    [warn] Archive returned None — skipping", flush=True)
            results.append({"error": "No result", "thread_id": thread_id})
            continue

        results.append(result)

        # Mark as archived in state — persist IMMEDIATELY so crash/cancel doesn't lose progress
        session_rel = result.get("filepath", "")
        new_state[thread_id]["status"] = "archived"
        new_state[thread_id]["archived_at"] = TIMESTAMP.isoformat()
        if session_rel:
            new_state[thread_id]["session_file"] = session_rel
        save_thread_state(new_state)  # persist after each thread so partial runs are saved
        print(f"  ✅ Archived: {info['title'][:60]}", flush=True)

    return {"checked": len(new_state), "inactive_found": len(inactive), "archived": len(results), "results": results}

def cmd_track(args) -> dict:
    track_thread(args.thread_id, args.channel_id, args.title,
                  datetime.utcnow(), "active")
    return {"tracked": args.thread_id, "title": args.title}

def cmd_send_clarify(args) -> dict:
    embed = build_clarify_embed(args.title)
    result = send_discord_embed(args.webhook or AGENT_WEBHOOK, embed)
    return {"sent": result.get("success", False), "message_id": result.get("message_id", ""),
            "webhook": args.webhook or AGENT_WEBHOOK[:40] + "..."}

def cmd_status() -> dict:
    state = load_thread_state()
    active = [k for k, v in state.items() if v.get("status") == "active"]
    archived = [k for k, v in state.items() if v.get("status") == "archived"]
    return {
        "total_tracked": len(state),
        "active": len(active),
        "archived": len(archived),
        "sessions_dir": str(SESSIONS_DIR),
        "webhook_configured": bool(AGENT_WEBHOOK),
        "vault_path": str(VAULT),
    }

# ── CLI ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    ap = argparse.ArgumentParser(prog="archiver")
    sub = ap.add_subparsers()

    p = sub.add_parser("archive", help="Archive a session")
    p.add_argument("--title", default="Untitled Session")
    p.add_argument("--messages", nargs="*", default=[])
    p.add_argument("--participants", default="@humanerd")
    p.add_argument("--trigger", default="manual")
    p.add_argument("--thread-url", default="")
    p.add_argument("--webhook", default="")
    p.add_argument("--no-clarify", action="store_true")
    p.add_argument("--ask-clarify", action="store_true", default=True)
    p.set_defaults(func=cmd_archive)

    p2 = sub.add_parser("inactivity", help="Check inactive threads (cron)")
    p2.set_defaults(func=lambda a: cmd_inactivity_check())

    p3 = sub.add_parser("track", help="Track a new thread")
    p3.add_argument("--thread-id", required=True)
    p3.add_argument("--channel-id", required=True)
    p3.add_argument("--title", required=True)
    p3.set_defaults(func=cmd_track)

    p4 = sub.add_parser("clarify", help="Send clarify question embed")
    p4.add_argument("--title", required=True)
    p4.add_argument("--webhook", default="")
    p4.set_defaults(func=cmd_send_clarify)

    p5 = sub.add_parser("status", help="System status")
    p5.set_defaults(func=lambda a: cmd_status())

    p6 = sub.add_parser("check-reactions", help="Check pending clarify reactions (cron)")
    p6.set_defaults(func=lambda a: check_clarify_reactions())

    p7 = sub.add_parser("archive-thread-event", help="Archive a Discord thread on close/delete (event-driven)")
    p7.add_argument("--thread-id", required=True)
    p7.add_argument("--channel-id", required=True)
    p7.add_argument("--guild-id", default="")
    p7.add_argument("--title", required=True)
    p7.add_argument("--trigger-type", required=True, choices=["thread_close", "thread_delete"])
    p7.add_argument("--participants", default="")
    p7.set_defaults(func=cmd_archive_thread_event)

    # ── Phase 4: Incremental Archiving CLI ──────────────────────────────────
    def cmd_ensure_note(args) -> dict:
        filepath, vault_rel = ensure_note(
            thread_id=args.thread_id,
            title=args.title,
            channel_id=args.channel_id,
            participants=args.participants or "@humanerd",
        )
        return {"success": True, "filepath": vault_rel, "thread_id": args.thread_id}

    def cmd_append_batch(args) -> dict:
        messages = args.messages or []
        return append_batch(
            thread_id=args.thread_id,
            messages=messages,
            batch_num=args.batch_num,
            ts=args.timestamp or TIMESTAMP.strftime("%Y-%m-%d %H:%M"),
        )

    def cmd_finalize(args) -> dict:
        return finalize_with_abstract(thread_id=args.thread_id)

    p8 = sub.add_parser("ensure-note", help="[Phase 4] Create empty skeleton note on thread creation")
    p8.add_argument("--thread-id", required=True)
    p8.add_argument("--channel-id", required=True)
    p8.add_argument("--title", required=True)
    p8.add_argument("--participants", default="@humanerd")
    p8.set_defaults(func=cmd_ensure_note)

    p9 = sub.add_parser("append-batch", help="[Phase 4] Append a batch of messages incrementally")
    p9.add_argument("--thread-id", required=True)
    p9.add_argument("--batch-num", type=int, required=True)
    p9.add_argument("--messages", nargs="*", default=[])
    p9.add_argument("--timestamp", default="")
    p9.set_defaults(func=cmd_append_batch)

    p10 = sub.add_parser("finalize", help="[Phase 4] Finalize note with Abstract on thread close/delete")
    p10.add_argument("--thread-id", required=True)
    p10.set_defaults(func=cmd_finalize)

    import sys as _sys
    _sys.stderr.write("archiver.py: about to parse_args\n")
    _sys.stderr.flush()
    args = ap.parse_args()
    _sys.stderr.write(f"archiver.py: parsed args={vars(args)}\n")
    _sys.stderr.flush()

    if hasattr(args, "func"):
        _sys.stderr.write("archiver.py: calling func\n")
        _sys.stderr.flush()
        result = args.func(args)
        _sys.stderr.write(f"archiver.py: func returned\n")
        _sys.stderr.flush()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        ap.print_help()
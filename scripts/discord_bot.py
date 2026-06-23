#!/usr/bin/env python3
"""Discord bot → opencode gateway with real-time streaming.

Each Discord thread maps to one opencode session. The bot streams
`opencode run --format json --thinking` output and updates a single
status message in the thread as events arrive.
"""
import asyncio
import json
import os
import re
import sqlite3
import sys
import time
from typing import List, Optional

import discord

HOME = os.path.expanduser("~")
TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
SELF_USER_ID: Optional[int] = None
DB_PATH = os.path.join(HOME, ".drewgent", "discord_sessions.db")

OPCODE_SERVE = "http://localhost:8642"
MAX_MSG_LEN = 1900          # Discord safe content length
MAX_STATUS_CONTENT = 1850   # leave room for emoji + whitespace prefixes
STREAM_TIMEOUT = 180        # seconds

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)


# ---------------------------------------------------------------------------
# Session database (kept from the original bot)
# ---------------------------------------------------------------------------
def init_db() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS sessions ("
        "thread_id TEXT PRIMARY KEY, session_id TEXT, updated_at INTEGER)"
    )
    conn.commit()
    conn.close()


def get_session(thread_id: str) -> Optional[str]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute("SELECT session_id FROM sessions WHERE thread_id=?", (thread_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def save_session(thread_id: str, session_id: str) -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT OR REPLACE INTO sessions VALUES (?,?,?)",
        (thread_id, session_id, int(time.time())),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Text chunking helpers
# ---------------------------------------------------------------------------
def chunk_text(text: str, limit: int = MAX_MSG_LEN) -> List[str]:
    """Split text into Discord-safe chunks, trying to keep code blocks intact.

    If a chunk boundary falls inside a triple-backtick fence, the chunk is
    closed with ``` and the next chunk reopens it.
    """
    if len(text) <= limit:
        return [text]

    chunks: List[str] = []
    current = ""
    in_fence = False

    for line in text.splitlines(keepends=True):
        is_fence = line.strip().startswith("```")

        # Start a new chunk if this line would overflow.
        if current and len(current) + len(line) > limit:
            if in_fence and not is_fence:
                current += "```\n"
            chunks.append(current)
            current = "```\n" if (in_fence and not is_fence) else ""

        current += line
        if is_fence:
            in_fence = not in_fence

    if current:
        chunks.append(current)
    return chunks or [""]


def strip_thinking_tags(text: str) -> str:
    return re.sub(r"<thinking>.*?</thinking>", "", text, flags=re.DOTALL).strip()


def format_status(emoji: str, content: str) -> str:
    content = content.strip()
    if not content:
        content = "생각 중..."
    if len(content) > MAX_STATUS_CONTENT:
        content = "..." + content[-(MAX_STATUS_CONTENT - 3):]
    return f"{emoji} {content}"


# ---------------------------------------------------------------------------
# opencode streaming handler
# ---------------------------------------------------------------------------
def _find_session_id(data: dict) -> Optional[str]:
    """Best-effort session ID extraction from a JSON event."""
    for key in ("sessionID", "session_id"):
        sid = data.get(key)
        if sid:
            return sid
        sid = data.get("part", {}).get(key)
        if sid:
            return sid
    return None


async def stream_opencode(thread: discord.Thread, prompt: str, thread_id: str) -> None:
    """Run opencode as a streaming subprocess and update Discord in real time."""
    session = get_session(thread_id)

    cmd = [
        "opencode", "run", prompt,
        "--dangerously-skip-permissions",
        "--print-logs",
        "--format", "json",
        "--thinking",
        "--dir", os.path.join(HOME, ".drewgent"),
        "--model", "opencode-go/deepseek-v4-flash",
        "--attach", OPCODE_SERVE,
    ]
    if session:
        cmd += ["--continue", "--session", session]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    status_msg: Optional[discord.Message] = None
    text_messages: List[discord.Message] = []  # final-answer message(s)
    final_text = ""
    last_session: Optional[str] = None
    error_seen = False

    # Reasoning coalescing state
    pending_reasoning: List[str] = []
    reasoning_handle: Optional[asyncio.TimerHandle] = None

    async def _set_status(emoji: str, content: str) -> None:
        nonlocal status_msg
        text = format_status(emoji, content)
        if status_msg is None:
            status_msg = await thread.send(text)
        else:
            try:
                await status_msg.edit(content=text)
            except discord.HTTPException:
                status_msg = await thread.send(text)

    def _cancel_reasoning() -> None:
        nonlocal reasoning_handle
        if reasoning_handle is not None:
            reasoning_handle.cancel()
            reasoning_handle = None
        pending_reasoning.clear()

    async def _flush_reasoning() -> None:
        nonlocal reasoning_handle
        reasoning_handle = None
        if not pending_reasoning:
            return
        full = "".join(pending_reasoning)
        pending_reasoning.clear()
        await _set_status("🤔", full)

    def _schedule_reasoning() -> None:
        nonlocal reasoning_handle
        if reasoning_handle is None:
            loop = asyncio.get_running_loop()
            reasoning_handle = loop.call_later(0.5, lambda: asyncio.create_task(_flush_reasoning()))

    async def _update_final_text() -> None:
        nonlocal final_text, status_msg
        if not final_text:
            return
        chunks = chunk_text(final_text, MAX_MSG_LEN)
        for idx, chunk in enumerate(chunks):
            prefix = "✅ " if idx == 0 else ""
            content = prefix + chunk
            if idx == 0:
                if status_msg is None:
                    status_msg = await thread.send(content)
                else:
                    await status_msg.edit(content=content)
                if not text_messages:
                    text_messages.append(status_msg)
            elif idx < len(text_messages):
                await text_messages[idx].edit(content=chunk)
            else:
                text_messages.append(await thread.send(chunk))

    async def _read_stream() -> None:
        nonlocal final_text, last_session, error_seen
        assert proc.stdout is not None
        while True:
            raw = await proc.stdout.readline()
            if not raw:
                break
            line = raw.decode("utf-8", errors="replace").rstrip("\n")
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                # Non-JSON line (e.g. stray log output); ignore.
                continue

            etype = data.get("type")
            part = data.get("part", {}) if isinstance(data.get("part"), dict) else {}

            sid = _find_session_id(data)
            if sid:
                last_session = sid

            if etype == "reasoning":
                content = (
                    part.get("text")
                    or part.get("reasoning")
                    or data.get("text")
                    or data.get("reasoning")
                    or ""
                )
                pending_reasoning.append(str(content))
                _schedule_reasoning()

            elif etype == "text":
                _cancel_reasoning()
                t = part.get("text") or data.get("text") or ""
                final_text += strip_thinking_tags(str(t))
                await _update_final_text()

            elif etype == "tool_use":
                _cancel_reasoning()
                tool = part.get("tool") or data.get("tool") or {}
                name = tool.get("name") if isinstance(tool, dict) else str(tool)
                if not name:
                    name = part.get("name") or data.get("name") or "tool"
                args = part.get("arguments") or data.get("arguments") or {}
                display = name
                if args:
                    args_text = json.dumps(args, ensure_ascii=False)
                    display += f"({args_text[:200]}{'...' if len(args_text) > 200 else ''})"
                tool_emojis = {
                    "bash": "💻", "terminal": "💻", "command": "💻",
                    "write": "📝", "edit": "📝", "apply_patch": "📝",
                    "read": "📖",
                    "webfetch": "🌐", "fetch": "🌐",
                    "grep": "🔍", "search": "🔍",
                    "glob": "📁",
                    "task": "🤖",
                    "discord": "💬", "discord_send": "💬",
                    "sqlite": "🗄️", "sqlite3": "🗄️",
                    "gbrain": "🧠", "query": "🧠",
                    "lazyweb": "🎨",
                    "todowrite": "📋",
                    "skill": "📎",
                    "question": "❓",
                    "delegate": "🔄",
                }
                base = name.split("_")[0].split(".")[0].lower()
                emoji = "🔧"
                for k, v in tool_emojis.items():
                    if k in name.lower():
                        emoji = v
                        break
                await _set_status(emoji, display)

            elif etype == "file":
                _cancel_reasoning()
                path = (
                    data.get("path")
                    or part.get("path")
                    or data.get("file")
                    or part.get("file")
                    or "output"
                )
                await _set_status("📦", str(path))

            elif etype == "error":
                _cancel_reasoning()
                error_seen = True
                err = (
                    part.get("error")
                    or part.get("message")
                    or data.get("error")
                    or data.get("message")
                    or json.dumps(data, ensure_ascii=False)
                )
                await _set_status("❌", str(err))

    async with thread.typing():
        try:
            await asyncio.wait_for(_read_stream(), timeout=STREAM_TIMEOUT)
        except asyncio.TimeoutError:
            proc.kill()
            await _set_status("❌", "timeout")
            error_seen = True

    # Clean up the subprocess and read any leftover stderr.
    if proc.returncode is None:
        proc.kill()
    await proc.wait()
    stderr = (await proc.stderr.read()).decode("utf-8", errors="replace") if proc.stderr else ""
    if stderr:
        print(f"[opencode stderr] {stderr.strip()[:500]}")

    # Flush any trailing reasoning that wasn't rendered yet.
    if reasoning_handle is not None:
        reasoning_handle.cancel()
        reasoning_handle = None
    if pending_reasoning:
        await _flush_reasoning()

    # Persist the session ID for thread continuity.
    if last_session:
        save_session(thread_id, last_session)

    # If nothing useful happened, let the user know.
    if not final_text and not error_seen:
        await _set_status("⏳", "no response")


# ---------------------------------------------------------------------------
# Discord event handlers (kept from the original bot)
# ---------------------------------------------------------------------------
@client.event
async def on_ready() -> None:
    global SELF_USER_ID
    init_db()
    SELF_USER_ID = client.user.id
    print(f"Bot online: {client.user} | Thread=Session streaming mode")


@client.event
async def on_message(msg: discord.Message) -> None:
    if msg.author.bot:
        return
    if msg.content.startswith("!"):
        return

    # Create a thread from the message, or reuse an existing thread.
    if isinstance(msg.channel, discord.Thread):
        thread = msg.channel
        thread_id = str(thread.id)
    else:
        try:
            thread = await msg.create_thread(
                name=msg.clean_content[:100],
                auto_archive_duration=60,
            )
            thread_id = str(thread.id)
        except Exception:
            thread = msg.channel  # type: ignore[assignment]
            thread_id = str(msg.channel.id)

    await stream_opencode(thread, msg.clean_content, thread_id)  # type: ignore[arg-type]


if __name__ == "__main__":
    if not TOKEN:
        print("DISCORD_BOT_TOKEN not set")
        sys.exit(1)
    print("Starting Discord bot (thread=session, streaming)...")
    client.run(TOKEN)

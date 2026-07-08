#!/usr/bin/env python3
"""Discord bot -> opencode gateway with real-time streaming.

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
DB_PATH = os.path.join(HOME, ".loragent", "discord_sessions.db")

OPCODE_SERVE = "http://localhost:8642"
MAX_MSG_LEN = 1900
MAX_STATUS_CONTENT = 1850

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

_active_tasks: dict[str, asyncio.Task] = {}


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


def chunk_text(text: str, limit: int = MAX_MSG_LEN) -> List[str]:
    if len(text) <= limit:
        return [text]
    chunks: List[str] = []
    current = ""
    in_fence = False
    for line in text.splitlines(keepends=True):
        is_fence = line.strip().startswith("```")
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


def _find_session_id(data: dict) -> Optional[str]:
    for key in ("sessionID", "session_id"):
        sid = data.get(key)
        if sid:
            return sid
        sid = data.get("part", {}).get(key)
        if sid:
            return sid
    return None


async def stream_opencode(thread: discord.Thread, prompt: str, thread_id: str) -> None:
    session = get_session(thread_id)
    cmd = [
        "opencode", "run", prompt,
        "--dangerously-skip-permissions",
        "--print-logs",
        "--format", "json",
        "--thinking",
        "--dir", os.path.join(HOME, ".loragent"),
        "--model", "opencode-go/deepseek-v4-flash",
        "--attach", OPCODE_SERVE,
    ]
    if session:
        cmd += ["--continue", "--session", session]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        limit=1024 * 1024,
    )

    reasoning_msg: Optional[discord.Message] = None
    tool_msg: Optional[discord.Message] = None
    text_messages: List[discord.Message] = []
    final_text = ""
    last_session: Optional[str] = None
    error_seen = False

    pending_reasoning: List[str] = []
    reasoning_handle: Optional[asyncio.TimerHandle] = None

    async def _set_reasoning(content: str) -> None:
        nonlocal reasoning_msg
        text = format_status("🤔", content)
        if reasoning_msg is None:
            reasoning_msg = await thread.send(text)
        else:
            try:
                await reasoning_msg.edit(content=text)
            except discord.HTTPException:
                reasoning_msg = await thread.send(text)

    async def _set_tool(emoji: str, content: str) -> None:
        nonlocal tool_msg
        text = format_status(emoji, content)
        if tool_msg is None:
            tool_msg = await thread.send(text)
        else:
            try:
                await tool_msg.edit(content=text)
            except discord.HTTPException:
                tool_msg = await thread.send(text)

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
        await _set_reasoning(full)

    def _schedule_reasoning() -> None:
        nonlocal reasoning_handle
        if reasoning_handle is None:
            loop = asyncio.get_running_loop()
            reasoning_handle = loop.call_later(0.5, lambda: asyncio.create_task(_flush_reasoning()))

    async def _update_final_text() -> None:
        nonlocal final_text
        if not final_text:
            return
        chunks = chunk_text(final_text, MAX_MSG_LEN)
        for idx, chunk in enumerate(chunks):
            prefix = "✅ " if idx == 0 else ""
            content = prefix + chunk
            if idx == 0:
                msg = await thread.send(content)
                if not text_messages:
                    text_messages.append(msg)
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
                    "recall": "🧠", "query": "🧠",
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
                await _set_tool(emoji, display)

            elif etype == "file":
                _cancel_reasoning()
                path = (
                    data.get("path")
                    or part.get("path")
                    or data.get("file")
                    or part.get("file")
                    or "output"
                )
                await _set_tool("📦", str(path))

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
                await _set_tool("❌", str(err))

    async def _typing_heartbeat() -> None:
        while True:
            try:
                await thread.trigger_typing()
                await asyncio.sleep(8)
            except asyncio.CancelledError:
                break

    typing_task = asyncio.create_task(_typing_heartbeat())

    try:
        await _read_stream()
    except asyncio.CancelledError:
        proc.kill()
        raise
    except Exception:
        proc.kill()
        raise
    finally:
        typing_task.cancel()

    if proc.returncode is None:
        proc.kill()
    await proc.wait()
    stderr = (await proc.stderr.read()).decode("utf-8", errors="replace") if proc.stderr else ""
    if stderr:
        print(f"[opencode stderr] {stderr.strip()[:500]}")

    if reasoning_handle is not None:
        reasoning_handle.cancel()
        reasoning_handle = None
    if pending_reasoning:
        await _flush_reasoning()

    if last_session:
        save_session(thread_id, last_session)

    if not final_text and not error_seen:
        await _set_tool("⏳", "no response")


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
            thread = msg.channel
            thread_id = str(msg.channel.id)

    prev = _active_tasks.get(thread_id)
    if prev and not prev.done():
        prev.cancel()

    task = asyncio.create_task(stream_opencode(thread, msg.clean_content, thread_id))
    _active_tasks[thread_id] = task
    task.add_done_callback(lambda _: _active_tasks.pop(thread_id, None))


async def _cleanup_thread(thread_id: str) -> None:
    task = _active_tasks.pop(thread_id, None)
    if task and not task.done():
        task.cancel()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM sessions WHERE thread_id=?", (thread_id,))
    conn.commit()
    conn.close()


@client.event
async def on_thread_update(before: discord.Thread, after: discord.Thread) -> None:
    if not after.archived:
        return
    await _cleanup_thread(str(after.id))


@client.event
async def on_thread_remove(thread: discord.Thread) -> None:
    await _cleanup_thread(str(thread.id))


if __name__ == "__main__":
    if not TOKEN:
        print("DISCORD_BOT_TOKEN not set")
        sys.exit(1)
    print("Starting Discord bot (thread=session, streaming)...")
    client.run(TOKEN)

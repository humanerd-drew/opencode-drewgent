#!/usr/bin/env python3
"""Discord bot → opencode gateway. Thread = session. Context preserved."""
import discord, asyncio, subprocess, json, os, re, sys, textwrap, sqlite3, time

HOME = os.path.expanduser("~")
TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
SELF_USER_ID = None
DB_PATH = os.path.join(HOME, ".drewgent", "discord_sessions.db")

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS sessions (thread_id TEXT PRIMARY KEY, session_id TEXT, updated_at INTEGER)")
    conn.commit()
    conn.close()

def get_session(thread_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute("SELECT session_id FROM sessions WHERE thread_id=?", (thread_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None

def save_session(thread_id, session_id):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT OR REPLACE INTO sessions VALUES (?,?,?)", (thread_id, session_id, int(time.time())))
    conn.commit()
    conn.close()

OPCODE_SERVE = "http://localhost:8642"

def call_opencode(message, thread_id):
    session = get_session(thread_id)
    prompt = message
    cmd = ["opencode", "run", prompt, "--dangerously-skip-permissions", "--print-logs", "--format", "json", "--dir", os.path.join(HOME, ".drewgent"), "--model", "opencode-go/deepseek-v4-flash", "--attach", OPCODE_SERVE]
    if session:
        cmd += ["--continue", "--session", session]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180, env={**os.environ})
        last_text = ""
        last_sid = ""
        for line in r.stdout.strip().split("\n"):
            try:
                data = json.loads(line)
                if data.get("type") == "text":
                    t = data.get("part", {}).get("text", "")
                    if t: last_text = t
                    sid = data.get("sessionID", "") or data.get("part", {}).get("sessionID", "")
                    if sid: last_sid = sid
                if data.get("type") == "step_finish":
                    sid = data.get("sessionID", "") or data.get("part", {}).get("sessionID", "")
                    if sid: last_sid = sid
            except json.JSONDecodeError:
                continue
        if last_sid: save_session(thread_id, last_sid)
        if last_text:
            return re.sub(r'<thinking>.*?</thinking>', '', last_text, flags=re.DOTALL).strip()
        return "[no response]"
    except subprocess.TimeoutExpired:
        return "[timeout]"
    except Exception as e:
        return f"[error: {e}]"

@client.event
async def on_ready():
    global SELF_USER_ID
    init_db()
    SELF_USER_ID = client.user.id
    print(f"Bot online: {client.user} | Thread=Session mode")

@client.event
async def on_message(msg):
    if msg.author.bot:
        return
    if msg.content.startswith("!"):
        return

    # Create thread from message (or use existing thread)
    if isinstance(msg.channel, discord.Thread):
        thread = msg.channel
        thread_id = str(thread.id)
    else:
        try:
            thread = await msg.create_thread(name=msg.clean_content[:100], auto_archive_duration=60)
            thread_id = str(thread.id)
        except:
            thread = msg.channel
            thread_id = str(msg.channel.id)

    async with thread.typing():
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, call_opencode, msg.clean_content, thread_id)

    chunks = textwrap.wrap(response, 1900) or ["[empty]"]
    for chunk in chunks:
        await thread.send(chunk)

if __name__ == "__main__":
    if not TOKEN:
        print("DISCORD_BOT_TOKEN not set"); sys.exit(1)
    print("Starting Discord bot (thread=session)...")
    client.run(TOKEN)

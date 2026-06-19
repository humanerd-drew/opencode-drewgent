# Gateway Delegate Pattern — Lightweight Subagent for Discord Messages

## Problem

The gateway creates a full AIAgent with **151 tools** (including 4 MCP servers)
for every Discord message. The system prompt is so large that context compaction
triggers on the **very first message** (`Context: ▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰ 100%`).

## Solution

Instead of running the agent inside the gateway process with all 151 tools,
`_handle_message_with_agent` now spawns a lightweight subagent with a focused
toolset:

```python
_sub_toolsets = ["terminal", "file", "web", "skills", "memory", "todo"]
```

This reduces the system prompt from ~151 tools to ~20 — small enough that the
first message never triggers compaction.

## Implementation

In `gateway/run.py`, the `_run_agent(self, ...)` call was replaced with:

```python
from run_agent import AIAgent

child = AIAgent(
    model=_sub_model,
    provider=_sub_runtime.get("provider"),
    base_url=_sub_runtime.get("base_url"),
    api_key=_sub_runtime.get("api_key"),
    api_mode=_sub_runtime.get("api_mode"),
    max_iterations=25,
    quiet_mode=True,
    enabled_toolsets=_sub_toolsets,    # ← 6 toolsets, not all 151
    session_id=session_entry.session_id,
    platform=source.platform.value if source.platform else "discord",
)
child_result = await asyncio.to_thread(
    child.run_conversation, user_message=message_text
)
```

## Benefits

1. **Clean context** — each message gets a fresh subagent with ~20 tools
2. **No compaction on first message** — system prompt is 5× smaller
3. **Gateway process stays lightweight** — never loads 151 tool schemas
4. **Same credentials** — uses `_resolve_runtime_agent_kwargs()` + `_resolve_gateway_model()` (same as main agent)
5. **Same model/provider** — opencode-go/deepseek-v4-flash, not OpenRouter

## Trade-offs

- Loses agent caching (prompt caching reuse between messages)
- Each message creates a new AIAgent (no warm cache)
- No streaming support (subagent is synchronous)

These are acceptable trade-offs: the gateway's primary job is message relay,
and each message is usually a new conversation turn anyway.

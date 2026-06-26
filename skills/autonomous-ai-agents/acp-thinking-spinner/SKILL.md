---
name: acp-thinking-spinner
description: Add a "Thinking..." spinner card to an ACP server's tool-call stack so ACP clients (Zed Agent Panel, openCode TUI, JetBrains/VS Code ACP UI) show a working indicator during the LLM API call phase. Triggers when working on an Agent Client Protocol (ACP) server and the user wants LLM-thinking visibility in the client's tool-call stack.
links:
  - "[[@action/skills/SKILL-INDEX]]"
  - "[[@identity/brain/rules]]"
---

# ACP Thinking Spinner — Tool-Card Pattern

When an ACP server (Drewgent's `acp_adapter/`, Hermes, or any Agent Client Protocol implementation) needs to show a working indicator during the LLM API call phase, the standard approach is to **synthesize a virtual tool call** with `kind="think"`. This places a "Thinking..." card in the client's tool-call stack — the same place real tool calls appear, which is the most reliable UI surface.

## Why this pattern (root-cause: ACP spec gap)

ACP has no dedicated channel for "agent is generating a response." It only has:

| Channel | Where it renders | Problem |
|---------|------------------|---------|
| `update_agent_thought_text` | Client's "Thinking" area | Most clients render this as **static text** — JetBrains got stuck on "Thinking" with rawInput updates, others don't blink. Unreliable for "is it stuck?" UX. |
| `update_agent_message_text` | Answer streaming area | Only fires once streaming actually starts; doesn't cover the 0-30s gap before first delta. |
| `ToolCallStart` / `ToolCallUpdate` | **Tool-call stack** (openCode-style) | The most reliable UI surface — clients render an animated spinner here for any tool call. Synthesizing a virtual think-kind call works. |
| Status bar | Client-specific | **Not standardized in ACP** — see `agentclientprotocol.com/rfds/session-usage` (RFD, not yet spec). Cannot trigger from the server. |

**Conclusion**: For a "is it stuck or working?" signal in ACP, the only reliable channel is the tool-call stack. Use a virtual `kind="think"` card.

## State machine

```
start     → ToolCallStart(kind="think", title="Thinking...")
heartbeat → ToolCallUpdate(status="in_progress", elapsed text)   # at 30s, 60s, ...
complete  → ToolCallUpdate(status="completed")
```

Hook sites in the LLM call lifecycle:

1. **Before** `_interruptible_api_call()` / `_interruptible_streaming_api_call()` → `start`
2. **First streamed delta** (`on_first_delta` callback) → `complete`
3. **Long-running timer** (e.g. `threading.Timer(30.0, ...)`) → `heartbeat`; cancel on complete

If a real tool call is dispatched before the LLM finishes, the thinking card is implicitly replaced by the real tool's card (ACP client stack semantics). No need to manually close.

## Drewgent reference implementation

Files modified (Drewgent ACP server at `~/.drewgent/source/drewgent-agent/`):

### `acp_adapter/tools.py` — three helpers
- `build_thinking_start(tool_call_id) -> ToolCallStart`
- `build_thinking_progress(tool_call_id, elapsed) -> ToolCallProgress`  
- `build_thinking_complete(tool_call_id) -> ToolCallProgress`

All use `kind="think"` and `acp.start_tool_call` / `acp.update_tool_call`.

### `acp_adapter/events.py` — callback factory
`make_agent_progress_cb(conn, session_id, loop)` returns a callable matching the signature:
```python
agent_progress_callback(state: str, name: str, args: dict = None)
```
Stores `name → tool_call_id` in a closure dict. State machine: start/heartbeat/complete.

### `acp_adapter/server.py` — wire
Alongside existing `thinking_cb`, add:
```python
agent_progress_cb = make_agent_progress_cb(conn, session_id, loop)
agent.agent_progress_callback = agent_progress_cb
```

### `run_agent.py` — three hook sites + callback attr
1. Add `agent_progress_callback: callable = None` to `AIAgent.__init__` signature
2. `self.agent_progress_callback = agent_progress_callback` in the body
3. **Hook A** (LLM call start, right before `_interruptible_*_api_call`):
   ```python
   if self.agent_progress_callback:
       try: self.agent_progress_callback("start", "llm_response", {})
       except Exception: pass
   ```
4. **Hook B** (first delta, inside the `on_first_delta` closure):
   ```python
   if self.agent_progress_callback:
       try: self.agent_progress_callback("complete", "llm_response", {})
       except Exception: pass
   ```
5. **Hook C** (30s+ timer callback):
   ```python
   def _llm_heartbeat():
       elapsed = time.time() - api_start_time
       if self.agent_progress_callback:
           try: self.agent_progress_callback("heartbeat", "llm_response", {"elapsed": elapsed})
           except Exception: pass
       # fallback: thinking_callback (text), _vprint (raw stdout)
   _llm_heartbeat_timer = threading.Timer(30.0, _llm_heartbeat)
   ```

## Channel routing rule (stdout breaks ACP)

ACP is **JSON-RPC over stdio**. Writing raw text to stdout (e.g. `print()` or `_vprint`) breaks the protocol. Three channels, in priority order:

| Channel | Path | When |
|---------|------|------|
| `agent_progress_callback` | `ToolCallStart`/`Update` (tool card) | ACP client available — preferred |
| `thinking_callback` | `update_agent_thought_text` | Fallback for non-ACP paths; some clients (JetBrains) render this as static "Thinking..." |
| `_vprint` (raw stdout) | Plain text | Last-resort for non-ACP environments (gateway streaming, plain CLI) |

Always check `agent_progress_callback` first, then `thinking_callback`, then `_vprint`. Never `print()` directly in agent code — it leaks through the JSON-RPC pipe.

## Env var

`DREW_LLM_HEARTBEAT_DISABLED=1` disables the 30s+ timer. Use for tests / CI to avoid timing flakiness.

## Verification

After patching:
1. `python3 -c "import ast; ast.parse(open('<file>').read())"` for each modified file
2. AST check that the 3 hook sites are present:
   ```python
   hook_count = body_src.count('self.agent_progress_callback(')
   assert hook_count == 3, f"expected 3 hook sites, got {hook_count}"
   ```
3. Restart the ACP server (e.g. exit the CLI process; new `drewgent` invocation picks up the patch)
4. Trigger a long-running LLM call and confirm the client shows the spinner card in the tool-call stack

## Pitfalls

- **Don't put text content in `update_agent_thought_text` thinking channel** if the user said "I don't want text — I want an indicator." Use the tool-card channel instead.
- **Don't write to `sys.stdout` directly** in ACP mode — breaks JSON-RPC. Always go through a registered callback or the tool-card helper.
- **Don't fire `heartbeat` without a prior `start`** — the closure dict won't have a tool_call_id, the call is a no-op. This is intentional safety.
- **Mock client skips streaming** — `if isinstance(client, Mock): _use_streaming = False` already exists; heartbeat only fires on streaming, so mock tests are unaffected.

## Related

- ACP spec: https://agentclientprotocol.com/protocol/v1/tool-calls
- ACP status/usage RFD (in progress, not yet spec): https://agentclientprotocol.com/rfds/session-usage
- openCode ACP: https://opencode.ai/docs/acp/
- Zed Agent Panel: https://zed.dev/docs/ai/agent-panel
- JetBrains ACP client (stuck on "Thinking" issue): https://youtrack.jetbrains.com/projects/WI/issues/WI-83745
- Drewgent's own ACP source: `acp_adapter/{server,events,tools,session}.py`

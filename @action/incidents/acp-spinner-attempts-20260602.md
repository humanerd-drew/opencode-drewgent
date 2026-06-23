---
title: ACP thinking-phase indicator — 3 attempts, all rejected
type: incident
space: claim
tags: [claim, ui, acp, non-retryable]
created: 2026-06-02
updated: 2026-06-10
links:
  - "[[@identity/brain/rules]]"
  - "[[@memory/memories/MEMORY.md]]"  # ACP/UI Constraints entry
---

# Incident — ACP thinking-phase indicator — 3 attempts, all rejected by user

**Date**: 2026-06-02 (initial), updated 2026-06-10 (memory link added)
**Severity**: P3 (low — feature gap, not blocking)
**Status**: Closed — DO NOT RETRY without explicit user override
**Author**: Drewgent self-investigation

---

## 1. Goal

Show a "thinking" indicator at the place where the LLM is currently thinking,
i.e. an LED/spinner in the streaming response area of the user's TUI/chat client.

The user's complaint (verbatim): "텍스트 추가 아님. 그 자리 깜빡이는 LED 필요.
메시지는 이미 있지." ("Not text addition. Need a blinking LED right there. The
message is already there.")

## 2. Attempts (all rejected)

### Attempt 1 — display.py `_format_bytes` + `_wrap` size hint
- **What**: Augment tool result line with size hint (5s+ tool, 1KB+ result) for visual
  emphasis. Reinforces existing tool card with more text.
- **Why rejected**: User said "텍스트 추가 아님" — more text is not the solution.
- **Code**: 6 file patch (display.py, run_agent.py, acp_adapter/{tools,events,server}.py,
  tests/test_display.py). Reverted.

### Attempt 2 — run_agent.py 30s+ heartbeat
- **What**: If a tool/API call takes >30s, emit a heartbeat event to callbacks
  (`_vprint` → `thinking_callback` routing).
- **Why rejected**: Heartbeat is still a textual/log event, not a visual LED.
- **Code**: Same 6 files. Reverted.

### Attempt 3 — openCode-style ToolCallStart (kind="think") + ToolCallUpdate
- **What**: Emit a synthetic "thinking" tool call at the start of each LLM call,
  with in_progress/completed status. ACP allows this via `ToolCallStart` event.
- **Why rejected**: All major ACP clients (Claude Code, Zed, opencode TUI) render
  tool cards in a *separate* area from the streaming response. The "thinking" tool
  card appears *above* the response, not at the cursor. Same problem as before.

## 3. Root cause (analysis)

The ACP spec has these relevant events:
- `update_agent_thought_text` — text content during thinking. Rendered as plain text
  by all clients, not as a blinking indicator. (JetBrains "stuck on 'Thinking'" issue
  is related — they show plain text, no spinner.)
- `ToolCallStart` — synthetic tool call. Rendered in tool card area, not in stream area.
- `ToolCallUpdate` — status update for the above.

**There is no ACP event that clients render as an in-stream visual indicator.**

The closest thing is `agentclientprotocol.com/rfds/session-usage` — a status bar
RFD in progress, not standardized.

## 4. Conclusion

**The LLM thinking-phase indicator is unsolvable via the current ACP spec.**

This is a *fundamental protocol limitation*, not an implementation gap. Until the
RFD lands and clients adopt, the feature is not deliverable through agent-side work.

## 5. Action: DO NOT RETRY

- **No further attempts** without user explicit override
- If user asks "LED 다시" or similar in the future, this document is the canonical
  reference — load it, cite the 3-attempt history, recommend accepting the gap
- Memory entry "[[ACP-spinner-attempts-20260602]]" (in MEMORY.md) references this doc

## 6. Partial alternative (not pursued)

User could install a *client-side* indicator — e.g., a custom Zed/Claude Code plugin
that shows a cursor blink when `update_agent_thought_text` arrives. This is *outside*
the agent's scope and was not requested.

## Links
- [[@memory/memories/MEMORY.md]]

## Related Neurons
- [[禁console_log.neuron]]
- [[禁blind_write.neuron]]

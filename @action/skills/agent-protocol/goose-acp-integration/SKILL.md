---
name: goose-acp-integration
description: Integrate Drewgent with ACP (Agent Client Protocol) agents. Reverse-engineered from goose's Rust ACP provider implementation.
space: outcome
type: document
tags: [acp, protocol, goose, integration]
links:
  - "[[@action/skills/agent-protocol/DESCRIPTION]]"
  - "[[@action/skills/SKILL-INDEX]]"
created: 2026-05-10
---

# Goose ACP Integration for Drewgent

## What is ACP

**Agent Client Protocol (ACP)** is a JSON-RPC-based standard for communicating with coding agents (GitHub: agentclientprotocol).

goose uses ACP to connect to agents like Claude Code as **provider** (subprocess communication over stdio):

```
goose → claude-agent-acp (NPM) → Claude Code CLI → Anthropic API
```

Key ACP providers in goose:
- `claude_acp.rs` — Claude Code via `@agentclientprotocol/claude-agent-acp`
- `codex_acp.rs` — OpenAI Codex
- `copilot_acp.rs` — GitHub Copilot

## Key Protocol Types (agent_client_protocol schema)

```rust
InitializeRequest/Response   // handshake
NewSessionRequest/Response    // create session
PromptRequest/Response       // send messages
SessionNotification          // async events (tool calls, permissions, completion)
  - ToolCallStart { id, name, kind, raw_input }
  - ToolCallComplete { id, raw_output, content[], is_error }
  - PermissionRequest { request: RequestPermissionRequest }
  - Complete(StopReason, Option<Usage>)
ToolCallContent / ToolCallStatus
RequestPermissionResponse
```

## How goose connects to Claude Code

```rust
// crates/goose/src/providers/claude_acp.rs
let config = AcpProviderConfig {
    command: resolved_command,  // path to claude-agent-acp
    args: vec![],
    env: vec![],
    work_dir: current_dir,
    mcp_servers: extension_configs_to_mcp_servers(&extensions),  // Drewgent tools as MCP
    session_mode_id: Some(mode_mapping[&goose_mode].clone()),
    // mode_mapping:
    //   Auto → bypassPermissions (fully autonomous)
    //   Approve → default (ask before risky)
    //   SmartApprove → acceptEdits (auto-accept edits)
    //   Chat → plan (plan only)
};
AcpProvider::connect(name, model, goose_mode, config).await
```

AcpProvider (crates/goose/src/acp/provider.rs):
- Spawns subprocess (stdio JSON-RPC)
- Sends `initialize` then `newSession`
- Streams `SessionNotification` back (tool calls, permissions)
- Sends tool results via `CallToolResult`

## Drewgent Implementation Points

### 1. ACP Provider Tool
Spawn any ACP agent as subprocess, communicate via newline-delimited JSON-RPC over stdio.

### 2. MCP Extension Bridge
Convert Drewgent tools → MCP server definitions → pass to ACP agent via `mcp_servers` config.

### 3. Permission Tiers
Map Drewgent P0-P6 brain rules to ACP permission decisions (AllowAlways/AllowOnce/RejectOnce/RejectAlways/Cancel).

## Implementation Plan

**Phase 1:** `tools/acp_provider.py` — subprocess spawn + JSON-RPC over stdio + session lifecycle
**Phase 2:** Delegate to Claude Code via `claude-agent-acp`, pass Drewgent tools as MCP servers
**Phase 3:** Permission callback system bridging Drewgent P0 rules to ACP permission requests

## References

- goose ACP provider impl: `crates/goose/src/providers/{claude_acp,codex_acp,copilot_acp}.rs`
- ACP core: `crates/goose/src/acp/provider.rs`
- ACP macros: `crates/goose-acp-macros/src/lib.rs`
- Protocol schema: `agent_client_protocol` Rust crate (github.com/agentclientprotocol)
- ACP npm adapter: `@agentclientprotocol/claude-agent-acp`
- Docs: https://goose-docs.ai/docs/guides/acp-providers

## Gotchas

1. **STDIO transport** — newline-delimited JSON-RPC, no HTTP
2. **Mode mapping** — each ACP agent has different mode strings; configured per-provider
3. **MCP servers** — must follow Model Context Protocol schema
4. **Permission suspension** — ACP agent waits for async permission response; cannot block main loop
5. **Nested sessions** — set `env_remove` to prevent infinite nesting (e.g., CLAUDECODE env var)

## Related
- [[@action/skills/SKILL-INDEX]]
- [[@action/skills/agent-protocol/DESCRIPTION]]

---
title: Loragent 아키텍처 — 데이터 흐름
type: document
space: concept
tags: [concept]
created: 2026-05-13
updated: 2026-05-20
links:
  - "[[P0-brainstem/brain/Loragent-brain/P0-brainstem/禁/禁auto_validate.neuron]]"
  - "[[P0-brainstem/brain/Loragent-brain/P0-brainstem/禁/禁brain_obsidian_graph.neuron]]"
  - "[[P0-brainstem/brain/Loragent-brain/P0-brainstem/禁/禁subagent_verify.neuron]]"
  - "[[P0-brainstem/brain/rules]]"
  - "[[P3-sensors/gateway/platforms/ADDING_A_PLATFORM]]"
  - "[[P3-sensors/resolver/RESOLVER.md]]"
  - "[[P3-sensors/skills/SKILL-INDEX]]"
  - "[[P5-ego/SELF_MODEL]]"
  - "[[P4-cortex/knowledge/NEURONFS_RULES]]"
---


# Loragent 아키텍처 — 데이터 흐름(Data Flow) 문서

**생성일**: 2026-05-13
**Updated**: 2026-05-13 (P0-brainstem enforcement layer)
**Target**: Loragent Agent 전체 데이터 흐름을 모든 레이어에서 추적 가능하게 함

---

## 1. 전체 데이터 흐름 맵 (Layer 7 → Layer 1)

```
Layer 7 — Prefrontal (Strategy / Archive)
    ↕ (long-term memory, growth patterns)
Layer 6 — P6-prefrontal (Planning / Incidents / Migrations)
Layer 5 — P5-ego (Self-Model / Integration Protocol / Brain Config)
    ↕ (self-awareness, integration decisions)
Layer 4 — P4-cortex (Learning / Insights / Growth)
    ↕ (pattern recognition, knowledge synthesis)
Layer 3 — P3-sensors (Gateway / Cron / Skills / Tools)
    ↕ (input routing, platform state)
Layer 2 — P2-hippocampus (Session DB / Memory / Context)
    ↕ (context window, session history)
Layer 1 — P1-limbic (Persona / SOUL / Voice)
    ↕ (identity, tone, style)
Layer 0 — P0-brainstem (Critical Rules / Safety / Never-Do)
```

---

## 2. 메시지 생명周期的 흐름 (End-to-End Trace)

```
[Platform: Discord/Telegram/etc.]
         │
         ▼
┌──────────────────────────────────────────────────────────────────┐
│ gateway/run.py — GatewayRunner                                     │
│                                                                  │
│  1. PlatformAdapter.receive(message)                             │
│     → _handle_message(event: MessageEvent)                       │
│                                                                  │
│  2. _is_user_authorized(source)                                  │
│     → pairing check                                              │
│                                                                  │
│  3. Commands check (/reset, /new, /retry...)                     │
│     → _handle_reset_command(), etc.                              │
│                                                                  │
│  4. session_store.get_or_create_session(source)                  │
│     → SessionContext (P2-hippocampus)                            │
│                                                                  │
│  5. build_session_context()                                      │
│     → platform config, model routing, session env                 │
│                                                                  │
│  6. build_session_context_prompt()                               │
│     → injected into system prompt (P1-limbic voice)              │
│                                                                  │
│  7. _set_session_env(context)                                    │
│     → environment variables for tools                           │
│                                                                  │
│  8. adapter.send() — home channel notice (if first session)      │
│                                                                  │
│  9. adapter.send() — typing indicator                            │
│                                                                  │
│  10. _write_session_in_progress() → checkpoint file             │
│                                                                  │
│  11. hooks.emit("agent:start", hook_ctx)                         │
│                                                                  │
│  12. await _run_agent(message, context_prompt, history, ...)      │
│      → _handle_message_with_agent() ←────────────────────────────────┐
│         │                                                               │
│         │  gateway/run.py — _run_agent()                                │
│         │  (runs in ThreadPool, returns Dict)                            │
│         │                                                               │
│         │  12a. from run_agent import AIAgent                           │
│         │  12b. progress_callback() — queues streaming updates          │
│         │  12c. AIAgent(...) — creates agent instance                   │
│         │  12d. agent.run_conversation() ←─────────────────────────────────┤
│         │                                                                    │
│         │    run_agent.py — AIAgent.run_conversation()                         │
│         │    (1,723-line core agent loop)                                    │
│         │                                                                    │
│         │    ┌─ pre-turn ─────────────────────────────────────────────────┐  │
│         │    │  • _restore_primary_runtime()                              │  │
│         │    │  • _sanitize_surrogates()                                 │  │
│         │    │  • task_id = uuid.uuid4()                                  │  │
│         │    │  • IterationBudget reset                                  │  │
│         │    │  • _cleanup_dead_connections()                             │  │
│         │    └───────────────────────────────────────────────────────────┘  │
│         │                                                                    │
│         │    ┌─ Phase 3-1: Build messages ─────────────────────────────────┐  │
│         │    │  • conversation_history loaded from session_db (P2)         │  │
│         │    │  • system prompt from prompt_builder.py (P1-limbic)         │  │
│         │    │  • _build_messages() → List[Dict]                         │  │
│         │    └───────────────────────────────────────────────────────────┘  │
│         │                                                                    │
│         │    ┌─ emit_turn_start() — P0-brainstem pre-validation ─────────┐  │
│         │    │  → event_bus.emit("turn.start")                            │  │
│         │    │  → _on_turn_start()                                        │  │
│         │    │    ├→ pattern detect: rm -rf / chmod 777 / sudo           │  │
│         │    │    └→ emit("dangerous.op") → _on_dangerous_op()           │  │
│         │    │          └→ _dangerous_ops_history += [op]                 │  │
│         │    │          └→ emit("awareness.integrity") if severity=high    │  │
│         │    └───────────────────────────────────────────────────────────┘  │
│         │                                                                    │
│         │    ┌─ Phase 3-2: Tool loop (api_call_count < max_iterations) ──┐  │
│         │    │                                                           │  │
│         │    │  while loop:                                              │  │
│         │    │    1. _api_call_count++ → _touch_activity()               │  │
│         │    │    2. iteration_budget.consume()                         │  │
│         │    │    3. _interruptible_api_call()                          │  │
│         │    │       → LLM API call (Anthropic/OpenAI/etc.)             │  │
│         │    │       → stream_callback (TTS pipeline)                    │  │
│         │    │       → returns messages list                             │  │
│         │    │    4. _handle_api_response()                              │  │
│         │    │       → parse assistant message                            │  │
│         │    │       → extract tool_calls[], content, reasoning          │  │
│         │    │    5. For each tool_call:                                 │  │
│         │    │       → tools registry.lookup(name)                        │  │
│         │    │       → tool.execute(args)                                 │  │
│         │    │       → tool result → messages.append()                   │  │
│         │    │    6. _checkpoint_mgr.snapshot()                          │  │
│         │    │    7. repeat until no more tool_calls                     │  │
│         │    └───────────────────────────────────────────────────────────┘  │
│         │                                                                    │
│         │    ┌─ Phase 3-3: emit_turn_end() — P0-brainstem post-verification┐  │
│         │    │  → event_bus.emit("turn.end")                               │  │
│         │    │  → _on_turn_end()                                           │  │
│         │    │    ├→ check 禁blind_write: write_file without prior read   │  │
│         │    │    ├→ check 禁secrets_in_code: sk-/ghp-/password= in args │  │
│         │    │    ├→ check 禁console_log: console.log/print() in code     │  │
│         │    │    └→ emit("rule.violation") → _on_rule_violation()        │  │
│         │    │          └→ _violation_history += [{rule, tool, severity}] │  │
│         │    │          └→ emit("awareness.integrity")                    │  │
│         │    └───────────────────────────────────────────────────────────┘  │
│         │                                                                    │
│         │    ┌─ emit_agent_complete() — P0-brainstem final gate ─────────┐  │
│         │    │  → event_bus.emit("agent.complete")                        │  │
│         │    │  → _on_agent_complete()                                    │  │
│         │    │    ├→ for wf in _active_workflows:                        │  │
│         │    │    │   if not wf.completed:                              │  │
│         │    │    │      emit("workflow.incomplete")                      │  │
│         │    │    │      → _on_workflow_incomplete()                     │  │
│         │    │    │         └→ _workflow_history += archived_workflow     │  │
│         │    │    └→ emit("session.violations") (by-rule summary)         │  │
│         │    └───────────────────────────────────────────────────────────┘  │
│         │                                                                    │
│         │    Returns: {final_response, messages, api_calls, completed}     │
│         │                                                                    │
│         └─ AIAgent.run_conversation() ─────────────────────────────────────┘
│         │                                                                    │
│         │  Returns Dict to gateway                                          │
│         └─ _run_agent() returns to _handle_message_with_agent() ◄──────────┘
│                                                                  │
│  13. stop_typing()                                               │
│                                                                  │
│  14. response = agent_result["final_response"]                   │
│                                                                  │
│  15. agent:end hook → hooks.emit("agent:end", hook_ctx)          │
│                                                                  │
│  16. if agent_result.already_sent:                              │
│         → _deliver_media_from_response()                          │
│         → return None (streaming already delivered)               │
│                                                                  │
│  17. Transcript write:                                          │
│      session_store.append_to_transcript(session_id, new_messages)│
│      → P2-hippocampus/sessions/{id}.jsonl                       │
│                                                                  │
│  18. session_store.update_session()                             │
│                                                                  │
│  19. _send_voice_reply() if TTS enabled                         │
│                                                                  │
│  20. adapter.send(response) → PlatformAdapter                   │
│      → Discord/Telegram/etc. (back to platform)                  │
│                                                                  │
│  21. _write_session_complete() → checkpoint file                 │
│                                                                  │
└─ GatewayRunner ────────────────────────────────────────────────────────┘
         │
         ▼
[Platform: Discord/Telegram/etc. — Response delivered]
```

---

## 3. 세션/메모리 데이터 흐름

### 3.1 세션 생성 → 소멸 (Life Cycle)

```
Platform message arrives
    │
    ▼
session_store.get_or_create_session(source: SessionSource)
    │
    ├─ Check P2-hippocampus/sessions/*.db for existing session
    ├─ If found: return SessionContext(session_key, session_id, history)
    └─ If not: create new SessionContext
                  → session_id = uuid.uuid4()
                  → P2-hippocampus/sessions/{id}.db created
                  → session_store.append_to_transcript() — session_meta entry
                  → emit("session:start") hook
    │
    ▼
history = session_store.load_history(session_id)
    │
    ├─ P2-hippocampus/sessions/{id}.db → SQLite query
    ├─ Transcript: P2-hippocampus/sessions/{id}.jsonl
    └─ Returns: List[Dict] — full conversation history
    │
    ▼
[Agent runs — run_conversation()]

After agent completes:
    │
    ▼
session_store.append_to_transcript(session_id, new_messages)
    │
    ├─ JSONL file write (always)
    └─ SQLite INSERT (if session_db available)
    │
    ▼
session_store.update_session(session_key, last_prompt_tokens=...)
    │
    ▼
[On gateway shutdown — _cleanup_session()]
    │
    ▼
_auto_learner.on_session_end(messages)
    ├─ Full conversation summarization via LLM
    ├─ Cross-turn pattern detection
    ├─ Entity/concept linking to wiki
    └─ → P2-hippocampus/memories/insights/

_memory_manager.on_session_end(messages)
    ├─ Flush pending memory items
    └─ → P2-hippocampus/memories/

AutoLearner.run_maintenance()
    ├─ Delete expired sessions
    └─ Archive old patterns
```

### 3.2 메모리 계층 (Memory Hierarchy)

```
┌─────────────────────────────────────────────────────┐
│ Prompt Builder — system prompt rebuilt each turn     │
│   - SOUL.md (P1-limbic)                             │
│   - AGENTS.md                                       │
│   - P0-brainstem neurons                            │
│   - session context                                 │
└─────────────────────────────────────────────────────┘
                    │
                    ▼ (context window)
┌─────────────────────────────────────────────────────┐
│ AIAgent conversation_history (in-memory)             │
│   - Loaded from session_db (P2) each turn           │
│   - Pre-filtered by _build_messages()               │
│   - System messages stripped before API call        │
│   - _flush_messages_to_session_db() periodically   │
└─────────────────────────────────────────────────────┘
                    │
                    ▼ (8,000 char context limit)
┌─────────────────────────────────────────────────────┐
│ ContextCompressor — compresses long sessions        │
│   - _compress_conversation()                       │
│   - Triggers /compact command when over threshold   │
│   - Preserves key entities and turn structure       │
│   - Summary template: Goal, Progress, Decisions,    │
│     Files, Next Steps, Critical Context             │
│   - Last Exchange section (2026-05-21): verbatim    │
│     last user message + Assistant Intent preserved  │
└─────────────────────────────────────────────────────┘
                    │
                    ▼ (session end)
┌─────────────────────────────────────────────────────┐
│ AutoLearner (P4-cortex)                             │
│   - learn_from_turn() — per-turn insight extraction │
│   - on_session_end() — deep reflection             │
│   - → P2-hippocampus/memories/insights/            │
│   - → Obsidian wiki (user/memory target)           │
└─────────────────────────────────────────────────────┘
```

---

## 4. Brain Signal System — Layer 3 (P3-sensors) Event Bus

```
agent/brain_signals.py (SignalEmitter — 428 lines)
agent/event_bus.py (BrainEvent + EventBus singleton — 344 lines)
agent/signal_processor.py (SignalProcessor — 1736 lines)
agent/awareness_reporter.py (AwarenessReporter — 370 lines)
```

### 4.1 Signal Emitter API (brain_signals.py)

```python
emit_turn_start(turn_number: int, user_message: str)
    → event_bus.emit("turn.start", payload={turn_number, user_message})

emit_turn_end(turn_number: int, assistant_response: str, tool_calls: List[Dict])
    → event_bus.emit("turn.end", payload={...})

emit_agent_complete(session_id: str, message_count: int)
    → event_bus.emit("agent.complete", payload={...})

emit_tool_start(tool_name: str, args: Dict)
emit_tool_complete(tool_name: str, result: str, success: bool)
emit_session_end(summary: str, message_count: int, tool_count: int)
emit_user_prompt(message: str)
emit_qa_gate(task_id: str, phase: str, evidence_dir: str)
```

### 4.2 SignalProcessor Handler Chain

```
turn.start  →  _on_turn_start()  →  dangerous.op  →  _on_dangerous_op()
                                              ↓
                                       _dangerous_ops_history += [op]
                                              ↓
                                       awareness.integrity (if high)

turn.end  →  _on_turn_end()  →  rule.violation  →  _on_rule_violation()
                                          ↓
                                   _violation_history += [{rule, tool, severity}]
                                          ↓
                                   awareness.integrity

agent.complete  →  _on_agent_complete()
                      ├→ workflow.incomplete  →  _on_workflow_incomplete()
                      │                                ↓
                      │                         _workflow_history += archived
                      └→ session.violations (summary)

integration.complete  →  _on_integration_complete()
                             └→ awareness.integrity (integration complete)
```

### 4.3 Integration Workflow Tracking

```python
ArchitectureModel (P4-cortex evaluation via P3-sensors processing):
    TOOL_INTEGRATION_FILES = ["tools/", "model_tools.py", "toolsets.py"]
    SKILL_INTEGRATION_FILES = ["skills/", "agent/skill_commands.py"]
    GATEWAY_PLATFORM_FILES = ["gateway/platforms/", "gateway/run.py"]
    SLASH_COMMAND_FILES = ["loragent_cli/commands.py", "cli.py"]
    MCP_SERVER_FILES = ["tools/mcp_tool.py", "tools/<name>.py"]
    CRON_JOB_FILES = ["cron/jobs.py", "cron/scheduler.py"]

    detect_*_integration_progress() → is_complete + missing_files + next_hint
```

---

## 5. Gateway — Platform Adapters

```
gateway/run.py — GatewayRunner (8,652 lines)
    │
    ├── adapters: Dict[Platform, BasePlatformAdapter]
    │   ├── discord.py — DiscordBot
    │   ├── telegram.py — TelegramBot
    │   ├── slack.py — SlackBot
    │   ├── whatsapp.py — WhatsAppBot
    │   └── ... (12 platforms)
    │
    ├── session_store: SessionStore (P2-hippocampus)
    │
    ├── hooks: LoragentHooks (lifecycle events)
    │
    ├── _auto_learner: AutoLearner (P4-cortex)
    │
    ├── _memory_manager: MemoryManager (P2-hippocampus)
    │
    └── _run_agent() → AIAgent.run_conversation()
```

### 5.1 Platform Message → Agent → Response

```
Platform adapter receives message
    → MessageEvent(text, source, user_id, chat_id, thread_id, ...)
    → _handle_message(event)
    → session_store.get_or_create_session()
    → build_session_context_prompt()
    → _run_agent() — ThreadPool
    → AIAgent.run_conversation()
    → response string
    → adapter.send(response)
    → session_store.append_to_transcript()
```

---

## 6. P Layer — 데이터 저장소 (Where Data Lives)

```
P0-brainstem/
    agent/signal_processor.py      ← brain signal enforcement
    agent/event_bus.py             ← event bus singleton
    agent/brain_signals.py         ← signal emitter API
    agent/brain_monitor.py         ← brain health monitor
    agent/brain_processor.py       ← brain processing logic

P1-limbic/
    persona/SOUL.md                ← identity & voice
    persona/writing-style-guide.md ← Korean writing style
    persona/AGENTS.md             ← coding principles

P2-hippocampus/
    memories/
        insights/2026-05.md       ← monthly insight log
        insights/.archive/         ← archived insights
        entities/                   ← wiki entity pages
    sessions/
        *.db                       ← SQLite session DBs
        *.jsonl                     ← transcript JSONL files
    state.db                       ← state database

P3-sensors/
    gateway/
        run.py                     ← GatewayRunner (8,652 lines)
        session_manager.py          ← session lifecycle
        delivery.py                ← DeliveryRouter
        platforms/                 ← platform adapters
    cron/                          ← cron job definitions
    skills/                        ← skill definitions

P4-cortex/
    growth/patterns/               ← session workflow patterns
    knowledge/                     ← knowledge base
    scripts/                       ← automation scripts

P5-ego/
    SELF_MODEL.md                  ← self-awareness model
    INTEGRATION_PROTOCOL.md        ← tool/skill integration guide
    config/                         ← configuration files
    state/                          ← runtime state

P6-prefrontal/
    logs/                          ← log files
    archive/                        ← old versions, migrations
    incidents/                      ← incident reports
```

---

## 7. 파일 참조 테이블 (Cross-Reference)

| 구성요소 | 파일 | 주요 클래스/함수 |
|---------|------|----------------|
| Gateway core | `gateway/run.py:7145` | `_run_agent()` → `_handle_message_with_agent()` → `AIAgent.run_conversation()` |
| Agent core | `run_agent.py:8356` | `AIAgent.run_conversation()` — tool loop, API calls |
| Brain signals | `agent/brain_signals.py` | `emit_turn_start/end`, `emit_agent_complete` |
| Event bus | `agent/event_bus.py` | `EventBus.emit()`, `EventBus.subscribe()` |
| Signal processor | `agent/signal_processor.py` | `_on_turn_start/end`, `_on_agent_complete`, `_on_workflow_incomplete` |
| Integration tracking | `agent/signal_processor.py` | `ArchitectureModel.detect_*_integration_progress()` |
| Session store | `gateway/session_manager.py` | `SessionStore.get_or_create_session()`, `load_history()`, `append_to_transcript()` |
| AutoLearner | `agent/auto_learn.py` | `AutoLearner.learn_from_turn()`, `on_session_end()` |
| Memory manager | `agent/memory_manager.py` | `MemoryManager.on_session_end()` |
| Prompt builder | `agent/prompt_builder.py` | system prompt construction (SOUL, AGENTS, context) |
| Delivery | `gateway/delivery.py` | `DeliveryRouter.deliver()`, `_deliver_to_platform()` |
| Platform adapters | `gateway/platforms/*.py` | `BasePlatformAdapter.send()` |

---

## 8. 신호 흐름 검증 (2026-05-13 기준)

```python
Full flow integration test:

turn.start  →  dangerous_ops=1  →  awareness.integrity (high)
turn.end   →  violations=2    →  awareness.integrity (×2)
agent.complete → workflow_history=1

Total emitted events: 11
  turn.start, dangerous.op, awareness.integrity,
  turn.end, rule.violation, awareness.integrity,
  turn.end, rule.violation, awareness.integrity,
  agent.complete, workflow.incomplete, session.violations
```

모든 핸들러가 event bus를 통해 subscriber에게 도달함 — **누수/단절 없음**.

---

## 9. 알려진 아키텍처 특성

### 9.1 AIAgent.run_conversation() — ThreadPool 실행
`_run_agent()`는 `asyncio.to_thread()`로 ThreadPool에서 실행. `AIAgent.run_conversation()`은 **동기 함수**이며 스레드 안전하도록 설계됨.

### 9.2 Gateway는 asyncio, Agent는 동기
`gateway/run.py` — async/await 기반
`run_agent.py` — threading-based (동기)
→ `gateway/run.py`가 스레드풀에서 `AIAgent`를 호출

### 9.3 transcript dual-write 방지
`_handle_message_with_agent()`에서 `agent_persisted = self._session_db is not None`으로 DB write를 건너뛰고 JSONL만 기록. SQLite duplicate-write bug (#860) 회피.

### 9.4 wf.started_at None trap — Python attribute 접근법
`hasattr(obj, attr)`은 attr이 존재하고 값이 `None`일 때도 `True`를 반환.
`getattr(obj, attr, None)`은 값이 `None`이면 세 번째 인자를 반환.
→ Fix: `getattr(wf, "started_at", None)` 사용.

### 9.5 platform-specific toolset routing
`run_agent.py:712`에서 `_get_platform_tools()`로 플랫폼별 사용 가능한 도구 집합 결정.
gateway config.yaml의 `platforms` 섹션에서 각 플랫폼의 toolsets 설정.

### 9.6 checkpoint for crash recovery
`_write_session_in_progress()` — 세션 시작 시 checkpoint 파일에 "IN_PROGRESS" 기록.
`_write_session_complete()` — 세션 완료 시 "COMPLETED"로 업데이트.
`_SESSION_CHECKPOINT_PATH` — crash 후 orphaned session 정리용.

## Related Documentation

- [[P5-ego/SELF_MODEL]] — P5-Ego self-awareness model (identity anchor)
- [[P3-sensors/gateway/platforms/ADDING_A_PLATFORM]] — How to add a new platform adapter to Loragent gateway
- [[P0-brainstem/brain/rules]] — P0 Brainstem absolute rules
- [[P3-sensors/resolver/RESOLVER.md]] — Context routing table (on-demand document loading)

---

## 태그

#architecture #data-flow #lifecycle #p-folder #signal-system #session #memory #gateway

## Links
- [[P0-brainstem/brain/Loragent-brain/P0-brainstem/禁/禁auto_validate.neuron]]
- [[P0-brainstem/brain/Loragent-brain/P0-brainstem/禁/禁brain_obsidian_graph.neuron]]
- [[P0-brainstem/brain/Loragent-brain/P0-brainstem/禁/禁subagent_verify.neuron]]
- [[P3-sensors/skills/SKILL-INDEX]]

---
title: headroom token compression — Drewgent POC + integration guide
name: token-compression-headroom
description: How to measure and cut token cost on Drewgent tool outputs. Two paths — headroom_ai library (POC done, deferred) and Drewgent-native 4-layer cap pattern (3 patches live, 78-80% savings). Auto-apply the cap pattern whenever you add or modify a tool that emits over 5K chars of JSON. Use when evaluating token compression, seeing high token cost on tool output, or adding a new tool that returns large records.
domain: software-development
created: 2026-06-02
updated: 2026-06-02
links:
  - "[[skills/software-development/external-tool-evaluation]]"
  - "[[skills/software-development/python-nested-import-nameerror]]"
  - "[[skills/software-development/llm-model-migration]]"
  - "[[P4-cortex/portfolio/drewgent]]"
  - "[[P4-cortex/knowledge/NEURONFS_RULES]]"
  - "[[P4-cortex/knowledge/headroom-poc-20260602]]"
  - "[[P4-cortex/knowledge/token-compression-headroom-20260602]]"
  - "[[P0-brainstem/brain/Drewgent-brain/P0-brainstem/禁/禁task_qa_gate.neuron]]"
  - "[[P0-brainstem/brain/rules]]"---

# headroom (token compression) — Drewgent POC + integration guide

## Auto-apply rule — for new/modified tools

**When adding a new tool OR modifying a tool's output schema, the agent MUST self-apply this checklist:**

1. **Will the tool's JSON output exceed 5,000 chars in typical use?**
   - Yes (e.g., list endpoints, bulk queries, file reads) → apply the cap pattern (next section)
   - No (e.g., single-record lookups, small status checks) → skip the cap, ship as-is

2. **What is the largest text field in the response?**
   - Identifiable (e.g., `body`, `content`, `stdout`, `output`, `data`) → add `body_chars` or `max_chars` param
   - Indistinguishable / mixed → apply 40/60 split to the entire JSON-encoded response

3. **Default cap value:**
   - Bulk list endpoints (kanban_list, search results): 500-1000 chars
   - Single-record gets (kanban_get, doc fetch): 3000-5000 chars
   - File reads (read_file): 20000 chars (rare to hit)

4. **Apply the pattern (see "Drewgent-native alternative" section below for full code template).**

5. **Document in the tool's schema what the cap does, the default, and how to override.**

6. **Test with the largest real-world output you've seen, not synthetic small data.**

7. **Restart gateway** (`launchctl kickstart -k gui/$UID/ai.custom-agent.gateway`) — local tool patches don't auto-reload.

**The 3 reference implementations (2026-06-02):**
- `file_tools.py:read_file` — `max_chars` (20K default)
- `kanban_tools.py:kanban_list` — `include_body` (default false) + `body_chars` (500)
- `kanban_tools.py:kanban_get` — `body_chars` (5K)

**Skip the cap pattern for:** source code files, image results, real-time streams (use `agent/context_compressor.py` instead for those).

## When to use this skill

You're evaluating `headroom-ai` (chopratejas/headroom, 4.3k stars, 60B+ tokens saved) for Drewgent, OR you're cutting token cost on Drewgent tool outputs. Use this skill to:
- Install headroom-ai in Drewgent's Python 3.14 venv (ABI3 workaround required)
- Run a POC to verify the 60-92% claim on real Drewgent tool outputs
- Apply the **Drewgent-native 4-layer cap pattern** (no library needed) — see "Drewgent-native alternative" section
- Decide between (a) full surgical integration (b) JSON-only opt-in (c) skip
- Debug `transforms_applied` logs when something looks off

## Install — Python 3.14 venv (PITFALLS)

PyO3 0.22.6 (headroom's Rust binding) does NOT officially support Python 3.14. ABI3 forward-compat required:

```bash
PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1 \
  /Users/drew/.drewgent/source/drewgent-agent/.venv/bin/python3 -m pip install headroom-ai
```

**Do NOT use `--no-build-isolation`** (maturin missing in build env → `Cannot import 'maturin'`). With build-isolation + ABI3 env, builds a `cp314` wheel cleanly.

Common symptoms:
- `error: the configured Python interpreter version (3.14) is newer than PyO3's maximum supported version (3.13)` → add the env var
- `Cannot import 'maturin'` → remove `--no-build-isolation` flag

## POC measurement pattern (PITFALLS)

```python
from headroom import compress
from headroom.providers.anthropic import AnthropicProvider

MODEL = "claude-sonnet-4-5-20250929"
provider = AnthropicProvider()  # tiktoken approximation, no client
tc = provider.get_token_counter(MODEL)

# WARMUP — first call triggers Rust/tiktoken/huggingface lazy init (~800ms).
# Without warmup, your first measurement is an outlier (tokens_after can
# exceed tokens_before due to lazy metadata).
_ = compress([{"role": "user", "content": "warmup"}], model=MODEL)

def measure(label, msgs):
    before = tc.count_messages(msgs)
    r = compress(msgs, model=MODEL)
    print(f"{label:40s} | before={before:>5,} | after={r.tokens_after:>5,} "
          f"| ratio={r.compression_ratio:>6.1%} | {r.transforms_applied}")
    return r
```

**Critical debug signal — `r.transforms_applied`**:
- `router:protected:user_message` — user prompt protected (default)
- `router:protected:recent_code` — code protected (CodeCompressor didn't fire)
- `router:mixed:0.04` — actual compression fired (number = ratio bucket)
- `[]` with `optimize=True` — passthrough, nothing compressed (rare)

**If tokens_after > tokens_before despite `optimize=True`**: the message was protected AND metadata overhead made it larger. This is signal not to compress that message type.

## Expected results — Drewgent tool inventory

| Tool output type | Compression | Why |
|---|---|---|
| **JSON array** (web_search, kanban_*, RAG) | **80-90%** ✅ | SmartCrusher row-drop, schema-aware |
| Plain text (browser_snapshot, git log, ls) | 0% | router protects as prose |
| Python source (read_file .py) | 0% or negative | router:protected:recent_code (~16% metadata overhead) |
| Image tool results | 0% via `compress()` API | image comp exists but not in default pipeline |

**Decision rule**: if your tool output is >50% JSON, headroom is worth integrating. Otherwise look at:
- **Drewgent-native 4-layer cap** (see next section) — no library, surgical patches, 78-80% savings on kanban/read
- Drewgent's existing `agent/context_compressor.py` (conversation-level summary, 0.9 threshold, M3 1M compatible)
- Custom JSON-specific compression (schema-aware row drop)

## Drewgent-native alternative — 4-layer cap pattern (no library)

If headroom_ai integration feels heavy, Drewgent already has a working token-saving pattern applied as surgical patches across 4 tool layers. **No library, no latency, no SDK compatibility concerns.**

### What was patched (2026-06-02)

| Layer | Tool | New param | Default | Real saving (measured) |
|-------|------|-----------|---------|------------------------|
| 1 | `terminal` | `tail_lines` (existed pre-2026-06-02) | 50 | long stdout → tail-biased |
| 2 | `read_file` | `max_chars` (NEW) | 20,000 chars | **80%** on 851-line file (25,134 → 5,129) |
| 3 | `kanban_list` | `include_body` (NEW, default false) + `body_chars` | no body / 500 | **78%** on 29 tasks (12,351 → 2,680 tokens) |
| 4 | `kanban_get` | `body_chars` (NEW) | 5,000 chars | **59%** on body=891 (891 → 368) |

**Truncation contract**: when a field exceeds the cap, apply **40% head + 60% tail** split and insert a marker `[... N chars truncated; set body_chars higher ...]`. The model sees the marker, knows it's truncated, can re-call with higher cap. **Zero silent info loss.**

### When to apply this pattern (decision rule)

Use the Drewgent-native cap pattern when:
- Tool output JSON has a "metadata + bulk" shape (e.g., `[{id, title, body}, ...]`)
- The bulk field is read-once by the model then discarded (no follow-up edits)
- You want zero new dependencies and zero added latency

Use headroom_ai instead when:
- Tool output is >50% JSON AND you need semantic compression (not just head/tail)
- You want to compress LLM message lists in-flight (not just tool output post-amble)
- You're already invested in OpenAI/Anthropic SDK message format

### When NOT to use either

- Source code files — both approaches protect code (router:protected:recent_code for headroom, model would re-read with offset for Drewgent-native)
- Image tool results — neither compresses (use vision model summary)
- Real-time streams (cron output, kanban log dumps) — these are better handled at the conversation level (`agent/context_compressor.py`)

### How to apply the cap pattern to a new tool

1. Identify the largest text field in the tool's JSON output (e.g., body, content, stdout, output)
2. Add a `max_chars` or `body_chars` param with sensible default (5,000-20,000 chars ≈ 1.2K-5K tokens)
3. Apply 40% head + 60% tail split if field exceeds cap
4. Add `_truncated: true` field to response when truncated
5. Update tool schema to document the param + its purpose
6. Update `_handle_*` dispatcher if your tool uses one
7. Test with a real call (use the actual largest output you've seen, not synthetic)
8. Restart gateway (`launchctl kickstart -k gui/$UID/ai.custom-agent.gateway`)

**Verification pattern**:
```python
# Test the patch end-to-end
import importlib, sys
sys.path.insert(0, "/Users/drew/.drewgent/source/drewgent-agent")
for m in list(sys.modules):
    if m.startswith("tools.YOUR_TOOL"):
        del sys.modules[m]
import tools.YOUR_TOOL as t
# ... call with and without the new param, compare sizes
```

### 40/60 vs 50/50 split — why Drewgent uses 40/60

Drewgent tool outputs are usually "context header + log dump" shaped. The model's next-action decision lives in the last error / result, which is in the tail. 50/50 would risk cutting the tail. 40/60 is the safe default — header gets less but the model only needs schema there, not body.

All 4 layers use the same 40/60 ratio for consistency.

### Backward compatibility

- `include_body=false` default → LLM that doesn't know about the new param gets the old "metadata only" view, never accidentally a 10K-token body
- `body_chars=5000` default → covers 99% of task bodies in real DB (max seen: 891 chars). Larger bodies trigger marker, model can re-call.
- `max_chars=20000` default → covers typical file reads (most files <500 lines). Larger reads trigger marker.
- No tool was removed; all old params still work.

## Integration options (headroom_ai library, if you still want it)

| Option | Code change | Reversibility | When |
|---|---|---|---|
| A. `headroom wrap claude` proxy | 0 | Easy | ❌ doubles with gateway |
| B. LiteLLM callback | Med | Med | ❌ we use native Anthropic SDK |
| **C. `compress(messages)` wrap in `_interruptible_api_call`** | Med | Flag toggle | ✅ best for full integration |
| D. MCP tool only | Low | Easy | 🤷 fallback if pipeline too complex |

For option C (in `run_agent.py:5244 _interruptible_api_call`, before the client call):
```python
if self.headroom_enabled and self._should_compress(api_kwargs):
    from headroom import compress
    api_kwargs["messages"], stats = compress(api_kwargs["messages"], model=self.model)
    self._headroom_stats_this_session += stats.tokens_saved
```
Add `headroom_enabled: bool = False` to `AIAgent.__init__` and `headroom.enabled: false` to `DEFAULT_CONFIG` (config.yaml:60ish).

## Latency budget (headroom_ai only)

- 5-50ms per call on small messages (typical tool output)
- 50-200ms on large messages (>10KB)
- Acceptable (Drewgent already does 1-3s API roundtrips)
- If latency-sensitive, gate on message length

**Drewgent-native 4-layer cap**: 0ms added latency. The truncation is a string operation (`s[:head] + marker + s[-tail:]`), no parsing, no library call.

## Info preservation verification (Drewgent-specific)

```python
# After compress, verify critical info (URLs, IDs, names) preserved
compressed_str = json.dumps(result.messages[1])
urls_kept = sum(1 for url in original_urls if url in compressed_str)
ids_kept = sum(1 for tid in original_task_ids if tid in compressed_str)
# Target: 100% preservation for any field the LLM needs to act on
```

**For Drewgent-native cap**: the marker is explicit, so verification is just checking `_truncated: true` in the JSON response. No library-specific tokens to count.

## Verification after integration (headroom_ai)

1. Measure `tokens_saved` over a 10-turn Drewgent session (target: 30-60% aggregate)
2. Run an existing workflow end-to-end, verify same final answer
3. Check `_headroom_stats_this_session` after each session
4. Monitor tool failure rate (no regressions)
5. If integrating into `run_agent.py`, run `qa-scenario-gen` tests (latent task → QA gate per `禁task_qa_gate`)

## Verification after Drewgent-native cap patch

1. `python3 -c "import ast; ast.parse(open('tools/your_tool.py').read())"` — syntax check
2. Fresh module reload + call with and without new param — compare response sizes
3. `ps -p $GATEWAY_PID` — confirm gateway still running 30s after restart
4. `tail -50 /Users/drew/.drewgent/logs/gateway.log` — confirm "80 tools loaded" and no import errors
5. `launchctl list | grep gateway` — confirm new PID after kickstart

## Lessons (POC + 4-layer patch, 2026-06-02)

### headroom_ai POC
- **JSON 압축이 핵심 가치**: 89.8% on web_search (4,131 → 482 tokens)
- **text/code는 default 보호**: 0% on browser snapshot, git log, .py
- **결정성 부족**: router policy black-box, 어떤 메시지가 압축될지 외부에서 control 어려움
- **JSON-only opt-in 권장**: `compress()` 명시적 호출 + JSON 도구 inventory로 한정
- **Cumulative 효과 미미**: 1 message 89%, 5 messages 85% — 큰 차이 없음 (last few turns는 protect_recent로 보존)
- **First-call lazy init**: warmup 안 하면 첫 측정만 outlier
- **Tool result는 인식 잘 됨**: OpenAI `role: tool` + `tool_call_id` 포맷 그대로 작동

### Drewgent-native 4-layer cap
- **78-80% saving on real DB**: measured, not estimated
- **40/60 split beats 50/50**: tail-biased, preserves model's next-action context
- **Truncation marker 필수**: silent truncation = model makes decision on incomplete data
- **Default false for `include_body`**: backward-compat zero, LLM can opt in
- **0ms added latency**: pure string op, no library, no SDK
- **Gateway restart needed**: unlike MCP tools (auto-reload), local tool patches need `launchctl kickstart -k gui/$UID/ai.custom-agent.gateway`
- **No new dependency**: 3 patches, ~30 lines added, zero risk of breaking integration

## When to revisit (re-evaluation triggers)

Re-evaluate headroom_ai integration if **2 or more** of these become true:
- MCP tool output is 90%+ JSON (currently ~30% estimated)
- Token cost crosses $100/month
- M3 1M context still triggers compression more than once per week
- headroom_ai adds provider-specific token counting (currently black-box estimate)
- A new tool is added that emits very large JSON (e.g., full RAG corpus dump)

## Related

- `[[skills/software-development/external-tool-evaluation]]` — sibling tool eval pattern
- `[[skills/software-development/python-nested-import-nameerror]]` — sibling Python 3.14 + ABI issue (json UnboundLocalError)
- `[[skills/software-development/llm-model-migration]]` — sibling LLM version change pattern (M2.7→M3)
- `[[P4-cortex/portfolio/drewgent]]` — Drewgent architecture
- `[[P4-cortex/knowledge/NEURONFS_RULES]]` — file system rules
- `[[P4-cortex/knowledge/headroom-poc-20260602]]` — headroom_ai POC result (sibling doc)
- `[[P4-cortex/knowledge/token-compression-headroom-20260602]]` — Drewgent-native 4-layer cap result (sibling doc)
- `[[P0-brainstem/brain/Drewgent-brain/P0-brainstem/禁/禁task_qa_gate.neuron]]` — QA gate (production integration 필수)
- `[[agent/context_compressor]]` — Drewgent's existing conversation-level summarizer (complementary, not redundant)

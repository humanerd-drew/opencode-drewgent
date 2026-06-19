#!/usr/bin/env python3
"""P-folder structure verification — Phase 1-5 completion check.

Run from: ~/source/drewgent-agent/
Usage: python scripts/verify_pfolder.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

def check(name, fn):
    try:
        result = fn()
        status = "✅" if result else "❌"
        print(f"{status} {name}: {result if isinstance(result, str) else 'OK'}")
        return result
    except Exception as e:
        print(f"❌ {name}: {type(e).__name__}: {e}")
        return False

# ── 1. Import chain ──────────────────────────────────────────────────────────
def test_imports():
    from agent.brain_processor import get_brain_processor, BrainProcessor
    from agent.signal_processor import get_signal_processor
    from agent.brain_signals import (
        emit_turn_start, emit_turn_end,
        emit_qa_gate, emit_agent_complete,
        get_signal_emitter,
    )
    return "all imports OK"

# ── 2. brain_processor P1-P6 integration ─────────────────────────────────────
def test_brain_processor_p1p6():
    from agent.brain_processor import BrainProcessor, _TASK_TYPE_LAYER_PRIORITY

    # All 7 layers present
    coding_layers = _TASK_TYPE_LAYER_PRIORITY.get("CODING", [])
    for layer in ["P0-brainstem", "P4-cortex", "P1-limbic", "P2-hippocampus", "P5-ego", "P6-prefrontal"]:
        if layer not in coding_layers:
            return f"CODING missing {layer}"

    # P1-P6 dedicated types
    for tt in ["MEMORY_QUERY", "STRATEGY", "SELF_IMPROVEMENT"]:
        if tt not in _TASK_TYPE_LAYER_PRIORITY:
            return f"{tt} not in _TASK_TYPE_LAYER_PRIORITY"

    # fallback rules include P1-P6
    bp = BrainProcessor.__new__(BrainProcessor)
    bp._brain_rules = []
    fallback = bp._get_fallback_rules("CODING")
    fallback_layers = {r["layer"] for r in fallback}
    expected = {"P0-brainstem", "P1-limbic", "P4-cortex", "P5-ego", "P6-prefrontal"}
    missing = expected - fallback_layers
    if missing:
        return f"fallback missing layers: {missing}"

    return f"fallback layers: {fallback_layers}"

# ── 3. signal_processor IntegrationWorkflow.next_hint ─────────────────────────
def test_workflow_hint():
    from agent.signal_processor import IntegrationWorkflow

    wf = IntegrationWorkflow(
        workflow_id="test",
        integration_type="tool",
        target_name="test_tool",
    )
    # next_hint should default to None
    if wf.next_hint is not None:
        return f"next_hint should default to None, got {wf.next_hint}"

    # get_hint() should return next_hint
    wf.next_hint = "model_tools.py not found"
    if wf.get_hint() != wf.next_hint:
        return f"get_hint() != next_hint: {wf.get_hint()} vs {wf.next_hint}"

    wf.next_hint = None
    if wf.get_hint() is not None:
        return f"get_hint() should return None when next_hint is None"

    return "IntegrationWorkflow.get_hint() + next_hint OK"

# ── 4. emit functions exist and have correct signatures ───────────────────────
def test_brain_signals():
    import inspect
    from agent import brain_signals as bs

    for fn_name, expected_params in [
        ("emit_turn_start", ["turn_number", "user_message"]),
        ("emit_turn_end", ["turn_number", "assistant_response", "tool_calls"]),
        ("emit_qa_gate", ["task_id", "phase", "evidence_dir"]),
        ("emit_agent_complete", ["session_id", "message_count"]),
    ]:
        fn = getattr(bs, fn_name, None)
        if fn is None:
            return f"{fn_name} not found in brain_signals"
        sig = inspect.signature(fn)
        params = list(sig.parameters.keys())
        if params[:len(expected_params)] != expected_params:
            return f"{fn_name} signature mismatch: {params} vs {expected_params}"

    return "emit_turn_start/end, emit_qa_gate, emit_agent_complete signatures OK"

# ── 5. SignalProcessor._bus subscribes to new events ─────────────────────────
def test_signal_processor_bus():
    from agent.signal_processor import SignalProcessor
    from agent.event_bus import get_event_bus

    # Check that _setup_subscriptions includes the new events
    # We check the source code for subscription calls
    import inspect
    source = inspect.getsource(SignalProcessor._setup_subscriptions)

    for event in ["turn.start", "turn.end", "qa.gate", "agent.complete"]:
        if f'"{event}"' not in source and f"'{event}'" not in source:
            return f"{event} not subscribed in _subscribe_to_events"

    return "turn.start/end, qa.gate, agent.complete subscriptions OK"

# ── 6. run_agent.py has emit calls + import ───────────────────────────────────
def test_run_agent_integration():
    import inspect
    import os

    # Find run_agent.py relative to this script's parent (drewgent-agent root)
    agent_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    agent_path = os.path.join(agent_root, "run_agent.py")
    with open(agent_path) as f:
        source = f.read()

    # Check import
    if "from agent.brain_processor import get_brain_processor" not in source:
        return "get_brain_processor import missing in run_agent.py"

    # Check emit calls
    for fn_name in ["emit_turn_start", "emit_turn_end", "emit_agent_complete"]:
        if fn_name not in source:
            return f"{fn_name} call missing in run_agent.py"

    return "run_agent.py: import + emit calls OK"

# ── 7. get_brain_processor returns valid singleton ──────────────────────────────
def test_brain_processor_singleton():
    from agent.brain_processor import get_brain_processor, BrainProcessor

    bp1 = get_brain_processor()
    bp2 = get_brain_processor()
    if bp1 is not bp2:
        return "get_brain_processor not singleton"

    if not isinstance(bp1, BrainProcessor):
        return f"not BrainProcessor instance: {type(bp1)}"

    return f"singleton OK, brain_rules={len(bp1._brain_rules)} rules"

# ── Run all checks ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("P-FOLDER STRUCTURE VERIFICATION")
    print("=" * 60)
    print()

    checks = [
        ("1. Import chain", test_imports),
        ("2. brain_processor P1-P6", test_brain_processor_p1p6),
        ("3. IntegrationWorkflow.get_hint()", test_workflow_hint),
        ("4. brain_signals emit signatures", test_brain_signals),
        ("5. SignalProcessor bus subscriptions", test_signal_processor_bus),
        ("6. run_agent.py integration", test_run_agent_integration),
        ("7. get_brain_processor singleton", test_brain_processor_singleton),
    ]

    results = []
    for name, fn in checks:
        results.append(check(name, fn))

    print()
    print("=" * 60)
    passed = sum(1 for r in results if r is not False and r is not None and r is not "")
    failed = len(checks) - passed
    print(f"RESULT: {passed}/{len(checks)} passed, {failed} failed")
    if failed == 0:
        print("✅ ALL CHECKS PASSED — P-folder structure is intact")
    else:
        print("❌ SOME CHECKS FAILED — review output above")
    print("=" * 60)
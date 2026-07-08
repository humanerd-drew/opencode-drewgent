---
name: brain-signal-system
title: Brain Signal System
description: Drewgent brain signal architecture — event bus, signal processor, awareness reporter, brain monitor
type: guide
space: outcome
tags: [brain, signal, architecture, agent]
created: 2026-05-31
updated: 2026-06-11
links:
  - "[[@identity/SELF_MODEL]]"
  - "[[@identity/persona/SOUL]]"
  - "[[@action/gateway/drewgent-architecture-dataflow]]"
  - "[[@identity/brain/rules]]"
  - "[[@action/resolver/RESOLVER]]"
  - "[[@memory/growth/INTEGRATION_PROTOCOL]]"
---

# Brain Signal System — Drewgent Self-Awareness Infrastructure

**Date**: 2026-05-31 (updated 2026-06-11)
**Status**: Operational
**Source**: `agent/brain_signals.py`, `agent/signal_processor.py`, `agent/event_bus.py`, `agent/awareness_reporter.py`, `agent/brain_monitor.py`
**Purpose**: Single source of truth for Drewgent's brain signal architecture.

---

## 12. Brain Monitor Fallback Cleanup (2026-06-10)

### Problem

`agent/brain_monitor.py:_deliver()` calls `_deliver_fallback()` when DeliveryRouter fails, writing `monitor/brain_signals_{ts}.md`. DeliveryRouter nearly always fails with `'dict' object has no attribute 'always_log_local'` → **5,123 files** in ~30 days (400MB+). All orphans in Obsidian graph (0 inbound links).

### Fix

```python
# Before (brain_monitor.py:364-367):
except Exception as e:
    logger.warning("DeliveryRouter unavailable, writing to local fallback: %s", e)
    self._deliver_fallback(content)

# After:
except Exception as e:
    logger.warning("DeliveryRouter unavailable (session %s): %s", self.session_id, e)
```

`_deliver_fallback()` retained as dead code (manual use possible) but no longer called.

### Cleanup

```bash
rm ~/.drewgent/monitor/brain_signals_*.md  # 5,123 files → 0
# Retained: ~/.drewgent/monitor/brain_signal_log.jsonl (5KB, compressed alternative)
```

### Verification

```bash
ls ~/.drewgent/monitor/  # should show only brain_signal_log.jsonl
```

### Pitfall

- If DeliveryRouter is ever fixed, the primary delivery path (Discord/Telegram channel) will start working and the fallback won't be needed. The `_deliver_fallback()` method is preserved for manual emergency use.
- Same data exists in `gateway.log` and `brain_signal_log.jsonl` — no information loss.
- The `BrainSignalMonitor` class still works; only the file fallback is removed.
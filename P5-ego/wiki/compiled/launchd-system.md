---
title: Launchd & System Operations — Compiled
type: wiki-compiled
tags: [compiled, launchd, system, self-healing, macos, watchdog]
trigger: "wiki-compile 2026-06-21 — compiled from P2-hippocampus; updated with mass failure incident"
provenance:
  session: "2026-06-21 wiki-compile"
  decision: "Launchd plist patterns and self-healing architecture, post-mass-failure hardening"
created: 2026-06-21
updated: 2026-06-21
links:
  - "P5-ego/wiki/compiled/cron-operations"
  - "P5-ego/wiki/compiled/system-incidents"
  - "P5-ego/wiki/compiled/discord-infrastructure"
---

# Launchd & System Operations — Compiled

## Core Decisions

### 1. KeepAlive Template (All Services)
**What:** All launchd plists use the dict form:
```xml
<key>KeepAlive</key>
<dict>
  <key>SuccessfulExit</key><false/>
  <key>ThrottleInterval</key><integer>10</integer>
</dict>
```
**Why:** `SuccessfulExit: false` catches Node.js/Python SIGTERM → exit 0 (both trap SIGTERM and exit cleanly). `ThrottleInterval: 10` prevents restart storm.
**Pitfalls:** Bare `<true/>` = no restart on exit 0. Bare `<false/>` = no restart ever. Both caused incidents.
**Alternatives considered:** Bare true/false, no KeepAlive (pre-6/10 behavior).
**Status:** Active on all 3 Drewgent plists: opencode, discord-bot, cron.

### 2. Three Active Launchd Services
**What:**
- `ai.drewgent.opencode` — headless server on :8642 (opencode serve)
- `ai.drewgent.discord-bot` — Discord ↔ opencode gateway (--attach)
- `ai.drewgent.cron` — cron dispatcher every 60s
**Why:** All use KeepAlive dict template for automatic crash recovery. RunAtLoad for reboot recovery.
**Status:** Active. 5min watchdog monitors all three.

### 3. Label Convention
**What:** Plist filename = label. `ai.drewgent.opencode.plist` → `ai.drewgent.opencode`. Label mismatch was a root cause in the 2026-06-10 mass failure.
**Why:** Customize layer patches Hermes' `get_launchd_label()` to match. Consistency across all services.
**Status:** Active. Gateway label renamed from `ai.custom-agent.gateway` to match filename.

### 4. Self-Healing Architecture
**What:** Multi-layer:
- launchd KeepAlive: crash → 10s auto-restart
- RunAtLoad: reboot → auto-start
- 5min watchdog script (`drewgent_launchd_watchdog.sh`): polls launchd state, alerts Discord on failure
**Why:** Zero manual intervention. Watchdog compensates for launchd not being a real watchdog.
**Alternatives considered:** Docker restart policies, supervisor, s6.
**Status:** Active. Added after mass failure incident.

### 5. Soft Signal Rules for PID Detection
**What:** `launchctl list PID=-` alone is NOT evidence of death (detached processes show PID=- while running). Real evidence: log mtime > 5min stale + cron/output/ mtime > 5min stale.
**Why:** macOS launchd reports PID=- for detached processes still working. Hard-learned from cron-runner debugging.
**Alternatives considered:** Rely on launchctl list alone.
**Status:** Active. Documented in harmony check procedures.

### 6. Launchd Mass Failure Postmortem (2026-06-10)
**What:** All 6 launchd services went down for 4-6 days undetected. Root causes:
1. Services exited cleanly (exit 0) → KeepAlive `SuccessfulExit: false` didn't trigger
2. No infrastructure watchdog existed
3. Gateway plist label mismatch (`ai.custom-agent.gateway` vs filename)
4. Cron-runner had no KeepAlive (only `StartInterval=60`)
5. Gateway housekeeping had broken nested try/except → silent cron ticker death
6. Memory vs reality drift — incidents documented as resolved while infra was dead
**Fix:** Template standardized, watchdog added, label fixed, housekeeping patched.
**Status:** Resolved. All fixes applied within 35 minutes.

### 7. Log Rotation Setup
**What:** Daily 04:00 rotation. 1.7GB error.log → 9.6MB gz. 100MB/7d threshold, 30d retention.
**Why:** Unbounded log growth caused disk pressure.
**Status:** Active.

## Rationale
launchd chosen over Docker for macOS-native lifecycle management. Key lesson: launchd is not a real watchdog — `SuccessfulExit: false` catches process crashes but not silent deaths. Watchdog cron compensates.

## Current Status
All 3 services stable. KeepAlive template standardized after mass failure. 5min watchdog monitors all services. Harmony check Layer 3.5 does cross-diff daily. Log rotation active.

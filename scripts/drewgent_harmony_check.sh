#!/bin/bash
# drewgent_harmony_check.sh
# Cross-layer state diff for Drewgent infrastructure. Run when:
#   - watchdog fires alert (6/10 incident trigger)
#   - user says "에이전트 상태 점검" or similar
#   - cron output is suspicious (no recent files, last_run_at stale)
#
# Compares 4 layers that can drift apart:
#   1. launchd process state (PID table) — what launchd *thinks* is running
#   2. ps aux / lsof — what *actually* is running
#   3. jobs.json (filesystem) — what the *scheduler config* says is scheduled
#   4. Memory "복구됨" claims (memory file) — what *prior agent* believed
#
# Output: structured report. Exit 0 = harmonious, exit 1 = drift detected.
# Designed to run on bare shell even when gateway/cron is dead.
#
# Cited by: 禁incident_aware neuron (P0 rule)

set -o pipefail

# NOTE: deliberately NOT set -u — bash 3.2 (macOS default) trips on associative
# array key expansion with dotted labels. Unbound-var check disabled for safety.

DREW_HOME="${DREW_HOME:-$HOME/.drewgent}"
JOBS_JSON="$DREW_HOME/cron/jobs.json"
LIB_PLIST="$HOME/Library/LaunchAgents"
# Memory is in P2-hippocampus (Drewgent's own), not ~/.claude/ (Codex's)
MEMORY_FILE="$DREW_HOME/P2-hippocampus/memories/MEMORY.md"
LAUNCHD_LABELS=(
  "ai.drewgent.cron-runner"
  "ai.drewgent.gateway"
  "ai.drewgent.kanban-dashboard"
  "ai.drewgent.n8n"
  "com.drewgent.quartz-fswatch"
  "com.drewgent.quartz-deploy"
)

# Per-label process fingerprints (ps grep patterns).
# bash 3.2 (macOS default) has no associative arrays, so use parallel
# arrays indexed by position. Order MUST match LAUNCHD_LABELS above.
PROC_PATTERNS=(
  "cron_runner.py"                              # ai.drewgent.cron-runner
  "drewgent_cli.main.*gateway"                  # ai.drewgent.gateway
  "kanban_dashboard_server.py"                  # ai.drewgent.kanban-dashboard
  "n8n start"                                   # ai.drewgent.n8n
  "quartz-fswatch.sh"                           # com.drewgent.quartz-fswatch
  "quartz-deploy.sh"                            # com.drewgent.quartz-deploy
)

drift=0
output_lines=()

# Helper: append line and bump drift count if marked
emit() {
  output_lines+=("$1")
  if [[ "$1" == *"⚠"* ]] || [[ "$1" == *"❌"* ]]; then
    drift=$((drift+1))
  fi
}

emit "🔍 **Drewgent harmony check** @ $(date '+%Y-%m-%d %H:%M:%S %Z')"
emit ""

# --- Layer 1: launchd view ---
emit "## Layer 1: launchd view (PID table)"
for label in "${LAUNCHD_LABELS[@]}"; do
  line=$(launchctl list 2>/dev/null | awk -v lbl="$label" '$3 == lbl { print; exit }')
  if [ -z "$line" ]; then
    emit "  ❌ $label: not in launchd table"
    continue
  fi
  pid=$(echo "$line" | awk '{print $1}')
  exit_code=$(echo "$line" | awk '{print $2}')
  if [ "$pid" = "-" ] && [ "$exit_code" != "0" ]; then
    emit "  ⚠ $label: PID=- exit=$exit_code"
  elif [ "$pid" = "-" ]; then
    emit "  ~ $label: PID=- exit=0 (graceful stop, ok)"
  else
    emit "  ✓ $label: PID=$pid"
  fi
done

# --- Layer 2: ps aux (ground truth) ---
emit ""
emit "## Layer 2: ps aux (ground truth)"
# Index PROC_PATTERNS by position (parallel to LAUNCHD_LABELS).
# bash 3.2 has no associative arrays, so we use index arithmetic.
i=0
for label in "${LAUNCHD_LABELS[@]}"; do
  pattern="${PROC_PATTERNS[$i]:-}"
  i=$((i+1))
  if [ -z "$pattern" ]; then
    emit "  ~ $label: no pattern configured"
    continue
  fi
  # pgrep with extended regex; -f matches full command line
  ps_pid=$(pgrep -f -i "$pattern" 2>/dev/null | head -1)
  if [ -n "$ps_pid" ]; then
    # Cross-check with launchd
    launchd_pid=$(launchctl list 2>/dev/null | awk -v lbl="$label" '$3 == lbl {print $1; exit}')
    if [ "$launchd_pid" = "$ps_pid" ]; then
      emit "  ✓ $label: ps matches launchd (PID=$ps_pid)"
    elif [ "$launchd_pid" = "-" ] || [ -z "$launchd_pid" ]; then
      emit "  ⚠ $label: ps PID=$ps_pid but launchd detached (PID=-)"
    else
      emit "  ⚠ $label: ps PID=$ps_pid but launchd PID=$launchd_pid (mismatch)"
    fi
  else
    emit "  ❌ $label: no process found via ps (pattern: $pattern)"
  fi
done

# --- Layer 3: jobs.json next_run_at drift ---
emit ""
emit "## Layer 3: jobs.json (scheduler config)"
if [ -f "$JOBS_JSON" ]; then
  layer3=$(python3 - "$JOBS_JSON" <<'PYEOF'
import json, sys, datetime
data = json.load(open(sys.argv[1]))
now = datetime.datetime.now().astimezone()
for j in data.get("jobs", []):
    if not j.get("enabled"):
        continue
    name = j.get("name", "?")
    nxt = j.get("next_run_at", "")
    if not nxt:
        print(f"  ❌ {name:30} next_run_at: NULL (Pattern A — recurring job needs fix)")
        continue
    try:
        nxt_dt = datetime.datetime.fromisoformat(nxt)
    except Exception:
        print(f"  ~ {name:30} next_run_at: {nxt} (unparseable)")
        continue
    if nxt_dt.tzinfo is None:
        nxt_dt = nxt_dt.astimezone()
    delta = (nxt_dt - now).total_seconds()
    if delta < -3600:
        hours = abs(delta) / 3600
        print(f"  ⚠ {name:30} next_run_at in PAST ({hours:.1f}h ago)")
    elif delta < 0:
        print(f"  ~ {name:30} next_run_at: {nxt[:19]} (slightly past)")
    else:
        print(f"  ✓ {name:30} next_run_at: {nxt[:19]}")
PYEOF
)
  while IFS= read -r line; do
    emit "$line"
  done <<< "$layer3"
else
  emit "  ❌ $JOBS_JSON not found"
fi

# --- Layer 3.5: jobs.json mtime vs cron-runner.log "dispatchers run" mtime ---
emit ""
emit "## Layer 3.5b: cron-runner fire frequency (T4 detection)"
# Count === ISO === blocks in cron-runner/<date>.log in the last 5 minutes.
# Each tick should produce exactly 1 fire per minute. 2+ fires within the
# same minute = double-fire (T4 incident). 0 fires = gateway stall.
if [ -d "$DREW_HOME/logs/cron-runner" ]; then
  CR_LOG="$DREW_HOME/logs/cron-runner/$(date +%Y-%m-%d).log"
  # Fall back to yesterday's log if today's doesn't exist (midnight rollover)
  if [ ! -f "$CR_LOG" ]; then
    CR_LOG="$DREW_HOME/logs/cron-runner/$(date -v-1d +%Y-%m-%d).log"
  fi
  if [ -f "$CR_LOG" ]; then
    # 5 min ago epoch
    CUTOFF=$(($(date +%s) - 300))
    # Parse each === ISO === block, convert ISO to epoch, filter >= cutoff
    FIRE_COUNT=$(awk -v cutoff="$CUTOFF" '
      /^=== [0-9]{4}/ {
        # Extract ISO timestamp
        ts = $2
        gsub(/[+].*$/, "", ts)  # Strip +00:00
        gsub(/Z$/, "", ts)       # Strip Z
        gsub(/T/, " ", ts)
        cmd = "date -u -j -f \"%Y-%m-%d %H:%M:%S\" \"" ts "\" +%s 2>/dev/null"
        cmd | getline ep
        close(cmd)
        if (ep+0 >= cutoff) count++
      }
      END { print count+0 }
    ' "$CR_LOG")
    if [ "$FIRE_COUNT" -eq 0 ]; then
      emit "  ⚠ cron-runner log: 0 fires in last 5 min — gateway scheduler may be stalled (T4)"
      fail=$((fail+1))
    elif [ "$FIRE_COUNT" -ge 12 ]; then
      # 5 min window * 1 fire/min = 5 expected. With T4 double-fire (2 fires/min),
      # max = 10. >= 12 means extra abnormal fires beyond double-fire pattern.
      emit "  ⚠ cron-runner log: $FIRE_COUNT fires in last 5 min — abnormal frequency (T4)"
      fail=$((fail+1))
    else
      emit "  ✓ cron-runner log: $FIRE_COUNT fires in last 5 min (expected ~5)"
    fi
  else
    emit "  ~ cron-runner log not found for today"
  fi
else
  emit "  ~ cron-runner dir not found"
fi
emit ""

emit ""
emit "## Layer 3.5: jobs.json mtime drift"
if [ -f "$JOBS_JSON" ]; then
  JOBS_MTIME=$(stat -f %m "$JOBS_JSON" 2>/dev/null || echo 0)
  # cron-runner.py writes to logs/cron-runner/YYYY-MM-DD.log (daily rotated)
  # with format: "=== YYYY-MM-DDTHH:MM:SS... ==="  (no "dispatchers run" word).
  # cron-runner wrapper's own stdout (captured by launchd) goes to
  # logs/cron-runner.log and contains "[ts] cron_runner: N dispatchers run".
  # The gateway scheduler, when running script_only jobs, also writes a
  # "Running job" line to logs/gateway.log.
  DISPATCHER_SOURCES=(
    "$DREW_HOME/logs/cron-runner/$(date +%Y-%m-%d).log"
    "$DREW_HOME/logs/cron-runner.log"
    "$DREW_HOME/logs/gateway.log"
  )
  LATEST_DISPATCH_MTIME=0
  for src in "${DISPATCHER_SOURCES[@]}"; do
    [ -f "$src" ] || continue
    # Look for last "dispatchers run" or "=== ISO ===" line timestamp.
    # Format examples: "=== 2026-06-10T11:59:25.760351+00:00 ===" (UTC) or
    # "2026-06-10 11:59:25" (naive). Convert to UTC epoch seconds.
    LAST_TS=$(grep -E "dispatchers run|=== [0-9]{4}|Running job '" "$src" 2>/dev/null | tail -1 | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}[T ][0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]+)?(Z|[+-][0-9]{2}:?[0-9]{2})?' | head -1)
    if [ -n "$LAST_TS" ]; then
      # Normalize ISO 8601 with Z or +HH:MM offset to +0000
      if [[ "$LAST_TS" == *"+00:00"* ]] || [[ "$LAST_TS" == *"Z"* ]]; then
        # UTC timestamp — convert directly
        LAST_TS_NAIVE="${LAST_TS%Z}"
        LAST_TS_NAIVE="${LAST_TS_NAIVE%+00:00}"
        MTIME=$(date -u -j -f "%Y-%m-%d %H:%M:%S" "$LAST_TS_NAIVE" +%s 2>/dev/null || echo 0)
      elif [[ "$LAST_TS" == *"+"* ]] || [[ "$LAST_TS" == *"-"* ]]; then
        # Has timezone offset, but not UTC. Use python for parse.
        MTIME=$(/Users/drew/.hermes/hermes-agent/venv/bin/python3 -c "
from datetime import datetime
import sys
ts = '$LAST_TS'
# Try ISO 8601 parse
try:
    dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
    print(int(dt.timestamp()))
except Exception as e:
    print(0)
" 2>/dev/null || echo 0)
      else
        # No timezone info, assume system local (which on KST = KST)
        # But the log format is UTC! So treat as UTC explicitly.
        # Replace space with T to make ISO, then parse as UTC.
        ISO="${LAST_TS/T/ }"
        MTIME=$(date -u -j -f "%Y-%m-%d %H:%M:%S" "$ISO" +%s 2>/dev/null || echo 0)
      fi
      if [ "$MTIME" -gt "$LATEST_DISPATCH_MTIME" ]; then
        LATEST_DISPATCH_MTIME=$MTIME
      fi
    fi
  done
  if [ "$LATEST_DISPATCH_MTIME" -gt 0 ]; then
    if [ "$JOBS_MTIME" -gt "$LATEST_DISPATCH_MTIME" ]; then
      AGE=$(( JOBS_MTIME - LATEST_DISPATCH_MTIME ))
      # T10: gateway double-fires interval=1min jobs (2 fires within 0.15s).
      # Jobs.json mtime updated by gateway in-memory save (cron.jobs fast-forward).
      # Within ~90s = normal save timing after tick; > 90s = potentially stale.
      if [ "$AGE" -gt 90 ]; then
        emit "  ⚠ jobs.json modified ${AGE}s after last dispatcher tick — in-memory state may be stale"
      else
        emit "  ✓ jobs.json mtime aligned (${AGE}s after tick, normal)"
      fi
    else
      # T10: gateway double-fires interval=1min jobs (2 fires within 0.15s).
      # Recent dispatcher mtime within 90s of now is normal (60s tick + 30s slack).
      # > 120s = stalled (> 2 ticks of silence).
      NOW_MTIME=$(date +%s)
      SINCE=$(( NOW_MTIME - LATEST_DISPATCH_MTIME ))
      if [ "$SINCE" -gt 120 ]; then
        emit "  ⚠ last dispatcher tick was ${SINCE}s ago (>120s) — scheduler may be stalled"
      else
        emit "  ✓ jobs.json mtime aligns with dispatcher tick (or pre-dates it, ${SINCE}s since last fire)"
      fi
    fi
  else
    emit "  ~ no dispatcher ticks logged yet (no baseline)"
  fi
fi

# --- Layer 4: memory claims vs filesystem ---
emit ""
emit "## Layer 4: memory claims vs filesystem"
# n8n plist claim from memory 6/1
if [ -f "$MEMORY_FILE" ] && grep -q "n8n 셀프호스트 launchd 등록 완료" "$MEMORY_FILE" 2>/dev/null; then
  if [ -f "$LIB_PLIST/ai.drewgent.n8n.plist" ]; then
    emit "  ✓ n8n plist: memory 6/1 claim matches filesystem"
  else
    emit "  ⚠ n8n plist: memory 6/1 says 'registered' but plist MISSING on disk"
  fi
else
  emit "  ~ n8n plist claim: not found in memory (skip)"
fi
# gateway plist label vs filename
if [ -f "$LIB_PLIST/ai.drewgent.gateway.plist" ]; then
  actual_label=$(plutil -extract Label raw "$LIB_PLIST/ai.drewgent.gateway.plist" 2>/dev/null)
  expected_label="ai.drewgent.gateway"
  if [ "$actual_label" = "$expected_label" ]; then
    emit "  ✓ gateway plist: Label = $actual_label (matches filename)"
  else
    emit "  ⚠ gateway plist: Label = $actual_label (filename says $expected_label — drift)"
  fi
fi

# --- Layer 4.5: memory single source of truth ---
emit ""
emit "## Layer 4.5: memory single source of truth"
DREW_MEMORY="$DREW_HOME/P2-hippocampus/memories/MEMORY.md"
CODEX_MEMORY="$HOME/.codex/memories/MEMORY.md"
if [ -f "$DREW_MEMORY" ] && [ -f "$CODEX_MEMORY" ]; then
  DREW_MTIME=$(stat -f %m "$DREW_MEMORY")
  CODEX_MTIME=$(stat -f %m "$CODEX_MEMORY")
  CODEX_NEWER_DAYS=$(( (CODEX_MTIME - DREW_MTIME) / 86400 ))
  if [ "$CODEX_MTIME" -gt $((DREW_MTIME + 86400)) ]; then
    emit "  ⚠ Codex MEMORY.md is ${CODEX_NEWER_DAYS}d newer than Drewgent memory"
    emit "     Drewgent does NOT sync to Codex path. This is informational only."
  else
    emit "  ✓ Drewgent memory is canonical (Codex ${CODEX_NEWER_DAYS}d older or aligned)"
  fi
elif [ -f "$DREW_MEMORY" ]; then
  emit "  ✓ Drewgent memory exists; Codex path absent (clean)"
fi

# --- Verdict ---
emit ""
if [ $drift -eq 0 ]; then
  emit "✅ **Verdict**: harmonious (4 layers agree)"
else
  emit "⚠ **Verdict**: $drift drift signal(s) — see 6/10 incident doc for canonical fix"
fi

printf '%s\n' "${output_lines[@]}"

# Note: drift is local; exit code reflects it for cron alerting
[ $drift -eq 0 ]

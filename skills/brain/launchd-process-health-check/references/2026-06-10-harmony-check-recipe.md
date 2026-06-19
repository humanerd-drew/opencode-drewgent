# 2026-06-10 cross-layer harmony check — recipe

This reference is the **cross-layer diff tool** for when launchd/process health checks pass individually but you suspect the *system* is broken. Created on 2026-06-10 to address the gap where launchd says "PID=ok", ps says "alive", jobs.json says "scheduled" — but the user reports "X not working." The answer was usually: **one layer is stale, the others are lying**.

---

## When to use

- Watchdog fired alert AND ps aux shows process alive AND jobs.json has future-dated entries — yet user reports something broken
- "에이전트 상태 점검" or "agent health check" request from user
- Periodic 24h follow-up after a known incident (Pattern E in `cron-jobs-stalled`)
- After any plist edit / gateway restart / jobs.json patch — sanity check
- Memory says "복구됨" but you're not 100% sure (the canonical memory-vs-reality drift case)

**What it is NOT**: a replacement for watchdog. The watchdog detects single-service outages fast (5min). Harmony check is the *next step*: when single services are alive but the system as a whole is incoherent.

---

## The script

**Path**: `~/.hermes/scripts/drewgent_harmony_check.sh` (Hermes cron requirement)

**Symlink to**: `~/.drewgent/P4-cortex/scripts/drewgent_harmony_check.sh` (canonical source)

**What it compares** — 4 layers that can drift apart:

| Layer | What it represents | Source |
|---|---|---|
| 1. launchd view | What launchd *thinks* is running | `launchctl list` |
| 2. ps aux view | What *actually* is running | `pgrep`/`ps` |
| 3. jobs.json | What the *scheduler config* says is scheduled | filesystem |
| 4. memory claims | What *prior agent* believed | `~/.drewgent/P2-hippocampus/memories/MEMORY.md` |

**Output** (verified, 6/10 17:14 KST run):
```
🔍 Drewgent harmony check @ 2026-06-10 17:14:50 KST

## Layer 1: launchd view (PID table)
  ~ ai.drewgent.cron-runner: PID=- exit=0 (graceful stop, ok)
  ✓ ai.drewgent.gateway: PID=82811
  ✓ ai.drewgent.kanban-dashboard: PID=1543
  ✓ ai.drewgent.n8n: PID=81753
  ⚠ com.drewgent.quartz-fswatch: PID=- exit=254
  ⚠ com.drewgent.quartz-deploy: PID=- exit=1

## Layer 2: ps aux (ground truth)
  ❌ ai.drewgent.cron-runner: no process found via ps (pattern: cron_runner.py)
  ✓ ai.drewgent.gateway: ps matches launchd (PID=82811)
  ...

## Layer 3: jobs.json (scheduler config)
  ✓ SEO Article Harvester          next_run_at: 2026-06-10T18:00:00
  ...

## Layer 4: memory claims vs filesystem
  ✓ n8n plist: memory 6/1 claim matches filesystem
  ✓ gateway plist: Label = ai.drewgent.gateway (matches filename)

⚠ Verdict: 5 drift signal(s) — see 6/10 incident doc for canonical fix
```

---

## The script (verbatim, macOS bash 3.2 compatible)

```bash
#!/bin/bash
# drewgent_harmony_check.sh
# Cross-layer state diff for Drewgent infrastructure.

set -o pipefail
# NOTE: deliberately NOT set -u — bash 3.2 (macOS default) trips on
# associative array key expansion with dotted labels.

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

# --- Layer 2: ps aux ---
emit ""
emit "## Layer 2: ps aux (ground truth)"
i=0
for label in "${LAUNCHD_LABELS[@]}"; do
  pattern="${PROC_PATTERNS[$i]:-}"
  i=$((i+1))
  if [ -z "$pattern" ]; then
    emit "  ~ $label: no pattern configured"
    continue
  fi
  ps_pid=$(pgrep -f -i "$pattern" 2>/dev/null | head -1)
  if [ -n "$ps_pid" ]; then
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

# --- Layer 4: memory claims vs filesystem ---
emit ""
emit "## Layer 4: memory claims vs filesystem"
if [ -f "$MEMORY_FILE" ] && grep -q "n8n 셀프호스트 launchd 등록 완료" "$MEMORY_FILE" 2>/dev/null; then
  if [ -f "$LIB_PLIST/ai.drewgent.n8n.plist" ]; then
    emit "  ✓ n8n plist: memory 6/1 claim matches filesystem"
  else
    emit "  ⚠ n8n plist: memory 6/1 says 'registered' but plist MISSING on disk"
  fi
else
  emit "  ~ n8n plist claim: not found in memory (skip)"
fi
if [ -f "$LIB_PLIST/ai.drewgent.gateway.plist" ]; then
  actual_label=$(plutil -extract Label raw "$LIB_PLIST/ai.drewgent.gateway.plist" 2>/dev/null)
  expected_label="ai.drewgent.gateway"
  if [ "$actual_label" = "$expected_label" ]; then
    emit "  ✓ gateway plist: Label = $actual_label (matches filename)"
  else
    emit "  ⚠ gateway plist: Label = $actual_label (filename says $expected_label — drift)"
  fi
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
```

---

## Cron registration

```
cronjob(action="create", name="Drewgent harmony check (cross-layer diff)",
        no_agent=True, schedule="0 9 * * *",
        script="drewgent_harmony_check.sh")
```

**Schedule**: daily 09:00 KST. Not 5m — this is *follow-up*, not real-time. Runs once a day to catch drift that the 5-min watchdog missed (e.g. memory-vs-filesystem drift that doesn't show in launchd).

---

## False-positive whitelist (verified 2026-06-10)

The script reports `❌` / `⚠` for these — they are KNOWN false positives, do not treat as incidents:

| Service | Layer | Reason it's OK | Verification |
|---|---|---|---|
| `ai.drewgent.cron-runner` | Layer 2 (ps) | `StartInterval=60` means process is idle between ticks; ps grep misses it | Layer 1 exit=0 + cron output mtime < 5min |
| `com.drewgent.quartz-deploy` | Layer 1 (launchd) | `spawn scheduled` — runs on fswatch trigger only, not continuously | Layer 2 shows no `quartz-deploy.sh` process — that's correct |
| `com.drewgent.quartz-fswatch` | Layer 2 (ps) | Wrapper script exits after spawning `fswatch` binary; `fswatch` is the long-running process but doesn't match the wrapper pattern | `pgrep fswatch` should return a PID; if not, that's a real outage |

If the script reports drift on these labels and the verification passes, suppress in the report. The script does NOT do this automatically — it's left to the human/agent to apply the whitelist.

---

## bash 3.2 (macOS) pitfalls hit during 6/10 development

These broke the script's first three attempts. If you're adapting this for your own service list, **do not skip**:

1. **NO `declare -A`** — bash 3.2 (macOS default bash) has no associative arrays. The script uses parallel indexed arrays (`LAUNCHD_LABELS` + `PROC_PATTERNS`) with `i=$((i+1))` indexing. Migrating to bash 4+ via `brew install bash` and changing shebang to `#!/opt/homebrew/bin/bash` is also valid, but increases portability cost.
2. **NO `set -u`** — combined with associative array keys, `set -u` trips on dotted label expansion. Use `set -o pipefail` only.
3. **`${1//./_}` arithmetic quirk** — bash 3.2 sometimes interprets the dot in parameter substitution as arithmetic. Use explicit `local out="$1"; out="${out//./_}"; echo "$out"` instead.
4. **Bash arithmetic on dotted variable names** — `drift_count=$((drift_count+1))` works, but `drift.ai.drewgent=$((...))` would trip. Don't use dots in arithmetic-context variable names.
5. **`heredoc` + python3** — works fine but use `<<'PYEOF'` (single-quoted) to prevent bash from interpolating `$` inside Python.

---

## What "harmonious" means

A run is "harmonious" when:
- All watched launchd labels have either a live PID OR a graceful exit=0 (idle but not crashed)
- All ps patterns that should match (Layer 1 says running) do match in Layer 2
- All enabled jobs.json entries have future-dated `next_run_at` (within 1h of being slightly past is normal — cron ticks every 60s)
- All memory claims about plist existence match filesystem truth
- All plist Labels match their filenames

A run is "drift detected" when ANY of the above fails. The script counts the failures and reports. **Do not auto-fix from harmony check** — the script's job is to surface, not to act. Fix decisions are human/agent decisions.

---

## When the script is too quiet

If harmony check shows everything green but the user still reports problems:
- The 4 layers checked are the *most common* drift points. Other possibilities:
  - Inside a process: e.g. agent loop hung but process is alive
  - Network: gateway can't reach Discord
  - Database: kanban DB corrupted
  - Config: yaml changed but not loaded
- These are *not* launchd-level problems. Use `drewgent-runtime-checkup` skill for those.

---

## Related

- `禁incident_aware.neuron` (P0 policy) — fires this script's invocation when watchdog alerts or user requests "에이전트 상태 점검"
- `cron-jobs-stalled` — Pattern E recovery sequence; run harmony check *after* Pattern E restart to verify the fix
- `references/2026-06-10-incident-fix-recipe.md` — sibling reference for the watchdog (5-min poll) and the canonical KeepAlive block
- `references/2026-06-10-log-rotation-recipe.md` — sibling reference for log size management

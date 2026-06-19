# Customize Layer Smoke Test — Reference

The T5/T6/T7/T8 smoke test, written 2026-06-10 19:34, runs weekly via
cron `f0b39d211970` (Sun 10:00 KST). All 4 checks pass as of 2026-06-10 19:36.

## Why this exists

The customize layer (`~/.drewgent/customize/`) is fragile in 3 ways:

1. **`~/.local/bin/hermes` wrapper** can be reinstalled by `hermes` upgrade,
   which would re-add `unset PYTHONPATH` and silently kill the layer.
2. **`hermes_cli.gateway` symbols** can be renamed upstream. If `get_launchd_label`
   becomes `get_launchd_label_v2`, our override silently no-ops.
3. **MEMORY.md wikilinks** can drift from vault reality (file renames,
   neuron deletions, knowledge refactors).

Without a smoke test, all 3 failures are *silent*. The user only notices
when `hermes cron list` says "Gateway is not running" (which they then
ignore as a known false-positive — or worse, take seriously and start
patching things that aren't broken).

## The 4 checks

### T5: hermes wrapper integrity
```bash
grep -E "^[[:space:]]*unset[[:space:]]+PYTHONPATH[[:space:]]*$" \
  ~/.local/bin/hermes > /dev/null
# If matches: ✗ (customize layer is being killed)
# If no match: ✓ (PYTHONPATH preserved, layer intact)
```

The anchored regex is critical. Naive `grep "PYTHONPATH"` matches
`unset PYTHONHOME` and produces a false positive (verified 6/10 19:35).

### T6: customize layer importable
```bash
PYTHONPATH=~/.drewgent/customize \
  ~/.hermes/hermes-agent/venv/bin/python -c "
from hermes_cli.gateway import get_launchd_label
assert get_launchd_label() == 'ai.drewgent.gateway'
"
# If assertions pass: ✓
```

This exercises the full proxy chain: `~/.drewgent/customize/hermes_cli/gateway.py`
loads the real hermes module, mirrors its symbols, then patches the
two we override. If any step in the proxy breaks (e.g. upstream renames
`find_gateway_pids` to `find_gateway_processes`), the import fails or
the assertion fails.

We also test `find_gateway_pids()` to confirm it returns a non-empty
list (gateway must be alive for the smoke test to be meaningful).

### T7: run_agent.py regression grep
```bash
~/.hermes/hermes-agent/venv/bin/python -c "
from pathlib import Path
text = Path.home().joinpath('.drewgent/logs/gateway.log').read_text(errors='ignore')
print(text.count('api_start_time is not defined'))
"
# Output must be 0
```

This is the F3 follow-up from 6/10 incident doc section 6.6. The
`NameError: api_start_time` was reported in a 9.6M-line error log
dump but `grep -c` returned 0. We add this as a T7 regression test
in case the error re-emerges under stress. If a future session sees
this counter > 0, that's a real signal — investigate.

### T8: memory wikilink integrity
Delegates to `drewgent_graph_gap_analysis.sh --dangling-only` and counts
the actual `⚠ dangling:` alert lines (not the section header).

```bash
DANGLES=$($HOME/.hermes/scripts/drewgent_graph_gap_analysis.sh --dangling-only 2>/dev/null | grep -c "⚠ dangling:" 2>/dev/null)
DANGLES=${DANGLES:-0}
# 0 = ✓, >0 = ✗ (with count)
```

Naive `grep -c "dangling"` matches the section header `## Dangling wikilinks`,
giving a constant false-positive count. Use the alert line marker (verified
6/10 19:35).

## Cron registration

```bash
hermes cronjob create \
  --name "Drewgent customize smoke test (weekly)" \
  --schedule "0 10 * * 0" \
  --no-agent true \
  --script "customize_smoke_test.sh"
```

**Script path constraint**: with `no_agent=True`, hermes requires the
script to live under `~/.hermes/scripts/` and be referenced by *bare
filename*. The actual implementation can live anywhere; symlink or
copy is fine.

## Output format

```
🔍 **Drewgent customize smoke test** @ 2026-06-10 19:36:04 KST

## T5: hermes wrapper
  ✓ /Users/drew/.local/bin/hermes does not unset PYTHONPATH (customize layer safe)
  ✓ /Users/drew/.local/bin/hermes.bak exists (original, for rollback)

## T6: customize layer
  ✓ get_launchd_label() = ai.drewgent.gateway
  ✓ find_gateway_pids() found 1 gateway process(es)

## T7: regression check (NameError api_start_time)
  ✓ 0 occurrences of 'api_start_time is not defined' (T7 confirmed false alarm)

## T8: memory wikilink integrity
  ✓ all memory wikilinks resolve

✅ **Verdict**: all checks pass
```

Silent-when-OK is the convention. The smoke test exits 0 on success
and prints only on failure.

## When to extend

Add a new check when a *new class* of silent failure appears. Examples
from 6/10:
- T5/T6 added because the customize layer was new and untested
- T7 added because a phantom error in a 9.6M-line log fooled a previous
  investigation (it was a visual artifact, not a real error)
- T8 added because memory wikilinks were restructured and danglings
  appeared transiently

Don't add a check for *known transient state* (e.g. "gateway PID=- is
fine during startup"). Those are documented in `launchd-process-health-check`
sub-pattern 2 (D2: launchd tracking failure).

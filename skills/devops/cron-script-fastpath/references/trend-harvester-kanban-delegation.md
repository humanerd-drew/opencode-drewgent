# Worked Example: Trend Harvester Pipeline Redesign (2026-06-13)

## Problem

Trend Harvester cron job kept timing out with:
```
TimeoutError: idle for 603s (limit 600s)
  — last activity: waiting for provider response (streaming)
```

Root cause: **LLM-based cron job** with `model: null, provider: null`.
At the time, the default model was `anthropic/claude-opus-4.6` via OpenRouter.
The agent prompt was just "Run python3 script, then summarize." The script ran fine, but the
LLM call at the end took >600s to start streaming (OpenRouter queue). The cron
scheduler's 600s idle limit killed the job.

**Mid-session model routing change (2026-06-14):** User switched all model routing
to `opencode-go/deepseek-v4-flash` — both Hermes and Drewgent configs now use
`provider: opencode-go` as the sole provider. The old `anthropic/claude-opus-4.6`
and OpenRouter routes are retired. See `references/opencode-go-models.md` for the
verified model catalog.

Meanwhile, **279 keep items** (scored trends) sat in `analyzed/keep/` with zero
ever applied — the evaluation → application → retirement pipeline never existed.

## Solution: Split into 5 Stages

Key insight: not all stages need LLM. Split along LLM-dependency boundaries
and delegate LLM stages to kanban workers.

### Stage 1: Collection (no_agent, 6h cron)

```json
{
  "name": "trend-collect",
  "script": "trend_harvester.py",
  "no_agent": true,
  "schedule": "0 */6 * * *"
}
```

Pure deterministic script. Scrapes GitHub trending + RSS, scores through
5-axis filter, writes to `analyzed/{keep,review,graveyard}/`.
Zero LLM tokens, zero timeout risk.

### Stage 2: Evaluate Trigger (LLM, daily cron)

Lightweight LLM agent. Single task: check state → call `kanban_create()` →
done. Uses fast model (`opencode-go/deepseek-v4-flash`) to avoid timeout.
The cron itself finishes in under 30s because it delegates the heavy LLM work.

### Stage 3: Evaluation (kanban worker)

Created by the trigger. Worker reads keep items, evaluates each with LLM,
decides APPLY/DISCUSS/DEFER/DISCARD. For each APPLY, creates a child kanban
task `trend-apply-<name>`. Worker has its own timeout budget independent of
the cron scheduler's 600s.

### Stage 4: Usage Watch (no_agent, daily cron)

Script-only, deterministic. Checks `applied/` items against skill dirs,
config files, neurons. Flags items with zero references for >30 days.

### Stage 5: Retire Trigger (LLM, weekly cron)

Same pattern as evaluate-trigger. Lightweight → delegates to kanban worker.

## Architecture Diagram

(same as trend-evaluate but for taste-review-trigger:
```
cron: taste-review-trigger (화/금 10:00, fast LLM)
  → kanban_create(title="taste-review: YYYY-MM-DD", ...)
    → kanban worker (web_search + file + terminal)
      → taste-reviews/YYYY-MM-DD-slug.md
      → applied/YYYY-MM-DD-hash.json
```

```
  trend-collect                  trend-evaluate-trigger
  (no_agent, 6h)                 (fast LLM, daily 10:00)
       │                                │
       ▼                                ▼
 analyzed/keep/              kanban_create(
 (JSON files)                  title="trend-evaluate:...",
                                assignee="default")
                                        │
                                        ▼
                                ┌─────────────────┐
                                │ kanban worker    │
                                │ (LLM reasoning)  │
                                │ evaluate → APPLY │
                                └────────┬────────┘
                                         │
                                  ┌──────┴──────┐
                                  ▼              ▼
                           evaluated/       kanban_create(
                           (results)         title="trend-apply-<name>")  
                                                │
                                                ▼
                                        ┌────────────────┐
                                        │ kanban worker   │
                                        │ (apply trend)   │
                                        │ → applied/      │
                                        └────────┬───────┘
                                                 │
                                                 ▼
                                        ┌──────────────────────┐
                                        │ trend-usage-watch     │
                                        │ (no_agent, daily)     │
                                        └──────────┬───────────┘
                                                   ▼
                                            .usage_report.json
                                                   │
                                                   ▼
                                        ┌──────────────────────┐
                                        │ trend-retire-trigger  │
                                        │ (fast LLM, weekly)    │
                                        │ → kanban worker       │
                                        │ → archive/            │
                                        └──────────────────────┘
```

## Key Design Decisions

1. **no_agent for collection and monitoring.** Deterministic scripts.
   No LLM → no timeout, zero cost.

2. **Fast model for trigger crons.** `opencode-go/deepseek-v4-flash` is
   cheap and fast. Trigger agent makes 1 tool call and finishes in <30s.
   No risk of hitting the 600s idle limit.

3. **Kanban delegation for LLM reasoning.** Evaluation/application/retirement
   need LLM judgment. Run as kanban workers with own timeout budget.

4. **Full lifecycle design.** Not just collect → done. The user asked for:
   evaluate → compare with existing → apply → watch → retire.

5. **Comparison logic during evaluation.** Check existing skills/configs/
   neurons before deciding: NEW vs UPGRADE vs REPLACE vs DISCUSS vs DISCARD.

## Also Migrated: Taste Review (2026-06-14)

Same pattern applied to Taste Review cron job (was `29ccd2c5d019`, same 603s timeout):

| Before | After |
|--------|-------|
| LLM cron (model: null → default heavy model) | LLM trigger (fast model: `opencode-go/deepseek-v4-flash`) |
| Direct execution in cron (600s idle risk) | `kanban_create` → kanban worker (independent timeout) |
| Single monolithic prompt | Trigger: check state + create task. Worker: web research + analysis |

## Key Files

| File | Purpose |
|------|---------|
| `P4-cortex/growth/trend-harvester/evaluated/` | Eval results dir |
| `scripts/trend_usage_watch.py` | Usage monitoring |
| `jobs.json` | 5 crons (4 trend + 1 taste) replaced 2 old LLM crons |

---
name: trend-harvester
title: trend-harvester
type: skill
space: outcome
tags: [outcome]
created: 2026-05-20
updated: 2026-06-14
description: "AI Trend Collection & Filtering — collect GitHub trending repos, score via 5-axis philosophy filter, evaluate, apply, and retire."
links:
  - "[[@action/skills/SKILL-INDEX]]"
  - "[[@memory/growth/trend-harvester/index]]"
---

# Trend Harvester — Full Pipeline

## Architecture Overview

```
[수집]   trend_harvester.py     (no_agent, 6h)
  │
  ▼
[평가]   kanban worker          (LLM, daily)
  │       ┌──────────────┐
  │       │ apply/discuss │
  │       │ defer/discard │
  │       │ + 비교 (기존과)│
  ▼       └──────────────┘
[적용]   kanban worker          (LLM, per-item)
  │       ┌─────────────────────┐
  │       │ skill patch/create  │
  │       │ neuron update       │
  │       │ config change       │
  ▼       └─────────────────────┘
[관찰]   trend_usage_watch.py   (no_agent, daily)
  │
  ▼
[폐기]   kanban worker          (LLM, weekly)
          ┌─────────────────────┐
          │ 검토 → retire       │
          │ 또는 keep           │
          └─────────────────────┘
```

## Pipeline Stages

### 1. 수집 (Collection)
- **Cron**: `trend-collect` (no_agent, `0 */6 * * *`)
- **Script**: `trend_harvester.py`
- **Output**: `collected/` → `analyzed/{keep,review,graveyard}/`
- **LLM 필요?**: ❌ No

### 2. 평가 (Evaluation)
- **Trigger cron**: `trend-evaluate-trigger` (LLM, daily 10:00 KST)
- **Worker**: Kanban worker (profile: default, trend-harvester skill loaded)
- **Input**: `analyzed/keep/*.json` (아직 evaluated/에 없는 항목)
- **Process**:
  1. Read keep JSON file
  2. Search existing skills/config/neurons for comparison
  3. Evaluate using 5-axis filter + comparison logic
  4. Decide: **APPLY** / **DISCUSS** / **DEFER** / **DISCARD**
  5. Write result to `evaluated/YYYY-MM-DD-hash.json`
  6. If APPLY: copy to `pending/`, create child kanban task `trend-apply-<name>`
  7. If DISCUSS: create kanban task for human review
- **Output**: Workers create child tasks for each APPLY item
- **LLM 필요?**: ✅ Yes

### 3. 적용 (Application)
- **Trigger**: Created as child task by evaluation worker
- **Worker**: Kanban worker
- **Input**: `pending/<name>.json`
- **Process**:
  1. Decide tier: Tier 1-2 (auto-apply) or Tier 3-4 (human approval)
  2. Auto-apply: create skill (Tier 1), patch existing skill (Tier 2)
  3. Human-approval: kanban task with draft + options
  4. Move to `applied/<name>.json` with provenance metadata
- **LLM 필요?**: ✅ Yes

### 4. 관찰 (Usage Watch)
- **Cron**: `trend-usage-watch` (no_agent, `0 6 * * *`)
- **Script**: `trend_usage_watch.py`
- **Process**:
  1. Read `applied/` items
  2. Check each against:
     - Skill directories: matching skill exists?
     - Config files: referenced?
     - Neuron/rules files: referenced?
  3. Classify: **active** / **stale** (30d+ no reference) / **recent_unreferenced**
  4. Write `.usage_report.json`
- **Output**: Summary to Discord, stale candidates flagged
- **LLM 필요?**: ❌ No

### 5. 폐기 (Retirement)
- **Trigger cron**: `trend-retire-trigger` (LLM, weekly Monday 10:00)
- **Worker**: Kanban worker
- **Input**: `.usage_report.json` (stale candidates)
- **Process**:
  1. Read stale items from usage report
  2. For each: confirm no hidden dependencies
  3. Archive: move to `archived/` with retirement note
  4. If still needed: reset `last_seen` to "exempt"
- **Output**: Archived items + summary
- **LLM 필요?**: ✅ Yes

## 판정 기준 (Evaluation Decision Matrix)

| Decision | Condition | Action |
|----------|-----------|--------|
| **APPLY** | score ≥ 6.0 AND no_model_dependency ≥ 0.7 AND (no existing OR clearly better) | → pending/ + child task |
| **UPGRADE** | existing skill found AND new item is strictly better | → pending/ (replace target) |
| **DISCUSS** | needs human judgment (architectural, Tier 3-4) | → kanban task (human) |
| **DEFER** | promising but not now (high effort, low urgency) | → evaluated/ with defer date |
| **DISCARD** | score < 4.0 OR model-dependent OR worse than existing | → graveyard/ |

## Pipeline State

| Directory | Purpose |
|-----------|---------|
| `collected/` | Raw GitHub/RSS scrape output |
| `analyzed/keep/` | Passes 5-axis filter (score ≥ 6.0) |
| `analyzed/review/` | Borderline (4.0 ≤ score < 6.0) |
| `analyzed/graveyard/` | Rejected (score < 4.0) |
| `evaluated/` | Keep items that have been LLM-evaluated |
| `pending/` | Approved for application, waiting for worker |
| `applied/` | Successfully applied |
| `archived/` | Previously applied but retired |

## Cron Jobs Summary

| Job | Schedule | Type | Model | LLM? |
|-----|----------|------|-------|------|
| `trend-collect` | `0 */6 * * *` | no_agent | — | ❌ |
| `trend-evaluate-trigger` | `0 10 * * *` | LLM agent | opencode-go/deepseek-v4-flash | ✅ (light) |
| `trend-usage-watch` | `0 6 * * *` | no_agent | — | ❌ |
| `trend-retire-trigger` | `0 10 * * 1` | LLM agent | opencode-go/deepseek-v4-flash | ✅ (light) |

## Troubleshooting

### Stale PID Lock Recovery
Same as before — `pkill -f trend_harvester` + `rm -f .harvester.lock`

### LLM Timeout (Evaluate Trigger)
Uses fast model (deepseek-v4-flash). If still timing out, check opencode-go API status.

### Kanban Worker Not Picking Up Tasks
Check kanban dispatcher is running (`launchctl list | grep cron-runner`)

## Integration with Drewgent

- **P4-cortex/growth/trend-harvester/** — Storage
- **P4-cortex/knowledge/harvester_sync_state.json** — Memory sync state
- **P4-cortex/growth/trend-harvester/.eval_state.json** — Evaluation state
- **P4-cortex/growth/trend-harvester/.usage_report.json** — Usage watch report
- **kanban board** — Worker tasks for evaluation/application/retirement

## Related
- [[@action/skills/SKILL-INDEX]]
- [[@memory/growth/trend-harvester/index]]
- [[taste-review]]

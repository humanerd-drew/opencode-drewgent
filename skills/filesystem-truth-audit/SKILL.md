---
name: filesystem-truth-audit
description: memory/vault의 "Done" path claim이 실제 filesystem에 존재하는지 검증
title: Filesystem Truth Audit — Memory vs Reality 검증
type: skill
space: growth
tags: [skill, filesystem-truth, audit, memory, vault, diagnostics]
created: 2026-06-01
updated: 2026-06-01
links:
  - "[[P0-brainstem/brain/Drewgent-brain/P0-brainstem/禁/禁filesystem_truth.neuron]]"
  - "[[P5-ego/SELF_MODEL]]"
  - "[[P3-sensors/gateway/drewgent-architecture-dataflow]]"
  - "[[P0-brainstem/brain/rules]]"---

# Filesystem Truth Audit — Memory vs Reality 검증

memory/vault/위키에 적힌 "Done" 또는 "exists" 항목이 실제 filesystem에 존재하는지 검증하는 스킬. P0-brainstem filesystem_truth 강제.

## Trigger

다음 중 하나:
- memory에 있다고 했는데 실제로 없음 의심
- root consolidation / source dir 이동 / rename 이후 검증
- 새 skill/tool/script의 path를 memory에서 인용할 때
- filesystem = truth 점검 요청

## Procedure

### Step 1: Claim 추출

memory/vault에서 path claim 찾기:

```bash
grep -rn "Done" ~/.drewgent/P0-brainstem ~/.drewgent/P4-cortex ~/.drewgent/P2-hippocampus 2>/dev/null | head -20
grep -rn "tools/.*\.py" ~/.drewgent/P4-cortex/growth 2>/dev/null | head -10
```

"tools/drewgent_kanban_db.py (Phase 1) Done" 같은 줄 추출.

### Step 1b: Config value claim 추출

memory/vault에서 config value claim (config 변경 사실) 찾기:

```bash
# threshold 같은 config 변경 claim
grep -rn "threshold:" ~/.drewgent/P4-cortex/growth 2>/dev/null | head -10
grep -rn "0.5 → 0.9\|0.5 -> 0.9" ~/.drewgent/P4-cortex ~/.drewgent/P6-prefrontal 2>/dev/null | head -10
grep -rn "applied\|patched\|configured" ~/.drewgent/P4-cortex/growth 2>/dev/null | head -10
```

"compression.threshold: 0.5 → 0.9 (2026-05-21)" 같은 줄 추출.

### Step 2: Real filesystem 검증

```bash
# 2a. 단일 path 직접 확인
test -f /Users/drew/.drewgent/source/drewgent-agent/tools/drewgent_kanban_db.py && echo EXISTS || echo MISSING

# 2b. 이름으로 전체 검색
find ~/.drewgent -name "drewgent_kanban_db.py" -type f 2>/dev/null

# 2c. wildcard 패턴 검증
ls ~/.drewgent/source/*/tools/*.py 2>/dev/null | wc -l
```

### Step 3: Symlink / Root confusion 처리

Drewgent는 root가 바뀔 수 있음:
- 옛 root: `~/.drewgent/source/claude-code`
- 신 root: `~/.drewgent/source/drewgent-agent`
- quarantine: `~/.drewgent/P6-prefrontal/archive/quarantine-.../`

```bash
readlink -f /Users/drew/.drewgent/source/drewgent-agent 2>/dev/null
ls -la ~/.drewgent/source/ 2>/dev/null
ls -la ~/.drewgent/P6-prefrontal/archive/ 2>/dev/null
```

### Step 4: Discrepancy Report

| Memory claim | Reality | Severity |
|--------------|---------|----------|
| tools/X.py Done | 파일 부재 | HIGH (broken ref) |
| ~/.drewgent/source/old/ path | 새 root로 이동 | MEDIUM (outdated) |
| script path in jobs.json | 실제 script 부재 | HIGH (cron fail) |
| table 존재 (memory) | DB에 부재 | MEDIUM (gap) |

### Step 5: Fix

- HIGH (broken ref): script 재작성 또는 memory 정정
- MEDIUM (outdated): memory 정정. links: frontmatter도 같이 업데이트
- LOW (cosmetic): vault graph orphan에 wikilink 추가

## Pitfalls

- readlink 없이 ls로 확인하면 symlink target를 모름
- brain root를 source root로 착각 — `~/.drewgent` (brain home) ≠ `~/.drewgent/source/drewgent-agent` (code root)
- quarantine 안에 진짜 있을 수도 — 옛 파일이 archive로 이동했을 수 있음
- vault path ≠ filesystem path — wikilink `[[P4-cortex/...]]` ↔ `~/.drewgent/P4-cortex/...` 변환 필요
- "Done" marker는 validation 안 됨 — implementation_plan.md 등의 status를 무조건 신뢰하지 말 것

## Verification

```bash
test -f PATH_1 && test -f PATH_2 && ... && echo "ALL OK"
N_CLAIM=$(grep -c "Done" PATH_TO_MEMORY.md)
N_REAL=$(find ~/.drewgent/source -name "*.py" | wc -l)
echo "claimed=$N_CLAIM real=$N_REAL"
```

## Example (2026-06-01)

- Claim: tools/drewgent_kanban_db.py Done
- Reality: find 0 hits
- 해석: dispatcher script가 자체 sqlite3 코드 갖고 있어서 import 안 함
- Action: memory 정정

## Related

- [[P0-brainstem/brain/Drewgent-brain/P0-brainstem/禁/禁filesystem_truth.neuron]] — P0 강제 규칙
- [[P5-ego/SELF_MODEL]] — self-model에 path claim
- [[P6-prefrontal/migrations/drewgent-root-consolidation-20260506]] — root 변경 migration

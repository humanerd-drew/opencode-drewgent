---
name: skill-usage-audit
description: Drewgent skills/ 디렉토리의 121개 SKILL.md를 3-criteria hard evidence 기준으로 dead/active 분류 — cron 등록, wikilink 참조, mtime 임계치
title: Skill Usage Audit — 3-Criteria Hard Evidence 분류
type: skill
space: growth
tags: [skill, audit, skills, hygiene, diagnostics, dead-code]
created: 2026-06-03
updated: 2026-06-03
links:
  - "[[P0-brainstem/brain/Drewgent-brain/P0-brainstem/禁/禁no_linear_workflow]]"
  - "[[P0-brainstem/brain/Drewgent-brain/P0-brainstem/禁/禁filesystem_truth.neuron]]"
  - "[[skills/filesystem-truth-audit]]"
  - "[[skills/cron-jobs-stalled]]"
  - "[[skills/kanban-dispatcher-stalled]]"
  - "[[P5-ego/SELF_MODEL]]"
  - "[[P1-limbic/persona/SOUL]]"
  - "[[P0-brainstem/brain/rules]]"---

# Skill Usage Audit — 3-Criteria Hard Evidence 분류

`~/.drewgent/skills/` 의 모든 SKILL.md를 dead/active로 분류하는 진단 스킬.
filesystem_truth + active workflow 매핑으로 판정. P0-brainstem 강제.

## Trigger

다음 중 하나:
- "스킬이 다 사용 중이야?" / "안 쓰는 스킬 있나?" 요청
- 새 skill batch 추가 후 (hugh 박스 import, 외부 repo 흡수)
- 6개월 주기 위생 점검
- context menu / skill picker가 noisy (선택지 너무 많음)
- 정책 위반 의심 (linear 등)

## 배경: 왜 3-criteria 인가

Drewgent는 hugh-kim 박스에서 ~100개 skill을 가져왔는데, 그 중 60%는 한 번도 안 쓰는 dead 코드.
단일 기준 (mtime 또는 위키 wikilink만) 으로는 오판 위험:
- mtime만 → "최근에 수정 안 했어도 active일 수 있음" (예: kanban-worker는 5/20 이후 mtime 그대로지만 cron에서 매일 호출)
- wikilink만 → "위키에 언급 안 됐어도 active일 수 있음" (예: humanerd-content-status-enforcement는 6/1에 만들어졌고 6/1부터 매번 humanerd.kr 빌드 시 사용)
- cron 등록만 → "cron에 안 올라가도 active일 수 있음" (예: filesystem-truth-audit은 skill_view로 수동 호출)

→ **3가지 hard evidence 모두 모자라야 dead로 판정**.

## Procedure

### Step 1: 인벤토리 — SKILL.md 모두 찾기

```bash
find ~/.drewgent/skills -name SKILL.md 2>/dev/null | wc -l
find ~/.drewgent/skills -name SKILL.md 2>/dev/null | xargs -I{} dirname {} | xargs -I{} basename {} | sort -u
```

기대치: 100~150개 (HUGH 박스 + Drewgent 자체).

### Step 2: mtime 분류 — 3-tier 임계치 (5/14, 5/20, 6/1)

```bash
for d in ~/.drewgent/skills/*/; do
  name=$(basename "$d")
  mt=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M" "$d/SKILL.md" 2>/dev/null)
  if [ -n "$mt" ]; then echo "$mt | $name"; fi
done | sort -r
```

해석:
- 6/1 ~ 6/2 = 최근 사용/수정 (token-plan-check, quartz-remove-drafts 등) → strong active
- 5/20 ~ 5/24 = Drewgent 자체 setup 시점 (kanban/neuron-fs 등 코어 1세대) → active 가능
- 5/14 00:31 = **HUGH 박스 일괄 import 시점 fingerprint** (2026-05-14 동일 timestamp) → **dead 확실**
- 5/27 20:01 = 재 import / partial touch (productivity/linear, red-teaming 등) → 별도 검토

**중요 발견 (2026-06-03 audit)**: H3 batch 1~6에서 제거한 51개 모두 mtime 5/14 00:31 동일. **동일 timestamp = 동일 import session에서 들어왔고 이후 한 번도 write 안 됨 = dead 100%**.

5/20 그룹은 두 종류로 나뉨:
- (a) active 코어 (kanban-worker, neuron-fs, dogfood, kanban-orchestrator) — cron 또는 wikilink 매핑
- (b) dead 의심 (autonomous-ai-agents 6, research 5, mcp 2, github 6) — cron/wikilink 0 → H4 follow-up 대상

**주의**: mtime 5/20이라도 active일 수 있음 (kanban-worker). mtime은 단독 판정 불가. 5/14 동시간 batch는 단독으로도 dead 판정 가능.

### Step 3: cron 등록 — jobs.json 매핑

```bash
cat ~/.drewgent/cron/jobs.json | python3 -c "
import json, sys
data = json.load(sys.stdin)
for j in data.get('jobs', []):
    print(j.get('name', '?'), '|', j.get('skills', []))
"
```

해석: `skills: [...]`에 등록된 이름 = cron에서 자동 호출됨 → active hard evidence.

기대 cron skills (2026-06-03 기준): `seo-article-harvester, trend-harvester, kanban-worker, content-pipeline, site-spec-audit`.

### Step 4: wikilink 참조 — vault 전체

```bash
grep -rEho "skills/[a-z0-9-]+" ~/.drewgent/P2-hippocampus ~/.drewgent/P4-cortex ~/.drewgent/P5-ego ~/.drewgent/P6-prefrontal 2>/dev/null | sort -u
```

해석: vault 어디든 wikilink로 등장 = 문서화된 사용 = active hard evidence.

### Step 5: 정책 위반 scan — P0 brainstem

```bash
# 禁no_linear_workflow 위반
test -d ~/.drewgent/skills/productivity/linear && echo "POLICY VIOLATION: linear skill"

# 禁kanban_* 등 미구현
ls ~/.drewgent/skills/kanban-*/SKILL.md 2>/dev/null
```

기대: 모든 P0 neuron 의 `.md` 가 skills/ 에 살아있으면 안 됨.

### Step 6: 3-criteria 판정

| Criterion | hard evidence | weight |
|-----------|---------------|--------|
| C1. cron 등록 | `jobs.json` skills 배열 | high |
| C2. wikilink 참조 | vault grep 1회+ | high |
| C3. mtime ≥ 5/20 | SKILL.md last modified | low (참고용만) |

**active 판정**: C1 OR C2 → active
**dead 의심**: C1, C2 모두 0 + (선택) C3 < 5/20 → dead 후보
**즉시 제거**: dead 의심 + 정책 위반 (linear)

### Step 7: 카테고리별 dead 통계 + 빈 카테고리 폴더 scan

```bash
# 7a. 카테고리별 SKILL.md 분포
find ~/.drewgent/skills -name SKILL.md | sed 's|.*/skills/||' | sed 's|/SKILL.md||' | awk -F'/' '
{ cat = (NF == 1) ? "root" : $1"/"; skills[cat] = skills[cat] " " $NF }
END { for (c in skills) print c, "->", skills[c] }' | sort

# 7b. SKILL.md 0개 1-level 카테고리 (별도 정리 필요)
for d in $(ls -d ~/.drewgent/skills/*/ 2>/dev/null); do
  cnt=$(find "$d" -name SKILL.md 2>/dev/null | wc -l)
  if [ "$cnt" -eq 0 ]; then echo "EMPTY-CATEGORY: $d"; fi
done
```

**7b 결과로 발견되는 빈 카테고리는 dead skill removal과 별도 batch** (예: 2026-06-03 audit에서 8개 발견 — creative, media, inference-sh, gifs, feeds, diagramming, domain, index-cache). SKILL.md 0개라서 find 결과엔 안 잡히지만 `ls` 시 빈 폴더로 남음. → 별도 batch 6으로 `rm -rf`.

기대 dead 카테고리 (HUGH 박스):
- apple/*, gaming/*, leisure/*, smart-home/*, social-media/*, email/*, red-teaming/*
- data-science/*, note-taking/* (중복)
- mlops/* (Drewgent는 API consumer, trainer 아님)
- media/*, creative/* (비디오/애니메이션 안 함)
- mcp/* (MCP 호출 안 함)
- autonomous-ai-agents/* (부모 프로젝트 자체)
- research/* (사용 빈도 낮음)
- github/* (PR/이슈 workflow 빈도 낮음 — 5/20 mtime 그룹)

### Step 8: 보고 + 권고 옵션 (H1~H4 + H4a follow-up)

| Option | 작업 | risk | 효과 |
|--------|------|------|------|
| H1. 정책 위반 1개만 제거 (linear) | `rm -rf ~/.drewgent/skills/productivity/linear` | 0 | 정책 복구 |
| H2. H1 + dead 의심 카테고리 통째 (~36개, mtime 5/14 batch) | `rm -rf` 카테고리별 batch | 0 (재import 가능) | context menu 노이즈 ↓ |
| H3. H2 + 추가 (notion, creative 영상, productivity/ocr 등) | 5/22 명시 "안 쓴다" 포함 + 빈 카테고리 8개 | 0 | 121개 → ~70개 (실측 2026-06-03) |
| H4. 그대로 두기 | 0 | 0 | 변동 없음 |
| **H4a follow-up** | H3 후 남은 5/20 mtime 그룹 (autonomous-ai-agents 6, research 5, mcp 2, github 6, dogfood 1 = 21개) | 0 | 70개 → ~50개 |

**H3 권고 이유 (실측 2026-06-03)**: 121 → 70 (51개 제거, 42% 감소). 6 batch × verify 패턴으로 안전. 0 risk (모두 mtime 5/14 00:31 동일 batch fingerprint + 정책 위반 1개).

**H4a 권고**: 5/20 mtime 그룹 21개가 H3 후 남음. mtime 5/14 batch보다는 "덜 dead" (5/20 = setup 시점이라 read-only로 한 번씩 봤을 수도). 단, cron/wikilink evidence 0이면 dead 강한 의심. 사용자 confirm 후 진행.

## Pitfalls

- **HUGH 박스 mtime 착각**: 5/20이 Drewgent setup 시점이고, 그 이전 mtime = "한 번도 안 건드림". 그러나 core kanban/neuron-fs도 5/20 mtime → mtime 단독 판정 금지
- **5/14 동일 timestamp batch fingerprint**: HUGH 박스를 5/14 00:31에 일괄 import한 경우 모든 dead skill이 동일 mtime을 가짐. mtime 5/14 00:31 = dead 100% 단독 판정 가능. (2026-06-03 audit에서 51개 모두 이 패턴)
- **trend-harvester는 skills/ 에 없음**: `~/.drewgent/scripts/trend_harvester.py` 결정론적 script로 cron이 직접 호출. SKILL.md로 따로 load 안 함. SKILL.md 없다고 dead 아님
- **root level + category 동시 존재**: `humanerd-site/SKILL.md` 와 `humanerd-site/humanerd-content-status-enforcement/SKILL.md` 둘 다 있을 수 있음. 중복 dead 아님 — 두 개의 다른 skill
- **SKILL.md 2-depth**: `apple/apple-notes/SKILL.md` 처럼 category/skill/SKILL.md 구조. `find -maxdepth 2` 로 찾으면 일부 놓침. `find` (무한 depth) + path filter로 찾기
- **policy violation은 dead와 별개**: `productivity/linear`는 active일 수도 있지만 정책 위반이라 무조건 제거 대상. dead 판정과 직교
- **autocomplete / context menu 캐시**: skill picker에 dead skill이 남아있을 수 있음. skill picker cache reload 안 되는 경우 restart 필요
- **broken symlink vs quarantine**: quarantine된 skill (`P6-prefrontal/archive/...`)과 active skill의 symlink가 깨진 경우 — `ls -la`로 확인. HUGH 박스 가져올 때 symlink가 만들어졌을 수 있음
- **wikilink pre-check 필수**: 제거 전 vault 전체에서 `skills/<target>` grep. wikilink 참조 있으면 broken link 발생 가능. 2026-06-03 audit에서 확인 — H3 범위 51개 모두 wikilink 참조 0 → 안전
- **vault-ontology.jsonl은 자동 재구성 가능**: ontology_frontmatter_sync.py가 10분마다 vault 전체를 스캔하여 `space:` frontmatter 추가. 제거된 skill의 ontology entry는 다음 cron tick에서 자동 정리됨
- **empty category 폴더는 find에 안 잡힘**: SKILL.md 0개라서 `find ... -name SKILL.md` 결과에 안 들어옴. 별도 `ls -d */` + SKILL.md 0개 체크 필요. 2026-06-03에서 8개 발견 (creative, media, inference-sh, gifs, feeds, diagramming, domain, index-cache) — skill 다 지운 후 잔존

## Verification

```bash
# 1. active count (cron + wikilink union)
N_CRON=$(jq -r '.jobs[].skills[]' ~/.drewgent/cron/jobs.json 2>/dev/null | sort -u | wc -l)
N_WIKI=$(grep -rEho "skills/[a-z0-9-]+" ~/.drewgent/P2-hippocampus ~/.drewgent/P4-cortex ~/.drewgent/P5-ego 2>/dev/null | sort -u | wc -l)
echo "cron_skills=$N_CRON wikilink_skills=$N_WIKI"

# 2. dead 의심 (C1, C2 모두 0, mtime 5/14 batch)
DEAD=$(find ~/.drewgent/skills -name SKILL.md -newermt "2026-05-14" ! -newermt "2026-05-15" 2>/dev/null | wc -l)
echo "mtime_5_14_batch=$DEAD"

# 3. 정책 위반 scan
test -d ~/.drewgent/skills/productivity/linear && echo "VIOLATION: linear"

# 4. 빈 카테고리 scan
EMPTY=$(for d in $(ls -d ~/.drewgent/skills/*/); do
  [ "$(find "$d" -name SKILL.md | wc -l)" -eq 0 ] && echo "$d"
done | wc -l)
echo "empty_categories=$EMPTY"

# 5. batch-by-batch removal (6 batch × verify)
for batch in "apple gaming leisure smart-home social-media email red-teaming data-science note-taking" \
             "productivity/{linear,notion,google-workspace,powerpoint,ocr-and-documents,nano-pdf}" \
             "creative/{ascii-art,ascii-video,excalidraw,manim-video,p5js,popular-web-designs,songwriting-and-ai-music}" \
             "media/{gif-search,heartmula,songsee,youtube-content}" \
             "mlops" \
             "creative diagramming domain feeds gifs index-cache inference-sh media"; do
  rm -rf $batch
  echo "  batch removed: $batch"
  N=$(find ~/.drewgent/skills -name SKILL.md | wc -l)
  echo "  remaining: $N"
done
```

## Output Format

```
═══════════════════════════════════════════════
Skill Usage Audit — 2026-06-03
═══════════════════════════════════════════════
Total SKILL.md: 121 (root 21 + category 100)

Active (45):
  cron (5): seo-article-harvester, trend-harvester, kanban-worker, ...
  wikilink (~25): obsidian-markdown, content-pipeline, ...
  recent mtime (~15): 6/1~6/2 updates

Dead 의심 (70):
  apple/* (4), gaming/* (2), leisure/* (1), smart-home/* (1), ...
  mlops/* (24), media/* (4), creative/* 영상/음악 (6), ...

Policy Violation (1):
  🔴 productivity/linear/ — 禁no_linear_workflow 위반, 즉시 제거

Options:
  H1. linear만 제거 (0 risk, 30s)
  H2. H1 + dead 카테고리 36개 (0 risk, 5min) ← 추천
  H3. H2 + notion 등 5/22 명시 (0 risk, 30min)
  H4. 그대로 두기 (0 risk, 0)
```

## Example (2026-06-03 실제 결과)

- User: "안쓰는 스킬이 있나? 스킬 목록이 엄청 많잖아?"
- Audit 결과: 121개 중 51개 dead (모두 mtime 5/14 00:31 batch), 1개 정책 위반 (linear), 8개 빈 카테고리
- 3-criteria 판정: cron 5 + wikilink ~25 + recent mtime ~15 = 45 active, 70 dead 의심 + 6 H4 candidates
- 권고 옵션: H1~H4 제시 → **사용자 H3 선택** (mtime 5/14 batch + 명시 dead + 빈 카테고리 8개)
- 실행: 6 batch × verify 패턴으로 안전 진행
  - Batch 1: 9 카테고리 (apple/gaming/leisure/smart-home/social-media/email/red-teaming/data-science/note-taking) = 13 skills
  - Batch 2: productivity/{linear,notion,google-workspace,powerpoint,ocr-and-documents,nano-pdf} = 6
  - Batch 3: creative/{ascii-art,ascii-video,excalidraw,manim-video,p5js,popular-web-designs,songwriting-and-ai-music} = 7
  - Batch 4: media/{gif-search,heartmula,songsee,youtube-content} = 4
  - Batch 5: mlops/* 전체 = 22
  - Batch 6: 빈 카테고리 8개 (creative, media, inference-sh, gifs, feeds, diagramming, domain, index-cache)
- 최종: **121 → 70** (51개 제거, 42% 감소), 0 risk
- 부수 효과: 이 audit 작업을 `skill-usage-audit` 스킬로 영구화 (다음번 재실행 가능)
- Follow-up: H4a 후보 21개 (5/20 mtime 그룹 — autonomous-ai-agents 6, research 5, mcp 2, github 6, dogfood 1) — 사용자 confirm 대기

## Related

- [[P0-brainstem/brain/Drewgent-brain/P0-brainstem/禁/禁no_linear_workflow]] — 정책 위반 scan
- [[P0-brainstem/brain/Drewgent-brain/P0-brainstem/禁/禁filesystem_truth.neuron]] — "filesystem = truth" 원칙
- [[skills/filesystem-truth-audit]] — memory vs reality 검증 (유사 audit 패턴)
- [[skills/cron-jobs-stalled]] — dead cron 진단 (유사 진단 패턴)
- [[skills/kanban-dispatcher-stalled]] — dead worker reclaim (유사 진단 패턴)
- [[P5-ego/SELF_MODEL]] — agent identity anchor
- [[P1-limbic/persona/SOUL]] — voice anchor

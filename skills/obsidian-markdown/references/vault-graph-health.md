# Vault Graph Health — Obsidian Wikilink Connectivity

Techniques to ensure Obsidian Graph View shows meaningful connections in an AI agent vault (Drewgent P0-P6 architecture).

## 1. `.neuron` Extension Registration

Obsidian ignores `.neuron` files by default. `[[禁task_qa_gate.neuron]]` links show as broken.

**Fix**: `~/.drewgent/.obsidian/app.json`
```json
{
  "extensionOverrides": [".neuron"]
}
```

No file rename needed. Obsidian now treats `.neuron` as markdown.

## 2. Frontmatter `links:` → Body Wikilinks

Obsidian Graph View prioritizes **body wikilinks** (`[[Target]]` in markdown body) over frontmatter `links:` entries. Frontmatter links are parsed but don't appear in backlinks count.

**Fix**: Script to convert frontmatter links to body links:
1. Parse YAML frontmatter for `links:` list
2. Extract `[[target]]` or plain target names
3. Append to end of body as `## Links\n- [[target]]`
4. Skip targets already present in body

## 3. Bidirectional Crosslinks

For graph connectivity, each node needs both:
- **Outbound links** (→ what this file references)
- **Inbound links** (← what references this file)

Most effective crosslinks:
- P0 neurons ↔ P6 incident docs (policy ↔ experience)
- P2 memory ↔ P0 neurons (knowledge ↔ rules)
- P3 skills ↔ P4-cortex rules (tools ↔ growth)

## 4. Orphan Detection

```bash
grep -rln '\[\[TargetSlug\]\]' .drewgent/  # find inbound links
```

Or use GBrain's `find_orphans` MCP tool.

## 5. Gap Analysis

`drewgent_graph_gap_analysis.sh` checks:
- Dangling wikilinks (`[[X]]` → file not found)
- Missing links (vault files not referenced from memory)

## 6. Cron Output Pollution

Cron job 출력 파일이 vault에 저장되면 Obsidian 그래프뷰를 오염시킬 수 있다. 특히 한 cron job이 **매분 실행**되며 출력 파일마다 **SKILL.md frontmatter**를 포함하는 경우, 두 wikilink가 수천 개 파일에서 반복돼 **거대한 인공 클러스터**를 생성한다.

### 증상
- 3~5개 노드에 수천 개의 파일이 연결된 **거대한 스타 패턴**
- 실제 vault 콘텐츠 파일 수보다 wikilink 카운트가 10배 이상 높음

### 진단
```bash
# 가장 많이 링크된 페이지 TOP 15 확인
grep -roh '\[\[[^]]*\]\]' ~/.drewgent --include='*.md' \
  --exclude-dir=cron 2>/dev/null | sed 's/\[\[//;s/\]\]//' | \
  sort | uniq -c | sort -rn | head -15

# cron output 디렉토리 크기 확인
du -sh ~/.drewgent/cron/output/*/ | sort -rh | head -10
```

### 해결

1. **Obsidian exclusion**: `.obsidian/app.json`에 `userIgnoreFilters` 추가
   ```json
   {
     "userIgnoreFilters": ["cron/output"]
   }
   ```
   그래프뷰에서 즉시 제거된다. 기존 파일은 디스크에 보존.

2. **Cron 출력 정리** (선택):
   ```bash
   mv ~/.drewgent/cron/output/<job_id> ~/.drewgent/.trash/
   ```

3. **재발 방지**: cron job 출력 템플릿에서 SKILL.md frontmatter를 생략하거나, `[SILENT]`를 사용해 no-op tick을 출력하지 않도록 개선.

## 7. Naming Collision Detection

vault에 중복 파일명이 있는지 주기적으로 확인한다:

```bash
find ~/.drewgent -name '*.md' -not -path '*/cron/*' -not -path '*/.trash/*' \
  -not -path '*/_agent/*' -not -path '*/archive/*' -not -path '*/node_modules/*' \
  2>/dev/null | while read f; do basename "$f"; done | \
  sort | uniq -c | sort -rn | awk '$1 > 1 {print $1, $2}'
```

충돌이 발견되면:
- **P-layer 핵심 파일**은 반드시 full canonical path로 링크 (`[[@identity/persona/SOUL]]` — short name `[[SOUL]]` 금지)
- **중복이 불가피한 파일** (SKILL.md, index.md)은 경로를 포함한 wikilink만 사용

## 8. Graph Health Checklist

- [ ] `cron/output`이 Obsidian exclusion에 등록됨
- [ ] `.neuron` 확장자가 extensionOverrides에 등록됨
- [ ] P-layer core 파일들이 full canonical path로 링크됨 (short name 없음)
- [ ] SEO 수집 파일이 허브 2~3개에만 의존하지 않고 topic 기반 cross-link를 가짐
- [ ] inbound/outbound 비율이 1:3 이상 (너무 많은 inbound만 있으면 star 패턴 의심)

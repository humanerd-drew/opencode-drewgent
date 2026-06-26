# Vault Graph Health Check (2026-06-10)

## Obsidian 호환성 문제와 해결

### 문제 1: `.neuron` 확장자 미인식

13개 P0 rule 파일(`禁xxx.neuron`)이 Obsidian에서 markdown으로 인식 안 됨.
`[[禁task_qa_gate.neuron]]` 링크가 Obsidian Graph View에서 broken으로 표시.

**Fix**: `.obsidian/app.json`에 extensionOverrides 추가:
```json
{
  "extensionOverrides": [".neuron"]
}
```
파일 rename 불필요. Obsidian 재시작 시 적용.

### 문제 2: frontmatter `links:` → body wikilink

208개 core 파일의 frontmatter에 `links: ["[[target]]"]` 형식으로 링크가 있었으나,
Obsidian Graph View가 frontmatter 링크를 본문 링크보다 약하게 인식.
→ 84% 파일이 0 backlink (graph에서 고아로 보임).

**Fix**: `write_file`로 각 파일 본문 하단에 `## Links` 섹션 추가.
462개 링크가 frontmatter → body로 이동. 208개 파일 업데이트.

**스크립트 패턴**:
```python
import yaml, re
WIKILINK_PATTERN = re.compile(r'\[\[([^\]]+?)(?:\|[^\]]+)?\]\]')

with open(fp) as f:
    content = f.read()
# Parse frontmatter
if content.startswith('---'):
    _, fm_text, body = content.split('---', 2)
    fm = yaml.safe_load(fm_text)
    for link in fm.get('links', []):
        m = WIKILINK_PATTERN.match(link.strip())
        if m and m.group(1) not in body:
            body += f'\n- [[{m.group(1)}]]'
    # Write back
```

**Pitfall**: `links:`에 일반 텍스트(target만, `[[...]]` 없이)도 있을 수 있음.
정규식으로 `[[...]]` 감싸진 것만 추출할 것.

### 문제 3: Incident ↔ Neuron bidirectional 부재

7개 incident doc이 P0 neuron을 전혀 참조하지 않음. 13개 neuron도 incident doc 참조 없음.
→ Obsidian Local Graph에서 incident와 neuron이 분리된 cluster.

**Fix**: 각 incident doc에 `## Related Neurons` 섹션, 각 neuron에 `## Related Incidents` 섹션 추가.
15개 파일 업데이트. 결과: incident당 2-4 inbound, neuron당 1-6 inbound.

**매핑 기준**:
- launchd/cron incident → `禁incident_aware`, `禁filesystem_truth`
- double-fire incident → `禁filesystem_truth`, `禁task_qa_gate`, `禁console_log`
- publish leak incident → `禁auto_validate`, `禁subagent_verify`, `禁blind_write`
- ACP spinner → `禁console_log`, `禁blind_write`

### 문제 4: Brain signal orphan 노드

`monitor/brain_signals_*.md` 5,123개 파일이 Obsidian graph에 고아 노드로 표시.
inbound 0, outbound만 있음 (rules.md, SELF_MODEL.md로).

**Fix**: 생성 중단 (`brain_monitor.py:_deliver()`에서 `_deliver_fallback()` 호출 제거)
+ 기존 파일 일괄 삭제. 정보 손실 0 (gateway.log + brain_signal_log.jsonl에 동일 데이터).

```python
# 생성 중단 코드 패턴
def _deliver(self, entries, ...):
    try:
        # DeliveryRouter → Discord 등
        ...
    except Exception as e:
        # BEFORE: self._deliver_fallback(content) → 5K개 파일
        # AFTER: logger.warning("DeliveryRouter unavailable: %s", e)
        logger.warning("DeliveryRouter unavailable (session %s): %s", self.session_id, e)
```

### 문제 5: GBrain 검색 vs Obsidian Graph

GBrain MCP server (89 tools)가 vault의 keyword+vector 검색 제공.
Obsidian Graph View는 wikilink 기반 시각화. 둘은 보완 관계:
- GBrain: "gateway cron stall" 의미 검색 → 관련 문서 0.9+ score로 반환
- Obsidian: `[[禁filesystem_truth.neuron]]` 그래프 탐색 → incident/neuron/memory 시각적 연결

## 검증 명령어

```bash
# dangling wikilink 검사 (MEMORY.md 기준)
bash ~/.hermes/scripts/drewgent_graph_gap_analysis.sh

# 특정 파일의 inbound link 확인 (GBrain)
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"get_backlinks","arguments":{"slug":"p2-hippocampus/memories/memory"}}}' | gbrain serve 2>/dev/null | python3 -m json.tool

# Obsidian Graph View = vault를 Obsidian으로 열어서 확인
open /Users/drew/.drewgent
```

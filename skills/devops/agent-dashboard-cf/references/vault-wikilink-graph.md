# Vault Wikilink Graph (Dashboard)

Pusher가 vault의 `.md` 파일을 스캔해서 `[[wikilinks]]`를 추출, vis-network로 렌더링.

## 수집 범위

| 레이어 | 폴더 | 제한 |
|--------|------|------|
| P0-Brainstem | `P0-brainstem/` | 60 files max |
| P1-Limbic | `P1-limbic/` | 60 files max |
| P3-Sensors | `P3-sensors/` | 60 files max |
| P4-Cortex | `P4-cortex/` | 60 files max |
| P5-Ego | `P5-ego/` | 60 files max |
| P6-Prefrontal | `P6-prefrontal/` | 60 files max |
| Skills | `skills/` | SKILL.md만 (142개) |
| Root | `.drewgent/` | 최상위 .md 파일 |

**제외:** P2-hippocampus (11GB, DB/벡터 파일 위주)

## 동작

1. `glob.glob("**/*.md", recursive=True)`로 파일 수집
2. 각 파일의 첫 30KB 읽기 (성능)
3. 정규식 `\[\[([^\]|]+)(?:\|[^\]]+)?\]\]`로 wikilink 추출
4. Frontmatter `title:` 필드 → 노드 라벨 (없으면 filename → Title Case)
5. 파일당 최대 20 link, 총 300 nodes cap
6. 100KB 이상 파일 스킵

## 엣지 해석

Wikilink를 노드 ID로 변환:
1. lookup dict 생성: label, filename stem, short path
2. 직접 매칭 실패 시 fuzzy fallback (contains)
3. 중복 엣지 제거 (source/target 정렬 후 key 생성)
4. 연결되지 않은 노드 제외 (connected set)

## 렌더링 (vis-network)

```javascript
new vis.Network(container, { nodes, edges }, {
  physics: {
    solver: 'forceAtlas2Based',
    forceAtlas2Based: {
      gravitationalConstant: -30,
      springLength: 100,
      springConstant: 0.02,
      damping: 0.4,
    },
    stabilization: { iterations: 80 },
  },
  interaction: { hover: true, tooltipDelay: 200, navigationButtons: true },
});
```

## 색상 체계

| Layer | Hex | 의미 |
|-------|-----|------|
| root | `#8b949e` | 최상위 문서 |
| P0 | `#f85149` (red) | 절대 규칙 |
| P1 | `#d29922` (yellow) | 정체성 |
| P3 | `#58a6ff` (blue) | 센서 |
| P4 | `#3fb950` (green) | 성장 |
| P5 | `#bc8cff` (purple) | 자아 |
| P6 | `#d4760e` (orange) | 전전두엽 |
| skill | `#79c0ff` (light blue) | 스킬 |

## 한계

- Static snapshot: pusher가 5분마다 갱신
- 첫 30KB만 읽음 → 문서 후반부 wikilink 누락 가능
- Fuzzy link matching이 과도하게 연결할 수 있음
- 300 nodes cap → 대규모 vault에서는 서브셋만 표시

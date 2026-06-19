# Agent Dashboard — Design Evolution & Patterns

## 설계 진화 (2026-06-15 세션)

### v1: 16:9 3-Column Grid
- **트리거**: 유저 "세로로 길게하지 말고 16:9 레이아웃"
- **구조**: Col1(System/Services/Vault/Git/Brew) | Col2(Kanban/Network/Docker/Thermal) | Col3(Cron/Sessions)
- **문제**: 정보 위계 없음, 15개 섹션이 동등 비중, "정보 전달에 도움 안 됨"

### v2: Health Bar + 3-Column + Footer Grid
- **추가**: 상단 Health Bar (sticky, green/yellow/red), Recent Errors, Gateway Status
- **변경**: 상태바 28px→20px 축소 (유저 "공간 불필요")
- **문제**: 여전히 3열이 논리적이지 않음 (col1에 unrelated items)

### v3: Card-based Accordion
- **트리거**: 유저 "카드 형식으로 다시 구성하고 아코디언이나 모달"
- **구조**: 4열 카드 그리드, 클릭→아코디언, 한 번에 하나만 열림
- **핵심**: 점진적 공개 (요약→상세)

### v4 (최종): Activity Timeline + Gentle Refresh
- **트리거**: 유저 "인사이트가 없다" + "더 역동적이면 좋겠어"
- **변경**: Sessions 카드 제거 → Activity Timeline (2열 너비)
- **변경**: 화면 전체 리프레시 대신 90초마다 조용히 값 업데이트 + pulse
- **핵심**: "살아있는" 느낌 — 이벤트 스트림, timeAgo, Live pulsing dot

## Activity Timeline 컴포넌트

### 데이터 수집 (`collect_timeline()`)
```python
# pusher/collect_timeline(cron_data, sessions, recent_errors)
# 1. Cron jobs: last_run_at → timestamp + name + status
# 2. Errors: time + level + message
# 3. 정렬: timestamp descending, 중복 제거 (msg[:40]), 최대 12개
```

### 렌더링 (CSS)
```css
.tl-event {
  display: flex; gap: 10px; padding: 6px 14px;
  border-left: 2px solid var(--border);
  margin-left: 20px; position: relative;
}
.tl-event::before {  /* circle dot */
  content: ''; position: absolute; left: -5px; top: 10px;
  width: 8px; height: 8px; border-radius: 50%;
  background: var(--surface2);
  border: 2px solid var(--border);
}
.tl-cron-ok::before { border-color: var(--green); background: var(--green); }
.tl-cron-err::before { border-color: var(--red); background: var(--red); }
.tl-new { animation: slideIn 0.4s ease-out; }
```

### 실시간 업데이트 (`updateTimeline()`)
```javascript
// 새 이벤트를 위에 prepend, slideIn 애니메이션
// existing[0].dataset.ts 와 비교해서 중복 방지
// Header의 activityAgo 업데이트 (timeAgo(latest.time) + ' · Live')
```

## Gentle Refresh Pattern

```javascript
var _openCard = null;  // 아코디언 상태 유지
var _prevValues = {};  // 이전 값 저장 (변화 감지)

// 최초 1회: renderCards(data) — 전체 구조 생성
// 이후:   updateValues(data) — 값만 업데이트

function updateValues(d) {
  cards.forEach(function(c) {
    var v = document.getElementById('val-' + c.id);
    if (!v) return;
    if (_prevValues[c.id] !== c.value) {
      v.innerHTML = c.value;
      v.classList.remove('changed');
      void v.offsetWidth;  // force reflow
      v.classList.add('changed');  // → CSS highlight animation
      _prevValues[c.id] = c.value;
    }
    // 열린 카드 본문은 업데이트 안 함 (방해 금지)
    if (b && !el.classList.contains('expanded')) { b.innerHTML = c.body; }
  });
}
```

## 유저 피드백 로그

| 피드백 | 해결 |
|--------|------|
| "글자가 너무 작다" | body 10→13px, value 18→28→22px |
| "정보 전달에 도움 안 됨" | 3열→카드 아코디언 |
| "인사이트가 없다" | Activity Timeline 추가 |
| "더 역동적이면 좋겠어" | Live dot, pulse, timeAgo |
| "인터벌 늘리는건 해결책이 아님" | 화면 리프레시 NO, 조용한 값 업데이트 |
| "카드 형식 + 아코디언" | Progressive disclosure |

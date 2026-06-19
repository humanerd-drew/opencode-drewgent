# Dashboard Refresh Strategy

## History

| Version | Strategy | Problem | Fix |
|---------|----------|---------|-----|
| v1 | 30s auto-refresh, full re-render | 읽는 중 화면 blink, 아코디언 리셋 | — |
| v2 | 120s auto-refresh, full re-render | 인터벌만 늘림, 근본 문제 미해결 | 인터벌 늘리는 건 해결책이 아님 |
| v3 | Manual only (Refresh button) | 사용자가 직접 눌러야 함 | 유저 OK |
| v4 | Gentle 90s background update | 값만 변경, 구조 유지 | **최종** |

## v4 Strategy (Current)

### Flow
```
Page Load → loadDashboard()
              ├─ fetch /api/status
              ├─ renderCards()        [최초 1회만]
              ├─ renderGraph()        [최초 1회만, _graphNetwork 플래그]
              ├─ renderHealth()
              └─ renderAlerts()
              
90s later → setTimeout(loadDashboard, 90000)
              ├─ fetch /api/status
              ├─ updateValues()       [DOM 값만 변경]
              │    └─ val-{id}.innerHTML = newValue
              │    └─ sub-{id}.innerHTML = newSub
              │    └─ tag-{id}.innerHTML = newTag
              │    └─ body-{id}.innerHTML = newBody (닫힌 카드만)
              └─ updateTimeline()     [새 이벤트만 prepend]
```

### Why 90 seconds?
- Short enough to feel "live" (< 2 min)
- Long enough to not be distracting (> 30s vs 60s vs 90s: 90s felt right in practice)
- Aligns with cron job push interval (5 min) — dashboard may update between pushes, but value changes are minimal

### Value Animation
```javascript
// Before updating, compare with previous value
if (_prevValues[cardId] !== newValue) {
    el.innerHTML = newValue;
    el.classList.remove('changed');
    void el.offsetWidth;  // force reflow to restart CSS animation
    el.classList.add('changed');
    _prevValues[cardId] = newValue;
}
```

### Accordion Preservation
- Track `_open` variable (open card id)
- On update: skip body update for `.expanded` cards
- Only one card allowed open at a time (singleton pattern)

### Graph Preservation
- `_graphNetwork` flag prevents re-initializing vis.Network
- vis-network is expensive to rebuild; only build once

## Trade-offs

| Decision | Why | Risk |
|----------|-----|------|
| Manual refresh not default | User said auto-refresh was needed, just not disruptive | Some users prefer fully manual |
| 90s vs 30s | Less distracting, same effective freshness | Slow to show new errors |
| Skip graph re-render | vis-network rebuild is slow (~500ms) and visibly jarring | Graph won't reflect new wiki links until manual refresh |
| Update closed cards only | User might miss detail changes while card is open | They close it eventually |

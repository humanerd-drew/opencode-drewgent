# 2026-06-12 Session Patches

## sessionStorage Auto-Submit Pattern

결제 후 자동 실행 + 리프레시 시 재호출 방지를 위한 패턴.

```javascript
// handleSubmit() - 결제 이동 전
sessionStorage.setItem('__PENDING_COMPREHENSIVE__', 'true');
window.location.hash = '#/payment?type=luck';

// init() - 플래그 확인
const pendingReport = sessionStorage.getItem('__PENDING_COMPREHENSIVE__');
const isPending = pendingReport === 'true' && isPaid;
if (isPending) sessionStorage.removeItem('__PENDING_COMPREHENSIVE__');
this.state = { isSimulatingAnalysis: isPending, ... };

// mounted() - 조건부 auto-submit
if (this.state.isPaid && this.state.isSimulatingAnalysis && !this.state.reportData && !this._autoSubmitted) {
    this._autoSubmitted = true;
    this.startLoadingSimulation();
    this.autoSubmitFromSavedForm();
    return;
}
```

## z-override: location-dropdown

```css
/* z-override.css — form dropdown이 sidebar 위로 */
.location-dropdown,
.birth-form .location-dropdown { z-index: 3001 !important; }
```

기존 CSS (`form.css:265`)는 `z-index: 200` — sidebar (z-index: 3000) 아래에 가려짐.

## analyze() Engine Integration for Comprehensive Report

```typescript
import { analyze } from '../analysis/engine';

const analysisReport = analyze({
    pillars: saju.data.pillars,
    dayMaster: saju.data.analysis?.dayMaster,
    gender, birthYear, currentYear, currentMonth,
    daewoonCycles: saju.data.daewoon?.cycles,
    pdcTenGods: saju.data.tenGods,
    pdcDaewoonDirection: saju.data.daewoon?.direction,
});

// structured source data
const sourceLines = [
    '[사주 기본 정보]', ..., '',
    '[현재 대운 (10년 단위 큰 흐름)]',
    `간지: ${dw.ganji} (${dw.startAge}세 시작)`,
    `대운 결합 오행: ...`,
    '', etc.
];
```

Before: `JSON.stringify(saju.data)` — raw JSON dump.
After: labeled, pre-computed structured narrative.

## Prompt ONTOLOGY_CTX Removed

`getOntologyContext('analyze')` returns Postziping personality/relationship ontology (~2.2KB). For comprehensive (fortune/luck) reports this is irrelevant — removed from system prompt assembly. Source Data provides all needed context.

## Dating Report CTA Buttons z-index

`ReportDatingView.js` CTA buttons (`#generateDatingReportBtn`, `.select-chart-btn`, `#printReportBtn`, `#resetDatingBtn`) reported invisible on desktop after deploy. Root cause unconfirmed (DOM present, 200 OK, no console errors).

Applied to z-override.css:
```css
.chart-picker-sheet { z-index: 3001 !important; }
.select-chart-btn, #generateDatingReportBtn, #resetDatingBtn, #printReportBtn { position: relative; z-index: 1; }
```

**Lesson**: CTA buttons in DOM but invisible = z-index stacking context or overflow clipping. `position: relative; z-index: 1` as first diagnostic step. (2026-06-12, unresolved)

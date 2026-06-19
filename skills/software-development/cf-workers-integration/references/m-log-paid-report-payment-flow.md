# M-LOG Paid Report Payment Flow

## Architecture

All paid reports (desire, luck, dating compatibility, dating divorce) follow the same flow:

```
입력 → 분석하기 → (1) API 호출 → (2) 결과 localStorage 저장 → (3) 결제 페이지
                                        ↓ (결제 완료 후 복귀)
                  (4) init() → __RESTORE_REPORT__ 복원 → (5) 로더 2.5초 → (6) 리포트 표시
```

## Key Principle: API Call First, Payment Second

The report generation API is called **before** the user pays. The pre-generated result is saved to `localStorage`. After payment, the user returns to the report page, where:

1. `init()` detects `__RESTORE_REPORT__` + `__RESTORE_REPORT_TYPE__`
2. Restores `reportData` from saved data
3. Checks `__PURCHASED_REPORTS__` → if now paid, sets `isSimulatingAnalysis: true`
4. `mounted()` detects `isSimulatingAnalysis` → runs 2.5s loading animation
5. After animation → `isSimulatingAnalysis = false` → template shows report

## Implementation Pattern

### State
```js
isPaidC: !!purchased.dating_compatibility,
isPaidD: !!purchased.dating_divorce,
isSimulatingAnalysis: false,
```

### init() — Restore after payment
```js
const restoreData = localStorage.getItem('__RESTORE_REPORT__');
if (restoreData && type === 'dating') {
    const parsed = JSON.parse(restoreData);
    if (parsed && parsed.report) {
        this.state.reportData = parsed.report;
        const purchased = JSON.parse(localStorage.getItem('__PURCHASED_REPORTS__') || '{}');
        if (purchased.dating_compatibility || purchased.dating_divorce) {
            this.state.isSimulatingAnalysis = true;
        }
    }
}
```

### handleAnalyze — No payment early-return
```js
// ❌ Don't check payment before API call
// ✅ Always call API first
const res = await DatingAPI.fetchDatingReport(activeTab, payload);
if (res.success && res.data) {
    // Save result
    this.setState({ reportData: res.data, loading: false });
    // Save to history
    await SajuAPI.saveHistory({...});
    
    // If not paid → save restore data → redirect to payment
    const needsPayment = (activeTab === 'compatibility' && !isPaidC) ||
                         (activeTab === 'divorce' && !isPaidD);
    if (needsPayment) {
        localStorage.setItem('__RESTORE_REPORT__', JSON.stringify(savedReport));
        localStorage.setItem('__RESTORE_REPORT_TYPE__', 'dating');
        window.location.hash = '#/payment?type=dating_divorce';
        return;
    }
}
```

### mounted() — Loading simulation (1-time guard)
```js
if (this.state.isSimulatingAnalysis && !this._simStarted) {
    this._simStarted = true;
    this.startLoadingSimulation();
    setTimeout(() => {
        this.stopLoadingSimulation();
        this.setState({ isSimulatingAnalysis: false });
    }, 2500);
    return;
}
```

### Template — Show loading for both `loading` and `isSimulatingAnalysis`
```js
if (isSimulatingAnalysis || loading) { return loadingAnimationHtml; }
if (reportData) { return reportHtml; }
return formHtml;
```

## Form Data Preservation

When switching tabs via CTA from a report result, the form values must be saved **before** the API call (in `handleAnalyze`), not in `syncInputsFromDOM()` (which can't find DOM elements when the report result is showing).

```js
// In handleAnalyze — save BEFORE API call
this.state.personA = personA;  // from DOM
this.state.personB = personB;
```

Also restore from history formData:
```js
if (formData.personA) this.state.personA = { ...this.state.personA, ...formData.personA };
if (formData.personB) this.state.personB = { ...this.state.personB, ...formData.personB };
```

## Caveats

- The `?t=` query param workaround (see SKILL.md SPA Routing section) is essential for payment return flow because the user returns to the same hash route.
- Dating report CTA buttons use `class="dating-cta-btn"` and `data-tab="divorce"` — handled by `handleCtaTabSwitch`.
- Always verify CSS `.section-header` `justify-content` doesn't override inline styles (add `justify-content: flex-start` inline when needed).

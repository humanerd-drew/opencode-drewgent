---
name: m-log-payment
description: M-LOG 프로젝트 결제 모듈 — PortOne V2 (KG이니시스) 연동, 명식 단위 구매 모델, D1 결제 기록 저장, mobile redirect 대응
---

# M-LOG Payment Module

## Trigger Conditions
- User asks about payment, 결제, PortOne, KG이니시스, purchase, buying reports
- Working on PaymentView.js, payment controller, purchases table
- Any task involving paid report features in M-LOG

## Architecture Invariants

### 1. Payment is PER-MYEONGSIK, not per-account
```
Old (wrong):  purchased[reportType] = true
New (correct): purchased[reportType_fingerprint] = { txId, ... }
```
- `fingerprint` = `{year}_{month}_{day}_{hour}_{min}_{gender}_{isLunar}_{loc}_{name}` (whitespace stripped)
- Dating uses both Person A + B fingerprints: `{type}_{fpA}_vs_{fpB}`
- Same myeongsik data → same fingerprint → same purchase → no re-payment needed
- Different myeongsik data → different fingerprint → separate purchase

### 2. Dual Storage: localStorage + D1
- **localStorage** (`__PURCHASED_REPORTS__`): 빠른 offline 체크, fingerprint key
- **D1** (`purchases` table): 영구 저장, 서버 간 동기화, 교차 디바이스
- Service-side verify: `POST /api/payment/verify` after PortOne success
- Fallback: `localStorage` only when server verify fails

### 3. Fingerprint-Based Auth Across Controllers

The `purchases` table is not only for payment verification — it's also used by **report generation controllers** to authenticate anonymous purchasers.

**Pattern** (implemented in `comprehensive-report.ts` 2026-06-12):
```
Request body: { person, fingerprint, anonymousId }
Session check → nil? → dbQueries.checkPurchase(DB, null, anonymousId, type, fingerprint)
```
- `report_type` = `'comprehensive'` or `'luck'` (buyers of either type can access)
- `user_id = null` (anonymous), matched via `anonymous_id` + `fingerprint`
- On success: report is generated, history saved with `userId = null`

See `m-log-development-patterns` → `Auth` section for full details.

### 4. Required Payment Fields for KG이니시스
```js
customer: {
    email: Store.state.user?.email || '',        // 필수
    fullName: Store.state.user?.name || '',       // 권장
    phoneNumber: payerPhone || undefined,          // 필수 (KG이니시스 결제 인증)
}
redirectUrl: window.location.href,                // 모바일 redirect 대응
```

### Multi-Channel Payment Methods
When multiple PG channels are configured (e.g., KG이니시스 + 카카오페이 + 한국결제네트웍스):

```js
const PORTONE_CONFIG = {
    storeId: 'store-...',
    channelKeys: {
        naverpay: 'channel-key-...',   // KG이니시스 (네이버페이)
        kakaopay: 'channel-key-...',   // 카카오페이 (카카오페이)
        card: 'channel-key-...',       // 한국결제네트웍스 (신용카드)
    },
};

// Select channel + payMethod by method:
const method = this.state.selectedMethod; // 'naverpay' | 'kakaopay' | 'card'
const requestBody = {
    storeId: PORTONE_CONFIG.storeId,
    channelKey: PORTONE_CONFIG.channelKeys[method],  // ← 동적 선택
    payMethod: method === 'card' ? 'CARD' : 'EASY_PAY',
    easyPay: method === 'naverpay' ? { easyPayProvider: 'NAVERPAY' }
           : method === 'kakaopay' ? { easyPayProvider: 'KAKAOPAY' }
           : undefined,
};
```

### Post-Payment Redirect: sessionStorage Flag Pattern

After payment completes and redirects to the report page, the report view must auto-submit to generate the LLM report — but **only on the first load after payment**, not on page refresh.

**Solution**: `sessionStorage` flag (not `localStorage` — that would survive refresh and cause infinite calls):

```javascript
// PaymentView.onPaymentSuccess() — 결제 완료 후 리포트 페이지로 이동
window.location.hash = `#/report-${reportHash}`;
// View가 mount되면 init()에서 sessionStorage 확인
```

```javascript
// ReportComprehensiveView.js
init() {
    const pendingReport = sessionStorage.getItem('__PENDING_COMPREHENSIVE__');
    const isPending = pendingReport === 'true' && isPaid;
    if (isPending) sessionStorage.removeItem('__PENDING_COMPREHENSIVE__');
    this.state = { isSimulatingAnalysis: isPending, ... };
}
mounted() {
    if (this.state.isPaid && this.state.isSimulatingAnalysis && !this.state.reportData && !this._autoSubmitted) {
        this._autoSubmitted = true;
        this.autoSubmitFromSavedForm();
    }
}

// handleSubmit() — 결제 페이지로 이동하기 전 플래그 설정
if (!isPaid) {
    sessionStorage.setItem('__PENDING_COMPREHENSIVE__', 'true');
    window.location.hash = '#/payment?type=luck';
}
```

**Why sessionStorage and not localStorage**: `localStorage` survives tab close/reopen. If user refreshes the report page, the flag would still be set → auto-submit fires again → new LLM call. `sessionStorage` is cleared when the tab session ends (page refresh counts as same session? NO — actually sessionStorage survives F5 refresh. But the flag is consumed in `init()` on the first mount after payment. The key insight: **sessionStorage is cleared when the TAB is closed**, while `localStorage` persists across tabs and browser restarts. For this pattern, the flag is set → consumed on next mount → removed. If user refreshes AFTER the flag was consumed, no re-trigger.)

**Pitfall (2026-06-12)**: Original code had `_autoSubmitted` as a Component instance variable. Router destroys and recreates the view on hash change → new instance → `_autoSubmitted = undefined` → auto-submit fires again → infinite LLM calls costing $1-2/hour. The `sessionStorage` + `isSimulatingAnalysis: isPending` pattern solves this by gating the auto-submit on a session-bounded flag, not an instance variable.

## Implementation Patterns

### QA Standard (M-LOG-specific)
- "사소한 이슈도 있으면 안되겠지": 고객이 발견할 수 있는 UX/로직 이슈는 절대 남겨두지 말 것
- 리포트 뷰의 결제 상태(isPaid, 구매완료 표시)는 form 값 변경 시에도 항상 정확해야 함
- 모바일/데스크톱 모두 검증 필수
- D1 마이그레이션, public/ 동기화 등 배포 전 단계 누락 없이 확인

## PortOne V2 SDK Integration
```js
// SDK loaded via index.html: <script src="https://cdn.portone.io/v2/browser-sdk.js">
const response = await window.PortOne.requestPayment({
    storeId: PORTONE_CONFIG.storeId,
    channelKey: PORTONE_CONFIG.channelKey,
    paymentId: `MLOG-${Date.now()}-${random}`,
    orderName: config.title,
    totalAmount: config.amount,        // 정수 (KRW)
    currency: 'KRW',
    customer: { email, fullName, phoneNumber },
    redirectUrl: window.location.href,  // 필수 (모바일)
    payMethod: 'CARD' | 'EASY_PAY',
    easyPay: method === 'naverpay' ? { easyPayProvider: 'NAVERPAY' } : undefined,
});
```

### Mobile Redirect Handling
- `redirectUrl: window.location.href` → PortOne SDK가 결제 완료 후 자동 복귀 처리
- SDK script가 URL의 query params (`?paymentId=...&txId=...`) 감지 → promise resolve
- PC: popup 방식 → promise return
- Mobile: redirect 방식 → 자동 복귀 + promise resolve

### D1 `purchases` Table Schema
```sql
CREATE TABLE purchases (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    anonymous_id TEXT,
    report_type TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    tx_id TEXT,
    payment_id TEXT,
    amount INTEGER NOT NULL DEFAULT 3800,
    status TEXT NOT NULL DEFAULT 'completed',
    purchased_at TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_purchases_user ON purchases(user_id, report_type, fingerprint);
CREATE INDEX idx_purchases_anon ON purchases(anonymous_id, report_type, fingerprint);
```

### Backend API Endpoints
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/payment/verify` | POST | PortOne 검증 + D1 저장 |
| `/api/payment/check` | GET | 구매 여부 확인 (type + fingerprint) |

### Frontend Files
- `frontend/app/js/views/PaymentView.js` — 결제 UI + PortOne SDK 호출
- `frontend/app/js/views/Report*.js` — 6개 리포트 뷰의 purchase check (fingerprint 기반)
- `frontend/app/js/views/ReportDatingView.js` — dating 전용 fingerprint + `_updatePurchaseState()`
- `packages/core/utils.js` — `getMyeongsikFingerprint()`, `getPurchaseKey()`, `getDatingPurchaseKey()`
- `public/app/index.html` — PortOne SDK <script> 태그

### 인증마크 표시
- **Footer**: desktop에서 표시 (`body.is-mobile .footer { display:none }`)
- **PaymentView 하단**: mobile에서도 보이도록 payment 페이지 내에 직접 삽입
- `<img src="https://image.inicis.com/mkt/certmark/inipay/inipay_43x43_color.png">`

## Pitfalls
- **PaymentView에서 `Store` import**: `/app/shared/core/store.js` 경로 사용 (상대경로 아님)
- **Fingerprint 공백**: `getMyeongsikFingerprint()`는 `.replace(/\s+/g, '')`로 공백 제거
- **DatingView isPaidC/D 동기화**: init 시점이 아닌 `update()` 오버라이드로 실시간 재계산
- **모바일 footer**: `display:none` → 인증마크는 PaymentView 내부에도 추가 필요
- **PORTONE_API_SECRET**: 반드시 `wrangler secret put`으로 등록 (vars에 평문 저장 금지)
- **D1 마이그레이션**: 로컬 DB 리셋 시 `.wrangler/state/v3/d1` 삭제 후 재적용
- **`__LAST_SAJU_DATA__` 백업**: 리포트 뷰에서 `removeItem('__SAJU_DATA__')` 전에 반드시 `__LAST_SAJU_DATA__`에 백업.
  DashboardView는 `__SAJU_DATA__` 우선, 없으면 `__LAST_SAJU_DATA__` fallback. 백업 없이 지우면 대시보드가 빈 화면 표시.
- **전화번호 저장 키**: `__PAYER_PHONE__` — 결제 페이지에서 한 번 입력 시 localStorage에 저장, 다음 결제 때 자동 복원
- **Public/ 동기화 누락**: `frontend/app/`에서 수정 후 `public/app/`에 복사 안 하면 배포에 미반영. `npm run deploy`의 `sync:local`은 packages/만 동기화하므로 app JS/HTML은 수동 복사 필수

## Deploy Checklist
```bash
# 1. public/ 파일 동기화 (수동)
cp -r frontend/app/ public/app/
cp packages/core/* public/app/shared/core/

# 2. D1 마이그레이션
npx wrangler d1 migrations apply m_log_db --remote

# 3. API Secret 등록
npx wrangler secret put PORTONE_API_SECRET

# 4. 배포
npm run deploy
```

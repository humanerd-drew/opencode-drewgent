---
name: korean-payment-gateway
description: >-
  Integrate Korean payment gateways (KG이니시스, KCP, tosspayments, etc.) via
  PortOne V2 SDK into vanilla JS SPAs. Covers SDK loading, requestPayment API,
  payMethod selection (CARD / EASY_PAY for NaverPay/KakaoPay), payment response
  handling, and backend verification pattern.
trigger:
  - user asks to add payment to a web app
  - user mentions PortOne / 아임포트 / KG이니시스 / KCP / PG사 결제
  - user provides a channelKey or storeId for a payment gateway
---

# Korean Payment Gateway Integration (PortOne V2 SDK)

## Overview

PortOne (포트원, formerly 아임포트) is the dominant payment gateway aggregator for Korean e-commerce. It unifies multiple PG providers (KG이니시스, NHN KCP, 토스페이먼츠, etc.) under a single JavaScript SDK.

This skill covers the **PortOne V2 SDK** (`@portone/browser-sdk`) integration into a vanilla JS SPA (no bundler).

## Architecture

```
┌─────────────┐     PortOne.requestPayment()     ┌──────────────┐
│  Browser SDK │ ──────────────────────────────▶  │ PortOne Cloud │
│  (CDN load)  │ ◀──────────────────────────────  │  (PG routing) │
└──────┬──────┘     Response { txId, paymentId }  └──────┬───────┘
       │                                                  │
       │  txId + paymentId                                 │ PortOne API verify
       ▼                                                  ▼
┌──────────────┐                                  ┌──────────────┐
│  Your Backend │ ◀─── payment/verify API ──────▶  │  Your Server  │
│  (CF Worker)  │                                  │  (portone     │
└──────────────┘                                  │   server-sdk) │
                                                  └──────────────┘
```

## Step 1: SDK Loading

### CDN (Vanilla JS — no bundler)

Add to `<head>` or before closing `</body>`:

```html
<script src="https://cdn.portone.io/v2/browser-sdk.js"></script>
```

This sets `window.PortOne` globally. The SDK auto-loads its core from the same CDN.

### NPM (Bundler — Vite, webpack, etc.)

```bash
npm i @portone/browser-sdk
```

```js
import PortOne from '@portone/browser-sdk/v2';
```

## Step 2: Configuration

Two values from [PortOne Admin Console](https://admin.portone.io) → **결제 연동 → 연동 정보**:

| Key          | Description | Format |
|-------------|-------------|--------|
| `storeId`    | 상점 아이디 (top-right corner) | `store-abc123` |
| `channelKey` | 채널 키 (per-channel) | `channel-key-xxxxx` |

```js
const PORTONE_CONFIG = {
  storeId: 'store-YOUR_STORE_ID',
  channelKey: 'channel-key-YOUR_CHANNEL_KEY',
};
```

## Step 3: Payment Request

### Basic Request (카드 결제)

```js
const response = await window.PortOne.requestPayment({
  storeId: PORTONE_CONFIG.storeId,
  channelKey: PORTONE_CONFIG.channelKey,
  paymentId: `ORDER-${Date.now()}-${Math.random().toString(36).slice(2,8)}`,
  orderName: '프리미엄 리포트',
  totalAmount: 3800,          // Integer (KRW = 1×)
  currency: 'KRW',
  payMethod: 'CARD',           // 신용/체크카드
});
```

### NaverPay (네이버페이 간편결제)

```js
const response = await window.PortOne.requestPayment({
  storeId: PORTONE_CONFIG.storeId,
  channelKey: PORTONE_CONFIG.channelKey,
  paymentId: `ORDER-${Date.now()}-${Math.random().toString(36).slice(2,8)}`,
  orderName: '프리미엄 리포트',
  totalAmount: 3800,
  currency: 'KRW',
  payMethod: 'EASY_PAY',
  easyPay: { easyPayProvider: 'NAVERPAY' },
});
```

### Supported `payMethod` Values

| Value | Description | PG Support |
|-------|-------------|-----------|
| `CARD` | 신용/체크카드 | All |
| `EASY_PAY` | 간편결제 (네이버페이/카카오페이 등) | All + `easyPay.easyPayProvider` |
| `VIRTUAL_ACCOUNT` | 가상계좌 | Most |
| `TRANSFER` | 계좌이체 | Most |
| `MOBILE` | 휴대폰 소액결제 | Most |
| `GIFT_CERTIFICATE` | 상품권/문화상품권 | Select PGs |

### Supported `EasyPayProvider` Values (for `payMethod: 'EASY_PAY'`)

| Provider | Enum Value | Supported by KG이니시스 |
|----------|-----------|------------------------|
| 네이버페이 | `NAVERPAY` | ✅ |
| 카카오페이 | `KAKAOPAY` | ✅ |
| 토스페이 | `TOSSPAY` | ✅ |
| 페이코 | `PAYCO` | ✅ |
| 삼성페이 | `SAMSUNGPAY` | ✅ |
| L페이 | `LPAY` | ✅ |
| SSG페이 | `SSGPAY` | ✅ |
| 애플페이 | `APPLEPAY` | ✅ |

## Step 4: Response Handling

```js
const response = await window.PortOne.requestPayment(requestBody);

// User closed the popup without completing
if (!response) {
  // → show "결제가 취소되었습니다." toast
  return;
}

// Payment failed
if (response.code) {
  console.error('[Payment] Error:', response);
  // → show `response.message` or `response.pgMessage` to user
  return;
}

// Payment success
console.log('Success:', { txId: response.txId, paymentId: response.paymentId });
// → send txId to backend for verification
// → mark purchase in local state
```

### Customer Info (Required by KG이니시스)

KG이니시스 requires the **customer email AND phone number** for payment processing. Without phone number the payment also fails.

Add a `customer` field to the request body:

```js
// Get user from Store (after importing `Store` from '/app/shared/core/store.js')
const user = Store.state.user || null;

const requestBody = {
  storeId: PORTONE_CONFIG.storeId,
  channelKey: PORTONE_CONFIG.channelKey,
  paymentId: `ORDER-${Date.now()}`,
  orderName: config.title,
  totalAmount: config.amount,
  currency: 'KRW',
  customer: {
    email: user?.email || '',          // ← required by KG이니시스
    fullName: user?.name || '',
    phoneNumber: this.state.payerPhone || undefined,  // ← ALSO required
  },
  // payMethod, etc.
};
```

**Phone number UX pattern (SPA with localStorage persistence):**

Since most apps don't collect phone numbers at registration, add an input field to the payment page:

```js
const PHONE_STORAGE_KEY = '__PAYER_PHONE__';

// In component init():
this.state = { payerPhone: localStorage.getItem(PHONE_STORAGE_KEY) || '' };

// Input event handler (strip non-digits, save on every keystroke):
handlePhoneInput(e) {
    const phone = e.target.value.replace(/[^0-9]/g, '');
    this.state.payerPhone = phone;
    localStorage.setItem(PHONE_STORAGE_KEY, phone);
}

// Template snippet (insert between payment-methods and payment-actions):
`<div class="payment-payer-info">
  <label>결제자 정보</label>
  <input type="tel" id="payerPhone"
         value="${this.state.payerPhone}"
         placeholder="휴대폰 번호 (01012345678)">
  <span>KG이니시스 결제 인증에 필요합니다. 한 번 입력 시 저장됩니다.</span>
</div>`
```

**Import pattern in vanilla JS SPA:**
```js
import { Store } from '/app/shared/core/store.js';
```

`Store.state.user` contains `{ email, name, id, ... }` when the user is logged in. For anonymous users, pass an empty string — the PG may still process it.

**Pitfalls:**
- `Store.state.user` may be `null` if the user is not logged in. Use optional chaining (`user?.email ?? ''`).
- NEVER expose the PortOne API Secret in the frontend. Store only `storeId` and `channelKey` in frontend config.
- The email is visible in the PortOne transaction log — ensure compliance with your privacy policy.

### Response `PaymentResponse` Shape

```ts
type PaymentResponse = {
  transactionType: 'PAYMENT';
  txId: string;           // PortOne transaction ID (for backend verification)
  paymentId: string;      // Your original order ID
  paymentToken?: string;  // For manual-confirm flows
  code?: string;          // Error code (present on failure)
  message?: string;       // Error message
  pgCode?: string;        // PG-specific error code
  pgMessage?: string;     // PG-specific error message
};
```

## Step 5: Backend Verification (Pattern)

The frontend should NOT trust the payment result alone. Send `txId` to your backend for verification:

```
POST /api/payment/verify
Body: { txId, paymentId }
```

Backend calls PortOne API:

```js
// Using @portone/server-sdk
// GET https://api.portone.io/payments/{paymentId}
// or with txId via webhook
```

**Key Points:**
- Use PortOne API Secret Key from admin console (server-side only!)
- Verify `totalAmount` matches your product price
- Never trust client-side `totalAmount` for billing (only use it for display)
- Implement idempotency on `paymentId` to prevent double-processing

## Pitfalls

### 1. StoreId is REQUIRED
`channelKey` alone is not enough. Both `storeId` and `channelKey` are required. StoreId is found at top-right of PortOne Admin Console → 결제 연동 → 연동 정보.

### 2. SDK Not Loaded Error
The CDN script is async. If you call `window.PortOne.requestPayment()` before the script loads, it errors. Solution: either load script early in `<head>` or check `window.PortOne` before calling.

### 3. Integer Amount
`totalAmount` must be an integer. For KRW use raw won (e.g., 3800 for ₩3,800). For USD, use cents (e.g., 600 for $6.00).

### 4. Mobile Redirect Required
On mobile, the payment often redirects to a PG page. Set `redirectUrl` to the page users should return to after payment.

### 5. Test vs Live Channel
PortOne admin has separate **테스트** and **실연동** channel sections. Test channels use the same SDK but don't charge real money. Verify you're using the right channel key.

## Verification

1. Open your payment page
2. Click 결제하기 — PortOne/이니시스 결제창 opens
3. Complete test payment (test card: usually `4111111111111111` for KG이니시스)
4. Check `response.txId` is a non-empty string
5. Verify `__PURCHASED_REPORTS__` localStorage entry has `txId` and `paymentId`
6. Check console for any errors

## 인증마크 (PG Certification Mark)

Korean PG providers require displaying a **certification mark** (인증마크) in the site footer to prove the payment system is legitimate.

### KG이니시스 인증마크 HTML

Place in the site footer (before copyright):

```html
<div class="footer-payment-mark" style="margin-top: 0.75rem; display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">
  <img src="https://image.inicis.com/mkt/certmark/inipay/inipay_43x43_color.png"
       alt="클릭하시면 이니시스 결제시스템의 유효성을 확인하실 수 있습니다."
       style="cursor: pointer; height: 43px; width: auto;"
       onclick="window.open('https://mark.inicis.com/mark/popup_v3.php?mid=YOUR_MID','mark','scrollbars=no,resizable=no,width=565,height=683');">
  <span style="font-size: 0.7rem; color: var(--text-secondary); opacity: 0.7;">KG이니시스 안전 결제</span>
</div>
```

**Pitfalls:**
- `cursor:hand` is IE-only legacy → use `cursor:pointer`
- `Onclick` → lowercase `onclick`
- `border='0'` on `<img>` → use CSS `border: none`
- `javascript:` prefix in onclick → remove it (just `window.open(...)`)
- Replace `YOUR_MID` with your actual KG이니시스 merchant ID (e.g., `MOI6180465`)
- On mobile, the footer is often hidden (`display: none`); consider a separate mobile placement

### Where to Place

| Page Type | Location | Notes |
|-----------|----------|-------|
| SPA footer (AppShell) | After company info, before copyright | Dynamic, all views |
| Static legal pages | Same position in legal-footer | privacy.html, terms.html, refund.html |
| Dev/staging pages | Same pattern | Keep in sync |
| Payment page content (mobile fallback) | Below payment buttons | Visible even when footer is hidden on mobile |

## Environment & Secret Management

### PortOne API Secret

The API Secret Key is used server-side for payment verification — NEVER expose it in frontend code.

**Local development** (`.dev.vars`):
```
PORTONE_API_SECRET=your_secret_here
```

**Production** (Wrangler secret):
```bash
npx wrangler secret put PORTONE_API_SECRET
```

**Type definition** (worker-configuration.d.ts):
```typescript
interface Env {
  // ...
  PORTONE_API_SECRET?: string;
}
```

### Frontend Config Pattern

Store `storeId` and `channelKey` in a config constant in the view file. These are not secret (they're visible in the JS bundle), but the API Secret must stay server-side.

```js
const PORTONE_CONFIG = {
  storeId: 'store-YOUR_STORE_ID',      // public
  channelKey: 'channel-key-YOUR_CHANNEL_KEY',  // public
};
```

## Mobile Considerations

### Footer Hidden on Mobile

Most SPA footers are hidden on mobile (`display: none`). Since Korean PG 인증마크 is typically placed in the footer, it won't be visible on mobile.

**Solution:** Place the 인증마크 directly in the payment page content, not just the site-wide footer:

```html
<div style="margin-top: 1rem; text-align: center; font-size: 0.7rem;">
  <p style="margin: 0 0 0.5rem 0;">KG이니시스 / PortOne 안전 결제</p>
  <img src="https://image.inicis.com/mkt/certmark/inipay/inipay_43x43_color.png"
       alt="KG이니시스 결제 인증"
       style="cursor: pointer; height: 32px; width: auto; opacity: 0.7;"
       onclick="window.open('https://mark.inicis.com/mark/popup_v3.php?mid=YOUR_MID','mark','scrollbars=no,resizable=no,width=565,height=683');">
</div>
```

Keep the 인증마크 in both places (footer for desktop, payment page for mobile).

## Dual-Directory Deploy Pitfall (M-LOG / CF Workers)

In projects served via Cloudflare Workers with `assets.directory = "./public"`, the source files may live in a different directory tree (e.g., `frontend/app/`) than the deployment directory (`public/app/`).

**The deploy script only syncs `packages/` via `sync:local`.** App JS/HTML files must be manually copied:

```bash
cp frontend/app/js/views/PaymentView.js public/app/js/views/PaymentView.js
cp frontend/app/index.html public/app/index.html
# etc.
```

**Symptoms of missed sync:**
- Payment page 404 / not found
- 인증마크 not appearing
- Old mock payment instead of PortOne SDK

### Shared Utils vs Local Utils

In m-log, there are TWO utils files:
- `packages/core/utils.js` → synced to `public/app/shared/core/utils.js` → imported as `'/app/shared/core/utils.js'`
- `frontend/app/js/utils.js` → standalone, used by `api.js`, `myeongsik.js`

**When adding shared helpers (like fingerprint functions):** Always update `packages/core/utils.js`, NOT `frontend/app/js/utils.js`. The views import from the shared path.

## Dating (Two-Person) Payment Model

For apps involving two sets of birth data (e.g., compatibility/divorce reports), the fingerprint must combine BOTH persons' data:

### Two-Person Fingerprint

```javascript
// In shared utils:
getDatingPurchaseKey(reportType, personA, personB) {
    const fpA = this.getMyeongsikFingerprint(personA || {});
    const fpB = this.getMyeongsikFingerprint(personB || {});
    return `${reportType}_${fpA}_vs_${fpB}`;
}
```

Result: `"dating_compatibility_1991_7_24_13_30_male_0_서울_홍길동_vs_1992_3_15_9_0_female_0_부산_김영희"`

Either person changing → different key → separate purchase required.

### Data Flow for Dating

1. **Before redirect to payment:** Save `{ personA, personB }` to `__DATING_FORM_VALUES__`:
   ```javascript
   localStorage.setItem('__DATING_FORM_VALUES__', JSON.stringify({ personA, personB }));
   window.location.hash = '#/payment?type=dating_compatibility';
   ```

2. **PaymentView reads dating data** when `type` starts with `'dating_'`:
   ```javascript
   if (config.type.startsWith('dating_')) {
       const dating = JSON.parse(localStorage.getItem('__DATING_FORM_VALUES__') || '{}');
       purchaseKey = Utils.getDatingPurchaseKey(config.type, dating.personA, dating.personB);
   } else {
       purchaseKey = Utils.getPurchaseKey(config.type);
   }
   ```

3. **Report view checks** with current personA/personB:
   ```javascript
   const pk = Utils.getDatingPurchaseKey('dating_compatibility', this.state.personA, this.state.personB);
   const isPaid = !!purchased[pk];
   ```

### Dynamic Purchase State (Critical Pitfall)

**Problem:** In the DatingView, `personA` and `personB` are form inputs that change over time. If `isPaidC`/`isPaidD` are computed once in `init()` with default/empty Person B, they'll be wrong when the user fills in actual data.

**Fix:** Override `update()` to recompute purchase state before every render:

```javascript
_updatePurchaseState() {
    const { personA, personB } = this.state;
    const purchased = JSON.parse(localStorage.getItem('__PURCHASED_REPORTS__') || '{}');
    const pkC = Utils.getDatingPurchaseKey('dating_compatibility', personA, personB);
    const pkD = Utils.getDatingPurchaseKey('dating_divorce', personA, personB);
    this.state.isPaidC = !!purchased[pkC];
    this.state.isPaidD = !!purchased[pkD];
}

update() {
    this._updatePurchaseState();
    Component.prototype.update.call(this);
}
```

This ensures the template always displays the correct purchase status based on current form values.

## D1 Database Integration (Backend Verification)

For production, supplement localStorage with a server-side purchase record:

### Schema

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
CREATE INDEX idx_purchases_payment ON purchases(payment_id);
```

### API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/payment/verify` | POST | PortOne API 검증 + D1 저장 |
| `/api/payment/check` | GET | D1 구매 여부 확인 |

### Verify Endpoint Logic

1. Receives `{ type, fingerprint, txId, paymentId, amount }` from frontend
2. Calls PortOne API to verify: `GET https://api.portone.io/payments/{paymentId}` with `Authorization: PortOne {API_SECRET}`
3. Checks `status === 'PAID'`
4. Inserts into D1 `purchases` table
5. Returns `{ success: true }`

### Check Endpoint

```
GET /api/payment/check?type=desire&fingerprint=1991_...&anonymousId=anon_...
```

Returns `{ success: true, data: { purchased: true/false, purchase: {...} } }`

### Frontend Call (on payment success)

```javascript
async _verifyOnServer(config, response) {
    const fingerprint = /* dating or single based on config.type */;
    const body = {
        type: config.type,
        fingerprint,
        txId: response.txId,
        paymentId: response.paymentId,
        amount: config.amount,
    };
    const res = await fetch('/api/payment/verify', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    // On failure → localStorage fallback (offline/degraded mode)
}
```

### Strategy: Dual Storage

1. **localStorage** — Primary fast check (synchronous, works offline)
2. **D1 via API** — Persistent server-side record (survives cache clears, cross-device)

Both are written on payment success. Report views check localStorage first (fast path) and optionally verify with D1 (background).

For apps where purchase is tied to a **specific entity** (birth chart / myeongsik), NOT to the user account. Each unique birth data set requires its own purchase. This prevents a user from buying one report and accessing it for all their family members' charts.

### Fingerprint Generation

Generate a deterministic fingerprint from the birth form data. Include **location and name** for precision (user's explicit preference):

```javascript
function getMyeongsikFingerprint(fv) {
    if (!fv) return '';
    const y = fv.year ?? '';
    const m = fv.month ?? '';
    const d = fv.day ?? '';
    const h = fv.hour ?? '';
    const min = fv.minute ?? '';
    const gender = fv.gender || 'male';
    const isLunar = fv.isLunar ? '1' : '0';
    const loc = (fv.location || '').trim();
    const name = (fv.personName || '').trim();
    return `${y}_${m}_${d}_${h}_${min}_${gender}_${isLunar}_${loc}_${name}`.replace(/\s+/g, '');
}
```

### Purchase Key Pattern (localStorage)

Store purchases keyed by `reportType_fingerprint`:

```javascript
// Saving a purchase:
const purchaseKey = `${config.type}_${Utils.getMyeongsikFingerprint(formValues)}`;
purchased[purchaseKey] = { purchasedAt: new Date().toISOString(), txId, paymentId };

// Checking a purchase:
const purchaseKey = Utils.getPurchaseKey('desire'); // reads __SAJU_FORM_VALUES__ from localStorage
const isPaid = !!purchased[purchaseKey];
```

### Utility Helper (shared module)

```javascript
Utils.getPurchaseKey = function(reportType) {
    const formStr = localStorage.getItem('__SAJU_FORM_VALUES__');
    const fv = formStr ? Utils.safeJsonParse(formStr, {}) : {};
    const fp = Utils.getMyeongsikFingerprint(fv);
    return `${reportType}_${fp}`;
};
```

### Critical Pitfalls

1. **Form values MUST be saved BEFORE redirect to payment.** The payment view reads `__SAJU_FORM_VALUES__` to generate the correct fingerprint:
   ```javascript
   // ✅ RIGHT: Save first, then redirect
   const fv = { year, month, day, hour, minute, gender, isLunar, location, personName };
   localStorage.setItem('__SAJU_FORM_VALUES__', JSON.stringify(fv));
   window.location.hash = '#/payment?type=desire';

   // ❌ WRONG: Redirect without saving → empty fingerprint → all purchases collapse
   window.location.hash = '#/payment?type=desire';
   ```

2. **Fingerprint must be consistent across all three stages:**
   - Report view `init()`: check `purchased[purchaseKey]` — determines if report is unlocked
   - Before redirect: save form values to `__SAJU_FORM_VALUES__` — ensures correct key at payment time
   - Payment callback: save `purchased[purchaseKey]` — records the purchase

   Mismatch at any stage causes double-payment or false "already purchased".

3. **Backend verification:** localStorage-only approach is fragile. For production, verify via server (PortOne API + DB) and store purchase records keyed by entity ID on the backend.

### Existing Report Detection

When user enters birth data that matches an already-purchased chart:
- Frontend: check `purchased[Utils.getPurchaseKey(type)]` — runs in report view `init()`
- Server (optional): query history API for existing report with matching saju data
- If found → show existing report directly (skip payment form) with toast "이전에 구매한 리포트가 있습니다."

## Payment Method Selection UI

When offering multiple payment methods (e.g., 네이버페이 + 신용카드), manage the `payMethod` dynamically:

```js
// In component state
this.state = { selectedMethod: 'naverpay' }; // 'naverpay' | 'card'

// Build request params
function buildPaymentRequest(config) {
  const base = {
    storeId: PORTONE_CONFIG.storeId,
    channelKey: PORTONE_CONFIG.channelKey,
    paymentId: `ORDER-${Date.now()}-${Math.random().toString(36).slice(2,8)}`,
    orderName: config.title,
    totalAmount: config.amount,
    currency: 'KRW',
  };

  if (this.state.selectedMethod === 'naverpay') {
    base.payMethod = 'EASY_PAY';
    base.easyPay = { easyPayProvider: 'NAVERPAY' };
  } else {
    base.payMethod = 'CARD';
  }

  return base;
}
```

## Test Payments

### KG이니시스 Test Card Numbers

| Card Type | Number | Notes |
|-----------|--------|-------|
| 테스트 성공 | `4111111111111111` | Any expiry > today, any CVC |
| 테스트 실패 | Check PG docs | Specific numbers for error simulation |

### Test Payment Flow

1. Use a **테스트** channel in PortOne Admin (not 실연동)
2. Channel keys for test channels start with `channel-key-...`
3. Test payments don't charge real money
4. Verify success: check `response.txId` is non-empty and `response.code` is absent
5. Verify failure handling: close the popup, use invalid card, etc.

## Webhooks & Mobile Redirect

For production, configure PortOne webhooks to receive async payment notifications:

```js
const requestBody = {
  // ... standard params
  redirectUrl: 'https://your-site.com/#/payment/callback',
  noticeUrls: ['https://your-api.com/api/payment/webhook'],
};
```

- `redirectUrl`: Where mobile users land after PG redirect
- `noticeUrls`: Backend endpoints that receive payment status changes
- For WebView apps, set `appScheme` for proper return-to-app behavior

## References

See `references/portone-v2-api.md` for complete SDK type definitions (PaymentRequest, EasyPayProvider, PaymentResponse, Currency enum).
See `references/m-log-portone-setup.md` for session-specific M-LOG integration notes.

## Overlap Notice

This skill and `software-development/portone-payment-integration` cover the same territory with significant overlap. The background curator should consolidate into one class-level skill.

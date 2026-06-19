# M-LOG Payment Module — PortOne V2 + KG이니시스

Session: 2026-06-12 Payment module for M-LOG saju app.

## Credentials

| Key | Value |
|-----|-------|
| Store ID | `store-c1680a66-c1c3-4ae0-86bb-3a56413bfc69` |
| Channel Key | `channel-key-a121da23-96da-417d-991d-275af89c6f22` |
| MID (인증마크) | `MOI6180465` |
| API Secret | `.dev.vars` / `wrangler secret put` |

## Per-Myeongsik Payment Model (Key Learning)

**The payment is per-birth-chart, NOT per-account.** This was a correction from the user.

### Architecture

```
User submits birth data → Report view check:
  ┌─ purchased[reportType_fingerprint] exists? → YES → show report
  └─ NO → save form values → redirect to #/payment?type=...
         → PortOne payment → save purchased[reportType_fingerprint]
         → redirect back → report view checks again → found → show report
```

### Files Modified

| File | Change |
|------|--------|
| `packages/core/utils.js` | Added `getMyeongsikFingerprint()`, `getPurchaseKey()`, `getDatingPurchaseKey()` |
| `frontend/app/js/views/PaymentView.js` | Mock → PortOne real payment + fingerprint-based save + server verify + phone input |
| `frontend/app/index.html` | PortOne SDK script tag |
| `frontend/app/js/components/layouts/AppShell.js` | 인증마크 in footer |
| `frontend/app/{privacy,terms,refund}.html` | 인증마크 in legal footers |
| `frontend/app/js/views/ReportDesireView.js` | `purchased.desire` → `purchased[Utils.getPurchaseKey('desire')]` |
| `frontend/app/js/views/ReportAiView.js` | Same pattern |
| `frontend/app/js/views/ReportLuckView.js` | Same pattern |
| `frontend/app/js/views/ReportDesireDeepView.js` | Same pattern |
| `frontend/app/js/views/ReportComprehensiveView.js` | Same pattern + added form values saving |
| `frontend/app/js/views/ReportDatingView.js` | Import Utils, fingerprint-based purchase, `_updatePurchaseState()` |
| `worker-configuration.d.ts` | `PORTONE_API_SECRET` type |
| `.dev.vars` | API Secret stored |
| `migrations/0006_add_purchases.sql` | D1 purchases table |
| `src/db/queries.ts` | `checkPurchase()`, `insertPurchase()` |
| `src/controllers/payment.ts` | Payment API endpoints |
| `worker.ts` | Payment routes |

### Pitfalls Encountered

1. **Customer email AND phone required by KG이니시스:** Payment failed with "결제자 이메일이 필요합니다" and "휴대폰 번호가 필요합니다". Fixed by adding `customer: { email, fullName, phoneNumber }` to requestPayment(). Phone stored in localStorage as `__PAYER_PHONE__`, collected via an input field in the payment form.

2. **`public/` vs `frontend/` dual-directory trap:** The m-log project has source in `frontend/app/` but the Cloudflare Worker serves from `public/app/`. The deploy script only syncs `packages/` via `sync:local`, NOT the app JS/HTML files. After editing `frontend/app/`, must manually copy to `public/app/`:

   ```bash
   cp packages/core/utils.js public/app/shared/core/utils.js
   cp frontend/app/js/views/PaymentView.js public/app/js/views/PaymentView.js
   cp frontend/app/index.html public/app/index.html
   # etc.
   ```

3. **Payment page not showing:** Caused by the above sync issue. The payment route (`'/payment': PaymentView`) was registered in the source but the file wasn't deployed.

4. **Form values saving not present in ReportComprehensiveView:** Unlike the other 4 report views, `ReportComprehensiveView.handleSubmit()` did NOT save form values to `__SAJU_FORM_VALUES__` before redirecting to payment. Had to add this manually.

5. **Shared vs local utils:** `packages/core/utils.js` is synced to `public/app/shared/core/utils.js` (used by views/AppShell). `frontend/app/js/utils.js` is a standalone file (used by api.js/myeongsik.js). Must update `packages/core/utils.js` for shared helpers.

6. **DatingView init purchase state:** Person B starts empty → `isPaidC`/`isPaidD` computed with empty Person B are always false → fix by overriding `update()` with `_updatePurchaseState()`.

7. **Mobile footer hidden:** Footer is `display: none` on mobile. 인증마크 placed in footer won't show on phones. Added 인증마크 directly in PaymentView template as fallback.

8. **Store import path:** Must import Store from `/app/shared/core/store.js` (absolute from site root), NOT `../core/Store.js` (relative, doesn't resolve in module context).

### Dating Flow Details

- Dating view has TWO purchase types: `dating_compatibility` and `dating_divorce`
- Fingerprint combines Person A + Person B: `Utils.getDatingPurchaseKey(type, A, B)`
- Form values saved to `__DATING_FORM_VALUES__` (not `__SAJU_FORM_VALUES__`)
- PaymentView detects `type.startsWith('dating_')` reads from `__DATING_FORM_VALUES__`
- Dynamic `_updatePurchaseState()` pattern in ReportDatingView

### D1 Integration

```sql
CREATE TABLE purchases (
    id TEXT PRIMARY KEY,
    user_id TEXT, anonymous_id TEXT,
    report_type TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    tx_id TEXT, payment_id TEXT,
    amount INTEGER NOT NULL DEFAULT 3800,
    status TEXT NOT NULL DEFAULT 'completed',
    purchased_at TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

API: `POST /api/payment/verify`, `GET /api/payment/check`

### Migration & Deploy

```bash
npx wrangler d1 migrations apply m_log_db
npx wrangler secret put PORTONE_API_SECRET
npm run deploy
```

### Test Flow

1. `#/report-desire` → enter birth data → submit
2. Saju calculated → redirected to `#/payment?type=desire`
3. Enter phone number (first time, persisted to localStorage)
4. Select 네이버페이 or 신용카드
5. Click "💳 3,800원 안전 결제하기"
6. KG이니시스 test payment popup
7. Test card: `4111111111111111` (any future expiry)
8. Success → localStorage saved with fingerprint key → POST /api/payment/verify → report view unlocked

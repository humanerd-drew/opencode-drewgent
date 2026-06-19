---
name: korean-payment-integration
description: "PortOne V2 SDK + D1 payment database integration for Korean PG (KG이니시스/카카오페이/한국결제네트웍스) in a Cloudflare Workers SPA. Covers: SDK setup, per-myeongsik fingerprint purchase tracking, D1 schema, mobile redirect, multi-channel config, ontology-backed LLM prompts."
---

# Korean Payment Gateway Integration (PortOne V2 + D1)

## When to Use

Integrating PortOne (포트원) V2 SDK with KG이니시스, 카카오페이, or other Korean PGs into a Cloudflare Workers SPA. The m-log project using React-like Component architecture, not a framework.

## Architecture

```
Frontend (PortOne SDK)  →  Backend (CF Worker)  →  D1 Database
     │                          │
     ├─ requestPayment()        ├─ POST /api/payment/verify
     │  with storeId +          │   (verify + save)
     │  channelKey + customer   │
     │                          ├─ GET /api/payment/check
     └─ fingerprint-based       │   (purchase lookup)
        localStorage cache      └─ PortOne API verify
```

## PortOne V2 SDK Setup

### CDN Script (in index.html)
```html
<script src="https://cdn.portone.io/v2/browser-sdk.js"></script>
```

### Configuration
```javascript
const PORTONE_CONFIG = {
    storeId: 'store-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx',
    channelKeys: {
        naverpay: 'channel-key-...',   // KG이니시스
        kakaopay: 'channel-key-...',   // 카카오페이
        card: 'channel-key-...',       // 한국결제네트웍스
    },
};
```

### requestPayment Parameters
```javascript
const response = await window.PortOne.requestPayment({
    storeId, channelKey, paymentId, orderName,
    totalAmount: 3800,           // integer, KRW won
    currency: 'KRW',
    payMethod: 'EASY_PAY',       // or 'CARD'
    easyPay: { easyPayProvider: 'NAVERPAY' },
    customer: { email, fullName, phoneNumber },
    redirectUrl: window.location.href,    // mobile redirect
});
```

### PayMethod Mapping
| Method | payMethod | easyPayProvider |
|--------|-----------|-----------------|
| 네이버페이 | EASY_PAY | NAVERPAY |
| 카카오페이 | EASY_PAY | KAKAOPAY |
| 신용카드 | CARD | (none) |

## Per-Myeongsik Purchase Tracking

Payment is per birth chart fingerprint, NOT per account.

```javascript
getMyeongsikFingerprint(fv) {
    return `${year}_${month}_${day}_${hour}_${min}_${gender}_${isLunar}_${loc}_${name}`;
}
getPurchaseKey(type) {
    return `${type}_${this.getMyeongsikFingerprint(formValues)}`;
}
getDatingPurchaseKey(type, personA, personB) {
    return `${type}_${fpA}_vs_${fpB}`;
}
```

## D1 Database

### Migration
```sql
CREATE TABLE purchases (
    id TEXT PRIMARY KEY, user_id TEXT, anonymous_id TEXT,
    report_type TEXT NOT NULL, fingerprint TEXT NOT NULL,
    tx_id TEXT, payment_id TEXT, amount INTEGER DEFAULT 3800,
    status TEXT DEFAULT 'completed', purchased_at TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## Deployment Checklist

1. Sync ALL migrations from NAS before deploying
2. Check NAS for canonical source (frontend features may differ)
3. Set `wrangler secret put PORTONE_API_SECRET`
4. Apply remote migrations: `wrangler d1 migrations apply m_log_db --remote`
5. Manual sync frontend files to `public/app/` before deploy
6. Verify dashboard feature preservation post-deploy

## Pitfalls

1. KG이니시스 requires phoneNumber in customer field
2. Mobile redirectUrl is mandatory
3. channelKey per method — never use single key for all methods
4. DatingView isPaidC/D stale — recompute on every update()
5. __SAJU_DATA__ cleared → backup to __LAST_SAJU_DATA__
6. Migration numbering conflicts between NAS and local
7. sync:local script doesn't copy frontend app files — manual sync needed

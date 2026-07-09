---
name: korean-payment-integration
description: "PortOne V2 SDK + D1 payment database integration for Korean PG (KG이니시스/카카오페이/토스페이먼츠) in a Cloudflare Workers SPA. Covers: SDK setup, per-entity fingerprint purchase tracking, D1 schema, mobile redirect, and multi-channel config."
---

# Korean Payment Gateway Integration (PortOne V2 + D1)

## When to Use

Integrating PortOne (포트원) V2 SDK with KG이니시스, 카카오페이, or other Korean PGs into a Cloudflare Workers SPA.

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
    totalAmount: 10000,          // integer, KRW won
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

## Per-Entity Purchase Tracking

For apps where purchase is tied to a specific entity (record, chart, document, etc.), NOT to the user account. Each unique entity requires its own purchase.

```javascript
function getEntityFingerprint(entity) {
    // deterministic fingerprint from entity fields
    return `${entity.id}_${entity.type}_${entity.hash}`.replace(/\s+/g, '');
}

function getPurchaseKey(reportType, entity) {
    return `${reportType}_${getEntityFingerprint(entity)}`;
}
```

## D1 Database

### Migration

```sql
CREATE TABLE purchases (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    anonymous_id TEXT,
    report_type TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    tx_id TEXT,
    payment_id TEXT,
    amount INTEGER DEFAULT 10000,
    status TEXT DEFAULT 'completed',
    purchased_at TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_purchases_user ON purchases(user_id, report_type, fingerprint);
CREATE INDEX idx_purchases_anon ON purchases(anonymous_id, report_type, fingerprint);
```

## Deployment Checklist

1. Set `wrangler secret put PORTONE_API_SECRET`
2. Apply remote migrations: `wrangler d1 migrations apply YOUR_DB --remote`
3. Deploy: `npm run deploy`

## Pitfalls

1. KG이니시스 requires `phoneNumber` in customer field
2. Mobile `redirectUrl` is mandatory
3. Use a different `channelKey` per payment method — never reuse one key for all methods
4. `localStorage` purchase cache is a fast path; always verify server-side for production
5. Keep `PORTONE_API_SECRET` server-side only

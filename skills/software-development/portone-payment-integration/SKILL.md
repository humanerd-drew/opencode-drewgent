---
name: portone-payment-integration
title: PortOne V2 Payment Gateway Integration (Korean PG)
type: skill
space: outcome
description: Integrate PortOne (포트원) V2 SDK with KG이니시스, 카카오페이, 토스페이먼츠 and other Korean PGs in a Cloudflare Workers + vanilla JS SPA architecture. Covers frontend SDK, backend verification, D1 purchase tracking, and multi-channel management.
tags: [payment, portone, inicis, kakaopay, cloudflare-workers]
created: 2026-06-12
updated: 2026-06-12
links:
  - "[[software-development/cloudflare-workers-deploy]]"
---

# PortOne V2 Payment Integration (Korean PG)

## Overview

PortOne (포트원, formerly 아임포트/I'mport) is a Korean payment gateway aggregator. This skill covers integration with a Cloudflare Workers backend and vanilla JS SPA frontend, using the PortOne V2 SDK (`@portone/browser-sdk`).

## When to Use

- Adding Korean PG payment (KG이니시스, 카카오페이, 토스페이먼츠, etc.) to a web app
- Need per-entity/per-record purchase tracking (not per-account)
- Integrating with Cloudflare Workers + D1 database
- Setting up payment verification backend

## Core Architecture

### Data Flow

```
User → SPA (PaymentView) → PortOne SDK → PG 결제창
                                          ↓ 성공
                                    SPA → POST /api/payment/verify
                                          ↓
                                    CF Worker → PortOne API 검증
                                          ↓
                                    D1 purchases 테이블 저장
                                          ↓
                                    SPA localStorage 캐시 (fallback)
```

### Required Configuration

```javascript
const PORTONE_CONFIG = {
  storeId: 'store-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx',  // PortOne admin console
  channelKeys: {
    naverpay: 'channel-key-...',   // KG이니시스 (네이버페이)
    kakaopay: 'channel-key-...',   // 카카오페이
    card: 'channel-key-...',       // 한국결제네트웍스
  },
};
```

## Frontend Integration

### SDK Loading

```html
<script src="https://cdn.portone.io/v2/browser-sdk.js"></script>
<script type="module" src="js/app.js"></script>
```

The SDK exposes `window.PortOne.requestPayment()`.

### Payment Request

```javascript
const response = await window.PortOne.requestPayment({
  storeId: PORTONE_CONFIG.storeId,
  channelKey: PORTONE_CONFIG.channelKeys[selectedMethod],
  paymentId: `ORDER-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
  orderName: config.title,
  totalAmount: config.amount,      // integer (KRW = 1x)
  currency: 'KRW',
  customer: {
    email: user?.email || '',
    fullName: user?.name || '',
    phoneNumber: payerPhone || undefined,
  },
  redirectUrl: window.location.href,
  payMethod: 'EASY_PAY',           // 'CARD' | 'EASY_PAY' | 'TRANSFER' | etc.
  easyPay: { easyPayProvider: 'NAVERPAY' },
});
```

### Response Handling

```javascript
if (!response) { /* cancelled */ return; }
if (response.code) { /* failed */ return; }

await verifyOnServer(response);
await saveToLocalStorage(config, response);
```

### Customer Info

KG이니시스 requires `customer.phoneNumber`. Collect it on the payment page and persist to localStorage:

```javascript
const PHONE_STORAGE_KEY = '__PAYER_PHONE__';
localStorage.setItem(PHONE_STORAGE_KEY, phoneDigitsOnly);
```

### Multi-Channel Payment Methods

| Method | payMethod | easyPayProvider | Channel PG |
|--------|-----------|----------------|------------|
| 네이버페이 | `EASY_PAY` | `NAVERPAY` | KG이니시스 |
| 카카오페이 | `EASY_PAY` | `KAKAOPAY` | 카카오페이 |
| 신용카드 | `CARD` | — | 한국결제네트웍스 |

## Per-Entity Purchase Tracking

For apps where purchase is tied to a specific entity (record, chart, document, etc.), generate a deterministic fingerprint:

```javascript
function getEntityFingerprint(entity) {
  return `${entity.id}_${entity.type}_${entity.hash}`.replace(/\s+/g, '');
}

const purchaseKey = `${reportType}_${getEntityFingerprint(entity)}`;
```

## Backend Verification (Cloudflare Workers)

### D1 Migration

```sql
CREATE TABLE IF NOT EXISTS purchases (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    anonymous_id TEXT,
    report_type TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    tx_id TEXT,
    payment_id TEXT,
    amount INTEGER NOT NULL DEFAULT 10000,
    status TEXT NOT NULL DEFAULT 'completed',
    purchased_at TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_purchases_user ON purchases(user_id, report_type, fingerprint);
CREATE INDEX IF NOT EXISTS idx_purchases_anon ON purchases(anonymous_id, report_type, fingerprint);
```

### Payment Verification Controller

```typescript
async function handlePaymentVerify(request, env) {
  const { type, fingerprint, txId, paymentId, amount } = await request.json();

  if (env.PORTONE_API_SECRET) {
    const verifyRes = await fetch(`https://api.portone.io/payments/${paymentId}`, {
      headers: { 'Authorization': `PortOne ${env.PORTONE_API_SECRET}` }
    });
    const verifyData = await verifyRes.json();
    if (verifyData.status !== 'PAID') throw new Error('Payment not completed');
  }

  await insertPurchase(env.DB, {
    id: `pur_${Date.now()}_${crypto.randomUUID().slice(0, 8)}`,
    reportType: type,
    fingerprint,
    txId,
    paymentId,
    amount: amount || 10000,
    purchasedAt: new Date().toISOString(),
  });

  return { success: true };
}
```

## Deployment Steps

1. **D1 Migration**: `npx wrangler d1 migrations apply YOUR_DB --remote`
2. **API Secret**: `echo "SECRET" | npx wrangler secret put PORTONE_API_SECRET`
3. **Deploy**: `npm run deploy`

## Pitfalls

- **채널 환경**: 테스트 결제는 PortOne 관리자콘솔에서 **테스트 연동** 채널을 생성해야 함.
- **모바일 리디렉션**: `redirectUrl`이 없으면 모바일 결제 완료 후 사용자가 돌아올 위치를 모름. 반드시 `window.location.href`로 설정.
- **휴 대폰 번호**: KG이니시스는 결제자 휴 대폰 번호 필수. `customer.phoneNumber`를 빈 문자열이나 undefined로 본으면 결제창에서 오류 발생.
- **D1 로컬 vs 리모트**: `wrangler d1 migrations apply`는 기본 로컬. 운영 배포 전에 반드시 `--remote`로 실행.
- **storeId 확인 위치**: PortOne 관리자콘솔 → 결제연동 → 연동정보 페이지 **우측 상단**.
- **채널 키 분리**: PG사별로 채널 키가 다름. 네이버페이(KG이니시스), 카카오페이(카카오페이), 신용카드(한국결제네트웍스) 각각 별도 채널 키 필요.

## Related

- `[[software-development/cloudflare-workers-deploy]]` — Secrets management, D1 migration, deployment workflow
- `[[software-development/korean-payment-gateway]]` — Overlapping skill covering similar PortOne V2 territory. Consolidation candidate.

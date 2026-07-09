---
name: korean-payment-gateway
description: >-
  Integrate Korean payment gateways (KG이니시스, KCP, tosspayments, etc.) via
  PortOne V2 SDK into vanilla JS SPAs. Covers SDK loading, requestPayment API,
  payMethod selection (CARD / EASY_PAY for NaverPay/KakaoPay), payment response
  handling, and backend verification pattern.
---

# Korean Payment Gateway Integration (PortOne V2 SDK)

## Overview

PortOne (포트원, formerly 아임포트) is a Korean payment gateway aggregator. It unifies multiple PG providers (KG이니시스, NHN KCP, 토스페이먼츠, etc.) under a single JavaScript SDK.

This skill covers the **PortOne V2 SDK** (`@portone/browser-sdk`) integration into a vanilla JS SPA (no bundler).

## Architecture

```
Browser SPA ──PortOne.requestPayment()──▶ PortOne Cloud ──PG routing──▶ PG provider
     │                                          │
     │ txId + paymentId                         │ PortOne API verify
     ▼                                          ▼
Your Backend ◀──── payment/verify API ─────── PortOne server SDK
```

## Step 1: SDK Loading

### CDN (Vanilla JS — no bundler)

```html
<script src="https://cdn.portone.io/v2/browser-sdk.js"></script>
```

This sets `window.PortOne` globally.

### NPM (Bundler — Vite, webpack, etc.)

```bash
npm i @portone/browser-sdk
```

```js
import PortOne from '@portone/browser-sdk/v2';
```

## Step 2: Configuration

Two values from PortOne Admin Console → **결제 연동 → 연동 정보**:

| Key | Description | Format |
|-----|-------------|--------|
| `storeId` | 상점 아이디 | `store-abc123` |
| `channelKey` | 채널 키 (per-channel) | `channel-key-xxxxx` |

```js
const PORTONE_CONFIG = {
  storeId: 'store-YOUR_STORE_ID',
  channelKey: 'channel-key-YOUR_CHANNEL_KEY',
};
```

## Step 3: Payment Request

### Basic Card Payment

```js
const response = await window.PortOne.requestPayment({
  storeId: PORTONE_CONFIG.storeId,
  channelKey: PORTONE_CONFIG.channelKey,
  paymentId: `ORDER-${Date.now()}-${Math.random().toString(36).slice(2,8)}`,
  orderName: 'Premium Report',
  totalAmount: 10000,          // Integer (KRW = 1×)
  currency: 'KRW',
  payMethod: 'CARD',
});
```

### NaverPay / KakaoPay (Easy Pay)

```js
const response = await window.PortOne.requestPayment({
  storeId: PORTONE_CONFIG.storeId,
  channelKey: PORTONE_CONFIG.channelKey,
  paymentId: `ORDER-${Date.now()}`,
  orderName: 'Premium Report',
  totalAmount: 10000,
  currency: 'KRW',
  payMethod: 'EASY_PAY',
  easyPay: { easyPayProvider: 'NAVERPAY' }, // or 'KAKAOPAY'
});
```

### Supported `payMethod` Values

| Value | Description |
|-------|-------------|
| `CARD` | 신용/체크카드 |
| `EASY_PAY` | 간편결제 (네이버페이/카카오페이 등) |
| `VIRTUAL_ACCOUNT` | 가상계좌 |
| `TRANSFER` | 계좌이체 |
| `MOBILE` | 휴대폰 소액결제 |
| `GIFT_CERTIFICATE` | 상품권/문화상품권 |

## Step 4: Response Handling

```js
const response = await window.PortOne.requestPayment(requestBody);

if (!response) {
  // User closed the popup
  return;
}

if (response.code) {
  // Payment failed
  console.error('[Payment] Error:', response);
  return;
}

// Success — send txId + paymentId to backend for verification
await verifyOnServer(response);
```

### Customer Info (Required by KG이니시스)

```js
const requestBody = {
  storeId: PORTONE_CONFIG.storeId,
  channelKey: PORTONE_CONFIG.channelKey,
  paymentId: `ORDER-${Date.now()}`,
  orderName: config.title,
  totalAmount: config.amount,
  currency: 'KRW',
  customer: {
    email: user?.email || '',          // required by KG이니시스
    fullName: user?.name || '',
    phoneNumber: payerPhone || undefined, // also required
  },
  payMethod: 'CARD',
};
```

## Step 5: Backend Verification (Pattern)

```
POST /api/payment/verify
Body: { txId, paymentId }
```

Backend calls PortOne API:

```js
// GET https://api.portone.io/payments/{paymentId}
// Authorization: PortOne {API_SECRET}
```

**Key Points:**
- Use PortOne API Secret Key server-side only
- Verify `totalAmount` matches your product price
- Never trust client-side `totalAmount` for billing
- Implement idempotency on `paymentId`

## Pitfalls

1. **StoreId is REQUIRED** — both `storeId` and `channelKey` are required.
2. **SDK not loaded** — load the script early or check `window.PortOne` before calling.
3. **Integer amount** — `totalAmount` must be an integer.
4. **Mobile redirect** — set `redirectUrl` for mobile flows.
5. **Test vs live channel** — PortOne admin has separate **테스트** and **실연동** channels.
6. **Never expose API Secret** in frontend code.

## 인증마크 (PG Certification Mark)

Korean PG providers require displaying a certification mark in the site footer.

### KG이니시스 Example

```html
<div class="footer-payment-mark">
  <img src="https://image.inicis.com/mkt/certmark/inipay/inipay_43x43_color.png"
       alt="KG이니시스 결제 인증"
       style="cursor:pointer;height:43px;"
       onclick="window.open('https://mark.inicis.com/mark/popup_v3.php?mid=YOUR_MID','mark','scrollbars=no,resizable=no,width=565,height=683');">
  <span>KG이니시스 안전 결제</span>
</div>
```

Replace `YOUR_MID` with your KG이니시스 merchant ID. Place in footer (desktop) and payment page content (mobile fallback).

## Environment & Secret Management

### PortOne API Secret

**Local development** (`.dev.vars`):
```
PORTONE_API_SECRET=your_secret_here
```

**Production** (Wrangler secret):
```bash
npx wrangler secret put PORTONE_API_SECRET
```

### Frontend Config Pattern

Store `storeId` and `channelKey` in a config constant in the view file. These are public (visible in JS bundle). The API Secret stays server-side.

```js
const PORTONE_CONFIG = {
  storeId: 'store-YOUR_STORE_ID',
  channelKey: 'channel-key-YOUR_CHANNEL_KEY',
};
```

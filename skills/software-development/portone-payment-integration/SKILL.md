---
name: portone-payment-integration
title: PortOne V2 Payment Gateway Integration (Korean PG)
type: skill
space: outcome
description: Integrate PortOne (포트원) V2 SDK with KG이니시스, 카카오페이, 한국결제네트웍스 and other Korean PGs in a Cloudflare Workers + vanilla JS SPA architecture. Covers frontend SDK, backend verification, D1 purchase tracking, and multi-channel management.
tags: [payment, portone, inicis, kakaopay, kpn, cloudflare-workers, saju, m-log]
created: 2026-06-12
updated: 2026-06-12
links:
  - "[[software-development/cloudflare-workers-deploy]]"
  - "[[devops/kanban-worker]]"
---

# PortOne V2 Payment Integration (Korean PG)

## Overview

PortOne (포트원, formerly 아임포트/I'mport) is a Korean payment gateway aggregator. This skill covers integration with a Cloudflare Workers backend and vanilla JS SPA frontend, using the PortOne V2 SDK (`@portone/browser-sdk`).

## When to Use

- Adding Korean PG payment (KG이니시스, 카카오페이, 토스페이먼츠, KSNET, etc.) to a web app
- Need per-chart/per-record purchase tracking (not per-account)
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

Add the PortOne SDK script to your HTML before the app entry point:

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
  currency: 'CURRENCY_KRW',        // or 'KRW'
  customer: {
    email: user?.email || '',
    fullName: user?.name || '',
    phoneNumber: payerPhone || undefined,
  },
  // 모바일 리디렉션 대응: 결제 완료 후 현재 페이지로 복귀
  redirectUrl: window.location.href,
  // payMethod + channelKey로 PG/수단 지정
  payMethod: 'EASY_PAY',           // 'CARD' | 'EASY_PAY' | 'TRANSFER' | etc.
  easyPay: { easyPayProvider: 'NAVERPAY' },  // 'NAVERPAY' | 'KAKAOPAY' | 'TOSSPAY' | etc.
});
```

### Response Handling

```javascript
// 사용자 취소 (결제창 닫음)
if (!response) { /* show cancel toast */ return; }

// 결제 실패
if (response.code) {
  console.error('[Payment] Error:', response);
  /* show error toast with response.message */
  return;
}

// 결제 성공
// response.txId, response.paymentId available
await verifyOnServer(response);
await saveToLocalStorage(config, response);
```

### Customer Info

KG이니시스 requires `customer.phoneNumber` for payment authentication. Collect it on the payment page and persist to localStorage:

```javascript
const PHONE_STORAGE_KEY = '__PAYER_PHONE__';

// Save
localStorage.setItem(PHONE_STORAGE_KEY, phoneDigitsOnly);

// Restore on init
this.state.payerPhone = localStorage.getItem(PHONE_STORAGE_KEY) || '';
```

### Multi-Channel Payment Methods

Different payment methods can use different PortOne channels (each with its own PG):

| Method | payMethod | easyPayProvider | Channel PG |
|--------|-----------|----------------|------------|
| 네이버페이 | `EASY_PAY` | `NAVERPAY` | KG이니시스 |
| 카카오페이 | `EASY_PAY` | `KAKAOPAY` | 카카오페이 |
| 신용카드 | `CARD` | — | 한국결제네트웍스 |

## Per-Myeongsik Purchase Tracking (M-LOG Specific)

Unlike typical per-account licensing, M-LOG tracks purchases per **myeongsik** (birth chart fingerprint):

### Fingerprint Generation

```javascript
// year_month_day_hour_minute_gender_isLunar_location_name
getMyeongsikFingerprint(fv) {
  return `${fv.year}_${fv.month}_${fv.day}_${fv.hour}_${fv.minute}_${fv.gender}_${fv.isLunar ? '1' : '0'}_${(fv.location||'').trim()}_${(fv.personName||'').trim()}`.replace(/\s+/g, '');
}
```

### localStorage Purchase Key

```javascript
// Key format: {reportType}_{fingerprint}
// Example: "desire_1991_7_24_13_30_male_0_서울_홍길동"
const purchaseKey = `${reportType}_${fingerprint}`;
```

### Dating Report (Two-Person Fingerprint)

For dating compatibility/divorce reports that involve two people:

```javascript
getDatingPurchaseKey(reportType, personA, personB) {
  const fpA = getMyeongsikFingerprint(personA);
  const fpB = getMyeongsikFingerprint(personB);
  return `${reportType}_${fpA}_vs_${fpB}`;
}
```

## Backend Verification (Cloudflare Workers)

### D1 Migration

```sql
-- 0006_add_purchases.sql
CREATE TABLE IF NOT EXISTS purchases (
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
CREATE INDEX IF NOT EXISTS idx_purchases_user ON purchases(user_id, report_type, fingerprint);
CREATE INDEX IF NOT EXISTS idx_purchases_anon ON purchases(anonymous_id, report_type, fingerprint);
```

### Payment Verification Controller

```typescript
// POST /api/payment/verify
async function handlePaymentVerify(request, env, url) {
  const { type, fingerprint, txId, paymentId, amount } = await request.json();

  // 1. PortOne API verification
  if (env.PORTONE_API_SECRET) {
    const verifyRes = await fetch(`https://api.portone.io/payments/${paymentId}`, {
      headers: { 'Authorization': `PortOne ${env.PORTONE_API_SECRET}` }
    });
    const verifyData = await verifyRes.json();
    if (verifyData.status !== 'PAID') throw new Error('Payment not completed');
  }

  // 2. Save to D1
  await dbQueries.insertPurchase(env.DB, {
    id: `pur_${Date.now()}_${crypto.randomUUID().slice(0, 8)}`,
    userId, anonymousId, reportType: type, fingerprint,
    txId, paymentId, amount: amount || 3800,
    purchasedAt: new Date().toISOString(),
  });

  return { success: true };
}
```

### Frontend → Backend Verify Call

```javascript
async function _verifyOnServer(config, response) {
  const fingerprint = Utils.getMyeongsikFingerprint(
    JSON.parse(localStorage.getItem('__SAJU_FORM_VALUES__') || '{}')
  );
  const body = {
    type: config.type,
    fingerprint,
    txId: response.txId,
    paymentId: response.paymentId,
    amount: config.amount,
    anonymousId: window.App?.getAnonymousId?.(),
  };
  const res = await fetch('/api/payment/verify', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error('Server verify failed');
}
```

## Deployment Steps

1. **D1 Migration**: `npx wrangler d1 migrations apply DB_NAME --remote`
2. **API Secret**: `echo "SECRET" | npx wrangler secret put PORTONE_API_SECRET`
3. **Deploy**: `npm run deploy`

## Pitfalls

- **채널 환경**: 테스트 결제는 PortOne 관리자콘솔에서 **테스트 연동** 채널을 생성해야 함. 실 채널로는 테스트 불가.
- **캐시 무효화 — ES 모듈 싱글톤 상태 중복 (critical)**: `app.js`의 ES 모듈 import 경로에 `?v=2.4.0` 같은 캐시버스팅 파라미터를 추가할 때, 싱글톤 모듈(`export const Store = { ... }`)에는 절대 붙이지 말 것. 브라우저는 URL이 다르면 서로 다른 모듈 인스턴스로 인식 → Store/AuthManager 등이 중복 생성 → 상태 불일치 → 앱 전체가 빈 화면 표시.
  - **✅ 올바름**: 뷰 클래스(`DashboardView.js`, `PaymentView.js` 등)에만 `?v=` 추가. 이들은 싱글톤이 아니며 한 곳에서만 import됨.
  - **❌ 위험**: `/app/shared/core/store.js?v=...` → `AppShell.js`가 `/app/shared/core/store.js`(무버전)로 import한 Store와 다른 인스턴스가 됨.
  - **fix**: `app.js`에서 `import { Store } from '/app/shared/core/store.js'` (버전 파라미터 제거). 뷰 파일만 `import { DashboardView } from './views/DashboardView.js?v=2.4.0'`.
- **CF CDN 캐시**: Cloudflare Workers의 `env.ASSETS` 바인딩은 `cache-control: public, max-age=0, must-revalidate` 헤더를 설정하지만 CDN 에지에서 `cf-cache-status: HIT`로 응답할 수 있음. 뷰 파일 URL에 `?v=버전` 파라미터를 추가하면 새 캐시 엔트리가 생성되어 강제로 최신 파일 로드. (`app.js`의 동적 module import는 쿼리 파라미터를 상속받지 않으므로 각 import 경로에 직접 `?v=`를 명시해야 함)
- **모바일 리디렉션**: `redirectUrl`이 없으면 모바일 결제 완료 후 사용자가 돌아올 위치를 모름. 반드시 `window.location.href` (전체 URL + hash 포함)로 설정.
- **휴대폰 번호**: KG이니시스는 결제자 휴대폰 번호 필수. `customer.phoneNumber`를 빈 문자열이나 undefined로 보내면 결제창에서 오류 발생. `__PAYER_PHONE__` 키로 localStorage에 저장하여 다음 결제 시 자동 복원. `input type="tel"` + 숫자만 필터링.
- **D1 로컬 vs 리모트**: `wrangler d1 migrations apply`는 기본 로컬. `--remote` 플래그 없이 실행하면 로컬 DB에만 적용됨. 운영 배포 전에 반드시 `--remote`로 실행.
- **localStorage 키 충돌**: `__PURCHASED_REPORTS__` 저장 구조를 변경할 때는 모든 리포트 뷰의 체크 로직도 함께 수정해야 함 (총 6개 리포트 뷰 + PaymentView).
- **파일 이중 구조**: `frontend/app/`에서 작업 후 `public/app/`에 수동 복사해야 반영됨. `npm run sync:local`은 shared packages만 동기화하고 app JS/HTML은 동기화하지 않음. `cp`로 직접 복사.
- **DatingView 구매 상태**: `isPaidC`/`isPaidD`는 init 시점이 아닌 `_updatePurchaseState()`로 동적 재계산. Person B 데이터가 나중에 입력되므로 handleSubmit에서도 실시간 계산.
- **`__SAJU_DATA__` 백업**: 리포트 뷰에서 `removeItem('__SAJU_DATA__')` 전에 `__LAST_SAJU_DATA__`에 백업 저장해야 대시보드가 마지막 명식을 표시 가능.
- **온톨로지 프롬프트 주입**: NAS의 온톨로지 마크다운 문서(12,700라인)를 LLM 프롬프트에 포함시킬 때는 용량 주의. 핵심 문서만 선별(백본+구조+가이드 ~16KB)하여 TS 문자열로 임베드. 전체 카탈로그(600KB+)는 번들에서 제외.
- **storeId 확인 위치**: PortOne 관리자콘솔 → 결제연동 → 연동정보 페이지 **우측 상단**에 있음. 좌측/하단 메뉴 아님.
- **채널 키 분리**: PG사별로 채널 키가 다름. 네이버페이(KG이니시스), 카카오페이(카카오페이), 신용카드(한국결제네트웍스) 각각 별도 채널 키 필요.

## Related

- `[[software-development/cloudflare-workers-deploy]]` — Secrets management, D1 migration, deployment workflow
- `[[software-development/korean-payment-gateway]]` — Overlapping skill covering similar PortOne V2 territory. Consolidation candidate.
- `[[software-development/m-log-payment]]` — M-LOG-specific payment module (per-myeongsik fingerprints, dating two-person model)
- `[[devops/kanban-worker]]` — Kanban task execution workflow

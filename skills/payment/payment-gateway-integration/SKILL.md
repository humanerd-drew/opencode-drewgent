---
name: payment-gateway-integration
category: payment
tags: [portone, kg-inicis, inicis, korean-payment, payment-gateway]
description: PortOne V2 SDK (KG이니시스) 결제 연동 패턴 — SDK 통합, 다중 채널, per-myeongsik 결제 트래킹, D1 저장, 모바일 대응
---

# Payment Gateway Integration (Korean PG)

PortOne V2 SDK (KG이니시스) 결제 연동 패턴 및 함정.

## PortOne V2 SDK Integration

### SDK 로드
```html
<script src="https://cdn.portone.io/v2/browser-sdk.js"></script>
```
SDK 로드 시 `window.PortOne`에 객체가 주입됨 (`PortOne.requestPayment()`).

### 결제 요청 파라미터
```js
PortOne.requestPayment({
  storeId: 'store-...',
  channelKey: 'channel-key-...',
  paymentId: `ORDER-${Date.now()}-${random}`,
  orderName: '상품명',
  totalAmount: 3800,      // 정수 (KRW)
  currency: 'KRW',
  payMethod: 'CARD',       // 또는 'EASY_PAY'
  easyPay: { easyPayProvider: 'NAVERPAY' },
  customer: {
    email: 'user@email.com',
    fullName: '홍길동',
    phoneNumber: '01012345678',
  },
  redirectUrl: window.location.href, // 모바일 리디렉션 대응
});
```

### PayMethod / EasyPayProvider
| PayMethod | EasyPayProvider (간편결제시) |
|-----------|------------------------------|
| `CARD` | - |
| `EASY_PAY` | `NAVERPAY`, `KAKAOPAY`, `TOSSPAY` |

## 다중 채널 관리
```js
const CHANNEL_KEYS = {
  naverpay: 'channel-key-...',
  card: 'channel-key-...',
};
channelKey: CHANNEL_KEYS[method === 'card' ? 'card' : 'naverpay'],
```

## Per-Myeongsik (명식 단위) 결제
계정 단위가 아닌 **생년월일시+성별+지역+이름 fingerprint** 기준 결제 트래킹.
```js
getFingerprint(fv) => `${year}_${month}_${day}_${hour}_${min}_${gender}_${lunar}_${loc}_${name}`;
getPurchaseKey(type) => `${type}_${fingerprint}`;
getDatingKey(type, A, B) => `${type}_${fpA}_vs_${fpB}`;
```

## Dual Storage
- **localStorage**: `__PURCHASED_REPORTS__`에 fingerprint-keyed 객체 저장
- **D1**: `POST /api/payment/verify`로 PortOne 검증 후 저장, `GET /api/payment/check`로 조회

## KG이니시스 필수값
`customer.email`, `customer.phoneNumber`, `customer.fullName` — phone은 입력폼 제공 + localStorage 저장. 테스트 카드: `1234-1234-1234-1234` (12/25, pw 00).

## 모바일
- 인증마크: footer에만 두면 모바일에서 미노출 (`display: none`) → 결제 페이지 본문에도 배치
- `redirectUrl` 필수 (PortOne SDK가 URL 파라미터로 결과 전달)

## Pitfalls
1. 테스트 채널은 `테스트 연동 관리` 탭에서 생성, 실 채널 테스트 불가
2. 모바일 footer `display:none` — 중요 정보는 본문에도 배치
3. D1 마이그레이션: 기존 테이블 있으면 실패 → `.wrangler/state/v3/d1` 리셋 후 재시도
4. 익명 사용자 구매: `anonymousId`로 추적 (서버 user_id 대체)
5. `Store.state.user` 접근은 Store 모듈 import 후에 가능

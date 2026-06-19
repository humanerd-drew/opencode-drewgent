# PortOne V2 SDK Reference

## Customer Type (요청 시 포함)

```typescript
type Customer = {
  customerId?: string;
  fullName?: string;       // 구매자 전체 이름
  firstName?: string;      // 페이팔 전용
  lastName?: string;       // 페이팔 전용
  phoneNumber?: string;    // KG이니시스 필수
  email?: string;          // 올바른 이메일 형식
  address?: Address;
  zipcode?: string;
  gender?: Gender;
  birthYear?: string;      // "1991" 형식
  birthMonth?: string;     // "07" 형식
  birthDay?: string;       // "24" 형식
  firstNameKana?: string;  // KG이니시스 JPPG 전용
  lastNameKana?: string;   // KG이니시스 JPPG 전용
};
```

## PaymentRequest (핵심 필드)

```typescript
type PaymentRequestBase = {
  storeId: string;          // PortOne 관리자콘솔 → 연동정보 우측상단
  channelKey?: string;      // 채널 키 (채널그룹 ID와 택1)
  channelGroupId?: string;
  paymentId: string;        // 고객사 주문번호 (고유값, 중복 시 실패)
  orderName: string;        // 주문명
  orderDetail?: string;
  totalAmount: number;      // 정수 (KRW=1배, USD=100배)
  currency: PaymentCurrency; // 'KRW' | 'USD' | etc.
  payMethod: PaymentPayMethod; // 'CARD' | 'EASY_PAY' | 'TRANSFER' | etc.
  customer?: Customer;
  redirectUrl?: string;     // 모바일 결제 완료 후 복귀 URL (window.location.href 권장)
  windowType?: WindowTypes; // 'POPUP' | 'REDIRECTION' | 'IFRAME'
  noticeUrls?: string[];    // 웹훅 URL (관리자콘솔 설정 대신 사용)
  customData?: Record<string, any>;
  locale?: Locale;
  country?: Country;
  productType?: ProductType;
  bypass?: PaymentBypass;   // PG사별 bypass 파라미터
  // 간편결제 전용 (payMethod='EASY_PAY' 시)
  easyPay?: {
    easyPayProvider: EasyPayProvider; // 'NAVERPAY' | 'KAKAOPAY' | 'TOSSPAY' | etc.
    availableCards?: CardCompany[];
    installment?: Installment;
    useCardPoint?: boolean;
    useInstallment?: boolean;
  };
};
```

## Customer Type (KG이니시스 요구사항)

```typescript
type Customer = {
  customerId?: string;
  fullName?: string;       // 구매자 전체 이름
  firstName?: string;      // 페이팔 전용
  lastName?: string;       // 페이팔 전용
  phoneNumber?: string;    // KG이니시스 필수! 없으면 결제창 오류
  email?: string;          // 올바른 이메일 형식
  address?: Address;
  zipcode?: string;
  gender?: Gender;
  birthYear?: string;      // "1991" 형식
  birthMonth?: string;     // "07" 형식  
  birthDay?: string;       // "24" 형식
};
```

KG이니시스는 `phoneNumber` 필수. `email`도 대부분 환경에서 필요.
로그인 사용자는 `Store.state.user`에서 email/name 조회.
비로그인은 빈 문자열 전송 (일부 PG에서 허용).
| `TOSSPAY` | 토스페이먼츠, KG이니시스, NHN KCP, 스마트로, 한국결제네트웍스 |
| `SAMSUNGPAY` | 토스페이먼츠, KG이니시스, 나이스페이먼츠, NHN KCP, 스마트로, 한국결제네트웍스 |
| `PAYCO` | 토스페이먼츠, KG이니시스, 나이스페이먼츠, 스마트로, KSNET, 한국결제네트웍스 |
| `LPAY` | 토스페이먼츠, KG이니시스, 나이스페이먼츠, 스마트로, KSNET |

## PortOne REST API V2 (서버 검증)

### 결제 단건 조회
```http
GET https://api.portone.io/payments/{paymentId}
Authorization: PortOne {API_SECRET}
```

Response status values: `PAID`, `READY`, `FAILED`, `CANCELLED`

### 결제 수동 승인 (수동 승인 채널 전용)
```http
POST https://api.portone.io/payments/{paymentId}/confirm
Authorization: PortOne {API_SECRET}
```

## Test Card Numbers (KG이니시스)

| 구분 | 카드번호 | 유효기간 | 비밀번호 | 생년월일 |
|------|---------|---------|---------|---------|
| 성공 | `1234-1234-1234-1234` | 12/25+ | 00 | 000000 |
| 성공 | `1111-1111-1111-1111` | 12/25+ | 00 | 000000 |
| 잔액부족 | `1234-5678-1234-5678` | 12/25+ | 00 | 000000 |

## CDN URLs

- SDK: `https://cdn.portone.io/v2/browser-sdk.js`
- NPM: `@portone/browser-sdk`
- jsDelivr (ESM): `https://cdn.jsdelivr.net/npm/@portone/browser-sdk@latest/dist/v2.js`
- 인증마크: `https://image.inicis.com/mkt/certmark/inipay/inipay_43x43_color.png`

## Admin Console

- https://admin.portone.io
- **storeId**: 결제연동 → 연동정보 → 우측 상단
- **channelKey**: 결제연동 → 채널관리 → 각 채널 상세
- **API Secret**: 결제연동 → 연동정보 → V2 API Secret
- **테스트 채널**: 결제연동 → 테스트 연동 관리 (실 채널과 별도)

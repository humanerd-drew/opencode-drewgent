# PortOne V2 SDK API Reference

Source: `@portone/browser-sdk@0.1.7` type definitions (unpkg).

## `PortOne.requestPayment(request)` — Full Request Shape

```typescript
type PaymentRequestBase = {
  storeId: string;            // REQUIRED: store-xxx from admin console
  paymentId: string;          // REQUIRED: unique order ID
  orderName: string;          // REQUIRED: product name
  orderDetail?: string;       // optional description
  totalAmount: number;        // REQUIRED: integer (KRW=1×, USD=100×)
  currency: 'KRW' | 'USD' | 'EUR' | 'JPY' | string;  // REQUIRED
  payMethod: PayMethod;       // REQUIRED: see PayMethod enum below
  channelKey?: string;        // channel-key-xxx (xor channelGroupId)
  channelGroupId?: string;    // for smart routing (xor channelKey)
  taxFreeAmount?: number;
  vatAmount?: number;
  customer?: Customer;        // buyer info (name, email, phone)
  windowType?: 'POPUP' | 'IFRAME' | 'REDIRECTION';
  redirectUrl?: string;       // return URL for mobile/redirect flows
  forceRedirect?: boolean;
  noticeUrls?: string[];      // webhook URLs
  confirmUrl?: string;
  appScheme?: string;         // for payment app return on mobile
  isEscrow?: boolean;
  products?: Product[];       // item details
  isCulturalExpense?: boolean;
  locale?: Locale;
  customData?: Record<string, any>;
  country?: string;
  productType?: ProductType;
  offerPeriod?: { range?: { from?: string; to?: string }; interval?: string };
  storeDetails?: StoreDetails;
  shippingAddress?: Address;
  promotionId?: string;
  popup?: Popup;
  iframe?: Iframe;
  bypass?: PaymentBypass;     // PG-specific raw passthrough

  // PayMethod-specific options:
  card?: PaymentRequestUnionCard;
  virtualAccount?: PaymentRequestUnionVirtualAccount;
  transfer?: PaymentRequestUnionTransfer;
  mobile?: PaymentRequestUnionMobile;
  giftCertificate?: PaymentRequestUnionGiftCertificate;
  easyPay?: PaymentRequestUnionEasyPay;
  paypal?: PaymentRequestUnionPaypal;
  alipay?: PaymentRequestUnionAlipay;
  convenienceStore?: PaymentRequestUnionConvenienceStore;
  alipayPlus?: PaymentRequestUnionAlipayPlus;
};
```

## PayMethod Enum

```typescript
const PayMethod = {
  CARD: 'CARD',                          // 신용/체크카드
  VIRTUAL_ACCOUNT: 'VIRTUAL_ACCOUNT',    // 가상계좌
  TRANSFER: 'TRANSFER',                  // 계좌이체
  MOBILE: 'MOBILE',                      // 휴대폰 소액결제
  GIFT_CERTIFICATE: 'GIFT_CERTIFICATE',  // 상품권
  EASY_PAY: 'EASY_PAY',                  // 간편결제
  PAYPAL: 'PAYPAL',
  ALIPAY: 'ALIPAY',
  CONVENIENCE_STORE: 'CONVENIENCE_STORE',
  ALIPAY_PLUS: 'ALIPAY_PLUS',
};
```

## EasyPay Provider Enum (for `payMethod: 'EASY_PAY'`)

```typescript
const EasyPayProvider = {
  NAVERPAY: 'NAVERPAY',     // 네이버페이
  KAKAOPAY: 'KAKAOPAY',     // 카카오페이
  TOSSPAY: 'TOSSPAY',       // 토스페이
  PAYCO: 'PAYCO',           // 페이코
  CHAI: 'CHAI',             // 차이페이
  LPAY: 'LPAY',             // L페이
  KPAY: 'KPAY',             // K페이
  SSGPAY: 'SSGPAY',         // SSG페이
  SAMSUNGPAY: 'SAMSUNGPAY', // 삼성페이
  APPLEPAY: 'APPLEPAY',     // 애플페이
};
```

## PaymentResponse (Success / Failure)

```typescript
type PaymentResponse = {
  transactionType: 'PAYMENT';
  txId: string;             // PortOne transaction ID for this attempt
  paymentId: string;        // your original order ID
  paymentToken?: string;    // for manual-confirm flows
  code?: string;            // error code (absent = success)
  message?: string;         // error message
  pgCode?: string;          // PG-specific error code
  pgMessage?: string;       // PG-specific error message
};
```

## Currency Enum (truncated — common codes)

```typescript
const Currency = {
  KRW: 'KRW',   // South Korean won (1×)
  USD: 'USD',   // US dollar (100× = cents)
  EUR: 'EUR',   // Euro
  JPY: 'JPY',   // Japanese yen (1×)
  CNY: 'CNY',   // Chinese yuan
  VND: 'VND',   // Vietnamese dong
  THB: 'THB',   // Thai baht
  SGD: 'SGD',   // Singapore dollar
  HKD: 'HKD',   // Hong Kong dollar
  GBP: 'GBP',   // Pound sterling
};
```

Both `'KRW'` and `'CURRENCY_KRW'` are accepted (`PaymentCurrency = Currency | \`CURRENCY_${Currency}\``).

## Customer Info Shape

```typescript
type Customer = {
  customerId?: string;
  fullName?: string;
  firstName?: string;
  lastName?: string;
  phoneNumber?: string;
  email?: string;
  address?: Address;
  zipcode?: string;
};
```

## SDK Loading Internals

The `@portone/browser-sdk` package provides a loader (`dist/v2.js`) that dynamically injects the real SDK from `https://cdn.portone.io/v2/browser-sdk.js`. The loader:

1. Checks `window.PortOne` (already loaded via CDN script tag)
2. If not found, creates `<script src="https://cdn.portone.io/v2/browser-sdk.js">`
3. Waits for load event
4. Resolves `window.PortOne`

So using a direct `<script>` tag is equivalent to importing the npm package.

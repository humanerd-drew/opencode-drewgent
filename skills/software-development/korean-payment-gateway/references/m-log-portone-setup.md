# M-LOG PortOne Integration Notes

## Project Structure

```
~/m-log/
├── frontend/
│   ├── app/               ← MODULAR SPA (Component-based ES modules)
│   │   ├── index.html     ← PortOne SDK script added here
│   │   ├── js/
│   │   │   ├── app.js     ← Entry point, imports PaymentView
│   │   │   ├── views/
│   │   │   │   └── PaymentView.js  ← PortOne integration lives here
│   │   │   └── components/layouts/AppShell.js  ← Footer with 인증마크
│   │   ├── privacy.html, terms.html, refund.html  ← Legal pages with footer
│   │   └── css/
│   └── dev/               ← OLDER monolithic version (single-file app.js)
│       └── index.html     ← PortOne SDK + 인증마크 also added here
└── src/                   ← Backend (Cloudflare Workers)
    └── controllers/       ← No payment endpoint yet
```

## Key Files Modified

| File | Change |
|------|--------|
| `frontend/app/js/views/PaymentView.js` | Mock → PortOne real payment |
| `frontend/app/index.html` | Added PortOne SDK `<script>` tag |
| `frontend/dev/index.html` | Added PortOne SDK `<script>` tag + 인증마크 |
| `frontend/app/js/components/layouts/AppShell.js` | Added KG이니시스 인증마크 in footer |
| `frontend/app/{privacy,terms,refund}.html` | Added 인증마크 in legal footers |
| `frontend/dev/{privacy,terms}.html` | Added 인증마크 in legal footers |

## Payment Flow

1. User clicks **결제하기** on PaymentView
2. PaymentView calls `window.PortOne.requestPayment()` with:
   - `storeId`: store-... (NEEDS REAL VALUE)
   - `channelKey`: channel-key-a121da23-96da-417d-991d-275af89c6f22
   - `paymentId`: `MLOG-${timestamp}-${random8}`
   - `orderName`: report title
   - `totalAmount`: 3800 (₩3,800)
   - `currency`: 'KRW'
   - `payMethod`: 'CARD' or 'EASY_PAY' (+ `easyPay.easyPayProvider: 'NAVERPAY'`)
3. On success: `{ txId, paymentId }` saved to `localStorage.__PURCHASED_REPORTS__[type]`
4. User redirected to report page

## 인증마크 HTML

```html
<img src="https://image.inicis.com/mkt/certmark/inipay/inipay_43x43_color.png"
     alt="클릭하시면 이니시스 결제시스템의 유효성을 확인하실 수 있습니다."
     style="cursor: pointer; height: 43px; width: auto;"
     onclick="window.open('https://mark.inicis.com/mark/popup_v3.php?mid=MOI6180465','mark','scrollbars=no,resizable=no,width=565,height=683');">
<span style="font-size: 0.7rem;">KG이니시스 안전 결제</span>
```

Notes:
- `cursor:hand` → `cursor:pointer` (IE legacy → standard)
- `Onclick` → `onclick` (lowercase)
- `border='0'` removed (CSS handles it)
- `javascript:` prefix removed from onclick

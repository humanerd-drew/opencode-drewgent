# Vite Multi-Entry MPA Setup

## Vite 설정 (vite.config.js)
```js
import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'
import { resolve } from 'path'

export default defineConfig({
  root: 'entries',                    // HTML 진입점 디렉토리
  publicDir: false,
  plugins: [svelte()],
  build: {
    outDir: resolve(__dirname, '../../public'),  // ← 절대경로 필수 (root 기준X)
    emptyOutDir: false,                // 기존 public/app/ 유지
    sourcemap: false,
    rollupOptions: {
      input: {
        input: resolve(__dirname, 'entries/input.html'),
        dashboard: resolve(__dirname, 'entries/dashboard.html'),
        payment: resolve(__dirname, 'entries/payment.html'),
        compare: resolve(__dirname, 'entries/compare.html'),
        'report/desire': resolve(__dirname, 'entries/report/desire.html'),
        'report/desire-deep': resolve(__dirname, 'entries/report/desire-deep.html'),
        'report/ai': resolve(__dirname, 'entries/report/ai.html'),
        'report/comprehensive': resolve(__dirname, 'entries/report/comprehensive.html'),
        'report/dating': resolve(__dirname, 'entries/report/dating.html'),
      },
    },
  },
  server: {
    port: 5173,
    proxy: { '/api': 'http://localhost:8787' },
  },
})
```

## Entry HTML 템플릿
각 페이지는 `entries/{page}.html`에 위치. 공통 패턴:

```html
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>M-LOG | Page Title</title>
  <!-- 원본 CSS import 체인 -->
  <link rel="stylesheet" href="/app/shared/theme/variables.css">
  <link rel="stylesheet" href="/app/css/index.css">
  <link rel="stylesheet" href="/app/css/z-override.css">
  <link rel="icon" type="image/png" href="/assets/m-log_logo.png">
  <!-- ⚠️ 필수: dark mode 활성화. 없으면 모든 페이지가 light mode로 렌더링됨 -->
  <script>document.documentElement.setAttribute('data-theme','dark');</script>
</head>
<body>
  <div id="app"></div>
  <script type="module">
    import { mount } from 'svelte'
    import Page from '../src/pages/MyPage.svelte'
    mount(Page, { target: document.getElementById('app') })
  </script>
</body>
</html>
```

## 빌드 후 디렉토리 변환
## 빌드 후 디렉토리 변환\n`npm run build:ui` 스크립트가 Vite가 생성한 `public/{page}.html`을 `public/{page}/index.html`로 이동:

⚠️ **entry 페이지 제거 시**: `build:ui` 스크립트의 `for p in ...` 목록에서도 제거해야 함. 제거하지 않으면 `mv public/{page}.html: No such file or directory` 오류 발생. (Non-fatal이지만 로그에 남음. `2>/dev/null`로 redirect 처리 권장)`, true

```bash
for p in input dashboard payment compare; do
  mkdir -p public/$p && mv public/$p.html public/$p/index.html
done
for p in desire desire-deep ai comprehensive dating; do
  mkdir -p public/report/$p && mv public/report/$p.html public/report/$p/index.html
done
```

이렇게 하면 `/input/` URL이 `public/input/index.html`을 서빙하게 됨.

⚠️ **오래된 entry 제거 시**: build:ui 스크립트에서도 해당 entry를 제거해야 함. 그렇지 않으면 `mv public/x.html: No such file or directory` 에러 발생. `2>/dev/null`로 redirect하거나 목록에서 삭제.

## wrangler dev ASSETS binding 한계
- `.html` 확장자 파일을 wrangler dev에서 직접 요청하면 307 리디렉트됨
- 원인: wrangler dev의 ASSETS binding이 `.html` 파일을 직접 경로로 서빙하지 못함
- 해결: 디렉토리 URL 사용 (`/input/` → `public/input/index.html`)
- worker.ts에서 `/*.html` → `/*/` 301 리디렉트 추가
- 프로덕션 (Cloudflare Workers)에서는 이 문제 없음 — ASSETS binding이 정상 동작

### worker.ts 패턴
```ts
// .html → directory URL 리디렉트
const pageMatch = url.pathname.match(/^\/(\w[\w-]*)\.html$/)
if (pageMatch) {
  const base = pageMatch[1]
  return Response.redirect(new URL(`/${base}/`, url.origin).toString(), 301)
}
const reportMatch = url.pathname.match(/^\/report\/([\w-]+)\.html$/)
if (reportMatch) {
  return Response.redirect(new URL(`/report/${reportMatch[1]}/`, url.origin).toString(), 301)
}
```

## 의존성 버전
- `@sveltejs/vite-plugin-svelte@^3` + Vite 5 + Svelte 5 = 호환 (경고는 있음)
- `@sveltejs/vite-plugin-svelte@^7` = Vite 8 필요 (Vite 5와 호환 불가)

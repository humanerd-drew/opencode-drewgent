# Svelte MPA Setup (Vite Multi-Entry)

## Architecture

SPA 대신 MPA (Multi-Page App)를 사용하는 이유:
- 각 페이지가 독립 URL → SEO 가능, 브라우저 기본 네비게이션
- 페이지별 필요한 JS만 로드 (code split)
- Router/SPA 복잡도 0
- `<a href="/page.html">`로 이동, JS 오버헤드 없음

## Project Structure

```
src/ui/
├── entries/                 ← HTML 엔트리 포인트 (페이지별)
│   ├── input.html
│   ├── dashboard.html
│   ├── payment.html
│   └── report/
│       ├── desire.html
│       ├── comprehensive.html
│       └── dating.html
├── src/
│   ├── pages/               ← 페이지 Svelte 컴포넌트
│   │   ├── InputPage.svelte
│   │   ├── DashboardPage.svelte
│   │   └── report/
│   │       ├── Desire.svelte
│   │       └── ...
│   └── lib/
│       ├── api.ts           ← 공유 API 클라이언트
│       ├── components/
│       │   ├── AppHeader.svelte
│       │   └── AppFooter.svelte
│       └── styles/          ← CSS 변수 공유
├── vite.config.js
└── tsconfig.json
```

## Entry HTML Pattern

각 페이지의 `entries/X.html`:

```html
<!DOCTYPE html>
<html>
<head>
  <!-- 공통 헤더 -->
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&display=swap" rel="stylesheet">
  <style>*{margin:0;padding:0;box-sizing:border-box}body{background:#080c12;font-family:'JetBrains Mono',monospace;color:#e0e4e8}</style>
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

## Vite Multi-Entry Config

```js
// src/ui/vite.config.js
import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'
import { resolve } from 'path'

export default defineConfig({
  root: 'entries',                       // ← HTML 기준 디렉토리
  publicDir: false,
  plugins: [svelte()],
  build: {
    outDir: '../../public/ui-dist',
    emptyOutDir: true,
    sourcemap: false,
    rollupOptions: {
      input: {
        input: resolve(__dirname, 'entries/input.html'),
        dashboard: resolve(__dirname, 'entries/dashboard.html'),
        payment: resolve(__dirname, 'entries/payment.html'),
        compare: resolve(__dirname, 'entries/compare.html'),
        'report/desire': resolve(__dirname, 'entries/report/desire.html'),
        // ... all pages
      },
    },
  },
  server: {
    port: 5173,
    proxy: { '/api': 'http://localhost:8787' },  // wrangler dev API 프록시
  },
})
```

## Package Version Compatibility

| 패키지 | 버전 | 비고 |
|--------|------|------|
| `svelte` | ^5.x | 5.56.3 tested |
| `@sveltejs/vite-plugin-svelte` | ^3.x | **NOT v7** — v7 requires Vite 8 |
| `vite` | ^5.x | Wrangler 4.x와 호환 |
| `wrangler` | ^4.x | |

## Build Commands

```bash
# Frontend build
cd src/ui && npx vite build          # → public/ui-dist/

# Frontend dev (HMR, API → wrangler proxy)
cd src/ui && npx vite                # localhost:5173

# Backend dev (needed for API proxy)
cd ~/m-log-v2 && npx wrangler dev    # localhost:8787

# Combined
npm run build:ui
npm run dev:ui
```

## Svelte 5 Patterns Used

| 패턴 | 용법 |
|------|------|
| `$state()` | 반응형 상태 선언 |
| `$derived()` | 다른 상태에서 파생된 값 |
| `$effect()` | 사이드 이펙트 (DOM, API, 구독) |
| `$props()` | 컴포넌트 속성 수신 |
| `mount()` | 컴포넌트 마운트 (SPA의 mount와 동일) |
| `onclick` | 이벤트 핸들러 (Svelte 5 — `on:click` 아님) |

## SPA → MPA Migration Checklist

1. 각 `View.svelte`를 `entries/X.html` + `pages/X.svelte`로 분리
2. `Router.svelte` 삭제 (더 이상 필요 없음)
3. `App.svelte` 삭제 (더 이상 필요 없음)
4. `AppLayout.svelte` → `AppHeader.svelte` + `AppFooter.svelte`로 분리
5. 각 페이지에 `AppHeader`/`AppFooter` 직접 include
6. Vite config에 모든 entry 등록
7. `window.location.hash` → `window.location.href` / `<a href>`로 교체
8. 서버측 static serving: `/{page}.html` → `ui-dist/{page}.html` 매핑

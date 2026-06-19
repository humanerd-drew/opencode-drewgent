# 2026-06-14 MPA 완료: Svelte 5 + Vite Multi-Page App

## 결정

SPA(Svelte 5 + Router) → **MPA(Svelte 5 + Vite multi-entry + `<a href>` 네비게이션)**.

## 삭제된 파일
| 파일 | 대체 |
|------|------|
| `src/ui/index.html` (SPA entry) | `entries/{page}.html` |
| `src/ui/src/main.ts` | 각 entry HTML이 직접 mount |
| `src/ui/src/App.svelte` (Router) | 삭제 |
| `src/ui/src/lib/Router.svelte` | 삭제 |
| `src/ui/src/lib/AppLayout.svelte` | `AppHeader` + `AppFooter` |
| `src/ui/src/routes/` | `src/ui/src/pages/` |

## wrangler dev 307 문제 + 해결

`wrangler dev`에서 `assets.fetch()`가 `.html` 확장자 파일에 **307 Temporary Redirect** 반환.
프로덕션에서는 정상 동작 — wrangler dev quirk.

**해결:** ASSETS이 directory 접근 시 자동으로 index.html 서빙하는 특성 활용

```bash
# build:ui 스크립트
for f in input dashboard payment compare; do
  mkdir -p public/$f && cp public/ui-dist/$f.html public/$f/index.html
done
```

Worker에서 `.html` → directory URL 301 redirect:
```ts
const MPA_ROUTES: Record<string, string> = {
  '/input.html': '/input/', '/dashboard.html': '/dashboard/', ...
}
if (MPA_ROUTES[url.pathname])
  return Response.redirect(new URL(MPA_ROUTES[url.pathname], url.origin).toString(), 301)
```

## Dev Workflow
- `npm run dev` → concurrently로 wrangler(:8787) + Vite(:5173) 동시 실행
- Vite :5173 = HMR + assets 정상. /api → wrangler proxy
- Wrangler :8787 = API + 빌드 MPA

---
name: m-log-v2-architecture
title: m-log-v2 Architecture
description: "Domain-based project structure for m-log-v2 — Svelte 5 MPA frontend, Hono backend on CF Workers, CSS variables design system"
trigger: "m-log-v2 전면 구조 개편 — Vanilla JS SPA → Svelte 5 MPA + Hono 백엔드"
provenance:
  session: "2026-06-13 m-log-v2 restructuring"
  decision: "SPA 대신 MPA 선택"
created: 2026-06-14
updated: 2026-06-15
---

# M-LOG v2 Architecture

## Completed Refactoring (2026-06-15)

### 중복 코드 통합 완료
→ `src/utils/report-format.ts` + `src/utils/llm-report.ts`

| 함수 | 처리 | 통합 위치 |
|------|------|----------|
| `callLLMJson` | 3개 파일 중복 → `callReportLLM`으로 통일 | `utils/llm-report.ts` |
| `callNvidiaWithFallback` | 3개 파일 중복 → 기존 `utils/llm.ts`로 통일 | `utils/llm.ts` |
| `callDeepSeek` | deprecated wrapper 제거 | `utils/llm.ts` |
| `hasRequiredKeys` / `sanitizeReportOutput` / `finalReportText` | 2-3개 파일 중복 → 통합 | `utils/report-format.ts` |
| `extractJsonObject` | 중복 → 기존 `utils/llm.ts` 사용 | `utils/llm.ts` |
| `polishReport` | 각 파일 자체 prompt 유지하되 `callReportLLM` 사용 | 각 generate-*.ts 파일에 잔류 |

### Controller → 도메인 파일 세분화 완료

모든 컨트롤러는 barrel re-export로 유지되어 기존 import 경로 호환성 보존:

| 원본 | 분리 결과 | 비고 |
|------|----------|------|
| `saju/saju-controller.ts` | `orchestrate-analyze.ts`, `get-iljin.ts`, `get-locations.ts`, `handle-sinsal.ts` | barrel |
| `user/auth-controller.ts` | `oauth-naver.ts`, `oauth-google.ts`, `sign-in.ts`, `manage-profile.ts` | barrel |
| `db/queries.ts` | `query-user.ts`, `query-myeongsik.ts`, `query-history.ts`, `query-report.ts`, `query-payment.ts` | barrel |
| `report/dating-controller.ts` | `generate-dating-report.ts` + `prompts/dating-system.ts` + `format/dating-score.ts`, `format/dating-text.ts`, `format/dating-analysis.ts` | barrel |
| `report/report-controller.ts` | `generate-free-report.ts`, `generate-paid-report.ts` + `prompts/report-system.ts` | barrel |
| `report/comprehensive-controller.ts` | `generate-comprehensive-report.ts` + `prompts/comprehensive-system.ts` | barrel |
| `payment/payment-controller.ts` | `verify-payment.ts`, `check-payment.ts` | barrel |

### Barrel Re-Export Pattern (사용된 기법)

대규모 리팩토링 시 기존 `import` 경로를 깨지 않고 내부 구조만 변경하는 패턴:

```typescript
// Before (monolith): src/report/dating-controller.ts — 1,565줄
export async function handleGenerateDatingReport(...) { ... }
// ... 1500줄의 private helpers ...

// After (barrel): src/report/dating-controller.ts — 1줄
export { handleGenerateDatingReport } from './generate-dating-report';
```

**장점:** 모든 importer(`route-report.ts` 등)가 코드 변경 없이 동작.
**단점:** barrel이 한 겹 더 생기지만, 디렉토리 구조 변경 시 유일하게 안전한 전환 방법.

## 디렉토리
- `src/api/` — Hono 라우트 + 미들웨어
- `src/saju/` — 사주 엔진
- `src/user/` — 계정/인증/기록
- `src/report/` — 리포트 생성
- `src/payment/` — 결제 검증
- `src/db/` — D1 쿼리
- `src/config/` — 설정/상수
- `src/utils/` — 공통 유틸
- `src/ui/` — Svelte 5 MPA 프론트엔드
- `public/app/` — 원본 SPA 백업

## 주요 명령어
- `npm run dev` = wrangler dev (localhost:8787)
- `npm run build:ui` = Vite build + public/ 디렉토리 생성

## MPA URL 구조
- `/input/`, `/dashboard/`, `/payment/`, `/compare/`
- `/report/{desire,desire-deep,ai,comprehensive,dating}/`
- 디렉토리/index.html 방식
- worker.ts에서 .html → 디렉토리 URL 301 리디렉트

## 정적 에셋 라우팅 (worker.ts vs ASSETS binding) — 흔한 함정

`wrangler.jsonc`에 `assets.directory: "./public"`가 설정되면, workerd는 Worker 코드를 실행하기 전에 먼저 ASSETS에서 파일을 찾아 서빙한다. 이로 인한 함정 두 가지:

### 함정 1: `Response.redirect()`가 데드 코드
worker.ts에 `if (url.pathname === '/') return Response.redirect('/app/')` 같은 로직을 짜도 **실행되지 않는다**. ASSETS가 먼저 `public/index.html`을 서빙하고 끝남. **worker.ts에는 `/` 핸들러를 작성하지 않는다** (또는 작성하더라도 ASSETS 우선이라 무시됨).

### 함정 2: `/app/`와 V2 MPA 공존
기존 Vanilla JS SPA가 `public/app/`에 보존되어 있다. ASSETS가 그걸 서빙하므로 `/app/` 경로는 자동으로 옛날 SPA가 됨 (백업으로 유용). `worker.ts`의 `/app/*` 라우팅은 **이중 정의 금지** — ASSETS가 처리함. `worker.ts`는 `/home-beta` 같은 옛 URL 호환만 처리하면 됨.

### 권장 worker.ts redirect 책임
- ✅ `/home-beta` → `/app/home-beta` (옛 URL 호환)
- ✅ `/page.html` → `/page/` (MPA URL 정규화)
- ✅ POST → GET 리디렉트 (form fallback)
- ❌ `/` → `/app/` (ASSETS가 처리, dead code)
- ❌ `/app/*` 명시 라우팅 (ASSETS가 처리, dead code)

### ⚠️ `/` 랜딩 페이지 결정 (사용자 디자인 정체성 — 2026-06-15 교훈)

**랜딩 페이지는 V2 빌드 산출물(`public/landing/index.html`)이 아니라, 사용자가 원본으로 지정한 페이지여야 한다.** 에이전트가 만든 기본 V2 랜딩을 무심코 `public/index.html`로 만들면, 사용자가 "이건 내가 만든 게 아닌데?"라고 즉각 거부한다. 이건 디자인 정체성 문제.

**올바른 절차:**
```bash
# 1. 사용자가 원본으로 지정한 HTML을 public/index.html로 복사
cp public/app/index.html public/index.html   # V2 이전의 런치앱 (사용자 디자인)
# 또는
cp public/landing/index.html public/index.html  # V2 Svelte 랜딩 (사용자가 선택했다면)
```

**build:ui 스크립트에 `cp` 명령을 넣지 않는다** — 매 빌드마다 사용자의 명시적 선택을 덮어쓰는 사고를 방지. 랜딩 페이지 변경은 사용자가 명시적으로 요청할 때만 수동으로 수행.

**이런 실수를 방지하는 검수:**
- `public/index.html`을 처음 cp할 때 사용자에게 "원본 = public/app/index.html, V2 랜딩 = public/landing/index.html. 어느 쪽?" 한 번이라도 확인
- cp 후 `head public/index.html`로 "<!-- v2.0.7 -->" 같은 원본 코멘트가 보이는지 확인 (Svelte 빌드 산출물에는 없음)
- V2 MPA로의 마이그레이션이 끝났어도, 사용자가 "원본 디자인 유지"를 명시적으로 선택하면 그게 default

## 디자인 시스템 (필수)
- CSS variables ONLY (`var(--xxx)`) — #hex 금지
- data-theme="dark" 필수
- AppShell 공유 컴포넌트 사용
- 원본 CSS: public/app/shared/theme/variables.css + public/app/css/index.css

## 현재 상태 (2026-06-15)
- Hono + 도메인 구조 완료
- Quintax/Just5/데드코드 제거
- Secrets 5개 등록
- Svelte 5 MPA 9페이지 전환 완료
- AppShell, 리포트 포맷팅, 히스토리 저장 구현
- **Controller 세분화 완료** — 7개 모노리스 → 20+ 도메인 파일 (barrel 호환)
- **중복 코드 통합 완료** — 6개 함수 중복 제거 (utils/llm.ts, report-format.ts, llm-report.ts)
- wrangler dev에서 ASSETS .html 307 이슈 있음 (프로덕션 정상)

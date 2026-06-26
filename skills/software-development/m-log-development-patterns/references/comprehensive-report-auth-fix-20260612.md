# Comprehensive Report Auth & Auto-Submit Fix (2026-06-12)

## Problem

대세월운 종합 리포트(/api/report/comprehensive)에서 두 가지 문제가 동시에 발생:

1. **Auto-submit 무한 호출**: `ReportComprehensiveView.mounted()`에서 결제 후 자동으로 API 호출. `_autoSubmitted` 인스턴스 변수로 1회 제한했지만, Router가 View를 destroy/재생성하면 초기화되어 리프레시마다 API 재호출. 유저가 LLM 생성 기다리다 리프레시 → 무한 반복, LLM 비용만 소진.

2. **Anonymous 401 차단**: 결제는 `anonymousId`로 가능하지만 리포트 API는 `m_log_session` 쿠키 필수. anonymous 결제자 → redirect → 401 → refresh → 401.

## Root Cause: public/ vs frontend/ divergence

`public/app/js/views/ReportComprehensiveView.js` (배포됨)와 `frontend/app/js/views/ReportComprehensiveView.js` (개발)가 달랐음.

`public/` 버전이 auto-submit 로직을 포함했고, `frontend/` 버전은 깔끔함. wrangler.jsonc의 `assets.directory: "./public"`로 인해 `public/`만 배포되므로 버그가 프로덕션에 노출됨.

## Diagnosis Process

1. 두 worker.ts(`/m-log/worker.ts` + `/m-log/public/worker.ts`) 비교 → 동일
2. Frontend `app.js` router mapping 확인 → `/report-luck`과 `/report-comprehensive` 모두 `ReportComprehensiveView` 사용
3. Component lifecycle 추적: `init()` → `render()` → `mounted()` → `setState()` → `render()` → `mounted()`
4. `_autoSubmitted` 인스턴스 변수의 취약점 확인 (Router 재생성 시 초기화)
5. NAS vs local `comprehensive-report.ts` 비교 → auth 로직 동일
6. `getSessionPayload()` + `dbQueries.checkPurchase()` 조합으로 anonymous auth 해결

## Fix Summary

### View: `public/app/js/views/ReportComprehensiveView.js`
- `init()`: `isSimulatingAnalysis: false` (고정, mount 시 자동 호출 금지)
- `mounted()`: 자동 API 호출 로직 제거. 항상 BirthForm 표시 (+ paid 메시지)
- `handleSubmit()`: 사용자 클릭 시에만 API 호출
- template: `loading || isSimulatingAnalysis` 조건으로 스피너 제어

### Controller: `src/controllers/comprehensive-report.ts`
- 요청 body에서 `fingerprint` + `anonymousId` 수용
- 세션 없으면 D1 `purchases` 테이블 조회
- `comprehensive` + `luck` 타입 모두 확인
- history save: `payload.id` → `userId` (null 가능)

### Pattern change: request body read before auth

```typescript
// BEFORE: auth → body read
const payload = await getSessionPayload(request, env, url);
if (!payload) return 401;
const input = await request.json();  // request body consumed after auth
const { person } = input;

// AFTER: body read → auth
const input = await request.json() as any;
const { person, fingerprint, anonymousId } = input;  // fingerprint 먼저 추출
const payload = await getSessionPayload(request, env, url);
let userId = payload?.id || null;
if (!payload) {
    if (!fingerprint) return 401;
    // checkPurchase() ...
}
```

### Files changed (3 files, m-log/)
- `public/app/js/views/ReportComprehensiveView.js`
- `src/controllers/comprehensive-report.ts`
- `src/db/queries.ts` (변경 없음 — 기존 `checkPurchase` 사용)

### NAS sync
- `/Users/drew/Library/CloudStorage/SynologyDrive-Log-Project/m-log/src/controllers/comprehensive-report.ts`

**⚠️ NAS/local divergence found during this fix:** NAS `frontend/app/js/views/DashboardView.js` is OLDER than local — missing "숨겨진 욕망" tab (DesireReport section). NAS version has `<h2 class="mlog-card-title">12신살 분석</h2>` without the sinsal-tabs/desire-tab. Local version has the full tab implementation. This caused the user to report "탭이 사라졌다" even though DashboardView.js was not edited.

**Lesson:** Always verify NAS ↔ local file consistency before deploying. The NAS canonical version may lack features present in the local development version.

---

## Session Extension: DashboardView unrestricted branch fix (same session)

After the auth fix deploy, user reported \"12신살 분석 옆 숨겨진 욕망 탭이 없어졌다\". Investigation revealed:

1. **DashboardView.js was NOT edited** by the auth fix — user's accusation was incorrect
2. The file on disk and server response both contained `sinsal-tabs` (verified via curl + grep)
3. DOM query `document.querySelector('.sinsal-tabs')` returned `null`
4. **Root cause**: The 12신살 section exists in TWO template branches (restricted/unrestricted), controlled by `isRestricted = !Store.state.user || sajuData.isRestricted === true || !sajuData.analysis`
5. The `sinsal-tabs` div with the 숨겨진 욕망 button only existed in the RESTRICTED branch (lines 741-763). The UNRESTRICTED branch (lines 863-937) had a different 12신살 section WITHOUT tabs.
6. When user logged in → `isRestricted = false` → UNRESTRICTED branch selected → tabs disappeared.

**No causal relationship to auth fix.** This was a pre-existing bug in the DashboardView template that only manifested when user logged in.

**Fix**: Added `sinsal-tabs` div + `sinsalPanel` wrapper + `desirePanel` div to the UNRESTRICTED branch, matching the RESTRICTED branch structure.

**Lesson for M-LOG template debugging:**
1. If file on disk is correct but DOM query returns null → check template ternary branches (`isRestricted`)
2. `curl -s http://localhost:8787/.../file.js | grep -c 'search'` to verify server response
3. `document.querySelector()` vs browser Sources tab — latter shows SOURCE code, former shows RENDERED DOM
4. **Always check both branches** when modifying DashboardView template sections
5. 304 Not Modified in wrangler dev logs is NOT an error — it's normal HTTP caching behavior
6. **desirePanel display fix**: Use `class="hidden"` not `style="display:none"` because `DesireReport.switchTab()` toggles the 'hidden' class via `classList.add/remove`. Inline style has higher specificity and prevents the panel from showing when the tab is clicked.

### Sub-fix: desireHtml dead code & heading layout (same session, subsequent turns)

After the unrestricted branch fix, two more issues were found:

1. **desireHtml 데드코드**: `generateDesireReportHtml()` on line 329 assigns to `desireHtml` but the variable is NEVER consumed in the template. `updateUI()` in `DesireReport.render()` uses ID-based selectors (`#swotGrid`, `#temperamentContent`, etc.) that don't exist in the rendered HTML (which uses class names like `swot-grid`, `temperament-content`).

2. **Heading layout**: User rejected the h2 + separate buttons pattern (redundant "12신살"). Fixed to inline heading: `12신살 분석 | 숨겨진 욕망` with `.sinsal-tabs` inside the h2.

**Fixed in switchSinsalTab():**
```
switchSinsalTab → injects generateDesireReportHtml() result into #desireContainer
                → DesireReport.render() still runs for LLM commentary in #mySinsalContent
```

**Heading fix (both branches):**
```
BEFORE: <h2>12신살 분석</h2> + <div class="sinsal-tabs"><button>12신살</button><button>숨겨진 욕망</button></div>
AFTER:  <h2><span class="sinsal-tabs"><span class="tab-btn">12신살 분석</span> | <span class="tab-btn">숨겨진 욕망</span></span></h2>
```

**Hit count for verification: `grep -c '숨겨진 욕망' dashboardView.js` should be 4**:
- 2x in template (restricted branch button + desirePanel comment)
- 2x in unrestricted branch (button + desirePanel comment)

**Key lesson**: When a computed variable (`desireHtml`) is never referenced in the template literal, it's dead code. Before adding new features, check if they're actually wired to the DOM. `grep` the variable name in the same file — if only the assignment line matches, it's dead.

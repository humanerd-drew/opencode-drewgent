---
name: m-log-development-patterns
description: M-LOG(사주 분석 플랫폼) 개발 패턴, PortOne 결제 연동, 레이어/z-index 시스템. 실수 방지 체크리스트 포함.
---

# M-LOG Development Patterns

## 프로젝트 구조
- `frontend/app/` — 모듈형 SPA (ES modules, Component 기반)
- `frontend/dev/` — 모놀리식 dev 버전 (별도 코드베이스, 수정 시 double-check)
- `public/app/` — 실제 배포 디렉토리. `frontend/app/`에서 수동 sync 필요
- `packages/core/` → `public/app/shared/core/`로 sync:local 복사
- `packages/theme/` → `public/app/shared/theme/` 복사
- `src/` — Cloudflare Workers 백엔드

## ❗절대 하지 말 것 (실수 방지)

### 1. 새 리포트/API 컨트롤러 추가 시 worker.ts 라우트 등록 누락

컨트롤러(예: `comprehensive-report.ts`)를 만들어도 `worker.ts`에 **import + 라우트 등록**을 하지 않으면 엔드포인트가 404를 반환한다.

`worker.ts`에서 다음 두 군데를 반드시 추가:

```typescript
// 1. import (기존 import 블록에 추가)
import { handleGenerateComprehensiveReport } from './src/controllers/comprehensive-report';

// 2. 라우트 등록 (POST 블록 내, 기존 비슷한 엔드포인트 근처)
if (url.pathname === '/api/report/comprehensive' && request.method === 'POST') {
    return handleGenerateComprehensiveReport(request, env, url);
}
```

**Pitfall**: 컨트롤러 파일만 만들고 끝내지 말 것. worker.ts에 등록하기 전까지는 죽은 코드다.

### 2. write_file로 JS파일 덮어쓰지 말 것
- `write_file`로 import 구문만 수정하려다 전체 파일(177→16줄)을 날림
- import만 추가/수정할 땐 **patch** 도구 사용
- 큰 파일(1000줄 이상)은 execute_code → patch로 처리

### 3. ES module import에 ?v=params 남발 금지
- `import { Store } from '/app/shared/core/store.js'` 에 `?v=2.4.0` 추가 시
  Store가 중복 로드되어 singleton 상태 공유 깨짐 → 앱 전체 먹통
- **규칙**: instance화되는 class(뷰)에만 ?v=params. singleton(Store, AuthManager)엔 절대 금지
- cache-busting은 HTML의 `<script src="...?v=VERSION">`만으로 충분

### 4. backdrop-filter z-index 버그
- `backdrop-filter`가 mobile Safari에서 예상과 다른 z-index stacking context 생성
- 레이어 문제 발생 시 `backdrop-filter: blur(...)` 제거가 1순위 해결책
- 대신 `background: rgba(...)` 반투명 처리로 대체

### 5. CSS 변수 두 세트 충돌
- `shared/theme/variables.css` (실제 로드됨) vs `app/css/variables.css` (로드 안 됨)
- `--z-fab: 2000`(shared) vs `6000`(app) 등 값이 다름
- **해결**: `z-override.css`를 index.css 다음에 로드해서 모든 z-index 강제 통일

## PortOne 결제 연동

### 설정
```javascript
// PaymentView.js
const PORTONE_CONFIG = {
  storeId: 'store-...',
  channelKeys: {
    naverpay: 'channel-key-...',  // KG이니시스
    kakaopay: 'channel-key-...',  // 카카오페이
    card: 'channel-key-...',      // 한국결제네트웍스
  },
};
```

### 결제 요청 파라미터
```javascript
PortOne.requestPayment({
  storeId, channelKey, paymentId,
  orderName: config.title,
  totalAmount: 3800,
  currency: 'KRW',
  customer: { email, fullName, phoneNumber },
  payMethod: 'EASY_PAY' | 'CARD',
  easyPay: { easyPayProvider: 'NAVERPAY' | 'KAKAOPAY' },
  redirectUrl: window.location.href,  // 모바일 리디렉션 대응
});
```

### 백엔드 검증
- `POST /api/payment/verify` → PortOne API 호출 → D1 purchases 테이블 저장
- `GET /api/payment/check?type=...&fingerprint=...`

## 명식 fingerprint (구매 단위)
- `Utils.getMyeongsikFingerprint(fv)` → `{year}_{month}_{day}_{hour}_{min}_{gender}_{isLunar}_{loc}_{name}`
- 구매 키: `{reportType}_{fingerprint}` — 명식 단위로 추적
- 데이팅: `{reportType}_{fpA}_vs_{fpB}` — 두 명식 fingerprint 조합

## 레이어/z-index 시스템
- `z-override.css`가 최종 권위 — `!important`로 모든 CSS 변수 오버라이드
- 레이어 순서: content(1) → restricted(100) → **form-dropdown(3001)** → header(120) → bottom-nav(500) → fab(700) → legend(800) → drawer-overlay(2999) → sidebar(3000) → modal(5000) → loading(6000) → toast(10000)

### form dropdown z-index (중요)

`.location-dropdown`은 `form.css`에서 `z-index: 200`으로 정의되지만, sidebar(z-index: 3000) 아래에 가려진다. **반드시 z-override.css에서 3001로 올려야 함:**

```css
/* z-override.css */
.location-dropdown,
.birth-form .location-dropdown { z-index: 3001 !important; }
```

ChartPickerSheet 등 form popup도 동일 패턴:
```css
.chart-picker-sheet { z-index: 3001 !important; }
```

Dating report CTA 버튼이 sidebar에 가려진 경우 (미확인):
```css
#generateDatingReportBtn, .select-chart-btn, #printReportBtn, #resetDatingBtn { position: relative; z-index: 1; }
```

### 6. 프론트엔드 Component 라이프사이클 — `mounted()` 직접 API 호출 금지

### sessionStorage 플래그 패턴 (결제 후 1회 자동 실행)

결제 완료 후 리포트 페이지로 돌아왔을 때는 자동으로 API를 호출해야 하지만, 리프레시 시에는 다시 호출하면 안 된다. **sessionStorage 플래그**가 이 문제를 해결한다:

```javascript
// ① 결제 페이지로 이동할 때 플래그 설정
sessionStorage.setItem('__PENDING_COMPREHENSIVE__', 'true');
window.location.hash = '#/payment?type=luck';

// ② init()에서 플래그 확인 — sessionStorage는 새 탭/리프레시 시 소멸
init() {
    const pendingReport = sessionStorage.getItem('__PENDING_COMPREHENSIVE__');
    const isPending = pendingReport === 'true' && isPaid;
    if (isPending) sessionStorage.removeItem('__PENDING_COMPREHENSIVE__');
    this.state = {
        isSimulatingAnalysis: isPending,  // 결제 후 복귀時만 true
        ...
    };
}

// ③ mounted()에서 조건부 auto-submit
mounted() {
    if (this.state.isPaid && this.state.isSimulatingAnalysis && !this.state.reportData && !this._autoSubmitted) {
        this._autoSubmitted = true;
        this.startLoadingSimulation();
        this.autoSubmitFromSavedForm();
        return;
    }
}
```

**localStorage vs sessionStorage 차이:** localStorage는 탭/브라우저 종료 후에도 유지 — 리프레시해도 플래그가 남아서 무한 API 호출 발생. sessionStorage는 탭 세션에만 유지 — 리프레시 시 소멸.

### 절대 하지 말 것: mounted()에서 API 호출

```javascript
// ❌ 절대 금지: View가 재생성될 때마다 LLM API가 재호출되어 요금 폭탄
mounted() {
    if (this.state.isPaid && this.state.isSimulatingAnalysis && !this.state.reportData && !this._autoSubmitted) {
        this._autoSubmitted = true;
        this.autoSubmitFromSavedForm();  // 매 View 마운트마다 LLM 호출
    }
}
```

**위험 이유**: `_autoSubmitted`는 Component 인스턴스 변수. Router가 `handleRoute()`로 View를 destroy/재생성하면 새로운 인스턴스에서 `_autoSubmitted`는 `undefined`. 리프레시나 내비게이션마다 API가 재호출되어 LLM 비용이 무한 누적된다.

**실제 피해 (2026-06-12):** 유저가 리포트 생성 중 리프레시할 때마다 LLM API 호출 × 2회(생성+윤문) × DeepSeek+NVIDIA fallback = 최대 8회 호출.

### 따라야 할 표현: 간결한 문단 간격

```javascript
// formatContent — 심플 문단 간격, 장식 없음
formatContent(text) {
    if (!text) return '';
    return text.split('\n').map(line => {
        const trimmed = line.trim();
        if (!trimmed) return '<div style="height:0.5rem;"></div>';
        if (trimmed.includes(':')) {
            const parts = trimmed.split(':');
            const label = parts[0].trim();
            const desc = parts.slice(1).join(':').trim();
            return `<div style="margin-bottom:0.9rem;">
                <div style="color:var(--accent-gold);font-size:0.85rem;font-weight:700;margin-bottom:0.15rem;">${label}</div>
                <div style="color:var(--text-secondary);font-size:0.85rem;line-height:1.7;">${desc}</div>
            </div>`;
        }
        return `<p style="margin:0.4rem 0;color:var(--text-secondary);font-size:0.85rem;line-height:1.7;">${trimmed}</p>`;
    }).join('');
}
```

**절대 금지**: 배지(①), 컬러 보더, 번호 원형 아이콘, 그라데이션 등 시각적 장식. 순수한 문단 간격만.

### 올바른 패턴: 결제 후에도 폼 표시, 사용자 클릭 기반 API 호출

```javascript
init() {
    this.state = {
        reportData: null,
        isPaid,
        isSimulatingAnalysis: false,   // ← 절대 true로 시작하지 않음
        loading: false,
        ...
    };
}

mounted() {
    // mounted()에서는 UI 설정만. API 호출 절대 금지.
    if (this.state.reportData && !this._historySaved) {
        this._historySaved = true;
        SajuAPI.saveHistory({...}).catch(() => {});
    }
    // 결제 여부와 무관하게 항상 폼 표시
    if (this.container.querySelector('#birthFormMount')) {
        this.birthForm = new BirthForm(..., {
            onSubmit: (fd) => this.handleSubmit(fd)
        });
    }
}

// 사용자가 직접 버튼 클릭 → API 호출
async handleSubmit(formData) {
    const isPaid = !!purchased[key];
    if (!isPaid) { /* 결제 페이지로 */ return; }
    this.setState({ loading: true });
    const res = await fetch('/api/report/comprehensive', { ... });
    // ...
}

// template: loading 상태로 스피너 제어
if (loading || isSimulatingAnalysis) { /* spinner */ }
```

### 템플릿 로딩 조건: `loading || isSimulatingAnalysis`

`isPaid && isSimulatingAnalysis` 조건은 `isSimulatingAnalysis`가 절대 true가 아니므로 의미 없음. 대신 `loading` 상태로 제어:

```javascript
// ✅ 올바름
if (loading || isSimulatingAnalysis) { /* spinner */ }

// ❌ 올바르지 않음 — isSimulatingAnalysis가 false면 절대 스피너 안 보임
if (isPaid && isSimulatingAnalysis) { /* spinner */ }
```

### public/ vs frontend/ 버전 불일치 (배포 위험)

`public/` (실제 배포)와 `frontend/` (개발/모듈형) 디렉토리가 독립적으로 관리된다. wrangler.jsonc의 `assets.directory: "./public"`로 배포되므로 **`public/`만 실제 서빙된다.**

**Router.js 결정적 차이 (2026-06-12 발견):**

```bash
$ diff public/app/js/core/Router.js frontend/app/js/core/Router.js
25c25
< const hasSaju = !!sessionStorage.getItem('__SAJU_DATA__');
---
> const hasSaju = !!localStorage.getItem('__SAJU_DATA__');
```

`sessionStorage`는 탭 종료 시 소멸 → 페이지 리프레시하면 `hasSaju`가 false가 되어 대시보드 대신 입력 페이지로 리다이렉트됨. `frontend/`의 `localStorage`가 올바른 동작.

**수정**: `public/`의 Router.js를 `frontend/` 버전으로 덮어써야 함:
```bash
cp frontend/app/js/core/Router.js public/app/js/core/Router.js
```

**현재 상태 (2026-06-12 기준, 수정 완료):**

| 항목 | `public/app/js/views/ReportComprehensiveView.js` | `frontend/app/js/views/ReportComprehensiveView.js` |
|---|---|---|
| `init()` state | ✅ `isSimulatingAnalysis: false` | ✅ `isSimulatingAnalysis: false` |
| `mounted()` | ✅ 자동 API 호출 제거됨 (BirthForm 항상 표시) | ✅ 자동 호출 없음 |
| Loading 상태 조건 | ✅ `loading \|\| isSimulatingAnalysis` | ✅ `loading \|\| isSimulatingAnalysis` |
| 결제 완료 메시지 | ✅ "✅ 이미 결제 완료" 표시 | ✅ 동일 |

**2026-06-12 수정:** `public/` 버전을 `frontend/` 버전과 동기화 완료. 더 이상 `mounted()`에서 자동 API 호출하지 않음.

**해결**: `frontend/`에서 수정한 후 반드시 `public/`으로 복사해야 한다:
```bash
# 수동 sync 필요 (sync:local script가 안 함)
cp -r frontend/app/js/views/ public/app/js/views/
```

### LLM 호출 비용 — polishReport 위험

```javascript
// 1회 종합 리포트 요청에서 발생하는 LLM API 호출:
callLLMJson(env, sys, userContent, keys, 4000, 0.25);  // ① 메인 생성
→ DeepSeek 시도 → 실패 시 NVIDIA 3회 fallback (최대 4회)
polishReport(report, env, keys);                         // ② 윤문 — ❌ 비용 2배
→ callLLMJson() 내부에서 동일한 fallback 체인 (최대 4회)
```

**요청 1건당 최대 8회 LLM API 호출 가능.** Cloudflare Worker CPU 제한(30초)을 초과할 가능성도 있음.

**✅ 권장:** `polishReport()`를 disabled 상태로 유지. main 호출의 system prompt를 강화해서 직접 품질 좋은 출력을 유도하는 것이 비용 대비 효과적.

**⛔ 경험 (2026-06-12):** auto-submit 버그 + polishReport 2회 호출 조합으로 유저 1명이 1시간 내 50회 이상 LLM 호출 유발. DeepSeek 기준 약 $1-2/시간 소진.

### Auth: anonymous 사용자 → ✅ fingerprint 기반 인증으로 해결

`handleGenerateComprehensiveReport()`는 `getSessionPayload()`로 `m_log_session` 쿠키를 확인한다. anonymous 사용자는 세션이 없어 401 응답을 받았다.

**문제:** PortOne 결제는 `anonymousId`로도 가능(세션 불필요)하지만 리포트 API는 세션이 필요했다. anonymous 결제자 → redirect → 401 → refresh → 401 반복.

**✅ 해결 (2026-06-12):** Fingerprint 기반 접근 제어

1. 요청 body에 `fingerprint` + `anonymousId` 필드 수용
2. 세션 없으면 D1 `purchases` 테이블에서 `dbQueries.checkPurchase()` 조회
3. `comprehensive` + `luck` 타입 모두 확인
4. 조회 성공 시 리포트 생성 허용

```typescript
const input = await request.json() as any;
const { person, fingerprint, anonymousId } = input;
const payload = await getSessionPayload(request, env, url);
let userId = payload?.id || null;
if (!payload) {
    if (!fingerprint) return 401;
    const purchase = await dbQueries.checkPurchase(env.DB, null, anonymousId || null, 'comprehensive', fingerprint)
        || await dbQueries.checkPurchase(env.DB, null, anonymousId || null, 'luck', fingerprint);
    if (!purchase) return 401;
}
// history 저장 시 userId 사용 (null 가능)
await env.DB.prepare('INSERT INTO history (...) VALUES (...)')
    .bind(recordId, userId, ...).run();
```

## 리포트(Report) 생성 파이프라인

### 4단계 파이프라인 (모든 리포트의 공통 아키텍처)

모든 리포트는 다음 4단계를 거쳐 생성된다. 단계별로 구현 현황이 리포트마다 다를 수 있다.

| 단계 | 설명 | 구현 | 종합(comprehensive) | 데이트(dating) | 나의 Log(free) |
|---|---|---|---|---|---|
| **① 명식 데이터** | 사주 계산 결과 + 페르소나 분석을 userContent에 JSON 주입 | `sajuApi + personaApi → data` | ✅ | ✅ | ✅ (just5Data) |
| **② 온톨로지 주입** | `getOntologyContext(mode)`로 포스트자평 관계론 backbone을 system prompt 앞에 추가 | `ONTOLOGY_CTX + '\\n\\n' + buildSystemPrompt(keys)` | ✅ `'analyze'` | ✅ `mode`에 따라 | ✅ `'analyze'` (2026-06-12 추가) |
| **③ LLM 초안 생성** | `callLLMJson()` → `response_format: json_object` → `hasRequiredKeys()` 검증 | DeepSeek → NVIDIA 3-key fallback | ✅ | ✅ | ✅ (generateAIReportContent) |
| **④ 윤문(Polish)** | `polishReport()` → POLISH_SYSTEM_PROMPT으로 AI 티 제거 (변경률 30% 제한) | 문자열 키만 처리 | ✅ | ✅ | ✅ |

모든 리포트가 동일한 `getOntologyContext()`를 통해 포스트자평 관계론 온톨로지(backbone + structure + graph catalog)를 주입받는다.

### 공통 패턴
1. **프롬프트 빌드** — `buildSystemPrompt(keys)`에서 출력 키 정의 + 분석 지시 + (선택) `ONTOLOGY_CTX`
2. **LLM 생성** — `callLLMJson(env, sys, userContent, keys, maxTokens, temperature)` → `response_format: { type: "json_object" }`로 지정 키만 가진 JSON 강제
3. **윤문(Polish)** — `polishReport(report, env, keys)` → 각 문자열 키를 LLM에 보내 AI 티 제거 (POLISH_SYSTEM_PROMPT)

### 출력 구조 패턴
| 리포트 | 출력 키 | 구성 단위 |
|---|---|---|
| 종합(comprehensive) | `layer0~3, synthesis` | ontology 층위 (L0~L3) + 종합 |
| 나의 Log(free) | `basePattern, currentCycle, keywords, guide, premiumPreview` | 주제 섹션 |
| 연애 분석(dating-analyze) | `out1_personality ~ out7_reunion` (7개) | 관계 분석 단계 |
| 연애 궁합(dating-compatibility) | `section1_my ~ section5_reunion` (5개) | 궁합 분석 단계 |
| 이혼 위험(dating-divorce) | `section1_my ~ section5_next` (5개) | 이혼 분석 단계 |

### 각 값은 문자열 (라벨:내용 형식)
- 모든 섹션 값은 **flat string**, 내부는 "라벨: 내용" 형식의 문단들
- 프론트 `formatContent()`가 ":" 기준으로 파싱 → 라벨(bold) + 내용(secondary) 렌더링
- 윤문(polishReport)이 문자열 값만 처리하므로 중첩 객체는 불가

### 윤문(POLISH) 시스템 프롬프트
```typescript
const POLISH_SYSTEM_PROMPT = [
  "당신은 한국어 리포트의 AI 티를 제거하는 전문 교열자입니다.",
  "...",
  "## 4대 철칙",
  "1. 의미 불변: 사실·주장·수치·라벨명·고유명사는 100% 원문 보존",
  "2. 근거 기반: im-not-ai 패턴(A/D/G/H/I)에 해당하는 구간만 수정",
  "3. 장르 유지: 정중한 해요체 리포트 문체 유지",
  "4. 과윤문 금지: 변경률 30% 초과 금지",
  "...",
].join("\\n");
```

### 종합 리포트(comprehensive) 출력 구조

**라우트**: `#/report-comprehensive` + `#/report-luck` (두 라우트 모두 동일한 `ReportComprehensiveView` 사용)
**구매 키**: `comprehensive` + `luck` 모두 허용 (2026-06-12부터 `luck` 타입 구매자도 접근 가능)

**결제 후 동작**: 결제 완료 후 리포트 페이지로 돌아오면 폼이 표시된다. 사용자가 직접 정보를 확인하고 Submit 버튼을 클릭해야 API가 호출된다. 자동 호출은 더 이상 하지 않는다.

```javascript
// ✅ 현재 (2026-06-12+): 사용자 클릭 기반
mounted() {
    // UI 설정만 — API 호출 금지
    if (this.container.querySelector('#birthFormMount')) {
        this.birthForm = new BirthForm(..., {
            onSubmit: (fd) => this.handleSubmit(fd)
        });
    }
}

async handleSubmit(formData) {
    const isPaid = !!(purchased[luckKey] || purchased[compKey]);
    if (!isPaid) { /* 결제 페이지로 이동 */ return; }
    this.setState({ loading: true });
    const res = await fetch('/api/report/comprehensive', { body: JSON.stringify({ person }) });
    const result = await res.json();
    if (result.success) this.setState({ reportData: result.data });
}
```

**출력 키**: `layer0, layer1, layer2, layer3, synthesis` (5개 문자열 키, 라벨:내용 형식)

| 키 | 제목 | 분석 항목 |
|---|---|---|
| `layer0` | 외재 조건 | 시기, 역할, 돈, 권력, 가족, 직업, 사회환경, 사건 |
| `layer1` | 신체·에너지 조건 | 수면, 회복, 각성, 피로, 건강, 감각, 생리 리듬 |
| `layer2` | 주의·정서·애착 조건 | 주의력, 실행기능, 충동, 불안, 회피, 상처, 내적작동모델 |
| `layer3` | 의미·관계·행동 조건 | 욕망, 자기서사, 역할 선택, 관계 반응, 실제 행동, 개입 레버 |
| `synthesis` | 종합 | 4개 레이어를 관통하는 핵심 변화와 권장 대응 방향 |

각 layer의 reasoning chain (6단계): 무엇이 변했는가 → 그 변화가 어떤 경험으로 나타나는가 → 기본 반응은 무엇인가 → 더 나은 반응 레버는 무엇인가 → 그 반응이 어떤 결과를 만들 가능성이 있는가 → 근거등급은 무엇인가

synthesis는 4개 항목: 전체 관점에서 무엇이 변했는가 / 가장 영향력이 큰 변화와 그 이유 / 전체적으로 권장하는 대응 레버 / 예상되는 단기·장기 결과

**변경 이력**: 기존에는 temporal 층위 기준(layer1=대운, layer2=세운, layer3=월운)이었으나, 2026-06-12에 ontology 레이어 기준으로 변경됨. temporal 층위는 각 ontology layer의 "무엇이 변했는가" 단계 내에 내재화됨.

자세한 스키마 명세는 `references/comprehensive-report-output-schema.md`, 수정 내역은 `references/comprehensive-report-auth-fix-20260612.md` 참고.

### max_tokens 조정 규칙

온톨로지 컨텍스트나 추가 콘텐츠를 system prompt에 주입할 때는 **반드시 `callLLMJson()`의 `maxTokens`를 함께 올려야 한다.**

| 리포트 | 온톨로지 전 | 온톨로지 후 | max_tokens |
|---|---|---|---|
| 나의 Log (free) | 없음 | `getOntologyContext('analyze')` | **1500→3000** |
| 종합(comprehensive) | 있음 | 유지 | **5000** (4000→5000, 2026-06-12) |
| 데이트 (dating) | 있음 | 유지 | 2600~3200 |

**Pitfall**: 온톨로지 컨텍스트(~2KB, ~500-700 tokens)를 system prompt 앞에 추가했는데 `maxTokens`를 그대로 두면, LLM이 출력을 짧게 잘라낸다. 특히 free report처럼 원래 max_tokens가 낮은(1500) 경우에 두드러진다.

**수정 패턴**:
```typescript
// 전 (maxTokens=1500 기본값):
const genResult = await callLLMJson(env, systemPrompt, userContent);

// 후 (maxTokens=3000으로 증가):
const genResult = await callLLMJson(env, systemPrompt, userContent, 3000);
```

### 소스 데이터 구조화 원칙 (pre-computed narrative vs raw JSON dump)

**핵심 규칙:** LLM에 전달하는 소스 데이터는 raw JSON 덤프가 아니라 **구조화된 narrative(기술문)** 형태여야 한다.

#### 잘못된 패턴 (before 2026-06-12)

```typescript
// 전: raw JSON 덤프 — LLM이 API 응답 구조를 추측해서 파싱해야 함
const userContent = `[Source Data]\n${JSON.stringify(data)}`;
```

LLM은 JSON blob 속에서 다음을 스스로 찾아야 한다:
- 현재 대운이 무엇인지 (daewoon.cycles 배열을 순회하며 현재 나이에 맞는 cycle 검색)
- 현재 세운/월운이 무엇인지
- 오행 점수, 스펙트럼 등 분석 데이터

이 과정에서 실수하면 엉뚱한 대운으로 분석하거나 추측성 내용을 생성한다.

#### 올바른 패턴 (after 2026-06-12)

```typescript
// 후: 미리 계산된 항목을 라벨과 함께 전달
const sourceLines = [
  '[사주 기본 정보]',
  `일간: ${dayMaster}`,
  `사주 기둥: ${pillars}`,
  '',
  '[현재 대운 (10년 단위 큰 흐름)]',
  `간지: ${dw.ganji} (${dw.startAge}세 시작, 방향: ${dw.direction})`,
  `대운 결합 오행: 목(${l1.ohang.wood}) 화(${l1.ohang.fire}) ...`,
  `대운 스펙트럼 변화량: ${l1.spectrumDelta} (방향: ${l1.direction})`,
  '',
  '[현재 세운 (올해의 흐름)]',
  `간지: ${sw.ganji} (${sw.year}년)`,
  `대운-세운 관계: ${l2.relation}`,
  `올해 테마: ${l2.theme}`,
].filter(Boolean).join('\n');
```

이 방식의 장점:
1. **Pre-computed**: 현재 대운/세운/월운을 분석 엔진이 이미 찾아서 전달 — LLM이 배열 순회할 필요 없음
2. **명시적 라벨**: `[현재 대운]`, `[오행 점수]` 등 섹션 구분자로 LLM이 데이터 구조를 즉시 이해
3. **계산된 값 포함**: `대운-세운 관계`, `올해 테마` 등 분석 엔진 결정론적 결과를 포함
4. **Filter(Boolean)**: 빈 줄 자동 제거 — 데이터 누락 시 해당 섹션이 출력에서 사라짐 (빈 값 전달보다 나음)

#### 적용 대상

모든 리포트 컨트롤러에서 raw JSON 대신 structured source를 사용해야 한다:

| 리포트 | 전 (raw JSON) | 후 (structured source) | 상태 |
|--------|--------------|----------------------|------|
| 종합(comprehensive) | `JSON.stringify(saju.data)` | `sourceLines.join('\n')` (라벨+값) | ✅ 2026-06-12 변경 |
| 연애(dating) | `JSON.stringify(data)` | `buildAnalyzeSource()` / `buildPairSource()` (`compactPerson` + `ontologyLens`) | ✅ 항상 구조화 |
| 나의 Log(free) | `JSON.stringify(data)` | `buildJust5Data()` / `extractAnalysisData()` | ✅ 항상 구조화 |

연애 리포트의 `compactPerson()`이 좋은 참고 패턴:
```typescript
// 필요한 필드만 추출, 불필요한 raw data는 버림
function compactPerson(person: any) {
  return {
    core: person.core,
    pillars: saju.pillars,
    analysis: { dayMaster, gyeokguk, yongsin },
    persona: { loveProfile, activeComponents }
  };
}
```

#### 분석 엔진 통합 (analyze() 함수 사용)

종합 리포트는 사주 데이터를 가져온 후 분석 엔진(`analysis/engine.ts`)을 통해 구조화된 `AnalysisReport`를 생성해야 한다. 엔진이 이미 계산한 다음 값을 명시적으로 LLM에 전달:

```typescript
import { analyze } from '../analysis/engine';

// Fetch → analyze() → structured source
const analysisReport = analyze({
    pillars: saju.data.pillars,
    dayMaster: saju.data.analysis?.dayMaster,
    gender, birthYear, currentYear, currentMonth,
    daewoonCycles: saju.data.daewoon?.cycles,
    pdcTenGods: saju.data.tenGods,
    pdcDaewoonDirection: saju.data.daewoon?.direction,
});

// 현재 대운/세운/월운이 pre-compute되어 있음
const luck = analysisReport.currentLuck;
// daewoon.ganji, saewoon.relation, wolun.month 등
// layer1 (원국+대운) combined ohang, spectrum delta
// layer2 (원국+대운+세운) relation, theme
```

**Pitfall (2026-06-12 발견):** 종합 리포트는 사주 API를 직접 호출하고 raw JSON을 LLM에 전달했다. 분석 엔진(`analyze()`)이 이미 `findCurrentLuck()`으로 현재 대운/세운을 찾고 `layer1`/`layer2` 결합 오행을 계산했지만, 이 값들은 버려지고 raw JSON만 전달됨. LLM이 API 응답 구조를 추측해야 했고, 방향성(대운→세운→월운의 흐름)이 분석에서 빠지는 원인이 됨.

**해결:** `analyze()` 호출 후 `currentLuck.daewoon.layer1`, `currentLuck.saewoon.layer2` 등 pre-computed 값을 structured source에 포함.

### LLM 호출 fallback 체인
```
DeepSeek (primary) → NVIDIA NIM Key 1 → Key 2 → Key 3
```
- DeepSeek: `DEEPSEEK_API_KEY` → `deepseek-chat`, `response_format: json_object`
- NVIDIA: `NVIDIA_NIM_KEY`, `NVIDIA_NIM_KEY_FALLBACK`, `NVIDIA_NIM_KEY_FALLBACK_2`
- 각 key 55초 timeout (종합 리포트는 2026-06-12에 30→55초로 상향, dating과 동일)
- `callLLMJson()` vs `generateAIReportContent()`: 전자는 JSON 검증(hasRequiredKeys), 후자는 원시 텍스트

### ReportLuckView / ReportComprehensiveView 구조 (혼동 주의)

M-LOG에는 "대세월운" 관련 리포트로 **두 개의 별도 구현체**가 존재한다. 혼동하면 안 된다.

| 항목 | ReportLuckView (OLD) | ReportComprehensiveView (CURRENT) |
|---|---|---|
| 라우트 | `#/report-luck` (→ 현재는 ReportComprehensiveView로 변경됨) | `#/report-comprehensive` / `#/report-luck` |
| 제목 | 📈 대세월운 종합 리포트 | 📈 대세월운 종합 리포트 |
| 데이터 소스 | `SajuAPI.fetchSaju()` → raw 사주 데이터 | `POST /api/report/comprehensive` → LLM 생성 |
| LLM 사용 | ❌ 없음 (하드코딩 해설 문단) | ✅ 4단계 파이프라인 (명식→온톨로지→LLM→윤문) |
| 구매 키 | `luck` | `luck` 또는 `comprehensive` |
| 출력 | 대운 테이블 + 고정 텍스트 | L0~L3 ontology 레이어 + synthesis |
| 상태 | **ReportComprehensiveView로 대체됨** | ✅ 활성 |

**변경 이력 (2026-06-12)**: `ReportLuckView` → `ReportComprehensiveView`로 라우트 통일.
- `app.js`: `'/report-luck': ReportLuckView` → `'/report-luck': ReportComprehensiveView`
- `ReportComprehensiveView.init()`: `comprehensive` + `luck` 구매키 모두 체크
- `ReportComprehensiveView.handleSubmit()`: 결제 타입 `type=luck` 사용 (기존 구매자 호환)
- `ReportComprehensiveView.mounted()`: 로딩 시뮬레이션 제거, 폼 표시 기반으로 변경
- `DashboardView`의 "대세월운 종합 리포트" CTA는 `#/report-luck` 링크

**Lesson**: M-LOG 리포트를 수정할 때는 반드시 `app.js`의 라우트 매핑과 `PaymentView.js`의 구매 타입을 먼저 확인할 것. 같은 이름("대세월운 종합 리포트")으로 여러 구현체가 존재할 수 있다.

## Premium CTA 패턴 (free report → paid report 이동)

무료 리포트의 `premiumPreview` 섹션 CTA 버튼은 반드시 실제 유료 리포트 페이지로 내비게이트해야 한다.

**구현 위치**: `DashboardView.js` ~2057라인, `onclick` 핸들러:

```javascript
// 올바름: 실제 페이지로 이동
onclick="window.location.hash='#/report-comprehensive'"

// 틀림: placeholder 토스트만 띄움 (사용자 클릭 후 아무 일도 안 일어남)
onclick="window.App?.appShell?.showToast(...)"
```

**Pitfall**: 새 리포트를 추가할 때마다 해당 CTA를 실제 목적지 hash로 설정할 것. 토스트/alert로 남겨두면 사용자가 클릭해도 반응이 없다.

**자동 결제 리다이렉트**: 목적지 페이지(`ReportComprehensiveView` 등)는 내부적으로 `__PURCHASED_REPORTS__`를 확인하여 미결제 시 자동으로 `#/payment?type=comprehensive`으로 보내므로, CTA에서는 단순히 목적지 hash만 설정하면 된다.

### 온톨로지 컨텍스트
- `getOntologyContext(mode)`로 `data/ontology/ontology.ts`에서 PostZiping 온톨로지 로딩
- `ONTOLOGY_CTX + '\\n\\n' + buildSystemPrompt(keys)` → 전체 system prompt
- dating-report의 경우 `buildPersonaLens()`로 페르소나 데이터 구조화 후 userContent에 포함

## 배포 절차
1. `frontend/app/js/views/` 수정 → `cp`로 `public/app/js/views/`에 동기화 (sync:local이 자동으로 안 함)
2. 그 외 `frontend/app/` 수정 → `public/app/`에 동기화
3. `packages/core/` 수정 → `public/app/shared/core/` 동기화
4. `src/controllers/` + `worker.ts` 수정 → 자동으로 wrangler가 번들링
5. `npm run deploy` (sync:local + wrangler deploy)
6. deploy 시 Cloudflare CDN cache HIT 주의 → 하드 새로고침 필요

**Pitfall**: `sync:local` script는 JS view 파일(`frontend/app/js/views/*`)을 `public/`으로 복사하지 않는다. 매번 수동 `cp -r` 또는 rsync 필요.

## 템플릿 Ternary Branch 불일치 (restricted vs unrestricted)

DashboardView의 `template()`에 **`isRestricted`로 분기되는 두 개의 HTML branch**가 있다:

```
${isRestricted ? `   ← 로그아웃/미로그인 상태 (RESTRICTED)
    ... (블러 처리 + 로그인 오버레이)
` : `                 ← 로그인 상태 (UNRESTRICTED)
    ... (전체 공개 버전)
`}
```

### 문제

각 branch의 12신살 분석 섹션이 **다른 HTML 구조**로 독립적으로 존재한다. 한 branch만 수정하면 다른 branch와 불일치 발생:

| 항목 | RESTRICTED branch | UNRESTRICTED branch (before 2026-06-12) |
|---|---|---|
| `sinsal-tabs` (12신살 + 숨겨진 욕망) | ✅ 있음 | ❌ 없었음 |
| `sinsalPanel` + `desirePanel` | ✅ 있음 | ❌ 없었음 |
| 동적 sinsal 데이터 | ❌ 하드코딩 `-` | ✅ `sinsalYearBase`, `sinsalDayBase` |

**2026-06-12 사례**: 로그인한 유저가 DashboardView의 \"숨겨진 욕망\" 탭이 사라졌다고 보고. 원인은 UNRESTRICTED branch에 탭이 아예 없었기 때문. 한 달 전 RESTRICTED branch에만 feature를 추가하고 UNRESTRICTED branch는 수정하지 않음.

### 수정 패턴

DashboardView 템플릿 수정 시 반드시 양쪽 branch를 모두 확인:

```bash
# 두 branch에서 모두 찾는 문자열 검색
grep -n 'sinsal-tabs\|desirePanel\|12신살' public/app/js/views/DashboardView.js
```

결과가 2개면 양쪽 branch 모두 존재. 1개면 한쪽만 수정된 것.

실제 수정:
```javascript
// RESTRICTED branch (line ~741-763): tabs + panel 있음
// UNRESTRICTED branch (line ~863-937): tabs만 추가, panel만 추가
// 1. section-header에 sinsal-tabs div 추가
// 2. sinsal-container를 sinsalPanel으로 wrapping
// 3. desirePanel div 추가
```

### 일반화: Component 템플릿 내 조건부 branch

M-LOG Component의 `template()` 메서드에서 다음과 같은 조건부 분기가 자주 사용된다:

- **`isRestricted`** — 로그인 상태에 따라 다른 HTML 렌더링 (DashboardView)
- **`reportData`** — 미리보기 vs 결과 표시 (Report*View)
- **`loading`** — 로딩 스피너 vs 컨텐츠 (모든 Report*View)
- **`error`** — 오류 메시지 표시 (모든 Report*View)

**규칙**: 조건부 branch가 있는 template을 수정할 때는 **모든 branch에서 동일한 feature가 존재하는지 확인**. 하나의 branch에만 추가하면 다른 상태에서 기능이 사라진 것처럼 보인다.

## 탭 UI 패턴

### 탭은 heading inline으로: "제목 A | 제목 B"

```html
<!-- ❌ 잘못됨: 제목 + 별도 버튼 → "12신살"이 두 번 반복됨 -->
<div class="section-header">
    <h2>12신살 분석</h2>
    <div class="sinsal-tabs">
        <button>12신살</button>
        <button>숨겨진 욕망</button>
    </div>
</div>

<!-- ✅ 올바름: heading 하나에 inline으로 -->
<div class="section-header">
    <h2>
        <span class="sinsal-tabs" style="display:inline-flex;align-items:center;gap:6px;">
            <span class="tab-btn active" data-tab="sinsal" style="cursor:pointer;">12신살 분석</span>
            <span style="color:var(--text-tertiary);opacity:0.4;">|</span>
            <span class="tab-btn" data-tab="desire" style="cursor:pointer;color:var(--text-secondary);">숨겨진 욕망</span>
        </span>
    </h2>
</div>
```

이 패턴은 `section-header`의 `.mlog-card-title` h2 안에 `.sinsal-tabs`를 inline-flex로 배치한다. `|` separator는 `opacity:0.4`로 시각적 구분만 준다.

`.tab-btn` 클래스와 `data-tab` 속성은 `switchSinsalTab()` 함수의 이벤트 위임(`'click .sinsal-tabs .tab-btn': 'switchSinsalTab'`)과 `DesireReport.switchTab()`의 DOM 쿼리(`.sinsal-tabs .tab-btn`)를 위해 반드시 유지해야 한다.

### desirePanel: `style="display:none"` 금지, `class="hidden"` 사용

`DesireReport.switchTab()`은 `hidden` 클래스를 토글(add/remove)해서 패널을 표시/숨긴다:

```javascript
// DesireReport.js line 126-131
if (tabType === 'sinsal') {
    sinsalPanel?.classList.remove('hidden');
    desirePanel?.classList.add('hidden');
} else {
    sinsalPanel?.classList.add('hidden');
    desirePanel?.classList.remove('hidden');
}
```

**반드시 `class="hidden"`을 사용하고, `style="display:none"`을 사용하지 말 것:**

```html
<!-- ❌ 잘못됨: switchTab()이 'hidden' 클래스를 찾는데 inline style이 우선함 -->
<div id="desirePanel" style="display:none;">

<!-- ✅ 올바름 -->
<div id="desirePanel" class="hidden">
```

CSS `.hidden { display: none !important; }`는 `utility.css`에 정의되어 있다.

`.sinsal-tabs`가 포함된 section은 `id="sinsalCardSection"` (unrestricted branch) 또는 inline style (restricted branch)로 존재하며, 두 branch 모두 동일한 구조를 가져야 한다.

### desireHtml 데드코드 패턴 (SWOT/기질/재능 렌더링 안 됨)

DashboardView에서 `generateDesireReportHtml()`은 `desireHtml` 변수에 결과를 할당하지만 (line 329), 이 변수는 **어디에서도 템플릿에 주입되지 않음**. SWOT, 기질, 재능, 신살 해설 등의 내용이 생성만 되고 렌더링되지 않는 전형적인 데드코드.

```javascript
// DashboardView.js template() — line 328-329
let desireHtml = sajuData ? this.generateDesireReportHtml(sajuData) : '';
// ↑ desireHtml은 이 줄 이후로 참조되지 않음! 어디에서도 ${desireHtml} 없음
```

이 때문에 `DesireReport.render()`가 `updateUI()`에서 `document.getElementById('swotGrid')` 등으로 직접 DOM을 찾아 주입하려 했지만, `generateDesireReportHtml()`이 생성하는 HTML은 **class명**(`swot-grid`, `temperament-content`, `talent-content` 등)이고 `updateUI()`는 **id명**(`#swotGrid`, `#temperamentContent` 등)으로 찾아서 불일치 발생.

**해결**: `switchSinsalTab()`에서 `#desireContainer`에 `generateDesireReportHtml()` 결과를 직접 주입:

```javascript
// DashboardView.js — switchSinsalTab()
switchSinsalTab(e, target) {
    const tab = target.getAttribute('data-tab');
    if (!tab) return;
    DesireReport.switchTab(tab);
    if (tab === 'desire' && this.state.sajuData) {
        const container = document.getElementById('desireContainer');
        if (container) {
            const desireHtml = this.generateDesireReportHtml(this.state.sajuData);
            container.innerHTML = desireHtml;  // ← 직접 주입
        }
        // LLM commentary는 DesireReport.render()에서 별도 처리
        DesireReport.render(name, this.state.sajuData, birthHour).catch(() => {});
    }
}
```

**Pitfall**: `generateDesireReportHtml()`은 static 분석 데이터(SWOT, 기질, 재능, 신살 해설)만 생성. LLM 기반 신살 해설은 `DesireReport.render()` → `renderLLMCommentary()`가 `#mySinsalContent`에 별도로 렌더링하므로 둘 다 필요. `/data/sinsal-guide.json` fetch 실패 시 sinsal 데이터가 빈 값이 될 수 있음. 실패는 console.warn만 출력되므로 조용히 넘어감.

## 리포트 파이프라인 디버깅 방법론

리포트(comprehensive, dating, free-log)가 생성되지 않거나 품질이 기대와 다를 때, 파이프라인 어느 단계에서 막혔는지 추적하는 방법.

### 파이프라인 개요 (4단계)

모든 리포트는 동일한 4단계 파이프라인을 거친다:

```
① 명식 데이터 → ② 온톨로지 주입 → ③ LLM 초안 생성 → ④ 윤문(Polish)
```

### 단계별 실패 진단

#### ① 명식 데이터 준비
- saju API / persona API 응답 확인 (worker 로그의 `fetchWithTimeout` 결과)
- 실패 시: `"[Comprehensive Report Error]"` 또는 `"[Dating LLM Error]"` 로그
- **진단**: wrangler dev 로그에서 해당 API 호출의 HTTP 상태 코드 확인. saju API가 다른 worker라면 그 worker의 로그도 확인.

#### ② 온톨로지 주입
- `getOntologyContext('analyze')` 결과(~2,188 chars)가 system prompt 앞에 붙는지 확인
- **문제점**: postziping 관계론 온톨로지로, 사주/운세 분석에 직접적 도움 안 됨 (성격/관계 심리 전용)
- **진단**: 온톨로지 컨텍스트 길이는 약 2.2KB. system prompt가 비정상적으로 짧으면 import 실패 가능성. worker startup 시 module-level throw면 worker 전체 로드 불가.

#### ③ LLM 초안 생성 (`callLLMJson`)
- DeepSeek → NVIDIA 3-key fallback 순차 시도
- **성공 로그**: `[Comprehensive] DeepSeek OK (...ms)` (종합, 2026-06-12 추가)
- **실패 로그**: `[Comprehensive] DeepSeek API error (status) after ...ms` 또는 `[Comprehensive] DeepSeek error after ...ms` (종합, 2026-06-12에 경과 시간 추가)
- **fallback 소진 로그**: 없음 (throw → catch에서 fallback 메시지)
- **진단**:
  1. wrangler dev 로그에서 `[Comprehensive]` / `[Dating AI]` / `[Dating LLM Error]` prefix 검색
  2. `[Comprehensive]` 로그가 하나도 없으면 DeepSeek이 조용히 성공한 것 (정상)
  3. 로그에 400/401/429 에러가 있으면 API 키 문제 또는 rate limit
  4. 로그에 timeout/abort 에러가 있으면 네트워크 지연 또는 Cloudflare 30초 제한

#### ④ 윤문 (polishReport)
- `callLLMJson()`을 한 번 더 호출 (비용 2배)
- **성공해도 merge 조건 탈락 가능**:
  ```typescript
  // 검증 조건 (comprehensive-report.ts line 131)
  val.trim().length >= orig.length * 0.7
  ```
  AI 톤 제거가 문장을 간결하게 만들어 이 조건에 자주 걸린다. merge reject 시 `merged`는 원본 복사본.
- **실패해도 catch에서 조용히 원문 반환** (단, 2026-06-12부터 `console.warn` 로그 추가)
- **진단**:
  1. 종합 리포트: `[Comprehensive] Polish starting (...)` 로그로 시작 확인
  2. `[Comprehensive] Polish done: N/5 fields merged` — 변경된 필드 수 확인 (0이면 merge 검증 탈락)
  3. `[Comprehensive] Polish failed: ...` 로그로 윤문 실패 확인
  4. 윤문 실패 로그 없는데 merge가 0이면 → `70% length` 검증 통과 못 한 것

### timeout 분석

| 리포트 | `callLLMJson` timeout | 최대 LLM 호출 수 (fallback 전체) | 관측된 총 응답 시간 |
|--------|----------------------|--------------------------------|-------------------|
| 종합(comprehensive) | **55초** (30초→55초로 상향, 2026-06-12) | 최대 8회 (생성 4 + 윤문 4) | 35~58초 |
| 연애(dating) | 55초 | 최대 8회 (생성 4 + 윤문 4) | 비슷 |
| 나의 Log(free) | 60초 | 1회 (단일 call) | 5~15초 |

Cloudflare Worker의 CPU 시간 제한(30초)과는 별개로, `fetch()` 호출의 timeout은 각각 독립적이다. 단일 worker가 3분(180초) 동안 실행될 수 있으며, 이 시간 내에 여러 외부 API를 순차 호출할 수 있다.

**종합 리포트 timeout 상향 완료 (2026-06-12):**
- 실측: `POST /api/report/comprehensive 200 OK (57743ms)` — 57.7초
- `callLLMJson` timeout을 30초 → **55초**로 상향
- `max_tokens`: main 4000→**5000**, polish 최대 4500→**6000**
- 각 provider별 55초 timeout, DeepSeek → NVIDIA 3회 fallback은 유지

### 진단 체크리스트

리포트 문제 발생 시 다음 순서로 확인:

1. [ ] wrangler dev 로그에 `[Comprehensive]` / `[Dating]` / `[Dating Polish]` 메시지 있나?
2. [ ] DeepSeek API 에러(400/401/429)나 timeout 로그가 있나?
3. [ ] 프론트엔드 90초 abort 전에 응답이 왔나? (`POST /api/report/comprehensive` 응답 시간 확인)
4. [ ] 출력에 `layer0~3` + `synthesis` 5개 키가 모두 있고 비어있지 않나?
5. [ ] 출력이 fallback 에러 메시지인가? ("분석 데이터를 불러오는 중 오류가 발생했습니다" = catch 블록)
6. [ ] 경로별 fallback 차이:
   - **종합(comprehensive)**: fallback = 에러 메시지
   - **연애(dating)**: fallback = 정적 리포트 (pre-written content)
   - **나의 Log(free)**: fallback = `내용을 준비할 수 없습니다`
7. [ ] 온톨로지 컨텍스트가 system prompt에 포함되었나? (컨트롤러 line 254 확인)
8. [ ] 윤문 merge 검증 조건(line 131)을 통과했나? (val.length >= orig.length * 0.7)

## 연애 리포트 vs 종합 리포트 구조 비교 (2026-06-12)

두 리포트 컨트롤러는 동일한 4단계 파이프라인을 공유하지만 구현 디테일에서 차이가 있다. 종합 리포트 개선 시 참고할 벤치마크.

### 전체 비교표

| 항목 | 종합(comprehensive) | 연애(dating) | 비고 |
|------|-------------------|-------------|------|
| **timeout** | **55초** (2026-06-12에 30→55 상향) | 55초 | 통일 완료 |
| **최대 max_tokens** | **5000** (2026-06-12에 4000→5000 상향) | 2600~3200 (동적) | 상향 완료 |
| **온톨로지** | `getOntologyContext('analyze')` | 동일 | 동일 |
| **윤문 패턴 수** | **14개** (2026-06-12에 5→14 확장) | 12+개 | 확장 완료 |
| **윤문 절대 보존 항목** | **추가 완료** (2026-06-12) | 있음 | 추가 완료 |
| **console.log** | **추가 완료** (전 단계, 2026-06-12) | 있음 | 추가 완료 |
| **폴백(fallback)** | 에러 메시지 | 정적 리포트 | 미구현 |
| **근거 기반 강제** | **추가 완료** (2026-06-12) | 있음 | 추가 완료 |
| **섹션 최소 글자수** | **추가 완료** (400자, 2026-06-12) | 300~450자 | 추가 완료 |
| **사주→일상 번역** | **추가 완료** (2026-06-12) | 있음 | 추가 완료 |
| **출력 키 수** | 5개 (L0~3 + synthesis) | 5~7개 (mode별) | 유지 |
| **callLLMJson 위치** | 컨트롤러 인라인 | ../utils/llm.ts 공유 모듈 | 통합 가능 |
| **hasRequiredKeys** | 컨트롤러 인라인 | 공유 함수 | 공유화 |

### 윤문 프롬프트 상세 비교 (2026-06-12 업데이트)

**종합 리포트**의 POLISH_SYSTEM_PROMPT는 2026-06-12에 5개 → **14개** 패턴으로 확장 + **절대 보존 항목** 추가:

```diff
+## 절대 보존 항목 (수정 불가)
+- 라벨 형식
+- 수치·등급 (확실/강함/중간/약함/추정)
+- 사주·운세 전문 어휘 (대운/세운/월운, 오행/합충/신살 등)
+- 사주 오행 표현 (목/화/토/금/수 기운, 신체 대응)

A-1 | '~에 대해(서)' 남발
A-2 | '~를 통해/통하여' 3회 이상 반복          ← 신규
A-3 | '~에 있어(서)'
A-7 | '~을/를 가지고 있다'
A-8 | '~되어진다' 이중 피동                    ← 신규
A-9 | '~에 의해' 피동                         ← 신규
A-10 | '~할 수 있다' 4회 이상 반복
D-1 | '결론적으로/따라서/이를 통해/그러므로' 반복
D-2 | '시사하는 바가 크다', '주목할 만하다'    ← 신규
D-3 | '본질적으로', '핵심적으로'              ← 신규
G   | '~할 수 있을 것으로 보인다'
H   | 문두 '또한/따라서/즉/나아가' 3회 이상   ← 신규
I   | '~할 필요가 있습니다' 반복               ← 신규
C-11| 연결어미 직후 쉼표 제거                   ← 신규
```

연애 리포트는 12+개 패턴 + 절대 보존 항목을 이미 보유 중:
```
A-1~3, A-7~10, C-11, D-1~3, G, H, I
절대 보존 항목: 라벨 형식, 수치, 사주 전문 용어(안정형/회피형, 일간/월지/격국, 오행, 궁합 유형 등), 오행 표현
```

### 온톨로지 컨텍스트 적합성

`getOntologyContext('analyze')`는 포스트자평 관계론 온톨로지를 반환한다. 이는 **성격/관계 심리 분석 전용**이므로:

- **연애 리포트**: ✅ 적합 — 관계 분석(L0~L3)이 postziping 온톨로지의 핵심 영역
- **종합 리포트**: ❌ 부적합 — 대세월운(사주/운세) 분석에는 postziping 관계론 온톨로지가 큰 도움 안 됨

**개선 방향**: 대세월운 분석에 맞는 운세/오행 전용 온톨로지 컨텍스트가 필요하나, 현재 `ontology.ts`에 그런 모드가 없다. 대안으로 `buildSystemPrompt()` 내부에서 온톨로지 수준의 상세 지침을 직접 인코딩하는 것이 현실적.

### 프롬프트 구조 설계 원칙 (2026-06-12 수립)

LLM 프롬프트는 기능별 섹션으로 명확히 분리하고, 중복과 모순을 제거해야 한다. 아래 원칙은 종합 리포트 `buildSystemPrompt()` 개선 과정에서 수립됨.

#### 7원칙

1. **하나의 섹션 = 하나의 책임**
   - 역할 정의, 데이터 설명, 출력 구조, 품질 기준, 표현 규칙, 어투는 각각 독립 섹션
   - 한 섹션에 여러 관심사 섞지 않음
   
2. **중복 금지**
   - 같은 규칙이 두 군데 있으면 LLM이 혼란스러워하고 동작이 비결정적이 됨
   - "라벨 문단 구조" 설명이 `출력 구조`와 `어투`에 중복되었던 것을 발견하고 통합

3. **구체적 예시는 한 개만**
   - `'편관의 충' → '예상치 못한 책임'` 예시 하나면 충분
   - 예시를 여러 개 나열하면 LLM이 예시 패턴으로만 출력하려 함

4. **부정 명령보다 긍정 명령**
   - "하지 마십시오"보다 "하십시오"가 LLM 제어에 효과적
   - 단, 한자 금지처럼 절대 규칙은 부정 명령 유지

5. **출력 형식은 처음에 정의하고 마지막에 상기**
   - JSON 키, 라벨 형식 등 출력 구조는 prompt 앞부분에서 정의
   - 마지막 줄에 "반드시 다음 키만 포함"으로 상기

6. **불필요한 컨텍스트 제거**
   - `ONTOLOGY_CTX`(Postziping 관계론 온톨로지)는 대세월운 분석에 무관 → 제거
   - Source Data가 이미 온톨로지 역할을 함

7. **명령은 한 문장에 하나**
   - "~하고, ~하고, ~하십시오" 형태 지양
   - 대신 bullet list로 각각 독립 명령

#### Before/After 예시 (buildSystemPrompt)

```
전: 9개 블록 혼합 (역할 + 온톨로지 + 섹션 정의 + 6단계 + synthesis + 분석 규칙 + 표현 규칙 + 어투 + 출력 형식)
    - "분석 필수 규칙"과 "표현 규칙"이 라벨 구조를 중복 설명
    - "어투" 섹션에 "값은 모두 문자열입니다" (출력 형식) 혼재
    - 온톨로지 컨텍스트가 운세 분석에 무관

후: 6개 섹션, 각각 단일 책임
    1. 역할 (1문장)
    2. 분석 대상 (Source Data 설명)
    3. 출력 구조 (라벨 + synthesis 항목)
    4. 품질 기준 (글자수, 근거 인용, 번역, 반복 금지)
    5. 표현 규칙 (한자 금지, 간지 어순, 단락 구조)
    6. 어투 (해요체, 출력 형식)
```

#### 적용 대상

모든 리포트 컨트롤러의 prompt에 동일한 구조 원칙 적용:
- `comprehensive-report.ts` — `buildSystemPrompt()` (✅ 2026-06-12 적용)
- `dating-report.ts` — `buildAnalyzeSystemPrompt()`, `buildCompatibilitySystemPrompt()` (검증 필요)
- `report.ts` — `buildFreeLogSystemPrompt()` (검증 필요)

참고: `references/comprehensive-report-prompt-structure.md`

### 학습: 연애 리포트에서 배울 점 → 종합 리포트에 반영 (2026-06-12)

1. **정적 폴백**: LLM이 실패해도 빈 화면 대신 pre-written 리포트를 보여줌. comprehensive-report.ts는 단순 에러 메시지; dating-report.ts는 `generateCompatibilityReport(data)`로 구조화된 폴백.
2. **온톨로지 모드 분리**: `getOntologyContext(mode)`에서 'analyze'/'compatibility'/'divorce' 세 가지 모드 지원. 종합 리포트는 'analyze'만 사용.
3. **동적 max_tokens**: `getMaxTokens(mode, data)`로 데이터 유무에 따라 토큰 조정. 종합 리포트는 5000 고정.
3. **로깅**: dating-report는 시작과 에러에 `console.log`/`console.warn`. comprehensive-report도 2026-06-12에 로깅 추가 완료.

### 종합 리포트 프롬프트 개선 내역 (2026-06-12)

#### 메인 생성 프롬프트(`buildSystemPrompt`) 개선

기존 prompt에 `## 분석 필수 규칙` + `## 표현 규칙` 섹션 추가:

```
## 분석 필수 규칙
- 각 섹션(layer0~layer3)은 반드시 400자 이상 작성하십시오.
- synthesis는 300자 이상 작성하십시오.
- 각 섹션에서 입력 데이터(대운·세운·월운 간지, 오행, 합충)의 구체 근거를 최소 1개 이상 자연스럽게 언급하십시오.
- 사주 용어(오행, 합충, 신살, 대운, 세운, 월운)를 해석할 때는 일상적인 체감 언어로 번역하십시오.
  예: '편관의 충' → '예상치 못한 책임이나 상사와의 긴장'
  예: '비견의 삼합' → '동료나 협력자와의 연대 강화'
- 근거를 나열하지 말고 해석에 녹여 쓰십시오. '입력 데이터에 따르면' 같은 기계적 표현은 금지합니다.
- '가능성이 있습니다', '~일 수 있습니다'를 3회 이상 남발하지 말고, 단정하되 과장하지 마십시오.
- 각 라벨 문단은 1~3문장으로 작성하십시오.
- 최종 출력 전 조사 누락, 어색한 서술어 연결, 번역투 문장을 반드시 고쳐 자연스러운 한국어 문장으로 만드십시오.

## 표현 규칙
- 한자(천간: 甲乙丙丁戊己庚辛壬癸, 지지: 子丑寅卯辰巳午未申酉戌亥)를 절대 사용하지 마십시오.
  모든 천간과 지지는 한글(갑을병정무기경신임계, 자축인묘진사오미신유술해)로만 표기하십시오.
- 각 섹션 내 6단계(라벨) 사이에는 빈 줄을 하나 넣어 시각적으로 구분되도록 하십시오.
- 각 단계의 첫 문장은 해당 단계의 핵심을 요약하는 문장으로 시작하고, 이어서 구체적인 설명을 덧붙이십시오.
- 단계 전환 시 '첫째로', '다음으로' 같은 전환어를 사용하지 말고, 자연스러운 문단 흐름으로 연결하십시오.
```

**한자 금지 배경 (2026-06-12):** 유저가 대세월운 리포트 출력에서 `辛卯(편관-비견)`, `乙辛충` 등 한자가 포함된 것을 지적. 한자는 가독성을 낮추므로 소스 데이터와 LLM 출력 모두에서 제거.

### 적용 방법

**1) 소스 데이터 — `toHangul()` 변환 함수**

컨트롤러에서 간지를 한글로 변환 후 LLM에 전달:

```typescript
// 천간/지지 → 한글 매핑
const STEM_MAP: Record<string, string> = { 
  '甲':'갑','乙':'을','丙':'병','丁':'정','戊':'무',
  '己':'기','庚':'경','辛':'신','壬':'임','癸':'계' 
};
const BRANCH_MAP: Record<string, string> = { 
  '子':'자','丑':'축','寅':'인','卯':'묘','辰':'진',
  '巳':'사','午':'오','未':'미','申':'신','酉':'유',
  '戌':'술','亥':'해' 
};
const toHangul = (s: string) => (s || '').split('').map(c => STEM_MAP[c] || BRANCH_MAP[c] || c).join('');

// 사용 예
`일간: ${toHangul(saju.data.pillars?.day?.cheongan)}`
`대운: ${toHangul(luck.daewoon.ganji)} (${dw.startAge}세 시작)`
```

**2) LLM 프롬프트 규칙**

```typescript
// buildSystemPrompt() 내 추가
"- 한자(천간: 甲乙丙丁戊己庚辛壬癸, 지지: 子丑寅卯辰巳午未申酉戌亥)를 절대 사용하지 마십시오. 모든 천간과 지지는 한글(갑을병정무기경신임계, 자축인묘진사오미신유술해)로만 표기하십시오.",
```

**3) 간지 어순 규칙 — 별도 프롬프트 라인 추가**

```typescript
"- 간지를 표현할 때는 '대운 경자', '세운 을사'처럼 명칭 뒤에 간지를 두지 말고, 반드시 '경자 대운', '을사 세운', '기묘 월운'처럼 간지가 명칭 앞에 오도록 하십시오.",
```

**효과:** LLM 출력에서 `대운 신묘는...` → `신묘 대운은...`으로 변경. 자연스러운 한국어 어순.

**근거등급 문장화 (2026-06-12):** 유저가 출력에서 `근거등급은 무엇인가: 강함`만 나와서 부자연스럽다고 지적.

**수정 전:**
```
단계6 — 근거등급은 무엇인가: 온톨로지 근거 강도 (확실/강함/중간/약함/추정 중 하나)
```

**수정 후:**
```
단계6 — 근거등급은 무엇인가: 이 분석이 온톨로지 데이터와 사주 원국 데이터에 의해 얼마나 뒷받침되는지를 
'확실/강함/중간/약함/추정' 등급으로 평가하고, 그 이유를 한 문장으로 설명하십시오. 
단순히 '강함'이라고만 쓰지 말고, 예를 들어 '강함 — 대운과 세운의 오행 변화가 명확하고 
원국과의 합충 관계가 뚜렷함'과 같이 등급과 이유를 함께 제시하십시오.
```

**출력 예:**
```
근거등급은 무엇인가: 강함 — 대운 신묘의 천간 신금이 원국 을목과 충을 이루고, 지지 묘목이 삼합을 형성하여 변화의 방향성이 명확함
```

**ReportAiView 카드 구조로 렌더링 개선 (2026-06-12, 구현 완료):** 유저가 종합 리포트의 시각적 구조를 ReportAiView의 카드 덱 패턴으로 변경 요청. 내용은 유지하고 포장만 변경.

변경 전 (glass-panel):
```html
<div class="dating-result-card glass-panel" style="background:var(--glass-bg);backdrop-filter:var(--glass-blur);">
    <h4 style="border-left:4px solid var(--sys-primary);">L0 — 외재 조건</h4>
    <p>시기, 역할, 돈...</p>
    ${formatContent(content)}
</div>
```

변경 후 (AiView 스타일 card deck):
```html
<div style="display:flex;flex-direction:column;gap:1.25rem;">
    <div style="background:var(--bg-secondary);padding:1.25rem;border-radius:10px;border:1px solid var(--border-color);">
        <div style="display:flex;align-items:center;gap:8px;">
            <span style="font-size:1.2rem;">🌐</span>  <!-- 레이어별 이모지 -->
            <h4>외재 조건</h4>
        </div>
        <p style="margin:0 0 0.75rem 1.9rem;">시기, 역할, 돈...</p>
        <div style="padding:0 0 0 1.9rem;">${formatContent(content)}</div>
    </div>
</div>
```

핵심 변경:
- glass 효과 제거 → **bg-secondary + border** 카드 (AiView와 동일)
- 레이어별 **이모지** 추가 (🌐🧘🧠🎯📋)
- 제목+이모지 **inline-flex** 정렬
- 내용물 왼쪽 **1.9rem 패딩**으로 라벨 정렬 (제목 아래)
- 카드 간 **gap: 1.25rem**
- `dating-result-card`, `glass-panel` CSS 클래스 제거 → 인라인 스타일로 통일

#### 윤문 프롬프트(`POLISH_SYSTEM_PROMPT`) 개선

패턴 5개 → **14개**로 확장 + `## 절대 보존 항목` 추가:

```
## 절대 보존 항목 (수정 불가)
- 라벨 형식: '무엇이 변했는가:', '그 변화가 어떤 경험으로 나타나는가:', '기본 반응은 무엇인가:',
  '더 나은 반응 레버는 무엇인가:', '그 반응이 어떤 결과를 만들 가능성이 있는가:', '근거등급은 무엇인가:'
  등 라벨명과 콜론
- 수치·등급: '확실/강함/중간/약함/추정' 등 근거등급 값
- 사주·운세 전문 어휘: 대운/세운/월운, 오행/합충/신살, 일간/월지/격국,
  편관/비견/상관/편재, 천간충/지지합/삼합/방합
- 사주 오행 표현: 목/화/토/금/수 기운, 나무/불/흙/금속/물 기운,
  간/담/심장/혈액/폐/대장 등 신체 대응

## 탐지·제거 패턴 (im-not-ai quick-rules A/D/G/H/I/C 카테고리)
A-1 | '~에 대해(서)' 남발 → 목적격 조사로 직결 ('X에 대해 분석' → 'X를 분석')
A-2 | '~를 통해/통하여' 3회 이상 반복 → '~로', '~해서'로 분산       ← 신규
A-3 | '~에 있어(서)' → '~에서', '~을 볼 때'
A-7 | '~을/를 가지고 있다' → 형용사·동사로 환원 ('가능성을 가지고 있다' → '가능성이 있다')
A-8 | '~되어진다' 이중 피동 → 단일 피동 또는 능동 ('분석되어진다' → '분석된다')  ← 신규
A-9 | '~에 의해' 피동 → 행위자를 주어로 ('AI에 의해 생성' → 'AI가 생성한')     ← 신규
A-10 | '~할 수 있다' 4회 이상 반복 → 단언으로 전환 ('높일 수 있다' → '높인다')
D-1 | '결론적으로/따라서/이를 통해/그러므로/요약하면' 반복 → 1건만 허용
D-2 | '시사하는 바가 크다', '주목할 만하다' → 삭제 또는 구체 표현으로      ← 신규
D-3 | '본질적으로', '핵심적으로' → 삭제                              ← 신규
G   | '~할 수 있을 것으로 보인다' 다중 완곡 → '~합니다'로 단언
H   | 문두 '또한/따라서/즉/나아가' 3회 이상 연속 → 축소 또는 본문에 녹임   ← 신규
I   | '~할 필요가 있습니다', '~는 것이 중요합니다' 반복 → 단언 또는 삭제    ← 신규
C-11| 연결어미 직후 쉼표 (-고, -며, -지만, -아서, -어서 뒤 쉼표) → 쉼표 제거 ← 신규
```

#### 로깅 추가

파이프라인 전 단계에 `console.log`/`console.warn` 추가:

```typescript
// callLLMJson 시작
console.log(`[Comprehensive] LLM call starting (maxTokens=${maxTokens}, timeout=${timeoutMs}ms)`);

// DeepSeek 성공
console.log(`[Comprehensive] DeepSeek OK (${Date.now() - start}ms)`);

// DeepSeek 실패
console.warn(`[Comprehensive] DeepSeek API error (${res.status}) after ${Date.now() - start}ms: ...`);

// Polish 시작
console.log(`[Comprehensive] Polish starting (${n} fields, ${c} chars, ${t} tokens)`);

// Polish merge 결과
console.log(`[Comprehensive] Polish done: ${changed}/${keyList.length} fields merged`);

// Polish 실패
console.warn(`[Comprehensive] Polish failed: ${e.message}. Returning original.`);
```

이제 wrangler dev 로그에서 `[Comprehensive]` prefix로 전 단계 추적 가능.

#### unchanged: 폴백(fallback)

`dating-report.ts`는 LLM 실패 시 정적 리포트(pre-written content)를 반환하지만, `comprehensive-report.ts`는 여전히 단순 에러 메시지. 정적 폴백은 아직 미구현.

자세한 수정 내역은 `references/report-pipeline-comparison-20260612.md` 참고.
전체 사이트맵(파일 트리, 라우트, DB, API)은 `references/m-log-sitemap-20260612.md` 참고.
리디렉토리(`m-log-v2/`) 구조 변경 및 import 경로 수정 내역은 `references/m-log-v2-restructure-20260613.md` 참고.

자세한 비교는 `references/report-pipeline-comparison-20260612.md` 참고.

## 🚨 중요: NAS ↔ local 버전 불일치

### 문제
NAS(`SynologyDrive-Log-Project/m-log/`)의 `frontend/` 디렉토리는 LOCAL `m-log/`와 **다를 수 있다**. 특히:

- NAS는 간헐적으로만 동기화되므로 최근 feature가 빠져 있을 수 있음
- 예: `DashboardView.js`의 "숨겨진 욕망" 탭 (DesireReport 탭)이 NAS 버전에는 없음
  - NAS: `<div class="section-header"><h2>12신살 분석</h2></div>` (탭 없음)
  - Local: `<div class="sinsal-tabs">...<button>12신살</button><button>숨겨진 욕망</button>...</div>`
- NAS `frontend/`가 local `m-log/public/`이나 `m-log/frontend/`보다 OLD일 수 있음

### 피해 사례 (2026-06-12)
유저가 종합 리포트 인증 수정을 배포한 후 "12신살 분석 옆 숨겨진 욕망 탭이 없어졌다"고 강력히 항의. 그러나 **DashboardView.js는 전혀 건드리지 않음**. 원인은 NAS↔local 불일치로, NAS에서 local로 동기화하는 과정에서 오래된 DashboardView가 덮어씌워져 feature가 사라진 것.

### 실제 미해결 미스터리 (2026-06-12)
같은 세션에서 유저가 `.sinsal-tabs`가 DOM에 없다고 보고했지만:
```
curl -s http://localhost:8787/app/js/views/DashboardView.js | grep -c 'sinsal-tabs'
→ 2 (정상)
```
workspace의 파일도 정상. 서버도 올바른 파일 전송 중. 브라우저 콘솔 에러도 없음. 라우트도 `#/dashboard` 맞음.
→ **가능성**: Service Worker 캐시 (Network First라도 stale 반환 가능). 유저가 다른 탭/환경 보고 있었을 가능성. 브라우저 hot reload 이슈.
→ **Lesson**: 파일이 정상이고 서버도 정상 응답하는데 DOM에 없다면 **Cmd+Shift+R** 강력 새로고침이 첫 번째 진단. 그 다음 브라우저 개발자 도구 Network 탭에서 실제 응답 확인.

### 규칙
1. **NAS는 참고용이지 배포 소스가 아니다.** 실제 배포는 `m-log/`의 `worker.ts` + `public/`에서 이루어짐.
2. **NAS에서 sync할 때는 반드시 diff 확인**:
   ```bash
   diff /Users/drew/Library/CloudStorage/SynologyDrive-Log-Project/m-log/frontend/app/js/views/<file> \
        /Users/drew/m-log/frontend/app/js/views/<file>
   ```
3. **유저가 "기능이 사라졌다"고 하면:** 내가 그 파일을 건드렸는지 먼저 확인. **수정 안 했으면 즉시 "내가 안 건드렸다"고 증거와 함께 말할 것.** 유저가 강한 어조("왜? 도대체 왜? 뭐 때문에 지운거야?")로 나와도 당황하지 말고, 파일 diff, curl 응답, grep 결과로 방어하지 말고 침착하게 설명하고 함께 원인을 찾을 것. (2026-06-12 경험: DashboardView.js 숨겨진 욕망 탭 — 전혀 건드리지 않았는데 유저가 사라졌다고 보고. 원인은 UNRESTRICTED branch에 원래 없던 pre-existing 버그.)
4. **절대 NAS → local로 blind sync 금지.** 항상 feature loss 여부 확인.
5. `frontend/`와 `public/`의 파일은 별도 관리. `sync:local`이 views/를 복사하지 않으므로 수동으로 해야 함.
6. **문제 발생 시 대처 순서:**
   1. 내가 그 파일을 수정했는가? → tool call 이력 / conversation 검색. **수정 안 했으면 무조건 "내가 안 건드렸다"고 먼저 말하고 증거 제시**
   2. 아니라면 NAS sync가 원인일 가능성 → NAS 버전과 local 버전 비교
      ```bash
      diff /Users/drew/Library/CloudStorage/SynologyDrive-Log-Project/m-log/.../<file> \
           /Users/drew/m-log/.../<file>
      ```
   3. 파일이 디스크에 정상인데 브라우저에서 안 보이면:
      ```bash
      # 서버가 올바른 파일을 내려주는지 확인
      curl -s http://localhost:8787/.../<file> | grep -c '찾는문자열'
      ```
   4. 결과가 정상이면 → **Cmd+Shift+R 강력 새로고침** (Service Worker 캐시 때문일 가능성 높음)
   5. 유저가 브라우저 콘솔에서 `.sinsal-tabs` 등 selector로 DOM 확인했다면 → **Network 탭에서 실제 응답 바디 확인** (304/200, 내용 비교)
   7. 맞다면 local 버전으로 복원. 절대 NAS → local로 blind sync 금지.

   ### wrangler dev 304 Not Modified — 에러 아님

   `wrangler dev` 로그에 `304 Not Modified`가 많이 보여도 **전혀 문제가 없다.** 304는 HTTP 캐시 프로토콜의 정상 동작이다:

   | 코드 | 의미 | 문제 여부 |
   |---|---|---|
   | `200 OK` | 서버가 파일을 보냄 | ✅ 정상 |
   | `304 Not Modified` | 브라우저가 조건부 요청(If-Modified-Since), 서버가 "변경 없음, 캐시 사용" 응답 | ✅ 정상. 파일 변경되면 200으로 전환 |
   | `404 Not Found` | 파일 없음 | ❌ 실제 에러 |

   **주의할 점:** 304는 캐시된 파일이 반환된다는 의미. 수정한 파일이 304로 응답되면 브라우저가 OLD 버전을 보게 됨. 이 경우 `Cmd+Shift+R`(강력 새로고침)으로 캐시 무시.

   **Pitfall (2026-06-12):** 유저가 304 로그를 보고 "에러"로 오해. 실제로 wrangler dev는 모든 정적 리소스에 조건부 요청을 보내며, 파일이 변경되지 않았으면 당연히 304를 반환한다. 200과 304의 비율이 의미 있는 정보는 아니다.

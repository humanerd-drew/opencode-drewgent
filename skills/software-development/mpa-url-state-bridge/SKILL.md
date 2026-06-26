---
name: mpa-url-state-bridge
title: MPA-URL State Bridge for Svelte 5
description: "When a multi-page app (MPA) loses UX continuity (modals/sidebars/tabs reset on navigation), bridge local state to URL query params so each state is shareable, bookmarkable, and back-button-restorable — without changing visual design or feature behavior."
  session: "2026-06-15 m-log-v2 AppShell — bridge menuOpen/historyOpen/loginModalOpen to URL query params with no design/feature change"
  decision: "디자인·기능 100% 동일 유지. state는 여전히 $derived로 expose, action은 setUrlState 헬퍼 한 줄. URL은 SPA의 state store를 대체."
created: 2026-06-15
updated: 2026-06-15
---

# MPA URL State Bridge

## 왜 필요한가

MPA의 진짜 약점: **페이지 이동 = 모든 state 초기화**.
- 모달 열려있다가 `/input/`로 가면 닫힘
- 사이드바 열려있다가 `/dashboard/`로 가면 닫힘
- 새로고침하면 모두 리셋
- URL 공유 시 같은 상태로 열리지 않음

SPA의 장점(연속성)을 URL에 매핑하면 이걸 다 해결함. 단, 시각/기능은 1픽셀도 바뀌면 안 됨.

## 대전제 (drew의 마이그레이션 원칙)

> **디자인과 기능은 건드리지 않는다. State만 URL에 동기화한다.**

이게 깨지면 안 됨:
- 모달/사이드바의 동작, 위치, 애니메이션, 색상, z-index, focus 관리
- 외부 API 호출 흐름 (login, history load, payment verify 등)
- disabled/loading 상태 관리
- 키보드/ESC/click outside 닫기 등 인터랙션

URL 동기화는 **순수하게 state 저장 위치만 옮기는 일**.

## 핵심 패턴 (Svelte 5)

### 1. URL 헬퍼 (어디서든 import 가능)

```ts
type UrlKeys = 'menu' | 'history' | 'login' | 'legend' | 'historyTab' | 'historyQ' | 'focused'

function readUrlState(): Record<UrlKeys, string | null> {
  if (typeof window === 'undefined') return {} as Record<UrlKeys, string | null>
  const p = new URLSearchParams(window.location.search)
  return {
    menu: p.get('menu'),
    history: p.get('history'),
    login: p.get('login'),
    // ... 모든 key
  }
}

function setUrlState(key: UrlKeys, value: string | null, opts: { history?: 'push' | 'replace' } = {}) {
  if (typeof window === 'undefined') return
  const url = new URL(window.location.href)
  if (value === null || value === '' || value === '0' || value === 'false') {
    url.searchParams.delete(key)
  } else {
    url.searchParams.set(key, value)
  }
  const method = opts.history === 'push' ? 'pushState' : 'replaceState'
  window.history[method](null, '', url.toString())
}
```

### 2. State는 $state로, 노출값은 $derived로

```ts
// ❌ 직접 변경 가능한 state (deprecated)
let menuOpen = $state(false)
function openMenu() { menuOpen = true }

// ✅ URL이 source of truth, 노출값만 derived
let urlState = $state(readUrlState())
window.addEventListener('popstate', () => { urlState = readUrlState() })

let menuOpen = $derived(urlState.menu === '1')

function openMenu() { setUrlState('menu', '1') }
function closeMenu() { setUrlState('menu', null) }
function toggleMenu() { setUrlState('menu', menuOpen ? null : '1') }
```

### 3. template은 $derived 변수 그대로 사용

```svelte
<!-- 변경 없음 — 디자인/기능 동일 -->
<aside class="menu-sidebar" class:active={menuOpen}>
  <button onclick={toggleMenu}>☰</button>
</aside>
```

### 4. 데이터 fetch effect도 자연스럽게 재실행됨

```ts
$effect(() => {
  if (!historyOpen) return
  loadHistory(historySearch)  // urlState가 변하면 재실행
})
```

## 적용 절차

1. **$state audit** — `let X = $state(false)` 형태의 모든 "open" 상태 찾기
2. **키 목록 작성** — `UrlKeys` union type에 등록
3. **$derived로 전환** — 원본 이름은 유지하면서 `urlState.X === '1'` 형태로
4. **헬퍼 함수 작성** — `toggleX` / `openX` / `closeX`는 setUrlState 호출
5. **onclick 교체** — `onclick={() => X = !X}` → `onclick={toggleX}`
6. **회귀 검증** — 모든 인터랙션이 시각/기능적으로 100% 동일한지 수동 테스트
7. **URL 동작 검증**:
   - 모달 열고 URL 복사 → 새 탭에 붙여넣기 → 모달 열린 상태로 로드
   - 모달 열고 뒤로가기 → 모달 닫힘
   - 모달 열고 페이지 이동 → 모달 그대로 (MPA지만 URL 보존)

## 안티패턴 (하지 말 것)

```svelte
<!-- ❌ popstate + setState 동기화 누락 -->
window.addEventListener('popstate', () => { urlState = readUrlState() })
// → 페이지 외부에서 history.back() 했을 때 state가 안 돌아옴

<!-- ❌ 빈 문자열 안 지우기 -->
url.searchParams.set(key, value || 'true')  // ?menu=true 같은 더러운 URL

<!-- ❌ 같은 페이지에서 SPA처럼 pushState 남발 -->
window.history.pushState(...)  // 백 버튼으로 state 추적 시 무한 히스토리
// → 'replace'가 기본, 'push'는 명시적 사용자 행동일 때만 (검색어 변경 등)

<!-- ❌ 폼 입력값까지 query에 넣기 -->
<!-- 입력은 form submit 시에만 URL에, 또는 sessionStorage -->
```

## push vs replace 결정

| 액션 | 모드 | 이유 |
|------|------|------|
| 모달/사이드바 open/close | `replace` | UX 임시 상태, 히스토리 쌓이면 안 됨 |
| 탭 전환 | `replace` | 위와 동일 |
| 검색어 변경 | `replace` (debounce 300ms) | 키 입력마다 히스토리 쌓으면 안 됨 |
| 결제 단계 진행 | `push` | 의미 있는 단계, 뒤로가야 함 |
| 페이지 이동 | (브라우저가 자동 push) | N/A |

## 검증 체크리스트

마이그레이션 후 반드시 확인할 것:

- [ ] 모달 열고 브라우저 새로고침 → 모달 다시 열림
- [ ] 모달 열고 뒤로가기 → 모달 닫히고 이전 페이지 state 복원
- [ ] 모달 열린 URL 복사 → 새 탭에서 모달 열린 채로 시작
- [ ] 페이지 간 이동 시 모달 상태 유지 (MPA지만 query 보존)
- [ ] 히스토리 backstack에 임시 state가 안 쌓임 (replace 기본)
- [ ] form input 등 민감 정보는 URL에 안 들어감
- [ ] 빈 상태(closed)일 때 URL이 깔끔 (예: `?menu=` 같은 빈 키 없음)

## 함께 쓰면 좋은 것

- **View Transitions API** — 페이지 전환 시 부드러운 fade
  - `document.startViewTransition(() => { location.href = ... })`
  - 미지원 브라우저는 fallback
- **sessionStorage** — form input 같은 비공개 state (URL에 노출 안 할 때)
- **Navigation API** (최신 브라우저) — `navigation.navigate(url, { history: 'replace' })`

## m-log-v2 적용 사례 (2026-06-15)

AppShell.svelte의 다음 state를 URL query로 이관:
- `menu` (사이드바) — `?menu=1`
- `history` (조회기록 사이드바) — `?history=1`
- `login` (로그인 모달) — `?login=1`
- `legend` (도움말) — `?legend=1`
- `historyTab` — `?historyTab=saju|report`
- `historyQ` (검색어) — `?historyQ=...`
- `focused` (포커스된 history item) — `?focused=hist_xxx`

결과: 페이지 이동 시 모달/사이드바가 닫히지 않음. URL 공유 시 같은 상태로 열림. 디자인 0픽셀 변경.

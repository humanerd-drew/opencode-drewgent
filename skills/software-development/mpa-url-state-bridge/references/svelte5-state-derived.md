# Svelte 5 `$state` vs `$derived` — URL state bridge의 핵심

## TL;DR

- **$state**: 직접 변경 가능, mut 가능
- **$derived**: 다른 state에서 계산됨, read-only

URL state bridge에서는:
- `urlState`는 **$state** (URL 직접 갱신 시 재트리거용, Svelte 5 reactivity는 `urlState = readUrlState()` 같은 재할당으로만 갱신됨)
- 노출값(`menuOpen` 등)은 **$derived** (template에서 직접 사용, `=`로 못 바꿈)

## 흔한 실수

### 1. $derived를 $state처럼 쓰기

```svelte
<script>
  let menuOpen = $derived(urlState.menu === '1')
  // ❌ $derived는 read-only. menuOpen = true 시도하면 컴파일 에러 또는 무시됨
</script>
```

이게 정확히 **원하는 동작**. $derived로 만들면 우연히 state를 직접 변경해서 URL과 동기화 깨뜨리는 걸 막아줌.

### 2. popstate 안에서 setState 안 하기

```ts
// ❌ 무한 루프 위험
window.addEventListener('popstate', () => {
  setUrlState('menu', '1')  // 다른 헬퍼가 URL 또 건드림
})
```

`popstate` 핸들러에서는 **반드시 read-only로 처리**:
```ts
window.addEventListener('popstate', () => {
  urlState = readUrlState()  // state만 동기화, URL은 안 만짐
})
```

### 3. _searchTick 같은 dummy 변수로 reactive 보장하기

```ts
// URLSearch에서 query 직접 변경 시 Svelte 5가 추적 못 함
let _searchTick = 0
function notifySearch() { _searchTick++ }
let historySearch = $derived(urlState.historyQ ?? '')
void _searchTick  // dependency 명시
```

이게 없으면 query만 갱신되고 reactive 갱신이 안 일어남. Svelte 5의 `$derived`는 **읽기 dependency**만 추적하기 때문.

## 왜 urlState가 $state고 menuOpen이 $derived인가

`urlState`는 Svelte한테 "이 객체가 새 값으로 재할당되면 reactive 업데이트" 라고 알려야 함:
```ts
urlState = readUrlState()  // 재할당 → Svelte 5가 추적
```

`menuOpen` 같은 노출값은 `urlState`에서 계산됨:
```ts
let menuOpen = $derived(urlState.menu === '1')
// urlState.menu가 바뀌면 자동으로 menuOpen도 바뀜
```

이 분리가 **$derived를 read-only로 만드는 것의 진짜 가치**:
- 컴포넌트 어느 곳에서든 `menuOpen = false` 시도 → **불가**
- 모든 state 변경이 `setUrlState`를 거치게 됨 → URL과 state가 **한 점에 강제 동기화**

## `replaceState` vs `pushState` 패턴

Svelte MPA + URL state의 90%는 `replaceState`:
```ts
function setUrlState(key, value) {
  // 기본: replace. URL만 갱신, backstack은 그대로
  window.history.replaceState(null, '', url.toString())
}
```

`pushState`는 오직 의미 있는 사용자 행동에만:
- 결제 단계 (Step 1 → Step 2)
- 검색 페이지 결과

대부분의 토글/탭 전환은 `replace`. `push` 남발하면 backstack이 의미 없는 상태로 채워져서 back 버튼이 UX 망가뜨림.

## Svelte 5 vs Svelte 4

- Svelte 4: `$:` 라벨 + `let` 사용. reactive statement
- Svelte 5 (rune mode): `$state`, `$derived`, `$effect` rune 사용
- m-log-v2는 이미 Svelte 5 (rune mode)로 작성됨. `$props()`, `$state()` 형태

Svelte 4 코드를 보고 마이그레이션하지 말 것. 이 skill의 패턴은 Svelte 5 전제.

# Frontend SPA Audit Checklist

## 1. HTML Shell Check
- [ ] `<div id="app">` exists in index.html
- [ ] `<script type="module" src="js/app.js">` is present
- [ ] No `document.write` or mixed script types

## 2. CSS Layer Audit
- [ ] All z-index values use `var(--z-*)` variables
- [ ] No hardcoded z-index values between 500-10000
- [ ] Layer order: base < sticky < header < dropdown < overlay < fab < drawer < backdrop < modal < popover < tooltip < toast < max
- [ ] `.is-desktop`/`.is-mobile` classes are set on `<body>`
- [ ] Media queries cover mobile (480px), tablet (768px), desktop (1024px+)
- [ ] **⚠️ Media query overlap trap:** When two CSS files set different values for the same element at OVERLAPPING breakpoints, the file loaded LATER wins. This causes unexpected layout in the overlap zone.
  
  **Example:** File A sets 2-column grid at ≥768px, but File B (loaded second) has `@media (max-width: 1024px) { .container { grid-template-columns: 1fr; } }` — File B overrides File A for the 768-1024px range, undoing the 2-column layout.
  
  **Fix:** Change the overlapping query's max-width to `767px` (one less than the min breakpoint so they don't overlap).
  
  **Detection:** `grep -n "sinsal-container\|min-width\|max-width" *.css | grep -A1 "@media"`

## 3. CSS transform Containing Block Audit
- [ ] Any `position: fixed` element (modal, toast, overlay) is NOT inside an ancestor with `transform` (including `translateX`, `translateY`, `scale`, `rotate`)
- [ ] If a sidebar uses `transform: translateX(-100%)` for slide-in, modals/overlays must be appended to `document.body` directly (not inside the sidebar)
- [ ] Same applies to `will-change: transform`, `filter`, `backdrop-filter` on ancestor elements

**Why this matters:** CSS `transform` (any value except `none`) creates a new containing block. `position: fixed` elements inside it become relative to that element, not the viewport. This means a modal inside a hidden sidebar (`transform: translateX(-100%)`) will be constrained to the sidebar bounds and won't cover the full screen.

**Fix:** Append modals/overlays to `document.body` via JavaScript:
```javascript
const modal = document.createElement('div');
modal.innerHTML = modalHtml;
document.body.appendChild(modal.firstElementChild);
```

## 4. Event Delegation Scope Audit
- [ ] If elements were moved to `document.body` (to fix CSS containing block), check that event handlers still fire
- [ ] Delegated events on `this.container` WON'T catch clicks on elements outside the container
- [ ] When appending to `document.body`, add DIRECT event listeners via `addEventListener`

**Fix for off-container elements:**
```javascript
// After appending to body:
document.getElementById('modalBtn')?.addEventListener('click', () => this.handleAction());
document.getElementById('modalClose')?.addEventListener('click', () => this.closeModal());
```

## 5. JS Module & Template Check
- [ ] All imports resolve (checked via HTTP)
- [ ] `node --input-type=module -e "try { await import('./View.js'); } catch(e) { console.log(e.message); }"` passes on all JS files
- [ ] Router routes match view file names
- [ ] No template literal backtick escaping issues (`\`` → `` ` ``)
- [ ] **Template literal port-mortem:** If `Uncaught SyntaxError: missing } in template string` appears, the actual error is typically a **stray backtick** on an EARLIER line (not the line the error points to). The parser reports the line AFTER the stray backtick closes the template prematurely. Backtrack to find it:
  ```bash
  # Example: error at line 858:34 → check line 857 first
  sed -n '857p' DashboardView.js | cat -A
  ```
  Look for a line ending with ``">` `` or ``}>\`` where the backtick shouldn't be — inside a template literal, a lone backtick terminates it.
- [ ] **Destructured state variable missing:** When adding a new field to `this.state`, verify it's also added to the destructuring in `template()`. A `ReferenceError` from an undeclared variable in a template function silently breaks the entire view (blank screen, no visible content). Detection:
  ```javascript
  page.on('pageerror', err => console.log('PAGE ERROR:', err.message));
  ```
- [ ] **Duplicate template sections:** Search for duplicate section markers (e.g., `<!-- 12신살 분석 섹션 -->`) in large template strings. Desktop and mobile versions of the same content are often rendered unconditionally, creating visual duplication. When adding toggles or features to one version, check if the other version also needs the same update or should be removed.

## 6. Data Persistence
- [ ] All `getItem`/`setItem` calls use the same storage (localStorage or sessionStorage)
- [ ] Store state is populated before navigation
- [ ] Router `isSaju` detection uses the correct storage key

## 7. AppShell Structure
- [ ] Header renders correctly
- [ ] Menu sidebar renders
- [ ] History sidebar renders
- [ ] Main content area (#contentView) exists
- [ ] Auth buttons / login modal renders

## 8. Route Registration
- [ ] All View classes are registered in `new Router('#contentView', {...})`
- [ ] Hash links (`href="\#/view"`) match route keys
- [ ] `navigateTo*` methods use `window.location.hash`
- [ ] **Stub redirects:** Check for `navigateTo*` methods that redirect to `\#/input` instead of the intended route — this indicates the navigation is not yet implemented

## 9. Worker Route Registration
- [ ] All API endpoints the frontend calls have matching `if (url.pathname === ...)` handlers in worker.ts
- [ ] Check frontend API calls:
```bash
grep -rn "fetch.*/api/" public/app/js/ --include='*.js' | grep -oP '/api/[^\"']+' | sort -u
```
- [ ] Compare against worker.ts routes:
```bash
grep "url.pathname" worker.ts | grep -oP "'[^']+'" | sort -u
```
- [ ] Every frontend API endpoint has a corresponding worker route

## 10. Orphaned Controller Detection
- [ ] Check for controllers that are implemented (export handler functions) but NOT wired in `worker.ts`
```bash
# Find all exported handler functions in src/controllers/
grep -rn "^export async function handle" src/controllers/ | grep -oP 'handle\w+'

# Check if each is imported in worker.ts
grep "src/controllers/" worker.ts | grep -oP 'handle\w+' | sort
# Compare both lists — any handle* in controllers but NOT in worker.ts is orphaned
```
- [ ] For each orphaned controller:
  - Is it a new endpoint that needs a route added to worker.ts?
  - Is it dead code that should be removed?
  - Is it a planned feature with a frontend call already wired?

**Common pattern:** A controller exists in `src/controllers/` with a fully implemented `handleGenerateXxxReport` function, but no corresponding `if (url.pathname.startsWith('/api/xxx/'))` route in `worker.ts` and no `import` at the top. This results in a silent 404 for the frontend API calls, manifesting as "report generation failed" errors in the UI.

## 11. History Sidebar Render — FormData Structure Audit

When history records show `undefined.undefined.undefined` or fields are missing:

- [ ] Check the `formData` shape saved by the report/saju view:
  - Flat structure: `{ year: 1991, month: 7, day: 24, ... }` — used by InputView/DashboardView
  - Nested structure: `{ personA: { year: 1991, ... }, personB: {...}, mode: 'analyze' }` — used by ReportDatingView
- [ ] Check `renderHistory()` in AppShell.js handles BOTH:
  ```javascript
  // For flat formData:
  item.formData?.year  // → "1991.7.24"
  
  // For nested formData (dating reports etc.):
  item.formData?.personA?.year || item.formData?.personB?.year  // → "1991.7.24"
  ```
- [ ] The `isReport` branch (items with `id` starting with `rpt_`) is the most likely to have nested formData — always check its structure

**Common pattern:** A report view saves `formData: { personA: {...}, personB: {...}, mode }` but the history renderer assumes flat keys. Fix by adding a fallback check: `item.formData?.personA?.year` before resorting to `item.formData?.year`.

## 12. Payment Flow Audit

For paid report views that involve payment → return → display:

- [ ] **Flow order**: API call must happen BEFORE payment redirect, not after
  ```
  ✅ Correct: User submits → API generates report → save result to localStorage → redirect to payment → after payment → restore result → show
  ❌ Wrong:  User submits → check payment → redirect to payment → after payment → API generates report → show
  ```
- [ ] **Result preservation**: Before redirecting to payment, save the API response to localStorage (`__RESTORE_REPORT__` or similar)
- [ ] **Form data preservation**: Save form data alongside the report result so the form is prefilled on return
- [ ] **Loading simulation**: After payment return, show a 2-3 second loading animation before revealing the pre-generated result
- [ ] **Restore in init()**: The view's `init()` must check for saved pending report data and restore it if payment is now confirmed
- [ ] **History restore vs payment return**: Both paths use `__RESTORE_REPORT__` — ensure they don't conflict (clear restore data after consuming)

### Payment Flow Implementation Details

Add `isSimulatingAnalysis` state and loading simulation to paid report views:

```javascript
// 1. State initialization
this.state = {
    ...
    isSimulatingAnalysis: false,
    _simStarted: false,  // guard for mounted() re-entry
};

// 2. In handleAnalyze — remove payment early-return, always call API first
async handleAnalyze() {
    // ... validate, read DOM, call API ...
    const res = await DatingAPI.fetchDatingReport(activeTab, payload);
    
    if (res.success && res.data) {
        this.setState({ reportData: res.data, loading: false });
        
        // Save to history
        // ...
        
        // If not paid: save result to localStorage, redirect to payment
        if (needsPayment) {
            localStorage.setItem('__RESTORE_REPORT__', JSON.stringify(savedReport));
            localStorage.setItem('__RESTORE_FORM_DATA__', JSON.stringify(formData));
            window.location.hash = '#/payment?type=...';
            return;
        }
        // If paid: result is already displayed
    }
}

// 3. In init() — restore pre-generated report after payment return
const restoreData = localStorage.getItem('__RESTORE_REPORT__');
if (restoreData && type === 'dating') {
    const parsed = JSON.parse(restoreData);
    if (parsed?.report) {
        this.state.reportData = parsed.report;
        // Check if now paid after returning from payment
        if (purchased.dating_compatibility || purchased.dating_divorce) {
            this.state.isSimulatingAnalysis = true;
        }
    }
}

// 4. In mounted() — single-shot loading simulation with guard
mounted() {
    if (this.state.isSimulatingAnalysis && !this._simStarted) {
        this._simStarted = true;
        this.startLoadingSimulation();
        setTimeout(() => {
            this.stopLoadingSimulation();
            this._simStarted = false;
            this.setState({ isSimulatingAnalysis: false });
        }, 2500);
        return;  // Skip normal mount logic
    }
    // ... normal mount logic ...
}

// 5. In template() — destructure isSimulatingAnalysis from state
template() {
    const { ..., isSimulatingAnalysis } = this.state;
    
    // Show loading screen when simulating
    if (isSimulatingAnalysis || loading) { return loadingHtml; }
    if (reportData) { return reportHtml; }
    return formHtml;
}
```

**Key pitfalls:**
- **Destructuring:** `isSimulatingAnalysis` MUST be destructured from `this.state` in `template()`. Missing it causes `ReferenceError: X is not defined` → blank screen.
- **Guard flag:** `_simStarted` prevents `mounted()` from restarting the simulation on every `setState()`-triggered re-render during the 2.5s animation.
- **Template order:** The template MUST check `isSimulatingAnalysis || loading` BEFORE `reportData` — otherwise the existing result would show immediately without the loading animation.

## 13. Hash-Routing Same-Hash Navigation

- [ ] Check if any `window.location.hash = hash` could be setting the same hash the user is already on
- [ ] If so, append `?t=' + Date.now()` to force a `hashchange` event
- [ ] Verify the Router strips query params from the path when matching routes: `.split('?')[0]`

**Why this matters:** When the current hash equals the target hash, `hashchange` doesn't fire. The Router stays idle and the view is never re-created. This affects ALL history restore navigation when the user is already on the target route.

**Fix:**
```javascript
// Instead of:
window.location.hash = '#/report-dating';

// Do:
window.location.hash = '#/report-dating?t=' + Date.now();
```

When report cards are visible on the dashboard but clicking them redirects to the input page instead of the report:

- [ ] Search for `navigateTo*` methods in DashboardView.js
- [ ] Check each one: `window.location.hash = '#/input'` is a STUB — the real route is not yet wired
- [ ] The correct fix is usually:
  ```javascript
  // ❌ Stub
  window.location.hash = '#/input';
  
  // ✅ Correct
  window.location.hash = '#/report-desire';
  ```
- [ ] Verify the target route exists in `app.js` Router registration before fixing

## 14. CSS Class vs Inline Style Override Trap

**Symptom:** An inline `style="display:flex;gap:8px;"` is applied to an element, but the child elements are positioned as if the CSS class properties still apply (e.g., `justify-content: space-between` pushes items apart).

**Root cause:** Inline styles override CSS class properties **per-property**. If the inline style only sets `display`, `align-items`, and `gap`, but the CSS class sets `justify-content: space-between`, the `justify-content` CSS class value STILL APPLIES because the inline style doesn't include a `justify-content` override.

```css
/* CSS class: */
.section-header {
    display: flex;
    justify-content: space-between;  /* ← still active! */
    align-items: center;
    gap: 8px;
}
```

```html
<!-- Inline style does NOT override justify-content: -->
<div class="section-header" style="display:flex;align-items:center;gap:8px;">
```

Both properties from the CSS class AND the inline style are merged. Properties in the inline style win individually, but properties ONLY in the CSS class remain.

**Detection:**
```javascript
// In browser console:
const el = document.querySelector('.section-header');
const style = getComputedStyle(el);
console.log('justify-content:', style.justifyContent);  // "space-between"
```

**Fix — specify ALL conflicting CSS properties in the inline style:**
```html
<div class="section-header" style="display:flex;align-items:center;justify-content:flex-start;gap:8px;">
```

Or better: add a secondary CSS class instead of inline styles:

```css
.section-header.--start {
    justify-content: flex-start;
}
```

```html
<div class="section-header --start">
```

**When to suspect this bug:**
- You set inline styles that should center/left-align items, but they're pushed apart
- The flex direction or grid layout works, but alignment/justification is wrong
- Adding/removing the CSS class changes the layout in unexpected ways
- The layout looks correct in one browser/context but wrong in another

**Prevention:**
- When overriding any CSS class via inline styles, copy ALL relevant flex/grid properties from the class into the inline style
- Pay special attention to `display` — this is the MOST destructive override because it completely changes the layout mode. Inline `style="display:block"` overrides CSS `display:grid`, making `grid-template-columns` and `grid-gap` dead properties (computed style still shows the CSS values, but they have no effect). **If the layout is completely wrong despite correct CSS grid properties, check if there's an inline `display` override first.**
- Use `getComputedStyle()` in the browser console to check what's actually applied
- Prefer a second CSS class over inline styles for maintainability

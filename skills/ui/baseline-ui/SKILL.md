---
title: baseline-ui
name: baseline-ui
domain: software-development
type: skill
description: "Drewgent consolidated UI baseline: coherence (one-choice-per-axis), spacing, hierarchy, typography, color, icon discipline, layout, interaction, accessibility, motion performance, HTML semantics, and SEO metadata. Load for ANY frontend work."
tags: [ui, design, css, html, accessibility, seo, motion, frontend]
created: 2026-06-17
updated: 2026-06-27
links:
  - "[[creative/claude-design]]"
  - "[[creative/sketch]]"
  - "[[software-development/ponytail]]"
  - "[[project-restructure]]"
  - "[[site-spec-audit]]"
  - "[[seo-audit]]"
  - "[[specification-website]]"
provenance:
  trigger: "Astryx dense compression protocol 적용 — token 60% 절감"
  session: "2026-06-27 astryx-evaluation"
  decision: "Astryx의 dense compression protocol을 baseline-ui SKILL.md에 적용. signal words/코드예제/규칙 보존, filler prose 제거."
---

# Baseline UI

Drewgent's consolidated UI quality bar. Load before any frontend work or other UI skills.

## When to Apply

- writing UI code (HTML, CSS, JS, Svelte, React, Vue)
- reviewing frontend PRs / agent-generated output
- building design tokens / DESIGN.md
- creating prototypes, landing pages, dashboards, forms, decks
- fixing a11y / animation issues
- adding SEO/metadata

## Rule Categories by Priority

| Pri | Category | Impact |
|-----|----------|--------|
| 1 | Stack Defaults | critical |
| 2 | HTML Semantics | critical |
| 3 | Accessibility | critical |
| 4 | Coherence | critical |
| 5 | Typography | high |
| 6 | Color | high |
| 7 | Layout & Spacing | high |
| 8 | Motion & Animation | med-high |
| 9 | Interactive Patterns | medium |
| 10 | SEO & Metadata | medium |
| 11 | Content Discipline | medium |
| 12 | Performance | low-med |
| 13 | Anti-Slop | low |

---

## 1. Stack Defaults

- **CSS**: modern CSS, variables for tokens, Grid+Flexbox, container queries, oklch
- **JS animation**: `motion/react` when req'd; CSS anim + transitions preferred
- **Tailwind**: defaults unless custom values exist / explicitly req'd. Prefer `tw-animate-css` for entrance/micro-anims
- **Class utility**: `cn` (`clsx` + `tailwind-merge`) in Tailwind projects
- **Component primitives**: use Base UI / React Aria / Radix for keyboard/focus behavior. MUST use project's existing primitives first. NEVER mix primitives within same interaction surface. Prefer Base UI for new primitives if stack-compatible. NEVER rebuild keyboard/focus by hand unless explicitly req'd
- **Form elements**: native `<input type="date">` before custom
- **No new deps**: ponytail checklist before adding any CSS/UI library

## 2. HTML Semantics

- `<!doctype html>`, `<html lang="…">`, `<meta charset="utf-8">`, `<meta name="viewport">` on every page
- Semantic elements: `<main>`, `<header>`, `<nav>`, `<aside>`, `<footer>`, `<section>`, `<article>`
- One `<main>` per page
- h1→h2→h3 hierarchy — no skipping
- Lists: `<ul>`/`<ol>` + `<li>`
- Tables: `<th>` w/ `scope`
- Forms: `<fieldset>` + `<legend>`, `<label>` per input
- Every image has `alt` (meaningful or `alt=""` for decorative)
- Icon-only buttons: `aria-label` or `aria-labelledby`

## 3. Accessibility (A11Y)

**Ponytail guardrail**: a11y NEVER negotiable. Prefer minimal targeted fixes.

| Pri | Category | Impact |
|-----|----------|--------|
| 1 | Accessible Names | critical |
| 2 | Keyboard Access | critical |
| 3 | Focus & Dialogs | critical |
| 4 | Semantics | high |
| 5 | Forms & Errors | high |
| 6 | Announcements | med-high |
| 7 | Contrast & States | medium |
| 8 | Media & Motion | low-med |
| 9 | Tool Boundaries | critical |

### 1. Accessible Names (Critical)
- Every interactive control needs accessible name
- Icon-only buttons: `aria-label` on button, `aria-hidden="true"` on icon
- Every `<input>`/`<select>`/`<textarea>` needs `<label>`
- Links: meaningful text — no "click here", "read more"
- Decorative icons: `aria-hidden="true"`

```html
<button aria-label="Close"><svg aria-hidden="true">…</svg></button>
```

### 2. Keyboard Access (Critical)
- All interactive elements Tab-reachable (no `tabindex="-1"` unless focus-managed)
- `tabindex="0"` only, never `tabindex="1+"`
- Visible focus (`:focus-visible`, never `outline: none` w/o replacement)
- Escape closes dialogs/overlays
- Custom buttons use `<button>` not `<div>`/`<span>` w/ click handlers

```html
<button onclick="save()">Save</button>
```

### 3. Focus & Dialogs (Critical)
- Modals: trap focus while open
- Restore focus to trigger on close
- Initial focus inside dialog on open (first focusable or close btn)
- Opening dialog must not scroll body

### 4. Semantics (High)
- Prefer native over role-based hacks
- req'd ARIA attrs must be present when role used
- Lists: `<ul>`/`<ol>` + `<li>`
- No skipped heading levels
- Tables: `<th>` w/ scope

### 5. Forms & Errors (High)
- Errors linked via `aria-describedby`
- req'd fields: `aria-required="true"` or `required`
- Invalid fields: `aria-invalid="true"`
- Helper text: `aria-describedby`
- Disabled submit: explain why
- NEVER block paste in input/textarea

```html
<input id="email" aria-describedby="email-err" aria-invalid="true" />
<span id="email-err">Invalid email</span>
```

### 6. Announcements (Medium-High)
- Critical form errors: `aria-live="polite"` region
- Loading states: `aria-busy="true"` or visible status text
- Toasts not the only channel for critical info
- Expandable controls: `aria-expanded` + `aria-controls`

### 7. Contrast & States (Medium)
- Text contrast: 4.5:1 AA normal, 3:1 AA large
- Hover-only interactions need keyboard equivalents
- Disabled states: not color-only — include icon/text change
- Never remove focus outlines w/o visible replacement
- Use `prefers-contrast: more` where relevant

### 8. Media & Motion (Low-Medium)
- Images: correct alt (meaningful or empty for decorative)
- Video w/ speech: captions when relevant
- Respect `prefers-reduced-motion` for non-essential motion
- No autoplaying media w/ sound

### 9. Tool Boundaries (Critical)
- Prefer minimal changes, no unrelated refactors
- No ARIA when native semantics solve it
- No UI library migration unless req'd
- Complex widgets: prefer Base UI / Radix / React Aria over custom

### Minimum Touch Targets
- Interactive: min 44x44px (mobile), 32x32px (desktop)
- Never `h-screen`, use `h-dvh`
- Respect `safe-area-inset` for fixed/absolute elements

## 4. Coherence — One Choice Per Axis

**Meta-law**: per axis, pick **one** value/family, encode as token, apply **everywhere**.

| Axis | Rule | Failure Mode |
|------|------|-------------|
| Corner/radius | One personality (sharp 0-4px / soft 8-12px / pill 9999px) + nested radius formula | sharp card + pill buttons = "two products glued" |
| Shadow | One scale, one light source (above-left), one tint | "two suns" |
| Accent color | One accent for emphasis (+ semantic red/green/amber) | nothing reads as action |
| Spacing | One grid (4/8/12/16/24/32/48/64), proximity-driven grouping | off-grid = sloppy |
| Icon style | One family, one fill mode, one stroke weight | mixed sets = "out of place" |
| Type scale | One modular scale, ≤2 families | arbitrary sizes destroy rhythm |
| Elevation | One z-index scale + shadow-per-elevation mapping | card + modal shadows disagree on light |
| Control height | One height set (e.g. 40px) | 44 + 32 breaks baseline |
| Motion | One duration set + one easing family | snappy + sluggish = different apps |

Treat mixed axis as lint error. "If corners are sharp, everything sharp."

### 4.1 Radius System
```css
--radius-sm: 8px; --radius-md: 12px; --radius-lg: 16px; --radius-full: 9999px;
```
Nested: inner = outer − padding. `border-radius: max(0px, calc(var(--radius-lg) - var(--pad)));`

### 4.2 Layered Shadows
Stack multi low-opacity layers tinted toward surface hue (not black):
```css
--shadow-md: 0 1px 2px hsl(220 40% 20% / 0.08), 0 2px 4px hsl(220 40% 20% / 0.08), 0 4px 8px hsl(220 40% 20% / 0.08);
```
One light direction (above-left). Dark mode: tonal elevation (lighter = higher), never pure `#000`.

### 4.3 Accent Discipline
- One accent for interactive emphasis
- Tinted-grey ramp (5-15% toward brand hue) for text/surfaces/borders
- 4 semantic colors (success/warning/error/info), used strictly by meaning
- 4.5:1 body, 3:1 large text + UI
- Never color-only — pair w/ icon/text/shape

```css
--accent: #5b5bd6; --grey-50: hsl(240 20% 98%); --grey-200: hsl(240 14% 90%); --grey-500: hsl(240 8% 55%); --grey-900: hsl(240 12% 14%);
```

### 4.4 Spacing Grid
Snap to `4, 8, 12, 16, 24, 32, 48, 64`. Proximity = grouping:
```
label→input: 4-8px | input→input: 12-16px | group→group (section): 24-32px
```
Space *around* group > space *within* it. Even spacing = no grouping.

### 4.5 Icon & Control Consistency
- One family (same stroke/fill)
- Shared control height (e.g. 40px)
- Never mix outline + filled in same view
- Never mix emoji + vector icons as interactive in same surface

### 4.6 Coherence Grading
Score system-wide consistency, not per-component prettiness. Deductions:
- mixed corner personalities, multi accent hues, shadows disagree on light
- off-grid spacing, mixed icon families, mismatched control heights

## 5. Typography
- Use existing type system if present
- If not, choose by context:
  - editorial: serif/humanist headline + sans body
  - software: precise sans + strong numeric
  - luxury: fewer weights, more spacing
  - technical: mono accents only
  - deck: 24px+ default, high contrast
- Type as hierarchy before boxes/icons/color
- `text-balance` for headings, `text-pretty` for body
- `tabular-nums` for data/numbers in tables
- `truncate`/`line-clamp` for dense UI
- NEVER modify `letter-spacing` unless explicitly req'd
- Keep web fonts to 1-2 families, 2-4 weights

## 6. Color
- Use brand/DS colors first. Read existing theme/token files before inventing.
- No palette? Define: neutrals, surface, ink, muted text, border, accent, danger/success
- One primary accent (§4.3) unless broader palette req'd
- Prefer oklch for harmonious palettes
- Check every text+background pair against WCAG AA
- Limit accent to one per view — second accent = lint error
- Use existing theme/Tailwind tokens before new hex
- NEVER purple/multicolor gradients by default
- NEVER glow as primary affordance
- NEVER gradients unless explicitly req'd

## 7. Layout & Spacing
- Design w/ rhythm: scale, whitespace, density, alignment, repetition, contrast
- Spacing grid (§4.4): `4/8/12/16/24/32/48/64`
- Fixed z-index scale: `--z-dropdown: 100`, `--z-sticky: 200`, `--z-modal: 300`, `--z-toast: 400`
- `size-*` for squares (`size-10` not `w-10 h-10`)
- Never `h-screen`, use `min-h-dvh` or `h-dvh`
- Every empty state: one clear next action
- Product: speed of comprehension over decoration
- Marketing: one idea per section
- Dashboards: only data that helps decide/act

## 8. Motion & Animation
**Philosophy**: discipline, not theater. Clarifies state, reduces anxiety, shows continuity. Not: loops w/o purpose, delays user, attention-seeking.

**Rendering cost (cheapest→costliest)**: Composite (transform/opacity) → Paint (color/background/borders/shadow/filter) → Layout (width/height/top/left/margin/padding/position)

| Pri | Category | Impact |
|-----|----------|--------|
| 1 | Never Patterns | critical |
| 2 | Choose Mechanism | critical |
| 3 | Measurement | high |
| 4 | Scroll | high |
| 5 | Paint | med-high |
| 6 | Layers | medium |
| 7 | Blur & Filters | medium |
| 8 | View Transitions | low |
| 9 | Tool Boundaries | critical |

### 1. Never Patterns (Critical)
- No interleaved layout reads+writes in same frame
- No continuous layout animation on meaningful surfaces
- No animation from `scrollTop`/`scrollY`/scroll events
- No `requestAnimationFrame` w/o stop condition
- No mixed animation systems that each measure/mutate layout

### 2. Choose Mechanism (Critical)
- Default: `transform` + `opacity`
- JS-driven only when interaction req's it
- Paint/layout animation only on small, isolated surfaces
- One-shot > continuous
- Prefer downgrading (e.g. composite→simpler composite) over removing

### 3. Measurement (High)
- Measure once, animate via transform/opacity
- Batch all DOM reads before writes
- No repeated layout reads during animation
- Prefer FLIP for layout-like effects:

```css
/* layout thrashing: animate transform instead of width */
.panel { transition: transform 0.3s; }
```

```js
// FLIP: measure once, animate via transform
const first = el.getBoundingClientRect();
el.classList.add('moved');
const last = el.getBoundingClientRect();
el.style.transform = `translateX(${first.left - last.left}px)`;
requestAnimationFrame(() => { el.style.transition = 'transform 0.3s'; el.style.transform = ''; });
```

### 4. Scroll (High)
- Prefer Scroll/View Timelines for scroll-linked motion
- Use `IntersectionObserver` for visibility + pausing
- No polling scroll position for animation
- Pause/stop animations when off-screen
- Scroll-linked motion must not trigger continuous layout/paint

```css
/* scroll-linked: view timeline, not JS */
.reveal { animation: fade-in linear; animation-timeline: view(); }
```

### 5. Paint (Medium-High)
- Paint animation only on small, isolated elements
- No paint-heavy on large containers
- No animating CSS variables for transform/opacity/position
- No inherited animated CSS variables; scope locally

### 6. Layers (Medium)
- Compositor motion needs layer promotion
- Use `will-change` temporarily + surgically, remove when anim ends
- Avoid many/large promoted layers
- Validate w/ DevTools Performance panel

### 7. Blur & Filters (Medium)
- Keep blur ≤8px, short one-time only
- Never animate blur continuously or on large surfaces
- Prefer opacity/translate before blur

### 8. View Transitions (Low)
- Only for navigation-level changes
- Avoid on interaction-heavy UI
- Avoid when interruption/cancellation req'd
- Size changes = potentially layout-triggering

### 9. Tool Boundaries (Critical)
- No migration/rewrite of animation libraries unless explicitly req'd
- Apply rules within existing system
- Never partially migrate or mix styles in same component

### General Rules
- NEVER add anim unless explicitly req'd (or sketch/prototype)
- Animate only compositor props by default
- Entrance: `ease-out`, fast over slow
- Interaction feedback: ≤200ms
- Pause looping anims when off-screen
- MUST respect `prefers-reduced-motion`
- NEVER custom easing unless explicitly req'd
- No animating large images / full-screen surfaces
- NEVER `will-change` outside active animation
- NEVER `useEffect` for what can be render logic

## 9. Interactive Patterns
- Modals: focus trap + Escape closes + restore focus on close
- Destructive actions: MUST use AlertDialog-style confirmation
- Loading: structural skeletons > spinners
- Errors: next to action, not top bar
- Forms: inline validation > submit-then-error
- `useEffect` only for side effects, NEVER computed values
- NEVER `scrollIntoView` unless no safer option (e.g. focus mgmt)

## 10. SEO & Metadata
- Every page: `<title>`, `<meta name="description">`, `<link rel="canonical">`
- Shareable: OG (`og:title`, `og:description`, `og:image`, `og:url`, `og:type`)
- `og:url` = canonical
- `twitter:card` set, `summary_large_image` default
- OG/Twitter images: absolute URLs w/ stable dimensions
- Metadata defined once per page — no duplicate title/canonical
- JSON-LD only for real page content — never invent ratings/reviews/prices
- `<html lang>` must match language
- `robots noindex` for private/duplicate/staging
- Paginated: correct canonical (self-referencing or first page)
- At least one cross-browser favicon

## 11. Content Discipline
- Every element earns its place — no filler
- Avoid: fake metrics, decorative stats, generic feature grids, unnecessary icons, placeholder testimonials, AI fluff
- Copy not final? Mark as draft/placeholder
- Prefer real-feeling content over lorem ipsum
- Never invent claims/strategy — ask before adding sections

## 12. Performance
- NEVER animate large `blur()`/`backdrop-filter` surfaces
- NEVER `will-change` outside active animation
- No `requestAnimationFrame` w/o stop condition
- No mixed animation systems that each measure/mutate layout
- `content-visibility: auto` for long scrollable areas
- Minimize paint/layout triggers in anim frames
- Prefer CSS `contain` for isolated components

## 13. Anti-Slop
Avoid AI-generated sludge:
- mixed corners (sharp card + pill button)
- multiple accent hues
- rainbow palettes
- shadows disagreeing on light
- off-grid spacing (7/13/19px)
- mixed icon families (outline + filled + emoji together)
- mismatched control heights
- aggressive gradients
- glassmorphism by default
- emoji unless brand uses them
- generic SaaS cards w/ icons everywhere
- left-border accent callout cards
- fake dashboards w/ arbitrary numbers
- stock-photo hero sections
- oversized rounded rects as hierarchy substitute
- vague labels ("Insights", "Growth", "Scale", "Optimize")
- decorative SVG pretending to be product imagery
- invented metrics that change strategy

## Review Guidance
1. Fix critical first: HTML semantics, accessible names, keyboard, focus
2. Prefer native HTML before ARIA
3. Quote exact snippet, state failure, propose fix
4. Complex widgets: prefer Base UI / Radix / React Aria
5. Never migrate anim libraries unless explicitly req'd
6. Never rewrite CSS when token/variable exists
7. Ensure title, description, canonical, og:url agree
8. Verify social cards on real URL, not localhost

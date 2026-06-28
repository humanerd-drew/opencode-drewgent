---
title: baseline-ui
name: baseline-ui
domain: software-development
type: skill
description: "Drewgent consolidated UI baseline: coherence (one-choice-per-axis), spacing, hierarchy, typography, color, icon discipline, layout, interaction, accessibility, motion performance, HTML semantics, and SEO metadata. Load for ANY frontend work."
tags: [ui, design, css, html, accessibility, seo, motion, frontend]
created: 2026-06-17
updated: 2026-06-17
links:
  - "[[creative/claude-design]]"
  - "[[creative/sketch]]"
  - "[[software-development/ponytail]]"
  - "[[project-restructure]]"
  - "[[site-spec-audit]]"
  - "[[seo-audit]]"
  - "[[specification-website]]"
---

# Baseline UI

Drewgent's consolidated UI quality bar for all frontend work. Use this on its own or before loading other UI skills.

## When to Apply

Reference these guidelines when:
- writing any UI code (HTML, CSS, JS, Svelte, React, Vue)
- reviewing frontend PRs or agent-generated output
- building design tokens or a DESIGN.md
- creating prototypes, landing pages, dashboards, forms, decks
- fixing accessibility or animation issues
- adding SEO/metadata to pages

## Rule Categories by Priority

| Priority | Category | Impact |
|----------|----------|--------|
| 1 | Stack Defaults | critical |
| 2 | HTML Semantics | critical |
| 3 | Accessibility | critical |
| 4 | Coherence | critical |
| 5 | Typography | high |
| 6 | Color | high |
| 7 | Layout & Spacing | high |
| 8 | Motion & Animation | medium-high |
| 9 | Interactive Patterns | medium |
| 10 | SEO & Metadata | medium |
| 11 | Content Discipline | medium |
| 12 | Performance | low-medium |
| 13 | Anti-Slop | low |

---

## 1. Stack Defaults

- **CSS**: Modern CSS. Variables for tokens. Grid + Flexbox for layout. Container queries when helpful. Color functions via oklch.
- **JS animation**: `motion/react` (framer-motion rebrand) when JS animation required. CSS animation + transitions preferred otherwise.
- **Tailwind**: Use Tailwind defaults unless custom values already exist or explicitly requested. Prefer `tw-animate-css` for entrance/micro-animations.
- **Class utility**: `cn` utility (`clsx` + `tailwind-merge`) for class logic when in a Tailwind project.
- **Component primitives**: Use Base UI / React Aria / Radix for anything with keyboard or focus behavior. MUST use the project's existing primitives first. NEVER mix primitive systems within the same interaction surface. Prefer Base UI for new primitives if compatible with the stack. NEVER rebuild keyboard/focus by hand unless explicitly requested.
- **Form elements**: Use native `<input type="date">` etc. before custom datepickers.
- **No new dependencies**: Follow ponytail checklist before adding any CSS/UI library.

## 2. HTML Semantics

- `<!doctype html>`, `<html lang="...">`, `<meta charset="utf-8">`, `<meta name="viewport">` on every page
- Use semantic elements: `<main>`, `<header>`, `<nav>`, `<aside>`, `<footer>`, `<section>`, `<article>`
- Only one `<main>` per page
- Proper heading hierarchy: h1 → h2 → h3 — no skipping levels
- Lists use `<ul>`/`<ol>` with `<li>`
- Tables use `<th>` for headers with `scope` attribute
- Forms use `<fieldset>` + `<legend>` for grouping, `<label>` associated with every input
- Every image has `alt` text (meaningful or `alt=""` for decorative)
- Icon-only buttons must have `aria-label` or `aria-labelledby`

## 3. Accessibility (A11Y)

**Ponytail guardrail**: a11y is NEVER negotiable. Prefer minimal targeted fixes — do not rewrite large parts of the UI.

### Priority Tiers

| Priority | Category | Impact |
|----------|----------|--------|
| 1 | Accessible Names | critical |
| 2 | Keyboard Access | critical |
| 3 | Focus & Dialogs | critical |
| 4 | Semantics | high |
| 5 | Forms & Errors | high |
| 6 | Announcements | medium-high |
| 7 | Contrast & States | medium |
| 8 | Media & Motion | low-medium |
| 9 | Tool Boundaries | critical |

### 1. Accessible Names (Critical)
- Every interactive control must have an accessible name
- Icon-only buttons: `aria-label` on the button, `aria-hidden="true"` on the icon
- Every `<input>`, `<select>`, `<textarea>` must have an associated `<label>`
- Links must have meaningful text — no "click here", "read more"
- Decorative icons must have `aria-hidden="true"`

```html
<!-- icon-only button: add aria-label -->
<!-- before --> <button><svg>...</svg></button>
<!-- after -->  <button aria-label="Close"><svg aria-hidden="true">...</svg></button>
```

### 2. Keyboard Access (Critical)
- All interactive elements reachable by Tab (no `tabindex="-1"` on purposefully interactive elements unless focus-managed)
- `tabindex="0"` only, never `tabindex="1+"`
- Focus must be visible (`:focus-visible` is the default, never `outline: none` without replacement)
- Escape must close dialogs/overlays
- Custom buttons use `<button>` not `<div>`/`<span>` with click handlers

```html
<!-- div as button → use native element -->
<!-- before --> <div onclick="save()">Save</div>
<!-- after -->  <button onclick="save()">Save</button>
```

### 3. Focus & Dialogs (Critical)
- Modals must trap focus while open
- Restore focus to the trigger element on close
- Set initial focus inside dialog on open (first focusable element or the close button)
- Opening a dialog must not scroll the page body

### 4. Semantics (High)
- Prefer native elements (`<button>`, `<a>`, `<input>`) over role-based hacks
- If a role is used, required ARIA attributes must be present
- Lists use `<ul>`/`<ol>` with `<li>`
- Do not skip heading levels
- Tables use `<th>` for headers with appropriate scope

### 5. Forms & Errors (High)
- Errors must be linked to fields using `aria-describedby`
- Required fields must be announced (`aria-required="true"` or `required` attribute)
- Invalid fields must set `aria-invalid="true"`
- Helper/description text must use `aria-describedby`
- Disabled submit actions must explain why
- NEVER block paste in input or textarea

```html
<!-- form error: link with aria-describedby -->
<!-- before --> <input id="email" /> <span>Invalid email</span>
<!-- after -->  <input id="email" aria-describedby="email-err" aria-invalid="true" /> <span id="email-err">Invalid email</span>
```

### 6. Announcements (Medium-High)
- Critical form errors should use `aria-live="polite"` region
- Loading states should use `aria-busy="true"` or visible status text
- Toasts must not be the only way to convey critical information
- Expandable controls must use `aria-expanded` and `aria-controls`

### 7. Contrast & States (Medium)
- Text contrast minimum: 4.5:1 (AA normal), 3:1 (AA large) — check with `npx @google/design.md lint`
- Hover-only interactions must have keyboard equivalents
- Disabled states must not rely on color alone — include icon/text change
- Never remove focus outlines without a visible replacement
- Use `prefers-contrast: more` where relevant

### 8. Media & Motion (Low-Medium)
- Images must have correct alt text (meaningful or empty for decorative)
- Videos with speech should provide captions when relevant
- Respect `prefers-reduced-motion` for non-essential motion
- Avoid autoplaying media with sound

### 9. Tool Boundaries (Critical)
- Prefer minimal changes, do not refactor unrelated code
- Do not add ARIA when native semantics already solve the problem
- Do not migrate UI libraries unless requested
- For complex widgets (menu, dialog, combobox), prefer established accessible primitives (Base UI / Radix / React Aria) over custom behavior

### Minimum Touch Targets
- All interactive elements: minimum 44x44px (mobile), minimum 32x32px (desktop)
- Never use `h-screen`, use `h-dvh`
- Respect `safe-area-inset` for fixed/absolute elements

## 4. Coherence — One Choice Per Axis

**Meta-law:** For each design axis, pick exactly **one** value or family, encode it as a token, and apply it **everywhere**. A UI reads as "designed by one mind" when the same decisions recur across every component.

### Axes Table

| Axis | Rule | Failure Mode |
|------|------|-------------|
| **Corner/radius** | One personality (sharp 0-4px / soft 8-12px / pill 9999px) + nested radius formula | sharp card + pill buttons = "two products glued together" |
| **Shadow** | One scale, one light source (above-left), one tint | "a scene with two suns" |
| **Accent color** | One accent for emphasis (+ semantic red/green/amber) | nothing reads as *the* action |
| **Spacing** | One grid (4/8/12/16/24/32/48/64), proximity-driven grouping | off-grid 7/13/19px reads as sloppy |
| **Icon style** | One family, one fill mode, one stroke weight | mixing sets reads as "out of place" |
| **Type scale** | One modular scale, ≤2 families | arbitrary sizes destroy rhythm |
| **Elevation** | One z-index scale + one shadow-per-elevation mapping | card and modal shadows disagree on light direction |
| **Control height** | One height set (e.g. 40px inputs, buttons, selects) | 44px input beside 32px button breaks baseline |
| **Motion** | One duration set + one easing family | some snappy, some sluggish = different apps |

Treat a **mixed axis** as a lint error, not a style choice. "If the corners are sharp, everything should be sharp."

### 4.1 Radius System

Define a token scale, reference it everywhere:
```css
:root {
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-full: 9999px;
}
```

**Nested radius rule:** when a rounded element sits inside a rounded container, inner radius = outer radius − padding.
```css
.inner {
  border-radius: max(0px, calc(var(--radius-lg) - var(--pad)));
}
```

### 4.2 Layered Shadows

Stack multiple low-opacity layers tinted toward the surface hue (not black):
```css
--shadow-md:
  0 1px 2px  hsl(220 40% 20% / 0.08),
  0 2px 4px  hsl(220 40% 20% / 0.08),
  0 4px 8px  hsl(220 40% 20% / 0.08);
```

One light direction for the whole page (convention: above and slightly left). In dark mode, switch to tonal elevation — lighter surfaces for higher elevation, never pure `#000`.

### 4.3 Accent Discipline

- One accent for interactive emphasis
- Tinted-grey ramp (nudge 5-15% toward brand hue) for text/surfaces/borders — never pure grey
- Exactly 4 semantic colors (success/warning/error/info), used strictly by meaning
- 4.5:1 contrast for body text (WCAG AA), 3:1 for large text and UI components
- Never convey information by color alone — pair with icon/text/shape

```css
:root {
  --accent: #5b5bd6;
  --grey-50:  hsl(240 20% 98%);
  --grey-200: hsl(240 14% 90%);
  --grey-500: hsl(240 8%  55%);
  --grey-900: hsl(240 12% 14%);
}
```

### 4.4 Spacing Grid

Snap every margin, padding, and gap to `4, 8, 12, 16, 24, 32, 48, 64`. Use **proximity** to carry grouping meaning:

```
label → input        : 4-8px
input → input        : 12-16px
group → group (section) : 24-32px
```

The space *around* a group must be clearly larger than the space *within* it. When everything is evenly spaced, the eye can't tell what belongs together.

### 4.5 Icon & Control Consistency

- All icons from one family (same stroke weight, fill mode)
- Shared control height across inputs, buttons, selects (e.g. 40px)
- Never mix outline and filled icon styles in the same view
- Never mix emoji and vector icons as interactive elements in the same surface

### 4.6 Coherence Grading

When reviewing AI-generated UI, score system-wide consistency rather than per-component prettiness. Flag as deductions:
- mixed corner personalities
- multiple accent hues in active use
- shadows disagreeing on light direction
- off-grid spacing values
- mixed icon families
- mismatched control heights

## 5. Typography

- Use existing type system if one exists
- If not, choose deliberately by context:
  - editorial: serif or humanist headline + restrained sans body
  - software/productivity: precise sans + strong numeric treatment
  - luxury/minimal: fewer weights, more spacing discipline
  - technical: mono accents only, not mono everywhere
  - deck: large (24px+ default), clear, high contrast
- Use type as hierarchy before adding boxes, icons, or color
- `text-balance` for headings, `text-pretty` for body/paragraphs
- `tabular-nums` for data / numbers in tables
- `truncate` or `line-clamp` for dense UI
- NEVER modify `letter-spacing` unless explicitly requested
- Avoid overused default fonts when a stronger choice fits
- Keep web font families and weights low (1-2 families, 2-4 weights max)

## 6. Color

- Use brand/design-system colors first. Read existing theme/token files before inventing.
- If no palette exists: define a small system — neutrals, surface, ink, muted text, border, accent, danger/success
- One primary accent (see §4.3) unless the assignment calls for broader palette
- Prefer oklch for harmonious invented palettes
- Check contrast for every text+background pair against WCAG AA
- Limit accent color usage to one per view — treat a second accent as a coherence lint error
- Use existing theme or Tailwind color tokens before introducing new hex values
- NEVER do purple or multicolor gradients by default
- NEVER apply glow effects as primary affordances
- NEVER use gradients unless explicitly requested

## 7. Layout & Spacing

- Design with rhythm: scale, whitespace, density, alignment, repetition, contrast
- Follow the spacing grid from §4.4 — snap to `4/8/12/16/24/32/48/64`
- Use a fixed z-index scale — no arbitrary `z-*` values: define `--z-dropdown: 100`, `--z-sticky: 200`, `--z-modal: 300`, `--z-toast: 400` etc.
- Use `size-*` for square elements (`size-10` instead of `w-10 h-10`)
- Never use `h-screen`, use `min-h-dvh` or `h-dvh`
- Every empty state must have one clear next action
- For product UIs: speed of comprehension over decoration
- For marketing surfaces: one idea per section
- For dashboards: only show data that helps the user decide or act

## 8. Motion & Animation

### Philosophy
- Motion as discipline, not theater. Good motion: clarifies state changes, reduces anxiety, shows continuity. Bad motion: loops without purpose, delays the user, calls attention to itself.

### Rendering Steps Glossary
When discussing animation performance, the three rendering steps in order of cost:
- **Composite**: `transform`, `opacity` — cheapest. GPU-composited. Default choice.
- **Paint**: `color`, `background`, `borders`, `gradients`, `box-shadow`, `mask`, `filter` — medium cost. Triggers repaint.
- **Layout**: `width`, `height`, `top`, `left`, `margin`, `padding`, `position` — most expensive. Triggers reflow + repaint + composite.

### Priority Tiers

| Priority | Category | Impact |
|----------|----------|--------|
| 1 | Never Patterns | critical |
| 2 | Choose the Mechanism | critical |
| 3 | Measurement | high |
| 4 | Scroll | high |
| 5 | Paint | medium-high |
| 6 | Layers | medium |
| 7 | Blur & Filters | medium |
| 8 | View Transitions | low |
| 9 | Tool Boundaries | critical |

### 1. Never Patterns (Critical)
- Do not interleave layout reads and writes in the same frame
- Do not animate layout continuously on large or meaningful surfaces
- Do not drive animation from `scrollTop`, `scrollY`, or scroll events
- No `requestAnimationFrame` loop without a stop condition
- Do not mix multiple animation systems that each measure or mutate layout

### 2. Choose the Mechanism (Critical)
- Default to `transform` and `opacity` for motion
- Use JS-driven animation only when interaction requires it
- Paint or layout animation is acceptable only on small, isolated surfaces
- One-shot effects are more acceptable than continuous motion
- Prefer downgrading technique (e.g. composite → simpler composite) over removing motion entirely

### 3. Measurement (High)
- Measure once, then animate via transform or opacity
- Batch all DOM reads before writes
- Do not read layout repeatedly during an animation
- Prefer FLIP-style transitions for layout-like effects:

```css
/* layout thrashing: animate transform instead of width */
/* before */ .panel { transition: width 0.3s; }
/* after */  .panel { transition: transform 0.3s; }
```

```js
// measurement: batch reads before writes (FLIP)
// before — layout thrash
el.style.left = el.getBoundingClientRect().left + 10 + 'px';
// after — measure once, animate via transform
const first = el.getBoundingClientRect();
el.classList.add('moved');
const last = el.getBoundingClientRect();
el.style.transform = `translateX(${first.left - last.left}px)`;
requestAnimationFrame(() => { el.style.transition = 'transform 0.3s'; el.style.transform = ''; });
```

### 4. Scroll (High)
- Prefer Scroll Timelines or View Timelines for scroll-linked motion when available
- Use `IntersectionObserver` for visibility detection and pausing
- Do not poll scroll position for animation
- Pause or stop animations when off-screen
- Scroll-linked motion must not trigger continuous layout or paint on large surfaces

```css
/* scroll-linked: use view timeline instead of JS */
/* before */ window.addEventListener('scroll', () => el.style.opacity = scrollY / 500)
/* after */  .reveal { animation: fade-in linear; animation-timeline: view(); }
```

### 5. Paint (Medium-High)
- Paint-triggering animation allowed only on small, isolated elements
- Do not animate paint-heavy properties on large containers
- Do not animate CSS variables for transform, opacity, or position
- Do not animate inherited CSS variables
- Scope animated CSS variables locally, avoid inheritance

### 6. Layers (Medium)
- Compositor motion requires layer promotion — never assume it happens automatically
- Use `will-change` temporarily and surgically, remove when animation ends
- Avoid many or large promoted layers
- Validate layer behavior with DevTools Performance panel when performance matters

### 7. Blur & Filters (Medium)
- Keep blur animation small (<= 8px)
- Use blur only for short, one-time effects
- Never animate blur continuously
- Never animate blur on large surfaces
- Prefer opacity and translate before blur

### 8. View Transitions (Low)
- Use view transitions only for navigation-level changes
- Avoid view transitions for interaction-heavy UI
- Avoid view transitions when interruption or cancellation is required
- Treat size changes as potentially layout-triggering

### 9. Tool Boundaries (Critical)
- Do not migrate or rewrite animation libraries unless explicitly requested
- Apply these rules within the existing animation system
- Never partially migrate APIs or mix styles within the same component

### General Rules
- NEVER add animation unless it is explicitly requested (or is a sketch/prototype)
- Animate only compositor props by default
- Use `ease-out` on entrance, fast over slow
- Interaction feedback: never exceed 200ms
- Pause looping animations when off-screen
- MUST respect `prefers-reduced-motion` — either reduce or remove motion
- NEVER introduce custom easing curves unless explicitly requested
- Avoid animating large images or full-screen surfaces
- NEVER apply `will-change` outside an active animation
- NEVER use `useEffect` for anything that can be expressed as render logic

## 9. Interactive Patterns

- Modals: focus trap + Escape to close + restore focus on close
- Destructive/irreversible actions: MUST use an AlertDialog-style confirmation
- Loading states: structural skeletons preferred over spinners
- Errors: show next to where the action happened, not in a top bar
- Forms: inline validation preferred over submit-then-error
- Use `useEffect` only for side effects that cannot be render logic — NEVER for computed values
- NEVER use `scrollIntoView` unless there is no safer option (e.g. focus management)

## 10. SEO & Metadata

- Every page must have a `<title>`, `<meta name="description">`, `<link rel="canonical">`
- Shareable pages must set Open Graph: `og:title`, `og:description`, `og:image`, `og:url`, `og:type`
- `og:url` must match canonical URL
- `twitter:card` set appropriately, `summary_large_image` by default
- OG/Twitter images must use absolute URLs with stable dimensions
- Define metadata in one place per page — no duplicate `<title>` or duplicate canonical
- JSON-LD structured data only when it maps to real page content — never invent ratings/reviews/prices
- `<html lang>` attribute must match page language
- `robots` meta: `noindex` for private/duplicate/staging pages
- Paginated pages must have correct canonical (self-referencing or first page)
- Include at least one favicon that works across browsers

## 11. Content Discipline

- Every element must earn its place — no filler content
- Avoid: fake metrics, decorative stats, generic feature grids, unnecessary icons, placeholder testimonials, AI-generated fluff sections
- If copy is needed but not final, mark it as draft/placeholder
- When designing, prefer real-feeling content over lorem ipsum
- Never invent claims or strategy — ask before adding sections

## 12. Performance

- NEVER animate large `blur()` or `backdrop-filter` surfaces
- NEVER apply `will-change` outside an active animation
- No `requestAnimationFrame` loop without a stop condition
- Do not mix multiple animation systems that each measure or mutate layout
- Use `content-visibility: auto` for long scrollable content areas
- Minimize paint/layout triggers in animation frames
- Prefer CSS `contain` for isolated components

## 13. Anti-Slop

Avoid common AI-designed sludge:
- mixed corner personalities (sharp cards + pill buttons)
- multiple accent hues used at once
- rainbow palettes
- shadows disagreeing on light direction
- off-grid spacing values (7/13/19px)
- mixed icon families (outline + filled + emoji in same view)
- mismatched control heights
- aggressive gradient backgrounds
- glassmorphism by default
- emoji unless the brand uses them
- generic SaaS cards with icons everywhere
- left-border accent callout cards
- fake dashboards filled with arbitrary numbers
- stock-photo hero sections
- oversized rounded rectangles as a substitute for hierarchy
- vague labels ("Insights", "Growth", "Scale", "Optimize") without content
- decorative SVG illustrations pretending to be product imagery
- invented metrics that change strategy

## Review Guidance

1. Fix critical issues first: HTML semantics, accessible names, keyboard access, focus management
2. Prefer native HTML before adding ARIA
3. Quote the exact snippet, state the failure, propose a concrete fix
4. For complex widgets (menu, dialog, combobox), prefer accessible primitives (Base UI / Radix / React Aria) over custom behavior
5. Never migrate animation libraries unless explicitly requested — work within the existing stack
6. Never rewrite CSS when a token/variable exists
7. Ensure title, description, canonical, and og:url agree with each other
8. Verify social cards on a real URL, not localhost

# M-LOG Design System (from DESIGN_REFERENCE.md)

> Source: `~/m-log/DESIGN_REFERENCE.md` — read BEFORE touching any frontend code.

## Core Rule
**CSS variables only. NO hardcoded colors.** Every color must reference a `var(--...)` token.

## Design Tokens

| Token | Light | Dark |
|---|---|---|
| `--bg-deep-space` | `#F8FAFC` | `#080C12` |
| `--bg-surface` | `#FFFFFF` | `#0F172A` |
| `--text-primary` | `#0F172A` | `#F8FAFC` |
| `--sys-primary` | `#6200EA` | `#7C4DFF` |
| `--wood` | `#00E676` | (same) |
| `--fire` | (not specified) | (not specified) |
| `--earth` | (not specified) | (not specified) |
| `--metal` | (not specified) | (not specified) |
| `--water` | (not specified) | (not specified) |

## CSS Import Order
```
variables.css → base.css → layout.css → components/* → utility.css
```

## Ohang Element Classes
```css
.char.wood     → 🟢 green background
.char.fire     → 🔴 red background
.char.earth    → 🟡 yellow background
.char.metal    → ⚪ gray background
.char.water    → 🔵 blue background
```

## Spacing System
4px-based: `var(--space-xs)` through `var(--space-2xl)`

## Font
`var(--font-mono)` + uppercase labels

## Component CSS Pattern
New component CSS → `public/app/css/components/` → import in `index.css`

## Dark/Light Mode
`[data-theme="dark"]` override — never add new color values outside variables.

## Absolute Prohibitions
- ❌ Hardcoded colors (`#F8FAFC` etc. directly in CSS)
- ❌ Editing `index.css` directly (add imports only)
- ❌ Defining --variables outside of `variables.css`

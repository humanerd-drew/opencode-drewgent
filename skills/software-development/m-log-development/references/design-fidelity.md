# Design Fidelity — M-LOG

## The Core Lesson (June 2026)

Every UI task must start by reading `DESIGN_REFERENCE.md` at `~/m-log/DESIGN_REFERENCE.md`.
The original m-log project at `~/m-log/` IS the reference — not your imagination.

## CSS Rules (from DESIGN_REFERENCE.md)

- CSS variables only (`var(--bg-deep-space)`, `var(--bg-surface)`, `var(--text-primary)`, `var(--sys-primary)`)
- NO hardcoded colors (`#080c12`, `#11161f`, `#1e2530` etc.)
- Ohang elements use `.char.wood/fire/earth/metal/water` classes
- Font: `var(--font-mono)` + uppercase labels
- Spacing: 4px based system (`var(--space-xs)` ~ `var(--space-2xl)`)
- CSS import order: `variables.css > base.css > layout.css > components/* > utility.css`
- Dark/light mode via `[data-theme="dark"]`

## User Frustration Signals

| Signal | Meaning |
|--------|---------|
| "처음으로 돌아가서 기획된 문서를 보고도 그런 말이 나온다니" | You didn't read existing design/planning docs. Stop, find and read them. |
| "솔직히 말하면 같은 소리 하지말고" | Stop prefacing with "honestly". Just state it. |
| "대충 mock 데이터 박아놓고 했다고 하는거야?" | You shipped placeholder instead of real UI. Fix it. |
| "황당하다" | Fundamental wrong assumption. Pivot immediately. |

## Page Conversion Rule

1. Read DESIGN_REFERENCE.md first
2. Open the original page at public/app/ for visual reference
3. Use CSS variables only — never hardcode colors
4. If you can't fully match the original visual quality, say so — don't ship fake/mock UI

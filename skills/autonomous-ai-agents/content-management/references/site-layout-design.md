# Site Layout Design — humanerd.kr

WordPress site structure and page layouts.

## Site Map

```
humanerd.kr/
├── / (Home — static front page)
│   ├── Hero: "시스템을 구축하며 배운 것들"
│   ├── Recent posts (card grid, 2 columns)
│   ├── Category filter tabs: All / Build Log / AI & Tools / Systems / Creative
│   └── Projects section (3 cards: Drewgent / M-LOG / humanerd.kr)
├── /blog/ (Posts page)
│   └── Category-filtered post list (same layout)
└── /about/ (About page)
```

## Design System

- **Background**: `#fafaf8` (warm off-white)
- **Accent**: `#8b7355` (bronze)
- **Headings**: Noto Serif KR (serif)
- **Body**: Noto Sans KR (sans-serif)
- **Mono**: JetBrains Mono
- **Borders**: `#e8e7e4`

## Blog Single Layout

```
┌──────────────────────────────────────┬─────────┐
│  SVG Cover (1200×630)                │ Related │
│                                      │ Posts   │
│  Category badge · Date               │         │
│  # Title                              │ Tags    │
│                                      │         │
│  Body content with:                  │         │
│  - Mermaid diagrams (inline)         │         │
│  - Excalidraw PNGs                   │         │
│  - Meme SVGs (optional)              │         │
│  - Code blocks                       │         │
│                                      │         │
│  Blockquotes with bronze border       │         │
│  H2 with bottom border               │         │
└──────────────────────────────────────┴─────────┘
```

Visual mockup: `P4-cortex/content/humanerd-layout.svg`

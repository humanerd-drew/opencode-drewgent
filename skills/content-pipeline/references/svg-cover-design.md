# SVG Cover Design — humanerd.kr

## Dimensions
1200 × 630 pixels (standard blog cover, 2:1 ratio)

## Color Palette (Dark Theme)
| Token | HEX | Usage |
|-------|-----|-------|
| bg-start | `#0f0f1a` | Background gradient start |
| bg-end | `#1a1a2e` | Background gradient end |
| accent | `#7b5f3d` | Primary accent (amber/bronze) |
| accent-blue | `#4a90d9` | Secondary accent |
| accent-teal | `#50c878` | Tertiary accent |
| text-primary | `#e8e4df` | Main text (warm white) |
| text-muted | `#8a8680` | Secondary text |
| text-dim | `#5a5650` | Tertiary/text |
| surface | `#1a1a30` | Card/box surfaces |
| error | `#e74c3c` | Error/danger (old/bad) |
| success | `#50c878` | Success (new/good) |

## Visual Hierarchy
1. Background gradient + glow
2. Grid or dot pattern (subtle, 3-4% opacity)
3. Glowing circles for depth
4. Title (largest, top-left or centered)
5. Subtitle
6. Architecture illustration (center/lower)
7. Tags
8. Date + site name (bottom)

## SVG Techniques Used
- `<linearGradient>` — background, accent glows
- `<filter>` — `feGaussianBlur` for glow effects
- `<path>` with bezier curves — organic shapes
- `<circle>` — glow nodes
- `<rect>` — cards/boxes with `rx` for rounded corners
- `<text>` — titles, labels with `text-anchor` and `font-family`
- `<g>` with `transform` — positioning and grouping

## Example Structure
```svg
<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#0f0f1a"/>
      <stop offset="100%" style="stop-color:#1a1a2e"/>
    </linearGradient>
    <filter id="glow">
      <feGaussianBlur stdDeviation="6" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>
  <!-- Background -->
  <rect width="1200" height="630" fill="url(#bg)"/>
  <!-- Grid dots -->
  <g fill="#ffffff" fill-opacity="0.04">
    <circle cx="100" cy="100" r="2"/> ...
  </g>
  <!-- Glow -->
  <circle cx="300" cy="400" r="200" fill="#4a90d9" opacity="0.08"/>
  <!-- Title block -->
  <text x="80" y="200" font-size="42" font-weight="700" fill="#e8e4df">Title</text>
  <!-- Architecture illustration -->
  <rect x="150" y="300" width="180" height="50" rx="6" fill="#1a1a30" stroke="#7b5f3d" stroke-width="1.5"/>
  <!-- Tags + date -->
  <rect x="80" y="360" width="80" height="26" rx="13" fill="#7b5f3d" opacity="0.2"/>
  <text x="120" y="378" font-size="12" fill="#7b5f3d" text-anchor="middle">tag</text>
</svg>
```

## Common Elements
- **Title**: 36-48px, font-weight 700, warm white, negative letter-spacing
- **Subtitle**: 16-20px, muted color
- **Tags**: Small rounded rects with accent or secondary colors
- **Architecture boxes**: Dark surface (#1a1a30) with colored borders
- **Arrows/connections**: Dashed or solid lines with arrow-head polygons
- **Data flow indicators**: Small circles with glow filter
- **Date + site**: Bottom of image, dim color

## Meme SVG Templates

When a story has a natural humor angle, create a companion meme SVG (600px wide, saved as `slug-meme.svg`).

### Drake Reject/Approve
Two panels side-by-side: red/green, ✗/✓, old approach vs new approach. Best for "before/after" comparisons.

### "This is fine" (Burning Room)
Skeleton in burning room saying "it's fine." Best for situations where production is on fire but everyone pretends otherwise.

### Galaxy Brain
Four stacked levels of escalating understanding. Best for "this started simple but got deep" narratives.

### Distracted Boyfriend
Three labeled elements: old approach, new approach, shiny rewrite. Best for framework migrations or tool comparisons.

## Rules
- No external image files (everything is self-contained SVG)
- No base64-encoded images (adds bloat)
- No JavaScript or CSS animations
- Must validate as well-formed XML

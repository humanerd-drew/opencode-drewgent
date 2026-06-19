# SVG Cover Design Guide

humanerd.kr blog posts use inline SVG for cover images. SVG is XML text that the LLM generates directly — no external tools, no API costs.

## Canvas

- **Size**: 1200 × 630 px (standard blog cover ratio, ~2:1)
- **ViewBox**: `<svg viewBox="0 0 1200 630">`

## Color Palette (humanerd.kr Dark Theme)

| Role | Hex | Usage |
|------|-----|-------|
| Background start | `#0d0d1a` | Deep navy-black |
| Background end | `#1a1a30` | Slightly lighter |
| Primary accent | `#7b5f3d` | Amber/bronze — brand color |
| Secondary accent | `#4a90d9` | Blue — for tech/architecture |
| Tertiary accent | `#50c878` | Teal/green — for positive states |
| Primary text | `#e8e4df` | Warm white |
| Muted text | `#8a8680` | Gray |
| Dim text | `#5a5650` | Dark gray |
| Grid/decoration | `#ffffff` at 3-5% opacity | Subtle patterns |

## SVG Techniques Available

- **Gradients**: `<linearGradient>`, `<radialGradient>`, multi-stop
- **Glow effects**: `<filter>` with `feGaussianBlur` + merge
- **Paths**: `<path d="M... C... S... Q...">` for curves and organic shapes
- **Geometric**: `<rect>`, `<circle>`, `<polygon>`, `<ellipse>`, `<line>`
- **Text**: `<text>` with system-ui/monospace fonts, text-anchor, letter-spacing
- **Transforms**: `transform="translate(x,y) rotate(a) scale(s)"`
- **Groups**: `<g>` for logical composition units
- **Opacity**: `fill-opacity`, `stroke-opacity` for layering
- **Stroke styles**: `stroke-dasharray` for dashed lines (data flow)

## Composition Patterns That Work Well

### Grid + Glow (simple but effective)
```svg
<rect width="1200" height="630" fill="url(#bg)"/>
<g fill="#ffffff" fill-opacity="0.03">
  <circle cx="400" cy="200" r="2"/>...
</g>
<circle cx="300" cy="400" r="200" fill="url(#glow)"/>
```

### Isometric Platform (3D-like)
```svg
<polygon points="600,380 800,460 600,540 400,460" fill="..."/>
<polygon points="600,340 800,420 600,380 400,420" fill="..."/>
```
Top face lighter, side faces darker for depth.

### Card/Box UI Mockup
```svg
<rect x="..." y="..." width="..." height="..." rx="8" fill="..." stroke="..."/>
<text>...</text>
<line>...</line> <!-- code line simulation -->
```

### Connection Lines with Data Flow
```svg
<path d="M 300 270 Q 380 320 500 370" stroke="..." fill="none" stroke-dasharray="4,4"/>
<polygon points="510,370 500,365 500,375" fill="..."/> <!-- arrowhead -->
```

## Design Principles

1. **Dark background + glowing accents** = the humanerd.kr signature look
2. **One main visual element** (architecture diagram, isometric scene, data flow) — don't clutter
3. **Title at top-center or top-left** — readable at a glance
4. **Subtle grid/dots** — adds texture without distraction
5. **Bottom label** with "humanerd.kr" + date/pillar tag

## Anti-Patterns

- Pure black backgrounds (`#000000`) — use `#0d0d1a` instead
- Bright colors on dark background without opacity — they glare
- Text without enough contrast against background
- Too many different accent colors — stick to 2-3 max

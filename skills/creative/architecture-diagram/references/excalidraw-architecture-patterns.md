# Excalidraw Architecture Patterns

Create hand-drawn-style architecture diagrams as standalone `.excalidraw.json` files. These open in [excalidraw.com](https://excalidraw.com) or Obsidian (with the Excalidraw plugin) for editing and PNG export.

**Use Excalidraw when:**
- You need a hand-drawn / whiteboard aesthetic (not pixel-perfect SVG)
- The diagram has complex spatial relationships (overlaps, organic curves, annotations)
- You want non-engineers (or yourself later) to be able to tweak positions visually
- The diagram lives with content (blog post companion) more than with the codebase

**Use the SVG HTML skill (`architecture-diagram`) when:**
- You need a precise, professional dark-themed render with exact colors
- The diagram is for slides, docs, or printed materials
- You need cloud-provider icons or boundary-box semantics

## File Format

```json
{
  "type": "excalidraw",
  "version": 2,
  "source": "https://excalidraw.com",
  "elements": [ /* ... */ ],
  "appState": {
    "gridSize": null,
    "viewBackgroundColor": "#1a1a2e"
  }
}
```

## Element Types

### Rectangle (most common — boxes and boundaries)

```json
{
  "id": "unique-id",
  "type": "rectangle",
  "x": 80,
  "y": 80,
  "width": 460,
  "height": 240,
  "angle": 0,
  "strokeColor": "#ff6b6b",
  "backgroundColor": "#2a1a1a",
  "fillStyle": "solid",
  "strokeWidth": 2,
  "roughness": 1,
  "opacity": 100,
  "roundness": { "type": 3 }
}
```

| Property | Meaning | Common values |
|----------|---------|---------------|
| `roughness` | Hand-drawn wobble: 0=perfect, 1-2=slight, 3+=messy | 0 (clean boxes), 1 (slight hand-drawn), 2 (sketchy) |
| `fillStyle` | Filling: solid, cross-hatch, zigzag | solid (most common) |
| `roundness` | Corner radius: null=straight, `{type:3}`=rounded | `{type:3}` for boxes, null for boundaries |
| `opacity` | 0-100 | 100 (opaque), 30-50 (transparent overlays) |

### Text

```json
{
  "id": "title-text",
  "type": "text",
  "x": 80,
  "y": 90,
  "width": 300,
  "height": 25,
  "angle": 0,
  "strokeColor": "#ffffff",
  "backgroundColor": "transparent",
  "fontSize": 18,
  "fontFamily": 1,
  "textAlign": "left",
  "text": "Architecture Title"
}
```

| Property | Meaning |
|----------|---------|
| `fontFamily` | 1=Normal (hand-drawn), 2=Handwriting, 3=Code (monospace) |
| `fontSize` | Point size: 12 (body), 16-18 (section), 24-36 (title) |
| `textAlign` | left, center, right |
| `baseline` | Vertical offset (use same as a rough guide) |

### Arrow

```json
{
  "id": "arrow-1",
  "type": "arrow",
  "x": 280,
  "y": 520,
  "width": 80,
  "height": 0,
  "angle": 0,
  "strokeColor": "#ffffff",
  "strokeWidth": 2,
  "roughness": 0,
  "opacity": 100,
  "roundness": { "type": 2 },
  "points": [[0, 0], [80, 0]]
}
```

Curved arrows use a multi-point `points` array:
```json
"points": [[0, 0], [50, 20], [100, 0]]
```

## Color Palette (Dark-Theme Architecture Diagrams)

| Role | Stroke | Background | Usage |
|------|--------|-----------|-------|
| Background | — | `#1a1a2e` | Main canvas fill |
| Error/Old system | `#ff6b6b` | `#2a1a1a` | Before/deprecated |
| Success/New system | `#4ecdc4` | `#1a2a2a` | After/improved |
| Highlight | `#ffd93d` | `#2a2a1a` | AGENTS.md, callouts |
| Primary text | `#ffffff` | — | Titles, labels |
| Secondary text | `#8899aa` | — | Subtitles, annotations |
| Code text | `#66ddcc` | — | File paths, terminal |
| Info box | `#845ef7` | `#1a1a2e` | Client/frontend |
| API box | `#ff922b` | `#1a1a2e` | API layer |
| DB box | `#74b9ff` | `#1a2a3a` | Database/storage |

## Layout Patterns

### Before/After Comparison
Place two rectangles side-by-side with an arrow between them:
```
[Before box (red, left)] → [After box (teal, right)]
```
X-offset: old box at x=80, arrow starts at x=550, new box at x=660

### System Flow (Left to Right)
```
[Client x=80] → [API x=360] → [Domain x=750]
                    ↓              ↓ (branch down)
               [Middleware]    [Database]
```
Y-offset increments: main flow at y=480, branching down to y=590-640

### Callout/Highlight
Place a highlighted rectangle below the main diagram with different Y coordinate:
```
[Main diagram area at y=80 to y=320]
[Callout box at y=330 — distinct Y offset]
```

## Typical Output Pipeline

1. Create `.excalidraw.json` alongside the blog post draft (same directory)
2. Blog post frontmatter references: `<!-- EXCALIDRAW: filename.excalidraw.json -->`
3. File can be opened in Obsidian (Excalidraw plugin) or excalidraw.com
4. From Obsidian, export as PNG for actual blog embed if needed

## Example Use Case

This reference was extracted from the M-LOG v2 Architecture blog post (2026-06-14), which included:
- Before/After comparison (old MVC vs new domain-based structure)
- Architecture flow (Svelte → Hono → Middleware → Domain Logic → DB)
- AGENTS.md callout box

See the example file at the content-aware path for the full working JSON.

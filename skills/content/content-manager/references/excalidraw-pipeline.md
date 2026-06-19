# Excalidraw → PNG Pipeline

Converts Excalidraw JSON diagrams to PNG images for blog embedding.

## Script: `~/.drewgent/scripts/excalidraw-to-png.js`

Node.js script that:
1. Uploads `.excalidraw.json` to excalidraw.com for rendering
2. Opens the embed URL (`?embed=1&theme=light`) in headless Chrome (Puppeteer)
3. Screenshots the diagram as PNG
4. Saves alongside the JSON file

## Usage
```bash
export NODE_PATH=/Users/drew/.drewgent/scripts/node_modules
node /Users/drew/.drewgent/scripts/excalidraw-to-png.js \
  input.excalidraw.json \
  output.png
```

## Dependencies
- puppeteer (installed locally at `scripts/node_modules/`)
- excalidraw-cli (globally via npm)
- Chrome for Testing (auto-downloaded by Puppeteer)

## Excalidraw File Format
Minimal structure:
```json
{
  "type": "excalidraw",
  "version": 2,
  "source": "https://excalidraw.com",
  "elements": [
    {
      "type": "rectangle",
      "x": 100, "y": 100, "width": 200, "height": 80,
      "strokeColor": "#1e1e1e",
      "backgroundColor": "#e8f4f8",
      "roughness": 1
    },
    {
      "type": "text",
      "x": 150, "y": 125,
      "text": "Component",
      "fontSize": 20
    },
    {
      "type": "arrow",
      "x": 300, "y": 140,
      "points": [[0,0],[100,0]]
    }
  ]
}
```

## Embedding in Blog Posts
```markdown
![[YYYY-MM-DD-slug.png|700]]
*{caption}*
```

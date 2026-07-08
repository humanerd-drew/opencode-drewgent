---
title: astryx
name: astryx
domain: ui
type: skill
description: "Use Meta's Astryx design system (React 19 + StyleX) for any React-based UI work. 150+ accessible, themeable components with full agent support via MCP. Load when writing React components, building internal tools, or designing admin panels."
tags: [ui, react, design-system, meta, astryx, components]
created: 2026-06-27
updated: 2026-06-27
links:
  - "[[ui/baseline-ui]]"
  - "[[software-development/ponytail]]"
trigger: "Astryx 전면 도입 결정 (2026-06-27) — React 프로젝트의 디자인 기본 선택"
provenance:
  session: "2026-06-27 astryx-evaluation"
  decision: "컴포넌트 라이브러리 자체는 stack 종속적(React+StyleX). agent-first 패턴(dense compression, vibe tests)은 패턴만 채택. MCP 서버는 즉시 등록. 모든 React 프로젝트에서 기본 선택."
---

# Astryx

Meta's open-source design system. React 19 + StyleX, 150+ components, 7 themes, MIT license.

## When to Use

- **React 프로젝트**: 무조건 Astryx 먼저 고려. 150개 컴포넌트로 90% 커버.
- **내부 도구 / admin panel**: Astryx의 Table/Dialog/FormLayout/Toast가 진가를 발휘
- **새 프로젝트 시작**: `npx astryx init --features agents`로 세팅
- **WordPress / CF Workers SPA**: Astryx 컴포넌트는 못 쓰지만, design token naming + semantic color는 CSS 변수로 차용 가능

## MCP Tools

Astryx MCP 서버(`astryx`)가 opencode.jsonc에 등록되어 있음. 두 tools:

| Tool | Description | When |
|------|-------------|------|
| `search(query, limit?)` | Natural language 검색 | 어떤 컴포넌트 쓸지 모를 때 |
| `get(name)` | Full props + usage + examples | 특정 컴포넌트 문서 필요할 때 |

### Workflow

1. `search("dropdown menu")` → 3-8개 후보
2. `get("Selector")` → props + best practices
3. 필요시 `get("Selector")`에서 `--dense` 모드로 token-efficient 조회

## Quick Start

```bash
npm install @astryxdesign/core @astryxdesign/theme-neutral @astryxdesign/cli
npx astryx init
```

## Key Conventions

- **Import**: `import {Button} from '@astryxdesign/core/Button'` (per-component subpath)
- **Theme CSS**: `@import '@astryxdesign/core/reset.css'` + `@import '@astryxdesign/core/astryx.css'` + `@import '@astryxdesign/theme-neutral/theme.css'`
- **Styling**: prefer StyleX `xstyle` prop. Components also accept `className`, Tailwind, or plain CSS
- **Dense mode**: 모든 CLI 명령어 `--dense` 지원 (token-efficient, agent용)
- **버전**: v0.1.1 Beta. breaking change 가능성 있음 → `npx astryx upgrade --apply`

## Component Categories

| Category | Key Components |
|----------|---------------|
| Layout | VStack, HStack, Grid, FormLayout, Card, Section |
| Navigation | TopNav, SideNav, Tabs, Breadcrumbs, Pagination |
| Forms | TextInput, Selector, DateInput, NumberInput, Slider, Switch |
| Feedback | Dialog, AlertDialog, Toast, Banner, ProgressBar |
| Data | Table (with plugins), List, TreeList, Pagination |
| Overlay | Popover, Tooltip, HoverCard, CommandPalette |
| Display | Badge, Avatar, Icon, Thumbnail, Skeleton, CodeBlock |
| Chat | ChatComposer, ChatMessage, ChatMessageBubble (full chat UI) |

## Smoke Test (Agent Self-Check)

Before writing Astryx code, agent must answer these 3:

1. Button import path? → `@astryxdesign/core/Button`
2. How to make Dialog non-dismissible? → `purpose="required"`
3. What prop does Selector use for items? → `options` (not `items` or `children`)

If uncertain, call `get("Button")`, `get("Dialog")`, `get("Selector")` via MCP.

## Theming

7 available themes: neutral (start here), butter, chocolate, gothic, matcha, stone, y2k.

```tsx
import { Theme } from '@astryxdesign/core/Theme';
import { neutralTheme } from '@astryxdesign/theme-neutral/built';

<Theme theme={neutralTheme}>
  <App />
</Theme>
```

Themes are CSS variable cascades. All tokens adapt to dark mode via `light-dark()`.

## Design Tokens (CSS Variables)

Component-independent tokens usable in any project:

- `--color-text-primary`, `--color-accent`, `--color-border`, `--color-surface` etc.
- Spacing: `--spacing-{1..12}` (4px scale)
- Radius: `--radius-sm`, `--radius-md`, `--radius-lg`, `--radius-full`
- Full reference: `search("tokens")` → `get("tokens")`

## Density Protocol 적용

이 skill은 Astryx의 dense compression protocol을 따라 작성됨:
- Signal words 보존 (must, never, always, instead)
- Filler prose 제거
- 코드 예제 보존
- 명령형 어조

## Links

- [GitHub](https://github.com/facebook/astryx)
- [Docs](https://astryx.atmeta.com/docs/getting-started)
- [Components](https://astryx.atmeta.com/components)
- [Playground](https://astryx.atmeta.com/playground)
- [MCP](https://astryx.atmeta.com/mcp)

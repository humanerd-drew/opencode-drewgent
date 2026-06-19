# Dashboard Design: Insight-Driven Evolution

## Core Principle

A dashboard is not a data dump. Every element must answer a specific question the user has when they open the page. If a metric doesn't drive a decision or flag an issue, it's noise.

## The Question Hierarchy

When the user opens the dashboard, their brain asks in order:

1. **Is something wrong?** → Health banner (green/yellow/red) + alert pills
2. **Is the agent alive?** → Activity row (live dot, session, elapsed)
3. **What's the big picture?** → Quick cards (CPU, Disk, Brain, Today, etc.)
4. **What needs attention?** → Kanban blocked tasks, cron errors, disk warnings
5. **What's been happening?** → Activity events, recent errors
6. **Deep dive?** → Tab pages with full detail

## Anti-Patterns (Applied & Fixed During v1→v6)

| Anti-Pattern | What was wrong | Fix |
|---|---|---|
| **Equal weighting** | macOS version had same visual weight as "3 cron errors" | Size/color hierarchy: problems get attention first |
| **Copying without understanding** | AgentsRoom layout (multi-agent grid) forced onto single-agent system | Tab-based layout adapted to Drewgent's actual architecture |
| **Over-engineering** | 90s gentle refresh with DOM-preserving update → too complex, buggy | Simple 15s full fetch, tab-based pages load fast enough |
| **Data dump** | All 15 sections shown at once on one page | Tab pages: Overview (summary) + System (detail) + Brain (models/vault) + Usage (activity) |
| **Recurring errors as duplicates** | Same HTTP 400 shown 8 times in error list | Group by message prefix, show count badge |
| **Non-actionable metrics** | Brew outdated count, Docker container count — rarely useful | Moved to Misc, not front and center |

## When to NOT Add a Feature

Signal phrases that mean "this is not the right direction":
- "전혀 참조하지 않고 만든 것 같은데" → stop and actually study the reference
- "이게 뭐지" → the feature isn't communicating its purpose
- "그냥 insight 위주로 되돌리자" → over-engineering alert, simplify
- "무리한 요구를 했다" → the implementation doesn't match the system's capability

## AgentsRoom vs Drewgent: Honest Comparison

| Capability | AgentsRoom | Drewgent | Why Drewgent Can't |
|---|---|---|---|
| Multi-agent grid | Native desktop, 1 card per agent | Single agent CLI+gateway | Architecture difference |
| Real-time terminal output | WebSocket/proc attach | 12s log polling | Agent runs in terminal, not subprocess |
| Screenshot feedback | Electron MCP (CDP) | computer-use tool | Need running app to debug |
| Desktop app | Swift/SwiftUI | Web dashboard | Scope/resource |
| Role-based agents | Agent per tab | Kanban + subagent | Different paradigm |

The key: build what fits Drewgent's architecture, not what looks cool in another product.

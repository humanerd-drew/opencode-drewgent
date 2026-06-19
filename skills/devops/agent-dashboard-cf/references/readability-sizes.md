# Readability: Sizes That Worked (And Didn't)

## Font Size Evolution

| Context | Attempt 1 | User said | Final |
|---------|-----------|-----------|-------|
| Body text | 10px | "너무 작다" | **13px** |
| Section headers | 9px | — | **10-11px** with uppercase |
| Status values | 28px | "많아보인다" | **18-20px** (pill style) |
| Table cells | 9px | — | **11-12px** |
| Hero card values | 26px | — | **26px** (accepted) |
| Hero card labels | 9px | — | **9px** uppercase |
| Health banner | 11px | — | **12px** |

## Padding / Spacing

| Element | Too tight | User said | Final |
|---------|-----------|-----------|-------|
| Card padding | 6px | cramped | **10-12px** |
| Table rows | 2px | hard to scan | **3-4px** |
| Section margin | 6px | — | **8px** |
| Card gap | 6px | — | **8-10px** (grid) |

## Key Insight

Dashboard readability is NOT just font size — it's **information density + hierarchy**:

- **Important numbers** (status, count): bold + 18-20px
- **Supporting text** (labels, timestamps): 9-11px, dim color
- **Badges/tags**: 8-9px, colored background
- **Error rows**: red text, full weight

The 13px body + 9-11px meta pattern is consistent with Datadog/Grafana monitoring UIs. Source: Grafana's `grafana.dashboard` CSS uses 12-13px body, 10px meta on dark theme.

## Don't Do

- Same size for everything (no visual hierarchy)
- ALL CAPS for long labels (use for short headers only)
- Color alone to convey meaning (add icon or bold)
- Below 10px for any body text (illegible on 1080p)

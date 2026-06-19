# CSS Layer / Z-Index Debug Patterns

## Dual CSS Variable System Conflict

**Symptom:** App renders but z-index values are wrong — overlays appear above modals, sidebars hide behind content, the FAB floats above everything. Fixing one z-index breaks another.

**Root cause:** The app has TWO CSS variable files defining overlapping custom properties:

- `theme/variables.css` (shared, loaded via `<link>` in HTML) — `--z-fab: 2000`
- `app/css/variables.css` (app-specific, **NEVER LOADED**) — `--z-fab: 6000`

The app-specific `variables.css` defines the CORRECT values but is not imported by `index.css` or linked in `index.html`. Only the shared theme's variables take effect. CSS classes that use `var(--z-fab)` get 2000 instead of 6000, causing the FAB to conflict with the drawer (also at 2000).

**Detection:**

```bash
# Check which variables.css is actually loaded
grep -n "variables.css" public/app/index.html
# If only theme/variables.css is linked → app-specific overrides are missing

# Compare values between the two files
grep "\-\-z-" app/css/variables.css
grep "\-\-z-" packages/theme/variables.css

# Find all hardcoded z-index values
grep -rn "z-index:" public/app/ --include='*.css' --include='*.js' | grep -v "var(--z"
```

**Fix:**

1. Create a dedicated `z-override.css` loaded LAST in `<head>`:
   ```html
   <link rel="stylesheet" href="/app/css/z-override.css?v=2.4.0">
   ```
2. Define ALL z-index values explicitly with `!important`:
   ```css
   .menu-sidebar { z-index: 3000 !important; }
   .menu-overlay { z-index: 2999 !important; }
   .legend-toggle { z-index: 700 !important; }
   ```
3. Remove conflicting inline styles (in JS templates) that hardcode z-index.

## `backdrop-filter` Z-Index Bug on Mobile (WebKit)

**Symptom:** On iOS Safari (and some Android browsers), an element with `backdrop-filter: blur()` appears ABOVE elements that should be at a higher z-index. The menu sidebar disappears behind a blur overlay even though the sidebar has `z-index: 3000` and the overlay has `z-index: 100`.

**Root cause:** `backdrop-filter` creates a new stacking context AND a containing block. On WebKit-based browsers (Safari, Chrome iOS), `backdrop-filter` can cause the element to render in a separate compositor layer that ignores conventional z-index ordering. This is a known WebKit rendering bug.

**Detection:**

```bash
# Find all backdrop-filter usage
grep -rn "backdrop-filter" public/app/ --include='*.css' --include='*.js'
```

**Fix:**

Remove `backdrop-filter: blur()` from overlays that need to be behind other elements. Use a plain semi-transparent background instead:

```css
/* ❌ Causes z-index breakage on mobile */
.restricted-overlay {
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    z-index: 100;
}

/* ✅ Safe alternative */
.restricted-overlay {
    background: rgba(8, 12, 18, 0.6);
    z-index: 100;
}
```

**When you MUST use backdrop-filter** (e.g., menu overlay), keep it at the HIGHEST z-index level and accept that nothing can stack above it:

```css
.menu-overlay {
    z-index: 2999;          /* Must be higher than anything behind the blur */
    backdrop-filter: blur(4px);
    -webkit-backdrop-filter: blur(4px);
}
.menu-sidebar {
    z-index: 3000;          /* Sidebar must be ABOVE its overlay */
}
```

## Z-Index Stacking Reference

For a mobile-first SPA with sidebar drawer, bottom nav, FAB, and modals:

```
z-index | Element
--------|---------
100     | Restricted overlay (login prompt) — no backdrop-filter
500     | Bottom navigation bar
700     | FAB legend toggle button
800     | Legend panel
2997    | History drawer overlay
2998    | History sidebar
2999    | Menu overlay (can use backdrop-filter here)
3000    | Menu sidebar (must be above its overlay)
5000    | Bottom sheet / breakdown sheet
6000    | Loading overlay
10000   | Toast container
```

## CSS `transform` Containing Block Trap (refresher)

Any ancestor with `transform` (even `translateX(-100%)` for slide-in drawers), `will-change: transform`, `filter`, or `backdrop-filter` creates a new containing block. `position: fixed` elements inside it are constrained to that ancestor, NOT the viewport. This affects both positioning AND z-index stacking.

**Always append modals/toasts to `document.body`** after rendering — don't nest them inside component templates that might have `transform` ancestors.

## NAS Canonical Source Check

Before modifying the m-log project (or any project with a NAS mirror):

1. Check if the NAS has a more complete/canonical version:
   ```bash
   ls ~/Library/CloudStorage/SynologyDrive-Log-Project/m-log/
   ```
2. Compare migration files — the NAS may have migrations the local project is missing:
   ```bash
   diff <(ls migrations/*.sql | sort) <(ls ~NAS_PATH/migrations/*.sql | sort)
   ```
3. Copy missing migrations or sync files BEFORE making changes.

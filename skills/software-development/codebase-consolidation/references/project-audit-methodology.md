# Project Audit Methodology

Systematic process for auditing a codebase — finding dead code, detecting structural gaps, and planning safe refactoring.

## Step 1: Full File Tree

Map every file, excluding generated/third-party dirs:

```bash
find . -type f \
  -not -path '*/node_modules/*' \
  -not -path '*/.git/*' \
  -not -path '*/.wrangler/*' \
  -not -path '*/public/assets/*' \
  | sort
```

## Step 2: Categorize Files

Group by type to understand the surface:

```bash
echo "=== Backend ===" && ls src/**/*.ts 2>/dev/null
echo "=== Frontend JS ===" && ls public/**/*.js 2>/dev/null
echo "=== Frontend CSS ===" && ls public/**/*.css 2>/dev/null
echo "=== HTML entries ===" && ls public/**/*.html 2>/dev/null
echo "=== Config ===" && ls wrangler*.{jsonc,toml} tsconfig.json package.json 2>/dev/null
echo "=== Migrations ===" && ls migrations/*.sql 2>/dev/null
```

## Step 3: Import/Reference Graph

Trace every import, `<script src>`, `<link href>`, and `@import`:

```bash
echo "=== JS/TS imports ==="
grep -rn "import " --include='*.ts' --include='*.js' source/ \
  --exclude-dir=node_modules | grep -v 'node_modules'

echo "=== HTML scripts/styles ==="
grep -rn 'src=\|href=' --include='*.html' public/ \
  | grep -v node_modules

echo "=== CSS @import ==="
grep -rn '@import' --include='*.css' public/ \
  | grep -v node_modules
```

## Step 4: Dead Code Detection

For each candidate file, check if ANY reference exists:

```bash
# Single file
grep -rn "filename\|exportedName" --include='*.{ts,js,html}' source/ \
  | grep -v 'the file itself' | grep -v node_modules
# Zero matches = dead code

# Batch: check all JS/TS files for being imported
for f in $(find public/app/js -name '*.js' | sort); do
  basename=$(basename "$f")
  name="${basename%.*}"
  refs=$(grep -rn "'\./$name\|'$name\|$name\.js\|$name" --include='*.html' --include='*.js' public/app/ \
    | grep -v "$f" | wc -l | tr -d ' ')
  if [ "$refs" -eq 0 ]; then
    echo "⚠️ DEAD: $f (0 references)"
  fi
done
```

Also check:
- **HTML `<script>` tags** that load files no longer imported by any module
- **CSS `@import` in chain** vs **CSS `<link>` in HTML** — any CSS loaded twice?
- **Environment variables defined in wrangler.jsonc** but never used in code

## Step 5: CSS Chain Audit

Compare HTML `<link>` vs CSS `@import` to find duplicates:

```bash
# List all CSS linked from HTML
grep -roh 'href="[^"]*\.css[^"]*"' public/**/*.html \
  | sed 's/href="//;s/?v=[^"]*//;s/"[^"]*$//' | sort -u

# List all CSS in @import chain
grep -roh "url('[^']*\.css[^']*')" public/**/*.css 2>/dev/null \
  | sed "s/url('//;s/')//" | sort -u

# Compare — any CSS appearing in both lists = duplicate load
```

## Step 6: Config/Data Duplication Audit

Check for environment variables, API endpoints, and client IDs defined in multiple places:

```bash
grep -rn "SAJU_API_ENDPOINT\|NAVER_CLIENT_ID\|GOOGLE_CLIENT_ID" \
  --include='*.{ts,js,jsonc}' . | grep -v node_modules
```

If the same value appears in both `wrangler.jsonc` (var) and a frontend `constants.js`, one of them is dead.

## Step 7: Reference the Result

After the audit, update the relevant skill's reference file or SKILL.md with specific patterns found. Don't capture environment-specific issues (missing binaries, wrong paths) — those are one-time setup problems.

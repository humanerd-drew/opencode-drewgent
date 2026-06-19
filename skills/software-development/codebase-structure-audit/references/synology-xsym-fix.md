# Synology Drive Symlink Corruption Recovery

## Problem
Synology Drive replaces symlinks with regular files containing `XSym` metadata header. In `node_modules/.bin/`, this breaks all CLI binaries.

## Detection
```bash
# Check if a .bin file is corrupted
head -1 node_modules/.bin/wrangler
# Output: "XSym" ← corrupted

# Check all .bin files at once
for f in node_modules/.bin/*; do
  if head -1 "$f" 2>/dev/null | grep -q "^XSym$"; then
    echo "CORRUPTED: $f"
  fi
done
```

## Recovery
The 4th line of the corrupted file contains the original symlink target:
```bash
target=$(sed -n '4p' node_modules/.bin/wrangler)
# target = "../wrangler/bin/wrangler.js"

rm node_modules/.bin/wrangler
ln -s "$target" node_modules/.bin/wrangler
```

## Bulk Fix
```bash
for f in node_modules/.bin/*; do
  if head -1 "$f" 2>/dev/null | grep -q "^XSym$"; then
    target=$(sed -n '4p' "$f")
    real_target=$(echo "$target" | sed 's|^\.\./||')
    if [ -f "node_modules/$real_target" ]; then
      rm "$f" && ln -s "$target" "node_modules/.bin/$(basename $f)"
      echo "FIXED: $f → $target"
    fi
  fi
done
```

## Prevention
- Work outside Synology Drive shared folders for dev projects
- Or: add `node_modules` to Synology Drive sync exclusion list

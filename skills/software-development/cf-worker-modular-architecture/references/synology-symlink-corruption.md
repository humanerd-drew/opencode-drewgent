# Synology Drive Symlink Corruption

Synology Drive replaces symlinks in `node_modules/.bin/` with regular files containing XSym metadata headers. This breaks all CLI tools.

## Detection
```bash
file node_modules/.bin/wrangler
# Output: "ASCII text, with very long lines" instead of "symbolic link"
head -1 node_modules/.bin/wrangler
# Output: "XSym"
```

## Fix
```bash
# Recreate corrupted symlinks
for f in node_modules/.bin/*; do
  if head -1 "$f" 2>/dev/null | grep -q "^XSym$"; then
    target=$(sed -n '4p' "$f')
    rm "$f" && ln -s "$target" "node_modules/.bin/$(basename $f)"
  fi
done
```

Or reinstall `node_modules` outside Synology drive, then copy back.

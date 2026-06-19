# Synology Drive XSym Symlink Corruption Fix

## Problem

When a Node.js project lives on a Synology Drive-synced folder, the `node_modules/.bin/` symlinks get replaced with regular files containing XSym metadata headers. Commands like `npx`, `npm run dev`, and direct `node_modules/.bin/wrangler` execution fail with `command not found` or XSym-related errors.

## Detection

```bash
# A corrupted symlink looks like this:
$ head -1 node_modules/.bin/wrangler
XSym
$ head -4 node_modules/.bin/wrangler
XSym
0027
55dc2e7e26c1987594550e2494ed29ad
../wrangler/bin/wrangler.js
```

The 4th line contains the target path (relative to `.bin/`).

## Fix

Identify all corrupted symlinks and recreate them:

```bash
cd /path/to/project
for f in node_modules/.bin/*; do
  if head -1 "$f" 2>/dev/null | grep -q "^XSym$"; then
    target=$(sed -n '4p' "$f" 2>/dev/null)
    echo "⚠️ $f → corrupted (target: ${target})"
    # Verify target exists
    real_target=$(echo "$target" | sed 's|^\.\./||')
    if [ -f "node_modules/$real_target" ]; then
      rm "$f" && ln -s "$target" "node_modules/.bin/$(basename $f)" && echo "  → restored"
    else
      echo "  → target not found, needs npm install"
    fi
  fi
done
```

## Prevention

- Don't store `node_modules/` on Synology Drive (add to synology ignore list)
- Run `npm install` on the local machine (not on a Synology-mounted path)
- If the project directory must be on Synology Drive, reinstall deps locally after every sync

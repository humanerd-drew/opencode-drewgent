# Two-Codebase Merge (NAS ↔ Working Copy)

Pattern for consolidating two copies of the same project when one has drifted — typically a "working copy" (where dev/test happens) and a "source copy" (NAS, CI checkout, deployment artifact). The goal is to combine both without breaking the running dev server.

## When This Happens

- You've been editing a Synology Drive-synced copy (`~/Library/CloudStorage/SynologyDrive-xxx/project`)
- The NAS has a more complete version with controllers, utils, db, etc. that the working copy lacks
- You need to merge the NAS additions into your working copy WITHOUT losing your local changes
- You work from multiple devices (MacBook Air + Mac Mini) each syncing to the same NAS via Synology Drive, SMB, or NFS, leading to version divergence

## Three-Phase Merge

### Phase 1: Diff Directory Structure

Compare both source trees at the top levels:

```bash
# Show what's unique to each side
diff -rq /path/to/working/copy/src/ /path/to/nas/copy/src/ \
  | grep -v 'DS_Store' | grep -v node_modules
```

Output shows:
- `Only in working: x` — your local additions (KEEP)
- `Only in NAS: y` — missing files (COPY)
- `Files differ: z` — same path, different content (MERGE)

### Phase 2: Categorize Differences

| Marker | Meaning | Action |
|--------|---------|--------|
| `Only in working copy` | Your new file (analysis engine, etc.) | Keep — don't touch |
| `Only in NAS` | Files that should exist (controllers, utils, db) | Copy to working copy |
| `Files differ` | Same path but different content | Manual merge needed |

### Phase 3: SHA256 Content-Hash Comparison

**Don't trust modification times alone.** Synology Drive can set bulk timestamps on synced files, making hundreds of files look "newer" when only a few actually changed.

Use SHA256 to identify files with genuinely different content:

```bash
# Find files at the same relative path that have different content
python3 << 'PYEOF'
import os, hashlib

DIR_A = "/path/to/copy/a"
DIR_B = "/path/to/copy/b"
SKIP_DIRS = {'.git', 'node_modules', '.wrangler', '.idea', '__pycache__'}

def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()

def scan(base):
    result = {}
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            rel = os.path.relpath(os.path.join(root, f), base)
            if rel.startswith('.git/'): continue
            result[rel] = os.path.join(root, f)
    return result

a = scan(DIR_A); b = scan(DIR_B)
common = set(a) & set(b)

print("=== Files with different content ===")
for path in sorted(common):
    if sha256(a[path]) != sha256(b[path]):
        print(f"  DIFF: {path}")

print(f"\n=== Only in A: {len(set(a) - common)} files")
print(f"=== Only in B: {len(set(b) - common)} files")
print(f"=== Common & identical: {len(common) - sum(1 for p in common if sha256(a[p]) != sha256(b[p]))} files")
PYEOF
```

### Phase 4: Git-History Check Before Overwriting Entry-Point Files

**CRITICAL**: Before copying any file from one copy to another, especially the project's entry-point file (`worker.ts`, `main.ts`, `index.js`), check the git history first. Entry-point files are the most likely to have different import structures between diverged copies.

```bash
cd /path/to/copy/b
git show HEAD:worker.ts | head -20
# Compare imports — if different structure, DON'T overwrite blindly
```

If the entry-point files have different import structures (e.g., one imports `./src/analysis/engine` and the other doesn't), the correct approach is:

1. **Restore** the target's entry-point file from git history
2. **Apply targeted patches** (model name fix, config update) to the restored file
3. **Copy only the auxiliary files** (controller/*, utils/*) that were changed

**Do NOT overwrite entry-point files with the source copy's version** — this is the most common way to break the build.

### Phase 5: Selective Copy

Copy NAS-only directories to the working copy:

```bash
SRC=/Volumes/nas/project/src
DST=~/project/src

for item in "controllers" "engine" "utils" "db" "some-file.ts"; do
  if [ -e "$SRC/$item" ] && [ ! -e "$DST/$item" ]; then
    cp -R "$SRC/$item" "$DST/$item"
  fi
done
```

### Phase 6: Symlink Dependencies

If the project has inter-package symlinks (e.g., `../packages/core/*` referenced via a `sync:local` script), check that those dependency packages actually exist after the merge:

```bash
# Check packages/ directory
ls ../packages/ 2>/dev/null || echo "MISSING packages/ — sync:local will copy nothing"

# Re-run the sync script from package.json
npm run sync:local
```

### Phase 7: Post-Merge Verification

1. **TypeScript check** — Run `tsc --noEmit` and note new errors. Expect these types of issues:
   - Missing environment variables in `Env` interface (add to `worker-configuration.d.ts`)
   - Missing module references (copy referenced files)
   - Type mismatches (pre-existing, unrelated to merge)

2. **Build check** — Run `wrangler deploy --dry-run` to verify the worker builds before actually deploying:
   ```bash
   npx wrangler deploy --dry-run
   ```
   This catches import resolution failures without deploying broken code.

3. **Dev server test** — If `wrangler dev` is running, it auto-reloads. Hit the app's main page and a key API endpoint.

4. **Spot-check new controllers** — Hit any new API endpoints the controllers provide. They may fail due to missing env vars — that's expected and doesn't block merge.

## Common Issues

### Missing Env Vars

NAS controllers often reference env vars that don't exist in your wrangler config:

```
Property 'DEEPSEEK_API_KEY' does not exist on type 'Env'
Property 'NVIDIA_NIM_KEY' does not exist on type 'Env'
```

These are NOT blocking — they'll fail at runtime only when that code path is hit. Add placeholder entries to `worker-configuration.d.ts` to quiet the type checker:

```typescript
// Add to worker-configuration.d.ts under the existing Env interface:
DEEPSEEK_API_KEY?: string;
NVIDIA_NIM_KEY?: string;
```

### Missing Data Files

NAS controllers may reference JSON data files not in your working copy:

```
Cannot find module '../../frontend/data/sinsal-guide.json'
```

Copy from NAS to the expected path:

```bash
cp /Volumes/nas/project/frontend/data/sinsal-guide.json \
  ~/project/frontend/data/sinsal-guide.json
```

### Symlink Corruption (Synology)

Synology Drive replaces symlinks in `node_modules/.bin/` with XSym text files. Fix:

```bash
for f in node_modules/.bin/*; do
  if head -1 "$f" 2>/dev/null | grep -q "^XSym$"; then
    target=$(sed -n '4p' "$f" 2>/dev/null)
    real_target=$(echo "$target" | sed 's|^\.\./||')
    if [ -f "node_modules/$real_target" ]; then
      rm "$f" && ln -s "$target" "node_modules/.bin/$(basename $f)"
    fi
  fi
done
```

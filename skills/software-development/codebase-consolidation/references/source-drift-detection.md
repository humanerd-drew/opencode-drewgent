# Source Drift Detection — Synology Drive Multi-Mount Workflow

## Context
When a project lives on a Synology Drive that's mounted under different paths on different machines (or different sync profiles), the "same" project can have different content across mounts. This is especially dangerous when one mount is used for active development and another is the NAS source of truth.

## Symptom
You search for a file that logically should exist (based on architecture docs, import paths in existing code, the user's statements) but it's not found. Or the user insists a feature works, but you can't find the code that implements it.

## Diagnosis

```bash
# Find ALL mount points of the same project
find /Users/drew/Library/CloudStorage -maxdepth 4 -name "project-name" -type d 2>/dev/null

# Compare a key file across mounts
diff -q /mount1/path/to/key-file.ts /mount2/path/to/key-file.ts

# Check directory listing differences
diff <(ls /mount1/project/src/) <(ls /mount2/project/src/)
```

## Common Pattern
- **Mount A**: Working copy with active changes (may be behind the NAS)
- **Mount B**: NAS source of truth (has controllers, utils, db that the working copy lacks)
- **Deployed to Cloudflare**: May be yet another version

## Resolution
1. Identify which mount is the authoritative source (ask the user or check file timestamps)
2. Copy missing directories from the source mount to the working copy
3. Update imports in the working copy to match the source mount's directory structure
4. Commit to the working copy — the NAS sync propagates automatically

## Prevention
When starting work on a Synology-hosted project, always:
```bash
echo "=== All mounts of $(basename $(pwd)) ==="
find /Users/drew/Library/CloudStorage -maxdepth 4 -name "$(basename $(pwd))" -type d 2>/dev/null
echo "=== Key file comparison ==="
# Pick a structurally important file and compare
```
Log the authoritative mount path to memory so future sessions know where to look.

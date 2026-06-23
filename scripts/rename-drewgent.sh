#!/usr/bin/env bash
# rename-drewgent.sh — Replace all "drewgent" references with a new agent name.
# Usage: bash scripts/rename-drewgent.sh "alexgent"
set -euo pipefail

OLD="drewgent"
NEW="${1:?Usage: $0 <newname> (e.g., alexgent)}"
ROOT="${2:-$HOME/.drewgent}"

if [ ! -d "$ROOT" ]; then
  echo "Directory $ROOT not found"
  exit 1
fi

echo "Renaming $OLD → $NEW in $ROOT ..."

cd "$ROOT"

# 1. Replace in all tracked + untracked text files
echo "  Replacing in source files ..."
find . -type f \( -name "*.md" -o -name "*.py" -o -name "*.json" -o -name "*.jsonc" \
  -o -name "*.yaml" -o -name "*.yml" -o -name "*.sh" -o -name "*.js" -o -name "*.html" \) \
  -not -path "./.git/*" -not -path "*/node_modules/*" -not -path "*/__pycache__/*" \
  -print0 | xargs -0 sed -i '' "s/$OLD/$NEW/g" 2>/dev/null || true

# 2. Capitalized version (Drewgent → Alexgent)
CAP_OLD="Drewgent"
CAP_NEW="$(echo "${NEW:0:1}" | tr 'a-z' 'A-Z')${NEW:1}"
echo "  Replacing capitalized ($CAP_OLD → $CAP_NEW) ..."
find . -type f \( -name "*.md" -o -name "*.py" -o -name "*.json" -o -name "*.jsonc" \
  -o -name "*.yaml" -o -name "*.yml" -o -name "*.sh" -o -name "*.js" -o -name "*.html" \) \
  -not -path "./.git/*" -not -path "*/node_modules/*" -not -path "*/__pycache__/*" \
  -print0 | xargs -0 sed -i '' "s/$CAP_OLD/$CAP_NEW/g" 2>/dev/null || true

# 3. Rename the directory if $ROOT is ~/.drewgent
if [ "$ROOT" = "$HOME/.drewgent" ] && [ "$OLD" = "drewgent" ]; then
  NEW_ROOT="$HOME/.$NEW"
  echo "  Renaming directory $ROOT → $NEW_ROOT ..."
  cd "$HOME"
  # Check if target exists
  if [ -e "$NEW_ROOT" ]; then
    echo "  WARNING: $NEW_ROOT already exists. Not renaming directory."
    echo "  Source files updated in $ROOT. Move manually if desired."
  else
    mv "$ROOT" "$NEW_ROOT"
    echo "  Directory renamed. Update any symlinks or launchd plists."
    echo "  Next: update opencode.jsonc skill paths (now ~/.$NEW/skills)"
    ROOT="$NEW_ROOT"
  fi
fi

echo ""
echo "Done. Verify:"
echo "  grep -r \"$OLD\" \"$ROOT\" --include='*.md' --include='*.py' --include='*.json' | head -5"
echo "  (Should return nothing)"
echo ""
echo "If you moved the directory, also update:"
echo "  - launchd plists (~/Library/LaunchAgents/)"
echo "  - opencode.jsonc skill paths"
echo "  - Any cron scripts with hardcoded paths"

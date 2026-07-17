#!/usr/bin/env python3
"""Clean up AutoLearner noise from wiki files.

AutoLearner's _detect_implicit_style writes an entry for every short
command input (~/tool, curl, grep, git, etc.) and _ANTI_PATTERNS writes
"don't X" entries for any negative sentence.  After months of operation,
these noise entries drown out the handful of genuinely useful facts.

What this script does:
  1. Reads every .md file under memories/entities/ concepts/ insights/
  2. Removes log entries matching known noise patterns
  3. Compacts files that have only noise + header, preserving the structure
  4. Reports what it removed
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

DREW_HOME = Path(__file__).resolve().parent.parent
WIKI_DIR = DREW_HOME / "memories"


# ── Noise patterns ────────────────────────────────────────────────────
# These match the AutoLearner _detect_implicit_style output format.
# Each log entry in wiki files starts with "- YYYY-MM-DD:" followed by content.

NOISE_PREFIXES = [
    "from short input:",          # _detect_implicit_style — every short cmd
    "^(?:#environment, )?#tool",  # tool pattern match
]

NOISE_SUBSTRINGS = [
    "from short input:",
    "^tool-",
]


def is_noise(line: str) -> bool:
    """Return True if line is AutoLearner noise that should be removed."""
    stripped = line.strip()
    # Standard log entries: "- YYYY-MM-DD: ..."
    if stripped.startswith("- 20"):
        if "anti-preference-" in stripped:
            return True
        if re.search(r"\^style-\w+-\d{8}", stripped):
            return True
        if "#identity" in stripped and "[SYSTEM:" in stripped:
            return True
        for sub in NOISE_SUBSTRINGS:
            if sub in stripped:
                return True
        return False
    # Non-log noise: any line with "from short input"
    if "from short input:" in stripped:
        return True
    return False


def strip_metadata_tags(text: str) -> str:
    """Remove AutoLearner metadata tags like ^anti-preference-YYYYMMDD from text.
    
    These tags are invisible to the agent but clutter the wiki files.
    """
    return re.sub(r'\^[\w-]+-\d{8}', '', text)


def clean_wiki_file(path: Path) -> dict:
    """Remove noise entries from a wiki file. Returns removal stats."""
    original = path.read_text(encoding="utf-8")
    lines = original.split("\n")
    kept = []
    removed_count = 0
    for line in lines:
        if is_noise(line):
            removed_count += 1
        else:
            kept.append(line)
    cleaned = "\n".join(kept)
    # Strip metadata tags from remaining content
    cleaned = strip_metadata_tags(cleaned)
    if cleaned != original:
        path.write_text(cleaned, encoding="utf-8")
    return {
        "file": str(path.relative_to(DREW_HOME)),
        "original_lines": len(lines),
        "removed": removed_count,
        "kept": len(kept),
        "tags_stripped": cleaned != original and len(kept) == len(lines),
        "changed": cleaned != original,
    }


def main() -> str:
    now = datetime.now(timezone.utc)
    stats = []

    for folder in ("entities", "concepts", "insights"):
        folder_path = WIKI_DIR / folder
        if not folder_path.exists():
            continue
        for md_file in sorted(folder_path.glob("*.md")):
            try:
                st = clean_wiki_file(md_file)
                if st["removed"] > 0:
                    stats.append(st)
            except Exception as exc:
                print(f"Error processing {md_file}: {exc}", file=sys.stderr)

    if not stats:
        return "[SILENT]"

    lines = []
    lines.append("# Wiki Cleanup Report")
    lines.append(f"**Total files cleaned**: {len(stats)}")
    lines.append(f"**Total entries removed**: {sum(s['removed'] for s in stats)}")
    lines.append("")
    for s in stats:
        lines.append(f"- **{s['file']}**: removed {s['removed']}/{s['original_lines']} entries (kept {s['kept']})")
    lines.append("")
    lines.append(f"Cleaned at: {now.isoformat()}")

    return "\n".join(lines)


if __name__ == "__main__":
    output = main()
    if output != "[SILENT]":
        print(output)

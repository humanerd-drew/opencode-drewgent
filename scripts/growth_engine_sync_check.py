#!/usr/bin/env python3
"""
growth_engine_sync_check.py
============================
Check whether source/drewgent-agent/modules/growth_engine.py (canonical)
and P4-cortex/growth/engine.py (shadow) are in sync.

Usage:
  python3 growth_engine_sync_check.py
  python3 growth_engine_sync_check.py --verbose
  python3 growth_engine_sync_check.py --sync     # patch P4-cortex from source

This script is the source-of-truth guardian: it ensures that modifications
to the canonical source/modules/growth_engine.py are reflected in the
P4-cortex shadow (used by drewgent_hooks.py when P4 is the runtime context).

Canonical:  source/drewgent-agent/modules/growth_engine.py
Shadow:      P4-cortex/growth/engine.py
"""

import argparse
import difflib
import hashlib
import json
import sys
from pathlib import Path

_DREW_HOME = Path.home() / ".drewgent"
CANONICAL = _DREW_HOME / "source" / "drewgent-agent" / "modules" / "growth_engine.py"
SHADOW = _DREW_HOME / "P4-cortex" / "growth" / "engine.py"
STATE_FILE = _DREW_HOME / "P4-cortex" / "knowledge" / "growth_engine_sync.json"


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {"last_canonical_hash": "", "last_shadow_hash": "", "last_sync": None}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def file_hash(path: Path) -> str:
    if not path.exists():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:32]


def get_methods(path: Path) -> set:
    """Extract all def method names from a Python file."""
    if not path.exists():
        return set()
    content = path.read_text(encoding="utf-8")
    methods = set()
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("def ") and not stripped.startswith("def _"):
            # public method
            name = stripped.split("(")[0].replace("def ", "").strip()
            methods.add(name)
        elif stripped.startswith("def _"):
            # private method (include for completeness)
            name = stripped.split("(")[0].replace("def _", "_").strip()
            methods.add(name)
    return methods


def get_classes(path: Path) -> set:
    """Extract all class names from a Python file."""
    if not path.exists():
        return set()
    content = path.read_text(encoding="utf-8")
    classes = set()
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("class "):
            name = stripped.split("(")[0].replace("class ", "").strip()
            classes.add(name)
    return classes


def main() -> int:
    parser = argparse.ArgumentParser(description="Check growth_engine sync between source and P4-cortex")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--sync", action="store_true", help="Copy canonical → shadow (overwrite shadow)")
    parser.add_argument("--watch", action="store_true", help="Poll every 60s for changes")
    args = parser.parse_args()

    state = load_state()
    canonical_hash = file_hash(CANONICAL)
    shadow_hash = file_hash(SHADOW)

    print("growth_engine Sync Check")
    print("=" * 50)
    print(f"  Canonical: {CANONICAL}")
    print(f"  Shadow:   {SHADOW}")
    print()
    print(f"  Canonical hash: {canonical_hash[:16]}")
    print(f"  Shadow hash:    {shadow_hash[:16]}")
    print(f"  Last canonical: {state.get('last_canonical_hash', 'unknown')[:16]}")
    print()

    if not CANONICAL.exists():
        print("FATAL: Canonical file not found!")
        return 1

    if not shadow_hash:
        print("STATUS: Shadow file does not exist yet.")
        print("ACTION: Run with --sync to create it from canonical.")
        if args.sync:
            print(f"\n  Copying canonical → shadow...")
            SHADOW.parent.mkdir(parents=True, exist_ok=True)
            SHADOW.write_bytes(CANONICAL.read_bytes())
            state["last_canonical_hash"] = canonical_hash
            state["last_shadow_hash"] = canonical_hash
            state["last_sync"] = str(Path(__file__).name) + " initial sync"
            save_state(state)
            print("  Done.")
        return 0

    if canonical_hash == shadow_hash:
        print("STATUS: ✅ In sync (hashes match)")
        return 0

    # Hashes differ — analyze what changed
    canonical_content = CANONICAL.read_text(encoding="utf-8")
    shadow_content = SHADOW.read_text(encoding="utf-8")

    canonical_classes = get_classes(CANONICAL)
    shadow_classes = get_classes(SHADOW)
    canonical_methods = get_methods(CANONICAL)
    shadow_methods = get_methods(SHADOW)

    canonical_public = {m for m in canonical_methods if not m.startswith("_")}
    shadow_public = {m for m in shadow_methods if not m.startswith("_")}
    canonical_private = {m for m in canonical_methods if m.startswith("_")}
    shadow_private = {m for m in shadow_methods if m.startswith("_")}

    print("STATUS: ⚠️  Out of sync — hashes differ")
    print()
    print("Class comparison:")
    print(f"  Canonical: {canonical_classes}")
    print(f"  Shadow:    {shadow_classes}")
    only_canonical = canonical_methods - shadow_methods
    only_shadow = shadow_methods - canonical_methods
    common = canonical_methods & shadow_methods
    print()
    print(f"Methods: {len(canonical_methods)} canonical, {len(shadow_methods)} shadow")
    if only_canonical:
        print(f"  Only in canonical ({len(only_canonical)}): {sorted(only_canonical)}")
    if only_shadow:
        print(f"  Only in shadow    ({len(only_shadow)}): {sorted(only_shadow)}")
    print(f"  Common: {len(common)}")

    if args.verbose and canonical_hash != shadow_hash:
        print()
        print("Diff (canonical vs shadow, first 60 lines):")
        diff = list(difflib.unified_diff(
            shadow_content.splitlines(keepends=True),
            canonical_content.splitlines(keepends=True),
            fromfile=str(SHADOW),
            tofile=str(CANONICAL),
            lineterm="",
        ))
        for line in diff[:60]:
            print(line.rstrip())

    if args.sync:
        print()
        print("SYNC: Copying canonical → shadow (overwrite)...")
        SHADOW.write_bytes(CANONICAL.read_bytes())
        state["last_canonical_hash"] = canonical_hash
        state["last_shadow_hash"] = canonical_hash
        state["last_sync"] = "manual --sync"
        save_state(state)
        print("  Done. Shadow is now identical to canonical.")

    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
P5→P0 Rule Promotion — Closes P5-Ego to P0-brainstem pipeline

When P5-Ego creates a new rule (detected via rules.json changes),
this script promotes it to P0-brainstem as a 禁-token HARD rule.

Usage:
  python3 p5_to_p0_promote.py                    # scan + promote
  python3 p5_to_p0_promote.py --dry-run          # show what would change
  python3 p5_to_p0_promote.py --watch           # watch mode (poll every 60s)
  python3 p5_to_p0_promote.py --check FILE      # check specific file for new rules
"""

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

_DREWGENT_HOME = Path.home() / ".drewgent"
_P5_EGO_DIR = _DREWGENT_HOME / "P5-ego"
_P0_BRAIN_DIR = _DREWGENT_HOME / "P0-brainstem" / "brain"
_P0_RULES_FILE = _P0_BRAIN_DIR / "Drewgent-brain" / "rules.json"
_STATE_FILE = _DREWGENT_HOME / "P4-cortex" / "knowledge" / "p5_p0_state.json"
_DRY_RUN = False

# Rules that should NEVER be promoted (stay in P5, never reach P0)
P0_NEVER_PROMOTE = {
    "identity", "personality", "tone", "style", "values",
    "strategy", "planning", "long-term", "prefrontal",
}

# Rules that are candidates for P0 promotion
P0_CANDIDATE_PREFIXES = ("禁", "never", "always", "must", "shall", "require")


def load_state() -> dict:
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text())
        except Exception:
            pass
    return {"known_hashes": [], "promoted_rules": {}, "last_check": None, "promoted_count": 0}


def save_state(state: dict) -> None:
    if _DRY_RUN:
        return
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def file_hash(path: Path) -> str:
    if not path.exists():
        return ""
    return hashlib.md5(path.read_text(encoding="utf-8").encode()).hexdigest()[:16]


def detect_rules_from_content(content: str, source_file: str) -> list[dict]:
    """
    Extract rule-like statements from P5 content.
    Looks for lines with 禁 prefix or explicit rule patterns.
    """
    rules = []
    for line_num, line in enumerate(content.splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("//"):
            continue

        # Pattern 1: 禁-token
        if line.startswith("禁"):
            parts = line.split(None, 1)
            token = parts[0].lstrip("*-:")
            rule_name = token.replace("禁", "")
            rules.append({
                "token": token,
                "name": rule_name,
                "content": parts[1] if len(parts) > 1 else "",
                "source": source_file,
                "line": line_num,
                "priority": "P0",
                "severity": "critical",
            })

        # Pattern 2: HARD/Never/SOFT markers
        elif any(line.startswith(p) for p in ("**HARD**", "**NEVER**", "**SOFT**", "*NEVER*")):
            marker_end = 0
            for marker in ("**HARD**", "**NEVER**", "**SOFT**", "*NEVER*"):
                if line.startswith(marker):
                    marker_end = len(marker)
                    break
            body = line[marker_end:].strip().lstrip(":- ").strip()
            rules.append({
                "token": f"禁{body.split(',')[0].split('：')[0].split(':')[0].strip()}",
                "name": body.split(",")[0].strip(),
                "content": body,
                "source": source_file,
                "line": line_num,
                "priority": "P0" if "HARD" in line or "NEVER" in line else "P5",
                "severity": "critical",
            })

        # Pattern 3: all-caps directive style
        elif len(line) > 5 and line.isupper() and any(c.islower() for c in line):
            # mixed case all-caps — probably a directive
            rules.append({
                "token": f"禁{line.split()[0]}",
                "name": line.split()[0],
                "content": line,
                "source": source_file,
                "line": line_num,
                "priority": "P5",
                "severity": "info",
            })

    return rules


def scan_p5_for_rules() -> list[dict]:
    """Scan P5-ego directory for new rules."""
    rules = []

    if not _P5_EGO_DIR.exists():
        return rules

    for md_file in _P5_EGO_DIR.rglob("*.md"):
        rel_path = md_file.relative_to(_DREWGENT_HOME)
        try:
            content = md_file.read_text(encoding="utf-8")
        except Exception:
            continue

        file_rules = detect_rules_from_content(content, str(rel_path))
        rules.extend(file_rules)

    # Also check SELF_MODEL.md which is the primary P5 identity doc
    self_model = _P5_EGO_DIR / "SELF_MODEL.md"
    if self_model.exists():
        try:
            content = self_model.read_text(encoding="utf-8")
            rules.extend(detect_rules_from_content(content, "P5-ego/SELF_MODEL.md"))
        except Exception:
            pass

    return rules


def build_p0_rule(rule: dict) -> dict:
    """Convert a P5 rule dict into a P0-brainstem hard_hook rule."""
    return {
        "id": f"p5_promoted_{rule['name'].lower().replace(' ', '_')[:30]}",
        "name": rule['name'][:50],
        "description": rule['content'][:200] if rule['content'] else f"Promoted from P5: {rule['source']}",
        "pattern": f"regex:.{rule['name'][:20]}",
        "action": "block",
        "weight": 2.0,
        "enabled": True,
        "neuron": f"禁{rule['name']}.neuron",
        "source": f"p5_promote:{rule['source']}",
        "promoted_at": datetime.now().isoformat(),
    }


def promote_rules(new_rules: list[dict], state: dict) -> list[str]:
    """Promote eligible rules from P5 to P0."""
    promoted = []
    eligible = [r for r in new_rules if not any(
        keyword in r["name"].lower() for keyword in P0_NEVER_PROMOTE
    )]

    if not _P0_RULES_FILE.exists():
        if not _DRY_RUN:
            _P0_RULES_FILE.parent.mkdir(parents=True, exist_ok=True)
            _P0_RULES_FILE.write_text(json.dumps({"hard_hooks": [], "soft_hooks": []}, indent=2))
        else:
            print(f"[DRY-RUN] Would create {_P0_RULES_FILE}")

    try:
        rules_data = json.loads(_P0_RULES_FILE.read_text())
    except Exception:
        rules_data = {"hard_hooks": [], "soft_hooks": []}

    for rule in eligible:
        token = rule["token"]
        # Skip if already promoted
        if token in state.get("promoted_rules", {}):
            continue

        # Check if neuron already exists in P0 rules
        neuron_id = f"禁{rule['name']}.neuron"
        existing = any(h.get("neuron") == neuron_id for h in rules_data.get("hard_hooks", []))
        if existing:
            continue

        p0_rule = build_p0_rule(rule)

        if not _DRY_RUN:
            rules_data["hard_hooks"].append(p0_rule)
            _P0_RULES_FILE.write_text(json.dumps(rules_data, indent=2, ensure_ascii=False))

        promoted.append(f"禁{rule['name']}")
        state["promoted_rules"][token] = {
            "promoted_at": datetime.now().isoformat(),
            "source": rule["source"],
            "neuron": neuron_id,
        }
        state["promoted_count"] += 1
        print(f"{'[DRY-RUN] ' if _DRY_RUN else ''}✓ Promoted: 禁{rule['name']} (from {rule['source']})")

    return promoted


def main() -> int:
    global _DRY_RUN

    parser = argparse.ArgumentParser(description="P5→P0 Rule Promotion Pipeline")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--check", metavar="FILE", help="Check specific file for new rules")
    args = parser.parse_args()
    _DRY_RUN = args.dry_run

    state = load_state()
    print(f"P5→P0 Rule Promotion {'(DRY-RUN)' if _DRY_RUN else ''}")
    print(f"  P5 source: {_P5_EGO_DIR}")
    print(f"  P0 target: {_P0_RULES_FILE.parent}")
    print(f"  Previously promoted: {state['promoted_count']}")
    print()

    if args.watch:
        print("Watch mode: polling every 60s. Ctrl-C to stop.")
        last_hashes: dict[str, str] = {}
        while True:
            changed = []
            for md_file in list(_P5_EGO_DIR.rglob("*.md")) + [_P5_EGO_DIR / "SELF_MODEL.md"]:
                if not md_file.exists():
                    continue
                h = file_hash(md_file)
                if md_file not in last_hashes or last_hashes[md_file] != h:
                    last_hashes[md_file] = h
                    changed.append(md_file)

            if changed:
                print(f"\n[{datetime.now():%H:%M:%S}] Changes detected in {len(changed)} file(s)")
                all_rules = scan_p5_for_rules()
                promoted = promote_rules(all_rules, state)
                if promoted:
                    state["last_check"] = datetime.now().isoformat()
                    save_state(state)
                    print(f"  Total promoted rules: {state['promoted_count']}")
                else:
                    print("  No new rules to promote.")
            else:
                print(f".", end="", flush=True)
            time.sleep(60)
        return 0

    if args.check:
        f = Path(args.check)
        if f.exists():
            content = f.read_text()
            rules = detect_rules_from_content(content, str(f))
            print(f"Rules in {args.check}: {len(rules)}")
            for r in rules:
                print(f"  禁{r['name']}: {r['content'][:60]}")
            return 0
        else:
            print(f"File not found: {args.check}")
            return 1

    # Default: scan + promote
    all_rules = scan_p5_for_rules()
    print(f"P5 rules found: {len(all_rules)}")
    promoted = promote_rules(all_rules, state)

    if not promoted:
        print("No new rules to promote.")
        return 0

    if not _DRY_RUN:
        state["last_check"] = datetime.now().isoformat()
        save_state(state)
        print(f"\nDone. {len(promoted)} rule(s) promoted. Total: {state['promoted_count']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

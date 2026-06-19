#!/usr/bin/env python3
"""
Trend Usage Watch — applied/ 항목 사용 흔적 체크

Scans applied/ items and checks if they're actually being used:
  1. Skill with matching name exists?
  2. Referenced in config files?
  3. Referenced in neuron/rules files?
  4. Last_seen timestamp?

Output: JSON report to .usage_report.json
Exit codes: 0 = all active, 1 = some stale candidates found, 2 = no applied items
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

_DREWGENT_HOME = Path.home() / ".drewgent"
_P4_TREND = _DREWGENT_HOME / "P4-cortex" / "growth" / "trend-harvester"
_STALE_DAYS = 30  # No reference in N days = stale candidate

# Search targets
_SKILL_DIRS = [
    _DREWGENT_HOME / "skills",
    _DREWGENT_HOME / "P3-sensors" / "skills",
]
_CONFIG_FILES = [
    Path.home() / ".hermes" / "config.yaml",
    _DREWGENT_HOME / "config.yaml",
    _DREWGENT_HOME / "P5-ego" / "config" / "config.yaml",
]
_NEURON_DIR = _DREWGENT_HOME / "P0-brainstem"
_RULES_FILE = _DREWGENT_HOME / "P0-brainstem" / "brain" / "rules.md"


def slugify(name: str) -> str:
    """Create a searchable slug from trend name."""
    return re.sub(r'[^a-z0-9_-]', '', name.lower().replace(' ', '-').replace('/', '-'))


def check_skill(name: str, slug: str) -> dict:
    """Check if a skill exists with matching name."""
    for skills_dir in _SKILL_DIRS:
        if not skills_dir.exists():
            continue
        # Direct name match
        skill_path = skills_dir / slug / "SKILL.md"
        if skill_path.exists():
            return {"exists": True, "path": str(skill_path), "match_type": "exact_slug"}
        # Partial match in skill directories
        for skill_dir in skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            md_path = skill_dir / "SKILL.md"
            if md_path.exists():
                content = md_path.read_text(encoding="utf-8", errors="ignore")
                if name.lower() in content.lower() or slug in skill_dir.name:
                    return {"exists": True, "path": str(md_path), "match_type": "content_reference"}
    return {"exists": False, "path": None, "match_type": None}


def check_config(name: str, slug: str) -> list:
    """Check if name appears in config files."""
    references = []
    for cf in _CONFIG_FILES:
        if cf.exists():
            content = cf.read_text(encoding="utf-8", errors="ignore")
            if slug in content or name.lower() in content.lower():
                references.append(str(cf))
    return references


def check_neurons(name: str, slug: str) -> list:
    """Check if name appears in neuron/rules files."""
    references = []
    
    # Check rules.md
    if _RULES_FILE.exists():
        content = _RULES_FILE.read_text(encoding="utf-8", errors="ignore")
        if slug in content or name.lower() in content.lower():
            references.append(str(_RULES_FILE))
    
    # Check neuron directory
    if _NEURON_DIR.exists():
        for f in _NEURON_DIR.rglob("*.neuron"):
            content = f.read_text(encoding="utf-8", errors="ignore")
            if slug in content or name.lower() in content.lower():
                references.append(str(f))
    
    return references


def main():
    applied_dir = _P4_TREND / "applied"
    if not applied_dir.exists():
        print(json.dumps({"error": "applied/ directory not found", "items": [], "stale_count": 0, "active_count": 0}))
        return 2

    items = []
    for f in sorted(applied_dir.glob("*.json")):
        try:
            data = json.loads(f.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        
        item = data.get("item", {})
        name = item.get("name", f.stem)
        slug = slugify(name)
        
        # Check usage
        skill_ref = check_skill(name, slug)
        config_refs = check_config(name, slug)
        neuron_refs = check_neurons(name, slug)
        
        # Determine status
        all_refs = []
        if skill_ref["exists"]:
            all_refs.append(skill_ref["path"])
        all_refs.extend(config_refs)
        all_refs.extend(neuron_refs)
        
        file_mtime = f.stat().st_mtime
        last_modified = datetime.fromtimestamp(file_mtime, tz=timezone.utc)
        days_since_mod = (datetime.now(timezone.utc) - last_modified).days
        
        if all_refs:
            status = "active"
        elif days_since_mod > _STALE_DAYS:
            status = "stale"
        else:
            status = "recent_unreferenced"
        
        items.append({
            "name": name,
            "file": f.name,
            "status": status,
            "applied_at": data.get("applied_at", last_modified.isoformat()),
            "days_since_mod": days_since_mod,
            "skill_match": skill_ref,
            "config_refs": len(config_refs),
            "neuron_refs": len(neuron_refs),
            "total_refs": len(all_refs),
            "references": all_refs,
        })
    
    active_count = sum(1 for i in items if i["status"] == "active")
    stale_count = sum(1 for i in items if i["status"] == "stale")
    recent_count = sum(1 for i in items if i["status"] == "recent_unreferenced")
    
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_applied": len(items),
        "active_count": active_count,
        "stale_count": stale_count,
        "recent_unreferenced_count": recent_count,
        "stale_threshold_days": _STALE_DAYS,
        "items": items,
    }
    
    # Write report
    report_path = _P4_TREND / ".usage_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    
    # Summary to stdout (this becomes the cron delivery)
    print(f"## Trend Usage Watch — {datetime.now().strftime('%Y-%m-%d')}")
    print(f"Applied: {len(items)} | Active: {active_count} | Stale: {stale_count} | Recent: {recent_count}")
    
    if stale_count > 0:
        print(f"\n### Stale Candidates ({stale_count})")
        for i in items:
            if i["status"] == "stale":
                print(f"- **{i['name']}**: last modified {i['days_since_mod']}d ago, 0 references")
    
    if active_count > 0:
        print(f"\n### Active Items ({active_count})")
        for i in items[:5]:
            refs_str = ", ".join(i["references"][:3])
            print(f"- **{i['name']}**: {len(i['references'])} reference(s) — {refs_str}")
        if active_count > 5:
            print(f"  ... and {active_count - 5} more")
    
    if stale_count > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

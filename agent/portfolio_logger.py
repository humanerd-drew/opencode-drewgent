"""
Portfolio System — Drewgent Second Brain Project Lens

Provides:
- Project structure creation (called from project_context.py)
- Project listing for CLI /portfolio command

Obsidian view: portfolio/index.md (Dataview queries)
Drewgent brain: memories/ (unchanged, project tags applied at session end)
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

import logging

from agent.obsidian_graph import ensure_backlink, links_frontmatter_lines, wiki_link

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------
# Paths (use drewgent_constants so profiles work)
# --------------------------------------------------------------------------

def _portfolio_root() -> Path:
    from drewgent_constants import get_drewgent_home
    return get_drewgent_home() / "portfolio"


def _projects_root() -> Path:
    from drewgent_constants import get_drewgent_home
    return get_drewgent_home() / "projects"


# --------------------------------------------------------------------------
# Project Creation
# --------------------------------------------------------------------------

def create_project(
    project_id: str,
    title: str,
    why: str = "",
    tags: List[str] = None,
    priority: str = "medium",
    deadline: str = "",
) -> Dict[str, Any]:
    """Create a new project structure.

    Called from project_context.py when /project create <name> is run.

    Creates:
    - portfolio/projects/<id>.md — Obsidian project note
    - projects/<id>/{artifacts/, episodes/, sessions/, src/} — local workspace

    Args:
        project_id: unique identifier (used in filenames/paths)
        title: human-readable title
        why: why this project was started
        tags: list of tags
        priority: high/medium/low
        deadline: YYYY-MM-DD format

    Returns:
        dict with created paths
    """
    if tags is None:
        tags = []

    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")

    # Portfolio project note
    portfolio_proj_dir = _portfolio_root() / "projects"
    portfolio_proj_dir.mkdir(parents=True, exist_ok=True)

    project_note = portfolio_proj_dir / f"{project_id}.md"
    parent_links = [
        wiki_link("P5-ego/SELF_MODEL"),
        wiki_link("portfolio/index"),
    ]

    frontmatter = [
        "---",
        f"title: {title}",
        f"id: {project_id}",
        "status: active",
        f"priority: {priority}",
        f"tags: [{', '.join(tags)}]",
        f"started: {date_str}",
    ]
    frontmatter.extend(links_frontmatter_lines(parent_links))
    if deadline:
        frontmatter.append(f"deadline: {deadline}")
    frontmatter.extend([
        f"created: {now.isoformat()}",
        "---",
        "",
        f"# {title}",
        "",
    ])
    if why:
        frontmatter.extend(["## Why This Project", why, ""])
    frontmatter.extend([
        "## Current State",
        "<!-- Describe current progress -->",
        "",
        "## Next Actions",
        "- [ ] ",
        "",
        "---",
        f"*Created by Drewgent Portfolio System on {now.isoformat()}*",
    ])

    project_note.write_text("\n".join(frontmatter), encoding="utf-8")
    ensure_backlink(_portfolio_root() / "index.md", project_note, _portfolio_root().parent)
    logger.info(f"Created portfolio project: {project_note}")

    # Local workspace (artifacts, episodes, sessions, src)
    actual_proj_dir = _projects_root() / project_id
    actual_proj_dir.mkdir(parents=True, exist_ok=True)
    (actual_proj_dir / "artifacts").mkdir(exist_ok=True)
    (actual_proj_dir / "artifacts" / "experimental").mkdir(exist_ok=True)
    (actual_proj_dir / "episodes").mkdir(exist_ok=True)
    (actual_proj_dir / "sessions").mkdir(exist_ok=True)
    (actual_proj_dir / "src").mkdir(exist_ok=True)

    return {
        "project_id": project_id,
        "portfolio_note": str(project_note),
        "actual_dir": str(actual_proj_dir),
        "artifacts_dir": str(actual_proj_dir / "artifacts"),
        "episodes_dir": str(actual_proj_dir / "episodes"),
    }


# --------------------------------------------------------------------------
# Project Listing
# --------------------------------------------------------------------------

def list_projects() -> List[Dict[str, Any]]:
    """List all projects in portfolio/projects/."""
    projects = []
    projects_dir = _portfolio_root() / "projects"

    if not projects_dir.exists():
        return projects

    for md_file in projects_dir.glob("*.md"):
        if md_file.name.startswith("."):
            continue
        try:
            frontmatter = _parse_frontmatter(md_file.read_text(encoding="utf-8"))
            projects.append({
                "id": md_file.stem,
                "path": str(md_file),
                "title": frontmatter.get("title", md_file.stem),
                "status": frontmatter.get("status", "unknown"),
                "priority": frontmatter.get("priority", "medium"),
                "tags": frontmatter.get("tags", []),
                "started": frontmatter.get("started", ""),
                "deadline": frontmatter.get("deadline", ""),
            })
        except Exception:
            projects.append({
                "id": md_file.stem,
                "path": str(md_file),
                "title": md_file.stem,
                "status": "unknown",
                "priority": "medium",
                "tags": [],
                "started": "",
                "deadline": "",
            })

    return projects


# --------------------------------------------------------------------------
# Utilities
# --------------------------------------------------------------------------

def _parse_frontmatter(content: str) -> Dict[str, Any]:
    """Parse YAML frontmatter from markdown content."""
    frontmatter = {}

    if not content.startswith("---"):
        return frontmatter

    parts = content.split("---", 2)
    if len(parts) < 3:
        return frontmatter

    fm_text = parts[1].strip()

    for line in fm_text.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        if ": " in line:
            key, val = line.split(": ", 1)
            key = key.strip()
            val = val.strip()

            if val.startswith("[") and val.endswith("]"):
                items = [x.strip() for x in val[1:-1].split(",")]
                frontmatter[key] = items
            else:
                frontmatter[key] = val
        elif line.endswith(":"):
            frontmatter[line[:-1].strip()] = True

    return frontmatter

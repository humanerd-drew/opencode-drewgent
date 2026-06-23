"""Obsidian graph integrity helpers for Drewgent-generated markdown.

Drewgent uses the Obsidian graph as a user-visible view of its internal
NeuronFS structure. Generated notes should not become orphan nodes unless they
are explicitly telemetry/log output.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable


GRAPH_EXEMPT_PARTS = {
    ".archive",
    ".trash",
    "archive",
    "cache",
    "checkpoints",
    "monitor",
    "output",
    "retired",
    "sessions",
    "source",
    "vector",
}


def vault_relative_path(path: Path, vault_root: Path | None = None) -> str:
    """Return a POSIX vault-relative markdown path without the .md suffix."""
    resolved = path.resolve()
    root = (vault_root or _infer_vault_root(path)).resolve()
    try:
        rel = resolved.relative_to(root)
    except ValueError:
        rel = path
    rel_str = rel.as_posix()
    return rel_str[:-3] if rel_str.endswith(".md") else rel_str


def wiki_link(path_or_target: Path | str, vault_root: Path | None = None) -> str:
    """Return an Obsidian wikilink for a path or already-relative target."""
    if isinstance(path_or_target, Path):
        target = vault_relative_path(path_or_target, vault_root)
    else:
        target = path_or_target.strip()
        if target.endswith(".md"):
            target = target[:-3]
    return f"[[{target}]]"


def normalize_link_target(link: str) -> str:
    """Extract the target portion from a wikilink or raw target string."""
    target = link.strip().strip('"').strip("'")
    if target.startswith("[[") and target.endswith("]]"):
        target = target[2:-2]
    target = target.split("|", 1)[0].split("#", 1)[0].strip()
    return target[:-3] if target.endswith(".md") else target


def is_graph_exempt(path: Path) -> bool:
    """Return True for generated telemetry/corpus paths exempt from graph rules."""
    parts = set(path.parts)
    if parts & GRAPH_EXEMPT_PARTS:
        return True
    rel = path.as_posix()
    return (
        "/cron/output/" in rel
        or "/qa-evidence/" in rel
        or "/external-links/all_sources/" in rel
        or "/external-links/ixdf_raw/" in rel
        or "/external-links/nngroup_raw/" in rel
        or "/seo-articles/" in rel
    )


def ensure_related_section(content: str, links: Iterable[str], heading: str = "Related") -> str:
    """Ensure a markdown section contains each wikilink once."""
    wanted = [link for link in dict.fromkeys(links) if link]
    if not wanted:
        return content

    existing = set(re.findall(r"\[\[([^\]]+)\]\]", content))
    missing = [link for link in wanted if normalize_link_target(link) not in existing]
    if not missing:
        return content

    section_re = re.compile(rf"(^## {re.escape(heading)}\n)(.*?)(?=^## |\Z)", re.M | re.S)
    match = section_re.search(content)
    lines = [f"- {link}" for link in missing]
    if match:
        body = match.group(2).rstrip()
        addition = ("\n" if body else "") + "\n".join(lines) + "\n\n"
        return content[: match.end(2)] + addition + content[match.end(2) :]

    suffix = "" if content.endswith("\n") else "\n"
    return content + f"{suffix}\n## {heading}\n" + "\n".join(lines) + "\n"


def ensure_backlink(parent_path: Path, child_path: Path, vault_root: Path | None = None) -> None:
    """Add a child wikilink to a parent note's Related section."""
    if not parent_path.exists() or is_graph_exempt(parent_path):
        return
    content = parent_path.read_text(encoding="utf-8")
    updated = ensure_related_section(content, [wiki_link(child_path, vault_root)])
    if updated != content:
        parent_path.write_text(updated, encoding="utf-8")


def links_frontmatter_lines(links: Iterable[str]) -> list[str]:
    """Return YAML lines for an Obsidian-friendly links field."""
    unique = [link for link in dict.fromkeys(links) if link]
    if not unique:
        return []
    return ["links:"] + [f'  - "{link}"' for link in unique]


def _infer_vault_root(path: Path) -> Path:
    current = path.resolve()
    if current.is_file():
        current = current.parent
    for candidate in [current, *current.parents]:
        if (candidate / ".obsidian").exists():
            return candidate
    return current

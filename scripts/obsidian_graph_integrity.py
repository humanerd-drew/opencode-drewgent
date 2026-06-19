#!/usr/bin/env python3
"""Check Drewgent Obsidian graph integrity for generated brain notes."""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent.obsidian_graph import is_graph_exempt, normalize_link_target


WIKI_RE = re.compile(r"!?\[\[([^\]]+)\]\]")
CHECK_PREFIXES = (
    "P0-brainstem/",
    "P1-limbic/",
    "P2-hippocampus/memories/",
    "P3-sensors/",
    "P4-cortex/",
    "P5-ego/",
    "P6-prefrontal/",
    "memories/",
    "skills/",
)


def _vault_rel(path: Path, root: Path) -> str:
    rel = path.resolve().relative_to(root.resolve()).as_posix()
    return rel[:-3] if rel.endswith(".md") else rel


def _links(content: str) -> set[str]:
    # Obsidian does not treat wikilink-shaped text in code as graph links.
    content = re.sub(r"```.*?```", "", content, flags=re.S)
    content = re.sub(r"`[^`\n]*`", "", content)
    return {normalize_link_target(match) for match in WIKI_RE.findall(content)}


def _aliases(content: str) -> set[str]:
    """Extract simple title/aliases from YAML frontmatter for link resolution."""
    aliases = set()
    match = re.match(r"^---\n(.*?)\n---", content, flags=re.S)
    if not match:
        return aliases
    frontmatter = match.group(1)
    title = re.search(r"^title:\s*(.+)$", frontmatter, flags=re.M)
    if title:
        aliases.add(title.group(1).strip().strip('"').strip("'"))
    alias_block = re.search(r"^aliases:\n((?:\s*-\s*.+\n?)+)", frontmatter, flags=re.M)
    if alias_block:
        for item in re.findall(r"^\s*-\s*(.+)$", alias_block.group(1), flags=re.M):
            aliases.add(item.strip().strip('"').strip("'"))
    return aliases


def _canonical_key(value: str) -> str:
    """Normalize human-facing aliases for resilient wikilink resolution."""
    value = normalize_link_target(value)
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.lower()
    value = value.replace("’", "'").replace("`", "'")
    value = re.sub(r"['’]", "", value)
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def check_graph(root: Path) -> dict:
    root = root.resolve()
    md_files = []
    target_files = []
    seen_realpaths = set()
    candidate_files = []
    for path in root.rglob("*.md"):
        realpath = path.resolve()
        if ".git" in path.parts or "venv" in path.parts or not realpath.is_relative_to(root):
            continue
        target_files.append(path)
        if realpath in seen_realpaths or is_graph_exempt(path):
            continue
        rel = _vault_rel(path, root)
        candidate_files.append((path, rel, realpath))

    if any(rel.startswith(CHECK_PREFIXES) for _, rel, _ in candidate_files):
        candidate_files = [
            (path, rel, realpath)
            for path, rel, realpath in candidate_files
            if rel.startswith(CHECK_PREFIXES)
        ]

    for path, _rel, realpath in candidate_files:
        if realpath in seen_realpaths:
            continue
        seen_realpaths.add(realpath)
        md_files.append(path)

    contents = {}
    outlinks = {}
    inbound = {path: set() for path in md_files}
    by_target = {}
    by_canonical = {}
    by_stem = {}

    def add_target(alias: str, path: Path) -> None:
        alias = normalize_link_target(alias)
        by_target.setdefault(alias, path)
        key = _canonical_key(alias)
        if key:
            by_canonical.setdefault(key, path)

    for path in target_files:
        rel = _vault_rel(path, root)
        text = path.read_text(encoding="utf-8", errors="ignore")
        add_target(rel, path)
        by_stem.setdefault(path.stem, path)
        add_target(path.stem, path)
        for alias in _aliases(text):
            add_target(alias, path)
        parts = rel.split("/")
        for idx in range(1, len(parts)):
            add_target("/".join(parts[idx:]), path)

    for path in root.rglob("*.neuron"):
        if ".git" in path.parts or "venv" in path.parts:
            continue
        rel = path.resolve().relative_to(root).as_posix()
        target = rel[:-7] if rel.endswith(".neuron") else rel
        add_target(target, path)
        add_target(path.stem, path)

    for path in md_files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        contents[path] = text
        outlinks[path] = _links(text)

    broken = []
    for src, targets in outlinks.items():
        for target in targets:
            dst = by_target.get(target) or by_canonical.get(_canonical_key(target)) or by_stem.get(Path(target).name)
            if dst:
                if dst in inbound:
                    inbound[dst].add(src)
            elif not target.startswith(("http://", "https://", "mailto:")):
                broken.append({"source": _vault_rel(src, root), "target": target})

    orphan_like = []
    for path in md_files:
        rel = _vault_rel(path, root)
        if path.name.lower() == "index.md":
            continue
        if not outlinks[path] or not inbound[path]:
            orphan_like.append(
                {
                    "path": rel,
                    "outgoing_count": len(outlinks[path]),
                    "inbound_count": len(inbound[path]),
                }
            )

    return {
        "checked": len(md_files),
        "broken_links": broken,
        "orphan_like": orphan_like,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", help="Vault root")
    parser.add_argument("--json", action="store_true", help="Print JSON")
    args = parser.parse_args()

    result = check_graph(Path(args.root))
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"checked: {result['checked']}")
        print(f"broken_links: {len(result['broken_links'])}")
        print(f"orphan_like: {len(result['orphan_like'])}")
        for item in result["orphan_like"][:50]:
            print(
                f"- {item['path']} "
                f"(out={item['outgoing_count']}, in={item['inbound_count']})"
            )
    return 1 if result["broken_links"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

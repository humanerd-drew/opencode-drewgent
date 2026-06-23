"""Helpers that keep runtime homes out of source import precedence."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import MutableSequence

from drewgent_constants import get_drewgent_home


def _resolve_path_entry(entry: str, cwd: Path) -> Path | None:
    if entry == "":
        return cwd.resolve()
    try:
        return Path(entry).expanduser().resolve()
    except (OSError, RuntimeError):
        return None


def ensure_source_import_precedence(
    project_root: Path,
    runtime_home: Path | None = None,
    *,
    path_entries: MutableSequence[str] | None = None,
    cwd: Path | None = None,
) -> dict[str, list[str]]:
    """Place source root before runtime home entries in import search path.

    ``DREW_HOME`` is data/config state, not a Python source root. When a gateway
    or CLI process is launched from inside the runtime home, Python's empty
    ``sys.path`` entry can otherwise resolve top-level modules from runtime
    stubs before the canonical source tree.
    """
    entries = path_entries if path_entries is not None else sys.path
    cwd = (cwd or Path.cwd()).resolve()
    project_root = project_root.expanduser().resolve()
    runtime_home = (runtime_home or get_drewgent_home()).expanduser().resolve()

    removed_runtime_entries: list[str] = []
    kept: list[str] = []
    for entry in list(entries):
        resolved = _resolve_path_entry(entry, cwd)
        if resolved == project_root:
            continue
        if resolved == runtime_home:
            removed_runtime_entries.append(entry)
            continue
        kept.append(entry)

    entries[:] = [str(project_root), *kept]
    return {"removed_runtime_entries": removed_runtime_entries}

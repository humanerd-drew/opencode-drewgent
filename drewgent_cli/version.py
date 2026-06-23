"""
Version scheme for Drewgent:

  drewgent-{upstream_version}-{date}-{seq}
  Example: drewgent-0.7.0-20260509-1

Where:
  upstream_version = Drewgent fork's base version from upstream (e.g., 0.7.0)
  date              = UTC date of Drewgent release in YYYYMMDD format
  seq               = sequence number for releases on the same (upstream_version, date)

Upstream sync tagging:
  upstream-{upstream_tag}
  Example: upstream-v2026.5.7

The __version__ string encodes where Drewgent stands relative to upstream:
  - upstream_version tells you which upstream version this Drewgent fork is based on
  - date tells you when Drewgent made its own release
  - seq differentiates multiple Drewgent releases on the same day
"""

from __future__ import annotations

import datetime
import os
import subprocess
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Constants for upstream tracking
# ---------------------------------------------------------------------------

# The upstream version Drewgent forked from (matches hermes-agent version at fork time)
UPSTREAM_VERSION = "0.7.0"

# The upstream git remote name (can be overridden via env for testing)
UPSTREAM_REMOTE = os.environ.get("DREWAGENT_UPSTREAM_REMOTE", "upstream")

# Fallback version when git is unavailable
FALLBACK_VERSION = f"drewgent-{UPSTREAM_VERSION}-20260403-1"
FALLBACK_UPSTREAM_TAG = "v2026.4.3"


def _run_git(cmd: list[str], cwd: Optional[str] = None) -> str:
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd or _repo_root(),
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout.strip()
    except Exception:
        return ""


def _repo_root() -> str:
    return str(Path(__file__).resolve().parents[2])


def _upstream_tag() -> str:
    """Return the most recent upstream tag reachable from HEAD, e.g. 'v2026.5.7'."""
    # Find the most recent tag on any branch that is a direct upstream tag
    tags = _run_git(["git", "tag", "--sort=-v:refname", "-l", "v*"]).splitlines()
    if not tags:
        return FALLBACK_UPSTREAM_TAG

    # Walk ancestry from HEAD to find the newest upstream tag that is an ancestor of HEAD
    for tag in tags:
        ret = _run_git(["git", "merge-base", "--is-ancestor", tag, "HEAD"])
        if ret == "" or ret == "true":
            return tag
    return FALLBACK_UPSTREAM_TAG


def _drewgent_tags() -> list[str]:
    """Return all Drewgent release tags, newest first."""
    tags = _run_git(["git", "tag", "--sort=-v:refname", "-l", "drewgent-*"]).splitlines()
    return tags


def _parse_drewgent_tag(tag: str) -> Optional[tuple[str, str, str]]:
    """
    Parse 'drewgent-{upstream_version}-{date}-{seq}' into its components.
    Returns (upstream_version, date, seq) or None if tag doesn't match.
    """
    if not tag.startswith("drewgent-"):
        return None
    parts = tag.split("-")
    if len(parts) != 4:
        return None
    _, upstream_version, date, seq = parts
    return (upstream_version, date, seq)


def _current_utc_date() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d")


def _next_seq(upstream_version: str, date: str) -> int:
    """
    Find the next sequence number for (upstream_version, date) combination.
    """
    tags = _drewgent_tags()
    max_seq = 0
    for tag in tags:
        parsed = _parse_drewgent_tag(tag)
        if parsed and parsed[0] == upstream_version and parsed[1] == date:
            try:
                seq = int(parsed[2])
                if seq > max_seq:
                    max_seq = seq
            except ValueError:
                pass
    return max_seq + 1


# ---------------------------------------------------------------------------
# Public version interface
# ---------------------------------------------------------------------------

def get_version() -> str:
    """
    Returns the current Drewgent version string.
    Format: drewgent-{upstream_version}-{date}-{seq}
    Example: drewgent-0.7.0-20260509-1

    Returns fallback version if git is unavailable.
    """
    upstream_version = UPSTREAM_VERSION
    date = _current_utc_date()
    seq = _next_seq(upstream_version, date)
    return f"drewgent-{upstream_version}-{date}-{seq}"


def get_upstream_tag() -> str:
    """
    Returns the upstream git tag this Drewgent is synced to.
    Format: upstream-{tag}, e.g. 'upstream-v2026.5.7'

    Returns fallback if git is unavailable.
    """
    return f"upstream-{_upstream_tag()}"


def get_release_date() -> str:
    """Returns UTC date string in YYYYMMDD format."""
    return _current_utc_date()
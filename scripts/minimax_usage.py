#!/usr/bin/env python3
"""
minimax-usage — Token Plan 사용량/리셋 터미널 표시.

API: GET https://api.minimax.io/v1/api/openplatform/coding_plan/remains
Auth: MINIMAX_API_KEY (~/.drewgent/.env)

출력: model별 (general, video) 현재 5h interval + 주간 사용량/리셋까지 남은 시간.

사용법:
    ~/.drewgent/scripts/minimax_usage.py            # 컬러 출력
    ~/.drewgent/scripts/minimax_usage.py --json     # machine-readable
    ~/.drewgent/scripts/minimax_usage.py --watch 30 # 30초마다 refresh (Ctrl-C 종료)
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

API_URL = "https://api.minimax.io/v1/api/openplatform/coding_plan/remains"
ENV_PATH = Path.home() / ".drewgent" / ".env"
DEFAULT_CACHE_PATH = Path.home() / ".drewgent" / "cache" / "minimax_usage.json"
DEFAULT_CACHE_TTL = 60  # seconds

# ANSI colors (auto-disabled if NO_COLOR set or stdout not a tty)
USE_COLOR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if USE_COLOR else text


def bold(t: str) -> str:
    return c("1", t)


def dim(t: str) -> str:
    return c("2", t)


def green(t: str) -> str:
    return c("32", t)


def yellow(t: str) -> str:
    return c("33", t)


def red(t: str) -> str:
    return c("31", t)


def cyan(t: str) -> str:
    return c("36", t)


def bar(percent_used: float, width: int = 30) -> str:
    """Filled block bar showing percent USED (not remaining)."""
    pct = max(0.0, min(100.0, percent_used))
    filled = int(round(pct / 100 * width))
    empty = width - filled
    # Color gradient: green → yellow → red
    if pct < 50:
        bar_color = "32"  # green
    elif pct < 80:
        bar_color = "33"  # yellow
    else:
        bar_color = "31"  # red
    return c(bar_color, "█" * filled) + dim("░" * empty)


def fmt_duration(ms: int) -> str:
    """Render a millisecond duration as 'Xh Ym' or 'Xd Yh'."""
    if ms is None or ms < 0:
        return "-"
    total_s = ms // 1000
    days, rem = divmod(total_s, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    if days:
        return f"{days}d {hours}h"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def fmt_epoch_ms(ms: int | None) -> str:
    if not ms:
        return "-"
    dt = datetime.fromtimestamp(ms / 1000, tz=timezone.utc).astimezone()
    return dt.strftime("%Y-%m-%d %H:%M %Z")


def load_api_key() -> str | None:
    """Read MINIMAX_API_KEY from ~/.drewgent/.env (no shell sourcing needed)."""
    if not ENV_PATH.is_file():
        return None
    for line in ENV_PATH.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("MINIMAX_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def fetch_remaining(api_key: str) -> dict[str, Any]:
    req = Request(
        API_URL,
        headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
        method="GET",
    )
    with urlopen(req, timeout=15) as resp:  # noqa: S310 — fixed provider URL
        return json.loads(resp.read().decode("utf-8"))


STATUS_LABELS = {
    0: "inactive",
    1: "active",
    2: "exhausted",
    3: "unlimited",
}


# ---------------------------------------------------------------------------
# Cache + RPROMPT support
# ---------------------------------------------------------------------------

def color_for_pct(used: float | None) -> str:
    """ANSI color code by usage percent (green/yellow/red)."""
    if used is None:
        return ""
    if used < 50:
        return "32"  # green
    if used < 80:
        return "33"  # yellow
    return "31"  # red


def render_rprompt(data: dict, stale: bool = False) -> str:
    """Compact single-line RPROMPT for zsh right prompt.

    Format: ``mm 5h:51% 2h44m · wk:52% 5d16h``
    (with ANSI color on the percentages, ⏳ prefix when cache is stale)
    """
    models = data.get("model_remains") or []
    general = next((m for m in models if m.get("model_name") == "general"), None)
    if not general:
        return "mm: ?"

    interval_used = (100 - general["current_interval_remaining_percent"]) if general.get("current_interval_remaining_percent") is not None else None
    weekly_used = (100 - general["current_weekly_remaining_percent"]) if general.get("current_weekly_remaining_percent") is not None else None
    interval_remains = general.get("remains_time") or 0
    weekly_remains = general.get("weekly_remains_time") or 0

    i_color = color_for_pct(interval_used)
    w_color = color_for_pct(weekly_used)
    stale_marker = "\033[2m⏳\033[0m " if stale else ""

    if USE_COLOR:
        return (
            f"{stale_marker}\033[1m\033[36mToken Plan\033[0m  "
            f"\033[{i_color}m5h:{interval_used:.0f}%\033[0m {fmt_duration(interval_remains)}  ·  "
            f"\033[{w_color}mwk:{weekly_used:.0f}%\033[0m {fmt_duration(weekly_remains)}"
        )
    return (
        f"{stale_marker}Token Plan  "
        f"5h:{interval_used:.0f}% {fmt_duration(interval_remains)}  ·  "
        f"wk:{weekly_used:.0f}% {fmt_duration(weekly_remains)}"
    )


def _lock_path(cache_path: Path) -> Path:
    return cache_path.with_suffix(cache_path.suffix + ".lock")


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


def spawn_background_refresh(cache_path: Path) -> bool:
    """Spawn detached ``--write-cache`` process. Returns True if spawned.

    Uses a PID lock file so multiple invocations don't pile up.
    """
    lock = _lock_path(cache_path)
    if lock.exists():
        try:
            pid = int(lock.read_text().strip())
            if _pid_alive(pid):
                return False  # another refresh in flight
        except (ValueError, OSError):
            pass
        lock.unlink(missing_ok=True)

    try:
        proc = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "--write-cache", str(cache_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            close_fds=True,
        )
        lock.write_text(str(proc.pid))
        return True
    except Exception:
        return False


def write_cache_mode(api_key: str, cache_path: Path) -> int:
    """Fetch from API and write cache atomically. Silent on success."""
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    lock = _lock_path(cache_path)
    lock.write_text(str(os.getpid()))
    try:
        try:
            payload = fetch_remaining(api_key)
        except (HTTPError, URLError) as e:
            print(f"[mm-usage] refresh failed: {e}", file=sys.stderr)
            return 1
        # Atomic write via temp + rename (avoids partial reads)
        tmp = cache_path.with_suffix(cache_path.suffix + ".tmp")
        blob = {"fetched_at": time.time(), "data": payload}
        tmp.write_text(json.dumps(blob, ensure_ascii=False))
        tmp.replace(cache_path)
        return 0
    finally:
        lock.unlink(missing_ok=True)


def rprompt_mode(cache_path: Path, ttl: int) -> int:
    """Read cache, render RPROMPT. If stale, spawn bg refresh (fire-and-forget)."""
    if not cache_path.exists():
        if not load_api_key():
            print("Token Plan  n/a", end="")
        else:
            # We have a key. Try to spawn a refresh — even if the lock is
            # held (a sibling refresh already in flight), the user still
            # gets fresh data soon, so the right-prompt label is the same.
            spawn_background_refresh(cache_path)
            print("Token Plan  refreshing…", end="")
        return 0

    try:
        blob = json.loads(cache_path.read_text())
    except (json.JSONDecodeError, OSError):
        print("Token Plan  ?", end="")
        return 0

    age = time.time() - blob.get("fetched_at", 0)
    stale = age > ttl
    if stale and load_api_key():
        spawn_background_refresh(cache_path)

    print(render_rprompt(blob["data"], stale=stale), end="")
    return 0


def maybe_refresh_mode(cache_path: Path, ttl: int) -> int:
    """Spawn bg refresh only if cache is stale or missing."""
    if not cache_path.exists():
        if load_api_key():
            spawn_background_refresh(cache_path)
        return 0
    try:
        blob = json.loads(cache_path.read_text())
    except (json.JSONDecodeError, OSError):
        if load_api_key():
            spawn_background_refresh(cache_path)
        return 0
    if time.time() - blob.get("fetched_at", 0) > ttl and load_api_key():
        spawn_background_refresh(cache_path)
    return 0


def render_text(payload: dict[str, Any]) -> str:
    models = payload.get("model_remains") or []
    base = payload.get("base_resp") or {}
    if base.get("status_code") != 0:
        return red(f"API error: {base.get('status_msg', 'unknown')}")

    out: list[str] = []
    out.append(bold(cyan("Token Plan usage")))
    out.append(dim(f"fetched {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"))
    out.append("")

    for m in models:
        name = m.get("model_name", "?")
        interval_pct_remaining = m.get("current_interval_remaining_percent")
        weekly_pct_remaining = m.get("current_weekly_remaining_percent")
        interval_status = m.get("current_interval_status")
        weekly_status = m.get("current_weekly_status")
        interval_remains_ms = m.get("remains_time")
        weekly_remains_ms = m.get("weekly_remains_time")
        interval_start = m.get("start_time")
        interval_end = m.get("end_time")
        weekly_start = m.get("weekly_start_time")
        weekly_end = m.get("weekly_end_time")

        interval_used = None if interval_pct_remaining is None else (100 - interval_pct_remaining)
        weekly_used = None if weekly_pct_remaining is None else (100 - weekly_pct_remaining)

        out.append(bold(f"● {name}"))
        out.append(f"  5h interval")
        if interval_pct_remaining is not None:
            out.append(f"    used:      {bar(interval_used)}  {interval_used:5.1f}%   ({STATUS_LABELS.get(interval_status, '?')})")
        if interval_remains_ms is not None:
            out.append(f"    resets in: {green(fmt_duration(interval_remains_ms))}  (at {dim(fmt_epoch_ms(interval_end))})")
        out.append(f"    window:    {dim(fmt_epoch_ms(interval_start))} → {dim(fmt_epoch_ms(interval_end))}")
        out.append(f"  weekly")
        if weekly_pct_remaining is not None:
            out.append(f"    used:      {bar(weekly_used)}  {weekly_used:5.1f}%   ({STATUS_LABELS.get(weekly_status, '?')})")
        if weekly_remains_ms is not None:
            out.append(f"    resets in: {green(fmt_duration(weekly_remains_ms))}  (at {dim(fmt_epoch_ms(weekly_end))})")
        out.append(f"    window:    {dim(fmt_epoch_ms(weekly_start))} → {dim(fmt_epoch_ms(weekly_end))}")
        out.append("")

    return "\n".join(out).rstrip()


def main() -> int:
    p = argparse.ArgumentParser(description="Show MiniMax Token Plan usage and reset time.")
    p.add_argument("--json", action="store_true", help="emit raw API response as JSON")
    p.add_argument("--watch", type=int, metavar="SEC", help="refresh every N seconds until interrupted")
    p.add_argument("--write-cache", metavar="PATH", help="fetch and atomically write cache, silent (used for bg refresh)")
    p.add_argument("--rprompt", action="store_true", help="render compact string for zsh RPROMPT (reads cache, may trigger bg refresh)")
    p.add_argument("--maybe-refresh", action="store_true", help="spawn background refresh iff cache is stale or missing")
    p.add_argument("--cache-path", metavar="PATH", help="override default cache location")
    p.add_argument("--cache-ttl", type=int, default=DEFAULT_CACHE_TTL, metavar="SEC",
                   help=f"cache freshness window in seconds (default {DEFAULT_CACHE_TTL})")
    args = p.parse_args()

    cache_path = Path(args.cache_path) if args.cache_path else DEFAULT_CACHE_PATH
    api_key = load_api_key()

    # --- Cache/rprompt modes don't require interactive API key handling ---
    if args.write_cache:
        if not api_key:
            print("[mm-usage] MINIMAX_API_KEY not found", file=sys.stderr)
            return 1
        return write_cache_mode(api_key, cache_path)
    if args.rprompt:
        return rprompt_mode(cache_path, args.cache_ttl)
    if args.maybe_refresh:
        return maybe_refresh_mode(cache_path, args.cache_ttl)

    # --- Pretty / json / watch modes need API key + interactive loop ---
    if not api_key:
        print(red("error: MINIMAX_API_KEY not found in ~/.drewgent/.env"), file=sys.stderr)
        return 1

    while True:
        try:
            payload = fetch_remaining(api_key)
        except HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")[:300]
            print(red(f"HTTP {e.code}: {body}"), file=sys.stderr)
            return 1
        except URLError as e:
            print(red(f"network error: {e.reason}"), file=sys.stderr)
            return 1

        if args.json:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            # clear screen on watch so refreshes don't pile up
            if args.watch and sys.stdout.isatty():
                print("\033[2J\033[H", end="")
            print(render_text(payload))

        if not args.watch:
            return 0
        try:
            time.sleep(args.watch)
        except KeyboardInterrupt:
            print()
            return 0


if __name__ == "__main__":
    sys.exit(main())

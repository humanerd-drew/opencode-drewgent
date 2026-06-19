#!/usr/bin/env python3
"""Cron output cleanup — delete files older than 7 days from all cron output dirs."""
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))
CRON_OUTPUT = Path.home() / ".drewgent" / "cron" / "output"
MAX_AGE_DAYS = 7
DRY_RUN = "--dry-run" in sys.argv

now_kst = datetime.now(KST)
cutoff = now_kst - timedelta(days=MAX_AGE_DAYS)
cutoff_ts = cutoff.timestamp()

total_deleted = 0
total_freed = 0

if not CRON_OUTPUT.exists():
    print("[SILENT]")
    sys.exit(0)

for board_dir in sorted(CRON_OUTPUT.iterdir()):
    if not board_dir.is_dir():
        continue
    for f in board_dir.iterdir():
        if not f.is_file() or f.suffix not in (".md", ".log"):
            continue
        mtime = f.stat().st_mtime
        if mtime < cutoff_ts:
            size = f.stat().st_size
            if DRY_RUN:
                print(f"  [dry-run] would delete: {f.name} ({size:,} bytes)")
            else:
                f.unlink()
                print(f"  deleted: {f.name} ({size:,} bytes)")
            total_deleted += 1
            total_freed += size

if total_deleted == 0:
    print("[SILENT]")
else:
    freed_mb = total_freed / (1024 * 1024)
    print(f"cleanup complete: deleted={total_deleted} freed={freed_mb:.1f}MB")
